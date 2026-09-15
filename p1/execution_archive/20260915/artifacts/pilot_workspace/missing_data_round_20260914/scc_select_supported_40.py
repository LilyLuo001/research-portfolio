#!/usr/bin/env python3
"""Use outcomes-blind earnings metadata to freeze a fully supported 40 roster."""
import hashlib,json,math
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq
ROOT=Path('/projectnb/econdept/qluo/P1_Refraction_WRDS/missing_data_round_20260914');RAW=Path('/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared/raw');RES=ROOT/'crsp_attached/stock_wave_candidate_roster.csv';OUT=ROOT/'supported_roster'
LINK=RAW/'crsp_ibes_link_full.parquet'
C={'W002':('2020-11-16','2021-06-14','2019-01-01','2022-12-31'),'W013':('2021-12-01','2022-10-31','2020-01-01','2024-03-31'),'W016':('2022-08-26','2023-03-13','2020-01-01','2024-09-30'),'W021':('2023-02-07','2023-07-31','2020-01-01','2024-12-31'),'W025':('2023-06-14','2023-11-20','2020-01-01','2024-12-31')}
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def ecdf(s,p):
 x=sorted(s);return x[math.ceil(len(x)*p)-1]
def main():
 if OUT.exists():raise FileExistsError('preserve output')
 OUT.mkdir();r=pd.read_csv(RES);r=r[r.ownership_common_basis_candidate.gt(0)].copy();ps=set(r.permno.astype(int))
 l=pq.read_table(LINK,columns=['permno','ncusip','sdate','edate','score'],filters=[('permno','in',sorted(ps))]).to_pandas();l=l[l.permno.isin(ps)].copy();l['cusip']=l.ncusip.astype('string').str.strip().str.upper();l.sdate=pd.to_datetime(l.sdate);l.edate=pd.to_datetime(l.edate).fillna(pd.Timestamp('2099-12-31'));cs=set(l.cusip)
 acts=[]
 for y in range(2019,2025):
  p=RAW/f'ibes_actuals_eps_{y}.parquet';x=pd.read_parquet(p,columns=['ticker','cusip','pends','pdicity','anndats','anntims','actdats','acttims']);x['cusip']=x.cusip.astype('string').str.strip().str.upper();acts.append(x[x.cusip.isin(cs)])
 a=pd.concat(acts,ignore_index=True);a.pends=pd.to_datetime(a.pends);a.anndats=pd.to_datetime(a.anndats);j=a.merge(l,on='cusip');j=j[(j.sdate<=j.anndats)&(j.anndats<=j.edate)&(j.pdicity.astype(str).str.upper()=='QTR')].copy();j=j.drop_duplicates(['permno','cusip','pends','anndats','anntims'])
 # Actual source record must map to one candidate PERMNO on its date.
 sk=['cusip','pends','anndats','anntims'];j['mapped_permnos']=j.groupby(sk,dropna=False).permno.transform('nunique');j=j[j.mapped_permnos==1]
 # Exact 20 observed CRSP sessions after implementation for every candidate.
 dfs=[]
 for y in range(2021,2025):
  p=RAW/'rescue'/f'crsp_dsf_allcols_{y}.parquet';d=pd.read_parquet(p,columns=['permno','date']);dfs.append(d[d.permno.isin(ps)])
 d=pd.concat(dfs).drop_duplicates(['permno','date']);d.date=pd.to_datetime(d.date);dates={p:sorted(g.date.unique()) for p,g in d.groupby('permno')}
 support=[]
 for rr in r.itertuples(index=False):
  w=rr.wave_id;ann,impl,lo,hi=C[w];ds=[pd.Timestamp(z) for z in dates.get(int(rr.permno),[]) if pd.Timestamp(z)>pd.Timestamp(impl)];thr=ds[19] if len(ds)>=20 else pd.NaT
  z=j[(j.permno==int(rr.permno))&j.anndats.between(lo,hi)].copy();period=z.groupby('pends').agg(release_dates=('anndats',lambda s:sorted(set(s.dropna()))),source_rows=('ticker','size')).reset_index();period['release_date']=period.release_dates.map(lambda q:q[0] if len(q)==1 else pd.NaT)
  pre=period[period.release_date<pd.Timestamp(ann)];post=period[period.release_date>=thr] if pd.notna(thr) else period.iloc[0:0]
  support.append({'permno':int(rr.permno),'wave_id':w,'pre_unique_periods':len(pre),'post_unique_periods':len(post),'ambiguous_periods':int(period.release_date.isna().sum()),'post_20_session_threshold':thr.strftime('%Y-%m-%d') if pd.notna(thr) else '', 'has_8pre_4post':len(pre)>=8 and len(post)>=4})
 s=pd.DataFrame(support);x=r.merge(s,on=['permno','wave_id'],validate='one_to_one');selected=[];tiers=[]
 for w,g in x.groupby('wave_id'):
  q1=ecdf(g.ownership_common_basis_candidate,1/3);q2=ecdf(g.ownership_common_basis_candidate,2/3);g=g.copy();g['tier']=g.ownership_common_basis_candidate.map(lambda v:'LOW' if v<=q1 else ('HIGH' if v>q2 else 'MIDDLE'))
  for tier in ['LOW','HIGH']:
   t=g[g.tier==tier].copy();med=t.liquidity_median_dollar_volume_pre250_21.median();t['liquidity_stratum']=t.liquidity_median_dollar_volume_pre250_21.map(lambda v:'LOW_LIQ' if v<=med else 'HIGH_LIQ');ok=t[t.has_8pre_4post].copy();p=[]
   for ls in ['LOW_LIQ','HIGH_LIQ']:
    z=ok[ok.liquidity_stratum==ls].sort_values(['ownership_common_basis_candidate','permno'],ascending=[tier=='LOW',True]).head(2);p.append(z)
   z=pd.concat(p);selected.append(z);tiers.append({'wave_id':w,'tier':tier,'all_tier':len(t),'complete_8pre4post':len(ok),'q1':q1,'q2':q2,'liquidity_median':med,'selected':len(z)})
 out=pd.concat(selected,ignore_index=True);out['purpose']='SUPPORTED_DATA_ACQUISITION_ROSTER_ONLY';out['final_analysis_eligibility']='NOT_CERTIFIED';out.to_csv(OUT/'PILOT_STOCKS_40_SUPPORTED.csv',index=False);x.to_csv(OUT/'ALL_CANDIDATE_EVENT_SUPPORT.csv',index=False);pd.DataFrame(tiers).to_csv(OUT/'TIER_SUPPORT.csv',index=False)
 receipt={'status':'SUPPORTED_40_ROSTER_BUILT' if len(out)==40 else 'INSUFFICIENT_SUPPORTED_ROSTER','selected_rows':len(out),'waves':out.wave_id.nunique(),'unique_permnos':out.permno.nunique(),'all_candidate_rows':len(x),'candidates_with_8pre4post':int(x.has_8pre_4post.sum()),'roster_sha256':sha(OUT/'PILOT_STOCKS_40_SUPPORTED.csv'),'support_sha256':sha(OUT/'ALL_CANDIDATE_EVENT_SUPPORT.csv'),'response_values_read':False,'actual_eps_values_read':False}
 (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
