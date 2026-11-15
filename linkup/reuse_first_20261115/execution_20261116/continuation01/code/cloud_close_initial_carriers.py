"""Reuse the initial five Kimi results and original Astra failure; never regenerate."""
import collections,datetime,hashlib,json,os,sqlite3
from pathlib import Path
R=Path.home()/'migration';B=R/'execution_20261116/run001';C=B/'continuation01';O=C/'joined_revision003';os.umask(0o077);O.mkdir(exist_ok=False)
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
oldpath=C/'joined_revision002/REUSED_VALUES_WITH_CREATED_PRIVATE.sqlite';oldsha=sha(oldpath);db=sqlite3.connect(O/'REUSED_VALUES_WITH_CREATED_PRIVATE.sqlite');old=sqlite3.connect(oldpath.as_uri()+'?mode=ro',uri=True);old.backup(db);old.close()
idxpath=R/'integration_20261116/run001/revision003/STATUS_INDEX_PRIVATE.sqlite';idx=sqlite3.connect(idxpath.as_uri()+'?mode=ro',uri=True);states=dict(idx.execute('select h,state from final_status'));db.execute('create table extra_carrier_provenance(d TEXT PRIMARY KEY,original_ledger_sha TEXT,validation_sha TEXT,input_sha TEXT,original_status TEXT)')
statepath=R/'opencode_kimi_20261115/run01/CANDIDATE_STATE_PRIVATE.json';stsha=sha(statepath);state=read(statepath);pins={str(statepath):stsha};counts=collections.Counter()
def attach(row,p,asset,validation,inputpath,ledger_sha,original_status):
 h=row['context_sha256'];assert states[h]=='saved_unverified';assert not db.execute('select 1 from document where h=?',(h,)).fetchone();assert not db.execute('select 1 from protected where h=?',(h,)).fetchone()
 inp=[json.loads(l) for l in inputpath.read_bytes().splitlines() if l.strip()];assert len(inp)==1;assert inp[0]['context_sha256']==h;assert inp[0]['record_id']==row['record_id'];assert hashlib.sha256(inp[0]['full_document'].encode()).hexdigest()==h
 vr=read(validation);assert sha(inputpath)==vr['inputs']['packet_sha256'];assert vr['inputs']['schema_sha256']=='fdc5b0d653bd8f1c98a3e6cd20970156621403154a7ad073e977ea14ddfb310e'
 source=sha(p)
 if original_status=='pass':assert source==vr['private_outputs']['validated_sha256']
 else:assert source in {x['sha256'] for x in vr['inputs']['review_inputs']}
 payload=json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'));did=hashlib.sha256((asset+'\0'+source+'\0'+'1'+'\0'+payload).encode()).hexdigest();db.execute('insert into document values(?,?,?,?,?,?,?,?)',(did,h,'',asset,source,1,0,payload))
 vals={'document_status':row.get('document_status'),'technology':{'inventory_status':row.get('technology_inventory_status'),'items':row.get('technology_items',[])},'experience':{'outcomes':row.get('experience_outcomes'),'items':row.get('experience_clauses',[])},'entry':{'outcomes':row.get('entry_outcomes'),'items':row.get('entry_items',[])},'responsibility':{'outcomes':row.get('responsibility_outcomes'),'items':row.get('responsibility_items',[])},'qualification_alternatives':row.get('qualification_alternatives',[]),'evidence_resolution':row.get('evidence_resolution',[]),'unresolved_notes':row.get('unresolved_notes',[])}
 for family,value in vals.items():db.execute('insert into field_value values(?,?,?,?)',(did,family,'saved_unverified' if original_status=='pass' else 'failed_frozen_validation_not_usable',json.dumps(value,ensure_ascii=False)))
 db.execute('insert into extra_carrier_provenance values(?,?,?,?,?)',(did,ledger_sha,sha(validation),sha(inputpath),original_status))
 for f in [p,validation,inputpath]:pins[str(f)]=sha(f);db.execute('insert or ignore into source values(?,?,?)',(sha(f),str(f),f.stat().st_size))
 if original_status!='pass':db.execute('insert or replace into do_not_reinfer_context values(?,?,?)',(h,'original_Astra_frozen_validation_failed_preserve_output',sha(validation)));db.execute('insert into issue values(?,?,?,?)',('attached_original_failed_validation',h,source,'retained_unusable;not_newly_accepted;retry_forbidden'))
 counts[asset]+=1
for task,x in state['engineering_candidates'].items():
 p=Path(x['path']);assert sha(p)==x['validated_sha256'];row=json.loads(p.read_text());vp=p.parent/'CLOUD_VALIDATION_PUBLIC.json';assert read(vp)['status']=='pass';attach(row,p,'Kimi_initial_saved_unverified',vp,p.parent/'INPUT_PRIVATE.jsonl',stsha,'pass')
left=read(C/'joined_revision002/REMAINING_SAVED_LOCATORS_PRIVATE.json');target={x['context_sha256'] for x in left if x['task']=='batch052/packet_0094/0'};assert len(target)==1
for vp in (R/'astra/extraction').glob('*/VALIDATION_PUBLIC.json'):
 vr=read(vp)
 if vr['status']!='fail':continue
 p=vp.parent/'REVIEW_PRIVATE.jsonl';ip=vp.parent/'INPUT_PRIVATE.jsonl'
 if not p.exists() or not ip.exists():continue
 assert sha(ip)==vr['inputs']['packet_sha256'];inp=json.loads(ip.read_text())
 if inp['context_sha256'] not in target:continue
 row=json.loads(p.read_text());assert row['context_sha256']==inp['context_sha256'];attach(row,p,'Astra_original_failed_saved_unverified',vp,ip,None,'fail')
covered={x[0] for x in db.execute('select distinct h from document')};missing=collections.Counter(s for h,s in states.items() if h not in covered)
# Diagnose, but never repair, the remaining Pro identity-binding gaps from saved metadata.
plan=read(B/'stage2/REMAINING_SOURCE_LOCATORS_PRIVATE.json');val=read(B/'stage2/revision002/PRIMARY_VALIDATION_PRIVATE.json');issues=[]
for x in left:
 h=x['context_sha256']
 if h in covered:continue
 mm=plan['mapping'].get(h,{});v=[v for v in val if h in v['contexts']];checks=[]
 for y in v:
  p=B/'stage2/revision002/cache'/(y['primary_sha256']+'.data')
  if not p.exists():checks.append({'status':'file_not_cached'});continue
  assert sha(p)==y['primary_sha256'];rows=[json.loads(l) for l in p.read_bytes().splitlines() if l.strip()]
  checks.append({'status':y['status'],'source_sha256':y['primary_sha256'],'stored_rows':len(rows),'context_id_matches':sum(r.get('context_sha256')==h for r in rows),'record_id_matches':sum(r.get('record_id')=='corpus-pro-'+h for r in rows)})
 issues.append({'context_sha256':h,'original_state':states[h],'source_packet':mm,'existing_primary_checks':checks,'disposition':'identity_or_carrier_gap_not_eligible_for_new_inference'})
(O/'UNBOUND_PRO_REMAINDER_PRIVATE.json').write_text(json.dumps(issues,indent=2)+'\n')
db.execute("delete from issue where kind='no_value_carrier_attached_yet' and h in (select h from document)");assert all(sha(Path(p))==h for p,h in pins.items());assert sha(oldpath)==oldsha;assert db.execute('pragma integrity_check').fetchone()[0]=='ok';assert not db.execute('select 1 from document where h in (select h from protected)').fetchone()
report={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'initial_output_carriers_attached_existing_states_preserved','additional_carriers_by_asset':dict(counts),'covered_contexts_by_original_state':dict(collections.Counter(s for h,s in states.items() if h in covered)),'unattached_contexts_by_original_state':dict(missing),'unbound_Pro_contexts':len(issues),'unbound_Pro_with_matching_record_id':sum(any(c.get('record_id_matches') for c in x['existing_primary_checks']) for x in issues),'unbound_Pro_with_matching_context_id':sum(any(c.get('context_id_matches') for c in x['existing_primary_checks']) for x in issues),'unbound_Pro_with_zero_stored_rows':sum(bool(x['existing_primary_checks']) and all(c.get('stored_rows')==0 for c in x['existing_primary_checks']) for x in issues),'all_ad_keys_created_matched':db.execute("select count(*) from metadata_resolution where status='matched_consistent'").fetchone()[0],'original_accepted_ad_keys_with_values':db.execute('select count(distinct k) from accepted_original_values').fetchone()[0],'retry_forbidden_or_quarantined_contexts':db.execute('select count(*) from do_not_reinfer_context').fetchone()[0],'new_model_calls':0,'new_production_accepted':0,'all_source_SHA_pins_unchanged':True,'previous_database_sha256':oldsha,'paper_paused':True}
db.commit();db.close();idx.close();report['database_sha256']=sha(O/'REUSED_VALUES_WITH_CREATED_PRIVATE.sqlite');(O/'INITIAL_OUTPUT_REUSE_PUBLIC.json').write_text(json.dumps(report,indent=2)+'\n');(O/'EXTRA_SOURCE_PINS_PRIVATE.json').write_text(json.dumps(pins,indent=2)+'\n');print(json.dumps(report))
