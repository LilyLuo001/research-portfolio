#!/usr/bin/env python3
import pandas as pd
from run_other_wave_join import build_pairs

c=pd.DataFrame([['A','W1','high',1],['B','W2','low',2]],columns=['candidate_id','wave_id','provisional_tier','permno'])
e=pd.DataFrame([[1,'W1','2020-01-01'],[1,'W3','2021-01-01'],[1,'W3','2021-01-01'],[1,'W4','2022-01-01'],[1,'W5','2023-01-01'],[1,'W6',pd.NA]],columns=['permno','wave_id','effective_date'])
u=pd.DataFrame([['W3','2021-01-01','Adv','S1','Fund','P1','ETF','PASS'],['W3','2021-01-01','Adv','S2','Fund2','P2','ETF2','PASS'],['W4','2020-01-01','Adv4','S4','Fund4','P4','ETF4','PASS'],['W6',pd.NA,pd.NA,'S6','Fund6','P6','ETF6','PASS']],columns=['wave_id','effective_date','adviser','pre_series_id','pre_series_name','post_series_id','post_series_name','gate0'])
p=build_pairs(c,e,u)
assert len(p)==5
assert set(p[p.candidate_id.eq('A')].other_wave_id)=={'W3','W4','W5','W6'}
assert p[p.candidate_id.eq('B')].other_wave_id.item()=='NO_OTHER_WAVE_MATCH'
assert p[p.other_wave_id.eq('W3')].public_pre_series_count.item()==2
assert p[p.other_wave_id.eq('W3')].public_metadata_relation.item()=='AT_LEAST_ONE_EXACT_EFFECTIVE_DATE_MATCH'
assert p[p.other_wave_id.eq('W4')].public_metadata_relation.item()=='WAVE_PRESENT_EFFECTIVE_DATE_CONFLICT_RETAINED'
assert p[p.other_wave_id.eq('W5')].public_metadata_relation.item()=='OTHER_WAVE_MISSING_FROM_PUBLIC_UNIVERSE_METADATA'
assert p[p.other_wave_id.eq('W5')].sponsor_provenance_status.item()=='MISSING_ADVISER_METADATA_UNKNOWN'
assert p[p.other_wave_id.eq('W6')].public_metadata_relation.item()=='UNKNOWN_EFFECTIVE_DATE_IN_ONE_OR_BOTH_SOURCES'
assert p[p.other_wave_id.eq('W6')].sponsor_provenance_status.item()=='MISSING_ADVISER_METADATA_UNKNOWN'
assert p.candidate_other_wave_pair_key.nunique()==5
assert not p.duplicated(['candidate_id','other_wave_id']).any()
assert p.competing_conversion_inference_status.eq('NOT_ASSESSED_NO_CLEAN_EXCLUDE_INFERENCE').all()
print('{"status":"PASS","fixture_count":13}')
