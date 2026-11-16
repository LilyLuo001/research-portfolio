"""Close the frozen test with independent audit evidence; never auto-promote output."""
import collections,datetime,hashlib,json,os,sqlite3,sys
from pathlib import Path
R=Path.home()/'migration';B=R/'execution_20261116/run001';Q=B/'qualification500_v1';L=Q/'luna_revision002';K=Q/'kimi_reference350_v1';A=Q/'astra_audit50_transport_recovery_v1';O=B/'continuation02';os.umask(0o077)
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def write(p,x):
 b=(json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode()
 if p.exists():assert p.read_bytes()==b,'final_snapshot_conflict'
 else:p.write_bytes(b)
def attempt_usage(d):
 ev={}
 logs=[d/'ATTEMPTS_PRIVATE.jsonl']
 if d.name=='astra_audit50_transport_recovery_v1':logs.insert(0,Q/'astra_audit50_v1/ATTEMPTS_PRIVATE.jsonl')
 for log in logs:
  for l in log.read_text().splitlines():
   x=json.loads(l);ev[x['ordinal'],x['attempt']]=x
 c=read(d/'BENCHMARK_CONFIG_PUBLIC.json');s=read(d/'RUN_STATUS_PUBLIC.json')
 inp=sum(x.get('usage',{}).get('prompt_tokens',0) for x in ev.values());out=sum(x.get('usage',{}).get('completion_tokens',0) for x in ev.values())
 return {'physical_attempts':len(ev),'input_tokens':inp,'output_tokens':out,'responses_without_usage':sum(not x.get('usage') for x in ev.values()),'conservative_reserved_usd':sum(x['reservation_usd'] for x in ev.values()),'priced_usage_estimate_usd':(inp*c['input_pricing_usd_per_million']+out*c['output_pricing_usd_per_million'])/1e6,'price_type':c['price_type'],'actual_invoice_verified':False,'engineering_pass':s['engineering_pass'],'completed':s['completed'],'selected':s['selected'],'original_ledgers_unchanged':s['original_ledgers_unchanged'],'rate_limit_tokens_headers':dict(collections.Counter(x.get('rate_headers',{}).get('x-ratelimit-limit-tokens','missing') for x in ev.values())),'returned_model_names':dict(collections.Counter(x.get('returned_model','not_returned') for x in ev.values()))}
for d in (L,A):
 s=read(d/'RUN_STATUS_PUBLIC.json');assert s['status']=='finite_benchmark_completed' and s['completed']==s['selected']
 p=Path('/proc')/str(s['pid'])/'cmdline';assert not p.exists() or str(d).encode() not in p.read_bytes(),'worker_still_running'
 for name,h in read(d/'SHA256SUMS_PRIVATE.json').items():assert sha(d/name)==h,'completed_worker_source_or_result_changed'
 assert s['original_ledgers_unchanged']
assert sha(B/'continuation01/joined_revision003/REUSED_VALUES_WITH_CREATED_PRIVATE.sqlite')=='fdcdfc86270c0391fef512dcdd641438606ec9ad2f00b0554c8bc9b1353f49a5'
assert sha(R/'integration_20261116/run001/revision003/STATUS_INDEX_PRIVATE.sqlite')=='0344e94b9f2b75af74652a2f517c4e5c535d8090e1db62eec84b55afced1523a'
assert sha(Q/'metrics_execution_fix001/qualification_metrics.py')=='33f354aa7dda0c117032f4cbc06c4bba427eb50727372528980471570b809d11'
sys.path.insert(0,str(Q/'metrics_execution_fix001'));import qualification_metrics as metrics
allcases={x['case']:x for x in read(O/'FIELD_COMPARISON_PRIVATE.json')};selection=read(A/'SELECTION_PRIVATE.json');inputs=[json.loads(l) for l in (A/'INPUTS_PRIVATE.jsonl').read_text().splitlines()];audit={}
for i,x in enumerate(inputs):
 d=A/'results'/f'case{i:04d}';res=read(d/'RESULT_PUBLIC.json');valid=res['status']=='frozen_validator_pass_independent_audit_only';review=read(d/'REVIEW_PRIVATE.jsonl') if valid else None
 if review:assert review['context_sha256']==x['row']['context_sha256'] and review['record_id']==x['row']['record_id']
 audit[str(x['case'])]=(review,valid,res['status'])
assert len(audit)<=50 and set(audit)==set(selection['heldout30'])|set(selection['disagreement20'])
report={};gate=read(L/'PROTOCOL_PUBLIC.json')['field_gate']
for group,ids in selection.items():
 if not ids:
  report[group]={'cases':0,'status':'no_cases_selected_by_frozen_rule','not_a_population_accuracy_estimate':True}
  continue
 comparisons={}
 for side in ('candidate','reference'):
  rows=[]
  for case in ids:
   c=allcases[case];review,valid,status=audit[case]
   rows.append({'case':case,'split':'heldout','candidate':c[side],'candidate_valid':c[side+'_valid'],'reference':review,'reference_valid':valid})
  result=metrics.evaluate(rows,gate)
  comparisons[side]={'fields':{f:{k:x[k] for k in ('known_reference_cases','unknown_reference_cases','candidate_known_cases_all','support','positive_outcome','outcome_macro_f1','complete_relation')} for f,x in result['fields'].items()},'cases':len(rows),'not_a_population_accuracy_estimate':True}
 tiebreak={}
 for f in metrics.FIELDS:
  count=collections.Counter()
  for case in ids:
   c=allcases[case];g,gv,_=audit[case];cs=metrics.extract(c['candidate'],f,c['candidate_valid']);ks=metrics.extract(c['reference'],f,c['reference_valid']);gs=metrics.extract(g,f,gv)
   if not gv or gs[0]=='unknown':count['GPT_unresolved']+=1
   elif cs==ks==gs:count['all_three_exactly_agree']+=1
   elif cs!=ks and gs==ks:count['GPT_exact_supports_Kimi_not_Luna']+=1
   elif cs!=ks and gs==cs:count['GPT_exact_supports_Luna_not_Kimi']+=1
   else:count['different_or_unresolved_semantics']+=1
  tiebreak[f]=dict(count)
 report[group]={'model_agreement':comparisons,'bounded_tiebreak_support':tiebreak,'stratum_selected_on_disagreement':group=='disagreement20'}
comparison=read(O/'QUALIFICATION_COMPARISON_PUBLIC.json');qualified=[f for f,x in comparison['fields'].items() if x['machine_reference_field_gate_pass']]
# This result is a machine-comparison gate. Audit disagreement never silently edits any source label.
final={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'fixed_qualification_protocol_completed','scope':'500_predeclared_historical_contexts_not_population_production','candidate_model':'gpt-6-luna','independent_reference_model':'Kimi-K3.1-Pro','audit_model':'gpt-6-astra','selected_inputs':500,'heldout_inputs':300,'development_inputs_not_used_in_gate':200,'independent_Kimi_existing_reused':150,'independent_Kimi_new_results_accounted':350,'Astra_audit_results_accounted':len(audit),'Astra_audits_with_validated_outputs':sum(x[1] for x in audit.values()),'Astra_initial_HTTP400_rejections_preserved':50,'Astra_transport_recovery_did_not_repeat_any_model_generated_answer':True,'Astra_audit_outcomes':dict(collections.Counter(x[2] for x in audit.values())),'machine_reference_qualified_fields':qualified,'field_blocking_reasons':{f:x['blocking_reasons'] for f,x in comparison['fields'].items()},'machine_agreement_not_human_gold':True,'no_human_review_required_or_performed':True,'no_population_generalization_claim':True,'no_prompts_schemas_samples_or_thresholds_retuned_to_pass':True,'Astra_audit_did_not_replace_Kimi_labels':True,'new_production_accepted':0,'stage4_admitted_inputs':0,'stage4_reason':'no_field_passed_frozen_qualification' if not qualified else 'field_gate_evidence_requires_verified_nonduplicate_missing_field_queue_before_admission','stage4_budget_spent_usd':0,'whole_corpus_missing_unique_input_count':None,'whole_corpus_production_budget_released':False,'paper_paused':True,'original_ledger_and_reused_values_SHA_unchanged':True,'Luna_usage':attempt_usage(L),'Astra_usage':attempt_usage(A)}
write(O/'INDEPENDENT_AUDIT_PUBLIC.json',{'scope_note':'30 hash-ranked heldout and 20 selected disagreements reported separately; automated reference comparisons, not human truth or unbiased pooled accuracy','groups':report,'original_outputs_unchanged':True})
write(O/'QUALIFICATION_DECISION_PUBLIC.json',final)
print(json.dumps({k:v for k,v in final.items() if k not in ('field_blocking_reasons','Luna_usage','Astra_usage')}))
