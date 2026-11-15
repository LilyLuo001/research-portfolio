"""Classify finite benchmark validator failures without publishing private values."""
import collections,datetime,hashlib,json,re
from pathlib import Path
R=Path.home()/'migration';D=R/'reuse_first_20261115/run01/benchmark20'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
state=read(D/'RUN_STATUS_PUBLIC.json');assert state['status']=='finite_benchmark_completed'
counts=collections.Counter();fields=collections.Counter();n=0
for p in (D/'results').glob('case*/RESULT_PUBLIC.json'):
    if read(p)['status']!='frozen_validation_failed_preserve_output':continue
    n+=1;e=p.parent/'ERRORS_PRIVATE.jsonl'
    if not e.exists():counts['validator_did_not_create_error_file']+=1;continue
    for line in e.read_text().splitlines():
        x=json.loads(line)
        for message in x.get('errors',[]):
            if message.startswith('schema '):
                counts['json_schema_constraint']+=1
                path=message.split(':',1)[0][7:]
                fields[re.sub(r'\[\d+\]','[]',path) if re.fullmatch(r'[A-Za-z0-9_.\[\]]+',path) else 'schema_path_redacted']+=1
            elif message.startswith('exact quote missing at '):counts['exact_evidence_quote_missing']+=1
            elif 'years_min' in message or 'years_relation' in message:counts['year_bounds_inconsistent']+=1
            elif 'alternative' in message or 'qualification group' in message:counts['alternative_links_inconsistent']+=1
            elif 'present lacks' in message:counts['positive_outcome_missing_support_item']+=1
            elif 'not_mentioned conflicts' in message or 'nonmention conflicts' in message:counts['nonmention_conflicts_with_items']+=1
            elif 'context_sha256' in message or 'record_id' in message:counts['identity_binding_mismatch']+=1
            else:counts['other_cross_field_or_schema_constraint']+=1
pid=state['pid'];proc=Path('/proc')/str(pid)/'stat'
process_state=proc.read_text().rsplit(')',1)[1].split()[0] if proc.exists() else 'absent'
report={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'finite_failure_categories_saved_no_reruns','failed_records':n,'error_categories':dict(counts),'schema_field_paths':dict(fields),'worker_running':process_state not in ('absent','Z','X'),'final_summary_sha256':sha(D/'FINAL_SUMMARY_PUBLIC.json'),'full_comparison_sha256':sha(D/'comparison_v1/COMPARISON_PUBLIC.json'),'original_ledgers_unchanged':state['original_ledgers_unchanged'],'model_calls_in_diagnostic':0,'historical_results_modified':False}
(D/'FAILURE_DIAGNOSTIC_PUBLIC.json').write_text(json.dumps(report,indent=2)+'\n')
p=R/'CURRENT_RESEARCH_POLICY_PUBLIC.json';q=read(p);q.update(status='finite_candidate_benchmark_completed',benchmark_final_summary=str(D/'FINAL_SUMMARY_PUBLIC.json'),global_inference_running=False,benchmark_worker_running=report['worker_running']);p.write_text(json.dumps(q,indent=2)+'\n')
print(json.dumps(report,separators=(',',':')))
