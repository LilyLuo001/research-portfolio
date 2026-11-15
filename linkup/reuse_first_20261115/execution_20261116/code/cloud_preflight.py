import json,os,hashlib,sqlite3,datetime,collections,base64,zlib
from pathlib import Path
R=Path.home()/'migration';B=R/'integration_20261116/run001';I=B/'revision003';O=R/'execution_20261116/run001';os.umask(0o077);O.mkdir(parents=True,exist_ok=True)
def sh(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def rd(p):return json.loads(p.read_bytes())
def shape(o):
 if isinstance(o,dict):return {k:('dict:'+','.join(list(v)[:18]) if isinstance(v,dict) else 'list:'+str(len(v)) if isinstance(v,list) else type(v).__name__) for k,v in o.items()}
 return type(o).__name__
workers=[]
for p in Path('/proc').glob('[0-9]*/cmdline'):
 try:
  argv=p.read_bytes().split(b'\0')
  if int(p.parent.name)==os.getpid():continue
  for n in ['cloud_benchmark_worker.py','bulk_worker.py','qualification_worker.py']:
   if any(Path(v.decode(errors='ignore')).name==n for v in argv):workers.append({'pid':int(p.parent.name),'script':n})
 except (OSError,ValueError):pass
assert not workers,'known_model_worker_active'
assert sh(I/'STATUS_INDEX_PRIVATE.sqlite')=='0344e94b9f2b75af74652a2f517c4e5c535d8090e1db62eec84b55afced1523a'
c=sqlite3.connect((I/'STATUS_INDEX_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True)
report={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'known_running_workers':workers,'db_states':dict(c.execute('select state,count(*) from final_status group by state').fetchall()),'shapes':{},'candidate_metadata':{},'disk_free_bytes':__import__('shutil').disk_usage(R).free}
for label,d in [('fixed','794d76b2a6e913d7d08adab7e99bc96a3f57f8553c73518ae27b966a8fad86fb'),('relation','9ea1fcd0f61182d2d125b19d90af820f549e77351ff1064320613c311ae0d8a9')]:
 p=B/'metadata_cache'/(d+'.metadata');row=json.loads(p.open('rb').readline());report['shapes'][label]=shape(row)
for asset in ['Pro','Pro_merged']:
 x=c.execute('select source from field where asset=? limit 1',(asset,)).fetchone()
 if x:
  p=B/'metadata_cache'/(x[0]+'.metadata')
  if p.exists():report['shapes'][asset]=shape(json.loads(p.open('rb').readline()))
p=next(iter((I/'packet_metadata').glob('*.metadata')));report['shapes']['accepted_packet']=shape(json.loads(p.open('rb').readline()))
x=rd(R/'opencode_kimi_20261115/run01/bulk_1309_20261115/CANDIDATE_STATE_PRIVATE.json');report['shapes']['candidate_state_top']=shape(x)
for k in ['engineering_candidates','handled','exceptions']:
 if x.get(k):report['shapes']['candidate_'+k]=shape(next(iter(x[k].values())))
pre=rd(R/'full_scope_catalog_preflight_20261115/20261115T120402Z/CATALOG_LOCATORS_AND_MANIFEST_CANDIDATES_PRIVATE.json');items=[]
for cluster,v in pre['clusters'].items():items+=v['delivery_manifest_name_candidates']
uniq={x['sha256']:x for x in items};report['candidate_metadata']={'locations':len(items),'unique_contents':len(uniq),'bytes_unique':sum(x['size'] for x in uniq.values()),'largest_bytes':max(x['size'] for x in uniq.values()),'basenames':dict(collections.Counter(Path(x['rel']).name for x in items).most_common(25))}
# No raw payloads or IDs leave the VM. List scalar shape and counts only.
(O/'PREFLIGHT_PUBLIC.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'aggregate_zlib_b64':base64.b64encode(zlib.compress(json.dumps(report).encode())).decode()}))
