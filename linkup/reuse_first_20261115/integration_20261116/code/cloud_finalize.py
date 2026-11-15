"""Finalize metadata-only integration artifacts and verify an existing private Blob copy."""
import base64,datetime,hashlib,json,os,sqlite3,sys,tarfile
from pathlib import Path
R=Path.home()/'migration';B=R/'integration_20261116/run001';O=B/'revision003'
sys.path.insert(0,str(R/'code'));from workflow import call
from checkpoint_scope import BASE,upload

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 os.umask(0o077);report=json.loads((O/'INTEGRATION_PUBLIC.json').read_text())
 assert report['database_sha256']==sha(O/'STATUS_INDEX_PRIVATE.sqlite')
 checks={'partition':sum(report['context_state_partition'].values())==55882,'canonical_binding_unique':report['unique_canonical_ad_keys']==report['distinct_ad_context_bindings']==62414,'no_new_inference':report['new_model_calls']==report['new_production_accepted']==0,'protected_union_preserved':report['known_protected_contexts']==56}
 for rel,d in report['source_snapshot_sha256'].items():checks['unchanged:'+rel]=sha(R/rel)==d
 db=sqlite3.connect((O/'STATUS_INDEX_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True)
 checks['sqlite_integrity']=db.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
 checks['no_protected_context_in_pending']=not db.execute("SELECT 1 FROM final_status f JOIN blocked b ON b.h=f.h WHERE f.state!='quarantined' LIMIT 1").fetchone();db.close();assert all(checks.values())
 source_files=[]
 for name,encoded in FILES_B64.items():
  p=O/name;p.parent.mkdir(exist_ok=True,parents=True);p.write_bytes(base64.b64decode(encoded));source_files.append({'name':name,'sha256':sha(p),'bytes':p.stat().st_size})
 qa={'status':'pass','created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'new_model_calls':0,'new_source_ad_reads':0,'accepted_context_scope_not_full_field_known':True,'paper_new_estimation':False}
 (O/'FINAL_QA_PUBLIC.json').write_text(json.dumps(qa,indent=2)+'\n')
 (O/'CODE_AND_DOCUMENT_MANIFEST_PUBLIC.json').write_text(json.dumps(source_files,indent=2)+'\n')
 pointer={'status':'current_known_asset_integration_not_full_delivery','created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'database':str(O/'STATUS_INDEX_PRIVATE.sqlite'),'database_sha256':report['database_sha256'],'report':str(O/'INTEGRATION_PUBLIC.json'),'report_sha256':sha(O/'INTEGRATION_PUBLIC.json'),'known_unique_contexts':report['known_union_unique_contexts'],'context_state_partition':report['context_state_partition'],'full_delivery_identity_complete':False,'new_inference_admitted':False,'shared_project_tpm_ceiling':1000000,'human_review_required':False,'prior_root_research_state_preserved':True}
 (O/'AZURE_RESEARCH_STATE.json').write_text(json.dumps(pointer,indent=2)+'\n')
 public_pointer=R/'CURRENT_INTEGRATION_PUBLIC.json'
 with public_pointer.open('x') as f:json.dump(pointer,f,indent=2);f.write('\n')
 archive=B/'INTEGRATED_METADATA_INDEX_PRIVATE.tar.gz'
 chosen=[O/'STATUS_INDEX_PRIVATE.sqlite',O/'INTEGRATION_PUBLIC.json',O/'FINAL_QA_PUBLIC.json',O/'CODE_AND_DOCUMENT_MANIFEST_PUBLIC.json',O/'AZURE_RESEARCH_STATE.json',B/'SOURCE_MANIFEST_PRIVATE.json',B/'revision002/PENDING_METADATA_ONLY_PRIVATE.jsonl']+[O/x['name'] for x in source_files]
 with tarfile.open(archive,'w:gz',compresslevel=1) as tar:
  for p in chosen:tar.add(p,arcname=p.relative_to(B).as_posix(),recursive=False)
 key='reuse-integration/20261116/run001/INTEGRATED_METADATA_INDEX_PRIVATE.tar.gz';upload(archive,key)
 h=hashlib.sha256();size=0
 with call(BASE+key,'https://storage.azure.com/',headers={'x-ms-version':'2023-11-03'}) as response:
  while True:
   b=response.read(1024*1024)
   if not b:break
   size+=len(b);h.update(b)
 assert size==archive.stat().st_size and h.hexdigest()==sha(archive)
 receipt={'status':'integration_and_paper_saved_private_blob_readback_verified','completed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cloud_output_directory':str(O),'archive_blob_key':key,'archive_bytes':size,'archive_sha256':h.hexdigest(),'database_sha256':report['database_sha256'],'integration_report_sha256':sha(O/'INTEGRATION_PUBLIC.json'),'qa_sha256':sha(O/'FINAL_QA_PUBLIC.json'),'paper_sha256':sha(O/'PAPER_DRAFT_EN.md'),'context_state_partition':report['context_state_partition'],'known_unique_contexts':55882,'known_unique_ad_keys':62414,'accepted_Pro_status_contexts_projected':report['accepted_Pro_status_contexts_projected_after_recovery'],'accepted_Pro_status_contexts_still_missing':sum(g.get('status_contexts_still_unprojected',0) for g in report['metadata_gaps']),'new_model_calls':0,'new_production_accepted':0,'full_delivery_remaining_unique_model_tasks':None,'no_production_worker_started':True,'source_snapshots_unchanged':True,'blob_full_readback_verified':True}
 (O/'FINAL_EXECUTION_PUBLIC.json').write_text(json.dumps(receipt,indent=2)+'\n')
 upload(O/'FINAL_EXECUTION_PUBLIC.json','reuse-integration/20261116/run001/FINAL_EXECUTION_PUBLIC.json')
 print(json.dumps(receipt))
if __name__=='__main__':
 try:main()
 except Exception as e:
  import traceback
  (B/'FINALIZE_FAILURE_PRIVATE.txt').write_text(traceback.format_exc());print(json.dumps({'status':'finalize_failed_preserved','exception_type':type(e).__name__}));raise SystemExit(2)
