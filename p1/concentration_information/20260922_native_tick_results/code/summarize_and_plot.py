#!/usr/bin/env python3
"""Create compact, non-row-level summaries and figures for the native-tick pilot."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "FIGURES"
FIG.mkdir(exist_ok=True)


def scalar(df, column):
    if len(df) != 1:
        return np.nan
    return df.iloc[0][column]


pairs = pd.read_csv(ROOT / "PAIR_COUNTS.csv")
diag = pd.read_csv(ROOT / "QUOTE_DIAGNOSTICS.csv")
response = pd.read_csv(ROOT / "TRADE_RESPONSE.csv")
paths = pd.read_csv(ROOT / "ANNOUNCEMENT_PATHS.csv")

rows = []
keys = pairs[["window", "dataset", "stock"]].drop_duplicates().sort_values(["window", "dataset"])
for key in keys.itertuples(index=False):
    k = (pairs.window.eq(key.window) & pairs.dataset.eq(key.dataset) & pairs.stock.eq(key.stock))
    main = pairs[k & pairs.axis.eq("EVENT") & pairs.variant.eq("ALL_TRADES") & pairs.threshold_us.eq(20) & pairs.category.eq("ALL")]
    recv = pairs[k & pairs.axis.eq("RECEIVE") & pairs.variant.eq("ALL_TRADES") & pairs.threshold_us.eq(20) & pairs.category.eq("ALL")]
    periodic = pairs[k & pairs.axis.eq("EVENT") & pairs.variant.eq("EXCLUDE_FIRST_200MS") & pairs.threshold_us.eq(20) & pairs.category.eq("ALL")]
    same = pairs[k & pairs.axis.eq("EVENT") & pairs.variant.eq("ALL_TRADES") & pairs.threshold_us.eq(20) & pairs.category.isin(["B_B", "S_S"])]

    d = diag[(diag.window.eq(key.window)) & (diag.dataset.eq(key.dataset)) & (diag.stock.eq(key.stock)) & diag.axis.eq("EVENT")]
    stock_d = d[d.instrument.eq(key.stock)]
    spy_d = d[d.instrument.eq("SPY")]
    stock_total = scalar(stock_d, "classified_buy_trades") + scalar(stock_d, "classified_sell_trades") + scalar(stock_d, "unknown_direction_trades")
    spy_total = scalar(spy_d, "classified_buy_trades") + scalar(spy_d, "classified_sell_trades") + scalar(spy_d, "unknown_direction_trades")

    base = {
        "window": key.window,
        "module": "A_ANNOUNCEMENT" if not (key.window.endswith("_RTH") or key.window.endswith("_CTRL")) else ("B_RTH" if key.window.endswith("_RTH") else "C_CONTROL"),
        "dataset": key.dataset,
        "stock": key.stock,
        "stock_trades": scalar(main, "stock_trades"),
        "spy_trades": scalar(main, "spy_trades"),
        "near_pairs_20us_event": scalar(main, "near_pairs"),
        "background_pairs_event": scalar(main, "background_pairs"),
        "excess_pairs_20us_event": scalar(main, "excess_pairs"),
        "excess_per_1000_stock_event": scalar(main, "excess_per_1000_stock_trades"),
        "excess_per_1000_stock_receive": scalar(recv, "excess_per_1000_stock_trades"),
        "excess_per_1000_stock_event_periodic_exclusion": scalar(periodic, "excess_per_1000_stock_trades"),
        "same_direction_excess_pairs_event": same.excess_pairs.sum(min_count=1),
        "stock_direction_available_rate": (stock_total - scalar(stock_d, "unknown_direction_trades")) / stock_total if stock_total else np.nan,
        "spy_direction_available_rate": (spy_total - scalar(spy_d, "unknown_direction_trades")) / spy_total if spy_total else np.nan,
    }
    rkey = response.window.eq(key.window) & response.dataset.eq(key.dataset) & response.stock.eq(key.stock) & response.horizon_seconds.eq(5) & response.trade_sign.eq("ALL_SIGNED")
    for instrument_label, instrument in [("stock", key.stock), ("spy", "SPY")]:
        for group_label, group in [("paired", "SAME_DIRECTION_PAIRED_20US"), ("unpaired", "NOT_SAME_DIRECTION_PAIRED_20US")]:
            rr = response[rkey & response.instrument.eq(instrument) & response.pair_group.eq(group)]
            base[f"{instrument_label}_5s_{group_label}_n"] = scalar(rr, "n")
            base[f"{instrument_label}_5s_{group_label}_signed_mid_change_bp_mean"] = scalar(rr, "signed_mid_change_bp_mean")
    rows.append(base)

summary = pd.DataFrame(rows)
summary.to_csv(ROOT / "EVENT_SUMMARY.csv", index=False)

# Figure 1: main event-time excess coactivity, keeping negative estimates visible.
plot = summary.copy()
plot["label"] = plot.window + "\n" + plot.dataset.str.replace(".", "\n", regex=False)
colors = plot.module.map({"A_ANNOUNCEMENT": "#7b6fd0", "B_RTH": "#e07a2d", "C_CONTROL": "#4b9b82"})
fig, ax = plt.subplots(figsize=(13, 5.5))
ax.bar(np.arange(len(plot)), plot.excess_per_1000_stock_event, color=colors)
ax.axhline(0, color="black", linewidth=0.8)
ax.set_xticks(np.arange(len(plot)), plot.label, rotation=55, ha="right", fontsize=8)
ax.set_ylabel("20 µs excess pairs per 1,000 stock trades")
ax.set_title("Near-synchronous stock–SPY coactivity by window and venue")
ax.grid(axis="y", alpha=0.25)
fig.tight_layout()
fig.savefig(FIG / "excess_pairs_by_window.png", dpi=180)
plt.close(fig)

# Figure 2: event versus Databento receive timestamp sensitivity.
fig, ax = plt.subplots(figsize=(6.4, 6.0))
for module, color, marker in [("A_ANNOUNCEMENT", "#7b6fd0", "o"), ("B_RTH", "#e07a2d", "s"), ("C_CONTROL", "#4b9b82", "^")]:
    g = summary[summary.module.eq(module)]
    ax.scatter(g.excess_per_1000_stock_event, g.excess_per_1000_stock_receive, label=module, color=color, marker=marker, s=55, alpha=0.9)
lo = np.nanmin(summary[["excess_per_1000_stock_event", "excess_per_1000_stock_receive"]].to_numpy())
hi = np.nanmax(summary[["excess_per_1000_stock_event", "excess_per_1000_stock_receive"]].to_numpy())
ax.plot([lo, hi], [lo, hi], linestyle="--", color="gray", linewidth=1)
ax.axhline(0, color="black", linewidth=0.5)
ax.axvline(0, color="black", linewidth=0.5)
ax.set_xlabel("Event-time excess per 1,000 stock trades")
ax.set_ylabel("Receive-time excess per 1,000 stock trades")
ax.set_title("Timestamp-axis sensitivity at ±20 µs")
ax.legend(frameon=False)
ax.grid(alpha=0.2)
fig.tight_layout()
fig.savefig(FIG / "event_vs_receive_axis.png", dpi=180)
plt.close(fig)

# Figure 3: five-second signed midquote response; show sample sizes in labels.
rr = summary[summary.module.isin(["B_RTH", "C_CONTROL"])].copy()
rr["label"] = rr.window + "\n" + rr.dataset.str.split(".").str[0]
x = np.arange(len(rr))
width = 0.36
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
for ax, inst, title in [(ax1, "stock", "Stock"), (ax2, "spy", "SPY")]:
    paired = rr[f"{inst}_5s_paired_signed_mid_change_bp_mean"]
    unpaired = rr[f"{inst}_5s_unpaired_signed_mid_change_bp_mean"]
    ax.bar(x - width / 2, paired, width, label="same-direction paired", color="#d95f02")
    ax.bar(x + width / 2, unpaired, width, label="not paired", color="#1b9e77")
    ax.axhline(0, color="black", linewidth=0.7)
    ax.set_ylabel("5-second signed mid change (bp)")
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.2)
ax1.legend(frameon=False, ncol=2)
ax2.set_xticks(x, rr.label, rotation=50, ha="right", fontsize=8)
fig.suptitle("Post-trade quote response in RTH and control windows", y=0.995)
fig.tight_layout()
fig.savefig(FIG / "five_second_quote_response.png", dpi=180)
plt.close(fig)

# Figure 4: announcement-window mid paths. These are venue-specific, not NBBO.
a = paths[~paths.window.str.endswith(("_RTH", "_CTRL"))]
fig, axes = plt.subplots(3, 2, figsize=(12, 10), sharex=False)
for ax, ((window, dataset), g) in zip(axes.ravel(), a.groupby(["window", "dataset"], sort=True)):
    for instrument, color in [(g.stock.iloc[0], "#d95f02"), ("SPY", "#1b9e77")]:
        z = g[g.instrument.eq(instrument)]
        ax.plot(z.relative_second, z.mid_return_bp, label=instrument, color=color, linewidth=1)
    ax.axvline(0, color="black", linestyle="--", linewidth=0.7)
    ax.set_title(f"{window} — {dataset}")
    ax.set_xlabel("seconds from candidate minute")
    ax.set_ylabel("mid return (bp)")
    ax.grid(alpha=0.2)
axes[0, 0].legend(frameon=False)
fig.suptitle("Announcement-window venue midquote paths (candidate minute only)", y=0.995)
fig.tight_layout()
fig.savefig(FIG / "announcement_mid_paths.png", dpi=180)
plt.close(fig)

print(f"wrote {len(summary)} EVENT_SUMMARY rows and 4 figures")
