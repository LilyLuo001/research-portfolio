#!/usr/bin/env python3
import datetime as dt, hashlib, json, subprocess, sys
from pathlib import Path
ROOT=Path('/public/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/metadata_join_first5_d60');WORK=ROOT/'work_fast';PUB=ROOT/'public';OUT=ROOT/'output_fast';BASE=ROOT/'code/targeted_metadata_join.py';EXPECTED=424226
BASE_SHA='d44ee0be0f8f3c7b93fd5d5ff72aa375d92a257c0481ab7978b29637cbd2ded2';FAST_SHA='598615d8d93c3c14cfbab8869508949ebeab61fcae5adc91281acad4a37dd161';QUAL_RECEIPT_SHA='eb94ab0866c8a9d9bb1c7365bd41c1e1d5c6098285b53392d0a86999158a1350';KEY_RECEIPT_SHA='008b2e3d4efa8e68dbbc23fef530e33973c685566387a99283a4fd141ac9f2ac'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def atomic(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=Path(str(p)+'.tmp');t.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n');t.replace(p)
def main():
 qpath=PUB/'FAST_EXTRACT_QUALIFICATION_PUBLIC.json';q=json.load(open(qpath));assert sha(qpath)==QUAL_RECEIPT_SHA and q['status']=='pass' and q['base_code_sha256']==BASE_SHA and q['fast_code_sha256']==FAST_SHA
 assert sha(BASE)==BASE_SHA and sha(ROOT/'code/fast_extract_batch.py')==FAST_SHA
 m=json.load(open(WORK/'FAST_ARRAY_MAP_PRIVATE.json'));assert m['qualification_receipt_sha256']==QUAL_RECEIPT_SHA and m['base_code_sha256']==BASE_SHA and m['fast_code_sha256']==FAST_SHA
 invs={}
 for kind in ('records','onet'):
  inv=json.load(open(ROOT/'work'/(kind.upper()+'_INVENTORY_PRIVATE.json')));entries=[];scanned_total=0
  for e in [x for x in m['entries'] if x['kind']==kind]:
   spec=json.load(open(e['spec']));rp=Path(spec['receipt']);r=json.load(open(rp));assert r['status']=='complete' and r['identity']['fast_code_sha256']==FAST_SHA and r['identity']['base_code_sha256']==BASE_SHA
   assert r['identity']['batch_spec_sha256']==e['spec_sha256'] and r['identity']['key_receipt_sha256']==KEY_RECEIPT_SHA
   assert r['source_rows_scanned']==e['source_rows'] and r['staged_input_bytes']==e['source_bytes'];scanned_total+=r['source_rows_scanned']
   entries.append({'output':spec['output'],'receipt':str(rp),'receipt_sha256':sha(rp)})
  assert scanned_total==sum(x['rows'] for x in inv['files'])
  mp=WORK/(kind.upper()+'_FAST_EXTRACTION_MANIFEST_PRIVATE.json');atomic(mp,{'kind':kind,'frozen_source_inventory_sha256':inv['inventory_sha256'],'batches':entries});invs[kind]=(inv,mp)
 OUT.mkdir(parents=True,exist_ok=True);output=OUT/'FIRST5_METADATA_FAST_PRIVATE.parquet';private=WORK/'FIRST5_METADATA_FAST_RECEIPT_PRIVATE.json';public=PUB/'FIRST5_METADATA_FAST_RECEIPT_PUBLIC.json'
 ri,rm=invs['records'];oi,om=invs['onet']
 subprocess.run([sys.executable,str(BASE),'finalize','--key-dir',str(ROOT/'private/keys'),'--key-receipt',str(ROOT/'output/FIRST5_KEY_PREP_RECEIPT_PUBLIC.json'),'--records-manifest',str(rm),'--onet-manifest',str(om),'--official-codes','/public/home/lilysharp/linkup_analysis_execution_oct02/private/official_onet2019_occupations.csv','--output',str(output),'--private-receipt',str(private),'--public-receipt',str(public),'--expected-rows',str(EXPECTED),'--expected-records-bytes',str(ri['bytes']),'--expected-onet-bytes',str(oi['bytes']),'--expected-records-inventory-sha256',ri['inventory_sha256'],'--expected-onet-inventory-sha256',oi['inventory_sha256'],'--source-cache-cap-bytes','35000000000'],check=True)
 pr=json.load(open(public));c=pr['counts'];prefixes=('records_','onet_','company_','geography_','occupation_','created_');parts={p:sum(v for k,v in c.items() if k.startswith(p)) for p in prefixes}
 assert pr['status']=='complete' and pr['posting_denominator']==EXPECTED and pr['output_rows']==EXPECTED and pr['row_conservation'] and all(v==EXPECTED for v in parts.values())
 assert c.get('records_one_to_many_unresolved',0)==0 and c.get('onet_one_to_many_unresolved',0)==0 and c.get('created_calendar_date_disagreement',0)==0 and sha(output)==pr['output_sha256']
 qa={'version':'d61-fast-first5-metadata-qa-v1','created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'pass','posting_denominator':EXPECTED,'output_rows':pr['output_rows'],'output_bytes':pr['output_bytes'],'output_sha256':pr['output_sha256'],'partition_sums':parts,'counts':c,'qualification_receipt_sha256':sha(qpath),'base_code_sha256':BASE_SHA,'fast_code_sha256':FAST_SHA,'array_map_sha256':sha(WORK/'FAST_ARRAY_MAP_PRIVATE.json'),'checks':{'row_conservation':True,'all_status_partitions':True,'no_multiplicity_failures':True,'no_created_disagreement':True,'output_hash':True},'claim_boundary':pr['claim_boundary']}
 atomic(PUB/'FIRST5_METADATA_FAST_QA_PUBLIC.json',qa);print(json.dumps(qa,sort_keys=True))
if __name__=='__main__':main()
