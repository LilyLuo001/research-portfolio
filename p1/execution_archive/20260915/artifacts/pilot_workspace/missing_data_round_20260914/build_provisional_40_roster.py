#!/usr/bin/env python3
"""Build the original 5-package 4H/4L procurement roster, outcome-blind.

This freezes a reproducible acquisition roster but does not certify the final
analysis population.  Candidate ownership uses the explicitly labelled common
split-basis field; the later scientific review must adjudicate that convention.
"""
import hashlib,json,math
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parent
SRC=ROOT/'crsp_attached/stock_wave_candidate_roster.csv'
E007=Path('/Users/lilyluo/research-portfolio-p1-advanced-readonly/p1/exposure/exposure_stock_wave_all.csv')
A={'W002':'2020-11-16','W013':'2021-12-01','W016':'2022-08-26','W021':'2023-02-07','W025':'2023-06-14'}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def cutoff(s,p):
 x=sorted(s);return x[math.ceil(p*len(x))-1]
def main():
 x=pd.read_csv(SRC);x=x[x.ownership_common_basis_candidate.gt(0)].copy()
 e=pd.read_csv(E007);e=e[e.primary_ready.eq(True)&e.exposure_ownership.gt(0)].copy();e.effective_date=pd.to_datetime(e.effective_date)
 selected=[];tier_rows=[]
 for wave,g in x.groupby('wave_id'):
  q1=cutoff(g.ownership_common_basis_candidate.tolist(),1/3);q2=cutoff(g.ownership_common_basis_candidate.tolist(),2/3)
  g=g.copy();g['tier']=g.ownership_common_basis_candidate.map(lambda v:'LOW' if v<=q1 else ('HIGH' if v>q2 else 'MIDDLE'))
  lo=pd.Timestamp(A[wave])-pd.DateOffset(months=24);hi=pd.Timestamp(A[wave])+pd.DateOffset(months=24)
  other=e[(e.wave_id!=wave)&e.effective_date.between(lo,hi)]
  byperm=other.groupby('permno').agg(competing_waves=('wave_id',lambda s:';'.join(sorted(set(s)))),competing_dates=('effective_date',lambda s:';'.join(sorted({z.strftime('%Y-%m-%d') for z in s}))))
  g=g.merge(byperm,left_on='permno',right_index=True,how='left');g['competing_conversion_flag']=g.competing_waves.notna()
  for tier in ['LOW','HIGH']:
   t=g[g.tier==tier].copy();med=t.liquidity_median_dollar_volume_pre250_21.median();t['liquidity_stratum']=t.liquidity_median_dollar_volume_pre250_21.map(lambda v:'LOW_LIQ' if v<=med else 'HIGH_LIQ')
   picks=[]
   for ls in ['LOW_LIQ','HIGH_LIQ']:
    z=t[t.liquidity_stratum==ls].copy()
    z=z.sort_values(['ownership_common_basis_candidate','permno'],ascending=[tier=='LOW',True])
    z=z.head(2);picks.append(z)
   p=pd.concat(picks);p['selection_rank_within_tier']=range(1,len(p)+1);selected.append(p)
   tier_rows.append({'wave_id':wave,'tier':tier,'eligible_positive_rows':len(t),'ownership_cutoff_q1':q1,'ownership_cutoff_q2':q2,'liquidity_median':med,'selected':len(p),'selected_with_competing_conversion':int(p.competing_conversion_flag.sum())})
 out=pd.concat(selected,ignore_index=True)
 out['purpose']='PROVISIONAL_DATA_ACQUISITION_ROSTER_ONLY'
 out['final_analysis_eligibility']='NOT_CERTIFIED'
 out['ownership_formula_status']='PROVISIONAL_COMMON_SPLIT_BASIS_BOTH_RAW_FACTORS_PRESERVED'
 cols=['permno','historical_ticker','wave_id','announcement_cutoff','tier','liquidity_stratum','ownership_common_basis_candidate','liquidity_median_dollar_volume_pre250_21','predecessor_funds','report_dates','source_accessions','competing_conversion_flag','competing_waves','competing_dates','selection_rank_within_tier','purpose','final_analysis_eligibility','ownership_formula_status']
 out[cols].to_csv(ROOT/'PILOT_STOCKS_PROVISIONAL.csv',index=False)
 pd.DataFrame(tier_rows).to_csv(ROOT/'PILOT_TIER_RECEIPT.csv',index=False)
 receipt={'status':'PROVISIONAL_40_ROSTER_BUILT','rows':len(out),'waves':out.wave_id.nunique(),'unique_permnos':out.permno.nunique(),'high':int((out.tier=='HIGH').sum()),'low':int((out.tier=='LOW').sum()),'competing_flagged':int(out.competing_conversion_flag.sum()),'source_sha256':sha(SRC),'e007_sha256':sha(E007),'roster_sha256':sha(ROOT/'PILOT_STOCKS_PROVISIONAL.csv'),'tier_receipt_sha256':sha(ROOT/'PILOT_TIER_RECEIPT.csv'),'response_outcomes_read':False}
 (ROOT/'PILOT_STOCKS_PROVISIONAL_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
