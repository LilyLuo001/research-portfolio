#!/usr/bin/env python3
"""Build fixed ES.v.0 previous-day-volume-front requests for the 24 dates."""
from __future__ import annotations
import argparse, json
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
NY=ZoneInfo("America/New_York"); UTC=ZoneInfo("UTC")
def utc(day:date,hour:int,minute:int)->str:
    return datetime.combine(day,time(hour,minute),tzinfo=NY).astimezone(UTC).isoformat().replace("+00:00","Z")
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--dates",required=True,type=Path);ap.add_argument("--out",required=True,type=Path);ap.add_argument("--contract-map",required=True,type=Path);a=ap.parse_args()
    dates=pd.read_csv(a.dates)
    if len(dates)!=24 or dates.date.nunique()!=24 or not {"date","split"}<=set(dates):raise RuntimeError("immutable 24-date input required")
    rows=[]
    for x in dates.itertuples(index=False):
        d=date.fromisoformat(x.date);rows.append({"request_id":f"GLBX_MDP3_{d}_ESV0_MBP1","date":str(d),"split":x.split,"dataset":"GLBX.MDP3","schema":"mbp-1","symbol":"ES.v.0","stype_in":"continuous","stype_out":"instrument_id","start_utc":utc(d,9,59),"end_utc":utc(d,10,31),"core_start_et":"10:00:00","core_end_et_exclusive":"10:30:00","request_copy":"ONE_SHARED_FUTURES_REQUEST_FOR_BOTH_EQUITY_VENUES"})
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps({"manifest_version":2,"dataset":"GLBX.MDP3","schema":"mbp-1","request_count":24,"unique_future_windows":24,"not_duplicated_for_equity_venues":True,"contract_rule":"Databento ES.v.0 continuous contract: rank eligible expirations by previous-day trading volume; resolve actual raw symbol separately for each date before download.","date_selection":"Inherited deterministic 5th/15th NYSE trading-day sample; not selected for earnings, macro events, futures activity, prices, or outcomes.","timezone_rule":"09:59-10:31 America/New_York converted per date with IANA zoneinfo","requests":rows},indent=2,sort_keys=True)+"\n")
    pd.DataFrame({"date":dates.date,"continuous_symbol":"ES.v.0","actual_raw_symbol":"PENDING_API_RESOLUTION","instrument_id":"PENDING_API_RESOLUTION","rule_id":"DATABENTO_CONTINUOUS_PREVIOUS_DAY_VOLUME_FRONT","rule":"Databento ES.v.0 ranks expirations by previous-day trading volume; fixed before data access.","selection_uses_prices_or_prediction_results":False}).to_csv(a.contract_map,index=False)
if __name__=="__main__":main()
