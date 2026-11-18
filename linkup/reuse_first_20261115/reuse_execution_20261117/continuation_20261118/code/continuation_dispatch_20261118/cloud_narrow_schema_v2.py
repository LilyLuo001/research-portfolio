import sys,json,sqlite3,hashlib,datetime,importlib.util,urllib.parse,struct,time,resource,signal
from pathlib import Path
R=Path.home()/'migration';sys.dont_write_bytecode=True;sys.path.insert(0,str(R/'scope_continuation_20261117/run001/parquet_runtime_20261118_run001/libraries'));O=R/'scope_continuation_20261117/run001';sys.path.insert(0,str(R/'code'));from workflow import call
resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3));signal.alarm(240);t=time.monotonic()
report={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'bounded_narrow_schema_probe','identity_type':'existing_VM_managed_identity','metadata_only':True,'source_bodies_read':0,'new_model_calls':0,'new_resources':0,'network_bytes_read':0,'files':[],'pyarrow_available':bool(importlib.util.find_spec('pyarrow'))}
base=json.loads((O/'BASE_SHARD_SCOPE_REGISTER_PRIVATE.json').read_text());inv=json.loads((O/'RECORDS_EXECUTION_INVENTORIES_PRIVATE.json').read_text())
b=min(base,key=lambda x:x['ad_bytes']);parts=[f for v in inv for f in v['files'] if f.get('source_binding_status')=='unique_basename_size_rows_source_metadata_match'];p=min(parts,key=lambda x:x['size_bytes'])
targets=[('existing_base_ad',b['ad_sha256'],b['ad_bytes']),('existing_Records_narrow_index',p['sha256'],p['size_bytes'])]
for label,sha,size in targets:
 r={'asset':label,'recorded_content_sha256':sha,'expected_size':size,'whole_content_sha_recomputed':False};matches=[]
 for cluster in ['kunshan','wuzhen','huazhong']:
  d=sqlite3.connect((R/cluster/'LEDGER_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True);d.execute('PRAGMA query_only=ON');d.set_progress_handler(lambda:int(time.monotonic()-t>220),10000)
  for path,root,rel,n,status in d.execute('SELECT path,root,rel,size,status FROM files WHERE sha=? AND status=? LIMIT 2',(sha,'verified')):matches.append((cluster,path,root,rel,n,status))
  d.close()
 if not matches:r['status']='no_existing_verified_ledger_locator';report['files'].append(r);continue
 cluster,path,root,rel,n,status=matches[0];assert n==size
 conf=json.loads((R/'private'/(cluster+'.json')).read_text());url=conf['container_sas'].split('?',1)[0]+'/'+urllib.parse.quote(conf['snapshot']+'/'+Path(root).name+'/'+rel,safe='/')
 r.update(locator_identity='existing_verified_ledger_SHA_and_size',duplicate_verified_locator_count=len(matches),source_container='scnet-'+cluster)
 if not report['pyarrow_available']:r['status']='existing_runtime_missing_pyarrow_no_install';report['files'].append(r);continue
 import pyarrow as pa,pyarrow.parquet as pq
 def get_range(start,end):
  expected=end-start+1
  with call(url,'https://storage.azure.com/',headers={'x-ms-version':'2023-11-03','Range':f'bytes={start}-{end}'}) as response:
   assert response.status==206,'bounded_range_not_honored';data=response.read(expected+1);assert len(data)==expected
  report['network_bytes_read']+=len(data);return data
 try:
  trailer=get_range(size-8,size-1);assert trailer[4:]==b'PAR1','not_parquet';length=struct.unpack('<I',trailer[:4])[0];assert 0<length<=2*1024*1024 and length+8<size,'footer_cap_or_format'
  footer=get_range(size-length-8,size-9);meta=pq.read_metadata(pa.BufferReader(b'PAR1'+footer+trailer));schema=meta.schema.to_arrow_schema();r.update(status='live_Blob_footer_schema_read',footer_sha256=hashlib.sha256(footer+trailer).hexdigest(),footer_bytes=length+8,footer_rows=meta.num_rows,row_groups=meta.num_row_groups,columns=[{'name':f.name,'type':str(f.type)} for f in schema],full_source_rows_read=0)
 except Exception as e:r.update(status='footer_read_failed_no_retry',exception_type=type(e).__name__,http_status=getattr(e,'code',None))
 report['files'].append(r)

def shape(v,depth=0):
 if depth>4:return type(v).__name__
 if isinstance(v,dict):return {k:shape(x,depth+1) for k,x in v.items()}
 if isinstance(v,list):return {'type':'list','length':len(v),'first_type':shape(v[0],depth+1) if v else None}
 return type(v).__name__
account=json.loads((R/'execution_20261116/run001/stage1/ALL_SHARD_ACCOUNTING_PRIVATE.json').read_text());a=next(x for x in account if x['shard_id']==b['shard_id']);d=a['publication_receipt_sha256'];rp=R/'execution_20261116/run001/stage1/metadata_cache'/(d+'.metadata');assert rp.stat().st_size<2*1024*1024;rb=rp.read_bytes();assert hashlib.sha256(rb).hexdigest()==d
report['one_cached_publication_receipt']={'sha256':d,'bytes':len(rb),'shape':shape(json.loads(rb)),'raw_data_read':False,'all_shard_accounting_repeated':False}

report['elapsed_seconds']=time.monotonic()-t
with (O/'NARROW_SCHEMA_PROBE_V2_PUBLIC.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps(report));signal.alarm(0)
