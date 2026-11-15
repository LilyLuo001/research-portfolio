"""Targeted existing locator inventory for 16 missing carriers; no source-text scan."""
import collections,datetime,hashlib,json,os,sqlite3
from pathlib import Path
R=Path.home()/'migration';B=R/'execution_20261116/run001';C=B/'continuation01';O=B/'continuation02';O.mkdir(exist_ok=True);os.umask(0o077)
def read(p):return json.loads(p.read_text())
old=read(C/'RESUME_LOCATORS_PRIVATE.json');idx=sqlite3.connect((R/'integration_20261116/run001/revision003/STATUS_INDEX_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True)
unbound=read(C/'joined_revision003/UNBOUND_PRO_REMAINDER_PRIVATE.json')
# Only field names and paths from already established bounded locators leave cloud.
accepted=[]
for x in old['missing_accepted_packets']:
 checkpoint=read(R/'integration_20261116/run001/metadata_cache'/(x['checkpoint_sha256']+'.metadata'))
 accepted.append({'packet':x['packet'],'checkpoint_top_keys':list(checkpoint),'checkpoint_path_fields':{k:v for k,v in checkpoint.items() if isinstance(v,str) and ('/' in v) and len(v)<600}})
summary={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'missing_accepted_packet_locator_metadata':accepted,'unbound_shape':type(unbound).__name__,'unbound_field_names':sorted({k for x in unbound for k in x}) if isinstance(unbound,list) else list(unbound),'unreconciled_event_groups':[{'asset':a,'state':s,'n':n} for a,s,n in idx.execute("select e.asset,e.state,count(distinct e.h) from event e join final_status f on e.h=f.h where f.state='not_reconciled' group by e.asset,e.state")],'no_raw_text_scan':True,'new_model_calls':0}
# Candidate alternate files are located by already known packet basenames, not raw source text.
locators=[]
for cluster in ('kunshan','wuzhen','huazhong'):
 db=sqlite3.connect((R/cluster/'LEDGER_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True)
 for path,root,rel,size,status,sha in db.execute("select path,root,rel,size,status,sha from files where (path like '%packet_0080%' or path like '%packet_0133%') and (path like '%validated%' or path like '%review%' or path like '%PRIMARY%')"):
  if 'batch035' not in path.lower():locators.append({'cluster':cluster,'path':path,'root':root,'rel':rel,'size':size,'status':status,'sha256':sha})
 db.close()
(O/'TARGETED_ALTERNATE_LOCATORS_PRIVATE.json').write_text(json.dumps(locators,indent=2)+'\n')
summary['alternate_filename_locator_count']=len(locators)
summary['alternate_locator_total_bytes']=sum(x['size'] for x in locators)
summary['old_Astra_run_metadata_paths']=[str(p.relative_to(R)) for p in (R/'astra').glob('*/*PUBLIC.json') if p.is_file()]
(O/'TARGETED_GAP_INVENTORY_PRIVATE.json').write_text(json.dumps(summary,indent=2)+'\n')
import base64,zlib
enc=base64.b64encode(zlib.compress(json.dumps(summary).encode(),9)).decode();assert len(enc)<3600
print(json.dumps({'aggregate_zlib_b64':enc}))
