#!/usr/bin/env python3
"""Aggregate SCC model losses by event cluster and copy-safe summaries."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


COMPARISONS = {
    "A0_TO_A1_SPY_QUOTE_WEAK_BASE": ("A0", "A1"),
    "A2_TO_A3_SPY_QUOTE_AFTER_C": ("A2", "A3"),
    "A3_TO_A5_SPY_TRADE_AFTER_CQ": ("A3", "A5"),
    "A2_TO_A5_COMPLETE_SPY_AFTER_C": ("A2", "A5"),
    "A0_TO_A2_CASH_TRADES": ("A0", "A2"),
    "A1_TO_A3_CASH_TRADES_AFTER_Q": ("A1", "A3"),
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for part in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def event_cell_results(loss: pd.DataFrame) -> pd.DataFrame:
    keys = ["venue", "grid_shift_ms", "symbol", "fit_spec", "window",
            "date", "event_id", "sample_kind", "split"]
    wide = loss.pivot_table(index=keys, columns="model", values=["sse", "n"], aggfunc="sum")
    wide.columns = [f"{a}_{b}" for a, b in wide.columns]
    wide = wide.reset_index()
    rows = []
    for name, (base, full) in COMPARISONS.items():
        part = wide[keys].copy()
        part["comparison"] = name
        part["base_model"] = base; part["full_model"] = full
        part["n"] = wide[f"n_{base}"].astype(int)
        part["sse_base"] = wide[f"sse_{base}"]
        part["sse_full"] = wide[f"sse_{full}"]
        part["G"] = 1.0 - part.sse_full / part.sse_base
        rows.append(part)
    return pd.concat(rows, ignore_index=True)


def equal_weight_event(cell: pd.DataFrame) -> pd.DataFrame:
    keys = ["fit_spec", "window", "event_id", "sample_kind", "split", "comparison"]
    stock = cell.groupby(keys + ["venue", "grid_shift_ms", "symbol"], as_index=False).agg(
        G=("G", "mean"), n=("n", "sum"), sse_base=("sse_base", "sum"), sse_full=("sse_full", "sum"))
    event = stock.groupby(keys, as_index=False).agg(
        equal_weight_G=("G", "mean"), cells=("G", "size"),
        n=("n", "sum"), sse_base=("sse_base", "sum"), sse_full=("sse_full", "sum"))
    event["pooled_sse_G"] = 1.0 - event.sse_full / event.sse_base
    return event


def paired(event: pd.DataFrame) -> pd.DataFrame:
    index = ["fit_spec", "window", "event_id", "split", "comparison"]
    values = ["equal_weight_G", "pooled_sse_G", "cells", "n"]
    wide = event.pivot(index=index, columns="sample_kind", values=values)
    wide.columns = [f"{a}_{b.lower()}" for a, b in wide.columns]
    wide = wide.reset_index()
    required = {"equal_weight_G_event", "equal_weight_G_control"}
    if not required.issubset(wide.columns):
        raise RuntimeError("every event cluster needs EVENT and CONTROL rows")
    wide["paired_difference_G"] = wide.equal_weight_G_event - wide.equal_weight_G_control
    return wide


def bootstrap_summary(pairs: pd.DataFrame, repetitions: int, seed: int):
    rng = np.random.default_rng(seed); rows = []; loo = []
    group = ["fit_spec", "window", "split", "comparison"]
    for keys, frame in pairs.groupby(group, sort=False):
        frame = frame.sort_values("event_id")
        values = frame.paired_difference_G.to_numpy(float)
        event_values = frame.equal_weight_G_event.to_numpy(float)
        control_values = frame.equal_weight_G_control.to_numpy(float)
        draws_diff = []; draws_event = []; draws_control = []
        for _ in range(repetitions):
            ix = rng.integers(0, len(frame), len(frame))
            draws_diff.append(float(values[ix].mean()))
            draws_event.append(float(event_values[ix].mean()))
            draws_control.append(float(control_values[ix].mean()))
        row = dict(zip(group, keys))
        row.update({
            "events": len(frame),
            "event_G": float(event_values.mean()),
            "event_ci_low": float(np.quantile(draws_event, .025)),
            "event_ci_high": float(np.quantile(draws_event, .975)),
            "control_G": float(control_values.mean()),
            "control_ci_low": float(np.quantile(draws_control, .025)),
            "control_ci_high": float(np.quantile(draws_control, .975)),
            "paired_difference_G": float(values.mean()),
            "paired_ci_low": float(np.quantile(draws_diff, .025)),
            "paired_ci_high": float(np.quantile(draws_diff, .975)),
            "positive_event_clusters": int((event_values > 0).sum()),
            "positive_paired_differences": int((values > 0).sum()),
        })
        rows.append(row)
        if len(frame) > 1:
            for event_id in frame.event_id:
                keep = frame.event_id != event_id
                loo.append({**dict(zip(group, keys)), "left_out_event_id": event_id,
                            "event_G": float(event_values[keep].mean()),
                            "control_G": float(control_values[keep].mean()),
                            "paired_difference_G": float(values[keep].mean())})
    return pd.DataFrame(rows), pd.DataFrame(loo)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--daily-sse", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--repetitions", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20260922)
    args = ap.parse_args()
    loss = pd.read_csv(args.daily_sse, dtype={"date": str, "event_id": str})
    cell = event_cell_results(loss)
    event = equal_weight_event(cell)
    pairs = paired(event)
    summary, loo = bootstrap_summary(pairs, args.repetitions, args.seed)
    args.out.mkdir(parents=True, exist_ok=True)
    cell.to_csv(args.out / "EVENT_PREDICTION_RESULTS.csv", index=False)
    event.to_csv(args.out / "EVENT_LEVEL_RESULTS.csv", index=False)
    pairs.to_csv(args.out / "PAIRED_EVENT_CONTROL.csv", index=False)
    summary.to_csv(args.out / "PREDICTION_SUMMARY.csv", index=False)
    loo.to_csv(args.out / "LOO.csv", index=False)
    receipt = {
        "status": "COMPLETE_FOMC_PREDICTION_SUMMARY",
        "daily_sse_sha256": digest(args.daily_sse), "bootstrap_repetitions": args.repetitions,
        "seed": args.seed, "comparisons": COMPARISONS,
        "cell_rows": len(cell), "event_rows": len(event), "pair_rows": len(pairs),
        "summary_rows": len(summary), "loo_rows": len(loo),
        "primary": {"split": "TEST", "window": "POST_0_60S",
                    "comparison": "A2_TO_A5_COMPLETE_SPY_AFTER_C",
                    "weighting": "equal stocks, equal venue-grid cells, equal event clusters"},
    }
    (args.out / "SUMMARY_RECEIPT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
