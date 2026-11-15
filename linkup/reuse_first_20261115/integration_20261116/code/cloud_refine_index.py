"""Additive revision of this run's index: resolve missing sidecars and keep transport uncertainty distinct."""
import base64,collections,datetime,hashlib,json,os,re,sqlite3,sys,urllib.parse,zlib
from pathlib import Path
R=Path.home()/'migration';I=R/'integration_20261116/run001';O=I/'revision002'
sys.path.insert(0,str(R/'code'));from workflow import call
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(p.read_bytes())
def blocked(p):return 'batch035' in p.lower() or '01a17beb-973b-74e2-adbb-20f8d004b1fc' in p.lower()
def main():
 os.umask(0o077);O.mkdir(exist_ok=False)
 report=read(I/'INTEGRATION_PUBLIC.json');oldsha=sha(I/'STATUS_INDEX_PRIVATE.sqlite');assert oldsha==report['database_sha256']
 src=sqlite3.connect((I/'STATUS_INDEX_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True)
 db=sqlite3.connect(O/'STATUS_INDEX_PRIVATE.sqlite');src.backup(db);src.close()
 ids={r['task']:r for r in read(R/'AZURE_RESEARCH_IDENTITIES_PRIVATE.json')['rows']}
 bulk=read(R/'opencode_kimi_20261115/run01/bulk_1309_20261115/CANDIDATE_STATE_PRIVATE.json')
 # A handled request may have only a transport error, not a saved model result.
 changed=0
 for task,v in bulk['handled'].items():
  h=ids[task]['context_sha256']
  if db.execute('SELECT 1 FROM blocked WHERE h=?',(h,)).fetchone():continue
  if task not in bulk['engineering_candidates'] and v['status']!='frozen_validation_failed_preserve_output':
   changed+=db.execute("UPDATE event SET state='not_reconciled',detail=? WHERE h=? AND asset='Azure_parent' AND state='saved_unverified'",('transport_or_identity_exception_preserved_not_proof_of_saved_model_output:'+v['status'],h)).rowcount
 migration={}
 for cluster in ['kunshan','wuzhen','huazhong']:
  c=sqlite3.connect((R/cluster/'LEDGER_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True);c.execute('PRAGMA query_only=ON');migration[cluster]=c
 def lookup(d):
  matches=[]
  for cluster,c in migration.items():
   for path,root,rel,size,status,digest in c.execute('SELECT path,root,rel,size,status,sha FROM files WHERE sha=?',(d,)):
    if not blocked(path):matches.append(dict(cluster=cluster,path=path,root=root,rel=rel,size=size,status=status,sha256=digest))
  return matches
 recovered=[];unresolved=[]
 for gap in report['metadata_gaps']:
  if gap['kind']!='accepted_context_ledger_missing':unresolved.append(gap);continue
  c=read(I/'metadata_cache'/(gap['receipt_sha256']+'.metadata'));digest=c['outputs']['ad_level_reference_sha256'];matches=lookup(digest);verified=[m for m in matches if m['status']=='verified']
  if not verified:
   unresolved.append({**gap,'alternative_ad_reference_sha256':digest,'alternative_inventory_status_counts':dict(collections.Counter(m['status'] for m in matches))});continue
  m=verified[0];assert m['size']<32*1024*1024
  cfg=read(R/'private'/(m['cluster']+'.json'));url=cfg['container_sas'].split('?',1)[0]+'/'+urllib.parse.quote(cfg['snapshot']+'/'+Path(m['root']).name+'/'+m['rel'],safe='/')
  with call(url,'https://storage.azure.com/',headers={'x-ms-version':'2023-11-03'}) as r:b=r.read(m['size']+1)
  assert len(b)==m['size'] and hashlib.sha256(b).hexdigest()==digest
  p=O/(digest+'.metadata');p.write_bytes(b);seen={}
  for line in b.splitlines():
   if not line.strip():continue
   row=json.loads(line);h=row['context_sha256']
   assert db.execute("SELECT 1 FROM event WHERE h=? AND asset='Pro' AND state='accepted'",(h,)).fetchone()
   if db.execute('SELECT 1 FROM blocked WHERE h=?',(h,)).fetchone():continue
   dims={'document_status':row['document_status'],'technology_inventory_status':row['technology_inventory_status']}
   for f in ['experience_outcomes','entry_outcomes','responsibility_outcomes']:dims.update({f+'.'+k:v for k,v in row[f].items()})
   if h in seen:assert seen[h]==dims,'same_context_conflicting_original_statuses';continue
   seen[h]=dims
   for f,s in dims.items():db.execute('INSERT INTO field VALUES(?,?,?,?,?,?)',(h,'',f,s,'Pro',digest))
  assert len(seen)==c['counts']['accepted_contexts']
  db.execute('INSERT INTO provenance VALUES(?,?)',(digest,json.dumps(m)));recovered.append({'receipt_sha256':gap['receipt_sha256'],'ad_reference_sha256':digest,'contexts':len(seen)})
 report['context_state_partition']=dict(db.execute('SELECT state,count(*) FROM final_status GROUP BY state'))
 report['context_states_by_asset_not_additive']={}
 for a,s,n in db.execute('SELECT asset,state,count(DISTINCT h) FROM event GROUP BY asset,state'):report['context_states_by_asset_not_additive'].setdefault(a,{})[s]=n
 report['field_status_counts']={}
 for a,f,s,n in db.execute('SELECT asset,family,status,count(*) FROM field GROUP BY asset,family,status'):report['field_status_counts'].setdefault(a,{}).setdefault(f,{})[s]=n
 report['reviewed_unknown_or_partial_contexts_overlapping_states']=db.execute("SELECT count(DISTINCT h) FROM field WHERE status IN ('unknown','unknown_or_conflict','unresolved','reviewed_partial','partial')").fetchone()[0]
 report['metadata_gaps']=unresolved;report['alternate_ad_reference_projections']=recovered
 report['transport_or_identity_events_reclassified_not_saved_output']=changed
 report['revision']=2;report['previous_index_sha256_preserved']=oldsha
 report['revision_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
 # Candidate claims are disabled. Export actual pending identities privately, not as API inputs.
 q=O/'PENDING_METADATA_ONLY_PRIVATE.jsonl'
 with q.open('x') as f:
  for h,s in db.execute("SELECT h,state FROM final_status WHERE state IN ('not_reconciled','unprocessed_asof_checkpoint') ORDER BY h"):
   f.write(json.dumps({'context_sha256':h,'state':s,'inference_admitted':False})+'\n')
 db.commit();db.close();assert sha(I/'STATUS_INDEX_PRIVATE.sqlite')==oldsha
 report['database_sha256']=sha(O/'STATUS_INDEX_PRIVATE.sqlite');report['pending_metadata_sha256']=sha(q)
 (O/'INTEGRATION_PUBLIC.json').write_text(json.dumps(report,indent=2)+'\n')
 compact={k:report[k] for k in ['status','revision','known_union_unique_contexts','unique_canonical_ad_keys','distinct_ad_context_bindings','canonical_keys_with_multiple_body_versions_preserved','context_state_partition','context_states_by_asset_not_additive','reviewed_unknown_or_partial_contexts_overlapping_states','transport_or_identity_events_reclassified_not_saved_output','alternate_ad_reference_projections','metadata_gaps','database_sha256','known_protected_contexts','exact_reuse_binding_rows_imported','new_model_calls','new_production_accepted']}
 compact['report_sha256']=sha(O/'INTEGRATION_PUBLIC.json')
 print(json.dumps({'aggregate_zlib_b64':base64.b64encode(zlib.compress(json.dumps(compact).encode(),9)).decode()}))
if __name__=='__main__':
 try:main()
 except Exception as e:
  import traceback
  (I/'REFINE_FAILURE_PRIVATE.txt').write_text(traceback.format_exc());print(json.dumps({'status':'refine_failed_preserved','exception_type':type(e).__name__}));raise SystemExit(2)
