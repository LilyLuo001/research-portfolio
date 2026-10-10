#!/bin/bash
#SBATCH --job-name=d63-wz-qa
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --time=00:20:00
#SBATCH --no-requeue
#SBATCH --output=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/wz_wave_0001/logs/qa-%j.out
#SBATCH --error=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/wz_wave_0001/logs/qa-%j.err
set -euo pipefail; umask 077
ROOT=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/wz_wave_0001
OLD=/work/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/domestic_wz_d60
RUNTIME=/work/home/lilysharp/linkup_release_v1/runtime_py38
EXPECTED=3826142b6cddb549e831c8302be1d460ba3e85ee96bb7736af5549f878b3bf44
set +u; source /etc/profile >/dev/null 2>&1 || true; module purge >/dev/null 2>&1 || true; module load python/3.8.10; set -u
export PYTHONPATH="$OLD/code:$RUNTIME" ROOT OLD EXPECTED
python3 - <<'PY'
import collections,datetime as dt,hashlib,json,os,pathlib,subprocess,sys
root=pathlib.Path(os.environ['ROOT']);old=pathlib.Path(os.environ['OLD']);expected=os.environ['EXPECTED']
def sha(p):
 h=hashlib.sha256();
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
entries=json.load(open(root/'private/WAVE_0001_MANIFEST_PRIVATE.json'))['selected_entries']
if len(entries)!=4 or len({x['shard_id'] for x in entries})!=4:raise RuntimeError('new wave identity failure')
new=[]
for e in entries:
 sid=e['shard_id'];out=root/('output/shard_'+sid);receipt=root/('private/SHARD_'+sid+'_RECEIPT.json')
 subprocess.check_call([sys.executable,str(old/'code/run_one_shard.py'),'--raw',e['source_path'],'--sidecar',e['sidecar_path'],'--output-dir',str(out),'--public-receipt',str(receipt),'--expected-raw-sha256',e['source_sha256_cached'],'--expected-sidecar-sha256',e['sidecar_sha256'],'--workers','4'])
 if json.load(open(out/'PROGRESS_PUBLIC.json')).get('resume_verified') is not True:raise RuntimeError('resume verification absent')
 new.append({'shard_id':sid,'verify_new_output':True,'posting':str(out/'POSTING_NARROW_PRIVATE.parquet'),'evidence':str(out/'EVIDENCE_PRIVATE.parquet'),'production_receipt':str(receipt),'qa_output':str(root/('private/SHARD_'+sid+'_QA.json')),'expected_runner_sha256':expected})
oldm=json.load(open(old/'private/QA_MANIFEST_PRIVATE.json'))
prior=[]
for x in oldm['shards']:
 y=dict(x);y['verify_new_output']=False;prior.append(y)
manifest={'status':'frozen','scope':'D63 WZ accepted-four plus new-four mechanical QA','shards':prior+new}
mp=root/'private/QA_MANIFEST_8_PRIVATE.json';mp.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
setp=root/'private/SHARD_SET_8_QA_PRIVATE.json'
subprocess.check_call([sys.executable,str(old/'code/verify_shard_set_outputs.py'),'--manifest',str(mp),'--verifier',str(old/'code/verify_one_shard_outputs.py'),'--allowed-root','/work/home/lilysharp/linkup_rulefirst_20261008','--output',str(setp)])
setq=json.load(open(setp))
if setq.get('status')!='pass' or setq.get('shard_count')!=8:raise RuntimeError('combined set QA failed')
c=collections.Counter();output_bytes=0;elapsed=[]
for e in entries:
 r=json.load(open(root/('private/SHARD_'+e['shard_id']+'_RECEIPT.json')))
 if r.get('status')!='complete' or r.get('identity',{}).get('runner_sha256')!=expected or not r.get('row_conservation'):raise RuntimeError('receipt failure')
 c['raw_rows']+=r['raw_rows'];c['posting_rows']+=r['outputs']['posting_rows'];c['evidence_rows']+=r['outputs']['evidence_rows'];output_bytes+=r['outputs']['posting_bytes']+r['outputs']['evidence_bytes'];elapsed.append(r['elapsed_seconds'])
if output_bytes>1_000_000_000:raise RuntimeError('output budget exceeded')
pub={'status':'pass','version':'d63-wz-wave-0001-qa-v1','scope':'mechanical QA of four new in-place Wuzhen frozen-rule outputs plus cross-eight uniqueness','qa_job_id':os.environ.get('SLURM_JOB_ID'),'production_array_job_id':os.environ.get('PRODUCTION_JOB_ID'),'scheduler':{'partition':'wzhdtest','cpus':4,'memory_gib':8,'time_limit':'00:20:00','dcu_requested':1,'dcu_use':'scheduler-QOS-minimum; unused by CPU verifier'},'new_shard_count':4,'combined_shard_count':8,'raw_rows':c['raw_rows'],'posting_rows':c['posting_rows'],'evidence_rows':c['evidence_rows'],'output_bytes':output_bytes,'output_budget_max_bytes':1_000_000_000,'row_conservation_all':True,'full_output_sha256_all':True,'frozen_schema_all':True,'evidence_span_structure_errors':0,'evidence_locator_index_and_count_consistent':True,'canonical_locator_unique_across_combined_shards':setq['canonical_locator_unique_across_shards'],'canonical_job_hash_unique_across_combined_shards':setq['canonical_job_hash_unique_across_shards'],'distinct_source_file_count_combined':setq['distinct_source_file_count'],'idempotent_resume_verified_all':True,'runner_sha256':expected,'elapsed_seconds_min':min(elapsed),'elapsed_seconds_max':max(elapsed),'api_calls':0,'model_calls':0,'semantic_changes':False,'claim_boundary':'rule-observed candidates; no-match remains unknown; metadata linkage pending','created_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
t=root/'public/WAVE_0001_QA_PUBLIC.json.tmp';t.write_text(json.dumps(pub,indent=2,sort_keys=True)+'\n');os.replace(t,root/'public/WAVE_0001_QA_PUBLIC.json')
PY
