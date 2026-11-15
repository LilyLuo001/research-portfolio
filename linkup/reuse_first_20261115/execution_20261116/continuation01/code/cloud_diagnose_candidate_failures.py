"""Aggregate existing frozen-validator errors only; no prompt tuning or resubmission."""
import collections,datetime,json,os
from pathlib import Path
R=Path.home()/'migration';B=R/'execution_20261116/run001';D=B/'qualification500_v1/luna_revision002';C=B/'continuation01'
def read(p):return json.loads(p.read_bytes())
def category(e):
 if e.startswith('schema '):return 'schema'
 if e.startswith('exact quote missing'):return 'exact_source_quote_missing'
 if 'context_sha256' in e or 'outside trusted' in e:return 'identity_binding'
 if 'no review' in e:return 'review_missing'
 if 'duplicate review' in e:return 'duplicate_review'
 if 'requires reviewed_full' in e:return 'partial_nonmention'
 if e.startswith('experience_clauses') and ('years' in e or 'bounds' in e):return 'year_bound_consistency'
 for fam in ['experience','entry','responsibility']:
  if e.startswith(fam+' '):return fam+'_outcome_consistency'
 if 'technology' in e:return 'technology_outcome_consistency'
 if 'qualification' in e or 'alternative' in e:return 'alternative_reference_consistency'
 return 'other_frozen_rule'
counts=collections.Counter();cases=collections.Counter();failed=0;missing=0
for p in sorted((D/'results').glob('case*/RESULT_PUBLIC.json')):
 if read(p)['status']!='frozen_validation_failed_preserve_output':continue
 failed+=1;err=p.parent/'ERRORS_PRIVATE.jsonl';cats=set()
 if not err.exists():missing+=1;continue
 for line in err.read_text().splitlines():
  x=json.loads(line)
  for message in x.get('errors',[]):cat=category(message);counts[cat]+=1;cats.add(cat)
 cases.update(cats)
s=read(D/'RUN_STATUS_PUBLIC.json');report={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'completed_candidate_cases_at_snapshot':s['completed'],'engineering_pass_at_snapshot':s['engineering_pass'],'failed_candidate_outputs_examined':failed,'failures_missing_error_file':missing,'error_occurrences_by_category':dict(counts),'distinct_failed_cases_by_category_nonadditive':dict(cases),'new_model_calls':0,'original_outputs_and_rules_changed':False,'failed_cases_retried':False,'quality_gate_evaluated':False,'interpretation':'Engineering failures are not rate-limit failures or semantic accuracy estimates. Preserve every result; no post-hoc prompt changes or sample replacement.'}
(C/'CANDIDATE_FAILURE_DIAGNOSTIC_PUBLIC.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
