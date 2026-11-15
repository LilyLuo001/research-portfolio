import json,hashlib,csv,io,sqlite3,collections,datetime,base64,zlib
from pathlib import Path
R=Path.home()/'migration';O=R/'execution_20261116/run001/stage1';inv=json.loads((O/'VERIFIED_DELIVERY_METADATA_PRIVATE.json').read_text());reports=[];source_records={};index_reports=[];parquet_summaries={};delivery=[];catalog_names=[]
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
for item in inv:
 p=O/'metadata_cache'/(item['sha256']+'.metadata');assert sha(p)==item['sha256'];name=Path(item['locator']['rel']).name
 try:o=json.loads(p.read_bytes())
 except Exception:
  if name=='job_records_manifest.tsv':
   rows=list(csv.DictReader(io.StringIO(p.read_text()),delimiter='\t'));key=hashlib.sha256(json.dumps(sorted((x['file'],x['bytes'],x['footer_rows']) for x in rows)).encode()).hexdigest();source_records[key]={'source_sha256':item['sha256'],'files':len(rows),'rows':sum(int(x['footer_rows']) for x in rows),'bytes':sum(int(x['bytes']) for x in rows),'unit':'source_file_footer_rows_not_unique_ads'}
  continue
 if not isinstance(o,dict):continue
 if name=='dewey-audit-manifest.json':
  d=o.get('describe',{});meta=o.get('metadata',{});record={'source_sha256':item['sha256'],'dataset_name':d.get('dataset_name'),'dataset_version_timestamp':d.get('dataset_version_timestamp'),'unloaded_at':d.get('unloaded_at'),'snapshot_at':o.get('snapshot_at'),'files_listed':len(o.get('files',[])),'total_files':meta.get('total_files'),'total_size':meta.get('total_size'),'files_total_pages':o.get('files_total_pages')};delivery.append((record,o));reports.append(record)
 elif name=='description_regions_disjoint_manifest.json':
  vals={k:o.get(k) for k in ['wuzhen_count','kunshan_count','union_count','union_bytes','dedup_rule','source_record_dedup_note']};vals['source_sha256']=item['sha256'];reports.append({'description_file_union':vals})
 elif name=='index_manifest.json':
  index_reports.append({k:o.get(k) for k in ['status','rows','source_files','available_source_files','output_footer_rows','input_manifest_sha256','columns','output_bytes']})
 elif 'source' in o and 'output_rows' in o and isinstance(o['source'],dict):
  s=o['source'];key=(Path(s['file']).name,s['bytes'],s['footer_rows'],s['skinny_schema_sha256']);parquet_summaries.setdefault(key,[]).append({'source_sha256':item['sha256'],'output_rows':o['output_rows'],'status':o['status']})
 elif name=='RECORDS_INVENTORY_PRIVATE.json':reports.append({'records_inventory':{'source_sha256':item['sha256'],'files':len(o['files']),'rows':sum(x['rows'] for x in o['files']),'bytes':o['bytes'],'kind':o['kind'],'note':'index/shard inventory; possible overlap with source Records, not additive'}})
 elif name.startswith('catalog'):
  ds=o.get('datasets',[]);ds=ds.get('results',[]) if isinstance(ds,dict) else ds
  for d in ds:
   if isinstance(d,dict) and 'linkup' in str(d.get('name','')).lower():catalog_names.append(d['name'])
# One pass over metadata inventory, matching delivery filename+size, no source file reads.
lookup=collections.defaultdict(list)
for cluster in ['kunshan','wuzhen','huazhong']:
 c=sqlite3.connect((R/cluster/'LEDGER_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True)
 for rel,size,status,h in c.execute("select rel,size,status,sha from files where lower(path) like '%linkup%' and (lower(rel) like '%.parquet' or lower(rel) like '%.gz')"):
  lookup[(Path(rel).name,size)].append((status,h))
 c.close()
for report,data in delivery:
 matches=collections.Counter();conflicts=0
 for f in data.get('files',[]):
  matches_found=lookup.get((Path(f['file_name']).name,f['file_size_bytes']),[])
  if any(s=='verified' for s,h in matches_found):matches['listed_file_with_verified_name_size_match']+=1
  else:matches['listed_file_without_verified_name_size_match']+=1
  if len({h for s,h in matches_found if s=='verified'})>1:conflicts+=1
 report['migration_matching']=dict(matches);report['multiple_distinct_verified_content_sha_for_same_name_size']=conflicts;report['matching_is_file_inventory_not_ad_identity']=True
cat=R/'full_scope_catalog_preflight_20261115/20261115T120402Z/CORPUS_RELEASE_CATALOG_PRIVATE.jsonl';numeric=collections.Counter();numericcounts=collections.Counter();keys=set()
for l in cat.open():
 o=json.loads(l);keys.update(o)
 for k,v in o.items():
  if isinstance(v,(int,float)) and not isinstance(v,bool):numeric[k]+=v;numericcounts[k]+=1
r={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'available_delivery_metadata_reconciled_full_unique_ad_denominator_unresolved','delivery_and_other_scope_reports':reports,'records_footer_manifests_distinct_logical_contents':list(source_records.values()),'record_index_reports':index_reports,'per_source_record_shard_reports':{'unique_source_file_size_rows_schema_keys':len(parquet_summaries),'source_footer_rows_sum':sum(k[2] for k in parquet_summaries),'duplicate_version_rows':sum(len(v)-1 for v in parquet_summaries.values()),'all_preserve_row_count':all(all(x['output_rows']==k[2] for x in v) for k,v in parquet_summaries.items()),'not_canonical_ad_dedup':True},'frozen_US_catalog':{'keys':sorted(keys),'numeric_sums':dict(numeric),'numeric_field_nonmissing_file_counts':dict(numericcounts),'sha256':sha(cat)},'catalog_linkup_names':sorted(set(catalog_names)),'global_unique_ads':None,'global_missing_semantic_contexts':None,'no_new_model_calls':True,'no_advertisement_files_read':True}
(O/'SCOPE_RECONCILIATION_PUBLIC.json').write_text(json.dumps(r,indent=2)+'\n');e=base64.b64encode(zlib.compress(json.dumps(r).encode(),9)).decode();assert len(e)<3800,len(e);print(json.dumps({'aggregate_zlib_b64':e}))
