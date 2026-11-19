"""Resume only the existing bounded run, deadline, rate policy and admission ledger."""
import json,sys,time
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parents[1]/'execution_20261116_continuation02'));import control
source=r'''import argparse,datetime,json,os,subprocess,sys,time
from pathlib import Path
os.umask(0o077);C=Path.home()/'migration/pilot_economic_20261119/run01';D=C/'control/jsonl_recovery_20261119'
sys.path.insert(0,str(C/'control'));import finite_pipeline_v2 as f
receipt=D/'RESUME_PUBLIC.json'
assert not receipt.exists(),'resume_receipt_exists_no_duplicate'
recovery=f.read(D/'RECOVERY_PUBLIC.json')
assert recovery['protected_file_sha_unchanged'] and recovery['model_calls_during_recovery']==0
for n,h in recovery['code_sha256'].items():assert f.sha(C/n)==h,'recovery_code_pin_changed'
with f.controller_lock(C):
 obj=f.Supervisor(argparse.Namespace(directory=C,concurrency=4,max_wall_seconds=172800,prepare_and_apply_rate_amendment=False))
 obj.guards()
 assert obj.state['completed_batches']==['batch0001','batch0002'],'unexpected_resume_cursor'
 assert time.time()<obj.deadline,'original_deadline_expired'
 cmd=[sys.executable,'-B',str(C/'control/finite_pipeline_v2.py'),'--directory',str(C),'--concurrency','4','--max-wall-seconds','172800']
 # Release the same flock before launching the one controller; it reacquires it.
with (D/'RESUMED_FINITE_PIPELINE_PRIVATE.log').open('xb') as log:
 p=subprocess.Popen(cmd,cwd=C,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 time.sleep(2)
 result={'status':'bounded_resume_launched','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'controller_pid':p.pid,'active_after_two_seconds':p.poll() is None,'early_exit':p.poll(),'completed_batches_before_resume':obj.state['completed_batches'],'original_start_epoch':obj.state['started_epoch'],'deadline_epoch':obj.deadline,'max_physical_rows':10000,'pilot_cap_usd':150,'policy_sha256':obj.policy_sha,'schema_unchanged':True,'budget_reset':False,'timer_created':False}
 f.immutable(receipt,f.encoded(result));print(json.dumps(result))
'''
r=control.vm(source,'jsonl_resume_'+str(time.time_ns()));(P/'RESUME_PUBLIC.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
