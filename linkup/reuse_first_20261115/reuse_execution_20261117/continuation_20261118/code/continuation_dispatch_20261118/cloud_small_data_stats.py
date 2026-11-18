"""Bounded two-artifact data-access statistics, not corpus inference or quality certification."""
import os,sys,json,sqlite3,hashlib,urllib.parse,datetime,signal,time,resource,collections
from pathlib import Path

def main():
 os.umask(0o077);signal.alarm(120);t=time.monotonic();resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3));R=Path.home()/'migration';S=R/'scope_continuation_20261117/run001';O=R/'scope_identity_slice_20261118/run001';O.mkdir(parents=True,exist_ok=False)
 sys.dont_write_bytecode=True;sys.path.insert(0,str(S/'parquet_runtime_20261118_run001/libraries'));import pyarrow as pa;import pyarrow.parquet as pq
 sys.path.insert(0,str(R/'code'));from workflow import call
 previous=json.loads((S/'NARROW_SCHEMA_PROBE_V2_PUBLIC.json').read_text());allowed={f['asset']:[(x['name'],x['type']) for x in f['columns']] for f in previous['files']}
 base=json.loads((S/'BASE_SHARD_SCOPE_REGISTER_PRIVATE.json').read_text());b=min((x for x in base if x['ad_rows']>0),key=lambda x:x['ad_bytes']);rec=next(f for f in previous['files'] if f['asset']=='existing_Records_narrow_index')
 targets=[('existing_base_ad',b['ad_sha256'],b['ad_bytes'],b['ad_rows']),('existing_Records_narrow_index',rec['recorded_content_sha256'],rec['expected_size'],rec['footer_rows'])]
 results=[];pins=[];total=0
 for label,sha,size,rows in targets:
  assert 0<size<=1024*1024 and 0<rows<=100000,'small_file_cap'
  matches=[]
  for cluster in ['kunshan','wuzhen','huazhong']:
   db=sqlite3.connect((R/cluster/'LEDGER_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True);db.execute('PRAGMA query_only=ON');db.set_progress_handler(lambda:int(time.monotonic()-t>100),10000)
   matches +=[(cluster,*x) for x in db.execute('SELECT path,root,rel,size FROM files WHERE sha=? AND status=? LIMIT 2',(sha,'verified'))];db.close()
  assert matches;cluster,path,root,rel,n=matches[0];assert n==size
  conf=json.loads((R/'private'/(cluster+'.json')).read_text());url=conf['container_sas'].split('?',1)[0]+'/'+urllib.parse.quote(conf['snapshot']+'/'+Path(root).name+'/'+rel,safe='/')
  def read_range(start,end):
   nonlocal total
   with call(url,'https://storage.azure.com/',headers={'x-ms-version':'2023-11-03','Range':f'bytes={start}-{end}'}) as response:
    assert response.status==206;data=response.read(end-start+2);assert len(data)==end-start+1
   total+=len(data);return data
  import struct
  trailer=read_range(size-8,size-1);assert trailer[4:]==b'PAR1';flen=struct.unpack('<I',trailer[:4])[0];assert 0<flen<size-8
  footer=read_range(size-flen-8,size-9);md=pq.read_metadata(pa.BufferReader(b'PAR1'+footer+trailer));names=md.schema.to_arrow_schema().names
  assert [(f.name,str(f.type)) for f in md.schema.to_arrow_schema()]==allowed[label],'unexpected_schema_no_body_read';assert md.num_rows==rows
  with call(url,'https://storage.azure.com/',headers={'x-ms-version':'2023-11-03'}) as response:
   assert response.status==200;data=response.read(size+1)
  total+=len(data);assert len(data)==size and hashlib.sha256(data).hexdigest()==sha
  source=O/(label+'_SOURCE_PRIVATE.parquet');source.write_bytes(data)
  columns=['JOB_HASH','SOURCE_FILE','SOURCE_ROW','RECORD_SOURCE_ROW','CREATED'] if label=='existing_base_ad' else names
  table=pq.ParquetFile(pa.BufferReader(data)).read(columns=columns,use_threads=False);assert table.num_rows==rows;v={name:table.column(name).to_pylist() for name in columns}
  missing={name:sum(x is None for x in xs) for name,xs in v.items()};dates=[x for x in v['CREATED'] if x is not None]
  r={'asset':label,'rows':rows,'source_bytes':size,'source_sha256':sha,'whole_file_SHA_verified':True,'decoded_columns':columns,'null_counts':missing,'JOB_HASH_unique':len(set(x for x in v['JOB_HASH'] if x is not None)),'CREATED_min':min(dates).isoformat() if dates else None,'CREATED_max':max(dates).isoformat() if dates else None,'full_dataset_or_representative_sample':False}
  if label=='existing_base_ad':
   four=tuple(columns[:4]);keys=list(zip(*(v[k] for k in four)));r.update(four_key_unique=len(set(keys)),four_key_duplicate_rows=rows-len(set(keys)),source_file_unique=len(set(v['SOURCE_FILE'])),nonempty_base_chosen_after_empty_schema_probe=True)
  else:r['COUNTRY_counts']=dict(collections.Counter(str(x) if x is not None else 'NULL' for x in v['COUNTRY']))
  pins.append({'asset':label,'sha256':sha,'bytes':size,'locator':{'cluster':cluster,'path':path,'root':root,'rel':rel},'base_shard':b if label=='existing_base_ad' else None});results.append(r)
 report={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'two_small_derived_data_files_read_and_aggregated','identity_type':'existing_VM_managed_identity','execution_channel':'existing_VM_Agent_RunCommand_as_linkup','files':results,'network_bytes_read':total,'elapsed_seconds':time.monotonic()-t,'new_model_calls':0,'new_semantic_acceptance':0,'raw_advertisement_bodies_read':0,'new_resources':0,'old_results_modified':False,'global_gap_count_inferred':False,'arbitrary_base_to_Records_join_attempted':False,'time_boundary':'CREATED is a first-observed-time proxy; changes do not establish AI causality.'}
 (O/'INPUT_PINS_PRIVATE.json').write_text(json.dumps(pins,indent=2)+'\n');(O/'SMALL_DATA_STATS_PUBLIC.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));signal.alarm(0)
if __name__=='__main__':main()
