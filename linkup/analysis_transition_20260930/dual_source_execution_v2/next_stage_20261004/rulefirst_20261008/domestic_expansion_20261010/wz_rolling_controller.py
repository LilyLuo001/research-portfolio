#!/usr/bin/env python3
import datetime as dt,glob,hashlib,json,os,shutil,subprocess
from pathlib import Path
BASE=Path('/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010');OLD=Path('/work/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/domestic_wz_d60');PLAN=Path('/work/home/lilysharp/linkup_release_v1/semantic_v1/wuzhen/plan.jsonl');RUNNER='3826142b6cddb549e831c8302be1d460ba3e85ee96bb7736af5549f878b3bf44';TARGET_LAST=5
def sha(p):
 h=hashlib.sha256();
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def atomic(p,o):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n');os.replace(t,p)
current=int(os.environ['CURRENT_WAVE']); cur=BASE/f'wz_wave_{current:04d}';qa=cur/f'public/WAVE_{current:04d}_QA_PUBLIC.json';q=json.load(open(qa))
if q.get('status')!='pass' or q.get('new_shard_count')!=16:raise RuntimeError('prior QA not accepted')
ledgerp=BASE/'rolling/public/ROLLING_LEDGER_PUBLIC.json';ledger=json.load(open(ledgerp)) if ledgerp.exists() else {'version':'d63-wz-rolling64-v1','target_new_shards_waves_2_5':64,'waves':[]}
for x in ledger['waves']:
 if x['wave']==current:x.update(status='completed',qa_sha256=sha(qa),completed_utc=dt.datetime.now(dt.timezone.utc).isoformat())
if not any(x['wave']==current for x in ledger['waves']):ledger['waves'].append({'wave':current,'status':'completed','selected_shards':16,'qa_sha256':sha(qa),'completed_utc':dt.datetime.now(dt.timezone.utc).isoformat()})
if current>=TARGET_LAST:ledger['status']='complete_target_64';atomic(ledgerp,ledger);raise SystemExit
n=current+1;root=BASE/f'wz_wave_{n:04d}';[p.mkdir(parents=True,exist_ok=True) for p in [root/'private',root/'public',root/'logs',root/'output']]
accepted={Path(x).name[6:] for x in glob.glob(str(OLD/'output/shard_*'))}
for w in range(1,n):accepted|={Path(x).name[6:] for x in glob.glob(str(BASE/f'wz_wave_{w:04d}/output/shard_*'))}
expected=8+16*(n-2)
if len(accepted)!=expected:raise RuntimeError('accepted count mismatch')
rows=[json.loads(x) for x in open(PLAN) if x.strip()];pending=[x for x in rows if x['shard_id'] not in accepted];sel=pending[:16]
if len(sel)!=16:raise RuntimeError('insufficient pending')
for x in sel:
 for k,prefix in [('source_path','/work/home/lilysharp/dewey_remaining_descriptions/'),('sidecar_path','/work/home/lilysharp/linkup_release_v1/semantic_v1/wuzhen/sidecars/')]:
  p=Path(x[k]);
  if not str(p).startswith(prefix) or not p.is_file():raise RuntimeError('source gate')
free=shutil.disk_usage(BASE).free
if free-4_000_000_000<10_000_000_000:ledger['status']='stopped_capacity';atomic(ledgerp,ledger);raise RuntimeError('capacity gate')
mp=root/f'private/WAVE_{n:04d}_MANIFEST_PRIVATE.json';atomic(mp,{'version':'d63-wz-rolling-private-v1','wave':n,'selected_entries':sel,'accepted_before_count':len(accepted),'runner_sha256':RUNNER})
atomic(root/f'public/WAVE_{n:04d}_PREP_PUBLIC.json',{'version':'d63-wz-rolling-prep-v1','status':'pass','wave':n,'accepted_before':len(accepted),'selected_shards':16,'remaining_unselected':len(pending)-16,'selected_raw_rows':sum(x['raw_rows'] for x in sel),'free_bytes_before':free,'reserve_bytes':10_000_000_000,'output_cap_bytes':4_000_000_000,'prior_qa_sha256':sha(qa),'manifest_sha256':sha(mp),'created_utc':dt.datetime.now(dt.timezone.utc).isoformat()})
code=BASE/'rolling/code';prod=subprocess.check_output(['sbatch','--parsable',f'--export=ALL,WAVE={n}',str(code/'wz_rolling_production.sbatch')],text=True).strip();qj=subprocess.check_output(['sbatch','--parsable',f'--dependency=afterok:{prod}',f'--export=ALL,WAVE={n},PRODUCTION_JOB_ID={prod}',str(code/'wz_rolling_qa.sbatch')],text=True).strip();cj=subprocess.check_output(['sbatch','--parsable',f'--dependency=afterok:{qj}',f'--export=ALL,CURRENT_WAVE={n}',str(code/'wz_rolling_controller.sbatch')],text=True).strip()
ledger['waves'].append({'wave':n,'status':'submitted','selected_shards':16,'production_job_id':prod,'qa_job_id':qj,'next_controller_job_id':cj,'manifest_sha256':sha(mp)});ledger['status']='active';ledger['updated_utc']=dt.datetime.now(dt.timezone.utc).isoformat();atomic(ledgerp,ledger)
