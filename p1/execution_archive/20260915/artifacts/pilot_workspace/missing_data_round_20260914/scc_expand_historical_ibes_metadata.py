#!/usr/bin/env python3
"""Project the 1,696 previously omitted historical-CUSIP metadata rows.

This completes the identifier-envelope retrieval requested by the original P1
metadata package.  It is kept separate from the old v2 projection.  No EPS
value or forecast value is read or exported.
"""
import hashlib,json
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq
ROOT=Path('/projectnb/econdept/qluo/P1_Refraction_WRDS')
RAW=ROOT/'WRDS_MIRROR_20260902/p1_refraction_wrds_shared/raw'
SEED=ROOT/'p1_roster_earnings_20260913/event_calendar_v1/run_v2/new_historical_cusip_delta.csv'
OUT=ROOT/'missing_data_round_20260914/historical_ibes_delta'
EXPECTED='e244a0e402a732d60930242d0203da0456bd40be257df4268765372d48ef303f'
COLS=['ticker','cusip','pends','pdicity','anndats','anntims','actdats','acttims']
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 if sha(SEED)!=EXPECTED:raise ValueError('historical CUSIP delta changed')
 if OUT.exists():raise FileExistsError('preserve prior output')
 OUT.mkdir(parents=True)
 s=pd.read_csv(SEED,dtype=str);cs=set(s.ncusip.str.strip().str.upper())
 if len(cs)!=1696:raise ValueError(f'expected 1696, got {len(cs)}')
 frames=[];inputs=[]
 for y in range(2019,2027):
  p=RAW/f'ibes_actuals_eps_{y}.parquet'
  if not p.exists():inputs.append({'path':str(p),'status':'MISSING'});continue
  if any(c not in pq.read_schema(p).names for c in COLS):raise ValueError(f'schema mismatch {p}')
  x=pd.read_parquet(p,columns=COLS);allrows=len(x);x['cusip']=x.cusip.astype('string').str.strip().str.upper();x=x[x.cusip.isin(cs)].copy();x['source_partition']=p.name;frames.append(x);inputs.append({'path':str(p),'sha256':sha(p),'projected_rows':allrows,'selected_rows':len(x)})
 out=pd.concat(frames,ignore_index=True);p=OUT/'ibes_announcement_metadata_historical_delta.csv';out.to_csv(p,index=False)
 receipt={'status':'HISTORICAL_CUSIP_DELTA_PROJECTED','seed_cusips':len(cs),'source_records':len(out),'matched_cusips':out.cusip.nunique(),'unmatched_cusips':len(cs-set(out.cusip.dropna())),'seed_sha256':EXPECTED,'output_sha256':sha(p),'inputs':inputs,'columns':list(out.columns),'economic_event_count':None,'timezone':'UNVERIFIED','financial_values_read':False,'response_outcomes_read':False}
 (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
