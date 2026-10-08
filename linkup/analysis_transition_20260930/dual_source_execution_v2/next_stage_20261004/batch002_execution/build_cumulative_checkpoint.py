#!/usr/bin/env python3
"""Build the cumulative private completion checkpoint for finalized batches.

This is a mechanical join by the immutable exact-text SHA-256 key. It does not
inspect or revise labels, estimate a population quantity, or alter source files.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent
STAGE_ROOT = ROOT.parent / "production_standard_20261008"

BATCH_INPUTS = (
    ("batch001", STAGE_ROOT / "private/batch001/FINAL_CANDIDATES_PRIVATE.jsonl"),
    ("batch002", ROOT / "private/batch002/FINAL_CANDIDATES_PRIVATE.jsonl"),
)
QUEUE_PATH = STAGE_ROOT / "private/full_queue/UNIQUE_EXACT_TEXT_QUEUE_PRIVATE.jsonl"
REPRESENTED_PATH = STAGE_ROOT / "private/full_queue/REPRESENTED_FIXED10000_KEYS_PRIVATE.jsonl"

PRIVATE_OUTPUT_DIR = ROOT / "private/cumulative_checkpoint"
COMPLETED_PATH = PRIVATE_OUTPUT_DIR / "COMPLETED_SOURCE_HASH_LEDGER_PRIVATE.jsonl"
REMAINING_PATH = PRIVATE_OUTPUT_DIR / "REMAINING_UNIQUE_EXACT_TEXT_QUEUE_PRIVATE.jsonl"
MAPPING_PATH = PRIVATE_OUTPUT_DIR / "REPRESENTED_ORIGINAL_AD_TO_FINAL_CANDIDATE_PRIVATE.jsonl"
RECEIPT_PATH = ROOT / "CUMULATIVE_CHECKPOINT_RECEIPT.json"

HASH_KEYS = {"source_text_sha256", "exact_text_sha256"}
POINTER_KEYS = {
    "final_candidate_batch",
    "final_candidate_row_1based",
    "final_candidate_row_sha256",
}


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_jsonl(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    raw_lines = path.read_text(encoding="utf-8").splitlines()
    if any(not line.strip() for line in raw_lines):
        raise ValueError(f"blank JSONL line in {path}")
    return raw_lines, [json.loads(line) for line in raw_lines]


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        os.replace(temporary_path, path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def encode_jsonl(rows: Iterable[dict[str, Any]]) -> str:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    )


def assert_hex_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{label} is not a SHA-256 hex string")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{label} is not a SHA-256 hex string") from exc
    return value


def main() -> int:
    immutable_inputs = [path for _, path in BATCH_INPUTS] + [QUEUE_PATH, REPRESENTED_PATH]
    before_hashes = {str(path.relative_to(ROOT.parent)): file_sha256(path) for path in immutable_inputs}

    candidate_by_hash: dict[str, dict[str, Any]] = {}
    finalized_by_batch: dict[str, int] = {}
    for batch_name, path in BATCH_INPUTS:
        raw_lines, rows = read_jsonl(path)
        finalized_by_batch[batch_name] = len(rows)
        for row_number, (raw_line, row) in enumerate(zip(raw_lines, rows), 1):
            source_hash = assert_hex_sha256(
                row.get("source_text_sha256"),
                f"{batch_name} row {row_number} source_text_sha256",
            )
            if source_hash in candidate_by_hash:
                previous = candidate_by_hash[source_hash]
                raise ValueError(
                    "duplicate finalized source hash across candidate rows: "
                    f"{previous['final_candidate_batch']} row "
                    f"{previous['final_candidate_row_1based']} and {batch_name} row {row_number}"
                )
            candidate_by_hash[source_hash] = {
                "final_candidate_batch": batch_name,
                "final_candidate_row_1based": row_number,
                "final_candidate_row_sha256": text_sha256(raw_line),
            }

    queue_raw_lines, queue_rows = read_jsonl(QUEUE_PATH)
    queue_by_hash: dict[str, dict[str, Any]] = {}
    for expected_position, row in enumerate(queue_rows, 1):
        if row.get("queue_position_1based") != expected_position:
            raise ValueError("queue positions do not reproduce immutable file order")
        source_hash = assert_hex_sha256(
            row.get("exact_text_sha256"), f"queue row {expected_position} exact_text_sha256"
        )
        if source_hash in queue_by_hash:
            raise ValueError("duplicate exact-text SHA in immutable unique queue")
        if text_sha256(row.get("original_text", "")) != source_hash:
            raise ValueError(f"queue source text SHA mismatch at row {expected_position}")
        queue_by_hash[source_hash] = row

    missing_from_queue = sorted(set(candidate_by_hash).difference(queue_by_hash))
    if missing_from_queue:
        raise ValueError(f"finalized source hashes absent from immutable queue: {len(missing_from_queue)}")

    _, represented_rows = read_jsonl(REPRESENTED_PATH)
    represented_counts: Counter[str] = Counter()
    previous_fixed_position = 0
    for row in represented_rows:
        fixed_position = row.get("fixed_sample_position_1based")
        if fixed_position != previous_fixed_position + 1:
            raise ValueError("represented fixed-sample positions do not reproduce immutable file order")
        previous_fixed_position = fixed_position
        source_hash = assert_hex_sha256(
            row.get("exact_text_sha256"), f"represented row {fixed_position} exact_text_sha256"
        )
        if source_hash not in queue_by_hash:
            raise ValueError(f"represented row {fixed_position} does not join to immutable queue")
        if POINTER_KEYS.intersection(row):
            raise ValueError(f"represented input row {fixed_position} already contains checkpoint pointers")
        represented_counts[source_hash] += 1

    for source_hash, queue_row in queue_by_hash.items():
        if represented_counts[source_hash] != queue_row.get("duplicate_member_count"):
            raise ValueError("queue duplicate_member_count disagrees with represented original ads")

    completed_rows: list[dict[str, Any]] = []
    remaining_raw_lines: list[str] = []
    for raw_line, queue_row in zip(queue_raw_lines, queue_rows):
        source_hash = queue_row["exact_text_sha256"]
        pointer = candidate_by_hash.get(source_hash)
        if pointer is None:
            remaining_raw_lines.append(raw_line)
            continue
        completed_rows.append(
            {
                "queue_position_1based": queue_row["queue_position_1based"],
                "source_text_sha256": source_hash,
                "represented_original_ad_count": represented_counts[source_hash],
                **pointer,
            }
        )

    mapped_rows: list[dict[str, Any]] = []
    for represented_row in represented_rows:
        pointer = candidate_by_hash.get(represented_row["exact_text_sha256"])
        if pointer is not None:
            mapped_rows.append({**represented_row, **pointer})

    if len(completed_rows) != len(candidate_by_hash):
        raise ValueError("completed ledger does not contain every finalized candidate hash exactly once")
    if len(completed_rows) + len(remaining_raw_lines) != len(queue_rows):
        raise ValueError("completed and remaining queue partitions do not cover immutable queue")
    if len(mapped_rows) != sum(represented_counts[row["source_text_sha256"]] for row in completed_rows):
        raise ValueError("represented original-ad mapping count mismatch")

    for output_row in mapped_rows:
        source_hash = output_row["exact_text_sha256"]
        original_row = represented_rows[output_row["fixed_sample_position_1based"] - 1]
        if any(output_row[key] != value for key, value in original_row.items()):
            raise ValueError("represented original-ad metadata changed during mapping")
        if any(key not in original_row and key not in POINTER_KEYS for key in output_row):
            raise ValueError("unexpected field added to represented original-ad mapping")
        if source_hash not in candidate_by_hash:
            raise ValueError("mapped represented original ad lacks a finalized candidate")

    completed_content = encode_jsonl(completed_rows)
    remaining_content = "".join(line + "\n" for line in remaining_raw_lines)
    mapping_content = encode_jsonl(mapped_rows)
    write_atomic(COMPLETED_PATH, completed_content)
    write_atomic(REMAINING_PATH, remaining_content)
    write_atomic(MAPPING_PATH, mapping_content)

    after_hashes = {str(path.relative_to(ROOT.parent)): file_sha256(path) for path in immutable_inputs}
    if after_hashes != before_hashes:
        raise RuntimeError("an immutable input changed during checkpoint construction")

    completed_represented = len(mapped_rows)
    receipt = {
        "status": "complete",
        "scope": "mechanical cumulative checkpoint by immutable exact-text SHA-256; no label inference, population estimate, or source mutation",
        "finalized_candidate_rows_by_batch": finalized_by_batch,
        "counts": {
            "immutable_unique_exact_text_queue": len(queue_rows),
            "completed_unique_exact_texts": len(completed_rows),
            "remaining_unique_exact_texts": len(remaining_raw_lines),
            "represented_original_ads_total": len(represented_rows),
            "represented_original_ads_completed": completed_represented,
            "represented_original_ads_remaining": len(represented_rows) - completed_represented,
            "completed_duplicate_members_beyond_unique": completed_represented - len(completed_rows),
        },
        "ordering": {
            "completed_ledger": "immutable queue_position_1based order",
            "remaining_queue": "immutable queue_position_1based order with completed hashes removed",
            "represented_mapping": "immutable fixed_sample_position_1based order with incomplete hashes removed",
        },
        "validation": {
            "finalized_source_hashes_unique": True,
            "every_finalized_hash_matches_queue": True,
            "every_queue_original_text_matches_exact_text_sha256": True,
            "queue_duplicate_counts_match_represented_rows": True,
            "represented_member_metadata_preserved": True,
            "immutable_input_file_hashes_unchanged_during_run": True,
        },
        "input_file_sha256": before_hashes,
        "output_file_sha256": {
            str(COMPLETED_PATH.relative_to(ROOT)): file_sha256(COMPLETED_PATH),
            str(REMAINING_PATH.relative_to(ROOT)): file_sha256(REMAINING_PATH),
            str(MAPPING_PATH.relative_to(ROOT)): file_sha256(MAPPING_PATH),
        },
        "privacy": "Public receipt contains derived counts, methods, paths, and whole-file hashes only. Source text, source hashes, record IDs, canonical keys, arms, cells, and weights remain in private artifacts.",
        "execution": {"llm_called": False, "remote_cluster_called": False, "git_action": False},
    }
    receipt_content = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    write_atomic(RECEIPT_PATH, receipt_content)

    print(
        json.dumps(
            {
                "completed_unique_exact_texts": len(completed_rows),
                "represented_original_ads_completed": completed_represented,
                "remaining_unique_exact_texts": len(remaining_raw_lines),
                "status": "complete",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
