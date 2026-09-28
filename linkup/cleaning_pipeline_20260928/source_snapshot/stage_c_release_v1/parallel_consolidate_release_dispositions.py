#!/usr/bin/env python3
"""Parallel, restartable disposition consolidation without repeated tree scans."""
from __future__ import annotations

import argparse
import concurrent.futures as futures
import json
import os
import shutil
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

import prepare_release_dispositions as prep

VERSION = "parallel_consolidation_v1"
DEFAULT_CAP = 17_000_000_000
DEFAULT_RESERVE = 8_000_000_000
OUTPUT_ALLOWANCE = 64 * 1024 * 1024


def read_json(path):
    return json.loads(Path(path).read_text())


def validate_prefix_headers(cfg, root):
    receipts = []
    for prefix in prep.PREFIXES:
        path = root / "prefix_receipts" / ("prefix_%s.json" % prefix)
        value = read_json(path)
        if (value.get("status") != "complete"
                or value.get("config_sha256") != cfg["_config_sha256"]
                or value.get("script_sha256") != cfg["_script_sha256"]
                or not value.get("row_conservation")):
            raise RuntimeError("invalid prefix receipt: " + prefix)
        receipts.append(value)
    return receipts


def build_tasks(cfg, receipts):
    """Load metadata once and assign every source exactly one deterministic task."""
    sources, _ = prep.load_inventory(cfg["source_inventories"])
    expected_doc = read_json(cfg["expected_source_rows"])
    expected = {(x["region"], x["source_file"]): int(x["raw_rows"])
                for x in expected_doc["sources"]}
    fragments = defaultdict(list)
    fragment_root = Path(cfg["output_root"]) / "prefix_fragments"
    for receipt in receipts:
        for item in receipt["fragment_files"]:
            path = Path(item["path"])
            relative = path.relative_to(fragment_root)
            if len(relative.parts) != 4:
                raise RuntimeError("unexpected fragment path: " + str(path))
            _, region, sid, _ = relative.parts
            fragments[(region, sid)].append({"path": str(path), "bytes": int(item["bytes"])})
    tasks = []
    for (region, source_file), source in sorted(sources.items()):
        sid = source["shard_id"]
        if (region, source_file) not in expected:
            raise RuntimeError("source absent from expected rows")
        task = {"region": region, "source_file": source_file, "source": source,
                "expected_rows": expected[(region, source_file)],
                "fragments": sorted(fragments.get((region, sid), []), key=lambda x: x["path"]),
                "sidecar_root": cfg["sidecar_root"]}
        tasks.append(task)
    ids = [x["source"]["shard_id"] for x in tasks]
    if len(ids) != len(set(ids)) or len(tasks) != len(sources):
        raise RuntimeError("consolidation task plan is not one-to-one")
    return tasks


def output_paths(task):
    output = Path(task["sidecar_root"]) / task["region"] / (task["source"]["shard_id"] + ".parquet")
    return output, output.with_suffix(".complete.json"), Path(str(output) + ".tmp")


def validate_complete(task, output, receipt_path):
    if not receipt_path.exists():
        return None
    receipt = read_json(receipt_path)
    if (receipt.get("status") != "complete"
            or receipt.get("shard_id") != task["source"]["shard_id"]
            or receipt.get("source_file") != task["source_file"]
            or receipt.get("raw_rows") != task["expected_rows"]
            or not output.is_file()
            or receipt.get("sidecar_sha256") != prep.sha256(output)):
        raise RuntimeError("existing sidecar receipt failed validation: " + task["source_file"])
    return receipt


def delete_known_fragments(receipt_path, receipt, fragments):
    if not receipt_path.is_file():
        raise RuntimeError("refusing fragment deletion before receipt seal")
    for item in fragments:
        Path(item["path"]).unlink(missing_ok=True)
    receipt["generated_fragments_deleted_after_sidecar_seal"] = True
    prep.atomic_json(receipt_path, receipt)


def consolidate_task(task):
    if hasattr(pa, "set_cpu_count"):
        pa.set_cpu_count(1)
    output, receipt_path, temp = output_paths(task)
    existing = validate_complete(task, output, receipt_path)
    fragment_bytes = sum(x["bytes"] for x in task["fragments"] if Path(x["path"]).exists())
    if existing:
        delete_known_fragments(receipt_path, existing, task["fragments"])
        return {"status": "resumed_sealed", "shard_id": existing["shard_id"],
                "fragment_bytes_deleted": fragment_bytes, "sidecar_bytes": output.stat().st_size,
                "storage_delta_bytes": -fragment_bytes}

    # A killed writer may leave a temp or an atomically-renamed output before
    # its receipt. Fragments are deleted only after receipt seal, so this state
    # is safe to discard and rebuild if all indexed fragments still exist.
    bad = [x["path"] for x in task["fragments"]
           if not Path(x["path"]).is_file() or Path(x["path"]).stat().st_size != x["bytes"]]
    if not task["fragments"] or bad:
        raise RuntimeError("unsealed shard has missing fragments: " + task["source_file"])
    recovered_orphan = output.exists() or temp.exists()
    old_generated_bytes = sum(path.stat().st_size for path in (output, temp) if path.exists())
    temp.unlink(missing_ok=True)
    output.unlink(missing_ok=True)

    paths = [x["path"] for x in task["fragments"]]
    table = pq.read_table(paths, schema=prep.SIDECAR_SCHEMA, use_threads=False)
    order = pc.sort_indices(table, sort_keys=[("SOURCE_ROW", "ascending")])
    table = pc.take(table, order)
    rows = table["SOURCE_ROW"].combine_chunks()
    values = rows.to_numpy(zero_copy_only=False)
    if (rows.null_count or len(values) != task["expected_rows"]
            or not np.array_equal(values, np.arange(task["expected_rows"], dtype=np.int64))):
        raise RuntimeError("SOURCE_ROW is not complete/unique for " + task["source_file"])
    counts = Counter(table["MATCH_DISPOSITION"].to_pylist())
    if set(counts) - prep.DISPOSITIONS:
        raise RuntimeError("unknown disposition in consolidated sidecar")

    output.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, temp, compression="zstd", row_group_size=8192)
    max_output = max(2 * fragment_bytes, fragment_bytes + OUTPUT_ALLOWANCE)
    if temp.stat().st_size > max_output:
        temp.unlink()
        raise RuntimeError("sidecar exceeded conservative output reservation")
    os.replace(temp, output)
    source = task["source"]
    receipt = {
        "status": "complete", "shard_id": source["shard_id"], "region": task["region"],
        "source_file": task["source_file"], "raw_rows": table.num_rows,
        "disposition_counts": dict(sorted(counts.items())),
        "sidecar_path": str(output), "sidecar_bytes": output.stat().st_size,
        "sidecar_sha256": prep.sha256(output), "fragment_count": len(paths),
        "source_path": source["source_path"], "source_bytes": source["source_bytes"],
        "source_sha256_cached": source["source_sha256_cached"],
        "consolidator": VERSION, "recovered_unsealed_generated_output": recovered_orphan,
    }
    prep.atomic_json(receipt_path, receipt)
    delete_known_fragments(receipt_path, receipt, task["fragments"])
    return {"status": "sealed", "shard_id": source["shard_id"],
            "fragment_bytes_deleted": fragment_bytes, "sidecar_bytes": output.stat().st_size,
            "storage_delta_bytes": output.stat().st_size - fragment_bytes - old_generated_bytes,
            "raw_rows": table.num_rows, "recovered_orphan": recovered_orphan}


def known_current_bytes(tasks, root):
    paths = set()
    for task in tasks:
        output, _, temp = output_paths(task)
        for path in (output, temp):
            if path.exists(): paths.add(path)
        for item in task["fragments"]:
            path = Path(item["path"])
            if path.exists(): paths.add(path)
    attempts = root / "prefix_attempts"
    if attempts.exists():
        paths.update(path for path in attempts.rglob("*") if path.is_file())
    return sum(path.stat().st_size for path in paths)


def task_reservation(task):
    _, receipt, _ = output_paths(task)
    if receipt.exists():
        return 0
    size = sum(x["bytes"] for x in task["fragments"] if Path(x["path"]).exists())
    return max(2 * size, size + OUTPUT_ALLOWANCE)


def choose_batch(pending, workers, current_bytes, cap_bytes, free_bytes, reserve_bytes):
    batch = []; reservation = 0
    for task in pending[:workers]:
        extra = task_reservation(task)
        if current_bytes + reservation + extra > cap_bytes:
            break
        if reservation + extra > max(0, free_bytes - reserve_bytes):
            break
        batch.append(task); reservation += extra
    if not batch:
        raise RuntimeError("no consolidation task fits storage/reserve envelope")
    return batch, reservation


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--intermediate-cap-bytes", type=int, default=DEFAULT_CAP)
    parser.add_argument("--free-reserve-bytes", type=int, default=DEFAULT_RESERVE)
    args = parser.parse_args()
    if not 1 <= args.workers <= 24:
        raise ValueError("workers must be 1..24")
    cfg = prep.load_config(args.config)
    cfg["_config_sha256"] = prep.sha256(args.config)
    cfg["_script_sha256"] = prep.sha256(Path(prep.__file__).resolve())
    root = Path(cfg["output_root"])
    receipts = validate_prefix_headers(cfg, root)
    tasks = build_tasks(cfg, receipts)
    progress = root / "PARALLEL_CONSOLIDATION_PROGRESS.json"
    prep.atomic_json(root / "PARALLEL_CONSOLIDATION_PLAN.json", {
        "status": "frozen", "version": VERSION, "planned_shards": len(tasks),
        "workers": args.workers, "task_shard_ids": [x["source"]["shard_id"] for x in tasks],
    })
    current = known_current_bytes(tasks, root)
    completed = 0; statuses = Counter()
    with futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        while completed < len(tasks):
            pending = tasks[completed:]
            free = shutil.disk_usage(root).free
            batch, reservation = choose_batch(pending, args.workers, current,
                                                args.intermediate_cap_bytes, free,
                                                args.free_reserve_bytes)
            results = list(pool.map(consolidate_task, batch))
            for result in results:
                statuses[result["status"]] += 1
                current += int(result["storage_delta_bytes"])
            completed += len(batch)
            # Bounded post-check: validate only the files touched by this batch.
            for task in batch:
                output, receipt_path, temp = output_paths(task)
                if temp.exists() or validate_complete(task, output, receipt_path) is None:
                    raise RuntimeError("batch post-check failed")
                if any(Path(x["path"]).exists() for x in task["fragments"]):
                    raise RuntimeError("sealed batch retained generated fragments")
            prep.atomic_json(progress, {"status": "running", "version": VERSION,
                "completed_shards": completed, "planned_shards": len(tasks),
                "result_statuses": dict(statuses), "tracked_intermediate_bytes": current,
                "last_batch_shards": len(batch), "last_batch_reserved_bytes": reservation,
                "intermediate_cap_bytes": args.intermediate_cap_bytes})
    result = prep.finalize(cfg)
    result.update({"consolidator": VERSION, "workers": args.workers,
                   "result_statuses": dict(statuses), "tracked_intermediate_bytes": current})
    prep.atomic_json(root / "CONSOLIDATION_COMPLETE.json", result)
    prep.atomic_json(progress, {"status": "complete", "planned_shards": len(tasks),
                                "result_statuses": dict(statuses)})
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
