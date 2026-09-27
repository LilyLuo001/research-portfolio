#!/usr/bin/env python3
import datetime as dt,hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
import pyarrow as pa,pyarrow.parquet as pq
r=Path(tempfile.mkdtemp(prefix='stage_d_fixture_'));onet=r/'onet';rec=r/'records';out=r/'out';onet.mkdir();rec.mkdir()
record_hashes=[p+('a'*31) for p in '0123456789abcdef']+['f'+('c'*31)]
onet_hashes=list(record_hashes);onet_hashes[0]='0'+('b'*31)
codes=['15-1252.00', '', 'BAD']+['11-1011.00']*14
pq.write_table(pa.table({'JOB_HASH':onet_hashes,'ONET_OCCUPATION_CODE':codes}),onet/'o.parquet')
rs=pa.schema([('JOB_HASH',pa.string()),('COMPANY_ID',pa.decimal128(10,0)),('COUNTRY',pa.string()),('STATE',pa.string()),('CREATED',pa.timestamp('ms')),('LAST_UPDATED',pa.timestamp('ms')),('LAST_CHECKED',pa.timestamp('ms')),('DELETE_DATE',pa.timestamp('ms')),('RECORD_SOURCE_ROW',pa.uint64())])
for i,h in enumerate(record_hashes):
 d=rec/('hash_prefix='+h[0]);d.mkdir(exist_ok=True);pq.write_table(pa.Table.from_arrays([pa.array([h]),pa.array([1],type=pa.decimal128(10,0)),pa.array(['USA']),pa.array(['CA']),pa.array([None if i==16 else dt.datetime(2016+i%2,1,1)],type=pa.timestamp('ms')),pa.array([None],type=pa.timestamp('ms')),pa.array([None],type=pa.timestamp('ms')),pa.array([None],type=pa.timestamp('ms')),pa.array([i],type=pa.uint64())],schema=rs),d/('r%d.parquet'%i))
man=rec/'index_manifest.json';man.write_text(json.dumps({'status':'complete','rows':17,'output_footer_rows':17,'columns':rs.names}));(rec/'COMPLETE').write_text(json.dumps({'manifest':'index_manifest.json','sha256':hashlib.sha256(man.read_bytes()).hexdigest()}))
cfg={'onet_glob':str(onet/'*.parquet'),'records_index':str(rec),'records_complete':str(rec/'COMPLETE'),'output_dir':str(out),'tmp_root':str(r/'tmp'),'threads':2,'memory_limit':'1GB','expected_onet_rows':17,'expected_usa_records':17,'min_tmp_free_bytes':1000000,'max_scratch_bytes':500000000,'max_output_bytes':100000000}
c=r/'config.json';c.write_text(json.dumps(cfg));subprocess.run([sys.executable,str(Path(__file__).with_name('build_occupation_baseline.py')),'--config',str(c)],check=True,env=dict(os.environ,SLURM_TMPDIR=str(r/'tmp')))
x=json.load(open(out/'run_report.json'));assert x['totals']=={'usa_records':17,'matched_onet_key':16,'valid_code':14,'blank_code':1,'invalid_format':1,'missing_onet_key':1}
assert sum(z['usa_records'] for z in pq.read_table(out/'quarter_coverage.parquet').to_pylist())==17
full=pq.read_table(out/'quarter_full_code.parquet').to_pylist();major=pq.read_table(out/'quarter_major_group.parquet').to_pylist();assert sum(x['record_count'] for x in full)==sum(x['record_count'] for x in major)==17;assert any(x['created_year'] is None for x in major)
print(json.dumps({'status':'PASS','fixture':str(r),'totals':x['totals']}))
