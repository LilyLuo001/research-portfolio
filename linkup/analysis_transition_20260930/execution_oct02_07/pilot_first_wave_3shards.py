#!/usr/bin/env python3
"""Select and run a fixed three-shard diagnostic using the frozen table builder."""
from __future__ import annotations
import argparse, hashlib, json, os, resource, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import run_first_wave as full_driver

SEED = "oct02-release-first-pilot-v1"

def read_json(path): return json.loads(Path(path).read_text())
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def atomic(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".tmp"); temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n"); os.replace(temp, path)
def ranked(rows): return sorted(rows, key=lambda r: (hashlib.sha256((SEED + ":" + r["shard_id"]).encode()).hexdigest(), r["shard_id"]))

def select(rows):
    by_id = {r["shard_id"]: r for r in rows}
    if len(by_id) != len(rows): raise RuntimeError("duplicate shard_id")
    ks = ranked([r for r in rows if str(r.get("region", "")).lower() == "kunshan"])
    wz = ranked([r for r in rows if str(r.get("region", "")).lower() == "wuzhen"])
    if not ks or not wz: raise RuntimeError("inventory must include Kunshan and Wuzhen")
    chosen = [ks[0], wz[0]]
    chosen_ids = {r["shard_id"] for r in chosen}
    extra = next(r for r in ranked(rows) if r["shard_id"] not in chosen_ids)
    return chosen + [extra]

def validate_gate(path, pre_gate):
    if pre_gate:
        return {"mode": "pre_gate_diagnostic", "global_acceptance": False}
    if not path: raise RuntimeError("--gate is required unless --pre-gate-diagnostic is explicit")
    gate = read_json(path)
    if gate.get("status") != "complete" or gate.get("final_publication_complete") is not True or gate.get("total_shards") != 2464:
        raise RuntimeError("global release gate is incomplete")
    return {"mode": "post_global_gate", "global_acceptance": True, "gate_sha256": digest(path)}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--inventory", type=Path, required=True, help="JSONL rows: shard_id, region, shard_dir, receipt")
    p.add_argument("--plans", type=Path, nargs="+", required=True, help="Exact frozen regional plan JSONL files")
    p.add_argument("--output", type=Path, required=True); p.add_argument("--gate", type=Path)
    p.add_argument("--pre-gate-diagnostic", action="store_true")
    p.add_argument("--builder", type=Path, default=Path(__file__).resolve().parents[2] / "stage_c_release_v1/build_release_first_tables.py")
    a = p.parse_args(); gate = validate_gate(a.gate, a.pre_gate_diagnostic)
    frozen_ids = full_driver.load_plan_ids([x.resolve() for x in a.plans])
    rows = [json.loads(x) for x in a.inventory.read_text().splitlines() if x.strip()]
    if len(rows) != 2464 or {r.get("shard_id") for r in rows} != frozen_ids:
        raise RuntimeError("inventory IDs must equal the exact frozen regional plans")
    chosen = select(rows); a.output.mkdir(parents=True, exist_ok=False)
    (a.output / "summaries").mkdir()
    started = time.monotonic(); usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    summaries = []
    for row in chosen:
        shard, receipt = Path(row["shard_dir"]), Path(row["receipt"])
        if not shard.is_dir() or not receipt.is_file(): raise FileNotFoundError(row["shard_id"])
        full_driver.validate_shard_identity(row)
        target = a.output / "summaries" / (row["shard_id"] + ".json")
        subprocess.run([sys.executable, str(a.builder), "shard", "--shard-dir", str(shard), "--receipt", str(receipt), "--output", str(target)], check=True)
        summaries.append(target)
    merged = a.output / "tables"
    subprocess.run([sys.executable, str(a.builder), "merge", "--summaries", *map(str, summaries), "--output-dir", str(merged)], check=True)
    report = read_json(merged / "CONSERVATION_REPORT.json")
    if report.get("status") != "complete" or report.get("shards") != 3: raise RuntimeError("pilot merge failed conservation")
    usage_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    atomic(a.output / "PILOT_RUN_RECEIPT.json", {**gate, "status": "complete", "seed": SEED,
        "selection_rule": "lowest SHA256(seed:shard_id): one Kunshan, one Wuzhen, then lowest remaining globally; no semantic output used",
        "shard_ids": [r["shard_id"] for r in chosen], "builder_sha256": digest(a.builder),
        "inventory_sha256": digest(a.inventory), "plan_sha256": {str(x): digest(x) for x in a.plans},
        "conservation_report_sha256": digest(merged / "CONSERVATION_REPORT.json"),
        "runtime": {"wall_seconds": time.monotonic() - started,
                    "child_cpu_seconds": (usage_after.ru_utime + usage_after.ru_stime - usage_before.ru_utime - usage_before.ru_stime),
                    "child_peak_rss_native": usage_after.ru_maxrss, "platform": sys.platform}})

if __name__ == "__main__": main()
