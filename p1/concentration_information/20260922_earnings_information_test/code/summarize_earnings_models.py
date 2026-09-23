#!/usr/bin/env python3
"""Combine SCC model losses into safe hierarchical comparisons and sensitivity tables."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

COMPARISONS = {"A0_TO_A1": ("A0", "A1"), "A2_TO_A3": ("A2", "A3"), "A3_TO_A5": ("A3", "A5"), "A2_TO_A5": ("A2", "A5"), "A0_TO_A2": ("A0", "A2")}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def union_components(frame: pd.DataFrame) -> dict[str, str]:
    events = sorted(frame.event_id.unique())
    parent = {event: event for event in events}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[max(a, b)] = min(a, b)
    for _day, group in frame[["date", "event_id"]].drop_duplicates().groupby("date"):
        ids = sorted(group.event_id.unique())
        for other in ids[1:]:
            union(ids[0], other)
    return {event: find(event) for event in events}


def hierarchical_loss(frame: pd.DataFrame, col: str) -> float:
    return float(frame.groupby(["issuer", "event_id"])[col].mean().groupby(level=0).mean().mean())


def statistic(frame: pd.DataFrame) -> dict:
    b, f = hierarchical_loss(frame, "mean_loss_baseline"), hierarchical_loss(frame, "mean_loss_full")
    sb, sf = float(frame.sse_baseline.sum()), float(frame.sse_full.sum())
    return {"G_equal_issuer_event": 1.0 - f / b if b else np.nan, "G_pooled_sse": 1.0 - sf / sb if sb else np.nan, "mean_loss_baseline": b, "mean_loss_full": f, "paired_mean_loss_change": b - f, "sse_baseline": sb, "sse_full": sf, "prediction_centers": int(frame.n.sum()), "events": int(frame.event_id.nunique()), "issuers": int(frame.issuer.nunique()), "dates": int(frame.date.nunique()), "components": int(frame.component_id.nunique())}


def bootstrap(frame: pd.DataFrame, seed: int, draws: int = 2000) -> tuple[float, float]:
    components = sorted(frame.component_id.unique())
    if len(components) < 2:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    values = []
    groups = {component: frame[frame.component_id == component] for component in components}
    for _ in range(draws):
        sampled = rng.choice(components, len(components), replace=True)
        pieces = []
        for draw_id, component in enumerate(sampled):
            part = groups[component].copy()
            part["event_id"] = part.event_id + f"__draw{draw_id}"
            pieces.append(part)
        values.append(statistic(pd.concat(pieces, ignore_index=True))["G_equal_issuer_event"])
    return float(np.nanquantile(values, 0.025)), float(np.nanquantile(values, 0.975))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, action="append", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    raw = pd.concat([pd.read_csv(path) for path in args.input], ignore_index=True)
    key = ["venue", "grid_shift_ms", "horizon_seconds", "fit_spec", "window", "sample_id", "event_id", "issuer", "date", "sample_kind", "split", "session", "n"]
    comparisons = []
    for name, (baseline, full) in COMPARISONS.items():
        b = raw[raw.model == baseline][key + ["sse", "mean_loss"]].rename(columns={"sse": "sse_baseline", "mean_loss": "mean_loss_baseline"})
        f = raw[raw.model == full][key + ["sse", "mean_loss"]].rename(columns={"sse": "sse_full", "mean_loss": "mean_loss_full"})
        pair = b.merge(f, on=key, validate="one_to_one")
        pair["comparison"] = name
        comparisons.append(pair)
    paired = pd.concat(comparisons, ignore_index=True)
    mapping = union_components(paired)
    paired["component_id"] = paired.event_id.map(mapping)
    group_cols = ["venue", "grid_shift_ms", "horizon_seconds", "fit_spec", "window", "comparison", "split", "sample_kind", "session"]
    results = []
    for number, (keys, group) in enumerate(paired.groupby(group_cols, sort=False)):
        point = statistic(group)
        low, high = bootstrap(group, 20260923 + number)
        results.append({**dict(zip(group_cols, keys)), **point, "ci_low": low, "ci_high": high})
    results = pd.DataFrame(results)
    loo = []
    primary = paired[(paired.comparison == "A2_TO_A5") & (paired.split == "TEST")]
    for group_keys, group in primary.groupby(["venue", "grid_shift_ms", "horizon_seconds", "fit_spec", "window", "sample_kind", "session"]):
        meta = dict(zip(["venue", "grid_shift_ms", "horizon_seconds", "fit_spec", "window", "sample_kind", "session"], group_keys))
        for issuer in sorted(group.issuer.unique()):
            part = group[group.issuer != issuer]
            if len(part): loo.append({**meta, "deletion_type": "ISSUER", "deleted": issuer, **statistic(part)})
        for component in sorted(group.component_id.unique()):
            part = group[group.component_id != component]
            if len(part): loo.append({**meta, "deletion_type": "DATE_COMPONENT", "deleted": component, **statistic(part)})
    support = paired.groupby(["split", "sample_kind", "session"]).agg(events=("event_id", "nunique"), issuers=("issuer", "nunique"), dates=("date", "nunique"), components=("component_id", "nunique"), prediction_centers=("n", "sum")).reset_index()
    args.out.mkdir(parents=True, exist_ok=True)
    results.to_csv(args.out / "PREDICTION_RESULTS.csv", index=False)
    pd.DataFrame(loo).to_csv(args.out / "LOO.csv", index=False)
    support.to_csv(args.out / "DEPENDENCE_AND_SUPPORT.csv", index=False)
    paired.to_csv(args.out / "PAIRED_MODEL_LOSSES.csv.gz", index=False, compression="gzip")
    receipt = {"status": "COMPLETE_SAFE_EARNINGS_MODEL_SUMMARY", "inputs": [{"path": str(path), "sha256": digest(path)} for path in args.input], "result_rows": len(results), "loo_rows": len(loo), "bootstrap_draws": 2000, "dependency_cluster": "connected components of event_ids sharing any event/control economic date", "primary_comparison": "A2_TO_A5"}
    (args.out / "SUMMARY_RECEIPT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
