#!/usr/bin/env python3
"""Materialize one canonical-USA shard input from a frozen disposition sidecar."""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


DISPOSITIONS = {
    "matched_usa_canonical",
    "matched_usa_duplicate_quarantine",
    "matched_non_usa",
    "record_unmatched",
}
OUTPUT_SCHEMA = pa.schema([
    ("JOB_HASH", pa.string()), ("SOURCE_FILE", pa.string()),
    ("SOURCE_ROW", pa.int64()), ("RECORD_SOURCE_ROW", pa.int64()),
    ("CREATED", pa.timestamp("ms")), ("COUNTRY", pa.string()),
    ("STATE", pa.string()), ("DESCRIPTION", pa.string()),
])


def is_usa(value: object) -> bool:
    normalized = " ".join(str(value or "").strip().upper().replace(".", "").split())
    return normalized in {"US", "USA", "UNITED STATES", "UNITED STATES OF AMERICA"}


def atomic_json(path: Path, value: dict) -> None:
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temp, path)


def prepare(raw_path: Path, sidecar_path: Path, output_path: Path) -> dict:
    sidecar_table = pq.read_table(sidecar_path)
    required = {
        "SOURCE_ROW", "JOB_HASH", "MATCH_DISPOSITION", "RECORD_SOURCE_ROW",
        "CREATED", "COUNTRY", "STATE", "SOURCE_FILE",
    }
    missing = required - set(sidecar_table.column_names)
    if missing:
        raise ValueError("sidecar missing columns: " + ",".join(sorted(missing)))
    sidecars = sidecar_table.to_pylist()
    by_row = {}
    dispositions = Counter()
    sidecar_source_files = set()
    for row in sidecars:
        source_row = row["SOURCE_ROW"]
        disposition = row["MATCH_DISPOSITION"]
        if not isinstance(source_row, int) or source_row in by_row:
            raise ValueError("sidecar SOURCE_ROW missing or duplicated")
        if disposition not in DISPOSITIONS:
            raise ValueError("unknown MATCH_DISPOSITION: %r" % disposition)
        matched = disposition != "record_unmatched"
        if matched != (row["RECORD_SOURCE_ROW"] is not None):
            raise ValueError("matched disposition/RECORD_SOURCE_ROW inconsistency")
        if disposition in {"matched_usa_canonical", "matched_usa_duplicate_quarantine"} and not is_usa(row["COUNTRY"]):
            raise ValueError("USA disposition has non-USA COUNTRY")
        if disposition == "matched_non_usa" and is_usa(row["COUNTRY"]):
            raise ValueError("matched_non_usa disposition has USA COUNTRY")
        by_row[source_row] = row
        dispositions[disposition] += 1
        sidecar_source_files.add(row["SOURCE_FILE"])

    pf = pq.ParquetFile(raw_path)
    if pf.metadata.num_rows != len(by_row):
        raise ValueError("sidecar/raw row conservation failure")
    if set(by_row) != set(range(pf.metadata.num_rows)):
        raise ValueError("sidecar SOURCE_ROW must be zero-based and contiguous")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(output_path) + ".tmp")
    writer = pq.ParquetWriter(temp, OUTPUT_SCHEMA, compression="zstd")
    source_row = 0
    selected = 0
    try:
        for group in range(pf.num_row_groups):
            raw = pf.read_row_group(group, columns=["JOB_HASH", "DESCRIPTION"]).to_pylist()
            batch = []
            for item in raw:
                joined = by_row[source_row]
                if item["JOB_HASH"] != joined["JOB_HASH"]:
                    raise ValueError("raw/sidecar JOB_HASH mismatch at SOURCE_ROW=%d" % source_row)
                if joined["MATCH_DISPOSITION"] == "matched_usa_canonical":
                    batch.append({
                        "JOB_HASH": item["JOB_HASH"],
                        "SOURCE_FILE": joined["SOURCE_FILE"],
                        "SOURCE_ROW": source_row,
                        "RECORD_SOURCE_ROW": joined["RECORD_SOURCE_ROW"],
                        "CREATED": joined["CREATED"], "COUNTRY": joined["COUNTRY"],
                        "STATE": joined["STATE"], "DESCRIPTION": item["DESCRIPTION"],
                    })
                source_row += 1
            if batch:
                writer.write_table(pa.Table.from_pylist(batch, schema=OUTPUT_SCHEMA))
                selected += len(batch)
        writer.close()
        os.replace(temp, output_path)
    except Exception:
        writer.close()
        temp.unlink(missing_ok=True)
        raise
    return {
        "raw_rows": pf.metadata.num_rows,
        "sidecar_rows": len(sidecars),
        "canonical_usa_rows": selected,
        "sidecar_source_files": sorted(sidecar_source_files),
        "disposition_counts": dict(sorted(dispositions.items())),
        "row_conservation": sum(dispositions.values()) == pf.metadata.num_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--sidecar", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    receipt = prepare(args.raw.resolve(), args.sidecar.resolve(), args.output.resolve())
    atomic_json(args.receipt.resolve(), receipt)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
