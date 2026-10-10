#!/usr/bin/env python3
"""Create the next dependency-linked KS wave; never waits on allocated cores."""
import argparse, datetime as dt, hashlib, json, os, shutil, subprocess
from pathlib import Path
CAP=10_000_000_000; OUTPUT_CAP=125_000_000_000; TASK_CAP=200_000_000_000; MIN_PROJECT_FREE=200_000_000_000; MIN_GLOBAL_FREE=300_000_000_000; RUNNER_SHA='3826142b6cddb549e831c8302be1d460ba3e85ee96bb7736af5549f878b3bf44'
def sha(p):
 h=hashlib.sha256(); f=open(p,'rb')
 for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 f.close(); return h.hexdigest()
def atomic(p,x):
 p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); t=Path(str(p)+'.tmp'); t.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n'); os.replace(t,p)
def qsub(script):
 out=subprocess.check_output(['qsub',str(script)],text=True); return out.strip().split()[2].split('.')[0]
def tree_bytes(root):
 return sum(p.stat().st_size for p in Path(root).rglob('*') if p.is_file())
def output_valid(root,e):
 short=e['shard_id'][:16]; p=root/'output'/('SHARD_'+short+'_RECEIPT_PUBLIC.json'); d=root/'output'/('shard_'+short)
 try:
  r=json.loads(p.read_text()); q=json.loads((root/'output'/('SHARD_'+short+'_QA_PUBLIC.json')).read_text()); post=d/'POSTING_NARROW_PRIVATE.parquet'; evid=d/'EVIDENCE_PRIVATE.parquet'
  return (r.get('status')=='complete' and q.get('status')=='pass' and r.get('identity',{}).get('runner_sha256')==RUNNER_SHA and r.get('identity',{}).get('raw_sha256')==e['source_sha256_cached'] and r.get('identity',{}).get('sidecar_sha256')==e['sidecar_sha256'] and post.is_file() and evid.is_file() and sha(post)==r['outputs']['posting_sha256']==q.get('posting_sha256') and sha(evid)==r['outputs']['evidence_sha256']==q.get('evidence_sha256'))
 except Exception:return False
def quota_snapshot(root):
 out=subprocess.check_output(['pquota','econdept'],text=True)
 line=next(x for x in out.splitlines() if x.strip().startswith('/projectnb/econdept'))
 parts=line.split(); quota_gb=float(parts[1]); used_gb=float(parts[3]); project_free=int((quota_gb-used_gb)*1_000_000_000)
 st=os.statvfs(str(root)); global_free=st.f_bavail*st.f_frsize
 outputs=tree_bytes(root/'output') if (root/'output').exists() else 0; task=tree_bytes(root)
 if project_free<MIN_PROJECT_FREE or global_free<MIN_GLOBAL_FREE or outputs>OUTPUT_CAP or task>TASK_CAP: raise RuntimeError('D59 storage admission threshold blocked')
 return {'project_free_bytes':project_free,'global_free_bytes':global_free,'output_tree_bytes':outputs,'task_tree_bytes':task}
def cleanup_prior(root,ledger):
 prev=ledger.get('prior_wave')
 if not prev:return []
 q=Path(prev['qa_receipt']); m=Path(prev['manifest']); qr=json.loads(q.read_text()); mm=json.loads(m.read_text())
 if qr.get('status')!='pass' or qr.get('manifest_sha256')!=sha(m): raise RuntimeError('prior QA missing/mismatch; cleanup and continuation blocked')
 qby={x['shard_id']:x for x in qr['shards']}; removed=[]
 for e in mm['entries']:
  sid=e['shard_id']; short=sid[:16]; pr=root/'output'/('SHARD_'+short+'_RECEIPT_PUBLIC.json'); r=json.loads(pr.read_text()); x=qby[short]
  d=root/'output'/('shard_'+short); post=d/'POSTING_NARROW_PRIVATE.parquet'; evid=d/'EVIDENCE_PRIVATE.parquet'
  if (r.get('identity',{}).get('raw_sha256')!=e['source_sha256_cached'] or r.get('identity',{}).get('sidecar_sha256')!=e['sidecar_sha256'] or not post.is_file() or not evid.is_file() or sha(post)!=r['outputs']['posting_sha256'] or sha(evid)!=r['outputs']['evidence_sha256'] or r['outputs']['posting_sha256']!=x['posting_sha256'] or r['outputs']['evidence_sha256']!=x['evidence_sha256']): raise RuntimeError('actual output hash changed after QA')
  d=root/'staging'/'ready'/sid
  if d.exists(): shutil.rmtree(d); removed.append(short)
 return removed
def main():
 p=argparse.ArgumentParser(); p.add_argument('--root',required=True); p.add_argument('--master',required=True); p.add_argument('--ledger',required=True); p.add_argument('--wave-size',type=int,default=8); a=p.parse_args(); root=Path(a.root); ledger_path=Path(a.ledger)
 lock=root/'control'/'private'/'CONTROLLER.lock'
 try: lock.mkdir()
 except FileExistsError: raise RuntimeError('controller exclusive lock held')
 try:
  ledger=json.loads(ledger_path.read_text()) if ledger_path.exists() else {'version':'d59-rolling-v1','waves':[],'prior_wave':None}
  inflight=root/'control'/'private'/'INFLIGHT_WAVE_PRIVATE.json'
  if inflight.exists(): raise RuntimeError('unresolved inflight wave blocks duplicate submission')
  removed=cleanup_prior(root,ledger)
  quota=quota_snapshot(root)
  rows=[json.loads(x) for x in Path(a.master).read_text().splitlines() if x.strip()]
  accepted=dict(ledger.get('accepted_entries',{}))
  if ledger.get('prior_wave'):
   pm=json.loads(Path(ledger['prior_wave']['manifest']).read_text()); pq=json.loads(Path(ledger['prior_wave']['qa_receipt']).read_text())
   for e in pm['entries']:
    short=e['shard_id'][:16]; pr=json.loads((root/'output'/('SHARD_'+short+'_RECEIPT_PUBLIC.json')).read_text()); qr=root/'output'/('SHARD_'+short+'_QA_PUBLIC.json')
    accepted[e['shard_id']]={'raw_sha256':e['source_sha256_cached'],'sidecar_sha256':e['sidecar_sha256'],'runner_sha256':RUNNER_SHA,'posting_sha256':pr['outputs']['posting_sha256'],'evidence_sha256':pr['outputs']['evidence_sha256'],'qa_receipt_sha256':sha(qr)}
   ledger['accepted_entries']=accepted; atomic(ledger_path,ledger)
  def accepted_matches(e):
   x=accepted.get(e['shard_id'])
   return bool(x and x.get('raw_sha256')==e['source_sha256_cached'] and x.get('sidecar_sha256')==e['sidecar_sha256'] and x.get('runner_sha256')==RUNNER_SHA and x.get('posting_sha256') and x.get('evidence_sha256') and x.get('qa_receipt_sha256'))
  # Master rows are frozen runner-plan records. Only KS is admitted while WZ route is blocked.
  pending=[]; blocked=0
  for e in rows:
   if e.get('region')!='kunshan': blocked+=1; continue
   if accepted_matches(e): continue
   pending.append(e)
  chosen=[]; total=0
  for e in pending:
   size=int(e['source_bytes'])+int(e['sidecar_bytes'])
   if len(chosen)>=a.wave_size or total+size>CAP: break
   chosen.append(e); total+=size
  projected_reserve=2*total
  if (quota['task_tree_bytes']+projected_reserve>TASK_CAP or quota['output_tree_bytes']+total>OUTPUT_CAP or quota['project_free_bytes']-projected_reserve<MIN_PROJECT_FREE or quota['global_free_bytes']-projected_reserve<MIN_GLOBAL_FREE): raise RuntimeError('D59 projected wave reserve blocked')
  if not chosen:
   ledger.update({'status':'ks_complete_or_no_admissible_entries','wuzhen_blocked_count':blocked,'updated_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'last_cleanup':removed}); atomic(ledger_path,ledger); return
  wave_no=len(ledger['waves'])+1; wid='wave_%04d'%wave_no; ctl=root/'control'/'private'; pub=root/'public'; code=root/'code'; manifest=ctl/(wid+'_MANIFEST_PRIVATE.json')
  atomic(manifest,{'batch_id':wid,'selection':'next admissible uncompleted KS rows in frozen master order','manifest_source_sha256':sha(a.master),'staging_cap_bytes':CAP,'entries':chosen})
  prod=code/(wid+'_prod.sh'); qa=code/(wid+'_qa.sh'); nxt=code/(wid+'_next.sh')
  common='#!/bin/bash -l\n#$ -cwd\n#$ -j y\n#$ -P econdept\n#$ -q econ\n#$ -l no_gpu=TRUE\n'
  setup='set -euo pipefail\numask 077\nmodule load python3/3.8.10\n'
  inflight_state={'wave_id':wid,'manifest':str(manifest),'manifest_sha256':sha(manifest),'jobs':{},'created_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
  atomic(inflight,inflight_state)
  stage_jobs=[]
  for lane in range(min(4,len(chosen))):
   lane_entries=chosen[lane::4]; lane_manifest=ctl/(wid+'_LANE%d_PRIVATE.json'%(lane+1)); atomic(lane_manifest,{'batch_id':wid+'_lane_%d'%(lane+1),'manifest_source_sha256':sha(a.master),'staging_cap_bytes':CAP,'entries':lane_entries})
   stage=code/(wid+'_stage_lane%d.sh'%(lane+1)); stage.write_text(common+'#$ -pe omp 1\n#$ -l h_rt=08:00:00\n#$ -l mem_per_core=4G\n#$ -N lk_st_'+str(wave_no)+'_'+str(lane+1)+'\nset -euo pipefail\numask 077\nmodule load python3/3.8.10\npython3 '+str(code/'stage_manifest.py')+' --manifest '+str(lane_manifest)+' --stage-root '+str(root/'staging')+' --credential-dir /projectnb/econdept/qluo/.linkup_transfer_credentials_20261010 --cap-bytes 10000000000 --public-receipt '+str(pub/(wid+'_LANE%d_STAGING_RECEIPT_PUBLIC.json'%(lane+1)))+'\n'); os.chmod(stage,0o700)
   sj=qsub(stage); stage_jobs.append(sj); inflight_state['jobs']['stage_job_ids']=stage_jobs; atomic(inflight,inflight_state)
  stage_hold=','.join(stage_jobs)
  prod.write_text(common+'#$ -pe omp 4\n#$ -l h_rt=02:00:00\n#$ -l mem_per_core=2G\n#$ -t 1-'+str(len(chosen))+'\n#$ -tc 4\n#$ -hold_jid '+stage_hold+'\n#$ -N lk_pr_'+str(wave_no)+'\nset -euo pipefail\numask 077\nmodule load python3/3.8.10\nPYTHONPATH=/projectnb/econdept/qluo/linkup_rulefirst_20261008/full_production_20261009/code:${PYTHONPATH:-} python3 '+str(code/'run_manifest_entry.py')+' --manifest '+str(manifest)+' --index "$SGE_TASK_ID" --stage-root '+str(root/'staging')+' --output-root '+str(root/'output')+' --runner /projectnb/econdept/qluo/linkup_rulefirst_20261008/full_production_20261009/code/run_one_shard.py --workers "$NSLOTS"\n'); os.chmod(prod,0o700); pj=qsub(prod); inflight_state['jobs']['production_job_id']=pj; atomic(inflight,inflight_state)
  qa_receipt=pub/(wid+'_QA_PUBLIC.json'); qa.write_text(common+'#$ -pe omp 1\n#$ -l h_rt=02:00:00\n#$ -l mem_per_core=4G\n#$ -hold_jid '+pj+'\n#$ -N lk_qa_'+str(wave_no)+'\nset -euo pipefail\numask 077\nmodule load python3/3.8.10\nPYTHONPATH=/projectnb/econdept/qluo/linkup_rulefirst_20261008/full_production_20261009/code:${PYTHONPATH:-} python3 '+str(code/'verify_wave_outputs.py')+' --manifest '+str(manifest)+' --output-root '+str(root/'output')+' --verifier /projectnb/econdept/qluo/linkup_rulefirst_20261008/full_production_20261009/code/verify_one_shard_outputs.py --public-receipt '+str(qa_receipt)+'\n'); os.chmod(qa,0o700); qj=qsub(qa); inflight_state['jobs']['qa_job_id']=qj; atomic(inflight,inflight_state)
  nxt.write_text(common+'#$ -pe omp 1\n#$ -l h_rt=00:10:00\n#$ -l mem_per_core=2G\n#$ -hold_jid '+qj+'\n#$ -N lk_ctl_'+str(wave_no+1)+'\nset -euo pipefail\numask 077\nmodule load python3/3.8.10\npython3 '+str(code/'rolling_controller.py')+' --root '+str(root)+' --master '+a.master+' --ledger '+a.ledger+' --wave-size '+str(a.wave_size)+'\n'); os.chmod(nxt,0o700); cj=qsub(nxt); inflight_state['jobs']['next_controller_job_id']=cj; atomic(inflight,inflight_state)
  ledger['prior_wave']={'manifest':str(manifest),'qa_receipt':str(qa_receipt)}; ledger['waves'].append({'wave_id':wid,'manifest_sha256':sha(manifest),'shard_count':len(chosen),'input_bytes':total,'stage_job_ids':stage_jobs,'production_job_id':pj,'qa_job_id':qj,'next_controller_job_id':cj}); ledger['quota_snapshot']=quota; ledger.update({'status':'active_ks_only','wuzhen_blocked_count':blocked,'last_cleanup':removed,'updated_utc':dt.datetime.now(dt.timezone.utc).isoformat()}); atomic(ledger_path,ledger); inflight.unlink()
 finally:
  try: lock.rmdir()
  except OSError: pass
if __name__=='__main__': main()
