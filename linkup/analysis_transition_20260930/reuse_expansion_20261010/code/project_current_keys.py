#!/usr/bin/env python3
"""Project canonical posting keys for one frozen D67 shard.

This is a mechanical, scheduled projection.  It does not inspect text or run
any rule/model.  Input identity is taken from the accepted production receipt.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import platform
from pathlib import Path

import pyarrow.parquet as pq

KEY_COLUMNS = ["JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW",
               "CREATED", "STATE"]
VERSION = "d67-current-key-projection-v1"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temp, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--index", required=True, type=int)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()
    manifest = json.load(open(args.manifest, encoding="utf-8"))
    shards = manifest["shards"]
    if not 0 <= args.index < len(shards):
        raise RuntimeError("array index outside frozen manifest")
    shard = shards[args.index]
    receipt = json.load(open(shard["production_receipt"], encoding="utf-8"))
    if receipt.get("status") != "complete":
        raise RuntimeError("production receipt is not complete")
    posting = Path(shard["posting"])
    expected = receipt["outputs"]
    if sha256(posting) != expected["posting_sha256"]:
        raise RuntimeError("posting sha differs from accepted receipt")
    parquet = pq.ParquetFile(posting)
    missing = set(KEY_COLUMNS) - set(parquet.schema_arrow.names)
    if missing:
        raise RuntimeError("posting lacks columns: " + ",".join(sorted(missing)))
    if parquet.metadata.num_rows != expected["posting_rows"]:
        raise RuntimeError("posting row count differs from accepted receipt")
    output_root = Path(args.output_root); output_root.mkdir(parents=True, exist_ok=True)
    shard_id = shard["shard_id"]
    output = output_root / (shard_id + ".keys.parquet")
    temp = Path(str(output) + ".tmp")
    writer = None; rows = 0
    try:
        for batch in parquet.iter_batches(batch_size=65536, columns=KEY_COLUMNS):
            if writer is None:
                writer = pq.ParquetWriter(temp, batch.schema, compression="zstd")
            writer.write_table(__import__("pyarrow").Table.from_batches([batch]))
            rows += batch.num_rows
        if writer is None:
            raise RuntimeError("posting unexpectedly empty")
        writer.close(); writer = None; os.replace(temp, output)
    finally:
        if writer is not None:
            writer.close()
        if temp.exists():
            temp.unlink()
    if rows != expected["posting_rows"]:
        raise RuntimeError("projected rows do not conserve posting denominator")
    atomic_json(output_root / (shard_id + ".keys.receipt.json"), {
        "version": VERSION, "status": "complete", "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "shard_id": shard_id, "source_file": receipt.get("source_file"),
        "posting_path": str(posting), "posting_sha256": expected["posting_sha256"],
        "posting_rows": expected["posting_rows"], "output_path": str(output),
        "output_rows": rows, "output_bytes": output.stat().st_size, "output_sha256": sha256(output),
        "scheduler": {"job_id": os.environ.get("SLURM_JOB_ID"), "array_task_id": os.environ.get("SLURM_ARRAY_TASK_ID"),
                      "host": platform.node()}, "model_calls": 0, "api_calls": 0, "full_text_reads": 0,
    })


if __name__ == "__main__":
    main()
