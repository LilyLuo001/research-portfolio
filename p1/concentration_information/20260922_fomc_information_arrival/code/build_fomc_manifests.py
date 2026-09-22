#!/usr/bin/env python3
"""Build immutable FOMC, calendar-control, and 96-request manifests.

The only calendar decision here is the previous fifth NYSE full trading
session.  The public artifacts contain no market data or credentials.
"""
from __future__ import annotations
import argparse, csv, json
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York"); UTC = ZoneInfo("UTC")
FOMC = (
 ("2023-02-01", False), ("2023-03-22", True), ("2023-05-03", False),
 ("2023-06-14", True), ("2023-07-26", False), ("2023-09-20", True),
 ("2023-11-01", False), ("2023-12-13", True), ("2024-01-31", False),
 ("2024-03-20", True), ("2024-05-01", False), ("2024-06-12", True),
 ("2024-07-31", False), ("2024-09-18", True), ("2024-11-07", False),
 ("2024-12-18", True),
)
# NYSE full-day closures only.  Early closes remain eligible trading sessions.
CLOSED = {
 "2023-01-02", "2023-01-16", "2023-02-20", "2023-04-07", "2023-05-29",
 "2023-06-19", "2023-07-04", "2023-09-04", "2023-11-23", "2023-12-25",
 "2024-01-01", "2024-01-15", "2024-02-19", "2024-03-29", "2024-05-27",
 "2024-06-19", "2024-07-04", "2024-09-02", "2024-11-28", "2024-12-25",
}
SYMBOLS = ["SPY","GOOG","LLY","V","AAPL","ABBV","KO","PG","MRK","BDX","CVS","DLTR","TJX","CMI","MMC","MNST","KHC","KEY","RSG","WST","EBAY","NWSA","NDSN","XYL"]
def iso_utc(day: str, clock: str) -> str:
    return datetime.combine(date.fromisoformat(day), time.fromisoformat(clock), NY).astimezone(UTC).isoformat().replace("+00:00", "Z")
def is_session(d: date) -> bool: return d.weekday() < 5 and d.isoformat() not in CLOSED
def control(day: str, all_events: set[str]) -> tuple[str, int]:
    d=date.fromisoformat(day); n=0
    while n < 5:
        d -= timedelta(days=1)
        if is_session(d) and d.isoformat() not in all_events: n += 1
    return d.isoformat(), n
def event_url(day: str) -> str:
    return "https://www.federalreserve.gov/newsevents/pressreleases/monetary" + day.replace("-", "") + "a.htm"
def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument("--out", type=Path, required=True); a=p.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    all_events={x[0] for x in FOMC}; events=[]; controls=[]
    for i,(day,sep) in enumerate(FOMC,1):
        c,ordinal=control(day,all_events)
        events.append({"event_id":f"FOMC_{day.replace('-','')}","event_date":day,"event_number":i,"statement_url":event_url(day),"calendar_url":"https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm","scheduled_time_et":"14:00:00","timezone":"America/New_York","scheduled_time_utc":iso_utc(day,"14:00:00"),"utc_offset":datetime.combine(date.fromisoformat(day),time(14),NY).strftime("%z"),"sep_simultaneous_material":sep,"time_evidence_level":"OFFICIAL_STATEMENT_PAGE_RELEASED_TIME","time_evidence_note":"Official scheduled/released statement clock; not an assertion of identical terminal receipt time."})
        controls.append({"event_id":events[-1]["event_id"],"event_date":day,"control_date":c,"control_rank_previous_nyse_session":ordinal,"same_clock_et":"14:00:00","control_time_utc":iso_utc(c,"14:00:00"),"calendar_rule":"previous fifth NYSE full trading session; skip a regular FOMC statement date; no price, volatility, news, or data-support selection","known_same_clock_other_news":"NOT_SCREENED_CALENDAR_CONTROL_NOT_NO_NEWS_CLAIM"})
    with (a.out/"EVENT_MANIFEST.csv").open("w",newline="") as f: w=csv.DictWriter(f,fieldnames=list(events[0])); w.writeheader();w.writerows(events)
    with (a.out/"CONTROL_MANIFEST.csv").open("w",newline="") as f: w=csv.DictWriter(f,fieldnames=list(controls[0]));w.writeheader();w.writerows(controls)
    unique=[]; analysis=[]
    for e,c in zip(events,controls):
        number = int(e["event_number"])
        split = "TEST" if e["event_date"].startswith("2024") else (
            "TRAIN" if number <= 4 else ("VALID" if number <= 6 else "HISTORY"))
        unique += [(e["event_date"],"EVENT",e["event_id"]),(c["control_date"],"CONTROL",e["event_id"])]
        analysis += [
            {"date": e["event_date"], "event_id": e["event_id"], "sample_kind": "EVENT", "split": split,
             "event_date": e["event_date"], "control_date": c["control_date"]},
            {"date": c["control_date"], "event_id": e["event_id"], "sample_kind": "CONTROL", "split": split,
             "event_date": e["event_date"], "control_date": c["control_date"]},
        ]
    # Control dates are intentionally retained once per paired event.  This instance has 32 unique dates.
    if len({x[0] for x in unique}) != 32: raise RuntimeError("expected 32 unique FOMC/control dates")
    with (a.out/"ANALYSIS_DATES.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(analysis[0]));w.writeheader();w.writerows(analysis)
    req=[]
    for day,kind,pair in unique:
        for ds in ("XNAS.ITCH","ARCX.PILLAR"):
            req.append({"request_id":f"{ds.replace('.','_')}_{day}","date":day,"day_type":kind,"paired_event_id":pair,"dataset":ds,"schema":"mbp-1","stype_in":"raw_symbol","symbols":";".join(SYMBOLS),"symbol_count":len(SYMBOLS),"start_utc":iso_utc(day,"13:44:00"),"end_utc":iso_utc(day,"14:11:00"),"window_et":"13:44:00-14:11:00","reuse_status":"PENDING_EXACT_SCC_CHECK","raw_path":"PENDING"})
        req.append({"request_id":f"GLBX_MDP3_{day}_ESV0_MBP1","date":day,"day_type":kind,"paired_event_id":pair,"dataset":"GLBX.MDP3","schema":"mbp-1","stype_in":"continuous","symbols":"ES.v.0","symbol_count":1,"start_utc":iso_utc(day,"13:44:00"),"end_utc":iso_utc(day,"14:11:00"),"window_et":"13:44:00-14:11:00","reuse_status":"PENDING_EXACT_SCC_CHECK","raw_path":"PENDING"})
    if len(req)!=96: raise RuntimeError("expected 64 equity + 32 shared ES requests")
    with (a.out/"REQUEST_MANIFEST.csv").open("w",newline="") as f: w=csv.DictWriter(f,fieldnames=list(req[0]));w.writeheader();w.writerows(req)
    (a.out/"REQUEST_MANIFEST.json").write_text(json.dumps({"status":"PREPARED_UNQUOTED","request_count":96,"equity_request_count":64,"shared_futures_request_count":32,"unique_dates":32,"symbols":SYMBOLS,"source_window":"13:44-14:11 America/New_York native mbp-1; analysis 13:50-14:10","requests":req},indent=2,sort_keys=True)+"\n")
    (a.out/"OFFICIAL_CLOCK_SOURCES.md").write_text("# Official FOMC statement clock sources\n\nEach event row links the Federal Reserve statement page and records its 14:00 America/New_York release/scheduled clock. This is an official event-time anchor, not a microsecond terminal-receipt assertion. The calendar-control rule and complete event records are in the two CSV manifests.\n")
if __name__ == "__main__": main()
