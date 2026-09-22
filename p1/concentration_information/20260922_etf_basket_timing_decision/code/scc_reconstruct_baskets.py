#!/usr/bin/env python3
"""Build aggregate SPY/basket paths on SCC without exporting component rows."""
from __future__ import annotations

import bisect
import csv
import glob
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import databento as db
import duckdb
import numpy as np
from databento_dbn import BBOMsg, UNDEF_ORDER_SIZE, UNDEF_PRICE


ROOT = Path("/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared")
OUT = Path("/scratch/qluo/etf_basket_timing_20260922")
HOLDING_FILES = glob.glob(str(ROOT / "raw/rescue_remaining/crsp_holdings_etf_202*" / "part_*.parquet"))
PORTNO = 1021980
FEEDS = ("XNAS.ITCH", "ARCX.PILLAR")
SHIFTS = (0, 30)
MINUTES = tuple(range(-15, 76))
MAIN_MINUTES = tuple(range(-5, 31))
LAGS = tuple(range(-5, 6))
VARIANTS = (
    ("P1-2023-08-01", "XOM", "2022-12-31", "2023-01-31T11:30:00Z", "06:30_ET", "SOURCE_SUPPORTED_MINUTE_CANDIDATE"),
    ("P1-2023-08-03", "XOM", "2023-06-30", "2023-07-28T10:00:00Z", "06:00_ET", "ISSUER_WIRE_CONFLICT"),
    ("P1-2023-08-03", "XOM", "2023-06-30", "2023-07-28T10:30:00Z", "06:30_ET", "ISSUER_WIRE_CONFLICT"),
    ("P1-2023-06-02", "UNH", "2023-03-31", "2023-04-14T09:55:00Z", "05:55_ET", "EARLIEST_OBSERVED_WIRE_CANDIDATE"),
    ("P1-2023-01-01", "AAPL", "2022-12-31", "2023-02-02T21:30:00Z", "16:30_ET", "SOURCE_SUPPORTED_MINUTE_CANDIDATE"),
    ("P1-2023-01-03", "AAPL", "2023-06-30", "2023-08-03T20:30:00Z", "16:30_ET", "SOURCE_SUPPORTED_MINUTE_CANDIDATE"),
    ("P1-2023-02-02", "MSFT", "2023-03-31", "2023-04-25T20:07:00Z", "16:07_ET", "AVAILABILITY_NOTICE_NOT_ORIGINAL_RELEASE"),
)


def ns(value: datetime) -> int:
    return int(value.timestamp() * 1_000_000_000)


def state(record: BBOMsg) -> tuple[str, float | None, float | None]:
    level = record.levels[0]
    bid, ask, bid_size, ask_size = map(int, (level.bid_px, level.ask_px, level.bid_sz, level.ask_sz))
    if bid == UNDEF_PRICE or ask == UNDEF_PRICE or bid_size == UNDEF_ORDER_SIZE or ask_size == UNDEF_ORDER_SIZE or min(bid, ask, bid_size, ask_size) <= 0:
        return "INVALID_UNDEFINED_OR_ZERO_SIDE", None, None
    if ask < bid:
        return "INVALID_CROSSED", None, None
    return ("VALID_LOCKED" if ask == bid else "VALID"), bid / 1e9, ask / 1e9


def select(updates: list[tuple[int, str, float | None, float | None]], target: int, file_end: int):
    if target >= file_end:
        return "UNAVAILABLE_BEYOND_ARCHIVE_END", None, None, None
    if not updates:
        return "UNKNOWN_NO_SYMBOL_RECORD", None, None, None
    times = [row[0] for row in updates]
    right = bisect.bisect_right(times, target)
    if right == 0:
        return "UNKNOWN_NO_PRIOR_STATE", None, None, None
    last_time = times[right - 1]
    left = bisect.bisect_left(times, last_time, 0, right)
    same = updates[left:right]
    if len({row[1:] for row in same}) > 1:
        return "INVALID_SAME_TIMESTAMP_CONFLICT", None, None, last_time
    _, status, bid, ask = same[-1]
    return status, bid, ask, last_time


def valid(quote) -> bool:
    return str(quote[0]).startswith("VALID") and quote[1] is not None and quote[2] is not None


def midpoint(quote) -> float | None:
    return None if not valid(quote) else (quote[1] + quote[2]) / 2


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty output {path}")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def holdings(connection, report_date: str):
    source_rows = connection.execute(
        "select upper(trim(ticker)),percent_tna,nbr_shares,permno from holdings where crsp_portno=? and cast(report_dt as date)=cast(? as date)",
        [PORTNO, report_date],
    ).fetchall()
    total_weight = sum(float(row[1] or 0) for row in source_rows) / 100
    stock_rows = [row for row in source_rows if row[0] and row[2] is not None and row[2] > 0 and row[3] is not None]
    weights = defaultdict(float)
    for ticker, percent_tna, _, _ in stock_rows:
        weights[ticker] += float(percent_tna or 0) / 100
    return dict(weights), {
        "source_rows": len(source_rows),
        "ordinary_stock_rows": len(stock_rows),
        "total_report_weight": total_weight,
        "ordinary_stock_weight": sum(weights.values()),
        "cash_other_unknown_weight": total_weight - sum(weights.values()),
    }


def decode(path: Path, date: str, wanted: set[str]):
    store = db.DBNStore.from_file(path)
    candidates = defaultdict(set)
    for raw_symbol, mappings in store.metadata.mappings.items():
        symbol = raw_symbol.upper().strip()
        if symbol not in wanted:
            continue
        ids = {int(item["symbol"]) for item in mappings if str(item["start_date"]) <= date < str(item["end_date"])}
        if len(ids) == 1:
            candidates[next(iter(ids))].add(symbol)
    id_to_symbol = {instrument_id: next(iter(symbols)) for instrument_id, symbols in candidates.items() if len(symbols) == 1}
    records = defaultdict(list)
    for record in store:
        if not isinstance(record, BBOMsg) or int(record.instrument_id) not in id_to_symbol:
            continue
        symbol = id_to_symbol[int(record.instrument_id)]
        status, bid, ask = state(record)
        records[symbol].append((int(record.ts_recv), status, bid, ask))
    for symbol in records:
        records[symbol].sort(key=lambda row: row[0])
    return records, int(store.metadata.end), set(id_to_symbol.values())


def quote(records, file_end, symbol: str, anchor: datetime, minute: int, shift: int):
    return select(records.get(symbol, []), ns(anchor + timedelta(minutes=minute, seconds=shift)), file_end)


def correlation(x: list[float], y: list[float]) -> float | None:
    if len(x) < 3 or np.std(x) == 0 or np.std(y) == 0:
        return None
    return float(np.corrcoef(np.asarray(x), np.asarray(y))[0, 1])


def lag_rows(path_index: dict[int, tuple[float | None, float | None]], meta: dict, window: str):
    if window == "MAIN_-5_TO_30":
        level_minutes, fixed_t = list(range(-5, 31)), list(range(1, 26))
    else:
        level_minutes, fixed_t = list(range(0, 31)), list(range(6, 26))
    delta_e, delta_b = {}, {}
    for previous, minute in zip(level_minutes, level_minutes[1:]):
        e0, b0 = path_index.get(previous, (None, None))
        e1, b1 = path_index.get(minute, (None, None))
        if None not in (e0, b0, e1, b1):
            delta_e[minute], delta_b[minute] = e1 - e0, b1 - b0
    output = []
    for lag in LAGS:
        pairs = [(delta_e[t], delta_b[t + lag]) for t in fixed_t if t in delta_e and t + lag in delta_b]
        corr = correlation([p[0] for p in pairs], [p[1] for p in pairs]) if pairs else None
        output.append({**meta, "window": window, "lag_minutes": lag, "correlation": corr, "n_pairs": len(pairs)})
    return output


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if not HOLDING_FILES:
        raise RuntimeError("no holdings parquet files found")
    connection = duckdb.connect()
    source = "[" + ",".join(repr(path) for path in HOLDING_FILES) + "]"
    connection.execute(f"create view holdings as select * from read_parquet({source})")
    report_cache = {report: holdings(connection, report) for report in {row[2] for row in VARIANTS}}
    decoded = {}
    for event_id, _, report_date, anchor_text, _, _ in VARIANTS:
        key_date = datetime.fromisoformat(anchor_text.replace("Z", "+00:00")).date().isoformat()
        weights, _ = report_cache[report_date]
        for feed in FEEDS:
            key = (event_id, feed)
            if key not in decoded:
                filename = f"{event_id}_{feed.replace('.', '_')}.dbn.zst"
                spy_filename = f"{event_id}_{feed.replace('.', '_')}_SPY.dbn.zst"
                component_records, component_end, component_mapped = decode(OUT / filename, key_date, set(weights))
                spy_records, spy_end, spy_mapped = decode(OUT / spy_filename, key_date, {"SPY"})
                component_records["SPY"] = spy_records.get("SPY", [])
                decoded[key] = component_records, min(component_end, spy_end), component_mapped | spy_mapped

    paths, lags, coverage, events = [], [], [], []
    for event_id, issuer, report_date, anchor_text, anchor_label, clock_class in VARIANTS:
        anchor = datetime.fromisoformat(anchor_text.replace("Z", "+00:00"))
        weights, report_meta = report_cache[report_date]
        issuer_weight = weights.get(issuer, 0.0)
        common_symbols = set(weights)
        mapped_by_feed = {}
        for feed in FEEDS:
            records, file_end, mapped = decoded[(event_id, feed)]
            mapped_by_feed[feed] = mapped
            eligible = set()
            for symbol in weights:
                checks = []
                for shift in SHIFTS:
                    checks.append(quote(records, file_end, symbol, anchor, -5, shift))
                    checks.extend(quote(records, file_end, symbol, anchor, minute, shift) for minute in MAIN_MINUTES)
                if all(valid(item) for item in checks):
                    eligible.add(symbol)
            common_symbols &= eligible
        common_weight = sum(weights[symbol] for symbol in common_symbols)
        for feed in FEEDS:
            records, file_end, mapped = decoded[(event_id, feed)]
            mapped_weight = sum(weights.get(symbol, 0.0) for symbol in mapped)
            for shift in SHIFTS:
                baseline_quotes = {symbol: quote(records, file_end, symbol, anchor, -5, shift) for symbol in common_symbols | {"SPY"}}
                baseline_mid = {symbol: midpoint(value) for symbol, value in baseline_quotes.items()}
                path_index = {}
                for minute in MINUTES:
                    spy_quote = quote(records, file_end, "SPY", anchor, minute, shift)
                    spy_mid, spy_base = midpoint(spy_quote), baseline_mid.get("SPY")
                    etf_return = None if spy_mid is None or spy_base is None else spy_mid / spy_base - 1
                    etf_lower = None if not valid(spy_quote) or not valid(baseline_quotes["SPY"]) else spy_quote[1] / baseline_quotes["SPY"][2] - 1
                    etf_upper = None if not valid(spy_quote) or not valid(baseline_quotes["SPY"]) else spy_quote[2] / baseline_quotes["SPY"][1] - 1
                    basket = lower = upper = covered = rest = 0.0
                    issuer_return = None
                    issuer_lower_contribution = issuer_upper_contribution = 0.0
                    for symbol in common_symbols:
                        current, base = quote(records, file_end, symbol, anchor, minute, shift), baseline_quotes[symbol]
                        if not valid(current) or not valid(base):
                            continue
                        current_mid, base_mid = midpoint(current), midpoint(base)
                        component_return, weight = current_mid / base_mid - 1, weights[symbol]
                        component_lower = current[1] / base[2] - 1
                        component_upper = current[2] / base[1] - 1
                        basket += weight * component_return
                        lower += weight * component_lower
                        upper += weight * component_upper
                        covered += weight
                        if symbol == issuer:
                            issuer_return = component_return
                            issuer_lower_contribution = weight * component_lower
                            issuer_upper_contribution = weight * component_upper
                        else:
                            rest += weight * component_return
                    complete = abs(covered - common_weight) < 1e-12
                    basket_value = basket if complete else None
                    lower_value = lower if complete else None
                    upper_value = upper if complete else None
                    discrepancy = None if etf_return is None or not complete else etf_return - basket
                    implied = None if etf_return is None or issuer_weight <= 0 or not complete else (etf_return - rest) / issuer_weight
                    rest_lower = lower - issuer_lower_contribution
                    rest_upper = upper - issuer_upper_contribution
                    implied_lower = None if etf_lower is None or issuer_weight <= 0 or not complete else (etf_lower - rest_upper) / issuer_weight
                    implied_upper = None if etf_upper is None or issuer_weight <= 0 or not complete else (etf_upper - rest_lower) / issuer_weight
                    omitted_weight = report_meta["total_report_weight"] - covered
                    break_even = None if discrepancy is None or omitted_weight <= 0 else discrepancy / omitted_weight
                    row = {
                        "event_id": event_id, "issuer": issuer, "report_date": report_date,
                        "anchor_utc": anchor_text, "anchor_label": anchor_label, "clock_class": clock_class,
                        "feed": feed, "grid_shift_seconds": shift, "minute": minute,
                        "etf_status": spy_quote[0], "etf_return": etf_return,
                        "basket_return_subset": basket_value, "tracking_discrepancy": discrepancy,
                        "basket_lower": lower_value, "basket_upper": upper_value, "etf_lower": etf_lower, "etf_upper": etf_upper,
                        "coverage_weight": covered, "omitted_report_weight": omitted_weight,
                        "break_even_omitted_asset_return": break_even, "issuer_return": issuer_return,
                        "issuer_weight": issuer_weight, "issuer_implied_return": implied,
                        "issuer_implied_lower": implied_lower, "issuer_implied_upper": implied_upper,
                        "amplification_1_over_weight": None if issuer_weight <= 0 else 1 / issuer_weight,
                    }
                    paths.append(row)
                    path_index[minute] = (etf_return, basket_value)
                lag_meta = {
                    "event_id": event_id, "issuer": issuer, "anchor_utc": anchor_text,
                    "anchor_label": anchor_label, "feed": feed, "grid_shift_seconds": shift,
                    "fixed_common_weight": common_weight,
                }
                lags.extend(lag_rows(path_index, lag_meta, "MAIN_-5_TO_30"))
                lags.extend(lag_rows(path_index, lag_meta, "SUPPLEMENT_0_TO_30"))
                # Uniform finite sensitivity: remove the largest absolute +5 weighted
                # contribution, selected mechanically within each setting.
                contribution_rows = []
                for symbol in common_symbols:
                    base = baseline_quotes[symbol]
                    current = quote(records, file_end, symbol, anchor, 5, shift)
                    if valid(base) and valid(current):
                        component_return = midpoint(current) / midpoint(base) - 1
                        contribution_rows.append((abs(weights[symbol] * component_return), symbol, weights[symbol] * component_return, base, current))
                largest = max(contribution_rows) if contribution_rows else None
                sensitivity_best = None
                if largest:
                    _, largest_symbol, largest_contribution, largest_base, largest_current = largest
                    sensitivity_index = {}
                    for minute in MAIN_MINUTES:
                        etf_value, basket_value = path_index[minute]
                        current = quote(records, file_end, largest_symbol, anchor, minute, shift)
                        if etf_value is None or basket_value is None or not valid(current):
                            sensitivity_index[minute] = (etf_value, None)
                        else:
                            component_return = midpoint(current) / midpoint(largest_base) - 1
                            sensitivity_index[minute] = (etf_value, basket_value - weights[largest_symbol] * component_return)
                    sensitivity_candidates = [row for row in lag_rows(sensitivity_index, lag_meta, "MAIN_-5_TO_30") if row["correlation"] is not None]
                    sensitivity_best = max(sensitivity_candidates, key=lambda row: row["correlation"]) if sensitivity_candidates else None
                    baseline_target = ns(anchor + timedelta(minutes=-5, seconds=shift))
                    plus5_target = ns(anchor + timedelta(minutes=5, seconds=shift))
                    baseline_age = None if largest_base[3] is None else (baseline_target - largest_base[3]) / 1e9
                    plus5_age = None if largest_current[3] is None else (plus5_target - largest_current[3]) / 1e9
                    baseline_spread = 1e4 * (largest_base[2] - largest_base[1]) / midpoint(largest_base)
                    plus5_spread = 1e4 * (largest_current[2] - largest_current[1]) / midpoint(largest_current)
                else:
                    largest_symbol = largest_contribution = baseline_age = plus5_age = baseline_spread = plus5_spread = None
                coverage.append({
                    "event_id": event_id, "issuer": issuer, "report_date": report_date,
                    "anchor_utc": anchor_text, "anchor_label": anchor_label,
                    "feed": feed, "grid_shift_seconds": shift, **report_meta,
                    "unique_stock_tickers": len(weights), "mapped_stock_weight": mapped_weight,
                    "fixed_common_stock_count": len(common_symbols), "fixed_common_weight": common_weight,
                    "uncovered_report_weight": report_meta["total_report_weight"] - common_weight,
                    "issuer_weight": issuer_weight,
                    "amplification_1_over_weight": None if issuer_weight <= 0 else 1 / issuer_weight,
                    "largest_abs_plus5_component": largest_symbol,
                    "largest_abs_plus5_weighted_contribution": largest_contribution,
                    "largest_component_baseline_quote_age_seconds": baseline_age,
                    "largest_component_plus5_quote_age_seconds": plus5_age,
                    "largest_component_baseline_spread_bps": baseline_spread,
                    "largest_component_plus5_spread_bps": plus5_spread,
                    "best_lag_ex_largest_component": None if sensitivity_best is None else sensitivity_best["lag_minutes"],
                    "best_corr_ex_largest_component": None if sensitivity_best is None else sensitivity_best["correlation"],
                })

        main_lags = [row for row in lags if row["event_id"] == event_id and row["anchor_utc"] == anchor_text and row["window"] == "MAIN_-5_TO_30"]
        settings = []
        for feed in FEEDS:
            for shift in SHIFTS:
                candidates = [row for row in main_lags if row["feed"] == feed and row["grid_shift_seconds"] == shift and row["correlation"] is not None]
                settings.append((feed, shift, max(candidates, key=lambda row: row["correlation"]) if candidates else None))
        best_lags = [item[2]["lag_minutes"] for item in settings if item[2] is not None]
        if len(best_lags) != 4:
            classification = "UNABLE_TO_DISTINGUISH_DATA_LIMIT"
        elif all(value > 0 for value in best_lags):
            classification = "ETF_EARLIER_DESCRIPTIVE"
        elif all(value < 0 for value in best_lags):
            classification = "BASKET_EARLIER_DESCRIPTIVE"
        elif all(value == 0 for value in best_lags):
            classification = "MINUTE_SCALE_SIMULTANEOUS"
        else:
            classification = "MIXED_OR_GRID_VENUE_SENSITIVE"
        primary = [row for row in paths if row["event_id"] == event_id and row["anchor_utc"] == anchor_text and row["feed"] == "XNAS.ITCH" and row["grid_shift_seconds"] == 0]
        endpoint = {row["minute"]: row for row in primary}
        get_best = lambda feed, shift, key: next((best[key] for f, s, best in settings if f == feed and s == shift and best), None)
        events.append({
            "event_id": event_id, "issuer": issuer, "report_date": report_date,
            "anchor_utc": anchor_text, "anchor_label": anchor_label, "clock_class": clock_class,
            "classification": classification, "fixed_common_weight": common_weight,
            "issuer_weight": issuer_weight, "amplification_1_over_weight": None if issuer_weight <= 0 else 1 / issuer_weight,
            "xnas_plus5_etf_return": endpoint[5]["etf_return"], "xnas_plus5_basket_return": endpoint[5]["basket_return_subset"],
            "xnas_plus5_tracking_discrepancy": endpoint[5]["tracking_discrepancy"],
            "xnas_plus30_etf_return": endpoint[30]["etf_return"], "xnas_plus30_basket_return": endpoint[30]["basket_return_subset"],
            "xnas_plus30_tracking_discrepancy": endpoint[30]["tracking_discrepancy"],
            "best_lag_xnas_0s": get_best("XNAS.ITCH", 0, "lag_minutes"),
            "best_corr_xnas_0s": get_best("XNAS.ITCH", 0, "correlation"),
            "best_lag_xnas_30s": get_best("XNAS.ITCH", 30, "lag_minutes"),
            "best_lag_arcx_0s": get_best("ARCX.PILLAR", 0, "lag_minutes"),
            "best_lag_arcx_30s": get_best("ARCX.PILLAR", 30, "lag_minutes"),
        })

    write_csv(OUT / "BASKET_PATHS.csv", paths)
    write_csv(OUT / "LAG_DIAGNOSTICS.csv", lags)
    write_csv(OUT / "COVERAGE_AND_SENSITIVITY.csv", coverage)
    write_csv(OUT / "EVENT_RESULTS.csv", events)
    quote_receipt = json.loads((OUT / "BASKET_COST_QUOTE.json").read_text())
    quality = {
        "status": "COMPUTED", "events": 6, "clock_variants": 7,
        "feeds": list(FEEDS), "grid_shifts_seconds": list(SHIFTS),
        "path_rows": len(paths), "lag_rows": len(lags), "coverage_rows": len(coverage), "event_rows": len(events),
        "fixed_constituent_rule": "intersection with valid states at baseline and every -5..+30 minute target across both feeds and both 0/30-second grids; original report weights retained without survivor renormalization",
        "lag_pair_rule": "same t support for every lag: t=1..25 for main window and t=6..25 for supplemental window",
        "holdings_role": "retrospective lagged-report proxy, not verified event-time holdings",
        "basket_quoted_total_usd": quote_receipt["quoted_total_usd"],
        "spy_supplement_quoted_total_usd": json.loads((OUT / "SPY_SUPPLEMENT_COST_QUOTE.json").read_text())["quoted_total_usd"],
        "billing_ledger_debit_usd": "NOT_OBSERVED",
    }
    (OUT / "QUALITY_SUMMARY.json").write_text(json.dumps(quality, indent=2) + "\n")
    print(json.dumps(quality, indent=2))


if __name__ == "__main__":
    main()
