"""Reuse and revalidate prior blind Kimi references, prepare no candidate answers."""
import contextlib,io,base64,datetime,hashlib,importlib.util,json,os,sys,unittest
from pathlib import Path
R=Path.home()/'migration';B=R/'execution_20261116/run001';Q=B/'qualification500_v1';L=Q/'luna_revision002';D=Q/'reference_preflight001';os.umask(0o077);D.mkdir(exist_ok=False)
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def read(p):return json.loads(p.read_bytes())
for name,data in FILES_B64.items():(D/name).write_bytes(base64.b64decode(data))
sys.path.insert(0,str(D));suite=unittest.defaultTestLoader.discover(str(D),pattern='test_qualification_metrics.py');result=unittest.TextTestRunner(stream=(D/'SYNTHETIC_TEST_LOG_PRIVATE.txt').open('w'),verbosity=2).run(suite);assert result.wasSuccessful()
protocol=read(L/'PROTOCOL_PUBLIC.json');assert protocol['reference']['existing_independent_Kimi']==150 and protocol['reference']['new_Kimi_max']==350
assert sha(Q/'INPUTS_PRIVATE.jsonl')=='e750ffd9f34596e558c8350f51fe3bafb86d26e2568eb16e2c029250848c0c72'
# The original frame remains the source of heldout membership, never current outcomes.
framepath=B/'qualification_frame_v1/FRAME_PRIVATE.json';assert sha(framepath)=='28821e74712ce7d102044cc6a002d25f9cae9218c089897150bda38085ce2ab8'
inputs=[json.loads(l) for l in (L/'INPUTS_PRIVATE.jsonl').read_text().splitlines()];assert len(inputs)==500;bycase={x['case']:x for x in inputs}
ex=read(L/'EXCLUSIONS_PRIVATE.json');blocked=set(ex['context_sha256']);blocked_tasks=set(ex['tasks']);prior=[]
for line in (Q/'PRIOR_KIMI_REFERENCES_PRIVATE.jsonl').read_text().splitlines():
 r=json.loads(line);inp=bycase[r['case']];h=inp['row']['context_sha256']
 if h in blocked or inp['task'] in blocked_tasks:continue
 assert r['review']['context_sha256']==h;assert r['review']['record_id']==inp['row']['record_id'];assert hashlib.sha256(inp['row']['full_document'].encode()).hexdigest()==h;prior.append(r)
packet=D/'PRIOR_REFERENCE_INPUTS_PRIVATE.jsonl';reviews=D/'PRIOR_REFERENCES_PRIVATE.jsonl';packet.write_text(''.join(json.dumps(bycase[x['case']]['row'],ensure_ascii=False)+'\n' for x in prior));reviews.write_text(''.join(json.dumps(x['review'],ensure_ascii=False)+'\n' for x in prior))
frozen=R/'code/validate_reviews.py';assert sha(frozen)=='f7737143004374f9391a16ad2d1bab2fa47950c589232510045d1eee93bc2c20';sp=importlib.util.spec_from_file_location('frozen_reference',frozen);v=importlib.util.module_from_spec(sp);sp.loader.exec_module(v)
sys.argv=['validate_reviews.py','--packet',str(packet),'--reviews',str(reviews),'--schema',str(L/'SCHEMA.json'),'--expected-records',str(len(prior)),'--private-validated',str(D/'PRIOR_VALIDATED_PRIVATE.jsonl'),'--private-errors',str(D/'PRIOR_ERRORS_PRIVATE.jsonl'),'--public-receipt',str(D/'PRIOR_VALIDATION_PUBLIC.json')]
try:
 with contextlib.redirect_stdout(io.StringIO()):v.main()
except SystemExit:pass
vr=read(D/'PRIOR_VALIDATION_PUBLIC.json')
prior_cases={x['case'] for x in prior};queue=[]
for x in inputs:
 if x['stratum']=='existing_Kimi_saved':continue
 if x['row']['context_sha256'] in blocked or x['task'] in blocked_tasks:continue
 queue.append({'case':x['case'],'split':x['split'],'stratum':x['stratum'],'row':x['row'],'qualification_task':x['task']})
assert len(queue)<=350 and not (prior_cases & {x['case'] for x in queue})
(D/'BLIND_NEW_REFERENCE_INPUTS_PRIVATE.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in queue))
report={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'reference_sources_prepared_not_submitted','existing_independent_Kimi_references':len(prior),'existing_Kimi_references_frozen_validation_status':vr['status'],'existing_Kimi_references_validation_counts':vr['counts'],'new_blind_Kimi_inputs_prepared':len(queue),'blocked_cases_removed_no_replacement':500-len(prior)-len(queue),'candidate_answers_read':False,'new_model_calls':0,'new_production_accepted':0,'new_Kimi_route':'existing OpenCode -> Azure Kimi; transport worker not yet launched','serial_legs_required':True,'live_exclusions_must_be_rechecked_at_every_submission':True,'paper_paused':True,'metrics_synthetic_tests':{'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful()},'metrics_measurement':'exact normalized complete semantic tuples; conservative disagreements can include free-text paraphrases; no fuzzy matches or output-guided aliases','quality_gate_evaluated':False,'input_pins':{name:sha(D/name) for name in ['PRIOR_REFERENCE_INPUTS_PRIVATE.jsonl','PRIOR_REFERENCES_PRIVATE.jsonl','BLIND_NEW_REFERENCE_INPUTS_PRIVATE.jsonl','qualification_metrics.py','test_qualification_metrics.py']}}
(D/'REFERENCE_PREFLIGHT_PUBLIC.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
