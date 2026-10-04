#!/usr/bin/env python3
"""Select the fixed unused development 20; never reads evaluation or labels."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq


SEED = "D26-single-revision-unused20-v1"
LOCATORS = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")


def sha256_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def rank(row: dict[str, Any]) -> str:
    key = "|".join(str(row[field]) for field in LOCATORS)
    return hashlib.sha256(f"{SEED}|{key}".encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixed80", type=Path, required=True)
    parser.add_argument("--fixed80-text", type=Path, required=True)
    parser.add_argument("--previous20", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--public-receipt", type=Path, required=True)
    args = parser.parse_args()

    meta_rows = pq.read_table(args.fixed80).to_pylist()
    text_rows = read_jsonl(args.fixed80_text)
    previous_rows = read_jsonl(args.previous20)
    if len(meta_rows) != 80 or len({str(row["JOB_HASH"]) for row in meta_rows}) != 80:
        raise ValueError("fixed80 metadata must contain exactly 80 unique JOB_HASH values")
    if len(text_rows) != 80 or len({str(row["record_id"]) for row in text_rows}) != 80:
        raise ValueError("fixed80 text pack must contain exactly 80 unique record_id values")
    if len(previous_rows) != 20 or len({str(row["record_id"]) for row in previous_rows}) != 20:
        raise ValueError("previous blind pack must contain exactly 20 unique record_id values")
    if any(set(row) != {"record_id", "original_text"} for row in previous_rows):
        raise ValueError("previous20 must be a two-column blind pack")

    text_by_id = {str(row["record_id"]): row["original_text"] for row in text_rows}
    previous_ids = {str(row["record_id"]) for row in previous_rows}
    if not previous_ids <= set(text_by_id):
        raise ValueError("previous20 includes records outside fixed80")
    previous_text_hashes = {text_sha(str(row["original_text"])) for row in previous_rows}

    candidates: list[dict[str, Any]] = []
    excluded_previous_text = {"A": 0, "B": 0}
    remaining_by_arm = {"A": 0, "B": 0}
    for metadata in meta_rows:
        record_id = str(metadata["JOB_HASH"])
        arm = str(metadata["arm"])
        if arm not in remaining_by_arm:
            raise ValueError(f"unexpected arm {arm}")
        if record_id in previous_ids:
            continue
        remaining_by_arm[arm] += 1
        if record_id not in text_by_id:
            raise ValueError("fixed80 metadata/text mismatch")
        digest = text_sha(text_by_id[record_id])
        if digest in previous_text_hashes:
            excluded_previous_text[arm] += 1
            continue
        row = dict(metadata)
        row["record_id"] = record_id
        row["original_text"] = text_by_id[record_id]
        row["text_digest"] = digest
        row["fixed_rank"] = rank(row)
        candidates.append(row)

    selected: list[dict[str, Any]] = []
    selected_counts = {"A": 0, "B": 0}
    selected_text_hashes: set[str] = set()
    within_batch_duplicate_skips = {"A": 0, "B": 0}
    for row in sorted(candidates, key=lambda item: item["fixed_rank"]):
        arm = str(row["arm"])
        if selected_counts[arm] >= 10:
            continue
        if row["text_digest"] in selected_text_hashes:
            within_batch_duplicate_skips[arm] += 1
            continue
        selected.append(row)
        selected_counts[arm] += 1
        selected_text_hashes.add(row["text_digest"])
        if selected_counts == {"A": 10, "B": 10}:
            break
    if selected_counts != {"A": 10, "B": 10}:
        raise ValueError(f"insufficient unique unused fixed80 candidates: {selected_counts}")

    args.output.parent.mkdir(parents=True, exist_ok=False)
    with args.output.open("w", encoding="utf-8") as handle:
        for row in selected:
            handle.write(json.dumps({"record_id": row["record_id"], "original_text": row["original_text"]}, ensure_ascii=False, separators=(",", ":")) + "\n")
    os.chmod(args.output.parent, 0o700)
    os.chmod(args.output, 0o400)
    receipt = {
        "version": "fixed80_unused20_selection_v1.1.0",
        "selection_seed": SEED,
        "selection_rule": "Within the fixed80 only, remove the already-read 20 and all exact full-text matches to them; rank canonical four-field keys by SHA-256(seed|key), scan globally, take 10 per original A/B arm, and skip exact full-text repeats within the new batch.",
        "inputs": {
            "fixed80_metadata_sha256": sha256_bytes(args.fixed80),
            "fixed80_text_pack_sha256": sha256_bytes(args.fixed80_text),
            "previous20_blind_pack_sha256": sha256_bytes(args.previous20),
        },
        "counts": {
            "fixed80": len(meta_rows),
            "previously_read": len(previous_rows),
            "remaining_unread_by_arm": remaining_by_arm,
            "excluded_same_text_as_previous20_by_arm": excluded_previous_text,
            "within_new_batch_duplicate_skips_by_arm": within_batch_duplicate_skips,
            "selected_by_arm": selected_counts,
            "selected_total": len(selected),
            "selected_unique_full_text": len(selected_text_hashes),
        },
        "private_output": {
            "columns": ["record_id", "original_text"],
            "sha256": sha256_bytes(args.output),
            "mode": "0400",
        },
        "privacy": "No record IDs, source text, arm assignments, locators, row-level ranks, or labels are present in this public receipt.",
        "evaluation_read": False,
        "labels_read": False
    }
    args.public_receipt.parent.mkdir(parents=True, exist_ok=True)
    args.public_receipt.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
