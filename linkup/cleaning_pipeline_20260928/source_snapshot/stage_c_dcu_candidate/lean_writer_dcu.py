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

from candidate_adapter import extract_enrich_batch
from prefilter import load_frozen_enrichment, load_frozen_v6

HERE = Path(__file__).resolve().parent
ORIGINAL = HERE.parent / "stage_c_release_v1" / "lean_writer.py"
_spec = importlib.util.spec_from_file_location("frozen_lean_writer_dcu_host", str(ORIGINAL))
if _spec is None or _spec.loader is None:
    raise RuntimeError("cannot load frozen lean writer")
host = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(host)

DCU_EXECUTABLE = Path(os.environ.get("LINKUP_DCU_EXECUTABLE", ""))
BATCH_ROWS = int(os.environ.get("LINKUP_DCU_BATCH_ROWS", "4096"))
DCU_ARCH = os.environ.get("LINKUP_DCU_ARCH", "")
EXPECTED_EXECUTABLE_SHA256 = os.environ.get("LINKUP_DCU_EXECUTABLE_SHA256", "")
SOURCE_SHA256 = {
    "prefilter.py": "a884fb426d9269c480e1ab1e5760601412fa436573022c51f6fe5812dbca2803",
    "candidate_adapter.py": "f83c13d084e19e762a5f71b1441b1610f8de983664feb75c03ad8e404a53909a",
    "dcu_anchor_scan.hip.cpp": "54a804af0ae59db2aadbd8cb50f71935ed725b47d1b1980eeabfa890add58488",
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


if not str(DCU_EXECUTABLE) or not DCU_EXECUTABLE.is_file():
    raise RuntimeError("LINKUP_DCU_EXECUTABLE must name the compiled HIP scanner")
if not 256 <= BATCH_ROWS <= 16384:
    raise RuntimeError("LINKUP_DCU_BATCH_ROWS must be 256..16384")
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

    def consume(rows):
        nonlocal processed, exp_n, tech_n, audit_n, parse_n, trunc_n, incomplete_n, empty_n
        payloads, results, _ = extract_enrich_batch(
            [row.get("DESCRIPTION") for row in rows], parser, enrichment, DCU_EXECUTABLE
        )
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

    try:
        source_path = Path(source)
        if source_path.suffix == ".arrow":
            with host.pa.memory_map(str(source_path), "r") as mapped:
                row_iterator = iter(host.pa.ipc.open_file(mapped).read_all().to_pylist())
        else:
            row_iterator = host.iter_range(source_path, start, count)
        for row in row_iterator:
            pending.append(row)
            if len(pending) >= BATCH_ROWS:
                consume(pending); pending = []
        if pending: consume(pending)
        flush(force=True)
        for writer_value in writers.values(): writer_value.close()
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
                   "outputs": outputs}
        (out / "COMPLETE.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        return receipt
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
    try:
        if total:
            columns = ["JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW",
                       "CREATED", "COUNTRY", "STATE", "DESCRIPTION"]
            # Decode every Parquet row group once. The old equal-row workers each
            # reopened and decompressed every overlapping group independently.
            table = parquet.read(columns=columns)
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
        with cf.ProcessPoolExecutor(max_workers=workers) as pool:
            receipts = list(pool.map(worker, tasks))
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
