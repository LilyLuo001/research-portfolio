#!/usr/bin/env python3
"""Bounded V4 candidate/performance trial over raw LinkUp Parquet files.

This program is deliberately limited to four deterministically selected files
and at most 4,000 physical rows per file.  Its rows are parser candidates, not
validated labels and not a probability or national sample.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
import os
import platform
import resource
import shutil
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import pyarrow as pa
import pyarrow.parquet as pq


RUNNER_VERSION = "bounded-v4-candidate-performance-v1"
FROZEN_PARSER_SHA256 = "19da310725580bc0ff12c2088e0c5b969558474eda5f7b92d5ab37a3bd92bfbc"
DEFAULT_FILE_COUNT = 4
DEFAULT_ROWS_PER_FILE = 4000
DEFAULT_BATCH_SIZE = 256
DEFAULT_WORKERS = 4
DEFAULT_OUTPUT_CAP_BYTES = 250_000_000
MODULES = ("software", "ai", "experience", "education", "tasks")


OUTPUT_SCHEMA = pa.schema([
    pa.field("JOB_HASH", pa.string()),
    pa.field("SOURCE_FILE", pa.string()),
    pa.field("SOURCE_ROW", pa.int64()),
    pa.field("RAW_SHA256", pa.string()),
    pa.field("NORMALIZED_SHA256", pa.string()),
    pa.field("STATUS", pa.string()),
    pa.field("HAS_PARSE_ERROR", pa.bool_()),
    pa.field("EVIDENCE_TRUNCATED", pa.bool_()),
    pa.field("ERROR_COUNT", pa.int32()),
    pa.field("CANDIDATE_JSON", pa.string()),
])


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(str(path), flags, 0o444)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _select_inputs(manifest: Mapping[str, Any], region: str, count: int) -> List[Dict[str, Any]]:
    entries = manifest.get(region)
    if not isinstance(entries, list):
        raise ValueError("manifest has no region list: %s" % region)
    ordered = sorted(entries, key=lambda x: (str(x["file_name"]), str(x["path"])))
    if len(ordered) < count:
        raise ValueError("region %s has only %d inputs" % (region, len(ordered)))
    selected = [dict(item) for item in ordered[:count]]
    names = [item["file_name"] for item in selected]
    if len(set(names)) != len(names):
        raise ValueError("selected provider basenames are not unique")
    return selected


def _source_stat(entry: Mapping[str, Any]) -> Dict[str, Any]:
    path = Path(str(entry["path"]))
    stat = path.stat()
    expected_size = int(entry["bytes"])
    if stat.st_size != expected_size:
        raise ValueError("input size differs from audited manifest for %s" % path)
    return {
        "file_name": str(entry["file_name"]),
        "path": str(path),
        "manifest_bytes": expected_size,
        "manifest_sha256": str(entry["sha256"]),
        "stat_size": stat.st_size,
        "stat_mtime_ns": stat.st_mtime_ns,
    }


def _runner_sha() -> str:
    return _sha256_file(Path(__file__).resolve())


def _build_identity(args: argparse.Namespace, entries: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    manifest_path = Path(args.manifest).resolve()
    parser_path = Path(args.parser).resolve()
    actual_parser_sha = _sha256_file(parser_path)
    if actual_parser_sha != FROZEN_PARSER_SHA256:
        raise ValueError("frozen parser SHA256 mismatch: %s" % actual_parser_sha)
    inputs = [_source_stat(entry) for entry in entries]
    config = {
        "region": args.region,
        "selection_rule": "lexical_file_name_then_path_first_n",
        "file_count": args.file_count,
        "rows_per_file": args.rows_per_file,
        "batch_size": args.batch_size,
        "workers": args.workers,
        "output_cap_bytes_decimal": args.output_cap_bytes,
        "per_shard_cap_bytes_decimal": (args.output_cap_bytes - 1_000_000) // args.file_count,
        "identity_and_receipt_reserve_bytes_decimal": 1_000_000,
        "candidate_only": True,
        "sample_design": "computational_performance_trial_not_probability_or_national_sample",
    }
    core = {
        "runner_version": RUNNER_VERSION,
        "runner_sha256": _runner_sha(),
        "parser_path": str(parser_path),
        "parser_sha256": actual_parser_sha,
        "manifest_path": str(manifest_path),
        "manifest_sha256": _sha256_file(manifest_path),
        "config": config,
        "inputs": inputs,
    }
    core["job_hash"] = _sha256_bytes(_canonical(core).encode("utf-8"))
    return core


def _ensure_identity(path: Path, identity: Mapping[str, Any]) -> None:
    if path.exists():
        if _load_json(path) != identity:
            raise RuntimeError("existing output identity differs; code, config, manifest, parser, path, or source stat changed")
    else:
        _write_json_exclusive(path, identity)


def _load_parser(path: str):
    spec = importlib.util.spec_from_file_location("frozen_requirement_candidates", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen parser")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.extract


def _rss_mb() -> float:
    value = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    # Linux reports KiB; macOS reports bytes.  Production Slurm targets Linux.
    return value / (1024.0 if platform.system() != "Darwin" else 1024.0 * 1024.0)


def _aggregate_status(payload: Mapping[str, Any]) -> str:
    if payload.get("errors"):
        return "parse_error"
    summaries = payload.get("summary") or {}
    if any((summaries.get(module) or {}).get("status") == "candidate" for module in MODULES):
        return "candidate"
    return "no_candidate"


def _row_result(job_hash: Any, description: Any, source_file: str, source_row: int, extract) -> Dict[str, Any]:
    try:
        payload = extract(description)
        if not isinstance(payload, dict):
            raise TypeError("extract did not return dict")
    except Exception as exc:
        payload = {
            "record_kind": "CANDIDATES", "candidate_only": True,
            "normalized_text": "", "source_fingerprint_sha256": None,
            "normalized_text_fingerprint_sha256": None,
            "summary": {m: {"status": "parse_error", "candidate_count": 0} for m in MODULES},
            "evidence": [], "evidence_truncated": False,
            "module_evidence_truncated": {m: False for m in MODULES},
            "errors": ["runner caught %s: %s" % (type(exc).__name__, exc)],
        }
    errors = payload.get("errors") or []
    raw_sha = _sha256_bytes(description.encode("utf-8")) if isinstance(description, str) else None
    # The parser's own fingerprints are checked rather than silently trusted.
    if isinstance(description, str) and payload.get("source_fingerprint_sha256") != raw_sha:
        errors = list(errors) + ["source_fingerprint_sha256 mismatch"]
        payload["errors"] = errors
    return {
        "JOB_HASH": None if job_hash is None else str(job_hash),
        "SOURCE_FILE": source_file,
        "SOURCE_ROW": source_row,
        "RAW_SHA256": raw_sha,
        "NORMALIZED_SHA256": payload.get("normalized_text_fingerprint_sha256"),
        "STATUS": _aggregate_status(payload),
        "HAS_PARSE_ERROR": bool(errors),
        "EVIDENCE_TRUNCATED": bool(payload.get("evidence_truncated", False)),
        "ERROR_COUNT": len(errors),
        "CANDIDATE_JSON": _canonical(payload),
    }


def _shard_paths(output_dir: Path, index: int, file_name: str) -> Tuple[Path, Path]:
    safe = "%02d_%s" % (index, file_name.replace(".snappy.parquet", "").replace(".parquet", ""))
    return output_dir / (safe + ".candidates.parquet"), output_dir / (safe + ".receipt.json")


def _verify_completed(output_path: Path, receipt_path: Path, job_hash: str, source: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    if not output_path.exists() and not receipt_path.exists():
        return None
    if not output_path.is_file() or not receipt_path.is_file():
        raise RuntimeError("partial prior shard exists: %s" % output_path.name)
    receipt = _load_json(receipt_path)
    checks = (
        receipt.get("job_hash") == job_hash,
        receipt.get("source") == source,
        receipt.get("output_bytes") == output_path.stat().st_size,
        receipt.get("output_sha256") == _sha256_file(output_path),
        receipt.get("output_rows") == pq.ParquetFile(output_path).metadata.num_rows,
        pq.ParquetFile(output_path).schema_arrow.equals(OUTPUT_SCHEMA),
    )
    if not all(checks):
        raise RuntimeError("prior shard failed resume verification: %s" % output_path.name)
    return receipt


def _process_file(task: Mapping[str, Any]) -> Dict[str, Any]:
    started = time.monotonic()
    cpu_started = time.process_time()
    source = task["source"]
    source_path = Path(source["path"])
    output_path = Path(task["output_path"])
    receipt_path = Path(task["receipt_path"])
    tmp_path = output_path.with_name(output_path.name + ".tmp.%d" % os.getpid())
    rows = 0
    batches = 0
    projected_arrow_bytes = 0
    raw_text_utf8_bytes = 0
    parse_errors = 0
    truncated = 0
    statuses = {"candidate": 0, "no_candidate": 0, "parse_error": 0}
    writer = None
    try:
        extract = _load_parser(task["parser_path"])
        parquet = pq.ParquetFile(source_path)
        names = set(parquet.schema_arrow.names)
        missing = {"JOB_HASH", "DESCRIPTION"} - names
        if missing:
            raise ValueError("source missing columns: %s" % sorted(missing))
        writer = pq.ParquetWriter(tmp_path, OUTPUT_SCHEMA, compression="snappy")
        for batch in parquet.iter_batches(batch_size=task["batch_size"], columns=["JOB_HASH", "DESCRIPTION"]):
            if rows >= task["rows_per_file"]:
                break
            take = min(batch.num_rows, task["rows_per_file"] - rows)
            sliced = batch.slice(0, take)
            projected_arrow_bytes += sliced.nbytes
            values = sliced.to_pylist()
            out = []
            for offset, value in enumerate(values):
                item = _row_result(value.get("JOB_HASH"), value.get("DESCRIPTION"), str(source_path), rows + offset, extract)
                out.append(item)
                if isinstance(value.get("DESCRIPTION"), str):
                    raw_text_utf8_bytes += len(value["DESCRIPTION"].encode("utf-8"))
                statuses[item["STATUS"]] = statuses.get(item["STATUS"], 0) + 1
                parse_errors += int(item["HAS_PARSE_ERROR"])
                truncated += int(item["EVIDENCE_TRUNCATED"])
            writer.write_table(pa.Table.from_pylist(out, schema=OUTPUT_SCHEMA), row_group_size=task["batch_size"])
            rows += take
            batches += 1
            if tmp_path.stat().st_size > task["per_shard_cap_bytes"]:
                raise RuntimeError("per-shard output cap exceeded")
        writer.close()
        writer = None
        output_bytes = tmp_path.stat().st_size
        if output_bytes > task["per_shard_cap_bytes"]:
            raise RuntimeError("per-shard output cap exceeded")
        os.replace(str(tmp_path), str(output_path))
        receipt = {
            "receipt_version": 1,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "job_hash": task["job_hash"],
            "source": source,
            "output_file": output_path.name,
            "output_sha256": _sha256_file(output_path),
            "output_bytes": output_bytes,
            "output_rows": rows,
            "arrow_batches": batches,
            "status_counts": statuses,
            "parse_error_rows": parse_errors,
            "truncated_rows": truncated,
            "wall_seconds": time.monotonic() - started,
            "cpu_seconds": time.process_time() - cpu_started,
            "worker_peak_rss_mb": _rss_mb(),
            "input_logical_bytes": int(source["stat_size"]),
            "projected_arrow_bytes_for_selected_rows": projected_arrow_bytes,
            "raw_text_utf8_bytes_for_selected_rows": raw_text_utf8_bytes,
            "rows_per_wall_second": rows / max(time.monotonic() - started, 1e-9),
            "rows_per_cpu_second": rows / max(time.process_time() - cpu_started, 1e-9),
            "bytes_unit_note": "file and projected/raw text sizes are bytes; MB RSS is 1024^2 bytes; whole-file bytes are storage context, selected-row byte metrics are actual logical/projected inputs",
        }
        _write_json_exclusive(receipt_path, receipt)
        return receipt
    except Exception:
        if writer is not None:
            writer.close()
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
        raise


def run(args: argparse.Namespace) -> int:
    for name in ("file_count", "rows_per_file", "batch_size", "workers", "output_cap_bytes"):
        if getattr(args, name) <= 0:
            raise ValueError("%s must be positive" % name)
    if args.file_count != 4 or args.rows_per_file > 4000 or args.batch_size not in (128, 256) or args.workers > 4:
        raise ValueError("initial bounded limits require 4 files, <=4000 rows/file, batch 128/256, <=4 workers")
    if args.output_cap_bytes > 1_000_000_000:
        raise ValueError("persistent output cap may not exceed 1 GB decimal")
    if args.output_cap_bytes <= 1_000_000:
        raise ValueError("output cap must leave the fixed 1 MB receipt/identity reserve")
    required_headroom = args.output_cap_bytes + 50_000_000
    if args.confirmed_headroom_bytes < required_headroom:
        raise ValueError("confirmed user-quota headroom must be at least %d bytes" % required_headroom)

    manifest = _load_json(Path(args.manifest))
    selected = _select_inputs(manifest, args.region, args.file_count)
    identity = _build_identity(args, selected)
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    identity_path = output_dir / "IDENTITY.json"
    _ensure_identity(identity_path, identity)
    complete_path = output_dir / "COMPLETE.json"
    if complete_path.exists():
        complete = _load_json(complete_path)
        if complete.get("job_hash") != identity["job_hash"]:
            raise RuntimeError("COMPLETE receipt identity mismatch")
        for index, source in enumerate(identity["inputs"]):
            output_path, receipt_path = _shard_paths(output_dir, index, source["file_name"])
            if _verify_completed(output_path, receipt_path, identity["job_hash"], source) is None:
                raise RuntimeError("COMPLETE receipt exists but a verified shard is missing")
        print(_canonical({"status": "already_complete", "job_hash": identity["job_hash"]}))
        return 0

    lock_path = output_dir / ("RUNNING.%s.lock" % identity["job_hash"])
    lock_fd = os.open(str(lock_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        os.write(lock_fd, ("pid=%d\n" % os.getpid()).encode("ascii"))
    finally:
        os.close(lock_fd)

    run_started = time.monotonic()
    receipts: List[Dict[str, Any]] = []
    tasks = []
    try:
        for index, source in enumerate(identity["inputs"]):
            output_path, receipt_path = _shard_paths(output_dir, index, source["file_name"])
            verified = _verify_completed(output_path, receipt_path, identity["job_hash"], source)
            if verified is not None:
                verified = dict(verified)
                verified["resume_verified_skip"] = True
                receipts.append(verified)
                continue
            tasks.append({
                "source": source, "output_path": str(output_path), "receipt_path": str(receipt_path),
                "parser_path": identity["parser_path"], "job_hash": identity["job_hash"],
                "rows_per_file": args.rows_per_file, "batch_size": args.batch_size,
                "per_shard_cap_bytes": (args.output_cap_bytes - 1_000_000) // args.file_count,
            })
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
            future_map = {pool.submit(_process_file, task): task for task in tasks}
            for future in concurrent.futures.as_completed(future_map):
                receipts.append(future.result())
        receipts.sort(key=lambda item: item["source"]["file_name"])
        persistent_bytes = sum(int(item["output_bytes"]) for item in receipts)
        if persistent_bytes > args.output_cap_bytes:
            raise RuntimeError("global persistent output cap exceeded")
        report = {
            "receipt_version": 1,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "job_hash": identity["job_hash"],
            "candidate_only": True,
            "formal_semantic_release": False,
            "sample_design": "computational/performance trial; selected source rows are not a probability or national sample",
            "evidence_time_status": "unknown",
            "selected_files": args.file_count,
            "actual_rows": sum(int(item["output_rows"]) for item in receipts),
            "status_counts": {status: sum(int(item["status_counts"].get(status, 0)) for item in receipts) for status in ("candidate", "no_candidate", "parse_error")},
            "parse_error_rows": sum(int(item["parse_error_rows"]) for item in receipts),
            "truncated_rows": sum(int(item["truncated_rows"]) for item in receipts),
            "persistent_parquet_bytes": persistent_bytes,
            "persistent_output_cap_bytes_decimal": args.output_cap_bytes,
            "wall_seconds": time.monotonic() - run_started,
            "sum_worker_cpu_seconds": sum(float(item["cpu_seconds"]) for item in receipts if not item.get("resume_verified_skip")),
            "max_worker_peak_rss_mb": max([float(item["worker_peak_rss_mb"]) for item in receipts] or [0.0]),
            "projected_arrow_bytes_for_selected_rows": sum(int(item["projected_arrow_bytes_for_selected_rows"]) for item in receipts),
            "raw_text_utf8_bytes_for_selected_rows": sum(int(item["raw_text_utf8_bytes_for_selected_rows"]) for item in receipts),
            "workers": receipts,
        }
        existing_persistent_bytes = sum(path.stat().st_size for path in output_dir.iterdir() if path.is_file())
        complete_receipt_bytes = len((json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n").encode("utf-8"))
        if existing_persistent_bytes + complete_receipt_bytes > args.output_cap_bytes:
            raise RuntimeError("total persistent output including identity and receipts would exceed cap")
        _write_json_exclusive(complete_path, report)
        print(_canonical(report))
        return 0
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", required=True, choices=("kunshan", "wuzhen"))
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--parser", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--file-count", type=int, default=DEFAULT_FILE_COUNT)
    parser.add_argument("--rows-per-file", type=int, default=DEFAULT_ROWS_PER_FILE)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, choices=(128, 256))
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--output-cap-bytes", type=int, default=DEFAULT_OUTPUT_CAP_BYTES)
    parser.add_argument("--confirmed-headroom-bytes", type=int, required=True,
                        help="user-quota headroom confirmed outside this program; shared df space is not sufficient")
    return parser


if __name__ == "__main__":
    try:
        sys.exit(run(_parser().parse_args()))
    except Exception as exc:
        print("FATAL: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        traceback.print_exc()
        sys.exit(2)
