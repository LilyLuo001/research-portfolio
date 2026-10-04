#!/usr/bin/env python3
"""Validate a cached offline shard and failure evidence; performs no inference."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from validate_extraction_v1_1 import SCHEMA_PATH, validate_record


ROOT = Path(__file__).resolve().parent
PROMPT_PATH = ROOT / "prompts" / "extraction_v1_1.md"


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-shard", type=Path, required=True)
    parser.add_argument("--prediction-cache", type=Path, required=True)
    parser.add_argument("--failure-evidence", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    source_rows = read_jsonl(args.source_shard)
    prediction_rows = read_jsonl(args.prediction_cache)
    failure_rows = read_jsonl(args.failure_evidence)
    source_by_id = {str(row.get("record_id", "")): row for row in source_rows}
    if "" in source_by_id or len(source_by_id) != len(source_rows):
        raise ValueError("source shard requires unique nonempty record_id")
    if any(not isinstance(row.get("original_text"), str) for row in source_rows):
        raise ValueError("source shard requires string original_text")
    prediction_by_id = {str(row.get("record_id", "")): row for row in prediction_rows}
    if "" in prediction_by_id or len(prediction_by_id) != len(prediction_rows):
        raise ValueError("prediction cache requires unique nonempty record_id")
    failure_by_id: dict[str, dict[str, Any]] = {}
    required_failure = {"record_id", "stage", "error_type", "message", "retry_count"}
    for row in failure_rows:
        record_id = str(row.get("record_id", ""))
        if not required_failure <= set(row) or not record_id or record_id in failure_by_id:
            raise ValueError("failure evidence requires unique record_id plus stage/error_type/message/retry_count")
        if not isinstance(row["retry_count"], int) or row["retry_count"] < 0:
            raise ValueError("failure retry_count must be a nonnegative integer")
        failure_by_id[record_id] = row
    overlap = sorted(set(prediction_by_id) & set(failure_by_id))
    unknown = sorted((set(prediction_by_id) | set(failure_by_id)) - set(source_by_id))
    record_errors: dict[str, list[str]] = {}
    for record_id, prediction in prediction_by_id.items():
        if record_id in source_by_id:
            found = validate_record(prediction, source_by_id[record_id]["original_text"], record_id)
            if found:
                record_errors[record_id] = found
    valid_ids = set(prediction_by_id) - set(record_errors) - set(overlap) - set(unknown)
    failed_ids = set(failure_by_id) - set(overlap) - set(unknown)
    pending_ids = sorted(set(source_by_id) - valid_ids - failed_ids)
    receipt = {
        "version": "offline_cached_shard_receipt_v1.1.0",
        "route": "offline_import_only_no_model_or_api_call",
        "inputs": {
            "source_shard_sha256": file_sha(args.source_shard),
            "prediction_cache_sha256": file_sha(args.prediction_cache) if args.prediction_cache.exists() else None,
            "failure_evidence_sha256": file_sha(args.failure_evidence) if args.failure_evidence.exists() else None,
            "schema_sha256": file_sha(SCHEMA_PATH),
            "prompt_sha256": file_sha(PROMPT_PATH),
        },
        "counts": {
            "source": len(source_rows), "cached_predictions": len(prediction_rows), "valid_cached": len(valid_ids),
            "explicit_failures": len(failed_ids), "pending": len(pending_ids), "invalid_cached": len(record_errors),
        },
        "failure_type_counts": dict(sorted(Counter(str(row["error_type"]) for row in failure_by_id.values()).items())),
        "overlap_prediction_and_failure_ids": overlap,
        "unknown_ids": unknown,
        "invalid_cached_record_errors": record_errors,
        "pending_record_ids": pending_ids,
        "complete": not pending_ids and not overlap and not unknown and not record_errors,
        "production_l3_started": False,
        "api_state": "unavailable_no_api",
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if receipt["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
