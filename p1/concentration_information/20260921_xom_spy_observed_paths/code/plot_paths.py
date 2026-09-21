#!/usr/bin/env python3
"""Render the compact, derived primary-feed paths (no raw DBN input)."""
import csv
from pathlib import Path
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
rows = [r for r in csv.DictReader((ROOT / "PATHS.csv").open()) if r["anchor"] == "06:30_ET"]
x = [int(r["minute_from_anchor"]) for r in rows]
series = [
    ("SPY_mid_index", "SPY", "#3567a8", "-"),
    ("XOM_mid_index", "XOM", "#e6550d", "-"),
    ("CRSP_lagged_fixed_available_subset_mid_index", "6-stock lagged subset (XOM 67.6%)", "#31a354", "-"),
    ("CRSP_lagged_fixed_available_subset_ex_XOM_mid_index", "5-stock ex-XOM diagnostic", "#756bb1", "--"),
]
fig, ax = plt.subplots(figsize=(11, 6.4))
for col, label, color, style in series:
    y = [float(r[col]) if r[col] else float("nan") for r in rows]
    ax.plot(x, y, label=label, color=color, linestyle=style, linewidth=2)
ax.axhline(100, color="0.55", linewidth=0.8)
ax.axvline(0, color="0.25", linewidth=1)
ax.set(xlabel="Minutes from 06:30 ET operational anchor", ylabel="Midquote index (baseline at -5 minutes = 100)", title="XOM announcement window, 2023-01-31 — XNAS.ITCH bbo-1s (ts_recv)")
ax.text(0.01, 0.01, "Venue-specific BBO; not SIP NBBO. CRSP proxy is a retrospective, low-coverage diagnostic—not SPY NAV or actual holdings.", transform=ax.transAxes, fontsize=8, va="bottom")
ax.legend(loc="best", frameon=False)
ax.grid(axis="y", color="0.9")
fig.tight_layout()
fig.savefig(ROOT / "PATHS.png", dpi=180)
