"""Materialize versioned legacy-value projections on Azure, without inference.

Source databases remain read-only and SHA-pinned. Output is a new sidecar; no
old acceptance, unknown, PRIMARY, model schema or production queue is changed.
"""
import collections
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
from adapter import adapt_document


ROOT=Path.home()/'migration'
OUT=ROOT/'reuse_execution_20261117/run001'


def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()


def js(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)


def save(path,value):
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    os.replace(temporary,path)


def exact_family_masks(masks, *, document_key, asset, source_sha):
    """A context-wide document may not borrow an ad-specific original mask."""
    exact=collections.defaultdict(set)
    for key,family,status,mask_asset,mask_source in masks:
        same_scope=(key==document_key or (document_key!='' and key==''))
        if mask_asset==asset and mask_source==source_sha and same_scope:
            exact[family].add(status)
    return {family:next(iter(values)) if len(values)==1 else 'conflicting_original_masks'
            for family,values in exact.items()}


def main():
    os.umask(0o077)
    with (OUT/'MATERIALIZE.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        return materialize_locked()


def materialize_locked():
    os.umask(0o077);started=time.monotonic()
    destination=OUT/'LINKUP_REUSED_VARIABLES_V1_PRIVATE.sqlite'
    assert not destination.exists(),'existing_output_preserved_no_duplicate_run'
    auth=json.loads((OUT/'AUTHORIZATION_PUBLIC.json').read_text())
    assert auth['step1_execution_authorized'] and auth['model_calls_allowed_in_step1']==0
    pins=json.loads((OUT/'RUN_PINS_PUBLIC.json').read_text())
    for name,digest in pins['code_and_contract'].items():assert sha(OUT/name)==digest,'code_or_contract_changed'
    statepath=ROOT/'execution_20261116/run001/AZURE_RESEARCH_STATE.json'
    state=json.loads(statepath.read_text());source=ROOT/state['database_relative_to_migration']
    state_sha=sha(statepath);source_sha=sha(source)
    assert source_sha==state['database_sha256']==pins['source_database_sha256']
    recpath=OUT/'RECONCILED_STATE_V3_PRIVATE.sqlite';recsha=sha(recpath)
    assert recsha==pins['reconciliation_database_sha256'],'reconciliation_pin_changed'
    rec=sqlite3.connect(recpath.as_uri()+'?mode=ro',uri=True);rec.execute('PRAGMA query_only=ON')
    denied={h for h, in rec.execute('SELECT h FROM context_state WHERE reuse_excluded=1')}
    # Include every execution exclusion, even identities outside the old index.
    exclusion_path=ROOT/state['runtime_exclusions_relative_to_migration']
    exclusion_bytes=exclusion_path.read_bytes();exclusion_sha=hashlib.sha256(exclusion_bytes).hexdigest()
    assert exclusion_sha==pins['runtime_exclusions_sha256'],'runtime_exclusions_pin_changed'
    exclusions=json.loads(exclusion_bytes)
    denied.update(exclusions.get('context_sha256',[]))
    old=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True);old.execute('PRAGMA query_only=ON')
    denied.update(h for h, in old.execute('SELECT h FROM protected'))
    # do_not_reinfer_context forbids model retries, not deterministic reuse of a
    # preserved failed carrier. Only explicit reuse/content exclusions deny reads.
    placeholders=','.join('?' for _ in denied);denyargs=tuple(sorted(denied))
    filter_sql='h NOT IN ('+placeholders+')' if denied else '1=1'
    total=old.execute('SELECT COUNT(*) FROM document WHERE '+filter_sql,denyargs).fetchone()[0]
    skipped=old.execute('SELECT COUNT(*) FROM document').fetchone()[0]-total
    dictionary=json.loads((OUT/'VARIABLE_DICTIONARY_PUBLIC.json').read_text())
    valid_variables={x['variable_key']:x for x in dictionary['variables']}
    d=sqlite3.connect(destination)
    last_resource_check=[0.0]
    def within_resource_limits(force=False):
        now=time.monotonic()
        if now-started>=10800:return False
        if force or now-last_resource_check[0]>=1.0:
            last_resource_check[0]=now
            # SQLite rollback/WAL files count toward this output's disk envelope.
            size=sum(p.stat().st_size for p in [destination,Path(str(destination)+'-journal'),
                      Path(str(destination)+'-wal')] if p.exists())
            if size>=16*1024**3:return False
        return True
    def bounded_sql():return 0 if within_resource_limits() else 1
    for connection in (old,rec,d):connection.set_progress_handler(bounded_sql,100000)
    d.executescript('''PRAGMA journal_mode=DELETE; PRAGMA synchronous=FULL; PRAGMA cache_size=-32768;
      CREATE TABLE run_metadata(key TEXT PRIMARY KEY,value_json TEXT);
      CREATE TABLE context_state(h TEXT PRIMARY KEY,original_state TEXT,carrier_present INTEGER,original_protected INTEGER,reuse_excluded INTEGER,audit_resolution TEXT);
      CREATE TABLE source_document(d TEXT PRIMARY KEY,h TEXT,k TEXT,asset TEXT,source_sha TEXT,source_ordinal INTEGER,original_accepted INTEGER,mask_binding_state TEXT,adaptation_state TEXT);
      CREATE TABLE original_mask(h TEXT,k TEXT,family TEXT,status TEXT,asset TEXT,source TEXT);
      CREATE TABLE ad_binding(k TEXT,h TEXT,original_source TEXT,created TEXT,created_state TEXT,PRIMARY KEY(k,h,original_source));
      CREATE TABLE variable_value(id TEXT PRIMARY KEY,d TEXT,h TEXT,k TEXT,variable_key TEXT,source_path TEXT,item_anchor_json TEXT,dimension TEXT,value_json TEXT,value_present INTEGER,measurement_state TEXT,workflow_state TEXT,engineering_state TEXT,eligible_original_scope INTEGER,derived INTEGER,original_mask TEXT,metadata_json TEXT);
      CREATE TABLE deferred_mapping(d TEXT,h TEXT,variable_key TEXT,source_path TEXT,reason TEXT);
      CREATE TABLE adapter_issue(d TEXT,h TEXT,code TEXT,source_path TEXT,variable_key TEXT);
      CREATE TABLE metadata_value(k TEXT,variable_key TEXT,source_sha TEXT,source_ordinal INTEGER,physical_column TEXT,value_json TEXT,state TEXT);
      CREATE TABLE dictionary_definition(variable_key TEXT PRIMARY KEY,definition_json TEXT);
      CREATE TABLE metadata_field_inventory(physical_column TEXT PRIMARY KEY,rows_present INTEGER,nonnull_rows INTEGER);
    ''')
    d.executemany('INSERT INTO dictionary_definition VALUES(?,?)',[(k,js(v)) for k,v in valid_variables.items()])
    d.executemany('INSERT INTO context_state VALUES(?,?,?,?,?,?)',rec.execute(
        'SELECT h,original_state,carrier_present,original_protected,reuse_excluded,audit_resolution FROM main.context_state'))
    d.executemany('INSERT INTO original_mask VALUES(?,?,?,?,?,?)',old.execute('SELECT h,k,family,status,asset,source FROM field_mask WHERE '+filter_sql,denyargs))
    # Existing four-key metadata link is copied, never recomputed or hash-only joined.
    d.executemany('INSERT INTO ad_binding VALUES(?,?,?,?,?)',old.execute('SELECT a.k,a.h,a.source,m.created,m.status FROM ad a LEFT JOIN metadata_resolution m ON m.k=a.k'))
    d.executemany('INSERT INTO metadata_value VALUES(?,?,?,?,?,?,?)',
        ((k,'lk.time.created',source_sha,0,'metadata_resolution.created',js(created),status)
         for k,created,status in old.execute('SELECT k,created,status FROM metadata_resolution')))
    physical_aliases={
       'metadata_delete_date':'lk.time.delete','DELETE_DATE':'lk.time.delete',
       'metadata_last_checked':'lk.time.last_checked','LAST_CHECKED':'lk.time.last_checked',
       'metadata_last_updated':'lk.time.last_updated','LAST_UPDATED':'lk.time.last_updated',
       'metadata_company_id':'lk.company.vendor_id','COMPANY_ID':'lk.company.vendor_id',
       'metadata_title':'lk.job.title','TITLE':'lk.job.title',
       'metadata_state':'lk.geo','STATE':'lk.geo','COUNTRY':'lk.geo',
       'metadata_census_region':'lk.geo','CENSUS_REGION':'lk.geo',
       'OCCUPATION_MAJOR':'lk.occupation','metadata_occupation_major':'lk.occupation',
    }
    meta_present=collections.Counter();meta_nonnull=collections.Counter()
    for k,s,n,conf,payload in old.execute('SELECT k,source_sha,row_ordinal,source_conflict,payload_json FROM metadata_evidence'):
        values=json.loads(payload)
        for col,value in values.items():
            meta_present[col]+=1;meta_nonnull[col]+=value is not None
            if col in physical_aliases:
                d.execute('INSERT INTO metadata_value VALUES(?,?,?,?,?,?,?)',(k,physical_aliases[col],s,n,col,js(value),'source_flagged_conflict' if conf else 'null_preserved' if value is None else 'retained_source_value'))
    d.executemany('INSERT INTO metadata_field_inventory VALUES(?,?,?)',[(c,n,meta_nonnull[c]) for c,n in sorted(meta_present.items())])
    d.commit()
    counters=collections.Counter();assets=collections.Counter();last_h=None;masks=[]
    def progress(status):
        save(OUT/'RUN_STATUS_PUBLIC.json',{'status':status,'pid':os.getpid(),'eligible_source_documents':total,'excluded_source_documents':skipped,
          'processed_documents':counters['processed_documents'],'materialized_variable_rows':counters['variable_rows'],
          'new_model_calls':0,'new_production_accepted':0,'elapsed_seconds':time.monotonic()-started,
          'updated_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
    progress('materializing_existing_values')
    for docid,h,k,asset,src,n,accepted,raw in old.execute('SELECT d,h,k,asset,source_sha,source_ordinal,original_accepted,document_json FROM document WHERE '+filter_sql+' ORDER BY h,d',denyargs):
        assert h not in denied,'deny_before_payload_projection_failed'
        assert within_resource_limits(),'bounded_resource_limit_reached_output_preserved'
        if h!=last_h:
            masks=list(old.execute('SELECT k,family,status,asset,source FROM field_mask WHERE h=?',(h,)));last_h=h
        final_masks=exact_family_masks(masks,document_key=k,asset=asset,source_sha=src)
        binding='exact_source_masks' if final_masks else 'no_exact_external_mask'
        try:
            doc=json.loads(raw)
            result=adapt_document(doc,asset=asset,source_sha=src,source_ordinal=n,context_sha256=h,
                original_accepted=bool(accepted),family_masks=final_masks,
                source_versions={'retained_source_database_sha256':source_sha,'dictionary':'1.0.0','source_measurement_version':'retained_original_not_upgraded'})
        except (ValueError,TypeError,KeyError):
            result={'rows':[],'issues':[{'code':'adapter_input_rejected_preserved_source','source_path':''}],'deferred':[]}
        adaptation='adapted_with_explicit_issues' if result['issues'] else 'adapted'
        d.execute('INSERT INTO source_document VALUES(?,?,?,?,?,?,?,?,?)',(docid,h,k,asset,src,n,accepted,binding,adaptation))
        for i,row in enumerate(result['rows']):
            assert row['variable_key'] in valid_variables,'adapter_variable_not_in_dictionary'
            assert not row['new_semantic_acceptance_granted'],'new_acceptance_forbidden'
            identifier=hashlib.sha256((docid+'\0'+str(i)).encode()).hexdigest()
            keep={key:row[key] for key in ['definition_version','source_family','dependency_masks','effective_mask','effective_dependency_masks','route_qualification','new_semantic_acceptance_granted','supporting_item_anchors','complete_review_required','complete_review_requirement_met'] if key in row}
            d.execute('INSERT INTO variable_value VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(
                identifier,docid,h,k,row['variable_key'],row['source_path'],js(row.get('item_anchor')),row.get('dimension'),js(row['value']),int(row['value_present']),
                row['measurement_state'],row['workflow_state'],row['engineering_state'],int(row['eligible_original_scope']),int(row['deterministic_derivation']),row['original_mask'],js(keep)))
            counters['variable_rows']+=1
        for item in result['deferred']:
            assert item['variable_key'] in valid_variables,'deferred_variable_not_in_dictionary'
            d.execute('INSERT INTO deferred_mapping VALUES(?,?,?,?,?)',(docid,h,item['variable_key'],item['source_path'],item['reason']))
        for item in result['issues']:
            d.execute('INSERT INTO adapter_issue VALUES(?,?,?,?,?)',(docid,h,item['code'],item.get('source_path',''),item.get('variable_key')))
        counters['processed_documents']+=1;assets[asset]+=1
        if counters['processed_documents']%500==0:
            d.commit();progress('materializing_existing_values')
            assert within_resource_limits(force=True),'bounded_resource_limit_reached_output_preserved'
    assert counters['processed_documents']==total,'source_document_conservation_failed'
    d.commit();progress('building_coverage_and_integrity_checks')
    d.executescript('''CREATE INDEX variable_context ON variable_value(h,variable_key);
       CREATE INDEX variable_key ON variable_value(variable_key);
       CREATE INDEX source_doc_context ON source_document(h);
       CREATE INDEX bindings_context ON ad_binding(h);
       CREATE INDEX metadata_ad ON metadata_value(k,variable_key);
       CREATE VIEW analysis_values_with_created AS
       SELECT b.k AS ad_key,b.h AS context_fingerprint,b.created,b.created_state,v.*
       FROM variable_value v JOIN
         (SELECT DISTINCT k,h,created,created_state FROM ad_binding) b
         ON v.h=b.h AND (v.k='' OR v.k=b.k);
    ''')
    eligible_contexts=d.execute('SELECT COUNT(DISTINCT h) FROM source_document').fetchone()[0]
    coverage=[]
    for variable,definition in valid_variables.items():
        n,c,known,unknown,pending=d.execute("""SELECT COUNT(*),COUNT(DISTINCT h),
          COUNT(DISTINCT CASE WHEN eligible_original_scope=1 AND value_present=1 AND measurement_state IN ('known','not_mentioned','not_applicable') THEN h END),
          COUNT(DISTINCT CASE WHEN measurement_state IN ('unknown','unknown_or_conflict','partial') THEN h END),
          COUNT(DISTINCT CASE WHEN workflow_state='saved_unverified' THEN h END)
          FROM variable_value WHERE variable_key=?""",(variable,)).fetchone()
        m=d.execute("SELECT COUNT(DISTINCT k) FROM metadata_value WHERE variable_key=? AND state IN ('matched_consistent','retained_source_value') AND value_json!='null'",(variable,)).fetchone()[0]
        coverage.append({'variable_key':variable,'unit':definition['unit'],'source_availability':definition['availability_code'],
          'projected_atom_rows':n,'contexts_with_any_projection':c,'contexts_with_some_original_scope_known_atom':known,
          'contexts_with_unknown_or_partial_atom':unknown,'contexts_with_saved_unverified_atom':pending,
          'ad_keys_with_nonnull_structural_source_value':m,
          'eligible_carrier_contexts_without_projection':eligible_contexts-c if variable.startswith(('lk.exp.','lk.duty.','lk.entry.','lk.tech.','lk.qual.','lk.task.')) else None,
          'without_projection_is_not_proven_missing_requirement':True,'some_known_atom_is_not_complete_variable_coverage':True,
          'full_delivery_missing_unique_inputs':None})
    issue_counts=[{'code':code,'rows':n} for code,n in d.execute('SELECT code,COUNT(*) FROM adapter_issue GROUP BY code')]
    mask_counts=[{'asset':a,'binding':b,'documents':n} for a,b,n in d.execute('SELECT asset,mask_binding_state,COUNT(*) FROM source_document GROUP BY asset,mask_binding_state')]
    checks={'source_document_conservation':counters['processed_documents']==total,
      'all_89_definitions_preserved':len(valid_variables)==89,
      'protected_projection_count_zero':not any(d.execute('SELECT 1 FROM source_document WHERE h=? LIMIT 1',(h,)).fetchone() for h in denied),
      'all_original_ad_bindings_preserved':d.execute('SELECT COUNT(*) FROM ad_binding').fetchone()[0]==old.execute('SELECT COUNT(*) FROM ad').fetchone()[0],
      'one_created_state_per_ad_context':not d.execute('''SELECT 1 FROM
          (SELECT DISTINCT k,h,created,created_state FROM ad_binding)
          GROUP BY k,h HAVING COUNT(*)>1 LIMIT 1''').fetchone(),
      'existing_created_join_not_recomputed':True,'no_original_schema_or_ledger_update':True,
      'sqlite_integrity':d.execute('PRAGMA integrity_check').fetchone()[0]=='ok'}
    assert all(checks.values()),'materialization_checks_failed'
    for k,v in {'dictionary_version':'1.0.0','source_database_sha256':source_sha,'source_database_relative_to_migration':str(source.relative_to(ROOT)),
       'reconciliation_sha256':recsha,'time_proxy_notice':'CREATED is first-observed posting-time proxy; changes are not automatically AI causal effects.',
       'scope':'existing_fine_semantic_ledger_only_full_delivery_gaps_unresolved'}.items():d.execute('INSERT INTO run_metadata VALUES(?,?)',(k,js(v)))
    d.commit();d.close();rec.close();old.close()
    checks['source_database_SHA_unchanged']=sha(source)==source_sha
    checks['source_state_SHA_unchanged']=sha(statepath)==state_sha
    checks['reconciliation_SHA_unchanged']=sha(recpath)==recsha
    checks['runtime_exclusions_SHA_unchanged']=sha(exclusion_path)==exclusion_sha
    assert all(checks.values()),'source_preservation_check_failed'
    save(OUT/'VARIABLE_COVERAGE_PUBLIC.json',{'dictionary_version':'1.0.0','scope':'existing_fine_semantic_carriers_and_retained_metadata',
         'eligible_carrier_contexts':eligible_contexts,'counts_across_states_and_variables_not_additive':True,'variables':coverage})
    report={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'first_reuse_materialization_complete',
       'source_database_sha256':source_sha,'destination_relative_to_migration':str(destination.relative_to(ROOT)),
       'destination_sha256':sha(destination),'destination_bytes':destination.stat().st_size,
       'dictionary_version':'1.0.0','processed_documents':counters['processed_documents'],'excluded_source_documents':skipped,
       'eligible_carrier_contexts':eligible_contexts,'materialized_variable_rows':counters['variable_rows'],'source_documents_by_asset':dict(assets),
       'mask_binding_counts':mask_counts,'adapter_issue_counts':issue_counts,'checks':checks,'elapsed_seconds':time.monotonic()-started,
       'new_model_calls':0,'new_production_accepted':0,'raw_advertisement_files_read':0,'full_delivery_missing_unique_inputs':None,
       'not_all_variables_complete_for_all_contexts':True,'no_semantic_requalification_from_adapter':True}
    save(OUT/'MATERIALIZATION_PUBLIC.json',report)
    save(OUT/'OUTPUT_SHA256_PUBLIC.json',{p.name:sha(p) for p in [destination,OUT/'VARIABLE_COVERAGE_PUBLIC.json',OUT/'MATERIALIZATION_PUBLIC.json']})
    progress('first_reuse_materialization_complete')


if __name__=='__main__':
    try:main()
    except Exception as exc:
        import traceback
        (OUT/'MATERIALIZATION_FAILURE_PRIVATE.txt').write_text(traceback.format_exc())
        save(OUT/'FAILURE_PUBLIC.json',{'status':'materialization_failed_output_preserved','exception_type':type(exc).__name__,
             'new_model_calls':0,'old_sources_not_written':True})
        raise SystemExit(2)
