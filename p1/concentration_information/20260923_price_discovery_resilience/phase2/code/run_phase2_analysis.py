#!/usr/bin/env python3
"""SCC-only, bounded analysis for the 2023-01-24 NYSE opening-auction event.

This program reads one Databento DBN file at a time and writes only derived,
aggregate tables and figures to ``--out-dir``.  It deliberately calls the
cross-venue quote construct a *three-feed composite BBO*: it is never NBBO,
SIP, or complete-NMS coverage.  Raw DBN rows are neither copied nor exported.

Inputs are the files made by ``acquire_phase2.py`` and the 503-row roster made
by ``build_sp500_roster.py``.  The script is intentionally defensive about
DBN-version differences: unrecognised records are counted in the receipt,
not silently treated as prices, trades, or auction evidence.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import databento as db
from databento_dbn import MBP1Msg, UNDEF_ORDER_SIZE, UNDEF_PRICE

NS = 1_000_000_000
EVENT_DATE = "2023-01-24"
REFERENCE_DATES = ("2023-01-17", "2023-01-18", "2023-01-19", "2023-01-20", "2023-01-23",
                   "2023-01-25", "2023-01-26", "2023-01-27", "2023-01-30", "2023-01-31")
DATES = (*REFERENCE_DATES[:5], EVENT_DATE, *REFERENCE_DATES[5:])
VENUES = ("XNYS.PILLAR", "XNAS.ITCH", "ARCX.PILLAR")
ET_OPEN = 9 * 3600 + 30 * 60
ET_START = 9 * 3600 + 25 * 60
ET_END = 11 * 3600 + 30 * 60
MARKERS = (("OPEN_FAILURE", ET_OPEN), ("NYSE_INTERNAL_DISCOVERY", 10 * 3600 + 9 * 60),
           ("NYSE_MEMBER_DISCLOSURE", 10 * 3600 + 21 * 60),
           ("SCOPE_INVESTIGATION", 10 * 3600 + 53 * 60))
ENDPOINT_SECONDS = (1, 5, 30, 60, 300)
ACTIVITY_WINDOWS = {
    "PREOPEN_0925_092959": (-300, -1),
    "OPEN_0_300S": (0, 300),
    "POST_301_1800S": (301, 1800),
    "POST_1801_7200S": (1801, 7200),
    "FULL_0925_1130": (-300, 7200),
}


def canonical(symbol: object, shrcls: object | None = None) -> str:
    """Canonicalize Databento/CRSP class-ticker spellings (BRK B -> BRK.B)."""
    base = str(symbol or "").upper().strip().replace("/", ".")
    base = re.sub(r"\s+", " ", base)
    if shrcls is not None and str(shrcls).strip() not in {"", "<NA>", "NAN", "NONE"}:
        cls = str(shrcls).upper().strip()
        if not re.search(r"[ .-]" + re.escape(cls) + r"$", base):
            base = f"{base}.{cls}"
    m = re.fullmatch(r"([A-Z0-9]+)[ .-]([A-Z])", base)
    return f"{m.group(1)}.{m.group(2)}" if m else base.replace("-", ".")


def enum_value(value: object) -> str:
    return str(getattr(value, "value", value)).upper()


def request_meta(path: Path) -> tuple[str, str, str]:
    stem = path.name.removesuffix(".dbn.zst")
    # Dataset includes an underscore-normalized dot.  Some filenames also carry
    # a requested symbol token before the schema (for example ESH3_mbp-1), so
    # classify the schema from the finite known suffixes rather than treating
    # the entire remaining filename as a schema name.
    for dataset, token in (("XNYS.PILLAR", "XNYS_PILLAR"), ("XNAS.ITCH", "XNAS_ITCH"),
                           ("ARCX.PILLAR", "ARCX_PILLAR"), ("GLBX.MDP3", "GLBX_MDP3")):
        marker = "_" + token + "_"
        if marker in stem:
            date, tail = stem.split(marker, 1)
            for schema in ("bbo-1s", "trades", "mbp-1", "status", "statistics", "imbalance"):
                if tail == schema or tail.endswith("_" + schema):
                    return date, dataset, schema
            raise ValueError(f"unrecognised schema suffix in DBN request filename: {path.name}")
    raise ValueError(f"unrecognised DBN request filename: {path.name}")


def mapping(store: Any) -> dict[int, str]:
    return {int(span["symbol"]): canonical(raw)
            for raw, spans in store.metadata.mappings.items() for span in spans}


def bbo(record: Any) -> tuple[float, float, float, float] | None:
    if not hasattr(record, "levels"):
        return None
    level = record.levels[0]
    try:
        bid, ask, bid_sz, ask_sz = map(int, (level.bid_px, level.ask_px, level.bid_sz, level.ask_sz))
    except (AttributeError, TypeError, ValueError):
        return None
    if (bid in (UNDEF_PRICE, 0) or ask in (UNDEF_PRICE, 0)
            or bid_sz in (UNDEF_ORDER_SIZE, 0) or ask_sz in (UNDEF_ORDER_SIZE, 0)
            or bid < 0 or ask < bid):
        return None
    return bid / 1e9, ask / 1e9, float(bid_sz), float(ask_sz)


def ns_for(date: str, et_second: int) -> int:
    # All selected January 2023 sessions are EST (UTC-5); no DST conversion is implicit.
    return int(pd.Timestamp(f"{date}T00:00:00Z").value + (et_second + 5 * 3600) * NS)


def grid(date: str) -> np.ndarray:
    return np.arange(ns_for(date, ET_START), ns_for(date, ET_END) + NS, NS, dtype=np.int64)


def state_at(times: np.ndarray, values: np.ndarray, target: np.ndarray) -> np.ndarray:
    pos = np.searchsorted(times, target, side="right") - 1
    out = np.full(len(target), np.nan)
    good = pos >= 0
    out[good] = values[pos[good]]
    return out


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temp.replace(path)


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        fields.extend(k for k in row if k not in fields)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def decode_bbo_file(path: Path, allowed: set[str], target_grid: np.ndarray) -> tuple[pd.DataFrame, dict]:
    """Read one BBO/MBP DBN only; no future quote is used for an earlier grid cell."""
    store = db.DBNStore.from_file(path)
    symbols, rows, unknown = mapping(store), defaultdict(list), Counter()
    sampled_bbo = request_meta(path)[2] == "bbo-1s"
    for order, rec in enumerate(store):
        name = type(rec).__name__
        if not hasattr(rec, "ts_event") or not hasattr(rec, "instrument_id"):
            unknown[name] += 1; continue
        symbol = symbols.get(int(rec.instrument_id))
        if symbol not in allowed:
            continue
        quote = bbo(rec)
        action = enum_value(getattr(rec, "action", ""))
        # BBO-1s is sampled on ts_recv; ts_event is the last underlying venue
        # event and can be stale for several sampled seconds.  Event-driven
        # MBP uses ts_event below.
        stamp = int(rec.ts_recv) if sampled_bbo and hasattr(rec, "ts_recv") else int(rec.ts_event)
        rows[symbol].append((stamp, int(getattr(rec, "sequence", 0)), order, quote, action))
    output = []
    for symbol, values in rows.items():
        values.sort(key=lambda x: (x[0], x[1], x[2]))
        t, bid, ask, bsz, asz = [], [], [], [], []
        prior = None
        for stamp, _seq, _order, quote, action in values:
            # A clear/retract or invalid level destroys the previous executable state.
            if action in {"R", "CLEAR", "RETRACT"} or quote is None:
                current = None
            else:
                current = quote
            prior = current
            t.append(stamp)
            bid.append(current[0] if current else math.nan); ask.append(current[1] if current else math.nan)
            bsz.append(current[2] if current else math.nan); asz.append(current[3] if current else math.nan)
        arrays = [np.asarray(x) for x in (t, bid, ask, bsz, asz)]
        qbid, qask, qbsz, qasz = [state_at(arrays[0], a, target_grid) for a in arrays[1:]]
        valid = np.isfinite(qbid) & np.isfinite(qask) & (qbid > 0) & (qask >= qbid)
        qmid = np.where(valid, (qbid + qask) / 2, np.nan)
        changed = np.zeros(len(qmid), dtype=bool)
        changed[1:] = (np.isfinite(qmid[1:]) & np.isfinite(qmid[:-1]) & (qmid[1:] != qmid[:-1]))
        output.append(pd.DataFrame({"symbol": symbol, "t_ns": target_grid, "bid": qbid, "ask": qask,
                                    "bid_sz": qbsz, "ask_sz": qasz, "quote_valid": valid,
                                    "mid_change": changed}))
    return (pd.concat(output, ignore_index=True) if output else pd.DataFrame(),
            {"decoded_symbols": len(rows), "unrecognised_record_types": dict(unknown)})


def decode_trades_file(path: Path, allowed: set[str], date: str) -> tuple[pd.DataFrame, dict]:
    store = db.DBNStore.from_file(path)
    symbols, rows, unknown = mapping(store), defaultdict(lambda: [0, 0.0, 0]) , Counter()
    lo, hi = ns_for(date, ET_START), ns_for(date, ET_END) + NS
    for rec in store:
        name = type(rec).__name__.upper()
        if "TRADE" not in name or not hasattr(rec, "ts_event") or not hasattr(rec, "instrument_id"):
            if "TRADE" not in name: unknown[name] += 1
            continue
        symbol = symbols.get(int(rec.instrument_id))
        if symbol not in allowed:
            continue
        stamp = int(rec.ts_event)
        if not (lo <= stamp <= hi):
            continue
        try:
            price, size = int(rec.price), int(rec.size)
        except (AttributeError, TypeError, ValueError):
            continue
        second = (stamp // NS) * NS
        key = (symbol, second)
        action = enum_value(getattr(rec, "action", ""))
        rows[key][0] += 1
        if price not in (UNDEF_PRICE, 0) and size > 0:
            rows[key][1] += price / 1e9 * size
        if action in {"C", "R", "CANCEL", "CORRECT"}:
            rows[key][2] += 1
    out = [{"symbol": sym, "t_ns": sec, "trade_count": count, "trade_notional": notional,
            "trade_correction_records": corrections}
           for (sym, sec), (count, notional, corrections) in rows.items()]
    return pd.DataFrame(out), {"trade_rows": len(out), "unrecognised_record_types": dict(unknown)}


def decode_mbp_updates(path: Path, allowed: set[str], date: str,
                       state_symbol: str | None = None) -> tuple[list[dict], pd.DataFrame]:
    store, symbols, counts, states = db.DBNStore.from_file(path), None, Counter(), []
    symbols = mapping(store)
    for rec in store:
        if not isinstance(rec, MBP1Msg):
            continue
        symbol = symbols.get(int(rec.instrument_id))
        if symbol not in allowed:
            continue
        second = (int(rec.ts_event) - ns_for(date, ET_OPEN)) // NS
        for window, (lo, hi) in ACTIVITY_WINDOWS.items():
            if lo <= second <= hi:
                counts[(symbol, window)] += 1
        if state_symbol is not None and symbol == state_symbol:
            quote = bbo(rec)
            states.append((symbol, int(rec.ts_event), quote[0] if quote else math.nan,
                           quote[1] if quote else math.nan, enum_value(getattr(rec, "action", ""))))
    rows = [{"symbol": s, "time_window": window, "mbp1_message_count": n}
            for (s, window), n in counts.items()]
    state_frame = pd.DataFrame(states, columns=["symbol", "t_ns", "bid", "ask", "action"])
    return rows, state_frame


def mbp_path(states: pd.DataFrame, target: np.ndarray, symbol: str) -> pd.DataFrame:
    """Convert one already-opened MBP-1 stream into a right-continuous BBO path."""
    use = states[states.symbol == symbol].sort_values("t_ns")
    if use.empty:
        return pd.DataFrame(columns=["t_ns", "mid"])
    stamps, mids, current = [], [], None
    for row in use.itertuples(index=False):
        if row.action in {"R", "CLEAR", "RETRACT"} or not (np.isfinite(row.bid) and np.isfinite(row.ask) and row.bid > 0 and row.ask >= row.bid):
            current = math.nan
        else:
            current = (row.bid + row.ask) / 2
        stamps.append(row.t_ns); mids.append(current)
    return pd.DataFrame({"t_ns": target, "mid": state_at(np.asarray(stamps, dtype=np.int64), np.asarray(mids, float), target)})


def decode_xnys_admin(path: Path, allowed: set[str], date: str) -> tuple[list[dict], Counter]:
    """Retain only aggregate administrative evidence; absence is never proof by itself."""
    store, symbols, kinds, grouped = db.DBNStore.from_file(path), None, Counter(), Counter()
    symbols = mapping(store)
    for rec in store:
        if not hasattr(rec, "instrument_id"):
            continue
        symbol = symbols.get(int(rec.instrument_id))
        if symbol not in allowed:
            continue
        kind = type(rec).__name__.upper()
        if not any(x in kind for x in ("STATUS", "STAT", "IMBALANCE")):
            continue
        kinds[kind] += 1
        qualifier = (
            int(getattr(rec, "stat_type", -1)),
            enum_value(getattr(rec, "auction_type", "")),
            int(getattr(rec, "trading_event", -1)),
            enum_value(getattr(rec, "is_trading", "")),
            enum_value(getattr(rec, "is_quoting", "")),
        )
        grouped[(symbol, kind, *qualifier)] += 1
    schema = request_meta(path)[2]
    rows = [
        {"date": date, "schema": schema, "symbol": symbol, "record_type": kind,
         "stat_type": stat_type, "auction_type": auction_type,
         "trading_event": trading_event, "is_trading": is_trading,
         "is_quoting": is_quoting, "record_count": count}
        for (symbol, kind, stat_type, auction_type, trading_event, is_trading, is_quoting), count
        in grouped.items()
    ]
    return rows, kinds


def prepare_roster(path: Path) -> pd.DataFrame:
    roster = pd.read_parquet(path)
    if len(roster) != 503:
        raise RuntimeError(f"expected exactly 503 roster issues, found {len(roster)}")
    roster = roster.copy()
    roster["symbol"] = [canonical(t, c if str(t).upper().strip() in {"BF", "BRK"} else None)
                        for t, c in zip(roster["ticker"], roster.get("shrcls", pd.Series([None] * len(roster))))]
    roster["p0"] = pd.to_numeric(roster["prc"], errors="coerce").abs()
    roster["weight"] = pd.to_numeric(roster["weight_proxy"], errors="coerce")
    if roster.symbol.duplicated().any() or not np.isclose(roster.weight.sum(), 1.0) or (roster.p0 <= 0).any():
        raise RuntimeError("roster ticker, weight, or prior-close validation failed")
    roster["exchcd"] = pd.to_numeric(roster["exchcd"], errors="coerce").astype("Int64")
    return roster[["symbol", "weight", "p0", "exchcd"]]


def composite(date: str, venue_tables: dict[str, pd.DataFrame], roster: pd.DataFrame) -> pd.DataFrame:
    """Build the named three-feed composite BBO without calling it NBBO."""
    all_symbols = set(roster.symbol) | {"SPY"}
    pieces = []
    for venue, frame in venue_tables.items():
        if frame.empty:
            continue
        use = frame[frame.symbol.isin(all_symbols)].copy()
        use = use.rename(columns={"bid": f"bid_{venue}", "ask": f"ask_{venue}"})
        pieces.append(use[["symbol", "t_ns", f"bid_{venue}", f"ask_{venue}"]])
    if not pieces:
        return pd.DataFrame()
    wide = pieces[0]
    for piece in pieces[1:]:
        wide = wide.merge(piece, on=["symbol", "t_ns"], how="outer", validate="one_to_one")
    bid_cols, ask_cols = [c for c in wide if c.startswith("bid_")], [c for c in wide if c.startswith("ask_")]
    wide["composite_bid"] = wide[bid_cols].max(axis=1, skipna=True)
    wide["composite_ask"] = wide[ask_cols].min(axis=1, skipna=True)
    wide["composite_valid"] = (np.isfinite(wide.composite_bid) & np.isfinite(wide.composite_ask)
                               & (wide.composite_bid > 0) & (wide.composite_ask >= wide.composite_bid))
    wide["mid"] = np.where(wide.composite_valid, (wide.composite_bid + wide.composite_ask) / 2, np.nan)
    weights = roster.set_index("symbol")
    cash = wide[wide.symbol.isin(weights.index)].merge(weights, left_on="symbol", right_index=True, how="left")
    cash["covered_weight"] = np.where(np.isfinite(cash.mid), cash.weight, 0.0)
    cash["basket_term"] = np.where(np.isfinite(cash.mid), cash.weight * cash.mid / cash.p0, np.nan)
    summary = cash.groupby("t_ns", as_index=False).agg(covered_weight=("covered_weight", "sum"),
                                                          basket_raw=("basket_term", "sum"),
                                                          basket_issue_count=("symbol", "count"))
    summary["basket_valid_95"] = summary.covered_weight >= 0.95
    # No renormalization: an invalid basket remains missing rather than dividing by covered weight.
    summary["basket_value"] = np.where(summary.basket_valid_95, summary.basket_raw, np.nan)
    spy = wide[wide.symbol == "SPY"][["t_ns", "mid", "composite_valid"]].rename(
        columns={"mid": "spy_mid", "composite_valid": "spy_valid"})
    out = summary.merge(spy, on="t_ns", how="outer").sort_values("t_ns")
    out.insert(0, "date", date)
    out["price_source"] = "THREE_FEED_COMPOSITE_BBO_NOT_NBBO"
    return out


def normalize(frame: pd.DataFrame, col: str, date: str) -> tuple[np.ndarray, str]:
    cutoff = ns_for(date, ET_OPEN) - NS
    prior = frame.loc[(frame.t_ns <= cutoff) & np.isfinite(frame[col]), col]
    if len(prior):
        base, source = float(prior.iloc[-1]), "LAST_VALID_AT_OR_BEFORE_092959_ET"
    else:
        first = frame.loc[np.isfinite(frame[col]), col]
        base, source = (float(first.iloc[0]), "FALLBACK_FIRST_VALID_IN_WINDOW") if len(first) else (math.nan, "NO_VALID_BASE")
    return (frame[col].to_numpy(float) / base if math.isfinite(base) and base > 0 else np.full(len(frame), np.nan), source)


def build_daily_paths(date: str, comp: pd.DataFrame, es: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    target = comp.t_ns.to_numpy(np.int64)
    if es.empty:
        es_mid = np.full(len(target), np.nan)
    else:
        es_mid = state_at(es.t_ns.to_numpy(np.int64), es.mid.to_numpy(float), target)
    out = comp.copy(); out["esh3_mid"] = es_mid
    bases = {}
    for raw, normal in (("basket_value", "basket_norm"), ("spy_mid", "spy_norm"), ("esh3_mid", "esh3_norm")):
        out[normal], bases[raw] = normalize(out, raw, date)
    for left, right, name in (("basket_norm", "spy_norm", "basket_spy"),
                              ("basket_norm", "esh3_norm", "basket_esh3"),
                              ("spy_norm", "esh3_norm", "spy_esh3")):
        out[f"{name}_signed_bp"] = 1e4 * (out[left] - out[right])
        out[f"{name}_abs_bp"] = out[f"{name}_signed_bp"].abs()
    return out, bases


def activity_rows(date: str, venue_tables: dict[str, pd.DataFrame], trades: dict[str, pd.DataFrame],
                  mbp: dict[str, list[dict]], roster: pd.DataFrame) -> list[dict]:
    rows = []
    nyse = set(roster.loc[roster.exchcd.eq(1), "symbol"])
    non_nyse = set(roster.loc[~roster.exchcd.eq(1), "symbol"])
    groups = {
        "ALL_BASKET_AND_SPY": set(roster.symbol) | {"SPY"},
        "NYSE_LISTED_BASKET": nyse,
        "NON_NYSE_BASKET": non_nyse,
        "SPY_ETF": {"SPY"},
    }
    for venue in VENUES:
        q = venue_tables.get(venue, pd.DataFrame())
        t = trades.get(venue, pd.DataFrame())
        m = pd.DataFrame(mbp.get(venue, []))
        for group_name, symbols in groups.items():
            for window, (lo, hi) in ACTIVITY_WINDOWS.items():
                qg = q[q.symbol.isin(symbols)] if not q.empty else q
                tg = t[t.symbol.isin(symbols)] if not t.empty else t
                if not qg.empty:
                    qsec = (qg.t_ns - ns_for(date, ET_OPEN)) // NS
                    qg = qg[qsec.between(lo, hi)]
                if not tg.empty:
                    tsec = (tg.t_ns - ns_for(date, ET_OPEN)) // NS
                    tg = tg[tsec.between(lo, hi)]
                mg = m[m.symbol.isin(symbols) & m.time_window.eq(window)] if not m.empty else m
                rows.append({"date": date, "venue": venue, "universe_group": group_name,
                             "time_window": window, "start_second_from_open": lo,
                             "end_second_from_open": hi,
                             "valid_quote_seconds": int(qg.quote_valid.sum()) if not qg.empty else 0,
                             "midpoint_change_seconds": int(qg.mid_change.sum()) if not qg.empty else 0,
                             "trade_count": int(tg.trade_count.sum()) if not tg.empty else 0,
                             "trade_notional": float(tg.trade_notional.sum()) if not tg.empty else 0.0,
                             "trade_correction_records": int(tg.trade_correction_records.sum()) if not tg.empty else 0,
                             "mbp1_update_count": int(mg.mbp1_message_count.sum()) if not mg.empty else math.nan,
                             "quote_feed_available": not q.empty, "trade_feed_available": not t.empty,
                             "mbp1_requested_event_or_jan23_only": date in {EVENT_DATE, "2023-01-23"}})
    return rows


def normal_bands(paths: pd.DataFrame) -> pd.DataFrame:
    pairs = ("basket_spy", "basket_esh3", "spy_esh3")
    ref = paths[paths.date.isin(REFERENCE_DATES)]
    rows = []
    for pair in pairs:
        for second, values in ref.groupby("second_from_open")[f"{pair}_abs_bp"]:
            good = values.dropna().to_numpy(float)
            rows.append({"pair": pair, "second_from_open": int(second), "normal_n": len(good),
                         "normal_abs_p50_bp": float(np.quantile(good, .50)) if len(good) else math.nan,
                         "normal_abs_p975_bp": float(np.quantile(good, .975)) if len(good) else math.nan})
    return pd.DataFrame(rows)


def outcomes(event: pd.DataFrame, bands: pd.DataFrame) -> tuple[list[dict], list[dict], list[dict]]:
    pair_rows, endpoint_rows, recovery_rows = [], [], []
    event = event.copy().sort_values("second_from_open")
    for pair in ("basket_spy", "basket_esh3", "spy_esh3"):
        data = event[["second_from_open", f"{pair}_signed_bp", f"{pair}_abs_bp"]].merge(
            bands[bands.pair == pair], on="second_from_open", how="left")
        for label, marker in MARKERS:
            after = data[data.second_from_open >= marker - ET_OPEN].copy()
            for horizon in (300, 1800, ET_END - marker):
                use = after[after.second_from_open <= marker - ET_OPEN + horizon]
                # One-second grid: sum equals bp-seconds, and missing observations are not set to zero.
                pair_rows.append({"date": EVENT_DATE, "pair": pair, "marker": label, "horizon_seconds": horizon,
                                  "valid_seconds": int(use[f"{pair}_abs_bp"].notna().sum()),
                                  "abs_deviation_auc_bp_seconds": float(use[f"{pair}_abs_bp"].sum(min_count=1)),
                                  "right_censored_at_collection_end": horizon == ET_END - marker})
            for delta in ENDPOINT_SECONDS:
                hit = after[after.second_from_open == marker - ET_OPEN + delta]
                row = hit.iloc[0] if len(hit) else None
                endpoint_rows.append({"date": EVENT_DATE, "pair": pair, "marker": label, "seconds_after_marker": delta,
                                      "signed_deviation_bp": float(row[f"{pair}_signed_bp"]) if row is not None else math.nan,
                                      "absolute_deviation_bp": float(row[f"{pair}_abs_bp"]) if row is not None else math.nan,
                                      "covered_or_pair_valid": bool(row is not None and np.isfinite(row[f"{pair}_abs_bp"]))})
            trigger = after[after.second_from_open <= marker - ET_OPEN + 60].copy()
            supported = (np.isfinite(trigger[f"{pair}_abs_bp"].to_numpy(float))
                         & np.isfinite(trigger.normal_abs_p975_bp.to_numpy(float)))
            exceeded = supported & (trigger[f"{pair}_abs_bp"].to_numpy(float)
                                    > trigger.normal_abs_p975_bp.to_numpy(float))
            if not supported.any():
                status, recovery_second = "MISSING_SUPPORT", math.nan
                loss_second = math.nan
            elif not exceeded.any():
                status, recovery_second = "NO_DETECTABLE_INITIAL_LOSS", math.nan
                loss_second = math.nan
            else:
                first_loss = int(np.flatnonzero(exceeded)[0])
                loss_second = int(trigger.iloc[first_loss].second_from_open)
                after_loss = after[after.second_from_open >= loss_second]
                good = ((after_loss[f"{pair}_abs_bp"].to_numpy(float) <= after_loss.normal_abs_p975_bp.to_numpy(float))
                        & np.isfinite(after_loss[f"{pair}_abs_bp"].to_numpy(float))
                        & np.isfinite(after_loss.normal_abs_p975_bp.to_numpy(float)))
                found = next((i for i in range(len(good) - 29) if good[i:i + 30].all()), None)
                status = "RECOVERED_30_CONSECUTIVE_VALID_SECONDS" if found is not None else "RIGHT_CENSORED_NO_30_SECOND_RECOVERY"
                recovery_second = int(after_loss.iloc[found].second_from_open) if found is not None else math.nan
            recovery_rows.append({"date": EVENT_DATE, "pair": pair, "marker": label, "status": status,
                                  "initial_loss_detected_second_from_open": loss_second,
                                  "initial_loss_detection_window_seconds": 60,
                                  "recovery_second_from_open": recovery_second, "continuity_seconds_required": 30})
    return pair_rows, endpoint_rows, recovery_rows


def figure_paths(paths: pd.DataFrame, out: Path) -> None:
    event = paths[paths.date == EVENT_DATE]
    x = event.second_from_open / 60
    event = event[event.second_from_open >= 0]
    x = event.second_from_open / 60
    fig, ax = plt.subplots(figsize=(10, 5));
    ax.plot(x, event.covered_weight, label="cash basket covered weight")
    ax.plot(x, event.basket_valid_95.astype(float), label="basket valid (>=95%)", alpha=.7)
    ax.set(xlabel="minutes after 09:30 ET", ylabel="weight / indicator", title="Cash-basket coverage and validity")
    ax.legend(); fig.tight_layout(); fig.savefig(out / "FIG1_COVERAGE.png", dpi=160); plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 5));
    for column, label in (("basket_norm", "cash basket"), ("spy_norm", "SPY"), ("esh3_norm", "ESH3")):
        ax.plot(x, 1e4 * (event[column] - 1), label=label)
    ax.set(xlabel="minutes after 09:30 ET", ylabel="normalized move (bp)", title="Three-tool normalized paths")
    ax.legend(); fig.tight_layout(); fig.savefig(out / "FIG3_THREE_TOOL_PATHS.png", dpi=160); plt.close(fig)


def figure_activity(activity: pd.DataFrame, out: Path) -> None:
    use = activity[activity.universe_group.eq("NYSE_LISTED_BASKET")
                   & activity.time_window.eq("OPEN_0_300S")].copy()
    event = use[use.date.eq(EVENT_DATE)].set_index("venue")
    normal = use[use.date.isin(REFERENCE_DATES)].groupby("venue")[["trade_notional", "midpoint_change_seconds"]].median()
    ratio = event[["trade_notional", "midpoint_change_seconds"]].div(normal).rename(
        columns={"trade_notional": "trade-notional ratio", "midpoint_change_seconds": "midpoint-update ratio"})
    fig, ax = plt.subplots(figsize=(8, 5)); ratio.plot.bar(ax=ax)
    ax.axhline(1, color="black", linewidth=.8, linestyle="--")
    ax.set(ylabel="event / 10-session same-window median",
           title="NYSE-listed basket activity, first five minutes")
    fig.tight_layout(); fig.savefig(out / "FIG2_VENUE_ACTIVITY.png", dpi=160); plt.close(fig)


def figure_deviation(event: pd.DataFrame, bands: pd.DataFrame, out: Path) -> None:
    event = event[event.second_from_open >= 0]
    fig, ax = plt.subplots(figsize=(10, 5)); x = event.second_from_open / 60
    for pair in ("basket_spy", "basket_esh3", "spy_esh3"):
        b = bands[bands.pair == pair].set_index("second_from_open")
        ax.plot(x, event[f"{pair}_abs_bp"], label=f"{pair} absolute")
        ax.plot(x, event.second_from_open.map(b.normal_abs_p975_bp), linestyle="--", alpha=.45)
    ax.set(xlabel="minutes after 09:30 ET", ylabel="absolute deviation (bp)", title="System deviations and same-clock normal bands")
    ax.legend(ncol=2); fig.tight_layout(); fig.savefig(out / "FIG4_DEVIATION_RECOVERY.png", dpi=160); plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", type=Path, default=Path("/project/econdept/qluo/p1_price_discovery_resilience_20260923/phase2/raw/databento"))
    ap.add_argument("--roster", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--work-dir", type=Path, required=True, help="SCC-only temporary derived per-venue tables")
    args = ap.parse_args(); args.out_dir.mkdir(parents=True, exist_ok=True); args.work_dir.mkdir(parents=True, exist_ok=True)
    roster, allowed = prepare_roster(args.roster), set()
    allowed = set(roster.symbol) | {"SPY", "ESH3"}
    files = sorted(args.raw_dir.rglob("*.dbn.zst"))
    if not files: raise RuntimeError(f"no DBN files under {args.raw_dir}")
    by_date: dict[str, list[Path]] = defaultdict(list)
    for path in files:
        date, _dataset, _schema = request_meta(path)
        if date in DATES: by_date[date].append(path)
    admin, record_types, processed, activity, mbp_rows = [], Counter(), [], [], []
    daily_path_files: list[Path] = []
    # Work a date at a time. Within each date, each native DBN is opened once,
    # converted to a temporary derived table, and released before the next date.
    for date in DATES:
        q, trades, mbp, es = {}, {}, {}, None
        for path in sorted(by_date[date]):
            _date, dataset, schema = request_meta(path)
            if schema == "bbo-1s":
                table, meta = decode_bbo_file(path, allowed, grid(date))
                q[dataset] = pd.concat([q.get(dataset, pd.DataFrame()), table], ignore_index=True)
                q[dataset] = q[dataset].drop_duplicates(["symbol", "t_ns"], keep="last")
                record_types.update(meta["unrecognised_record_types"])
            elif schema == "trades":
                table, meta = decode_trades_file(path, allowed, date)
                trades[dataset] = pd.concat([trades.get(dataset, pd.DataFrame()), table], ignore_index=True)
                record_types.update(meta["unrecognised_record_types"])
            elif schema == "mbp-1":
                counts, states = decode_mbp_updates(
                    path, allowed, date, state_symbol="ESH3" if dataset == "GLBX.MDP3" else None
                )
                mbp.setdefault(dataset, []).extend(counts)
                if dataset == "GLBX.MDP3": es = mbp_path(states, grid(date), "ESH3")
                record_types["MBP1_MESSAGES"] += sum(
                    x["mbp1_message_count"] for x in counts if x["time_window"] == "FULL_0925_1130"
                )
            elif dataset == "XNYS.PILLAR" and schema in {"status", "statistics", "imbalance"}:
                rows, kinds = decode_xnys_admin(path, allowed, date); admin.extend(rows); record_types.update(kinds)
            processed.append({"file": path.name, "date": date, "dataset": dataset, "schema": schema})
        if es is None:
            raise RuntimeError(f"missing GLBX.MDP3 ESH3 MBP-1 file for {date}")
        comp = composite(date, q, roster)
        if comp.empty: raise RuntimeError(f"no named-feed BBO support for {date}")
        daily, bases = build_daily_paths(date, comp, es); daily["second_from_open"] = ((daily.t_ns - ns_for(date, ET_OPEN)) // NS).astype(int)
        daily["basket_base_source"], daily["spy_base_source"], daily["esh3_base_source"] = bases["basket_value"], bases["spy_mid"], bases["esh3_mid"]
        temporary_path = args.work_dir / f"{date}_COMPOSITE_PATH.parquet"
        daily.to_parquet(temporary_path, index=False); daily_path_files.append(temporary_path)
        activity.extend(activity_rows(date, q, trades, mbp, roster))
        mbp_rows.extend({"date": date, "venue": venue, **row} for venue, rows in mbp.items() for row in rows)
        del q, trades, mbp, es, comp, daily
    path_table, activity_table = pd.concat([pd.read_parquet(p) for p in daily_path_files], ignore_index=True), pd.DataFrame(activity)
    bands = normal_bands(path_table); event = path_table[path_table.date == EVENT_DATE]
    auc, endpoints, recovery = outcomes(event, bands)
    auction = pd.DataFrame(admin)
    if not auction.empty:
        auction["is_opening_related_evidence"] = auction.record_type.str.contains("STAT|IMBALANCE", regex=True)
        auction["is_opening_price_stat"] = auction.record_type.str.contains("STAT", regex=True) & auction.stat_type.eq(1)
    else:
        auction = pd.DataFrame(columns=["date", "schema", "symbol", "record_type", "record_count",
                                                "is_opening_related_evidence", "is_opening_price_stat"])
    event_admin = auction[auction.date.eq(EVENT_DATE)] if not auction.empty else auction
    observed_opening = set(event_admin.loc[event_admin.is_opening_price_stat, "symbol"])
    reference_open_counts = (auction[auction.date.isin(REFERENCE_DATES) & auction.is_opening_price_stat]
                             .groupby("symbol").date.nunique()) if not auction.empty else pd.Series(dtype=int)
    validation = roster[["symbol", "exchcd"]].copy()
    validation["date"] = EVENT_DATE
    validation["historical_nyse_listing"] = validation.exchcd.eq(1)
    validation["event_opening_price_stat_present"] = validation.symbol.isin(observed_opening)
    validation["reference_days_with_opening_price_stat"] = validation.symbol.map(reference_open_counts).fillna(0).astype(int)
    validation["auction_evidence_status"] = np.select(
        [~validation.historical_nyse_listing,
         validation.historical_nyse_listing & ~validation.event_opening_price_stat_present
         & validation.reference_days_with_opening_price_stat.gt(0),
         validation.historical_nyse_listing & validation.event_opening_price_stat_present],
        ["NON_NYSE_LISTED_DESCRIPTIVE_COMPARISON",
         "SEC_SCOPE_NYSE_LISTED_AND_EVENT_OPEN_STAT_ABSENT_WITH_REFERENCE_SUPPORT",
         "EVENT_OPENING_PRICE_STAT_PRESENT_REQUIRES_RECONCILIATION"],
        default="UNKNOWN_INSUFFICIENT_ADMIN_SUPPORT",
    )
    admin_summary = event_admin.groupby("symbol", as_index=False).agg(
        xnys_admin_record_count=("record_count", "sum"),
        xnys_admin_record_types=("record_type", lambda values: ";".join(sorted(set(values)))),
    )
    validation = validation.merge(admin_summary, on="symbol", how="left")
    for name, value in (("COMPOSITE_PATHS.csv", path_table), ("VENUE_ACTIVITY.csv", activity_table),
                        ("NORMAL_BANDS.csv", bands), ("DEVIATION_AUC.csv", pd.DataFrame(auc)),
                        ("PATH_ENDPOINTS.csv", pd.DataFrame(endpoints)), ("RECOVERY.csv", pd.DataFrame(recovery)),
                        ("XNYS_AUCTION_ADMIN_RECORDS.csv", auction), ("XNYS_AUCTION_VALIDATION.csv", validation)):
        value.to_csv(args.out_dir / name, index=False)
    pd.DataFrame(mbp_rows).to_csv(args.out_dir / "MBP1_UPDATE_COUNTS.csv", index=False)
    figure_paths(path_table, args.out_dir); figure_activity(activity_table, args.out_dir); figure_deviation(event, bands, args.out_dir)
    receipt = {"status": "COMPLETE_DERIVED_AGGREGATES_ON_SCC", "event_date": EVENT_DATE,
               "raw_dir": str(args.raw_dir), "roster_rows": len(roster), "dates": list(DATES), "venues": list(VENUES),
               "composite_label": "THREE_FEED_COMPOSITE_BBO_NOT_NBBO", "basket_threshold": 0.95,
               "no_missing_weight_renormalization": True, "processed_files": processed,
               "unrecognised_record_type_counts": dict(record_types), "raw_rows_exported": False,
               "limitations": ["Direct-feed composite is not NBBO or complete NMS coverage.",
                               "As-disseminated and later corrected/busted states are only separated where source fields identify them.",
                               "Missing ESH3/state support remains missing; it is never interpolated."],
               "output_files": sorted(p.name for p in args.out_dir.iterdir() if p.is_file())}
    atomic_json(args.out_dir / "ANALYSIS_RECEIPT.json", receipt)
    print(json.dumps({"status": receipt["status"], "path_rows": len(path_table), "files": len(processed)}, sort_keys=True))


if __name__ == "__main__":
    main()
