#!/usr/bin/env python3
"""Build a fixed-seed, template-grouped USA development review pack.

Selection is independent of parser predictions. This is a bounded regional-pilot
review sample, not a national probability sample or human gold standard.
"""
import csv,datetime as dt,hashlib,html,json,re,unicodedata
from collections import Counter,defaultdict
from pathlib import Path
import pyarrow as pa,pyarrow.parquet as pq

ROOT=Path('/Users/lilyluo/Documents/LinkUp_Research_20260924')
INPUT=ROOT/'reports/stage_c_pilot_review/sample_ads.parquet'
OUT=ROOT/'stage_c_v3/validation_pack'
SEED='linkup-usa-validation-pack-v1-20260927'
COHORTS=['2015','2016-17','2018-19','2020-22','2023-latest','other']
N_PER=20
EXCLUSION_SOURCES=[
 ROOT/'audit_20260927/local_text_v2/bounded_semantic_review_20260927.json',
 ROOT/'audit_20260927/local_text_v2/targeted_regressions.json',
 ROOT/'stage_c_v3/test_v3.py',
]
HEX32=re.compile(r'(?<![0-9a-f])[0-9a-f]{32}(?![0-9a-f])')

def digest(s):return hashlib.sha256(s.encode('utf-8')).hexdigest()
def file_sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def normalize_template(text):
 s=unicodedata.normalize('NFKC',html.unescape(text or '')).lower()
 s=re.sub(r'<[^>]+>',' ',s);s=re.sub(r'https?://\S+|www\.\S+',' <url> ',s)
 s=re.sub(r'\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b',' <email> ',s)
 s=re.sub(r'\b[0-9a-f]{24,}\b',' <id> ',s);s=re.sub(r'\d+(?:[.,:/-]\d+)*',' <num> ',s)
 s=re.sub(r'[^\w<>]+',' ',s,flags=re.UNICODE);return re.sub(r'\s+',' ',s).strip()
def rank(*parts):return digest(SEED+'\0'+'\0'.join(map(str,parts)))
def atomic_json(p,x):
 t=Path(str(p)+'.tmp');t.write_text(json.dumps(x,indent=2,sort_keys=True,default=str)+'\n');t.replace(p)

def main():
 if OUT.exists() and any(OUT.iterdir()):raise RuntimeError('validation_pack already exists; refuse overwrite')
 OUT.mkdir(parents=True,exist_ok=True)
 excluded=set();exclusion_detail=[]
 for p in EXCLUSION_SOURCES:
  found=set(HEX32.findall(p.read_text())) if p.exists() else set();excluded|=found
  exclusion_detail.append({'path':str(p),'exists':p.exists(),'literal_hashes':len(found),'sha256':file_sha(p) if p.exists() else None})
 table=pq.read_table(INPUT); allrows=table.to_pylist(); usa=[r for r in allrows if r['COUNTRY']=='USA']
 input_hashes={r['JOB_HASH'] for r in allrows}; known_in_input=excluded&input_hashes; known_usa={r['JOB_HASH'] for r in usa}&excluded
 eligible=[]
 for r in usa:
  if r['JOB_HASH'] in excluded:continue
  norm=normalize_template(r['DESCRIPTION']);r=dict(r);r['_NORM']=norm;r['_FP']=digest(norm);eligible.append(r)
 groups=defaultdict(list)
 for r in eligible:groups[r['_FP']].append(r)
 # One deterministic representative per normalized template globally, preventing
 # the same template from entering two cohort strata.
 reps=[]
 for fingerprint,items in groups.items():
  items=sorted(items,key=lambda x:(rank('within-template',x['JOB_HASH']),x['JOB_HASH']))
  rep=dict(items[0]);rep['_GROUP_SIZE']=len(items);reps.append(rep)
 assigned=defaultdict(list)
 for r in reps:
  if r['COHORT'] in COHORTS:assigned[r['COHORT']].append(r)
 selected=[];frame={}
 for cohort in COHORTS:
  pool=sorted(assigned[cohort],key=lambda x:(rank('template',cohort,x['_FP']),x['_FP']))
  n=min(N_PER,len(pool)); chosen=pool[:n]
  frame[cohort]={'usa_ads_before_known_exclusion':sum(x['COHORT']==cohort for x in usa),
   'eligible_ads_after_known_exclusion':sum(x['COHORT']==cohort for x in eligible),
   'globally_unique_templates_assigned_to_cohort':len(pool),'selected_templates':n}
  template_pi=1 if not pool else min(1,N_PER/len(pool))
  for r in chosen:
   r['_TEMPLATE_PI']=template_pi;r['_WITHIN_PI']=1/r['_GROUP_SIZE'];r['_PI']=template_pi/r['_GROUP_SIZE'];selected.append(r)
 if len(selected)!=N_PER*len(COHORTS):raise RuntimeError('insufficient template groups for balanced sample')
 if len({r['_FP'] for r in selected})!=len(selected):raise RuntimeError('template leakage in selected sample')
 if any(r['JOB_HASH'] in excluded for r in selected):raise RuntimeError('known development case selected')
 outrows=[]
 for r in sorted(selected,key=lambda x:(COHORTS.index(x['COHORT']),rank('final',x['JOB_HASH']))):
  z={k:v for k,v in r.items() if not k.startswith('_')};z.update({
   'REGION_SCOPE':'kunshan_64_shard_pilot','NORMALIZED_TEMPLATE_TEXT':r['_NORM'],'NORMALIZED_TEMPLATE_SHA256':r['_FP'],
   'TEMPLATE_GROUP_SIZE':r['_GROUP_SIZE'],'COHORT_ELIGIBLE_ADS':frame[r['COHORT']]['eligible_ads_after_known_exclusion'],
   'COHORT_ASSIGNED_TEMPLATE_GROUPS':frame[r['COHORT']]['globally_unique_templates_assigned_to_cohort'],
   'TEMPLATE_SELECTION_PROBABILITY_CONDITIONAL':r['_TEMPLATE_PI'],'WITHIN_TEMPLATE_SELECTION_PROBABILITY_CONDITIONAL':r['_WITHIN_PI'],
   'AD_SELECTION_PROBABILITY_CONDITIONAL':r['_PI'],'VALIDATION_CONDITIONAL_WEIGHT':1/r['_PI'],
   'TIME_SEMANTICS_STATUS':'current_delivery_text_effective_time_unknown','KNOWN_DEVELOPMENT_CASE_EXCLUDED':False})
  outrows.append(z)
 pq.write_table(pa.Table.from_pylist(outrows),OUT/'validation_sample.parquet',compression='zstd')
 fields=['JOB_HASH','COHORT','BOUNDARY_STATUS','JAN01_STATUS','CREATED','LAST_UPDATED','LAST_CHECKED','DELETE_DATE','STATE','SOURCE_FILE','SOURCE_ROW','NORMALIZED_TEMPLATE_SHA256','TEMPLATE_GROUP_SIZE','AD_SELECTION_PROBABILITY_CONDITIONAL','VALIDATION_CONDITIONAL_WEIGHT','DESCRIPTION',
 'reviewer_id','review_status','text_usable','context','general_experience_label','general_experience_evidence_text','relevant_experience_label','relevant_experience_evidence_text','tool_experience_label','tool_experience_evidence_text','education_label','education_evidence_text','qualification_or_label','qualification_or_evidence_text','explicit_no_experience_label','explicit_no_experience_evidence_text','unknown_or_ambiguous','unknown_reason','extractor_false_positive','missed_requirement','review_notes']
 with (OUT/'annotation_template.csv').open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in outrows:
   z={k:r.get(k) for k in fields};z.update({k:'' for k in fields[16:]});w.writerow(z)
 annotation_schema={'status':'unlabeled_template','allowed_values':{
  'review_status':['unreviewed','first_review_complete','independent_review_complete','adjudicated'],
  'text_usable':['yes','no','uncertain'],'context':['required','preferred','duties','company','benefits','ambiguous','multiple'],
  'general_experience_label':['required','preferred','explicit_none','not_mentioned','unknown'],
  'relevant_experience_label':['required','preferred','explicit_none','not_mentioned','unknown'],
  'tool_experience_label':['required','preferred','explicit_none','not_mentioned','unknown'],
  'education_label':['required','preferred','alternative_path','not_mentioned','unknown'],
  'qualification_or_label':['explicit_or','equivalent','including','and','unresolved','not_present','unknown'],
  'explicit_no_experience_label':['yes','no','unknown'],'unknown_or_ambiguous':['yes','no']},
  'evidence_rule':'Copy exact supporting or contradicting text from DESCRIPTION. Empty parser output must still receive full-text human review.',
  'not_gold_standard':'Rows are blank until independent human review and adjudication.'}
 atomic_json(OUT/'annotation_schema.json',annotation_schema)
 atomic_json(OUT/'known_development_exclusions.json',{'sources':exclusion_detail,'literal_hash_union':len(excluded),'present_in_2926_input':len(known_in_input),'present_in_usa_frame':len(known_usa),'excluded_usa_hashes':sorted(known_usa)})
 report={'status':'complete','created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'seed':SEED,'input':str(INPUT),'input_sha256':file_sha(INPUT),'input_rows':len(allrows),'usa_rows':len(usa),'known_development_hashes_excluded_from_usa':len(known_usa),'eligible_usa_rows':len(eligible),'normalized_template_groups':len(groups),'global_template_representatives':len(reps),'selected_rows':len(outrows),'selected_by_cohort':dict(Counter(r['COHORT'] for r in outrows)),'frame_by_cohort':frame,
  'selection_design':'Known development/regression hashes excluded. Normalize all eligible USA text; form global exact normalized-template groups; choose one fixed-hash representative per group; assign that group to the representative cohort; select the 20 lowest independent fixed-seed template hashes per cohort.',
  'probability_scope':'Recorded probabilities are conditional on the 1,030-ad USA portion of the existing deterministic 64-shard Kunshan pilot, known-case exclusions, realized global template representative assignment, and cohort. They are not national/full-corpus inclusion probabilities.',
  'holdout_status':'development review pack; independence is not established because unrecorded prior inspection or development contamination cannot be ruled out',
  'onet_status':'not joined; occupation stratification is absent from this first pack','parser_predictions_used_for_selection':False,
  'text_time_status':'effective time of delivered DESCRIPTION is unknown; cohort is Records CREATED and must not be treated as text vintage'}
 atomic_json(OUT/'selection_report.json',report)
 readme=f'''# USA validation pack (development review only)\n\nThis pack contains {len(outrows)} ads: 20 from each of six Records `CREATED` cohorts. It is drawn only from the 1,030 USA ads in the existing deterministic 64-shard Kunshan pilot. It is not nationally representative, a full-corpus probability sample, an independent holdout, or a human gold standard.\n\nKnown real cases found in the bounded semantic review, targeted regression ledger, and `test_v3.py` were excluded ({len(known_usa)} USA hashes). Other prior human inspection cannot be reconstructed completely, so unknown development contamination remains possible. No parser prediction was used in selection. O*NET was not joined, so occupation balance is not claimed.\n\nExact normalized-template groups are global across cohorts. One fixed-seed representative is retained per group before balanced cohort selection, preventing the same normalized template from appearing twice. Conditional inclusion probabilities and weights describe only this realized pilot frame.\n\n`validation_sample.parquet` retains raw DESCRIPTION, source pointers, record dates, temporal-risk fields, the original selected-shard weight, normalized-template metadata, and conditional validation weights. `annotation_template.csv` is blank and must be completed through independent reading and evidence copying under `annotation_schema.json` and the Stage C annotation protocol.\n'''
 (OUT/'README.md').write_text(readme)
 atomic_json(OUT/'COMPLETE',{'status':'complete','selection_report_sha256':file_sha(OUT/'selection_report.json'),'validation_sample_sha256':file_sha(OUT/'validation_sample.parquet')})
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
