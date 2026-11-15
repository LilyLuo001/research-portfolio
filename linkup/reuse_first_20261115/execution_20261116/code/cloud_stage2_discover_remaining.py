import json,sqlite3,re,collections,hashlib,datetime,base64,zlib
from pathlib import Path
R=Path.home()/'migration';B=R/'integration_20261116/run001';O=R/'execution_20261116/run001/stage2';c=sqlite3.connect((B/'revision003/STATUS_INDEX_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True)
states=dict(c.execute('select h,state from final_status'));mapping={};preps={};metas=json.loads((B/'DISCOVERY_PRIVATE.json').read_text())['metadata_inventory']
for m in metas:
 p=B/'metadata_cache'/(m['sha256']+'.metadata')
 if not p.exists():continue
 if m['rel'].endswith('PACKET_MANIFEST_PRIVATE.jsonl'):
  b=re.search(r'batch\d+',m['path']).group(0)
  for i,line in enumerate(p.open()):
   x=json.loads(line);mapping[x['context_sha256']]={'batch':b,'packet':f'packet_{i//5+1:04d}','ordinal':i%5,'manifest_sha256':m['sha256']}
 elif m['rel'].endswith('PACKET_PREPARATION_PUBLIC.json'):
  x=json.loads(p.read_bytes());mh=x.get('packet_manifest_sha256') or x.get('output_sha256',{}).get('packet_manifest_private')
  if mh:preps[mh]={x['name'][:-6]:x['sha256'] for x in x.get('packet_files',[])}
wanted={(x['batch'],x['packet']) for h,x in mapping.items() if states.get(h) in ['saved_unverified','not_reconciled']};found={}
for cluster in ['kunshan','wuzhen','huazhong']:
 d=sqlite3.connect((R/cluster/'LEDGER_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True)
 for path,root,rel,size,status,sha in d.execute("select path,root,rel,size,status,sha from files where path like '%corpus_pro_review_20261026%' and rel like '%PRIMARY.jsonl'"):
  if 'batch035' in path.lower() or status!='verified':continue
  match=re.search(r'(batch\d+)_?(packet_\d{4})_PRIMARY\.jsonl$',path)
  if match and match.groups() in wanted:found.setdefault(sha,{'cluster':cluster,'path':path,'root':root,'rel':rel,'size':size,'status':status,'sha256':sha,'batch':match.group(1),'packet':match.group(2)})
 d.close()
plan={'mapping':mapping,'primary_files':list(found.values()),'input_packet_sha_by_manifest':preps};(O/'REMAINING_SOURCE_LOCATORS_PRIVATE.json').write_text(json.dumps(plan,indent=2)+'\n')
counts=collections.Counter();pairs={(m['batch'],m['packet']) for m in found.values()}
for h,x in mapping.items():
 if states[h] in ['saved_unverified','not_reconciled']:counts[(states[h],'primary_located' if (x['batch'],x['packet']) in pairs else 'no_primary_in_current_migration_ledger')]+=1
# Accepted Astra carrier provenance, not semantic content.
a=json.loads((R/'astra/extraction/STATE_PRIVATE.json').read_text());afiles=[]
for val in a['accepted'].values():
 run=R/'astra/extraction/runs'/val['run'];matches=[]
 for p in run.glob('*'):
  if p.is_file() and p.stat().st_size<4000000 and p.name.endswith('.jsonl'):
   if hashlib.sha256(p.read_bytes()).hexdigest()==val['sha256']:matches.append(str(p))
 afiles.append({'context_sha256':val['context_sha256'],'expected_sha256':val['sha256'],'matching_paths':matches,'run_dir_exists':run.exists()})
(O/'ASTRA_CARRIERS_PRIVATE.json').write_text(json.dumps(afiles,indent=2)+'\n')
r={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'remaining_Pro_context_status_locator_counts':[{'state':s,'carrier':k,'contexts':n} for (s,k),n in sorted(counts.items())],'source_primary_files_located':len(found),'source_primary_total_bytes':sum(m['size'] for m in found.values()),'source_primary_max_bytes':max([m['size'] for m in found.values()] or [0]),'prep_manifest_count':len(preps),'Astra_accepted_carriers_found':sum(bool(x['matching_paths']) for x in afiles),'Astra_run_dirs_found':sum(x['run_dir_exists'] for x in afiles),'raw_source_reads':0,'model_calls':0,'missing_primary_is_not_proof_never_processed':True};(O/'REMAINING_DISCOVERY_PUBLIC.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
