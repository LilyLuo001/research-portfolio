#!/usr/bin/env python3
"""Exact recovered99 x other-wave metadata join; no conversion inference."""
from pathlib import Path
import argparse, hashlib, json
import pandas as pd

CAND_COLS=['candidate_id','wave_id','provisional_tier','permno']
EXP_COLS=['permno','wave_id','effective_date']
UNI_COLS=['wave_id','effective_date','adviser','pre_series_id','pre_series_name','post_series_id','post_series_name','gate0']

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def vals(s): return ';'.join(sorted(set(str(x) for x in s.dropna() if str(x))))

def verify_manifest(path):
    m=json.load(open(path))
    for x in m['inputs']:
        p=Path(x['path'])
        if not p.exists(): raise ValueError(f'missing input {p}')
        if x['verification']=='sha256' and sha(p)!=x['sha256']: raise ValueError(f'hash mismatch {p}')
    return m

def aggregate_universe(u):
    return u.groupby('wave_id',dropna=False).agg(public_universe_effective_dates=('effective_date',vals),adviser_labels=('adviser',vals),pre_series_ids=('pre_series_id',vals),pre_series_names=('pre_series_name',vals),post_series_ids=('post_series_id',vals),post_series_names=('post_series_name',vals),gate0_statuses=('gate0',vals),public_fund_series_rows=('pre_series_id','size'),public_pre_series_count=('pre_series_id','nunique'),public_post_series_count=('post_series_id','nunique')).reset_index().rename(columns={'wave_id':'other_wave_id'})

def relation(r):
    if r.other_wave_id=='NO_OTHER_WAVE_MATCH': return 'NOT_APPLICABLE_NO_OTHER_WAVE_MATCH'
    if pd.isna(r.public_universe_effective_dates): return 'OTHER_WAVE_MISSING_FROM_PUBLIC_UNIVERSE_METADATA'
    a={x for x in str(r.other_effective_dates).split(';') if x and x.lower() not in {'nan','nat','<na>'}}
    b={x for x in str(r.public_universe_effective_dates).split(';') if x and x.lower() not in {'nan','nat','<na>'}}
    if not a or not b: return 'UNKNOWN_EFFECTIVE_DATE_IN_ONE_OR_BOTH_SOURCES'
    return 'AT_LEAST_ONE_EXACT_EFFECTIVE_DATE_MATCH' if a & b else 'WAVE_PRESENT_EFFECTIVE_DATE_CONFLICT_RETAINED'

def build_pairs(c,e,u):
    c=c.copy(); e=e.copy(); u=u.copy()
    c['permno']=pd.to_numeric(c.permno,errors='raise').astype(int); e['permno']=pd.to_numeric(e.permno,errors='raise').astype(int)
    x=c.merge(e,on='permno',how='left',suffixes=('_focal','_other'),validate='many_to_many')
    x=x[x.wave_id_other.notna() & x.wave_id_other.ne(x.wave_id_focal)].copy()
    pairs=x.groupby(['candidate_id','wave_id_focal','provisional_tier','permno','wave_id_other'],dropna=False).agg(other_effective_dates=('effective_date',vals),exposure_source_rows=('effective_date','size'),distinct_other_effective_dates=('effective_date','nunique')).reset_index().rename(columns={'wave_id_other':'other_wave_id'})
    present=set(pairs.candidate_id); missing=c[~c.candidate_id.isin(present)].copy().rename(columns={'wave_id':'wave_id_focal'})
    missing['other_wave_id']='NO_OTHER_WAVE_MATCH'; missing['other_effective_dates']=pd.NA; missing['exposure_source_rows']=0; missing['distinct_other_effective_dates']=0
    pairs=pd.concat([pairs,missing[pairs.columns]],ignore_index=True)
    pairs=pairs.merge(aggregate_universe(u),on='other_wave_id',how='left',validate='many_to_one')
    pairs['public_metadata_relation']=pairs.apply(relation,axis=1)
    pairs['sponsor_provenance_status']='ADVISER_ONLY_NOT_SIGNED_ECONOMIC_SPONSOR'
    pairs.loc[pairs.adviser_labels.isna()|pairs.adviser_labels.eq(''),'sponsor_provenance_status']='MISSING_ADVISER_METADATA_UNKNOWN'
    pairs.loc[pairs.other_wave_id.eq('NO_OTHER_WAVE_MATCH'),'sponsor_provenance_status']='NOT_APPLICABLE_NO_OTHER_WAVE_MATCH'
    pairs['announcement_provenance_status']=pairs.other_wave_id.eq('NO_OTHER_WAVE_MATCH').map({True:'NOT_APPLICABLE_NO_OTHER_WAVE_MATCH',False:'PRIMARY_PUBLIC_ANNOUNCEMENT_BOUND_NOT_ATTACHED_UNKNOWN'})
    pairs['implementation_provenance_status']=pairs.other_wave_id.eq('NO_OTHER_WAVE_MATCH').map({True:'NOT_APPLICABLE_NO_OTHER_WAVE_MATCH',False:'EFFECTIVE_DATE_METADATA_ONLY_RULE_CORRECT_IW_UNKNOWN'})
    pairs['competing_conversion_inference_status']='NOT_ASSESSED_NO_CLEAN_EXCLUDE_INFERENCE'
    pairs['candidate_other_wave_pair_key']=pairs.candidate_id+'|'+pairs.other_wave_id
    assert not pairs.duplicated(['candidate_id','other_wave_id']).any()
    assert set(pairs.candidate_id)==set(c.candidate_id)
    return pairs.sort_values(['wave_id_focal','provisional_tier','candidate_id','other_wave_id']).reset_index(drop=True)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mode',choices=['pilot','full'],required=True); ap.add_argument('--config',required=True); ap.add_argument('--manifest',required=True); ap.add_argument('--out',required=True); ap.add_argument('--gate'); ap.add_argument('--pilot-receipt'); a=ap.parse_args()
    code_h,config_h,manifest_h=sha(__file__),sha(a.config),sha(a.manifest)
    if a.mode=='full':
        if not a.gate or not a.pilot_receipt: raise ValueError('gate and pilot receipt required before source read')
        expected={'status':'OTHER_WAVE_JOIN_PILOT_PASS','code_sha256':code_h,'config_sha256':config_h,'manifest_sha256':manifest_h,'pilot_receipt_sha256':sha(a.pilot_receipt),'required_invariants_passed':True}
        if json.load(open(a.gate))!=expected: raise ValueError('gate mismatch before source read')
    cfg=json.load(open(a.config)); verify_manifest(a.manifest)
    out=Path(a.out)
    if out.exists(): raise FileExistsError(out)
    out.mkdir(parents=True)
    c=pd.read_csv(cfg['protected_recovered99_sidecar'],usecols=CAND_COLS,dtype=str).drop_duplicates(CAND_COLS)
    if c.candidate_id.nunique()!=cfg['expected_candidate_denominator']: raise ValueError('candidate denominator mismatch')
    if c.groupby('candidate_id').size().max()!=1: raise ValueError('candidate identity not one-to-one')
    if a.mode=='pilot': c=c.sort_values('candidate_id').head(20).copy()
    e=pd.read_csv(cfg['exposure_projection'],usecols=EXP_COLS,dtype=str); u=pd.read_csv(cfg['public_universe_projection'],usecols=UNI_COLS,dtype=str)
    source_waves=sorted(e.wave_id.dropna().unique()); universe_waves=sorted(u.wave_id.dropna().unique())
    pairs=build_pairs(c,e,u); pairs.to_csv(out/'protected_candidate_other_wave_sidecar.csv',index=False,lineterminator='\n')
    real=pairs[pairs.other_wave_id.ne('NO_OTHER_WAVE_MATCH')]
    focal=pairs.groupby(['wave_id_focal','provisional_tier']).agg(focal_candidate_denominator=('candidate_id','nunique'),candidates_with_any_other_wave_match=('candidate_id',lambda s:s[pairs.loc[s.index,'other_wave_id'].ne('NO_OTHER_WAVE_MATCH')].nunique()),no_other_wave_match_candidates=('candidate_id',lambda s:s[pairs.loc[s.index,'other_wave_id'].eq('NO_OTHER_WAVE_MATCH')].nunique()),candidate_other_wave_pairs=('other_wave_id',lambda s:int(s.ne('NO_OTHER_WAVE_MATCH').sum())),distinct_matched_other_waves=('other_wave_id',lambda s:s[s.ne('NO_OTHER_WAVE_MATCH')].nunique())).reset_index()
    detail=pairs.groupby(['wave_id_focal','provisional_tier','other_wave_id','public_metadata_relation','sponsor_provenance_status','announcement_provenance_status','implementation_provenance_status','competing_conversion_inference_status'],dropna=False).agg(unique_focal_candidates=('candidate_id','nunique'),candidate_other_wave_pair_units=('candidate_other_wave_pair_key','nunique')).reset_index()
    other=real.groupby(['other_wave_id','public_metadata_relation'],dropna=False).agg(unique_focal_candidates=('candidate_id','nunique'),candidate_other_wave_pair_units=('candidate_other_wave_pair_key','nunique'),focal_waves=('wave_id_focal',vals),adviser_labels=('adviser_labels','first'),public_pre_series_count=('public_pre_series_count','first'),public_post_series_count=('public_post_series_count','first'),other_effective_dates=('other_effective_dates',vals),public_universe_effective_dates=('public_universe_effective_dates','first')).reset_index()
    source=pd.DataFrame([{'source_version':cfg['source_version'],'metadata_rows':len(e),'observed_wave_count':len(source_waves),'observed_wave_ids':';'.join(source_waves),'meaning':'OTHER_WAVE_MATCH_UNIVERSE_VERSION_NOT_COMPLETE_CONVERSION_CALENDAR'},{'source_version':cfg['public_universe_version'],'metadata_rows':len(u),'observed_wave_count':len(universe_waves),'observed_wave_ids':';'.join(universe_waves),'meaning':'PUBLIC_FUND_SERIES_METADATA_VERSION'}])
    focal.to_csv(out/'matches_by_focal_wave_tier.csv',index=False,lineterminator='\n'); detail.to_csv(out/'matches_by_focal_wave_tier_other_wave.csv',index=False,lineterminator='\n'); other.to_csv(out/'matched_other_wave_metadata_coverage.csv',index=False,lineterminator='\n'); source.to_csv(out/'source_version_wave_coverage.csv',index=False,lineterminator='\n')
    detail_real_units=int(detail.loc[detail.other_wave_id.ne('NO_OTHER_WAVE_MATCH'),'candidate_other_wave_pair_units'].sum())
    detail_no_match_units=int(detail.loc[detail.other_wave_id.eq('NO_OTHER_WAVE_MATCH'),'candidate_other_wave_pair_units'].sum())
    inv={'exact_candidate_denominator_preserved':pairs.candidate_id.nunique()==len(c),'no_match_candidates_retained':set(c.candidate_id)==set(pairs.candidate_id) and detail_no_match_units==c.candidate_id.nunique()-real.candidate_id.nunique(),'candidate_other_wave_pairs_unique':not real.duplicated(['candidate_id','other_wave_id']).any(),'same_permno_distinct_waves_retained':True,'focal_wave_excluded_by_exact_wave_id_only':True,'fund_series_aggregated_before_candidate_join':True,'missing_public_wave_or_date_conflict_retained':len(real)==detail_real_units,'adviser_not_relabelled_signed_sponsor':True,'clean_or_exclude_inference_made':False,'financial_or_outcome_values_read':False,'protected_rows_local_exported':False}
    expected={**{k:True for k in inv if k not in ['clean_or_exclude_inference_made','financial_or_outcome_values_read','protected_rows_local_exported']},'clean_or_exclude_inference_made':False,'financial_or_outcome_values_read':False,'protected_rows_local_exported':False}
    files=['matches_by_focal_wave_tier.csv','matches_by_focal_wave_tier_other_wave.csv','matched_other_wave_metadata_coverage.csv','source_version_wave_coverage.csv']
    rec={'status':f'RECOVERED99_OTHER_WAVE_PROVENANCE_{a.mode.upper()}_COMPLETE','mode':a.mode,'code_sha256':code_h,'config_sha256':config_h,'manifest_sha256':manifest_h,'focal_candidate_denominator':c.candidate_id.nunique(),'candidate_other_wave_pairs':len(real),'candidates_with_any_other_wave_match':real.candidate_id.nunique(),'candidates_with_no_other_wave_match':c.candidate_id.nunique()-real.candidate_id.nunique(),'matched_other_wave_count':real.other_wave_id.nunique(),'source_version_observed_wave_count':len(source_waves),'source_version_observed_wave_ids':source_waves,'public_universe_observed_wave_count':len(universe_waves),'matched_pairs_missing_public_universe_wave':int(real.public_metadata_relation.eq('OTHER_WAVE_MISSING_FROM_PUBLIC_UNIVERSE_METADATA').sum()),'matched_pairs_effective_date_conflict':int(real.public_metadata_relation.eq('WAVE_PRESENT_EFFECTIVE_DATE_CONFLICT_RETAINED').sum()),'required_invariants':inv,'required_invariant_expectations':expected,'required_invariants_passed':inv==expected,'aggregate_hashes':{f:sha(out/f) for f in files},'competing_conversion_inference':'NOT_ASSESSED','announcement_and_implementation_bounds':'UNKNOWN_NOT_ATTACHED','sponsor_provenance':'ADVISER_ONLY_NOT_SIGNED','outcomes_financial_quotes_power_effects_read_or_estimated':False,'backend_telemetry':'NOT_OBSERVED'}
    (out/'receipt.json').write_text(json.dumps(rec,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:rec[k] for k in ['status','focal_candidate_denominator','candidate_other_wave_pairs','candidates_with_any_other_wave_match','candidates_with_no_other_wave_match','matched_other_wave_count','matched_pairs_missing_public_universe_wave','matched_pairs_effective_date_conflict','required_invariants_passed']}))

if __name__=='__main__': main()
