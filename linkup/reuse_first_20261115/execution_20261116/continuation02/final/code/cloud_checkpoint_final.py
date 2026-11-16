"""Persist a closed qualification and truthful current pointers, then verify Blob bytes."""
import base64,collections,datetime,hashlib,json,os,sqlite3,sys,tarfile
from pathlib import Path
os.umask(0o077)
R=Path.home()/'migration';B=R/'execution_20261116/run001';Q=B/'qualification500_v1';O=B/'continuation02';C=O/'final_checkpoint'
def read(p):return json.loads(p.read_text())
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,x):
 t=p.with_name(p.name+'.tmp');t.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');os.replace(t,p)
def immutable(p,data):
 if p.exists():assert p.read_bytes()==data,'checkpoint_source_conflict'
 else:p.write_bytes(data)
assert not (C/'CHECKPOINT_PUBLIC.json').exists(),'checkpoint_already_finished_read_existing_receipt'
C.mkdir(exist_ok=True)
final=read(O/'QUALIFICATION_DECISION_PUBLIC.json');assert final['status']=='fixed_qualification_protocol_completed'
assert final['stage4_admitted_inputs']==0 and final['new_production_accepted']==0
for name,encoded in TRANSPORT_B64.items():
 assert '/' not in name and name in ('KIMI_FINAL_PUBLIC.json','GATEWAY_ATTEMPTS_PRIVATE.jsonl','LEASE_RECOVERY_PUBLIC.json')
 immutable(C/name,base64.b64decode(encoded))
kimi=read(C/'KIMI_FINAL_PUBLIC.json');assert kimi['finished']==350 and kimi['cloud_validated']==350
assert kimi['reserved_usd']<=135 and kimi['physical_attempts']<=420
legacy=R/'integration_20261116/run001/revision003/STATUS_INDEX_PRIVATE.sqlite';database=B/'continuation01/joined_revision003/REUSED_VALUES_WITH_CREATED_PRIVATE.sqlite'
assert sha(legacy)=='0344e94b9f2b75af74652a2f517c4e5c535d8090e1db62eec84b55afced1523a'
assert sha(database)=='fdcdfc86270c0391fef512dcdd641438606ec9ad2f00b0554c8bc9b1353f49a5'
conn=sqlite3.connect(database.as_uri()+'?mode=ro',uri=True);assert conn.execute('pragma integrity_check').fetchone()[0]=='ok';conn.close()
# Check no model process from this qualification remains; no unrelated services are touched.
for dirname,script in [('luna_revision002','cloud_qualification_luna_worker.py'),('astra_audit50_v1','cloud_astra_audit_worker.py'),('astra_audit50_transport_recovery_v1','cloud_astra_transport_recovery_worker.py')]:
 d=Q/dirname;s=read(d/'RUN_STATUS_PUBLIC.json');p=Path('/proc')/str(s['pid'])/'cmdline'
 assert s['status']=='finite_benchmark_completed' and (not p.exists() or str(d/script).encode() not in p.read_bytes())
 for rel,h in read(d/'SHA256SUMS_PRIVATE.json').items():assert sha(d/rel)==h
lease=read(Q/'kimi_reference350_v1/LEASE_PRIVATE.json');p=Path('/proc')/str(lease['pid'])/'cmdline';assert not p.exists() or b'hold_reference_lane.py' not in p.read_bytes()
# Preserve new provider protections as an append-only execution overlay rather
# than mutating historical acceptance labels or mixing different scope counts.
base_exclusions=read(Q/'luna_revision002/EXCLUSIONS_PRIVATE.json');runtime_exclusions={k:set(base_exclusions.get(k,[])) for k in ('tasks','context_sha256')}
for p in list((Q/'kimi_reference350_v1/commits').glob('*/EXCLUSIONS_PRIVATE.json'))+[Q/'astra_audit50_transport_recovery_v1/EXCLUSIONS_PRIVATE.json']:
 e=read(p)
 for k in runtime_exclusions:runtime_exclusions[k].update(e.get(k,[]))
new_protected=len(runtime_exclusions['context_sha256']-set(base_exclusions.get('context_sha256',[])))
save(C/'RUNTIME_EXCLUSIONS_PRIVATE.json',{k:sorted(v) for k,v in runtime_exclusions.items()})
old=read(B/'AZURE_RESEARCH_STATE.json');immutable(C/'PREVIOUS_EXECUTION_POINTER_PUBLIC.json',(json.dumps(old,indent=2)+'\n').encode())
gap=read(B/'continuation01/GAP_REGISTER_PUBLIC.json');gap['at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
gap['action_by_gap']['10_original_accepted_missing_carriers']='Both exact expected carriers were held for credential_content_review; VM managed identity HEAD returned BlobNotFound. Preserve accepted state; no rerun or bypass of hold.'
gap['known_qualified_new_production_fields']=len(final['machine_reference_qualified_fields']);gap['qualification_decision_relative_to_migration']=str((O/'QUALIFICATION_DECISION_PUBLIC.json').relative_to(R));save(C/'GAP_REGISTER_PUBLIC.json',gap)
usage={'Luna':final['Luna_usage'],'Kimi':{'physical_attempts':kimi['physical_attempts'],'input_tokens':kimi['input_tokens'],'output_tokens':kimi['output_tokens'],'conservative_reserved_usd':kimi['reserved_usd'],'priced_usage_estimate_usd':kimi['public_list_usage_estimate_usd'],'responses_without_usage':kimi['responses_without_usage'],'actual_invoice_verified':False},'Astra':final['Astra_usage']}
cost={'qualification_model_legs':usage,'total_priced_usage_estimate_usd':sum(x['priced_usage_estimate_usd'] for x in usage.values()),'total_conservative_model_reservations_usd':sum(x['conservative_reserved_usd'] for x in usage.values()),'qualification_cap_usd':250,'stage1_cap_usd':25,'stage2_cap_usd':25,'stage4_cap_usd':150,'stage4_model_spend_usd':0,'paper_cap_usd':0,'new_paid_resources_created':False,'infrastructure_job_level_invoice_usd':None,'infrastructure_note':'Existing VM/Blob only. Caps and reservation estimates are not charges. No zero-infrastructure-cost or Azure-credit coverage claim.'}
assert cost['total_conservative_model_reservations_usd']<=250;save(C/'COST_PUBLIC.json',cost)
pointer={**old,'at_utc':gap['at_utc'],'status':'fixed_qualification_complete_production_not_admitted','database_relative_to_migration':str(database.relative_to(R)),'database_sha256':sha(database),'gap_register_relative_to_migration':str((C/'GAP_REGISTER_PUBLIC.json').relative_to(R)),'qualification_decision_relative_to_migration':str((O/'QUALIFICATION_DECISION_PUBLIC.json').relative_to(R)),'qualification_status_relative_to_migration':str((O/'QUALIFICATION_DECISION_PUBLIC.json').relative_to(R)),'step4_released':False,'step6_released':False,'paper_paused':True,'new_authorized_cap_usd':450,'whole_delivery_unique_missing_field_inputs':None,'new_production_accepted':0,'runtime_exclusions_relative_to_migration':str((C/'RUNTIME_EXCLUSIONS_PRIVATE.json').relative_to(R)),'new_qualification_provider_protected_contexts':new_protected}
save(C/'AZURE_RESEARCH_STATE.json',pointer);save(B/'AZURE_RESEARCH_STATE.json',pointer);save(R/'CURRENT_EXECUTION_PUBLIC.json',pointer)
code=C/'code';code.mkdir(exist_ok=True)
for name,encoded in CODE_B64.items():
 assert '/' not in name and name.endswith('.py');immutable(code/name,base64.b64decode(encoded))
chosen=[p for p in Q.rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith('.lock')]
chosen += [p for p in O.glob('*.json') if p.is_file()]
chosen += [p for p in C.rglob('*') if p.is_file() and p.suffix in ('.py','.json','.jsonl')]
chosen=list(dict.fromkeys(chosen));pins={str(p.relative_to(B)):sha(p) for p in chosen};save(C/'CHECKPOINT_FILES_PRIVATE.json',pins);chosen.append(C/'CHECKPOINT_FILES_PRIVATE.json')
archive=C/'QUALIFICATION_FINAL_PRIVATE.tar.gz'
if not archive.exists():
 temp=archive.with_suffix('.partial')
 with tarfile.open(temp,'w:gz',compresslevel=1) as tar:
  for p in chosen:tar.add(p,arcname=str(p.relative_to(B)),recursive=False)
 temp.rename(archive)
assert all(sha(B/p)==h for p,h in pins.items());assert archive.stat().st_size<600000000
sys.path.insert(0,str(R/'code'));from checkpoint_scope import upload,BASE;from workflow import call
key='reuse-execution/20261116/run001/continuation02/QUALIFICATION_FINAL_PRIVATE.tar.gz';upload(archive,key)
h=hashlib.sha256();n=0
with call(BASE+key,'https://storage.azure.com/',headers={'x-ms-version':'2023-11-03'}) as response:
 while True:
  b=response.read(1048576)
  if not b:break
  h.update(b);n+=len(b)
assert n==archive.stat().st_size and h.hexdigest()==sha(archive)
report={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'closed_qualification_checkpoint_verified','archive_blob_key':key,'archive_bytes':n,'archive_sha256':h.hexdigest(),'full_blob_readback_SHA_verified':True,'frozen_case_accounting':500,'Kimi_prior_reused':150,'Kimi_new_results_accounted':350,'Astra_audit_results':final['Astra_audit_results_accounted'],'qualified_fields':final['machine_reference_qualified_fields'],'old_status_index_and_value_database_unchanged':True,'current_pointer_relative_to_migration':str((B/'AZURE_RESEARCH_STATE.json').relative_to(R)),'new_production_accepted':0,'model_workers_in_this_protocol_running':False,'paper_paused':True,'stage4_released':False,'stage6_released':False,'whole_delivery_missing_input_count':None,'new_qualification_provider_protected_contexts':new_protected,'runtime_protections_preserved_separately_from_historical_56_status_count':True}
save(C/'CHECKPOINT_PUBLIC.json',report)
import zlib
out={'CHECKPOINT_PUBLIC.json':report,'COST_PUBLIC.json':cost,'GAP_REGISTER_PUBLIC.json':gap,'AZURE_RESEARCH_STATE.json':pointer}
encoded=base64.b64encode(zlib.compress(json.dumps(out).encode(),9)).decode();assert len(encoded)<3800;print(json.dumps({'aggregate_zlib_b64':encoded}))
