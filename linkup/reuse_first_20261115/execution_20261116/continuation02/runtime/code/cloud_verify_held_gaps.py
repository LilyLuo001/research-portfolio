"""HEAD only for two held accepted carriers; record actual absence vs auth failure."""
import datetime,json,os,sqlite3,sys,urllib.parse,urllib.error
from pathlib import Path
R=Path.home()/'migration';B=R/'execution_20261116/run001';O=B/'continuation02';os.umask(0o077);sys.path.insert(0,str(R/'code'));from workflow import call
out=[]
for lineage in json.loads((O/'EXACT_LINEAGE_FILES_PRIVATE.json').read_text()):
 target='packet_0133' if '125737131' in lineage['prefix'] else 'packet_0080'
 db=sqlite3.connect((R/lineage['cluster']/'LEDGER_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True)
 for x in lineage['files']:
  if target not in x['path'] or not x['rel'].endswith('VALIDATED_PRIVATE.jsonl'):continue
  reason=db.execute('select reason from files where path=?',(x['path'],)).fetchone()[0]
  cfg=json.loads((R/'private'/(lineage['cluster']+'.json')).read_text());url=cfg['container_sas'].split('?',1)[0]+'/'+urllib.parse.quote(cfg['snapshot']+'/'+Path(x['root']).name+'/'+x['rel'],safe='/')
  result={'checkpoint':Path(lineage['prefix']).name,'packet':target,'migration_state':x['status'],'migration_hold_reason':reason,'expected_bytes':x['size'],'identity':'existing_VM_system_managed_identity','operation':'HEAD_exact_expected_Blob_no_content_read','new_role_requested':False}
  try:
   with call(url,'https://storage.azure.com/',method='HEAD',headers={'x-ms-version':'2023-11-03'}) as r:result.update(http_status=r.status,blob_bytes=int(r.headers.get('Content-Length',0)),blob_sha256=r.headers.get('x-ms-meta-sha256'))
  except urllib.error.HTTPError as e:result.update(http_status=e.code,azure_error_code=e.headers.get('x-ms-error-code'))
  out.append(result)
 db.close()
report={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'missing_accepted_carrier_probe':out,'SCNet_connections':0,'new_model_calls':0,'held_files_not_bypassed':True}
(O/'HELD_GAP_VERIFICATION_PUBLIC.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
