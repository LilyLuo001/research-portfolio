#!/usr/bin/env python3
import importlib.util,tempfile,time
from pathlib import Path
import duckdb,pyarrow as pa,pyarrow.parquet as pq
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('t4',HERE/'build_full_time_risk.py');t4=importlib.util.module_from_spec(spec);spec.loader.exec_module(t4)
with tempfile.TemporaryDirectory() as td:
 root=Path(td);raw=root/'raw.parquet';keys=root/'keys'/'hash_prefix=0';keys.mkdir(parents=True);dup=root/'dup.parquet';groups=root/'groups.parquet'
 hashes=['%032x'%i for i in range(6)]
 pq.write_table(pa.table({'JOB_HASH':hashes,'COMPANY_ID':[1]*6,'TITLE':['Senior Engineer 2025!']*6,'CITY':['Boston']*6,'COUNTRY':['US']*6,'CREATED':[pa.scalar('2021-01-01',type=pa.string()).as_py()]*6,'LAST_UPDATED':['2021-01-02']*6,'LAST_CHECKED':['2021-01-03']*6,'DELETE_DATE':['2021-01-04']*6,'BASE_HASH':['parent']*6,'URL':['u'+str(i) for i in range(6)]}),raw)
 pq.write_table(pa.table({'JOB_HASH':hashes}),keys/'data.parquet');pq.write_table(pa.table({'JOB_HASH':pa.array([],type=pa.string()),'occurrences':pa.array([],type=pa.int64())}),dup);pq.write_table(pa.table({'COMPANY_ID':[1],'normalized_title':['senior engineer 2025'],'CITY':['Boston'],'years':[3]}),groups)
 con=t4.connect(2,'1GB',root/'duckdb_tmp'/'fixture');assert con.space_monitor_active is True
 rows=con.execute(t4.annual_candidate_sql([str(raw)],str(root/'keys'/'hash_prefix=*'/'*.parquet'),[str(dup)],groups,t4.SEED)).fetchall();assert len(rows)==3,len(rows);thread=con._thread;con.close();assert not thread.is_alive()
 old_gib=t4.GIB;t4.GIB=1;guard=t4.connect(1,'256MB',root/'guardcase'/'duckdb_tmp'/'fixture');(guard._temp/'spill.bin').write_bytes(b'1234567890123');time.sleep(1.2)
 try:guard.execute('SELECT 1');raise AssertionError('space monitor did not block execution')
 except RuntimeError as e:assert 'temp directory exceeded' in str(e)
 t4.GIB=old_gib;assert not guard._thread.is_alive()
 print('ok: DuckDB 0.9.2 soft space monitor active, interrupts on limit, and stops; ambiguous group fields bound; global company/title/city/year cap retained 3')
