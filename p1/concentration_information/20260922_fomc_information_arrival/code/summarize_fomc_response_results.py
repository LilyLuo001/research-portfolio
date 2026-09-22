#!/usr/bin/env python3
"""Create disclosure-safe FOMC response/timing summaries from SCC outputs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def asset_class(row: pd.Series) -> str:
    if row["dataset"] == "GLBX.MDP3":
        return "ES"
    if row["symbol"] == "SPY":
        return "SPY"
    return "STOCK"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--response-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()
    src = Path(args.response_dir)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    r = pd.read_csv(src / "EVENT_RESPONSE_SUMMARY.csv")
    t = pd.read_csv(src / "TIMING_DIAGNOSTICS.csv")
    r["asset_class"] = r.apply(asset_class, axis=1)
    t["asset_class"] = t.apply(asset_class, axis=1)

    # Preserve only valid endpoints and provide transparent row denominators.
    rv = r[r["valid"].astype(str).str.lower().eq("true")].copy()
    rv["abs_mid_change_bp"] = rv["mid_change_bp"].abs()
    agg = (
        rv.groupby(["split", "sample_kind", "asset_class", "endpoint_ms"], dropna=False)
        .agg(
            observations=("mid_change_bp", "size"),
            dates=("date", "nunique"),
            symbols=("symbol", "nunique"),
            mean_mid_change_bp=("mid_change_bp", "mean"),
            median_mid_change_bp=("mid_change_bp", "median"),
            mean_abs_mid_change_bp=("abs_mid_change_bp", "mean"),
            median_abs_mid_change_bp=("abs_mid_change_bp", "median"),
            median_spread_bp=("spread_bp", "median"),
            median_quote_state_age_ms=("quote_state_age_ms", "median"),
        )
        .reset_index()
    )
    agg.to_csv(out / "RESPONSE_PATH_AGGREGATES.csv", index=False)

    # Per-date paths are compact enough to support event/control inspection.
    by_event = (
        rv.groupby(["date", "event_id", "split", "sample_kind", "asset_class", "endpoint_ms"])
        .agg(
            observations=("mid_change_bp", "size"),
            mean_mid_change_bp=("mid_change_bp", "mean"),
            median_mid_change_bp=("mid_change_bp", "median"),
            mean_abs_mid_change_bp=("abs_mid_change_bp", "mean"),
            median_abs_mid_change_bp=("abs_mid_change_bp", "median"),
        )
        .reset_index()
    )
    by_event.to_csv(out / "RESPONSE_BY_DATE.csv", index=False)

    t["detected"] = t["status"].eq("DETECTED")
    timing = (
        t.groupby(["split", "sample_kind", "asset_class", "grid_shift_ms", "mad_multiplier"])
        .agg(
            observations=("status", "size"),
            dates=("date", "nunique"),
            detection_rate=("detected", "mean"),
            median_detection_seconds=("detection_seconds", "median"),
            p25_detection_seconds=("detection_seconds", lambda x: x.quantile(.25)),
            p75_detection_seconds=("detection_seconds", lambda x: x.quantile(.75)),
        )
        .reset_index()
    )
    timing.to_csv(out / "TIMING_SUMMARY.csv", index=False)
    main_t = t[(t["grid_shift_ms"] == 0) & (t["mad_multiplier"] == 3)].copy()
    timing_event = (
        main_t.groupby(["date", "event_id", "split", "sample_kind", "asset_class"])
        .agg(
            observations=("status", "size"),
            detected=("detected", "sum"),
            detection_rate=("detected", "mean"),
            median_detection_seconds=("detection_seconds", "median"),
        )
        .reset_index()
    )
    timing_event.to_csv(out / "TIMING_BY_DATE_MAIN.csv", index=False)

    # Plot TEST event/control magnitude paths (descriptive, not causal).
    p = agg[agg["split"].eq("TEST")]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), sharex=True)
    for ax, ac in zip(axes, ["ES", "SPY", "STOCK"]):
        q = p[p["asset_class"].eq(ac)]
        for kind, style in [("EVENT", "-"), ("CONTROL", "--")]:
            z = q[q["sample_kind"].eq(kind)].sort_values("endpoint_ms")
            ax.plot(z["endpoint_ms"] / 1000, z["median_abs_mid_change_bp"], style, marker="o", label=kind)
        ax.set_xscale("log")
        ax.set_title(ac)
        ax.set_xlabel("Seconds after 14:00 ET (log scale)")
        ax.grid(alpha=.25)
    axes[0].set_ylabel("Median absolute mid-price change (bp)")
    axes[-1].legend(frameon=False)
    fig.suptitle("2024 FOMC event versus matched-control response paths")
    fig.tight_layout()
    fig.savefig(out / "FIGURE_RESPONSE_PATHS_TEST.png", dpi=180)
    plt.close(fig)

    receipt = {
        "status": "COMPLETE_DISCLOSURE_SAFE_RESPONSE_SUMMARY",
        "response_input_rows": int(len(r)),
        "valid_response_rows": int(len(rv)),
        "timing_input_rows": int(len(t)),
        "event_dates": int(r.loc[r.sample_kind.eq("EVENT"), "date"].nunique()),
        "control_dates": int(r.loc[r.sample_kind.eq("CONTROL"), "date"].nunique()),
        "main_timing_rule": {"grid_shift_ms": 0, "mad_multiplier": 3},
        "interpretation_boundary": "descriptive event-clock evidence; no causal ETF leadership claim",
        "outputs": sorted(x.name for x in out.iterdir()),
    }
    (out / "RESPONSE_SUMMARY_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
