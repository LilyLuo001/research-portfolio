#!/usr/bin/env python3
"""Stage production processing batch 001 and the full exact-text queue."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pyarrow.csv as pacsv
import pyarrow.parquet as pq


BATCH_SEED = "production-standard-20261008-batch001-v1"
QUEUE_SEED = "production-standard-20261008-full7635-v1"
ARMS = ("A", "B", "C")
KEY_FIELDS = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")
CELL_FIELDS = ("OCCUPATION_MAJOR", "CENSUS_REGION", "created_year")
WEIGHT_FIELDS = (
    "frame_count_a", "frame_count_b", "selected_cell_arm_n", "inclusion_probability",
    "design_weight", "W_h", "stable_rank_in_cell_arm", "sample_rank_in_cell_arm",
    "nested_frame_cell_arm_N", "next_selected_cell_arm_n", "original_inclusion_probability",
    "conditional_inclusion_probability", "total_inclusion_probability", "nested_design_weight",
    "pooled_cell_standardization_weight",
)


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def text_digest(text: str) -> str:
    return digest_bytes(text.encode("utf-8"))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def review_files(roots: list[Path], explicit: list[Path]) -> list[Path]:
    files = {path.resolve() for path in explicit}
    for root in roots:
        if root.is_file():
            files.add(root.resolve())
        elif root.is_dir():
            files.update(path.resolve() for path in root.rglob("*.jsonl"))
            files.update(path.resolve() for path in root.rglob("*.text.csv"))
    return sorted(files)


def reviewed_texts(path: Path) -> list[str]:
    if path.suffix == ".jsonl":
        values = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and isinstance(row.get("original_text"), str):
                values.append(row["original_text"])
        return values
    if path.name.endswith(".text.csv"):
        try:
            table = pacsv.read_csv(
                path,
                read_options=pacsv.ReadOptions(block_size=1 << 24),
                parse_options=pacsv.ParseOptions(newlines_in_values=True),
            )
        except Exception:
            return []
        if "original_text" not in table.schema.names:
            return []
        return [row["original_text"] for row in table.to_pylist() if isinstance(row.get("original_text"), str)]
    return []


def canonical_key(row: dict[str, Any]) -> dict[str, Any]:
    return {field: row[field] for field in KEY_FIELDS}


def row_metadata(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "canonical_key": canonical_key(row),
        "arm": row["arm"],
        "cell": {field: row[field] for field in CELL_FIELDS},
        "weights": {field: row[field] for field in WEIGHT_FIELDS},
    }


def key_tuple(row: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(row[field] for field in KEY_FIELDS)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--merged-fixed10000", type=Path, required=True)
    parser.add_argument("--unique-cache", type=Path, required=True)
    parser.add_argument("--review-root", type=Path, action="append", default=[])
    parser.add_argument("--review-file", type=Path, action="append", default=[])
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    batch_dir = args.output_root / "private" / "batch001"
    queue_dir = args.output_root / "private" / "full_queue"
    receipt_path = args.output_root / "BATCH001_AND_QUEUE_RECEIPT.json"
    if batch_dir.exists() or queue_dir.exists() or receipt_path.exists():
        raise RuntimeError("refusing to overwrite existing batch, queue, or receipt")

    merged_table = pq.read_table(args.merged_fixed10000)
    cache_table = pq.read_table(args.unique_cache)
    if merged_table.num_rows != 10000 or cache_table.num_rows != 7635:
        raise RuntimeError("verified fixed-corpus row counts changed")
    required = set(KEY_FIELDS + CELL_FIELDS + WEIGHT_FIELDS + ("arm", "exact_text_sha256", "original_text"))
    missing = sorted(required - set(merged_table.schema.names))
    if missing:
        raise RuntimeError(f"merged corpus lacks required fields: {missing}")
    rows = merged_table.to_pylist()
    cache = cache_table.to_pylist()
    if any(row["arm"] not in ARMS for row in rows):
        raise RuntimeError("unexpected arm in fixed corpus")
    if any(not isinstance(row["original_text"], str) or not row["original_text"] for row in rows):
        raise RuntimeError("empty or non-string source text in fixed corpus")
    if any(text_digest(row["original_text"]) != row["exact_text_sha256"] for row in rows):
        raise RuntimeError("merged exact-text hash mismatch")
    if len({key_tuple(row) for row in rows}) != 10000:
        raise RuntimeError("canonical fixed-sample keys are not unique")

    by_sha: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_sha[row["exact_text_sha256"]].append(row)
    if len(by_sha) != 7635:
        raise RuntimeError("merged unique exact-text count changed")
    if any(len({row["arm"] for row in members}) != 1 for members in by_sha.values()):
        raise RuntimeError("an exact text spans multiple arms; balanced processing rule is ambiguous")

    cache_by_sha = {row["exact_text_sha256"]: row for row in cache}
    if len(cache_by_sha) != 7635 or set(cache_by_sha) != set(by_sha):
        raise RuntimeError("unique cache does not match merged exact-text keys")
    for sha, members in by_sha.items():
        item = cache_by_sha[sha]
        if item["original_text"] != members[0]["original_text"] or item["duplicate_member_count"] != len(members):
            raise RuntimeError("unique cache text or duplicate count mismatch")

    discovered = review_files(args.review_root, args.review_file)
    excluded_hashes: set[str] = set()
    review_rows = 0
    review_files_with_text = 0
    review_artifact_hashes = []
    for path in discovered:
        texts = reviewed_texts(path)
        if not texts:
            continue
        review_files_with_text += 1
        review_artifact_hashes.append(digest_file(path))
        review_rows += len(texts)
        excluded_hashes.update(text_digest(text) for text in texts)

    representatives: dict[tuple[str, str], dict[str, Any]] = {}
    for sha, members in by_sha.items():
        arm = members[0]["arm"]
        representatives[(arm, sha)] = min(members, key=key_tuple)
    selected: list[dict[str, Any]] = []
    selected_shas: set[str] = set()
    eligible_counts = {}
    for arm in ARMS:
        candidates = [
            (digest_bytes(f"{BATCH_SEED}|{arm}|{sha}".encode()), sha, row)
            for (candidate_arm, sha), row in representatives.items()
            if candidate_arm == arm and sha not in excluded_hashes
        ]
        eligible_counts[arm] = len(candidates)
        arm_selected = 0
        for rank, sha, row in sorted(candidates):
            if sha in selected_shas:
                continue
            selected.append({"selection_rank_sha256": rank, "exact_text_sha256": sha, "representative": row})
            selected_shas.add(sha)
            arm_selected += 1
            if arm_selected == 8:
                break
        if arm_selected != 8:
            raise RuntimeError(f"insufficient unreviewed unique texts in arm {arm}")
    selected.sort(key=lambda item: digest_bytes(f"{BATCH_SEED}|processing|{item['exact_text_sha256']}".encode()))
    if len(selected) != 24 or len(selected_shas) != 24:
        raise RuntimeError("batch count or exact-text uniqueness failed")

    label_rows, manifest_rows = [], []
    for position, item in enumerate(selected, 1):
        sha, representative = item["exact_text_sha256"], item["representative"]
        record_id = digest_bytes(f"{BATCH_SEED}|record|{sha}".encode())[:32]
        label_rows.append({"record_id": record_id, "original_text": representative["original_text"]})
        represented = [row_metadata(row) for row in sorted(by_sha[sha], key=key_tuple)]
        manifest_rows.append({
            "record_id": record_id,
            "processing_position_1based": position,
            "selection_arm": representative["arm"],
            "selection_rank_sha256": item["selection_rank_sha256"],
            "exact_text_sha256": sha,
            "original_text": representative["original_text"],
            "represented_fixed_sample_rows": len(represented),
            "representative": row_metadata(representative),
            "represented_rows": represented,
        })

    queue_ranked = sorted(
        cache,
        key=lambda row: digest_bytes(f"{QUEUE_SEED}|{row['exact_text_sha256']}".encode()),
    )
    queue_rows = []
    for position, item in enumerate(queue_ranked, 1):
        sha = item["exact_text_sha256"]
        queue_rows.append({
            "queue_position_1based": position,
            "queue_record_id": digest_bytes(f"{QUEUE_SEED}|record|{sha}".encode())[:32],
            "exact_text_sha256": sha,
            "duplicate_member_count": item["duplicate_member_count"],
            "original_text": item["original_text"],
        })
    represented_rows = []
    for position, row in enumerate(rows, 1):
        represented_rows.append({
            "fixed_sample_position_1based": position,
            "exact_text_sha256": row["exact_text_sha256"],
            **row_metadata(row),
        })

    label_path = batch_dir / "LABEL_PACK_PRIVATE.jsonl"
    manifest_path = batch_dir / "UNBLIND_MANIFEST_PRIVATE.jsonl"
    write_jsonl(label_path, label_rows)
    write_jsonl(manifest_path, manifest_rows)
    block_paths = []
    for block_index in range(6):
        path = batch_dir / "blocks" / f"block_{block_index + 1:02d}_of_06_PRIVATE.jsonl"
        write_jsonl(path, label_rows[block_index * 4:(block_index + 1) * 4])
        block_paths.append(path)
    queue_path = queue_dir / "UNIQUE_EXACT_TEXT_QUEUE_PRIVATE.jsonl"
    represented_path = queue_dir / "REPRESENTED_FIXED10000_KEYS_PRIVATE.jsonl"
    write_jsonl(queue_path, queue_rows)
    write_jsonl(represented_path, represented_rows)
    for directory in (args.output_root / "private", batch_dir, batch_dir / "blocks", queue_dir):
        os.chmod(directory, 0o700)
    for path in (label_path, manifest_path, queue_path, represented_path, *block_paths):
        os.chmod(path, 0o400)

    if sum(1 for row in queue_rows for _ in range(row["duplicate_member_count"])) != 10000:
        raise RuntimeError("queue duplicate-member total does not represent 10,000 rows")
    if Counter(item["selection_arm"] for item in manifest_rows) != Counter({"A": 8, "B": 8, "C": 8}):
        raise RuntimeError("batch arm balance failed")
    if any(label_rows[index]["record_id"] != manifest_rows[index]["record_id"] for index in range(24)):
        raise RuntimeError("label pack and private manifest order mismatch")
    if any(
        json.loads(line)["record_id"] != label_rows[index]["record_id"]
        for index, line in enumerate("".join(path.read_text(encoding="utf-8") for path in block_paths).splitlines())
    ):
        raise RuntimeError("six-block concatenation does not reproduce label-pack order")

    receipt = {
        "status": "staged",
        "created_at": "2026-10-07T23:34:00+08:00",
        "stage_name": "production_standard_20261008",
        "scope": "processing order only; not a new inferential sample and no fixed-10000 probabilities, weights, cells, arms, or source rows were changed",
        "batch001": {
            "unique_exact_texts": 24,
            "arm_counts": {"A": 8, "B": 8, "C": 8},
            "blocks": 6,
            "records_per_block": 4,
            "exact_text_unique": True,
            "excluded_all_discoverable_reviewed_exact_texts": True,
            "selection_seed": BATCH_SEED,
            "eligible_unique_texts_after_exclusion_by_arm": eligible_counts,
        },
        "full_queue": {
            "unique_exact_texts": len(queue_rows),
            "represented_fixed_sample_keys": len(represented_rows),
            "duplicate_members_beyond_unique": len(represented_rows) - len(queue_rows),
            "queue_key": "exact UTF-8 text SHA-256",
            "queue_seed": QUEUE_SEED,
            "resume_contract": "Process stable queue_position_1based order and checkpoint completed exact_text_sha256 values; restart skips completed hashes without relabeling duplicate sample rows.",
            "all_keys_join_to_queue": set(row["exact_text_sha256"] for row in represented_rows) == set(row["exact_text_sha256"] for row in queue_rows),
        },
        "review_exclusion": {
            "artifacts_discovered": len(discovered),
            "artifacts_with_original_text": review_files_with_text,
            "review_rows_seen": review_rows,
            "unique_exact_text_hashes": len(excluded_hashes),
            "artifact_sha256": sorted(review_artifact_hashes),
        },
        "input_sha256": {
            "merged_fixed10000": digest_file(args.merged_fixed10000),
            "unique_exact_text_cache": digest_file(args.unique_cache),
        },
        "output_sha256": {
            "batch_label_pack_private": digest_file(label_path),
            "batch_unblind_manifest_private": digest_file(manifest_path),
            "blocks_private": [digest_file(path) for path in block_paths],
            "full_unique_queue_private": digest_file(queue_path),
            "represented_fixed10000_keys_private": digest_file(represented_path),
        },
        "privacy": "Public receipt contains aggregate counts, methods, and whole-file hashes only. Source text, record IDs, canonical keys, cells, arms, and weights remain in private artifacts.",
        "execution": {"llm_called": False, "remote_cluster_called": False, "git_action": False},
    }
    args.output_root.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "staged", "batch": 24, "queue": 7635, "represented": 10000}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
