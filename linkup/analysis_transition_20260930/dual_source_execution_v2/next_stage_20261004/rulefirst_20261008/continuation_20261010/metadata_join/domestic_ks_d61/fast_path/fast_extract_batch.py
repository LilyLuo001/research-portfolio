#!/usr/bin/env python3
"""Mechanical Arrow JOB_HASH prefilter for D61 metadata extraction."""
import argparse, datetime as dt, importlib.util, json, os
from pathlib import Path
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
BASE_PATH=Path('/public/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/metadata_join_first5_d60/code/targeted_metadata_join.py')
spec=importlib.util.spec_from_file_location('d61_base',str(BASE_PATH)); base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
BATCH_SIZE=262144
VERSION='d61-arrow-prefilter-v1'

def filtered_rows(batch,kind,record_keys,job_values):
 mask=pc.fill_null(pc.is_in(batch.column(batch.schema.get_field_index('JOB_HASH')),value_set=job_values),False)
 arrays=[pc.filter(batch.column(i),mask) for i in range(batch.num_columns)]
 filtered=pa.RecordBatch.from_arrays(arrays,schema=batch.schema)
 rows=base.arrow_rows(filtered)
 if kind=='records': rows=[r for r in rows if (r['JOB_HASH'],r['RECORD_SOURCE_ROW']) in record_keys]
 return rows

def extract(args):
 spec_path=Path(args.batch_spec); cfg=base.read_manifest(spec_path);kind=cfg.get('kind')
 if kind not in {'records','onet'}:raise RuntimeError('batch kind must be records or onet')
 inputs=cfg.get('input_files');cap=int(cfg.get('staging_cap_bytes',base.DEFAULT_CAP))
 if not isinstance(inputs,list) or not inputs or cap>base.DEFAULT_CAP:raise RuntimeError('invalid input batch/cap')
 verified=[];total_bytes=0
 for item in inputs:
  p=Path(item['path']);size=p.stat().st_size;digest=base.sha256(p);sid=item.get('source_id')
  if not isinstance(sid,str) or not sid or size!=item.get('size_bytes') or digest!=item.get('sha256'):raise RuntimeError('source identity mismatch')
  total_bytes+=size;verified.append({'source_id':sid,'path':str(p),'size_bytes':size,'sha256':digest})
 if total_bytes>cap:raise RuntimeError('batch cap exceeded')
 output=Path(cfg['output']);receipt=Path(cfg['receipt']);output.parent.mkdir(parents=True,exist_ok=True)
 _lock=base.lock(output.parent,'.%s.fast.lock'%cfg.get('batch_id','batch'))
 identity={'version':VERSION,'base_code_sha256':base.sha256(BASE_PATH),'fast_code_sha256':base.sha256(__file__),'kind':kind,'batch_id':cfg.get('batch_id'),'batch_spec_sha256':base.sha256(spec_path),'key_receipt_sha256':base.sha256(cfg['key_receipt']),'inputs':verified,'batch_size':BATCH_SIZE,'prefilter':'pyarrow.compute.is_in_JOB_HASH_then_exact_record_tuple'}
 if receipt.exists():
  old=json.loads(receipt.read_text())
  if old.get('status')=='complete' and old.get('identity')==identity and output.exists() and old.get('output_sha256')==base.sha256(output):return
  raise RuntimeError('existing fast receipt identity mismatch')
 record_keys,job_keys=base.load_key_sets(cfg['key_dir'],cfg['key_receipt']);job_values=pa.array(sorted(job_keys),type=pa.string())
 schema=base.RECORD_HIT_SCHEMA if kind=='records' else base.ONET_HIT_SCHEMA
 columns=(['JOB_HASH','RECORD_SOURCE_ROW','COMPANY_ID','CREATED','LAST_CHECKED','DELETE_DATE','STATE'] if kind=='records' else ['JOB_HASH','ONET_OCCUPATION_CODE'])
 temp=Path(str(output)+'.tmp');temp.unlink(missing_ok=True);writer=pq.ParquetWriter(temp,schema,compression='zstd');scanned=hits=post_key_filter_rows=0
 try:
  for item in verified:
   parquet=pq.ParquetFile(item['path']);missing=set(columns)-set(parquet.schema_arrow.names)
   if missing:raise RuntimeError('source schema missing '+','.join(sorted(missing)))
   for batch in parquet.iter_batches(batch_size=BATCH_SIZE,columns=columns):
    scanned+=batch.num_rows;rows=filtered_rows(batch,kind,record_keys,job_values);post_key_filter_rows+=len(rows);selected=[]
    for row in rows:
     if kind=='records':selected.append({'JOB_HASH':row['JOB_HASH'],'RECORD_SOURCE_ROW':row['RECORD_SOURCE_ROW'],'COMPANY_ID':base.clean_string(row.get('COMPANY_ID')),'CREATED':row.get('CREATED'),'LAST_CHECKED':row.get('LAST_CHECKED'),'DELETE_DATE':row.get('DELETE_DATE'),'STATE':base.clean_string(row.get('STATE'))})
     else:selected.append({'JOB_HASH':row['JOB_HASH'],'ONET_OCCUPATION_CODE':base.clean_string(row.get('ONET_OCCUPATION_CODE'))})
    if selected:writer.write_table(base.rows_table(selected,schema));hits+=len(selected)
  writer.close();os.replace(temp,output)
 except Exception:
  writer.close();temp.unlink(missing_ok=True);raise
 base.atomic_json(receipt,{'status':'complete','version':VERSION,'stage':'extract_%s'%kind,'identity':identity,'source_rows_scanned':scanned,'post_key_filter_rows':post_key_filter_rows,'hit_rows':hits,'staged_input_bytes':total_bytes,'staging_cap_bytes':cap,'output_bytes':output.stat().st_size,'output_sha256':base.sha256(output),'runtime':base.runtime(),'created_utc':dt.datetime.now(dt.timezone.utc).isoformat()})

def main():
 base.check_runtime();p=argparse.ArgumentParser();p.add_argument('--batch-spec',required=True);extract(p.parse_args())
if __name__=='__main__':main()
