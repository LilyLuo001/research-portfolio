#!/usr/bin/env python3
import datetime as dt, hashlib, importlib.util, json, os
from pathlib import Path
ROOT=Path('/public/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/metadata_join_first5_d60');WORK=ROOT/'work_fast';HITS=ROOT/'private/hits_fast';PUB=ROOT/'public';CAP=10_000_000_000
BASE_SHA='d44ee0be0f8f3c7b93fd5d5ff72aa375d92a257c0481ab7978b29637cbd2ded2';FAST_SHA='598615d8d93c3c14cfbab8869508949ebeab61fcae5adc91281acad4a37dd161';QUAL_SHA='2117bcbdc2ca66cb14ec3c229695468271fceee77f1a997e760baa23be1fdc2c';QUAL_RECEIPT_SHA='eb94ab0866c8a9d9bb1c7365bd41c1e1d5c6098285b53392d0a86999158a1350'
EXPECTED={'records':{'files':1160,'bytes':15415146010,'digest':'ff7d9d7567282308472e944b2ff2bdf10698f428d98ffc41534ffd623a86ffb9'},'onet':{'files':62,'bytes':11190962194,'digest':'ad19d7cdb535a084a414ee8e920d680791cca12a75e2bf8fdff4444134929e9b'}}
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def atomic(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=Path(str(p)+'.tmp');t.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n');os.replace(t,p)
def groups(rows):
 out=[];cur=[];n=0
 for x in rows:
  if cur and n+x['size_bytes']>CAP:out.append(cur);cur=[];n=0
  cur.append(x);n+=x['size_bytes']
 if cur:out.append(cur)
 return out
def main():
 qpath=PUB/'FAST_EXTRACT_QUALIFICATION_PUBLIC.json';q=json.loads(qpath.read_text())
 assert sha(qpath)==QUAL_RECEIPT_SHA and q['status']=='pass' and q['fast_code_sha256']==FAST_SHA and q['qualification_code_sha256']==QUAL_SHA and q['base_code_sha256']==BASE_SHA
 assert sha(ROOT/'code/fast_extract_batch.py')==FAST_SHA and sha(ROOT/'code/targeted_metadata_join.py')==BASE_SHA
 WORK.mkdir(parents=True,exist_ok=True);HITS.mkdir(parents=True,exist_ok=True);mapping=[]
 for kind in ('records','onet'):
  inv=json.load(open(ROOT/'work'/(kind.upper()+'_INVENTORY_PRIVATE.json')));exp=EXPECTED[kind]
  assert len(inv['files'])==exp['files'] and inv['bytes']==exp['bytes'] and inv['inventory_sha256']==exp['digest']
  ids=[x['source_id'] for x in inv['files']];paths=[x['path'] for x in inv['files']];assert len(ids)==len(set(ids)) and len(paths)==len(set(paths))
  gs=groups(inv['files']);assert len(gs)==2 and all(sum(x['size_bytes'] for x in g)<=CAP for g in gs)
  assert {x['source_id'] for g in gs for x in g}==set(ids) and sum(len(g) for g in gs)==len(ids)
  for i,g in enumerate(gs,1):
   bid='%s_%02d'%(kind,i);spec=WORK/(bid+'_SPEC_PRIVATE.json');output=HITS/(bid+'.parquet');receipt=WORK/(bid+'_RECEIPT_PRIVATE.json')
   atomic(spec,{'batch_id':'fast_'+bid,'kind':kind,'staging_cap_bytes':CAP,'key_dir':str(ROOT/'private/keys'),'key_receipt':str(ROOT/'output/FIRST5_KEY_PREP_RECEIPT_PUBLIC.json'),'input_files':[{k:x[k] for k in ('source_id','path','size_bytes','sha256')} for x in g],'output':str(output),'receipt':str(receipt)})
   mapping.append({'array_index':len(mapping)+1,'kind':kind,'batch':i,'spec':str(spec),'spec_sha256':sha(spec),'source_files':len(g),'source_bytes':sum(x['size_bytes'] for x in g),'source_rows':sum(x['rows'] for x in g)})
 atomic(WORK/'FAST_ARRAY_MAP_PRIVATE.json',{'version':'d61-fast-array-v1','qualification_receipt_sha256':QUAL_RECEIPT_SHA,'source_inventories':EXPECTED,'base_code_sha256':BASE_SHA,'fast_code_sha256':FAST_SHA,'entries':mapping})
 atomic(PUB/'FAST_SPECS_RECEIPT_PUBLIC.json',{'version':'d61-fast-specs-v1','created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'complete','qualification_receipt_sha256':QUAL_RECEIPT_SHA,'source_inventories':EXPECTED,'base_code_sha256':BASE_SHA,'fast_code_sha256':FAST_SHA,'batches':[{k:x[k] for k in ('array_index','kind','batch','spec_sha256','source_files','source_bytes','source_rows')} for x in mapping]})
if __name__=='__main__':main()
