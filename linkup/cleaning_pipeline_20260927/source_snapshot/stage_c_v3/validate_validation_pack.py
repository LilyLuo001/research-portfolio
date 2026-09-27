#!/usr/bin/env python3
import csv,hashlib,json
from collections import Counter
from pathlib import Path
import pyarrow.parquet as pq
HERE=Path(__file__).parent;OUT=HERE/'validation_pack';ROOT=HERE.parent
sample=pq.read_table(OUT/'validation_sample.parquet').to_pylist();source=pq.read_table(ROOT/'reports/stage_c_pilot_review/sample_ads.parquet').to_pylist()
source_map={(r['JOB_HASH'],r['SOURCE_FILE'],r['SOURCE_ROW']):r for r in source}
ex=set(json.load(open(OUT/'known_development_exclusions.json'))['excluded_usa_hashes'])
checks={}
checks['rows_120']=len(sample)==120
checks['balanced_cohort']=Counter(r['COHORT'] for r in sample)==Counter({'2015':20,'2016-17':20,'2018-19':20,'2020-22':20,'2023-latest':20,'other':20})
checks['usa_only']=all(r['COUNTRY']=='USA' for r in sample)
checks['job_hash_unique']=len({r['JOB_HASH'] for r in sample})==120
checks['normalized_template_unique']=len({r['NORMALIZED_TEMPLATE_SHA256'] for r in sample})==120
checks['known_development_disjoint']=not ({r['JOB_HASH'] for r in sample}&ex)
checks['source_pointer_and_text_exact']=all((r['JOB_HASH'],r['SOURCE_FILE'],r['SOURCE_ROW']) in source_map and source_map[(r['JOB_HASH'],r['SOURCE_FILE'],r['SOURCE_ROW'])]['DESCRIPTION']==r['DESCRIPTION'] for r in sample)
checks['template_hash_exact']=all(hashlib.sha256(r['NORMALIZED_TEMPLATE_TEXT'].encode()).hexdigest()==r['NORMALIZED_TEMPLATE_SHA256'] for r in sample)
checks['conditional_probability_valid']=all(0<r['AD_SELECTION_PROBABILITY_CONDITIONAL']<=1 and abs(r['VALIDATION_CONDITIONAL_WEIGHT']*r['AD_SELECTION_PROBABILITY_CONDITIONAL']-1)<1e-10 for r in sample)
with (OUT/'annotation_template.csv').open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
checks['annotation_rows_120']=len(rows)==120
label_cols=['reviewer_id','review_status','text_usable','context','general_experience_label','general_experience_evidence_text','relevant_experience_label','relevant_experience_evidence_text','tool_experience_label','tool_experience_evidence_text','education_label','education_evidence_text','qualification_or_label','qualification_or_evidence_text','explicit_no_experience_label','explicit_no_experience_evidence_text','unknown_or_ambiguous','unknown_reason','extractor_false_positive','missed_requirement','review_notes']
checks['annotation_labels_blank']=all(all(r[x]=='' for x in label_cols) for r in rows)
report={'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'selected_description_bytes':sum(len(r['DESCRIPTION'].encode()) for r in sample),'template_group_size_distribution':dict(Counter(r['TEMPLATE_GROUP_SIZE'] for r in sample))}
(OUT/'validation_report.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print(json.dumps(report,indent=2))
if report['status']!='PASS':raise SystemExit(1)
