"""Locate exact lineage directories and original Astra failure metadata only."""
import collections,datetime,json,os,sqlite3
from pathlib import Path
R=Path.home()/'migration';B=R/'execution_20261116/run001';C=B/'continuation01';O=B/'continuation02';os.umask(0o077)
def read(p):return json.loads(p.read_text())
loc=read(C/'RESUME_LOCATORS_PRIVATE.json');sha={x['checkpoint_sha256'] for x in loc['missing_accepted_packets']};receipt_paths=[]
for cluster in ('kunshan','wuzhen','huazhong'):
 db=sqlite3.connect((R/cluster/'LEDGER_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True)
 for path,root,rel,size,status,h in db.execute('select path,root,rel,size,status,sha from files where sha in ('+','.join('?' for _ in sha)+')',list(sha)):
  receipt_paths.append({'cluster':cluster,'path':path,'root':root,'rel':rel,'size':size,'status':status,'sha256':h})
 db.close()
(O/'ACCEPTED_CHECKPOINT_LINEAGE_PRIVATE.json').write_text(json.dumps(receipt_paths,indent=2)+'\n')
target={x['context_sha256'] for x in loc['missing_saved_cases'] if x.get('task')=='batch052/packet_0094/0'};astrafiles=[]
for p in (R/'astra/extraction').rglob('*'):
 if p.is_file() and p.name in ('VALIDATION_PUBLIC.json','INPUT_PRIVATE.jsonl','REVIEW_PRIVATE.jsonl','ERRORS_PRIVATE.jsonl','RESPONSE_VISIBLE_PRIVATE.txt'):
  item={'relative':str(p.relative_to(R)),'bytes':p.stat().st_size}
  if p.name=='VALIDATION_PUBLIC.json':item['validation_status']=read(p).get('status')
  if p.name=='INPUT_PRIVATE.jsonl':
   rows=[json.loads(l) for l in p.read_text().splitlines() if l.strip()];item['rows']=len(rows);item['target_matches']=sum(x.get('context_sha256') in target for x in rows)
  astrafiles.append(item)
summary={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'accepted_checkpoint_paths':receipt_paths,'Astra_original_file_inventory':astrafiles,'new_model_calls':0,'input_operation':'existing_saved_input_identity_only_no_model','original_results_unchanged':True}
(O/'GAP_LINEAGE_PRIVATE.json').write_text(json.dumps(summary,indent=2)+'\n')
import base64,zlib
enc=base64.b64encode(zlib.compress(json.dumps(summary).encode(),9)).decode();assert len(enc)<3600;print(json.dumps({'aggregate_zlib_b64':enc}))
