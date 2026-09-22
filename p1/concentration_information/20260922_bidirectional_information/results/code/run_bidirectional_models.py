#!/usr/bin/env python3
"""Estimate the bounded ETF-stock bidirectional prediction design.

The script consumes SCC-resident, causally constructed security-second features.
It exports aggregate losses and predictive gains only; no quote or price levels.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


LAMBDAS = np.asarray([0.0, 0.01, 0.1, 1.0, 10.0, 100.0])
RETURN_FEATURES = ["ret_0_100ms", "ret_100ms_1s", "ret_1s_5s"]
FLOW_FEATURES = ["flow_0_100ms", "flow_100ms_1s", "flow_1s_5s"]
STATE_FEATURES = [
    "spread_bp", "bid_depth", "ask_depth", "volume_5s",
    "native_direction_share_5s",
]
OWN_FEATURES = RETURN_FEATURES + FLOW_FEATURES + STATE_FEATURES
HORIZONS = {"100ms": "y_100ms_bp", "1s": "y_1s_bp", "5s": "y_5s_bp"}
PRIMARY_HORIZON = "5s"


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty output: {path}")
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    return pd.read_csv(path)


@dataclass
class Scaler:
    mean: np.ndarray
    scale: np.ndarray

    @classmethod
    def fit(cls, x: np.ndarray) -> "Scaler":
        mean = np.mean(x, axis=0)
        scale = np.std(x, axis=0)
        scale[~np.isfinite(scale) | (scale == 0)] = 1.0
        return cls(mean, scale)

    def apply(self, x: np.ndarray) -> np.ndarray:
        return (x - self.mean) / self.scale


@dataclass
class RidgeModel:
    scaler: Scaler
    intercept: float
    coef: np.ndarray
    lam: float

    def predict(self, x: np.ndarray) -> np.ndarray:
        return self.intercept + self.scaler.apply(x) @ self.coef


def fit_ridge(x: np.ndarray, y: np.ndarray, scaler: Scaler, lam: float) -> RidgeModel:
    z = scaler.apply(x)
    ybar = float(np.mean(y))
    zbar = np.mean(z, axis=0)
    zc = z - zbar
    yc = y - ybar
    n = len(y)
    gram = zc.T @ zc / n
    rhs = zc.T @ yc / n
    coef = np.linalg.pinv(gram + float(lam) * np.eye(z.shape[1])) @ rhs
    intercept = ybar - float(zbar @ coef)
    return RidgeModel(scaler, intercept, coef, float(lam))


def select_lambda(
    x_train: np.ndarray, y_train: np.ndarray,
    x_valid: np.ndarray, y_valid: np.ndarray,
) -> tuple[float, Scaler, list[dict]]:
    scaler = Scaler.fit(x_train)
    rows = []
    for lam in LAMBDAS:
        model = fit_ridge(x_train, y_train, scaler, float(lam))
        pred = model.predict(x_valid)
        mse = float(np.mean((y_valid - pred) ** 2))
        rows.append({"lambda": float(lam), "validation_mse": mse})
    best = min(rows, key=lambda r: (r["validation_mse"], r["lambda"]))
    return float(best["lambda"]), scaler, rows


def finite_common(*arrays: np.ndarray) -> np.ndarray:
    mask = np.ones(len(arrays[0]), dtype=bool)
    for array in arrays:
        if array.ndim == 1:
            mask &= np.isfinite(array)
        else:
            mask &= np.all(np.isfinite(array), axis=1)
    return mask


def one_hot_time(frame: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    bins = frame["minute_bin_5m"].astype(int).to_numpy()
    # Drop the first category; intercept is fitted separately.
    x = np.column_stack([(bins == k).astype(float) for k in range(1, 6)])
    return x, [f"minute_bin_{k}" for k in range(1, 6)]


def prefix(frame: pd.DataFrame, cols: list[str], name: str) -> pd.DataFrame:
    return frame[["date", "t_ns", *cols]].rename(columns={c: f"{name}__{c}" for c in cols})


def build_panel(features: pd.DataFrame, roster: pd.DataFrame, venue: str, shift: int) -> pd.DataFrame:
    f = features[(features["venue"] == venue) & (features["grid_shift_ms"] == shift)].copy()
    if f.empty:
        return f
    available = set(f["symbol"].astype(str))
    # Keep the fixed roster as the reporting denominator, but estimate on the
    # provider-resolved members. Missing symbols are coverage loss, not a
    # reason to make every other-stock control missing or to redraw the sample.
    stock_roster = roster[(roster["symbol"] != "SPY") & roster["symbol"].isin(available)].copy()
    weights = stock_roster.set_index("symbol")["report_weight"].astype(float)
    symbols = list(weights.index)
    stock = f[f["symbol"].isin(symbols)].copy()
    spy = f[f["symbol"] == "SPY"].copy()
    if spy.empty:
        return pd.DataFrame()

    # Build fixed-weight return controls only when every other selected stock is observed.
    index_cols = ["date", "t_ns"]
    pivots = {}
    for col in RETURN_FEATURES:
        pivots[col] = stock.pivot(index=index_cols, columns="symbol", values=col).reindex(columns=symbols)

    pieces = []
    spy_cols = OWN_FEATURES + list(HORIZONS.values()) + ["quote_valid", "minute_bin_5m"]
    spy_base = prefix(spy, spy_cols, "spy")
    for symbol in symbols:
        own = stock[stock["symbol"] == symbol].copy()
        if own.empty:
            continue
        own_cols = OWN_FEATURES + list(HORIZONS.values()) + ["quote_valid", "minute_bin_5m"]
        panel = prefix(own, own_cols, "stock").merge(spy_base, on=index_cols, how="inner", validate="one_to_one")
        panel["minute_bin_5m"] = panel["stock__minute_bin_5m"]
        others = [s for s in symbols if s != symbol]
        denom = float(weights.loc[others].sum()) if others else 0.0
        for col in RETURN_FEATURES:
            p = pivots[col]
            if not others or denom <= 0:
                series = pd.Series(np.nan, index=p.index)
            else:
                series = p[others].mul(weights.loc[others], axis=1).sum(axis=1, min_count=len(others)) / denom
            control = series.rename(f"basket_ex_i__{col}").reset_index()
            panel = panel.merge(control, on=index_cols, how="left", validate="one_to_one")
        panel["symbol"] = symbol
        panel["report_weight"] = float(weights.loc[symbol])
        rr = stock_roster[stock_roster["symbol"] == symbol].iloc[0]
        panel["weight_tier"] = rr["weight_tier"]
        panel["liquidity_tier"] = rr["liquidity_tier"]
        pieces.append(panel)
    return pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()


def design_arrays(panel: pd.DataFrame, direction: str, horizon: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    basket = [f"basket_ex_i__{c}" for c in RETURN_FEATURES]
    time_x, time_names = one_hot_time(panel)
    if direction == "ETF_TO_STOCK":
        base_cols = [f"stock__{c}" for c in OWN_FEATURES] + basket
        extra_cols = [f"spy__{c}" for c in OWN_FEATURES]
        target = panel[f"stock__{HORIZONS[horizon]}"].to_numpy(float)
    elif direction == "STOCK_TO_ETF":
        base_cols = [f"spy__{c}" for c in OWN_FEATURES] + basket
        extra_cols = [f"stock__{c}" for c in OWN_FEATURES]
        target = panel[f"spy__{HORIZONS[horizon]}"].to_numpy(float)
    else:
        raise ValueError(direction)
    xb = np.column_stack([panel[base_cols].to_numpy(float), time_x])
    xf = np.column_stack([xb, panel[extra_cols].to_numpy(float)])
    return xb, xf, target, base_cols + time_names + extra_cols


def predictions_for_model(panel: pd.DataFrame, direction: str, horizon: str, split: dict[str, set[str]]) -> dict:
    xb, xf, y, names = design_arrays(panel, direction, horizon)
    dates = panel["date"].astype(str).to_numpy()
    common = finite_common(xb, xf, y)
    idx = {
        key: common & np.isin(dates, sorted(value))
        for key, value in split.items()
    }
    if min(int(idx[k].sum()) for k in ("train", "valid", "test")) == 0:
        raise RuntimeError(f"empty model split for {direction}/{horizon}")
    lam_b, scaler_b, trace_b = select_lambda(xb[idx["train"]], y[idx["train"]], xb[idx["valid"]], y[idx["valid"]])
    lam_f, scaler_f, trace_f = select_lambda(xf[idx["train"]], y[idx["train"]], xf[idx["valid"]], y[idx["valid"]])
    fit_mask = idx["train"] | idx["valid"]
    model_b = fit_ridge(xb[fit_mask], y[fit_mask], scaler_b, lam_b)
    model_f = fit_ridge(xf[fit_mask], y[fit_mask], scaler_f, lam_f)
    test_rows = np.flatnonzero(idx["test"])
    pred_b = model_b.predict(xb[test_rows])
    pred_f = model_f.predict(xf[test_rows])
    return {
        "dates": dates[test_rows], "t_ns": panel["t_ns"].to_numpy()[test_rows],
        "y": y[test_rows], "pred_b": pred_b, "pred_f": pred_f,
        "xb": xb[test_rows], "xf": xf[test_rows], "test_rows": test_rows,
        "model_b": model_b, "model_f": model_f, "lambda_b": lam_b, "lambda_f": lam_f,
        "validation_trace_b": trace_b, "validation_trace_f": trace_f,
        "feature_names": names, "n_train": int(idx["train"].sum()),
        "n_valid": int(idx["valid"].sum()), "n_test": int(idx["test"].sum()),
    }


def loss_stats(result: dict) -> tuple[dict, list[dict]]:
    eb = (result["y"] - result["pred_b"]) ** 2
    ef = (result["y"] - result["pred_f"]) ** 2
    daily = []
    for date in sorted(set(result["dates"])):
        m = result["dates"] == date
        daily.append({"date": date, "n": int(m.sum()), "sse_baseline": float(eb[m].sum()),
                      "sse_full": float(ef[m].sum()), "loss_difference": float((eb[m] - ef[m]).sum())})
    sb, sf = float(eb.sum()), float(ef.sum())
    stats = {
        "n_test": len(eb), "test_dates": len(daily), "sse_baseline": sb, "sse_full": sf,
        "mse_baseline": float(eb.mean()), "mse_full": float(ef.mean()),
        "loss_difference": sb - sf, "G": (1.0 - sf / sb) if sb > 0 else math.nan,
        "target_variance": float(np.var(result["y"])),
    }
    return stats, daily


def interval_from_days(daily: list[dict], seed: int = 20260922, reps: int = 1000) -> dict:
    rng = np.random.default_rng(seed)
    sb = np.asarray([r["sse_baseline"] for r in daily], float)
    sf = np.asarray([r["sse_full"] for r in daily], float)
    n = len(daily)
    draws = []
    for _ in range(reps):
        ix = rng.integers(0, n, n)
        b, f = float(sb[ix].sum()), float(sf[ix].sum())
        draws.append(1.0 - f / b if b > 0 else np.nan)
    draws = np.asarray(draws, float)
    loo = []
    if n > 1:
        for k in range(n):
            keep = np.arange(n) != k
            b, f = float(sb[keep].sum()), float(sf[keep].sum())
            loo.append(1.0 - f / b if b > 0 else np.nan)
    return {
        "bootstrap_ci_low": float(np.nanquantile(draws, 0.025)),
        "bootstrap_ci_high": float(np.nanquantile(draws, 0.975)),
        "loo_min": float(np.nanmin(loo)) if loo else math.nan,
        "loo_max": float(np.nanmax(loo)) if loo else math.nan,
    }


def offday_gain(panel: pd.DataFrame, direction: str, horizon: str, result: dict, test_dates: list[str]) -> float:
    # Replace only the added source block with the next test day's same-clock values.
    xb, xf, y, _ = design_arrays(panel, direction, horizon)
    dates = panel["date"].astype(str).to_numpy()
    times = panel["t_ns"].to_numpy(dtype=np.int64)
    starts = panel.groupby("date")["t_ns"].transform("min").to_numpy(dtype=np.int64)
    offsets = times - starts
    source_width = len(OWN_FEATURES)
    altered = xf.copy()
    date_next = {d: test_dates[(i + 1) % len(test_dates)] for i, d in enumerate(test_dates)}
    lookup = {(dates[i], int(offsets[i])): i for i in range(len(panel))}
    valid = np.ones(len(result["test_rows"]), dtype=bool)
    rows = result["test_rows"]
    for j, row in enumerate(rows):
        other = lookup.get((date_next[dates[row]], int(offsets[row])))
        if other is None or not np.all(np.isfinite(xf[other, -source_width:])):
            valid[j] = False
        else:
            altered[row, -source_width:] = xf[other, -source_width:]
    if not valid.any():
        return math.nan
    yv = y[rows][valid]
    pb = result["pred_b"][valid]
    pf = result["model_f"].predict(altered[rows][valid])
    sb, sf = float(np.sum((yv - pb) ** 2)), float(np.sum((yv - pf) ** 2))
    return 1.0 - sf / sb if sb > 0 else math.nan


def run_pair_models(panel: pd.DataFrame, split: dict[str, set[str]], venue: str, shift: int) -> tuple[list[dict], list[dict]]:
    gain_rows, daily_rows = [], []
    for symbol in sorted(panel["symbol"].unique()):
        one = panel[panel["symbol"] == symbol].sort_values(["date", "t_ns"]).reset_index(drop=True)
        for direction in ("ETF_TO_STOCK", "STOCK_TO_ETF"):
            for horizon in HORIZONS:
                result = predictions_for_model(one, direction, horizon, split)
                stats, daily = loss_stats(result)
                ci = interval_from_days(daily, seed=20260922 + shift)
                offday = offday_gain(one, direction, horizon, result, sorted(split["test"]))
                meta = {
                    "venue": venue, "grid_shift_ms": shift, "symbol": symbol,
                    "weight_tier": one["weight_tier"].iloc[0],
                    "liquidity_tier": one["liquidity_tier"].iloc[0],
                    "report_weight": float(one["report_weight"].iloc[0]),
                    "direction": direction, "horizon": horizon,
                    "lambda_baseline": result["lambda_b"], "lambda_full": result["lambda_f"],
                    "n_train": result["n_train"], "n_valid": result["n_valid"],
                    **stats, **ci, "offday_G": offday,
                }
                gain_rows.append(meta)
                for row in daily:
                    daily_rows.append({k: meta[k] for k in ("venue", "grid_shift_ms", "symbol", "weight_tier", "liquidity_tier", "direction", "horizon")} | row)
    return gain_rows, daily_rows


def group_ablation(features: pd.DataFrame, roster: pd.DataFrame, split: dict[str, set[str]], venue: str, shift: int) -> list[dict]:
    f = features[(features["venue"] == venue) & (features["grid_shift_ms"] == shift)].copy()
    available = set(f["symbol"].astype(str))
    stocks = roster.loc[(roster["symbol"] != "SPY") & roster["symbol"].isin(available), "symbol"].tolist()
    tiers = roster[roster["symbol"].isin(stocks)].set_index("symbol")["weight_tier"].to_dict()
    spy = f[f["symbol"] == "SPY"].set_index(["date", "t_ns"]).sort_index()
    blocks = []
    # The predeclared ablation adds each stock's full historical block,
    # including contemporaneously observable spread/depth/volume state.
    stock_feature_cols = OWN_FEATURES
    for symbol in stocks:
        block = f[f["symbol"] == symbol].set_index(["date", "t_ns"])[stock_feature_cols]
        block = block.rename(columns={c: f"{symbol}__{c}" for c in stock_feature_cols})
        blocks.append(block)
    joined = pd.concat([spy, *blocks], axis=1, join="inner").reset_index()
    time_x, time_names = one_hot_time(joined.rename(columns={"minute_bin_5m": "minute_bin_5m"}))
    own_cols = [c for c in OWN_FEATURES if c in joined.columns]
    base = np.column_stack([joined[own_cols].to_numpy(float), time_x])
    all_cols = [f"{s}__{c}" for s in stocks for c in stock_feature_cols]
    full = np.column_stack([base, joined[all_cols].to_numpy(float)])
    y = joined[HORIZONS[PRIMARY_HORIZON]].to_numpy(float)
    dates = joined["date"].astype(str).to_numpy()
    common = finite_common(base, full, y)
    masks = {k: common & np.isin(dates, sorted(v)) for k, v in split.items()}
    if min(int(masks[k].sum()) for k in ("train", "valid", "test")) == 0:
        return []

    designs = {"SPY_ONLY": base, "ALL_STOCKS": full}
    for tier in sorted(set(tiers.values())):
        keep = [c for c in all_cols if tiers[c.split("__", 1)[0]] != tier]
        designs[f"WITHOUT_{tier}"] = np.column_stack([base, joined[keep].to_numpy(float)])
    output = []
    for name, x in designs.items():
        lam, scaler, _ = select_lambda(x[masks["train"]], y[masks["train"]], x[masks["valid"]], y[masks["valid"]])
        fit = masks["train"] | masks["valid"]
        model = fit_ridge(x[fit], y[fit], scaler, lam)
        pred = model.predict(x[masks["test"]])
        err = (y[masks["test"]] - pred) ** 2
        output.append({"venue": venue, "grid_shift_ms": shift, "model": name,
                       "horizon": PRIMARY_HORIZON, "lambda": lam, "feature_count": x.shape[1],
                       "n_train": int(masks["train"].sum()), "n_valid": int(masks["valid"].sum()),
                       "n_test": int(masks["test"].sum()), "sse": float(err.sum()), "mse": float(err.mean())})
    base_sse = next(r["sse"] for r in output if r["model"] == "SPY_ONLY")
    full_sse = next(r["sse"] for r in output if r["model"] == "ALL_STOCKS")
    for row in output:
        row["G_vs_spy_only"] = 1.0 - row["sse"] / base_sse if base_sse > 0 else math.nan
        row["loss_increase_vs_all_stocks"] = row["sse"] - full_sse
    return output


def validate_inputs(features: pd.DataFrame, roster: pd.DataFrame, dates: pd.DataFrame) -> None:
    required = {"date", "t_ns", "symbol", "venue", "grid_shift_ms", "minute_bin_5m", *OWN_FEATURES, *HORIZONS.values()}
    missing = sorted(required - set(features.columns))
    if missing:
        raise ValueError(f"feature table missing columns: {missing}")
    if features.duplicated(["date", "t_ns", "symbol", "venue", "grid_shift_ms"]).any():
        raise ValueError("duplicate security-grid rows")
    if set(dates["split"]) != {"train", "valid", "test"}:
        raise ValueError("date manifest must contain train/valid/test")
    if "SPY" not in set(features["symbol"]):
        raise ValueError("SPY absent")
    if roster["symbol"].duplicated().any():
        raise ValueError("duplicate roster symbols")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", required=True)
    parser.add_argument("--roster", required=True)
    parser.add_argument("--dates", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    features = read_table(Path(args.features))
    roster = pd.read_csv(args.roster)
    dates = pd.read_csv(args.dates, dtype={"date": str})
    features["date"] = features["date"].astype(str)
    validate_inputs(features, roster, dates)
    split = {name: set(dates.loc[dates["split"] == name, "date"].astype(str)) for name in ("train", "valid", "test")}
    gains, daily, ablation = [], [], []
    for venue in sorted(features["venue"].unique()):
        for shift in sorted(features.loc[features["venue"] == venue, "grid_shift_ms"].unique()):
            panel = build_panel(features, roster, venue, int(shift))
            if panel.empty:
                continue
            g, d = run_pair_models(panel, split, venue, int(shift)); gains += g; daily += d
            ablation += group_ablation(features, roster, split, venue, int(shift))
    write_csv(out / "PREDICTIVE_GAINS.csv", gains)
    write_csv(out / "DAILY_LOSS_SUMMARY.csv", daily)
    write_csv(out / "GROUP_ABLATION.csv", ablation)
    receipt = {
        "status": "COMPLETE", "features": str(args.features), "roster": str(args.roster),
        "dates": str(args.dates), "gain_rows": len(gains), "daily_rows": len(daily),
        "ablation_rows": len(ablation), "lambda_grid": LAMBDAS.tolist(),
        "ridge_objective": "mean squared error plus lambda times squared standardized coefficients",
        "main_horizon": PRIMARY_HORIZON, "bootstrap_repetitions": 1000,
    }
    (out / "MODEL_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
