#!/usr/bin/env python3
import datetime as dt, glob, hashlib, json, os, shutil
from pathlib import Path
ROOT=Path('/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/wz_wave_0002'); OLD=Path('/work/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/domestic_wz_d60'); PRIOR=Path('/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/wz_wave_0001'); PLAN=Path('/work/home/lilysharp/linkup_release_v1/semantic_v1/wuzhen/plan.jsonl')
RUNNER='3826142b6cddb549e831c8302be1d460ba3e85ee96bb7736af5549f878b3bf44'; PRIOR_QA='98f5f46cb27631e74799937c604e89c33c6fe1ed1c01694e528243e2c94f6e6a'; RESERVE=10_000_000_000; OUTPUT_CAP=4_000_000_000
def sha(p):
 h=hashlib.sha256();
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def atomic(p,o):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n');os.replace(t,p)
if sha(OLD/'code/run_one_shard.py')!=RUNNER or sha(PRIOR/'public/WAVE_0001_QA_PUBLIC.json')!=PRIOR_QA:raise RuntimeError('frozen runner or prior acceptance mismatch')
priorqa=json.load(open(PRIOR/'public/WAVE_0001_QA_PUBLIC.json'))
if priorqa.get('status')!='pass' or priorqa.get('new_shard_count')!=4:raise RuntimeError('prior wave not accepted')
accepted={Path(x).name[6:] for x in glob.glob(str(OLD/'output/shard_*'))+glob.glob(str(PRIOR/'output/shard_*'))}
if len(accepted)!=8:raise RuntimeError('accepted count != 8')
rows=[json.loads(x) for x in open(PLAN) if x.strip()];ids=[x['shard_id'] for x in rows]
if len(ids)!=len(set(ids)) or not accepted.issubset(set(ids)):raise RuntimeError('plan identity failure')
pending=[x for x in rows if x['shard_id'] not in accepted];selected=pending[:16]
if len(selected)!=16:raise RuntimeError('fewer than 16 pending')
for x in selected:
 for key,prefix in [('source_path','/work/home/lilysharp/dewey_remaining_descriptions/'),('sidecar_path','/work/home/lilysharp/linkup_release_v1/semantic_v1/wuzhen/sidecars/')]:
  p=Path(x[key]);
  if not str(p).startswith(prefix) or not p.is_file() or p.stat().st_size<=0:raise RuntimeError('invalid source file')
free=shutil.disk_usage(ROOT.parent).free
if free-OUTPUT_CAP<RESERVE:raise RuntimeError('capacity gate')
mp=ROOT/'private/WAVE_0002_MANIFEST_PRIVATE.json';atomic(mp,{'version':'d63-wz-wave-0002-private-v1','selected_entries':selected,'accepted_before':sorted(accepted),'plan_rows':len(rows),'runner_sha256':RUNNER})
atomic(ROOT/'public/WAVE_0002_PREP_PUBLIC.json',{'version':'d63-wz-wave-0002-prep-v1','status':'pass','created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'plan_rows':len(rows),'accepted_before':8,'prior_qa_sha256':PRIOR_QA,'remaining_before_selection':len(pending),'selected_shards':16,'remaining_unselected':len(pending)-16,'selected_raw_rows':sum(int(x['raw_rows']) for x in selected),'selected_source_bytes':sum(int(x['source_bytes']) for x in selected),'selected_sidecar_bytes':sum(int(x['sidecar_bytes']) for x in selected),'manifest_sha256':sha(mp),'capacity':{'free_bytes_before':free,'required_reserve_bytes':RESERVE,'wave_output_cap_bytes':OUTPUT_CAP},'runner_sha256':RUNNER,'api_calls':0,'model_calls':0,'semantic_changes':False})
