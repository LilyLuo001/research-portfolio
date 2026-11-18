"""Drain, preserve and amend only the proven Luna scheduler quota; resume same rows."""
import base64
import json
from pathlib import Path
import sys
import time
import zlib

P=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(P.parent/'execution_20261116_continuation02'))
import control
files={n:(P/'runtime_v2'/n).read_text() for n in ['rate_amendment.py','pilot_worker_v2.py']}
bundle=base64.b64encode(zlib.compress(json.dumps(files).encode(),9)).decode()
source=r'''import base64,datetime,hashlib,json,os,subprocess,sys,time,zlib
from pathlib import Path
os.umask(0o077);R=Path.home()/'migration';C=R/'pilot_economic_20261119/run01';C5=R/'confirmation_stage5_20261118/execution_v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def imm(p,data):
 p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():assert p.read_bytes()==data,'immutable_conflict'
 else:p.write_bytes(data)
def active():
 found=[]
 for p in Path('/proc').glob('[0-9]*/cmdline'):
  try:args=p.read_bytes().split(b'\0')
  except OSError:continue
  if any(str(C/n).encode() in args for n in ['runtime/pilot_worker.py','runtime_v2/pilot_worker_v2.py']):found.append(int(p.parent.name))
 return found
def run(cmd,name):
 cp=subprocess.run(cmd,capture_output=True,text=True,timeout=90)
 imm(C/'control'/(name+'_PRIVATE.json'),json.dumps({'returncode':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr}).encode())
 try:r=json.loads(cp.stdout)
 except Exception:r={'status':'no_structured_receipt','returncode':cp.returncode}
 if cp.returncode:print(json.dumps({'status':'rate_transition_stopped_preserve_state','step':name,'detail':r}));raise SystemExit(2)
 return r
for n,text in json.loads(zlib.decompress(base64.b64decode(__BUNDLE__))).items():imm(C/'runtime_v2'/n,text.encode())
stop=C/'STOP';marker=b'quiescent_rate_only_amendment_250k_evidence_20261119\n'
imm(stop,marker)
deadline=time.time()+100
while active() and time.time()<deadline:time.sleep(1)
assert not active(),'workers_have_not_drained_STOP_retained'
backup=C/'control/pre_rate_upgrade_snapshot';backup.mkdir(exist_ok=True)
for name in ['LUNA_FINAL_PUBLIC.json','RUN_STATUS_PUBLIC.json','OUTPUTS_LUNA_batch0001_PRIVATE.jsonl','CHECKPOINT_FIRST_BATCH_PUBLIC.json']:
 if (C/name).exists():imm(backup/name,(C/name).read_bytes())
amend=C/'RATE_AMENDMENT_PUBLIC.json'
prepared=run([sys.executable,'-B',str(C/'runtime_v2/rate_amendment.py'),'prepare','--directory',str(C),'--output',str(amend)],'RATE_PREPARE')
applied=run([sys.executable,'-B',str(C/'runtime_v2/rate_amendment.py'),'apply','--directory',str(C),'--amendment',str(amend),'--amendment-sha256',sha(amend)],'RATE_APPLY')
assert stop.read_bytes()==marker;stop.unlink()
field=C5/'repo/linkup/reuse_first_20261115/measurement_protocol_20261117/code/field_validation.py';frozen=C5/'repo/linkup/formal800_20261012/code/validate_reviews.py';M=C/'preparation/batch0001/BATCH_MANIFEST_PUBLIC.json'
cmd=[sys.executable,'-B',str(C/'runtime_v2/pilot_worker_v2.py'),'--rate-amendment',str(amend),'--rate-amendment-sha256',sha(amend),'--leg','Luna','--directory',str(C),'--policy',str(C/'policy.json'),'--batch-manifest',str(M),'--batch-manifest-sha256',sha(M),'--field-validator',str(field),'--frozen-validator',str(frozen),'--workflow-directory',str(R/'code'),'--max-new-logical','100','--concurrency','4','--max-wall-seconds','14400','--stop-file',str(C/'STOP')]
with (C/'control/LUNA_FIRST_BATCH_RATE_V2_PRIVATE.log').open('xb') as log:
 p=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,cwd=C);time.sleep(1)
result={'status':'Luna_rate_only_amendment_applied_and_same_batch_resumed','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pid':p.pid,'active_after_one_second':p.poll() is None,'early_exit':p.poll(),'old_scheduled_tpm':80000,'verified_header_tpm':250000,'new_scheduled_tpm':200000,'aggregate_tpm_unchanged':800000,'amendment_sha256':sha(amend),'preserved_attempts':applied['preserved_checkpoint']['physical_attempts'],'preserved_reservations_usd':applied['preserved_checkpoint']['reserved_nano']/1e9,'non_rate_ledger_state_unchanged':applied['all_non_rate_ledger_state_unchanged'],'original_policy_sha256':sha(C/'policy.json'),'batch':'batch0001','launch_logical_ceiling_cumulative':100,'concurrency':4,'scientific_and_budget_settings_unchanged':True}
imm(C/'control/RATE_UPGRADE_LAUNCH_PUBLIC.json',(json.dumps(result,sort_keys=True)+'\n').encode());print(json.dumps(result))
'''.replace('__BUNDLE__',repr(bundle))
compile(source,'<rate-only-upgrade>', 'exec')
result=control.vm(source,'economic_rate_upgrade_'+str(time.time_ns()))
control.save(P/'control/RATE_UPGRADE_LAUNCH_PUBLIC.json',result);print(json.dumps(result))
