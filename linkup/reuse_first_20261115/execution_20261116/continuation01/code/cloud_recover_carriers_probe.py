"""Recover exactly pinned accepted carriers and inspect only bounded join schemas."""
import collections,concurrent.futures,datetime,hashlib,importlib.util,json,os,sqlite3,sys,urllib.parse
from pathlib import Path
R=Path.home()/'migration';B=R/'execution_20261116/run001';O=B/'continuation01';P=O/'carrier_recovery';P.mkdir(exist_ok=False);(P/'cache').mkdir();os.umask(0o077)
read=lambda p:json.loads(p.read_bytes())
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
loc=read(O/'RESUME_LOCATORS_PRIVATE.json');needed={'733875307de475a296e3da4531ad64ba99351f5e2dff109b757ad80b80b34adb'}
for x in loc['missing_accepted_packets']:
    for k in ['packet_sha256','review_sha256','validated_sha256']:
        d=x['packet'].get(k)
        if isinstance(d,str):needed.add(d)
for x in loc['selected_Pro_shard_catalog']:needed.add(x['ad_sha256_from_original_receipt'])
found={};configs={}
for cluster in ['kunshan','wuzhen','huazhong']:
    c=sqlite3.connect((R/cluster/'LEDGER_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True)
    for path,root,rel,size,status,d in c.execute('select path,root,rel,size,status,sha from files where sha in ('+','.join('?' for _ in needed)+')',list(needed)):
        if status=='verified' and 'batch035' not in path.lower():found.setdefault(d,dict(cluster=cluster,path=path,root=root,rel=rel,size=size,sha256=d))
    c.close();configs[cluster]=read(R/'private'/(cluster+'.json'))
assert sum(x['size'] for x in found.values())<64*1024*1024
sys.path.insert(0,str(R/'code'));from workflow import call
def fetch(d):
    m=found[d];cfg=configs[m['cluster']];u=cfg['container_sas'].split('?',1)[0]+'/'+urllib.parse.quote(cfg['snapshot']+'/'+Path(m['root']).name+'/'+m['rel'],safe='/')
    with call(u,'https://storage.azure.com/',headers={'x-ms-version':'2023-11-03'}) as r:data=r.read(m['size']+1)
    assert len(data)==m['size'] and hashlib.sha256(data).hexdigest()==d;(P/'cache'/(d+'.data')).write_bytes(data)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(fetch,found))
frozen=R/'code/validate_reviews.py';assert sha(frozen)=='f7737143004374f9391a16ad2d1bab2fa47950c589232510045d1eee93bc2c20'
sp=importlib.util.spec_from_file_location('frozen_carrier_recovery',frozen);v=importlib.util.module_from_spec(sp);sp.loader.exec_module(v);outcomes=[]
for i,x in enumerate(loc['missing_accepted_packets']):
    y=x['packet'];s=P/f'packet{i:02d}';s.mkdir();info={'ordinal':i,'input_located':y['packet_sha256'] in found,'review_located':y['review_sha256'] in found,'expected_validated_sha256':y['validated_sha256']}
    if info['input_located'] and info['review_located']:
        sys.argv=['validate_reviews.py','--packet',str(P/'cache'/(y['packet_sha256']+'.data')),'--reviews',str(P/'cache'/(y['review_sha256']+'.data')),'--schema',str(R/'astra/extraction/FORMAL800_REVIEW_SCHEMA.json'),'--expected-records',str(y['expected_records']),'--private-validated',str(s/'VALIDATED_PRIVATE.jsonl'),'--private-errors',str(s/'ERRORS_PRIVATE.jsonl'),'--public-receipt',str(s/'RECEIPT_PUBLIC.json')]
        try:v.main()
        except SystemExit:pass
        rr=read(s/'RECEIPT_PUBLIC.json');info.update(validation_status=rr['status'],reconstructed_sha256=sha(s/'VALIDATED_PRIVATE.jsonl'),rows=rr['counts']['validated_records']);info['matches_original_accepted_SHA']=info['reconstructed_sha256']==y['validated_sha256']
    outcomes.append(info)
savedprobe=[]
for x in loc['missing_saved_cases']:
    e=x['exception'];p=Path(e['path']) if e.get('path') else None
    if p:savedprobe.append({'context_sha256':x['context_sha256'],'path':str(p),'exists':p.exists(),'is_directory':p.is_dir(),'files':[{'name':f.name,'bytes':f.stat().st_size} for f in (p.iterdir() if p.is_dir() else p.parent.iterdir()) if f.is_file()] if p.exists() else []})
(P/'SAVED_CARRIER_PATHS_PRIVATE.json').write_text(json.dumps(savedprobe,indent=2)+'\n')
sys.path.insert(0,str(R/'macro_records_20261115/dependencies'));import duckdb
sql=duckdb.connect();sql.execute('SET threads=1');sql.execute("SET memory_limit='256MB'");schemas=[]
for d in ['733875307de475a296e3da4531ad64ba99351f5e2dff109b757ad80b80b34adb']+[x['ad_sha256_from_original_receipt'] for x in loc['selected_Pro_shard_catalog']]:
    if d in found:
        cols=sql.execute('describe select * from read_parquet(?)',[str(P/'cache'/(d+'.data'))]).fetchall();schemas.append({'sha256':d,'fields':[{'name':x[0],'type':x[1]} for x in cols],'rows':sql.execute('select count(*) from read_parquet(?)',[str(P/'cache'/(d+'.data'))]).fetchone()[0]})
details={'accepted_packet_recovery':outcomes,'join_schemas':schemas,'verified_sources':found};(P/'RECOVERY_DETAILS_PRIVATE.json').write_text(json.dumps(details,indent=2)+'\n')
report={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'verified_files':len(found),'verified_bytes':sum(x['size'] for x in found.values()),'missing_accepted_packet_reconstruction':outcomes,'saved_failed_paths_found':sum(x['exists'] for x in savedprobe),'saved_path_file_names':sorted({f['name'] for x in savedprobe for f in x['files']}),'join_schemas':schemas,'new_model_calls':0,'original_result_mutations':0}
(P/'CARRIER_RECOVERY_PROBE_PUBLIC.json').write_text(json.dumps(report,indent=2)+'\n')
import base64,zlib
e=base64.b64encode(zlib.compress(json.dumps(report).encode(),9)).decode();assert len(e)<3800;print(json.dumps({'aggregate_zlib_b64':e}))
