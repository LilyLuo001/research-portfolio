#!/usr/bin/env python3
"""Validate one lean-writer pilot without emitting record identifiers."""
import argparse
import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pilot_dir")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.pilot_dir)
    receipt = json.loads((root / "COMPLETE.json").read_text())
    keys = ["JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW"]
    ad_keys = set()
    ad_count_sum = {"experience": 0, "technology": 0}
    evidence_keys = {"experience": set(), "technology": set()}
    observed = {"ad_status": 0, "experience": 0, "technology": 0}
    hashes_ok = True
    metadata_rows_ok = True
    for chunk in receipt["chunks"]:
        chunk_dir = root / ("chunk_%02d" % (chunk["start"] // chunk["requested_rows"]))
        for table_name, filename in (("ad_status", "ad_status.parquet"),
                                     ("experience", "experience.parquet"),
                                     ("technology", "technology.parquet")):
            path = chunk_dir / filename
            expected = chunk["outputs"][filename]
            hashes_ok &= sha256(path) == expected["sha256"]
            metadata_rows_ok &= pq.ParquetFile(path).metadata.num_rows == expected["rows"]
            columns = list(keys)
            if table_name == "ad_status":
                columns += ["EXPERIENCE_EVIDENCE_COUNT", "TECHNOLOGY_EVIDENCE_COUNT"]
            rows = pq.read_table(path, columns=columns).to_pylist()
            observed[table_name] += len(rows)
            for row in rows:
                key = tuple(row[name] for name in keys)
                if table_name == "ad_status":
                    ad_keys.add(key)
                    ad_count_sum["experience"] += row["EXPERIENCE_EVIDENCE_COUNT"]
                    ad_count_sum["technology"] += row["TECHNOLOGY_EVIDENCE_COUNT"]
                else:
                    evidence_keys[table_name].add(key)
    result = {
        "status": "pass" if all((
            hashes_ok, metadata_rows_ok,
            observed["ad_status"] == receipt["processed_rows"],
            observed["experience"] == receipt["experience_rows"],
            observed["technology"] == receipt["technology_rows"],
            len(ad_keys) == receipt["processed_rows"],
            evidence_keys["experience"].issubset(ad_keys),
            evidence_keys["technology"].issubset(ad_keys),
            ad_count_sum["experience"] == observed["experience"],
            ad_count_sum["technology"] == observed["technology"],
        )) else "fail",
        "processed_rows": receipt["processed_rows"],
        "unique_ad_keys": len(ad_keys),
        "observed_rows": observed,
        "ad_count_sums": ad_count_sum,
        "evidence_key_subsets": {
            name: values.issubset(ad_keys) for name, values in evidence_keys.items()
        },
        "file_hashes_ok": hashes_ok,
        "parquet_metadata_rows_ok": metadata_rows_ok,
    }
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
    if result["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
