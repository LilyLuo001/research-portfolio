import json,hashlib,sqlite3,datetime,collections,sys,urllib.parse,os,shutil
from pathlib import Path
R=Path.home()/'migration';B=R/'execution_20261116/run001/stage2';I=B/'revision002';O=B/'revision003';os.umask(0o077);O.mkdir(exist_ok=False)
def sh(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def rd(p):return json.loads(p.read_bytes())
oldsha=sh(I/'REUSED_VALUES_PRIVATE.sqlite');db=sqlite3.connect(O/'REUSED_VALUES_PRIVATE.sqlite');old=sqlite3.connect((I/'REUSED_VALUES_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True);old.backup(db);old.close()
index=sqlite3.connect((R/'integration_20261116/run001/revision003/STATUS_INDEX_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True);states=dict(index.execute('select h,state from final_status'));blocked={h for h,st in states.items() if st=='quarantined'}
sys.path.insert(0,str(R/'code'));from workflow import call;from checkpoint_scope import BASE
missing_astra=[];attached=0
for task,x in rd(R/'astra/extraction/STATE_PRIVATE.json')['accepted'].items():
 h=x['context_sha256']
 if db.execute('select 1 from document where h=? and original_accepted=1',(h,)).fetchone():continue
 try:
  with call(BASE+'astra-extraction/v1/'+urllib.parse.quote(task,safe='/')+'/VALIDATED_PRIVATE.jsonl','https://storage.azure.com/',headers={'x-ms-version':'2023-11-03'}) as response:data=response.read(2000001)
  assert len(data)<=2000000 and hashlib.sha256(data).hexdigest()==x['sha256'];p=O/(x['sha256']+'.jsonl');p.write_bytes(data)
  for n,l in enumerate(data.splitlines(),1):
   row=json.loads(l);assert row['context_sha256']==h and h not in blocked and states[h]=='accepted_original_scope';payload=json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'));d=hashlib.sha256(('Astra_original_accepted\0'+x['sha256']+'\0'+str(n)+'\0'+payload).encode()).hexdigest();db.execute('INSERT INTO document VALUES(?,?,?,?,?,?,?,?)',(d,h,'','Astra_original_accepted',x['sha256'],n,1,payload))
   vals={'document_status':row.get('document_status'),'technology':{'inventory_status':row.get('technology_inventory_status'),'items':row.get('technology_items',[])},'experience':{'outcomes':row.get('experience_outcomes'),'items':row.get('experience_clauses',[])},'entry':{'outcomes':row.get('entry_outcomes'),'items':row.get('entry_items',[])},'responsibility':{'outcomes':row.get('responsibility_outcomes'),'items':row.get('responsibility_items',[])},'qualification_alternatives':row.get('qualification_alternatives',[]),'evidence_resolution':row.get('evidence_resolution',[]),'unresolved_notes':row.get('unresolved_notes',[])}
   for family,value in vals.items():db.execute('INSERT INTO field_value VALUES(?,?,?,?)',(d,family,'original_scope',json.dumps(value,ensure_ascii=False)))
   attached+=1
  db.execute('INSERT OR IGNORE INTO source VALUES(?,?,?)',(x['sha256'],str(p),len(data)))
 except Exception as e:missing_astra.append({'exception_type':type(e).__name__,'http_status':getattr(e,'code',None),'operation':'read_original_accepted_Astra_Blob','identity':'existing_VM_system_managed_identity','resource':'existing_private_checkpoint_Blob','minimum_permission_if_authorization_error':'Storage Blob Data Reader on existing container'})
error_types=collections.Counter()
for p in (I/'validation').glob('*/ERRORS_PRIVATE.jsonl'):
 for l in p.open():
  for e in json.loads(l).get('errors',[]):
   if e.startswith('schema '):cat='schema'
   elif e.startswith('exact quote missing'):cat='exact_quote_missing'
   elif 'no review' in e:cat='missing_review'
   elif 'outside trusted' in e or 'context_sha256' in e:cat='input_identity_mismatch'
   elif 'duplicate review' in e:cat='duplicate_review'
   else:cat='cross_field_or_relation_rule'
   error_types[cat]+=1
# Preserve and expose multiple stored versions, never choose the newest automatically.
conflict_rows=db.execute("select h,count(distinct document_json),count(*) from document where asset='Pro_PRIMARY_saved_unverified' group by h having count(distinct document_json)>1").fetchall()
(O/'MULTIPLE_PRIMARY_VERSIONS_PRIVATE.json').write_text(json.dumps([{'context_sha256':h,'distinct_payloads':n,'stored_rows':m} for h,n,m in conflict_rows],indent=2)+'\n')
covered={h for h, in db.execute('select distinct h from document')};accepted={h for h, in db.execute('select distinct h from document where original_accepted=1')};cov=collections.Counter();missing=collections.Counter()
for h,state in states.items():
 (cov if h in covered else missing)[state]+=1
# Required next lookup for date and source metadata: derive exact shard references, not JOB_HASH search.
metas=rd(R/'integration_20261116/run001/DISCOVERY_PRIVATE.json')['metadata_inventory'];shards=set()
for m in metas:
 p=R/'integration_20261116/run001/metadata_cache'/(m['sha256']+'.metadata')
 if m['rel'].endswith('PACKET_MANIFEST_PRIVATE.jsonl') and p.exists():
  for l in p.open():
   x=json.loads(l)
   if x['context_sha256'] in accepted:shards.add(x.get('shard_id'))
assert sh(I/'REUSED_VALUES_PRIVATE.sqlite')==oldsha;assert db.execute('pragma integrity_check').fetchone()[0]=='ok';assert not db.execute('select 1 from document where h in (select h from protected)').fetchone()
public={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'available_old_values_attached_with_explicit_gaps_and_no_promotion','old_database_preserved_sha256':oldsha,'Astra_original_accepted_additional_Blob_recovery':attached,'Astra_Blob_read_errors':missing_astra,'accepted_original_contexts_with_values':len(accepted),'accepted_ad_keys_with_values':db.execute('select count(distinct k) from accepted_original_values').fetchone()[0],'covered_contexts_by_original_state':dict(cov),'unattached_contexts_by_original_state':dict(missing),'PRIMARY_error_entry_categories_not_unique_records':dict(error_types),'contexts_with_multiple_distinct_PRIMARY_payloads':len(conflict_rows),'Pro_accepted_first_context_shards_for_metadata_join':len(shards),'CREATED_join_materialized':False,'new_model_calls':0,'new_production_accepted':0,'protected_payloads_absent':True,'integrity_pass':True,'source_schema_rules_changed':False,'raw_ads_rescanned':False,'known_base_model_budget_spent_usd':0,'independent_machine_qualification_not_started':True}
db.execute("DELETE FROM issue WHERE kind='no_value_carrier_attached_yet' AND h IN (SELECT h FROM document)");db.commit();db.close();index.close();public['database_sha256']=sh(O/'REUSED_VALUES_PRIVATE.sqlite');(O/'REUSE_CLOSURE_PUBLIC.json').write_text(json.dumps(public,indent=2)+'\n')
print(json.dumps(public))
