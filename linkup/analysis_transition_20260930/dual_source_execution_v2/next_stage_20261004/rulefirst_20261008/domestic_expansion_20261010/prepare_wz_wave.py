#!/usr/bin/env python3
import datetime as dt, glob, hashlib, json, os
from pathlib import Path
ROOT=Path('/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/wz_wave_0001')
OLD=Path('/work/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/domestic_wz_d60')
PLAN=Path('/work/home/lilysharp/linkup_release_v1/semantic_v1/wuzhen/plan.jsonl')
EXPECTED={'run_one_shard.py':'3826142b6cddb549e831c8302be1d460ba3e85ee96bb7736af5549f878b3bf44','rule_engine.py':'e429463ddfe947587c5d1afaea2aa87ab287bf91144496e09c7819bb53f71526','legacy_v5_frozen.py':'336242bed5372e446dbdc2b2d02944e906024ee90138a2fa424b866aee7293dd','relation_overlay.py':'1a888cbdaf11f4f8e97dd71c84f4af723491597825fe3b1427b2e64c773bc626'}
def sha(p):
 h=hashlib.sha256();
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def atomic(p,o):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n');os.replace(t,p)
for n,s in EXPECTED.items():
 if sha(OLD/'code'/n)!=s: raise RuntimeError('frozen code mismatch '+n)
oldqa=json.load(open(OLD/'public/QA_PUBLIC.json'))
if sha(OLD/'public/QA_PUBLIC.json')!='04c4fdddade8b38eca26f44c54fd594ceb10b48828d9d919c0d9b44410ea9da2' or oldqa.get('status')!='pass' or oldqa.get('shard_count')!=4: raise RuntimeError('old WZ4 acceptance missing')
accepted={Path(x).name[6:] for x in glob.glob(str(OLD/'output/shard_*'))}
if len(accepted)!=4: raise RuntimeError('accepted output count != 4')
rows=[json.loads(x) for x in open(PLAN) if x.strip()]
ids=[x['shard_id'] for x in rows]
if len(ids)!=len(set(ids)) or not accepted.issubset(set(ids)): raise RuntimeError('plan identity failure')
pending=[x for x in rows if x['shard_id'] not in accepted]; selected=pending[:4]
if len(selected)!=4: raise RuntimeError('fewer than four pending')
for x in selected:
 for key,prefix in [('source_path','/work/home/lilysharp/dewey_remaining_descriptions/'),('sidecar_path','/work/home/lilysharp/linkup_release_v1/semantic_v1/wuzhen/sidecars/')]:
  p=Path(x[key]);
  if not str(p).startswith(prefix) or not p.is_file(): raise RuntimeError('invalid source path')
 if p.stat().st_size<=0: raise RuntimeError('empty source')
manifest={'version':'d63-wz-wave-0001-private-v1','selected_entries':selected,'accepted_before':sorted(accepted),'plan_rows':len(rows),'runner_sha256':EXPECTED['run_one_shard.py']}
mp=ROOT/'private/WAVE_0001_MANIFEST_PRIVATE.json';atomic(mp,manifest)
atomic(ROOT/'public/WAVE_0001_PREP_PUBLIC.json',{'version':'d63-wz-wave-prep-public-v1','status':'pass','created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'plan_rows':len(rows),'accepted_before':len(accepted),'accepted_wz4_qa_sha256':'04c4fdddade8b38eca26f44c54fd594ceb10b48828d9d919c0d9b44410ea9da2','remaining_before_selection':len(pending),'selected_shards':4,'remaining_unselected':len(pending)-4,'selected_source_bytes':sum(int(x['source_bytes']) for x in selected),'selected_sidecar_bytes':sum(int(x['sidecar_bytes']) for x in selected),'selected_raw_rows':sum(int(x['raw_rows']) for x in selected),'manifest_sha256':sha(mp),'frozen_code':EXPECTED,'api_calls':0,'model_calls':0,'semantic_changes':False})
