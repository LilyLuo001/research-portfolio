"""Recover only status projections from original accepted packet artifacts when aggregate sidecars are absent."""
import base64,collections,concurrent.futures,datetime,hashlib,json,os,sqlite3,sys,urllib.parse,zlib
from pathlib import Path
R=Path.home()/'migration';B=R/'integration_20261116/run001';I=B/'revision002';O=B/'revision003'
sys.path.insert(0,str(R/'code'));from workflow import call
def read(p):return json.loads(p.read_bytes())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def blocked(s):return 'batch035' in s.lower() or '01a17beb-973b-74e2-adbb-20f8d004b1fc' in s.lower()
def main():
 os.umask(0o077);O.mkdir(exist_ok=False);(O/'packet_metadata').mkdir()
 report=read(I/'INTEGRATION_PUBLIC.json');previous=sha(I/'STATUS_INDEX_PRIVATE.sqlite');assert previous==report['database_sha256']
 db=sqlite3.connect(O/'STATUS_INDEX_PRIVATE.sqlite');src=sqlite3.connect((I/'STATUS_INDEX_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True);src.backup(db);src.close()
 jobs={};groups={}
 for gap in report['metadata_gaps']:
  if gap['kind']!='accepted_context_ledger_missing':continue
  c=read(B/'metadata_cache'/(gap['receipt_sha256']+'.metadata'));groups[gap['receipt_sha256']]=(c,gap)
  for item in c['packets']:
   if item['status']=='accepted':jobs[item['validated_sha256']]={'receipt':gap['receipt_sha256'],'packet':item}
 found={};configs={}
 for cluster in ['kunshan','wuzhen','huazhong']:
  c=sqlite3.connect((R/cluster/'LEDGER_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True);c.execute('PRAGMA query_only=ON')
  for path,root,rel,size,status,d in c.execute('SELECT path,root,rel,size,status,sha FROM files WHERE sha IN ('+','.join('?' for _ in jobs)+')',list(jobs)):
   if status=='verified' and not blocked(path):found.setdefault(d,dict(cluster=cluster,path=path,root=root,rel=rel,size=size,status=status,sha256=d))
  c.close();configs[cluster]=read(R/'private'/(cluster+'.json'))
 def fetch(item):
  d,m=item;c=configs[m['cluster']];assert m['size']<2*1024*1024
  url=c['container_sas'].split('?',1)[0]+'/'+urllib.parse.quote(c['snapshot']+'/'+Path(m['root']).name+'/'+m['rel'],safe='/')
  try:
   with call(url,'https://storage.azure.com/',headers={'x-ms-version':'2023-11-03'}) as r:b=r.read(m['size']+1)
   assert len(b)==m['size'] and hashlib.sha256(b).hexdigest()==d
   p=O/'packet_metadata'/(d+'.metadata');p.write_bytes(b);return d,p,None
  except Exception as e:return d,None,type(e).__name__
 seen=collections.defaultdict(set);download_errors=[];verified=0;bytes_read=0
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  for digest,p,error in pool.map(fetch,found.items()):
   if error:download_errors.append({'source_sha256':digest,'error_type':error});continue
   job=jobs[digest];accepted_rows=[json.loads(l) for l in p.read_bytes().splitlines() if l.strip()]
   assert len(accepted_rows)==job['packet']['validated_records']==job['packet']['expected_records']
   for row in accepted_rows:
    h=row['context_sha256'];assert h not in seen[job['receipt']]
    assert db.execute("SELECT 1 FROM event WHERE h=? AND asset='Pro' AND state='accepted' AND source=?",(h,job['receipt'])).fetchone()
    assert not db.execute('SELECT 1 FROM blocked WHERE h=?',(h,)).fetchone()
    dims={'document_status':row['document_status'],'technology_inventory_status':row['technology_inventory_status']}
    for f in ['experience_outcomes','entry_outcomes','responsibility_outcomes']:dims.update({f+'.'+k:v for k,v in row[f].items()})
    for f,s in dims.items():db.execute('INSERT INTO field VALUES(?,?,?,?,?,?)',(h,'',f,s,'Pro',digest))
    seen[job['receipt']].add(h)
   db.execute('INSERT INTO provenance VALUES(?,?)',(digest,json.dumps(found[digest])));verified+=1;bytes_read+=p.stat().st_size
 outcomes=[];remaining=[]
 for receipt,(c,gap) in groups.items():
  expected=c['counts']['accepted_contexts'];n=len(seen[receipt]);assert n<=expected
  outcome={'receipt_sha256':receipt,'expected_contexts':expected,'status_contexts_recovered_from_original_accepted_packets':n,'complete':n==expected};outcomes.append(outcome)
  if n<expected:remaining.append({**gap,'status_contexts_still_unprojected':expected-n})
 report['metadata_gaps']=remaining;report['packet_status_recovery']=outcomes;report['packet_recovery_download_errors']=download_errors
 report['accepted_Pro_status_contexts_projected_after_recovery']=report['accepted_Pro_contexts_in_projected_ledgers']+sum(len(x) for x in seen.values())
 report['packet_artifacts_verified']=verified;report['packet_artifact_bytes_read']=bytes_read
 report['field_status_counts']={}
 for a,f,s,n in db.execute('SELECT asset,family,status,count(*) FROM field GROUP BY asset,family,status'):report['field_status_counts'].setdefault(a,{}).setdefault(f,{})[s]=n
 report['reviewed_unknown_or_partial_contexts_overlapping_states']=db.execute("SELECT count(DISTINCT h) FROM field WHERE status IN ('unknown','unknown_or_conflict','unresolved','reviewed_partial','partial')").fetchone()[0]
 assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
 db.commit();db.close();assert sha(I/'STATUS_INDEX_PRIVATE.sqlite')==previous
 report['revision']=3;report['previous_index_sha256_preserved']=previous;report['revision_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();report['database_sha256']=sha(O/'STATUS_INDEX_PRIVATE.sqlite')
 report['pending_metadata_sha256']=sha(I/'PENDING_METADATA_ONLY_PRIVATE.jsonl');report['pending_metadata_location']='revision002/PENDING_METADATA_ONLY_PRIVATE.jsonl'
 (O/'INTEGRATION_PUBLIC.json').write_text(json.dumps(report,indent=2)+'\n')
 compact={k:report[k] for k in ['revision','context_state_partition','packet_status_recovery','packet_artifacts_verified','packet_artifact_bytes_read','accepted_Pro_status_contexts_projected_after_recovery','reviewed_unknown_or_partial_contexts_overlapping_states','database_sha256','metadata_gaps']}
 compact['report_sha256']=sha(O/'INTEGRATION_PUBLIC.json')
 print(json.dumps({'aggregate_zlib_b64':base64.b64encode(zlib.compress(json.dumps(compact).encode(),9)).decode()}))
if __name__=='__main__':
 try:main()
 except Exception as e:
  import traceback
  (B/'PACKET_RECOVERY_FAILURE_PRIVATE.txt').write_text(traceback.format_exc());print(json.dumps({'status':'packet_recovery_failed_preserved','exception_type':type(e).__name__}));raise SystemExit(2)
