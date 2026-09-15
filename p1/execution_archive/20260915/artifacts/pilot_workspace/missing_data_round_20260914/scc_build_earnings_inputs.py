#!/usr/bin/env python3
"""Build the original pilot's 8-PRE/4-POST earnings/SUE inputs on SCC.

Raw licensed financial values remain on SCC.  Only manifests and aggregate
receipts may be copied locally.  No prices, quote outcomes, CARs or treatment
estimates are read.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq

ROOT=Path('/projectnb/econdept/qluo/P1_Refraction_WRDS/missing_data_round_20260914')
RAW=Path('/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared/raw')
ROSTER=ROOT/'PILOT_STOCKS_PROVISIONAL.csv'
LINK=RAW/'crsp_ibes_link_full.parquet'
OUT=ROOT/'earnings_inputs'
EXPECTED='f355358a4583ad83c8d458c656998a27132c793291edeed3b1ec386f83042c29'
CONFIG={
 'W002':{'a':'2020-11-16','i':'2021-06-14','lo':'2019-01-01','hi':'2022-12-31'},
 'W013':{'a':'2021-12-01','i':'2022-10-31','lo':'2020-01-01','hi':'2024-03-31'},
 'W016':{'a':'2022-08-26','i':'2023-03-13','lo':'2020-01-01','hi':'2024-09-30'},
 'W021':{'a':'2023-02-07','i':'2023-07-31','lo':'2020-01-01','hi':'2024-12-31'},
 'W025':{'a':'2023-06-14','i':'2023-11-20','lo':'2020-01-01','hi':'2024-12-31'}}
ACT=['ticker','cusip','pends','pdicity','anndats','anntims','actdats','acttims','value','curr_act','usfirm']
DET=['ticker','cusip','actdats','estimator','analys','currfl','pdf','fpi','measure','value','curr','usfirm','fpedats','acttims','revdats','revtims','anndats','anntims','report_curr']
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 if sha(ROSTER)!=EXPECTED:raise ValueError('roster hash mismatch')
 if OUT.exists():raise FileExistsError('new output directory required')
 OUT.mkdir(parents=True)
 r=pd.read_csv(ROSTER);permnos=set(r.permno.astype(int))
 links=pq.read_table(LINK,columns=['permno','ncusip','sdate','edate','score'],filters=[('permno','in',sorted(permnos))]).to_pandas()
 links=links[links.permno.isin(permnos)].copy();links['cusip']=links.ncusip.astype('string').str.strip().str.upper();links['sdate']=pd.to_datetime(links.sdate);links['edate']=pd.to_datetime(links.edate).fillna(pd.Timestamp('2099-12-31'))
 cusips=set(links.cusip.dropna())
 actual=[];ain=[]
 for year in range(2019,2025):
  p=RAW/f'ibes_actuals_eps_{year}.parquet';schema=pq.read_schema(p)
  if any(c not in schema.names for c in ACT):raise ValueError(f'actual schema missing {p}')
  x=pd.read_parquet(p,columns=ACT);x['cusip']=x.cusip.astype('string').str.strip().str.upper();x=x[x.cusip.isin(cusips)].copy();x['source_partition']=p.name;actual.append(x);ain.append({'path':str(p),'sha256':sha(p),'selected_rows':len(x)})
 a=pd.concat(actual,ignore_index=True);a['anndats']=pd.to_datetime(a.anndats);a['pends']=pd.to_datetime(a.pends)
 j=a.merge(links,on='cusip',how='inner');j=j[(j.sdate<=j.anndats)&(j.anndats<=j.edate)].copy()
 # Do not pick arbitrary mapping scores. Ambiguity is an explicit flag.
 key=['permno','cusip','pends','pdicity','anndats','anntims','value','curr_act']
 j['pit_mapping_count']=j.groupby(key,dropna=False).permno.transform('size')
 j['pit_mapping_status']=j.pit_mapping_count.map(lambda n:'UNAMBIGUOUS' if n==1 else 'AMBIGUOUS_RETAINED')
 events=[]
 for rr in r.itertuples(index=False):
  c=CONFIG[rr.wave_id];z=j[(j.permno==int(rr.permno))&(j.pdicity.astype(str).str.upper()=='QTR')&j.anndats.between(c['lo'],c['hi'])].copy()
  # Period-level identity; preserve source variants and only select a period
  # when the public release date has one unambiguous value.
  for pends,g in z.groupby('pends'):
   dates=sorted({d.strftime('%Y-%m-%d') for d in g.anndats.dropna()});clocks=sorted({str(v) for v in g.anntims.dropna()})
   d=dates[0] if len(dates)==1 else None
   regime='PRE' if d and d<c['a'] else ('POST_CANDIDATE' if d and d>=c['i'] else 'TRANSITION_OR_UNKNOWN')
   events.append({'wave_id':rr.wave_id,'permno':int(rr.permno),'historical_ticker':rr.historical_ticker,'tier':rr.tier,'liquidity_stratum':rr.liquidity_stratum,'pends':pends.strftime('%Y-%m-%d'),'announcement_date':d,'announcement_dates_all':';'.join(dates),'announcement_times_all':';'.join(clocks),'source_rows':len(g),'pit_ambiguous_rows':int((g.pit_mapping_status!='UNAMBIGUOUS').sum()),'regime_initial':regime,'search_lo':c['lo'],'search_hi':c['hi'],'announcement_cutoff':c['a'],'implementation_first_trade':c['i']})
 ev=pd.DataFrame(events);chosen=[]
 for (w,p),g in ev.groupby(['wave_id','permno']):
  g=g[g.announcement_date.notna()&g.pit_ambiguous_rows.eq(0)].copy();g['announcement_date_dt']=pd.to_datetime(g.announcement_date)
  pre=g[g.announcement_date_dt<pd.Timestamp(CONFIG[w]['a'])].sort_values('announcement_date_dt').tail(8).copy();pre['sample_period']='PRE'
  # 20-session threshold is computed from the stock's observed CRSP daily
  # calendar in the separately pinned daily inputs; for the acquisition seed,
  # retain a conservative 35-calendar-day threshold and label it provisional.
  threshold=pd.Timestamp(CONFIG[w]['i'])+pd.Timedelta(days=35)
  post=g[g.announcement_date_dt>=threshold].sort_values('announcement_date_dt').head(4).copy();post['sample_period']='POST'
  for q in [pre,post]:chosen.append(q)
 sel=pd.concat(chosen,ignore_index=True) if chosen else ev.iloc[0:0].copy()
 sel['post_threshold_status']='PROVISIONAL_35_CALENDAR_DAYS_AT_LEAST_20_SESSIONS_TO_BE_VERIFIED'
 sel.to_csv(OUT/'selected_earnings_event_metadata.csv',index=False)
 ev.to_csv(OUT/'all_quarterly_event_candidates.csv',index=False)
 # Store source actual records only for chosen stock-period keys.
 keys=sel[['permno','pends']].drop_duplicates();keys['pends']=pd.to_datetime(keys.pends)
 actual_selected=j.merge(keys,on=['permno','pends'],how='inner')
 actual_selected.to_parquet(OUT/'licensed_actuals_selected.parquet',index=False)
 # Forecast detail: filter candidate CUSIPs and then retain only selected
 # fiscal periods and the 90-day pre-release envelope. Values stay SCC-side.
 detail=[];din=[]
 selected_pends=set(pd.to_datetime(sel.pends));release={(int(x.permno),pd.Timestamp(x.pends)):pd.Timestamp(x.announcement_date) for x in sel.itertuples()}
 for year in range(2019,2025):
  p=RAW/f'ibes_detu_eps_{year}.parquet';schema=pq.read_schema(p)
  if any(c not in schema.names for c in DET):raise ValueError(f'detail schema missing {p}')
  x=pd.read_parquet(p,columns=DET);x['cusip']=x.cusip.astype('string').str.strip().str.upper();x['fpedats']=pd.to_datetime(x.fpedats);x=x[x.cusip.isin(cusips)&x.fpedats.isin(selected_pends)].copy();x['source_partition']=p.name;detail.append(x);din.append({'path':str(p),'sha256':sha(p),'candidate_rows':len(x)})
 d=pd.concat(detail,ignore_index=True);d['anndats']=pd.to_datetime(d.anndats);dj=d.merge(links,on='cusip',how='inner');dj=dj[(dj.sdate<=dj.fpedats)&(dj.fpedats<=dj.edate)&dj.permno.isin(permnos)].copy()
 dj['release_date']=dj.apply(lambda q:release.get((int(q.permno),pd.Timestamp(q.fpedats))),axis=1)
 dj=dj[dj.release_date.notna()&(dj.anndats<dj.release_date)&(dj.anndats>=dj.release_date-pd.Timedelta(days=90))].copy()
 dj.to_parquet(OUT/'licensed_forecasts_90d_selected.parquet',index=False)
 counts=sel.groupby(['wave_id','sample_period']).size().unstack(fill_value=0).reset_index();counts.to_csv(OUT/'event_counts_by_wave.csv',index=False)
 stock_counts=sel.groupby(['wave_id','permno','sample_period']).size().unstack(fill_value=0).reset_index();stock_counts.to_csv(OUT/'event_counts_by_stock.csv',index=False)
 receipt={'status':'EARNINGS_INPUTS_ACQUIRED_SCC_ONLY','roster_rows':len(r),'candidate_cusips':len(cusips),'pit_link_rows':len(links),'quarterly_period_candidates':len(ev),'selected_event_associations':len(sel),'selected_unique_stock_periods':len(keys),'selected_actual_source_rows':len(actual_selected),'forecast_rows_90d':len(dj),'stocks_with_8pre':int((stock_counts.get('PRE',0)>=8).sum()),'stocks_with_4post':int((stock_counts.get('POST',0)>=4).sum()),'actuals_sha256':sha(OUT/'licensed_actuals_selected.parquet'),'forecasts_sha256':sha(OUT/'licensed_forecasts_90d_selected.parquet'),'event_metadata_sha256':sha(OUT/'selected_earnings_event_metadata.csv'),'actual_inputs':ain,'forecast_inputs':din,'financial_values_local_exported':False,'quote_or_return_outcomes_read':False,'post_treatment_effect_estimated':False}
 (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
