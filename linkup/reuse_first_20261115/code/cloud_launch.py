"""Install a hash-pinned bounded worker on the existing VM; never restarts a timer.

PAYLOAD is injected by the local control-plane transport and contains code,
configuration and policy only, never advertisement records or credentials.
"""
import base64, datetime, hashlib, json, os, subprocess, sys, time
from pathlib import Path
R=Path.home()/'migration';D=R/'reuse_first_20261115/run01/benchmark20'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
assert D.exists() and read(D/'PREPARATION_PUBLIC.json')['selected_n']==20
assert sha(D/'INPUTS_PRIVATE.jsonl')=='1a24109c44c6fd619101b65ba2fd5f71043ed49cc16fde90bbefcd097fc6a96e'
assert not (D/'LAUNCH_PUBLIC.json').exists(),'already_launched_do_not_repeat'
for name in ('linkup-astra.timer','linkup-extract.timer','linkup-astra.service','linkup-extract.service'):
    q=subprocess.run(['systemctl','show',name,'-p','ActiveState'],capture_output=True,text=True,check=True)
    assert q.stdout.strip()=='ActiveState=inactive','legacy_worker_active'
os.umask(0o077)
expected={'cloud_benchmark_worker.py','BENCHMARK_CONFIG_PUBLIC.json','POLICY_V5_PUBLIC.json'}
assert set(PAYLOAD)==expected
for name,item in PAYLOAD.items():
    raw=base64.b64decode(item['data']);assert hashlib.sha256(raw).hexdigest()==item['sha256']
    p=D/name
    if p.exists():assert p.read_bytes()==raw
    else:p.write_bytes(raw)
prep=read(D/'PREPARATION_PUBLIC.json')
for name,h in prep['output_sha256'].items():assert sha(D/name)==h
files={n:sha(D/n) for n in ('INPUTS_PRIVATE.jsonl','SCHEMA.json','INSTRUCTIONS.md','BENCHMARK_CONFIG_PUBLIC.json')}
(D/'WORKER_INPUT_PINS_PUBLIC.json').write_text(json.dumps({'files':files,'runtime':prep['pins']},indent=2)+'\n')
L=read(R/'opencode_kimi_20261115/run01/bulk_1309_20261115/CANDIDATE_STATE_PRIVATE.json')
protected={t for t,x in L['exceptions'].items() if x.get('disposition')=='quarantined' or x.get('status','').startswith('quarantined_')}
protected.add('batch052/packet_0095/1')
(D/'EXCLUSIONS_PRIVATE.json').write_text(json.dumps({'tasks':sorted(protected)},indent=2)+'\n')
log=(D/'WORKER.log').open('ab')
p=subprocess.Popen([sys.executable,str(D/'cloud_benchmark_worker.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
report={'status':'finite_worker_process_started','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pid':p.pid,'worker_sha256':sha(D/'cloud_benchmark_worker.py'),'input_sha256':sha(D/'INPUTS_PRIVATE.jsonl'),'config_sha256':sha(D/'BENCHMARK_CONFIG_PUBLIC.json'),'policy_sha256':sha(D/'POLICY_V5_PUBLIC.json'),'role':'independent candidate benchmark not production','max_records':20,'reservation_cap_usd':1.0,'max_wall_seconds':1800,'model':'gpt-6-luna','unix_user':'linkup','identity_type':'existing VM system-assigned managed identity','timer_restarted':False,'new_gpu_vm_ptu':0}
(D/'LAUNCH_PUBLIC.json').write_text(json.dumps(report,indent=2)+'\n')
pointer={'policy_id':'linkup-reuse-first-v5','policy_path':str(D/'POLICY_V5_PUBLIC.json'),'policy_sha256':sha(D/'POLICY_V5_PUBLIC.json'),'current_run':str(D),'status':'finite_candidate_benchmark_started','global_inference_running':False,'human_review_required':False,'legacy_timers_restarted':False}
old=R/'CURRENT_RESEARCH_POLICY_PUBLIC.json';backup=R/'CURRENT_RESEARCH_POLICY_BEFORE_REUSE_FIRST_PUBLIC.json'
if old.exists() and not backup.exists():backup.write_bytes(old.read_bytes())
old.write_text(json.dumps(pointer,indent=2)+'\n')
time.sleep(2)
report['worker_alive_after_launch']=p.poll() is None
if (D/'RUN_STATUS_PUBLIC.json').exists():report['initial_status']=read(D/'RUN_STATUS_PUBLIC.json')
print(json.dumps(report,separators=(',',':')))
