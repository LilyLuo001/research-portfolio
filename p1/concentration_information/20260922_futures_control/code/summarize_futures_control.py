#!/usr/bin/env python3
"""Create the primary decision table and two figures from aggregate outputs."""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True, type=Path); args = ap.parse_args()
    root = args.root
    agg = pd.read_csv(root / "AGGREGATE_COMPARISON.csv")
    sens = pd.read_csv(root / "DATE_SENSITIVITY.csv")
    primary = agg[(agg.es_cutoff == "AT_T") & (agg.support == "ES_VALID")].copy()
    primary.to_csv(root / "PRIMARY_DECISION_TABLE.csv", index=False)

    # Figure 1: same-support SPY increment before and after adding ES.
    z = primary[primary.contrast.isin(["SPY_RAW", "SPY_GIVEN_ES"])].copy()
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    for ax, family in zip(axes, ["QUOTE_WITH_REST_BASKET", "QUOTE_TRADE_WITH_REST_BASKET"]):
        q = z[z.family == family]
        labels, x, vals, lows, highs, colors = [], [], [], [], [], []
        pos = 0
        for venue in ("XNAS.ITCH", "ARCX.PILLAR"):
            for shift in (0, 500):
                for contrast in ("SPY_RAW", "SPY_GIVEN_ES"):
                    r = q[(q.venue == venue) & (q.grid_shift_ms == shift) & (q.contrast == contrast)].iloc[0]
                    labels.append(f"{venue.split('.')[0]} {shift}ms\n{'raw' if contrast == 'SPY_RAW' else 'given ES'}")
                    x.append(pos); vals.append(r.equal_stock_G)
                    lows.append(r.equal_stock_G - r.equal_ci_low); highs.append(r.equal_ci_high - r.equal_stock_G)
                    colors.append("#2b6cb0" if contrast == "SPY_RAW" else "#dd6b20"); pos += 1
                pos += .35
        ax.bar(x, vals, color=colors, width=.82)
        ax.errorbar(x, vals, yerr=[lows, highs], fmt="none", ecolor="black", capsize=2, lw=.9)
        ax.axhline(0, color="black", lw=.8); ax.set_xticks(x, labels, rotation=45, ha="right", fontsize=7)
        ax.set_title("Quotes" if family.startswith("QUOTE_WITH") else "Quotes + separated trades")
        ax.set_ylabel("Out-of-sample G (equal stock)")
    fig.suptitle("SPY incremental prediction before and after ES control")
    fig.tight_layout(); fig.savefig(root / "FIG1_SPY_BEFORE_AFTER_ES.png", dpi=180); plt.close(fig)

    # Figure 2: two conditional increments and their leave-one-test-date-out range.
    q = primary[(primary.family == "QUOTE_WITH_REST_BASKET") & primary.contrast.isin(["SPY_GIVEN_ES", "ES_GIVEN_SPY"])].copy()
    s = sens[(sens.es_cutoff == "AT_T") & (sens.support == "ES_VALID") &
             (sens.family == "QUOTE_WITH_REST_BASKET") & sens.contrast.isin(["SPY_GIVEN_ES", "ES_GIVEN_SPY"])].copy()
    labels, vals, loo_min, loo_max, colors = [], [], [], [], []
    for venue in ("XNAS.ITCH", "ARCX.PILLAR"):
        for shift in (0, 500):
            for contrast in ("SPY_GIVEN_ES", "ES_GIVEN_SPY"):
                r = q[(q.venue == venue) & (q.grid_shift_ms == shift) & (q.contrast == contrast)].iloc[0]
                v = s[(s.venue == venue) & (s.grid_shift_ms == shift) & (s.contrast == contrast)].equal_stock_G
                labels.append(f"{venue.split('.')[0]} {shift}ms\n{'SPY|ES' if contrast == 'SPY_GIVEN_ES' else 'ES|SPY'}")
                vals.append(r.equal_stock_G); loo_min.append(v.min()); loo_max.append(v.max())
                colors.append("#2b6cb0" if contrast == "SPY_GIVEN_ES" else "#38a169")
    fig, ax = plt.subplots(figsize=(10, 4.7)); x = np.arange(len(vals))
    ax.bar(x, vals, color=colors)
    # The all-date nonlinear ratio need not fall inside the leave-one-date-out
    # range, so draw that range directly instead of using signed y-errors.
    ax.vlines(x, loo_min, loo_max, color="black", lw=1.2)
    ax.scatter(x, loo_min, color="black", marker="_", s=45, zorder=3)
    ax.scatter(x, loo_max, color="black", marker="_", s=45, zorder=3)
    ax.axhline(0, color="black", lw=.8); ax.set_xticks(x, labels, rotation=38, ha="right")
    ax.set_ylabel("Conditional G; bars show all-date point")
    ax.set_title("Conditional SPY and ES increments; whiskers are leave-one-date-out ranges")
    fig.tight_layout(); fig.savefig(root / "FIG2_CONDITIONAL_AND_DATE_SENSITIVITY.png", dpi=180); plt.close(fig)
    print({"primary_rows": len(primary), "figures": 2})


if __name__ == "__main__":
    main()
