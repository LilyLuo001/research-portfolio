#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib,json
import pandas as pd
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
ap=argparse.ArgumentParser();ap.add_argument('--protected',required=True);ap.add_argument('--outdir',required=True);a=ap.parse_args();od=Path(a.outdir);od.mkdir(parents=True,exist_ok=True)
use=['candidate_id','wave_id_focal','provisional_tier','other_wave_id','candidate_other_wave_pair_key','package_id','pre_series_id','series_membership_status','window_relation']
x=pd.read_csv(a.protected,usecols=use,dtype=str)
p=x.groupby(['candidate_id','wave_id_focal','provisional_tier','other_wave_id','candidate_other_wave_pair_key'],as_index=False).agg(
 any_exclusion=('window_relation',lambda s:s.str.startswith('ROBUST_EXCLUSION_CONDITION').any()),
 any_unknown=('window_relation',lambda s:s.str.startswith('UNKNOWN').any()))
c=p.groupby(['candidate_id','wave_id_focal','provisional_tier'],as_index=False).agg(any_observed_exclusion=('any_exclusion','any'),any_unknown_pair=('any_unknown','any'),real_other_wave_pairs=('other_wave_id',lambda s:s.ne('NO_OTHER_WAVE_MATCH').sum()))
c['candidate_fact_status']='NO_OBSERVED_EXCLUSION_BUT_COMPLETE_CALENDAR_UNKNOWN'
c.loc[c.any_observed_exclusion,'candidate_fact_status']='OBSERVED_OTHER_CONVERSION_CONTRACT_EXCLUSION_CONDITION_MET'
agg=c.groupby(['wave_id_focal','provisional_tier','candidate_fact_status'],as_index=False).agg(candidates=('candidate_id','nunique'))
agg.to_csv(od/'candidate_contract_condition_aggregate.csv',index=False)
w=x[x.other_wave_id.eq('W006')&x.series_membership_status.str.startswith('EXACT')]
wagg=w.groupby(['wave_id_focal','provisional_tier','package_id'],as_index=False).agg(candidate_other_wave_pairs=('candidate_other_wave_pair_key','nunique'),candidate_pair_series_rows=('pre_series_id','size'))
wagg.to_csv(od/'w006_independent_package_aggregate.csv',index=False)
inv={'candidate_denominator_99':c.candidate_id.nunique()==99,'pair_denominator_120':len(p)==120,'exclusion_positive_not_erased_by_unknown':not c[c.any_observed_exclusion].empty,'w006_packages_separate':w.package_id.nunique()==2,'no_candidate_clean_status':not c.candidate_fact_status.str.contains('CLEAN').any()};assert all(inv.values())
r={'status':'PROTECTED_RESULT_SUMMARY_COMPLETE','counts':{'candidates':int(c.candidate_id.nunique()),'candidate_pairs':len(p),'candidates_with_observed_contract_exclusion_condition':int(c.any_observed_exclusion.sum()),'candidates_without_observed_exclusion_but_calendar_incomplete':int((~c.any_observed_exclusion).sum()),'w006_independent_packages':int(w.package_id.nunique())},'invariants':{k:bool(v) for k,v in inv.items()},'input_sha256':sha(a.protected),'code_sha256':sha(__file__),'output_sha256':{str(od/'candidate_contract_condition_aggregate.csv'):sha(od/'candidate_contract_condition_aggregate.csv'),str(od/'w006_independent_package_aggregate.csv'):sha(od/'w006_independent_package_aggregate.csv')},'protected_rows_local_exported':False}
(od/'SUMMARY_RECEIPT.json').write_text(json.dumps(r,indent=2)+'\n')
