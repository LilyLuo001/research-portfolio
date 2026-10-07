#!/usr/bin/env python3
"""Fixed-10,000 copy of the frozen materializer; locator verification is unchanged.

Copied from pre_revelio_execution_v1/materialize_selected_text.py (SHA-256:
recorded in each receipt).  The sole operational extension is an authorized
10,000 row cap for the frozen fixed sample.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,os
from pathlib import Path
import pyarrow.parquet as pq
KEYS=('JOB_HASH','SOURCE_FILE','SOURCE_ROW','RECORD_SOURCE_ROW')
FROZEN_ORIGINAL='/public/home/lilysharp/linkup_analysis_execution_oct02/code/pre_revelio_execution_v1/materialize_selected_text.py'
FROZEN_LOCAL_COPY='/Users/lilyluo/Documents/LinkUp_Research_20260924/analysis_transition_20260930/pre_revelio_execution_v1/materialize_selected_text.py'
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def load_rows(path):
 p=Path(path)
 if p.suffix.lower()=='.csv':
  with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
 if p.suffix.lower()=='.json':
  value=json.loads(p.read_text());rows=value.get('selected') if isinstance(value,dict) else value
  if not isinstance(rows,list):raise RuntimeError('JSON selection requires a selected list')
  result=[]
  for row in rows:
   key=row.get('private_key') if isinstance(row,dict) else None
   try: parts=json.loads(key)
   except (TypeError,json.JSONDecodeError):raise RuntimeError('selection contains invalid private_key JSON')
   if not isinstance(parts,list) or len(parts)!=4:raise RuntimeError('private_key must encode the four-field canonical tuple')
   result.append(dict(zip(KEYS,parts)))
  return result
 return pq.read_table(p).to_pylist()
def load_map(path):
 rows=[json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()];result={}
 for row in rows:
  name=row.get('SOURCE_FILE');target=Path(row.get('path',''))
  if not name or name in result:raise RuntimeError('source locator mapping must have unique SOURCE_FILE values')
  if target.name!=name or not target.is_absolute() or not target.is_file():raise RuntimeError('source locator path must be an existing absolute path with matching basename: '+str(name))
  if row.get('sha256') and sha(target)!=row['sha256']:raise RuntimeError('source locator sha mismatch: '+name)
  result[name]=target
 return result
def locate_row(pf,index,columns):
 if index<0 or index>=pf.metadata.num_rows:raise RuntimeError('SOURCE_ROW outside file footer range')
 offset=0
 for rg in range(pf.metadata.num_row_groups):
  size=pf.metadata.row_group(rg).num_rows
  if index<offset+size:return pf.read_row_group(rg,columns=columns).slice(index-offset,1).to_pylist()[0],rg
  offset+=size
 raise RuntimeError('SOURCE_ROW not found')
def original_sha():
 for candidate in (FROZEN_ORIGINAL,FROZEN_LOCAL_COPY):
  if Path(candidate).is_file():return sha(candidate)
 return 'unavailable_at_runtime'
def main():
 p=argparse.ArgumentParser();p.add_argument('--selection',type=Path,required=True);p.add_argument('--source-map',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True);p.add_argument('--text-column',required=True);p.add_argument('--max-rows',type=int,choices=(10000,),required=True);a=p.parse_args()
 selected=load_rows(a.selection)
 if len(selected)>a.max_rows:raise RuntimeError('selection exceeds authorized fixed-sample row cap')
 missing=[i for i,row in enumerate(selected) if any(row.get(k) in (None,'') for k in KEYS)]
 if missing:raise RuntimeError('selection has incomplete canonical key at rows '+str(missing[:5]))
 identities=[tuple(str(row[k]) for k in KEYS) for row in selected]
 if len(identities)!=len(set(identities)):raise RuntimeError('selection repeats a canonical key')
 mapping=load_map(a.source_map);cache={};output=[];rowgroups=set()
 for selected_row in selected:
  name=str(selected_row['SOURCE_FILE']);path=mapping.get(name)
  if path is None:raise RuntimeError('SOURCE_FILE absent from explicit locator mapping: '+name)
  pf=cache.setdefault(name,pq.ParquetFile(path));schema=set(pf.schema_arrow.names)
  if not {'JOB_HASH',a.text_column}<=schema:raise RuntimeError(name+' lacks JOB_HASH or requested text column')
  row,rg=locate_row(pf,int(selected_row['SOURCE_ROW']),['JOB_HASH',a.text_column])
  if str(row['JOB_HASH'])!=str(selected_row['JOB_HASH']):raise RuntimeError('JOB_HASH mismatch at '+name+':'+str(selected_row['SOURCE_ROW']))
  key=json.dumps([selected_row[k] for k in KEYS],separators=(',',':'))
  output.append({'private_key':key,'original_text':row[a.text_column],**{k:selected_row[k] for k in KEYS},'ORIGINAL_TEXT':row[a.text_column]});rowgroups.add((name,rg))
 a.output.parent.mkdir(parents=True,exist_ok=True);tmp=Path(str(a.output)+'.tmp')
 with tmp.open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['private_key','original_text']+list(KEYS)+['ORIGINAL_TEXT']);w.writeheader();w.writerows(output)
 os.replace(tmp,a.output)
 value={'status':'complete','rows':len(output),'max_rows':a.max_rows,'selection_sha256':sha(a.selection),'source_map_sha256':sha(a.source_map),'output_sha256':sha(a.output),'source_files_opened':len(cache),'row_groups_read':len(rowgroups),'verification':'exact SOURCE_FILE basename mapping + SOURCE_ROW footer bound + JOB_HASH match','frozen_original_materializer_sha256':original_sha(),'extension':'only max_rows fixed at 10000; locator verification and output schema copied unchanged','privacy':'private original text; do not commit'}
 t=Path(str(a.receipt)+'.tmp');t.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n');os.replace(t,a.receipt)
if __name__=='__main__':main()
