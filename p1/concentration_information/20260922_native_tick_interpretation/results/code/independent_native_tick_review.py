#!/usr/bin/env python3
"""Independent SCC-side review of the native-tick interpretation output.

This decoder does not import the engineering implementation.  It exports only
aggregate recomputations and an aggregate raw-trade audit receipt; no timestamps,
prices, quotes, or other reconstructable market-data rows leave SCC.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import databento as db
from databento_dbn import MBP1Msg, UNDEF_ORDER_SIZE, UNDEF_PRICE


NS = 1_000_000_000
US = 1_000
ROOT = Path("/scratch/qluo/native_tick_pilot_20260922")
HORIZONS = (50 * US, 200 * US, 1_000 * US, 10_000 * US, 5 * NS)


def enum_value(value):
    return str(getattr(value, "value", value))


def dated_mapping(store):
    return {
        int(span["symbol"]): symbol.upper().strip()
        for symbol, spans in store.metadata.mappings.items()
        for span in spans
    }


def valid_bbo(record):
    level = record.levels[0]
    bid, ask = int(level.bid_px), int(level.ask_px)
    bid_size, ask_size = int(level.bid_sz), int(level.ask_sz)
    if bid == UNDEF_PRICE or ask == UNDEF_PRICE:
        return None
    if bid_size == UNDEF_ORDER_SIZE or ask_size == UNDEF_ORDER_SIZE:
        return None
    if min(bid, ask, bid_size, ask_size) <= 0 or ask < bid:
        return None
    return bid / 1e9, ask / 1e9, bid_size, ask_size


def bounds_by_file():
    rows = json.loads((ROOT / "REQUEST_MANIFEST.json").read_text())
    result = {}
    for row in rows:
        start = int(__import__("numpy").datetime64(row["start"].removesuffix("Z"), "ns").astype("int64"))
        end = int(__import__("numpy").datetime64(row["end"].removesuffix("Z"), "ns").astype("int64"))
        result[Path(row["path"]).name] = (start + 120 * NS, end - 65 * NS)
    return result


def file_meta(path):
    stem = path.name.removesuffix("_mbp1.dbn.zst")
    if stem.endswith("_XNAS_ITCH"):
        return stem[:-10], "XNAS.ITCH"
    if stem.endswith("_ARCX_PILLAR"):
        return stem[:-12], "ARCX.PILLAR"
    raise ValueError(path)


def decode(path, start, end):
    store = db.DBNStore.from_file(path)
    mapping = dated_mapping(store)
    symbols = {symbol for symbol in mapping.values() if symbol in {"AAPL", "XOM", "SPY"}}
    stock_symbol = "AAPL" if "AAPL" in symbols else "XOM"
    raw = {stock_symbol: [], "SPY": []}
    for file_order, record in enumerate(store):
        if not isinstance(record, MBP1Msg):
            continue
        symbol = mapping.get(int(record.instrument_id))
        if symbol not in raw:
            continue
        raw[symbol].append(
            (
                int(record.ts_event), int(record.sequence), file_order,
                enum_value(record.action), enum_value(record.side),
                int(record.price) / 1e9 if int(record.price) != UNDEF_PRICE else math.nan,
                int(record.size), valid_bbo(record),
            )
        )

    decoded = {}
    for symbol, messages in raw.items():
        messages.sort(key=lambda row: (row[0], row[1], row[2]))
        current = None
        carrying_ts = None
        change_ts = None
        state_times, state_bid, state_ask = [], [], []
        state_carrying_ts, state_change_ts = [], []
        trades = []
        invalid_bbo_messages = clear_messages = 0
        for ts, sequence, file_order, action, side, price, size, quote in messages:
            # The trade sees the state strictly before its own message.
            if action == "T" and start <= ts < end:
                midpoint = (current[0] + current[1]) / 2 if current else math.nan
                if side == "B":
                    sign, source = "B", "NATIVE"
                elif side == "A":
                    sign, source = "S", "NATIVE"
                elif math.isfinite(midpoint) and math.isfinite(price) and price != midpoint:
                    sign, source = ("B" if price > midpoint else "S"), "MIDPOINT"
                else:
                    sign, source = "U", "UNKNOWN"
                trades.append(
                    {
                        "t": ts, "sequence": sequence, "file_order": file_order,
                        "price": price, "size": size, "sign": sign, "source": source,
                        "pre_bid": current[0] if current else math.nan,
                        "pre_ask": current[1] if current else math.nan,
                    }
                )

            if action == "R":
                clear_messages += 1
                current = carrying_ts = change_ts = None
            elif quote is None:
                # Required review interpretation: an invalid/undefined BBO is not
                # permission to carry an older valid state.
                invalid_bbo_messages += 1
                current = carrying_ts = change_ts = None
            else:
                new_pair = quote[:2]
                if current is None or new_pair != current[:2]:
                    change_ts = ts
                current = quote
                carrying_ts = ts
            state_times.append(ts)
            state_bid.append(current[0] if current else math.nan)
            state_ask.append(current[1] if current else math.nan)
            state_carrying_ts.append(carrying_ts if carrying_ts is not None else -1)
            state_change_ts.append(change_ts if change_ts is not None else -1)

        decoded[symbol] = {
            "trades": trades,
            "state_times": state_times,
            "state_bid": state_bid,
            "state_ask": state_ask,
            "state_carrying_ts": state_carrying_ts,
            "state_change_ts": state_change_ts,
            "clear_messages": clear_messages,
            "invalid_bbo_messages": invalid_bbo_messages,
        }
    return stock_symbol, decoded


def times(rows, sign=None, native_only=False):
    return [
        row["t"] for row in rows
        if (sign is None or row["sign"] == sign)
        and (not native_only or row["source"] == "NATIVE")
    ]


def half_open_count(left, right, lo, hi):
    return sum(
        bisect.bisect_left(right, t + hi) - bisect.bisect_left(right, t + lo)
        for t in left
    )


def stock_pair_flags(source_times, target_times):
    return [
        bisect.bisect_left(target_times, t + 20 * US)
        > bisect.bisect_left(target_times, t - 20 * US)
        for t in source_times
    ]


def spy_pair_flags(source_times, target_stock_times):
    # d = t_spy - t_stock in [-20,+20) iff stock is in (spy-20, spy+20].
    return [
        bisect.bisect_right(target_stock_times, t + 20 * US)
        > bisect.bisect_right(target_stock_times, t - 20 * US)
        for t in source_times
    ]


def endpoint(decoded, target):
    pos = bisect.bisect_right(decoded["state_times"], target) - 1
    if pos < 0:
        return None
    bid, ask = decoded["state_bid"][pos], decoded["state_ask"][pos]
    if not (math.isfinite(bid) and math.isfinite(ask)):
        return None
    return pos, (bid + ask) / 2


def response_cells(window, dataset, stock, instrument, source, target, start, is_stock):
    cells = defaultdict(lambda: {"paired": [], "unpaired": []})
    source_rows = [row for row in source["trades"] if row["source"] == "NATIVE"]
    for direction in ("B", "S"):
        target_times = times(target["trades"], sign=direction, native_only=True)
        direction_rows = [row for row in source_rows if row["sign"] == direction]
        source_times = [row["t"] for row in direction_rows]
        flags = (stock_pair_flags(source_times, target_times) if is_stock
                 else spy_pair_flags(source_times, target_times))
        sign = 1 if direction == "B" else -1
        for row, paired in zip(direction_rows, flags):
            pre_mid = (row["pre_bid"] + row["pre_ask"]) / 2
            if not math.isfinite(pre_mid):
                continue
            bin_5m = (row["t"] - start) // (300 * NS)
            if not 0 <= bin_5m < 12:
                raise AssertionError("trade outside fixed hour")
            for horizon in HORIZONS:
                found = endpoint(source, row["t"] + horizon)
                if found is None:
                    continue
                _, post_mid = found
                value = sign * (post_mid - pre_mid) / pre_mid * 10_000
                label = "paired" if paired else "unpaired"
                cells[(horizon, direction, int(bin_5m))][label].append(value)
    return cells


def collapse_cross(event, dataset, instrument, rth_cells, ctrl_cells):
    output = []
    for horizon in HORIZONS:
        for direction in ("B", "S"):
            common = []
            for bin_5m in range(12):
                r = rth_cells.get((horizon, direction, bin_5m))
                c = ctrl_cells.get((horizon, direction, bin_5m))
                if not r or not c or not all(r[key] and c[key] for key in ("paired", "unpaired")):
                    continue
                r_diff = sum(r["paired"]) / len(r["paired"]) - sum(r["unpaired"]) / len(r["unpaired"])
                c_diff = sum(c["paired"]) / len(c["paired"]) - sum(c["unpaired"]) / len(c["unpaired"])
                common.append((r_diff - c_diff, len(r["paired"]), len(c["paired"]), len(r["unpaired"]), len(c["unpaired"])))
            for weighting in ("EQUAL_BIN", "PAIRED_N_WEIGHTED"):
                if weighting == "EQUAL_BIN":
                    weights = [1] * len(common)
                else:
                    weights = [row[1] + row[2] for row in common]
                estimate = (
                    sum(row[0] * weight for row, weight in zip(common, weights)) / sum(weights)
                    if weights else math.nan
                )
                output.append(
                    {
                        "comparison": "RTH_MINUS_CONTROL_COMMON_5M",
                        "window": event, "dataset": dataset,
                        "stock": "AAPL" if event.startswith("AAPL") else "XOM",
                        "instrument": instrument, "variant": "NATIVE_ONLY",
                        "horizon_ns": horizon,
                        "horizon_label": f"{horizon / US:g}us" if horizon < NS else f"{horizon / NS:g}s",
                        "direction": direction, "weighting": weighting,
                        "metric": "signed_mid_change_bp", "estimate": estimate,
                        "support_bins": len(common), "dropped_bins": 12 - len(common),
                        "rth_paired_n_sum": sum(row[1] for row in common),
                        "control_paired_n_sum": sum(row[2] for row in common),
                        "rth_unpaired_n_sum": sum(row[3] for row in common),
                        "control_unpaired_n_sum": sum(row[4] for row in common),
                    }
                )
    return output


def activity_row(window, dataset, stock, spy):
    stock_times, spy_times = times(stock["trades"]), times(spy["trades"])
    near = half_open_count(stock_times, spy_times, -20 * US, 20 * US)
    background = (
        half_open_count(stock_times, spy_times, -1200 * US, -1000 * US)
        + half_open_count(stock_times, spy_times, 1000 * US, 1200 * US)
    )
    excess = near - 0.1 * background
    return {
        "window": window, "dataset": dataset, "near_pairs": near,
        "background_pairs": background, "excess_pairs": excess,
        "stock_trades": len(stock_times), "spy_trades": len(spy_times),
        "excess_per_1000_stock": 1000 * excess / len(stock_times),
        "excess_per_1000_spy": 1000 * excess / len(spy_times),
    }


def audit_raw(file_objects):
    checks = defaultdict(int)
    audited = 0
    for _, _, stock_symbol, decoded in file_objects:
        for symbol in (stock_symbol, "SPY"):
            source = decoded[symbol]
            target = decoded["SPY" if symbol == stock_symbol else stock_symbol]
            candidates = [row for row in source["trades"] if row["source"] == "NATIVE"][:2]
            target_by_sign = {
                direction: times(target["trades"], direction, native_only=True)
                for direction in ("B", "S")
            }
            for row in candidates:
                audited += 1
                checks["native_sign_matches_raw_side"] += row["sign"] in ("B", "S")
                checks["finite_prior_bbo"] += math.isfinite(row["pre_bid"]) and math.isfinite(row["pre_ask"]) and row["pre_ask"] >= row["pre_bid"]
                targets = target_by_sign[row["sign"]]
                if symbol == stock_symbol:
                    fast = stock_pair_flags([row["t"]], targets)[0]
                    explicit = any(-20 * US <= t - row["t"] < 20 * US for t in targets)
                else:
                    fast = spy_pair_flags([row["t"]], targets)[0]
                    explicit = any(-20 * US <= row["t"] - t < 20 * US for t in targets)
                checks["oriented_half_open_pair_matches_explicit"] += fast == explicit
                for horizon in HORIZONS:
                    target_time = row["t"] + horizon
                    found = endpoint(source, target_time)
                    pos = bisect.bisect_right(source["state_times"], target_time) - 1
                    bracketing = pos >= 0 and source["state_times"][pos] <= target_time and (pos + 1 == len(source["state_times"]) or source["state_times"][pos + 1] > target_time)
                    checks["endpoint_lookup_brackets_target"] += bracketing
                    if found is not None:
                        checks["endpoint_lookup_returns_valid_bbo"] += math.isfinite(found[1])
                    checks["endpoint_checks"] += 1
    checks["audited_native_trades"] = audited
    checks["clear_messages_seen"] = sum(d[s]["clear_messages"] for *_, d in file_objects for s in d)
    checks["invalid_bbo_messages_seen"] = sum(d[s]["invalid_bbo_messages"] for *_, d in file_objects for s in d)
    return dict(checks)


def write_csv(path, rows):
    fields = list(rows[0])
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    bounds = bounds_by_file()
    objects = {}
    file_objects = []
    activity = []
    for path in sorted(ROOT.glob("*_mbp1.dbn.zst")):
        window, dataset = file_meta(path)
        if not (window.endswith("_RTH") or window.endswith("_CTRL")):
            continue
        stock_symbol, decoded = decode(path, *bounds[path.name])
        objects[(window, dataset)] = (stock_symbol, decoded, bounds[path.name][0])
        file_objects.append((window, dataset, stock_symbol, decoded))
        activity.append(activity_row(window, dataset, decoded[stock_symbol], decoded["SPY"]))

    cross = []
    for event in ("AAPL_FEB", "AAPL_AUG", "XOM_JAN"):
        for dataset in ("ARCX.PILLAR", "XNAS.ITCH"):
            stock_symbol, rth, rth_start = objects[(event + "_RTH", dataset)]
            _, ctrl, ctrl_start = objects[(event + "_CTRL", dataset)]
            for instrument in (stock_symbol, "SPY"):
                target_symbol = "SPY" if instrument == stock_symbol else stock_symbol
                rth_cells = response_cells(event + "_RTH", dataset, stock_symbol, instrument, rth[instrument], rth[target_symbol], rth_start, instrument == stock_symbol)
                ctrl_cells = response_cells(event + "_CTRL", dataset, stock_symbol, instrument, ctrl[instrument], ctrl[target_symbol], ctrl_start, instrument == stock_symbol)
                cross.extend(collapse_cross(event, dataset, instrument, rth_cells, ctrl_cells))

    # Four AAPL matched activity/decomposition rows.
    activity_lookup = {(row["window"], row["dataset"]): row for row in activity}
    decomposition = []
    for event in ("AAPL_FEB", "AAPL_AUG"):
        for dataset in ("ARCX.PILLAR", "XNAS.ITCH"):
            r = activity_lookup[(event + "_RTH", dataset)]
            c = activity_lookup[(event + "_CTRL", dataset)]
            level_raw = (r["excess_pairs"] - c["excess_pairs"]) / c["stock_trades"]
            activity_raw = r["excess_pairs"] * (1 / r["stock_trades"] - 1 / c["stock_trades"])
            decomposition.append(
                {
                    "window": event, "dataset": dataset,
                    "rth_near_pairs": r["near_pairs"], "control_near_pairs": c["near_pairs"],
                    "rth_background_pairs": r["background_pairs"], "control_background_pairs": c["background_pairs"],
                    "rth_excess_pairs": r["excess_pairs"], "control_excess_pairs": c["excess_pairs"],
                    "excess_pairs_difference": r["excess_pairs"] - c["excess_pairs"],
                    "rth_stock_trades": r["stock_trades"], "control_stock_trades": c["stock_trades"],
                    "rate_difference_per_1000_stock": r["excess_per_1000_stock"] - c["excess_per_1000_stock"],
                    "fixed_order_level_term_per_1000": 1000 * level_raw,
                    "fixed_order_activity_term_per_1000": 1000 * activity_raw,
                    "decomposition_sum_per_1000": 1000 * (level_raw + activity_raw),
                    "rth_spy_trades": r["spy_trades"], "control_spy_trades": c["spy_trades"],
                    "rate_difference_per_1000_spy": r["excess_per_1000_spy"] - c["excess_per_1000_spy"],
                }
            )

    write_csv(out / "INDEPENDENT_ACTIVITY_RECOMPUTATION.csv", decomposition)
    write_csv(out / "INDEPENDENT_RESPONSE_RECOMPUTATION.csv", cross)
    receipt = {
        "scope": "12 RTH/control DBNs; event-time primary native-only response",
        "files_decoded": len(file_objects),
        "response_rows": len(cross),
        "activity_rows": len(decomposition),
        "horizons_ns": HORIZONS,
        "raw_trade_audit": audit_raw(file_objects),
        "raw_inputs_modified": False,
        "raw_rows_exported": False,
        "new_data_purchased_usd": 0,
        "reviewer_routing": {
            "requested_model": "gpt-5.6-sol",
            "requested_effort": "high",
            "actual_model_or_effort": "NOT_OBSERVED",
            "note": "No independently verifiable backend routing telemetry was exposed to the reviewer.",
        },
    }
    (out / "INDEPENDENT_REVIEW_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
