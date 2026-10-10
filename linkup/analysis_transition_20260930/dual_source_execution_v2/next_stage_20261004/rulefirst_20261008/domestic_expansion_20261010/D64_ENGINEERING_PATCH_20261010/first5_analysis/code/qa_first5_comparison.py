#!/usr/bin/env python3
"""Public-output arithmetic/provenance QA; does not independently recompute strata weights."""
import argparse,csv,datetime as dt,hashlib,json,os

METRICS=[
 'broad_general_work','broad_occupation_task','broad_industry_domain','broad_related','broad_tool','broad_general_and_related',
 'narrow_general_work','narrow_occupation_task','narrow_industry_domain','narrow_related','narrow_tool','narrow_general_and_related',
 'numeric_duration_observed','conditional_or_alternative_experience_observed','experience_scope_unknown','unresolved_experience_observed',
 'independent_judgment_wording','client_responsibility_wording','people_supervision_wording','d57_current_duty_mentoring_candidate',
 'supervision_or_current_duty_mentoring','any_frozen_responsibility_wording']
GROUPS=['software_only','ai_only','software_and_ai','neither_observed']
RAW_GROUPS=GROUPS+['any_ai','all_first5']
ENTRY_MARKERS=['explicit_eligibility_wording_union','explicit_noexperience_any_scope','explicit_noexperience_unconditional','explicit_noexperience_conditional_or_alternative','explicit_noexperience_scope_unknown','specific_experience_waiver_not_general_eligibility','graduate_scope_not_recorded','combined_junior_wording_title_or_body_unresolved']
RESPONSIBILITY=['independent_judgment_wording','client_responsibility_wording','people_supervision_wording','d57_current_duty_mentoring_candidate','supervision_or_current_duty_mentoring','any_frozen_responsibility_wording']

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):
   h.update(b)
 return h.hexdigest()
def readcsv(path):
 with open(path,encoding='utf-8',newline='') as f:
  return list(csv.DictReader(f))
def num(x):
 return None if x in ('',None,'None') else float(x)
def exact_keys(rows,fields,expected,label):
 keys=[tuple(r[f] for f in fields) for r in rows]
 if len(keys)!=len(set(keys)):
  raise RuntimeError(label+' duplicate keys')
 if set(keys)!=set(expected):
  raise RuntimeError(label+' incomplete or unexpected keys')

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--public',required=True)
 ap.add_argument('--output',required=True)
 a=ap.parse_args()
 rec=json.load(open(os.path.join(a.public,'RUN_RECEIPT_PUBLIC.json')))
 if rec['status']!='pass' or rec['coverage_posting_denominator']!=424226 or rec['analysis_posting_denominator']!=424225:
  raise RuntimeError('receipt denominator/status')
 for name,meta in rec['outputs'].items():
  if sha(os.path.join(a.public,name))!=meta['sha256']:
   raise RuntimeError('output hash '+name)
 tech=readcsv(os.path.join(a.public,'TECHNOLOGY_GROUPS_PUBLIC.csv'))
 exact_keys(tech,['technology_group'],[(g,) for g in GROUPS],'technology groups')
 tc={r['technology_group']:int(r['posting_count']) for r in tech}
 if sum(tc.values())!=424225:
  raise RuntimeError('tech partition')
 raw=readcsv(os.path.join(a.public,'RAW_OUTCOME_RATES_PUBLIC.csv'))
 exact_keys(raw,['technology_group','metric'],[(g,m) for g in RAW_GROUPS for m in METRICS],'raw outcomes')
 den={'software_only':tc['software_only'],'ai_only':tc['ai_only'],'software_and_ai':tc['software_and_ai'],'neither_observed':tc['neither_observed'],'any_ai':tc['ai_only']+tc['software_and_ai'],'all_first5':424225}
 for r in raw:
  if int(r['denominator'])!=den[r['technology_group']]:
   raise RuntimeError('raw denominator')
  if not 0<=int(r['numerator'])<=int(r['denominator']):
   raise RuntimeError('raw bounds')
  d=int(r['denominator'])
  observed=num(r['fraction'])
  if d==0:
   if observed is not None:
    raise RuntimeError('zero-denominator raw fraction')
  elif observed is None or abs(observed-int(r['numerator'])/d)>1e-12:
   raise RuntimeError('raw fraction arithmetic')
 table_specs=(
  ('OCCUPATION_STANDARDIZED_COMPARISONS_PUBLIC.csv','occupation',20,['software_only_vs_any_ai','software_only_vs_ai_only']),
  ('COMPANY_OCCUPATION_SENSITIVITY_PUBLIC.csv','company_occupation',5,['software_only_vs_any_ai']))
 for name,kind,threshold,comparisons in table_specs:
  rows=readcsv(os.path.join(a.public,name))
  exact_keys(rows,['comparison','cell_kind','metric'],[(c,kind,m) for c in comparisons for m in METRICS],name)
  for r in rows:
   if int(r['threshold_each_arm'])!=threshold:
    raise RuntimeError('standardized threshold')
   for side in ('left','right'):
    if int(r[side+'_retained_n'])>int(r[side+'_valid_occupation_n']):
     raise RuntimeError('retained bounds')
   if r['status']=='estimated':
    left=num(r['left_standardized_rate'])
    right=num(r['right_standardized_rate'])
    difference=num(r['difference_right_minus_left_percentage_points'])
    if left is None or right is None or not (-1e-12<=left<=1+1e-12 and -1e-12<=right<=1+1e-12) or abs(difference-(right-left)*100)>1e-9:
     raise RuntimeError('standardized public bounds/difference')
 entry=readcsv(os.path.join(a.public,'ENTRY_RESPONSIBILITY_COOCCURRENCE_PUBLIC.csv'))
 exact_keys(entry,['eligibility_marker','responsibility_marker'],[(m,o) for m in ENTRY_MARKERS for o in RESPONSIBILITY],'entry cooccurrence')
 for r in entry:
  cells=sum(int(r[x]) for x in ('marker_yes_outcome_yes','marker_yes_outcome_no_observed','marker_no_observed_outcome_yes','marker_no_observed_outcome_no_observed'))
  if cells!=424225 or int(r['marker_population_n'])!=int(r['marker_yes_outcome_yes'])+int(r['marker_yes_outcome_no_observed']):
   raise RuntimeError('entry 2x2')
 result={'version':'d64-first5-public-output-qa-v2','status':'pass','created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'producer_receipt_sha256':sha(os.path.join(a.public,'RUN_RECEIPT_PUBLIC.json')),'checks':{'output_hashes':True,'exact_unique_table_keys':{'technology_groups':4,'raw_outcomes':132,'occupation_standardized':44,'company_occupation':22,'entry_cooccurrence':48},'technology_partition_424225':True,'raw_denominators':True,'standardized_public_bounds_and_delta':True,'entry_2x2_denominators':True},'scope':'public aggregates only; validates exact row keys, uniqueness and public arithmetic; does not independently recompute common-support cells, weights, stratified rates or semantics'}
 tmp=a.output+'.tmp'
 with open(tmp,'w') as f:
  json.dump(result,f,indent=2,sort_keys=True)
  f.write('\n')
 os.replace(tmp,a.output)

if __name__=='__main__':
 main()
