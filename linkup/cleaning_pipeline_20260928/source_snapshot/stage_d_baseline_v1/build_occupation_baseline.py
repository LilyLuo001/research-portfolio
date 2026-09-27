#!/usr/bin/env python3
"""USA first-observed cohort x snapshot O*NET occupation baseline.

This is a record-count table using current delivered O*NET codes. It is not a
historical occupation classification, vacancy count, adoption measure, or AI effect.
"""
import argparse,datetime as dt,glob,hashlib,json,os,shutil,threading
from pathlib import Path
import duckdb,pyarrow.parquet as pq
PFX='0123456789abcdef'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def atomic_json(p,x):
 t=Path(str(p)+'.tmp');t.write_text(json.dumps(x,indent=2,sort_keys=True,default=str)+'\n');os.replace(t,p)
def tree_bytes(p):return sum(x.stat().st_size for x in Path(p).rglob('*') if x.is_file())
def q(s):return str(s).replace("'","''")
def manifest(pattern):
 out=[]
 for x in sorted(glob.glob(pattern)):
  p=Path(x);pf=pq.ParquetFile(p);out.append({'name':p.name,'path':str(p),'bytes':p.stat().st_size,'rows':pf.metadata.num_rows,'row_groups':pf.metadata.num_row_groups,'schema':str(pf.schema_arrow)})
 return out
def verify_records(path):
 p=Path(path);m=json.loads(p.read_text());mp=p.parent/m.get('manifest','index_manifest.json')
 if m.get('sha256')!=sha(mp):raise RuntimeError('records COMPLETE manifest hash mismatch')
 x=json.loads(mp.read_text())
 if x.get('status')!='complete' or x.get('rows')!=x.get('output_footer_rows'):raise RuntimeError('records manifest incomplete')
 return {'complete_sha256':sha(p),'manifest_sha256':sha(mp),'rows':x['rows'],'columns':x['columns']}
class Guard:
 def __init__(self,root,limit,con):self.root=Path(root);self.limit=limit;self.con=con;self.hit=None;self.e=threading.Event();self.t=threading.Thread(target=self.run,daemon=True)
 def run(self):
  while not self.e.wait(2):
   try:
    n=tree_bytes(self.root)
    if n>self.limit:self.hit=n;self.con.interrupt();return
   except Exception:pass
 def start(self):self.t.start()
 def check(self):
  if self.hit is not None:raise RuntimeError('scratch cap exceeded %d > %d'%(self.hit,self.limit))
 def stop(self):self.e.set();self.t.join(timeout=3)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);a=ap.parse_args();cfg=json.loads(Path(a.config).read_text())
 out=Path(cfg['output_dir']);out.mkdir(parents=True,exist_ok=True);lock=out/'.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
 tmp=None;guard=None;con=None
 try:
  onet=manifest(cfg['onet_glob']);
  if not onet:raise RuntimeError('empty ONET input')
  if sum(x['rows'] for x in onet)!=cfg['expected_onet_rows']:raise RuntimeError('unexpected ONET footer row total')
  rv=verify_records(cfg['records_complete'])
  stable=[(x['name'],x['bytes'],x['rows'],x['schema']) for x in onet]
  identity={'code_sha256':sha(__file__),'config_sha256':sha(a.config),'onet_fingerprint':hashlib.sha256(json.dumps(stable,sort_keys=True).encode()).hexdigest(),'records':rv}
  ip=out/'identity.json'
  if ip.exists() and json.loads(ip.read_text())!=identity:raise RuntimeError('output identity mismatch')
  atomic_json(ip,identity);atomic_json(out/'input_manifest.json',{'onet':onet,'records':rv})
  token=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:12]+'_'+os.environ.get('SLURM_JOB_ID','local')
  tmp=Path(os.environ.get('SLURM_TMPDIR',cfg['tmp_root']))/('stage_d_occ_'+token);tmp.mkdir(parents=True,exist_ok=True)
  if shutil.disk_usage(tmp).free<cfg['min_tmp_free_bytes']:raise RuntimeError('insufficient node scratch free space')
  con=duckdb.connect(str(tmp/'work.duckdb'));con.execute('SET threads=%d'%cfg['threads']);con.execute("SET memory_limit='%s'"%cfg['memory_limit']);con.execute("SET temp_directory='%s'"%q(tmp/'spill'))
  guard=Guard(tmp,cfg['max_scratch_bytes'],con);guard.start();part=tmp/'onet';part.mkdir()
  print(json.dumps({'phase':'partition_onet','files':len(onet),'rows':sum(x['rows'] for x in onet)}),flush=True)
  con.execute(f"""COPY (SELECT substr(lower(JOB_HASH),1,1) prefix,JOB_HASH,ONET_OCCUPATION_CODE FROM read_parquet('{q(cfg['onet_glob'])}',union_by_name=true)) TO '{q(part)}' (FORMAT PARQUET,COMPRESSION ZSTD,PARTITION_BY(prefix),ROW_GROUP_SIZE 262144)""")
  pfiles=list(part.rglob('*.parquet'));prows=sum(pq.ParquetFile(p).metadata.num_rows for p in pfiles)
  if prows!=cfg['expected_onet_rows']:raise RuntimeError('ONET partition row conservation failed')
  guard.check();pref=tmp/'prefix_counts';pref.mkdir()
  for p in PFX:
   op=part/('prefix='+p)/'*.parquet';rp=Path(cfg['records_index'])/('hash_prefix='+p)/'*.parquet';dest=pref/('prefix_'+p+'.parquet')
   con.execute(f"""COPY (WITH r AS (SELECT JOB_HASH,CREATED FROM read_parquet('{q(rp)}') WHERE COUNTRY='USA'),
    o AS (SELECT JOB_HASH,ONET_OCCUPATION_CODE FROM read_parquet('{q(op)}'))
    SELECT year(r.CREATED) created_year,quarter(r.CREATED) created_quarter,
      CASE WHEN o.JOB_HASH IS NULL THEN 'missing_onet_key' WHEN o.ONET_OCCUPATION_CODE IS NULL OR trim(o.ONET_OCCUPATION_CODE)='' THEN 'blank_code' WHEN regexp_full_match(trim(o.ONET_OCCUPATION_CODE),'^[0-9]{{2}}-[0-9]{{4}}(\\.[0-9]{{2}})?$') THEN 'valid' ELSE 'invalid_format' END code_status,
      CASE WHEN o.JOB_HASH IS NULL THEN NULL ELSE trim(o.ONET_OCCUPATION_CODE) END onet_code,
      count(*) record_count
    FROM r LEFT JOIN o USING(JOB_HASH) GROUP BY 1,2,3,4) TO '{q(dest)}' (FORMAT PARQUET,COMPRESSION ZSTD)""")
   atomic_json(out/'progress.json',{'status':'running','completed_prefix':p,'updated_utc':dt.datetime.now(dt.timezone.utc).isoformat()});guard.check();print(json.dumps({'phase':'prefix_complete','prefix':p}),flush=True)
  fulltmp=out/'quarter_full_code.parquet.tmp';full=out/'quarter_full_code.parquet'
  con.execute(f"""COPY (SELECT created_year,created_quarter,code_status,onet_code,sum(record_count)::BIGINT record_count FROM read_parquet('{q(pref/'*.parquet')}') GROUP BY 1,2,3,4 ORDER BY 1,2,3,4) TO '{q(fulltmp)}' (FORMAT PARQUET,COMPRESSION ZSTD)""");os.replace(fulltmp,full)
  majtmp=out/'quarter_major_group.parquet.tmp';major=out/'quarter_major_group.parquet'
  con.execute(f"""COPY (WITH b AS (SELECT created_year,created_quarter,CASE WHEN code_status='valid' THEN substr(onet_code,1,2) ELSE '__'||upper(code_status)||'__' END occupation_major_group,record_count FROM read_parquet('{q(full)}')),
   g AS (SELECT created_year,created_quarter,occupation_major_group,sum(record_count)::BIGINT record_count FROM b GROUP BY 1,2,3)
   SELECT g.*,g.record_count/sum(g.record_count) OVER(PARTITION BY created_year,created_quarter) quarter_share FROM g ORDER BY 1,2,3) TO '{q(majtmp)}' (FORMAT PARQUET,COMPRESSION ZSTD)""");os.replace(majtmp,major)
  covtmp=out/'quarter_coverage.parquet.tmp';cov=out/'quarter_coverage.parquet'
  con.execute(f"""COPY (SELECT created_year,created_quarter,sum(record_count)::BIGINT usa_records,
   sum(CASE WHEN code_status<>'missing_onet_key' THEN record_count ELSE 0 END)::BIGINT matched_onet_key,
   sum(CASE WHEN code_status='valid' THEN record_count ELSE 0 END)::BIGINT valid_code,
   sum(CASE WHEN code_status='blank_code' THEN record_count ELSE 0 END)::BIGINT blank_code,
   sum(CASE WHEN code_status='invalid_format' THEN record_count ELSE 0 END)::BIGINT invalid_format,
   sum(CASE WHEN code_status='missing_onet_key' THEN record_count ELSE 0 END)::BIGINT missing_onet_key
   FROM read_parquet('{q(full)}') GROUP BY 1,2 ORDER BY 1,2) TO '{q(covtmp)}' (FORMAT PARQUET,COMPRESSION ZSTD)""");os.replace(covtmp,cov)
  shtmp=out/'major_group_2016plus_year_share.parquet.tmp';shares=out/'major_group_2016plus_year_share.parquet'
  con.execute(f"""COPY (WITH g AS (SELECT created_year,occupation_major_group,sum(record_count)::BIGINT record_count FROM read_parquet('{q(major)}') WHERE created_year>=2016 GROUP BY 1,2),d AS (SELECT created_year,sum(record_count)::DOUBLE denominator FROM g GROUP BY 1) SELECT g.*,g.record_count/d.denominator year_share FROM g JOIN d USING(created_year) ORDER BY 1,4 DESC) TO '{q(shtmp)}' (FORMAT PARQUET,COMPRESSION ZSTD)""");os.replace(shtmp,shares)
  crows=pq.read_table(cov).to_pylist();den=sum(x['usa_records'] for x in crows)
  if den!=cfg['expected_usa_records']:raise RuntimeError('USA record denominator mismatch %d'%den)
  for x in crows:
   if x['usa_records']!=x['valid_code']+x['blank_code']+x['invalid_format']+x['missing_onet_key']:raise RuntimeError('quarter status conservation failed')
  output_bytes=sum(p.stat().st_size for p in (full,major,cov,shares))
  if output_bytes>cfg['max_output_bytes']:raise RuntimeError('output cap exceeded')
  totals={k:sum(x[k] for x in crows) for k in ['usa_records','matched_onet_key','valid_code','blank_code','invalid_format','missing_onet_key']}
  report={'status':'complete','job_id':os.environ.get('SLURM_JOB_ID'),'semantics':'Counts are USA job-ad records by Records.CREATED first-observed cohort and current delivered snapshot O*NET code. They are not historical point-in-time occupations, vacancies, adoption, or AI effects.','inputs':{'onet_files':len(onet),'onet_rows':sum(x['rows'] for x in onet),'records_manifest':rv},'totals':totals,'quarter_rows':len(crows),'full_code_rows':pq.ParquetFile(full).metadata.num_rows,'major_group_rows':pq.ParquetFile(major).metadata.num_rows,'output_bytes':output_bytes,'completed_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
  atomic_json(out/'run_report.json',report);atomic_json(out/'COMPLETE',{'status':'complete','report_sha256':sha(out/'run_report.json')});print(json.dumps(report),flush=True)
 finally:
  if guard:guard.stop()
  if con:con.close()
  if tmp and tmp.exists():shutil.rmtree(tmp)
  os.close(fd)
  if lock.exists():lock.unlink()
if __name__=='__main__':main()
