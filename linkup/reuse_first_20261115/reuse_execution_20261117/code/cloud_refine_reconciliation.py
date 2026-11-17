"""Append a metadata-only correction for eventless identities; preserve v1."""
import base64
import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
import zlib


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    r=Path.home()/'migration';o=r/'reuse_execution_20261117/run001'
    oldpath=o/'RECONCILED_STATE_PRIVATE.sqlite';dest=o/'RECONCILED_STATE_V3_PRIVATE.sqlite'
    assert not dest.exists(),'refinement_exists_read_receipt'
    oldhash=sha(oldpath);source=sqlite3.connect(oldpath.as_uri()+'?mode=ro',uri=True)
    d=sqlite3.connect(dest);source.backup(d);source.close()
    index=sqlite3.connect((r/'integration_20261116/run001/revision003/STATUS_INDEX_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True)
    index.execute('PRAGMA query_only=ON')
    state=json.loads((r/'execution_20261116/run001/AZURE_RESEARCH_STATE.json').read_text())
    values=sqlite3.connect((r/state['database_relative_to_migration']).as_uri()+'?mode=ro',uri=True)
    values.execute('PRAGMA query_only=ON')
    eventless=[h for h, in index.execute("SELECT f.h FROM final_status f WHERE f.state='not_reconciled' AND NOT EXISTS(SELECT 1 FROM event e WHERE e.h=f.h)")]
    d.executemany("UPDATE context_state SET audit_resolution='identity_present_but_no_event_in_current_index' WHERE h=? AND reuse_excluded=0",[(h,) for h in eventless])
    inventory={'eventless_contexts':len(eventless),'with_ad_binding':0,'with_field_mask':0,'with_do_not_reinfer':0}
    for h in eventless:
        inventory['with_ad_binding']+=bool(index.execute('SELECT 1 FROM ad WHERE h=? LIMIT 1',(h,)).fetchone())
        inventory['with_field_mask']+=bool(index.execute('SELECT 1 FROM field WHERE h=? LIMIT 1',(h,)).fetchone())
        inventory['with_do_not_reinfer']+=bool(values.execute('SELECT 1 FROM do_not_reinfer_context WHERE h=? LIMIT 1',(h,)).fetchone())
    report=json.loads((o/'RECONCILIATION_PUBLIC.json').read_text())
    report.update(revision=3,at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
      audit_resolution_counts=dict(d.execute('SELECT audit_resolution,COUNT(*) FROM context_state GROUP BY audit_resolution')),
      eventless_identity_origins=inventory,
      correction='25 eventless contexts now have an explicit no-event label; no acceptance or source status changed',
      previous_private_state_sha256_preserved=oldhash)
    d.commit();assert d.execute('PRAGMA integrity_check').fetchone()[0]=='ok';d.close();index.close();values.close()
    assert sha(oldpath)==oldhash
    report['repair_provenance']={'prior_v2_failed_on_wrong_database_for_do_not_reinfer_view':True,'failed_v2_output_preserved':True,'correct_table_owner':'retained_values_database','no_model_or_raw_body_reads':True}
    report['private_state_relative_to_migration']=str(dest.relative_to(r));report['private_state_sha256']=sha(dest)
    # The initial structural shape probe used no raw text and exported no label
    # values, but its sample intersected the broader runtime exclusion list.
    report['preflight_boundary_correction']={'initial_structure_only_sample_runtime_overlap':report.get('preflight_shape_sample_protected_overlap'),
        'no_row_values_or_evidence_exported':True,'initial_probe_did_not_reinfer_or_review_semantics':True,
        'deny_before_payload_filter_required_for_materialization':True,'original_probe_and_correction_preserved':True}
    p=o/'RECONCILIATION_V3_PUBLIC.json';p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    b=p.read_bytes();encoded=base64.b64encode(zlib.compress(b,9)).decode();assert len(encoded)<3700
    print(json.dumps({'sha256':sha(p),'zlib_b64':encoded}))


if __name__=='__main__':main()
