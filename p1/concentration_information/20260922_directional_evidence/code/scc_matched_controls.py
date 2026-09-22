#!/usr/bin/env python3
"""SCC-only pre-center matched controls for directional midpoint events.

For each source midpoint-change event, controls are one-second grid centers in
the same source/date/five-minute bin.  They are matched exactly on terciles of
the source's *pre-center* quoted spread, absolute five-second midpoint move,
and prior-five-second midpoint-update count.  Candidate selection is a stable
hash within its exact pre-center cell; neither subsequent source nor target
events/responses enter matching.  Only aggregate event-minus-control rows are
written to the requested output directory.
"""
from __future__ import annotations
import argparse,json,hashlib
from pathlib import Path
import numpy as np,pandas as pd,databento as db
from databento_dbn import MBP1Msg,UNDEF_ORDER_SIZE,UNDEF_PRICE
NS=1_000_000_000; HS=[100_000_000,500_000_000,NS,2*NS,5*NS]
def q(r):
 x=r.levels[0];b,a,bs,az=map(int,(x.bid_px,x.ask_px,x.bid_sz,x.ask_sz))
 if b==UNDEF_PRICE or a==UNDEF_PRICE or bs==UNDEF_ORDER_SIZE or az==UNDEF_ORDER_SIZE or min(b,a,bs,az)<=0 or a<b:return (np.nan,np.nan)
 m=(b+a)/2e9;return m,1e4*(a-b)/(a+b)
def decode(p):
 s=db.DBNStore.from_file(p); mp={int(z['symbol']):k.upper() for k,v in s.metadata.mappings.items() for z in v};o={}
 for r in s:
  if not isinstance(r,MBP1Msg):continue
  z=mp.get(int(r.instrument_id));
  if z is None:continue
  act=str(getattr(r.action,'value',r.action));m,sp=(np.nan,np.nan) if act=='R' else q(r)
  o.setdefault(z,[[],[],[]]);o[z][0].append(int(r.ts_event));o[z][1].append(m);o[z][2].append(sp)
 ans={}
 for z,(t,m,sp) in o.items():
  t=np.asarray(t,np.int64);m=np.asarray(m,float);sp=np.asarray(sp,float);last=np.r_[np.flatnonzero(t[1:]!=t[:-1]),len(t)-1];t,m,sp=t[last],m[last],sp[last]
  ch=np.zeros(len(t),bool);ch[1:]=np.isfinite(m[1:])&np.isfinite(m[:-1])&(m[1:]!=m[:-1]);ans[z]=(t,m,sp,ch)
 return ans
def at(t,a,x,left=False):
 i=np.searchsorted(t,x,side='left' if left else 'right')-1
 return np.where(i>=0,a[np.maximum(i,0)],np.nan),i
def tercile(v,cut):return np.searchsorted(cut,v,side='right')
def run_pair(src,tgt,venue,date,direction,core_start,core_end,rows):
 st,sm,ss,sc=src;tt,tm,ts,tc=tgt; ei=np.flatnonzero(sc&(st>=core_start)&(st<core_end)); et=st[ei]
 # prospective non-overlap selection
 keep=[];last=-10**30
 for i in ei:
  if st[i]-last>=5*NS:keep.append(i);last=st[i]
 # fixed grid candidates and their strictly pre-center features
 grid=np.arange(core_start,core_end,NS,dtype=np.int64)
 # Matching covariates are strictly pre-center.  In particular, do not use
 # the quote/message at a grid or event center to select its control.
 gm,_=at(st,sm,grid,left=True);gsp,_=at(st,ss,grid,left=True);gm5,_=at(st,sm,grid-5*NS,left=True)
 pref=np.r_[0,np.cumsum(sc.astype(int))];gi0=np.searchsorted(st,grid-5*NS,side='right');gi1=np.searchsorted(st,grid,side='left')
 gup=pref[gi1]-pref[gi0];gvol=np.abs(np.log(gm/gm5))*1e4
 good=np.isfinite(gm)&np.isfinite(gsp)&np.isfinite(gvol)
 cuts=[np.quantile(x[good],[1/3,2/3]) for x in (gsp,gvol,gup)]
 gb=np.column_stack([grid//(300*NS),tercile(gsp,cuts[0]),tercile(gvol,cuts[1]),tercile(gup,cuts[2])])
 em, _=at(st,sm,et,left=True);esp,_=at(st,ss,et,left=True);em5,_=at(st,sm,et-5*NS,left=True);evol=np.abs(np.log(em/em5))*1e4
 ei0=np.searchsorted(st,et-5*NS,side='right');ei1=np.searchsorted(st,et,side='left');eup=pref[ei1]-pref[ei0]
 eb=np.column_stack([et//(300*NS),tercile(esp,cuts[0]),tercile(evol,cuts[1]),tercile(eup,cuts[2])])
 # Match within the exact five-minute-bin / three-tercile pre-state cell.
 # Controls must be strictly more than ten seconds away from the trigger, so
 # their response window cannot mechanically contain that trigger.  For every
 # event choose the nearest such grid center; ties go to the earlier center.
 # No future event or response data enter this choice.
 control=np.full(len(ei),-1,dtype=int)
 gkey=gb[:,0]*27+gb[:,1]*9+gb[:,2]*3+gb[:,3]
 ekey=eb[:,0]*27+eb[:,1]*9+eb[:,2]*3+eb[:,3]
 for key in np.unique(ekey):
  ix=np.flatnonzero(ekey==key); cand=np.flatnonzero(good&(gkey==key))
  if not len(cand):continue
  ct=grid[cand]
  # Last candidate strictly before t-10s, and first strictly after t+10s.
  li=np.searchsorted(ct,et[ix]-10*NS,side='left')-1
  ri=np.searchsorted(ct,et[ix]+10*NS,side='right')
  left=np.where(li>=0,cand[np.maximum(li,0)],-1)
  right=np.where(ri<len(cand),cand[np.minimum(ri,len(cand)-1)],-1)
  dl=np.where(left>=0,et[ix]-grid[np.maximum(left,0)],np.inf)
  dr=np.where(right>=0,grid[np.maximum(right,0)]-et[ix],np.inf)
  control[ix]=np.where(dl<=dr,left,right)
 for sample,ids in [('all',np.arange(len(ei))),('nonoverlap',np.searchsorted(ei,np.asarray(keep,int)))]:
  ids=ids[(ids>=0)&(ids<len(ei))&(control[ids]>=0)]; x=et[ids];cx=grid[control[ids]];sg=np.sign(sm[ei[ids]]-sm[ei[ids]-1])
  for h in HS:
   def resp(x):
    b,_=at(tt,tm,x,left=True);a,_=at(tt,tm,x+h);ok=np.isfinite(b)&np.isfinite(a)&(b>0)&(a>0);v=np.full(len(x),np.nan);v[ok]=sg[ok]*1e4*np.log(a[ok]/b[ok]);return v,ok
   ev,eok=resp(x);cv,cok=resp(cx);ok=eok&cok
   rows.append(dict(venue=venue,date=date,direction=direction,sample=sample,window_ms=h//1_000_000,matched_event_control_pairs=int(ok.sum()),candidate_controls=int(len(ids)),mean_event_minus_control_bp=float(np.mean(ev[ok]-cv[ok])) if ok.any() else np.nan))
def main():
 a=argparse.ArgumentParser();a.add_argument('--receipt',required=True);a.add_argument('--out',required=True);x=a.parse_args();r=json.load(open(x.receipt));by={q['request_id']:q for q in r['selected_variant']['requests']};rows=[]
 for f in r['files']:
  rq=by[f['request_id']];d=decode(Path(f['path']));core_start=int(pd.Timestamp(rq['start_utc']).value)+60*NS;core_end=int(pd.Timestamp(rq['end_utc']).value)-60*NS
  if 'SPY' not in d:continue
  for z in d:
   if z!='SPY':run_pair(d['SPY'],d[z],rq['dataset'],rq['start_utc'][:10],'ETF_TO_STOCK',core_start,core_end,rows);run_pair(d[z],d['SPY'],rq['dataset'],rq['start_utc'][:10],'STOCK_TO_ETF',core_start,core_end,rows)
 out=[]
 for k,g in pd.DataFrame(rows).groupby(['venue','direction','sample','window_ms']):
  w=g.matched_event_control_pairs;out.append(dict(zip(['venue','direction','sample','window_ms'],k),matched_event_control_pairs=int(w.sum()),candidate_controls=int(g.candidate_controls.sum()),mean_event_minus_control_bp=float(np.average(g.mean_event_minus_control_bp.fillna(0),weights=w)) if w.sum() else np.nan,test_dates=int(g.date.nunique())))
 Path(x.out).mkdir(parents=True,exist_ok=True);pd.DataFrame(out).to_csv(Path(x.out)/'MATCHED_CONTROL_RESPONSE_SUMMARY.csv',index=False)
if __name__=='__main__':main()
