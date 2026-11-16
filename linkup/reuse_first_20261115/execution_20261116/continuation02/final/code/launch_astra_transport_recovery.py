"""Submit once after proving definite invalid-input rejection for every original audit request."""
import base64,json,sys
from pathlib import Path
from control import HERE,vm,save
code=(HERE/'cloud_astra_transport_recovery_worker.py').read_bytes();plan=(HERE/'ASTRA_TRANSPORT_RECOVERY_PLAN_PUBLIC.json').read_bytes()
script='WORKER_B64='+repr(base64.b64encode(code).decode())+'\nPLAN_B64='+repr(base64.b64encode(plan).decode())+'''\nimport base64,datetime,hashlib,json,os,subprocess,sys,time
from pathlib import Path
os.umask(0o077)
R=Path.home()/'migration';Q=R/'execution_20261116/run001/qualification500_v1';OLD=Q/'astra_audit50_v1';D=Q/'astra_audit50_transport_recovery_v1'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\\n')
s=read(OLD/'RUN_STATUS_PUBLIC.json');proc=Path('/proc')/str(s['pid'])/'cmdline';assert not proc.exists() or str(OLD).encode() not in proc.read_bytes();assert s['completed']==50
for rel,h in read(OLD/'SHA256SUMS_PRIVATE.json').items():assert sha(OLD/rel)==h
assert not D.exists(),'existing_recovery_must_reconcile_no_relaunch';D.mkdir()
for name in ['INPUTS_PRIVATE.jsonl','SCHEMA.json','INSTRUCTIONS.md','EXCLUSIONS_PRIVATE.json','PROTOCOL_PUBLIC.json','SELECTION_PRIVATE.json']:(D/name).write_bytes((OLD/name).read_bytes())
c=read(OLD/'BENCHMARK_CONFIG_PUBLIC.json');c.update(run_id='reuse-qualification500-astra-audit-transport-recovery-v1',max_physical_attempts=100,absolute_deadline_epoch=datetime.datetime.fromisoformat(s['started_at_utc']).timestamp()+14400,prior_rejected_HTTP_attempts=50,prior_reservations_counted=True,max_new_attempts_per_original_input=1)
write(D/'BENCHMARK_CONFIG_PUBLIC.json',c)
pins=read(OLD/'WORKER_INPUT_PINS_PUBLIC.json');pins['files']={n:sha(D/n) for n in pins['files']};write(D/'WORKER_INPUT_PINS_PUBLIC.json',pins)
(D/'ASTRA_TRANSPORT_RECOVERY_PLAN_PUBLIC.json').write_bytes(base64.b64decode(PLAN_B64))
p=D/'cloud_astra_transport_recovery_worker.py';p.write_bytes(base64.b64decode(WORKER_B64));log=(D/'WORKER.log').open('ab')
job=subprocess.Popen([sys.executable,str(p)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
r={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pid':job.pid,'status':'one_shot_same_50_inputs_transport_recovery_launched_not_completed','worker_sha256':sha(p),'same_audit_input_pin':sha(D/'INPUTS_PRIVATE.jsonl'),'audit_budget_cap_including_prior_reservations_usd':100,'original_failed_outputs_preserved':True,'no_production_started':True};write(D/'LAUNCH_PUBLIC.json',r);print(json.dumps(r))
'''
r=vm(script,'launch_astra_transport_recovery001');save(HERE/'ASTRA_TRANSPORT_RECOVERY_LAUNCH_PUBLIC.json',r);print(json.dumps(r))
