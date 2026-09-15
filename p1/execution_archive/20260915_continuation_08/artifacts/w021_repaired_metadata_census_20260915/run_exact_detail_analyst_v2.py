#!/usr/bin/env python3
"""Count-only v2: release-time-aware, event-family-separated analyst census."""
import argparse, hashlib, json
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq
W002=[('W002|high|81665|POST|2021-09-30|2021-11-02','37892E10','2021-09-30','2021-11-02'),('W002|high|81665|PRE|2019-09-30|2019-10-29','87185110','2019-09-30','2019-10-29'),('W002|high|81665|PRE|2020-06-30|2020-07-28','87185110','2020-06-30','2020-07-28'),('W002|high|81665|PRE|2020-09-30|2020-10-30','87185110','2020-09-30','2020-10-30')]
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def main():
 a=argparse.ArgumentParser();a.add_argument('--raw',required=True);a.add_argument('--meta',required=True);a.add_argument('--w021',required=True);a.add_argument('--out',required=True);x=a.parse_args();out=Path(x.out)
 if out.exists():raise FileExistsError(out)
 w=pd.read_csv(x.w021,usecols=['event_key','cusip','pends','anndats','anntims']).drop_duplicates();w['scope']='W021'
 q=pd.DataFrame(W002,columns=['event_key','cusip','pends','anndats']);q['scope']='W002_HIGH4'; q['anntims']=pd.NA
 # Resolve W002 release times only from permitted metadata fields; nonunique/missing remains UNKNOWN.
 need=set((r.cusip,r.pends,r.anndats)for r in q.itertuples())
 hit=[]
 for c in pd.read_csv(x.meta,usecols=['cusip','pends','anndats','anntims','pdicity'],dtype=str,chunksize=200000):
  c['cusip']=c.cusip.str.strip().str.upper();hit.append(c[c.pdicity.eq('QTR')&c.apply(lambda r:(r.cusip,r.pends,r.anndats)in need,axis=1)])
 h=pd.concat(hit); t=h.groupby(['cusip','pends','anndats']).anntims.agg(lambda z:sorted(set(z.dropna()))).reset_index()
 q=q.merge(t,on=['cusip','pends','anndats'],how='left',suffixes=('','_resolved'));q['anntims']=q.anntims_resolved.map(lambda z:z[0] if isinstance(z,list)and len(z)==1 else pd.NA);q=q.drop(columns=['anntims_resolved'])
 k=pd.concat([w,q],ignore_index=True);k['cusip']=k.cusip.astype(str).str.strip().str.upper();k['pends_dt']=pd.to_datetime(k.pends);k['release_dt']=pd.to_datetime(k.anndats);k['release_time']=pd.to_datetime(k.anntims,format='%H:%M:%S',errors='coerce');k['release_key']=k.event_key+':'+k.anntims.fillna('UNKNOWN'); years=range((k.release_dt.min()-pd.Timedelta(days=90)).year,k.release_dt.max().year+1)
 out.mkdir(parents=True);detail=[];files=[]
 for fam,tm in [('DIRECT','ibes_detu_eps_{y}.parquet'),('RESCUE_ADJUSTED','rescue/ibes_allcols_detu_epsus_{y}.parquet')]:
  rows=[]
  for y in years:
   p=Path(x.raw)/tm.format(y=y)
   schema=pq.ParquetFile(p).schema.names; cols=[z for z in ['cusip','fpedats','analys','anndats','anntims','measure','usfirm','pdicity','fpi']if z in schema]
   if not {'cusip','fpedats','analys','anndats','anntims','measure'}.issubset(cols):raise ValueError(f'missing required schema {p}')
   d=pd.read_parquet(p,columns=cols);d=d[d.measure.astype(str).str.upper().eq('EPS')];d['cusip']=d.cusip.astype(str).str.strip().str.upper();d['pends_dt']=pd.to_datetime(d.fpedats);d['fdate']=pd.to_datetime(d.anndats);d['ftime']=pd.to_datetime(d.anntims,format='%H:%M:%S',errors='coerce');j=d.merge(k,on=['cusip','pends_dt'],how='inner');prior=j.fdate.lt(j.release_dt);same=j.fdate.eq(j.release_dt);ordered=same&j.ftime.notna()&j.release_time.notna()&(j.ftime<j.release_time);ambig=same&~ordered
   j=j[(j.fdate>=j.release_dt-pd.Timedelta(days=90))&(prior|ordered|ambig)].copy();j['eligible']=prior|ordered;j['ambiguous_same_day']=ambig;rows.append(j);files.append({'family':fam,'year':y,'sha256':sha(p),'schema_status':'AVAILABLE'})
  z=pd.concat(rows,ignore_index=True); 
  for key,g in z.groupby('release_key'):
   for rule,mask in [('EPS_BASE',g.eligible),('EPS_USFIRM1_DIAGNOSTIC',g.eligible&pd.to_numeric(g.usfirm,errors='coerce').eq(1))]:
    n=g.loc[mask,'analys'].dropna().astype(str).nunique(); ambiguous=bool(g.ambiguous_same_day.any());detail.append({'release_key':key,'family':fam,'rule':rule,'distinct_analysts':n,'same_day_ordering_status':'UNKNOWN_PRESENT'if ambiguous else 'RESOLVED_OR_ABSENT'})
 d=pd.DataFrame(detail);base=k[['release_key','event_key','scope']].drop_duplicates();grid=base.merge(pd.DataFrame([('DIRECT','EPS_BASE'),('DIRECT','EPS_USFIRM1_DIAGNOSTIC'),('RESCUE_ADJUSTED','EPS_BASE'),('RESCUE_ADJUSTED','EPS_USFIRM1_DIAGNOSTIC')],columns=['family','rule']),how='cross');o=grid.merge(d,on=['release_key','family','rule'],how='left');o['distinct_analysts']=o.distinct_analysts.fillna(0).astype(int);o['same_day_ordering_status']=o.same_day_ordering_status.fillna('RESOLVED_OR_ABSENT');o['coverage_class']=o.apply(lambda r:'OBSERVED_AT_LEAST_2_LOWER_BOUND'if r.distinct_analysts>=2 else ('UNKNOWN_SAME_DAY_ORDERING'if r.same_day_ordering_status=='UNKNOWN_PRESENT' else ('VERIFIED_ZERO_WITHIN_COMPLETE_SCC_FAMILY'if r.distinct_analysts==0 else 'VERIFIED_LT2_WITHIN_COMPLETE_SCC_FAMILY')),axis=1);o.to_csv(out/'protected_exact_detail_v2.csv',index=False);agg=o.groupby(['scope','family','rule','coverage_class']).agg(event_keys=('release_key','nunique')).reset_index();agg.to_csv(out/'exact_detail_v2_aggregate.csv',index=False);rec={'status':'EXACT_DETAIL_V2_COMPLETE','v1_status':'INVALID_FOR_DECISION','w021_accounting_period_date_keys':int(w.event_key.nunique()),'w021_release_keys':int(k[k.scope.eq('W021')].release_key.nunique()),'w002_high4_keys':4,'reconciliation_event_keys_per_family':int(base.release_key.nunique()),'years':list(years),'files':files,'protected_rows_local_exported':False,'financial_values_read':False,'aggregate_sha256':sha(out/'exact_detail_v2_aggregate.csv')};(out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n')
if __name__=='__main__':main()
