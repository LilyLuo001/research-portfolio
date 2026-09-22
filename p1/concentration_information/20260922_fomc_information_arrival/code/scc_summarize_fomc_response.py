#!/usr/bin/env python3
"""Create copy-safe FOMC response endpoints and timing diagnostics from DBN."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import databento as db
import numpy as np
import pandas as pd
from databento_dbn import MBP1Msg, UNDEF_ORDER_SIZE, UNDEF_PRICE


NS = 1_000_000_000
ENDPOINTS_MS = (100, 500, 1000, 2000, 5000, 10000, 30000, 60000, 300000, 600000)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for part in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def enum_value(value: object) -> str:
    return str(getattr(value, "value", value))


def bbo(record: MBP1Msg):
    level = record.levels[0]
    bid, ask, bid_size, ask_size = map(int, (level.bid_px, level.ask_px, level.bid_sz, level.ask_sz))
    if bid == UNDEF_PRICE or ask == UNDEF_PRICE or bid_size == UNDEF_ORDER_SIZE or ask_size == UNDEF_ORDER_SIZE:
        return None
    if min(bid, ask, bid_size, ask_size) <= 0 or ask < bid:
        return None
    return bid / 1e9, ask / 1e9, float(bid_size), float(ask_size)


def decode(path: Path):
    store = db.DBNStore.from_file(path)
    names = {int(span["symbol"]): raw.upper().strip()
             for raw, spans in store.metadata.mappings.items() for span in spans}
    rows: dict[str, list] = {}
    for order, record in enumerate(store):
        if not isinstance(record, MBP1Msg):
            continue
        symbol = names.get(int(record.instrument_id))
        if symbol is None:
            continue
        rows.setdefault(symbol, []).append((int(record.ts_event), int(record.sequence), order,
                                            enum_value(record.action), bbo(record)))
    output = {}
    for symbol, values in rows.items():
        values.sort(key=lambda row: (row[0], row[1], row[2]))
        state = None; times = []; bid = []; ask = []; mid = []; spread = []
        for ts, _sequence, _order, action, quote in values:
            state = None if action == "R" or quote is None else quote
            times.append(ts)
            if state is None:
                bid.append(math.nan); ask.append(math.nan); mid.append(math.nan); spread.append(math.nan)
            else:
                b, a, _bs, _az = state; m = (b + a) / 2
                bid.append(b); ask.append(a); mid.append(m); spread.append((a - b) / m * 1e4)
        output[symbol] = {"t": np.asarray(times, np.int64), "bid": np.asarray(bid, float),
                          "ask": np.asarray(ask, float), "mid": np.asarray(mid, float),
                          "spread_bp": np.asarray(spread, float)}
    return output


def state(data: dict, times: np.ndarray):
    pos = np.searchsorted(data["t"], times, side="right") - 1
    values = {name: np.full(len(times), np.nan) for name in ("bid", "ask", "mid", "spread_bp")}
    state_age = np.full(len(times), np.nan)
    good = pos >= 0
    for name in values:
        values[name][good] = data[name][pos[good]]
    state_age[good] = (times[good] - data["t"][pos[good]]) / 1e6
    values["state_age_ms"] = state_age
    return values


def mid_updates(data: dict):
    t, mid = data["t"], data["mid"]
    if not len(t):
        return np.asarray([], np.int64)
    last = np.r_[np.flatnonzero(t[1:] != t[:-1]), len(t) - 1]
    t, mid = t[last], mid[last]
    change = np.zeros(len(t), bool)
    change[1:] = np.isfinite(mid[1:]) & np.isfinite(mid[:-1]) & (mid[1:] != mid[:-1])
    return t[change]


def update_age(data: dict, times: np.ndarray):
    updates = mid_updates(data); answer = np.full(len(times), np.nan)
    pos = np.searchsorted(updates, times, side="right") - 1; good = pos >= 0
    answer[good] = (times[good] - updates[pos[good]]) / 1e6
    return answer


def bp_change(value: np.ndarray, base: float):
    answer = np.full(len(value), np.nan)
    good = np.isfinite(value) & np.isfinite(base) & (value > 0) & (base > 0)
    answer[good] = 1e4 * (np.log(value[good]) - np.log(base))
    return answer


def tick_bp(data: dict, event_ns: int, baseline: float):
    keep = (data["t"] >= event_ns - 600 * NS) & (data["t"] < event_ns)
    prices = np.r_[data["bid"][keep], data["ask"][keep]]
    prices = np.unique(prices[np.isfinite(prices) & (prices > 0)])
    difference = np.diff(prices); difference = difference[difference > 1e-10]
    if not len(difference) or not np.isfinite(baseline) or baseline <= 0:
        return math.nan
    return float(np.quantile(difference, .01) / baseline * 1e4)


def threshold_parts(data: dict, event_ns: int, baseline: float):
    endpoints = np.arange(event_ns - 600 * NS, event_ns - 59 * NS, NS, dtype=np.int64)
    values = state(data, endpoints)["mid"]
    returns = 1e4 * np.diff(np.log(values), prepend=np.nan)
    sample = returns[np.isfinite(returns)]
    median = float(np.median(sample)) if len(sample) else math.nan
    mad = float(1.4826 * np.median(np.abs(sample - median))) if len(sample) else math.nan
    near = np.arange(event_ns - 60 * NS, event_ns, NS, dtype=np.int64)
    spreads = state(data, near)["spread_bp"]
    spread = float(np.nanmedian(spreads)) if np.isfinite(spreads).any() else math.nan
    return mad, spread, tick_bp(data, event_ns, baseline)


def detection(data: dict, event_ns: int, shift_ms: int, multiplier: int):
    base = state(data, np.asarray([event_ns - 1], np.int64))["mid"][0]
    mad, spread, tick = threshold_parts(data, event_ns, base)
    finite = [x for x in (multiplier * mad, spread, tick) if np.isfinite(x)]
    if not np.isfinite(base) or not finite:
        return {"status": "MISSING_BASELINE_OR_THRESHOLD", "detection_seconds": math.nan,
                "threshold_bp": max(finite) if finite else math.nan, "mad_bp": mad,
                "spread_floor_bp": spread, "tick_floor_bp": tick}
    threshold = max(finite)
    grid = np.arange(event_ns + shift_ms * 1_000_000, event_ns + 600 * NS, NS, dtype=np.int64)
    moves = bp_change(state(data, grid)["mid"], base)
    found = None
    for index in range(len(moves) - 2):
        values = moves[index:index + 3]
        if np.all(np.isfinite(values)) and np.all(np.abs(values) > threshold) and np.all(np.sign(values) == np.sign(values[0])):
            found = index; break
    return {"status": "DETECTED" if found is not None else "RIGHT_CENSORED_600S",
            "detection_seconds": (shift_ms / 1000 + found) if found is not None else math.nan,
            "threshold_bp": threshold, "mad_bp": mad,
            "spread_floor_bp": spread, "tick_floor_bp": tick}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--download-receipt", required=True, type=Path)
    ap.add_argument("--analysis-dates", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    receipt = json.loads(args.download_receipt.read_text())
    dates = pd.read_csv(args.analysis_dates, dtype=str).set_index("date")
    endpoints = []; timings = []; sources = []
    for item in receipt["files"]:
        if not item.get("status", "").endswith("NATIVE_DBN_ON_SCC"):
            raise RuntimeError(f"incomplete source {item.get('request_id')}")
        day = str(item["date"]); metadata = dates.loc[day]
        event_ns = int(pd.Timestamp(day + " 14:00:00", tz="America/New_York").tz_convert("UTC").value)
        decoded = decode(Path(item["path"]))
        for raw_symbol, data in decoded.items():
            symbol = item.get("actual_raw_symbol", raw_symbol) if item["dataset"] == "GLBX.MDP3" else raw_symbol
            baseline_state = state(data, np.asarray([event_ns - 1], np.int64))
            base = {name: baseline_state[name][0] for name in ("bid", "ask", "mid")}
            query = event_ns + np.asarray(ENDPOINTS_MS, np.int64) * 1_000_000
            values = state(data, query); ages = update_age(data, query)
            for i, endpoint_ms in enumerate(ENDPOINTS_MS):
                endpoints.append({
                    "date": day, "event_id": metadata.event_id, "sample_kind": metadata.sample_kind,
                    "split": metadata.split, "dataset": item["dataset"], "symbol": symbol,
                    "endpoint_ms": endpoint_ms,
                    "mid_change_bp": bp_change(np.asarray([values["mid"][i]]), base["mid"])[0],
                    "bid_change_bp": bp_change(np.asarray([values["bid"][i]]), base["bid"])[0],
                    "ask_change_bp": bp_change(np.asarray([values["ask"][i]]), base["ask"])[0],
                    "spread_bp": values["spread_bp"][i], "quote_state_age_ms": values["state_age_ms"][i],
                    "mid_update_age_ms": ages[i], "valid": bool(np.isfinite(values["mid"][i])),
                })
            for shift in (0, 500):
                for multiplier in (2, 3, 4):
                    timings.append({
                        "date": day, "event_id": metadata.event_id, "sample_kind": metadata.sample_kind,
                        "split": metadata.split, "dataset": item["dataset"], "symbol": symbol,
                        "grid_shift_ms": shift, "mad_multiplier": multiplier,
                        **detection(data, event_ns, shift, multiplier),
                    })
        sources.append({"request_id": item["request_id"], "dataset": item["dataset"], "date": day,
                        "raw_sha256": item["sha256"], "decoded_symbols": len(decoded)})
    args.out.mkdir(parents=True, exist_ok=True)
    end = pd.DataFrame(endpoints); timing = pd.DataFrame(timings)
    end.to_csv(args.out / "EVENT_RESPONSE_SUMMARY.csv", index=False)
    timing.to_csv(args.out / "TIMING_DIAGNOSTICS.csv", index=False)
    support = end.groupby(["date", "event_id", "sample_kind", "split", "dataset"], as_index=False).agg(
        symbols=("symbol", "nunique"), endpoint_rows=("symbol", "size"), valid_fraction=("valid", "mean"),
        median_state_age_ms=("quote_state_age_ms", "median"), median_update_age_ms=("mid_update_age_ms", "median"))
    support.to_csv(args.out / "EVENT_SUPPORT.csv", index=False)
    receipt_out = {"status": "COMPLETE_FOMC_RESPONSE_SUMMARY", "download_receipt_sha256": digest(args.download_receipt),
                   "source_files": len(sources), "endpoint_rows": len(end), "timing_rows": len(timing),
                   "endpoints_ms": list(ENDPOINTS_MS), "source_records_stay_on_scc": True,
                   "clock": "ts_event ordered by sequence/source order; not SIP receipt time",
                   "baseline": "last state at or before 14:00 ET minus 1ns; invalid state stays invalid"}
    (args.out / "RESPONSE_RECEIPT.json").write_text(json.dumps(receipt_out, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt_out, sort_keys=True))


if __name__ == "__main__":
    main()
