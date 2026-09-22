#!/usr/bin/env python3
"""Create non-reconstructive aggregate tables and at most four pilot figures."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
import pandas as pd

DEGRADED_DATES = {"2023-09-22", "2023-11-21", "2023-12-07"}


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    good = np.isfinite(values) & np.isfinite(weights) & (weights >= 0)
    return float(np.average(values[good], weights=weights[good])) if good.any() and weights[good].sum() > 0 else np.nan


def gain_by_stock(frame: pd.DataFrame) -> pd.DataFrame:
    x = frame.groupby("symbol", as_index=False).agg(sse_baseline=("sse_baseline", "sum"), sse_full=("sse_full", "sum"))
    x["G"] = np.where(x.sse_baseline > 0, 1 - x.sse_full / x.sse_baseline, np.nan)
    return x


def bootstrap(frame: pd.DataFrame, weights: dict[str, float], reps: int = 1000) -> tuple[float, float, float, float]:
    compact = frame.groupby(["date", "symbol"], as_index=False).agg(
        sse_baseline=("sse_baseline", "sum"), sse_full=("sse_full", "sum")
    )
    days = sorted(compact.date.astype(str).unique())
    symbols = sorted(compact.symbol.unique())
    baseline = compact.pivot(index="date", columns="symbol", values="sse_baseline").reindex(index=days, columns=symbols).to_numpy(float)
    full = compact.pivot(index="date", columns="symbol", values="sse_full").reindex(index=days, columns=symbols).to_numpy(float)
    rng = np.random.default_rng(20260922)
    counts = np.vstack([np.bincount(rng.integers(0, len(days), len(days)), minlength=len(days)) for _ in range(reps)])
    sb, sf = counts @ baseline, counts @ full
    gains = np.where(sb > 0, 1 - sf / sb, np.nan)
    equal = np.nanmean(gains, axis=1)
    weight = np.asarray([weights.get(s, np.nan) for s in symbols], float)
    valid = np.isfinite(gains) & np.isfinite(weight)[None, :]
    weighted = np.nansum(gains * weight[None, :], axis=1) / np.sum(valid * weight[None, :], axis=1)
    return tuple(float(x) for x in (
        np.nanquantile(equal, .025), np.nanquantile(equal, .975),
        np.nanquantile(weighted, .025), np.nanquantile(weighted, .975),
    ))


def adjacent_two_day_bootstrap(frame: pd.DataFrame, reps: int = 1000) -> tuple[float, float]:
    compact = frame.groupby(["date", "symbol"], as_index=False).agg(
        sse_baseline=("sse_baseline", "sum"), sse_full=("sse_full", "sum")
    )
    days = sorted(compact.date.astype(str).unique())
    symbols = sorted(compact.symbol.unique())
    baseline = compact.pivot(index="date", columns="symbol", values="sse_baseline").reindex(index=days, columns=symbols).to_numpy(float)
    full = compact.pivot(index="date", columns="symbol", values="sse_full").reindex(index=days, columns=symbols).to_numpy(float)
    if len(days) % 2:
        return np.nan, np.nan
    baseline, full = baseline.reshape(-1, 2, len(symbols)).sum(axis=1), full.reshape(-1, 2, len(symbols)).sum(axis=1)
    rng = np.random.default_rng(20260923)
    counts = np.vstack([np.bincount(rng.integers(0, len(baseline), len(baseline)), minlength=len(baseline)) for _ in range(reps)])
    sb, sf = counts @ baseline, counts @ full
    gains = np.where(sb > 0, 1 - sf / sb, np.nan)
    equal = np.nanmean(gains, axis=1)
    return float(np.nanquantile(equal, .025)), float(np.nanquantile(equal, .975))


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = list(rows[0])
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fields, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def make_plots(out: Path, gains: pd.DataFrame, aggregate: pd.DataFrame, daily: pd.DataFrame, ablation: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt

    main = aggregate[(aggregate.horizon == "5s") & (aggregate.grid_shift_ms == 0)].copy()
    fig, ax = plt.subplots(figsize=(8, 4.5))
    labels, points, lows, highs = [], [], [], []
    for _, r in main.sort_values(["venue", "direction"]).iterrows():
        labels.append(f"{r.venue}\n{r.direction}")
        points.append(r.equal_stock_G); lows.append(r.equal_ci_low); highs.append(r.equal_ci_high)
    x = np.arange(len(points)); ax.errorbar(x, points, yerr=[np.array(points)-lows, np.array(highs)-points], fmt="o", capsize=4)
    ax.axhline(0, color="black", lw=.8); ax.set_xticks(x, labels); ax.set_ylabel("Out-of-sample incremental G")
    ax.set_title("Bidirectional predictive gain, equal-stock view"); fig.tight_layout(); fig.savefig(out / "FIG1_AGGREGATE_GAINS.png", dpi=180); plt.close(fig)

    g = gains[(gains.horizon == "5s") & (gains.grid_shift_ms == 0) & (gains.venue == "XNAS.ITCH")].copy()
    fig, axes = plt.subplots(1, 2, figsize=(11, 6), sharey=True)
    for ax, direction in zip(axes, ("ETF_TO_STOCK", "STOCK_TO_ETF")):
        z = g[g.direction == direction].sort_values("G")
        ax.scatter(z.G, np.arange(len(z)), c=z.report_weight, cmap="viridis", s=28)
        ax.axvline(0, color="black", lw=.8); ax.set_yticks(np.arange(len(z)), z.symbol); ax.set_title(direction); ax.set_xlabel("G")
    fig.suptitle("Stock-level five-second predictive gains"); fig.tight_layout(); fig.savefig(out / "FIG2_STOCK_GAINS.png", dpi=180); plt.close(fig)

    d = daily[(daily.horizon == "5s") & (daily.grid_shift_ms == 0)].groupby(["venue", "direction", "date"], as_index=False).loss_difference.sum()
    fig, ax = plt.subplots(figsize=(10, 4.5))
    for (venue, direction), z in d.groupby(["venue", "direction"]):
        ax.plot(z.date, z.loss_difference, marker="o", label=f"{venue} {direction}")
    ax.axhline(0, color="black", lw=.8); ax.tick_params(axis="x", rotation=45); ax.set_ylabel("SSE baseline − full"); ax.legend(fontsize=8); ax.set_title("Whole-date stability"); fig.tight_layout(); fig.savefig(out / "FIG3_DAILY_STABILITY.png", dpi=180); plt.close(fig)

    a = ablation.copy()
    fig, ax = plt.subplots(figsize=(9, 4.5))
    support = a.groupby(["venue", "grid_shift_ms"], as_index=False).n_test.min()
    expected = pd.MultiIndex.from_product(
        [["ARCX.PILLAR", "XNAS.ITCH"], [0, 500]], names=["venue", "grid_shift_ms"]
    ).to_frame(index=False)
    support = expected.merge(support, how="left", on=["venue", "grid_shift_ms"]).fillna({"n_test": 0})
    labels = [f"{r.venue}\nshift {int(r.grid_shift_ms)}ms" for _, r in support.iterrows()]
    ax.bar(np.arange(len(support)), support.n_test, color="slategray")
    ax.set_xticks(np.arange(len(support)), labels); ax.set_ylabel("Complete-case test centers")
    ax.set_title("Group ablation support (economic values not certified)")
    fig.tight_layout(); fig.savefig(out / "FIG4_GROUP_ABLATION_SUPPORT.png", dpi=180); plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", required=True, type=Path)
    ap.add_argument("--roster", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(); args.out.mkdir(parents=True, exist_ok=True)
    gains = pd.read_csv(args.model_dir / "PREDICTIVE_GAINS.csv")
    daily = pd.read_csv(args.model_dir / "DAILY_LOSS_SUMMARY.csv", dtype={"date": str})
    ablation = pd.read_csv(args.model_dir / "GROUP_ABLATION.csv")
    roster = pd.read_csv(args.roster)
    weights = roster.set_index("symbol").report_weight.astype(float).to_dict()
    rows = []
    keys = ["venue", "grid_shift_ms", "direction", "horizon"]
    for key, frame in daily.groupby(keys):
        gs = gain_by_stock(frame)
        ci = bootstrap(frame, weights)
        block_ci = adjacent_two_day_bootstrap(frame)
        degraded = DEGRADED_DATES if key[0] == "ARCX.PILLAR" else set()
        no_bad = gain_by_stock(frame[~frame.date.astype(str).isin(degraded)])
        off = gains.copy()
        for column, value in zip(keys, key):
            off = off[off[column] == value]
        off = gs[["symbol"]].merge(off[["symbol", "offday_G"]], on="symbol", how="left")
        rows.append(dict(zip(keys, key)) | {
            "stocks": len(gs), "test_dates": frame.date.nunique(),
            "equal_stock_G": float(gs.G.mean()), "equal_ci_low": ci[0], "equal_ci_high": ci[1],
            "report_weighted_G": weighted_mean(gs.G, gs.symbol.map(weights).astype(float)),
            "weighted_ci_low": ci[2], "weighted_ci_high": ci[3],
            "adjacent_two_day_ci_low": block_ci[0], "adjacent_two_day_ci_high": block_ci[1],
            "equal_stock_G_without_degraded_dates": float(no_bad.G.mean()) if len(no_bad) else np.nan,
            "mean_offday_G": float(off.offday_G.mean()),
        })
    write_csv(args.out / "AGGREGATE_GAINS.csv", rows)
    aggregate = pd.DataFrame(rows)
    make_plots(args.out, gains, aggregate, daily, ablation)
    print({"aggregate_rows": len(rows), "figures": 4})


if __name__ == "__main__":
    main()
