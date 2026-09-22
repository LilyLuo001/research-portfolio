#!/usr/bin/env python3
"""Fit event-clock A0--A5 models on 2023 and score 2024 FOMC pairs.

Row-level inputs, fitted objects, and daily losses remain on SCC.  The output
contains only stock/date/window SSE sums, validation traces, and receipts.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd


MODELS = ("A0", "A1", "A2", "A3", "A4", "A5")
FIT_SPECS = ("OWN_LAMBDA", "FIXED_A2_LAMBDA")
WINDOWS = {
    "PRE_600S": (-600, 0),
    "POST_0_60S": (0, 60),
    "POST_60_600S": (60, 600),
}


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for part in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def prepared(raw: np.ndarray, median: np.ndarray) -> np.ndarray:
    missing = ~np.isfinite(raw)
    return np.column_stack([np.where(missing, median, raw), missing.astype(float)])


def cluster_weights(dates: np.ndarray) -> np.ndarray:
    counts = pd.Series(dates).value_counts()
    weights = np.asarray([1.0 / counts[x] for x in dates], dtype=float)
    return weights / weights.sum()


def fit_ridge(x: np.ndarray, y: np.ndarray, weights: np.ndarray,
              mean: np.ndarray, scale: np.ndarray, lam: float):
    z = (x - mean) / scale
    zbar = np.sum(z * weights[:, None], axis=0)
    ybar = float(np.sum(y * weights))
    zc = z - zbar
    gram = (zc * weights[:, None]).T @ zc + lam * np.eye(z.shape[1])
    rhs = (zc * weights[:, None]).T @ (y - ybar)
    coef = np.linalg.solve(gram, rhs)
    return ybar - float(zbar @ coef), coef


def cluster_mse(y: np.ndarray, pred: np.ndarray, dates: np.ndarray) -> float:
    frame = pd.DataFrame({"date": dates, "loss": (y - pred) ** 2})
    return float(frame.groupby("date", sort=False).loss.mean().mean())


def time_controls(frame: pd.DataFrame) -> pd.DataFrame:
    rel = frame["second_index"].to_numpy(int) - 600
    bucket = np.select(
        [rel < -300, rel < 0, rel < 60, rel < 300],
        [0, 1, 2, 3], default=4,
    )
    # [-600,-300) is the reference category.
    out = {f"relative_bucket_{k}": (bucket == k).astype(float) for k in range(1, 5)}
    out["event_day"] = (frame["sample_kind"].to_numpy(str) == "EVENT").astype(float)
    return pd.DataFrame(out, index=frame.index)


def add_es(panel: pd.DataFrame, es: pd.DataFrame, quote: list[str], trade: list[str]):
    keys = ["date", "grid_shift_ms", "second_index"]
    available_trade = [x for x in trade if x in es.columns]
    cols = keys + ["es_valid"] + quote + available_trade
    renamed = es[cols].rename(columns={
        "es_valid": "es__valid",
        **{x: "es__" + x for x in quote + available_trade},
    })
    return panel.merge(renamed, on=keys, how="left", validate="many_to_one"), available_trade


def transform_es(frame: pd.DataFrame, quote: list[str], trade: list[str]) -> pd.DataFrame:
    out = frame.copy()
    for col in ("bid_depth", "ask_depth", "mid_update_count_1s", "mid_update_age_ms"):
        if col in out:
            out[col] = np.log1p(out[col].clip(lower=0))
    for col in trade:
        if col not in out:
            continue
        if col.startswith("known_signed_flow"):
            values = out[col].to_numpy(float)
            out[col] = np.sign(values) * np.log1p(np.abs(values))
        elif col.startswith("unknown_dollar_volume"):
            out[col] = np.log1p(out[col].clip(lower=0))
    return out


def block_columns(base, panel: pd.DataFrame, es_trade: list[str]):
    controls = [f"relative_bucket_{k}" for k in range(1, 5)] + ["event_day"]
    b = (["stock__" + x for x in base.QUOTE]
         + ["rest__" + x for x in base.QUOTE]
         + ["rest__coverage_" + x for x in base.QUOTE]
         + ["es__" + x for x in base.QUOTE]
         + ["es__" + x for x in es_trade]
         + controls)
    q = ["spy__" + x for x in base.QUOTE]
    c = (["stock__" + x for x in base.TRADE]
         + ["rest__" + x for x in base.TRADE]
         + ["rest__coverage_" + x for x in base.TRADE])
    p = ["spy__" + x for x in base.TRADE]
    models = {
        "A0": b, "A1": b + q, "A2": b + c,
        "A3": b + c + q, "A4": b + q + p, "A5": b + c + q + p,
    }
    absent = sorted({x for cols in models.values() for x in cols if x not in panel})
    if absent:
        raise RuntimeError(f"missing model columns: {absent}")
    return {"B": b, "Q": q, "C": c, "P": p, **models}


def fit_one(panel: pd.DataFrame, columns: list[str], target: str, lambdas: np.ndarray):
    usable = panel[np.isfinite(panel[target].to_numpy(float))].copy()
    raw = usable[columns].to_numpy(float)
    split = usable["split"].to_numpy(str)
    train = split == "TRAIN"; valid = split == "VALID"
    if not train.any() or not valid.any():
        raise RuntimeError("empty train or validation support")
    with np.errstate(all="ignore"):
        median = np.nanmedian(raw[train], axis=0)
    median[~np.isfinite(median)] = 0.0
    x = prepared(raw, median)
    mean = x[train].mean(axis=0)
    scale = x[train].std(axis=0)
    scale[(~np.isfinite(scale)) | (scale == 0)] = 1.0
    y = usable[target].to_numpy(float)
    train_weights = cluster_weights(usable.loc[train, "date"].to_numpy(str))
    trace = []
    for lam in lambdas:
        intercept, coef = fit_ridge(x[train], y[train], train_weights, mean, scale, float(lam))
        pred = intercept + (x[valid] - mean) / scale @ coef
        trace.append({
            "lambda": float(lam),
            "validation_cluster_mse": cluster_mse(
                y[valid], pred, usable.loc[valid, "date"].to_numpy(str)),
        })
    chosen = min(trace, key=lambda row: (row["validation_cluster_mse"], row["lambda"]))
    fit_mask = train | valid
    fit_weights = cluster_weights(usable.loc[fit_mask, "date"].to_numpy(str))
    intercept, coef = fit_ridge(x[fit_mask], y[fit_mask], fit_weights, mean, scale, chosen["lambda"])
    evaluate = usable["split"].isin(["HISTORY", "TEST"]).to_numpy()
    pred = intercept + (x[evaluate] - mean) / scale @ coef
    scored = usable.loc[evaluate, [
        "date", "event_id", "sample_kind", "split", "second_index"
    ]].copy()
    scored["squared_error"] = (y[evaluate] - pred) ** 2
    return chosen, trace, scored, {
        "median": median, "mean": mean, "scale": scale,
        "intercept": intercept, "coef": coef,
        "columns": columns,
    }


def score_with_lambda(panel: pd.DataFrame, columns: list[str], target: str, lam: float):
    chosen, trace, scored, artifact = fit_one(panel, columns, target, np.asarray([lam]))
    return chosen, trace, scored, artifact


def daily_sse(scored: pd.DataFrame, model: str, fit_spec: str, symbol: str,
              venue: str, shift: int):
    pieces = []
    rel = scored.second_index.to_numpy(int) - 600
    # The prediction made at grid center g targets the return ending at g+1.
    # Assign observations by that target endpoint, as required by the contract.
    target_rel = rel + 1
    for window, (lo, hi) in WINDOWS.items():
        part = scored[(target_rel >= lo) & (target_rel < hi)].copy()
        for keys, group in part.groupby(["date", "event_id", "sample_kind", "split"], sort=False):
            pieces.append({
                "venue": venue, "grid_shift_ms": shift, "symbol": symbol,
                "fit_spec": fit_spec, "model": model, "window": window,
                "date": keys[0], "event_id": keys[1], "sample_kind": keys[2],
                "split": keys[3], "n": len(group),
                "sse": float(group.squared_error.sum()),
            })
    return pieces


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", required=True, type=Path)
    ap.add_argument("--es-features", required=True, type=Path)
    ap.add_argument("--analysis-dates", required=True, type=Path)
    ap.add_argument("--roster", required=True, type=Path)
    ap.add_argument("--base-code", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--venue", choices=("XNAS.ITCH", "ARCX.PILLAR"))
    ap.add_argument("--grid-shift-ms", type=int, choices=(0, 500))
    args = ap.parse_args()
    base = load(args.base_code, "fomc_directional_base")
    raw = pd.read_parquet(args.features)
    es = pd.read_parquet(args.es_features)
    dates = pd.read_csv(args.analysis_dates, dtype=str)
    roster = pd.read_csv(args.roster)
    required_dates = {"date", "event_id", "sample_kind", "split"}
    if not required_dates.issubset(dates.columns):
        raise RuntimeError(f"analysis dates missing {sorted(required_dates - set(dates.columns))}")
    if dates.date.duplicated().any():
        raise RuntimeError("each source date must map to exactly one event/control cluster")
    raw["date"] = raw.date.astype(str); es["date"] = es.date.astype(str)
    es = transform_es(es, base.QUOTE, base.TRADE)
    if args.venue is not None:
        raw = raw[raw.venue == args.venue].copy()
    if args.grid_shift_ms is not None:
        raw = raw[raw.grid_shift_ms == args.grid_shift_ms].copy()
        es = es[es.grid_shift_ms == args.grid_shift_ms].copy()
    raw = raw.merge(dates[list(required_dates)], on="date", how="inner", validate="many_to_one")
    expected = {"TRAIN": 8, "VALID": 4, "HISTORY": 4, "TEST": 16}
    actual = dates.groupby("split").size().to_dict()
    if actual != expected:
        raise RuntimeError(f"unexpected date split counts: {actual}")
    outputs, validation, artifacts = [], [], {}
    for venue in sorted(raw.venue.unique()):
        for shift in (0, 500):
            frame = raw[(raw.venue == venue) & (raw.grid_shift_ms == shift)].copy()
            for symbol in frame.symbol.unique():
                mask = frame.symbol == symbol
                frame.loc[mask, base.QUOTE + base.TRADE] = base.transform_values(
                    frame.loc[mask, base.QUOTE + base.TRADE])[base.QUOTE + base.TRADE]
            panels = base.pair_panels(frame, roster, base.QUOTE + base.TRADE)
            for panel in panels:
                panel = panel.merge(dates[list(required_dates)], on="date", how="left", validate="many_to_one")
                tc = time_controls(panel); panel = pd.concat([panel, tc], axis=1)
                panel["grid_shift_ms"] = shift
                panel, es_trade = add_es(panel, es[es.grid_shift_ms == shift], base.QUOTE, base.TRADE)
                blocks = block_columns(base, panel, es_trade)
                symbol = str(panel.symbol.iloc[0]); target = "stock__" + base.TARGET
                own = {}
                for model in MODELS:
                    selected, trace, scored, artifact = fit_one(panel, blocks[model], target, base.LAMBDAS)
                    own[model] = (selected, trace, scored, artifact)
                a2_lambda = own["A2"][0]["lambda"]
                for fit_spec in FIT_SPECS:
                    for model in MODELS:
                        if fit_spec == "OWN_LAMBDA":
                            selected, trace, scored, artifact = own[model]
                        else:
                            selected, trace, scored, artifact = score_with_lambda(
                                panel, blocks[model], target, a2_lambda)
                        for row in trace:
                            validation.append({
                                "venue": venue, "grid_shift_ms": shift, "symbol": symbol,
                                "fit_spec": fit_spec, "model": model,
                                "selected": row["lambda"] == selected["lambda"], **row,
                            })
                        outputs.extend(daily_sse(scored, model, fit_spec, symbol, venue, shift))
                        artifacts[f"{venue}|{shift}|{symbol}|{fit_spec}|{model}"] = artifact
    args.out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(outputs).to_csv(args.out / "DAILY_MODEL_SSE.csv", index=False)
    pd.DataFrame(validation).to_csv(args.out / "VALIDATION_TRACE.csv", index=False)
    # Fitted objects stay on SCC and are only referenced by receipt.
    import pickle
    with (args.out / "FITTED_OBJECTS.pkl").open("wb") as handle:
        pickle.dump(artifacts, handle, protocol=pickle.HIGHEST_PROTOCOL)
    receipt = {
        "status": "COMPLETE_FOMC_MODELS_ON_SCC",
        "code_sha256": digest(Path(__file__)),
        "equity_feature_path": str(args.features), "es_feature_path": str(args.es_features),
        "analysis_dates_sha256": digest(args.analysis_dates),
        "venues": sorted(raw.venue.unique().tolist()),
        "grid_shifts_ms": sorted(int(x) for x in raw.grid_shift_ms.unique()),
        "stocks": int(raw.loc[raw.symbol != "SPY", "symbol"].nunique()),
        "models": list(MODELS), "fit_specs": list(FIT_SPECS),
        "windows": WINDOWS, "daily_sse_rows": len(outputs),
        "validation_rows": len(validation), "fitted_objects_stay_on_scc": True,
        "external_refit_or_rescale": False,
    }
    (args.out / "MODEL_RECEIPT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
