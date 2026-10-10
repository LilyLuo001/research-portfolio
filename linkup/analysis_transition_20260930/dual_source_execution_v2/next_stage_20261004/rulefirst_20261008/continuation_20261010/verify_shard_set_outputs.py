#!/usr/bin/env python3
"""Verify new D58 shard outputs and cross-shard key uniqueness on BU only."""
import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

VERSION = "d58-shard-set-output-verifier-v1"
KEY_COLUMNS = ["JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW"]


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def under(path, root):
    resolved = Path(path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        raise RuntimeError("input/output path is outside the admitted BU root")
    if str(resolved).startswith("/Users/"):
        raise RuntimeError("macOS workspace path is forbidden in BU verification")
    return resolved


def arrow_rows(batch):
    columns = batch.to_pydict()
    names = list(columns)
    count = len(columns[names[0]]) if names else 0
    return [{name: columns[name][i] for name in names} for i in range(count)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--verifier", required=True)
    parser.add_argument("--allowed-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--batch-size", type=int, default=8192)
    args = parser.parse_args()
    started = dt.datetime.now(dt.timezone.utc)
    allowed_root = Path(args.allowed_root).resolve()
    manifest_path = under(args.manifest, allowed_root)
    verifier_path = under(args.verifier, allowed_root)
    output_path = under(args.output, allowed_root)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("shards")
    if not isinstance(entries, list) or len(entries) < 2:
        raise RuntimeError("manifest must contain at least two shard entries")
    shard_ids = [str(item.get("shard_id")) for item in entries]
    if len(set(shard_ids)) != len(shard_ids) or any(x in {"", "None"} for x in shard_ids):
        raise RuntimeError("shard_id values must be nonempty and unique")

    qa_rows = []
    admitted = []
    for item in entries:
        posting = under(item["posting"], allowed_root)
        qa_output = under(item["qa_output"], allowed_root)
        if item.get("verify_new_output") is True:
            evidence = under(item["evidence"], allowed_root)
            receipt = under(item["production_receipt"], allowed_root)
            command = [
                sys.executable, str(verifier_path),
                "--posting", str(posting), "--evidence", str(evidence),
                "--production-receipt", str(receipt),
                "--expected-runner-sha256", str(item["expected_runner_sha256"]),
                "--output", str(qa_output),
            ]
            subprocess.check_call(command)
        qa = json.loads(qa_output.read_text(encoding="utf-8"))
        if qa.get("status") != "pass":
            raise RuntimeError("one shard QA is absent or not pass")
        current_posting_sha = digest(posting)
        if current_posting_sha != qa.get("posting_sha256"):
            raise RuntimeError("posting changed after its shard QA")
        admitted.append((str(item["shard_id"]), posting, qa))
        qa_rows.append({
            "shard_id": str(item["shard_id"]),
            "production_job_id": qa.get("production_job_id"),
            "posting_rows": qa.get("posting_rows"),
            "evidence_rows": qa.get("evidence_rows"),
            "posting_sha256": current_posting_sha,
            "shard_qa_sha256": digest(qa_output),
            "newly_verified_in_this_job": item.get("verify_new_output") is True,
        })

    seen_locator = set()
    seen_job_hash = set()
    source_files = collections.Counter()
    total_rows = 0
    for shard_id, posting, qa in admitted:
        shard_rows = 0
        parquet = pq.ParquetFile(posting)
        missing = set(KEY_COLUMNS) - set(parquet.schema_arrow.names)
        if missing:
            raise RuntimeError("posting lacks canonical key columns")
        for batch in parquet.iter_batches(batch_size=args.batch_size, columns=KEY_COLUMNS):
            for row in arrow_rows(batch):
                locator = tuple(row[name] for name in KEY_COLUMNS)
                job_hash = row["JOB_HASH"]
                if locator in seen_locator:
                    raise RuntimeError("canonical locator duplicated across shard set")
                if job_hash in seen_job_hash:
                    raise RuntimeError("canonical JOB_HASH duplicated across shard set")
                seen_locator.add(locator)
                seen_job_hash.add(job_hash)
                source_files[str(row["SOURCE_FILE"])] += 1
                shard_rows += 1
                total_rows += 1
        if shard_rows != qa.get("posting_rows"):
            raise RuntimeError("cross-shard scan row count differs from shard QA")

    if len(source_files) != len(entries):
        raise RuntimeError("shard set does not map one-to-one to distinct source files")
    completed = dt.datetime.now(dt.timezone.utc)
    result = {
        "status": "pass",
        "version": VERSION,
        "scope": "mechanical new-output QA plus cross-shard key uniqueness; no source text read, extraction rerun or semantic certification",
        "manifest_sha256": digest(manifest_path),
        "verifier_sha256": digest(verifier_path),
        "shards": qa_rows,
        "shard_count": len(entries),
        "distinct_source_file_count": len(source_files),
        "posting_rows": total_rows,
        "canonical_locator_unique_across_shards": len(seen_locator) == total_rows,
        "canonical_job_hash_unique_across_shards": len(seen_job_hash) == total_rows,
        "runtime": {"python": platform.python_version(), "pyarrow": pa.__version__},
        "started_utc": started.isoformat(),
        "completed_utc": completed.isoformat(),
    }
    atomic_json(output_path, result)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        try:
            destination = Path(sys.argv[sys.argv.index("--output") + 1])
            atomic_json(destination, {
                "status": "fail", "version": VERSION,
                "error_type": type(exc).__name__, "error": str(exc)[:500],
                "completed_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            })
        except Exception:
            pass
        raise
