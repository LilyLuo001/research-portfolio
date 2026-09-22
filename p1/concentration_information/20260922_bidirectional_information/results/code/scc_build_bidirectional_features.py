#!/usr/bin/env python3
"""Build the frozen per-second bidirectional feature table on SCC.

Native DBN and the resulting security-time panel remain on SCC. The script
uses ts_event, orders equal timestamps by sequence/source order, invalidates an
undefined/cleared BBO, and never backfills a future state into a predictor.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import databento as db
import numpy as np
import pandas as pd
from databento_dbn import MBP1Msg, UNDEF_ORDER_SIZE, UNDEF_PRICE

NS = 1_000_000_000
WINDOWS = (("0_100ms", 100_000_000), ("100ms_1s", 900_000_000), ("1s_5s", 4_000_000_000))
HORIZONS = (("100ms", 100_000_000), ("1s", NS), ("5s", 5 * NS))


def enum_value(x: object) -> str:
    return str(getattr(x, "value", x))


def valid_bbo(record: MBP1Msg):
    level = record.levels[0]
    bid, ask, bid_size, ask_size = map(int, (level.bid_px, level.ask_px, level.bid_sz, level.ask_sz))
    if bid == UNDEF_PRICE or ask == UNDEF_PRICE or bid_size == UNDEF_ORDER_SIZE or ask_size == UNDEF_ORDER_SIZE:
        return None
    if min(bid, ask, bid_size, ask_size) <= 0 or ask < bid:
        return None
    return bid / 1e9, ask / 1e9, float(bid_size), float(ask_size)


def mappings(store) -> dict[int, str]:
    return {
        int(span["symbol"]): raw.upper().strip()
        for raw, spans in store.metadata.mappings.items()
        for span in spans
    }


def decode(path: Path) -> dict[str, dict[str, np.ndarray]]:
    store = db.DBNStore.from_file(path)
    symbol_map = mappings(store)
    rows: dict[str, list] = {}
    for source_order, record in enumerate(store):
        if not isinstance(record, MBP1Msg):
            continue
        symbol = symbol_map.get(int(record.instrument_id))
        if symbol is None:
            continue
        rows.setdefault(symbol, []).append((
            int(record.ts_event), int(record.sequence), source_order,
            enum_value(record.action), enum_value(record.side),
            int(record.price) / 1e9 if int(record.price) != UNDEF_PRICE else math.nan,
            int(record.size), valid_bbo(record),
        ))
    decoded = {}
    for symbol, values in rows.items():
        values.sort(key=lambda x: (x[0], x[1], x[2]))
        state = None
        state_t, mid, spread, bid_depth, ask_depth, quote_valid = [], [], [], [], [], []
        trade_t, trade_dollars, trade_sign = [], [], []
        for ts, _sequence, _order, action, side, price, size, bbo in values:
            if action == "T":
                trade_t.append(ts)
                trade_dollars.append(price * size if math.isfinite(price) else math.nan)
                trade_sign.append(1.0 if side == "B" else (-1.0 if side == "A" else math.nan))
            if action == "R" or bbo is None:
                state = None
            else:
                state = bbo
            state_t.append(ts)
            if state is None:
                mid.append(math.nan); spread.append(math.nan); bid_depth.append(math.nan); ask_depth.append(math.nan); quote_valid.append(False)
            else:
                b, a, bs, az = state
                m = (b + a) / 2
                mid.append(m); spread.append((a - b) / m * 1e4); bid_depth.append(bs); ask_depth.append(az); quote_valid.append(True)
        decoded[symbol] = {
            "state_t": np.asarray(state_t, dtype=np.int64), "mid": np.asarray(mid, float),
            "spread_bp": np.asarray(spread, float), "bid_depth": np.asarray(bid_depth, float),
            "ask_depth": np.asarray(ask_depth, float), "quote_valid": np.asarray(quote_valid, bool),
            "trade_t": np.asarray(trade_t, dtype=np.int64), "trade_dollars": np.asarray(trade_dollars, float),
            "trade_sign": np.asarray(trade_sign, float),
        }
    return decoded


def state_at(data: dict, times: np.ndarray, field: str) -> np.ndarray:
    pos = np.searchsorted(data["state_t"], times, side="right") - 1
    result = np.full(len(times), np.nan)
    valid = pos >= 0
    result[valid] = data[field][pos[valid]]
    return result


def log_return(data: dict, start: np.ndarray, end: np.ndarray) -> np.ndarray:
    before, after = state_at(data, start, "mid"), state_at(data, end, "mid")
    answer = np.full(len(start), np.nan)
    valid = np.isfinite(before) & np.isfinite(after) & (before > 0) & (after > 0)
    answer[valid] = 1e4 * (np.log(after[valid]) - np.log(before[valid]))
    return answer


def trade_interval(data: dict, start: np.ndarray, end: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    left = np.searchsorted(data["trade_t"], start, side="right")
    right = np.searchsorted(data["trade_t"], end, side="right")
    flow, volume, native_share = np.zeros(len(start)), np.zeros(len(start)), np.full(len(start), np.nan)
    dollars, signs = data["trade_dollars"], data["trade_sign"]
    for i, (lo, hi) in enumerate(zip(left, right)):
        if lo == hi:
            # No trade is an observed zero flow and zero volume, not missing data.
            native_share[i] = 1.0
            continue
        d, s = dollars[lo:hi], signs[lo:hi]
        good_d = np.isfinite(d)
        volume[i] = float(np.sum(d[good_d]))
        known = good_d & np.isfinite(s)
        native_share[i] = float(np.sum(known) / np.sum(good_d)) if np.sum(good_d) else math.nan
        # A partially/fully unknown aggressor interval is not an actual zero.
        flow[i] = float(np.sum(d[known] * s[known])) if np.sum(good_d) and np.all(known[good_d]) else math.nan
    return flow, volume, native_share


def build_symbol(date: str, venue: str, symbol: str, data: dict, core_start: int, core_end: int, shift_ms: int) -> pd.DataFrame:
    shift = shift_ms * 1_000_000
    grid = np.arange(core_start + shift, core_end, NS, dtype=np.int64)
    frame = pd.DataFrame({"date": date, "t_ns": grid, "symbol": symbol, "venue": venue, "grid_shift_ms": shift_ms})
    frame["minute_bin_5m"] = ((grid - core_start) // (300 * NS)).astype(int)
    frame["quote_valid"] = np.isfinite(state_at(data, grid, "mid"))
    intervals = (
        ("0_100ms", grid - 100_000_000, grid),
        ("100ms_1s", grid - NS, grid - 100_000_000),
        ("1s_5s", grid - 5 * NS, grid - NS),
    )
    for name, start, end in intervals:
        frame[f"ret_{name}"] = log_return(data, start, end)
        flow, _volume, _share = trade_interval(data, start, end)
        frame[f"flow_{name}"] = flow
    frame["spread_bp"] = state_at(data, grid, "spread_bp")
    frame["bid_depth"] = state_at(data, grid, "bid_depth")
    frame["ask_depth"] = state_at(data, grid, "ask_depth")
    _flow5, volume5, native5 = trade_interval(data, grid - 5 * NS, grid)
    frame["volume_5s"] = volume5
    frame["native_direction_share_5s"] = native5
    for name, horizon in HORIZONS:
        frame[f"y_{name}_bp"] = log_return(data, grid, grid + horizon)
    return frame


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--download-receipt", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--receipt", required=True, type=Path)
    args = ap.parse_args()
    receipt = json.loads(args.download_receipt.read_text())
    if receipt.get("status") != "COMPLETE_NATIVE_DBN_ON_SCC":
        raise RuntimeError("complete download receipt required")
    request_by_id = {x["request_id"]: x for x in receipt["selected_variant"]["requests"]}
    frames, source_counts = [], []
    for item in receipt["files"]:
        if item.get("status") != "DOWNLOADED_NATIVE_DBN_ON_SCC":
            raise RuntimeError("incomplete source file in receipt")
        request = request_by_id[item["request_id"]]
        path = Path(item["path"])
        decoded = decode(path)
        request_start = int(pd.Timestamp(request["start_utc"]).value)
        request_end = int(pd.Timestamp(request["end_utc"]).value)
        core_start, core_end = request_start + 60 * NS, request_end - 60 * NS
        date = request["start_utc"][:10]
        for symbol in request["symbols"]:
            if symbol not in decoded:
                source_counts.append({"request_id": item["request_id"], "symbol": symbol, "status": "NO_DECODED_ROWS"})
                continue
            for shift_ms in (0, 500):
                frames.append(build_symbol(date, request["dataset"], symbol, decoded[symbol], core_start, core_end, shift_ms))
            source_counts.append({"request_id": item["request_id"], "symbol": symbol, "status": "FEATURES_BUILT"})
    if not frames:
        raise RuntimeError("no feature rows built")
    table = pd.concat(frames, ignore_index=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    table.to_parquet(args.out, index=False)
    summary = {
        "status": "COMPLETE_FEATURE_PANEL_ON_SCC", "feature_path": str(args.out),
        "rows": len(table), "dates": int(table.date.nunique()), "symbols": int(table.symbol.nunique()),
        "venues": sorted(table.venue.unique().tolist()), "grid_shifts_ms": sorted(table.grid_shift_ms.unique().tolist()),
        "source_status_counts": pd.DataFrame(source_counts).status.value_counts().to_dict(),
        "raw_or_feature_rows_exported_locally": False,
    }
    args.receipt.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
