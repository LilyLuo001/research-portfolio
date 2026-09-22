#!/usr/bin/env python3
"""Deterministic structural checks for the committed aggregate pilot outputs."""

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

filters = pd.read_csv(ROOT / "FILTER_COUNTS.csv")
diag = pd.read_csv(ROOT / "QUOTE_DIAGNOSTICS.csv")
pairs = pd.read_csv(ROOT / "PAIR_COUNTS.csv")
response = pd.read_csv(ROOT / "TRADE_RESPONSE.csv")
summary = pd.read_csv(ROOT / "EVENT_SUMMARY.csv")

assert len(filters) == 36 and not filters.duplicated(["file", "instrument"]).any()
assert len(diag) == 72 and not diag.duplicated(["file", "axis", "instrument"]).any()
assert len(pairs) == 972 and not pairs.duplicated(["file", "axis", "variant", "threshold_us", "category"]).any()
assert len(response) == 648 and not response.duplicated(["file", "instrument", "pair_group", "trade_sign", "horizon_seconds"]).any()
assert len(summary) == 18 and not summary.duplicated(["window", "dataset"]).any()

assert int(filters.total_mbp1_records.sum()) == 12_298_752
assert int(filters.trade_records.sum()) == 513_606
assert int(filters.analysis_window_trade_records.sum()) == 482_020
assert int(filters.support_only_trade_records.sum()) == 31_586
assert int(filters.fill_records.sum()) == 70
assert int(filters.flag_bad_ts_recv_records.sum()) == 0
assert int(filters.flag_maybe_bad_book_records.sum()) == 0
assert int(filters.invalid_bbo_records.sum()) == 0

event_diag = diag[diag.axis.eq("EVENT")]
trade_total = int((event_diag.classified_buy_trades + event_diag.classified_sell_trades + event_diag.unknown_direction_trades).sum())
assert trade_total == 482_020
assert int(event_diag.native_side_classified_trades.sum()) == 411_837
assert int(event_diag.midpoint_fallback_classified_trades.sum()) == 50_457
assert int(event_diag.native_side_missing_and_midpoint_unknown_trades.sum()) == 19_726
assert int(filters.raw_native_side_classified_trades.sum()) == 438_478
assert int(filters.raw_midpoint_fallback_classified_trades.sum()) == 54_347
assert int(filters.raw_unknown_direction_trades.sum()) == 20_781

# Category near-pair counts partition ALL exactly for every axis/variant/threshold.
key = ["file", "axis", "variant", "threshold_us"]
all_rows = pairs[pairs.category.eq("ALL")].set_index(key)
parts = pairs[pairs.category.isin(["B_B", "S_S", "B_S", "S_B", "UNKNOWN_EITHER"])].groupby(key).near_pairs.sum()
assert np.array_equal(all_rows.loc[parts.index].near_pairs.to_numpy(), parts.to_numpy())

# Main background formula and response identity.
calc = all_rows.near_pairs - all_rows.background_scale * all_rows.background_pairs
assert np.allclose(calc, all_rows.excess_pairs)
assert float(response.identity_max_abs_bp.max()) < 1e-9

# The central descriptive ranking reported in RESULTS: AAPL controls exceed matched RTH.
s = summary.set_index(["window", "dataset"])
for date in ("AAPL_FEB", "AAPL_AUG"):
    for venue in ("ARCX.PILLAR", "XNAS.ITCH"):
        assert s.loc[(date + "_CTRL", venue), "excess_per_1000_stock_event"] > s.loc[(date + "_RTH", venue), "excess_per_1000_stock_event"]

print("PASS: aggregate shapes, keys, partitions, formulas, quality flags, identity, and decisive ranking")
