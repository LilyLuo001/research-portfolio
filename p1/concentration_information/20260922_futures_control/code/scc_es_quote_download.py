#!/usr/bin/env python3
"""SCC-only quote/download of continuous ES; never prints or writes secrets."""
from __future__ import annotations
import argparse,csv,hashlib,json,os,re
from datetime import date,timedelta
from decimal import Decimal
from pathlib import Path
import databento as db
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,sort_keys=True)+"\n")
def client():
    k=os.getenv("DATABENTO_API_KEY")
    if not k:raise RuntimeError("DATABENTO_API_KEY absent from SCC environment")
    return db.Historical(k)
def rows(p):
    v=json.loads(p.read_text())["requests"]
    if len(v)!=24 or any(r["dataset"]!="GLBX.MDP3" or r["schema"]!="mbp-1" or r["stype_in"]!="continuous" or r["symbol"]!="ES.v.0" for r in v):raise RuntimeError("fixed ES.v.0 continuous 24-row manifest required")
    return v
def raw(resp,requested):
    todo=[resp.get("result",{}).get(requested,[]) if isinstance(resp,dict) else []]
    while todo:
        x=todo.pop()
        if isinstance(x,str) and re.fullmatch(r"ES[HMUZ][0-9]{1,2}",x.upper()):return x.upper()
        if isinstance(x,dict):todo.extend(x.values())
        if isinstance(x,(list,tuple)):todo.extend(x)
    raise RuntimeError("continuous symbol did not resolve to an ES quarterly raw symbol")
def instrument_id(resp,requested):
    """The symbology span's `s` is the resolved instrument-id target."""
    todo=[resp.get("result",{}).get(requested,[]) if isinstance(resp,dict) else []]
    while todo:
        x=todo.pop()
        if isinstance(x,dict):
            if "s" in x and str(x["s"]).isdigit():return str(x["s"])
            todo.extend(x.values())
        if isinstance(x,(list,tuple)):todo.extend(x)
    raise RuntimeError("continuous symbol did not resolve to an instrument id")
def resolve_two_step(cl,r):
    # Databento rejects continuous -> raw_symbol directly. Resolve continuous
    # -> instrument_id first, then that stable id -> raw_symbol on the same date.
    end=(date.fromisoformat(r["date"])+timedelta(days=1)).isoformat()
    first=cl.symbology.resolve(dataset=r["dataset"],symbols=[r["symbol"]],stype_in=r["stype_in"],stype_out="instrument_id",start_date=r["date"],end_date=end)
    iid=instrument_id(first,r["symbol"])
    second=cl.symbology.resolve(dataset=r["dataset"],symbols=[iid],stype_in="instrument_id",stype_out="raw_symbol",start_date=r["date"],end_date=end)
    return iid,raw(second,iid)
def quote(manifest,out):
    cl=client();q=[]
    for r in rows(manifest):
        iid,actual=resolve_two_step(cl,r)
        spec={"dataset":r["dataset"],"schema":r["schema"],"symbols":[r["symbol"]],"stype_in":r["stype_in"],"start":r["start_utc"],"end":r["end_utc"]}
        q.append({**r,"instrument_id":iid,"actual_raw_symbol":actual,"quoted_cost_usd":str(Decimal(str(cl.metadata.get_cost(**spec)))),"estimated_record_count":int(cl.metadata.get_record_count(**spec))})
    put(out,{"status":"QUOTED_NO_DOWNLOAD","manifest_sha256":sha(manifest),"sdk_version":getattr(db,"__version__","NOT_OBSERVED"),"total_quoted_cost_usd":str(sum((Decimal(x["quoted_cost_usd"]) for x in q),Decimal("0"))),"requests":q})
def mapfile(qp,cp):
    q=json.loads(qp.read_text())["requests"];cp.parent.mkdir(parents=True,exist_ok=True);fields=["date","continuous_symbol","actual_raw_symbol","instrument_id","rule_id","rule","selection_uses_prices_or_prediction_results"]
    with cp.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({"date":r["date"],"continuous_symbol":r["symbol"],"actual_raw_symbol":r["actual_raw_symbol"],"instrument_id":r["instrument_id"],"rule_id":"DATABENTO_CONTINUOUS_PREVIOUS_DAY_VOLUME_FRONT","rule":"Databento ES.v.0 ranks expirations by previous-day trading volume; actual raw symbol resolved per date before download.","selection_uses_prices_or_prediction_results":False} for r in q)
def download(manifest,qp,outdir):
    q=json.loads(qp.read_text())
    if q.get("manifest_sha256")!=sha(manifest) or len(q.get("requests",[]))!=24:raise RuntimeError("matching quote required")
    cl=client();outdir.mkdir(parents=True,exist_ok=True);done=[]
    for r in q["requests"]:
        target=outdir/(r["request_id"]+".dbn.zst")
        if target.exists():raise RuntimeError(f"refusing overwrite/recharge risk: {target}")
        state={k:r[k] for k in ("request_id","date","split","dataset","schema","symbol","stype_in","start_utc","end_utc","instrument_id","actual_raw_symbol")}|{"path":str(target),"status":"SUBMISSION_STARTED_NO_RETRY"};done.append(state);put(outdir/"DOWNLOAD_RECEIPT.json",{"status":"IN_PROGRESS","manifest_sha256":sha(manifest),"quote_sha256":sha(qp),"files":done})
        cl.timeseries.get_range(dataset=r["dataset"],schema=r["schema"],symbols=[r["symbol"]],stype_in=r["stype_in"],stype_out="instrument_id",start=r["start_utc"],end=r["end_utc"],path=target);state.update(status="DOWNLOADED_NATIVE_DBN_ON_SCC",bytes=target.stat().st_size,sha256=sha(target))
    put(outdir/"DOWNLOAD_RECEIPT.json",{"status":"COMPLETE_NATIVE_DBN_ON_SCC","manifest_sha256":sha(manifest),"quote_sha256":sha(qp),"quoted_total_usd":q["total_quoted_cost_usd"],"files":done})
def main():
    a=argparse.ArgumentParser();a.add_argument("mode",choices=("quote","download"));a.add_argument("--manifest",required=True,type=Path);a.add_argument("--out",required=True,type=Path);a.add_argument("--quote-receipt",type=Path);a.add_argument("--out-dir",type=Path);a.add_argument("--contract-map",type=Path);x=a.parse_args()
    if x.mode=="quote":quote(x.manifest,x.out); mapfile(x.out,x.contract_map) if x.contract_map else None
    else:
        if not x.quote_receipt or not x.out_dir:raise RuntimeError("download needs --quote-receipt and --out-dir")
        download(x.manifest,x.quote_receipt,x.out_dir)
if __name__=="__main__":main()
