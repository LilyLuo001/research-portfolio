#!/usr/bin/env python3
"""Exploratory one-second tier ablation with an unbalanced stock panel.

This is deliberately separate from the frozen five-second confirmatory pilot.
At each second, stock features are report-weighted over the available members
of each weight tier.  Available weight is renormalized and retained as an
explicit coverage feature.  Remaining feature gaps are imputed with medians
estimated on the training dates only and accompanied by missing indicators.
No forward-looking interpolation and no outcome values are used for imputation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


LAMBDAS = np.asarray([0.0, 0.01, 0.1, 1.0, 10.0, 100.0])
FEATURES = [
    "ret_0_100ms", "ret_100ms_1s", "ret_1s_5s",
    "flow_0_100ms", "flow_100ms_1s", "flow_1s_5s",
    "spread_bp", "bid_depth", "ask_depth", "volume_5s",
    "native_direction_share_5s",
]
TARGET = "y_1s_bp"
TIERS = ["high", "mid", "low"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def weighted_tier_panel(stock: pd.DataFrame, roster: pd.DataFrame, tier: str) -> pd.DataFrame:
    members = roster.loc[roster["weight_tier"] == tier, ["symbol", "report_weight"]].copy()
    members = members[members["symbol"].isin(stock["symbol"].unique())]
    total_weight = float(members["report_weight"].sum())
    if members.empty or total_weight <= 0:
        raise RuntimeError(f"no resolved members for tier {tier}")
    part = stock.merge(members, on="symbol", how="inner", validate="many_to_one")
    keys = ["date", "t_ns"]
    base = part[keys].drop_duplicates().set_index(keys).sort_index()
    out = pd.DataFrame(index=base.index)
    for feature in FEATURES:
        valid = np.isfinite(part[feature].to_numpy(float))
        numerator = np.where(valid, part[feature].to_numpy(float) * part["report_weight"].to_numpy(float), 0.0)
        denominator = np.where(valid, part["report_weight"].to_numpy(float), 0.0)
        tmp = part[keys].copy()
        tmp["numerator"] = numerator
        tmp["denominator"] = denominator
        agg = tmp.groupby(keys, sort=False)[["numerator", "denominator"]].sum()
        out[f"{tier}__{feature}"] = agg["numerator"] / agg["denominator"].replace(0.0, np.nan)
        out[f"{tier}__coverage_{feature}"] = agg["denominator"] / total_weight
    return out.reset_index()


def build_panel(features: pd.DataFrame, roster: pd.DataFrame, venue: str, shift: int) -> tuple[pd.DataFrame, dict]:
    f = features[(features["venue"] == venue) & (features["grid_shift_ms"] == shift)].copy()
    spy = f[f["symbol"] == "SPY"].copy()
    stock = f[f["symbol"] != "SPY"].copy()
    spy_cols = ["date", "t_ns", "minute_bin_5m", TARGET, *FEATURES]
    panel = spy[spy_cols].rename(columns={c: f"spy__{c}" for c in FEATURES})
    coverage = {}
    for tier in TIERS:
        tier_panel = weighted_tier_panel(stock, roster, tier)
        panel = panel.merge(tier_panel, on=["date", "t_ns"], how="left", validate="one_to_one")
        for feature in FEATURES:
            c = f"{tier}__coverage_{feature}"
            coverage[c] = {
                "mean": float(panel[c].mean()),
                "p05": float(panel[c].quantile(0.05)),
                "minimum": float(panel[c].min()),
            }
    return panel.sort_values(["date", "t_ns"]).reset_index(drop=True), coverage


def add_time_controls(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for k in range(1, 6):
        out[f"minute_bin_{k}"] = (out["minute_bin_5m"].astype(int) == k).astype(float)
    return out


def transform_with_train_imputation(train: pd.DataFrame, frames: dict[str, pd.DataFrame], columns: list[str]) -> tuple[dict[str, np.ndarray], dict]:
    raw_train = train[columns].to_numpy(float)
    with np.errstate(all="ignore"):
        medians = np.nanmedian(raw_train, axis=0)
    medians[~np.isfinite(medians)] = 0.0
    transformed = {}
    missing_rates = {}
    for name, frame in frames.items():
        raw = frame[columns].to_numpy(float)
        missing = ~np.isfinite(raw)
        filled = np.where(missing, medians, raw)
        transformed[name] = np.column_stack([filled, missing.astype(float)])
        missing_rates[name] = float(missing.mean())
    return transformed, {"train_medians": medians.tolist(), "missing_rates": missing_rates}


def standardize_fit(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale[~np.isfinite(scale) | (scale == 0)] = 1.0
    return mean, scale


def ridge_fit(x: np.ndarray, y: np.ndarray, mean: np.ndarray, scale: np.ndarray, lam: float) -> tuple[float, np.ndarray]:
    z = (x - mean) / scale
    zbar = z.mean(axis=0)
    ybar = float(y.mean())
    zc = z - zbar
    coef = np.linalg.pinv(zc.T @ zc / len(y) + lam * np.eye(z.shape[1])) @ (zc.T @ (y - ybar) / len(y))
    return ybar - float(zbar @ coef), coef


def predict(x: np.ndarray, mean: np.ndarray, scale: np.ndarray, intercept: float, coef: np.ndarray) -> np.ndarray:
    return intercept + ((x - mean) / scale) @ coef


def fit_spec(panel: pd.DataFrame, columns: list[str], split_dates: dict[str, set[str]]) -> tuple[dict, pd.DataFrame]:
    usable = panel[np.isfinite(panel[TARGET].to_numpy(float))].copy()
    frames = {name: usable[usable["date"].isin(dates)].copy() for name, dates in split_dates.items()}
    if min(len(frames[k]) for k in ("train", "valid", "test")) < 30:
        raise RuntimeError("fewer than 30 target-observed centers in a split")
    x, imputation = transform_with_train_imputation(frames["train"], frames, columns)
    y = {name: frame[TARGET].to_numpy(float) for name, frame in frames.items()}
    mean, scale = standardize_fit(x["train"])
    trace = []
    for lam in LAMBDAS:
        intercept, coef = ridge_fit(x["train"], y["train"], mean, scale, float(lam))
        pred = predict(x["valid"], mean, scale, intercept, coef)
        trace.append((float(np.mean((y["valid"] - pred) ** 2)), float(lam)))
    _, best_lambda = min(trace)
    fit_x = np.vstack([x["train"], x["valid"]])
    fit_y = np.concatenate([y["train"], y["valid"]])
    fit_mean, fit_scale = standardize_fit(fit_x)
    intercept, coef = ridge_fit(fit_x, fit_y, fit_mean, fit_scale, best_lambda)
    pred = predict(x["test"], fit_mean, fit_scale, intercept, coef)
    detail = frames["test"][["date", "t_ns"]].copy()
    detail["squared_error"] = (y["test"] - pred) ** 2
    return {
        "lambda": best_lambda,
        "raw_feature_count": len(columns),
        "model_feature_count_with_missing_indicators": int(x["train"].shape[1]),
        "n_train": len(frames["train"]), "n_valid": len(frames["valid"]), "n_test": len(frames["test"]),
        "sse": float(detail["squared_error"].sum()), "mse": float(detail["squared_error"].mean()),
        "imputation": imputation,
    }, detail


def bootstrap_gain(base_daily: pd.DataFrame, challenger_daily: pd.DataFrame, seed: int, reps: int = 2000) -> tuple[float, float]:
    joined = base_daily.merge(challenger_daily, on="date", suffixes=("_base", "_challenger"), validate="one_to_one")
    b = joined["squared_error_base"].to_numpy(float)
    c = joined["squared_error_challenger"].to_numpy(float)
    rng = np.random.default_rng(seed)
    draws = np.empty(reps)
    for i in range(reps):
        ix = rng.integers(0, len(joined), len(joined))
        draws[i] = 1.0 - c[ix].sum() / b[ix].sum()
    return float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", required=True)
    parser.add_argument("--roster", required=True)
    parser.add_argument("--dates", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    feature_path, roster_path, date_path = map(Path, (args.features, args.roster, args.dates))
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    features = pd.read_parquet(feature_path)
    roster = pd.read_csv(roster_path)
    dates = pd.read_csv(date_path, dtype={"date": str})
    features["date"] = features["date"].astype(str)
    split_dates = {name: set(dates.loc[dates["split"] == name, "date"]) for name in ("train", "valid", "test")}
    rows, daily_rows, coverage_rows, imputation_receipts = [], [], [], []
    time_cols = [f"minute_bin_{k}" for k in range(1, 6)]
    spy_cols = [f"spy__{c}" for c in FEATURES]
    tier_cols = {tier: [f"{tier}__{c}" for c in FEATURES] + [f"{tier}__coverage_{c}" for c in FEATURES] for tier in TIERS}
    for venue in sorted(features["venue"].unique()):
        for shift in sorted(features.loc[features["venue"] == venue, "grid_shift_ms"].unique()):
            panel, coverage = build_panel(features, roster, venue, int(shift))
            panel = add_time_controls(panel)
            specs = {"SPY_ONLY": spy_cols + time_cols, "ALL_TIERS": spy_cols + time_cols + sum(tier_cols.values(), [])}
            for tier in TIERS:
                specs[f"WITHOUT_{tier}"] = spy_cols + time_cols + sum((tier_cols[t] for t in TIERS if t != tier), [])
            fitted, detail = {}, {}
            for name, columns in specs.items():
                fitted[name], detail[name] = fit_spec(panel, columns, split_dates)
                imputation_receipts.append({"venue": venue, "grid_shift_ms": int(shift), "model": name, **fitted[name]["imputation"]})
            base_sse, full_sse = fitted["SPY_ONLY"]["sse"], fitted["ALL_TIERS"]["sse"]
            for name, result in fitted.items():
                if name == "SPY_ONLY":
                    reference = "SPY_ONLY"
                    gain = 0.0
                    ci_low = ci_high = np.nan
                elif name == "ALL_TIERS":
                    reference = "SPY_ONLY"
                    gain = 1.0 - result["sse"] / base_sse
                    bday = detail["SPY_ONLY"].groupby("date", as_index=False)["squared_error"].sum()
                    cday = detail[name].groupby("date", as_index=False)["squared_error"].sum()
                    ci_low, ci_high = bootstrap_gain(bday, cday, 20260922 + int(shift))
                else:
                    reference = name
                    gain = 1.0 - full_sse / result["sse"]
                    bday = detail[name].groupby("date", as_index=False)["squared_error"].sum()
                    cday = detail["ALL_TIERS"].groupby("date", as_index=False)["squared_error"].sum()
                    ci_low, ci_high = bootstrap_gain(bday, cday, 20260922 + int(shift))
                rows.append({
                    "venue": venue, "grid_shift_ms": int(shift), "horizon": "1s", "model": name,
                    "comparison_reference": reference, "G": gain, "bootstrap_ci_low": ci_low,
                    "bootstrap_ci_high": ci_high, **{k: v for k, v in result.items() if k != "imputation"},
                })
                for date, value in detail[name].groupby("date")["squared_error"].sum().items():
                    daily_rows.append({"venue": venue, "grid_shift_ms": int(shift), "model": name, "date": date, "sse": float(value)})
            for column, values in coverage.items():
                coverage_rows.append({"venue": venue, "grid_shift_ms": int(shift), "coverage_feature": column, **values})
    pd.DataFrame(rows).to_csv(out / "EXPLORATORY_GROUP_ABLATION.csv", index=False)
    pd.DataFrame(daily_rows).to_csv(out / "EXPLORATORY_GROUP_ABLATION_DAILY.csv", index=False)
    pd.DataFrame(coverage_rows).to_csv(out / "EXPLORATORY_TIER_COVERAGE.csv", index=False)
    receipt = {
        "status": "EXPLORATORY_COMPLETE", "role": "HYPOTHESIS_GENERATION_NOT_FINAL_ADJUDICATION",
        "horizon": "1s", "panel": "UNBALANCED_REPORT_WEIGHT_RENORMALIZED_WITH_COVERAGE_FEATURES",
        "imputation": "TRAIN_DATE_MEDIANS_PLUS_MISSING_INDICATORS; NO_FORWARD_OR_FUTURE_INTERPOLATION",
        "features": str(feature_path), "roster": str(roster_path), "dates": str(date_path),
        "source_hashes": {"roster": sha256(roster_path), "dates": sha256(date_path),
                          "code": sha256(Path(__file__))},
        "rows": len(rows), "minimum_required_split_centers": 30,
        "imputation_receipts": imputation_receipts,
    }
    (out / "EXPLORATORY_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
