#!/usr/bin/env python3
"""Build SCC-only ES quote features for 32 FOMC/control windows."""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np, pandas as pd, databento as db
from databento_dbn import MBP1Msg, UNDEF_ORDER_SIZE, UNDEF_PRICE
NS=1_000_000_000
TRADE=[f"{stem}_{window}" for window in ("0_100ms","100ms_1s","1s_5s") for stem in ("known_signed_flow","unknown_dollar_volume","no_trade")]
PREDICTORS=["ret_0_100ms","ret_100ms_1s","ret_1s_5s","spread_bp","bid_depth","ask_depth","mid_update_count_1s","mid_update_age_ms",*TRADE,"es_valid"]
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bbo(r):
 q=r.levels[0];b,a,bs,az=map(int,(q.bid_px,q.ask_px,q.bid_sz,q.ask_sz))
 if b==UNDEF_PRICE or a==UNDEF_PRICE or bs==UNDEF_ORDER_SIZE or az==UNDEF_ORDER_SIZE or min(b,a,bs,az)<=0 or a<b:return None
 return b/1e9,a/1e9,float(bs),float(az)
def decode(path):
 store=db.DBNStore.from_file(path); names={int(s["symbol"]):raw.upper().strip() for raw,spans in store.metadata.mappings.items() for s in spans};rows={}
 for order,r in enumerate(store):
  if isinstance(r,MBP1Msg) and int(r.instrument_id) in names:
   price=int(r.price)/1e9 if int(r.price)!=UNDEF_PRICE else math.nan
   rows.setdefault(names[int(r.instrument_id)],[]).append((int(r.ts_event),int(r.sequence),order,str(getattr(r.action,"value",r.action)),str(getattr(r.side,"value",r.side)),price,int(r.size),bbo(r)))
 out={}
 for sym,x in rows.items():
  x.sort(key=lambda z:(z[0],z[1],z[2]));state=None;t=[];m=[];sp=[];bd=[];ad=[];tt=[];td=[];tsign=[]
  for ts,_seq,_ord,act,side,price,size,q in x:
   if act=="T":tt.append(ts);td.append(price*size if math.isfinite(price) else math.nan);tsign.append(1.0 if side=="B" else (-1.0 if side=="A" else math.nan))
   state=None if act=="R" or q is None else q;t.append(ts)
   if state is None:m.append(math.nan);sp.append(math.nan);bd.append(math.nan);ad.append(math.nan)
   else:
    b,a,bs,az=state;mid=(a+b)/2;m.append(mid);sp.append((a-b)/mid*1e4);bd.append(bs);ad.append(az)
  out[sym]={"t":np.asarray(t,dtype=np.int64),"mid":np.asarray(m),"spread_bp":np.asarray(sp),"bid_depth":np.asarray(bd),"ask_depth":np.asarray(ad),"trade_t":np.asarray(tt,dtype=np.int64),"trade_value":np.asarray(td,float),"trade_sign":np.asarray(tsign,float)}
 return out
def at(d,t,k):
 ix=np.searchsorted(d["t"],t,side="right")-1;z=np.full(len(t),np.nan);good=ix>=0;z[good]=d[k][ix[good]];return z
def ret(d,a,b):
 x,y=at(d,a,"mid"),at(d,b,"mid");z=np.full(len(a),np.nan);good=np.isfinite(x)&np.isfinite(y)&(x>0)&(y>0);z[good]=1e4*(np.log(y[good])-np.log(x[good]));return z
def trades(d,a,b):
 left=np.searchsorted(d["trade_t"],a,side="right");right=np.searchsorted(d["trade_t"],b,side="right");signed=np.zeros(len(a));unknown=np.zeros(len(a));none=np.zeros(len(a));value,sign=d["trade_value"],d["trade_sign"]
 for i,(lo,hi) in enumerate(zip(left,right)):
  if lo==hi:none[i]=1.0;continue
  v,s=value[lo:hi],sign[lo:hi];good=np.isfinite(v);known=good&np.isfinite(s);signed[i]=float(np.sum(v[known]*s[known]));unknown[i]=float(np.sum(v[good&~np.isfinite(s)]))
 return signed,unknown,none
def values(d,g):
 t,m=d["t"],d["mid"];last=np.r_[np.flatnonzero(t[1:]!=t[:-1]),len(t)-1];t,m=t[last],m[last];changed=np.zeros(len(t),bool);changed[1:]=np.isfinite(m[1:])&np.isfinite(m[:-1])&(m[1:]!=m[:-1]);u=t[changed];l=np.searchsorted(u,g-NS,side="right");r=np.searchsorted(u,g,side="right");pos=np.searchsorted(u,g,side="right")-1;age=np.full(len(g),np.nan);good=pos>=0;age[good]=(g[good]-u[pos[good]])/1e6;mid=at(d,g,"mid")
 out={"ret_0_100ms":ret(d,g-100_000_000,g),"ret_100ms_1s":ret(d,g-NS,g-100_000_000),"ret_1s_5s":ret(d,g-5*NS,g-NS),"spread_bp":at(d,g,"spread_bp"),"bid_depth":at(d,g,"bid_depth"),"ask_depth":at(d,g,"ask_depth"),"mid_update_count_1s":(r-l).astype(float),"mid_update_age_ms":age,"es_valid":np.isfinite(mid).astype("int8")}
 for name,a,b in (("0_100ms",g-100_000_000,g),("100ms_1s",g-NS,g-100_000_000),("1s_5s",g-5*NS,g-NS)):
  signed,unknown,none=trades(d,a,b);out["known_signed_flow_"+name]=signed;out["unknown_dollar_volume_"+name]=unknown;out["no_trade_"+name]=none
 return out
def build(row):
 decoded=decode(row["path"])
 if len(decoded)!=1:raise RuntimeError(f"{row['path']}: expected one ES contract, got {sorted(decoded)}")
 actual,d=next(iter(decoded.items()));start=int(pd.Timestamp(row["start_utc"]).value);end=int(pd.Timestamp(row["end_utc"]).value);frames=[]
 for shift in (0,500):
  g=np.arange(start+60*NS+shift*1_000_000,end-60*NS,NS,dtype=np.int64);v=values(d,g);f=pd.DataFrame({"date":row["date"],"grid_shift_ms":shift,"second_index":np.arange(len(g)),"t_ns":g,"contract":row["actual_raw_symbol"],"dbn_metadata_symbol":actual,"requested_contract":row["symbols"]})
  for k,z in v.items():f[k]=z
  for k,z in values(d,g-NS).items():f["lag1_"+k]=z
  frames.append(f)
 return pd.concat(frames,ignore_index=True),actual
def main():
 a=argparse.ArgumentParser();a.add_argument("--download-receipt",required=True,type=Path);a.add_argument("--out",required=True,type=Path);a.add_argument("--receipt",required=True,type=Path);x=a.parse_args();d=json.loads(x.download_receipt.read_text());files=d.get("files",[])
 if d.get("status")!="COMPLETE_NATIVE_DBN_ON_SCC" or len(files)!=32:raise RuntimeError("32 completed ES FOMC windows required")
 frames=[];contracts=[]
 for r in files:
  f,actual=build(r);frames.append(f);contracts.append({"date":r["date"],"requested_continuous_contract":r["symbols"],"actual_raw_contract":r["actual_raw_symbol"],"dbn_metadata_symbol":actual,"raw_file":r["path"],"raw_sha256":r["sha256"]})
 table=pd.concat(frames,ignore_index=True);key=["date","grid_shift_ms","second_index"]
 if table.duplicated(key).any() or len(table)!=32*2*1500:raise RuntimeError("unexpected FOMC ES panel shape")
 x.out.parent.mkdir(parents=True,exist_ok=True);table.to_parquet(x.out,index=False);x.receipt.parent.mkdir(parents=True,exist_ok=True);x.receipt.write_text(json.dumps({"status":"COMPLETE_ES_FEATURES_ON_SCC","feature_path":str(x.out),"feature_sha256":digest(x.out),"rows":len(table),"dates":32,"grid_shifts_ms":[0,500],"keys":key,"primary_predictors":PREDICTORS,"clock_sensitivity_fields":["lag1_"+z for z in PREDICTORS],"ts_basis":"ts_event; source records ordered by ts_event, sequence, source order","trade_semantics":"Databento MBP-1 action=T; side B/A is buyer/seller aggressor. Flow unit is futures price times contracts, a scaled notional proxy without contract multiplier.","raw_or_row_data_exported_locally":False,"contracts":contracts},indent=2,sort_keys=True)+"\n")
if __name__=="__main__":main()
