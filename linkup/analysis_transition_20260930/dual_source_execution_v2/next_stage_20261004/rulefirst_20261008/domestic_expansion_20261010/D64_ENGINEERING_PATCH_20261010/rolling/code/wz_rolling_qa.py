#!/usr/bin/env python3
import collections,datetime as dt,glob,json,os,pathlib,subprocess,sys

BASE=pathlib.Path('/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010')
OLD=pathlib.Path('/work/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/domestic_wz_d60')
OUTPUT_CAP_BYTES=4_000_000_000
w=int(os.environ['WAVE'])
root=BASE/f'wz_wave_{w:04d}'
prior=BASE/f'wz_wave_{w-1:04d}'
expected='3826142b6cddb549e831c8302be1d460ba3e85ee96bb7736af5549f878b3bf44'
entries=json.load(open(root/f'private/WAVE_{w:04d}_MANIFEST_PRIVATE.json'))['selected_entries']
new=[]
c=collections.Counter()
outbytes=0
for e in entries:
 s=e['shard_id']
 o=root/('output/shard_'+s)
 r=root/('private/SHARD_'+s+'_RECEIPT.json')
 subprocess.check_call([sys.executable,str(OLD/'code/run_one_shard.py'),'--raw',e['source_path'],'--sidecar',e['sidecar_path'],'--output-dir',str(o),'--public-receipt',str(r),'--expected-raw-sha256',e['source_sha256_cached'],'--expected-sidecar-sha256',e['sidecar_sha256'],'--workers','4'])
 d=json.load(open(r))
 c['raw']+=d['raw_rows']
 c['posting']+=d['outputs']['posting_rows']
 c['evidence']+=d['outputs']['evidence_rows']
 outbytes+=d['outputs']['posting_bytes']+d['outputs']['evidence_bytes']
 if outbytes>OUTPUT_CAP_BYTES:
  raise RuntimeError('wave output cap exceeded')
 new.append({'shard_id':s,'verify_new_output':True,'posting':str(o/'POSTING_NARROW_PRIVATE.parquet'),'evidence':str(o/'EVIDENCE_PRIVATE.parquet'),'production_receipt':str(r),'qa_output':str(root/('private/SHARD_'+s+'_QA.json')),'expected_runner_sha256':expected})
pm=glob.glob(str(prior/'private/QA_MANIFEST_*_PRIVATE.json'))
if len(pm)!=1:
 raise RuntimeError('prior QA manifest count mismatch')
old=json.load(open(pm[0]))['shards']
for x in old:
 x.update(verify_new_output=False)
m={'status':'frozen','shards':old+new}
mp=root/f'private/QA_MANIFEST_{len(old)+16}_PRIVATE.json'
mp.write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
sp=root/f'private/SHARD_SET_{len(old)+16}_QA_PRIVATE.json'
subprocess.check_call([sys.executable,str(OLD/'code/verify_shard_set_outputs.py'),'--manifest',str(mp),'--verifier',str(OLD/'code/verify_one_shard_outputs.py'),'--allowed-root',str(BASE.parent),'--output',str(sp)])
sq=json.load(open(sp))
if sq.get('status')!='pass':
 raise RuntimeError('combined shard-set QA failed')
p={'status':'pass','version':'d64-wz-rolling-qa-v1','wave':w,'new_shard_count':16,'combined_shard_count':len(old)+16,'raw_rows':c['raw'],'posting_rows':c['posting'],'evidence_rows':c['evidence'],'output_bytes':outbytes,'output_budget_max_bytes':OUTPUT_CAP_BYTES,'row_conservation_all':True,'canonical_locator_unique_across_combined_shards':sq['canonical_locator_unique_across_shards'],'canonical_job_hash_unique_across_combined_shards':sq['canonical_job_hash_unique_across_shards'],'runner_sha256':expected,'production_array_job_id':os.environ['PRODUCTION_JOB_ID'],'qa_job_id':os.environ.get('SLURM_JOB_ID'),'api_calls':0,'model_calls':0,'semantic_changes':False,'created_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
t=root/f'public/WAVE_{w:04d}_QA_PUBLIC.json.tmp'
t.write_text(json.dumps(p,indent=2,sort_keys=True)+'\n')
os.replace(t,root/f'public/WAVE_{w:04d}_QA_PUBLIC.json')
