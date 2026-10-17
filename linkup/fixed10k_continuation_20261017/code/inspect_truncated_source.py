#!/usr/bin/env python3
"""Inspect only the locator structure needed to recover Batch004 record 084."""
import argparse
import json
from pathlib import Path

import pyarrow.parquet as pq


def rows(path):
    with open(path, encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--claim-manifest", required=True)
    parser.add_argument("--source-map", required=True)
    parser.add_argument("--frame", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    target = next(x for x in rows(args.claim_manifest)
                  if x["record_id"] == "fixed10k-prod-b004-084")
    key = target["representative_canonical_key"]
    source_matches = [x for x in rows(args.source_map)
                      if x.get("JOB_HASH") == key["JOB_HASH"]]
    report = {
        "target_found": True,
        "canonical_key_names": sorted(key),
        "source_file_value_kind": "absolute" if str(key["SOURCE_FILE"]).startswith("/") else "relative",
        "source_file_basename": Path(str(key["SOURCE_FILE"])).name,
        "source_row_type": type(key["SOURCE_ROW"]).__name__,
        "record_source_row_type": type(key["RECORD_SOURCE_ROW"]).__name__,
        "source_map_match_count_by_job_hash": len(source_matches),
        "source_map_field_names": sorted({name for row in source_matches for name in row}),
        "frame_schema_names": pq.ParquetFile(args.frame).schema.names,
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
