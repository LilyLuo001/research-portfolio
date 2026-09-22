#!/usr/bin/env python3
"""Compute SCC-resident, venue-local midpoint-update response summaries.

Only aggregate rows leave SCC.  A source event is a change in a valid BBO
midpoint; the target baseline is its final valid quote strictly before the
source timestamp.  Equal-timestamp target changes are counted separately and
not assigned an order.  The non-overlap sample is selected prospectively: a
source event is retained only when it is at least five seconds after the
previous retained event of that source security.
"""
from __future__ import annotations

import argparse, json, math
from pathlib import Path
import numpy as np
import pandas as pd
import databento as db
from databento_dbn import MBP1Msg, UNDEF_ORDER_SIZE, UNDEF_PRICE

NS=1_000_000_000
H=[100_000_000,500_000_000,NS,2*NS,5*NS]

def bbo(r):
    x=r.levels[0]; b,a,bs,az=map(int,(x.bid_px,x.ask_px,x.bid_sz,x.ask_sz))
    if b==UNDEF_PRICE or a==UNDEF_PRICE or bs==UNDEF_ORDER_SIZE or az==UNDEF_ORDER_SIZE: return None
    if min(b,a,bs,az)<=0 or a<b: return None
    return (b+a)/2e9

def decode(path):
    s=db.DBNStore.from_file(path)
    mp={int(z['symbol']): k.upper().strip() for k,v in s.metadata.mappings.items() for z in v}
    out={}
    state={}
    for order,r in enumerate(s):
        if not isinstance(r,MBP1Msg): continue
        sym=mp.get(int(r.instrument_id))
        if sym is None: continue
        t=int(r.ts_event); act=str(getattr(r.action,'value',r.action))
        v=None if act=='R' else bbo(r)
        old=state.get(sym)
        state[sym]=v
        # Retain invalid endpoints too.  A reset/invalid BBO starts a new
        # validity epoch; state_at must not carry a prior valid midpoint across it.
        q=out.setdefault(sym,[[],[]]); q[0].append(t); q[1].append(np.nan if v is None else v)
    ans={}
    for sym,(t,m) in out.items():
        t=np.asarray(t,dtype=np.int64); m=np.asarray(m,float)
        # Same timestamp messages may generate intermediate states.  Last state is
        # the actionable state at that timestamp; only compare timestamp endpoints.
        last=np.r_[np.flatnonzero(t[1:]!=t[:-1]),len(t)-1]
        tt=t[last]; mm=m[last]
        cc=np.zeros(len(mm),dtype=bool)
        cc[1:]=np.isfinite(mm[1:]) & np.isfinite(mm[:-1]) & (mm[1:]!=mm[:-1])
        ans[sym]=(tt,mm,cc)
    return ans

def state_before(t,m,x):
    i=np.searchsorted(t,x,side='left')-1
    return (m[i] if i>=0 else np.nan),i
def state_at(t,m,x):
    i=np.searchsorted(t,x,side='right')-1
    return (m[i] if i>=0 else np.nan),i

def process_pair(src,tgt,date,venue,direction,core_start,core_end,rows):
    st,sm,sc=src; tt,tm,tc=tgt
    # The downloaded 60-second buffers are endpoint support only.  Source
    # events follow exactly the prediction-center interval [10:00, 10:30).
    eidx=np.flatnonzero(sc & (st>=core_start) & (st<core_end))
    keep=[]; last=-10**30
    for i in eidx:
        if st[i]-last>=5*NS: keep.append(i); last=st[i]
    for sample,indices in [('all',eidx),('nonoverlap',np.asarray(keep,dtype=int))]:
        x=st[indices]; sign=np.sign(sm[indices]-sm[indices-1])
        # Prefix counts make equal-timestamp and post-trigger update tests O(n)
        # for the full event vector, rather than a Python loop per event.
        prefix=np.r_[0,np.cumsum(tc.astype(np.int64))]
        lo=np.searchsorted(tt,x,side='left'); hi=np.searchsorted(tt,x,side='right')
        uncertain=(prefix[hi]-prefix[lo])>0
        for ordered, label in [(False,sample),(True,sample+'_simultaneous_excluded')]:
         for h in H:
            selected=~uncertain if ordered else np.ones(len(x),dtype=bool)
            bpos=np.searchsorted(tt,x,side='left')-1
            apos=np.searchsorted(tt,x+h,side='right')-1
            ppos=np.searchsorted(tt,x-h,side='right')-1
            base=np.where(bpos>=0,tm[np.maximum(bpos,0)],np.nan)
            aft=np.where(apos>=0,tm[np.maximum(apos,0)],np.nan)
            bef=np.where(ppos>=0,tm[np.maximum(ppos,0)],np.nan)
            valid=selected & np.isfinite(base) & np.isfinite(aft) & (base>0) & (aft>0)
            value=np.full(len(x),np.nan); value[valid]=sign[valid]*1e4*np.log(aft[valid]/base[valid])
            u0=np.searchsorted(tt,x,side='right'); u1=np.searchsorted(tt,x+h,side='right')
            target_updated=(prefix[u1]-prefix[u0])>0
            prevalid=selected & np.isfinite(base) & np.isfinite(bef) & (base>0) & (bef>0)
            # Standard forward pre-event path: midpoint moves from t-h to the
            # strictly pre-trigger baseline, aligned to the source-event sign.
            prevalue=np.full(len(x),np.nan); prevalue[prevalid]=sign[prevalid]*1e4*np.log(base[prevalid]/bef[prevalid])
            n=int(selected.sum()); avail=int(valid.sum()); same=int(uncertain.sum())
            aligned=int((valid & target_updated & (value>0)).sum())
            rows.append({'venue':venue,'date':date,'direction':direction,'sample':label,'window_ms':h//1_000_000,
                         'events':int(n),'usable_quote_events':int(avail),'quote_availability':avail/n if n else np.nan,
                         'simultaneous_or_order_uncertain_events':int(same),'mean_signed_response_bp':float(np.nanmean(value)) if avail else np.nan,
                         'median_signed_response_bp':float(np.nanmedian(value)) if avail else np.nan,
                         'same_direction_endpoint_after_update_probability_all_usable_events':aligned/avail if avail else np.nan,
                         'mean_prepath_bp':float(np.nanmean(prevalue)) if prevalid.any() else np.nan})

def main():
 p=argparse.ArgumentParser(); p.add_argument('--receipt',required=True); p.add_argument('--out',required=True); a=p.parse_args()
 receipt=json.load(open(a.receipt)); by={x['request_id']:x for x in receipt['selected_variant']['requests']}
 rows=[]; up=[]
 for f in receipt['files']:
  req=by[f['request_id']]; venue=req['dataset']; date=req['start_utc'][:10]; dat=decode(Path(f['path']))
  core_start=int(pd.Timestamp(req['start_utc']).value)+60*NS; core_end=int(pd.Timestamp(req['end_utc']).value)-60*NS
  if 'SPY' not in dat: continue
  for sym,(t,m,ch) in dat.items():
   source_changes=np.flatnonzero(ch&(t>=core_start)&(t<core_end));di=np.diff(t[source_changes])
   up.append({'venue':venue,'date':date,'symbol':sym,'midpoint_updates':int(len(source_changes)),
              'median_update_spacing_ms':float(np.median(di)/1e6) if len(di) else np.nan})
  for sym in sorted(x for x in dat if x!='SPY'):
   process_pair(dat['SPY'],dat[sym],date,venue,'ETF_TO_STOCK',core_start,core_end,rows)
   process_pair(dat[sym],dat['SPY'],date,venue,'STOCK_TO_ETF',core_start,core_end,rows)
 # Consolidate only aggregates; per-event data never leaves SCC.
 d=pd.DataFrame(rows)
 keys=['venue','direction','sample','window_ms']
 out=[]
 for k,g in d.groupby(keys):
  w=g['usable_quote_events'].to_numpy(float); n=g['events'].sum(); den=w.sum()
  out.append(dict(zip(keys,k),events=int(n),usable_quote_events=int(den),quote_availability=den/n if n else np.nan,
   simultaneous_or_order_uncertain_events=int(g['simultaneous_or_order_uncertain_events'].sum()),
   mean_signed_response_bp=float(np.average(g['mean_signed_response_bp'].fillna(0),weights=w)) if den else np.nan,
   median_of_date_medians_bp=float(g['median_signed_response_bp'].median()),
   same_direction_endpoint_after_update_probability_all_usable_events=float(np.average(g['same_direction_endpoint_after_update_probability_all_usable_events'].fillna(0),weights=w)) if den else np.nan,
   mean_prepath_bp=float(np.average(g['mean_prepath_bp'].fillna(0),weights=w)) if den else np.nan,
   test_dates=int(g.date.nunique())))
 od=Path(a.out); od.mkdir(parents=True,exist_ok=True)
 pd.DataFrame(out).to_csv(od/'QUOTE_RESPONSE_SUMMARY.csv',index=False)
 pd.DataFrame(up).to_csv(od/'QUOTE_UPDATE_DIAGNOSTICS_RAW_AGGREGATES.csv',index=False)
 print(json.dumps({'summary_rows':len(out),'raw_rows_remain_scc':True}))
if __name__=='__main__': main()
