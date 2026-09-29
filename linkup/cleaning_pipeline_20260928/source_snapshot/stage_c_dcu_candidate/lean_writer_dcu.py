#!/usr/bin/env python3
"""Drop-in lean-writer entrypoint using the conservative HIP batch mask.

All schemas, authoritative CPU regexes, offsets, ordering, caps, and receipts
come from the frozen writer/modules. Only two empty V5 modules and individual
enrichment technology families may be skipped after a sound DCU prefilter.
"""
from __future__ import annotations

import importlib.util
import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import re
import resource
import shutil
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from candidate_adapter import extract_enrich_prepared_batch
from prefilter import gpu_masks_with_metrics, load_frozen_enrichment, load_frozen_v6

HERE = Path(__file__).resolve().parent
ORIGINAL = HERE.parent / "stage_c_release_v1" / "lean_writer.py"
_spec = importlib.util.spec_from_file_location("frozen_lean_writer_dcu_host", str(ORIGINAL))
if _spec is None or _spec.loader is None:
    raise RuntimeError("cannot load frozen lean writer")
host = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(host)

DCU_EXECUTABLE = Path(os.environ.get("LINKUP_DCU_EXECUTABLE", ""))
BATCH_ROWS = int(os.environ.get("LINKUP_DCU_BATCH_ROWS", "131072"))
DCU_ARCH = os.environ.get("LINKUP_DCU_ARCH", "")
EXPECTED_EXECUTABLE_SHA256 = os.environ.get("LINKUP_DCU_EXECUTABLE_SHA256", "")
SOURCE_SHA256 = {
    "prefilter.py": "415c4a87b3ea61983b9588256a9e4348ce8f5f623c7771ef3c9e3101146d2835",
    "candidate_adapter.py": "e318932c69cd5d270def1ccc33134c3042e999f9cf0963afed1c0a8cdd42493b",
    "dcu_anchor_scan.hip.cpp": "c21cea4b8480a9f9acbc0f3656cfce3f3da6ae264b6ac1443fc2c13bd082d2f2",
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


if not str(DCU_EXECUTABLE) or not DCU_EXECUTABLE.is_file():
    raise RuntimeError("LINKUP_DCU_EXECUTABLE must name the compiled HIP scanner")
if not 4096 <= BATCH_ROWS <= 262144:
    raise RuntimeError("LINKUP_DCU_BATCH_ROWS must be 4096..262144")
if not re.fullmatch(r"gfx[0-9a-z]+", DCU_ARCH):
    raise RuntimeError("LINKUP_DCU_ARCH must identify the reviewed target, e.g. gfx906")
if not re.fullmatch(r"[0-9a-f]{64}", EXPECTED_EXECUTABLE_SHA256):
    raise RuntimeError("LINKUP_DCU_EXECUTABLE_SHA256 is required")
for source_name, expected_sha256 in SOURCE_SHA256.items():
    observed_sha256 = file_sha256(HERE / source_name)
    if observed_sha256 != expected_sha256:
        raise RuntimeError("DCU candidate source SHA-256 mismatch: " + source_name)
EXECUTABLE_SHA256 = file_sha256(DCU_EXECUTABLE)
if EXECUTABLE_SHA256 != EXPECTED_EXECUTABLE_SHA256:
    raise RuntimeError("compiled HIP scanner SHA-256 mismatch")
DCU_PROVENANCE = {
    "backend": "hip",
    "architecture": DCU_ARCH,
    "batch_rows": BATCH_ROWS,
    "prefilter_sha256": SOURCE_SHA256["prefilter.py"],
    "adapter_sha256": SOURCE_SHA256["candidate_adapter.py"],
    "hip_source_sha256": SOURCE_SHA256["dcu_anchor_scan.hip.cpp"],
    "executable_sha256": EXECUTABLE_SHA256,
    "frozen_v6_sha256": "d8df533693cb9c01f169df51cac184f144888a1595bb28207deb82952ad2f744",
    "frozen_v5_sha256": "336242bed5372e446dbdc2b2d02944e906024ee90138a2fa424b866aee7293dd",
    "frozen_enrichment_sha256": "cf0cf8fae3451d463430c14ebe6bf2a6dcc72b8239589ed2fbeb20ef0c4451c6",
}


def normalize_batch(args):
    """Normalize one disjoint batch in the shared bounded process pool."""
    texts, parser_path = args
    parser = load_frozen_v6(Path(parser_path))
    normalized = []; format_flags = []; valid = []
    for text in texts:
        if not isinstance(text, str):
            normalized.append(""); format_flags.append({}); valid.append(False)
            continue
        try:
            value, value_flags = parser._base._normalize_with_flags(text)
            normalized.append(value); format_flags.append(value_flags); valid.append(True)
        except Exception:
            normalized.append(""); format_flags.append({}); valid.append(False)
    return normalized, format_flags, valid


def interval_union_seconds(receipts, key):
    intervals = sorted(interval for item in receipts for interval in item.pop(key, []))
    if not intervals:
        return 0.0
    total = 0.0; start, end = intervals[0]
    for next_start, next_end in intervals[1:]:
        if next_start <= end:
            end = max(end, next_end)
        else:
            total += end - start; start, end = next_start, next_end
    return total + end - start


def worker(args):
    source, parser_path, enrichment_path, out_dir, start, count, cap = args
    parser = load_frozen_v6(Path(parser_path))
    enrichment = load_frozen_enrichment(Path(enrichment_path))
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=False)
    temp = Path(tempfile.mkdtemp(prefix="tmp.", dir=str(out)))
    writers = {
        "ad_status": host.pq.ParquetWriter(temp / "ad_status.parquet", host.AD_SCHEMA, compression="zstd"),
        "experience": host.pq.ParquetWriter(temp / "experience.parquet", host.EXP_SCHEMA, compression="zstd"),
        "technology": host.pq.ParquetWriter(temp / "technology.parquet", host.TECH_SCHEMA, compression="zstd"),
        "v6_audit": host.pq.ParquetWriter(temp / "v6_audit.parquet", host.AUDIT_SCHEMA, compression="zstd"),
    }
    buffers = {name: [] for name in writers}
    schemas = {"ad_status": host.AD_SCHEMA, "experience": host.EXP_SCHEMA,
               "technology": host.TECH_SCHEMA, "v6_audit": host.AUDIT_SCHEMA}

    def flush(force=False):
        for name in buffers:
            if buffers[name] and (force or len(buffers[name]) >= 512):
                writers[name].write_table(host.pa.Table.from_pylist(buffers[name], schema=schemas[name]))
                buffers[name] = []

    processed = exp_n = tech_n = audit_n = parse_n = trunc_n = incomplete_n = empty_n = 0
    started = time.monotonic(); pending = []
    parse_seconds = write_seconds = 0.0
    parse_intervals = []; write_intervals = []

    def consume(rows):
        nonlocal processed, exp_n, tech_n, audit_n, parse_n, trunc_n, incomplete_n, empty_n
        nonlocal parse_seconds, write_seconds
        phase = time.monotonic()
        payloads, results, _ = extract_enrich_prepared_batch(
            [row.get("DESCRIPTION") for row in rows],
            [row.pop("__DCU_NORMALIZED") for row in rows],
            [json.loads(row.pop("__DCU_FLAGS_JSON")) for row in rows],
            [row.pop("__DCU_VALID") for row in rows],
            [row.pop("__DCU_MASK") for row in rows], parser, enrichment,
        )
        phase_end = time.monotonic(); parse_seconds += phase_end - phase
        parse_intervals.append((phase, phase_end))
        phase = time.monotonic()
        for row, payload, result in zip(rows, payloads, results):
            flags = result["flags"]
            key = {name: row.get(name) for name, _ in host.KEYS}
            description_empty = not isinstance(row.get("DESCRIPTION"), str) or not row["DESCRIPTION"].strip()
            audits = [{**key, **item} for item in host.v6_audit_rows(payload, flags["enrichment_incomplete"])]
            ads = [{**key, "CREATED": row.get("CREATED"), "COUNTRY": row.get("COUNTRY"),
                    "STATE": row.get("STATE"), "DESCRIPTION_EMPTY": description_empty,
                    "NORMALIZATION_VERSION": payload.get("normalization_version"),
                    "PARSE_ERROR": flags["input_parse_error"],
                    "INPUT_EVIDENCE_TRUNCATED": flags["input_evidence_truncated"],
                    "ENRICHMENT_INCOMPLETE": flags["enrichment_incomplete"],
                    "EXPERIENCE_EVIDENCE_COUNT": len(result["experience_evidence"]),
                    "TECHNOLOGY_EVIDENCE_COUNT": len(result["technology_evidence"]),
                    "V6_AUDIT_EVIDENCE_COUNT": len(audits)}]
            exps = [{**key, **{k.upper(): v for k, v in item.items()}}
                    for item in result["experience_evidence"]]
            techs = [{**key, **{k.upper(): v for k, v in item.items()}}
                     for item in result["technology_evidence"]]
            buffers["ad_status"].extend(ads); buffers["experience"].extend(exps)
            buffers["technology"].extend(techs); buffers["v6_audit"].extend(audits)
            flush()
            processed += 1; exp_n += len(exps); tech_n += len(techs); audit_n += len(audits)
            empty_n += int(description_empty); parse_n += int(flags["input_parse_error"])
            trunc_n += int(flags["input_evidence_truncated"])
            incomplete_n += int(flags["enrichment_incomplete"])
        phase_end = time.monotonic(); write_seconds += phase_end - phase
        write_intervals.append((phase, phase_end))

    try:
        source_path = Path(source)
        if source_path.suffix == ".arrow":
            with host.pa.memory_map(str(source_path), "r") as mapped:
                row_iterator = iter(host.pa.ipc.open_file(mapped).read_all().to_pylist())
        else:
            row_iterator = host.iter_range(source_path, start, count)
        for row in row_iterator:
            pending.append(row)
            if len(pending) >= 4096:
                consume(pending); pending = []
        if pending: consume(pending)
        phase = time.monotonic(); flush(force=True)
        for writer_value in writers.values(): writer_value.close()
        phase_end = time.monotonic(); write_seconds += phase_end - phase
        write_intervals.append((phase, phase_end))
        writers = {}
        bytes_out = sum(path.stat().st_size for path in temp.iterdir())
        if bytes_out > cap: raise RuntimeError("chunk cap exceeded")
        for path in temp.iterdir(): os.replace(path, out / path.name)
        temp.rmdir()
        outputs = {}
        for path in sorted(out.glob("*.parquet")):
            parquet = host.pq.ParquetFile(path)
            outputs[path.name] = {"bytes": path.stat().st_size, "sha256": host.sha(path),
                                  "rows": parquet.metadata.num_rows,
                                  "row_groups": parquet.metadata.num_row_groups,
                                  "schema": str(parquet.schema_arrow)}
        receipt = {"status": "complete", "start": start, "requested_rows": count,
                   "processed_rows": processed, "description_empty_rows": empty_n,
                   "experience_rows": exp_n, "technology_rows": tech_n,
                   "v6_audit_rows": audit_n, "parse_errors": parse_n,
                   "truncated_rows": trunc_n, "enrichment_incomplete_rows": incomplete_n,
                   "output_bytes": bytes_out, "wall_seconds": time.monotonic() - started,
                   "cpu_parse_seconds": parse_seconds, "write_seconds": write_seconds,
                   "outputs": outputs}
        (out / "COMPLETE.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        returned = dict(receipt)
        returned["_parse_intervals"] = parse_intervals
        returned["_write_intervals"] = write_intervals
        return returned
    except Exception:
        for writer_value in writers.values(): writer_value.close()
        shutil.rmtree(temp, ignore_errors=True)
        raise


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True); ap.add_argument("--parser", required=True)
    ap.add_argument("--enrichment", required=True); ap.add_argument("--output-dir", required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--output-cap-bytes", type=int, required=True)
    args = ap.parse_args()
    root = Path(args.output_dir); root.mkdir(parents=True, exist_ok=False)
    source = Path(args.source); parquet = host.pq.ParquetFile(source)
    total = parquet.metadata.num_rows
    workers = max(1, min(args.workers, total)); chunk = (total + workers - 1) // workers
    scratch = Path(tempfile.mkdtemp(prefix="linkup-dcu-input."))
    tasks = []; started = time.monotonic()
    normalize_wall = gpu_wall = parse_write_wall = 0.0
    gpu_metrics = []
    try:
        with cf.ProcessPoolExecutor(max_workers=workers) as pool:
            if total:
                columns = ["JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW",
                           "CREATED", "COUNTRY", "STATE", "DESCRIPTION"]
                # Decode each row group once, then reuse this bounded pool for
                # parallel normalization and authoritative parse/write.
                table = parquet.read(columns=columns)
                raw_texts = table.column("DESCRIPTION").to_pylist()
                normalization_tasks = []
                for index in range(workers):
                    start = index * chunk; count = min(chunk, total - start)
                    if count:
                        normalization_tasks.append((raw_texts[start:start + count], args.parser))
                phase = time.monotonic()
                normalized_parts = list(pool.map(normalize_batch, normalization_tasks))
                normalize_wall = time.monotonic() - phase
                normalized = [value for part, _, _ in normalized_parts for value in part]
                format_flags = [value for _, part, _ in normalized_parts for value in part]
                valid = [value for _, _, part in normalized_parts for value in part]
                phase = time.monotonic(); masks = []
                for offset in range(0, total, BATCH_ROWS):
                    batch_masks, metrics = gpu_masks_with_metrics(
                        normalized[offset:offset + BATCH_ROWS], DCU_EXECUTABLE)
                    masks.extend(batch_masks); gpu_metrics.append(metrics)
                gpu_wall = time.monotonic() - phase
                table = table.append_column("__DCU_NORMALIZED", host.pa.array(normalized, type=host.pa.string()))
                table = table.append_column("__DCU_FLAGS_JSON", host.pa.array(
                    [json.dumps(item, sort_keys=True) for item in format_flags], type=host.pa.string()))
                table = table.append_column("__DCU_VALID", host.pa.array(valid, type=host.pa.bool_()))
                table = table.append_column("__DCU_MASK", host.pa.array(masks, type=host.pa.uint32()))
                del raw_texts, normalized, format_flags, valid, masks, normalized_parts
                for index in range(workers):
                    start = index * chunk; count = min(chunk, total - start)
                    if not count: continue
                    split = scratch / ("chunk_%02d.arrow" % index)
                    with host.pa.OSFile(str(split), "wb") as sink:
                        with host.pa.ipc.new_file(sink, table.schema) as arrow_writer:
                            arrow_writer.write_table(table.slice(start, count))
                    tasks.append((split, args.parser, args.enrichment,
                                  root / ("chunk_%02d" % index), 0, count,
                                  args.output_cap_bytes // workers))
                del table
            else:
                tasks.append((source, args.parser, args.enrichment, root / "chunk_00",
                              0, 0, args.output_cap_bytes))
            phase = time.monotonic()
            receipts = list(pool.map(worker, tasks))
            parse_write_wall = time.monotonic() - phase
        cpu_parse_wall = interval_union_seconds(receipts, "_parse_intervals")
        write_wall = interval_union_seconds(receipts, "_write_intervals")
        output_bytes = sum(path.stat().st_size for path in root.rglob("*") if path.is_file())
        if output_bytes > args.output_cap_bytes: raise RuntimeError("global cap exceeded")
        complete = {
            "status": "complete", "created_utc": datetime.now(timezone.utc).isoformat(),
            "source": str(source.resolve()), "source_bytes": source.stat().st_size,
            "source_sha256": host.sha(source), "parser_sha256": host.sha(args.parser),
            "enrichment_sha256": host.sha(args.enrichment),
            "processed_rows": sum(item["processed_rows"] for item in receipts),
            "experience_rows": sum(item["experience_rows"] for item in receipts),
            "technology_rows": sum(item["technology_rows"] for item in receipts),
            "v6_audit_rows": sum(item["v6_audit_rows"] for item in receipts),
            "description_empty_rows": sum(item["description_empty_rows"] for item in receipts),
            "parse_errors": sum(item["parse_errors"] for item in receipts),
            "truncated_rows": sum(item["truncated_rows"] for item in receipts),
            "enrichment_incomplete_rows": sum(item["enrichment_incomplete_rows"] for item in receipts),
            "output_bytes": output_bytes, "output_cap_bytes": args.output_cap_bytes,
            "wall_seconds": time.monotonic() - started, "workers": workers,
            "stage_wall_seconds": {
                "normalize": normalize_wall,
                "gpu_calls": gpu_wall,
                "cpu_parse": cpu_parse_wall,
                "write": write_wall,
                "cpu_parse_and_write": parse_write_wall,
                "cpu_parse_worker_max": max((item["cpu_parse_seconds"] for item in receipts), default=0.0),
                "write_worker_max": max((item["write_seconds"] for item in receipts), default=0.0),
            },
            "dcu_timing": {
                "calls": len(gpu_metrics),
                "kernel_milliseconds": sum(item["kernel_milliseconds"] for item in gpu_metrics),
                "subprocess_wall_seconds": sum(item["subprocess_wall_seconds"] for item in gpu_metrics),
                "rows": sum(item["rows"] for item in gpu_metrics),
            },
            "max_rss_kb": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
            "schemas": {"ad_status": str(host.AD_SCHEMA), "experience": str(host.EXP_SCHEMA),
                        "technology": str(host.TECH_SCHEMA), "v6_audit": str(host.AUDIT_SCHEMA)},
            "chunks": receipts, "dcu_provenance": DCU_PROVENANCE,
        }
        (root / "COMPLETE.json").write_text(json.dumps(complete, indent=2, sort_keys=True) + "\n")
        print(json.dumps(complete, sort_keys=True))
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__": main()
