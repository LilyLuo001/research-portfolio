"""Resume only the proved zero-submission reference leg; no model queue reset."""
import datetime,hashlib,json,os,subprocess,sys,time
from pathlib import Path
from control import HERE,W,vm,save
os.umask(0o077)
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
assert not list((W/'records').glob('*/EXECUTION_PRIVATE.json')),'submissions_need_individual_reconciliation'
assert not (W/'GATEWAY_ATTEMPTS_PRIVATE.jsonl').exists(),'existing_admission_attempts_need_reconciliation'
old=json.loads((W/'WORKER_LAUNCH_PUBLIC.json').read_text())
try:os.kill(old['pid'],0)
except ProcessLookupError:pass
else:raise RuntimeError('old_worker_alive')
assert subprocess.run(['ps','-p',str(old['gateway_pid']),'-o','command='],capture_output=True,text=True).stdout.strip().endswith(str(HERE/'kimi_gateway.py'))
recovery="""import datetime,json,os,time,hashlib
from pathlib import Path
R=Path.home()/'migration';Q=R/'execution_20261116/run001/qualification500_v1';D=Q/'kimi_reference350_v1'
p=D/'LEASE_PRIVATE.json';x=json.loads(p.read_text());proc=Path('/proc')/str(x['pid'])/'cmdline'
assert not proc.exists() or str(D/'hold_reference_lane.py').encode() not in proc.read_bytes(),'prior_guard_alive'
assert time.time()>x['expires_epoch']
assert not list((D/'results').glob('*/RESULT_PUBLIC.json')) and not list((D/'commits').glob('*/RECEIPT_PUBLIC.json'))
assert not (Q/'astra_audit50_v1/ATTEMPTS_PRIVATE.jsonl').exists()
archive=D/'LEASE_EXPIRED_FIRST_ATTEMPT_PRIVATE.json';assert not archive.exists();p.rename(archive)
r={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'expired_guard_dead':True,'new_model_submissions_before_recovery':0,'cloud_reference_results_before_recovery':0,'old_lease_preserved_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'original_candidate_not_restarted':True,'cause':'ARM_result_poll_read_timeout_after_lease_was_created','no_research_definition_change':True}
(D/'LEASE_RECOVERY_PUBLIC.json').write_text(json.dumps(r,indent=2)+'\\n');print(json.dumps(r))
"""
r=vm(recovery,'recover_expired_zero_submission_lease001');save(HERE/'LEASE_RECOVERY_PUBLIC.json',r)
for name in ('WORKER_LAUNCH_PUBLIC.json','WORKER_CODE_IDENTITY_PUBLIC.json','RUN_STATUS_PUBLIC.json'):
 source=W/name;dest=W/('INITIAL_'+name);assert not dest.exists();dest.write_bytes(source.read_bytes())
log=(W/'WORKER_RESUME.log').open('ab')
p=subprocess.Popen([sys.executable,str(HERE/'kimi_worker.py')],cwd=HERE,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
save(W/'WORKER_RESUME_LAUNCH_PUBLIC.json',{'pid':p.pid,'at_utc':now(),'gateway_pid':old['gateway_pid'],'new_model_attempts_before_resume':0,'old_failed_control_preserved':True})
print(json.dumps({'worker_pid':p.pid,'state':'resumed_zero_submission_reference_leg'}),flush=True)
p.wait()
assert p.returncode==0,'reference_worker_stopped_reconcile'
from continue_fixed_protocol import start_astra,snapshot,note
s=json.loads((HERE/'KIMI_FINAL_PUBLIC.json').read_text());assert s['finished']==350 and s['cloud_validated']==350
start_astra();deadline=time.time()+5*3600;poll=0
while time.time()<deadline:
 s=snapshot('resumed_audit_status_'+str(poll));poll+=1;a=s['Astra']
 if a.get('status')=='finite_benchmark_completed' and not a.get('alive_exact_command'):break
 assert a.get('alive_exact_command'),'audit_stopped_reconcile';time.sleep(180)
else:raise RuntimeError('finite_audit_wait_bound')
note('fixed_model_legs_finished_ready_for_final_decision')
