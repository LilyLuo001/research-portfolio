#!/usr/bin/env python3
import collections,datetime as dt,json,os,pathlib,subprocess,sys
root=pathlib.Path('/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/wz_wave_0002');prior=pathlib.Path('/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/wz_wave_0001');old=pathlib.Path('/work/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/domestic_wz_d60');expected='3826142b6cddb549e831c8302be1d460ba3e85ee96bb7736af5549f878b3bf44'
entries=json.load(open(root/'private/WAVE_0002_MANIFEST_PRIVATE.json'))['selected_entries']
if len(entries)!=16 or len({x['shard_id'] for x in entries})!=16:raise RuntimeError('wave identity failure')
new=[]
for e in entries:
 sid=e['shard_id'];out=root/('output/shard_'+sid);receipt=root/('private/SHARD_'+sid+'_RECEIPT.json')
 subprocess.check_call([sys.executable,str(old/'code/run_one_shard.py'),'--raw',e['source_path'],'--sidecar',e['sidecar_path'],'--output-dir',str(out),'--public-receipt',str(receipt),'--expected-raw-sha256',e['source_sha256_cached'],'--expected-sidecar-sha256',e['sidecar_sha256'],'--workers','4'])
 if json.load(open(out/'PROGRESS_PUBLIC.json')).get('resume_verified') is not True:raise RuntimeError('resume verification absent')
 new.append({'shard_id':sid,'verify_new_output':True,'posting':str(out/'POSTING_NARROW_PRIVATE.parquet'),'evidence':str(out/'EVIDENCE_PRIVATE.parquet'),'production_receipt':str(receipt),'qa_output':str(root/('private/SHARD_'+sid+'_QA.json')),'expected_runner_sha256':expected})
oldm=json.load(open(prior/'private/QA_MANIFEST_8_PRIVATE.json')); prior_entries=[]
for x in oldm['shards']:
 y=dict(x);y['verify_new_output']=False;prior_entries.append(y)
manifest={'status':'frozen','scope':'D63 WZ accepted-eight plus new-sixteen mechanical QA','shards':prior_entries+new}
mp=root/'private/QA_MANIFEST_24_PRIVATE.json';mp.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n');setp=root/'private/SHARD_SET_24_QA_PRIVATE.json'
subprocess.check_call([sys.executable,str(old/'code/verify_shard_set_outputs.py'),'--manifest',str(mp),'--verifier',str(old/'code/verify_one_shard_outputs.py'),'--allowed-root','/work/home/lilysharp/linkup_rulefirst_20261008','--output',str(setp)])
setq=json.load(open(setp))
if setq.get('status')!='pass' or setq.get('shard_count')!=24:raise RuntimeError('combined set QA failed')
c=collections.Counter();output_bytes=0;elapsed=[]
for e in entries:
 r=json.load(open(root/('private/SHARD_'+e['shard_id']+'_RECEIPT.json')))
 if r.get('status')!='complete' or r.get('identity',{}).get('runner_sha256')!=expected or not r.get('row_conservation'):raise RuntimeError('receipt failure')
 c['raw_rows']+=r['raw_rows'];c['posting_rows']+=r['outputs']['posting_rows'];c['evidence_rows']+=r['outputs']['evidence_rows'];output_bytes+=r['outputs']['posting_bytes']+r['outputs']['evidence_bytes'];elapsed.append(r['elapsed_seconds'])
if output_bytes>4_000_000_000:raise RuntimeError('output budget exceeded')
pub={'status':'pass','version':'d63-wz-wave-0002-qa-v1','scope':'mechanical QA of sixteen new in-place Wuzhen frozen-rule outputs plus cross-24 uniqueness','qa_job_id':os.environ.get('SLURM_JOB_ID'),'production_array_job_id':os.environ.get('PRODUCTION_JOB_ID'),'new_shard_count':16,'combined_shard_count':24,'raw_rows':c['raw_rows'],'posting_rows':c['posting_rows'],'evidence_rows':c['evidence_rows'],'output_bytes':output_bytes,'output_budget_max_bytes':4_000_000_000,'row_conservation_all':True,'full_output_sha256_all':True,'frozen_schema_all':True,'evidence_span_structure_errors':0,'evidence_locator_index_and_count_consistent':True,'canonical_locator_unique_across_combined_shards':setq['canonical_locator_unique_across_shards'],'canonical_job_hash_unique_across_combined_shards':setq['canonical_job_hash_unique_across_shards'],'distinct_source_file_count_combined':setq['distinct_source_file_count'],'idempotent_resume_verified_all':True,'runner_sha256':expected,'elapsed_seconds_min':min(elapsed),'elapsed_seconds_max':max(elapsed),'scheduler':{'partition':'wzhdtest','production_concurrency':3,'production_cpus_per_task':4,'production_memory_gib':8,'dcu_use':'scheduler-QOS-minimum; unused by CPU verifier'},'api_calls':0,'model_calls':0,'semantic_changes':False,'claim_boundary':'rule-observed candidates; no-match remains unknown; metadata linkage pending','created_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
t=root/'public/WAVE_0002_QA_PUBLIC.json.tmp';t.write_text(json.dumps(pub,indent=2,sort_keys=True)+'\n');os.replace(t,root/'public/WAVE_0002_QA_PUBLIC.json')
