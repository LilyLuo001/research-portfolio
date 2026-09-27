#!/usr/bin/env python3
import concurrent.futures as cf, datetime as dt, hashlib, json, os
from pathlib import Path
DATA=Path('/public/home/lilysharp/dewey_downloads/data/linkup_job_descriptions')
META=Path('/public/home/lilysharp/dewey_downloads/metadata/linkup_job_descriptions')
OUT=Path('/public/home/lilysharp/linkup_analysis_v1/stage_b/metadata/destination_sha_validation.json')

def atomic(path,obj):
 t=Path(str(path)+'.tmp'); t.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n'); os.replace(t,path)
def digest(item):
 name,expected,size=item; p=DATA/name; before=p.stat(); h=hashlib.sha256()
 with p.open('rb',buffering=0) as f:
  while True:
   b=f.read(8*1024*1024)
   if not b: break
   h.update(b)
 after=p.stat(); actual=h.hexdigest()
 return {'file_name':name,'bytes':after.st_size,'expected_bytes':size,'expected_sha256':expected,
  'destination_sha256':actual,'sha256_match':actual==expected,'size_match':after.st_size==size,
  'unchanged_during_hash':(before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)}
started=dt.datetime.now(dt.timezone.utc)
h=json.loads((META/'migration_source_hashes.json').read_text())
expected={x['file_name']:(x['sha256'],x['file_size_bytes']) for x in h['files']}
for p in sorted((META/'bounded_receipts').glob('*.json')):
 x=json.loads(p.read_text()); expected[x['file_name']]=(x['sha256'],x['file_size_bytes'])
items=[(n,s,z) for n,(s,z) in sorted(expected.items())]
results=[]
with cf.ThreadPoolExecutor(max_workers=16) as ex:
 for r in ex.map(digest,items): results.append(r)
failed=[r for r in results if not (r['sha256_match'] and r['size_match'] and r['unchanged_during_hash'])]
out={'status':'PASS' if not failed and len(results)==1358 else 'FAIL','started_utc':started.isoformat(),
 'finished_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'workers':16,'files_expected':1358,
 'files_hashed':len(results),'bytes_hashed':sum(r['bytes'] for r in results),'migration_source_entries':len(h['files']),
 'bounded_receipt_entries':len(expected)-len(h['files']),'failed_count':len(failed),'failures':failed,
 'all_sha256_match':all(r['sha256_match'] for r in results),'all_sizes_match':all(r['size_match'] for r in results),
 'all_unchanged_during_hash':all(r['unchanged_during_hash'] for r in results),'results':results}
atomic(OUT,out); print(json.dumps({k:out[k] for k in ('status','files_hashed','bytes_hashed','failed_count','finished_utc')},sort_keys=True))
if out['status']!='PASS': raise SystemExit(2)
