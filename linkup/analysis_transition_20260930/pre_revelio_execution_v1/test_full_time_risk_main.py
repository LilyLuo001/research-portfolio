#!/usr/bin/env python3
"""Run the complete T4 main pipeline on a tiny 16-prefix fixture."""
import csv,hashlib,importlib.util,json,subprocess,sys,tempfile
from datetime import datetime
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('narrow_builder',HERE/'build_semantic_narrow.py')
narrow_builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(narrow_builder)
PREFIXES='0123456789abcdef'

def write(path,columns):
 path.parent.mkdir(parents=True,exist_ok=True);pq.write_table(pa.table(columns),path)

with tempfile.TemporaryDirectory() as td:
 root=Path(td);narrow=root/'narrow';keys=root/'keys';dups=root/'dups';records=root/'records';work=root/'work';out=root/'out'
 hashes=[p+('%031x'%(i+1)) for i,p in enumerate(PREFIXES)]
 years=[2020+(i%3) for i in range(16)]
 # The production diagnostic selects candidate groups from hash prefix 0.  Add
 # two more prefix-0 ads so that this frame contains the same group in three
 # CREATED years, while the selected cases can still be recovered globally.
 hashes.extend(['0'+('%031x'%1001),'0'+('%031x'%1002)])
 years.extend([2021,2022])
 prefixes=[h[0] for h in hashes]
 raw_rows=[];narrow_rows=[];onet_hash=[];onet_code=[]
 key_rows={p:[] for p in PREFIXES};record_rows={p:[] for p in PREFIXES}
 for i,(prefix,job,year) in enumerate(zip(prefixes,hashes,years)):
  created=datetime(year,1+(i%9),2);checked=datetime(2023,2,1);deleted=datetime(2023,3,1)
  raw_rows.append({'JOB_HASH':job,'COMPANY_ID':'fixture_company','TITLE':'Senior Engineer 2025!','CITY':'Boston','COUNTRY':'US','STATE':'MA','CREATED':created,'LAST_UPDATED':checked,'LAST_CHECKED':checked,'DELETE_DATE':deleted,'BASE_HASH':'parent_'+str(i%2),'URL':'https://fixture.invalid/'+str(i)})
  row={name:(None if name=='exp_occupation_task_main' else False) for name in narrow_builder.AD_OUTPUT_SCHEMA.names}
  row.update({'JOB_HASH':job,'SOURCE_FILE':'fixture.parquet','SOURCE_ROW':i,'RECORD_SOURCE_ROW':i,'CREATED':created,'STATE':'MA','usable':True})
  narrow_rows.append(row);onet_hash.append(job);onet_code.append('15-1252.00')
  key_rows[prefix].append(job)
  record_rows[prefix].append({'JOB_HASH':job,'COMPANY_ID':'fixture_company','STATE':'MA','CREATED':created,'LAST_CHECKED':checked,'DELETE_DATE':deleted})
 for prefix in PREFIXES:
  write(keys/('hash_prefix='+prefix)/'data.parquet',{'JOB_HASH':key_rows[prefix]})
  write(dups/(prefix+'.parquet'),{'JOB_HASH':pa.array([],type=pa.string()),'occurrences':pa.array([],type=pa.int64())})
  write(records/('hash_prefix='+prefix)/'data.parquet',pa.Table.from_pylist(record_rows[prefix]).to_pydict())
 narrow.mkdir();pq.write_table(pa.Table.from_pylist(narrow_rows,schema=narrow_builder.AD_OUTPUT_SCHEMA),narrow/'fixture.parquet')
 raw=root/'raw.parquet';pq.write_table(pa.Table.from_pylist(raw_rows),raw)
 onet=root/'onet.parquet';write(onet,{'JOB_HASH':onet_hash,'ONET_OCCUPATION_CODE':onet_code})
 official=root/'official.csv';official.write_text('O*NET-SOC Code\n15-1252.00\n')
 (records/'COMPLETE').write_text('fixture complete\n')
 batch=root/'batch.json';batch.write_text(json.dumps({'status':'complete','shards':1,'fixture':True}))
 audit=root/'audit.json';audit.write_text(json.dumps({'status':'complete','rows':18,'distinct_job_hashes':18,'fixture':True}))
 cmd=[sys.executable,str(HERE/'build_full_time_risk.py'),'--narrow-dir',str(narrow),'--narrow-batch-receipt',str(batch),'--global-key-audit',str(audit),'--global-key-dir',str(keys),'--duplicate-dir',str(dups),'--records-index-root',str(records),'--raw-records-glob',str(raw),'--onet-glob',str(onet),'--official-codes',str(official),'--work-dir',str(work),'--output-dir',str(out),'--threads','2','--memory-limit','1GB','--expected-shards','1','--expected-canonical-rows','18']
 subprocess.run(cmd,check=True,timeout=240)
 expected={'T4_TIME_RISK.csv','T4_CREATED_COHORT.csv','T4_ANNUAL_COVERAGE.csv','T4_SELECTED_ANNUAL_GROUP_SUMMARY.csv','T4_CONCENTRATION.csv','T4_CONCENTRATION_TOP20.csv','T4_RECEIPT.json'}
 assert expected=={p.name for p in out.iterdir()},sorted(p.name for p in out.iterdir())
 receipt=json.loads((out/'T4_RECEIPT.json').read_text());assert receipt['status']=='complete' and receipt['validation_scope']=='fixture_override'
 assert receipt['identity']['expected_shards']==1 and receipt['identity']['expected_canonical_rows']==18
 for name,digest in receipt['outputs'].items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest
 prefix_receipts=[json.loads((work/'prefix_summaries'/(p+'.receipt.json')).read_text()) for p in PREFIXES]
 assert sum(x['risk']['canonical_ads'] for x in prefix_receipts)==18
 assert sum(x['linkage']['records_1'] for x in prefix_receipts)==18
 assert sum(x['linkage']['onet_1'] for x in prefix_receipts)==18
 assert all(x['linkage']['records_gt1']==0 and x['linkage']['onet_gt1']==0 for x in prefix_receipts)
 with (out/'T4_SELECTED_ANNUAL_GROUP_SUMMARY.csv').open() as f:selected_groups=list(csv.DictReader(f))
 assert len(selected_groups)==1 and int(selected_groups[0]['created_years'])==3
 assert receipt['private_selected_keys']['rows']==9
 assert receipt['annual_diagnostic']['selection_frame']=='job_hash_prefix_0'
 with (work/'T4_SELECTED_ANNUAL_KEYS_PRIVATE.csv').open() as f:selected_keys=list(csv.DictReader(f))
 assert len({r['JOB_HASH'][0] for r in selected_keys})>1
 assert (work/'T4_ANNUAL_GROUP_COUNTS_PRIVATE.parquet').is_file() and (work/'T4_SELECTED_ANNUAL_KEYS_PRIVATE.csv').is_file()
 print(json.dumps({'status':'pass','validation_scope':'fixture_override','canonical_rows':18,'prefix_receipts':16,'public_outputs':len(expected)-1,'selected_groups':1,'selected_keys':9,'cross_prefix_recovery':True,'all_main_stages_exercised':True},sort_keys=True))
