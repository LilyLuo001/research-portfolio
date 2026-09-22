#!/usr/bin/env python3
"""Build SCC-only ES predictors on the frozen 0/500ms one-second grid.

All predictors use quote state at or before the grid centre based on ts_event.
`lag1_*` is the fixed clock sensitivity version: it exposes the value available
at t-1 second without moving the equity target. Native files and this parquet
must remain on SCC.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np
import pandas as pd
import databento as db
from databento_dbn import MBP1Msg, UNDEF_ORDER_SIZE, UNDEF_PRICE

NS=1_000_000_000
PREDICTORS=["ret_0_100ms","ret_100ms_1s","ret_1s_5s","spread_bp","bid_depth","ask_depth","mid_update_count_1s","mid_update_age_ms","es_valid"]

def digest(p: Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()
def bbo(record):
    q=record.levels[0]; b,a,bs,az=map(int,(q.bid_px,q.ask_px,q.bid_sz,q.ask_sz))
    if b==UNDEF_PRICE or a==UNDEF_PRICE or bs==UNDEF_ORDER_SIZE or az==UNDEF_ORDER_SIZE or min(b,a,bs,az)<=0 or a<b:return None
    return b/1e9,a/1e9,float(bs),float(az)
def raw_map(store): return {int(s["symbol"]): raw.upper().strip() for raw,spans in store.metadata.mappings.items() for s in spans}
def decode(path):
    store=db.DBNStore.from_file(path); names=raw_map(store); rows={}
    for order,r in enumerate(store):
        if not isinstance(r,MBP1Msg):continue
        sym=names.get(int(r.instrument_id));
        if sym is None:continue
        rows.setdefault(sym,[]).append((int(r.ts_event),int(r.sequence),order,str(getattr(r.action,"value",r.action)),bbo(r)))
    out={}
    for sym,x in rows.items():
        x.sort(key=lambda v:(v[0],v[1],v[2])); state=None; ts=[]; mid=[]; spr=[]; bd=[]; ad=[]
        for t,_seq,_ord,act,q in x:
            state=None if act=="R" or q is None else q; ts.append(t)
            if state is None: mid.append(math.nan);spr.append(math.nan);bd.append(math.nan);ad.append(math.nan)
            else:
                b,a,bs,az=state;m=(a+b)/2;mid.append(m);spr.append((a-b)/m*1e4);bd.append(bs);ad.append(az)
        out[sym]={"t":np.asarray(ts,dtype=np.int64),"mid":np.asarray(mid),"spread_bp":np.asarray(spr),"bid_depth":np.asarray(bd),"ask_depth":np.asarray(ad)}
    return out
def at(d,t,field):
    ix=np.searchsorted(d["t"],t,side="right")-1; ans=np.full(len(t),np.nan); good=ix>=0;ans[good]=d[field][ix[good]];return ans
def ret(d,start,end):
    a,b=at(d,start,"mid"),at(d,end,"mid");ans=np.full(len(start),np.nan);good=np.isfinite(a)&np.isfinite(b)&(a>0)&(b>0);ans[good]=1e4*(np.log(b[good])-np.log(a[good]));return ans
def update_times(d):
    t,m=d["t"],d["mid"]
    last=np.r_[np.flatnonzero(t[1:]!=t[:-1]),len(t)-1];t,m=t[last],m[last];changed=np.zeros(len(t),bool);changed[1:]=np.isfinite(m[1:])&np.isfinite(m[:-1])&(m[1:]!=m[:-1]);return t[changed]
def values(d,grid):
    u=update_times(d); l=np.searchsorted(u,grid-NS,side="right");r=np.searchsorted(u,grid,side="right");pos=np.searchsorted(u,grid,side="right")-1;age=np.full(len(grid),np.nan);good=pos>=0;age[good]=(grid[good]-u[pos[good]])/1e6
    mid=at(d,grid,"mid")
    return {"ret_0_100ms":ret(d,grid-100_000_000,grid),"ret_100ms_1s":ret(d,grid-NS,grid-100_000_000),"ret_1s_5s":ret(d,grid-5*NS,grid-NS),"spread_bp":at(d,grid,"spread_bp"),"bid_depth":at(d,grid,"bid_depth"),"ask_depth":at(d,grid,"ask_depth"),"mid_update_count_1s":(r-l).astype(float),"mid_update_age_ms":age,"es_valid":np.isfinite(mid).astype("int8")}
def build(row, file):
    decoded=decode(file); expected=row["actual_raw_symbol"].upper();
    # Require a single decoded symbol. Keep actual mapping for audit rather than silently choosing.
    if len(decoded)!=1: raise RuntimeError(f"{file}: expected one decoded contract, got {sorted(decoded)}")
    actual,d=next(iter(decoded.items())); start=int(pd.Timestamp(row["start_utc"]).value);end=int(pd.Timestamp(row["end_utc"]).value);frames=[]
    for shift in (0,500):
        grid=np.arange(start+60*NS+shift*1_000_000,end-60*NS,NS,dtype=np.int64);v=values(d,grid);frame=pd.DataFrame({"date":row["date"],"grid_shift_ms":shift,"second_index":np.arange(len(grid),dtype=int),"t_ns":grid,"contract":expected,"dbn_metadata_symbol":actual,"requested_contract":row["symbol"]})
        for k,x in v.items():frame[k]=x
        # Values at t-1s remain on the same key row, supporting a fixed early-information merge.
        lag=values(d,grid-NS)
        for k,x in lag.items():frame["lag1_"+k]=x
        frames.append(frame)
    return pd.concat(frames,ignore_index=True),actual
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--download-receipt",required=True,type=Path);ap.add_argument("--out",required=True,type=Path);ap.add_argument("--receipt",required=True,type=Path);a=ap.parse_args()
    receipt=json.loads(a.download_receipt.read_text())
    if receipt.get("status")!="COMPLETE_NATIVE_DBN_ON_SCC":raise RuntimeError("complete ES download receipt required")
    files=receipt["files"];rows=[];contract_rows=[]
    for item in files:
        r=item; # receipt records full request fields in this workflow's quote/receipt lineage
        # Recover request details from matching quoted request list when present.
        if "date" not in r: raise RuntimeError("download receipt must preserve request date/symbol fields")
        f,actual=build(r,Path(r["path"]));rows.append(f);contract_rows.append({"date":r["date"],"requested_continuous_contract":r["symbol"],"actual_raw_contract":r["actual_raw_symbol"],"dbn_metadata_symbol":actual,"raw_file":r["path"],"raw_sha256":r["sha256"]})
    table=pd.concat(rows,ignore_index=True);key=["date","grid_shift_ms","second_index"]
    if table.duplicated(key).any() or len(table)!=24*2*1800:raise RuntimeError("unexpected nonunique/fixed panel shape")
    a.out.parent.mkdir(parents=True,exist_ok=True);table.to_parquet(a.out,index=False)
    a.receipt.parent.mkdir(parents=True,exist_ok=True);a.receipt.write_text(json.dumps({"status":"COMPLETE_ES_FEATURES_ON_SCC","feature_path":str(a.out),"feature_sha256":digest(a.out),"rows":len(table),"dates":int(table.date.nunique()),"grid_shifts_ms":[0,500],"keys":key,"primary_predictors":PREDICTORS,"clock_sensitivity_fields":["lag1_"+x for x in PREDICTORS],"ts_basis":"ts_event; source records ordered by ts_event, sequence, source order","raw_or_row_data_exported_locally":False,"contracts":contract_rows},indent=2,sort_keys=True)+"\n")
if __name__=="__main__":main()
