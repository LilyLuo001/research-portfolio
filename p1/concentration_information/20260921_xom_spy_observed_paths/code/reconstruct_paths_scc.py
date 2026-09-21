#!/usr/bin/env python3
"""SCC-only reconstruction for the 2023-01-31 XOM announcement window.

Reads licensed DBN and CRSP rows only on SCC.  Emits compact derived paths,
endpoints, and quality aggregates; it never copies a DBN record off SCC.
"""
import csv
import glob
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import databento as db
from databento_dbn import BBOMsg, UNDEF_ORDER_SIZE, UNDEF_PRICE
import duckdb

ROOT = Path("/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared")
OUT = Path("/scratch/qluo/xom_spy_observed_paths_20260921")
FILES = [
    ("XNAS.ITCH", ROOT / "derived/p1_concentration_information/20260920_phase3/measurement/native_dbn/3e771140b59d588abd71.dbn.zst"),
    ("BATS.PITCH", ROOT / "derived/p1_concentration_information/20260920_phase3/measurement/native_dbn/4813a1381403d9d1c15e.dbn.zst"),
    ("ARCX.PILLAR", ROOT / "derived/p1_concentration_information/20260920_phase3/measurement/native_dbn_second/0960f2ea732a055227d0.dbn.zst"),
    ("XNYS.PILLAR", ROOT / "derived/p1_concentration_information/20260920_phase3/measurement/native_dbn_second/c44a02dd5fbacdfcb1f2.dbn.zst"),
]
EVENT_DATE = "2023-01-31"
ANCHORS = {"06:29_ET": "2023-01-31T11:29:00+00:00", "06:30_ET": "2023-01-31T11:30:00+00:00", "06:31_ET": "2023-01-31T11:31:00+00:00"}
ENDPOINTS = [1, 5, 15, 30, 60]

def ns(dt):
    return int(dt.timestamp() * 1_000_000_000)

def dt(s):
    return datetime.fromisoformat(s)

def active_mappings(meta):
    """Map date-valid metadata symbols to instrument IDs; no ticker inference."""
    out = {}
    for symbol, mappings in meta.mappings.items():
        ids = set()
        for item in mappings:
            if str(item["start_date"]) <= EVENT_DATE < str(item["end_date"]):
                ids.add(int(item["symbol"]))
        if len(ids) == 1:
            out[str(symbol).upper()] = next(iter(ids))
    return out

def holding_subset(available_symbols):
    """Fixed Dec-31 CRSP-report stock subset, intersected before any paths."""
    paths = sorted(glob.glob(str(ROOT / "raw/rescue_remaining/crsp_holdings_etf_2022_*/part_*.parquet")))
    con = duckdb.connect()
    psql = "[" + ",".join(repr(p) for p in paths) + "]"
    con.execute(f"CREATE VIEW h AS SELECT report_dt,crsp_portno,ticker,nbr_shares,percent_tna FROM read_parquet({psql})")
    rows = con.execute("""
      SELECT upper(trim(ticker)) ticker, sum(nbr_shares) shares,
             sum(percent_tna) report_weight
      FROM h WHERE crsp_portno=1021980 AND CAST(report_dt AS DATE)=DATE '2022-12-31'
        AND ticker IS NOT NULL AND nbr_shares IS NOT NULL AND nbr_shares>0
      GROUP BY 1
    """).fetchall()
    all_stocks = {r[0]: (float(r[1]), float(r[2]) if r[2] is not None else None) for r in rows if r[0] not in {"SPY", "QQQ"}}
    chosen = {s: all_stocks[s] for s in sorted(all_stocks) if s in available_symbols}
    weights = [v[1] for v in chosen.values() if v[1] is not None]
    return chosen, {"report_date":"2022-12-31", "report_effective_date":"2023-01-09", "report_stock_rows":len(all_stocks), "fixed_available_subset_count":len(chosen), "fixed_available_subset_report_weight_sum":sum(weights) if weights else None, "weight_rows_available":len(weights)}

def valid(level):
    b, a, bs, az = map(int, (level.bid_px, level.ask_px, level.bid_sz, level.ask_sz))
    return b != UNDEF_PRICE and a != UNDEF_PRICE and bs != UNDEF_ORDER_SIZE and az != UNDEF_ORDER_SIZE and b > 0 and a >= b and bs > 0 and az > 0

def snapshot(records, target):
    got = None
    for rec in records:
        if rec[0] <= target:
            got = rec
        else:
            break
    if got is None:
        return None
    t, bid, ask, flags = got
    return {"ts":t, "bid":bid / 1e9, "ask":ask / 1e9, "mid":(bid + ask) / 2e9, "spread_bps":(ask-bid) / ((ask+bid)/2) * 1e4, "age_seconds":(target-t)/1e9, "flags":flags}

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    primary_symbols = None
    file_results = {}
    mapping_summaries = {}
    for venue, path in FILES:
        store = db.DBNStore.from_file(path)
        mappings = active_mappings(store.metadata)
        mapping_summaries[venue] = {"mapped_symbols":sorted(mappings), "symbol_count":len(mappings)}
        if primary_symbols is None:
            primary_symbols = mappings
        # Preserve each venue as a separate diagnostic. Prices are only read for
        # SPY/XOM and the predeclared fixed stock subset on the primary venue.
        file_results[venue] = {"mappings":mappings, "path":str(path), "records":defaultdict(list), "metadata_start_ns":int(store.metadata.start), "metadata_end_ns":int(store.metadata.end)}

    subset, subset_quality = holding_subset(set(primary_symbols))
    wanted_primary = {"SPY", "XOM"} | set(subset)
    for venue, result in file_results.items():
        wanted = wanted_primary if venue == "XNAS.ITCH" else {"SPY", "XOM"}
        id_to_symbol = {iid:sym for sym, iid in result["mappings"].items() if sym in wanted}
        start = ns(dt("2023-01-31T11:15:00+00:00")); end = ns(dt("2023-01-31T12:45:00+00:00"))
        store = db.DBNStore.from_file(Path(result["path"]))
        for record in store:
            iid = int(record.instrument_id)
            if iid not in id_to_symbol or not isinstance(record, BBOMsg):
                continue
            t = int(record.ts_recv)
            if t < start or t > end or not valid(record.levels[0]):
                continue
            level = record.levels[0]
            result["records"][id_to_symbol[iid]].append((t, int(level.bid_px), int(level.ask_px), int(record.flags)))

    # Freeze one usable subset before calculating any proxy path.  A component
    # must have an observed state by the 06:30-anchor baseline and at every
    # announced endpoint; stale-but-valid states remain observations rather
    # than being silently converted into zero returns.
    primary_records = file_results["XNAS.ITCH"]["records"]
    anchor_630 = dt(ANCHORS["06:30_ET"])
    eligibility_times = [ns(anchor_630 - timedelta(minutes=5))] + [ns(anchor_630 + timedelta(minutes=h)) for h in ENDPOINTS]
    subset = {s:v for s,v in subset.items() if all(snapshot(primary_records.get(s, []), t) is not None for t in eligibility_times)}
    subset_quality["fixed_available_subset_count"] = len(subset)
    subset_quality["fixed_available_subset_report_weight_sum"] = sum(v[1] for v in subset.values() if v[1] is not None)
    subset_quality["selection_rule"] = "date-valid XNAS mapping; Dec-31 CRSP report stock; quote state at 06:30-anchor baseline and every +1/+5/+15/+30/+60 endpoint"
    subset_quality["retained_symbols"] = sorted(subset)
    subset_quality["quantity_basis"] = "sum of CRSP 2022-12-31 nbr_shares by ticker; common scale cancels after baseline normalization"
    value_base = {s: v[0] * snapshot(primary_records.get(s, []), eligibility_times[0])["mid"] for s, v in subset.items()}
    total_value_base = sum(value_base.values())
    subset_quality["baseline_value_weights"] = {s: value_base[s] / total_value_base for s in sorted(value_base)} if total_value_base else {}
    subset_quality["xom_baseline_value_share"] = value_base.get("XOM", 0.0) / total_value_base if total_value_base else None
    subset_ex_xom = {s:v for s,v in subset.items() if s != "XOM"}
    subset_quality["ex_xom_subset_count"] = len(subset_ex_xom)

    endpoint_rows, path_rows, quality = [], [], {"event_id":"P1-2023-08-01", "schema":"bbo-1s", "time_semantics":"ts_recv interval end", "primary_feed":"XNAS.ITCH", "feeds":{}, "basket":subset_quality, "anchors":ANCHORS}
    for venue, result in file_results.items():
        quality["feeds"][venue] = {"path":result["path"], "mapped_symbol_count":len(result["mappings"]), "selected_record_counts":{s:len(r) for s,r in result["records"].items()}, "observed_symbols":sorted(result["records"])}
        for label, anchor_str in ANCHORS.items():
            anchor = dt(anchor_str); base_target = ns(anchor-timedelta(minutes=5))
            for sym in ("SPY", "XOM"):
                base = snapshot(result["records"].get(sym, []), base_target)
                for h in [0] + ENDPOINTS:
                    point = snapshot(result["records"].get(sym, []), ns(anchor+timedelta(minutes=h)))
                    row = {"object":sym, "object_type":"ETF" if sym=="SPY" else "STOCK", "feed":venue, "anchor":label, "horizon_minutes":h, "baseline_mid":None if base is None else base["mid"], "mid":None if point is None else point["mid"], "bid":None if point is None else point["bid"], "ask":None if point is None else point["ask"], "mid_index":None if not base or not point else 100*point["mid"]/base["mid"], "mid_change_bps":None if not base or not point else 1e4*(point["mid"]/base["mid"]-1), "spread_bps":None if point is None else point["spread_bps"], "quote_age_seconds":None if point is None else point["age_seconds"], "observed":"YES" if base and point else "NO"}
                    endpoint_rows.append(row)
            if venue == "XNAS.ITCH":
                for minute in range(-15, 76):
                    target = ns(anchor+timedelta(minutes=minute))
                    values = {}
                    for sym in ("SPY", "XOM"):
                        base = snapshot(result["records"].get(sym, []), base_target); p = snapshot(result["records"].get(sym, []), target)
                        values[sym] = None if not base or not p else 100*p["mid"]/base["mid"]
                    bases, pts = [], []
                    complete = True
                    for sym, (shares, _) in subset.items():
                        b = snapshot(result["records"].get(sym, []), base_target); p = snapshot(result["records"].get(sym, []), target)
                        if not b or not p:
                            complete = False; break
                        bases.append(shares*b["mid"]); pts.append(shares*p["mid"])
                    proxy = 100*sum(pts)/sum(bases) if complete and bases and sum(bases)>0 else None
                    ex_bases, ex_pts = [], []
                    ex_complete = True
                    for sym, (shares, _) in subset_ex_xom.items():
                        b = snapshot(result["records"].get(sym, []), base_target); p = snapshot(result["records"].get(sym, []), target)
                        if not b or not p:
                            ex_complete = False; break
                        ex_bases.append(shares*b["mid"]); ex_pts.append(shares*p["mid"])
                    ex_proxy = 100*sum(ex_pts)/sum(ex_bases) if ex_complete and ex_bases and sum(ex_bases)>0 else None
                    path_rows.append({"feed":venue,"anchor":label,"minute_from_anchor":minute,"SPY_mid_index":values["SPY"],"XOM_mid_index":values["XOM"],"CRSP_lagged_fixed_available_subset_mid_index":proxy,"CRSP_lagged_fixed_available_subset_ex_XOM_mid_index":ex_proxy,"proxy_complete_fixed_subset":complete,"ex_xom_proxy_complete_fixed_subset":ex_complete})
                for h in [0] + ENDPOINTS:
                    proxy_point = next((x for x in path_rows if x["anchor"]==label and x["minute_from_anchor"]==h), None)
                    endpoint_rows.append({"object":"CRSP_LAGGED_FIXED_AVAILABLE_STOCK_SUBSET","object_type":"LAGGED_HOLDINGS_STOCK_PROXY","feed":venue,"anchor":label,"horizon_minutes":h,"baseline_mid":100.0,"mid":None if proxy_point is None else proxy_point["CRSP_lagged_fixed_available_subset_mid_index"],"bid":None,"ask":None,"mid_index":None if proxy_point is None else proxy_point["CRSP_lagged_fixed_available_subset_mid_index"],"mid_change_bps":None if not proxy_point or proxy_point["CRSP_lagged_fixed_available_subset_mid_index"] is None else 1e4*(proxy_point["CRSP_lagged_fixed_available_subset_mid_index"]/100-1),"spread_bps":None,"quote_age_seconds":None,"observed":"YES" if proxy_point and proxy_point["CRSP_lagged_fixed_available_subset_mid_index"] is not None else "NO"})
                    endpoint_rows.append({"object":"CRSP_LAGGED_FIXED_AVAILABLE_STOCK_SUBSET_EX_XOM","object_type":"LAGGED_HOLDINGS_STOCK_PROXY_SPILLOVER_DIAGNOSTIC","feed":venue,"anchor":label,"horizon_minutes":h,"baseline_mid":100.0,"mid":None if proxy_point is None else proxy_point["CRSP_lagged_fixed_available_subset_ex_XOM_mid_index"],"bid":None,"ask":None,"mid_index":None if proxy_point is None else proxy_point["CRSP_lagged_fixed_available_subset_ex_XOM_mid_index"],"mid_change_bps":None if not proxy_point or proxy_point["CRSP_lagged_fixed_available_subset_ex_XOM_mid_index"] is None else 1e4*(proxy_point["CRSP_lagged_fixed_available_subset_ex_XOM_mid_index"]/100-1),"spread_bps":None,"quote_age_seconds":None,"observed":"YES" if proxy_point and proxy_point["CRSP_lagged_fixed_available_subset_ex_XOM_mid_index"] is not None else "NO"})
    with (OUT/"ENDPOINTS.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(endpoint_rows[0])); w.writeheader(); w.writerows(endpoint_rows)
    with (OUT/"PATHS.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(path_rows[0])); w.writeheader(); w.writerows(path_rows)
    (OUT/"QUALITY_SUMMARY.json").write_text(json.dumps(quality,indent=2)+"\n")
    print(json.dumps({"endpoints":len(endpoint_rows),"paths":len(path_rows),"subset":subset_quality}))

if __name__ == "__main__":
    main()
