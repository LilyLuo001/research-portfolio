"""Verify the reuse overlay, reconcile source-version duplicates, archive immutables.

Does not snapshot mutable candidate responses or change any historical ledger.
CODE_FILES_B64 is injected from reviewed public source only.
"""
import base64, collections, datetime, hashlib, json, os, sqlite3, sys, tarfile
from pathlib import Path
R=Path.home()/'migration'; B=R/'execution_20261116/run001'; S=B/'stage1'; V=B/'stage2/revision003'; Q=B/'qualification500_v1'
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def read(p):return json.loads(p.read_bytes())
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def main():
    os.umask(0o077)
    assert sha(V/'REUSED_VALUES_PRIVATE.sqlite')=='0594d18bfb27a9a5f9069aec5065e0b03557965f9631f82ab9742ae525f57925'
    assert sha(R/'integration_20261116/run001/revision003/STATUS_INDEX_PRIVATE.sqlite')=='0344e94b9f2b75af74652a2f517c4e5c535d8090e1db62eec84b55afced1523a'
    receipts=read(S/'ALL_SHARD_ACCOUNTING_PUBLIC.json'); assert receipts['verified_shards']==2464 and receipts['missing_shards']==0
    assert receipts['totals']['accounting.raw_rows']==298673078 and receipts['totals']['accounting.source_bytes']==652027698428
    keys={};reports=0
    for m in read(S/'VERIFIED_DELIVERY_METADATA_PRIVATE.json'):
        p=S/'metadata_cache'/(m['sha256']+'.metadata')
        try:x=read(p)
        except (ValueError,UnicodeError):continue
        if not isinstance(x,dict) or 'source' not in x or 'output_rows' not in x or not isinstance(x['source'],dict):continue
        s=x['source'];k=(Path(s['file']).name,s['bytes'],s['footer_rows']);keys.setdefault(k,set()).add(s['skinny_schema_sha256']);reports+=1
    correction={'raw_source_key':'filename + bytes + footer_rows; derived skinny schema is not a new raw source','unique_Records_sources':len(keys),'source_footer_rows_once':sum(k[2] for k in keys),'raw_source_bytes_once':sum(k[1] for k in keys),'per_source_reports':reports,'derived_schema_versions_per_source':dict(collections.Counter(len(v) for v in keys.values())),'source_row_count_not_unique_ad_count':True}
    assert correction['unique_Records_sources']==269 and correction['source_footer_rows_once']==356449214
    save(S/'RECORDS_SOURCE_DEDUP_PUBLIC.json',correction)
    db=sqlite3.connect((V/'REUSED_VALUES_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True)
    assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
    assert not db.execute('select 1 from document where h in (select h from protected)').fetchone()
    values=read(V/'REUSE_CLOSURE_PUBLIC.json');assert sum(values['covered_contexts_by_original_state'].values())+sum(values['unattached_contexts_by_original_state'].values())==55882
    idx=sqlite3.connect((R/'integration_20261116/run001/revision003/STATUS_INDEX_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True)
    field_counts=[{'family':f,'status':s,'context_count':n} for f,s,n in idx.execute('select family,status,count(distinct h) from field group by family,status')]
    save(B/'FIELD_COVERAGE_REGISTER_PUBLIC.json',{'scope':'original seven-family fixed10k and fourteen-dimension Pro schema versions retain separate original masks; families are not additive','counts':field_counts,'unknown_not_missing_not_negative':True,'full_delivery_field_gaps_not_identified':True})
    gap={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope_units':{'delivery_Description_raw_rows':298673078,'delivery_Records_raw_rows':356449214,'canonical_US_base_ads':204774035,'existing_newer_rule_delta_ads_overlapping_base':5804936,'fine_semantic_context_union':55882,'full_delivery_unique_ads':None,'full_delivery_unique_missing_field_model_inputs':None},'fine_semantic_states':{'accepted_original_scope_values_attached':39298,'accepted_original_scope_missing_carrier':10,'saved_unverified_values_attached':6412,'saved_unverified_missing_carrier':94,'status_not_reconciled':10012,'protected_quarantined':56},'action_by_gap':{'10_original_accepted_missing_carriers':'Recover the two existing checkpoint carriers; do not rerun ads.','94_saved_missing_carriers':'Locate existing saved output by receipt; absence is not proof of never processed.','10012_status_unreconciled':'Resolve original receipts and identity bindings before assigning work.','56_quarantined':'Keep excluded from all models, training and retries.','67_multiple_PRIMARY_versions':'Retain every version, no newest-wins overwrite.','CREATED_join':'Not materialized in the value overlay; reuse existing fixed10k metadata and two identified Pro base shards.','full_delivery_unique_missing_fields':'Unresolved; never subtract unlike row/context units or quote full production from 500M assumption.'},'known_qualified_new_production_fields':0,'new_production_queue_released':False,'no_old_advertisement_recleaning':True,'paper_paused':True}
    save(B/'GAP_REGISTER_PUBLIC.json',gap)
    code=B/'code';code.mkdir(exist_ok=True)
    for name,encoded in CODE_FILES_B64.items():
        assert '/' not in name and (name.endswith('.py') or name.endswith('_PUBLIC.json'))
        p=code/name;data=base64.b64decode(encoded)
        if p.exists():assert p.read_bytes()==data
        else:p.write_bytes(data)
    code_manifest={p.name:sha(p) for p in sorted(code.iterdir()) if p.is_file()};save(B/'EXECUTED_CODE_MANIFEST_PUBLIC.json',code_manifest)
    chosen=[V/'REUSED_VALUES_PRIVATE.sqlite',V/'REUSE_CLOSURE_PUBLIC.json',V/'MULTIPLE_PRIMARY_VERSIONS_PRIVATE.json',S/'VERIFIED_DELIVERY_METADATA_PRIVATE.json',S/'MANIFEST_CONTENT_READ_PUBLIC.json',S/'SCOPE_RECONCILIATION_PUBLIC.json',S/'ALL_SHARD_ACCOUNTING_PUBLIC.json',S/'RECORDS_SOURCE_DEDUP_PUBLIC.json',B/'stage2/revision002/PRIMARY_VALIDATION_PRIVATE.json',B/'stage2/REMAINING_SOURCE_LOCATORS_PRIVATE.json',B/'FIELD_COVERAGE_REGISTER_PUBLIC.json',B/'GAP_REGISTER_PUBLIC.json',B/'EXECUTED_CODE_MANIFEST_PUBLIC.json',B/'qualification_frame_v1/FRAME_PRIVATE.json',B/'qualification_frame_v1/PROTOCOL_PUBLIC.json']+list(code.iterdir())
    chosen += [Q/n for n in ['INPUTS_PRIVATE.jsonl','PRIOR_KIMI_REFERENCES_PRIVATE.jsonl','SOURCE_LOCATORS_PRIVATE.json','PINS_PRIVATE.json','EXCLUSIONS_PRIVATE.json','PREPARATION_PUBLIC.json','SCHEMA.json','INSTRUCTIONS.md']]
    chosen += [Q/'luna'/n for n in ['cloud_qualification_luna_worker.py','BENCHMARK_CONFIG_PUBLIC.json','PROTOCOL_PUBLIC.json','SYNTHETIC_TEST_PUBLIC.json','EXECUTION_AUTHORIZATION_PUBLIC.json','WORKER_INPUT_PINS_PUBLIC.json','ADMISSION_PUBLIC.json','LAUNCH_PUBLIC.json']]
    pins={p.relative_to(B).as_posix():sha(p) for p in chosen};save(B/'CHECKPOINT_FILES_PRIVATE.json',pins);chosen.append(B/'CHECKPOINT_FILES_PRIVATE.json')
    archive=B/'REUSE_AND_QUALIFICATION_INPUT_CHECKPOINT_PRIVATE.tar.gz'
    assert not archive.exists(),'existing_archive_preserved'
    with tarfile.open(archive,'w:gz',compresslevel=1) as t:
        for p in chosen:t.add(p,arcname=p.relative_to(B).as_posix(),recursive=False)
    assert all(sha(B/rel)==d for rel,d in pins.items())
    sys.path.insert(0,str(R/'code'));from checkpoint_scope import upload,BASE;from workflow import call
    key='reuse-execution/20261116/run001/REUSE_AND_QUALIFICATION_INPUT_CHECKPOINT_PRIVATE.tar.gz';upload(archive,key)
    h=hashlib.sha256();size=0
    with call(BASE+key,'https://storage.azure.com/',headers={'x-ms-version':'2023-11-03'}) as response:
        while True:
            b=response.read(1048576)
            if not b:break
            h.update(b);size+=len(b)
    assert size==archive.stat().st_size and h.hexdigest()==sha(archive)
    live=read(Q/'luna/RUN_STATUS_PUBLIC.json');live['process_alive_observed']=Path('/proc')/str(live['pid']) in Path('/proc').iterdir()
    receipt={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'reuse_overlay_and_qualification_inputs_checkpointed','database_sha256':sha(V/'REUSED_VALUES_PRIVATE.sqlite'),'archive_blob_key':key,'archive_bytes':size,'archive_sha256':h.hexdigest(),'archive_full_readback_SHA_verified':True,'original_status_index_unchanged':True,'original_values_preserved':True,'no_protected_payloads_in_value_overlay':True,'accepted_original_contexts_reused':39298,'saved_unverified_contexts_attached':6412,'Records_source_dedup':correction,'qualification_candidate_live_snapshot':live,'stage4_locked':True,'paper_paused':True,'new_production_accepted':0,'infrastructure_incremental_invoice_cost_usd':None,'infrastructure_cost_note':'Existing VM and storage only; per-job bill not yet available. Stage1/2 each has a $25 risk allowance, not a claim of zero actual infrastructure cost.'}
    save(B/'EXECUTION_CHECKPOINT_PUBLIC.json',receipt)
    pointer={'wave':'execution_20261116/run001','status':'reuse_overlay_ready_qualification_candidate_leg_active_or_observed','database_relative_to_migration':'execution_20261116/run001/stage2/revision003/REUSED_VALUES_PRIVATE.sqlite','database_sha256':sha(V/'REUSED_VALUES_PRIVATE.sqlite'),'gap_register_relative_to_migration':'execution_20261116/run001/GAP_REGISTER_PUBLIC.json','qualification_status_relative_to_migration':'execution_20261116/run001/qualification500_v1/luna/RUN_STATUS_PUBLIC.json','paper_paused':True,'new_authorized_cap_usd':450,'stage3_cap_usd':250,'step4_released':False,'step6_released':False,'historical_root_AZURE_RESEARCH_STATE_unchanged':True}
    save(B/'AZURE_RESEARCH_STATE.json',pointer)
    dest=R/'CURRENT_EXECUTION_PUBLIC.json'
    if dest.exists():assert read(dest).get('wave')==pointer['wave'],'other_current_execution_pointer_preserved'
    save(dest,pointer)
    print(json.dumps(receipt))
if __name__=='__main__':
    try:main()
    except Exception as e:
        import traceback
        (B/'CHECKPOINT_FAILURE_PRIVATE.txt').write_text(traceback.format_exc())
        print(json.dumps({'status':'execution_checkpoint_failed_preserved','type':type(e).__name__}));raise SystemExit(2)
