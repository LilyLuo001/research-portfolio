#!/usr/bin/env python3
"""Independent raw-DBN verification for the native-tick pilot.

This script intentionally does not import or call the production analyzer. It
uses a two-pointer half-open range counter and an explicit bounded pair
enumeration. Only aggregate diagnostics are written.
"""
from __future__ import annotations

import bisect
import glob
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import databento as db
from databento_dbn import MBP1Msg, UNDEF_ORDER_SIZE, UNDEF_PRICE


ROOT = Path("/scratch/qluo/native_tick_pilot_20260922")
NS = 1_000_000_000
US = 1_000
NEAR = ((-20 * US, 20 * US),)
BACKGROUND = ((-1200 * US, -1000 * US), (1000 * US, 1200 * US))


def enum_value(obj) -> str:
    return str(getattr(obj, "value", obj))


def iso_ns(text: str) -> int:
    return int(datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp() * NS)


def bbo(record):
    level = record.levels[0]
    bid, ask = int(level.bid_px), int(level.ask_px)
    bid_size, ask_size = int(level.bid_sz), int(level.ask_sz)
    if bid == UNDEF_PRICE or ask == UNDEF_PRICE or bid_size == UNDEF_ORDER_SIZE or ask_size == UNDEF_ORDER_SIZE:
        return None
    if min(bid, ask, bid_size, ask_size) <= 0 or ask < bid:
        return None
    return bid / 1e9, ask / 1e9


def dated_mapping(store):
    result = {}
    for raw_symbol, spans in store.metadata.mappings.items():
        for span in spans:
            result[int(span["symbol"])] = raw_symbol.upper().strip()
    return result


def two_pointer_count(a, b, intervals):
    """Count ordered (a,b) pairs with b-a in union of half-open intervals."""
    total = 0
    for lo, hi in intervals:
        left = right = 0
        for timestamp in a:
            lower, upper = timestamp + lo, timestamp + hi
            while left < len(b) and b[left] < lower:
                left += 1
            if right < left:
                right = left
            while right < len(b) and b[right] < upper:
                right += 1
            total += right - left
    return total


def any_pair_mask(a, b, lo=-20 * US, hi=20 * US):
    out = [False] * len(a)
    left = right = 0
    for i, timestamp in enumerate(a):
        lower, upper = timestamp + lo, timestamp + hi
        while left < len(b) and b[left] < lower:
            left += 1
        if right < left:
            right = left
        while right < len(b) and b[right] < upper:
            right += 1
        out[i] = right > left
    return out


def build_axis(messages, axis):
    ts_pos = 1 if axis == "EVENT" else 2
    order = sorted(range(len(messages)), key=lambda i: (messages[i][ts_pos], messages[i][3], messages[i][0]))
    quotes_t, quotes_mid = [], []
    trades = []
    last_quote = None
    last_quote_t = None
    for i in order:
        row = messages[i]
        timestamp, sequence, action, side = row[ts_pos], row[3], row[4], row[5]
        price, size, bid, ask = row[6], row[7], row[8], row[9]
        if action == "T":
            pre_mid = math.nan if last_quote is None else (last_quote[0] + last_quote[1]) / 2
            pre_spread = math.nan if last_quote is None else (last_quote[1] - last_quote[0]) / pre_mid * 10_000
            if side == "B":
                sign, source, reason = "B", "NATIVE", "NATIVE_B"
            elif side == "A":
                sign, source, reason = "S", "NATIVE", "NATIVE_A"
            elif last_quote is None or not math.isfinite(price):
                sign, source, reason = "U", "UNKNOWN", "NO_PRIOR_QUOTE_OR_PRICE"
            elif price > pre_mid:
                sign, source, reason = "B", "MIDPOINT", "ABOVE_PRIOR_MID"
            elif price < pre_mid:
                sign, source, reason = "S", "MIDPOINT", "BELOW_PRIOR_MID"
            else:
                sign, source, reason = "U", "UNKNOWN", "AT_PRIOR_MID"
            trades.append({
                "t": timestamp, "sequence": sequence, "price": price, "size": size,
                "sign": sign, "source": source, "reason": reason,
                "pre_mid": pre_mid, "pre_spread": pre_spread,
                "pre_quote_same_timestamp": last_quote_t == timestamp,
            })
        if math.isfinite(bid) and math.isfinite(ask):
            last_quote = (bid, ask)
            last_quote_t = timestamp
            quotes_t.append(timestamp)
            quotes_mid.append((bid + ask) / 2)
    return {"trades": trades, "quote_t": quotes_t, "quote_mid": quotes_mid}


def subset(axis, start, end, periodic=False):
    trades = [row for row in axis["trades"] if start <= row["t"] < end]
    if periodic:
        trades = [row for row in trades if row["t"] % NS >= 200_000_000]
    return trades


def category_times(trades, sign=None):
    return [row["t"] for row in trades if sign is None or row["sign"] == sign]


def pair_summary(meta, stock_trades, spy_trades, axis, variant):
    st_all, et_all = category_times(stock_trades), category_times(spy_trades)
    result = {**meta, "axis": axis, "variant": variant,
              "stock_trades": len(st_all), "spy_trades": len(et_all)}
    all_near = two_pointer_count(st_all, et_all, NEAR)
    all_bg = two_pointer_count(st_all, et_all, BACKGROUND)
    result.update(all_near=all_near, all_background=all_bg,
                  all_excess=all_near - 0.1 * all_bg,
                  all_excess_per_1000=(1000 * (all_near - 0.1 * all_bg) / len(st_all)) if st_all else None)
    known_near = known_bg = 0
    for left_sign, right_sign, label in (("B", "B", "B_B"), ("S", "S", "S_S"),
                                         ("B", "S", "B_S"), ("S", "B", "S_B")):
        left = category_times(stock_trades, left_sign)
        right = category_times(spy_trades, right_sign)
        near = two_pointer_count(left, right, NEAR)
        bg = two_pointer_count(left, right, BACKGROUND)
        known_near += near
        known_bg += bg
        result[f"{label}_near"] = near
        result[f"{label}_background"] = bg
        result[f"{label}_excess"] = near - 0.1 * bg
    result["UNKNOWN_EITHER_near"] = all_near - known_near
    result["UNKNOWN_EITHER_background"] = all_bg - known_bg
    result["UNKNOWN_EITHER_excess"] = result["UNKNOWN_EITHER_near"] - 0.1 * result["UNKNOWN_EITHER_background"]
    result["same_direction_excess"] = result["B_B_excess"] + result["S_S_excess"]
    return result


def same_direction_flags(source, target):
    flags = [False] * len(source)
    for sign in ("B", "S"):
        source_indices = [i for i, row in enumerate(source) if row["sign"] == sign]
        source_times = [source[i]["t"] for i in source_indices]
        target_times = category_times(target, sign)
        signed_flags = any_pair_mask(source_times, target_times)
        for i, flag in zip(source_indices, signed_flags):
            flags[i] = flag
    return flags


def response_5s(meta, instrument, source, target, quote_t, quote_mid, identity_samples):
    paired = same_direction_flags(source, target)
    buckets = defaultdict(list)
    identity_max = 0.0
    identity_n = 0
    for row, is_paired in zip(source, paired):
        if row["sign"] not in ("B", "S") or not math.isfinite(row["pre_mid"]) or not math.isfinite(row["price"]):
            continue
        position = bisect.bisect_right(quote_t, row["t"] + 5 * NS) - 1
        if position < 0:
            continue
        post_mid = quote_mid[position]
        signed = 1 if row["sign"] == "B" else -1
        effective = 2 * signed * (row["price"] - row["pre_mid"]) / row["pre_mid"] * 10_000
        mid_change = signed * (post_mid - row["pre_mid"]) / row["pre_mid"] * 10_000
        realized = 2 * signed * (row["price"] - post_mid) / row["pre_mid"] * 10_000
        error = abs(effective - realized - 2 * mid_change)
        identity_n += 1
        identity_max = max(identity_max, error)
        label = "PAIRED" if is_paired else "UNPAIRED"
        buckets[label].append(mid_change)
        sample_key = f"{row['source']}_{'SAME_TS' if row['pre_quote_same_timestamp'] else 'PRIOR_TS'}"
        if len(identity_samples[sample_key]) < 20:
            identity_samples[sample_key].append(error)
    output = []
    for label in ("PAIRED", "UNPAIRED"):
        values = buckets[label]
        output.append({**meta, "instrument": instrument, "group": label,
                       "n": len(values), "signed_mid_change_bp_mean": sum(values) / len(values) if values else None})
    return output, identity_n, identity_max


def explicit_slice_check(stock, spy):
    # Select the one-second bucket with the most actual near pairs, then enumerate
    # every ordered pair in that bounded bucket exactly once.
    per_second = Counter()
    spy_times = category_times(spy)
    for row in stock:
        lo = bisect.bisect_left(spy_times, row["t"] - 20 * US)
        hi = bisect.bisect_left(spy_times, row["t"] + 20 * US)
        if hi > lo:
            per_second[row["t"] // NS] += hi - lo
    second, _ = per_second.most_common(1)[0]
    start, end = second * NS, (second + 1) * NS
    st = [row for row in stock if start <= row["t"] < end]
    et = [row for row in spy if start <= row["t"] < end]
    explicit = []
    for i, left in enumerate(st):
        for j, right in enumerate(et):
            diff = right["t"] - left["t"]
            if -1200 * US <= diff < 1200 * US:
                explicit.append((i, j, diff, left["sign"], right["sign"]))
    unique_keys = {(i, j) for i, j, *_ in explicit}
    near = [row for row in explicit if -20 * US <= row[2] < 20 * US]
    background = [row for row in explicit if (-1200 * US <= row[2] < -1000 * US) or (1000 * US <= row[2] < 1200 * US)]
    range_near = two_pointer_count(category_times(st), category_times(et), NEAR)
    range_background = two_pointer_count(category_times(st), category_times(et), BACKGROUND)
    return {
        "stock_trades_in_slice": len(st), "spy_trades_in_slice": len(et),
        "explicit_candidate_pairs": len(explicit), "unique_pair_keys": len(unique_keys),
        "duplicate_pair_keys": len(explicit) - len(unique_keys),
        "explicit_near": len(near), "range_near": range_near,
        "explicit_background": len(background), "range_background": range_background,
        "exact_lower_endpoint_near": sum(row[2] == -20 * US for row in explicit),
        "exact_upper_endpoint_near": sum(row[2] == 20 * US for row in explicit),
        "near_all_within_half_open": all(-20 * US <= row[2] < 20 * US for row in near),
    }


def main():
    manifest = json.loads((ROOT / "REQUEST_MANIFEST.json").read_text())
    manifest_by_file = {Path(row["path"]).name: row for row in manifest}
    pair_rows, response_rows = [], []
    action_totals, native_side_totals, flag_totals = Counter(), Counter(), Counter()
    dataset_actions, dataset_trade_sides = defaultdict(Counter), defaultdict(Counter)
    quote_validity = Counter()
    direction_totals = {"EVENT": Counter(), "RECEIVE": Counter()}
    analysis_direction_totals = {"EVENT": Counter(), "RECEIVE": Counter()}
    analysis_sign_totals = {"EVENT": Counter(), "RECEIVE": Counter()}
    reason_totals = {"EVENT": Counter(), "RECEIVE": Counter()}
    same_timestamp_totals = {"EVENT": Counter(), "RECEIVE": Counter()}
    identity_samples = defaultdict(list)
    identity_n = 0
    identity_max = 0.0
    explicit_check = None

    for raw_path in sorted(glob.glob(str(ROOT / "*_mbp1.dbn.zst"))):
        path = Path(raw_path)
        request = manifest_by_file[path.name]
        window, dataset = request["name"], request["dataset"]
        analysis_start = iso_ns(request["start"]) + 120 * NS
        analysis_end = iso_ns(request["end"]) - 65 * NS
        store = db.DBNStore.from_file(path)
        symbol_map = dated_mapping(store)
        present = {symbol for symbol in symbol_map.values() if symbol in {"AAPL", "XOM", "SPY"}}
        stock_symbol = "AAPL" if "AAPL" in present else "XOM"
        messages = {stock_symbol: [], "SPY": []}
        for index, record in enumerate(store):
            if not isinstance(record, MBP1Msg):
                continue
            symbol = symbol_map.get(int(record.instrument_id))
            if symbol not in messages:
                continue
            action, side, flags = enum_value(record.action), enum_value(record.side), int(record.flags)
            action_totals[action] += 1
            dataset_actions[dataset][action] += 1
            if action == "T":
                native_side_totals[side] += 1
                dataset_trade_sides[dataset][side] += 1
            flag_totals["bad_ts_recv"] += bool(flags & 8)
            flag_totals["maybe_bad_book"] += bool(flags & 4)
            flag_totals["publisher_specific"] += bool(flags & 2)
            quote = bbo(record)
            quote_validity["INVALID" if quote is None else "VALID"] += 1
            bid, ask = (math.nan, math.nan) if quote is None else quote
            price = math.nan if int(record.price) == UNDEF_PRICE else int(record.price) / 1e9
            messages[symbol].append((index, int(record.ts_event), int(record.ts_recv), int(record.sequence),
                                     action, side, price, int(record.size), bid, ask, flags))
        axes = {axis: {symbol: build_axis(rows, axis) for symbol, rows in messages.items()} for axis in ("EVENT", "RECEIVE")}
        meta = {"file": path.name, "window": window, "dataset": dataset, "stock": stock_symbol}
        for axis_name in ("EVENT", "RECEIVE"):
            core = {}
            for symbol in (stock_symbol, "SPY"):
                full_trades = axes[axis_name][symbol]["trades"]
                for row in full_trades:
                    direction_totals[axis_name][row["source"]] += 1
                    reason_totals[axis_name][row["reason"]] += 1
                    same_timestamp_totals[axis_name][(row["source"], row["pre_quote_same_timestamp"])] += 1
                core[symbol] = subset(axes[axis_name][symbol], analysis_start, analysis_end)
                for row in core[symbol]:
                    analysis_direction_totals[axis_name][row["source"]] += 1
                    analysis_sign_totals[axis_name][row["sign"]] += 1
            pair_rows.append(pair_summary(meta, core[stock_symbol], core["SPY"], axis_name, "ALL_TRADES"))
            if axis_name == "EVENT":
                periodic_stock = subset(axes[axis_name][stock_symbol], analysis_start, analysis_end, periodic=True)
                periodic_spy = subset(axes[axis_name]["SPY"], analysis_start, analysis_end, periodic=True)
                pair_rows.append(pair_summary(meta, periodic_stock, periodic_spy, axis_name, "EXCLUDE_FIRST_200MS"))
                if path.name == "AAPL_FEB_RTH_XNAS_ITCH_mbp1.dbn.zst":
                    explicit_check = explicit_slice_check(core[stock_symbol], core["SPY"])
                for symbol, target_symbol in ((stock_symbol, "SPY"), ("SPY", stock_symbol)):
                    rows, n, error = response_5s(meta, symbol, core[symbol], core[target_symbol],
                                                  axes[axis_name][symbol]["quote_t"], axes[axis_name][symbol]["quote_mid"],
                                                  identity_samples)
                    response_rows.extend(rows)
                    identity_n += n
                    identity_max = max(identity_max, error)

    output = {
        "method": "independent raw DBN decode; two-pointer half-open range counts; production analyzer not imported",
        "analysis_window_rule": "manifest start + 120 seconds through end - 65 seconds, half-open",
        "pair_rows": pair_rows,
        "response_5s": response_rows,
        "source": {
            "actions": dict(action_totals), "native_trade_sides": dict(native_side_totals),
            "dataset_actions": {key: dict(value) for key, value in dataset_actions.items()},
            "dataset_trade_sides": {key: dict(value) for key, value in dataset_trade_sides.items()},
            "quote_validity": dict(quote_validity),
            "flags": dict(flag_totals),
            "direction_sources": {axis: dict(counter) for axis, counter in direction_totals.items()},
            "analysis_window_direction_sources": {axis: dict(counter) for axis, counter in analysis_direction_totals.items()},
            "analysis_window_signs": {axis: dict(counter) for axis, counter in analysis_sign_totals.items()},
            "direction_reasons": {axis: dict(counter) for axis, counter in reason_totals.items()},
            "same_timestamp_prior_quote": {
                axis: {f"{key[0]}_{key[1]}": value for key, value in counter.items()}
                for axis, counter in same_timestamp_totals.items()
            },
        },
        "response_identity": {
            "all_finite_five_second_identities": identity_n,
            "max_abs_error_bp": identity_max,
            "sample_counts_by_source_and_same_timestamp": {key: len(value) for key, value in identity_samples.items()},
            "sample_max_abs_error_bp": {key: max(value) if value else None for key, value in identity_samples.items()},
            "unknown_classification_audit_counts": {
                "UNKNOWN_PRIOR_TS": min(20, same_timestamp_totals["EVENT"][("UNKNOWN", False)]),
                "UNKNOWN_SAME_TS": min(20, same_timestamp_totals["EVENT"][("UNKNOWN", True)]),
            },
        },
        "explicit_slice": explicit_check,
        "synthetic_boundary_check": {
            "inputs_ns": {"stock": [0], "spy": [-20 * US, 20 * US]},
            "expected_half_open_count": 1,
            "actual_count": two_pointer_count([0], [-20 * US, 20 * US], NEAR),
        },
    }
    (ROOT / "INDEPENDENT_RECOMPUTATION.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"status": "DONE", "pair_rows": len(pair_rows), "response_rows": len(response_rows),
                      "identity_n": identity_n, "identity_max": identity_max, "explicit": explicit_check}, indent=2))


if __name__ == "__main__":
    main()
