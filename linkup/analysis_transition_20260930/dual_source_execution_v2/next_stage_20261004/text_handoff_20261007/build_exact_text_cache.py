#!/usr/bin/env python3
"""Verify regional exact-text outputs and build a private 10,000-row cache."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

KEYS = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")
EXPECTED = {"kunshan": 5495, "wuzhen": 4505}


def allow_long_csv_fields() -> None:
    limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit //= 10


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def identity(row: dict) -> tuple[str, str, int, int]:
    return (str(row["JOB_HASH"]), str(row["SOURCE_FILE"]), int(row["SOURCE_ROW"]), int(row["RECORD_SOURCE_ROW"]))


def selection_keys(path: Path) -> set[tuple[str, str, int, int]]:
    value = json.loads(path.read_text())
    rows = value["selected"] if isinstance(value, dict) else value
    keys = set()
    for row in rows:
        parts = json.loads(row["private_key"])
        if len(parts) != 4:
            raise RuntimeError("selection contains a noncanonical private key")
        keys.add((str(parts[0]), str(parts[1]), int(parts[2]), int(parts[3])))
    if len(keys) != len(rows):
        raise RuntimeError("selection contains duplicate locator keys")
    return keys


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--handoff-dir", type=Path, required=True)
    parser.add_argument("--materialized-dir", type=Path, required=True)
    parser.add_argument("--public-receipt", type=Path, required=True)
    args = parser.parse_args()
    args.materialized_dir.mkdir(parents=True, exist_ok=True)
    allow_long_csv_fields()

    text_by_key = {}
    region_by_key = {}
    regional_inputs = {}
    for region, expected in EXPECTED.items():
        selection = args.handoff_dir / "private" / "run-123660254" / f"fixed10000_{region}.selection.json"
        source_map = args.handoff_dir / "private" / "run-123660254" / f"fixed10000_{region}.source_map.jsonl"
        output = args.materialized_dir / f"fixed10000_{region}.text.csv"
        receipt_path = args.materialized_dir / f"fixed10000_{region}.materialize_receipt.json"
        receipt = json.loads(receipt_path.read_text())
        selected = selection_keys(selection)
        if len(selected) != expected or receipt.get("rows") != expected:
            raise RuntimeError(f"{region} count mismatch")
        checks = {
            "selection_sha256": sha256_file(selection),
            "source_map_sha256": sha256_file(source_map),
            "output_sha256": sha256_file(output),
        }
        for field, actual in checks.items():
            if receipt.get(field) != actual:
                raise RuntimeError(f"{region} {field} mismatch")
        actual_keys = set()
        with output.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                key = identity(row)
                if json.loads(row["private_key"]) != [row[k] if k in ("JOB_HASH", "SOURCE_FILE") else int(row[k]) for k in KEYS]:
                    raise RuntimeError(f"{region} private_key does not match locator columns")
                if key in actual_keys or key in text_by_key:
                    raise RuntimeError("materialized output repeats a canonical key")
                actual_keys.add(key)
                text_by_key[key] = row["original_text"]
                region_by_key[key] = region
        if actual_keys != selected:
            raise RuntimeError(f"{region} materialized locator set differs from selection")
        regional_inputs[region] = {"rows": expected, **checks, "receipt_sha256": sha256_file(receipt_path)}

    sample_table = pq.read_table(args.sample)
    sample_rows = sample_table.to_pylist()
    if sample_table.num_rows != 10000:
        raise RuntimeError("frozen sample is not 10,000 rows")
    sample_keys = [identity(row) for row in sample_rows]
    if len(set(sample_keys)) != 10000 or set(sample_keys) != set(text_by_key):
        raise RuntimeError("merged materialized keys do not equal the frozen sample keys")

    regions = []
    text_hashes = []
    exact_texts = []
    hash_counts = Counter()
    unique_text = {}
    for row, key in zip(sample_rows, sample_keys):
        text = text_by_key[key]
        text_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        previous = unique_text.setdefault(text_sha, text)
        if previous != text:
            raise RuntimeError("SHA-256 collision between unequal exact texts")
        hash_counts[text_sha] += 1
        regions.append(region_by_key[key])
        text_hashes.append(text_sha)
        exact_texts.append(text)

    merged_path = args.materialized_dir / "MERGED_FIXED10000_EXACT_TEXT_PRIVATE.parquet"
    merged_table = sample_table
    for name, values in (
        ("materialized_region", regions), ("exact_text_sha256", text_hashes), ("original_text", exact_texts)
    ):
        if name in merged_table.schema.names:
            raise RuntimeError(f"sample already contains reserved output field {name}")
        merged_table = merged_table.append_column(name, pa.array(values, type=pa.string()))
    pq.write_table(merged_table, merged_path, compression="zstd")
    sample_fields = sample_table.schema.names
    probability_fields = [
        name for name in sample_fields
        if "probability" in name.lower() or "weight" in name.lower() or name.lower() in {"pi", "w_h"}
    ]
    manifest_names = list(KEYS) + ["arm"] + probability_fields
    manifest_table = sample_table.select(manifest_names)
    manifest_table = manifest_table.append_column("materialized_region", pa.array(regions, type=pa.string()))
    manifest_table = manifest_table.append_column("exact_text_sha256", pa.array(text_hashes, type=pa.string()))
    manifest_path = args.materialized_dir / "EXACT_TEXT_SHA_CACHE_MANIFEST_PRIVATE.parquet"
    pq.write_table(manifest_table, manifest_path, compression="zstd")
    cache_rows = [
        {"exact_text_sha256": text_sha, "duplicate_member_count": hash_counts[text_sha], "original_text": text}
        for text_sha, text in sorted(unique_text.items())
    ]
    cache_path = args.materialized_dir / "UNIQUE_EXACT_TEXT_INFERENCE_CACHE_PRIVATE.parquet"
    pq.write_table(pa.Table.from_pylist(cache_rows), cache_path, compression="zstd")

    duplicate_groups = [count for count in hash_counts.values() if count > 1]
    receipt = {
        "status": "complete",
        "sample_rows": 10000,
        "region_rows": EXPECTED,
        "unique_exact_texts_for_inference": len(unique_text),
        "duplicate_sample_rows_beyond_unique": 10000 - len(unique_text),
        "exact_text_duplicate_groups": len(duplicate_groups),
        "maximum_exact_text_group_size": max(hash_counts.values()),
        "empty_exact_text_rows": sum(not text for text in text_by_key.values()),
        "deduplication": "exact UTF-8 text SHA-256 only; no trimming, normalization, or fuzzy matching; all 10,000 sample rows and probability/weight fields retained",
        "probability_weight_fields_retained": probability_fields,
        "sample_arrow_schema_preserved": merged_table.schema.names[:-3] == sample_table.schema.names and all(
            merged_table.schema.field(i).type == sample_table.schema.field(i).type for i in range(len(sample_table.schema))
        ),
        "sample_sha256": sha256_file(args.sample),
        "regional_inputs": regional_inputs,
        "private_output_sha256": {
            merged_path.name: sha256_file(merged_path),
            manifest_path.name: sha256_file(manifest_path),
            cache_path.name: sha256_file(cache_path),
        },
        "private_outputs_excluded": True,
        "privacy": "receipt contains counts and file hashes only; exact text, locators, keys, probabilities, and weights remain private and excluded from Git",
    }
    args.public_receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
