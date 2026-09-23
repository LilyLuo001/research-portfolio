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
    # The resampling unit is the connected date component.  Pre-aggregate each
    # component's event-level losses by issuer, then apply bootstrap
    # multiplicities by matrix multiplication.  This is algebraically
    # equivalent to cloning component DataFrames (including cloned event IDs)
    # but avoids millions of small concat/groupby operations.
    event_loss = (
        frame.groupby(["component_id", "issuer", "event_id"], as_index=False)[
            ["mean_loss_baseline", "mean_loss_full"]
        ]
        .mean()
    )
    issuers = sorted(event_loss.issuer.unique())
    component_index = {value: idx for idx, value in enumerate(components)}
    issuer_index = {value: idx for idx, value in enumerate(issuers)}
    counts = np.zeros((len(components), len(issuers)), dtype=float)
    loss_b = np.zeros_like(counts)
    loss_f = np.zeros_like(counts)
    for row in event_loss.itertuples(index=False):
        c = component_index[row.component_id]
        i = issuer_index[row.issuer]
        counts[c, i] += 1.0
        loss_b[c, i] += row.mean_loss_baseline
        loss_f[c, i] += row.mean_loss_full
    rng = np.random.default_rng(seed)
    sampled = rng.integers(0, len(components), size=(draws, len(components)))
    multiplicities = np.zeros((draws, len(components)), dtype=float)
    rows = np.repeat(np.arange(draws), len(components))
    np.add.at(multiplicities, (rows, sampled.ravel()), 1.0)
    issuer_counts = multiplicities @ counts
    with np.errstate(divide="ignore", invalid="ignore"):
        issuer_b = (multiplicities @ loss_b) / issuer_counts
        issuer_f = (multiplicities @ loss_f) / issuer_counts
    issuer_b[issuer_counts == 0] = np.nan
    issuer_f[issuer_counts == 0] = np.nan
    mean_b = np.nanmean(issuer_b, axis=1)
    mean_f = np.nanmean(issuer_f, axis=1)
    values = 1.0 - mean_f / mean_b
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
    # Support must not sum the same target centers over comparisons, model
    # specifications, grids, or horizons.  The loss table has one identical
    # target-support row per model; retain one representative model row and
    # report each actual scoring cell separately.
    support_key = ["venue", "grid_shift_ms", "horizon_seconds", "window", "split", "sample_kind", "session", "sample_id", "event_id", "issuer", "date", "n"]
    support_rows = raw.drop_duplicates(support_key)[support_key].copy()
    support_rows["component_id"] = support_rows.event_id.map(union_components(support_rows))
    support = support_rows.groupby(["venue", "grid_shift_ms", "horizon_seconds", "window", "split", "sample_kind", "session"], dropna=False).agg(unique_events=("event_id", "nunique"), unique_issuers=("issuer", "nunique"), unique_dates=("date", "nunique"), date_components=("component_id", "nunique"), actual_prediction_centers=("n", "sum"), sample_rows=("sample_id", "nunique")).reset_index()
    support["support_definition"] = "deduplicated across model and fit_spec; per venue/grid/horizon/window/scoring cell"
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
