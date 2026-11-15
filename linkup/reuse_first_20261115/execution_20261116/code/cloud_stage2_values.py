"""Attach original values/evidence to the immutable status index; no model calls or source-ad reads."""
import json,hashlib,os,sqlite3,time,datetime,collections,fcntl,sys
from pathlib import Path
R=Path.home()/'migration';B=R/'integration_20261116/run001';I=B/'revision003';O=R/'execution_20261116/run001/stage2';os.umask(0o077);O.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def rows(p):
 with p.open('rb') as f:
  for n,b in enumerate(f,1):
   if b.strip():yield n,json.loads(b)
def canonical(k):
 if isinstance(k,dict):k=[k[x] for x in ['JOB_HASH','SOURCE_FILE','SOURCE_ROW','RECORD_SOURCE_ROW']]
 assert len(k)==4
 return json.dumps([str(v) for v in k],separators=(',',':'))
def main():
 lock=(O/'STAGE2.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);dest=O/'REUSED_VALUES_PRIVATE.sqlite';assert not dest.exists(),'previous_output_preserved'
 t0=time.monotonic();original=I/'STATUS_INDEX_PRIVATE.sqlite';original_sha=sha(original);assert original_sha=='0344e94b9f2b75af74652a2f517c4e5c535d8090e1db62eec84b55afced1523a'
 old=sqlite3.connect(original.as_uri()+'?mode=ro',uri=True);blocked={x[0] for x in old.execute('select h from blocked')};states=dict(old.execute('select h,state from final_status'))
 db=sqlite3.connect(dest);db.executescript('''PRAGMA journal_mode=DELETE; PRAGMA synchronous=FULL;
 CREATE TABLE ad(k TEXT,h TEXT,source TEXT,PRIMARY KEY(k,h,source));
 CREATE TABLE field_mask(h TEXT,k TEXT,family TEXT,status TEXT,asset TEXT,source TEXT,PRIMARY KEY(h,k,family,asset,source));
 CREATE TABLE document(d TEXT PRIMARY KEY,h TEXT,k TEXT,asset TEXT,source_sha TEXT,source_ordinal INTEGER,original_accepted INTEGER,document_json TEXT);
 CREATE TABLE field_value(d TEXT,family TEXT,status TEXT,value_json TEXT,PRIMARY KEY(d,family));
 CREATE TABLE source(sha TEXT PRIMARY KEY,path TEXT,bytes INTEGER);
 CREATE TABLE issue(kind TEXT,h TEXT,source TEXT,detail TEXT);
 CREATE TABLE protected(h TEXT PRIMARY KEY);
 ''')
 db.executemany('INSERT INTO ad VALUES(?,?,?)',old.execute('select k,h,source from ad'));db.executemany('INSERT INTO field_mask VALUES(?,?,?,?,?,?)',old.execute('select h,k,family,status,asset,source from field'));db.executemany('INSERT INTO protected VALUES(?)',[(h,) for h in blocked]);sources={};counts=collections.Counter();value_counts=collections.Counter();skipped=collections.Counter();shapes={}
 def verify(p,d):
  if d in sources:return
  assert p.is_file() and sha(p)==d,'source_sha_mismatch';sources[d]=p;db.execute('INSERT INTO source VALUES(?,?,?)',(d,str(p),p.stat().st_size))
 def add(row,asset,src,n,k='',accepted=False,fixed=False):
  h=row.get('normalized_context_sha256') or row.get('context_sha256');assert h in states,'context_not_in_original_index'
  if h in blocked:skipped['protected_rows']+=1;return
  if accepted:assert states[h]=='accepted_original_scope','acceptance_scope_conflict'
  raw=json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'));d=hashlib.sha256((asset+'\0'+src+'\0'+str(n)+'\0'+raw).encode()).hexdigest()
  db.execute('INSERT INTO document VALUES(?,?,?,?,?,?,?,?)',(d,h,k,asset,src,n,int(accepted),raw));counts[asset]+=1
  if fixed:vals={row['field_family']:(row['status'],row['structured_value'])}
  else:
   vals={'document_status':(row.get('document_status','unknown'),row.get('document_status')),'technology':(row.get('technology_inventory_status','unknown'),{'inventory_status':row.get('technology_inventory_status'),'items':row.get('technology_items',[])})}
   for fam,it in [('experience','experience_clauses'),('entry','entry_items'),('responsibility','responsibility_items')]:
    vals[fam]=('original_outcome_mask',{'outcomes':row.get(fam+'_outcomes'), 'items':row.get(it,[])})
   vals['qualification_alternatives']=('original_document_scope',row.get('qualification_alternatives',[]));vals['evidence_resolution']=('original_document_scope',row.get('evidence_resolution',[]));vals['unresolved_notes']=('retained_unknowns',row.get('unresolved_notes',[]))
  for fam,(st,v) in vals.items():db.execute('INSERT INTO field_value VALUES(?,?,?,?)',(d,fam,st,json.dumps(v,ensure_ascii=False,separators=(',',':'))));value_counts[asset]+=1
 fixed='794d76b2a6e913d7d08adab7e99bc96a3f57f8553c73518ae27b966a8fad86fb';p=B/'metadata_cache'/(fixed+'.metadata');verify(p,fixed)
 for n,row in rows(p):add(row,'fixed10k',fixed,n,canonical(row['canonical_key']),row['status'] in ['known','not_applicable','unknown_or_conflict','partial'],True)
 for asset in ['Pro','Pro_merged']:
  for (digest,) in old.execute('select distinct source from field where asset=?',(asset,)):
   p=B/'metadata_cache'/(digest+'.metadata')
   if not p.exists():p=I/'packet_metadata'/(digest+'.metadata')
   verify(p,digest)
   for n,row in rows(p):add(row,asset,digest,n,accepted=True)
 # Store existing Kimi output objects separately; an engineering pass never promotes them.
 statepath=R/'opencode_kimi_20261115/run01/bulk_1309_20261115/CANDIDATE_STATE_PRIVATE.json';state_sha=sha(statepath);state=json.loads(statepath.read_bytes())
 for task,x in state['engineering_candidates'].items():
  h=x['context_sha256']
  if h in blocked:skipped['protected_candidate']+=1;continue
  p=Path(x['path']);p=p if p.is_absolute() else R/p
  if not p.is_file():db.execute('INSERT INTO issue VALUES(?,?,?,?)',('saved_output_path_missing',h,state_sha,''));continue
  try:
   verify(p,x['validated_sha256']);seen=False
   for n,row in rows(p):
    if row.get('context_sha256')==h:add(row,'Kimi_saved_unverified',x['validated_sha256'],n,accepted=False);seen=True
   assert seen,'candidate_context_not_found'
  except Exception as e:db.execute('INSERT INTO issue VALUES(?,?,?,?)',('saved_output_read_failed',h,state_sha,type(e).__name__))
 # Additional saved and status-only contexts remain queued for reconciliation, never assumed unread.
 got={h for (h,) in db.execute('select distinct h from document')}
 for h,state in states.items():
  if state=='quarantined':continue
  if h not in got:db.execute('INSERT INTO issue VALUES(?,?,?,?)',('no_value_carrier_attached_yet',h,original_sha,state))
 db.executescript('''CREATE INDEX doc_h ON document(h);CREATE INDEX ad_h ON ad(h);CREATE INDEX mask_h ON field_mask(h);
 CREATE VIEW accepted_original_values AS SELECT a.k,a.h,d.d,d.asset,d.source_sha,d.source_ordinal,v.family,v.status,v.value_json
 FROM (SELECT DISTINCT k,h FROM ad) a JOIN document d ON d.h=a.h AND (d.k='' OR d.k=a.k) JOIN field_value v ON v.d=d.d
 WHERE d.original_accepted=1 AND NOT EXISTS(SELECT 1 FROM protected b WHERE b.h=a.h);
 CREATE VIEW unverified_documents AS SELECT d,h,asset,source_sha,source_ordinal FROM document WHERE original_accepted=0;
 ''')
 checks={'original_index_unchanged':sha(original)==original_sha,'candidate_ledger_unchanged':sha(statepath)==state_sha,'all_copied_source_sha_unchanged':all(sha(p)==d for d,p in sources.items()),'protected_payloads_absent':db.execute('select count(*) from document where h in (select h from protected)').fetchone()[0]==0,'integrity':db.execute('pragma integrity_check').fetchone()[0]=='ok'};assert all(checks.values())
 accepted_contexts=db.execute('select count(distinct h) from document where original_accepted=1').fetchone()[0]
 report={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'original_values_attached_partial_saved_output_reconciliation','original_index_sha256':original_sha,'copied_documents_by_asset':dict(counts),'field_value_rows_by_asset':dict(value_counts),'accepted_original_scope_contexts_with_values':accepted_contexts,'unverified_contexts_with_values':db.execute('select count(distinct h) from document where original_accepted=0').fetchone()[0],'protected_rows_skipped':dict(skipped),'issues':dict(db.execute('select kind,count(*) from issue group by kind')),'accepted_ad_keys_with_values':db.execute('select count(distinct k) from accepted_original_values').fetchone()[0],'original_source_files_sha_verified':len(sources),'source_bytes_reused_not_new_network_reads':sum(p.stat().st_size for p in sources.values()),'checks':checks,'elapsed_seconds':time.monotonic()-t0,'new_model_calls':0,'new_production_accepted':0,'source_advertisement_files_read':0,'full_regression_panel_complete':False,'values_preserve_original_masks_not_all_fields_known':True,'original_ledger_mutations':0,'CREATED_join_not_yet_materialized':True}
 db.commit();db.close();old.close();report['database_sha256']=sha(dest);(O/'VALUES_ATTACHMENT_PUBLIC.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':
 try:main()
 except Exception as e:
  import traceback
  (O/'FAILURE_PRIVATE.txt').write_text(traceback.format_exc());print(json.dumps({'status':'stage2_failed_preserved','exception_type':type(e).__name__}));raise SystemExit(2)
