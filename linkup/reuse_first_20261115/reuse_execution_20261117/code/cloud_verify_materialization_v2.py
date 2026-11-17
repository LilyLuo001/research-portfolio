"""Independent aggregate-only, bounded QA; never writes the SQLite source.

Equivalent join proof instead of a multi-million-row wide view GROUP BY:
1. Exact normalized view SQL contains DISTINCT(k,h,created,created_state).
2. variable_value.id is a unique, non-NULL single-column PRIMARY KEY (schema,
   full PRAGMA integrity_check, and non-NULL verification in the value scan).
3. A fixed v.id selects one v row and one h. Each distinct binding can therefore
   yield at most one (id,ad_key,created,created_state), even when provenance has
   multiple sources. The same exact view predicate proves nonempty v.k=ad_key.
No predicate/property is removed. A changed view, invalid PK or NULL id fails
closed. All original value checks and summaries are computed in one scan.
"""
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time

VERSION='independent-qa-v2.0.1'
WALL_SECONDS=1800
EXPECTED_VIEW="""CREATE VIEW analysis_values_with_created AS
 SELECT b.k AS ad_key,b.h AS context_fingerprint,b.created,b.created_state,v.*
 FROM variable_value v JOIN
 (SELECT DISTINCT k,h,created,created_state FROM ad_binding) b
 ON v.h=b.h AND (v.k='' OR v.k=b.k)"""


def normalized_sql(sql):
    """Compare SQL tokens, preserving every quoted byte and token boundary.

    Only ASCII whitespace between tokens and ASCII case in unquoted words are
    normalized. Quoted strings/identifiers, doubled quote escapes and comments
    remain exact; thus '' != ' ', 'A' != 'a', and SELECT a != SELECTa. Unicode
    identifier characters are not case-folded into ASCII identifiers.
    """
    sql=sql or '';tokens=[];i=0;size=len(sql)
    lowercase=str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')
    whitespace=' \t\r\n\f\v'
    def word_char(char):return char.isalnum() or char in '_$' or ord(char)>=128
    while i<size:
        char=sql[i]
        if char in whitespace:i+=1;continue
        start=i
        if char in "'\"`[":
            close=']' if char=='[' else char;i+=1
            while i<size:
                if sql[i]==close:
                    if i+1<size and sql[i+1]==close:i+=2;continue
                    i+=1;break
                i+=1
            else:raise ValueError('unterminated_quoted_sql_token')
            tokens.append(sql[start:i]);continue
        if sql.startswith('--',i):
            i=sql.find('\n',i+2)
            if i<0:i=size
            tokens.append(sql[start:i]);continue
        if sql.startswith('/*',i):
            close=sql.find('*/',i+2)
            if close<0:raise ValueError('unterminated_sql_comment')
            i=close+2;tokens.append(sql[start:i]);continue
        if word_char(char):
            i+=1
            while i<size and word_char(sql[i]):i+=1
            tokens.append(sql[start:i].translate(lowercase));continue
        operator=next((op for op in ('->>','!=','<>','<=','>=','||','->','==')
                       if sql.startswith(op,i)),None)
        if operator:tokens.append(operator);i+=len(operator)
        else:tokens.append(char);i+=1
    if tokens and tokens[-1]==';':tokens.pop()
    return tuple(tokens)


def sha(path, checkpoint=lambda:None):
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):
            checkpoint();value.update(block)
    return value.hexdigest()


def write_json(path, value):
    temporary=Path(str(path)+'.tmp')
    with temporary.open('w') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')
    os.replace(temporary,path)


def scan_properties(db, report, checkpoint=lambda phase, data:None, bound=lambda:None,
                    completed=None):
    """Only aggregate results escape this function; contexts/keys remain in RAM."""
    complete=dict(completed or {})
    def phase(name, work):
        if name not in complete:
            bound();checkpoint(name+'_started',{})
            complete[name]=work();bound();checkpoint(name+'_complete',complete[name])
        return complete[name]
    def full_integrity():
        # Fetch ALL diagnostic rows: merely checking the first row is insufficient.
        rows=db.execute('PRAGMA integrity_check').fetchall()
        return {'sqlite_integrity':rows==[('ok',)]}
    integrity=phase('integrity',full_integrity)
    assert integrity['sqlite_integrity'],'sqlite_integrity_failed'
    def structure():
        view=db.execute("SELECT sql FROM sqlite_master WHERE type='view' AND name='analysis_values_with_created'").fetchone()
        info=list(db.execute('PRAGMA table_info(variable_value)'))
        pk=[r[1] for r in info if r[5]]
        unique_id=False
        for idx in db.execute('PRAGMA index_list(variable_value)'):
            if not idx[2] or idx[4]:continue
            quoted=idx[1].replace('"','""')
            cols=[r[2] for r in db.execute('PRAGMA index_info("'+quoted+'")')]
            if cols==['id']:unique_id=True
        return {'exact_view_definition':bool(view) and normalized_sql(view[0])==normalized_sql(EXPECTED_VIEW),
                'id_single_column_primary_unique':pk==['id'] and unique_id,
                '89_dictionary_definitions':db.execute('SELECT COUNT(*) FROM dictionary_definition').fetchone()[0]==89}
    structure_checks=phase('structure',structure)
    assert all(structure_checks.values()),'analysis_schema_proof_failed'

    # These are narrow metadata tables, not model payloads. Preserve source-key
    # multiplicity in counts, but use a set for the view's DISTINCT relation.
    docs={};accept_contexts=collections.defaultdict(set);document_count=0
    excluded={r[0] for r in db.execute('SELECT h FROM context_state WHERE reuse_excluded=1')}
    runtime_bad=0
    for docid,h,k,accepted in db.execute('SELECT d,h,k,original_accepted FROM source_document'):
        document_count+=1;docs[docid]=(h,k,accepted)
        if h is not None:accept_contexts[accepted].add(h)
        runtime_bad+=h in excluded
        if document_count%25000==0:bound()
    binding_count=0;bindings=collections.defaultdict(set);created_states=collections.Counter();adkeys=set()
    for key,h,created,status in db.execute('SELECT k,h,created,created_state FROM ad_binding'):
        binding_count+=1;created_states[status]+=1
        if key is not None:adkeys.add(key)
        if h is not None:bindings[h].add((key,created,status))
    bound()
    metadata={'document_count':document_count,'binding_count':binding_count,'no_runtime_excluded_document':runtime_bad==0,
              'bound_ad_keys':len(adkeys),'bound_created_states':dict(created_states),
              'source_contexts_by_original_acceptance_nonadditive':{a:len(v) for a,v in accept_contexts.items()}}
    checkpoint('narrow_metadata_complete',metadata)

    def values():
        checks={'no_orphan_atoms':True,'no_unknown_or_invalid_promoted':True,
                'saved_documents_not_promoted':True,'no_new_semantic_acceptance':True,
                'negative_derivation_requires_complete_review':True,'variable_ids_nonnull':True,
                'metadata_json_valid':True}
        count=0;measurement=collections.Counter();workflow=collections.Counter()
        eligible_contexts=set();eligible_pairs=set()
        allowed={'known','not_mentioned','not_applicable','null_preserved'}
        # No joins, GROUP BY, temporary sort or value_json/anchor payload selection.
        sql='SELECT id,d,h,k,eligible_original_scope,measurement_state,workflow_state,metadata_json FROM variable_value'
        for vid,docid,h,k,eligible,ms,ws,payload in db.execute(sql):
            count+=1;measurement[ms]+=1;workflow[ws]+=1
            if vid is None:checks['variable_ids_nonnull']=False
            source=docs.get(docid)
            if source is None:checks['no_orphan_atoms']=False
            if eligible==1:
                # SQL NOT IN does not flag NULL. Fail closed on NULL as a strictly
                # stronger guard, while keeping all original invalid-state cases.
                if ms not in allowed:checks['no_unknown_or_invalid_promoted']=False
                if source is not None and source[2]==0:checks['saved_documents_not_promoted']=False
                if h is not None:eligible_contexts.add(h);eligible_pairs.add((h,k))
            try:
                meta=json.loads(payload)
                if not isinstance(meta,dict):raise ValueError('non_object_metadata')
            except (TypeError,ValueError):
                checks['metadata_json_valid']=False;meta={}
            accepted=meta.get('new_semantic_acceptance_granted')
            if accepted is None or accepted!=0:checks['no_new_semantic_acceptance']=False
            if eligible==1 and meta.get('complete_review_required')==1 and meta.get('complete_review_requirement_met')!=1:
                checks['negative_derivation_requires_complete_review']=False
            if count%25000==0:
                bound();checkpoint('variable_scan_progress',{'rows_checked':count})
        # Exactly the view's SQL three-valued equality: a NULL key never matches.
        eligible_ads=set()
        for h,k in eligible_pairs:
            for adkey,created,status in bindings.get(h,()):
                if adkey is not None and (k=='' or (k is not None and k==adkey)):
                    eligible_ads.add(adkey)
        return {'checks':checks,'atom_count':count,'variable_measurement_rows':dict(measurement),
                'variable_workflow_rows':dict(workflow),
                'ad_keys_with_any_original_scope_atom':len(eligible_ads),
                'contexts_with_any_original_scope_atom':len(eligible_contexts)}
    value_result=phase('variable_scan',values)
    def remaining():
        # One sequential projection replaces DISTINCT+COUNT scans of deferred.
        deferred_count=0;deferred_keys=set()
        for variable, in db.execute('SELECT variable_key FROM deferred_mapping'):
            deferred_count+=1;deferred_keys.add(variable)
            if deferred_count%50000==0:bound()
        counts={name:db.execute('SELECT COUNT(*) FROM '+name).fetchone()[0]
                for name in ['metadata_value','adapter_issue','context_state','original_mask']}
        counts['deferred_mapping']=deferred_count
        inventory=[{'physical_column':column,'rows_present':present,'nonnull_rows':nonnull}
                   for column,present,nonnull in db.execute(
                       'SELECT physical_column,rows_present,nonnull_rows FROM metadata_field_inventory ORDER BY physical_column')]
        return {'counts':counts,'deferred_variable_keys':sorted(deferred_keys),
                'metadata_field_inventory':inventory}
    other=phase('remaining_metadata',remaining)
    checks={**integrity,'document_count_matches_receipt':document_count==report['processed_documents'],
            'atom_count_matches_receipt':value_result['atom_count']==report['materialized_variable_rows'],
            '89_dictionary_definitions':structure_checks['89_dictionary_definitions'],
            'no_runtime_excluded_document':metadata['no_runtime_excluded_document'],**value_result['checks']}
    proof=checks['sqlite_integrity'] and structure_checks['exact_view_definition'] and structure_checks['id_single_column_primary_unique'] and checks['variable_ids_nonnull']
    checks['analysis_join_no_source_binding_duplication']=proof
    checks['analysis_join_respects_source_ad_key']=structure_checks['exact_view_definition']
    checks['exact_view_definition']=structure_checks['exact_view_definition']
    checks['id_single_column_primary_unique']=structure_checks['id_single_column_primary_unique']
    counts={**other['counts'],'source_document':document_count,'variable_value':value_result['atom_count'],'ad_binding':binding_count}
    summary={k:value_result[k] for k in ['variable_measurement_rows','variable_workflow_rows','ad_keys_with_any_original_scope_atom','contexts_with_any_original_scope_atom']}
    summary.update({k:metadata[k] for k in ['source_contexts_by_original_acceptance_nonadditive','bound_ad_keys','bound_created_states']})
    summary.update(deferred_variable_keys=other['deferred_variable_keys'],
                   metadata_field_inventory=other['metadata_field_inventory'],
                   never_add_atom_rows_to_ad_or_context_counts=True,some_original_scope_atom_not_all_fields_complete=True)
    return checks,counts,summary


def main():
    os.umask(0o077);started=time.monotonic()
    root=Path.home()/'migration';out=root/'reuse_execution_20261117/run001'
    receipt=out/'MATERIALIZATION_INDEPENDENT_QA_V2_PUBLIC.json'
    progress_path=out/'INDEPENDENT_QA_V2_PROGRESS_PUBLIC.json'
    events_path=out/'INDEPENDENT_QA_V2_EVENTS_PUBLIC.jsonl'
    assert not receipt.exists(),'previous_verification_preserved'
    def bound():
        if time.monotonic()-started>=WALL_SECONDS:raise TimeoutError('independent_qa_v2_wall_limit')
    report=json.loads((out/'MATERIALIZATION_PUBLIC.json').read_text())
    path=root/report['destination_relative_to_migration'];code_sha=sha(Path(__file__))
    input_sha=report['destination_sha256'];report_sha=sha(out/'MATERIALIZATION_PUBLIC.json')
    completed={};current='preflight';db=None
    def checkpoint(phase,data):
        nonlocal current
        current=phase
        if phase.endswith('_complete') and phase[:-9] in {'integrity','structure','variable_scan','remaining_metadata'}:
            completed[phase[:-9]]=data
        event={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'phase':phase,'aggregate':data,
               'elapsed_seconds':round(time.monotonic()-started,3)}
        with events_path.open('a') as stream:stream.write(json.dumps(event,ensure_ascii=False)+'\n')
        write_json(progress_path,{'version':VERSION,'code_sha256':code_sha,'input_sha256':input_sha,'materialization_report_sha256':report_sha,
                 'last_event':event,'completed_phases':completed,'source_database_written':False})
    try:
        assert report['status']=='first_reuse_materialization_complete'
        assert sha(path,bound)==input_sha,'output_sha_mismatch'
        if progress_path.exists():
            previous=json.loads(progress_path.read_text())
            if (previous.get('code_sha256'),previous.get('input_sha256'),previous.get('materialization_report_sha256'))==(code_sha,input_sha,report_sha):
                completed.update(previous.get('completed_phases',{}))
        checkpoint('source_sha_verified',{'completed_phases_reused':sorted(completed)})
        db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
        db.execute('PRAGMA query_only=ON');db.execute('PRAGMA cache_size=-262144')
        db.set_progress_handler(lambda:int(time.monotonic()-started>=WALL_SECONDS),100000)
        checks,counts,summary=scan_properties(db,report,checkpoint,bound,completed)
        db.close();db=None;bound()
        checks['output_sha_unchanged']=sha(path,bound)==input_sha
        checkpoint('final_sha_checked',{'checks':checks})
        result={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'version':VERSION,
                'status':'pass' if all(checks.values()) else 'fail_output_preserved','checks':checks,'counts':counts,'summary':summary,
                'output_sha256':input_sha,'elapsed_seconds':time.monotonic()-started,'wall_limit_seconds':WALL_SECONDS,
                'sqlite_read_cache_MiB':256,'new_model_calls':0,'new_production_accepted':0,
                'scope':'engineering_and_binding_integrity_not_semantic_requalification','private_output_remains_on_azure':True,
                'full_delivery_unique_missing_inputs':None,'wide_analysis_view_scanned':False,
                'join_equivalence_proof':'exact_view_SQL + full_integrity_check + unique_nonnull_variable_id + DISTINCT_binding_relation',
                'prior_QA_artifacts_preserved':True}
        with receipt.open('x') as stream:json.dump(result,stream,ensure_ascii=False,indent=2);stream.write('\n')
        print(json.dumps({'status':result['status'],'checks':checks,'counts':counts,'elapsed_seconds':result['elapsed_seconds'],'public_receipt_sha256':sha(receipt)}))
        assert all(checks.values()),'independent_verification_failed_output_preserved'
    except Exception as exc:
        checkpoint('failed_output_preserved',{'failed_after_phase':current,'exception_type':type(exc).__name__,
                   'new_model_calls':0,'source_database_written':False})
        print(json.dumps({'status':'qa_v2_failed_output_preserved','phase':current,'exception_type':type(exc).__name__}))
        raise
    finally:
        if db is not None:db.close()


if __name__=='__main__':main()
