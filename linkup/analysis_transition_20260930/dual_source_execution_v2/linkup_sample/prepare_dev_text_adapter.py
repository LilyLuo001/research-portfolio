#!/usr/bin/env python3
"""Adapt L1 development keys to the frozen regional text materializer interface."""
import argparse
import hashlib
import json
import os
from pathlib import Path

import pyarrow.parquet as pq

KEYS = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")
REGIONS = ("kunshan", "wuzhen")


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git_ancestor(path):
    path = Path(path).resolve()
    for candidate in (path, *path.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def read_jsonl(path):
    with Path(path).open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def atomic_text(path, text, mode=0o600):
    path = Path(path)
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(text)
    os.chmod(tmp, mode)
    os.replace(tmp, path)


def private_key(row):
    return json.dumps([row[name] for name in KEYS], separators=(",", ":"))


def load_plan_index(paths):
    index = {}
    plan_hashes = {}
    for path in paths:
        plan_hashes[str(path)] = sha256(path)
        for row in read_jsonl(path):
            region = row.get("region")
            name = row.get("source_file")
            source = row.get("source_path")
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


def load_keys(path, expected):
    rows = pq.read_table(path).to_pylist()
    if len(rows) != expected:
        raise RuntimeError(f"{path.name} must contain exactly {expected} rows")
    for i, row in enumerate(rows):
        if any(row.get(name) in (None, "") for name in KEYS):
            raise RuntimeError(f"incomplete canonical locator at row {i}")
        row["SOURCE_ROW"] = int(row["SOURCE_ROW"])
        row["RECORD_SOURCE_ROW"] = int(row["RECORD_SOURCE_ROW"])
    ids = [tuple(str(row[name]) for name in KEYS) for row in rows]
    if len(ids) != len(set(ids)):
        raise RuntimeError(f"{path.name} repeats a canonical key")
    return rows


def selection_json(rows, region, purpose):
    return {
        "format": "materialize_selected_text.selected_list.v1",
        "purpose": purpose,
        "region": region,
        "selected": [{"private_key": private_key(row)} for row in rows],
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--development", type=Path, required=True)
    p.add_argument("--config-compare", type=Path, required=True)
    p.add_argument("--source-plan", type=Path, action="append", required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--kunshan-materializer", default="/public/home/lilysharp/linkup_analysis_execution_oct02/code/pre_revelio_execution_v1/materialize_selected_text.py")
    p.add_argument("--wuzhen-materializer", default="/work/home/lilysharp/private/human_review_pack_20261003/phase2_tools/materialize_selected_text.py")
    a = p.parse_args()
    repo = git_ancestor(a.output_dir)
    if repo is not None:
        raise RuntimeError(f"private key adapter output cannot be inside Git worktree: {repo}")
    a.output_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(a.output_dir, 0o700)

    source_index, plan_hashes = load_plan_index(a.source_plan)
    dev = load_keys(a.development, 200)
    config = load_keys(a.config_compare, 80)
    dev_ids = {tuple(str(row[name]) for name in KEYS) for row in dev}
    config_ids = {tuple(str(row[name]) for name in KEYS) for row in config}
    if not config_ids <= dev_ids:
        raise RuntimeError("configuration comparison keys are not a subset of development keys")

    by_region = {region: [] for region in REGIONS}
    config_by_region = {region: [] for region in REGIONS}
    for row, target in [(row, by_region) for row in dev] + [(row, config_by_region) for row in config]:
        name = str(row["SOURCE_FILE"])
        source = source_index.get(name)
        if source is None:
            raise RuntimeError(f"SOURCE_FILE absent from frozen source plans: {name}")
        region = source["region"]
        if region not in target:
            raise RuntimeError(f"unknown region for selected key: {region!r}")
        target[region].append(row)

    outputs = []
    commands = ["#!/bin/bash", "set -euo pipefail", "OUT=${1:?pass adapter private output directory}"]
    materializers = {"kunshan": a.kunshan_materializer, "wuzhen": a.wuzhen_materializer}
    for region in REGIONS:
        selection = a.output_dir / f"development_200_{region}.selection.json"
        config_manifest = a.output_dir / f"config_compare_80_{region}.manifest.json"
        source_map = a.output_dir / f"development_200_{region}.source_map.jsonl"
        atomic_text(selection, json.dumps(selection_json(by_region[region], region, "development_200"), indent=2) + "\n")
        atomic_text(config_manifest, json.dumps(selection_json(config_by_region[region], region, "config_compare_80_within_development"), indent=2) + "\n")
        names = sorted({str(row["SOURCE_FILE"]) for row in by_region[region]})
        mapping = "".join(json.dumps({"SOURCE_FILE": name, "path": source_index[name]["path"]}, sort_keys=True) + "\n" for name in names)
        atomic_text(source_map, mapping)
        outputs.extend((selection, config_manifest, source_map))
        if by_region[region]:
            commands.extend([
                f"python {materializers[region]} \\",
                f"  --selection \"$OUT/{selection.name}\" \\",
                f"  --source-map \"$OUT/{source_map.name}\" \\",
                f"  --output \"$OUT/development_200_{region}.text.csv\" \\",
                f"  --receipt \"$OUT/development_200_{region}.materialize_receipt.json\" \\",
                "  --text-column DESCRIPTION --max-rows 200",
            ])
    runner = a.output_dir / "RUN_MATERIALIZE_BY_REGION_PRIVATE.sh"
    atomic_text(runner, "\n".join(commands) + "\n", mode=0o700)
    outputs.append(runner)

    partition_ids = {tuple(str(row[name]) for name in KEYS) for region in REGIONS for row in by_region[region]}
    if partition_ids != dev_ids or sum(map(len, by_region.values())) != 200:
        raise RuntimeError("development partition key conservation failed")
    config_partition_ids = {tuple(str(row[name]) for name in KEYS) for region in REGIONS for row in config_by_region[region]}
    if config_partition_ids != config_ids or sum(map(len, config_by_region.values())) != 80:
        raise RuntimeError("configuration partition key conservation failed")

    receipt = {
        "status": "complete_private_adapter_no_text_read",
        "development_rows": 200,
        "config_compare_rows": 80,
        "region_counts": {region: {"development": len(by_region[region]), "config_compare": len(config_by_region[region]), "source_files": len({row['SOURCE_FILE'] for row in by_region[region]})} for region in REGIONS},
        "invariants": {"development_key_conservation": True, "config_subset_of_development": True, "config_key_conservation": True, "unknown_region_is_error": True},
        "inputs": {"development_sha256": sha256(a.development), "config_compare_sha256": sha256(a.config_compare), "source_plan_sha256": plan_hashes},
        "outputs": {path.name: sha256(path) for path in outputs},
        "materializer_interface": {"selection": "JSON object with selected[].private_key encoding the four canonical fields", "source_map": "JSONL SOURCE_FILE to absolute path", "text_column": "DESCRIPTION", "max_rows": 200},
    }
    receipt_path = a.output_dir / "DEV_TEXT_ADAPTER_RECEIPT_PRIVATE.json"
    atomic_text(receipt_path, json.dumps(receipt, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()

