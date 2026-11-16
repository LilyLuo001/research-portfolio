"""Build a one-shot transport-only recovery, keeping all rejected attempts and caps in view."""
import ast,hashlib,json
from pathlib import Path
W=Path(__file__).parent
s=(W/'cloud_astra_audit_worker.py').read_text()
def replace(a,b):
 global s
 assert s.count(a)==1,(a[:80],s.count(a));s=s.replace(a,b)
replace("D=R/'execution_20261116/run001/qualification500_v1/astra_audit50_v1'","D=R/'execution_20261116/run001/qualification500_v1/astra_audit50_transport_recovery_v1';OLD=D.with_name('astra_audit50_v1')")
replace("C['max_physical_attempts']<=60","C['max_physical_attempts']<=100")
replace("log=D/'ATTEMPTS_PRIVATE.jsonl';history=[]\n    if log.exists():history=[json.loads(x) for x in log.read_text().splitlines()]", """log=D/'ATTEMPTS_PRIVATE.jsonl';history=[json.loads(x) for x in (OLD/'ATTEMPTS_PRIVATE.jsonl').read_text().splitlines()]
    if log.exists():history += [json.loads(x) for x in log.read_text().splitlines()]""")
replace("        events={}\n        if log.exists():", "        events={(e['ordinal'],e['attempt']):e for e in history}\n        if log.exists():")
replace("        if prior:\n            # An interrupted prior request is not automatically sent again, even if its result is missing.", "        if any(e['attempt']>=2 for e in prior):\n            # A second attempt is never repeated, even if its result is missing.")
replace("'input':json.dumps({k:row[k]", "'input':'Return JSON.\\n'+json.dumps({k:row[k]")
replace("for attempt in range(1,C['max_attempts_per_record']+1):", "for attempt in range(2,3):")
replace("if response.status in (401,403):state['status']='authentication_or_authorization_failed';outcome={'status':'http_auth_failed'};break", "if response.status in (400,401,403,404):state['status']='systemic_HTTP_failure_stop_preserve';outcome={'status':'systemic_http_error_preserved','http_status':response.status};break")
replace("if state['status']=='authentication_or_authorization_failed':break", "if state['status'] in ('authentication_or_authorization_failed','systemic_HTTP_failure_stop_preserve'):break")
# Recovery requires definite request-validation rejections, never a refusal, filter,
# uncertain submission or prior model-generated answer. No research judgment is rerun.
a="    C=read(D/'BENCHMARK_CONFIG_PUBLIC.json');"
b="""    old_state=read(OLD/'RUN_STATUS_PUBLIC.json')
    assert old_state['status']=='finite_benchmark_completed' and old_state['completed']==50
    assert old_state['physical_attempts']==50 and old_state['input_tokens']==old_state['output_tokens']==0
    for rel,h in read(OLD/'SHA256SUMS_PRIVATE.json').items():assert sha(OLD/rel)==h
    old_events={}
    for line in (OLD/'ATTEMPTS_PRIVATE.jsonl').read_text().splitlines():
        e=json.loads(line);old_events[e['ordinal'],e['attempt']]=e
    assert len(old_events)==50 and all(e['attempt']==1 and e.get('http_status')==400 and e['status']=='http_error' and not e.get('provider_content_filter') for e in old_events.values())
    for i in range(50):
        err=read(OLD/'results'/f'case{i:04d}'/'HTTP_RESPONSE_attempt01_PRIVATE.bin')['error']
        assert err['type']=='invalid_request_error' and err['param']=='input' and "must contain the word 'json'" in err['message']
    assert sha(D/'INPUTS_PRIVATE.jsonl')==sha(OLD/'INPUTS_PRIVATE.jsonl')
    C=read(D/'BENCHMARK_CONFIG_PUBLIC.json');"""
replace(a,b)
ast.parse(s);p=W/'cloud_astra_transport_recovery_worker.py';p.write_text(s)
r={'recovery_worker_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'original_worker_sha256':hashlib.sha256((W/'cloud_astra_audit_worker.py').read_bytes()).hexdigest(),'transport_fix':'Add Return JSON to the Responses API input, as required by json_object; unchanged original instructions, schema, reasoning effort and selected source content.','model_outputs_to_rerun':0,'definite_HTTP400_input_validation_rejections_preserved':50,'same_unique_audit_inputs':50,'attempts_per_input_max_including_original':2,'previous_self_imposed_HTTP_subcap':60,'recovery_HTTP_cap_including_original':100,'reason_for_HTTP_subcap_change':'One additional request per same audit input after definite pre-inference request rejection; no retries beyond attempt2. The original $100 audit reservation budget includes all first-attempt reservations and is unchanged.','user_stage3_dollar_cap_unchanged':250,'audit_dollar_cap_unchanged':100,'qualification_thresholds_unchanged':True,'first_new_systemic_HTTP_error_stops_recovery':True,'no_new_model_or_sample':True}
(W/'ASTRA_TRANSPORT_RECOVERY_PLAN_PUBLIC.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
