"""Complete frozen machine-reference comparison; prepare at most 50 blind audits.

No labels, validation gates, legacy results, or sample composition are repaired.
The 30+20 audit selection is deterministic and all provider-protected sources are
excluded. Audit results do not silently replace the independent Kimi reference.
"""
import base64,collections,datetime,hashlib,importlib.util,json,os,sys,time,zlib
from pathlib import Path
os.umask(0o077)
R=Path.home()/'migration';B=R/'execution_20261116/run001';Q=B/'qualification500_v1';L=Q/'luna_revision002';K=Q/'kimi_reference350_v1';P=Q/'reference_preflight002';D=Q/'astra_audit50_v1';O=B/'continuation02'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def immutable(p,b):
 if p.exists():assert p.read_bytes()==b,'immutable_conflict'
 else:p.write_bytes(b)
def write(p,x):immutable(p,(json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
def jsonl(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
state=read(L/'RUN_STATUS_PUBLIC.json');assert state['status']=='finite_benchmark_completed' and state['completed']==500
for rel,h in read(L/'SHA256SUMS_PRIVATE.json').items():assert sha(L/rel)==h,'candidate_final_pin_changed'
assert sha(Q/'PRIOR_KIMI_REFERENCES_PRIVATE.jsonl')==read(Q/'PINS_PRIVATE.json')['prepared']['PRIOR_KIMI_REFERENCES_PRIVATE.jsonl']
assert read(P/'PRIOR_VALIDATION_PUBLIC.json')['status']=='pass'
assert sha(P/'qualification_metrics.py')=='34c490817d9dfd5f93861607f8f892956bad3f3706d09fd42a88f8abedc86fba'
sys.path.insert(0,str(P));import qualification_metrics as metrics
frame=jsonl(L/'INPUTS_PRIVATE.jsonl');assert len(frame)==500 and len({str(x['case']) for x in frame})==500
prior=jsonl(Q/'PRIOR_KIMI_REFERENCES_PRIVATE.jsonl');prior_case={str(x['case']):x for x in prior};assert len(prior_case)==150
new=jsonl(P/'BLIND_NEW_REFERENCE_INPUTS_PRIVATE.jsonl');new_cases={str(x['case']) for x in new};assert len(new_cases)==350
assert new_cases.isdisjoint(prior_case) and new_cases|set(prior_case)=={str(x['case']) for x in frame}
results=list((K/'results').glob('*/RESULT_PUBLIC.json'));assert len(results)==350,'reference_leg_incomplete'
schema=read(L/'SCHEMA.json');cases=[];refs=[];sourcepins={};excluded=read(L/'EXCLUSIONS_PRIVATE.json')
for p in (K/'commits').glob('*/EXCLUSIONS_PRIVATE.json'):
 e=read(p)
 for k in ('tasks','context_sha256'):excluded[k]=sorted(set(excluded.get(k,[]))|set(e.get(k,[])))
for ordinal,item in enumerate(frame):
 case=str(item['case']);row=item['row'];cd=L/'results'/f'case{ordinal:04d}';cr=read(cd/'RESULT_PUBLIC.json');candidate_valid=cr['status']=='frozen_validator_pass_candidate_only';candidate=read(cd/'REVIEW_PRIVATE.jsonl') if candidate_valid else None
 if case in prior_case:
  carrier=prior_case[case]['review'];reference=metrics.unwrap_validated_carrier(carrier,schema);reference_valid=True;rs='reused_preinference_independent_Kimi'
 else:
  rd=K/'results'/case
  for name,digest in read(rd/'SHA256SUMS_PRIVATE.json').items():assert sha(rd/name)==digest,'reference_output_changed'
  rr=read(rd/'RESULT_PUBLIC.json');reference_valid=rr['status']=='frozen_validator_pass_reference_only';reference=read(rd/'REVIEW_PRIVATE.jsonl') if reference_valid else None;rs=rr['status']
  sourcepins[str(rd/'RESULT_PUBLIC.json')]=sha(rd/'RESULT_PUBLIC.json')
 for review in (candidate,reference):
  if review is not None:assert review['record_id']==row['record_id'] and review['context_sha256']==row['context_sha256'],'review_identity_conflict'
 cases.append({'case':case,'split':item['split'],'reference':reference,'reference_valid':reference_valid,'candidate':candidate,'candidate_valid':candidate_valid,'candidate_status':cr['status'],'reference_status':rs})
 refs.append({'case':case,'reference_status':rs,'reference_valid':reference_valid})
assert sum(x['split']=='heldout' for x in cases)==300
protocol=read(L/'PROTOCOL_PUBLIC.json');comparison=metrics.evaluate(cases,protocol['field_gate'])
comparison.update(at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),complete_predeclared_frame_accounted=500,reference_status_counts=dict(collections.Counter(x['reference_status'] for x in cases)),candidate_status_counts=dict(collections.Counter(x['candidate_status'] for x in cases)),production_locked_pending_full_protocol=True)
write(O/'FIELD_COMPARISON_PRIVATE.json',cases);write(O/'QUALIFICATION_COMPARISON_PUBLIC.json',comparison)
write(O/'REFERENCE_SOURCE_PINS_PRIVATE.json',sourcepins)
# Selection rule frozen in source before inference. No source or answer is sent in public reports.
bycase={str(x['case']):x for x in frame};blocked_h=set(excluded.get('context_sha256',[]));blocked_t=set(excluded.get('tasks',[]))
eligible=[x for x in cases if x['split']=='heldout' and bycase[x['case']]['row']['context_sha256'] not in blocked_h and bycase[x['case']]['task'] not in blocked_t]
def rank(c):return hashlib.sha256(('qualification500_v1/astra_blind_audit/v1/'+bycase[c['case']]['row']['context_sha256']).encode()).hexdigest()
ranked=sorted(eligible,key=rank);random30=ranked[:30];selected={x['case'] for x in random30}
def differs(c):
 return any(metrics.extract(c['candidate'],f,c['candidate_valid'])!=metrics.extract(c['reference'],f,c['reference_valid']) for f in metrics.FIELDS)
disagreements=[x for x in ranked if x['case'] not in selected and differs(x)][:20]
chosen=random30+disagreements;assert len(chosen)<=50 and len({x['case'] for x in chosen})==len(chosen)
D.mkdir(exist_ok=True);inputs=[bycase[x['case']] for x in chosen]
immutable(D/'INPUTS_PRIVATE.jsonl',''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in inputs).encode())
immutable(D/'SCHEMA.json',(L/'SCHEMA.json').read_bytes());immutable(D/'INSTRUCTIONS.md',(L/'INSTRUCTIONS.md').read_bytes())
write(D/'EXCLUSIONS_PRIVATE.json',excluded);write(D/'PROTOCOL_PUBLIC.json',protocol)
config={'run_id':'reuse-qualification500-astra-audit-v1','role':'independent_source_blind_audit_not_production','max_records':len(inputs),'model':'gpt-6-astra','deployment_name':'linkup-gpt-6-astra','reasoning_effort':'high','max_completion_tokens':12000,'max_request_utf8_bytes':63000,'max_physical_attempts':60,'max_attempts_per_record':2,'run_reservation_cap_usd':100,'scheduled_tpm_ceiling':800000,'concurrency':1,'max_wall_seconds':14400,'retry_only_confirmed_http_codes':[429,500,502,503,504],'input_pricing_usd_per_million':12.5,'output_pricing_usd_per_million':50.0,'price_type':'conservative_existing_Azure_short_context_cache_write_bound_not_invoice','price_source':'existing_astra_agent_PRICES_readonly_preserved','candidate_answers_available_to_worker':False,'reference_answers_available_to_worker':False,'no_human_gold_claim':True}
write(D/'BENCHMARK_CONFIG_PUBLIC.json',config)
files=['INPUTS_PRIVATE.jsonl','SCHEMA.json','INSTRUCTIONS.md','PROTOCOL_PUBLIC.json','BENCHMARK_CONFIG_PUBLIC.json']
runtime={'code/validate_reviews.py':'f7737143004374f9391a16ad2d1bab2fa47950c589232510045d1eee93bc2c20'}
write(D/'WORKER_INPUT_PINS_PUBLIC.json',{'files':{name:sha(D/name) for name in files},'runtime':runtime})
selection={'selected':len(inputs),'deterministic_heldout':len(random30),'additional_disagreement_cases':len(disagreements),'source_blind':True,'worker_reads_no_candidate_or_reference_answers':True,'input_pin':sha(D/'INPUTS_PRIVATE.jsonl'),'protected_sources_excluded_without_replacement':True,'budget_cap_usd':100,'new_production_accepted':0}
write(O/'ASTRA_AUDIT_SELECTION_PUBLIC.json',selection)
write(D/'SELECTION_PRIVATE.json',{'heldout30':[x['case'] for x in random30],'disagreement20':[x['case'] for x in disagreements]})
summary={'phase':'independent_Kimi_comparison_complete_Astra_audit_prepared','candidate_completed':500,'references_accounted':500,'qualified_before_Astra':[f for f,x in comparison['fields'].items() if x['machine_reference_field_gate_pass']],'audit_selection':selection,'candidate_status_counts':comparison['candidate_status_counts'],'reference_status_counts':comparison['reference_status_counts'],'production_locked':True}
print(json.dumps(summary))
