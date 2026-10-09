#!/usr/bin/env python3
"""Independent mechanical verification of one D58 shard output.

Reads only the narrow posting/evidence Parquet files and their public receipt.
It does not read source text, rerun extraction, or assign semantic labels.
"""
import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import platform
import traceback
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

import run_one_shard as production

VERSION = "d58-one-shard-output-verifier-v1"
KEY = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def arrow_rows(batch):
    columns = batch.to_pydict()
    names = list(columns)
    count = len(columns[names[0]]) if names else 0
    return [{name: columns[name][i] for name in names} for i in range(count)]


def schema_description(schema):
    return [{"name": field.name, "type": str(field.type), "nullable": field.nullable}
            for field in schema]


def compact_hash(value):
    payload = json.dumps(value, ensure_ascii=True, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def normalized_counter(counter):
    return {str(key): int(counter[key]) for key in sorted(counter, key=lambda x: str(x))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--posting", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--production-receipt", required=True)
    parser.add_argument("--expected-runner-sha256", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--batch-size", type=int, default=4096)
    args = parser.parse_args()
    started = dt.datetime.now(dt.timezone.utc)

    posting_path = Path(args.posting)
    evidence_path = Path(args.evidence)
    receipt_path = Path(args.production_receipt)
    output_path = Path(args.output)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("status") != "complete":
        raise RuntimeError("production receipt is not complete")
    if receipt.get("identity", {}).get("runner_sha256") != args.expected_runner_sha256:
        raise RuntimeError("production runner digest differs from expected frozen digest")

    posting_sha = digest(posting_path)
    evidence_sha = digest(evidence_path)
    expected_outputs = receipt.get("outputs") or {}
    if posting_sha != expected_outputs.get("posting_sha256"):
        raise RuntimeError("posting hash differs from production receipt")
    if evidence_sha != expected_outputs.get("evidence_sha256"):
        raise RuntimeError("evidence hash differs from production receipt")

    posting_pf = pq.ParquetFile(posting_path)
    evidence_pf = pq.ParquetFile(evidence_path)
    if posting_pf.schema_arrow != production.POSTING_SCHEMA:
        raise RuntimeError("posting schema differs from frozen production schema")
    if evidence_pf.schema_arrow != production.EVIDENCE_SCHEMA:
        raise RuntimeError("evidence schema differs from frozen production schema")

    posting_counts = {}
    job_hashes = set()
    processing = collections.Counter()
    experience = collections.Counter()
    flag_true = collections.Counter()
    metadata_status = collections.Counter()
    created_year = collections.Counter()
    posting_rows = 0
    for batch in posting_pf.iter_batches(batch_size=args.batch_size):
        for row in arrow_rows(batch):
            key = tuple(row[name] for name in KEY)
            if key in posting_counts:
                raise RuntimeError("duplicate canonical locator in posting output")
            if row["JOB_HASH"] in job_hashes:
                raise RuntimeError("duplicate canonical JOB_HASH in posting output")
            evidence_count = row.get("evidence_count")
            if not isinstance(evidence_count, int) or evidence_count < 0:
                raise RuntimeError("invalid posting evidence_count")
            posting_counts[key] = evidence_count
            job_hashes.add(row["JOB_HASH"])
            posting_rows += 1
            processing[row.get("processing_status") or "null"] += 1
            experience[row.get("experience_status") or "null"] += 1
            metadata_status[row.get("metadata_join_status") or "null"] += 1
            created = row.get("CREATED")
            created_year[str(created.year) if created is not None else "missing"] += 1
            try:
                flags = json.loads(row.get("flags_json") or "{}")
            except (TypeError, ValueError):
                raise RuntimeError("posting flags_json is invalid")
            if not isinstance(flags, dict):
                raise RuntimeError("posting flags_json is not an object")
            for name, value in flags.items():
                if value is True:
                    flag_true[str(name)] += 1

    if posting_rows != posting_pf.metadata.num_rows:
        raise RuntimeError("streamed posting row count differs from footer")
    if posting_rows != expected_outputs.get("posting_rows"):
        raise RuntimeError("posting row count differs from production receipt")
    if posting_rows != receipt.get("canonical_usa_rows"):
        raise RuntimeError("posting row count differs from canonical USA count")

    evidence_groups = collections.Counter()
    completed_evidence_keys = set()
    observed_evidence_keys = set()
    current_key = None
    next_index = 0
    evidence_rows = 0

    def finish_key(key, observed_count):
        if key is None:
            return
        if posting_counts.get(key) != observed_count:
            raise RuntimeError("per-posting evidence count mismatch")
        completed_evidence_keys.add(key)

    for batch in evidence_pf.iter_batches(batch_size=args.batch_size):
        for row in arrow_rows(batch):
            key = tuple(row[name] for name in KEY)
            if key not in posting_counts:
                raise RuntimeError("evidence locator absent from posting output")
            if key != current_key:
                finish_key(current_key, next_index)
                if key in completed_evidence_keys:
                    raise RuntimeError("evidence locator reappears non-contiguously")
                current_key = key
                next_index = 0
                observed_evidence_keys.add(key)
            if row.get("evidence_index") != next_index:
                raise RuntimeError("evidence_index is not contiguous from zero")
            start, end, quote = row.get("start"), row.get("end"), row.get("quote")
            if (not isinstance(start, int) or not isinstance(end, int) or
                    start < 0 or end < start or not isinstance(quote, str) or
                    len(quote) != end - start):
                raise RuntimeError("invalid evidence span structure")
            if row.get("coordinate_system") != "normalized_unicode_codepoints":
                raise RuntimeError("unexpected evidence coordinate system")
            group = tuple("" if row.get(name) is None else str(row.get(name)) for name in
                          ("kind", "rule", "outcome_status", "heading_scope_status"))
            evidence_groups[group] += 1
            next_index += 1
            evidence_rows += 1
    finish_key(current_key, next_index)

    for key, expected_count in posting_counts.items():
        if key not in observed_evidence_keys and expected_count != 0:
            raise RuntimeError("posting declares evidence but has no evidence rows")
    if evidence_rows != evidence_pf.metadata.num_rows:
        raise RuntimeError("streamed evidence row count differs from footer")
    if evidence_rows != expected_outputs.get("evidence_rows"):
        raise RuntimeError("evidence row count differs from production receipt")
    if sum(posting_counts.values()) != evidence_rows:
        raise RuntimeError("sum of posting evidence_count differs from evidence rows")

    group_rows = [
        {"kind": key[0], "rule": key[1], "outcome_status": key[2],
         "heading_scope_status": key[3], "count": int(count)}
        for key, count in sorted(evidence_groups.items())
    ]
    posting_schema = schema_description(posting_pf.schema_arrow)
    evidence_schema = schema_description(evidence_pf.schema_arrow)
    completed = dt.datetime.now(dt.timezone.utc)
    result = {
        "status": "pass",
        "version": VERSION,
        "scope": "mechanical verification and bounded public profile; no source text read, extraction rerun or semantic certification",
        "production_job_id": receipt.get("job_id"),
        "production_runner_sha256": args.expected_runner_sha256,
        "production_receipt_sha256": digest(receipt_path),
        "posting_sha256": posting_sha,
        "evidence_sha256": evidence_sha,
        "posting_rows": posting_rows,
        "evidence_rows": evidence_rows,
        "canonical_locator_unique": len(posting_counts) == posting_rows,
        "canonical_job_hash_unique": len(job_hashes) == posting_rows,
        "evidence_locator_index_and_count_consistent": True,
        "evidence_span_structure_errors": 0,
        "posting_schema_sha256": compact_hash(posting_schema),
        "evidence_schema_sha256": compact_hash(evidence_schema),
        "evidence_group_count": len(group_rows),
        "evidence_group_counts_sha256": compact_hash(group_rows),
        "processing_status_counts": normalized_counter(processing),
        "experience_status_counts": normalized_counter(experience),
        "metadata_join_status_counts": normalized_counter(metadata_status),
        "created_year_counts": normalized_counter(created_year),
        "flag_true_counts": normalized_counter(flag_true),
        "runtime": {"python": platform.python_version(), "pyarrow": pa.__version__},
        "started_utc": started.isoformat(),
        "completed_utc": completed.isoformat(),
    }
    atomic_json(output_path, result)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Public failure output contains no record keys, paths, or source text.
        try:
            destination = Path(__import__("sys").argv[__import__("sys").argv.index("--output") + 1])
            atomic_json(destination, {
                "status": "fail", "version": VERSION,
                "error_type": type(exc).__name__, "error": str(exc)[:500],
                "completed_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            })
        except Exception:
            pass
        traceback.print_exc()
        raise
