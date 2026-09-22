#!/usr/bin/env python3
"""Combine SCC cell outputs and compute synchronized date-level inference."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


MODELS = ("A0", "A1", "A2", "A3", "A4", "A5")
CONTRASTS = {
    "A0_TO_A1_SPY_QUOTE_BEFORE_C": ("A0", "A1"),
    "A2_TO_A3_SPY_QUOTE_AFTER_C": ("A2", "A3"),
    "A3_TO_A5_SPY_TRADE_AFTER_CQ": ("A3", "A5"),
    "A2_TO_A5_COMPLETE_SPY_AFTER_C": ("A2", "A5"),
    "A0_TO_A2_CASH_TRADES_BEFORE_Q": ("A0", "A2"),
    "A1_TO_A3_CASH_TRADES_AFTER_Q": ("A1", "A3"),
    "A0_TO_A4_COMPLETE_SPY_BEFORE_C": ("A0", "A4"),
    "A4_TO_A5_CASH_TRADES_AFTER_SPY": ("A4", "A5"),
}
SEED = 20260922


def load_parts(root: Path, sample: str):
    receipts = sorted(root.glob("*/CELL_RECEIPT.json"))
    if len(receipts) != 4:
        raise RuntimeError(f"{sample}: expected four cell receipts under {root}, got {len(receipts)}")
    cells, model_frames, daily_frames, trace_frames = [], [], [], []
    for receipt_path in receipts:
        receipt = json.loads(receipt_path.read_text())
        cell = (receipt["venue"], int(receipt["grid_shift_ms"]))
        cells.append(cell)
        model_frames.append(pd.read_csv(receipt_path.parent / "MODEL_COMPARISON_CELL.csv"))
        daily_frames.append(pd.read_csv(receipt_path.parent / "DAILY_LOSS_CELL.csv", dtype={"date": str}))
        trace_path = receipt_path.parent / "VALIDATION_TRACE_CELL.csv"
        if trace_path.exists():
            trace_frames.append(pd.read_csv(trace_path))
    if len(set(cells)) != 4:
        raise RuntimeError(f"{sample}: duplicate/missing cells {cells}")
    models = pd.concat(model_frames, ignore_index=True); models["sample"] = sample
    daily = pd.concat(daily_frames, ignore_index=True); daily["sample"] = sample
    traces = pd.concat(trace_frames, ignore_index=True) if trace_frames else pd.DataFrame()
    if not traces.empty:
        traces["sample"] = sample
    return models, daily, traces, receipts


def wide_models(models: pd.DataFrame) -> pd.DataFrame:
    keys = ["sample", "venue", "grid_shift_ms", "fit_spec", "symbol"]
    sse = models.pivot(index=keys, columns="model", values="sse").reset_index()
    n = models.groupby(keys, as_index=False).n_test.first().rename(columns={"n_test": "n_test"})
    out = sse.merge(n, on=keys, validate="one_to_one")
    for label, (baseline, full) in CONTRASTS.items():
        out["G_" + label] = 1.0 - out[full] / out[baseline]
        out["LOSS_CHANGE_" + label] = out[baseline] - out[full]
    out["Q_GAIN_AFTER_MINUS_BEFORE_C"] = (out["G_A2_TO_A3_SPY_QUOTE_AFTER_C"]
                                            - out["G_A0_TO_A1_SPY_QUOTE_BEFORE_C"])
    return out


def wide_daily(daily: pd.DataFrame) -> pd.DataFrame:
    keys = ["sample", "venue", "grid_shift_ms", "fit_spec", "symbol", "date"]
    sse = daily.pivot(index=keys, columns="model", values="sse").reset_index()
    n = daily.groupby(keys, as_index=False).n.first()
    return sse.merge(n, on=keys, validate="one_to_one")


def metric_from_totals(totals: dict[str, np.ndarray], label: str) -> np.ndarray:
    if label == "Q_GAIN_AFTER_MINUS_BEFORE_C":
        return (1.0 - totals["A3"] / totals["A2"]) - (1.0 - totals["A1"] / totals["A0"])
    baseline, full = CONTRASTS[label]
    return 1.0 - totals[full] / totals[baseline]


def summarize(daily_wide: pd.DataFrame, weights: dict[str, float], reps: int = 2000):
    labels = list(CONTRASTS) + ["Q_GAIN_AFTER_MINUS_BEFORE_C"]
    summaries, sensitivity = [], []
    for (sample, fit_spec), all_group in daily_wide.groupby(["sample", "fit_spec"]):
        cells = sorted(set(zip(all_group.venue, all_group.grid_shift_ms)))
        date_sets = [set(g.date) for _, g in all_group.groupby(["venue", "grid_shift_ms", "symbol"])]
        dates = sorted(set.intersection(*date_sets))
        if not dates:
            raise RuntimeError(f"no complete dates for {sample}/{fit_spec}")
        symbols = sorted(all_group.symbol.unique())
        w = np.asarray([weights[x] for x in symbols], float); w /= w.sum()
        matrices = {}
        for cell in cells:
            group = all_group[(all_group.venue == cell[0]) & (all_group.grid_shift_ms == cell[1])]
            matrices[cell] = {m: group.pivot(index="symbol", columns="date", values=m)
                .reindex(index=symbols, columns=dates).to_numpy(float) for m in MODELS}
            if any(not np.isfinite(x).all() for x in matrices[cell].values()):
                raise RuntimeError(f"incomplete common support for {sample}/{fit_spec}/{cell}")
        rng = np.random.default_rng(SEED)
        draws = rng.integers(0, len(dates), size=(reps, len(dates)))
        for label in labels:
            point_cells, weighted_cells, boot_equal_cells, boot_weight_cells = [], [], [], []
            for cell in cells:
                mats = matrices[cell]
                totals = {m: mats[m].sum(axis=1) for m in MODELS}
                point = metric_from_totals(totals, label)
                point_cells.append(float(point.mean())); weighted_cells.append(float(point @ w))
                boot = []
                for draw in draws:
                    draw_totals = {m: mats[m][:, draw].sum(axis=1) for m in MODELS}
                    boot.append(metric_from_totals(draw_totals, label))
                boot = np.asarray(boot)
                boot_equal_cells.append(boot.mean(axis=1)); boot_weight_cells.append(boot @ w)
                summaries.append({"sample": sample, "fit_spec": fit_spec, "scope": "CELL",
                    "venue": cell[0], "grid_shift_ms": cell[1], "contrast": label,
                    "stocks": len(symbols), "dates": len(dates), "equal_stock_metric": float(point.mean()),
                    "report_weight_metric": float(point @ w),
                    "equal_ci_low": float(np.quantile(boot.mean(axis=1), .025)),
                    "equal_ci_high": float(np.quantile(boot.mean(axis=1), .975)),
                    "report_weight_ci_low": float(np.quantile(boot @ w, .025)),
                    "report_weight_ci_high": float(np.quantile(boot @ w, .975))})
            boot_equal = np.mean(np.asarray(boot_equal_cells), axis=0)
            boot_weight = np.mean(np.asarray(boot_weight_cells), axis=0)
            summaries.append({"sample": sample, "fit_spec": fit_spec, "scope": "ALL_CELLS_EQUAL",
                "venue": "ALL", "grid_shift_ms": -1, "contrast": label, "stocks": len(symbols),
                "dates": len(dates), "equal_stock_metric": float(np.mean(point_cells)),
                "report_weight_metric": float(np.mean(weighted_cells)),
                "equal_ci_low": float(np.quantile(boot_equal, .025)),
                "equal_ci_high": float(np.quantile(boot_equal, .975)),
                "report_weight_ci_low": float(np.quantile(boot_weight, .025)),
                "report_weight_ci_high": float(np.quantile(boot_weight, .975))})
            for omitted in dates:
                keep = [i for i, date in enumerate(dates) if date != omitted]
                eq, rw = [], []
                for cell in cells:
                    mats = matrices[cell]
                    totals = {m: mats[m][:, keep].sum(axis=1) for m in MODELS}
                    point = metric_from_totals(totals, label); eq.append(float(point.mean())); rw.append(float(point @ w))
                sensitivity.append({"sample": sample, "fit_spec": fit_spec, "contrast": label,
                    "omitted_date": omitted, "remaining_dates": len(keep),
                    "equal_stock_metric": float(np.mean(eq)), "report_weight_metric": float(np.mean(rw))})
    return pd.DataFrame(summaries), pd.DataFrame(sensitivity)


def figures(summary: pd.DataFrame, daily: pd.DataFrame, out: Path) -> None:
    chosen = ["A0_TO_A1_SPY_QUOTE_BEFORE_C", "A2_TO_A3_SPY_QUOTE_AFTER_C",
              "A3_TO_A5_SPY_TRADE_AFTER_CQ", "A2_TO_A5_COMPLETE_SPY_AFTER_C"]
    x = summary[(summary.fit_spec == "OWN_LAMBDA") & (summary.scope == "ALL_CELLS_EQUAL")
                & summary.contrast.isin(chosen)].copy()
    samples = list(dict.fromkeys(x["sample"])); width = .35; positions = np.arange(len(chosen))
    fig, ax = plt.subplots(figsize=(10, 5))
    for i, sample in enumerate(samples):
        z = x[x["sample"] == sample].set_index("contrast").reindex(chosen)
        ax.bar(positions + (i - (len(samples)-1)/2)*width, z.equal_stock_metric, width, label=sample)
    ax.axhline(0, color="black", linewidth=.8); ax.set_xticks(positions)
    ax.set_xticklabels(["SPY Q\nbefore C", "SPY Q\nafter C", "SPY P\nafter C+Q", "SPY Q+P\nafter C"])
    ax.set_ylabel("Equal-stock G (four cells averaged)"); ax.legend(); fig.tight_layout()
    fig.savefig(out / "FIG1_SPY_QUOTE_TRADE_INCREMENT.png", dpi=180); plt.close(fig)

    d = daily[(daily.fit_spec == "OWN_LAMBDA")].copy()
    rows = []
    for (sample, date, venue, shift), g in d.groupby(["sample", "date", "venue", "grid_shift_ms"]):
        rows.append({"sample": sample, "date": date, "venue": venue, "grid_shift_ms": shift,
            "G": 1.0 - g.A5.sum() / g.A2.sum()})
    plot = pd.DataFrame(rows).groupby(["sample", "date"], as_index=False).G.mean()
    fig, ax = plt.subplots(figsize=(11, 5))
    for sample, g in plot.groupby("sample"):
        ax.plot(np.arange(len(g)), g.G, marker="o", label=sample)
    ax.axhline(0, color="black", linewidth=.8); ax.set_ylabel("Daily A2→A5 G (four cells averaged)")
    ax.set_xlabel("Chronological test date within sample"); ax.legend(); fig.tight_layout()
    fig.savefig(out / "FIG2_PRIMARY_DAILY_G.png", dpi=180); plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts-2023", required=True, type=Path)
    ap.add_argument("--parts-2024", type=Path)
    ap.add_argument("--roster", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(); args.out.mkdir(parents=True, exist_ok=True)
    model_frames, daily_frames, trace_frames, receipt_paths = [], [], [], []
    m, d, t, r = load_parts(args.parts_2023, "2023_HISTORICAL"); model_frames.append(m); daily_frames.append(d); receipt_paths += r
    if not t.empty: trace_frames.append(t)
    if args.parts_2024 is not None:
        m, d, t, r = load_parts(args.parts_2024, "2024_EXTERNAL"); model_frames.append(m); daily_frames.append(d); receipt_paths += r
        if not t.empty: trace_frames.append(t)
    models = pd.concat(model_frames, ignore_index=True); daily = pd.concat(daily_frames, ignore_index=True)
    comparison = wide_models(models); daily_wide = wide_daily(daily)
    weights = pd.read_csv(args.roster).set_index("symbol").report_weight.astype(float).to_dict()
    summary, sensitivity = summarize(daily_wide, weights)
    comparison[comparison["sample"] == "2023_HISTORICAL"].to_csv(args.out / "MODEL_COMPARISON_2023.csv", index=False)
    if "2024_EXTERNAL" in set(comparison["sample"]):
        comparison[comparison["sample"] == "2024_EXTERNAL"].to_csv(args.out / "MODEL_COMPARISON_2024.csv", index=False)
    daily_wide.to_csv(args.out / "DAILY_LOSS_DIFFERENCES.csv", index=False)
    if trace_frames:
        pd.concat(trace_frames, ignore_index=True).sort_values(
            ["venue", "grid_shift_ms", "model", "symbol", "lambda"]).to_csv(
                args.out / "VALIDATION_TRACE_2023.csv", index=False)
    summary.to_csv(args.out / "PAIRED_CONTRASTS.csv", index=False)
    sensitivity.to_csv(args.out / "DATE_SENSITIVITY.csv", index=False)
    figures(summary, daily_wide, args.out)
    receipt = {"status": "COMPLETE_SOURCE_ATTRIBUTION_SUMMARY", "samples": sorted(comparison["sample"].unique()),
        "fit_specs": sorted(comparison.fit_spec.unique()), "stocks": int(comparison.symbol.nunique()),
        "cells": int(comparison[["venue", "grid_shift_ms"]].drop_duplicates().shape[0]),
        "bootstrap_reps": 2000, "bootstrap_seed": SEED,
        "common_date_draw_matrix_across_all_cells_models_stocks": True,
        "cell_receipts": [str(x) for x in receipt_paths], "raw_or_prediction_rows_exported": False}
    (args.out / "SUMMARY_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
