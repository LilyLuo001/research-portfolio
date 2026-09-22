#!/usr/bin/env python3
"""Run the frozen four-model ES/SPY conditional-prediction comparison.

Row-level features and prediction errors remain on SCC.  This script exports
only model, daily-loss, aggregate, date-sensitivity, reverse-check and receipt
tables to the requested aggregate output directory.
"""
from __future__ import annotations

import argparse
import gc
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd


MODEL_NAMES = ("M0", "M1", "M2", "M3")
BOOTSTRAP_SEED = 20260922
CONTRASTS = {
    "SPY_RAW": ("M0", "M1"),
    "ES_RAW": ("M0", "M2"),
    "SPY_GIVEN_ES": ("M2", "M3"),
    "ES_GIVEN_SPY": ("M1", "M3"),
}


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("directional_base", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def prepare_es(frame: pd.DataFrame, quote_cols: list[str]) -> pd.DataFrame:
    out = frame.copy()
    for stem in ("", "lag1_"):
        for col in ("bid_depth", "ask_depth", "mid_update_count_1s", "mid_update_age_ms"):
            name = stem + col
            out[name] = np.log1p(out[name].clip(lower=0))
    required = ["date", "grid_shift_ms", "second_index", "contract", "requested_contract", "es_valid", "lag1_es_valid"]
    missing = [x for x in required + quote_cols + ["lag1_" + x for x in quote_cols] if x not in out]
    if missing:
        raise RuntimeError(f"missing futures feature columns: {missing}")
    return out


def merge_es(panel: pd.DataFrame, es: pd.DataFrame, cutoff: str, quote_cols: list[str]) -> pd.DataFrame:
    stem = "" if cutoff == "AT_T" else "lag1_"
    take = ["date", "grid_shift_ms", "second_index", stem + "es_valid", *[stem + x for x in quote_cols]]
    right = es[take].copy().rename(columns={stem + "es_valid": "es__valid", **{stem + x: "es__" + x for x in quote_cols}})
    return panel.merge(right, on=["date", "grid_shift_ms", "second_index"], how="left", validate="many_to_one")


def support_plan(frame: pd.DataFrame, quote_cols: list[str]):
    complete = frame["es__valid"].fillna(0).eq(1).all()
    complete = bool(complete and np.isfinite(frame[["es__" + x for x in quote_cols]].to_numpy(float)).all())
    if complete:
        return [("FULL", ("FULL", "ES_VALID"))]
    return [("FULL", ("FULL",)), ("ES_VALID", ("ES_VALID",))]


def fit_models(base, frame: pd.DataFrame, model_cols: dict[str, list[str]], splits: dict[str, set[str]], support: str):
    use = frame[np.isfinite(frame[base.TARGET].to_numpy(float))].copy()
    es_cols = sorted({col for cols in model_cols.values() for col in cols if col.startswith("es__")})
    if support == "ES_VALID":
        valid = use["es__valid"].fillna(0).eq(1).to_numpy()
        valid &= np.isfinite(use[es_cols].to_numpy(float)).all(axis=1)
        use = use.loc[valid].copy()
    masks = {k: use.date.isin(v).to_numpy() for k, v in splits.items()}
    if any(masks[k].sum() == 0 for k in ("train", "valid", "test")):
        raise RuntimeError(f"empty split under {support}")
    y = use[base.TARGET].to_numpy(float)
    predictions, stats = {}, {}
    for name, cols in model_cols.items():
        raw = use[cols].to_numpy(float)
        x, info = base.prepare_x(raw[masks["train"]], {k: raw[m] for k, m in masks.items()})
        mean = x["train"].mean(0); scale = x["train"].std(0)
        scale[(~np.isfinite(scale)) | (scale == 0)] = 1.0
        trace = []
        for lam in base.LAMBDAS:
            a, b = base.fit_ridge(x["train"], y[masks["train"]], mean, scale, float(lam))
            pred = a + (x["valid"] - mean) / scale @ b
            trace.append((float(np.mean((y[masks["valid"]] - pred) ** 2)), float(lam)))
        lam = min(trace)[1]
        fit_x = np.vstack([x["train"], x["valid"]]); fit_y = np.r_[y[masks["train"]], y[masks["valid"]]]
        a, b = base.fit_ridge(fit_x, fit_y, mean, scale, lam)
        pred = a + (x["test"] - mean) / scale @ b
        predictions[name] = pred
        stats[name] = {
            "lambda": lam,
            "validation_mse": min(trace)[0],
            "test_missing_rate": info["missing_rates"]["test"],
        }
    detail = use.loc[masks["test"], ["date", "second_index"]].copy()
    yt = y[masks["test"]]
    for name in model_cols:
        detail["sse_" + name] = (yt - predictions[name]) ** 2
    out = {
        "n_train": int(masks["train"].sum()),
        "n_valid": int(masks["valid"].sum()),
        "n_test": int(masks["test"].sum()),
        "es_valid_test_fraction": float(frame.loc[frame.date.isin(splits["test"]), "es__valid"].fillna(0).mean()),
    }
    for name in model_cols:
        sse = float(detail["sse_" + name].sum())
        out[f"sse_{name}"] = sse
        out[f"mse_{name}"] = sse / len(detail)
        out[f"lambda_{name}"] = stats[name]["lambda"]
        out[f"validation_mse_{name}"] = stats[name]["validation_mse"]
        out[f"missing_rate_test_{name}"] = stats[name]["test_missing_rate"]
    for label, (b, f) in CONTRASTS.items():
        if b not in model_cols or f not in model_cols:
            continue
        out["G_" + label] = 1.0 - out[f"sse_{f}"] / out[f"sse_{b}"]
        out["loss_change_" + label] = out[f"sse_{b}"] - out[f"sse_{f}"]
    return out, detail


def weighted_gain(arrays: dict[str, np.ndarray], contrast: str) -> np.ndarray:
    b, f = CONTRASTS[contrast]
    return 1.0 - arrays[f] / arrays[b]


def aggregate_daily(daily: pd.DataFrame, weights: dict[str, float], reps: int = 2000):
    keys = ["venue", "grid_shift_ms", "family", "es_cutoff", "support"]
    aggregate_rows, sensitivity_rows = [], []
    for key, group in daily.groupby(keys):
        dates = sorted(group.date.unique()); symbols = sorted(group.symbol.unique())
        mats = {m: group.pivot(index="symbol", columns="date", values="sse_" + m).reindex(index=symbols, columns=dates).to_numpy(float) for m in MODEL_NAMES}
        w = np.asarray([weights[x] for x in symbols], float); w /= w.sum()
        # Reset to the same seed for every venue/grid/specification.  With the
        # common eight test dates this enforces synchronized whole-date draws,
        # including identical FULL/ES_VALID intervals when their rows match.
        rng = np.random.default_rng(BOOTSTRAP_SEED)
        draws = rng.integers(0, len(dates), size=(reps, len(dates)))
        boot_sums = {m: np.stack([mats[m][:, ix].sum(1) for ix in draws]) for m in MODEL_NAMES}
        totals = {m: mats[m].sum(1) for m in MODEL_NAMES}
        for contrast in CONTRASTS:
            point = weighted_gain(totals, contrast)
            boot = weighted_gain(boot_sums, contrast)
            aggregate_rows.append(dict(zip(keys, key), contrast=contrast, stocks=len(symbols), test_dates=len(dates),
                equal_stock_G=float(point.mean()), report_weight_G=float(point @ w), positive_stocks=int((point > 0).sum()),
                equal_ci_low=float(np.quantile(boot.mean(1), .025)), equal_ci_high=float(np.quantile(boot.mean(1), .975)),
                weighted_ci_low=float(np.quantile(boot @ w, .025)), weighted_ci_high=float(np.quantile(boot @ w, .975))))
            for j, omitted in enumerate(dates):
                keep = [x for x in range(len(dates)) if x != j]
                loo = weighted_gain({m: mats[m][:, keep].sum(1) for m in MODEL_NAMES}, contrast)
                sensitivity_rows.append(dict(zip(keys, key), contrast=contrast, omitted_date=omitted,
                    remaining_test_dates=len(keep), equal_stock_G=float(loo.mean()), report_weight_G=float(loo @ w),
                    positive_stocks=int((loo > 0).sum())))
    return pd.DataFrame(aggregate_rows), pd.DataFrame(sensitivity_rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stock-features", required=True, type=Path)
    ap.add_argument("--futures-features", required=True, type=Path)
    ap.add_argument("--base-code", required=True, type=Path)
    ap.add_argument("--roster", required=True, type=Path)
    ap.add_argument("--dates", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--venue", choices=["XNAS.ITCH", "ARCX.PILLAR"])
    ap.add_argument("--grid-shift", type=int, choices=[0, 500])
    ap.add_argument("--family", choices=["QUOTE_WITH_REST_BASKET", "QUOTE_TRADE_WITH_REST_BASKET"])
    args = ap.parse_args()
    base = load_module(args.base_code)
    filters = []
    if args.venue is not None:
        filters.append(("venue", "==", args.venue))
    if args.grid_shift is not None:
        filters.append(("grid_shift_ms", "==", args.grid_shift))
    raw = pd.read_parquet(args.stock_features, filters=filters or None); raw.date = raw.date.astype(str)
    es = pd.read_parquet(args.futures_features); es.date = es.date.astype(str)
    roster = pd.read_csv(args.roster); dates = pd.read_csv(args.dates, dtype={"date": str})
    splits = {k: set(dates.loc[dates.split == k, "date"]) for k in ("train", "valid", "test")}
    es = prepare_es(es, base.QUOTE)
    weights = roster.set_index("symbol").report_weight.astype(float).to_dict()
    model_rows, daily_rows, reverse_rows = [], [], []
    for venue in sorted(raw.venue.unique()):
        # Respect CLI/parquet filters. Iterating the hard-coded shifts after
        # reading one shard created an empty second shard and failed only at
        # the split check, after the requested cell had already finished.
        for shift_value in sorted(raw.loc[raw.venue == venue, "grid_shift_ms"].unique()):
            shift = int(shift_value)
            stock = raw[(raw.venue == venue) & (raw.grid_shift_ms == shift)].copy()
            for symbol in stock.symbol.unique():
                mask = stock.symbol == symbol
                stock.loc[mask, base.QUOTE + base.TRADE] = base.transform_values(stock.loc[mask, base.QUOTE + base.TRADE])[base.QUOTE + base.TRADE]
            es_part = es[es.grid_shift_ms == shift].copy()
            families = (("QUOTE_WITH_REST_BASKET", base.QUOTE), ("QUOTE_TRADE_WITH_REST_BASKET", base.QUOTE + base.TRADE))
            if args.family is not None:
                families = tuple(x for x in families if x[0] == args.family)
            for family, cols in families:
                print(json.dumps({"stage": "START_CELL", "venue": venue, "grid_shift_ms": shift, "family": family}), flush=True)
                panels = base.pair_panels(stock, roster, cols)
                for panel in panels:
                    tc = base.time_controls(panel); panel = pd.concat([panel, tc], axis=1); panel["grid_shift_ms"] = shift
                    symbol = panel.symbol.iloc[0]
                    rest = [f"rest__{x}" for x in cols] + [f"rest__coverage_{x}" for x in cols]
                    base_cols = ["stock__" + x for x in cols] + rest + list(tc.columns)
                    spy_cols = ["spy__" + x for x in cols]
                    for cutoff in ("AT_T", "AT_T_MINUS_1S"):
                        q = merge_es(panel, es_part, cutoff, base.QUOTE).rename(columns={"stock__" + base.TARGET: base.TARGET})
                        es_cols = ["es__" + x for x in base.QUOTE]
                        models = {"M0": base_cols, "M1": base_cols + spy_cols, "M2": base_cols + es_cols, "M3": base_cols + es_cols + spy_cols}
                        for fitted_support, output_supports in support_plan(q, base.QUOTE):
                            stat, detail = fit_models(base, q, models, splits, fitted_support)
                            for support in output_supports:
                                meta = {"venue": venue, "grid_shift_ms": shift, "family": family, "es_cutoff": cutoff,
                                        "support": support, "symbol": symbol, "report_weight": weights[symbol], **stat}
                                model_rows.append(meta)
                                for date, g in detail.groupby("date"):
                                    row = {"venue": venue, "grid_shift_ms": shift, "family": family, "es_cutoff": cutoff,
                                           "support": support, "symbol": symbol, "date": date, "n": len(g)}
                                    row.update({"sse_" + m: float(g["sse_" + m].sum()) for m in MODEL_NAMES})
                                    daily_rows.append(row)
                # Reverse auxiliary: SPY own history + ES, then add existing tier aggregates.
                joint, tiers = base.joint_panel(stock, roster, cols, "TIER")
                tc = base.time_controls(joint); joint = pd.concat([joint, tc], axis=1); joint["grid_shift_ms"] = shift
                for cutoff in ("AT_T", "AT_T_MINUS_1S"):
                    q = merge_es(joint, es_part, cutoff, base.QUOTE).rename(columns={"spy__" + base.TARGET: base.TARGET})
                    base_cols = ["spy__" + x for x in cols] + ["es__" + x for x in base.QUOTE] + list(tc.columns)
                    models = {"M0": base_cols, "M1": base_cols + tiers}
                    for fitted_support, output_supports in support_plan(q, base.QUOTE):
                        stat, _ = fit_models(base, q, models, splits, fitted_support)
                        for support in output_supports:
                            reverse_rows.append({"venue": venue, "grid_shift_ms": shift, "family": family,
                                "es_cutoff": cutoff, "support": support, "n_test": stat["n_test"],
                                "sse_baseline_spy_plus_es": stat["sse_M0"], "sse_full_add_tiers": stat["sse_M1"],
                                "G_add_stock_tiers_given_es": 1.0 - stat["sse_M1"] / stat["sse_M0"]})
                del panels, joint, q
                gc.collect()
                print(json.dumps({"stage": "COMPLETE_CELL", "venue": venue, "grid_shift_ms": shift, "family": family}), flush=True)
    models = pd.DataFrame(model_rows); daily = pd.DataFrame(daily_rows)
    aggregates, sensitivity = aggregate_daily(daily, weights)
    args.out.mkdir(parents=True, exist_ok=True)
    models.to_csv(args.out / "MODEL_COMPARISON.csv", index=False)
    daily.to_csv(args.out / "DAILY_LOSS_DIFFERENCES.csv", index=False)
    aggregates.to_csv(args.out / "AGGREGATE_COMPARISON.csv", index=False)
    sensitivity.to_csv(args.out / "DATE_SENSITIVITY.csv", index=False)
    pd.DataFrame(reverse_rows).to_csv(args.out / "REVERSE_CHECK.csv", index=False)
    receipt = {"status": "COMPLETE_FUTURES_CONTROL_MODELS", "stock_feature_path": str(args.stock_features),
        "futures_feature_path": str(args.futures_features), "model_rows": len(models), "daily_rows": len(daily),
        "aggregate_rows": len(aggregates), "date_sensitivity_rows": len(sensitivity), "reverse_rows": len(reverse_rows),
        "target": "future one-second stock midpoint log return bp", "splits": {k: len(v) for k, v in splits.items()},
        "models": {"M0": "stock own + rest-of-22 + time", "M1": "M0 + SPY", "M2": "M0 + ES", "M3": "M0 + ES + SPY"},
        "cell_filter": {"venue": args.venue, "grid_shift_ms": args.grid_shift, "family": args.family},
        "raw_feature_or_prediction_rows_exported_locally": False}
    (args.out / "MODEL_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
