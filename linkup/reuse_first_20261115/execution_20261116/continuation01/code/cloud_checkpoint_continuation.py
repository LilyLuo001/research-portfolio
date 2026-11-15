"""Verify and checkpoint immutable continuation artifacts; leave the single model worker alone."""
import base64,collections,datetime,hashlib,json,os,sqlite3,sys,tarfile
from pathlib import Path
R=Path.home()/'migration';B=R/'execution_20261116/run001';C=B/'continuation01';V=C/'joined_revision003';Q=B/'qualification500_v1';L=Q/'luna_revision002';os.umask(0o077)
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def save(p,obj):
 data=(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode();tmp=p.with_name(p.name+'.tmp');tmp.write_bytes(data);os.replace(tmp,p)
assert sha(V/'REUSED_VALUES_WITH_CREATED_PRIVATE.sqlite')=='fdcdfc86270c0391fef512dcdd641438606ec9ad2f00b0554c8bc9b1353f49a5'
original_index=R/'integration_20261116/run001/revision003/STATUS_INDEX_PRIVATE.sqlite';assert sha(original_index)=='0344e94b9f2b75af74652a2f517c4e5c535d8090e1db62eec84b55afced1523a'
db=sqlite3.connect((V/'REUSED_VALUES_WITH_CREATED_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True);assert db.execute('pragma integrity_check').fetchone()[0]=='ok';assert not db.execute('select 1 from document where h in (select h from protected)').fetchone()
# Check that all old semantic/mask rows survive verbatim, not just total counts.
orig=B/'stage2/revision003/REUSED_VALUES_PRIVATE.sqlite';assert sha(orig)=='0594d18bfb27a9a5f9069aec5065e0b03557965f9631f82ab9742ae525f57925';db.execute('attach database ? as original',(str(orig),))
for table in ['ad','field_mask','document','field_value','source','protected']:
 assert not db.execute(f'select * from original.{table} except select * from {table} limit 1').fetchone()
old_accepted=db.execute('select count(distinct h) from document where original_accepted=1').fetchone()[0];assert old_accepted==39298;assert db.execute("select count(*) from metadata_resolution where status='matched_consistent'").fetchone()[0]==62414;db.close()
closure=read(V/'INITIAL_OUTPUT_REUSE_PUBLIC.json');unbound=read(V/'UNBOUND_PRO_REMAINDER_PRIVATE.json');left=read(C/'joined_revision002/REMAINING_SAVED_LOCATORS_PRIVATE.json');taskbyh={x['context_sha256']:x['task'] for x in left};parts=collections.Counter('Astra_original_failure' if taskbyh.get(x['context_sha256'])=='batch052/packet_0094/0' else 'Pro_original_carrier_or_binding' for x in unbound)
gap=read(B/'GAP_REGISTER_PUBLIC.json');save(C/'PREVIOUS_GAP_REGISTER_PUBLIC.json',gap)
gap['at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();gap['fine_semantic_states'].update(saved_unverified_values_attached=6500,saved_unverified_missing_carrier=6)
assert sum(gap['fine_semantic_states'].values())==55882
gap['action_by_gap'].pop('94_saved_missing_carriers',None);gap['action_by_gap']['6_saved_missing_carriers']='Five Pro carrier/binding gaps and one original Astra failed-output locator remain unresolved; none is proven unread or eligible for rerun.';gap['action_by_gap']['CREATED_join']='Materialized for all 62,414 existing four-key ad identities; 45,592 have original accepted values. This is the fine-semantic ledger scope, not full-corpus coverage.'
gap['saved_unattached_source_partition']=dict(parts);gap['saved_unattached_partition_correction']='The earlier initial-attachment report used unbound_Pro as a generic remainder label; exact partition is 5 Pro and 1 Astra.';gap['newly_reused_old_output_contexts_this_continuation']=88;gap['CREATED_join_missing_existing_ledger_keys']=0;gap['new_production_queue_released']=False
save(C/'GAP_REGISTER_PUBLIC.json',gap);save(B/'GAP_REGISTER_PUBLIC.json',gap)
# Correct current pointers only; root historical AZURE_RESEARCH_STATE and accepted ledgers stay untouched.
pointer=read(B/'AZURE_RESEARCH_STATE.json');save(C/'PREVIOUS_EXECUTION_POINTER_PUBLIC.json',pointer)
pointer.update(status='metadata_join_and_old_output_reuse_advanced_candidate_qualification_still_active_or_observed',database_relative_to_migration=str((V/'REUSED_VALUES_WITH_CREATED_PRIVATE.sqlite').relative_to(R)),database_sha256=sha(V/'REUSED_VALUES_WITH_CREATED_PRIVATE.sqlite'),gap_register_relative_to_migration=str((C/'GAP_REGISTER_PUBLIC.json').relative_to(R)),qualification_status_relative_to_migration=str((L/'RUN_STATUS_PUBLIC.json').relative_to(R)),reference_preflight_relative_to_migration=str((Q/'reference_preflight002/REFERENCE_PREFLIGHT_PUBLIC.json').relative_to(R)),step4_released=False,step6_released=False,paper_paused=True,new_authorized_cap_usd=450)
save(B/'AZURE_RESEARCH_STATE.json',pointer);save(R/'CURRENT_EXECUTION_PUBLIC.json',pointer);save(C/'CURRENT_EXECUTION_PUBLIC.json',pointer)
code=C/'code';code.mkdir(exist_ok=False)
for name,encoded in FILES_B64.items():
 assert '/' not in name and name.endswith('.py');(code/name).write_bytes(base64.b64decode(encoded))
chosen=[V/'REUSED_VALUES_WITH_CREATED_PRIVATE.sqlite']+list(code.iterdir())
for folder in [C/'carrier_recovery',C/'joined_revision001',C/'joined_revision002',V,C/'remaining_probe']:
 chosen += [p for p in folder.glob('*.json') if p.is_file()]
chosen += [C/n for n in ['RESUME_LOCATORS_PRIVATE.json','RESUME_INVENTORY_PUBLIC.json','GAP_REGISTER_PUBLIC.json','PREVIOUS_GAP_REGISTER_PUBLIC.json','CURRENT_EXECUTION_PUBLIC.json','PREVIOUS_EXECUTION_POINTER_PUBLIC.json']]
for folder in [Q/'reference_preflight001',Q/'reference_preflight002']:
 chosen += [p for p in folder.iterdir() if p.is_file()]
chosen=list(dict.fromkeys(chosen));pins={str(p.relative_to(B)):sha(p) for p in chosen};save(C/'CHECKPOINT_FILES_PRIVATE.json',pins);chosen.append(C/'CHECKPOINT_FILES_PRIVATE.json')
archive=C/'REUSE_CONTINUATION_PRIVATE.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz',compresslevel=1) as tar:
 for p in chosen:tar.add(p,arcname=str(p.relative_to(B)),recursive=False)
assert all(sha(B/p)==h for p,h in pins.items());assert archive.stat().st_size<256000000
sys.path.insert(0,str(R/'code'));from checkpoint_scope import upload,BASE;from workflow import call
key='reuse-execution/20261116/run001/continuation01/REUSE_CONTINUATION_PRIVATE.tar.gz';upload(archive,key);h=hashlib.sha256();n=0
with call(BASE+key,'https://storage.azure.com/',headers={'x-ms-version':'2023-11-03'}) as r:
 while True:
  data=r.read(1048576)
  if not data:break
  h.update(data);n+=len(data)
assert n==archive.stat().st_size and h.hexdigest()==sha(archive)
status=read(L/'RUN_STATUS_PUBLIC.json');proc=Path('/proc')/str(status['pid']);alive=proc.exists() and str(L/'cloud_qualification_luna_worker.py').encode() in (proc/'cmdline').read_bytes();events={}
for l in (L/'ATTEMPTS_PRIVATE.jsonl').read_text().splitlines():
 try:e=json.loads(l)
 except json.JSONDecodeError:continue
 events[e['ordinal'],e['attempt']]=e
snapshot={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'worker_status':status,'process_alive_exact_command':alive,'saved_case_results':len(list((L/'results').glob('case*/RESULT_PUBLIC.json'))),'physical_attempts':len(events),'rate_limit_tokens_header_counts':dict(collections.Counter(x.get('rate_headers',{}).get('x-ratelimit-limit-tokens','not_yet_received') for x in events.values())),'new_Kimi_or_GPT_requests_this_wave':0,'candidate_worker_restarted_by_this_continuation':False};save(C/'LATEST_QUALIFICATION_STATUS_PUBLIC.json',snapshot)
report={'at_utc':snapshot['at_utc'],'status':'immutable_continuation_checkpoint_verified','archive_blob_key':key,'archive_bytes':n,'archive_sha256':h.hexdigest(),'archive_full_readback_SHA_verified':True,'latest_value_database_relative_to_migration':str((V/'REUSED_VALUES_WITH_CREATED_PRIVATE.sqlite').relative_to(R)),'latest_value_database_sha256':sha(V/'REUSED_VALUES_WITH_CREATED_PRIVATE.sqlite'),'old_semantic_and_mask_rows_preserved_byte_value_identical':True,'original_status_index_unchanged':True,'old_output_contexts_reused_this_continuation':88,'saved_unverified_contexts_with_values':6500,'original_accepted_contexts_with_values':39298,'original_accepted_ad_keys_with_values':45592,'existing_ledger_ad_keys_created_matched':62414,'missing_saved_carrier_partition':dict(parts),'missing_accepted_carriers':10,'status_unreconciled':10012,'protected_quarantined':56,'independent_existing_Kimi_references_revalidated':150,'new_Kimi_reference_inputs_prepared_not_submitted':350,'new_production_accepted':0,'step4_locked':True,'paper_paused':True,'new_resources_or_timers':False,'infrastructure_invoice_cost_usd':None,'infrastructure_note':'Existing VM/Blob only; actual job-level invoice not available. Stage1/2 allowances are not reported as zero cost.'}
save(C/'CHECKPOINT_PUBLIC.json',report)
import zlib
out={'CHECKPOINT_PUBLIC.json':report,'LATEST_QUALIFICATION_STATUS_PUBLIC.json':snapshot,'GAP_REGISTER_PUBLIC.json':gap}
encoded=base64.b64encode(zlib.compress(json.dumps(out).encode(),9)).decode();assert len(encoded)<3800;print(json.dumps({'aggregate_zlib_b64':encoded}))
