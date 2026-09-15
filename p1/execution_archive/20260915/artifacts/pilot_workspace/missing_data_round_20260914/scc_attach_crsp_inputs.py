#!/usr/bin/env python3
"""SCC custodian build for the five-package strict-PRE holdings roster.

Reads only explicit identity, corporate-action, shares and liquidity fields.
It preserves both report-date and cutoff-date factors so a later contract can
choose the correct common split basis.  No return or post-treatment outcome is
read or emitted.
"""
from __future__ import annotations
import bisect, hashlib, json
from pathlib import Path
import pandas as pd

ROOT=Path('/projectnb/econdept/qluo/P1_Refraction_WRDS/missing_data_round_20260914')
MIRROR=Path('/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902')
RAW=MIRROR/'p1_refraction_wrds_shared/raw/rescue'
INPUT=ROOT/'strict_preannouncement_holdings.parquet'
OUT=ROOT/'crsp_attached'
EXPECTED='f0a4b73c12e152a5fa685f8d9726dd89354f195a462b91e88a810cba49a75afa'

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def norm(v): return '' if pd.isna(v) else str(v).strip().upper()

def main():
 if sha(INPUT)!=EXPECTED:raise ValueError('pinned holdings mismatch')
 if OUT.exists():raise FileExistsError('new output directory required')
 OUT.mkdir(parents=True)
 h=pd.read_parquet(INPUT)
 h=h[h.is_common_equity_candidate.eq(True)].copy()
 snp=RAW/'newcrsp_crsp_stocknames_v2_full.parquet'
 sn=pd.read_parquet(snp,columns=['permno','cusip9','cusip','ticker','namedt','nameenddt','sharetype','securitytype','securitysubtype','usincflg'])
 sn['namedt']=pd.to_datetime(sn.namedt,errors='coerce');sn['nameenddt']=pd.to_datetime(sn.nameenddt,errors='coerce').fillna(pd.Timestamp('2099-12-31'))
 for c in ['cusip9','cusip','ticker','sharetype','securitytype','securitysubtype','usincflg']:sn[c]=sn[c].map(norm)
 by9={k:g for k,g in sn.groupby('cusip9') if k};by8={k:g for k,g in sn.assign(c8=sn.cusip.str[:8]).groupby('c8') if k}
 mapped=[]
 for r in h.itertuples(index=False):
  c=norm(r.cusip);dt=pd.Timestamp(r.pre_report_date);method='cusip9'
  g=by9.get(c)
  if g is None or g.empty:method='cusip8';g=by8.get(c[:8])
  if g is None:g=sn.iloc[0:0]
  g=g[(g.namedt<=dt)&(dt<=g.nameenddt)]
  g=g[(g.sharetype=='NS')&(g.securitytype=='EQTY')&(g.securitysubtype=='COM')&(g.usincflg=='Y')]
  ps=sorted(pd.to_numeric(g.permno,errors='coerce').dropna().astype(int).unique())
  mapped.append({'mapping_status':'exact_matched' if len(ps)==1 else ('ambiguous' if len(ps)>1 else 'unmatched'),
   'mapping_method':method,'permno':ps[0] if len(ps)==1 else None,
   'candidate_permnos':';'.join(map(str,ps)),'historical_ticker':g.iloc[0].ticker if len(ps)==1 else ''})
 x=pd.concat([h.reset_index(drop=True),pd.DataFrame(mapped)],axis=1)
 wanted=set(pd.to_numeric(x.permno,errors='coerce').dropna().astype(int))
 daily=[]; lineage=[]
 for year in range(2019,2024):
  p=RAW/f'crsp_dsf_allcols_{year}.parquet'
  d=pd.read_parquet(p,columns=['permno','date','prc','vol','shrout','cfacshr'])
  d=d[d.permno.isin(wanted)].copy();d=d.rename(columns={'date':'crsp_date','prc':'price','cfacshr':'share_factor'})
  d['source_file']=str(p);daily.append(d);lineage.append({'path':str(p),'sha256':sha(p),'selected_rows':len(d)})
 d=pd.concat(daily,ignore_index=True);d['permno']=d.permno.astype(int);d['crsp_date']=pd.to_datetime(d.crsp_date)
 for c in ['price','vol','shrout','share_factor']:d[c]=pd.to_numeric(d[c],errors='coerce')
 d['price']=d.price.abs();d=d.sort_values(['permno','crsp_date']).drop_duplicates(['permno','crsp_date'],keep='last')
 idx={p:(list(g.crsp_date),list(g.itertuples(index=False))) for p,g in d.groupby('permno')}
 def prior(p,target,strict,maxgap):
  dates,rows=idx.get(int(p),([],[]));target=pd.Timestamp(target)
  j=(bisect.bisect_left(dates,target) if strict else bisect.bisect_right(dates,target))-1
  return None if j<0 or (target-dates[j]).days>maxgap else rows[j]
 for c in ['report_factor_date','report_share_factor','cutoff_denominator_date','cutoff_shares_outstanding_raw','cutoff_share_factor','cutoff_price','liquidity_median_dollar_volume_pre250_21','liquidity_days']:
  x[c]=None
 for i,r in x[x.mapping_status=='exact_matched'].iterrows():
  p=int(r.permno);rf=prior(p,r.pre_report_date,False,4);cd=prior(p,r.announcement_cutoff,True,7)
  if rf is not None:x.at[i,'report_factor_date']=rf.crsp_date.strftime('%Y-%m-%d');x.at[i,'report_share_factor']=rf.share_factor
  if cd is not None:
   x.at[i,'cutoff_denominator_date']=cd.crsp_date.strftime('%Y-%m-%d');x.at[i,'cutoff_shares_outstanding_raw']=cd.shrout*1000;x.at[i,'cutoff_share_factor']=cd.share_factor;x.at[i,'cutoff_price']=cd.price
  dates,rows=idx.get(p,([],[]));pos=bisect.bisect_left(dates,pd.Timestamp(r.announcement_cutoff));window=rows[max(0,pos-250):max(0,pos-20)]
  dvs=[z.price*z.vol for z in window if pd.notna(z.price) and pd.notna(z.vol) and z.price>0 and z.vol>=0]
  if dvs:x.at[i,'liquidity_median_dollar_volume_pre250_21']=float(pd.Series(dvs).median());x.at[i,'liquidity_days']=len(dvs)
 x['numerator_common_basis']=pd.to_numeric(x.raw_reported_shares,errors='coerce')*pd.to_numeric(x.report_share_factor,errors='coerce')
 x['denominator_common_basis']=pd.to_numeric(x.cutoff_shares_outstanding_raw,errors='coerce')*pd.to_numeric(x.cutoff_share_factor,errors='coerce')
 # Both raw inputs and two candidate arithmetic fields are retained.  This is
 # not a sign-off on the split convention.
 x['ownership_common_basis_candidate']=x.numerator_common_basis/x.denominator_common_basis
 x['ownership_legacy_formula_candidate']=x.numerator_common_basis/pd.to_numeric(x.cutoff_shares_outstanding_raw,errors='coerce')
 x.to_parquet(OUT/'position_inputs.parquet',index=False)
 # Aggregate only complete candidate common-basis inputs; this supports roster
 # preparation while retaining PROVISIONAL labels.
 z=x[x.mapping_status=='exact_matched'].copy()
 keys=['permno','wave_id','announcement_cutoff','announcement_cutoff_status','historical_ticker']
 def agg(g):
  nums=pd.to_numeric(g.numerator_common_basis,errors='coerce');den=pd.to_numeric(g.denominator_common_basis,errors='coerce').dropna().unique()
  return pd.Series({'predecessor_funds':g.pre_series_id.nunique(),'positions':len(g),'raw_shares_sum':pd.to_numeric(g.raw_reported_shares,errors='coerce').sum(min_count=1),
   'numerator_common_basis_sum':nums.sum(min_count=1),'denominator_common_basis':den[0] if len(den)==1 else None,
   'ownership_common_basis_candidate':nums.sum(min_count=1)/den[0] if nums.notna().all() and len(den)==1 and den[0]>0 else None,
   'denominator_date':';'.join(sorted(set(g.cutoff_denominator_date.dropna().astype(str)))),
   'report_dates':';'.join(sorted(set(g.pre_report_date.astype(str)))),'source_accessions':';'.join(sorted(set(g.pre_accession.astype(str)))),
   'liquidity_median_dollar_volume_pre250_21':pd.to_numeric(g.liquidity_median_dollar_volume_pre250_21,errors='coerce').median(),
   'liquidity_days_min':pd.to_numeric(g.liquidity_days,errors='coerce').min(),
   'split_basis_status':'PROVISIONAL_PENDING_CONTRACT_CONFIRMATION'})
 roster=z.groupby(keys,dropna=False).apply(agg).reset_index()
 roster.to_csv(OUT/'stock_wave_candidate_roster.csv',index=False)
 receipt={'status':'SCC_INPUT_BUILD_COMPLETE','positions_input':len(h),'mapped_positions':int((x.mapping_status=='exact_matched').sum()),
  'ambiguous_positions':int((x.mapping_status=='ambiguous').sum()),'unmatched_positions':int((x.mapping_status=='unmatched').sum()),
  'candidate_stock_wave_rows':len(roster),'waves':roster.wave_id.nunique(),'unique_permnos':roster.permno.nunique(),
  'position_inputs_sha256':sha(OUT/'position_inputs.parquet'),'candidate_roster_sha256':sha(OUT/'stock_wave_candidate_roster.csv'),
  'stocknames':{'path':str(snp),'sha256':sha(snp)},'daily_sources':lineage,'return_fields_read':False,'post_outcomes_read':False,
  'raw_inputs_modified':False,'formula_status':'BOTH_FACTORS_RETAINED_PROVISIONAL'}
 (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
