"""Read-only equality of the preserved old evidence rows, no new interpretation."""
import json,sqlite3,time,signal,datetime,hashlib
from pathlib import Path

def main():
 signal.alarm(90);t=time.monotonic();R=Path.home()/'migration/evidence_readiness_20261117';old=R/'run001/EVIDENCE_READINESS_V1_PRIVATE.sqlite';new=R/'run002/EVIDENCE_READINESS_V1_PRIVATE.sqlite';rp=R/'run002/EVIDENCE_READINESS_PUBLIC.json';r=json.loads(rp.read_text());assert r['source_size_and_mtime_unchanged'] and r['prior_directory_stat_unchanged'];assert r['inherited_processed_evidence_atoms']==126000
 a=sqlite3.connect(old.as_uri()+'?mode=ro',uri=True);b=sqlite3.connect(new.as_uri()+'?mode=ro',uri=True)
 for d in [a,b]:d.execute('PRAGMA query_only=ON');d.set_progress_handler(lambda:int(time.monotonic()-t>80),10000)
 ca=a.execute('SELECT * FROM evidence_readiness ORDER BY source_rowid');cb=b.execute('SELECT * FROM evidence_readiness WHERE source_rowid<=? ORDER BY source_rowid',(r['inherited_cursor_rowid'],));n=0
 while True:
  x=ca.fetchmany(128);y=cb.fetchmany(128);assert x==y,'old_prefix_changed'
  if not x:break
  n+=len(x)
 assert n==r['inherited_processed_evidence_atoms'];added=b.execute('SELECT COUNT(*) FROM evidence_readiness WHERE source_rowid>?',(r['inherited_cursor_rowid'],)).fetchone()[0];assert added==r['newly_audited_evidence_atoms'];a.close();b.close()
 out={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'actual_old_prefix_exactly_preserved','old_rows_compared_all_columns':n,'new_rows_strictly_after_old_cursor':added,'source_report_sha256':hashlib.sha256(rp.read_bytes()).hexdigest(),'elapsed_seconds':time.monotonic()-t,'new_model_calls':0,'new_semantic_acceptance':0,'old_results_modified':False,'comparison_reads_saved_sidecar_rows_not_raw_advertisement_bodies':True}
 with (R/'run002/PREFIX_QA_PUBLIC.json').open('x') as f:json.dump(out,f,indent=2)
 print(json.dumps(out));signal.alarm(0)
if __name__=='__main__':main()
