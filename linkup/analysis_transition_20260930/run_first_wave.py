#!/usr/bin/env python3
"""Receipt-gated, resumable driver for the existing release-first table builder."""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

EXPECTED_VERSION = "release_first_tables_v1"
EXPECTED_SHARDS = 2464


def load_json(path: Path):
    return json.loads(path.read_text())


def sha256(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def receipt_summary_id(path: Path):
    return hashlib.sha256(json.dumps(load_json(path), sort_keys=True).encode()).hexdigest()


def atomic_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(tmp, path)


def validate_gate(path: Path):
    gate = load_json(path)
    if gate.get("status") != "complete" or gate.get("final_publication_complete") is not True:
        raise RuntimeError("global publication gate is not complete")
    if gate.get("total_shards") != EXPECTED_SHARDS:
        raise RuntimeError("global gate does not cover the frozen 2,464-shard plan")
    return gate


def load_plan_ids(paths):
    ids = []
    for path in paths:
        ids.extend(json.loads(line)["shard_id"] for line in path.read_text().splitlines() if line.strip())
    if len(ids) != EXPECTED_SHARDS or len(set(ids)) != EXPECTED_SHARDS:
        raise RuntimeError("frozen plans must contain exactly 2,464 unique shard IDs")
    return set(ids)


def validate_shard_identity(row):
    sid = row["shard_id"]
    receipt_path = Path(row["receipt"])
    shard_dir = Path(row["shard_dir"])
    receipt = load_json(receipt_path)
    if receipt.get("status") != "published_verified" or receipt.get("shard_id") != sid:
        raise RuntimeError(sid + ": published receipt identity mismatch")
    complete_path = shard_dir / "SHARD_COMPLETE.json"
    if not complete_path.is_file():
        raise FileNotFoundError(sid + ": published SHARD_COMPLETE.json missing")
    if receipt.get("shard_complete_sha256") != sha256(complete_path):
        raise RuntimeError(sid + ": SHARD_COMPLETE digest differs from receipt")
    complete = load_json(complete_path)
    if receipt.get("shard_complete") != complete or complete.get("status") != "complete":
        raise RuntimeError(sid + ": SHARD_COMPLETE content/status differs from receipt")
    accounting = complete.get("accounting", {})
    if accounting.get("shard_id") != sid:
        raise RuntimeError(sid + ": SHARD_COMPLETE accounting shard identity mismatch")
    if not accounting.get("row_conservation") or sum(accounting.get("disposition_counts", {}).values()) != accounting.get("raw_rows"):
        raise RuntimeError(sid + ": receipt accounting does not conserve rows")


def load_manifest(path: Path, frozen_ids):
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    required = {"shard_id", "shard_dir", "receipt"}
    manifest_ids = {r.get("shard_id") for r in rows}
    if len(rows) != EXPECTED_SHARDS or manifest_ids != frozen_ids:
        raise RuntimeError("manifest shard IDs must equal the frozen-plan shard IDs")
    for row in rows:
        if not required <= set(row):
            raise RuntimeError("manifest row lacks shard_id, shard_dir or receipt")
        if not Path(row["shard_dir"]).is_dir() or not Path(row["receipt"]).is_file():
            raise FileNotFoundError("manifest input missing for shard " + str(row["shard_id"]))
        validate_shard_identity(row)
    return sorted(rows, key=lambda r: r["shard_id"])


def summary_valid(path: Path, receipt_path: Path):
    try:
        item = load_json(path)
        return (item.get("version") == EXPECTED_VERSION and item.get("shards") == 1
                and item.get("leaf_summary_ids") == [receipt_summary_id(receipt_path)])
    except (OSError, ValueError, TypeError):
        return False


def run_one(builder: Path, row: dict, summary: Path):
    summary.parent.mkdir(parents=True, exist_ok=True)
    receipt = Path(row["receipt"])
    validate_shard_identity(row)
    if summary_valid(summary, receipt):
        return "resumed"
    subprocess.run([
        sys.executable, str(builder), "shard", "--shard-dir", row["shard_dir"],
        "--receipt", row["receipt"], "--output", str(summary)
    ], check=True)
    if not summary_valid(summary, receipt):
        raise RuntimeError("builder emitted invalid summary for " + row["shard_id"])
    return "built"


def main():
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True,
                        help="Private JSONL: shard_id, absolute shard_dir, absolute receipt")
    parser.add_argument("--plans", type=Path, nargs="+", required=True,
                        help="Frozen regional plan JSONL files; their union defines exact shard identity")
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--builder", type=Path,
                        default=here.parent / "stage_c_release_v1" / "build_release_first_tables.py")
    args = parser.parse_args()
    if not 1 <= args.workers <= 8:
        raise SystemExit("--workers must be between 1 and 8")
    gate = validate_gate(args.gate.resolve())
    plans = [path.resolve() for path in args.plans]
    frozen_ids = load_plan_ids(plans)
    rows = load_manifest(args.manifest.resolve(), frozen_ids)
    builder = args.builder.resolve()
    if not builder.is_file():
        raise FileNotFoundError(builder)
    run_config = {
        "version": 1, "builder": str(builder), "builder_sha256": sha256(builder),
        "gate_sha256": sha256(args.gate.resolve()), "manifest_sha256": sha256(args.manifest.resolve()),
        "plan_sha256": {str(path): sha256(path) for path in plans}, "shards": EXPECTED_SHARDS
    }
    config_path = args.work_dir.resolve() / "RUN_CONFIG.json"
    if config_path.exists() and load_json(config_path) != run_config:
        raise RuntimeError("work directory is bound to a different builder/gate/manifest/plan configuration")
    if not config_path.exists():
        atomic_json(config_path, run_config)
    summaries = args.work_dir.resolve() / "shard_summaries"
    outputs = args.work_dir.resolve() / "release_first_tables"
    if outputs.exists():
        raise RuntimeError("merged output already exists; preserve it or choose a new --work-dir")

    counts = {"built": 0, "resumed": 0}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        future_rows = {
            pool.submit(run_one, builder, row, summaries / (row["shard_id"] + ".json")): row
            for row in rows
        }
        for future in concurrent.futures.as_completed(future_rows):
            counts[future.result()] += 1

    summary_paths = [summaries / (row["shard_id"] + ".json") for row in rows]
    subprocess.run([sys.executable, str(builder), "merge", "--summaries",
                    *map(str, summary_paths), "--output-dir", str(outputs)], check=True)
    report = load_json(outputs / "CONSERVATION_REPORT.json")
    if report.get("status") != "complete" or report.get("shards") != EXPECTED_SHARDS:
        raise RuntimeError("merged conservation report failed")
    atomic_json(args.work_dir.resolve() / "FIRST_WAVE_RUN_RECEIPT.json", {
        "status": "complete", "builder": str(builder), "builder_sha256": sha256(builder),
        "gate_sha256": sha256(args.gate.resolve()), "manifest_sha256": sha256(args.manifest.resolve()),
        "workers": args.workers, "shards": EXPECTED_SHARDS, "summary_actions": counts,
        "conservation_report_sha256": sha256(outputs / "CONSERVATION_REPORT.json"),
        "privacy": "receipt hashes and aggregate counts only; no raw text or person data"
    })


if __name__ == "__main__":
    main()
