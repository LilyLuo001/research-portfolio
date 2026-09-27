#!/usr/bin/env python3
"""Deterministic, bounded Stage C research sample preparation.

Selects source shards, projects keys once, joins the existing skinny Records
index by hash prefix, retains deterministic bottom-k candidates per stratum,
and fetches prose only for the final sampled source rows.
"""
import argparse, concurrent.futures as cf, datetime as dt, hashlib, heapq, json, os, shutil
from collections import defaultdict
from pathlib import Path
import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

PREFIXES='0123456789abcdef'
NOV=dt.datetime(2022,11,30)
JAN=dt.datetime(2023,1,1)
SNAPSHOT=dt.datetime(2026,9,6,23,59,59)
KEY_SCHEMA=pa.schema([('JOB_HASH',pa.string()),('DESCRIPTION_COMPANY_ID',pa.decimal128(10,0)),
 ('SOURCE_FILE',pa.string()),('SOURCE_ROW',pa.int64()),('SOURCE_FILE_BYTES',pa.int64()),
 ('SOURCE_FILE_ROWS',pa.int64()),('SAMPLE_HASH',pa.string())])
CANDIDATE_SCHEMA=pa.schema(list(KEY_SCHEMA)+[
 ('RECORD_MATCH',pa.bool_()),('RECORD_COMPANY_ID',pa.decimal128(10,0)),('COUNTRY',pa.string()),('STATE',pa.string()),
 ('CREATED',pa.timestamp('ms')),('LAST_UPDATED',pa.timestamp('ms')),('LAST_CHECKED',pa.timestamp('ms')),
 ('DELETE_DATE',pa.timestamp('ms')),('RECORD_SOURCE_ROW',pa.uint64()),('COHORT',pa.string()),
 ('BOUNDARY_STATUS',pa.string()),('JAN01_STATUS',pa.string()),('COUNTRY_GROUP',pa.string())])
SAMPLE_SCHEMA=pa.schema(list(CANDIDATE_SCHEMA)+[
 ('SOURCE_ROW_GROUP',pa.int32()),('ROW_IN_GROUP',pa.int64()),('DESCRIPTION',pa.string()),
 ('DESCRIPTION_UTF8_BYTES',pa.int64()),('STRATUM_DENOMINATOR',pa.int64()),('FINAL_SAMPLE_N',pa.int32()),
 ('WITHIN_SELECTED_SHARDS_WEIGHT',pa.float64())])

def atomic_json(path,obj):
 t=Path(str(path)+'.tmp'); t.write_text(json.dumps(obj,indent=2,sort_keys=True,default=str)+'\n'); os.replace(t,path)
def tree_bytes(path): return sum(p.stat().st_size for p in path.rglob('*') if p.is_file()) if path.exists() else 0
def ensure_cap(path,cap):
 used=tree_bytes(path)
 if used>cap: raise RuntimeError('output cap exceeded: %d > %d'%(used,cap))
 return used
def sha_file(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def source_info(path):
 pf=pq.ParquetFile(path); st=path.stat()
 return {'file_name':path.name,'path':str(path),'bytes':st.st_size,'mtime_ns':st.st_mtime_ns,
  'rows':pf.metadata.num_rows,'row_groups':pf.metadata.num_row_groups,
  'schema_sha256':hashlib.sha256(str(pf.schema_arrow).encode()).hexdigest()}
def source_set_fingerprint(items):
 return hashlib.sha256(json.dumps(items,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def rank(seed,name): return hashlib.sha256((seed+'\0'+name).encode()).hexdigest()
def sample_hash(seed,job_hash,source,row):
 return hashlib.sha256((seed+'\0'+str(job_hash)+'\0'+source+'\0'+str(row)).encode()).hexdigest()
def clean_dt(x):
 if x is None:return None
 if getattr(x,'tzinfo',None): return x.astimezone(dt.timezone.utc).replace(tzinfo=None)
 return x
def cohort(created):
 created=clean_dt(created)
 if created is None or created>SNAPSHOT:return 'other'
 y=created.year
 if y==2015:return '2015'
 if 2016<=y<=2017:return '2016-17'
 if 2018<=y<=2019:return '2018-19'
 if 2020<=y<=2022:return '2020-22'
 if y>=2023:return '2023-latest'
 return 'other'
def boundary_status(created,end,boundary):
 created,end=clean_dt(created),clean_dt(end)
 if created is None or end is None:return 'unknown'
 if end<created:return 'invalid_negative'
 if created>SNAPSHOT or end>SNAPSHOT:return 'future_out_of_snapshot'
 if created>=boundary:return 'starts_on_or_after_boundary'
 if end>=boundary:return 'crosses_boundary'
 return 'ends_before_boundary'
def verify_evidence(path):
 if not path:return
 x=json.loads(Path(path).read_text())
 if x.get('status')!='PASS' or not x.get('all_sha256_match',False):
  raise RuntimeError('destination SHA evidence is not PASS')
def verify_records_index(complete_path):
 complete_path=Path(complete_path); marker=json.loads(complete_path.read_text())
 manifest_path=complete_path.parent/marker.get('manifest','index_manifest.json')
 manifest=json.loads(manifest_path.read_text())
 if marker.get('sha256')!=sha_file(manifest_path) or manifest.get('status')!='complete':
  raise RuntimeError('records index COMPLETE/manifest validation failed')
 return manifest_path

def select_sources(cfg):
 manifest=Path(cfg['description_manifest'])
 paths=[Path(x) for x in manifest.read_text().splitlines() if x.strip()]
 if len(paths)!=len(set(map(str,paths))): raise RuntimeError('description manifest contains duplicate paths')
 infos=[source_info(p) for p in paths]
 chosen=sorted(infos,key=lambda x:(rank(cfg['seed'],x['file_name']),x['file_name']))[:cfg['selected_source_files']]
 return infos,chosen,hashlib.sha256(manifest.read_bytes()).hexdigest()

def project_keys(chosen,out,cfg):
 keydir=out/'keys_by_prefix'; keydir.mkdir(parents=True,exist_ok=True)
 writers={}; tmps={}; counts=defaultdict(int)
 try:
  for info in chosen:
   p=Path(info['path']); pf=pq.ParquetFile(p); source_row=0
   for batch in pf.iter_batches(columns=['JOB_HASH','COMPANY_ID'],batch_size=cfg['batch_rows'],use_threads=True):
    hashes=batch.column(0); companies=batch.column(1)
    if hashes.null_count: raise RuntimeError('null JOB_HASH in selected source '+p.name)
    valid=pc.match_substring_regex(hashes,r'^[0-9a-f]{32}$')
    if not pc.all(valid).as_py(): raise RuntimeError('malformed JOB_HASH in selected source '+p.name)
    first=np.asarray(pc.utf8_slice_codeunits(hashes,0,1).to_numpy(zero_copy_only=False))
    hash_list=hashes.to_pylist()
    sample_hashes=[sample_hash(cfg['seed'],h,p.name,source_row+i) for i,h in enumerate(hash_list)]
    base=pa.Table.from_arrays([hashes,companies,pa.array([p.name]*batch.num_rows),
      pa.array(np.arange(source_row,source_row+batch.num_rows,dtype=np.int64)),
      pa.array([info['bytes']]*batch.num_rows,type=pa.int64()),pa.array([info['rows']]*batch.num_rows,type=pa.int64()),
      pa.array(sample_hashes)],schema=KEY_SCHEMA)
    for prefix in PREFIXES:
     idx=np.flatnonzero(first==prefix)
     if not idx.size:continue
     if prefix not in writers:
      tmp=keydir/('prefix_%s.parquet.tmp'%prefix); tmps[prefix]=tmp
      writers[prefix]=pq.ParquetWriter(tmp,KEY_SCHEMA,compression='zstd',use_dictionary=True)
     part=base.take(pa.array(idx,type=pa.int64())); writers[prefix].write_table(part); counts[prefix]+=part.num_rows
    source_row+=batch.num_rows
   if source_row!=info['rows']:raise RuntimeError('source row conservation failed '+p.name)
   ensure_cap(out,cfg['max_output_bytes'])
 finally:
  for w in writers.values():w.close()
 for prefix,tmp in tmps.items():
  final=tmp.with_suffix(''); rows=pq.ParquetFile(tmp).metadata.num_rows
  if rows!=counts[prefix]:raise RuntimeError('prefix footer mismatch')
  os.replace(tmp,final)
 return dict(counts)

def join_prefix(args):
 prefix,keyfile,indexdir,outdir,seed,k= args
 pa.set_cpu_count(2)
 desc=pq.read_table(keyfile)
 recfiles=sorted((Path(indexdir)/('hash_prefix='+prefix)).glob('*.parquet'))
 cols=['JOB_HASH','COMPANY_ID','COUNTRY','STATE','CREATED','LAST_UPDATED','LAST_CHECKED','DELETE_DATE','RECORD_SOURCE_ROW']
 if recfiles:
  rec=pq.read_table(recfiles,columns=cols,use_threads=True)
  idx=pc.index_in(desc['JOB_HASH'],value_set=rec['JOB_HASH'])
  aligned={c:pc.take(rec[c],idx).to_pylist() for c in cols[1:]}
 else:
  rec=pa.table({'JOB_HASH':pa.array([],type=pa.string())})
  idx=pa.array([None]*desc.num_rows,type=pa.int32())
  aligned={c:[None]*desc.num_rows for c in cols[1:]}
 d={c:desc[c].to_pylist() for c in desc.column_names}
 heaps=defaultdict(list); denoms=defaultdict(int); serial=0
 for i in range(desc.num_rows):
  matched=idx[i].as_py() is not None
  cr=aligned['CREATED'][i] if matched else None; lc=aligned['LAST_CHECKED'][i] if matched else None
  co=cohort(cr) if matched else 'unmatched'
  bs=boundary_status(cr,lc,NOV) if matched else 'unmatched'
  js=boundary_status(cr,lc,JAN) if matched else 'unmatched'
  country=aligned['COUNTRY'][i] if matched else None
  cg='USA' if country=='USA' else ('unknown' if country is None else 'nonUSA')
  stratum=cg+'|'+co+'|'+bs; denoms[stratum]+=1
  row={c:d[c][i] for c in d}
  row.update({'RECORD_MATCH':matched,'RECORD_COMPANY_ID':aligned['COMPANY_ID'][i],
   'COUNTRY':aligned['COUNTRY'][i],'STATE':aligned['STATE'][i],'CREATED':cr,
   'LAST_UPDATED':aligned['LAST_UPDATED'][i],'LAST_CHECKED':lc,'DELETE_DATE':aligned['DELETE_DATE'][i],
   'RECORD_SOURCE_ROW':aligned['RECORD_SOURCE_ROW'][i],'COHORT':co,'BOUNDARY_STATUS':bs,'JAN01_STATUS':js,
   'COUNTRY_GROUP':cg})
  rv=int(row['SAMPLE_HASH'],16); serial+=1; item=(-rv,serial,row)
  h=heaps[stratum]
  if len(h)<k:heapq.heappush(h,item)
  elif rv < -h[0][0]:heapq.heapreplace(h,item)
 rows=[]
 for h in heaps.values():rows.extend(x[2] for x in h)
 dest=Path(outdir)/('candidates_%s.parquet'%prefix); tmp=Path(str(dest)+'.tmp')
 pq.write_table(pa.Table.from_pylist(rows,schema=CANDIDATE_SCHEMA),tmp,compression='zstd'); os.replace(tmp,dest)
 meta={'prefix':prefix,'description_rows':desc.num_rows,'record_rows':rec.num_rows,'candidate_rows':len(rows),'denominators':dict(denoms)}
 atomic_json(Path(outdir)/('prefix_%s.json'%prefix),meta); return meta

def merge_candidates(out,cfg):
 canddir=out/'prefix_candidates'; heaps=defaultdict(list); denoms=defaultdict(int); serial=0
 for mpath in sorted(canddir.glob('prefix_?.json')):
  m=json.loads(mpath.read_text())
  for s,n in m['denominators'].items():denoms[s]+=n
 for p in sorted(canddir.glob('candidates_?.parquet')):
  for row in pq.read_table(p).to_pylist():
   s=row['COUNTRY_GROUP']+'|'+row['COHORT']+'|'+row['BOUNDARY_STATUS']; rv=int(row['SAMPLE_HASH'],16); serial+=1; item=(-rv,serial,row); h=heaps[s]
   if len(h)<cfg['final_per_stratum']:heapq.heappush(h,item)
   elif rv < -h[0][0]:heapq.heapreplace(h,item)
 rows=[]
 for s,h in sorted(heaps.items()):
  chosen=sorted((x[2] for x in h),key=lambda r:r['SAMPLE_HASH']); n=len(chosen); denom=denoms[s]
  for r in chosen:r['_DENOM']=denom;r['_N']=n
  rows.extend(chosen)
 keys=out/'sample_keys.parquet'; pq.write_table(pa.Table.from_pylist([{k:v for k,v in r.items() if not k.startswith('_')} for r in rows],schema=CANDIDATE_SCHEMA),keys,compression='zstd')
 atomic_json(out/'stratum_denominators.json',{'denominators':dict(sorted(denoms.items())),
  'sample_counts':{s:len(h) for s,h in sorted(heaps.items())},'input_rows':sum(denoms.values())})
 return rows,denoms

def fetch_text(rows,out,cfg):
 byfile=defaultdict(list)
 for r in rows:byfile[r['SOURCE_FILE']].append(r)
 manifest={Path(x).name:Path(x) for x in Path(cfg['description_manifest']).read_text().splitlines() if x.strip()}
 final=[]
 for name,items in sorted(byfile.items()):
  p=manifest[name]; pf=pq.ParquetFile(p); offsets=[]; cur=0
  for rg in range(pf.metadata.num_row_groups):
   n=pf.metadata.row_group(rg).num_rows; offsets.append((cur,cur+n,rg));cur+=n
  wanted=defaultdict(list)
  for r in items:
   sr=r['SOURCE_ROW']
   for lo,hi,rg in offsets:
    if lo<=sr<hi:wanted[rg].append((r,sr-lo));break
   else:raise RuntimeError('SOURCE_ROW out of bounds')
  for rg,pairs in wanted.items():
   t=pf.read_row_group(rg,columns=['JOB_HASH','DESCRIPTION'])
   for r,within in pairs:
    if t['JOB_HASH'][within].as_py()!=r['JOB_HASH']:raise RuntimeError('source pointer hash mismatch')
    text=t['DESCRIPTION'][within].as_py(); outrow={k:v for k,v in r.items() if not k.startswith('_')}
    outrow.update({'SOURCE_ROW_GROUP':rg,'ROW_IN_GROUP':within,'DESCRIPTION':text,
      'DESCRIPTION_UTF8_BYTES':None if text is None else len(text.encode('utf-8')),
      'STRATUM_DENOMINATOR':r['_DENOM'],'FINAL_SAMPLE_N':r['_N'],
      'WITHIN_SELECTED_SHARDS_WEIGHT':None if not r['_N'] else r['_DENOM']/r['_N']})
    final.append(outrow)
 dest=out/'sample_ads.parquet';tmp=Path(str(dest)+'.tmp')
 pq.write_table(pa.Table.from_pylist(final,schema=SAMPLE_SCHEMA),tmp,compression='zstd');os.replace(tmp,dest)
 return len(final)

def validate_resume_projection(out,checkpoint,fp):
 if not checkpoint.exists():return False
 x=json.loads(checkpoint.read_text())
 if x.get('source_fingerprint')!=fp:return False
 files=list((out/'keys_by_prefix').glob('prefix_?.parquet'))
 expected={p for p,n in x.get('prefix_rows',{}).items() if n}
 actual={p.stem.split('_')[-1] for p in files}
 return actual==expected and sum(pq.ParquetFile(p).metadata.num_rows for p in files)==x.get('rows')

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);args=ap.parse_args()
 cfg=json.loads(Path(args.config).read_text()); out=Path(cfg['output_dir']); out.mkdir(parents=True,exist_ok=True)
 lock=(out/'.lock'); fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
 try:
  os.write(fd,str(os.getpid()).encode()); verify_evidence(cfg.get('destination_sha_validation'))
  records_manifest=verify_records_index(cfg['records_index_complete'])
  identity={'config_sha256':sha_file(Path(args.config)),'code_sha256':sha_file(Path(__file__)),
   'records_complete_sha256':sha_file(Path(cfg['records_index_complete'])),
   'records_manifest_sha256':sha_file(records_manifest)}
  identity['sha256']=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
  identity_path=out/'run_identity.json'
  if identity_path.exists() and json.loads(identity_path.read_text())!=identity:
   raise RuntimeError('existing output belongs to a different config/code/index identity; use a new output_dir')
  atomic_json(identity_path,identity)
  allinfo,chosen,manifest_sha=select_sources(cfg); fp=source_set_fingerprint(chosen)
  selection_path=out/'selection_manifest.json'
  if selection_path.exists() and json.loads(selection_path.read_text()).get('source_fingerprint')!=fp:
   raise RuntimeError('selected source fingerprint changed; use a new output_dir')
  atomic_json(selection_path,{'region':cfg['region'],'seed':cfg['seed'],'scope_warning':cfg['scope_warning'],
    'description_manifest_sha256':manifest_sha,'available_sources':len(allinfo),'selected_sources':len(chosen),
    'source_fingerprint':fp,'sources':chosen})
  cp=out/'projection_checkpoint.json'
  if not validate_resume_projection(out,cp,fp):
   if (out/'keys_by_prefix').exists():shutil.rmtree(out/'keys_by_prefix')
   counts=project_keys(chosen,out,cfg); atomic_json(cp,{'status':'complete','source_fingerprint':fp,'rows':sum(counts.values()),'prefix_rows':counts})
  canddir=out/'prefix_candidates';canddir.mkdir(exist_ok=True)
  tasks=[]
  for prefix in PREFIXES:
   keyfile=out/'keys_by_prefix'/('prefix_%s.parquet'%prefix)
   if keyfile.exists() and not (canddir/('prefix_%s.json'%prefix)).exists():
    tasks.append((prefix,str(keyfile),cfg['records_index'],str(canddir),cfg['seed'],cfg['per_prefix_per_stratum']))
  workers=min(cfg['join_workers'],max(1,int(os.environ.get('SLURM_CPUS_PER_TASK','1'))//2))
  if tasks:
   with cf.ProcessPoolExecutor(max_workers=workers) as pool:
    for meta in pool.map(join_prefix,tasks): ensure_cap(out,cfg['max_output_bytes'])
  rows,denoms=merge_candidates(out,cfg); n=fetch_text(rows,out,cfg)
  if n!=len(rows):raise RuntimeError('final sample row conservation failed')
  hashes=[r['JOB_HASH'] for r in rows]
  if len(hashes)!=len(set(hashes)):raise RuntimeError('final sample JOB_HASH values are not unique')
  projected_rows=json.loads(cp.read_text())['rows']
  if sum(denoms.values())!=projected_rows:raise RuntimeError('stratum denominators do not conserve projected rows')
  # Recheck selected source fingerprints after every raw read.
  after=[source_info(Path(x['path'])) for x in chosen]
  if source_set_fingerprint(after)!=fp:raise RuntimeError('source fingerprint changed during run')
  used=ensure_cap(out,cfg['max_output_bytes'])
  report={'status':'complete','region':cfg['region'],'selected_source_files':len(chosen),'selected_source_rows':sum(x['rows'] for x in chosen),
   'sample_rows':n,'strata':len(denoms),'output_bytes':used,'source_fingerprint':fp,'records_index':cfg['records_index'],
   'raw_description_scope':'only row groups containing final sampled rows are decoded; only final sampled descriptions are persisted',
   'weight_interpretation':'Denominator/sample_n describes only the deterministic selected-shard frame; it is not a full-corpus representative weight.',
   'temporal_interpretation':'CREATED-to-LAST_CHECKED is an observed vendor envelope; description text has no validated effective timestamp.',
   'scope_warning':cfg['scope_warning'],'completed_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
  atomic_json(out/'run_report.json',report); atomic_json(out/'COMPLETE',{'status':'complete','report_sha256':sha_file(out/'run_report.json')});print(json.dumps(report,sort_keys=True))
 finally:
  os.close(fd)
  if lock.exists():lock.unlink()
if __name__=='__main__':main()
