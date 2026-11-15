"""Acquire or renew finite shared model locks only AFTER the Luna leg finishes."""
import datetime,fcntl,hashlib,json,os,subprocess,sys,time
from pathlib import Path
R=Path.home()/'migration';Q=R/'execution_20261116/run001/qualification500_v1';L=Q/'luna_revision002';D=Q/'kimi_reference350_v1'
def read(p):return json.loads(p.read_text())
def save(p,x):
 t=p.with_name(p.name+'.tmp');t.write_text(json.dumps(x,indent=2)+'\n');os.replace(t,p)
def alive(pid,script):
 p=Path('/proc')/str(pid)/'cmdline';return p.exists() and str(script).encode() in p.read_bytes()
state=read(L/'RUN_STATUS_PUBLIC.json')
assert state['status']=='finite_benchmark_completed' and state['completed']==500,'candidate_not_finished_no_reference_calls'
assert not alive(state['pid'],L/'cloud_qualification_luna_worker.py'),'candidate_still_holds_model_lane'
assert state['original_ledgers_unchanged']
assert (L/'SHA256SUMS_PRIVATE.json').exists()
for rel,h in read(L/'SHA256SUMS_PRIVATE.json').items():
 assert hashlib.sha256((L/rel).read_bytes()).hexdigest()==h,'candidate_finish_pin_changed'
locks=[];guard=D/'hold_reference_lane.py';lease=D/'LEASE_PRIVATE.json'
old=read(lease) if lease.exists() else None
if old:
 assert alive(old['pid'],guard),'old_lease_dead_reconcile_do_not_relaunch'
 assert time.time()<old['expires_epoch'],'expired_lease_reconcile'
else:
 for p in [R/'astra/extraction/runner.lock',R/'astra/agent.lock',D/'REFERENCE.lock']:
  f=p.open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
 source="""import json,os,time\nfrom pathlib import Path\np=Path(__file__).with_name('LEASE_PRIVATE.json');deadline=time.time()+28800\nwhile time.time()<deadline:\n if p.exists():\n  x=json.loads(p.read_text())\n  if x.get('release') or time.time()>x['expires_epoch']:break\n time.sleep(2)\n"""
 if guard.exists():assert guard.read_text()==source
 else:guard.write_text(source)
 p=subprocess.Popen([sys.executable,str(guard)],pass_fds=tuple(f.fileno() for f in locks),stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 old={'pid':p.pid,'first_started_epoch':time.time()}
excluded=read(L/'EXCLUSIONS_PRIVATE.json')
# Only known provider/filter/refusal exclusions are added here; ordinary validation failures are not rerouted repairs.
for p in (D/'commits').glob('*/EXCLUSIONS_PRIVATE.json') if (D/'commits').exists() else []:
 x=read(p)
 for k in ('tasks','context_sha256'):excluded[k]=sorted(set(excluded.get(k,[]))|set(x.get(k,[])))
old['expires_epoch']=min(time.time()+1800,old['first_started_epoch']+28800);save(lease,old)
permit={'status':'candidate_finished_serial_reference_authorized','expires_epoch':old['expires_epoch'],'guard_pid':old['pid'],'input_bundle_sha256':hashlib.sha256((D/'INPUT_BUNDLE_PRIVATE.json.gz').read_bytes()).hexdigest(),'candidate_completed':500,'source_validator_unchanged':True}
save(D/'SERIAL_PERMIT_PUBLIC.json',permit)
# Return bounded positions, not the entire protected-hash registry (>10 KB).
# The complete registry remains cloud-side and the original snapshot is already
# in the SHA-pinned transport bundle. Positions encode every live relevant block.
queue=[json.loads(l) for l in (Q/'reference_preflight002/BLIND_NEW_REFERENCE_INPUTS_PRIVATE.jsonl').read_text().splitlines()]
blocked_h=set(excluded.get('context_sha256',[]));blocked_t=set(excluded.get('tasks',[]))
positions=[i for i,x in enumerate(queue) if x['row']['context_sha256'] in blocked_h or x['qualification_task'] in blocked_t]
answer={'permit':permit,'excluded_positions':positions,'encoding':'positions_in_SHA_pinned_350_input_order'}
import base64,zlib
encoded=base64.b64encode(zlib.compress(json.dumps(answer).encode(),9)).decode()
assert len(encoded)<3500
print(json.dumps({'lease_zlib_b64':encoded}))

