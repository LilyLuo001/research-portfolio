#!/usr/bin/env python3
"""Create a public aggregate workload diagnostic from a materialized text CSV."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def allow_long_csv_fields() -> None:
    limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit //= 10


def nearest_rank(values: list[int], probability: float) -> int:
    """Exact empirical nearest-rank quantile, rank ceil(p*n), one-indexed."""
    if not values:
        raise RuntimeError("cannot summarize an empty corpus")
    ordered = sorted(values)
    return ordered[max(0, math.ceil(probability * len(ordered)) - 1)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-csv", type=Path, required=True)
    parser.add_argument("--materialize-receipt", type=Path, required=True)
    parser.add_argument("--region-label", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    allow_long_csv_fields()

    materialize_receipt = json.loads(args.materialize_receipt.read_text())
    actual_input_sha = sha256_file(args.input_csv)
    if materialize_receipt.get("status") != "complete":
        raise RuntimeError("materialization receipt is not complete")
    if materialize_receipt.get("output_sha256") != actual_input_sha:
        raise RuntimeError("materialized CSV SHA-256 does not match its receipt")

    character_counts = []
    byte_counts = []
    text_hash_counts = Counter()
    with args.input_csv.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            text = row["original_text"]
            encoded = text.encode("utf-8")
            character_counts.append(len(text))
            byte_counts.append(len(encoded))
            text_hash_counts[hashlib.sha256(encoded).digest()] += 1
    rows = len(character_counts)
    if rows != materialize_receipt.get("rows"):
        raise RuntimeError("materialized CSV row count does not match its receipt")

    probabilities = (("p50", 0.50), ("p90", 0.90), ("p95", 0.95), ("p99", 0.99))
    duplicate_groups = [count for count in text_hash_counts.values() if count > 1]
    result = {
        "status": "complete",
        "diagnostic_scope": f"{args.region_label} regional file partition only; not a representative arm subsample and not a substantive research result",
        "purpose": "workload and corpus-readiness diagnostic only; no sample alteration",
        "rows": rows,
        "exact_text_sha256_unique_count": len(text_hash_counts),
        "exact_text_duplicate_rows_beyond_unique": rows - len(text_hash_counts),
        "exact_text_duplicate_group_count": len(duplicate_groups),
        "maximum_exact_text_duplicate_group_size": max(text_hash_counts.values()),
        "empty_exact_text_count": sum(value == 0 for value in character_counts),
        "unicode_character_count": {
            **{name: nearest_rank(character_counts, probability) for name, probability in probabilities},
            "max": max(character_counts),
            "greater_than_4096_characters": sum(value > 4096 for value in character_counts),
            "greater_than_8192_characters": sum(value > 8192 for value in character_counts),
        },
        "utf8_byte_count": {
            **{name: nearest_rank(byte_counts, probability) for name, probability in probabilities},
            "max": max(byte_counts),
        },
        "quantile_definition": "exact empirical nearest-rank quantile using rank ceil(p*n), one-indexed",
        "units_note": "Unicode character counts are Python Unicode code-point counts and are not tokens. UTF-8 byte counts are encoded bytes. No tokenization or token estimate was performed.",
        "hash_provenance": {
            "materialized_csv_sha256": actual_input_sha,
            "materialization_receipt_sha256": sha256_file(args.materialize_receipt),
            "selection_sha256": materialize_receipt.get("selection_sha256"),
            "source_map_sha256": materialize_receipt.get("source_map_sha256"),
        },
        "privacy": "aggregate counts only; no text, quotations, locators, private identifiers, or per-text hashes",
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "rows": rows, "unique_exact_texts": len(text_hash_counts)}, sort_keys=True))


if __name__ == "__main__":
    main()
