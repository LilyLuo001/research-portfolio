#!/usr/bin/env python3
"""Plot aggregate ETF/basket timing outputs copied from SCC."""
from pathlib import Path
import csv
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "FIGURES"
FIG.mkdir(exist_ok=True)


def read(name):
    with (ROOT / name).open(newline="") as handle:
        return list(csv.DictReader(handle))


def value(row, key):
    return None if row[key] in ("", "None") else float(row[key])


paths = read("BASKET_PATHS.csv")
lags = read("LAG_DIAGNOSTICS.csv")
events = read("EVENT_RESULTS.csv")
variants = [(row["event_id"], row["anchor_utc"], f'{row["issuer"]} {row["anchor_label"]}') for row in events]

fig, axes = plt.subplots(2, 4, figsize=(17, 8), sharex=True)
for axis, (event_id, anchor, title) in zip(axes.flat, variants):
    rows = [r for r in paths if r["event_id"] == event_id and r["anchor_utc"] == anchor and r["feed"] == "XNAS.ITCH" and r["grid_shift_seconds"] == "0"]
    x = [int(r["minute"]) for r in rows]
    axis.plot(x, [1e4 * value(r, "etf_return") if value(r, "etf_return") is not None else None for r in rows], label="SPY", lw=1.5)
    axis.plot(x, [1e4 * value(r, "basket_return_subset") if value(r, "basket_return_subset") is not None else None for r in rows], label="Fixed basket", lw=1.3)
    axis.axvline(0, color="black", lw=.7); axis.axhline(0, color="grey", lw=.5)
    axis.set_title(title); axis.set_ylabel("bp from -5 min"); axis.grid(alpha=.2)
axes.flat[-1].axis("off"); axes.flat[0].legend(); fig.tight_layout()
fig.savefig(FIG / "ETF_BASKET_PATHS.png", dpi=180); plt.close(fig)

fig, axes = plt.subplots(2, 4, figsize=(17, 8), sharex=True)
for axis, (event_id, anchor, title) in zip(axes.flat, variants):
    for feed, shift, style in [("XNAS.ITCH", "0", "-"), ("XNAS.ITCH", "30", "--"), ("ARCX.PILLAR", "0", ":"), ("ARCX.PILLAR", "30", "-.")]:
        rows = [r for r in lags if r["event_id"] == event_id and r["anchor_utc"] == anchor and r["feed"] == feed and r["grid_shift_seconds"] == shift and r["window"] == "MAIN_-5_TO_30"]
        axis.plot([int(r["lag_minutes"]) for r in rows], [value(r, "correlation") for r in rows], style, label=f"{feed.split('.')[0]} {shift}s")
    axis.axvline(0, color="black", lw=.7); axis.set_title(title)
    axis.set_xlabel("lag (positive = SPY earlier)"); axis.set_ylabel("correlation"); axis.grid(alpha=.2)
axes.flat[-1].axis("off"); axes.flat[0].legend(fontsize=8); fig.tight_layout()
fig.savefig(FIG / "LAG_CURVES.png", dpi=180); plt.close(fig)

fig, axes = plt.subplots(2, 4, figsize=(17, 8), sharex=True)
for axis, (event_id, anchor, title) in zip(axes.flat, variants):
    rows = [r for r in paths if r["event_id"] == event_id and r["anchor_utc"] == anchor and r["feed"] == "XNAS.ITCH" and r["grid_shift_seconds"] == "0"]
    x = [int(r["minute"]) for r in rows]
    axis.plot(x, [1e4 * value(r, "issuer_return") if value(r, "issuer_return") is not None else None for r in rows], label="Issuer stock", lw=1.4)
    axis.plot(x, [1e4 * value(r, "issuer_implied_return") if value(r, "issuer_implied_return") is not None else None for r in rows], label="SPY-implied issuer", lw=1.1)
    axis.axvline(0, color="black", lw=.7); axis.axhline(0, color="grey", lw=.5)
    axis.set_title(title); axis.set_ylabel("bp from -5 min"); axis.grid(alpha=.2)
axes.flat[-1].axis("off"); axes.flat[0].legend(); fig.tight_layout()
fig.savefig(FIG / "IMPLIED_ISSUER_DIAGNOSTIC.png", dpi=180); plt.close(fig)
