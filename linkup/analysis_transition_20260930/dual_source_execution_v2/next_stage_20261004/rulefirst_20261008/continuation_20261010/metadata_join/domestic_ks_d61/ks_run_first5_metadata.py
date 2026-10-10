#!/usr/bin/env python3
import datetime as dt, glob, hashlib, json, os, platform, subprocess, sys
from pathlib import Path
import pyarrow, pyarrow.parquet as pq
ROOT=Path('/public/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/metadata_join_first5_d60')
CODE=ROOT/'code/targeted_metadata_join.py'; KEY_DIR=ROOT/'private/keys'; KEY_RECEIPT=ROOT/'output/FIRST5_KEY_PREP_RECEIPT_PUBLIC.json'
RECORDS_ROOT=Path('/public/home/lilysharp/linkup_analysis_v1/stage_b/records_index_v1')
ONET_ROOT=Path('/public/home/lilysharp/dewey_downloads/data/dewey_ONET_tables/onet-taxonomy')
OFFICIAL=Path('/public/home/lilysharp/linkup_analysis_execution_oct02/private/official_onet2019_occupations.csv')
WORK=ROOT/'work'; HITS=ROOT/'private/hits'; PUB=ROOT/'public'; OUT=ROOT/'output'
CAP=10_000_000_000; EXPECTED=424226
OLD_RECORDS=15415489237; OLD_ONET=11190966290

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def atomic(path,obj):
 path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); tmp=Path(str(path)+'.tmp'); tmp.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n'); os.replace(tmp,path)
def inventory(kind,base,paths):
 rows=[]
 for path in paths:
  p=Path(path); name=p.name.lower()
  if '.part' in name or '.tmp' in name or name.startswith('.') or not p.is_file(): raise RuntimeError('non-final source admitted: '+str(p))
  pf=pq.ParquetFile(str(p)); _=pf.schema_arrow
  rows.append({'source_id':kind+'/'+str(p.relative_to(base)),'relative_path':str(p.relative_to(base)),'path':str(p),'size_bytes':p.stat().st_size,'sha256':sha(p),'rows':pf.metadata.num_rows})
 digest=hashlib.sha256(json.dumps([{'relative_path':x['relative_path'],'size_bytes':x['size_bytes'],'sha256':x['sha256']} for x in rows],sort_keys=True,separators=(',',':')).encode()).hexdigest()
 return rows,digest
def batches(rows):
 out=[]; cur=[]; total=0
 for x in rows:
  if cur and total+x['size_bytes']>CAP: out.append(cur);cur=[];total=0
  if x['size_bytes']>CAP: raise RuntimeError('single source exceeds 10GB batch cap')
  cur.append(x);total+=x['size_bytes']
 if cur: out.append(cur)
 return out
def run(args): subprocess.run([sys.executable,str(CODE)]+args,check=True)
def main():
 for p in (WORK,HITS,PUB,OUT): p.mkdir(parents=True,exist_ok=True)
 key=json.loads(KEY_RECEIPT.read_text()); assert key['posting_rows']==EXPECTED and len(key['key_files'])==16
 assert sha(KEY_RECEIPT)=='008b2e3d4efa8e68dbbc23fef530e33973c685566387a99283a4fd141ac9f2ac'
 assert sha(CODE)=='d44ee0be0f8f3c7b93fd5d5ff72aa375d92a257c0481ab7978b29637cbd2ded2'
 for x in key['key_files']:
  p=KEY_DIR/('keys_'+x['prefix']+'.parquet'); assert p.stat().st_size==x['bytes'] and sha(p)==x['sha256'] and pq.ParquetFile(str(p)).metadata.num_rows==x['rows']
 complete=RECORDS_ROOT/'COMPLETE'; assert sha(complete)=='77e6c971de21440d059ae20d20d21f84af28423a1f884da180aeb7388156afd2'
 assert sha(OFFICIAL)=='8b02868be11d5b55c60b0ab42ac14eb1c0b241dbdff523627c6f10a8ebe184ba'
 rpaths=sorted(glob.glob(str(RECORDS_ROOT/'hash_prefix=*/*.parquet'))); opaths=sorted(glob.glob(str(ONET_ROOT/'*.parquet')))
 if not rpaths or not opaths: raise RuntimeError('source inventory empty')
 records,rdigest=inventory('records',RECORDS_ROOT,rpaths); onet,odigest=inventory('onet',ONET_ROOT,opaths)
 rbytes=sum(x['size_bytes'] for x in records); obytes=sum(x['size_bytes'] for x in onet)
 atomic(WORK/'RECORDS_INVENTORY_PRIVATE.json',{'kind':'records','files':records,'bytes':rbytes,'inventory_sha256':rdigest,'complete_sha256':sha(complete)})
 atomic(WORK/'ONET_INVENTORY_PRIVATE.json',{'kind':'onet','files':onet,'bytes':obytes,'inventory_sha256':odigest})
 manifests={}
 for kind,rows,digest in [('records',records,rdigest),('onet',onet,odigest)]:
  entries=[]
  for i,group in enumerate(batches(rows),1):
   bid='%s_%02d'%(kind,i); output=HITS/(bid+'.parquet'); receipt=WORK/(bid+'_RECEIPT_PRIVATE.json'); spec=WORK/(bid+'_SPEC_PRIVATE.json')
   atomic(spec,{'batch_id':bid,'kind':kind,'staging_cap_bytes':CAP,'key_dir':str(KEY_DIR),'key_receipt':str(KEY_RECEIPT),'input_files':[{k:x[k] for k in ('source_id','path','size_bytes','sha256')} for x in group],'output':str(output),'receipt':str(receipt)})
   run(['extract-batch','--batch-spec',str(spec)])
   entries.append({'output':str(output),'receipt':str(receipt),'receipt_sha256':sha(receipt)})
  mp=WORK/(kind.upper()+'_EXTRACTION_MANIFEST_PRIVATE.json'); atomic(mp,{'kind':kind,'frozen_source_inventory_sha256':digest,'batches':entries}); manifests[kind]=mp
 final=OUT/'FIRST5_METADATA_PRIVATE.parquet'; private=WORK/'FIRST5_METADATA_RECEIPT_PRIVATE.json'; public=PUB/'FIRST5_METADATA_RECEIPT_PUBLIC.json'
 run(['finalize','--key-dir',str(KEY_DIR),'--key-receipt',str(KEY_RECEIPT),'--records-manifest',str(manifests['records']),'--onet-manifest',str(manifests['onet']),'--official-codes',str(OFFICIAL),'--output',str(final),'--private-receipt',str(private),'--public-receipt',str(public),'--expected-rows',str(EXPECTED),'--expected-records-bytes',str(rbytes),'--expected-onet-bytes',str(obytes),'--expected-records-inventory-sha256',rdigest,'--expected-onet-inventory-sha256',odigest,'--source-cache-cap-bytes','35000000000'])
 pr=json.loads(public.read_text()); assert pr['status']=='complete' and pr['posting_denominator']==EXPECTED and pr['output_rows']==EXPECTED and pr['row_conservation']
 checks={k:v for k,v in pr['counts'].items()}
 assert sum(v for k,v in checks.items() if k.startswith('records_'))==EXPECTED
 assert sum(v for k,v in checks.items() if k.startswith('onet_'))==EXPECTED
 assert sum(v for k,v in checks.items() if k.startswith('company_'))==EXPECTED
 assert sum(v for k,v in checks.items() if k.startswith('geography_'))==EXPECTED
 assert sum(v for k,v in checks.items() if k.startswith('occupation_'))==EXPECTED
 qa={'version':'d61-ks-first5-metadata-qa-v1','created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'pass','posting_denominator':EXPECTED,'output_rows':pr['output_rows'],'output_sha256':pr['output_sha256'],'output_bytes':pr['output_bytes'],'runtime':{'python':platform.python_version(),'pyarrow':pyarrow.__version__},'source_identity':{'records_files':len(records),'records_parquet_bytes':rbytes,'records_inventory_sha256':rdigest,'records_complete_sha256':sha(complete),'onet_files':len(onet),'onet_parquet_bytes':obytes,'onet_inventory_sha256':odigest,'official_codes_sha256':sha(OFFICIAL)},'historical_constant_corrections':{'records_rejected':OLD_RECORDS,'records_actual_parquet':rbytes,'records_difference':OLD_RECORDS-rbytes,'records_origin_not_claimed':True,'onet_prior':OLD_ONET,'onet_actual_parquet':obytes,'onet_difference':OLD_ONET-obytes},'checks':{'all_key_hashes':True,'all_source_files_regular_final_parquet':True,'all_source_footers_readable':True,'per_file_sha256_captured':True,'records_partition':True,'onet_partition':True,'company_partition':True,'geography_partition':True,'occupation_partition':True,'multiplicity_and_date_gates':True,'row_conservation':True},'claim_boundary':pr['claim_boundary']}
 atomic(PUB/'FIRST5_METADATA_QA_PUBLIC.json',qa); print(json.dumps(qa,sort_keys=True))
if __name__=='__main__': main()
