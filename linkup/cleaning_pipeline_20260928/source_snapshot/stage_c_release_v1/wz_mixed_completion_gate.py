#!/usr/bin/env python3
"""Promote a mixed-version Wuzhen run only after every frozen shard reconciles."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic(path: Path, value: dict) -> None:
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temp, path)


def plan(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def sealed_complete(checkpoints: Path, shard_id: str) -> tuple[dict, str]:
    published = checkpoints / (shard_id + ".published.json")
    if published.is_file():
        receipt = json.loads(published.read_text())
        if receipt.get("status") != "published_verified":
            raise RuntimeError(shard_id + ": invalid published receipt")
        return receipt["shard_complete"], "published"
    queued = checkpoints / (shard_id + ".queued.json")
    if not queued.is_file():
        raise RuntimeError(shard_id + ": no queued/published receipt")
    receipt = json.loads(queued.read_text())
    complete_path = Path(receipt["shard_complete"])
    if receipt.get("status") != "sealed_for_transfer" or not complete_path.is_file():
        raise RuntimeError(shard_id + ": invalid queued receipt/output")
    if sha(complete_path) != receipt["shard_complete_sha256"]:
        raise RuntimeError(shard_id + ": queued SHARD_COMPLETE digest mismatch")
    return json.loads(complete_path.read_text()), "queued"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full-plan", type=Path, required=True)
    ap.add_argument("--new-plan", type=Path, required=True)
    ap.add_argument("--checkpoint-root", type=Path, required=True)
    ap.add_argument("--old-code", type=Path, required=True)
    ap.add_argument("--new-code", type=Path, required=True)
    ap.add_argument("--new-provenance", type=Path, required=True)
    ap.add_argument("--partition-marker", default="REGION_QUEUE_COMPLETE.dcu_remaining.json")
    args = ap.parse_args()

    full_rows = plan(args.full_plan); new_rows = plan(args.new_plan)
    full = {row["shard_id"]: row for row in full_rows}
    new_ids = {row["shard_id"] for row in new_rows}
    if len(full) != len(full_rows) or len(new_ids) != len(new_rows):
        raise RuntimeError("duplicate shard_id in plan")
    if not new_ids < set(full):
        raise RuntimeError("new plan must be a proper subset of full plan")
    old_ids = set(full) - new_ids
    if (len(full), len(old_ids), len(new_ids)) != (1106, 349, 757):
        raise RuntimeError("frozen Wuzhen split must be 1106=349+757")

    old_code = json.loads(args.old_code.read_text())
    new_code = json.loads(args.new_code.read_text())
    expected_provenance = json.loads(args.new_provenance.read_text())
    marker_path = args.checkpoint_root / args.partition_marker
    marker = json.loads(marker_path.read_text())
    if (marker.get("status") != "compute_queue_complete"
            or marker.get("planned_shards") != 757
            or marker.get("completed_plan_shards") != 757
            or marker.get("plan_sha256") != sha(args.new_plan)):
        raise RuntimeError("remaining partition marker mismatch")

    states = {"queued": 0, "published": 0}
    for shard_id, row in full.items():
        complete, state = sealed_complete(args.checkpoint_root, shard_id)
        states[state] += 1
        expected_code = new_code if shard_id in new_ids else old_code
        if complete.get("code_sha256") != expected_code:
            raise RuntimeError(shard_id + ": code identity mismatch")
        accounting = complete.get("accounting", {})
        for key in ("source_file", "source_bytes", "source_sha256_cached", "sidecar_sha256", "raw_rows"):
            if accounting.get(key) != row[key]:
                raise RuntimeError(shard_id + ": accounting mismatch: " + key)
        if shard_id in new_ids:
            actual = complete.get("lean_complete", {}).get("dcu_provenance")
            if actual != expected_provenance:
                raise RuntimeError(shard_id + ": DCU provenance mismatch")

    expectation = {
        "schema_version": 1,
        "status": "frozen",
        "full_plan_sha256": sha(args.full_plan),
        "groups": [
            {"name": "cpu_original", "shard_ids": sorted(old_ids), "code_sha256": old_code},
            {"name": "dcu_remaining", "shard_ids": sorted(new_ids), "code_sha256": new_code,
             "dcu_provenance": expected_provenance},
        ],
    }
    expectation_path = args.checkpoint_root / "WZ_CODE_EXPECTATIONS.json"
    atomic(expectation_path, expectation)
    atomic(args.checkpoint_root / "REGION_QUEUE_COMPLETE.json", {
        "status": "compute_queue_complete", "planned_shards": 1106,
        "completed_plan_shards": 1106, "queued_receipts": states["queued"],
        "published_receipts": states["published"],
        "full_plan_sha256": sha(args.full_plan),
        "code_expectations_sha256": sha(expectation_path),
        "final_publication_complete": False,
    })


if __name__ == "__main__":
    main()
