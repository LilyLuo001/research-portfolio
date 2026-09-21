#!/usr/bin/env python3
"""SCC-only BBO reconstruction with target-time state validity, not valid-row filtering."""
import csv,json
from collections import defaultdict
from datetime import datetime,timedelta
from pathlib import Path
import databento as db
from databento_dbn import BBOMsg,UNDEF_PRICE,UNDEF_ORDER_SIZE

ROOT=Path('/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared/derived/p1_concentration_information/20260920_phase3/measurement')
MISS=Path('/projectnb/econdept/qluo/P1_Refraction_WRDS/missing_data_round_20260914/p1_six_event_20260922')
OUT=Path('/scratch/qluo/six_event_observed_paths_20260922')
EVENTS=[
 ('P1-2023-08-01','XOM','2023-01-31T11:30:00+00:00','06:30_ET',ROOT/'native_dbn/3e771140b59d588abd71.dbn.zst',ROOT/'native_dbn_second/0960f2ea732a055227d0.dbn.zst'),
 ('P1-2023-08-03','XOM','2023-07-28T10:00:00+00:00','06:00_ET',ROOT/'native_dbn/951e711f4f00f69187f1.dbn.zst',ROOT/'native_dbn_second/ddfffe94fb838815f703.dbn.zst'),
 ('P1-2023-08-03','XOM','2023-07-28T10:30:00+00:00','06:30_ET',ROOT/'native_dbn/951e711f4f00f69187f1.dbn.zst',ROOT/'native_dbn_second/ddfffe94fb838815f703.dbn.zst'),]
EVENTS += [
 ('P1-2023-06-02','UNH','2023-04-14T09:55:00+00:00','05:55_ET',MISS/'UNH_APR_XNAS.dbn.zst',MISS/'UNH_APR_ARCX.dbn.zst'),
 ('P1-2023-01-01','AAPL','2023-02-02T21:30:00+00:00','16:30_ET',MISS/'AAPL_FEB_XNAS.dbn.zst',MISS/'AAPL_FEB_ARCX.dbn.zst'),
 ('P1-2023-01-03','AAPL','2023-08-03T20:30:00+00:00','16:30_ET',MISS/'AAPL_AUG_XNAS.dbn.zst',MISS/'AAPL_AUG_ARCX.dbn.zst'),
 ('P1-2023-02-02','MSFT','2023-04-25T20:07:00+00:00','16:07_ET',MISS/'MSFT_APR_XNAS.dbn.zst',MISS/'MSFT_APR_ARCX.dbn.zst')]
def D(s): return datetime.fromisoformat(s)
def N(x): return int(x.timestamp()*1e9)
def ids(meta,date):
 out={}
 for s,ms in meta.mappings.items():
  v={int(m['symbol']) for m in ms if str(m['start_date'])<=date<str(m['end_date'])}
  if len(v)==1: out[s.upper()]=v.pop()
 return out
def state(r):
 l=r.levels[0]; b,a,bs,az=map(int,(l.bid_px,l.ask_px,l.bid_sz,l.ask_sz))
 if b==UNDEF_PRICE or a==UNDEF_PRICE or bs==UNDEF_ORDER_SIZE or az==UNDEF_ORDER_SIZE or min(b,a,bs,az)<=0: return ('INVALID_UNDEFINED_OR_ZERO_SIDE',None,None)
 if a<b:return ('INVALID_CROSSED',None,None)
 return ('VALID_LOCKED' if a==b else 'VALID',b/1e9,a/1e9)
def select(updates,target):
 # State evolution retains invalid updates. Conflicting same-time updates are invalid.
 xs=[x for x in updates if x[0]<=target]
 if not xs:return ('UNKNOWN_NO_PRIOR_STATE',None,None,None)
 t=xs[-1][0]; same=[x for x in xs if x[0]==t]
 if len({(x[1],x[2],x[3]) for x in same})>1:return ('INVALID_SAME_TIMESTAMP_CONFLICT',None,None,t)
 _,status,b,a=same[-1]; return (status,b,a,t)
def main():
 OUT.mkdir(parents=True,exist_ok=True); endpoints=[]; paths=[]; quality={'state_logic':'Every BBO update, including invalid/undefined/crossed states, is retained until target selection; invalid target state cannot be bypassed by prior valid quote. A no-update endpoint uses the latest observed state with quote age; continuity is not separately certified. Same-timestamp conflicting states are invalid.','state_fix_impact_jan31_xnas':'0 endpoint values changed versus the previous valid-row-only reconstruction; no later invalid target state was present at its declared endpoints.','purchases_usd':0.015461146832,'events':[]}
 for eid,stock,astr,label,xnas,arcx in EVENTS:
  anchor=D(astr); date=anchor.date().isoformat(); targets=[(-5,anchor-timedelta(minutes=5))]+[(h,anchor+timedelta(minutes=h)) for h in [0,1,5,15,30,60]]
  if xnas is None:
   for venue in ['XNAS.ITCH','ARCX.PILLAR']:
    for sym in ['SPY',stock]:
     for h,t in targets[1:]: endpoints.append({'event_id':eid,'stock':stock,'anchor':label,'anchor_utc':astr,'feed':venue,'symbol':sym,'horizon_minutes':h,'baseline_status':'UNAVAILABLE_NO_FILE','endpoint_status':'UNAVAILABLE_NO_FILE','baseline_mid':None,'bid':None,'ask':None,'mid':None,'mid_change_bps':None,'spread_bps':None,'cross_spread_lower_bps':None,'cross_spread_upper_bps':None,'quote_age_seconds':None})
    for minute in range(-15,76): paths.append({'event_id':eid,'stock':stock,'anchor':label,'anchor_utc':astr,'feed':venue,'minute_from_anchor':minute,'SPY_mid_index':None,'SPY_status':'UNAVAILABLE_NO_FILE','issuer_mid_index':None,'issuer_status':'UNAVAILABLE_NO_FILE'})
   quality['events'].append({'event_id':eid,'anchor':label,'status':'UNAVAILABLE_NO_FILE'});continue
  for venue,path in [('XNAS.ITCH',xnas),('ARCX.PILLAR',arcx)]:
   st=db.DBNStore.from_file(path); mp=ids(st.metadata,date); want={'SPY':mp.get('SPY'),stock:mp.get(stock)}; rec=defaultdict(list)
   file_end=int(st.metadata.end)
   lo=N(anchor-timedelta(minutes=15)); hi=N(anchor+timedelta(minutes=75))
   for r in st:
    if not isinstance(r,BBOMsg) or int(r.instrument_id) not in set(x for x in want.values() if x):continue
    if not lo<=int(r.ts_recv)<=hi:continue
    sym=next(k for k,v in want.items() if v==int(r.instrument_id)); z,b,a=state(r); rec[sym].append((int(r.ts_recv),z,b,a))
   for sym in ['SPY',stock]:
    base=select(rec[sym],N(anchor-timedelta(minutes=5))) if want.get(sym) else ('MISSING_SYMBOL_MAPPING',None,None,None)
    for h,t in targets[1:]:
     status,bid,ask,ts=('UNAVAILABLE_BEYOND_ARCHIVE_END',None,None,None) if N(t)>=file_end else (select(rec[sym],N(t)) if want.get(sym) else ('MISSING_SYMBOL_MAPPING',None,None,None))
     mid=None if bid is None else (bid+ask)/2; bm=None if base[1] is None else (base[1]+base[2])/2
     endpoints.append({'event_id':eid,'stock':stock,'anchor':label,'anchor_utc':astr,'feed':venue,'symbol':sym,'horizon_minutes':h,'baseline_status':base[0],'endpoint_status':status,'baseline_mid':bm,'bid':bid,'ask':ask,'mid':mid,'mid_change_bps':None if not bm or not mid else 1e4*(mid/bm-1),'spread_bps':None if not mid else 1e4*(ask-bid)/mid,'cross_spread_lower_bps':None if not bm or not bid or not base[2] else 1e4*(bid/base[2]-1),'cross_spread_upper_bps':None if not bm or not ask or not base[1] else 1e4*(ask/base[1]-1),'quote_age_seconds':None if ts is None else (N(t)-ts)/1e9})
   if venue=='XNAS.ITCH':
    for minute in range(-15,76):
     t=anchor+timedelta(minutes=minute); row={'event_id':eid,'stock':stock,'anchor':label,'anchor_utc':astr,'feed':venue,'minute_from_anchor':minute}
     for sym in ['SPY',stock]:
      base=select(rec[sym],N(anchor-timedelta(minutes=5))) if want.get(sym) else ('MISSING_SYMBOL_MAPPING',None,None,None); z,b,a,ts=('UNAVAILABLE_BEYOND_ARCHIVE_END',None,None,None) if N(t)>=file_end else (select(rec[sym],N(t)) if want.get(sym) else ('MISSING_SYMBOL_MAPPING',None,None,None)); bm=None if base[1] is None else (base[1]+base[2])/2; mid=None if b is None else (b+a)/2
      if sym=='SPY':
       row['SPY_mid_index']=None if not bm or not mid else 100*mid/bm; row['SPY_bid_index']=None if not bm or not b else 100*b/bm; row['SPY_ask_index']=None if not bm or not a else 100*a/bm; row['SPY_status']=z
      else:
       row['issuer_mid_index']=None if not bm or not mid else 100*mid/bm; row['issuer_bid_index']=None if not bm or not b else 100*b/bm; row['issuer_ask_index']=None if not bm or not a else 100*a/bm; row['issuer_status']=z
     paths.append(row)
   quality['events'].append({'event_id':eid,'anchor':label,'feed':venue,'path':str(path),'mapped_symbols':sorted(mp),'selected_record_counts':{s:len(rec[s]) for s in rec}})
 with (OUT/'ENDPOINTS.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=endpoints[0]);w.writeheader();w.writerows(endpoints)
 with (OUT/'PATHS.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=paths[0]);w.writeheader();w.writerows(paths)
 (OUT/'QUALITY_SUMMARY.json').write_text(json.dumps(quality,indent=2)+'\n');print(json.dumps({'endpoints':len(endpoints),'paths':len(paths)}))
if __name__=='__main__':main()
