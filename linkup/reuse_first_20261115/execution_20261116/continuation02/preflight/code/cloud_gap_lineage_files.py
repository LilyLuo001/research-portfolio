"""Inspect only ledger entries underneath the two known checkpoint directories."""
import collections,json,os,sqlite3
from pathlib import Path
R=Path.home()/'migration';B=R/'execution_20261116/run001';O=B/'continuation02';os.umask(0o077)
loc=json.loads((O/'ACCEPTED_CHECKPOINT_LINEAGE_PRIVATE.json').read_text());out=[]
for x in loc:
 db=sqlite3.connect((R/x['cluster']/'LEDGER_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True)
 prefix=str(Path(x['path']).parent.parent)+'/'
 rows=[dict(zip(['path','root','rel','size','status','sha256'],r)) for r in db.execute('select path,root,rel,size,status,sha from files where path like ?', (prefix+'%',))]
 out.append({'cluster':x['cluster'],'checkpoint_sha256':x['sha256'],'prefix':prefix,'files':rows});db.close()
(O/'EXACT_LINEAGE_FILES_PRIVATE.json').write_text(json.dumps(out,indent=2)+'\n')
summary=[]
for x in out:
 wanted='packet_0133' if '125737131' in x['prefix'] else 'packet_0080'
 summary.append({'checkpoint':Path(x['prefix']).name,'files':len(x['files']),'status_counts':dict(collections.Counter(y['status'] for y in x['files'])),'matching_packet_files':[{'rel':y['rel'],'status':y['status'],'size':y['size'],'sha256':y['sha256']} for y in x['files'] if wanted in y['path']],'file_suffix_counts':dict(collections.Counter(Path(y['path']).suffix for y in x['files']))})
print(json.dumps({'lineages':summary,'new_model_calls':0}))
