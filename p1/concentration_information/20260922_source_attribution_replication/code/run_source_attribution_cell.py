#!/usr/bin/env python3
"""Fit frozen 2023 A0--A5 models or score them on an external feature panel.

The pickle artifact and row-level feature data are SCC-only.  CSV outputs contain
only model- or date-level sums of squared errors and are safe to aggregate in Git.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd


MODELS = ("A0", "A1", "A2", "A3", "A4", "A5")
FIT_SPECS = ("OWN_LAMBDA", "FIXED_A2_LAMBDA")


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("directional_base", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def prepare_es(frame: pd.DataFrame, quote_cols: list[str]) -> pd.DataFrame:
    out = frame.copy()
    for col in ("bid_depth", "ask_depth", "mid_update_count_1s", "mid_update_age_ms"):
        out[col] = np.log1p(out[col].clip(lower=0))
    required = ["date", "grid_shift_ms", "second_index", "es_valid", *quote_cols]
    missing = [x for x in required if x not in out]
    if missing:
        raise RuntimeError(f"missing ES columns: {missing}")
    return out


def add_es(panel: pd.DataFrame, es: pd.DataFrame, quote_cols: list[str]) -> pd.DataFrame:
    take = ["date", "grid_shift_ms", "second_index", "es_valid", *quote_cols]
    right = es[take].rename(columns={"es_valid": "es__valid", **{x: "es__" + x for x in quote_cols}})
    return panel.merge(right, on=["date", "grid_shift_ms", "second_index"], how="left", validate="many_to_one")


def block_columns(base, panel: pd.DataFrame) -> dict[str, list[str]]:
    # Match the validated predecessor exactly: five dummy variables only.
    # `minute_bin_5m` is an integer source column, not an additional control.
    time_cols = [f"minute_{k}" for k in range(1, 6)]
    b = (["stock__" + x for x in base.QUOTE]
         + ["rest__" + x for x in base.QUOTE]
         + ["rest__coverage_" + x for x in base.QUOTE]
         + ["es__" + x for x in base.QUOTE]
         + time_cols)
    q = ["spy__" + x for x in base.QUOTE]
    c = (["stock__" + x for x in base.TRADE]
         + ["rest__" + x for x in base.TRADE]
         + ["rest__coverage_" + x for x in base.TRADE])
    p = ["spy__" + x for x in base.TRADE]
    blocks = {"B": b, "Q": q, "C": c, "P": p}
    expected = {
        "A0": b,
        "A1": b + q,
        "A2": b + c,
        "A3": b + c + q,
        "A4": b + q + p,
        "A5": b + c + q + p,
    }
    absent = sorted({x for cols in expected.values() for x in cols if x not in panel})
    if absent:
        raise RuntimeError(f"missing model columns: {absent}")
    return {**blocks, **expected}


def prepared(raw: np.ndarray, median: np.ndarray) -> np.ndarray:
    miss = ~np.isfinite(raw)
    return np.column_stack([np.where(miss, median, raw), miss.astype(float)])


def training_arrays(raw: np.ndarray, train_mask: np.ndarray, valid_mask: np.ndarray):
    with np.errstate(all="ignore"):
        median = np.nanmedian(raw[train_mask], axis=0)
    median[~np.isfinite(median)] = 0.0
    x = prepared(raw, median)
    mean = x[train_mask].mean(axis=0)
    scale = x[train_mask].std(axis=0)
    scale[(~np.isfinite(scale)) | (scale == 0)] = 1.0
    return x, median, mean, scale


def choose_lambda(base, x: np.ndarray, y: np.ndarray, train: np.ndarray, valid: np.ndarray,
                  mean: np.ndarray, scale: np.ndarray):
    trace = []
    for lam in base.LAMBDAS:
        intercept, coef = base.fit_ridge(x[train], y[train], mean, scale, float(lam))
        pred = intercept + (x[valid] - mean) / scale @ coef
        trace.append({"lambda": float(lam), "validation_mse": float(np.mean((y[valid] - pred) ** 2))})
    selected = min(trace, key=lambda z: (z["validation_mse"], z["lambda"]))
    return selected, trace


def support_frame(base, panel: pd.DataFrame) -> pd.DataFrame:
    es_cols = ["es__" + x for x in base.QUOTE]
    keep = np.isfinite(panel[base.TARGET].to_numpy(float))
    keep &= panel["es__valid"].fillna(0).eq(1).to_numpy()
    keep &= np.isfinite(panel[es_cols].to_numpy(float)).all(axis=1)
    return panel.loc[keep].copy()


def fit_symbol(base, frame: pd.DataFrame, cols: dict[str, list[str]], splits: dict[str, set[str]],
               venue: str, shift: int, symbol: str):
    masks = {name: frame.date.isin(values).to_numpy() for name, values in splits.items()}
    if any(masks[x].sum() == 0 for x in ("train", "valid", "test")):
        raise RuntimeError(f"empty 2023 split for {symbol}: { {x:int(v.sum()) for x,v in masks.items()} }")
    y = frame[base.TARGET].to_numpy(float)
    staged = {}
    for model in MODELS:
        raw = frame[cols[model]].to_numpy(float)
        x, median, mean, scale = training_arrays(raw, masks["train"], masks["valid"])
        selected, trace = choose_lambda(base, x, y, masks["train"], masks["valid"], mean, scale)
        staged[model] = dict(raw_columns=cols[model], x=x, median=median, mean=mean, scale=scale,
                             own_lambda=selected["lambda"], own_validation_mse=selected["validation_mse"],
                             validation_trace=trace)
    fixed_lambda = staged["A2"]["own_lambda"]
    artifact = {"venue": venue, "grid_shift_ms": shift, "symbol": symbol, "models": {}}
    model_rows, daily_rows, trace_rows = [], [], []
    for model in MODELS:
        for trace_item in staged[model]["validation_trace"]:
            trace_rows.append({"venue": venue, "grid_shift_ms": shift, "symbol": symbol,
                "model": model, **trace_item,
                "selected": trace_item["lambda"] == staged[model]["own_lambda"]})
    fit_mask = masks["train"] | masks["valid"]
    for fit_spec in FIT_SPECS:
        artifact["models"][fit_spec] = {}
        for model in MODELS:
            item = staged[model]
            lam = item["own_lambda"] if fit_spec == "OWN_LAMBDA" else fixed_lambda
            validation_mse_at_used_lambda = next(
                x["validation_mse"] for x in item["validation_trace"] if x["lambda"] == float(lam))
            intercept, coef = base.fit_ridge(item["x"][fit_mask], y[fit_mask], item["mean"], item["scale"], lam)
            pred = intercept + (item["x"][masks["test"]] - item["mean"]) / item["scale"] @ coef
            error = (y[masks["test"]] - pred) ** 2
            artifact["models"][fit_spec][model] = {
                "raw_columns": item["raw_columns"], "median": item["median"], "mean": item["mean"],
                "scale": item["scale"], "lambda": float(lam), "intercept": float(intercept),
                "coef": coef, "own_validation_mse": item["own_validation_mse"],
                "validation_trace": item["validation_trace"],
            }
            model_rows.append({"venue": venue, "grid_shift_ms": shift, "symbol": symbol,
                "fit_spec": fit_spec, "model": model, "lambda": float(lam),
                "own_selected_lambda": item["own_lambda"],
                "validation_mse_at_used_lambda": validation_mse_at_used_lambda,
                "own_selected_validation_mse": item["own_validation_mse"],
                "n_train": int(masks["train"].sum()), "n_valid": int(masks["valid"].sum()),
                "n_test": int(masks["test"].sum()), "sse": float(error.sum()), "mse": float(error.mean())})
            detail = frame.loc[masks["test"], ["date"]].copy()
            detail["squared_error"] = error
            for date, group in detail.groupby("date"):
                daily_rows.append({"venue": venue, "grid_shift_ms": shift, "symbol": symbol,
                    "fit_spec": fit_spec, "model": model, "date": date, "n": len(group),
                    "sse": float(group.squared_error.sum())})
    artifact["n_train"] = int(masks["train"].sum())
    artifact["n_valid"] = int(masks["valid"].sum())
    artifact["n_test"] = int(masks["test"].sum())
    return artifact, model_rows, daily_rows, trace_rows


def score_symbol(base, frame: pd.DataFrame, artifact: dict, venue: str, shift: int, symbol: str):
    y = frame[base.TARGET].to_numpy(float)
    model_rows, daily_rows = [], []
    for fit_spec in FIT_SPECS:
        for model in MODELS:
            item = artifact["models"][fit_spec][model]
            raw = frame[item["raw_columns"]].to_numpy(float)
            x = prepared(raw, item["median"])
            pred = item["intercept"] + (x - item["mean"]) / item["scale"] @ item["coef"]
            error = (y - pred) ** 2
            model_rows.append({"venue": venue, "grid_shift_ms": shift, "symbol": symbol,
                "fit_spec": fit_spec, "model": model, "lambda": item["lambda"],
                "n_test": len(frame), "sse": float(error.sum()), "mse": float(error.mean())})
            detail = frame[["date"]].copy(); detail["squared_error"] = error
            for date, group in detail.groupby("date"):
                daily_rows.append({"venue": venue, "grid_shift_ms": shift, "symbol": symbol,
                    "fit_spec": fit_spec, "model": model, "date": date, "n": len(group),
                    "sse": float(group.squared_error.sum())})
    return model_rows, daily_rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("fit2023", "score"), required=True)
    ap.add_argument("--stock-features", required=True, type=Path)
    ap.add_argument("--futures-features", required=True, type=Path)
    ap.add_argument("--base-code", required=True, type=Path)
    ap.add_argument("--roster", required=True, type=Path)
    ap.add_argument("--dates", required=True, type=Path)
    ap.add_argument("--artifact", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--venue", choices=("XNAS.ITCH", "ARCX.PILLAR"), required=True)
    ap.add_argument("--grid-shift", choices=(0, 500), type=int, required=True)
    args = ap.parse_args()
    base = load_module(args.base_code)
    raw = pd.read_parquet(args.stock_features, filters=[("venue", "==", args.venue),
        ("grid_shift_ms", "==", args.grid_shift)])
    raw.date = raw.date.astype(str)
    es = pd.read_parquet(args.futures_features, filters=[("grid_shift_ms", "==", args.grid_shift)])
    es.date = es.date.astype(str); es = prepare_es(es, base.QUOTE)
    requested_dates = pd.read_csv(args.dates, dtype={"date": str})
    date_set = set(requested_dates.date)
    raw = raw[raw.date.isin(date_set)].copy(); es = es[es.date.isin(date_set)].copy()
    roster = pd.read_csv(args.roster)
    # SAFE_ROSTER contains one historical draw (BF) that never entered the
    # validated 2023 feature panel.  Freeze the effective analysis roster to
    # the symbols actually present in that panel: 23 stocks plus SPY.
    analysis_stocks = sorted(set(raw.symbol.astype(str)) - {"SPY"})
    if len(analysis_stocks) != 23 or "SPY" not in set(raw.symbol.astype(str)):
        raise RuntimeError(f"expected frozen 23-stock panel plus SPY, got={sorted(raw.symbol.unique())}")
    roster = roster[roster.symbol.astype(str).isin(analysis_stocks)].copy()
    if set(roster.symbol.astype(str)) != set(analysis_stocks):
        raise RuntimeError("feature symbols are not fully represented in SAFE_ROSTER")
    for symbol in raw.symbol.unique():
        mask = raw.symbol == symbol
        raw.loc[mask, base.QUOTE + base.TRADE] = base.transform_values(raw.loc[mask, base.QUOTE + base.TRADE])[base.QUOTE + base.TRADE]
    panels = base.pair_panels(raw, roster, base.QUOTE + base.TRADE)
    all_models, all_daily, all_traces, artifacts = [], [], [], {}
    split_sets = None
    if args.mode == "fit2023":
        split_sets = {name: set(requested_dates.loc[requested_dates.split == name, "date"])
                      for name in ("train", "valid", "test")}
    else:
        if not args.artifact.exists():
            raise RuntimeError(f"frozen artifact absent: {args.artifact}")
        with args.artifact.open("rb") as handle:
            frozen = pickle.load(handle)
        if frozen["venue"] != args.venue or int(frozen["grid_shift_ms"]) != args.grid_shift:
            raise RuntimeError("frozen artifact cell does not match requested score cell")
    for panel in panels:
        tc = base.time_controls(panel); panel = pd.concat([panel, tc], axis=1)
        panel["grid_shift_ms"] = args.grid_shift
        panel = add_es(panel, es, base.QUOTE)
        panel = panel.rename(columns={"stock__" + base.TARGET: base.TARGET})
        panel = support_frame(base, panel)
        symbol = str(panel.symbol.iloc[0]); cols = block_columns(base, panel)
        if args.mode == "fit2023":
            artifact, rows, daily, traces = fit_symbol(base, panel, cols, split_sets, args.venue, args.grid_shift, symbol)
            artifacts[symbol] = artifact
            all_traces.extend(traces)
        else:
            if symbol not in frozen["symbols"]:
                raise RuntimeError(f"symbol absent from frozen object: {symbol}")
            rows, daily = score_symbol(base, panel, frozen["symbols"][symbol], args.venue, args.grid_shift, symbol)
        all_models.extend(rows); all_daily.extend(daily)
    args.out.mkdir(parents=True, exist_ok=True)
    models = pd.DataFrame(all_models).sort_values(["fit_spec", "model", "symbol"])
    daily = pd.DataFrame(all_daily).sort_values(["fit_spec", "model", "symbol", "date"])
    models.to_csv(args.out / "MODEL_COMPARISON_CELL.csv", index=False)
    daily.to_csv(args.out / "DAILY_LOSS_CELL.csv", index=False)
    if args.mode == "fit2023":
        pd.DataFrame(all_traces).sort_values(["model", "symbol", "lambda"]).to_csv(
            args.out / "VALIDATION_TRACE_CELL.csv", index=False)
    code_hash = sha256(Path(__file__))
    if args.mode == "fit2023":
        frozen = {"status": "FROZEN_2023_BEFORE_2024_SCORE", "venue": args.venue,
            "grid_shift_ms": args.grid_shift, "train_dates": sorted(split_sets["train"]),
            "valid_dates": sorted(split_sets["valid"]), "exploratory_2023_test_dates": sorted(split_sets["test"]),
            "code_sha256": code_hash, "base_code_sha256": sha256(args.base_code), "symbols": artifacts}
        args.artifact.parent.mkdir(parents=True, exist_ok=True)
        with args.artifact.open("wb") as handle:
            pickle.dump(frozen, handle, protocol=pickle.HIGHEST_PROTOCOL)
    receipt = {"status": "COMPLETE_" + args.mode.upper(), "venue": args.venue,
        "grid_shift_ms": args.grid_shift, "dates": sorted(date_set), "stock_symbols": len(panels),
        "excluded_safe_roster_symbols": sorted(set(pd.read_csv(args.roster).symbol.astype(str)) - set(analysis_stocks)),
        "model_rows": len(models), "daily_rows": len(daily), "validation_trace_rows": len(all_traces),
        "fit_specs": list(FIT_SPECS),
        "models": list(MODELS), "artifact_path": str(args.artifact),
        "artifact_sha256": sha256(args.artifact), "code_sha256": code_hash,
        "stock_features": str(args.stock_features), "futures_features": str(args.futures_features),
        "row_level_features_predictions_coefficients_exported_locally": False}
    (args.out / "CELL_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
