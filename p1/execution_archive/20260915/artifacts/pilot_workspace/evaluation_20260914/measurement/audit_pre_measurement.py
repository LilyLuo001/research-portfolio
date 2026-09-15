#!/usr/bin/env python3
"""PRE-only quote-measurement audit for the frozen P1 pilot.

This script deliberately never opens a file unless it is designated
DEVELOPMENT_PRE_FOCAL_ONLY, and only reads records whose BBO endpoint clock is
inside an event-map PRE leg.  It writes aggregates, never quote prices.
"""
from __future__ import annotations
import csv, hashlib, json, math, pathlib
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import databento as db
try:
    from databento_dbn import UNDEF_PRICE, UNDEF_ORDER_SIZE
except ImportError:
    UNDEF_PRICE, UNDEF_ORDER_SIZE = 9223372036854775807, 4294967295

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
NY = ZoneInfo("America/New_York")
NS = 1_000_000_000

def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def write_csv(name, rows, fields):
    with (OUT / name).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
def cid(r):
    return hashlib.sha256("\x1f".join(r[x] for x in ("dataset","schema","symbols","stype_in","start","end")).encode()).hexdigest()
def ns_iso(s): return int(datetime.fromisoformat(s.replace("Z","+00:00")).timestamp()*NS)
def local_ns(date, clock):
    return int(datetime.fromisoformat(date+"T"+clock).replace(tzinfo=NY).timestamp()*NS)
def iso(t):
    return datetime.fromtimestamp(t/NS, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def session(t):
    x = datetime.fromtimestamp(t/NS, NY).time()
    if x < datetime.strptime("09:30", "%H:%M").time(): return "PRE"
    if x < datetime.strptime("16:00", "%H:%M").time(): return "RTH"
    return "AFTER"
def record_ns(r):
    return int(getattr(r, "ts_recv"))
def qkey(r): return (str(getattr(r,"publisher_id","UNKNOWN")), str(getattr(r,"instrument_id","UNKNOWN")))
def side_values(r):
    """Direct names are the tested API; levels[0] is an explicit fallback."""
    source = "direct"
    try:
        v = (int(r.bid_px_00), int(r.ask_px_00), int(r.bid_sz_00), int(r.ask_sz_00))
    except (AttributeError, TypeError, ValueError):
        source = "levels0"
        z = getattr(r, "levels", [None])[0]
        if z is None: return None, "unreadable"
        v = (int(z.bid_px), int(z.ask_px), int(z.bid_sz), int(z.ask_sz))
    return v, source
def invalid_side(px, size):
    return px in (UNDEF_PRICE, 0) or size in (UNDEF_ORDER_SIZE, 0) or px < 0 or size < 0
def withdrawal(r):
    # This audit consumes only BBOMsg snapshots.  Do NOT generalize MBP1
    # action='D' as a whole-quote withdrawal: a book-level delete can leave a
    # valid post-event top of book. BBO's undefined/zero side is invalidated in
    # update() below; a literal withdrawal flag is the only flag-based reset.
    return "WITHDRAW" in str(getattr(r,"flags","")).upper()
def update(r):
    vals, source = side_values(r)
    if vals is None: return {"valid":False,"reason":"unreadable","src":source}
    bp, ap, bs, ass = vals
    if withdrawal(r): return {"valid":False,"reason":"withdraw","src":source}
    if invalid_side(bp,bs) or invalid_side(ap,ass): return {"valid":False,"reason":"undefined_or_zero_side","src":source}
    if bp >= ap: return {"valid":False,"reason":"crossed_or_locked","src":source}
    return {"valid":True,"reason":"valid","src":source,"mid":(bp+ap)/2.0}

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = list(csv.DictReader((ROOT/"delivery/DOWNLOAD_MANIFEST.csv").open()))
    req = {}
    for name in ("core32_requests.csv", "extra_etf_requests.csv", "validation_requests.csv", "core16_requests.csv"):
        p=ROOT/name
        if p.exists(): req.update({r["request_id"]:r for r in csv.DictReader(p.open())})
    events = {r["event_id"]:r for r in csv.DictReader((ROOT/"earnings_events.csv").open())}
    maps=[]; scope_rows=[]
    for name in ("core32_event_request_map.csv","extra_event_request_map.csv"):
        for r in csv.DictReader((ROOT/name).open()):
            if events.get(r["event_id"],{}).get("analysis_access") == "DEVELOPMENT_PRE_FOCAL_ONLY": maps.append(r)
    by_cid={r["canonical_id"]:r for r in manifest}
    legs=[]
    for m in maps:
        base=req.get(m["request_id"])
        f=by_cid.get(cid(base)) if base else None
        status = "DECODED_PRE" if f and f["analysis_access"] == "DEVELOPMENT_PRE_FOCAL_ONLY" else ("SEALED_OR_ARCHIVE_NOT_DECODED" if f else "NO_SELECTED_FILE")
        scope_rows.append({"event_id":m["event_id"],"symbol":m["symbol"],"leg":m["leg"],"request_id":m["request_id"],"map_source":m.get("map_source","core32_or_extra"),"canonical_id":f["canonical_id"] if f else "","measurement_scope_status":status})
        # Never decode archive / POST data even if a map changes accidentally.
        if not f or f["analysis_access"] != "DEVELOPMENT_PRE_FOCAL_ONLY": continue
        lo,hi=local_ns(m["local_date"],m["required_start_local"]),local_ns(m["local_date"],m["required_end_local"])
        legs.append({**m,"lo":lo,"hi":hi,"canonical_id":f["canonical_id"],"path":f["path"]})
    write_csv("pre_event_map_scope.csv",scope_rows,list(scope_rows[0]))
    # Decode each PRE file only once. BBO timestamp denotes the endpoint of
    # [endpoint-1s, endpoint), so retain lo < endpoint <= hi.
    needs=defaultdict(list)
    for l in legs: needs[l["path"]].append((l["lo"],l["hi"]))
    updates=defaultdict(lambda: defaultdict(list)); api=Counter(); parsed=Counter()
    for path, windows in needs.items():
        for r in db.DBNStore.from_file(path):
            if type(r).__name__ != "BBOMsg": continue
            t=record_ns(r)
            if not any(lo < t <= hi for lo,hi in windows): continue
            u=update(r); api[u["src"]]+=1; parsed[u["reason"]]+=1
            updates[path][qkey(r)].append((t,u))
    # each selected raw symbol should be a single publisher/instrument stream;
    # do not merge streams even if a file contains more than one.
    stream_problem=[]
    for path, streams in updates.items():
        if len(streams) != 1: stream_problem.append({"path":path,"publisher_instrument_streams":len(streams)})
        for xs in streams.values(): xs.sort(key=lambda x:x[0])
    leg_samples={}; leg_rows=[]
    for l in legs:
        streams=updates[l["path"]]
        # A non-single stream is not silently pooled; all fixed clocks are marked invalid.
        xs=next(iter(streams.values())) if len(streams)==1 else []
        at={t:u for t,u in xs}; cur=None; cur_t=None; samples=[]
        start=((l["lo"]//NS)+1)*NS
        for t in range(start, l["hi"]+1, NS):
            if t in at: cur_t,cur=t,at[t]
            if cur is None: status="missing_before_first"
            elif not cur["valid"]: status="invalid_"+cur["reason"]
            else: status="valid_observed" if cur_t==t else "valid_carried"
            samples.append((t,status, None if cur is None else cur.get("mid"), None if cur_t is None else (t-cur_t)/NS))
        leg_samples[(l["event_id"],l["symbol"],l["leg"])]=samples
        c=Counter(x[1] for x in samples); ages=[x[3] for x in samples if x[3] is not None]
        for ses in ("PRE","RTH","AFTER"):
            ss=[x for x in samples if session(x[0])==ses]; cc=Counter(x[1] for x in ss)
            leg_rows.append({"event_id":l["event_id"],"symbol":l["symbol"],"leg":l["leg"],"session":ses,"endpoint_clock_start":iso(ss[0][0]) if ss else "","endpoint_clock_end":iso(ss[-1][0]) if ss else "","fixed_endpoints":len(ss),"two_sided_valid":sum(v for k,v in cc.items() if k.startswith("valid_")),"observed_valid":cc["valid_observed"],"carried_valid":cc["valid_carried"],"missing_before_first":cc["missing_before_first"],"invalid_withdraw":cc["invalid_withdraw"],"invalid_undefined_or_zero_side":cc["invalid_undefined_or_zero_side"],"invalid_crossed_or_locked":cc["invalid_crossed_or_locked"],"two_sided_valid_fraction":(sum(v for k,v in cc.items() if k.startswith("valid_"))/len(ss) if ss else None),"max_sample_age_seconds":max((x[3] for x in ss if x[3] is not None),default=None)})
    fields=list(leg_rows[0]) if leg_rows else []
    write_csv("pre_event_leg_quote_coverage.csv",leg_rows,fields)
    # Stock+SPY synchronicity: equal fixed endpoint clocks, with distinct states
    # and no inferred equality from two unavailable quote tuples.
    pair_rows=[]; noise=[]
    groups=defaultdict(dict)
    for l in legs: groups[(l["event_id"],l["leg"])][l["symbol"]]=l
    for (event,leg), g in sorted(groups.items()):
        # Extra ETFs are separate descriptive controls, never substitutes for
        # the event stock in the stock+SPY synchronization denominator.
        stocks=[events[event]["ticker"]] if events[event]["ticker"] in g else []
        for stock in stocks:
            if "SPY" not in g: continue
            a=leg_samples[(event,stock,leg)]; b=leg_samples[(event,"SPY",leg)]
            valid=[]; carried=[]; ages=[]; residual=[]; prev=None
            for aa,bb in zip(a,b):
                ok=aa[1].startswith("valid_") and bb[1].startswith("valid_")
                if ok:
                    valid.append(aa[0]); carried.append(aa[1]=="valid_carried" or bb[1]=="valid_carried"); ages.extend([aa[3],bb[3]])
                    # descriptive, fixed-clock two-asset change only; no event response.
                    # Stock-only fixed-clock midpoint change. This is not a
                    # beta-one stock-minus-SPY return and is not an outcome.
                    cur=math.log(aa[2])
                    if prev is not None: residual.append((cur-prev)*10000)
                    prev=cur
                else: prev=None
            for ses in ("PRE","RTH","AFTER"):
                idx=[i for i,x in enumerate(a) if session(x[0])==ses]
                vv=[i for i in idx if a[i][1].startswith("valid_") and b[i][1].startswith("valid_")]
                cc=[i for i in vv if a[i][1]=="valid_carried" or b[i][1]=="valid_carried"]
                aa=[z for i in vv for z in (a[i][3],b[i][3]) if z is not None]
                pair_rows.append({"event_id":event,"leg":leg,"session":ses,"stock_symbol":stock,"benchmark_symbol":"SPY","fixed_endpoints":len(idx),"two_sided_valid_synchronized":len(vv),"synchronized_valid_fraction":len(vv)/len(idx) if idx else None,"either_state_carried":len(cc),"max_sample_age_seconds":max(aa,default=None),"exact_release_clock_status":events[event]["exact_release_clock_status"]})
            if residual: noise.append({"event_id":event,"leg":leg,"stock_symbol":stock,"benchmark_symbol":"SPY","fixed_clock_valid_stock_return_pairs":len(residual),"rms_stock_midpoint_change_bps":math.sqrt(sum(x*x for x in residual)/len(residual)),"interpretation":"PRE-authorized, stock-only fixed-market-clock calibration; not beta-adjusted, not earnings response, and not certified P1 power"})
    write_csv("pre_stock_spy_synchronized_coverage.csv",pair_rows,list(pair_rows[0]) if pair_rows else [])
    write_csv("pre_descriptive_fixed_clock_noise.csv",noise,list(noise[0]) if noise else ["event_id"])
    overall=Counter();
    for r in leg_rows:
        for k in ("fixed_endpoints","two_sided_valid","observed_valid","carried_valid","missing_before_first","invalid_withdraw","invalid_undefined_or_zero_side","invalid_crossed_or_locked"): overall[k]+=int(r[k] or 0)
    scope_counts=Counter(r["measurement_scope_status"] for r in scope_rows)
    summary={"scope":"PRE event-map windows only; POST files not decoded","bbo_clock_rule":"BBO ts_recv is treated as endpoint of [end-1s,end); endpoints satisfy requested_start < endpoint <= requested_end","quote_api":{"tested_direct_fields":True,"levels0_fallback_available":True,"direct_records":api["direct"],"levels0_records":api["levels0"],"unreadable_records":api["unreadable"]},"raw_update_classification":dict(parsed),"event_map_scope_rows":len(scope_rows),"event_map_scope_statuses":dict(scope_counts),"event_leg_rows_decoded":len(legs),"overall":dict(overall),"stream_key_anomalies":stream_problem,"stock_spy_pair_session_rows":len(pair_rows),"stock_spy_distinct_event_leg_pairs":len(pair_rows)//3,"noise_rows":len(noise),"exact_release_clocks":"UNKNOWN / NOT_CERTIFIED_BY_THIS_ORDER; no response or power inference"}
    (OUT/"measurement_summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    hashes={p.name:sha(p) for p in sorted(OUT.glob("*.csv"))}|{"measurement_summary.json":sha(OUT/"measurement_summary.json"),"audit_pre_measurement.py":sha(__file__)}
    (OUT/"measurement_hashes.json").write_text(json.dumps(hashes,indent=2,sort_keys=True)+"\n")
    pair_by_leg=defaultdict(lambda:[0,0])
    for r in pair_rows:
        pair_by_leg[r["leg"]][0]+=int(r["two_sided_valid_synchronized"])
        pair_by_leg[r["leg"]][1]+=int(r["fixed_endpoints"])
    pair_text="; ".join(f"{k}: {a}/{b} ({a/b:.1%})" for k,(a,b) in sorted(pair_by_leg.items()))
    report=("# P1 PRE measurement audit\n\n"
      "Only event-map PRE windows were decoded. POST DBNs were not opened. Actual BBOMsg and MBP1Msg records expose direct level-0 fields and levels[0]; this audit uses direct fields with an explicit levels[0] fallback.\n\n"
      f"Fixed BBO endpoints: {overall['fixed_endpoints']}; two-sided valid: {overall['two_sided_valid']}; valid carried: {overall['carried_valid']}; missing before first observation: {overall['missing_before_first']}; invalid/withdrawn or undefined states are excluded. PRE/RTH/AFTER rows and age distributions are in `pre_event_leg_quote_coverage.csv`.\n\n"
      f"Event-stock + SPY synchronized fixed-clock coverage by leg: {pair_text}. The pair output has {len(pair_rows)//3} decodable event-stock/SPY legs (three session rows each), deliberately separate from extra-ETF rows. The map denominator is {len(scope_rows)} PRE legs; {scope_counts['SEALED_OR_ARCHIVE_NOT_DECODED']} sealed/archive legs are explicitly excluded rather than treated as zero.\n\n"
      "Existing 100% MBP/BBO matching is not a sufficient validity result: it lacks a two-sided-valid denominator and timestamps are not keyed by publisher/instrument. This audit does not equate unavailable states. Exact release clocks remain unknown, so these outputs support feed/measurement feasibility only—not earnings-response identification or certified P1 power.\n\n"
      "`pre_descriptive_fixed_clock_noise.csv` is PRE fixed-market-clock descriptive calibration only; it is not an event response.\n")
    (OUT/"MEASUREMENT_FINDINGS.md").write_text(report)
if __name__ == "__main__": main()
