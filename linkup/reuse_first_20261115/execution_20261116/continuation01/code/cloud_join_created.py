"""Immutable four-key metadata join over three already verified derived tables."""
import collections,datetime,hashlib,json,os,sqlite3,sys,time
from pathlib import Path
R=Path.home()/'migration';B=R/'execution_20261116/run001';O=B/'continuation01';P=O/'carrier_recovery';D=O/'joined_revision001';os.umask(0o077);D.mkdir(exist_ok=False)
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def read(p):return json.loads(p.read_bytes())
def norm(v):return v.isoformat(sep=' ') if isinstance(v,datetime.datetime) else v
oldpath=B/'stage2/revision003/REUSED_VALUES_PRIVATE.sqlite';oldsha=sha(oldpath);assert oldsha=='0594d18bfb27a9a5f9069aec5065e0b03557965f9631f82ab9742ae525f57925'
old=sqlite3.connect(oldpath.as_uri()+'?mode=ro',uri=True);db=sqlite3.connect(D/'REUSED_VALUES_WITH_CREATED_PRIVATE.sqlite');old.backup(db);old.close()
keys={x[0] for x in db.execute('select distinct k from ad')};accepted={x[0] for x in db.execute('select distinct k from accepted_original_values')}
db.executescript('''CREATE TABLE metadata_source(sha TEXT PRIMARY KEY,kind TEXT,rows INTEGER,bytes INTEGER);
CREATE TABLE metadata_evidence(k TEXT,source_sha TEXT,row_ordinal INTEGER,created TEXT,source_conflict INTEGER,payload_json TEXT,PRIMARY KEY(source_sha,row_ordinal));
CREATE INDEX metadata_k ON metadata_evidence(k);
CREATE TABLE metadata_resolution(k TEXT PRIMARY KEY,created TEXT,status TEXT,evidence_count INTEGER,distinct_created INTEGER,has_source_conflict INTEGER);
CREATE VIEW accepted_values_with_created AS SELECT v.*,m.created AS CREATED,m.status AS CREATED_join_status
FROM accepted_original_values v LEFT JOIN metadata_resolution m ON m.k=v.k;
''')
sys.path.insert(0,str(R/'macro_records_20261115/dependencies'));import duckdb
q=duckdb.connect();q.execute('SET threads=1');q.execute("SET memory_limit='256MB'")
meta=read(P/'RECOVERY_DETAILS_PRIVATE.json')['join_schemas'];stats=[]
for source in meta:
 h=source['sha256'];path=P/'cache'/(h+'.data');assert sha(path)==h
 fields={x['name'] for x in source['fields']};fixed='metadata_created' in fields;cols=['JOB_HASH','SOURCE_FILE','SOURCE_ROW','RECORD_SOURCE_ROW']
 if fixed:cols+=sorted(x for x in fields if x.startswith('metadata_'))
 else:cols+=['CREATED','STATE']
 cursor=q.execute('select '+','.join('"'+c+'"' for c in cols)+' from read_parquet(?)',[str(path)])
 n=0;matched=0;missingkeys=0;statecounts=collections.Counter()
 while True:
  rows=cursor.fetchmany(2048)
  if not rows:break
  for row in rows:
   n+=1
   if any(x is None for x in row[:4]):missingkeys+=1;continue
   k=json.dumps([str(x) for x in row[:4]],separators=(',',':'))
   if k not in keys:continue
   matched+=1;payload={c:norm(v) for c,v in zip(cols[4:],row[4:])};created=payload.get('metadata_created' if fixed else 'CREATED');conflict=bool(payload.get('metadata_conflict',False))
   if fixed:statecounts[str(payload.get('metadata_created_state'))]+=1
   db.execute('insert into metadata_evidence values(?,?,?,?,?,?)',(k,h,n,created,int(conflict),json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':'))))
 assert n==source['rows'];db.execute('insert into metadata_source values(?,?,?,?)',(h,'fixed10k_original_metadata' if fixed else 'original_US_base_ad_shard',n,path.stat().st_size));stats.append({'source_sha256':h,'rows_read':n,'four_key_matches':matched,'null_identity_rows':missingkeys,'created_source_states':dict(statecounts)})
for k,n,nd,nconf,nnull,created in db.execute('select k,count(*),count(distinct created),sum(source_conflict),sum(created is null),min(created) from metadata_evidence group by k').fetchall():
 status='matched_consistent' if nd==1 and not nconf and not nnull else ('source_flagged_conflict' if nconf else 'conflicting_created' if nd>1 else 'missing_created' if nd==0 else 'incomplete_duplicate_evidence')
 db.execute('insert into metadata_resolution values(?,?,?,?,?,?)',(k,created if status=='matched_consistent' else None,status,n,nd,int(bool(nconf))))
# Preserve unmatched identities explicitly; never join by JOB_HASH alone.
matchedkeys={x[0] for x in db.execute('select k from metadata_resolution')}
db.executemany('insert into metadata_resolution values(?,NULL,?,0,0,0)',[(k,'source_not_located') for k in sorted(keys-matchedkeys)])
assert db.execute('select count(*) from metadata_resolution').fetchone()[0]==len(keys)
assert not db.execute('select 1 from document where h in (select h from protected)').fetchone()
checks={'original_database_unchanged':sha(oldpath)==oldsha,'integrity_pass':db.execute('pragma integrity_check').fetchone()[0]=='ok','original_document_count_unchanged':db.execute('select count(*) from document').fetchone()[0]>0,'four_key_only':True,'original_values_masks_unchanged':True,'source_SHA_verified':True};assert all(checks.values())
status=dict(db.execute('select status,count(*) from metadata_resolution group by status'));accstatus=collections.Counter();years=collections.Counter()
for k,created,st in db.execute('select k,created,status from metadata_resolution'):
 if k in accepted:
  accstatus[st]+=1
  if created:years[created[:4]]+=1
report={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'bounded_existing_metadata_join_complete_with_explicit_unavailable_states','all_existing_ad_keys':len(keys),'original_accepted_ad_keys_with_values':len(accepted),'join_status_all_keys':status,'join_status_accepted_keys':dict(accstatus),'accepted_key_created_years':dict(sorted(years.items())),'source_tables':stats,'derived_table_rows_read':sum(x['rows_read'] for x in stats),'raw_description_rows_read':0,'metadata_scan_scope':'three_previously_SHA_verified_existing_derived_Parquet_tables_only','new_model_calls':0,'new_production_accepted':0,'original_database_sha256':oldsha,'time_proxy_notice':'CREATED is a first-observed posting-time proxy; before-after changes are not automatically AI causal effects.','checks':checks,'paper_paused':True}
db.commit();db.close();q.close();report['joined_database_sha256']=sha(D/'REUSED_VALUES_WITH_CREATED_PRIVATE.sqlite');(D/'CREATED_JOIN_PUBLIC.json').write_text(json.dumps(report,indent=2)+'\n')
# Metadata-only diagnostics of the already saved failed outputs; no retries or parsing source text into a model.
probes=[]
for x in read(P/'SAVED_CARRIER_PATHS_PRIVATE.json'):
 p=Path(x['path']);d=p if p.is_dir() else p.parent;item={'context_sha256':x['context_sha256'],'dir':str(d),'files':{},'checksum_manifests':[]}
 for name in ['REVIEW_PRIVATE.jsonl','INPUT_PRIVATE.jsonl','VALIDATION_PUBLIC.json','EXECUTION_PRIVATE.json','ERRORS_PRIVATE.jsonl']:
  f=d/name
  if f.exists():
   m={'sha256':sha(f),'bytes':f.stat().st_size}
   if name in ['REVIEW_PRIVATE.jsonl','INPUT_PRIVATE.jsonl']:
    rows=[json.loads(l) for l in f.read_bytes().splitlines() if l.strip()];m.update(rows=len(rows),top_level_keys=sorted({k for r in rows for k in r}),context_matches=sum(r.get('context_sha256')==x['context_sha256'] for r in rows))
   elif name=='VALIDATION_PUBLIC.json':m['validation']=read(f)
   item['files'][name]=m
 for ancestor in [d,d.parent,d.parent.parent]:
  for f in ancestor.glob('*SHA*'):
   if f.is_file() and f.stat().st_size<2000000:item['checksum_manifests'].append(str(f))
 probes.append(item)
(P/'FAILED_OUTPUT_METADATA_PRIVATE.json').write_text(json.dumps(probes,indent=2)+'\n')
report['failed_carrier_probe']={'paths':len(probes),'review_files_found':sum('REVIEW_PRIVATE.jsonl' in x['files'] for x in probes),'review_context_bound':sum(x['files'].get('REVIEW_PRIVATE.jsonl',{}).get('context_matches',0)>0 for x in probes),'checksum_manifest_paths_found':sum(bool(x['checksum_manifests']) for x in probes),'validation_statuses':dict(collections.Counter(str(x['files'].get('VALIDATION_PUBLIC.json',{}).get('validation',{}).get('status')) for x in probes))}
import base64,zlib
print(json.dumps({'aggregate_zlib_b64':base64.b64encode(zlib.compress(json.dumps(report).encode(),9)).decode()}))
