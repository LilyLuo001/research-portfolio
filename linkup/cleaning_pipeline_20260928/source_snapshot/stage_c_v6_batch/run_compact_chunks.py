#!/usr/bin/env python3
"""Run compact-v2 on deterministic contiguous sample chunks in parallel."""
import argparse
import concurrent.futures as cf
import importlib.util
import json
import shutil
from pathlib import Path

import pyarrow.parquet as pq


def load_runner(path):
    spec = importlib.util.spec_from_file_location("compact_v6", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.MODULE


def task(values):
    runner_path, source, parser, output, start, rows, cap = values
    runner = load_runner(Path(runner_path))
    return runner.process_source(Path(source), Path(parser), Path(output), rows, 256, cap, start)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True); ap.add_argument("--parser", required=True)
    ap.add_argument("--output-dir", required=True); ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--output-cap-bytes", type=int, required=True)
    args = ap.parse_args()
    root = Path(args.output_dir); root.mkdir(parents=True, exist_ok=False)
    rows = pq.ParquetFile(args.source).metadata.num_rows
    chunks = min(args.workers, rows)
    chunk_rows = (rows + chunks - 1) // chunks
    per_cap = args.output_cap_bytes // chunks
    tasks = []
    for i in range(chunks):
        start = i * chunk_rows
        count = min(chunk_rows, rows - start)
        if count > 0:
            tasks.append((Path(__file__).resolve().parent / "compact_candidate_batch_v6.py",
                          args.source, args.parser, root / ("chunk_%02d" % i), start, count, per_cap))
    try:
        with cf.ProcessPoolExecutor(max_workers=chunks) as pool:
            receipts = list(pool.map(task, tasks))
        total_bytes = sum(p.stat().st_size for p in root.rglob("*") if p.is_file())
        if total_bytes > args.output_cap_bytes:
            raise RuntimeError("compact global output cap exceeded")
        complete = {
            "status": "complete" if all(x["status"] == "complete" for x in receipts) else "stopped_cap",
            "sample_rows": rows, "processed_rows": sum(x["processed_rows"] for x in receipts),
            "parse_errors": sum(x["status_counts"]["parse_error"] for x in receipts),
            "truncated_rows": sum(x["truncated_rows"] for x in receipts),
            "evidence_rows": sum(x["evidence_rows"] for x in receipts),
            "relation_rows": sum(x["relation_rows"] for x in receipts),
            "persistent_bytes": total_bytes, "output_cap_bytes": args.output_cap_bytes,
            "workers": chunks, "chunk_receipts": receipts,
        }
        (root / "COMPLETE.json").write_text(json.dumps(complete, indent=2, sort_keys=True) + "\n")
        print(json.dumps(complete, sort_keys=True))
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise


if __name__ == "__main__":
    main()
