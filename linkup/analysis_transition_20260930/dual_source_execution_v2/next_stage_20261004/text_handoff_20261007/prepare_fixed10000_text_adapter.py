#!/usr/bin/env python3
"""Prepare frozen regional text-materializer inputs for the fixed 10,000-key sample.

This program only reads locator keys and frozen source plans.  It never opens
source Parquet files or raw descriptions.  Its output directory must be a
private directory outside a Git worktree.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
from pathlib import Path

import pyarrow.parquet as pq

KEYS = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")
REGIONS = ("kunshan", "wuzhen")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git_ancestor(path: Path) -> Path | None:
    path = path.resolve()
    for candidate in (path, *path.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def atomic_text(path: Path, text: str, mode: int = 0o600) -> None:
    temp = Path(str(path) + ".tmp")
    temp.write_text(text)
    os.chmod(temp, mode)
    os.replace(temp, path)


def read_jsonl(path: Path) -> list[dict]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_source_index(paths: list[Path]) -> tuple[dict[str, dict], dict[str, str]]:
    index: dict[str, dict] = {}
    plan_hashes: dict[str, str] = {}
    for path in paths:
        plan_hashes[str(path)] = sha256(path)
        for row in read_jsonl(path):
            region, name, source = row.get("region"), row.get("source_file"), row.get("source_path")
            if region not in REGIONS:
                raise RuntimeError(f"unknown region in frozen source plan: {region!r}")
            if not name or Path(name).name != name:
                raise RuntimeError("invalid source_file in frozen source plan")
            if not source or not Path(source).is_absolute() or Path(source).name != name:
                raise RuntimeError(f"invalid source_path for {name}")
            value = {"region": region, "path": source}
            if name in index and index[name] != value:
                raise RuntimeError(f"conflicting frozen source mapping for {name}")
            index[name] = value
    return index, plan_hashes


def load_keys(path: Path, expected_rows: int) -> list[dict]:
    rows = pq.read_table(path, columns=list(KEYS)).to_pylist()
    if len(rows) != expected_rows:
        raise RuntimeError(f"{path.name} must contain exactly {expected_rows} rows, found {len(rows)}")
    ids = []
    for number, row in enumerate(rows):
        if any(row.get(name) in (None, "") for name in KEYS):
            raise RuntimeError(f"incomplete canonical locator at row {number}")
        row["SOURCE_ROW"] = int(row["SOURCE_ROW"])
        row["RECORD_SOURCE_ROW"] = int(row["RECORD_SOURCE_ROW"])
        ids.append(tuple(str(row[name]) for name in KEYS))
    if len(ids) != len(set(ids)):
        raise RuntimeError(f"{path.name} repeats a canonical key")
    return rows


def selection(rows: list[dict], region: str) -> dict:
    return {
        "format": "materialize_selected_text.selected_list.v1",
        "purpose": "fixed_research_sample_10000",
        "region": region,
        "selected": [{"private_key": json.dumps([row[name] for name in KEYS], separators=(",", ":"))} for row in rows],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--source-plan", type=Path, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--public-receipt", type=Path, required=True)
    parser.add_argument("--expected-rows", type=int, default=10_000)
    parser.add_argument("--kunshan-materializer", default="/public/home/lilysharp/linkup_analysis_execution_oct02/code/dual_source_execution_v2/next_stage_20261004/text_handoff_20261007/materialize_fixed10000_selected_text.py")
    parser.add_argument("--wuzhen-materializer", default="/work/home/lilysharp/private/dual_source_execution_v2/next_stage_20261004/text_handoff_20261007/materialize_fixed10000_selected_text.py")
    args = parser.parse_args()
    if git_ancestor(args.output_dir) is not None:
        raise RuntimeError("private adapter output cannot be inside a Git worktree")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(args.output_dir, 0o700)

    source_index, plan_hashes = load_source_index(args.source_plan)
    rows = load_keys(args.sample, args.expected_rows)
    by_region = {region: [] for region in REGIONS}
    for row in rows:
        source = source_index.get(str(row["SOURCE_FILE"]))
        if source is None:
            raise RuntimeError(f"SOURCE_FILE absent from frozen source plans: {row['SOURCE_FILE']}")
        by_region[source["region"]].append(row)

    outputs: list[Path] = []
    materializers = {"kunshan": args.kunshan_materializer, "wuzhen": args.wuzhen_materializer}
    for region in REGIONS:
        selected = args.output_dir / f"fixed10000_{region}.selection.json"
        source_map = args.output_dir / f"fixed10000_{region}.source_map.jsonl"
        atomic_text(selected, json.dumps(selection(by_region[region], region), indent=2) + "\n")
        names = sorted({str(row["SOURCE_FILE"]) for row in by_region[region]})
        atomic_text(source_map, "".join(json.dumps({"SOURCE_FILE": name, "path": source_index[name]["path"]}, sort_keys=True) + "\n" for name in names))
        outputs.extend((selected, source_map))
        if by_region[region]:
            commands = ["#!/bin/bash", "set -euo pipefail", "OUT=${1:?pass this adapter private output directory}"]
            commands.extend((
                f"python {shlex.quote(str(materializers[region]))} \\",
                f"  --selection \"$OUT/{selected.name}\" \\",
                f"  --source-map \"$OUT/{source_map.name}\" \\",
                f"  --output \"$OUT/fixed10000_{region}.text.csv\" \\",
                f"  --receipt \"$OUT/fixed10000_{region}.materialize_receipt.json\" \\",
                f"  --text-column DESCRIPTION --max-rows {args.expected_rows}",
            ))
            runner = args.output_dir / f"RUN_MATERIALIZE_FIXED10000_{region.upper()}_PRIVATE.sh"
            atomic_text(runner, "\n".join(commands) + "\n", mode=0o700)
            outputs.append(runner)

    selected_ids = {tuple(str(row[name]) for name in KEYS) for region in REGIONS for row in by_region[region]}
    input_ids = {tuple(str(row[name]) for name in KEYS) for row in rows}
    if selected_ids != input_ids or sum(map(len, by_region.values())) != args.expected_rows:
        raise RuntimeError("regional partition key conservation failed")
    receipt = {
        "status": "complete_private_adapter_no_text_read",
        "sample_rows": args.expected_rows,
        "region_counts": {region: {"records": len(by_region[region]), "source_files": len({row['SOURCE_FILE'] for row in by_region[region]})} for region in REGIONS},
        "invariants": {"canonical_key_unique": True, "regional_partition_key_conservation": True, "unknown_region_is_error": True},
        "inputs": {"sample_sha256": sha256(args.sample), "source_plan_sha256": plan_hashes},
        "outputs": {path.name: sha256(path) for path in outputs},
        "materializer_interface": {"selection": "selected[].private_key encodes JOB_HASH,SOURCE_FILE,SOURCE_ROW,RECORD_SOURCE_ROW", "source_map": "JSONL SOURCE_FILE to region-local absolute path", "text_column": "DESCRIPTION"},
    }
    atomic_text(args.output_dir / "FIXED10000_TEXT_ADAPTER_RECEIPT_PRIVATE.json", json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    public_receipt = {
        "status": "regional_materializer_inputs_prepared_no_text_read",
        "sample_rows": args.expected_rows,
        "region_counts": receipt["region_counts"],
        "invariants": receipt["invariants"],
        "input_hashes": {
            "sample_sha256": receipt["inputs"]["sample_sha256"],
            "source_plan_sha256": list(receipt["inputs"]["source_plan_sha256"].values()),
        },
        "privacy": "regional selections, source maps, raw paths, and all later text remain private; this receipt contains only counts and cryptographic hashes",
    }
    args.public_receipt.parent.mkdir(parents=True, exist_ok=True)
    atomic_text(args.public_receipt, json.dumps(public_receipt, indent=2, sort_keys=True) + "\n", mode=0o644)


if __name__ == "__main__":
    main()
