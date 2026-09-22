#!/usr/bin/env python3
"""SCC-only quote/download for the fixed FOMC 96-request manifest.

Never prints, accepts, serializes, hashes, or writes a Databento credential.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
import databento as db
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x): Path(p).parent.mkdir(parents=True,exist_ok=True); Path(p).write_text(json.dumps(x,indent=2,sort_keys=True)+"\n")
def client():
    key=os.getenv("DATABENTO_API_KEY")
    if not key: raise RuntimeError("DATABENTO_API_KEY absent from authenticated SCC environment")
    return db.Historical(key)
def load(p):
    x=json.loads(Path(p).read_text()); rows=x["requests"]; eq=[r for r in rows if r["dataset"] in {"XNAS.ITCH","ARCX.PILLAR"}]; es=[r for r in rows if r["dataset"]=="GLBX.MDP3"]
    if len(rows)!=96 or len(eq)!=64 or len(es)!=32 or len({r["date"] for r in rows})!=32: raise RuntimeError("requires exact 96-request FOMC manifest")
    return rows
def resolve_es(c,r):
    d=date.fromisoformat(r["date"]); end=str(d+timedelta(days=1)); a=c.symbology.resolve(dataset="GLBX.MDP3",symbols=["ES.v.0"],stype_in="continuous",stype_out="instrument_id",start_date=str(d),end_date=end); found=re.findall(r'"s"\s*:\s*"?(\d+)"?',json.dumps(a));
    if not found: raise RuntimeError(f"{r['date']}: ES.v.0 unresolved")
    iid=found[0]; b=c.symbology.resolve(dataset="GLBX.MDP3",symbols=[iid],stype_in="instrument_id",stype_out="raw_symbol",start_date=str(d),end_date=end); raw=re.findall(r'ES[HMUZ][0-9]{1,2}',json.dumps(b).upper())
    if not raw: raise RuntimeError(f"{r['date']}: raw ES unresolved")
    return iid,raw[0]
def resolve_equity(c,r):
    symbols=r["symbols"].split(";"); d=date.fromisoformat(r["date"]); a=c.symbology.resolve(dataset=r["dataset"],symbols=symbols,stype_in="raw_symbol",stype_out="instrument_id",start_date=str(d),end_date=str(d+timedelta(days=1))); result=a.get("result",{}); good=[s for s in symbols if result.get(s)]; bad=[s for s in symbols if s not in good]
    if "SPY" not in good: raise RuntimeError(f"{r['request_id']}: SPY unresolved")
    return good,bad
def quote(manifest,out):
    c=client(); q=[]
    for r in load(manifest):
        x=dict(r)
        if r["dataset"]=="GLBX.MDP3": iid,raw=resolve_es(c,r); syms=["ES.v.0"]; x.update(instrument_id=iid,actual_raw_symbol=raw,unresolved_symbols=[])
        else: syms,bad=resolve_equity(c,r); x.update(unresolved_symbols=bad)
        spec={"dataset":r["dataset"],"schema":"mbp-1","symbols":syms,"stype_in":r["stype_in"],"start":r["start_utc"],"end":r["end_utc"]}; x.update(resolved_symbols=syms,quoted_cost_usd=str(Decimal(str(c.metadata.get_cost(**spec))),),estimated_record_count=int(c.metadata.get_record_count(**spec))); q.append(x)
    put(out,{"status":"QUOTED_NO_DOWNLOAD","manifest_sha256":digest(manifest),"request_count":len(q),"total_quoted_cost_usd":str(sum((Decimal(x["quoted_cost_usd"]) for x in q),Decimal(0))),"requests":q})
def download(manifest,quote_path,raw_root):
    q=json.loads(Path(quote_path).read_text());
    if q.get("status")!="QUOTED_NO_DOWNLOAD" or q.get("manifest_sha256")!=digest(manifest) or len(q.get("requests",[]))!=96: raise RuntimeError("matching 96-row quote receipt required")
    c=client(); raw_root=Path(raw_root); done=[]
    for r in q["requests"]:
        target=raw_root/(r["request_id"]+".dbn.zst"); x=dict(r); x["path"]=str(target)
        if target.exists() and target.stat().st_size>0: x.update(status="REUSED_EXISTING_NATIVE_DBN_ON_SCC",bytes=target.stat().st_size,sha256=digest(target));done.append(x);continue
        if target.exists(): raise RuntimeError(f"refusing overwrite/recharge risk: {target}")
        raw_root.mkdir(parents=True,exist_ok=True);x["status"]="SUBMISSION_STARTED_NO_RETRY";done.append(x);put(raw_root/"DOWNLOAD_RECEIPT.json",{"status":"IN_PROGRESS","manifest_sha256":digest(manifest),"files":done})
        c.timeseries.get_range(dataset=r["dataset"],schema="mbp-1",symbols=r["resolved_symbols"],stype_in=r["stype_in"],stype_out="instrument_id",start=r["start_utc"],end=r["end_utc"],path=target);x.update(status="DOWNLOADED_NATIVE_DBN_ON_SCC",bytes=target.stat().st_size,sha256=digest(target))
    put(raw_root/"DOWNLOAD_RECEIPT.json",{"status":"COMPLETE_NATIVE_DBN_ON_SCC","manifest_sha256":digest(manifest),"quote_sha256":digest(quote_path),"quoted_total_usd":q["total_quoted_cost_usd"],"files":done})
def main():
    a=argparse.ArgumentParser();a.add_argument("mode",choices=("quote","download"));a.add_argument("--manifest",required=True);a.add_argument("--out");a.add_argument("--quote-receipt");a.add_argument("--raw-root");x=a.parse_args()
    if x.mode=="quote":
        if not x.out: raise RuntimeError("quote needs --out")
        quote(x.manifest,x.out)
    else:
        if not x.quote_receipt or not x.raw_root: raise RuntimeError("download needs quote receipt and raw root")
        download(x.manifest,x.quote_receipt,x.raw_root)
if __name__=="__main__": main()
