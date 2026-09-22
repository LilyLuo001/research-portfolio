#!/usr/bin/env python3
"""Small deterministic checks for the bidirectional estimator."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("models", HERE / "run_bidirectional_models.py")
models = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["models"] = models
spec.loader.exec_module(models)


def make_features() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(20260922)
    dates = [f"2023-01-{d:02d}" for d in range(2, 10)]
    symbols = ["AAA", "BBB", "CCC", "SPY"]
    rows = []
    for di, date in enumerate(dates):
        spy_signal = rng.normal(size=80)
        stock_signal = {s: rng.normal(size=80) for s in symbols[:-1]}
        for shift in (0, 500):
            for k in range(80):
                t = (di + 1) * 100_000_000_000_000 + shift * 1_000_000 + k * 1_000_000_000
                for symbol in symbols:
                    own = spy_signal[k] if symbol == "SPY" else stock_signal[symbol][k]
                    base = {
                        "date": date, "t_ns": t, "symbol": symbol, "venue": "XNAS.ITCH",
                        "grid_shift_ms": shift, "minute_bin_5m": min(k // 14, 5), "quote_valid": 1,
                        "ret_0_100ms": own, "ret_100ms_1s": 0.5 * own,
                        "ret_1s_5s": -0.2 * own, "flow_0_100ms": own + rng.normal(scale=.2),
                        "flow_100ms_1s": rng.normal(), "flow_1s_5s": rng.normal(),
                        "spread_bp": 1 + abs(rng.normal(scale=.1)), "bid_depth": 100 + rng.normal(),
                        "ask_depth": 100 + rng.normal(), "volume_5s": 500 + abs(rng.normal(scale=20)),
                        "native_direction_share_5s": .9,
                    }
                    if symbol == "SPY":
                        # Stock AAA has a known incremental path to future SPY.
                        target = 0.8 * stock_signal["AAA"][k] + rng.normal(scale=.15)
                    elif symbol == "AAA":
                        # SPY has a known incremental path to future AAA.
                        target = 0.9 * spy_signal[k] + rng.normal(scale=.15)
                    else:
                        target = rng.normal(scale=.5)
                    base.update(y_100ms_bp=target, y_1s_bp=target, y_5s_bp=target)
                    rows.append(base)
    roster = pd.DataFrame([
        {"symbol": "AAA", "report_weight": .5, "weight_tier": "TOP10", "liquidity_tier": "HIGH"},
        {"symbol": "BBB", "report_weight": .3, "weight_tier": "MID40", "liquidity_tier": "HIGH"},
        {"symbol": "CCC", "report_weight": .2, "weight_tier": "LOW50", "liquidity_tier": "LOW"},
    ])
    date_manifest = pd.DataFrame({"date": dates, "split": ["train"] * 4 + ["valid"] * 2 + ["test"] * 2})
    return pd.DataFrame(rows), roster, date_manifest


def main() -> None:
    features, roster, dates = make_features()
    models.validate_inputs(features, roster, dates)
    panel = models.build_panel(features, roster, "XNAS.ITCH", 0)
    split = {x: set(dates.loc[dates["split"] == x, "date"]) for x in ("train", "valid", "test")}
    gains, daily = models.run_pair_models(panel, split, "XNAS.ITCH", 0)
    lookup = {(x["symbol"], x["direction"], x["horizon"]): x for x in gains}
    assert lookup[("AAA", "ETF_TO_STOCK", "5s")]["G"] > .7
    assert lookup[("AAA", "STOCK_TO_ETF", "5s")]["G"] > .7
    assert len({x["date"] for x in daily}) == 2
    ablation = models.group_ablation(features, roster, split, "XNAS.ITCH", 0)
    assert {x["model"] for x in ablation} == {"SPY_ONLY", "ALL_STOCKS", "WITHOUT_TOP10", "WITHOUT_MID40", "WITHOUT_LOW50"}

    # Same baseline/full observation mask: one unavailable source row removes the row from both.
    first_spy = features.index[features["symbol"] == "SPY"][0]
    features.loc[first_spy, "flow_0_100ms"] = np.nan
    panel2 = models.build_panel(features, roster, "XNAS.ITCH", 0)
    result = models.predictions_for_model(panel2[panel2["symbol"] == "AAA"].reset_index(drop=True), "ETF_TO_STOCK", "5s", split)
    assert result["n_train"] < 4 * 80
    print("PASS: direction, date split, held-out gain, group ablation, and common missingness mask")


if __name__ == "__main__":
    main()
