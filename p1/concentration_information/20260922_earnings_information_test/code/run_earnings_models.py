#!/usr/bin/env python3
"""Fit pooled A0--A5 earnings models and retain SCC-only row-level losses."""
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
HORIZONS = (1, 5, 30)
WINDOWS = {"PRE_600S": (-600, 0), "POST_0_60S": (0, 60), "POST_60_600S": (60, 600)}


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


def prefix(frame: pd.DataFrame, cols: list[str], name: str, target: str) -> pd.DataFrame:
    selected = ["date", "second_index", target, *cols]
    return frame[selected].rename(columns={target: "stock__target" if name == "stock" else f"{name}__target", **{c: f"{name}__{c}" for c in cols}})


def target_panel(frame: pd.DataFrame, roster: pd.DataFrame, cols: list[str], issuer: str, target: str) -> pd.DataFrame:
    spy = frame[frame.symbol == "SPY"].copy()
    stocks = frame[frame.symbol != "SPY"].copy()
    weights = roster.set_index("symbol").report_weight.astype(float)
    stocks["report_weight"] = stocks.symbol.map(weights)
    if issuer not in set(stocks.symbol):
        raise RuntimeError(f"issuer {issuer} absent from feature sample")
    keys = ["date", "second_index"]
    one_raw = stocks[stocks.symbol == issuer].copy()
    panel = prefix(one_raw, cols, "stock", target).merge(prefix(spy, cols, "spy", target), on=keys, validate="one_to_one")
    own_weight = float(weights.loc[issuer])
    total_other_weight = float(weights.loc[stocks.symbol.unique()].sum() - own_weight)
    own = one_raw.set_index(keys)
    for col in cols:
        valid = np.isfinite(stocks[col].to_numpy(float))
        temp = stocks[keys].copy()
        temp["num"] = np.where(valid, stocks[col] * stocks.report_weight, 0.0)
        temp["den"] = np.where(valid, stocks.report_weight, 0.0)
        total = temp.groupby(keys)[["num", "den"]].sum().join(own[[col]], how="left")
        own_valid = np.isfinite(total[col].to_numpy(float))
        num = total.num.to_numpy(float) - np.where(own_valid, total[col].to_numpy(float) * own_weight, 0.0)
        den = total.den.to_numpy(float) - np.where(own_valid, own_weight, 0.0)
        rest = pd.DataFrame({"date": [x[0] for x in total.index], "second_index": [x[1] for x in total.index], f"rest__{col}": np.where(den > 0, num / den, np.nan), f"rest__coverage_{col}": den / total_other_weight})
        panel = panel.merge(rest, on=keys, how="left", validate="one_to_one")
    return panel


def es_transform(frame: pd.DataFrame, quote: list[str], trade: list[str]) -> pd.DataFrame:
    out = frame.copy()
    for col in ("bid_depth", "ask_depth", "mid_update_count_1s", "mid_update_age_ms"):
        out[col] = np.log1p(out[col].clip(lower=0))
    for col in trade:
        if col.startswith("known_signed_flow"):
            value = out[col].to_numpy(float)
            out[col] = np.sign(value) * np.log1p(np.abs(value))
        elif col.startswith("unknown_dollar_volume"):
            out[col] = np.log1p(out[col].clip(lower=0))
    return out


def controls(panel: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    rel = panel.second_index.to_numpy(int) - 600
    bucket = np.select([rel < -300, rel < 0, rel < 60, rel < 300], [0, 1, 2, 3], default=4)
    values = {f"relative_bucket_{k}": (bucket == k).astype(float) for k in range(1, 5)}
    values["event_day"] = (panel.sample_kind.to_numpy(str) == "EVENT").astype(float)
    for issuer in sorted(panel.issuer.unique())[1:]:
        values[f"issuer_{issuer}"] = (panel.issuer.to_numpy(str) == issuer).astype(float)
    for session in sorted(panel.session.unique())[1:]:
        values[f"session_{session}"] = (panel.session.to_numpy(str) == session).astype(float)
    result = pd.DataFrame(values, index=panel.index)
    return result, list(result.columns)


def blocks(base, control_cols: list[str], es_trade: list[str]) -> dict[str, list[str]]:
    b = (["stock__" + x for x in base.QUOTE] + ["rest__" + x for x in base.QUOTE] + ["rest__coverage_" + x for x in base.QUOTE] + ["es__" + x for x in base.QUOTE] + ["es__" + x for x in es_trade] + control_cols)
    q = ["spy__" + x for x in base.QUOTE]
    c = ["stock__" + x for x in base.TRADE] + ["rest__" + x for x in base.TRADE] + ["rest__coverage_" + x for x in base.TRADE]
    p = ["spy__" + x for x in base.TRADE]
    return {"A0": b, "A1": b + q, "A2": b + c, "A3": b + c + q, "A4": b + q + p, "A5": b + c + q + p}


def prepared(raw: np.ndarray, median: np.ndarray) -> np.ndarray:
    missing = ~np.isfinite(raw)
    return np.column_stack([np.where(missing, median, raw), missing.astype(float)])


def hierarchical_weights(frame: pd.DataFrame) -> np.ndarray:
    issuer_n = frame.issuer.nunique()
    events_per = frame[["issuer", "event_id"]].drop_duplicates().groupby("issuer").size()
    rows_per = frame.groupby("sample_id").size()
    weight = np.asarray([1.0 / issuer_n / events_per.loc[i] / rows_per.loc[s] for i, s in zip(frame.issuer, frame.sample_id)], float)
    return weight / weight.sum()


def fit_ridge(x: np.ndarray, y: np.ndarray, weights: np.ndarray, mean: np.ndarray, scale: np.ndarray, lam: float):
    z = (x - mean) / scale
    zbar = np.sum(z * weights[:, None], axis=0)
    ybar = float(np.sum(y * weights))
    centered = z - zbar
    gram = (centered * weights[:, None]).T @ centered + lam * np.eye(z.shape[1])
    rhs = (centered * weights[:, None]).T @ (y - ybar)
    coef = np.linalg.solve(gram, rhs)
    return ybar - float(zbar @ coef), coef


def hierarchical_mse(frame: pd.DataFrame, loss: np.ndarray) -> float:
    x = frame[["issuer", "event_id", "sample_id"]].copy()
    x["loss"] = loss
    return float(x.groupby(["issuer", "event_id", "sample_id"]).loss.mean().groupby(level=[0, 1]).mean().groupby(level=0).mean().mean())


def fit_one(panel: pd.DataFrame, columns: list[str], lambdas: np.ndarray):
    usable = panel[np.isfinite(panel.target.to_numpy(float))].copy()
    raw = usable[columns].to_numpy(float)
    split = usable.split.to_numpy(str)
    train, valid = split == "TRAIN", split == "VALID"
    if not train.any() or not valid.any():
        raise RuntimeError("empty train/validation support")
    with np.errstate(all="ignore"):
        median = np.nanmedian(raw[train], axis=0)
    median[~np.isfinite(median)] = 0.0
    x = prepared(raw, median)
    mean, scale = x[train].mean(0), x[train].std(0)
    scale[(~np.isfinite(scale)) | (scale == 0)] = 1.0
    y = usable.target.to_numpy(float)
    train_weights = hierarchical_weights(usable.loc[train])
    trace = []
    for lam in lambdas:
        intercept, coef = fit_ridge(x[train], y[train], train_weights, mean, scale, float(lam))
        pred = intercept + (x[valid] - mean) / scale @ coef
        trace.append({"lambda": float(lam), "validation_hierarchical_mse": hierarchical_mse(usable.loc[valid], (y[valid] - pred) ** 2)})
    chosen = min(trace, key=lambda z: (z["validation_hierarchical_mse"], z["lambda"]))
    fit = train | valid
    intercept, coef = fit_ridge(x[fit], y[fit], hierarchical_weights(usable.loc[fit]), mean, scale, chosen["lambda"])
    evaluate = np.isin(split, ["HISTORY", "TEST"])
    pred = intercept + (x[evaluate] - mean) / scale @ coef
    scored = usable.loc[evaluate, ["sample_id", "event_id", "issuer", "date", "sample_kind", "split", "session", "second_index"]].copy()
    scored["squared_error"] = (y[evaluate] - pred) ** 2
    return chosen, trace, scored, {"median": median, "mean": mean, "scale": scale, "intercept": intercept, "coef": coef, "columns": columns}


def losses(scored: pd.DataFrame, horizon: int, model: str, fit_spec: str, venue: str, shift: int) -> list[dict]:
    out = []
    predictor_rel = scored.second_index.to_numpy(int) - 600
    target_rel = predictor_rel + horizon
    for window, (lo, hi) in WINDOWS.items():
        mask = (predictor_rel >= lo) & (target_rel < hi)
        for keys, group in scored.loc[mask].groupby(["sample_id", "event_id", "issuer", "date", "sample_kind", "split", "session"], sort=False):
            out.append({"venue": venue, "grid_shift_ms": shift, "horizon_seconds": horizon, "fit_spec": fit_spec, "model": model, "window": window, "sample_id": keys[0], "event_id": keys[1], "issuer": keys[2], "date": keys[3], "sample_kind": keys[4], "split": keys[5], "session": keys[6], "n": len(group), "sse": float(group.squared_error.sum()), "mean_loss": float(group.squared_error.mean())})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", required=True, type=Path)
    ap.add_argument("--es-features", required=True, type=Path)
    ap.add_argument("--roster", required=True, type=Path)
    ap.add_argument("--base-code", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--venue", choices=("XNAS.ITCH", "ARCX.PILLAR"))
    ap.add_argument("--grid-shift-ms", type=int, choices=(0, 500))
    args = ap.parse_args()
    base = load(args.base_code, "earnings_base")
    raw = pd.read_parquet(args.features)
    es = pd.read_parquet(args.es_features)
    roster = pd.read_csv(args.roster)
    if args.venue:
        raw = raw[raw.venue == args.venue].copy()
    if args.grid_shift_ms is not None:
        raw = raw[raw.grid_shift_ms == args.grid_shift_ms].copy(); es = es[es.grid_shift_ms == args.grid_shift_ms].copy()
    es = es_transform(es, base.QUOTE, base.TRADE)
    output, validation, artifacts = [], [], {}
    for venue in sorted(raw.venue.unique()):
        for shift in sorted(raw.grid_shift_ms.unique()):
            source = raw[(raw.venue == venue) & (raw.grid_shift_ms == shift)].copy()
            for symbol in source.symbol.unique():
                mask = source.symbol == symbol
                source.loc[mask, base.QUOTE + base.TRADE] = base.transform_values(source.loc[mask, base.QUOTE + base.TRADE])[base.QUOTE + base.TRADE]
            for horizon in HORIZONS:
                parts = []
                target_name = f"y_{horizon}s_bp"
                for sample_id, sample in source.groupby("sample_id", sort=False):
                    issuer = str(sample.issuer.iloc[0])
                    try:
                        panel = target_panel(sample, roster, base.QUOTE + base.TRADE, issuer, target_name)
                    except (RuntimeError, KeyError, ValueError, pd.errors.MergeError):
                        continue
                    for col in ("sample_id", "event_id", "issuer", "sample_kind", "split", "anchor_utc", "anchor_et"):
                        panel[col] = sample[col].iloc[0]
                    clock = str(panel.anchor_et.iloc[0])
                    panel["session"] = "PREMARKET" if clock < "09:30:00" else ("RTH" if clock < "16:00:00" else "AFTER_HOURS")
                    parts.append(panel)
                if not parts:
                    continue
                panel = pd.concat(parts, ignore_index=True)
                es_cols = ["sample_id", "grid_shift_ms", "second_index", *base.QUOTE, *base.TRADE]
                renamed = es.loc[es.grid_shift_ms == shift, es_cols].rename(columns={x: "es__" + x for x in base.QUOTE + base.TRADE})
                panel = panel.merge(renamed, on=["sample_id", "grid_shift_ms", "second_index"], how="left", validate="many_to_one") if "grid_shift_ms" in panel else panel.assign(grid_shift_ms=shift).merge(renamed, on=["sample_id", "grid_shift_ms", "second_index"], how="left", validate="many_to_one")
                panel["target"] = panel["stock__target"]
                control_frame, control_cols = controls(panel)
                panel = pd.concat([panel, control_frame], axis=1)
                model_cols = blocks(base, control_cols, base.TRADE)
                own = {}
                for model in MODELS:
                    own[model] = fit_one(panel, model_cols[model], base.LAMBDAS)
                fixed = own["A2"][0]["lambda"]
                for fit_spec in FIT_SPECS:
                    for model in MODELS:
                        result = own[model] if fit_spec == "OWN_LAMBDA" else fit_one(panel, model_cols[model], np.asarray([fixed]))
                        chosen, trace, scored, artifact = result
                        for row in trace:
                            validation.append({"venue": venue, "grid_shift_ms": int(shift), "horizon_seconds": horizon, "fit_spec": fit_spec, "model": model, "selected": row["lambda"] == chosen["lambda"], **row})
                        output.extend(losses(scored, horizon, model, fit_spec, venue, int(shift)))
                        artifacts[f"{venue}|{shift}|{horizon}|{fit_spec}|{model}"] = artifact
    args.out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(output).to_csv(args.out / "SAMPLE_MODEL_LOSSES.csv", index=False)
    pd.DataFrame(validation).to_csv(args.out / "VALIDATION_TRACE.csv", index=False)
    with (args.out / "FITTED_OBJECTS.pkl").open("wb") as handle:
        pickle.dump(artifacts, handle, protocol=pickle.HIGHEST_PROTOCOL)
    receipt = {"status": "COMPLETE_EARNINGS_MODELS_ON_SCC", "code_sha256": digest(Path(__file__)), "loss_rows": len(output), "validation_rows": len(validation), "models": list(MODELS), "horizons_seconds": list(HORIZONS), "windows": WINDOWS, "venues": sorted(raw.venue.unique().tolist()), "grid_shifts_ms": sorted(int(x) for x in raw.grid_shift_ms.unique()), "external_test_refit_or_rescale": False, "fitted_objects_stay_on_scc": True}
    (args.out / "MODEL_RECEIPT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
