"""Attach existing failed outputs as unusable unverified evidence, never promote or retry."""
import collections,datetime,hashlib,json,os,sqlite3
from pathlib import Path
R=Path.home()/'migration';B=R/'execution_20261116/run001';C=B/'continuation01';P=C/'carrier_recovery';O=C/'joined_revision002';os.umask(0o077);O.mkdir(exist_ok=False)
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
orig=C/'joined_revision001/REUSED_VALUES_WITH_CREATED_PRIVATE.sqlite';oh=sha(orig);db=sqlite3.connect(O/'REUSED_VALUES_WITH_CREATED_PRIVATE.sqlite');old=sqlite3.connect(orig.as_uri()+'?mode=ro',uri=True);old.backup(db);old.close()
idxpath=R/'integration_20261116/run001/revision003/STATUS_INDEX_PRIVATE.sqlite';ih=sha(idxpath);idx=sqlite3.connect(idxpath.as_uri()+'?mode=ro',uri=True);states=dict(idx.execute('select h,state from final_status'))
bulk=R/'opencode_kimi_20261115/run01/bulk_1309_20261115/CANDIDATE_STATE_PRIVATE.json';bh=sha(bulk);ks=read(bulk)
db.executescript('''CREATE TABLE output_validation_provenance(d TEXT PRIMARY KEY,validation_status TEXT,validation_sha TEXT,input_sha TEXT,checksum_manifest_sha TEXT,commit_receipt_sha TEXT,retry_forbidden INTEGER);
CREATE TABLE do_not_reinfer_context(h TEXT PRIMARY KEY,reason TEXT,source_sha TEXT);
''')
ident={x['task']:x['context_sha256'] for x in read(R/'AZURE_RESEARCH_IDENTITIES_PRIVATE.json')['rows']}
for t,e in ks['exceptions'].items():
 if t in ident and e.get('retry_forbidden'):db.execute('insert or ignore into do_not_reinfer_context values(?,?,?)',(ident[t],e['status'],bh))
for h, in db.execute('select h from protected').fetchall():db.execute('insert or replace into do_not_reinfer_context values(?,?,?)',(h,'protected_quarantine',ih))
attached=0;pins={};filesverified=0
for x in read(P/'FAILED_OUTPUT_METADATA_PRIVATE.json'):
 h=x['context_sha256'];d=Path(x['dir']);assert states[h]=='saved_unverified' and not db.execute('select 1 from document where h=?',(h,)).fetchone();assert not db.execute('select 1 from protected where h=?',(h,)).fetchone()
 manifest=d.parent/'SHA256SUMS.json';commit=d.parent/'COMMITTED_PUBLIC.json';mp=read(manifest);cp=read(commit)
 assert cp['status']=='batch_committed_and_cloud_revalidated';assert sha(manifest)==cp['blob_receipts']['SHA256SUMS.json']['sha256']
 for name in ['REVIEW_PRIVATE.jsonl','INPUT_PRIVATE.jsonl','VALIDATION_PUBLIC.json','ERRORS_PRIVATE.jsonl','EXECUTION_PRIVATE.json']:
  f=d/name;hh=sha(f);assert mp[str(f.relative_to(d.parent))]==hh;pins[str(f)]=hh;filesverified+=1;db.execute('insert or ignore into source values(?,?,?)',(hh,str(f),f.stat().st_size))
 pins[str(manifest)]=sha(manifest);pins[str(commit)]=sha(commit)
 inp=[json.loads(l) for l in (d/'INPUT_PRIVATE.jsonl').read_bytes().splitlines() if l.strip()];rr=[json.loads(l) for l in (d/'REVIEW_PRIVATE.jsonl').read_bytes().splitlines() if l.strip()]
 assert len(inp)==len(rr)==1;row=rr[0];assert row['context_sha256']==h==inp[0]['context_sha256'];assert row['record_id']==inp[0]['record_id'];assert hashlib.sha256(inp[0]['full_document'].encode()).hexdigest()==h;assert read(d/'VALIDATION_PUBLIC.json')['status']=='fail';assert db.execute('select 1 from do_not_reinfer_context where h=?',(h,)).fetchone()
 payload=json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'));source=sha(d/'REVIEW_PRIVATE.jsonl');asset='Kimi_saved_failed_frozen_validation';did=hashlib.sha256((asset+'\0'+source+'\0'+'1'+'\0'+payload).encode()).hexdigest()
 db.execute('insert into document values(?,?,?,?,?,?,?,?)',(did,h,'',asset,source,1,0,payload));vals={'document_status':row.get('document_status'),'technology':{'inventory_status':row.get('technology_inventory_status'),'items':row.get('technology_items',[])},'experience':{'outcomes':row.get('experience_outcomes'),'items':row.get('experience_clauses',[])},'entry':{'outcomes':row.get('entry_outcomes'),'items':row.get('entry_items',[])},'responsibility':{'outcomes':row.get('responsibility_outcomes'),'items':row.get('responsibility_items',[])},'qualification_alternatives':row.get('qualification_alternatives',[]),'evidence_resolution':row.get('evidence_resolution',[]),'unresolved_notes':row.get('unresolved_notes',[])}
 for family,value in vals.items():db.execute('insert into field_value values(?,?,?,?)',(did,family,'failed_frozen_validation_not_usable',json.dumps(value,ensure_ascii=False)))
 db.execute('insert into output_validation_provenance values(?,?,?,?,?,?,?)',(did,'fail',sha(d/'VALIDATION_PUBLIC.json'),sha(d/'INPUT_PRIVATE.jsonl'),sha(manifest),sha(commit),1));db.execute('insert into issue values(?,?,?,?)',('attached_original_failed_validation',h,source,'retained_unusable;not_newly_accepted;retry_forbidden'));attached+=1
covered={x[0] for x in db.execute('select distinct h from document')};missing=collections.Counter(s for h,s in states.items() if h not in covered)
db.execute("delete from issue where kind='no_value_carrier_attached_yet' and h in (select h from document)")
# Verify all original semantic rows remain byte-for-byte equal in the SQLite copy.
db.execute('attach database ? as previous',(str(orig),))
checks={}
for table in ['ad','field_mask','protected','metadata_source','metadata_evidence','metadata_resolution']:
 assert db.execute(f'select count(*) from {table}').fetchone()==db.execute(f'select count(*) from previous.{table}').fetchone()
 assert not db.execute(f'select * from {table} except select * from previous.{table} limit 1').fetchone();checks[table+'_unchanged']=True
for table in ['document','field_value','source']:
 assert not db.execute(f'select * from previous.{table} except select * from {table} limit 1').fetchone();checks['all_old_'+table+'_rows_preserved']=True
assert sha(orig)==oh and sha(idxpath)==ih and sha(bulk)==bh;assert all(sha(Path(p))==h for p,h in pins.items());assert not db.execute('select 1 from document where h in (select h from protected)').fetchone();assert db.execute('pragma integrity_check').fetchone()[0]=='ok';assert attached==83
report={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'83_preexisting_failed_outputs_attached_without_promotion','existing_failed_contexts_attached':attached,'new_model_calls':0,'new_production_accepted':0,'original_accepted_contexts_with_values':db.execute('select count(distinct h) from document where original_accepted=1').fetchone()[0],'original_accepted_ad_keys_with_values':db.execute('select count(distinct k) from accepted_original_values').fetchone()[0],'covered_contexts_by_original_state':dict(collections.Counter(s for h,s in states.items() if h in covered)),'unattached_contexts_by_original_state':dict(missing),'all_ad_keys_created_matched':db.execute("select count(*) from metadata_resolution where status='matched_consistent'").fetchone()[0],'retry_forbidden_or_quarantined_contexts':db.execute('select count(*) from do_not_reinfer_context').fetchone()[0],'original_source_files_SHA_verified':filesverified,'original_commit_checksum_chain_verified':True,'all_source_and_ledger_pins_unchanged':True,'checks':checks,'previous_database_sha256':oh,'paper_paused':True}
db.commit();db.close();idx.close();report['database_sha256']=sha(O/'REUSED_VALUES_WITH_CREATED_PRIVATE.sqlite');(O/'FAILED_OUTPUT_REUSE_PUBLIC.json').write_text(json.dumps(report,indent=2)+'\n');(O/'RECOVERED_SOURCE_PINS_PRIVATE.json').write_text(json.dumps(pins,indent=2)+'\n')
# The remaining 11 have no usable exception locator. Record only path metadata now.
left=[x for x in read(C/'RESUME_LOCATORS_PRIVATE.json')['missing_saved_cases'] if x['context_sha256'] not in covered];(O/'REMAINING_SAVED_LOCATORS_PRIVATE.json').write_text(json.dumps(left,indent=2)+'\n')
print(json.dumps(report))
