#!/usr/bin/env python3
import datetime as dt, hashlib, importlib.util, json, time
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
ROOT=Path('/public/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/metadata_join_first5_d60')
def load(name,path):
 s=importlib.util.spec_from_file_location(name,str(path));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
base=load('base',ROOT/'code/targeted_metadata_join.py');fast=load('fast',ROOT/'code/fast_extract_batch.py')
def old_rows(batch,kind,rkeys,jkeys):
 rows=base.arrow_rows(batch)
 return [r for r in rows if ((r['JOB_HASH'],r['RECORD_SOURCE_ROW']) in rkeys if kind=='records' else r['JOB_HASH'] in jkeys)]
def compare_batch(batch,kind,rkeys,jkeys):
 vals=pa.array(sorted(jkeys),type=pa.string());a=old_rows(batch,kind,rkeys,jkeys);b=fast.filtered_rows(batch,kind,rkeys,vals);assert a==b;return len(a)
def synthetic():
 a='a'*32;b='b'*32;c='c'*32;rkeys={(a,10),(b,20)};j={a,b}
 rs=pa.schema([('JOB_HASH',pa.string()),('RECORD_SOURCE_ROW',pa.int64()),('COMPANY_ID',pa.string()),('CREATED',pa.timestamp('ms')),('LAST_CHECKED',pa.timestamp('ms')),('DELETE_DATE',pa.timestamp('ms')),('STATE',pa.string())])
 rows=[{k:v for k,v in zip(rs.names,x)} for x in [(a,10,'x',None,None,None,'CA'),(a,11,'wrong',None,None,None,'NY'),(None,10,'null',None,None,None,'TX'),(a,10,'dup',None,None,None,'CA'),(c,30,'nohit',None,None,None,'WA'),(b,20,None,None,None,None,None)]]
 rb=base.rows_table(rows,rs).to_batches()[0];assert compare_batch(rb,'records',rkeys,j)==3
 oschema=pa.schema([('JOB_HASH',pa.string()),('ONET_OCCUPATION_CODE',pa.string())]);orows=[{'JOB_HASH':x[0],'ONET_OCCUPATION_CODE':x[1]} for x in [(a,'11-1011.00'),(a,'dup'),(None,'null'),(c,'nohit'),(b,None)]]
 ob=base.rows_table(orows,oschema).to_batches()[0];assert compare_batch(ob,'onet',rkeys,j)==3
 return {'records_input':len(rows),'records_selected':3,'onet_input':len(orows),'onet_selected':3,'covers':['null_job_hash','duplicate_match','wrong_record_source_row','no_hit','null_metadata']}
def real_file(kind,path,rkeys,jkeys):
 max_batches=2
 cols=(['JOB_HASH','RECORD_SOURCE_ROW','COMPANY_ID','CREATED','LAST_CHECKED','DELETE_DATE','STATE'] if kind=='records' else ['JOB_HASH','ONET_OCCUPATION_CODE']);pf=pq.ParquetFile(path);old=[];new=[];scanned=0
 t=time.time()
 for i,b in enumerate(pf.iter_batches(batch_size=fast.BATCH_SIZE,columns=cols)):
  if i>=max_batches:break
  scanned+=b.num_rows;old.extend(old_rows(b,kind,rkeys,jkeys))
 old_s=time.time()-t;vals=pa.array(sorted(jkeys),type=pa.string());t=time.time()
 for i,b in enumerate(pf.iter_batches(batch_size=fast.BATCH_SIZE,columns=cols)):
  if i>=max_batches:break
  new.extend(fast.filtered_rows(b,kind,rkeys,vals))
 fast_s=time.time()-t;assert old==new
 digest=hashlib.sha256(json.dumps(old,sort_keys=True,default=str,separators=(',',':')).encode()).hexdigest()
 return {'kind':kind,'source_id':path.name,'source_bytes':path.stat().st_size,'qualification_batches':max_batches,'scanned_rows':scanned,'selected_rows':len(old),'ordered_selected_rows_sha256':digest,'exact_ordered_equality':True,'old_seconds':old_s,'fast_seconds':fast_s,'speedup_ratio':old_s/max(fast_s,1e-9)}
def main():
 rkeys,jkeys=base.load_key_sets(ROOT/'private/keys',ROOT/'output/FIRST5_KEY_PREP_RECEIPT_PUBLIC.json');ri=json.load(open(ROOT/'work/RECORDS_INVENTORY_PRIVATE.json'));oi=json.load(open(ROOT/'work/ONET_INVENTORY_PRIVATE.json'))
 rp=Path(min(ri['files'],key=lambda x:x['size_bytes'])['path']);op=Path(min(oi['files'],key=lambda x:x['size_bytes'])['path'])
 out={'version':'d61-arrow-prefilter-qualification-v1','created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'pass','synthetic':synthetic(),'real_files':[real_file('records',rp,rkeys,jkeys),real_file('onet',op,rkeys,jkeys)],'base_code_sha256':base.sha256(ROOT/'code/targeted_metadata_join.py'),'fast_code_sha256':base.sha256(ROOT/'code/fast_extract_batch.py'),'qualification_code_sha256':base.sha256(__file__),'batch_size':fast.BATCH_SIZE,'timing_note':'old pass ran first and fast pass may benefit from filesystem cache; ratio is diagnostic, equivalence is the acceptance gate','claim':'mechanical extraction equivalence only; no semantic certification'}
 base.atomic_json(ROOT/'public/FAST_EXTRACT_QUALIFICATION_PUBLIC.json',out);print(json.dumps(out,sort_keys=True))
if __name__=='__main__':main()
