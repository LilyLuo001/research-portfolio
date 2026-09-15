#!/usr/bin/env python3
"""Replace the provisional 35-day POST threshold with observed CRSP sessions."""
import hashlib,json
from pathlib import Path
import pandas as pd
ROOT=Path('/projectnb/econdept/qluo/P1_Refraction_WRDS/missing_data_round_20260914')
RAW=Path('/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared/raw/rescue')
IN=ROOT/'earnings_inputs/all_quarterly_event_candidates.csv';OLD=ROOT/'earnings_inputs/selected_earnings_event_metadata.csv';OUT=ROOT/'earnings_inputs_v2'
I={'W002':'2021-06-14','W013':'2022-10-31','W016':'2023-03-13','W021':'2023-07-31','W025':'2023-11-20'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 if OUT.exists():raise FileExistsError('preserve output')
 OUT.mkdir();e=pd.read_csv(IN);ps=set(e.permno.astype(int));frames=[]
 for y in range(2021,2025):
  p=RAW/f'crsp_dsf_allcols_{y}.parquet';d=pd.read_parquet(p,columns=['permno','date']);frames.append(d[d.permno.isin(ps)])
 d=pd.concat(frames);d.date=pd.to_datetime(d.date);d=d.drop_duplicates(['permno','date']).sort_values(['permno','date'])
 thresholds={}
 for w in I:
  impl=pd.Timestamp(I[w])
  for p in e[e.wave_id==w].permno.unique():
   dates=sorted(d[(d.permno==p)&(d.date>impl)].date.unique());thresholds[(w,int(p))]=pd.Timestamp(dates[19]) if len(dates)>=20 else pd.NaT
 chosen=[]
 for (w,p),g in e.groupby(['wave_id','permno']):
  g=g[g.announcement_date.notna()&g.pit_ambiguous_rows.eq(0)].copy();g['dt']=pd.to_datetime(g.announcement_date)
  pre=g[g.regime_initial=='PRE'].sort_values('dt').tail(8).copy();pre['sample_period']='PRE'
  post=g[g.dt>=thresholds[(w,int(p))]].sort_values('dt').head(4).copy();post['sample_period']='POST'
  pre['post_threshold_date']=thresholds[(w,int(p))].strftime('%Y-%m-%d');post['post_threshold_date']=thresholds[(w,int(p))].strftime('%Y-%m-%d')
  chosen += [pre,post]
 out=pd.concat(chosen,ignore_index=True);out['post_threshold_status']='VERIFIED_FROM_STOCK_CRSP_OBSERVED_SESSIONS_20TH_DATE_STRICTLY_AFTER_FIRST_TRADE';out.to_csv(OUT/'selected_earnings_event_metadata.csv',index=False)
 old=pd.read_csv(OLD);a=set(zip(old.permno.astype(int),old.pends.astype(str),old.sample_period));b=set(zip(out.permno.astype(int),out.pends.astype(str),out.sample_period))
 sc=out.groupby(['wave_id','permno','sample_period']).size().unstack(fill_value=0).reset_index();sc.to_csv(OUT/'event_counts_by_stock.csv',index=False)
 receipt={'status':'EXACT_20_SESSION_SELECTION_COMPLETE','associations':len(out),'stocks_with_8pre':int((sc.get('PRE',0)>=8).sum()),'stocks_with_4post':int((sc.get('POST',0)>=4).sum()),'same_event_keys_as_v1':a==b,'added_keys':len(b-a),'removed_keys':len(a-b),'output_sha256':sha(OUT/'selected_earnings_event_metadata.csv'),'prices_or_returns_read':False,'only_crsp_permno_date_read':True}
 (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
