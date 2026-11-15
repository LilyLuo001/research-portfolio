"""Start only the bounded candidate leg after immutable inputs and code tests.

FILES_B64 is injected by the local control-plane loader from public source files.
No credentials or advertisements are embedded in that loader.
"""
import base64, datetime, fcntl, hashlib, json, os, subprocess, sys, time
from pathlib import Path
R=Path.home()/'migration'; Q=R/'execution_20261116/run001/qualification500_v1'; D=Q/'luna'
def sha(p): return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def read(p): return json.loads(p.read_bytes())
def save(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def main():
    os.umask(0o077)
    assert read(Q/'PREPARATION_PUBLIC.json')['selected_inputs']==500
    assert sha(Q/'INPUTS_PRIVATE.jsonl')=='e750ffd9f34596e558c8350f51fe3bafb86d26e2568eb16e2c029250848c0c72'
    assert not D.exists(), 'partial_or_existing_run_preserved_do_not_relaunch'
    locks=[]
    for p in [R/'astra/extraction/runner.lock',R/'astra/agent.lock']:
        f=p.open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    active=[]
    for p in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            argv=p.read_bytes().split(b'\0')
            if any(Path(v.decode(errors='ignore')).name in ['cloud_benchmark_worker.py','cloud_qualification_luna_worker.py','bulk_worker.py','bulk_worker_parallel8.py'] for v in argv):active.append(int(p.parent.name))
        except OSError: pass
    assert not active,'another_known_model_worker_active'
    sourcepins=read(Q/'PINS_PRIVATE.json')
    for rel,d in sourcepins['source'].items(): assert sha(R/rel)==d
    D.mkdir()
    for name,encoded in FILES_B64.items():
        assert name in ['cloud_qualification_luna_worker.py','BENCHMARK_CONFIG_PUBLIC.json','PROTOCOL_PUBLIC.json','SYNTHETIC_TEST_PUBLIC.json','EXECUTION_AUTHORIZATION_PUBLIC.json']
        (D/name).write_bytes(base64.b64decode(encoded))
    assert read(D/'SYNTHETIC_TEST_PUBLIC.json')['status']=='pass'
    C=read(D/'BENCHMARK_CONFIG_PUBLIC.json')
    assert C['max_records']==500 and C['run_reservation_cap_usd']==15 and C['scheduled_tpm_ceiling']==80000
    assert C['stage3_allocation_caps_usd']=={'Luna':15,'Kimi':135,'Astra':100}
    rows=[json.loads(l) for l in (Q/'INPUTS_PRIVATE.jsonl').open()]
    for row in rows:row['task']='qualification500/'+row['case']
    (D/'INPUTS_PRIVATE.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows))
    for n in ['SCHEMA.json','INSTRUCTIONS.md','EXCLUSIONS_PRIVATE.json']:(D/n).write_bytes((Q/n).read_bytes())
    # The candidate worker has no path to a reference answer in its inputs/config.
    sourcepins['source']['execution_20261116/run001/qualification500_v1/INPUTS_PRIVATE.jsonl']=sha(Q/'INPUTS_PRIVATE.jsonl')
    save(D/'WORKER_INPUT_PINS_PUBLIC.json',{'files':{n:sha(D/n) for n in ['INPUTS_PRIVATE.jsonl','SCHEMA.json','INSTRUCTIONS.md','BENCHMARK_CONFIG_PUBLIC.json','PROTOCOL_PUBLIC.json','cloud_qualification_luna_worker.py']},'runtime':sourcepins['runtime'],'original_sources':sourcepins['source']})
    save(D/'ADMISSION_PUBLIC.json',{'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'candidate_leg_admitted_only','selected':500,'existing_reference_answers_not_in_request_payload':True,'candidate_cap_usd':15,'stage3_total_cap_usd':250,'step4_not_admitted':True,'paper_paused':True,'automatic_reference_or_production_launch':False,'worker_sha256':sha(D/'cloud_qualification_luna_worker.py')})
    for f in locks:fcntl.flock(f,fcntl.LOCK_UN);f.close()
    log=(D/'WORKER.log').open('ab')
    proc=subprocess.Popen([sys.executable,str(D/'cloud_qualification_luna_worker.py')],cwd=R,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True);log.close()
    save(D/'LAUNCH_PUBLIC.json',{'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pid':proc.pid,'status':'process_spawned_check_results_for_real_execution','worker_sha256':sha(D/'cloud_qualification_luna_worker.py'),'max_records':500,'candidate_nominal_reservation_cap_usd':15,'stage3_cap_usd':250,'no_production_admission':True})
    time.sleep(3)
    result=read(D/'LAUNCH_PUBLIC.json');result['process_alive_after_3s']=proc.poll() is None
    if (D/'RUN_STATUS_PUBLIC.json').exists():result['observed_run_status']=read(D/'RUN_STATUS_PUBLIC.json')
    print(json.dumps(result))
if __name__=='__main__':
    try:main()
    except Exception as e:
        import traceback
        (Q/'LAUNCH_FAILURE_PRIVATE.txt').write_text(traceback.format_exc())
        print(json.dumps({'status':'qualification_launch_failed_preserved','type':type(e).__name__}));raise SystemExit(2)
