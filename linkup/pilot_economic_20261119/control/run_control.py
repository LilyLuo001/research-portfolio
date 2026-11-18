"""Explicit finite launch/status/projection over the existing authenticated VM."""
import json
from pathlib import Path
import sys
import time

P=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(P.parent/'execution_20261116_continuation02'))
import control

BASE=r'''import datetime,hashlib,json,os,subprocess,sys,sqlite3,time
from pathlib import Path
os.umask(0o077)
R=Path.home()/'migration';C=R/'pilot_economic_20261119/run01';C5=R/'confirmation_stage5_20261118/execution_v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
field=C5/'repo/linkup/reuse_first_20261115/measurement_protocol_20261117/code/field_validation.py'
frozen=C5/'repo/linkup/formal800_20261012/code/validate_reviews.py'
'''


def main():
    action=sys.argv[1]
    if action=='launch':
        leg,batch,ceiling,concurrency=sys.argv[2:6]
        assert leg in ('Luna','Kimi','Astra')
        assert batch.startswith('batch') and batch[5:].isdigit()
        ceiling,concurrency=int(ceiling),int(concurrency)
        source=BASE+f"leg={leg!r};batch={batch!r};ceiling={ceiling};concurrency={concurrency}\n"+r'''
receipt=C/'control'/f'LAUNCH_{leg}_{batch}_{ceiling}_PUBLIC.json'
if receipt.exists():
 print(json.dumps({'status':'launch_receipt_already_exists_no_duplicate','receipt':read(receipt)}));raise SystemExit()
active=[]
for path in Path('/proc').glob('[0-9]*/cmdline'):
 try:args=path.read_bytes().split(b'\0')
 except (OSError,ProcessLookupError):continue
 if any(str(C/n).encode() in args for n in ['runtime/pilot_worker.py','runtime_v2/pilot_worker_v2.py']) and leg.encode() in args:active.append(int(path.parent.name))
assert not active,'worker_already_active_for_leg'
M=C/'preparation'/batch/'BATCH_MANIFEST_PUBLIC.json'
cmd=[sys.executable,'-B',str(C/'runtime/pilot_worker.py'),'--leg',leg,'--directory',str(C),'--policy',str(C/'policy.json'),'--batch-manifest',str(M),'--batch-manifest-sha256',sha(M),'--field-validator',str(field),'--frozen-validator',str(frozen),'--workflow-directory',str(R/'code'),'--max-new-logical',str(ceiling),'--concurrency',str(concurrency),'--max-wall-seconds','14400','--stop-file',str(C/'STOP')]
log=C/'control'/f'WORKER_{leg}_{batch}_{ceiling}_PRIVATE.log'
with log.open('xb') as stream:
 p=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,cwd=C)
 time.sleep(1)
 result={'status':'finite_pilot_worker_launched','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'leg':leg,'batch':batch,'pid':p.pid,'process_active_after_one_second':p.poll() is None,'early_exit':p.poll(),'launch_logical_ceiling_cumulative':ceiling,'concurrency':concurrency,'batch_manifest_sha256':sha(M),'policy_sha256':sha(C/'policy.json'),'run_directory':str(C),'pilot_cap_usd':150,'OpenCode_used':False}
receipt.write_text(json.dumps(result,sort_keys=True)+'\n');print(json.dumps(result))
'''
        target=P/'control'/f'LAUNCH_{leg}_{batch}_{ceiling}_PUBLIC.json'
    elif action=='status':
        source=BASE+r'''
active=[]
for path in Path('/proc').glob('[0-9]*/cmdline'):
 try:args=path.read_bytes().split(b'\0')
 except (OSError,ProcessLookupError):continue
 if any(str(C/n).encode() in args for n in ['runtime/pilot_worker.py','runtime_v2/pilot_worker_v2.py']):active.append(int(path.parent.name))
db=sqlite3.connect((C/'ADMISSION_PRIVATE.sqlite3').as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
rows=[dict(x) for x in db.execute('select * from attempts')]
hold=db.execute("select value from meta where key='global_hold'").fetchone()
legs={}
for leg in ['Luna','Kimi','Astra']:
 a=[x for x in rows if x['leg']==leg];states={}
 for x in a:states[x['state']]=states.get(x['state'],0)+1
 details=[json.loads(x['detail']) for x in a]
 legs[leg]={'logical_calls':db.execute('select count(*) from claims where leg=?',(leg,)).fetchone()[0],
 'physical_attempts':len(a),'states':states,'reserved_usd':sum(x['dollars_nano'] for x in a)/1e9,
 'input_tokens':sum((x.get('usage') or {}).get('prompt_tokens',0) or 0 for x in details),
 'output_tokens':sum((x.get('usage') or {}).get('completion_tokens',0) or 0 for x in details),
 'rate_limit_token_headers':sorted({str(x.get('rate_headers',{}).get('x-ratelimit-limit-tokens')) for x in details if x.get('rate_headers')})}
db.close()
result={'status':'live_pilot_snapshot','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'active_pids':active,'legs':legs,'global_hold':hold[0] if hold else None,
 'pilot_reserved_usd':sum(x['dollars_nano'] for x in rows)/1e9,
 'first_request_unix':min((x['forwarded'] for x in rows),default=None),
 'last_request_unix':max((x['forwarded'] for x in rows),default=None),
 'invoice_verified':False}
print(json.dumps(result))
'''
        target=P/'control'/f'STATUS_{time.time_ns()}_PUBLIC.json'
    elif action=='project':
        batch=sys.argv[2]
        assert batch.startswith('batch') and batch[5:].isdigit()
        source=BASE+f"batch={batch!r}\n"+r'''
out=C/'projection'/batch
scorer=C5/'protocol/field_score.py'
cmd=[sys.executable,'-B',str(C/'measurement/publish_physical_v2.py'),'--directory',str(C),'--through-batch',batch,'--output',str(out),'--scorer',str(scorer),'--scorer-sha256',sha(scorer),'--frozen-validator',str(frozen),'--frozen-validator-sha256',sha(frozen)]
cp=subprocess.run(cmd,capture_output=True,text=True,timeout=180)
(C/'control'/f'PROJECTION_{batch}_EXECUTION_PRIVATE.json').write_text(json.dumps({'returncode':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr}))
try:result=json.loads(cp.stdout)
except Exception:result={'status':'projection_failed_private_diagnostic_retained','returncode':cp.returncode}
print(json.dumps(result))
'''
        target=P/'control'/f'PROJECTION_{batch}_PUBLIC.json'
    elif action=='receipts':
        source=BASE+r'''
B=C/'preparation/batch0001';cpu=read(B/'CPU_RULE_RECEIPT_PUBLIC.json');m=read(B/'BATCH_MANIFEST_PUBLIC.json')
print(json.dumps({'CPU':cpu,'physical_rows':m['physical_rows'],'state_counts':m['state_counts']}))
'''
        target=P/'control/CPU_BATCH0001_PUBLIC.json'
    else:raise SystemExit('unknown_action')
    compile(source,'<finite-pilot-control>','exec')
    result=control.vm(source,'economic_pilot_'+action+'_'+str(time.time_ns()))
    control.save(target,result);print(json.dumps(result))


if __name__=='__main__':main()
