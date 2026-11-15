"""Repair trusted assignment only; never repeat any prior model request.

All v1 files remain intact. Prior returned responses are revalidated, and prior
attempt/budget history is inherited. Inference schema, prompt and 500 cases stay fixed.
FILES_B64 contains public v2 worker and real-contract test, injected by control.
"""
import base64, collections, datetime, fcntl, hashlib, importlib.util, json, os, shutil, subprocess, sys, time
from pathlib import Path
R=Path.home()/'migration';Q=R/'execution_20261116/run001/qualification500_v1';A=Q/'luna';D=Q/'luna_revision002'
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def read(p):return json.loads(p.read_bytes())
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def main():
    os.umask(0o077);stop=read(Q/'PACKAGING_FAULT_STOP_PUBLIC.json');assert stop['no_inflight_request_at_stop']
    oldstatus=read(A/'RUN_STATUS_PUBLIC.json');proc=Path('/proc')/str(oldstatus['pid'])
    if proc.exists():assert (proc/'stat').read_text().split(') ',1)[1].split()[0]=='Z'
    assert not D.exists(),'repair_revision_exists_preserve_no_relaunch'
    original={p.relative_to(A).as_posix():sha(p) for p in A.rglob('*') if p.is_file() and p.name not in ['WORKER.lock','WORKER.log']}
    locks=[]
    for p in [R/'astra/extraction/runner.lock',R/'astra/agent.lock']:
        f=p.open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    D.mkdir();(D/'results').mkdir()
    for name,data in FILES_B64.items():(D/name).write_bytes(base64.b64decode(data))
    assert read(D/'REAL_PACKET_CONTRACT_TEST_PUBLIC.json')['status']=='pass'
    rows=[json.loads(l) for l in (A/'INPUTS_PRIVATE.jsonl').open()];original_messages=[]
    for x in rows:
        assert set(x['row'])=={'record_id','context_sha256','full_document'}
        original_messages.append(json.dumps({k:x['row'][k] for k in ('record_id','context_sha256','full_document')},ensure_ascii=False))
        x['row']['assignment']={'packet_id':x['task'],'reviewer_role':'blind_audit','provenance':'Bounded independent machine qualification; unchanged original context, no historical-result replacement'}
    assert len(rows)==500
    assert original_messages==[json.dumps({k:x['row'][k] for k in ('record_id','context_sha256','full_document')},ensure_ascii=False) for x in rows]
    (D/'INPUTS_PRIVATE.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows))
    for n in ['SCHEMA.json','INSTRUCTIONS.md','EXCLUSIONS_PRIVATE.json','PROTOCOL_PUBLIC.json','ATTEMPTS_PRIVATE.jsonl','ORIGINAL_LEDGER_PINS_PUBLIC.json']:
        if (A/n).exists():shutil.copy2(A/n,D/n)
    c=read(A/'BENCHMARK_CONFIG_PUBLIC.json');c['absolute_deadline_epoch']=datetime.datetime.fromisoformat(oldstatus['started_at_utc']).timestamp()+43200
    save(D/'BENCHMARK_CONFIG_PUBLIC.json',c)
    frozen=R/'code/validate_reviews.py';assert sha(frozen)=='f7737143004374f9391a16ad2d1bab2fa47950c589232510045d1eee93bc2c20'
    sp=importlib.util.spec_from_file_location('frozen',frozen);v=importlib.util.module_from_spec(sp);sp.loader.exec_module(v)
    v.validate_packet([x['row'] for x in rows])
    history={}
    for l in (D/'ATTEMPTS_PRIVATE.jsonl').open():
        x=json.loads(l);history[x['ordinal'],x['attempt']]=x
    assert not any(x['status']=='forwarding_uncertain' for x in history.values())
    reused=[];counts=collections.Counter()
    for ordinal in sorted({i for i,a in history}):
        src=A/'results'/f'case{ordinal:04d}';dst=D/'results'/f'case{ordinal:04d}';shutil.copytree(src,dst)
        (dst/'INPUT_PRIVATE.jsonl').write_text(json.dumps(rows[ordinal]['row'],ensure_ascii=False)+'\n')
        oldresult=read(src/'RESULT_PUBLIC.json') if (src/'RESULT_PUBLIC.json').exists() else {'status':'attempt_preserved_without_final_result'}
        # The originally misleading validation-failure status stays in the old revision.
        # A new receipt is computed from the identical saved response and repaired trusted wrapper.
        if (src/'REVIEW_PRIVATE.jsonl').exists():
            sys.argv=['validate_reviews.py','--packet',str(dst/'INPUT_PRIVATE.jsonl'),'--reviews',str(src/'REVIEW_PRIVATE.jsonl'),'--schema',str(D/'SCHEMA.json'),'--expected-records','1','--private-validated',str(dst/'VALIDATED_PRIVATE.jsonl'),'--private-errors',str(dst/'ERRORS_PRIVATE.jsonl'),'--public-receipt',str(dst/'VALIDATION_PUBLIC.json')]
            try:v.main()
            except SystemExit:pass
            assert (dst/'VALIDATION_PUBLIC.json').exists(),'real_validator_receipt_required_before_restart'
            status='frozen_validator_pass_candidate_only' if read(dst/'VALIDATION_PUBLIC.json')['status']=='pass' else 'frozen_validation_failed_preserve_output'
            result={**oldresult,'status':status,'response_reused_no_model_call':True,'prior_result_sha256':sha(src/'RESULT_PUBLIC.json') if (src/'RESULT_PUBLIC.json').exists() else None}
        else:result={**oldresult,'response_or_attempt_preserved_no_model_call':True}
        save(dst/'RESULT_PUBLIC.json',result);counts[result['status']]+=1
        reused.append({'case':f'case{ordinal:04d}','original_result_status':oldresult['status'],'new_validation_status':result['status'],'original_review_sha256':sha(src/'REVIEW_PRIVATE.jsonl') if (src/'REVIEW_PRIVATE.jsonl').exists() else None})
    assert all(sha(A/n)==d for n,d in original.items()),'old_revision_changed'
    save(D/'REUSED_RESPONSE_MAP_PRIVATE.json',reused)
    pins=read(A/'WORKER_INPUT_PINS_PUBLIC.json');pins['files']={n:sha(D/n) for n in ['INPUTS_PRIVATE.jsonl','SCHEMA.json','INSTRUCTIONS.md','BENCHMARK_CONFIG_PUBLIC.json','PROTOCOL_PUBLIC.json','cloud_qualification_luna_worker.py']};save(D/'WORKER_INPUT_PINS_PUBLIC.json',pins)
    receipt={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'trusted_assignment_repaired_saved_responses_revalidated','complete_inputs_preflighted_with_actual_frozen_validator':500,'prior_attempts_inherited':len(history),'prior_cases_not_resubmitted':len(reused),'reused_response_outcomes':dict(counts),'old_revision_unchanged':True,'model_message_schema_prompt_and_contexts_unchanged':True,'research_definition_changed':False,'inference_requests_during_repair':0,'old_reservation_usd_inherited':sum(x['reservation_usd'] for x in history.values()),'same_candidate_cap_usd':15,'same_stage3_cap_usd':250,'new_production_accepted':0,'worker_sha256':sha(D/'cloud_qualification_luna_worker.py')}
    save(D/'PACKAGING_REPAIR_PUBLIC.json',receipt)
    for f in locks:fcntl.flock(f,fcntl.LOCK_UN);f.close()
    log=(D/'WORKER.log').open('ab');proc=subprocess.Popen([sys.executable,str(D/'cloud_qualification_luna_worker.py')],cwd=R,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True);log.close();time.sleep(3)
    receipt['resumed_pid']=proc.pid;receipt['resumed_process_alive']=proc.poll() is None
    if (D/'RUN_STATUS_PUBLIC.json').exists():receipt['live_snapshot']=read(D/'RUN_STATUS_PUBLIC.json')
    save(D/'RESUME_PUBLIC.json',receipt)
    pointer=read(R/'CURRENT_EXECUTION_PUBLIC.json');pointer['qualification_status_relative_to_migration']='execution_20261116/run001/qualification500_v1/luna_revision002/RUN_STATUS_PUBLIC.json';pointer['qualification_repair_receipt_relative_to_migration']='execution_20261116/run001/qualification500_v1/luna_revision002/PACKAGING_REPAIR_PUBLIC.json';save(R/'CURRENT_EXECUTION_PUBLIC.json',pointer);save(Q.parent/'AZURE_RESEARCH_STATE.json',pointer)
    print(json.dumps(receipt))
if __name__=='__main__':
    try:main()
    except Exception as e:
        import traceback
        (Q/'REPAIR_FAILURE_PRIVATE.txt').write_text(traceback.format_exc());print(json.dumps({'status':'packaging_repair_failed_preserved','type':type(e).__name__}));raise SystemExit(2)
