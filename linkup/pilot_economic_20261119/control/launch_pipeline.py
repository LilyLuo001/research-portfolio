"""Install final tested projection and launch one finite <=10000-row controller."""
import base64
import json
from pathlib import Path
import sys
import time
import zlib

P=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(P.parent/'execution_20261116_continuation02'))
import control
files={
 'control/finite_pipeline.py':(P/'control/finite_pipeline.py').read_text(),
 'control/profile_run.py':(P/'control/profile_run.py').read_text(),
 'measurement/publish_physical_v2.py':(P/'measurement/publish_physical.py').read_text()}
bundle=base64.b64encode(zlib.compress(json.dumps(files).encode(),9)).decode()
source=r'''import base64,datetime,hashlib,json,os,subprocess,sys,time,zlib
from pathlib import Path
os.umask(0o077);C=Path.home()/'migration/pilot_economic_20261119/run01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def imm(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():assert p.read_bytes()==b,'immutable_collision'
 else:p.write_bytes(b)
assert not (C/'control/FINITE_PIPELINE_LAUNCH_PUBLIC.json').exists(),'supervisor_already_launched_no_duplicate'
files=json.loads(zlib.decompress(base64.b64decode(__BUNDLE__)))
for n,t in files.items():
 p=C/n;b=t.encode();compile(b,str(p),'exec')
 if n=='measurement/publish_physical_v2.py' and p.exists() and p.read_bytes()!=b:
  assert not (C/'projection').exists(),'projection_already_used_do_not_mutate'
  assert sha(p)=='3541b3d191a85477bbb91163429f0b7fdf6935a3e15b53b863fba965df15fb58','unexpected_projection_version'
  imm(C/'measurement/publish_physical_v2_before_quarantine_guard.py',p.read_bytes())
  tmp=p.with_suffix('.next');tmp.write_bytes(b);os.replace(tmp,p)
 else:imm(p,b)
cmd=[sys.executable,'-B',str(C/'control/finite_pipeline.py'),'--directory',str(C),'--concurrency','4','--max-wall-seconds','172800']
with (C/'control/FINITE_PIPELINE_PRIVATE.log').open('xb') as log:
 p=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,cwd=C);time.sleep(1)
result={'status':'finite_10000_physical_row_controller_launched','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pid':p.pid,'active_after_one_second':p.poll() is None,'early_exit':p.poll(),'physical_row_cap':10000,'pilot_usd_cap':150,'wall_seconds_cap':172800,'concurrency':4,'same_policy_and_shared_ledger':True,'new_GPU_or_resources':False,'timers_or_cron_restored':False,'controller_sha256':sha(C/'control/finite_pipeline.py'),'projection_sha256':sha(C/'measurement/publish_physical_v2.py'),'state_path':str(C/'control/FINITE_PIPELINE_STATE_PUBLIC.json')}
imm(C/'control/FINITE_PIPELINE_LAUNCH_PUBLIC.json',(json.dumps(result,sort_keys=True)+'\n').encode());print(json.dumps(result))
'''.replace('__BUNDLE__',repr(bundle))
compile(source,'<launch-finite-pipeline>','exec')
result=control.vm(source,'launch_economic_finite_'+str(time.time_ns()))
control.save(P/'control/FINITE_PIPELINE_LAUNCH_PUBLIC.json',result);print(json.dumps(result))
