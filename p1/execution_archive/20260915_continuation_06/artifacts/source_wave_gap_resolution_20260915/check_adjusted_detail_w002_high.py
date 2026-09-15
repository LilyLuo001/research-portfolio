#!/usr/bin/env python3
"""Bounded W002-high four-key check against the separate adjusted detail archive."""
import collections, hashlib, json
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq

TARGETS=Path('/projectnb/econdept/qluo/P1_Refraction_WRDS/pilot_uncapped_metadata_20260915/corrected_v2/full_run_v2/protected_metadata_paths.csv')
RAW=Path('/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared/raw/rescue')
FILES=[RAW/f'ibes_allcols_det_epsus_{y}.parquet' for y in (2019,2020,2021)]
OUTPUT=Path('/projectnb/econdept/qluo/P1_Refraction_WRDS/source_wave_gap_resolution_20260915/adjusted_detail_w002_high_receipt.json')

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

d=pd.read_csv(TARGETS,dtype=str)
z=d[d.wave_id.isin(['W002','W016']) & d.event_side.isin(['PRE','POST']) & d.overlap_status.eq('PROPOSED_CLEAN_TRUE') & d.source_permno_mapping_status.eq('UNIQUE_VALID_PERMNO') & d.nominal_0930_1500_source_clock.eq('True')].copy()
both=z.groupby('candidate_id').event_side.nunique(); z=z[z.candidate_id.isin(both[both.eq(2)].index)].copy()
z['event_key']=z.apply(lambda r:f"{r.wave_id}|{r.provisional_tier}|{int(r.permno)}|{r.event_side}|{r.pends}|{r.anndats}",axis=1)
keys=['event_key','candidate_id','wave_id','permno','provisional_tier','event_side','pends','anndats']
e=z.groupby(keys,dropna=False).agg(cusip=('cusip','first'),cusip_variants=('cusip','nunique')).reset_index()
e=e[(e.wave_id=='W002') & e.provisional_tier.str.lower().eq('high')]
assert len(e)==4 and e.candidate_id.nunique()==1 and (e.event_side=='PRE').sum()==3 and (e.event_side=='POST').sum()==1 and e.cusip_variants.eq(1).all()

frames=[]
for p in FILES:
    frames.append(pq.read_table(p,columns=['cusip','fpedats','analys','anndats']).to_pandas())
t=pd.concat(frames,ignore_index=True); t.cusip=t.cusip.astype(str).str.strip().str.upper(); t.fpedats=pd.to_datetime(t.fpedats); t.anndats=pd.to_datetime(t.anndats)
counts=[]
for r in e.itertuples():
    rel=pd.Timestamp(r.anndats)
    q=t[(t.cusip==str(r.cusip).upper()) & (t.fpedats==pd.Timestamp(r.pends)) & (t.anndats>=rel-pd.Timedelta(days=90)) & (t.anndats<rel)]
    counts.append({'side':r.event_side,'rows':len(q),'analysts':int(q.analys.dropna().astype(str).nunique())})
by_side={}
for side in ['PRE','POST']:
    a=[x for x in counts if x['side']==side]
    by_side[side]={'keys':len(a),'observed_min2_keys':sum(x['analysts']>=2 for x in a),'observed_lt2_keys':sum(x['analysts']<2 for x in a),'matched_keys':sum(x['rows']>0 for x in a),'rows_in_windows':sum(x['rows'] for x in a),'analyst_count_histogram':dict(collections.Counter(x['analysts'] for x in a))}
out={'status':'ADJUSTED_DETAIL_W002_HIGH_FOUR_KEY_CHECK_COMPLETE','source_family':'RESCUE_ALLCOLS_DET_EPSUS_SEPARATE_NOT_POOLED','target':{'event_keys':4,'candidate_keys':1,'PRE':3,'POST':1},'pilot':{'definition':'first deterministic target key evaluated within same bounded source pass','executed':True,'key_count':1},'rules':{'columns':['cusip','fpedats','analys','anndats'],'window':'[release_date-90 days,release_date)','distinct_analyst_ids':True,'pooling':False},'by_side':by_side,'total':{'matched_keys':sum(x['rows']>0 for x in counts),'rows_in_windows':sum(x['rows'] for x in counts),'analyst_count_histogram':dict(collections.Counter(x['analysts'] for x in counts))},'source_manifest':[{'path':str(p),'bytes':p.stat().st_size,'sha256':'NOT_REHASHED_LARGE_ARCHIVE_EXISTING_LOCATOR_PROVENANCE'} for p in FILES],'targets_sha256':sha(TARGETS),'code_sha256':sha(Path(__file__)),'interpretation':'OBSERVED_ANALYST_ID_LOWER_BOUND_ONLY_SOURCE_COMPLETENESS_NOT_CERTIFIED_NOT_SUE','raw_values_read':False,'protected_rows_exported_local':False,'backend_telemetry':'NOT_OBSERVED'}
OUTPUT.parent.mkdir(parents=True,exist_ok=True)
OUTPUT.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'status':out['status'],'receipt':str(OUTPUT),'total':out['total']}))
