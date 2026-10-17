#!/usr/bin/env python3
"""Emit schemas and aggregate label shapes needed to configure the fixed baseline."""
import glob
import json
import os
from collections import Counter, defaultdict

import pyarrow.parquet as pq

LEDGER = "/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/batch001/final/FIELD_PROVENANCE_LEDGER_PRIVATE.jsonl"
FRAME = "/work/home/lilysharp/private/next_stage_20261004/text_handoff_20261007/verified_fixed10000/MERGED_FIXED10000_EXACT_TEXT_PRIVATE.parquet"
SHARDS = "/work/home/lilysharp/dewey_remaining_descriptions/data/linkup_job_descriptions"


def shape(value):
    if isinstance(value, dict):
        return {k: shape(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return {"list_len": len(value), "item_shapes": sorted({json.dumps(shape(v), sort_keys=True) for v in value})[:8]}
    return type(value).__name__


def main():
    statuses = Counter()
    shapes = defaultdict(Counter)
    rows = 0
    with open(LEDGER, encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            rows += 1
            family = row["field_family"]
            statuses[(family, row["status"])] += 1
            if row["status"] in ("known", "not_applicable"):
                shapes[family][json.dumps(shape(row.get("structured_value")), sort_keys=True)] += 1
    shard_paths = sorted(glob.glob(os.path.join(SHARDS, "**", "*.parquet"), recursive=True))
    if not shard_paths:
        raise RuntimeError("no LinkUp parquet shard found")
    out = {
        "ledger_rows": rows,
        "ledger_statuses": [{"family": k[0], "status": k[1], "count": v} for k, v in sorted(statuses.items())],
        "value_shapes": {k: [{"shape": s, "count": n} for s, n in v.most_common(8)] for k, v in sorted(shapes.items())},
        "frame_schema": str(pq.ParquetFile(FRAME).schema_arrow),
        "first_linkup_shard": shard_paths[0],
        "first_linkup_schema": str(pq.ParquetFile(shard_paths[0]).schema_arrow),
        "first_linkup_rows": pq.ParquetFile(shard_paths[0]).metadata.num_rows,
    }
    print(json.dumps(out, sort_keys=True))


if __name__ == "__main__":
    main()
