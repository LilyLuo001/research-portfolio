#!/usr/bin/env python3
import json,tempfile,subprocess,sys
from pathlib import Path
import pyarrow as pa, pyarrow.parquet as pq
root=Path(tempfile.mkdtemp(prefix='stage_c_fixture_')); desc=root/'desc'; idx=root/'index'; desc.mkdir(); idx.mkdir()
dschema=pa.schema([('COMPANY_ID',pa.decimal128(10,0)),('COMPANY_NAME',pa.string()),('DESCRIPTION',pa.string()),('JOB_HASH',pa.string())])
hashes=['0'+'a'*31,'1'+'b'*31,'2'+'c'*31,'3'+'d'*31,'4'+'e'*31,'f'+'9'*31]
for fi in range(3):
 hs=hashes[fi*2:fi*2+2]
 t=pa.Table.from_arrays([pa.array([fi+1,fi+1],type=pa.decimal128(10,0)),pa.array(['C','C']),pa.array(['text %d'%i for i in range(2)]),pa.array(hs)],schema=dschema)
 pq.write_table(t,desc/('job-descriptions_fixture_%d.snappy.parquet'%fi),row_group_size=1)
rschema=pa.schema([('JOB_HASH',pa.string()),('COMPANY_ID',pa.decimal128(10,0)),('COUNTRY',pa.string()),('STATE',pa.string()),
 ('CREATED',pa.timestamp('ms')),('LAST_UPDATED',pa.timestamp('ms')),('LAST_CHECKED',pa.timestamp('ms')),('DELETE_DATE',pa.timestamp('ms')),('RECORD_SOURCE_ROW',pa.uint64())])
vals=[
 (hashes[0],1,'USA','CA','2022-01-01','2022-12-01'),(hashes[1],1,'USA','TX','2021-01-01','2022-01-01'),
 (hashes[2],2,'USA','NY','2023-02-01','2023-03-01'),(hashes[3],2,'USA','WA','2018-01-01','2024-01-01'),
 (hashes[4],3,'CAN','ON','2015-01-01','2015-06-01')]
for j,v in enumerate(vals):
 p=v[0][0]; d=idx/('hash_prefix='+p);d.mkdir(exist_ok=True)
 def ts(x):return pa.scalar(x,type=pa.string()).cast(pa.timestamp('ms')).as_py()
 tab=pa.Table.from_arrays([pa.array([v[0]]),pa.array([v[1]],type=pa.decimal128(10,0)),pa.array([v[2]]),pa.array([v[3]]),
  pa.array([ts(v[4])],type=pa.timestamp('ms')),pa.array([None],type=pa.timestamp('ms')),pa.array([ts(v[5])],type=pa.timestamp('ms')),
  pa.array([None],type=pa.timestamp('ms')),pa.array([j],type=pa.uint64())],schema=rschema)
 pq.write_table(tab,d/('r%d.parquet'%j))
manifest=root/'manifest.txt';manifest.write_text(''.join(str(p)+'\n' for p in sorted(desc.glob('*.parquet'))))
evidence=root/'sha.json';evidence.write_text(json.dumps({'status':'PASS','all_sha256_match':True}))
index_manifest=idx/'index_manifest.json';index_manifest.write_text(json.dumps({'status':'complete','rows':5}))
import hashlib
index_complete=idx/'COMPLETE.json';index_complete.write_text(json.dumps({'manifest':'index_manifest.json','sha256':hashlib.sha256(index_manifest.read_bytes()).hexdigest()}))
cfg={'region':'fixture','seed':'fixture-seed','description_manifest':str(manifest),'records_index':str(idx),'output_dir':str(root/'out'),
 'records_index_complete':str(index_complete),'destination_sha_validation':str(evidence),'selected_source_files':3,'batch_rows':2,'join_workers':2,
 'per_prefix_per_stratum':2,'final_per_stratum':2,'max_output_bytes':50_000_000,
 'scope_warning':'fixture only'}
cp=root/'config.json';cp.write_text(json.dumps(cfg))
env=dict(__import__('os').environ);env['SLURM_CPUS_PER_TASK']='4'
subprocess.run([sys.executable,str(Path(__file__).parent/'prepare_sample.py'),'--config',str(cp)],check=True,env=env)
report=json.loads((root/'out/run_report.json').read_text()); sample=pq.read_table(root/'out/sample_ads.parquet')
assert report['status']=='complete' and report['selected_source_rows']==6 and sample.num_rows==6
assert sum(sample['RECORD_MATCH'].to_pylist())==5
assert sorted(sample['DESCRIPTION'].to_pylist())==['text 0','text 0','text 0','text 1','text 1','text 1']
assert all(x is not None for x in sample['SOURCE_ROW_GROUP'].to_pylist())
print(json.dumps({'status':'PASS','fixture_root':str(root),'sample_rows':sample.num_rows,'matched':5,'orphan':1},sort_keys=True))
