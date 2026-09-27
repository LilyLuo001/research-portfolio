#!/usr/bin/env python3
import hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
import pyarrow as pa, pyarrow.parquet as pq
r=Path(tempfile.mkdtemp(prefix='support_audit_fixture_')); on=r/'onet'; rem=r/'remote'; rec=r/'records';out=r/'out';on.mkdir();rem.mkdir();rec.mkdir()
hashes=[p+(p*31) for p in '0123456789abcdef']
# Every prefix exists; prefix 0 adds duplicate/conflicting codes.
pq.write_table(pa.table({'JOB_HASH':hashes+[hashes[0],None,'bad'],'ONET_OCCUPATION_CODE':['15-1252.00']*16+['11-1011.00',None,'bad']}),on/'o.parquet')
pq.write_table(pa.table({'END_DATE':['2023-02-01']*16+['2023-03-01','2023-02-01',None,'bogus','2023-03-01'],
 'JOB_HASH':hashes+[hashes[0],hashes[0],hashes[0],'bad',hashes[1]],
 'REMOTE_DETAIL':['remote']*16+['hybrid','remote','remote','x','remote'],'REMOTE_STATUS':[True]*16+[False,True,True,False,True],
 'START_DATE':['2023-01-01']*16+['2023-01-15','2023-02-01','2023-01-10','bad','2023-02-01']}),rem/'r.parquet')
rs=pa.schema([('JOB_HASH',pa.string()),('COMPANY_ID',pa.decimal128(10,0)),('COUNTRY',pa.string()),('STATE',pa.string()),('CREATED',pa.timestamp('ms')),('LAST_UPDATED',pa.timestamp('ms')),('LAST_CHECKED',pa.timestamp('ms')),('DELETE_DATE',pa.timestamp('ms')),('RECORD_SOURCE_ROW',pa.uint64())])
import datetime as dt
for i,h in enumerate(hashes):
 d=rec/('hash_prefix='+h[0]);d.mkdir();pq.write_table(pa.Table.from_arrays([pa.array([h]),pa.array([1],type=pa.decimal128(10,0)),pa.array(['USA']),pa.array(['CA']),pa.array([dt.datetime(2023,1,1)],type=pa.timestamp('ms')),pa.array([None],type=pa.timestamp('ms')),pa.array([None],type=pa.timestamp('ms')),pa.array([None],type=pa.timestamp('ms')),pa.array([i],type=pa.uint64())],schema=rs),d/'x.parquet')
man=rec/'index_manifest.json';man.write_text(json.dumps({'status':'complete','rows':16,'output_footer_rows':16,'columns':rs.names}))
(rec/'COMPLETE').write_text(json.dumps({'manifest':'index_manifest.json','sha256':hashlib.sha256(man.read_bytes()).hexdigest()}))
cfg={'onet_glob':str(on/'*.parquet'),'remote_glob':str(rem/'*.parquet'),'records_index':str(rec),'records_complete':str(rec/'COMPLETE'),'output_dir':str(out),'tmp_root':str(r/'tmp'),'threads':2,'memory_limit':'1GB','max_temp_directory_size':'2GB','max_tmp_bytes':500000000,'min_tmp_free_bytes':1000000,'max_output_bytes':100000000}
c=r/'cfg.json';c.write_text(json.dumps(cfg));subprocess.run([sys.executable,str(Path(__file__).with_name('support_audit.py')),'--config',str(c)],check=True,env=dict(os.environ,SLURM_TMPDIR=str(r/'tmp')))
x=json.loads((out/'support_audit_report.json').read_text());p0=[z for z in x['onet_prefix_metrics'] if z['prefix']=='0'][0];rr=[z for z in x['remote_prefix_metrics'] if z['prefix']=='0'][0]; rr1=[z for z in x['remote_prefix_metrics'] if z['prefix']=='1'][0]
assert p0['conflicting_code_jobs']==1 and p0['duplicate_job_hashes']==1
assert rr['strict_overlap_rows']>=1 and rr1['touching_interval_rows']>=1 and rr['open_end_rows']>=1 and rr['open_end_with_later_start_rows']>=1 and rr['jobs_with_multiple_labels']==1
cov=pq.read_table(out/'onet_usa_created_coverage.parquet')
assert cov.num_rows==1 and cov['denominator'][0].as_py()==16 and cov['matched_job_hash'][0].as_py()==16
print(json.dumps({'status':'PASS','fixture':str(r),'onet_conflict':1,'strict_overlap':rr['strict_overlap_rows'],'touching':rr1['touching_interval_rows']}))
