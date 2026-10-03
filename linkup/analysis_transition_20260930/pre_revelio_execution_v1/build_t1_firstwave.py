#!/usr/bin/env python3
"""Package the accepted first-wave funnel without conflating Records and description units."""
import argparse,csv,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--firstwave',type=Path,required=True);p.add_argument('--records-report',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
fw=json.loads((a.firstwave/'CONSERVATION_REPORT.json').read_text()); rr=json.loads(a.records_report.read_text())
if fw.get('status')!='complete' or fw.get('shards')!=2464 or not all(fw['conservation'].values()): raise RuntimeError('accepted 2464-shard firstwave required')
checks=rr['checks']; f=fw['funnel']; rows=[]
def add(order,layer,metric,count,denom=None,status='complete',note=''):
 rows.append({'order':order,'layer':layer,'metric':metric,'count':count,'denominator':denom if denom is not None else '',
  'share':count/denom if denom else '','status':status,'unit_note':note})
add(1,'Records','all_records',checks['raw_rows_scanned'],note='delivered Records rows; not vacancies or hires')
add(2,'Records','usa_records',checks['sum_monthly_us_records'],checks['raw_rows_scanned'],note='COUNTRY==USA Records rows')
add(3,'Descriptions','raw_description_rows',f['raw_input_rows'],note='description occurrences; not asserted distinct keys')
add(4,'Descriptions','record_matched_description_rows',f['record_matched_rows'],f['raw_input_rows'],note='description occurrences matched to Records')
add(5,'Descriptions','record_unmatched_description_rows',f['record_unmatched_rows'],f['raw_input_rows'],note='description occurrences unmatched to Records')
add(6,'Disposition','matched_non_usa_rows',f['matched_non_usa_rows'],f['record_matched_rows'])
add(7,'Disposition','matched_country_unknown_rows',f['matched_country_unknown_rows'],f['record_matched_rows'])
add(8,'Disposition','usa_canonical_regional_row_sum',f['canonical_ad_status'],f['record_matched_rows'],status='pending_global_job_hash_audit',note='sum of accepted regional canonical rows; unique JOB_HASH denominator pending global audit')
add(9,'Semantic','usable_nonempty_complete_parse',f['usable_nonempty_complete_parse'],f['canonical_ad_status'],status='row_level_complete_global_job_hash_audit_pending',note='usable is the mutually exhaustive pass/fail complement; individual failure flags may overlap')
add(10,'Comparison','comparison_eligible','',status='pending_full_narrow_join',note='requires date, occupation, region and common-support gates')
a.output_dir.mkdir(parents=True,exist_ok=True); out=a.output_dir/'01_population_funnel.csv'
with out.open('w',newline='') as h: w=csv.DictWriter(h,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
flags=[{'flag':k,'rows':f[k],'denominator':f['canonical_ad_status'],'share':f[k]/f['canonical_ad_status'],'note':'flags overlap; do not sum'} for k in ('empty_description','enrichment_incomplete','input_evidence_truncated')]
with (a.output_dir/'01_population_funnel_failure_flags.csv').open('w',newline='') as h: w=csv.DictWriter(h,fieldnames=list(flags[0]));w.writeheader();w.writerows(flags)
sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
receipt={'status':'limited_pending_global_job_hash_audit_and_join','shards':2464,'records_all':checks['raw_rows_scanned'],'records_usa':checks['sum_monthly_us_records'],'regional_canonical_row_sum':f['canonical_ad_status'],'usable_rows':f['usable_nonempty_complete_parse'],'funnel_sha256':sha(out),'failure_flags_sha256':sha(a.output_dir/'01_population_funnel_failure_flags.csv'),'source_conservation_report_sha256':sha(a.firstwave/'CONSERVATION_REPORT.json'),'records_report_sha256':sha(a.records_report)}
(a.output_dir/'01_population_funnel_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
