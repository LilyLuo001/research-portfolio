#!/usr/bin/env python3
import datetime as dt,glob,hashlib,json,os,shutil,subprocess
from pathlib import Path

BASE=Path('/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010')
OLD=Path('/work/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/domestic_wz_d60')
PATCH_BASE=BASE/'d64_engineering_patch_20261010'
PLAN=Path('/work/home/lilysharp/linkup_release_v1/semantic_v1/wuzhen/plan.jsonl')
RUNNER='3826142b6cddb549e831c8302be1d460ba3e85ee96bb7736af5549f878b3bf44'
CONTRACT=BASE/'d64_acceptance/ROOT_MEASUREMENT_USE_CONTRACT.json'
CONTRACT_SHA='62d56fbef87ecf0afd8479fee95101668aec0ffed23ea39cacc0ac39e966526f'
MEASUREMENT_USE='evidence_bearing_candidates_not_validated_requirements'
TARGET_LAST=5
LEDGER_PATH=PATCH_BASE/'rolling/public/ROLLING_LEDGER_PUBLIC.json'
LOCK_PATH=PATCH_BASE/'rolling/private/controller.claim'

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):
   h.update(b)
 return h.hexdigest()

def atomic(p,o):
 p=Path(p)
 p.parent.mkdir(parents=True,exist_ok=True)
 t=p.with_suffix(p.suffix+'.tmp')
 t.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n')
 os.replace(t,p)

def persist(ledger):
 ledger['updated_utc']=dt.datetime.now(dt.timezone.utc).isoformat()
 atomic(LEDGER_PATH,ledger)

def submit(ledger,wave,entry,phase,args,id_field):
 entry['status']='submitting_'+phase
 persist(ledger)
 try:
  job_id=subprocess.check_output(args,text=True).strip()
 except Exception:
  entry['status']='stopped_submission_uncertain'
  entry['uncertain_phase']=phase
  persist(ledger)
  raise
 if not job_id:
  entry['status']='stopped_submission_uncertain'
  entry['uncertain_phase']=phase
  persist(ledger)
  raise RuntimeError('empty sbatch job id')
 entry[id_field]=job_id
 entry['status']=phase+'_submitted'
 persist(ledger)
 return job_id

LOCK_PATH.parent.mkdir(parents=True,exist_ok=True)
try:
 os.mkdir(LOCK_PATH)
except FileExistsError:
 raise RuntimeError('controller claim exists; stop for manual inspection')
atomic(LOCK_PATH/'owner.json',{'job_id':os.environ.get('SLURM_JOB_ID'),'created_utc':dt.datetime.now(dt.timezone.utc).isoformat()})
try:
 current=int(os.environ['CURRENT_WAVE'])
 cur=BASE/f'wz_wave_{current:04d}'
 qa=cur/f'public/WAVE_{current:04d}_QA_PUBLIC.json'
 q=json.load(open(qa))
 if q.get('status')!='pass' or q.get('new_shard_count')!=16:
  raise RuntimeError('prior QA not accepted')
 if sha(CONTRACT)!=CONTRACT_SHA:
  raise RuntimeError('measurement-use contract mismatch')
 ledger=json.load(open(LEDGER_PATH)) if LEDGER_PATH.exists() else {'version':'d64-wz-rolling64-v1','target_new_shards_waves_2_5':64,'waves':[]}
 prior=next((x for x in ledger['waves'] if x['wave']==current),None)
 if prior is None:
  prior={'wave':current,'selected_shards':16}
  ledger['waves'].append(prior)
 prior.update(status='completed',qa_sha256=sha(qa),completed_utc=dt.datetime.now(dt.timezone.utc).isoformat())
 persist(ledger)
 if current>=TARGET_LAST:
  ledger['status']='complete_target_64'
  persist(ledger)
  raise SystemExit
 n=current+1
 entry=next((x for x in ledger['waves'] if x['wave']==n),None)
 if entry is not None:
  if entry.get('status') in {'active','submitted','controller_submitted'} and all(entry.get(k) for k in ('production_job_id','qa_job_id','next_controller_job_id')):
   raise SystemExit
  if entry.get('status')=='production_submitted' and entry.get('production_job_id'):
   pass
  elif entry.get('status')=='qa_submitted' and entry.get('production_job_id') and entry.get('qa_job_id'):
   pass
  else:
   raise RuntimeError('existing next-wave claim is incomplete or uncertain; stop for manual inspection')
 else:
  root=BASE/f'wz_wave_{n:04d}'
  for p in (root/'private',root/'public',root/'logs',root/'output'):
   p.mkdir(parents=True,exist_ok=True)
  accepted={Path(x).name[6:] for x in glob.glob(str(OLD/'output/shard_*'))}
  for w in range(1,n):
   accepted|={Path(x).name[6:] for x in glob.glob(str(BASE/f'wz_wave_{w:04d}/output/shard_*'))}
  expected=8+16*(n-2)
  if len(accepted)!=expected:
   raise RuntimeError('accepted count mismatch')
  rows=[json.loads(x) for x in open(PLAN) if x.strip()]
  pending=[x for x in rows if x['shard_id'] not in accepted]
  sel=pending[:16]
  if len(sel)!=16:
   raise RuntimeError('insufficient pending')
  for x in sel:
   for k,prefix in [('source_path','/work/home/lilysharp/dewey_remaining_descriptions/'),('sidecar_path','/work/home/lilysharp/linkup_release_v1/semantic_v1/wuzhen/sidecars/')]:
    p=Path(x[k])
    if not str(p).startswith(prefix) or not p.is_file():
     raise RuntimeError('source gate')
  free=shutil.disk_usage(BASE).free
  if free-4_000_000_000<10_000_000_000:
   ledger['status']='stopped_capacity'
   persist(ledger)
   raise RuntimeError('capacity gate')
  mp=root/f'private/WAVE_{n:04d}_MANIFEST_PRIVATE.json'
  atomic(mp,{'version':'d64-wz-rolling-private-v1','wave':n,'selected_entries':sel,'accepted_before_count':len(accepted),'runner_sha256':RUNNER,'measurement_contract_sha256':CONTRACT_SHA,'measurement_use':MEASUREMENT_USE})
  atomic(root/f'public/WAVE_{n:04d}_PREP_PUBLIC.json',{'version':'d64-wz-rolling-prep-v1','status':'pass','wave':n,'accepted_before':len(accepted),'selected_shards':16,'remaining_unselected':len(pending)-16,'selected_raw_rows':sum(x['raw_rows'] for x in sel),'free_bytes_before':free,'reserve_bytes':10_000_000_000,'output_cap_bytes':4_000_000_000,'per_shard_capacity_check':'10GB reserve plus 1GB conservative admission budget; not a hard quota','prior_qa_sha256':sha(qa),'manifest_sha256':sha(mp),'measurement_contract_sha256':CONTRACT_SHA,'measurement_use':MEASUREMENT_USE,'created_utc':dt.datetime.now(dt.timezone.utc).isoformat()})
  entry={'wave':n,'status':'claimed','selected_shards':16,'manifest_sha256':sha(mp),'claimed_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
  ledger['waves'].append(entry)
  ledger['status']='active'
  persist(ledger)
 code=PATCH_BASE/'rolling/code'
 prod=entry.get('production_job_id')
 if not prod:
  prod=submit(ledger,n,entry,'production',['sbatch','--parsable',f'--export=ALL,WAVE={n}',str(code/'wz_rolling_production.sbatch')],'production_job_id')
 qj=entry.get('qa_job_id')
 if not qj:
  qj=submit(ledger,n,entry,'qa',['sbatch','--parsable',f'--dependency=afterok:{prod}',f'--export=ALL,WAVE={n},PRODUCTION_JOB_ID={prod}',str(code/'wz_rolling_qa.sbatch')],'qa_job_id')
 cj=submit(ledger,n,entry,'controller',['sbatch','--parsable',f'--dependency=afterok:{qj}',f'--export=ALL,CURRENT_WAVE={n}',str(code/'wz_rolling_controller.sbatch')],'next_controller_job_id')
 entry['status']='submitted'
 ledger['status']='active'
 persist(ledger)
finally:
 owner=LOCK_PATH/'owner.json'
 if owner.exists():
  owner.unlink()
 if LOCK_PATH.exists():
  os.rmdir(LOCK_PATH)
