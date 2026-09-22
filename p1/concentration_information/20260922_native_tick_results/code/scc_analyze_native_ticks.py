#!/usr/bin/env python3
"""Aggregate native MBP-1 tick diagnostics on SCC; never export raw rows."""
from __future__ import annotations

import csv
import glob
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import databento as db
import numpy as np
from databento_dbn import MBP1Msg, UNDEF_ORDER_SIZE, UNDEF_PRICE


ROOT = Path("/scratch/qluo/native_tick_pilot_20260922")
NS = 1_000_000_000
US = 1_000
THRESHOLDS_US = (20, 100, 1000)
BACKGROUND_US = ((-1200, -1000), (1000, 1200))
RESPONSE_SECONDS = (1, 5, 60)
HIST_WIDTH_US = 50
HIST_MIN_US, HIST_MAX_US = -5000, 5000
ANCHORS = {
    "XOM_JAN": np.datetime64("2023-01-31T11:30:00", "ns").astype(np.int64),
    "AAPL_FEB": np.datetime64("2023-02-02T21:30:00", "ns").astype(np.int64),
    "AAPL_AUG": np.datetime64("2023-08-03T20:30:00", "ns").astype(np.int64),
}


def analysis_bounds():
    """Return start-inclusive/end-exclusive economic windows by DBN basename."""
    requests = json.loads((ROOT / "REQUEST_MANIFEST.json").read_text())
    out = {}
    for request in requests:
        start = np.datetime64(request["start"].removesuffix("Z"), "ns").astype(np.int64) + 120 * NS
        end = np.datetime64(request["end"].removesuffix("Z"), "ns").astype(np.int64) - 65 * NS
        out[Path(request["path"]).name] = (int(start), int(end))
    return out


def value(x) -> str:
    return str(getattr(x, "value", x))


def bbo(record):
    level = record.levels[0]
    bid, ask = int(level.bid_px), int(level.ask_px)
    bsz, asz = int(level.bid_sz), int(level.ask_sz)
    if bid == UNDEF_PRICE or ask == UNDEF_PRICE or bsz == UNDEF_ORDER_SIZE or asz == UNDEF_ORDER_SIZE:
        return None
    if min(bid, ask, bsz, asz) <= 0 or ask < bid:
        return None
    return bid / 1e9, ask / 1e9


def mapping(store):
    out = {}
    for raw, spans in store.metadata.mappings.items():
        for span in spans:
            out[int(span["symbol"])] = raw.upper().strip()
    return out


def write_csv(path: Path, rows: list[dict]):
    if not rows:
        raise RuntimeError(f"empty output: {path}")
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def filename_meta(path: Path):
    name = path.name.removesuffix("_mbp1.dbn.zst")
    if name.endswith("_XNAS_ITCH"):
        return name.removesuffix("_XNAS_ITCH"), "XNAS.ITCH"
    if name.endswith("_ARCX_PILLAR"):
        return name.removesuffix("_ARCX_PILLAR"), "ARCX.PILLAR"
    raise ValueError(path)


def load_file(path: Path):
    store = db.DBNStore.from_file(path)
    idmap = mapping(store)
    symbols = {s for s in idmap.values() if s in {"AAPL", "XOM", "SPY"}}
    stock = "AAPL" if "AAPL" in symbols else "XOM"
    records = {stock: [], "SPY": []}
    action_counts = {stock: Counter(), "SPY": Counter()}
    invalid_counts = Counter()
    previous_event = {stock: None, "SPY": None}
    previous_recv = {stock: None, "SPY": None}
    diagnostic = {stock: Counter(), "SPY": Counter()}
    for idx, record in enumerate(store):
        if not isinstance(record, MBP1Msg):
            continue
        symbol = idmap.get(int(record.instrument_id))
        if symbol not in records:
            continue
        action = value(record.action)
        flags = int(record.flags)
        action_counts[symbol][action] += 1
        event_ts, recv_ts = int(record.ts_event), int(record.ts_recv)
        if previous_event[symbol] is not None and event_ts < previous_event[symbol]:
            diagnostic[symbol]["event_nonmonotonic"] += 1
        if previous_recv[symbol] is not None and recv_ts < previous_recv[symbol]:
            diagnostic[symbol]["recv_nonmonotonic"] += 1
        if previous_event[symbol] == event_ts:
            diagnostic[symbol]["event_duplicate_adjacent"] += 1
        if previous_recv[symbol] == recv_ts:
            diagnostic[symbol]["recv_duplicate_adjacent"] += 1
        previous_event[symbol], previous_recv[symbol] = event_ts, recv_ts
        diagnostic[symbol]["flag_last"] += bool(flags & 128)
        diagnostic[symbol]["flag_publisher_specific"] += bool(flags & 2)
        diagnostic[symbol]["flag_bad_ts_recv"] += bool(flags & 8)
        diagnostic[symbol]["flag_maybe_bad_book"] += bool(flags & 4)
        quote = bbo(record)
        if quote is None:
            invalid_counts[(symbol, "invalid_bbo")] += 1
            bid = ask = math.nan
        else:
            bid, ask = quote
            invalid_counts[(symbol, "valid_bbo")] += 1
        price = int(record.price) / 1e9 if int(record.price) != UNDEF_PRICE else math.nan
        size = int(record.size)
        records[symbol].append(
            (idx, event_ts, recv_ts, int(record.sequence), action, value(record.side), price, size, bid, ask, flags)
        )
    return store, stock, records, action_counts, invalid_counts, diagnostic


def make_axis(records: list[tuple], axis: str):
    ts_index = 1 if axis == "EVENT" else 2
    order = sorted(range(len(records)), key=lambda i: (records[i][ts_index], records[i][3], records[i][0]))
    quote_times, quote_bid, quote_ask = [], [], []
    trade_t, trade_price, trade_size, trade_sign, trade_sign_source, trade_pre_mid, trade_pre_spread = [], [], [], [], [], [], []
    last_quote = None
    for i in order:
        row = records[i]
        timestamp, action, native_side, price, size, bid, ask = row[ts_index], row[4], row[5], row[6], row[7], row[8], row[9]
        if action == "T":
            if last_quote is None:
                pre_mid, pre_spread = math.nan, math.nan
            else:
                pre_mid = (last_quote[0] + last_quote[1]) / 2
                pre_spread = (last_quote[1] - last_quote[0]) / pre_mid * 10_000
            if native_side == "B":
                sign, sign_source = "B", "NATIVE"
            elif native_side == "A":
                sign, sign_source = "S", "NATIVE"
            elif last_quote is not None and math.isfinite(price):
                sign = "B" if price > pre_mid else ("S" if price < pre_mid else "U")
                sign_source = "MIDPOINT" if sign != "U" else "UNKNOWN"
            else:
                sign, sign_source = "U", "UNKNOWN"
            trade_t.append(timestamp)
            trade_price.append(price)
            trade_size.append(size)
            trade_sign.append(sign)
            trade_sign_source.append(sign_source)
            trade_pre_mid.append(pre_mid)
            trade_pre_spread.append(pre_spread)
        if math.isfinite(bid) and math.isfinite(ask):
            last_quote = (bid, ask)
            quote_times.append(timestamp)
            quote_bid.append(bid)
            quote_ask.append(ask)
    sort_trade = np.argsort(np.asarray(trade_t, dtype=np.int64), kind="stable")
    return {
        "times": np.asarray(trade_t, dtype=np.int64)[sort_trade],
        "price": np.asarray(trade_price, dtype=float)[sort_trade],
        "size": np.asarray(trade_size, dtype=np.int64)[sort_trade],
        "sign": np.asarray(trade_sign, dtype="U1")[sort_trade],
        "sign_source": np.asarray(trade_sign_source, dtype="U8")[sort_trade],
        "pre_mid": np.asarray(trade_pre_mid, dtype=float)[sort_trade],
        "pre_spread_bp": np.asarray(trade_pre_spread, dtype=float)[sort_trade],
        "quote_times": np.asarray(quote_times, dtype=np.int64),
        "quote_bid": np.asarray(quote_bid, dtype=float),
        "quote_ask": np.asarray(quote_ask, dtype=float),
    }


def trim_trade_window(source, start_ns, end_ns):
    """Trim trade centers only; retain full quote support for pre/post endpoints."""
    mask = (source["times"] >= start_ns) & (source["times"] < end_ns)
    trade_fields = {"times", "price", "size", "sign", "sign_source", "pre_mid", "pre_spread_bp"}
    return {key: (value[mask] if key in trade_fields else value) for key, value in source.items()}


def pair_count(a: np.ndarray, b: np.ndarray, lo_ns: int, hi_ns: int) -> int:
    if not len(a) or not len(b):
        return 0
    left = np.searchsorted(b, a + lo_ns, side="left")
    right = np.searchsorted(b, a + hi_ns, side="left")
    return int(np.sum(right - left))


def paired_mask(a: np.ndarray, b: np.ndarray, lo_ns: int, hi_ns: int) -> np.ndarray:
    if not len(a) or not len(b):
        return np.zeros(len(a), dtype=bool)
    return np.searchsorted(b, a + hi_ns, side="left") > np.searchsorted(b, a + lo_ns, side="left")


def category_arrays(stock_axis, spy_axis, category):
    st, ss = stock_axis["times"], stock_axis["sign"]
    et, es = spy_axis["times"], spy_axis["sign"]
    if category == "ALL":
        return st, et
    if category == "UNKNOWN_EITHER":
        known_pairs = sum(
            pair_count(st[ss == a], et[es == b], -20_000, 20_000) for a in ("B", "S") for b in ("B", "S")
        )
        return None, known_pairs
    a, b = category.split("_")
    return st[ss == a], et[es == b]


def counts_for_axis(meta, stock_axis, spy_axis, axis_name, variant="ALL_TRADES"):
    if variant == "EXCLUDE_FIRST_200MS":
        sm = (stock_axis["times"] % NS) >= 200_000_000
        em = (spy_axis["times"] % NS) >= 200_000_000
        stock_axis = {**stock_axis, "times": stock_axis["times"][sm], "sign": stock_axis["sign"][sm]}
        spy_axis = {**spy_axis, "times": spy_axis["times"][em], "sign": spy_axis["sign"][em]}
    rows = []
    categories = ("ALL", "B_B", "S_S", "B_S", "S_B")
    for threshold_us in THRESHOLDS_US:
        near_width = 2 * threshold_us
        all_near = None
        known_near = 0
        for category in categories:
            st, et = category_arrays(stock_axis, spy_axis, category)
            near = pair_count(st, et, -threshold_us * US, threshold_us * US)
            background = sum(pair_count(st, et, lo * US, hi * US) for lo, hi in BACKGROUND_US)
            scale = near_width / 400
            excess = near - scale * background
            if category == "ALL":
                all_near = near
                stock_unique = int(np.sum(paired_mask(st, et, -threshold_us * US, threshold_us * US)))
                spy_unique = int(np.sum(paired_mask(et, st, -threshold_us * US, threshold_us * US)))
            else:
                known_near += near
                stock_unique = spy_unique = ""
            rows.append({
                **meta,
                "axis": axis_name,
                "variant": variant,
                "threshold_us": threshold_us,
                "category": category,
                "stock_trades": len(stock_axis["times"]),
                "spy_trades": len(spy_axis["times"]),
                "near_pairs": near,
                "background_pairs": background,
                "background_scale": scale,
                "excess_pairs": excess,
                "excess_per_1000_stock_trades": 1000 * excess / len(stock_axis["times"]) if len(stock_axis["times"]) else math.nan,
                "unique_stock_trades_paired": stock_unique,
                "unique_spy_trades_paired": spy_unique,
            })
        rows.append({
            **meta,
            "axis": axis_name,
            "variant": variant,
            "threshold_us": threshold_us,
            "category": "UNKNOWN_EITHER",
            "stock_trades": len(stock_axis["times"]),
            "spy_trades": len(spy_axis["times"]),
            "near_pairs": int(all_near - known_near),
            "background_pairs": "",
            "background_scale": "",
            "excess_pairs": "",
            "excess_per_1000_stock_trades": "",
            "unique_stock_trades_paired": "",
            "unique_spy_trades_paired": "",
        })
    return rows


def offset_histogram(meta, stock_times, spy_times, axis):
    counts = np.zeros((HIST_MAX_US - HIST_MIN_US) // HIST_WIDTH_US, dtype=np.int64)
    lo_ns, hi_ns = HIST_MIN_US * US, HIST_MAX_US * US
    for timestamp in stock_times:
        left = np.searchsorted(spy_times, timestamp + lo_ns, side="left")
        right = np.searchsorted(spy_times, timestamp + hi_ns, side="left")
        if right <= left:
            continue
        diffs_us = (spy_times[left:right] - timestamp) // US
        bins = ((diffs_us - HIST_MIN_US) // HIST_WIDTH_US).astype(int)
        np.add.at(counts, bins[(bins >= 0) & (bins < len(counts))], 1)
    return [
        {**meta, "axis": axis, "bin_left_us": HIST_MIN_US + i * HIST_WIDTH_US, "bin_right_us": HIST_MIN_US + (i + 1) * HIST_WIDTH_US, "pair_count": int(n)}
        for i, n in enumerate(counts)
    ]


def same_direction_mask(source, target, threshold_us=20):
    out = np.zeros(len(source["times"]), dtype=bool)
    for sign in ("B", "S"):
        src_idx = np.flatnonzero(source["sign"] == sign)
        target_times = target["times"][target["sign"] == sign]
        out[src_idx] = paired_mask(source["times"][src_idx], target_times, -threshold_us * US, threshold_us * US)
    return out


def response_rows(meta, symbol, source, target):
    paired = same_direction_mask(source, target)
    rows = []
    quote_mid = (source["quote_bid"] + source["quote_ask"]) / 2
    for horizon in RESPONSE_SECONDS:
        positions = np.searchsorted(source["quote_times"], source["times"] + horizon * NS, side="right") - 1
        valid_position = (positions >= 0) & (positions < len(quote_mid))
        post_mid = np.full(len(source["times"]), np.nan)
        post_mid[valid_position] = quote_mid[positions[valid_position]]
        sign_num = np.where(source["sign"] == "B", 1.0, np.where(source["sign"] == "S", -1.0, np.nan))
        denom = source["pre_mid"]
        effective = 2 * sign_num * (source["price"] - denom) / denom * 10_000
        mid_change = sign_num * (post_mid - denom) / denom * 10_000
        realized = 2 * sign_num * (source["price"] - post_mid) / denom * 10_000
        for pair_label, pair_mask in (("SAME_DIRECTION_PAIRED_20US", paired), ("NOT_SAME_DIRECTION_PAIRED_20US", ~paired)):
            for sign in ("B", "S", "ALL_SIGNED"):
                mask = pair_mask & np.isfinite(sign_num) & np.isfinite(effective) & np.isfinite(mid_change) & np.isfinite(realized)
                if sign != "ALL_SIGNED":
                    mask &= source["sign"] == sign
                values = {
                    "effective_spread_bp": effective[mask],
                    "signed_mid_change_bp": mid_change[mask],
                    "realized_spread_bp": realized[mask],
                    "pre_quoted_spread_bp": source["pre_spread_bp"][mask],
                    "trade_size": source["size"][mask].astype(float),
                }
                n = int(np.sum(mask))
                row = {**meta, "instrument": symbol, "pair_group": pair_label, "trade_sign": sign, "horizon_seconds": horizon, "n": n}
                for key, array in values.items():
                    row[f"{key}_mean"] = float(np.mean(array)) if n else math.nan
                    row[f"{key}_median"] = float(np.median(array)) if n else math.nan
                    row[f"{key}_p25"] = float(np.quantile(array, .25)) if n else math.nan
                    row[f"{key}_p75"] = float(np.quantile(array, .75)) if n else math.nan
                identity = effective[mask] - realized[mask] - 2 * mid_change[mask]
                row["identity_max_abs_bp"] = float(np.max(np.abs(identity))) if n else math.nan
                rows.append(row)
    return rows


def announcement_paths(meta, event_name, axes):
    if event_name not in ANCHORS:
        return []
    anchor = int(ANCHORS[event_name])
    rows = []
    for symbol, source in axes.items():
        qt = source["quote_times"]
        for rel in range(-300, 301):
            target = anchor + rel * NS
            pos = int(np.searchsorted(qt, target, side="right") - 1)
            if pos < 0:
                bid = ask = mid = spread = math.nan
            else:
                bid, ask = float(source["quote_bid"][pos]), float(source["quote_ask"][pos])
                mid = (bid + ask) / 2
                spread = (ask - bid) / mid * 10_000
            rows.append({**meta, "instrument": symbol, "relative_second": rel, "bid": bid, "ask": ask, "mid": mid, "relative_spread_bp": spread})
    # Return transformations use each instrument's -300 second midpoint.
    baseline = {}
    for row in rows:
        if row["relative_second"] == -300:
            baseline[row["instrument"]] = row["mid"]
    for row in rows:
        base = baseline.get(row["instrument"], math.nan)
        for side in ("bid", "ask", "mid"):
            row[f"{side}_return_bp"] = (row[side] / base - 1) * 10_000 if math.isfinite(row[side]) and math.isfinite(base) else math.nan
    return rows


def main():
    filter_rows, diagnostic_rows, pair_rows, hist_rows, response_output, path_rows = [], [], [], [], [], []
    file_summaries = []
    bounds_by_file = analysis_bounds()
    for raw_path in sorted(glob.glob(str(ROOT / "*_mbp1.dbn.zst"))):
        path = Path(raw_path)
        event_name, dataset = filename_meta(path)
        store, stock, records, actions, invalids, diagnostic = load_file(path)
        meta = {"file": path.name, "window": event_name, "dataset": dataset, "stock": stock}
        event_axes_full = {s: make_axis(records[s], "EVENT") for s in (stock, "SPY")}
        recv_axes_full = {s: make_axis(records[s], "RECEIVE") for s in (stock, "SPY")}
        start_ns, end_ns = bounds_by_file[path.name]
        event_axes = {s: trim_trade_window(event_axes_full[s], start_ns, end_ns) for s in (stock, "SPY")}
        recv_axes = {s: trim_trade_window(recv_axes_full[s], start_ns, end_ns) for s in (stock, "SPY")}
        for symbol in (stock, "SPY"):
            raw_source_counts = Counter(event_axes_full[symbol]["sign_source"])
            filter_rows.append({
                **meta,
                "instrument": symbol,
                "analysis_start_utc_ns": start_ns,
                "analysis_end_utc_ns_exclusive": end_ns,
                "total_mbp1_records": len(records[symbol]),
                "trade_records": actions[symbol]["T"],
                "analysis_window_trade_records": len(event_axes[symbol]["times"]),
                "support_only_trade_records": actions[symbol]["T"] - len(event_axes[symbol]["times"]),
                "raw_native_side_classified_trades": raw_source_counts["NATIVE"],
                "raw_midpoint_fallback_classified_trades": raw_source_counts["MIDPOINT"],
                "raw_unknown_direction_trades": raw_source_counts["UNKNOWN"],
                "add_records": actions[symbol]["A"],
                "cancel_records": actions[symbol]["C"],
                "modify_records": actions[symbol]["M"],
                "clear_records": actions[symbol]["R"],
                "fill_records": actions[symbol]["F"],
                "other_records": sum(v for k, v in actions[symbol].items() if k not in {"T", "A", "C", "M", "R", "F"}),
                "valid_bbo_records": invalids[(symbol, "valid_bbo")],
                "invalid_bbo_records": invalids[(symbol, "invalid_bbo")],
                "flag_last_records": diagnostic[symbol]["flag_last"],
                "flag_publisher_specific_records": diagnostic[symbol]["flag_publisher_specific"],
                "flag_bad_ts_recv_records": diagnostic[symbol]["flag_bad_ts_recv"],
                "flag_maybe_bad_book_records": diagnostic[symbol]["flag_maybe_bad_book"],
            })
        for axis_name, axes in (("EVENT", event_axes), ("RECEIVE", recv_axes)):
            for symbol in (stock, "SPY"):
                direction_counts = Counter(axes[symbol]["sign"])
                source_counts = Counter(axes[symbol]["sign_source"])
                diagnostic_rows.append({
                    **meta,
                    "axis": axis_name,
                    "instrument": symbol,
                    "event_nonmonotonic_in_file_order": diagnostic[symbol]["event_nonmonotonic"],
                    "receive_nonmonotonic_in_file_order": diagnostic[symbol]["recv_nonmonotonic"],
                    "event_duplicate_adjacent_in_file_order": diagnostic[symbol]["event_duplicate_adjacent"],
                    "receive_duplicate_adjacent_in_file_order": diagnostic[symbol]["recv_duplicate_adjacent"],
                    "classified_buy_trades": direction_counts["B"],
                    "classified_sell_trades": direction_counts["S"],
                    "unknown_direction_trades": direction_counts["U"],
                    "native_side_classified_trades": source_counts["NATIVE"],
                    "midpoint_fallback_classified_trades": source_counts["MIDPOINT"],
                    "native_side_missing_and_midpoint_unknown_trades": source_counts["UNKNOWN"],
                    "direction_classification": "native aggressor side first; strict prior-message midpoint fallback on selected time axis",
                })
            pair_rows.extend(counts_for_axis(meta, axes[stock], axes["SPY"], axis_name))
            if axis_name == "EVENT":
                pair_rows.extend(counts_for_axis(meta, axes[stock], axes["SPY"], axis_name, "EXCLUDE_FIRST_200MS"))
            hist_rows.extend(offset_histogram(meta, axes[stock]["times"], axes["SPY"]["times"], axis_name))
        response_output.extend(response_rows(meta, stock, event_axes[stock], event_axes["SPY"]))
        response_output.extend(response_rows(meta, "SPY", event_axes["SPY"], event_axes[stock]))
        path_rows.extend(announcement_paths(meta, event_name, event_axes_full))
        file_summaries.append({**meta, "bytes": path.stat().st_size, "stock_trades": len(event_axes[stock]["times"]), "spy_trades": len(event_axes["SPY"]["times"])})
        print(json.dumps(file_summaries[-1]), flush=True)
    write_csv(ROOT / "FILTER_COUNTS.csv", filter_rows)
    write_csv(ROOT / "QUOTE_DIAGNOSTICS.csv", diagnostic_rows)
    write_csv(ROOT / "PAIR_COUNTS.csv", pair_rows)
    write_csv(ROOT / "OFFSET_HISTOGRAM.csv", hist_rows)
    write_csv(ROOT / "TRADE_RESPONSE.csv", response_output)
    write_csv(ROOT / "ANNOUNCEMENT_PATHS.csv", path_rows)
    (ROOT / "ANALYSIS_SUMMARY.json").write_text(json.dumps({
        "status": "COMPUTED_PENDING_INDEPENDENT_REVIEW",
        "files": len(file_summaries),
        "total_bytes": sum(row["bytes"] for row in file_summaries),
        "total_stock_trades": sum(row["stock_trades"] for row in file_summaries),
        "total_spy_trades": sum(row["spy_trades"] for row in file_summaries),
        "pair_rows": len(pair_rows),
        "response_rows": len(response_output),
        "path_rows": len(path_rows),
        "file_summaries": file_summaries,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
