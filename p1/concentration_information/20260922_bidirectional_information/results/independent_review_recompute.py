#!/usr/bin/env python3
"""Read-only arithmetic checks for the independent bidirectional-pilot review.

This script uses only exported aggregate CSVs. It does not import the estimator
or summarizer and does not read or write SCC data.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
PRIMARY = ("XNAS.ITCH", 0, "5s")
SPOT_STOCKS = ("AAPL", "CMI", "NWSA", "XYL")


def gain_by_stock(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.groupby("symbol", as_index=False).agg(
        sse_baseline=("sse_baseline", "sum"),
        sse_full=("sse_full", "sum"),
        n_test=("n", "sum"),
        test_dates=("date", "nunique"),
    )
    out["G"] = 1.0 - out["sse_full"] / out["sse_baseline"]
    return out


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    good = np.isfinite(values) & np.isfinite(weights) & (weights >= 0)
    return float(np.average(values[good], weights=weights[good]))


def bootstrap(frame: pd.DataFrame, weights: dict[str, float]) -> tuple[float, float, float, float]:
    dates = sorted(frame["date"].astype(str).unique())
    rng = np.random.default_rng(20260922)
    equal, weighted = [], []
    for _ in range(1000):
        sampled = rng.choice(dates, size=len(dates), replace=True)
        stock = gain_by_stock(pd.concat([frame[frame["date"] == d] for d in sampled], ignore_index=True))
        equal.append(float(stock["G"].mean()))
        weighted.append(weighted_mean(stock["G"], stock["symbol"].map(weights).astype(float)))
    return (
        float(np.quantile(equal, 0.025)),
        float(np.quantile(equal, 0.975)),
        float(np.quantile(weighted, 0.025)),
        float(np.quantile(weighted, 0.975)),
    )


def main() -> None:
    gains = pd.read_csv(HERE / "PREDICTIVE_GAINS.csv")
    daily = pd.read_csv(HERE / "DAILY_LOSS_SUMMARY.csv", dtype={"date": str})
    aggregate = pd.read_csv(HERE / "AGGREGATE_GAINS.csv")
    roster = pd.read_csv(HERE / "SAFE_ROSTER.csv")
    ablation = pd.read_csv(HERE / "GROUP_ABLATION.csv")
    weights = roster.set_index("symbol")["report_weight"].astype(float).to_dict()

    checks: dict[str, object] = {}
    checks["row_counts"] = {
        "predictive_gains": len(gains),
        "daily_loss": len(daily),
        "group_ablation": len(ablation),
        "expected_predictive": 2 * 2 * 23 * 2 * 3,
        "expected_daily": 2 * 2 * 23 * 2 * 3 * 8,
    }
    checks["daily_identity_max_abs"] = float(
        np.max(np.abs(daily["loss_difference"] - (daily["sse_baseline"] - daily["sse_full"])))
    )

    merged_rows = []
    for key, frame in daily.groupby(["venue", "grid_shift_ms", "symbol", "direction", "horizon"]):
        sb = float(frame["sse_baseline"].sum())
        sf = float(frame["sse_full"].sum())
        merged_rows.append(dict(zip(["venue", "grid_shift_ms", "symbol", "direction", "horizon"], key)) | {
            "n_test_re": int(frame["n"].sum()),
            "sse_baseline_re": sb,
            "sse_full_re": sf,
            "G_re": 1.0 - sf / sb,
        })
    merged = gains.merge(pd.DataFrame(merged_rows), on=["venue", "grid_shift_ms", "symbol", "direction", "horizon"], validate="one_to_one")
    checks["pairwise_max_abs"] = {
        "sse_baseline": float(np.max(np.abs(merged["sse_baseline"] - merged["sse_baseline_re"]))),
        "sse_full": float(np.max(np.abs(merged["sse_full"] - merged["sse_full_re"]))),
        "G": float(np.max(np.abs(merged["G"] - merged["G_re"]))),
        "n_test": int(np.max(np.abs(merged["n_test"] - merged["n_test_re"]))),
    }

    venue, shift, horizon = PRIMARY
    spot = merged[
        (merged["venue"] == venue)
        & (merged["grid_shift_ms"] == shift)
        & (merged["horizon"] == horizon)
        & merged["symbol"].isin(SPOT_STOCKS)
    ]
    checks["primary_spot_checks"] = spot[[
        "symbol", "weight_tier", "direction", "n_test_re",
        "sse_baseline_re", "sse_full_re", "G_re",
    ]].sort_values(["symbol", "direction"]).to_dict("records")

    aggregate_checks = []
    key_cols = ["venue", "grid_shift_ms", "direction", "horizon"]
    for key, frame in daily.groupby(key_cols):
        stock = gain_by_stock(frame)
        ci = bootstrap(frame, weights)
        row = aggregate
        for col, value in zip(key_cols, key):
            row = row[row[col] == value]
        assert len(row) == 1
        row = row.iloc[0]
        aggregate_checks.append(dict(zip(key_cols, key)) | {
            "equal_G_re": float(stock["G"].mean()),
            "equal_ci_low_re": ci[0],
            "equal_ci_high_re": ci[1],
            "weighted_G_re": weighted_mean(stock["G"], stock["symbol"].map(weights).astype(float)),
            "weighted_ci_low_re": ci[2],
            "weighted_ci_high_re": ci[3],
            "max_abs_vs_export": float(max(
                abs(float(row["equal_stock_G"]) - float(stock["G"].mean())),
                abs(float(row["equal_ci_low"]) - ci[0]),
                abs(float(row["equal_ci_high"]) - ci[1]),
                abs(float(row["report_weighted_G"]) - weighted_mean(stock["G"], stock["symbol"].map(weights).astype(float))),
                abs(float(row["weighted_ci_low"]) - ci[2]),
                abs(float(row["weighted_ci_high"]) - ci[3]),
            )),
        })
    aggregate_checks = pd.DataFrame(aggregate_checks)
    checks["aggregate_max_abs_vs_export"] = float(aggregate_checks["max_abs_vs_export"].max())
    checks["primary_aggregate"] = aggregate_checks[
        (aggregate_checks["venue"] == venue)
        & (aggregate_checks["grid_shift_ms"] == shift)
        & (aggregate_checks["horizon"].isin(["1s", "5s"]))
    ].sort_values(["horizon", "direction"]).to_dict("records")

    checks["primary_pair_support"] = gains[
        (gains["venue"] == venue)
        & (gains["grid_shift_ms"] == shift)
        & (gains["horizon"] == horizon)
    ].groupby("direction")["n_test"].agg(["min", "median", "max"]).to_dict("index")
    checks["ablation_support"] = ablation.groupby(["venue", "grid_shift_ms"])[
        ["n_train", "n_valid", "n_test"]
    ].first().reset_index().to_dict("records")
    checks["xnas_500_ablation_present"] = bool(
        ((ablation["venue"] == "XNAS.ITCH") & (ablation["grid_shift_ms"] == 500)).any()
    )
    print(json.dumps(checks, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
