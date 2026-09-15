import pandas as pd,pyarrow.parquet as pq,collections,json
p='/projectnb/econdept/qluo/P1_Refraction_WRDS/pilot_uncapped_metadata_20260915/corrected_v2/full_run_v2/protected_metadata_paths.csv'; d=pd.read_csv(p,dtype=str)
cfg={'target_waves':['W002','W016'],'target_event_sides':['PRE','POST'],'target_overlap_status':'PROPOSED_CLEAN_TRUE'}
z=d[d.wave_id.isin(cfg['target_waves'])&d.event_side.isin(cfg['target_event_sides'])&d.overlap_status.eq(cfg['target_overlap_status'])&d.source_permno_mapping_status.eq('UNIQUE_VALID_PERMNO')&d.nominal_0930_1500_source_clock.eq('True')].copy(); both=z.groupby('candidate_id').event_side.nunique(); z=z[z.candidate_id.isin(both[both.eq(2)].index)].copy(); z['event_key']=z.apply(lambda r:f"{r.wave_id}|{r.provisional_tier}|{int(r.permno)}|{r.event_side}|{r.pends}|{r.anndats}",axis=1); keys=['event_key','candidate_id','wave_id','permno','provisional_tier','event_side','pends','anndats']; e=z.groupby(keys,dropna=False).agg(cusip=('cusip','first'),cusip_variants=('cusip','nunique')).reset_index(); e=e[(e.wave_id=='W002')&e.provisional_tier.str.lower().eq('high')]; assert len(e)==4 and e.candidate_id.nunique()==1 and (e.event_side=='PRE').sum()==3 and (e.event_side=='POST').sum()==1 and e.cusip_variants.eq(1).all()
base='/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared/raw'; out={'selector':'EXACT_EXISTING_SELECT_TARGETS','target_event_keys':4,'pre':3,'post':1,'candidate_keys':1,'sources':{}}
for fam,ps in [('core',[f'{base}/ibes_detu_eps_{y}.parquet' for y in (2019,2020,2021)]),('rescue',[f'{base}/rescue/ibes_allcols_detu_epsus_{y}.parquet' for y in (2019,2020,2021)])]:
 rows=[]
 for pth in ps:
  t=pq.read_table(pth,columns=['cusip','fpedats','analys','anndats']).to_pandas(); rows.append(t)
 t=pd.concat(rows); t.cusip=t.cusip.astype(str).str.strip().str.upper(); t.fpedats=pd.to_datetime(t.fpedats); t.anndats=pd.to_datetime(t.anndats); counts=[]
 for r in e.itertuples():
  rel=pd.Timestamp(r.anndats); q=t[(t.cusip==str(r.cusip).upper())&(t.fpedats==pd.Timestamp(r.pends))&(t.anndats>=rel-pd.Timedelta(days=90))&(t.anndats<rel)]; counts.append({'rows':len(q),'analysts':int(q.analys.dropna().astype(str).nunique())})
 out['sources'][fam]={'per_key_aggregate':counts,'matched_keys':sum(x['rows']>0 for x in counts),'total_rows':sum(x['rows'] for x in counts),'distinct_analyst_histogram':dict(collections.Counter(x['analysts'] for x in counts))}
print(json.dumps(out))
