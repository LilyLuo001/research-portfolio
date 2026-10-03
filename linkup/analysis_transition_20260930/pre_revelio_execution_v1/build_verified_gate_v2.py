#!/usr/bin/env python3
"""Build an isolated, strictly validated regional gate and flat receipt handoff."""
import fcntl, hashlib, importlib.util, json, os, shutil, socket, time
from pathlib import Path

ROOT=Path(os.environ.get('LINKUP_GATE_ROOT','/public/home/lilysharp/linkup_release_v1/semantic_v1'))
KS=ROOT/'kunshan'; WZ=ROOT/'final_gate_wuzhen'
OUT=ROOT/'gate_v2_20261003'; TEMP=Path(str(OUT)+'.building')
MODULE=Path(os.environ.get('LINKUP_GATE_MODULE','/public/home/lilysharp/linkup_analysis_v1/stage_c_release_v1/final_receipt_gate.py'))
STATUS=ROOT/'gate_v2_validation_status.json'

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()

def status(phase,**extra):
 value={'status':'running','phase':phase,'host':socket.gethostname(),'pid':os.getpid(),'updated_at':time.time(),**extra}
 temp=Path(str(STATUS)+'.tmp'); temp.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n'); os.replace(temp,STATUS)

lock=(ROOT/'gate_v2_validation.lock').open('a+')
try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError: raise SystemExit('isolated gate v2 validation already active')

spec=importlib.util.spec_from_file_location('gate',MODULE); gate=importlib.util.module_from_spec(spec); spec.loader.exec_module(gate)
ks_plan=gate.load_plan(KS/'plan.jsonl'); wz_plan=gate.load_plan(WZ/'plan.jsonl')
ks_ids={x['shard_id'] for x in ks_plan}; wz_ids={x['shard_id'] for x in wz_plan}
if len(ks_ids)!=1358 or len(wz_ids)!=1106 or ks_ids & wz_ids or len(ks_ids|wz_ids)!=2464: raise RuntimeError('exact ID union failed')
status('validate_kunshan_receipts',processed_receipts=0,total_receipts=2464)
ks_result=gate.validate_region(ks_plan,KS/'checkpoints',KS/'checkpoints/REGION_PUBLISHED_COMPLETE.json','kunshan')
status('validate_wuzhen_receipts',processed_receipts=1358,total_receipts=2464)
wz_expected=gate.load_wz_expectations(WZ/'checkpoints',wz_plan)
wz_result=gate.validate_region(wz_plan,WZ/'checkpoints',WZ/'checkpoints/REGION_PUBLISHED_COMPLETE.json','wuzhen',wz_expected)
status('build_flat_receipt_handoff',processed_receipts=2464,total_receipts=2464)
if TEMP.exists(): shutil.rmtree(TEMP)
(TEMP/'published_receipts_v2').mkdir(parents=True); (TEMP/'plans').mkdir()
for source in list((KS/'checkpoints').glob('*.published.json'))+list((WZ/'checkpoints').glob('*.published.json')):
 dest=TEMP/'published_receipts_v2'/source.name
 if dest.exists(): raise RuntimeError('flat receipt collision: '+source.name)
 try: os.link(source,dest)
 except OSError: shutil.copy2(source,dest)
shutil.copy2(KS/'plan.jsonl',TEMP/'plans/kunshan.plan.jsonl'); shutil.copy2(WZ/'plan.jsonl',TEMP/'plans/wuzhen.plan.jsonl')
receipts=sorted((TEMP/'published_receipts_v2').glob('*.published.json'))
if len(receipts)!=2464: raise RuntimeError('flat archive count failed')
marker={'status':'complete','version':'isolated_gate_v2_20261003','code_sha256':gate.CODE,'regions':[ks_result,wz_result],
 'total_shards':2464,'total_raw_description_rows':ks_result['raw_rows']+wz_result['raw_rows'],
 'final_publication_complete':True,'exact_disjoint_id_union':True,'finished_at':time.time()}
(TEMP/'ALL_REGIONS_VERIFIED_COMPLETE.json').write_text(json.dumps(marker,indent=2,sort_keys=True)+'\n')
manifest={'status':'complete','total_receipts':2464,'gate_sha256':sha(TEMP/'ALL_REGIONS_VERIFIED_COMPLETE.json'),
 'plans':{'kunshan':sha(TEMP/'plans/kunshan.plan.jsonl'),'wuzhen':sha(TEMP/'plans/wuzhen.plan.jsonl')},
 'receipt_digest':hashlib.sha256(''.join(p.name+':'+sha(p)+'\n' for p in receipts).encode()).hexdigest()}
(TEMP/'ARCHIVE_MANIFEST.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
if OUT.exists(): raise RuntimeError('v2 output already exists')
os.replace(TEMP,OUT)
status('complete',processed_receipts=2464,total_receipts=2464,path=str(OUT),gate_sha256=manifest['gate_sha256'])
print(json.dumps({'status':'complete','path':str(OUT),'receipts':2464,'gate_sha256':manifest['gate_sha256']}))
