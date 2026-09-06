#!/usr/bin/env python3
"""Figures for the delay and daily-response results.

Only aggregates are plotted, so the output is committable; no licensed row
reaches the repository.
"""
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import ppw

FIG = ppw.WORK / "figures"
HOR = [0, 1, 2, 5, 10]
MAPPINGS = ["reaction_date_session", "reaction_date_sameday",
            "reaction_date_nextday"]


def fig_delay():
    d = pd.read_parquet(ppw.OUT / "s3_delay.parquet")
    d = d[d.denominator_ok]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    w = d[d.freq == "weekly"]
    ax[0].hist(w[w.kind == "stock"].d1, bins=40, color="#4C72B0", alpha=.85)
    for v, c in zip(sorted(w[w.kind == "etf"].label.unique()),
                    ["#C44E52", "#55A868", "#8172B2"]):
        ax[0].axvline(w[(w.kind == "etf") & (w.label == v)].d1.median(),
                      color=c, lw=2, label=f"{v} (median)")
    ax[0].set_xlabel("D1, weekly"), ax[0].set_ylabel("stock-formations")
    ax[0].set_title("Hou-Moskowitz D1: stocks vs the three ETFs")
    ax[0].legend(fontsize=8)

    t = w.groupby([w.formation.dt.year, "kind"]).d1.median().unstack()
    t.plot(ax=ax[1], marker="o")
    ax[1].set_xlabel("formation year"), ax[1].set_ylabel("median D1")
    ax[1].set_title("Median weekly D1 by formation year")
    ax[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "fig1_delay.png", dpi=150)


def fig_response(cars):
    fig, ax = plt.subplots(1, 3, figsize=(14, 4.2), sharey=True)
    for a, mp in zip(ax, MAPPINGS):
        g = cars[mp]
        for dec in (1, 5, 10):
            a.plot(HOR, [g[h][dec] for h in HOR], marker="o",
                   label=f"decile {dec}")
        a.axhline(0, color="k", lw=.6)
        a.set_title(mp.replace("reaction_date_", "mapping: "))
        a.set_xlabel("trading days after mapping, h")
    ax[0].set_ylabel("mean CAR (bps)")
    ax[0].legend(fontsize=8)
    fig.suptitle("Source-stock earnings response by surprise decile "
                 "(all three reaction-date mappings)", y=1.02)
    fig.tight_layout()
    fig.savefig(FIG / "fig2_response.png", dpi=150, bbox_inches="tight")

    fig, a = plt.subplots(figsize=(6.5, 4.2))
    for mp in MAPPINGS:
        g = cars[mp]
        a.plot(HOR, [g[h][10] - g[h][1] for h in HOR], marker="o",
               label=mp.replace("reaction_date_", ""))
    a.set_xlabel("trading days after mapping, h")
    a.set_ylabel("D10 - D1 spread (bps)")
    a.set_title("Almost the whole response is at the first close")
    a.legend(fontsize=8), a.grid(alpha=.3)
    fig.tight_layout()
    fig.savefig(FIG / "fig3_spread.png", dpi=150)


def fig_precision():
    t = pd.read_parquet(ppw.OUT / "s5_planning_table.parquet")
    tr = pd.read_parquet(ppw.OUT / "s2_tracking_daily.parquet")
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    ax[0].plot(t.assumed_sd_bps, t.mde80_event, marker="o", label="event level")
    ax[0].plot(t.assumed_sd_bps, t.mde80_date, marker="s", label="date level")
    ax[0].plot(t.assumed_sd_bps, t.mde80_rows_independent, marker="^",
               ls="--", label="rows independent (not recommended)")
    ax[0].set_xlabel("ASSUMED residual SD (bps per event)")
    ax[0].set_ylabel("MDE80 (bps)")
    ax[0].set_title("Conditional planning grid (assumptions, not measurements)")
    ax[0].legend(fontsize=8), ax[0].grid(alpha=.3)

    for etf, g in tr.groupby("etf"):
        ax[1].hist(g.te_bps.clip(-40, 40), bins=60, histtype="step", lw=1.6,
                   label=f"{etf} (sd {g.te_bps.std():.1f} bps)")
    ax[1].set_xlabel("daily ETF minus approximate basket (bps)")
    ax[1].set_title("Measured daily basket error, never rescaled to intraday")
    ax[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "fig4_precision.png", dpi=150)


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    ev = pd.read_parquet(ppw.OUT / "s1_earnings_events.parquet")
    ev = ev.dropna(subset=["surprise_scaled"]).copy()
    ev["s"] = ev.surprise_scaled * 100

    fr = []
    for y in range(2018, 2024):
        d = pd.read_parquet(ppw.abspath(f"raw/crsp_dsf_{y}.parquet"),
                            columns=["permno", "date", "ret"])
        fr.append(d[d.permno.isin(set(ev.permno))])
    r = pd.concat(fr, ignore_index=True)
    r["date"] = pd.to_datetime(r.date)
    r["ret"] = pd.to_numeric(r.ret, errors="coerce")
    w = r.dropna(subset=["ret"]).drop_duplicates(["permno", "date"]).pivot_table(
        index="date", columns="permno", values="ret").astype("float64")
    cal, cols = w.index, {p: i for i, p in enumerate(w.columns)}
    C = np.cumprod(1.0 + np.nan_to_num(w.values), axis=0)

    ev["dec"] = pd.qcut(ev.s.rank(method="first"), 10, labels=False) + 1
    cars = {}
    for mp in MAPPINGS:
        d = ev.dropna(subset=[mp])
        i = cal.searchsorted(pd.DatetimeIndex(d[mp]))
        j = np.array([cols.get(p, -1) for p in d.permno])
        cars[mp] = {}
        for h in HOR:
            s, e = i - 1, i + h
            ok = (j >= 0) & (s >= 0) & (e < len(cal))
            y = np.full(len(d), np.nan)
            y[ok] = (C[e[ok], j[ok]] / C[s[ok], j[ok]] - 1) * 10000
            cars[mp][h] = pd.Series(y).groupby(d.dec.values).mean()

    fig_delay()
    fig_response(cars)
    fig_precision()
    print(f"  figures written to {FIG}")
    for p in sorted(FIG.glob("*.png")):
        print(f"    {p.name}  {p.stat().st_size/1024:.0f} KiB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
