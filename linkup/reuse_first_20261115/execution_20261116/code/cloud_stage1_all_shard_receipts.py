"""Sum all frozen per-shard processing receipts, not raw advertisement data."""
import json,hashlib,sqlite3,os,sys,time,datetime,collections,concurrent.futures,urllib.parse,fcntl
from pathlib import Path
R=Path.home()/'migration';O=R/'execution_20261116/run001/stage1';cache=O/'metadata_cache';t0=time.monotonic();os.umask(0o077)
lock=(O/'STAGE1.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
cat=R/'full_scope_catalog_preflight_20261115/20261115T120402Z/CORPUS_RELEASE_CATALOG_PRIVATE.jsonl';rows=[json.loads(l) for l in cat.open()];assert len(rows)==2464;assert hashlib.sha256(cat.read_bytes()).hexdigest()=='4265e2469a8d3d35a769faad9c163823b0df32364f88061db5ecc5e131b1eb1e'
configs={k:json.loads((R/'private'/(k+'.json')).read_text()) for k in ['kunshan','wuzhen','huazhong']};sources={};errors=[];downloaded=0
sys.path.insert(0,str(R/'code'));from workflow import call

def resolve_and_fetch(ds):
 global downloaded
 ds=list(set(ds));found={};available={}
 for cluster in ['kunshan','wuzhen','huazhong']:
  db=sqlite3.connect((R/cluster/'LEDGER_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True)
  for start in range(0,len(ds),800):
   batch=ds[start:start+800]
   for path,root,rel,size,status,h in db.execute('select path,root,rel,size,status,sha from files where sha in ('+','.join('?' for _ in batch)+')',batch):
    if status=='verified' and 'batch035' not in path.lower():found.setdefault(h,dict(cluster=cluster,path=path,root=root,rel=rel,size=size,status=status,sha256=h))
  db.close()
 assert sum(m['size'] for m in found.values())<128*1024*1024,'receipt_network_cap'
 def fetch(d):
  p=cache/(d+'.metadata');m=found.get(d)
  try:
   if p.exists():assert hashlib.sha256(p.read_bytes()).hexdigest()==d;return d,json.loads(p.read_bytes()),0,None
   assert m and m['size']<2*1024*1024,'verified_small_receipt_not_found'
   c=configs[m['cluster']];url=c['container_sas'].split('?',1)[0]+'/'+urllib.parse.quote(c['snapshot']+'/'+Path(m['root']).name+'/'+m['rel'],safe='/')
   with call(url,'https://storage.azure.com/',headers={'x-ms-version':'2023-11-03'}) as response:b=response.read(m['size']+1)
   assert len(b)==m['size'] and hashlib.sha256(b).hexdigest()==d;p.write_bytes(b);return d,json.loads(b),len(b),None
  except Exception as e:return d,None,0,type(e).__name__
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  for d,obj,n,e in pool.map(fetch,ds):
   if e:errors.append({'sha256':d,'error_type':e})
   else:available[d]=obj;downloaded+=n
 sources.update(found);return available
analysis=resolve_and_fetch([x['original_receipt_sha256'] for x in rows]);(O/'ACCOUNTING_PROGRESS_PUBLIC.json').write_text(json.dumps({'stage':'analysis_receipts_verified','count':len(analysis),'target':2464}))
up=resolve_and_fetch([x['source_receipt_sha256'] for x in analysis.values()]);totals=collections.Counter();worker_profiles=collections.Counter();shard_checks=[];missing=[]
for row in rows:
 a=analysis.get(row['original_receipt_sha256']);p=up.get(a['source_receipt_sha256']) if a else None
 if not p:missing.append(row['shard_id']);continue
 assert a['canonical_ads']==a['output_rows']==row['ad_rows'];assert a['output_sha256']==row['ad_sha256_from_original_receipt'];assert p['shard_id']==row['shard_id']
 complete=p['shard_complete'];account=complete['accounting'];lean=complete['lean_complete'];assert account['canonical_usa_rows']==lean['processed_rows']==row['ad_rows'];assert account['raw_rows']==account['sidecar_rows']
 for k,v in account.items():
  if isinstance(v,(int,float)) and not isinstance(v,bool):totals['accounting.'+k]+=v
 for k in ['wall_seconds','experience_rows','technology_rows','v6_audit_rows','description_empty_rows','parse_errors','truncated_rows','enrichment_incomplete_rows']:
  if isinstance(lean.get(k),(int,float)):totals['lean.'+k]+=lean[k]
 worker_profiles[str(lean.get('workers'))]+=1
 if isinstance(lean.get('workers'),(int,float)) and isinstance(lean.get('wall_seconds'),(int,float)):totals['allocated_worker_seconds_proxy_not_measured_cpu_time']+=lean['workers']*lean['wall_seconds']
 shard_checks.append({'shard_id':row['shard_id'],'catalog_receipt_sha256':row['original_receipt_sha256'],'publication_receipt_sha256':a['source_receipt_sha256'],'raw_rows':account['raw_rows'],'canonical_US_ads':account['canonical_usa_rows'],'source_bytes':account['source_bytes']})
report={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'all_existing_shard_receipts_accounted' if not missing else 'partial_shard_receipt_accounting','target_shards':2464,'verified_shards':len(shard_checks),'missing_shards':len(missing),'analysis_receipts_verified':len(analysis),'publication_receipts_verified':len(up),'totals':dict(totals),'worker_count_distribution':dict(worker_profiles),'downloaded_bytes_this_trace':downloaded,'errors':errors,'source_raw_bytes_match_Job_Descriptions_delivery':totals['accounting.source_bytes']==652027698428,'canonical_US_count_match':totals['accounting.canonical_usa_rows']==204774035,'raw_rows_are_not_unique_advertisements':True,'raw_advertisement_files_read':0,'new_model_calls':0,'elapsed_seconds':time.monotonic()-t0,'full_delivery_unique_contexts':None}
(O/'ALL_SHARD_ACCOUNTING_PRIVATE.json').write_text(json.dumps(shard_checks,indent=2)+'\n');(O/'ALL_SHARD_SOURCE_LOCATORS_PRIVATE.json').write_text(json.dumps(list(sources.values()),indent=2)+'\n');(O/'ALL_SHARD_ACCOUNTING_PUBLIC.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
