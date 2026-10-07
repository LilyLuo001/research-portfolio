#!/usr/bin/env python3
"""Build a fixed 4-development + 16-heldout diagnostic source pack."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq

SEED = "20261007"
KEYS = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def text_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_key(row: dict) -> tuple[str, str, int, int]:
    return (str(row["JOB_HASH"]), str(row["SOURCE_FILE"]), int(row["SOURCE_ROW"]), int(row["RECORD_SOURCE_ROW"]))


def jsonl_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def discover_reviewed_files(roots: list[Path], development4: Path) -> list[Path]:
    files = {development4.resolve()}
    for root in roots:
        if root.is_file():
            files.add(root.resolve())
            continue
        files.update(path.resolve() for path in root.rglob("*.jsonl"))
        files.update(path.resolve() for path in root.rglob("*.text.csv"))
    return sorted(files)


def read_text_rows(path: Path) -> list[dict]:
    if path.suffix == ".jsonl":
        rows = jsonl_rows(path)
        return [row for row in rows if isinstance(row, dict) and isinstance(row.get("original_text"), str)]
    if path.name.endswith(".text.csv"):
        table = pacsv.read_csv(
            path,
            read_options=pacsv.ReadOptions(block_size=1 << 24),
            parse_options=pacsv.ParseOptions(newlines_in_values=True),
        )
        if "original_text" not in table.schema.names:
            return []
        return [row for row in table.to_pylist() if isinstance(row.get("original_text"), str)]
    return []


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--merged-parquet", type=Path, required=True)
    parser.add_argument("--development4-source", type=Path, required=True)
    parser.add_argument("--development4-key-source", type=Path, required=True)
    parser.add_argument("--development4-key-parquet", type=Path, required=True)
    parser.add_argument("--review-search-root", type=Path, action="append", default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--public-receipt", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise RuntimeError("refusing to overwrite an existing source-pack directory")

    merged = pq.read_table(args.merged_parquet)
    if merged.num_rows != 10000:
        raise RuntimeError("merged frozen sample must have exactly 10,000 rows")
    rows = merged.to_pylist()
    by_job = {str(row["JOB_HASH"]): row for row in rows}
    if len(by_job) != 10000:
        raise RuntimeError("merged frozen sample JOB_HASH values are not unique")

    development_rows = jsonl_rows(args.development4_source)
    if len(development_rows) != 4 or any(set(row) != {"record_id", "original_text"} for row in development_rows):
        raise RuntimeError("development4 source must be the exact four-row record_id/original_text pack")
    development_key_rows = {str(row["record_id"]): row for row in jsonl_rows(args.development4_key_source)}
    development_metadata = {canonical_key(row): row for row in pq.read_table(args.development4_key_parquet).to_pylist()}
    development_mapped = []
    for source_row in development_rows:
        key_row = development_key_rows.get(str(source_row["record_id"]))
        if key_row is None or source_row["original_text"] != key_row.get("original_text"):
            raise RuntimeError("development4 source does not map exactly to its frozen prior key source")
        metadata = development_metadata.get(canonical_key(key_row))
        if metadata is None:
            raise RuntimeError("development4 canonical key is absent from its frozen prior key parquet")
        development_mapped.append((source_row, key_row, metadata))

    reviewed_files = discover_reviewed_files(args.review_search_root, args.development4_source)
    excluded_keys = set()
    excluded_hashes = set()
    reviewed_rows_seen = 0
    reviewed_files_with_text = 0
    reviewed_artifact_hashes = []
    for path in reviewed_files:
        text_rows = read_text_rows(path)
        if not text_rows:
            continue
        reviewed_files_with_text += 1
        reviewed_artifact_hashes.append(sha256_file(path))
        for row in text_rows:
            reviewed_rows_seen += 1
            excluded_hashes.add(text_sha(row["original_text"]))
            if all(field in row and row[field] not in (None, "") for field in KEYS):
                excluded_keys.add(canonical_key(row))
            record_id = row.get("record_id")
            if record_id is not None and str(record_id) in by_job:
                excluded_keys.add(canonical_key(by_job[str(record_id)]))

    development_hashes = {text_sha(row["original_text"]) for row, _, _ in development_mapped}
    if len(development_hashes) != 4:
        raise RuntimeError("development4 contains duplicate exact text")
    selected = []
    selected_hashes = set(development_hashes)
    candidate_counts = {}
    excluded_current_key_counts = {}
    excluded_current_text_counts = {}
    for arm in ("A", "B"):
        candidates = []
        excluded_key = 0
        excluded_text = 0
        for row in rows:
            if row["arm"] != arm:
                continue
            key = canonical_key(row)
            digest = text_sha(row["original_text"])
            if key in excluded_keys:
                excluded_key += 1
                continue
            if digest in excluded_hashes:
                excluded_text += 1
                continue
            rank = hashlib.sha256((SEED + "|heldout16|" + arm + "|" + "|".join(map(str, key))).encode("utf-8")).hexdigest()
            candidates.append((rank, key, digest, row))
        candidate_counts[arm] = len(candidates)
        excluded_current_key_counts[arm] = excluded_key
        excluded_current_text_counts[arm] = excluded_text
        arm_selected = 0
        for rank, key, digest, row in sorted(candidates):
            if digest in selected_hashes:
                continue
            review_id = hashlib.sha256(("source20|" + SEED + "|" + "|".join(map(str, key))).encode("utf-8")).hexdigest()[:32]
            selected.append({"review_id": review_id, "rank": rank, "key": key, "digest": digest, "row": row})
            selected_hashes.add(digest)
            arm_selected += 1
            if arm_selected == 8:
                break
        if arm_selected != 8:
            raise RuntimeError(f"insufficient unique unreviewed candidates for arm {arm}")

    if len(selected) != 16 or len(selected_hashes) != 20:
        raise RuntimeError("source20 exact-text uniqueness invariant failed")

    development_dir = args.output_dir / "development4"
    heldout_dir = args.output_dir / "heldout16"
    full_dir = args.output_dir / "source20"
    for directory in (args.output_dir, development_dir, heldout_dir, full_dir):
        directory.mkdir(parents=True, exist_ok=True)
        os.chmod(directory, 0o700)
    development_output = development_dir / "SOURCE_PRIVATE.jsonl"
    shutil.copyfile(args.development4_source, development_output)
    if sha256_file(development_output) != sha256_file(args.development4_source):
        raise RuntimeError("development4 byte-for-byte copy failed")

    heldout_output = heldout_dir / "SOURCE_PRIVATE.jsonl"
    with heldout_output.open("w", encoding="utf-8") as handle:
        for item in selected:
            handle.write(json.dumps({"record_id": item["review_id"], "original_text": item["row"]["original_text"]}, ensure_ascii=False, separators=(",", ":")) + "\n")
    full_output = full_dir / "SOURCE_PRIVATE.jsonl"
    development_bytes = development_output.read_bytes()
    if not development_bytes.endswith(b"\n"):
        raise RuntimeError("development4 source must end with a newline for exact concatenation")
    with full_output.open("wb") as handle:
        handle.write(development_bytes)
        handle.write(heldout_output.read_bytes())

    manifest_path = args.output_dir / "UNBLIND_MANIFEST_PRIVATE.jsonl"
    with manifest_path.open("w", encoding="utf-8") as handle:
        for source_row, key_row, metadata in development_mapped:
            handle.write(json.dumps({
                "review_id": source_row["record_id"], "split": "development", "arm": metadata["arm"],
                "canonical_key": list(canonical_key(key_row)), "source_text_sha256": text_sha(source_row["original_text"]),
            }, sort_keys=True, separators=(",", ":")) + "\n")
        for item in selected:
            handle.write(json.dumps({
                "review_id": item["review_id"], "split": "heldout", "arm": item["row"]["arm"],
                "canonical_key": list(item["key"]), "source_text_sha256": item["digest"], "selection_rank_sha256": item["rank"],
            }, sort_keys=True, separators=(",", ":")) + "\n")
    for path in (development_output, heldout_output, full_output, manifest_path):
        os.chmod(path, 0o400)

    source20_rows = jsonl_rows(full_output)
    if len(source20_rows) != 20 or any(set(row) != {"record_id", "original_text"} for row in source20_rows):
        raise RuntimeError("reader-facing source20 schema/count invariant failed")
    if len({row["record_id"] for row in source20_rows}) != 20:
        raise RuntimeError("reader-facing review IDs are not unique")
    if len({text_sha(row["original_text"]) for row in source20_rows}) != 20:
        raise RuntimeError("reader-facing source20 texts are not exact-text unique")

    receipt = {
        "status": "complete",
        "scope": "diagnostic source pack only; not a redraw of the formal sample, not a main estimator, and not population-precision evidence",
        "seed": int(SEED),
        "counts": {"development": 4, "heldout_A": 8, "heldout_B": 8, "source20": 20},
        "reader_schema": ["record_id", "original_text"],
        "reader_blinding": "opaque review ID plus exact untruncated source text only; no arm, source filename, canonical locator, or reference label",
        "development4": "byte-for-byte copy of the prior pilot4 SOURCE_PRIVATE.jsonl; reference labels are separate and absent from source files",
        "development4_current_fixed10000_canonical_key_overlap": sum(canonical_key(key_row) in {canonical_key(row) for row in rows} for _, key_row, _ in development_mapped),
        "selection_algorithm": "within each A/B arm, exclude discoverable prior canonical keys and exact UTF-8 text SHA-256 values, rank remaining canonical four-field keys by SHA-256(seed|heldout16|arm|key), take first eight while enforcing exact-text uniqueness across development4 and heldout16",
        "exclusion_scope": {
            "review_roots_supplied": len(args.review_search_root),
            "artifacts_discovered": len(reviewed_files),
            "artifacts_with_original_text": reviewed_files_with_text,
            "reviewed_rows_seen_with_original_text": reviewed_rows_seen,
            "unique_exact_text_hashes": len(excluded_hashes),
            "unique_canonical_keys": len(excluded_keys),
            "current_sample_excluded_by_key": excluded_current_key_counts,
            "current_sample_additionally_excluded_by_exact_text": excluded_current_text_counts,
            "eligible_candidates_after_exclusions": candidate_counts,
            "reviewed_artifact_sha256": sorted(reviewed_artifact_hashes),
        },
        "invariants": {
            "heldout_arm_counts_exact": True,
            "source20_exact_text_unique": True,
            "development4_byte_identical": True,
            "fixed_sample_rows_or_weights_modified": False,
            "C_included": False,
        },
        "input_sha256": {
            "merged_fixed10000": sha256_file(args.merged_parquet),
            "prior_development4_source": sha256_file(args.development4_source),
            "prior_development4_key_source": sha256_file(args.development4_key_source),
            "prior_development4_key_parquet": sha256_file(args.development4_key_parquet),
        },
        "output_sha256": {
            "development4_source": sha256_file(development_output),
            "heldout16_source": sha256_file(heldout_output),
            "source20": sha256_file(full_output),
            "private_unblind_manifest": sha256_file(manifest_path),
        },
        "privacy": "public receipt contains counts, method, and whole-file hashes only; source text, review IDs, arms, keys, locators, and unblind mappings remain private",
    }
    args.public_receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "complete", "development": 4, "heldout_A": 8, "heldout_B": 8}, sort_keys=True))


if __name__ == "__main__":
    main()
