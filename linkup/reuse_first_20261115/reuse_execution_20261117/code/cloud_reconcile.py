"""Incremental audit of existing state and value indexes, never inference admission."""
import base64
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
import zlib


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    os.umask(0o077);start=time.monotonic()
    r=Path.home()/'migration';o=r/'reuse_execution_20261117/run001'
    assert not (o/'RECONCILIATION_PUBLIC.json').exists(),'existing_reconciliation_preserved'
    state_path=r/'execution_20261116/run001/AZURE_RESEARCH_STATE.json'
    state=json.loads(state_path.read_text());vpath=r/state['database_relative_to_migration']
    ipath=r/'integration_20261116/run001/revision003/STATUS_INDEX_PRIVATE.sqlite'
    source_sha={'values':sha(vpath),'status':sha(ipath),'state':sha(state_path)}
    assert source_sha['values']==state['database_sha256']
    assert source_sha['status']=='0344e94b9f2b75af74652a2f517c4e5c535d8090e1db62eec84b55afced1523a'
    c=sqlite3.connect(ipath.as_uri()+'?mode=ro',uri=True);c.execute('PRAGMA query_only=ON')
    c.execute('ATTACH DATABASE ? AS old_values',(vpath.as_uri()+'?mode=ro',))
    schema={name:[x[1] for x in c.execute('PRAGMA table_info('+name+')')] for name in ['event','provenance','final_status','do_not_reinfer_context']}
    required={'event':{'h','asset','state','source','detail'},'provenance':{'sha','metadata'},'final_status':{'h','state'}}
    assert all(v<=set(schema[k]) for k,v in required.items())
    all_states=dict(c.execute('SELECT state,COUNT(*) FROM final_status GROUP BY state'))
    event_groups=[]
    # Group only fixed metadata enums; free detail strings remain private.
    for a,s,n in c.execute("SELECT e.asset,e.state,COUNT(DISTINCT e.h) FROM event e JOIN final_status f ON f.h=e.h WHERE f.state='not_reconciled' GROUP BY e.asset,e.state"):
        event_groups.append({'asset':a,'source_state':s,'contexts_non_additive':n})
    partitions=[]
    for a,b,d,e,n in c.execute("""WITH u AS (SELECT h FROM final_status WHERE state='not_reconciled')
      SELECT EXISTS(SELECT 1 FROM event x WHERE x.h=u.h AND x.asset='Pro'),
      EXISTS(SELECT 1 FROM event x WHERE x.h=u.h AND x.asset='Azure_parent'),
      EXISTS(SELECT 1 FROM event x WHERE x.h=u.h AND x.asset='fixed10k'),
      EXISTS(SELECT 1 FROM event x WHERE x.h=u.h),COUNT(*) FROM u GROUP BY 1,2,3,4"""):
        partitions.append({'has_Pro':bool(a),'has_Azure_parent':bool(b),'has_fixed10k':bool(d),'has_any_event':bool(e),'contexts':n})
    missing=dict(c.execute('SELECT f.state,COUNT(*) FROM final_status f WHERE NOT EXISTS(SELECT 1 FROM old_values.document d WHERE d.h=f.h) GROUP BY f.state'))
    runtime_path=r/state['runtime_exclusions_relative_to_migration']
    runtime=json.loads(runtime_path.read_text());protected={h for h, in c.execute('SELECT h FROM blocked')}
    denied=protected|set(runtime.get('context_sha256',[]))
    runtime_intersection=collections.Counter()
    for h,s in c.execute('SELECT h,state FROM final_status'):
        if h in denied:runtime_intersection[s]+=1
    pfile=o/'RECONCILED_STATE_PRIVATE.sqlite';assert not pfile.exists()
    d=sqlite3.connect(pfile)
    d.executescript('''PRAGMA journal_mode=DELETE; PRAGMA synchronous=FULL;
      CREATE TABLE context_state(h TEXT PRIMARY KEY, original_state TEXT, carrier_present INTEGER, original_protected INTEGER, reuse_excluded INTEGER, audit_resolution TEXT);
      CREATE TABLE unresolved_origin(h TEXT,asset TEXT,source_state TEXT,source_sha TEXT,detail TEXT,provenance_present INTEGER);
      CREATE INDEX origin_h ON unresolved_origin(h);
      CREATE TABLE missing_carrier_origin(h TEXT,asset TEXT,source_state TEXT,source_sha TEXT,detail TEXT);
    ''')
    for h,s,has_value in c.execute('SELECT f.h,f.state,EXISTS(SELECT 1 FROM old_values.document d WHERE d.h=f.h) FROM final_status f'):
        resolution=('protected_not_reopened' if h in denied else 'existing_carrier_available' if has_value else
                    'held_carrier_previously_confirmed' if s=='accepted_original_scope' else
                    'saved_carrier_or_binding_still_missing' if s=='saved_unverified' else
                    'event_provenance_located_acceptance_unresolved')
        d.execute('INSERT INTO context_state VALUES(?,?,?,?,?,?)',(h,s,has_value,int(h in protected),int(h in denied),resolution))
    d.executemany('INSERT INTO unresolved_origin VALUES(?,?,?,?,?,?)',c.execute("SELECT DISTINCT e.h,e.asset,e.state,e.source,e.detail,EXISTS(SELECT 1 FROM provenance p WHERE p.sha=e.source) FROM event e JOIN final_status f ON f.h=e.h WHERE f.state='not_reconciled'"))
    d.executemany('INSERT INTO missing_carrier_origin VALUES(?,?,?,?,?)',c.execute("SELECT e.h,e.asset,e.state,e.source,e.detail FROM event e JOIN final_status f ON f.h=e.h WHERE f.state='saved_unverified' AND NOT EXISTS(SELECT 1 FROM old_values.document d WHERE d.h=f.h)"))
    statuses=dict(d.execute('SELECT audit_resolution,COUNT(*) FROM context_state GROUP BY audit_resolution'))
    located=d.execute('SELECT COUNT(DISTINCT source_sha) FROM unresolved_origin WHERE provenance_present=1').fetchone()[0]
    unlocated=d.execute('SELECT COUNT(DISTINCT source_sha) FROM unresolved_origin WHERE provenance_present=0').fetchone()[0]
    assert sum(x['contexts'] for x in partitions)==all_states['not_reconciled']
    assert sum(statuses.values())==sum(all_states.values())
    assert d.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    d.commit();d.close();c.close()
    assert source_sha=={'values':sha(vpath),'status':sha(ipath),'state':sha(state_path)},'original_source_changed'
    compact_file=o/'PREFLIGHT_COMPACT_PUBLIC.json'
    sample_overlap=json.loads(compact_file.read_text()).get('preflight_shape_sample_protected_overlap') if compact_file.exists() else None
    report={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'existing_indexes_reconciled_with_explicit_unresolved_acceptance',
        'scope':'existing_55882_context_ledger_not_full_delivery','source_sha256':source_sha,'actual_index_schema':schema,
        'original_state_counts':all_states,'unreconciled_disjoint_origins':partitions,'unreconciled_source_states':event_groups,
        'unattached_carriers_by_original_state':missing,'audit_resolution_counts':statuses,
        'unresolved_receipt_sources_with_provenance':located,'unresolved_receipt_sources_without_provenance':unlocated,
        'runtime_exclusion_contexts':len(runtime.get('context_sha256',[])),'exclusion_union':len(denied),'exclusion_intersection_original_states':dict(runtime_intersection),
        'preflight_shape_sample_protected_overlap':sample_overlap,
        'missing_accepted_carrier_resolution':'10 contexts already traced to 2 held credential-content-review files; no content or HEAD retry',
        'missing_saved_carrier_resolution':'5 Pro binding/carrier cases and 1 Astra failure locator retained; no proof of unread work',
        'original_state_mutations':0,'newly_admitted_unprocessed_contexts':0,'new_model_calls':0,'held_payload_reads':0,
        'new_source_body_scans':0,'full_delivery_missing_unique_inputs':None,
        'private_state_relative_to_migration':str(pfile.relative_to(r)),'private_state_sha256':sha(pfile),
        'original_databases_unchanged':True,'elapsed_seconds':time.monotonic()-start}
    (o/'RECONCILIATION_PUBLIC.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    b=(o/'RECONCILIATION_PUBLIC.json').read_bytes();x=base64.b64encode(zlib.compress(b,9)).decode();assert len(x)<3700
    print(json.dumps({'sha256':hashlib.sha256(b).hexdigest(),'zlib_b64':x}))


if __name__=='__main__':main()
