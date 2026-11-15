"""One finite task coordinator, not a timer, recurring service, or production job.

Wait for current candidate, then run new blind Kimi references, then <=50 Astra
audits. Never restart the Luna worker or auto-admit a production record.
"""
import base64,datetime,fcntl,json,os,subprocess,sys,time,traceback
from pathlib import Path
from control import HERE,W,vm,save
os.umask(0o077)
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def note(phase,**extra):
 x={'at_utc':now(),'phase':phase,'pid':os.getpid(),'finite_qualification_only':True,'new_production_accepted':0,**extra};save(HERE/'COORDINATOR_PUBLIC.json',x);print(json.dumps(x),flush=True)
def snapshot(tag):
 x=vm((HERE/'cloud_status.py').read_text(),tag);save(HERE/'LATEST_CLOUD_STATUS_PUBLIC.json',x);return x
def start_kimi():
 assert not (W/'WORKER_LAUNCH_PUBLIC.json').exists(),'prior_worker_reconcile_no_duplicate_start'
 log=(W/'GATEWAY.log').open('ab')
 env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}
 g=subprocess.Popen([sys.executable,str(HERE/'kimi_gateway.py')],cwd=HERE,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,env=env)
 for _ in range(50):
  if (W/'GATEWAY_PUBLIC.json').exists():break
  assert g.poll() is None,'gateway_start_failed';time.sleep(.2)
 gateway=json.loads((W/'GATEWAY_PUBLIC.json').read_text());assert gateway['pid']==g.pid
 loopback='.'.join(map(str,(127,0,0,1)))
 old=Path.home()/'.local/share/opencode/private/linkup-kimi-bulk1309-20261115/opencode.json'
 config=json.loads(old.read_text());config['providers']['azure-kimi']['settings']['baseURL']=f"http://{loopback}:{gateway['port']}/qualification350/openai/v1"
 save(W/'opencode.json',config)
 log=(W/'WORKER.log').open('ab')
 p=subprocess.Popen([sys.executable,str(HERE/'kimi_worker.py')],cwd=HERE,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,env=env)
 save(W/'WORKER_LAUNCH_PUBLIC.json',{'pid':p.pid,'gateway_pid':g.pid,'at_utc':now(),'configuration_scope':'isolated_project_only','original_opencode_configuration_unchanged':True})
 note('Kimi_reference_leg_started',worker_pid=p.pid)
 while p.poll() is None:time.sleep(30)
 assert p.returncode==0,'Kimi_worker_not_complete_preserve_reconcile'
 s=json.loads((HERE/'KIMI_FINAL_PUBLIC.json').read_text());assert s['finished']==350 and s['cloud_validated']==350,'Kimi_missing_cloud_results'
 note('Kimi_reference_leg_cloud_complete',frozen_pass=s['cloud_frozen_pass_references'],physical_attempts=s['physical_attempts'])
def start_astra():
 answer=vm((HERE/'cloud_evaluate_prepare_audit.py').read_text(),'evaluate_prepare_audit001');save(HERE/'REFERENCE_COMPARISON_SUMMARY_PUBLIC.json',answer)
 code=(HERE/'cloud_astra_audit_worker.py').read_bytes()
 launch="""import base64,json,os,subprocess,sys,time,hashlib
from pathlib import Path
R=Path.home()/'migration';Q=R/'execution_20261116/run001/qualification500_v1';K=Q/'kimi_reference350_v1';D=Q/'astra_audit50_v1'
lease=K/'LEASE_PRIVATE.json';x=json.loads(lease.read_text());x['release']=True;lease.write_text(json.dumps(x))
for _ in range(20):
 p=Path('/proc')/str(x['pid'])/'cmdline'
 if not p.exists() or str(K/'hold_reference_lane.py').encode() not in p.read_bytes():break
 time.sleep(1)
else:raise RuntimeError('reference_lock_not_released')
assert not (D/'RUN_STATUS_PUBLIC.json').exists() and not (D/'ATTEMPTS_PRIVATE.jsonl').exists(),'existing_Astra_attempt_do_not_restart'
source=D/'cloud_astra_audit_worker.py';code=base64.b64decode(CODE_B64)
if source.exists():assert source.read_bytes()==code
else:source.write_bytes(code)
log=(D/'WORKER.log').open('ab');p=subprocess.Popen([sys.executable,str(source)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
r={'pid':p.pid,'worker_sha256':hashlib.sha256(code).hexdigest(),'status':'independent_Astra_audit_started_not_finished','production_started':False}
(D/'LAUNCH_PUBLIC.json').write_text(json.dumps(r,indent=2)+'\\n');print(json.dumps(r))
"""
 result=vm('CODE_B64='+repr(base64.b64encode(code).decode())+'\n'+launch,'launch_astra_audit001');save(HERE/'ASTRA_AUDIT_LAUNCH_PUBLIC.json',result);note('Astra_independent_audit_started',worker_pid=result['pid'])
def main():
 lock=(W/'COORDINATOR.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 note('waiting_for_existing_Luna_no_restart')
 deadline=time.time()+12*3600;poll=0
 while time.time()<deadline:
  s=snapshot(f'protocol_status_{poll:04d}');poll+=1;l=s['Luna']
  if l['status']=='finite_benchmark_completed' and l['completed']==500 and not l['alive_exact_command']:break
  assert l['alive_exact_command'],'candidate_stopped_before_completion_reconcile'
  note('waiting_for_existing_Luna_no_restart',candidate_completed=l['completed'],candidate_engineering_pass=l['engineering_pass']);time.sleep(240)
 else:raise RuntimeError('coordinator_candidate_wait_bound')
 start_kimi();start_astra()
 while time.time()<deadline:
  s=snapshot(f'protocol_status_{poll:04d}');poll+=1;a=s['Astra']
  if a.get('status')=='finite_benchmark_completed' and not a.get('alive_exact_command'):break
  assert a.get('alive_exact_command'),'Astra_stopped_before_finish_reconcile';time.sleep(180)
 else:raise RuntimeError('coordinator_total_wall_bound')
 note('fixed_model_legs_finished_ready_for_final_decision',candidate_completed=s['Luna']['completed'],Astra_completed=s['Astra']['completed'])
if __name__=='__main__':
 try:main()
 except Exception as error:
  (W/'COORDINATOR_ERROR_PRIVATE.txt').write_text(traceback.format_exc());note('control_stopped_outputs_preserved',error_type=type(error).__name__);raise SystemExit(2)
