#!/usr/bin/env python3
from pathlib import Path
import argparse, hashlib, json
import pandas as pd

PAIR_COLS=['candidate_id','wave_id_focal','provisional_tier','permno','other_wave_id','candidate_other_wave_pair_key']
MAP_COLS=['permno','wave_id','event_id','pre_series_id']
FACT_COLS=['wave_id','pre_series_id','package_id','package_role','package_membership_status','announcement_lower_bound_date','announcement_upper_bound_date','implementation_lower_bound_date','implementation_upper_bound_date','implementation_bound_status']

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def interval_relation(a_lo,a_hi,i_lo,i_hi):
    """Robust relation using whole-day intervals and the approved overlap wording."""
    vals=pd.to_datetime([a_lo,a_hi,i_lo,i_hi],errors='coerce')
    if vals.isna().any(): return 'UNKNOWN_MISSING_BOUND'
    al,ah,il,ih=vals; ah=ah+pd.Timedelta(days=1); ih=ih+pd.Timedelta(days=1)
    # Contract excludes an observed other conversion before OR inside the window.
    if ih <= al-pd.DateOffset(months=24):
        return 'ROBUST_EXCLUSION_CONDITION_BEFORE_ANALYSIS_WINDOW'
    if il >= ah-pd.DateOffset(months=24) and ih <= al+pd.DateOffset(months=24):
        return 'ROBUST_EXCLUSION_CONDITION_INSIDE_ANALYSIS_WINDOW'
    if ih <= al+pd.DateOffset(months=24):
        return 'ROBUST_EXCLUSION_CONDITION_SPANS_BEFORE_TO_INSIDE_BOUNDARY'
    if il >= ah+pd.DateOffset(months=24):
        return 'ROBUSTLY_AFTER_WINDOW_NO_EXCLUSION_FROM_THIS_OBSERVED_LINK'
    return 'UNKNOWN_BOUNDARY_CROSSES_SUPPORTED_INTERVAL'

def build(pairs,mapping,facts):
    pairs=pairs[PAIR_COLS].drop_duplicates().copy()
    real=pairs[pairs.other_wave_id.ne('NO_OTHER_WAVE_MATCH')].copy()
    none=pairs[pairs.other_wave_id.eq('NO_OTHER_WAVE_MATCH')].copy()
    mapping=mapping[MAP_COLS].drop_duplicates()
    facts=facts[FACT_COLS].drop_duplicates()
    joined=real.merge(mapping,left_on=['permno','other_wave_id'],right_on=['permno','wave_id'],how='left',validate='many_to_many')
    joined=joined.merge(facts,left_on=['other_wave_id','pre_series_id'],right_on=['wave_id','pre_series_id'],how='left',suffixes=('','_fact'),validate='many_to_one')
    focal=facts[facts.package_role.isin(['FOCAL_MAIN','FOCAL_STRESS'])].groupby('wave_id',as_index=False).agg(
        focal_A_lower=('announcement_lower_bound_date','min'),focal_A_upper=('announcement_upper_bound_date','min'))
    focal=focal.rename(columns={'wave_id':'focal_wave_key'})
    joined=joined.merge(focal,left_on='wave_id_focal',right_on='focal_wave_key',how='left',validate='many_to_one')
    joined['series_membership_status']='EXACT_PERMNO_WAVE_TO_PREDECESSOR_SERIES_MEMBERSHIP'
    joined.loc[joined.pre_series_id.isna(),'series_membership_status']='UNKNOWN_NO_EXACT_SERIES_MEMBERSHIP_IN_PINNED_MAPPING'
    joined['window_relation']=joined.apply(lambda r: interval_relation(r.focal_A_lower,r.focal_A_upper,r.implementation_lower_bound_date,r.implementation_upper_bound_date),axis=1)
    none['series_membership_status']='UNKNOWN_NO_OTHER_WAVE_MATCH_IN_VERSIONED_EXPOSURE_SOURCE'
    none['window_relation']='UNKNOWN_NO_OTHER_WAVE_MATCH_IN_VERSIONED_EXPOSURE_SOURCE'
    for c in joined.columns:
        if c not in none: none[c]=pd.NA
    out=pd.concat([joined,none[joined.columns]],ignore_index=True)
    return out.sort_values(['wave_id_focal','provisional_tier','candidate_id','other_wave_id','package_id','pre_series_id'],na_position='last')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--pairs',required=True);ap.add_argument('--mapping',required=True);ap.add_argument('--facts',required=True);ap.add_argument('--outdir',required=True);ap.add_argument('--mode',choices=['pilot','full'],required=True);ap.add_argument('--gate-token')
    a=ap.parse_args(); od=Path(a.outdir);od.mkdir(parents=True,exist_ok=True)
    if a.mode=='full':
        assert a.gate_token, 'full mode requires gate token'
        t=json.load(open(a.gate_token)); assert t['status']=='FULL_GATE_AUTHORIZED'
        assert t['contract_sha256']=='00af7d39fd51e9c3c6a9051036f26a68b337f2132848368a729ff8a70d32663f'
        assert t['sha256']=={'code':sha(__file__),'facts':sha(a.facts),'mapping':sha(a.mapping),'full_pairs':sha(a.pairs)}
    pairs=pd.read_csv(a.pairs,usecols=PAIR_COLS,dtype=str); pairs['permno']=pd.to_numeric(pairs.permno,errors='raise').astype(int)
    mapping=pd.read_csv(a.mapping,usecols=MAP_COLS,dtype=str); mapping['permno']=pd.to_numeric(mapping.permno,errors='raise').astype(int)
    facts=pd.read_csv(a.facts,usecols=FACT_COLS,dtype=str)
    out=build(pairs,mapping,facts)
    protected=od/'protected_candidate_package_membership.csv'; out.to_csv(protected,index=False)
    pair=out.groupby(['candidate_id','wave_id_focal','provisional_tier','other_wave_id','candidate_other_wave_pair_key'],dropna=False).agg(
        series_membership_rows=('pre_series_id','count'),packages=('package_id','nunique'),
        robust_exclusion=('window_relation',lambda x:int(x.str.startswith('ROBUST_EXCLUSION_CONDITION').any())),
        unknown_relation=('window_relation',lambda x:int(x.str.startswith('UNKNOWN').any()))).reset_index()
    pair['pair_fact_status']='OBSERVED_LINK_OUTSIDE_SUPPORTED_WINDOW'
    pair.loc[pair.unknown_relation.eq(1),'pair_fact_status']='UNKNOWN_INCOMPLETE_OR_BOUNDARY_EVIDENCE'
    pair.loc[pair.robust_exclusion.eq(1),'pair_fact_status']='OBSERVED_OTHER_CONVERSION_CONTRACT_EXCLUSION_CONDITION_MET'
    pair_agg=pair.groupby(['wave_id_focal','provisional_tier','other_wave_id','pair_fact_status'],as_index=False).agg(candidate_other_wave_pairs=('candidate_other_wave_pair_key','nunique'),unique_candidates=('candidate_id','nunique'))
    series_agg=out[out.other_wave_id.ne('NO_OTHER_WAVE_MATCH')].groupby(['wave_id_focal','provisional_tier','other_wave_id','package_id','series_membership_status','window_relation'],dropna=False,as_index=False).agg(candidate_other_wave_pairs=('candidate_other_wave_pair_key','nunique'),unique_candidates=('candidate_id','nunique'),candidate_pair_series_rows=('pre_series_id','size'))
    pair_agg.to_csv(od/'candidate_pair_fact_aggregate.csv',index=False);series_agg.to_csv(od/'candidate_pair_series_aggregate.csv',index=False)
    inv={'input_candidate_count_expected':pairs.candidate_id.nunique()==(99 if a.mode=='full' else 20),'input_pairs_unique':not pairs.duplicated(['candidate_id','other_wave_id']).any(),'pair_reconciliation':len(pair)==len(pairs),'no_clean_flag_emitted':'clean' not in '|'.join(out.columns).lower()}
    if a.mode=='full': inv.update({'input_pair_rows_120':len(pairs)==120,'real_pairs_45':pairs.other_wave_id.ne('NO_OTHER_WAVE_MATCH').sum()==45,'no_match_candidates_75':pairs.loc[pairs.other_wave_id.eq('NO_OTHER_WAVE_MATCH'),'candidate_id'].nunique()==75})
    assert all(inv.values())
    rec={'status':'PROTECTED_MEMBERSHIP_SIDECAR_COMPLETE','mode':a.mode,'code_sha256':sha(__file__),'contract_sha256':'00af7d39fd51e9c3c6a9051036f26a68b337f2132848368a729ff8a70d32663f','counts':{'candidate_denominator':int(pairs.candidate_id.nunique()),'candidate_other_wave_pairs_including_no_match':len(pair),'real_candidate_other_wave_pairs':int(pair.other_wave_id.ne('NO_OTHER_WAVE_MATCH').sum()),'protected_candidate_pair_series_rows':len(out),'exact_series_membership_rows':int(out.series_membership_status.str.startswith('EXACT').sum()),'robust_contract_exclusion_condition_candidate_pairs':int(pair.robust_exclusion.sum()),'unknown_candidate_pairs':int(pair.unknown_relation.sum())},'invariants':{k:bool(v) for k,v in inv.items()},'input_sha256':{x:sha(x) for x in [a.pairs,a.mapping,a.facts]},'output_sha256':{str(protected):sha(protected),str(od/'candidate_pair_fact_aggregate.csv'):sha(od/'candidate_pair_fact_aggregate.csv'),str(od/'candidate_pair_series_aggregate.csv'):sha(od/'candidate_pair_series_aggregate.csv')},'protected_rows_local_exported':False,'interpretation':'Observed other conversion robustly before or inside the contract window satisfies the exclusion condition. An additional unknown constituent does not erase that positive fact. No-match/after rows are not certified clean because the versioned calendar is incomplete.'}
    (od/'PROTECTED_SIDECAR_RECEIPT.json').write_text(json.dumps(rec,indent=2)+'\n')
if __name__=='__main__': main()
