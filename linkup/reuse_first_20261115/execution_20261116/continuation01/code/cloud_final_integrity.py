"""Verify original reference-source hashes and refresh actual finite-run status."""
import collections,datetime,hashlib,json,os
from pathlib import Path
R=Path.home()/'migration';B=R/'execution_20261116/run001';C=B/'continuation01';Q=B/'qualification500_v1';L=Q/'luna_revision002';os.umask(0o077)
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def read(p):return json.loads(p.read_bytes())
pins=read(Q/'PINS_PRIVATE.json');assert sha(Q/'PRIOR_KIMI_REFERENCES_PRIVATE.jsonl')==pins['prepared']['PRIOR_KIMI_REFERENCES_PRIVATE.jsonl'];loc=read(Q/'SOURCE_LOCATORS_PRIVATE.json');refs=[json.loads(l) for l in (Q/'PRIOR_KIMI_REFERENCES_PRIVATE.jsonl').read_text().splitlines()];inputs={x['case']:x for x in [json.loads(l) for l in (L/'INPUTS_PRIVATE.jsonl').read_text().splitlines()]}
for ref in refs:
 h=inputs[ref['case']]['row']['context_sha256'];s=loc[h];p=Path(s['reference_path']);assert sha(p)==s['reference_sha256']==ref['source_sha256'];assert read(p)==ref['review'];assert h==ref['review']['context_sha256']
for folder,name in [(C/'joined_revision002','RECOVERED_SOURCE_PINS_PRIVATE.json'),(C/'joined_revision003','EXTRA_SOURCE_PINS_PRIVATE.json')]:
 for p,h in read(folder/name).items():assert sha(Path(p))==h
assert sha(R/'integration_20261116/run001/revision003/STATUS_INDEX_PRIVATE.sqlite')=='0344e94b9f2b75af74652a2f517c4e5c535d8090e1db62eec84b55afced1523a'
checkpoint=read(C/'CHECKPOINT_PUBLIC.json');assert checkpoint['archive_full_readback_SHA_verified'];assert sha(C/'joined_revision003/REUSED_VALUES_WITH_CREATED_PRIVATE.sqlite')==checkpoint['latest_value_database_sha256']
state=read(L/'RUN_STATUS_PUBLIC.json');proc=Path('/proc')/str(state['pid']);events={}
for line in (L/'ATTEMPTS_PRIVATE.jsonl').read_text().splitlines():
 try:e=json.loads(line)
 except json.JSONDecodeError:continue
 events[e['ordinal'],e['attempt']]=e
results=[read(p) for p in sorted((L/'results').glob('case*/RESULT_PUBLIC.json'))]
snapshot={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'worker_status':state,'process_alive_exact_command':proc.exists() and str(L/'cloud_qualification_luna_worker.py').encode() in (proc/'cmdline').read_bytes(),'saved_case_results':len(results),'saved_case_outcomes':dict(collections.Counter(x['status'] for x in results)),'physical_attempts':len(events),'rate_limit_tokens_header_counts':dict(collections.Counter(x.get('rate_headers',{}).get('x-ratelimit-limit-tokens','not_yet_received') for x in events.values())),'new_Kimi_or_GPT_requests_this_wave':0,'candidate_worker_restarted_by_this_continuation':False,'new_production_accepted':0}
(C/'LATEST_QUALIFICATION_STATUS_PUBLIC.json').write_text(json.dumps(snapshot,indent=2)+'\n')
report={'at_utc':snapshot['at_utc'],'status':'original_reference_and_recovered_source_pins_verified','existing_Kimi_reference_bank_matches_preinference_pin':True,'reference_rows_exactly_equal_original_independent_source_files':len(refs),'recovered_old_source_pins_unchanged':True,'original_status_index_unchanged':True,'checkpoint_database_SHA_matches':True,'new_model_calls':0,'qualification_quality_gate_passed':False,'stage4_locked':True,'paper_paused':True,'sample_scope_does_not_certify_full_corpus':True}
(C/'FINAL_INTEGRITY_PUBLIC.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'FINAL_INTEGRITY_PUBLIC.json':report,'LATEST_QUALIFICATION_STATUS_PUBLIC.json':snapshot}))
