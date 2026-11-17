"""Independent aggregate-only checks of the completed new sidecar on Azure."""
import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
import time


def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024*1024),b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    started=time.monotonic()
    root=Path.home()/'migration'
    out=root/'reuse_execution_20261117/run001'
    receipt=out/'MATERIALIZATION_INDEPENDENT_QA_PUBLIC.json'
    assert not receipt.exists(),'previous_verification_preserved'
    report=json.loads((out/'MATERIALIZATION_PUBLIC.json').read_text())
    path=root/report['destination_relative_to_migration']
    assert report['status']=='first_reuse_materialization_complete'
    assert sha(path)==report['destination_sha256']
    d=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
    d.execute('PRAGMA query_only=ON')
    d.set_progress_handler(lambda: int(time.monotonic()-started>900),100000)
    scalar=lambda sql: d.execute(sql).fetchone()[0]
    checks={
        'sqlite_integrity':scalar('PRAGMA integrity_check')=='ok',
        'document_count_matches_receipt':scalar('SELECT COUNT(*) FROM source_document')==report['processed_documents'],
        'atom_count_matches_receipt':scalar('SELECT COUNT(*) FROM variable_value')==report['materialized_variable_rows'],
        '89_dictionary_definitions':scalar('SELECT COUNT(*) FROM dictionary_definition')==89,
        'no_runtime_excluded_document':scalar('SELECT COUNT(*) FROM source_document d JOIN context_state c ON c.h=d.h WHERE c.reuse_excluded=1')==0,
        'no_orphan_atoms':scalar('SELECT COUNT(*) FROM variable_value v LEFT JOIN source_document d ON v.d=d.d WHERE d.d IS NULL')==0,
        'no_unknown_or_invalid_promoted':scalar("SELECT COUNT(*) FROM variable_value WHERE eligible_original_scope=1 AND measurement_state NOT IN ('known','not_mentioned','not_applicable','null_preserved')")==0,
        'saved_documents_not_promoted':scalar('SELECT COUNT(*) FROM variable_value v JOIN source_document d ON v.d=d.d WHERE v.eligible_original_scope=1 AND d.original_accepted=0')==0,
        'no_new_semantic_acceptance':scalar("SELECT COUNT(*) FROM variable_value WHERE COALESCE(json_extract(metadata_json,'$.new_semantic_acceptance_granted'),1)!=0")==0,
        'negative_derivation_requires_complete_review':scalar("SELECT COUNT(*) FROM variable_value WHERE eligible_original_scope=1 AND json_extract(metadata_json,'$.complete_review_required')=1 AND COALESCE(json_extract(metadata_json,'$.complete_review_requirement_met'),0)!=1")==0,
        'analysis_join_no_source_binding_duplication':scalar('SELECT COUNT(*) FROM (SELECT id,ad_key,created,created_state,COUNT(*) n FROM analysis_values_with_created GROUP BY id,ad_key,created,created_state HAVING n>1)')==0,
        'analysis_join_respects_source_ad_key':scalar("SELECT COUNT(*) FROM analysis_values_with_created WHERE k!='' AND k!=ad_key")==0,
    }
    counts={name:scalar('SELECT COUNT(*) FROM '+name) for name in
        ['source_document','variable_value','metadata_value','ad_binding','deferred_mapping','adapter_issue','context_state','original_mask']}
    summary={
       'variable_measurement_rows':dict(d.execute('SELECT measurement_state,COUNT(*) FROM variable_value GROUP BY measurement_state')),
       'variable_workflow_rows':dict(d.execute('SELECT workflow_state,COUNT(*) FROM variable_value GROUP BY workflow_state')),
       'source_contexts_by_original_acceptance_nonadditive':dict(d.execute('SELECT original_accepted,COUNT(DISTINCT h) FROM source_document GROUP BY original_accepted')),
       'bound_ad_keys':scalar('SELECT COUNT(DISTINCT k) FROM ad_binding'),
       'bound_created_states':dict(d.execute('SELECT created_state,COUNT(*) FROM ad_binding GROUP BY created_state')),
       'ad_keys_with_any_original_scope_atom':scalar('SELECT COUNT(DISTINCT ad_key) FROM analysis_values_with_created WHERE eligible_original_scope=1'),
       'contexts_with_any_original_scope_atom':scalar('SELECT COUNT(DISTINCT h) FROM variable_value WHERE eligible_original_scope=1'),
       'deferred_variable_keys':[r[0] for r in d.execute('SELECT DISTINCT variable_key FROM deferred_mapping ORDER BY variable_key')],
       'never_add_atom_rows_to_ad_or_context_counts':True,
       'some_original_scope_atom_not_all_fields_complete':True,
    }
    d.close()
    checks['output_sha_unchanged']=sha(path)==report['destination_sha256']
    result={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'status':'pass' if all(checks.values()) else 'fail_output_preserved',
       'checks':checks,'counts':counts,'summary':summary,'output_sha256':report['destination_sha256'],
       'elapsed_seconds':time.monotonic()-started,'new_model_calls':0,'new_production_accepted':0,
       'scope':'engineering_and_binding_integrity_not_semantic_requalification',
       'private_output_remains_on_azure':True,'full_delivery_unique_missing_inputs':None}
    receipt.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'checks':checks,'counts':counts,'elapsed_seconds':result['elapsed_seconds'],
          'public_receipt_sha256':sha(receipt)}))
    assert all(checks.values()),'independent_verification_failed_output_preserved'


if __name__=='__main__':
    main()
