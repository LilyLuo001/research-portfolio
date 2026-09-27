#!/usr/bin/env python3
"""Bounded, read-only audit of LinkUp O*NET and remote support tables."""
import argparse, datetime as dt, hashlib, json, os, shutil, threading, time
from pathlib import Path
import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

PFX='0123456789abcdef'

def atomic_json(path,obj):
 p=Path(path); t=Path(str(p)+'.tmp'); t.write_text(json.dumps(obj,indent=2,sort_keys=True,default=str)+'\n'); os.replace(t,p)
def sha(path):
 h=hashlib.sha256(); h.update(Path(path).read_bytes()); return h.hexdigest()
def tree_bytes(path): return sum(p.stat().st_size for p in Path(path).rglob('*') if p.is_file())
def file_manifest(globpat):
 files=sorted(Path().glob(globpat) if not globpat.startswith('/') else Path(globpat.split('*')[0]).parent.glob(Path(globpat).name))
 # Absolute glob robustly handled by glob module.
 import glob
 files=[Path(x) for x in sorted(glob.glob(globpat))]
 out=[]
 for p in files:
  pf=pq.ParquetFile(p); out.append({'path':str(p),'name':p.name,'bytes':p.stat().st_size,'rows':pf.metadata.num_rows,'row_groups':pf.metadata.num_row_groups,'schema':str(pf.schema_arrow)})
 return out
def fp(items):
 stable=[(x['name'],x['bytes'],x['rows'],x['schema']) for x in items]
 return hashlib.sha256(json.dumps(stable,sort_keys=True).encode()).hexdigest()
def qpath(path): return str(path).replace("'","''")
def rows_dict(cur):
 names=[x[0] for x in cur.description]; return [dict(zip(names,r)) for r in cur.fetchall()]
def cap(root,n,kind):
 b=tree_bytes(root)
 if b>n: raise RuntimeError('%s cap exceeded: %d > %d'%(kind,b,n))
 return b

class ScratchGuard:
 def __init__(self,root,limit,con):self.root=Path(root);self.limit=limit;self.con=con;self.exceeded=None;self.stop_event=threading.Event();self.thread=threading.Thread(target=self._run,daemon=True)
 def _run(self):
  while not self.stop_event.wait(2):
   try:
    used=tree_bytes(self.root)
    if used>self.limit:self.exceeded=used;self.con.interrupt();return
   except Exception:pass
 def start(self):self.thread.start()
 def check(self):
  if self.exceeded is not None:raise RuntimeError('scratch cap exceeded: %d > %d'%(self.exceeded,self.limit))
 def stop(self):self.stop_event.set();self.thread.join(timeout=3)

def partition(con, source_glob, dest, cols, max_tmp):
 dest=Path(dest)
 if (dest/'COMPLETE.json').exists(): return json.loads((dest/'COMPLETE.json').read_text())
 if dest.exists(): shutil.rmtree(dest)
 dest.mkdir(parents=True)
 colsql=', '.join(cols)
 sql=f"""COPY (SELECT CASE WHEN regexp_full_match(lower(coalesce(JOB_HASH,'')), '^[0-9a-f]{{32}}$') THEN substr(lower(JOB_HASH),1,1) ELSE 'invalid' END AS prefix, {colsql}
 FROM read_parquet('{qpath(source_glob)}', union_by_name=true)) TO '{qpath(dest)}' (FORMAT PARQUET, COMPRESSION ZSTD, PARTITION_BY (prefix), ROW_GROUP_SIZE 262144)"""
 con.execute(sql)
 b=cap(dest,max_tmp,'temporary partition')
 files=list(dest.rglob('*.parquet')); n=sum(pq.ParquetFile(p).metadata.num_rows for p in files)
 mark={'status':'complete','rows':n,'bytes':b,'files':len(files)}; atomic_json(dest/'COMPLETE.json',mark); return mark

def audit_prefix(con,prefix,recroot,onetroot,remoteroot):
 op=str(Path(onetroot)/('prefix='+prefix)/'*.parquet'); rp=str(Path(remoteroot)/('prefix='+prefix)/'*.parquet')
 rec=str(Path(recroot)/('hash_prefix='+prefix)/'*.parquet')
 onet_summary=rows_dict(con.execute(f"""
 WITH g AS (SELECT JOB_HASH,count(*) n_rows,count(ONET_OCCUPATION_CODE) n_nonnull,
 count(DISTINCT nullif(trim(ONET_OCCUPATION_CODE),'')) n_codes,
 sum(CASE WHEN ONET_OCCUPATION_CODE IS NOT NULL AND trim(ONET_OCCUPATION_CODE)<>'' AND regexp_full_match(trim(ONET_OCCUPATION_CODE),'^[0-9]{{2}}-[0-9]{{4}}(\\.[0-9]{{2}})?$') THEN 1 ELSE 0 END) n_format
 FROM read_parquet('{qpath(op)}') WHERE JOB_HASH IS NOT NULL GROUP BY JOB_HASH)
 SELECT '{prefix}' prefix,(SELECT count(*) FROM read_parquet('{qpath(op)}')) raw_rows,
 (SELECT count(*) FROM read_parquet('{qpath(op)}') WHERE JOB_HASH IS NULL) null_hash_rows,
 (SELECT count(*) FROM read_parquet('{qpath(op)}') WHERE JOB_HASH IS NOT NULL AND NOT regexp_full_match(lower(JOB_HASH),'^[0-9a-f]{{32}}$')) malformed_hash_rows,
 count(*) distinct_job_hashes,count(*) FILTER (WHERE n_rows>1) duplicate_job_hashes,count(*) FILTER (WHERE n_codes>1) conflicting_code_jobs,
 count(*) FILTER (WHERE n_codes=0) jobs_without_nonempty_code,count(*) FILTER (WHERE n_format>0) jobs_with_format_conforming_code FROM g
 """))[0]
 onet_coverage=rows_dict(con.execute(f"""
 WITH o AS (SELECT JOB_HASH,count(DISTINCT nullif(trim(ONET_OCCUPATION_CODE),'')) n_codes,
 max(CASE WHEN ONET_OCCUPATION_CODE IS NOT NULL AND trim(ONET_OCCUPATION_CODE)<>'' THEN 1 ELSE 0 END) has_code,
 max(CASE WHEN regexp_full_match(trim(coalesce(ONET_OCCUPATION_CODE,'')),'^[0-9]{{2}}-[0-9]{{4}}(\\.[0-9]{{2}})?$') THEN 1 ELSE 0 END) format_ok
 FROM read_parquet('{qpath(op)}') WHERE JOB_HASH IS NOT NULL GROUP BY JOB_HASH),
 r AS (SELECT JOB_HASH,CREATED FROM read_parquet('{qpath(rec)}') WHERE COUNTRY='USA')
 SELECT year(CREATED) created_year,quarter(CREATED) created_quarter,count(*) denominator,
 count(o.JOB_HASH) matched_job_hash,count(*) FILTER (WHERE has_code=1) nonempty_code,
 count(*) FILTER (WHERE n_codes=1) unique_code,count(*) FILTER (WHERE format_ok=1) format_conforming
 FROM r LEFT JOIN o USING(JOB_HASH) GROUP BY 1,2 ORDER BY 1,2
 """))
 remote_summary=rows_dict(con.execute(f"""
 WITH b AS (SELECT *,try_cast(nullif(trim(START_DATE),'') AS TIMESTAMP) s,try_cast(nullif(trim(END_DATE),'') AS TIMESTAMP) e FROM read_parquet('{qpath(rp)}')),
 g AS (SELECT JOB_HASH,count(*) n_rows,count(DISTINCT concat(coalesce(cast(REMOTE_STATUS AS VARCHAR),'NULL'),'|',coalesce(REMOTE_DETAIL,'NULL'))) n_labels FROM b WHERE JOB_HASH IS NOT NULL GROUP BY JOB_HASH),
 v AS (SELECT *,max(e) OVER(PARTITION BY JOB_HASH ORDER BY s,e ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) prior_max_end FROM b WHERE JOB_HASH IS NOT NULL AND s IS NOT NULL AND e IS NOT NULL AND e>=s)
 SELECT '{prefix}' prefix,(SELECT count(*) FROM b) raw_rows,(SELECT count(*) FROM b WHERE JOB_HASH IS NULL) null_hash_rows,
 (SELECT count(*) FROM b WHERE JOB_HASH IS NOT NULL AND NOT regexp_full_match(lower(JOB_HASH),'^[0-9a-f]{{32}}$')) malformed_hash_rows,
 (SELECT count(*) FROM b WHERE START_DATE IS NULL OR trim(START_DATE)='') missing_start_rows,
 (SELECT count(*) FROM b WHERE START_DATE IS NOT NULL AND trim(START_DATE)<>'' AND s IS NULL) invalid_start_rows,
 (SELECT count(*) FROM b WHERE END_DATE IS NULL OR trim(END_DATE)='') open_end_rows,
 (SELECT count(*) FROM b WHERE END_DATE IS NOT NULL AND trim(END_DATE)<>'' AND e IS NULL) invalid_end_rows,
 (SELECT count(*) FROM b WHERE s IS NOT NULL AND e IS NOT NULL AND e<s) negative_interval_rows,
 (SELECT count(*) FROM v WHERE prior_max_end IS NOT NULL AND s<prior_max_end) strict_overlap_rows,
 (SELECT count(*) FROM v WHERE prior_max_end IS NOT NULL AND s=prior_max_end) touching_interval_rows,
 (SELECT count(*) FROM b o WHERE o.JOB_HASH IS NOT NULL AND o.s IS NOT NULL AND (o.END_DATE IS NULL OR trim(o.END_DATE)='') AND EXISTS (SELECT 1 FROM b n WHERE n.JOB_HASH=o.JOB_HASH AND n.s>o.s)) open_end_with_later_start_rows,
 (SELECT count(*) FROM g) distinct_job_hashes,(SELECT count(*) FILTER (WHERE n_rows>1) FROM g) duplicate_job_hashes,
 (SELECT count(*) FILTER (WHERE n_labels>1) FROM g) jobs_with_multiple_labels
 """))[0]
 remote_coverage=rows_dict(con.execute(f"""
 WITH x AS (SELECT JOB_HASH,count(*) n_rows,
 max(CASE WHEN REMOTE_STATUS IS NOT NULL OR nullif(trim(REMOTE_DETAIL),'') IS NOT NULL THEN 1 ELSE 0 END) has_label
 FROM read_parquet('{qpath(rp)}') WHERE JOB_HASH IS NOT NULL GROUP BY JOB_HASH),
 r AS (SELECT JOB_HASH,CREATED FROM read_parquet('{qpath(rec)}') WHERE COUNTRY='USA')
 SELECT year(CREATED) created_year,quarter(CREATED) created_quarter,count(*) denominator,
 count(x.JOB_HASH) matched_job_hash,count(*) FILTER (WHERE has_label=1) nonempty_label
 FROM r LEFT JOIN x USING(JOB_HASH) GROUP BY 1,2 ORDER BY 1,2
 """))
 onet_conflicts=rows_dict(con.execute(f"""SELECT JOB_HASH,count(*) raw_rows,count(DISTINCT nullif(trim(ONET_OCCUPATION_CODE),'')) distinct_codes,
 list(DISTINCT ONET_OCCUPATION_CODE) codes FROM read_parquet('{qpath(op)}') WHERE JOB_HASH IS NOT NULL GROUP BY JOB_HASH HAVING distinct_codes>1 ORDER BY md5(JOB_HASH) LIMIT 10"""))
 remote_conflicts=rows_dict(con.execute(f"""SELECT JOB_HASH,count(*) raw_rows,count(DISTINCT concat(coalesce(cast(REMOTE_STATUS AS VARCHAR),'NULL'),'|',coalesce(REMOTE_DETAIL,'NULL'))) distinct_labels,
 list(DISTINCT concat(coalesce(cast(REMOTE_STATUS AS VARCHAR),'NULL'),'|',coalesce(REMOTE_DETAIL,'NULL'))) labels FROM read_parquet('{qpath(rp)}') WHERE JOB_HASH IS NOT NULL GROUP BY JOB_HASH HAVING distinct_labels>1 ORDER BY md5(JOB_HASH) LIMIT 10"""))
 return onet_summary,onet_coverage,remote_summary,remote_coverage,onet_conflicts,remote_conflicts

def invalid_partition_metrics(con,root,kind):
 pattern=str(Path(root)/'prefix=invalid'/'*.parquet')
 if not list((Path(root)/'prefix=invalid').glob('*.parquet')): return {'raw_rows':0,'null_hash_rows':0,'malformed_hash_rows':0}
 return rows_dict(con.execute(f"SELECT count(*) raw_rows,count(*) FILTER (WHERE JOB_HASH IS NULL) null_hash_rows,count(*) FILTER (WHERE JOB_HASH IS NOT NULL) malformed_hash_rows FROM read_parquet('{qpath(pattern)}')"))[0]

def aggregate_coverage(rows, fields):
 out={}
 for r in rows:
  k=(r['created_year'],r['created_quarter']); z=out.setdefault(k,{x:0 for x in fields})
  z.update({'created_year':r['created_year'],'created_quarter':r['created_quarter']})
  for x in fields:z[x]+=r[x]
 return [out[k] for k in sorted(out,key=lambda x:((-9999 if x[0] is None else x[0]),(-1 if x[1] is None else x[1])))]

def verify_records_complete(path):
 p=Path(path); marker=json.loads(p.read_text()); mp=p.parent/marker.get('manifest','index_manifest.json')
 if marker.get('sha256')!=sha(mp):raise RuntimeError('records COMPLETE manifest hash mismatch')
 m=json.loads(mp.read_text())
 if m.get('status')!='complete' or m.get('rows')!=m.get('output_footer_rows'):raise RuntimeError('records manifest incomplete')
 return {'complete_sha256':sha(p),'manifest_sha256':sha(mp),'rows':m['rows'],'columns':m['columns']}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);a=ap.parse_args(); cfg=json.loads(Path(a.config).read_text())
 out=Path(cfg['output_dir']);out.mkdir(parents=True,exist_ok=True); lock=out/'.lock'
 fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
 try:
  onet=file_manifest(cfg['onet_glob']); remote=file_manifest(cfg['remote_glob'])
  if not onet or not remote: raise RuntimeError('support source glob empty')
  records_validation=verify_records_complete(cfg['records_complete'])
  identity={'code_sha256':sha(Path(__file__)),'config_sha256':sha(a.config),'onet_fingerprint':fp(onet),'remote_fingerprint':fp(remote),'records':records_validation}
  ip=out/'identity.json'
  if ip.exists() and json.loads(ip.read_text())!=identity: raise RuntimeError('output identity mismatch; use new output_dir')
  atomic_json(ip,identity); atomic_json(out/'source_manifest.json',{'onet':onet,'remote':remote})
  token=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:12]+'_'+os.environ.get('SLURM_JOB_ID','local')
  tmp=Path(os.environ.get('SLURM_TMPDIR',cfg['tmp_root']))/('linkup_support_'+token); tmp.mkdir(parents=True,exist_ok=True)
  if shutil.disk_usage(tmp).free < cfg['min_tmp_free_bytes']:raise RuntimeError('node scratch has less than required free space')
  con=duckdb.connect(str(tmp/'audit.duckdb'));con.execute("SET threads=%d"%cfg['threads']);con.execute("SET memory_limit='%s'"%cfg['memory_limit']);con.execute("SET temp_directory='%s'"%qpath(tmp/'spill'))
  guard=ScratchGuard(tmp,cfg['max_tmp_bytes'],con);guard.start()
  print(json.dumps({'phase':'partition_onet','files':len(onet),'rows':sum(x['rows'] for x in onet)}),flush=True)
  om=partition(con,cfg['onet_glob'],tmp/'onet',['JOB_HASH','ONET_OCCUPATION_CODE'],cfg['max_tmp_bytes'])
  guard.check()
  print(json.dumps({'phase':'partition_remote','files':len(remote),'rows':sum(x['rows'] for x in remote)}),flush=True)
  rm=partition(con,cfg['remote_glob'],tmp/'remote',['JOB_HASH','START_DATE','END_DATE','REMOTE_STATUS','REMOTE_DETAIL'],cfg['max_tmp_bytes'])
  guard.check()
  cap(tmp,cfg['max_tmp_bytes'],'total scratch')
  allparts=[]; oc=[]; rs=[]; rc=[]; osamp=[]; rsamp=[]
  for p in PFX:
   a1,a2,a3,a4,a5,a6=audit_prefix(con,p,cfg['records_index'],tmp/'onet',tmp/'remote'); allparts.append(a1);oc+=a2;rs.append(a3);rc+=a4;osamp+=a5;rsamp+=a6
   atomic_json(out/'progress.json',{'status':'running','completed_prefixes':p,'updated_utc':dt.datetime.now(dt.timezone.utc).isoformat()});print(json.dumps({'phase':'prefix_complete','prefix':p}),flush=True)
   guard.check()
  oc=aggregate_coverage(oc,['denominator','matched_job_hash','nonempty_code','unique_code','format_conforming'])
  rc=aggregate_coverage(rc,['denominator','matched_job_hash','nonempty_label'])
  if sum(x['denominator'] for x in oc)!=sum(x['denominator'] for x in rc):raise RuntimeError('USA records denominator differs between support audits')
  for x in oc:
   if not (x['matched_job_hash']<=x['denominator'] and x['unique_code']<=x['matched_job_hash']):raise RuntimeError('ONET coverage invariant failed')
  for x in rc:
   if not (x['matched_job_hash']<=x['denominator']):raise RuntimeError('remote coverage invariant failed')
  pq.write_table(pa.Table.from_pylist(oc),out/'onet_usa_created_coverage.parquet',compression='zstd')
  pq.write_table(pa.Table.from_pylist(rc),out/'remote_usa_created_membership.parquet',compression='zstd')
  atomic_json(out/'onet_conflict_sample.json',osamp[:100]);atomic_json(out/'remote_conflict_sample.json',rsamp[:100])
  invalid={'onet':invalid_partition_metrics(con,tmp/'onet','onet'),'remote':invalid_partition_metrics(con,tmp/'remote','remote')}
  if sum(x['raw_rows'] for x in allparts)+invalid['onet']['raw_rows']!=om['rows']:raise RuntimeError('ONET partition conservation failed')
  if sum(x['raw_rows'] for x in rs)+invalid['remote']['raw_rows']!=rm['rows']:raise RuntimeError('remote partition conservation failed')
  report={'status':'complete','semantics':{'onet_code':'format conformity is not validation against an O*NET release; O*NET version timing is unconfirmed and codes are not treated as historical classifications','remote':'membership coverage only; remote intervals are not assumed to be historical label validity; REMOTE_STATUS=false means not tagged remote and does not confirm onsite work','overlap':'strict overlap uses next_start < prior_max_end; touching uses equality and is reported separately; open ends are not forced closed','multiple_labels':'jobs_with_multiple_labels can reflect changes across disjoint dates; overlapping different-label pairs are not established by this audit'},'source':{'onet_files':len(onet),'onet_rows':sum(x['rows'] for x in onet),'remote_files':len(remote),'remote_rows':sum(x['rows'] for x in remote),'onet_schema':sorted(set(x['schema'] for x in onet)),'remote_schema':sorted(set(x['schema'] for x in remote))},'records_validation':records_validation,'usa_records_denominator':sum(x['denominator'] for x in oc),'partition':{'onet':om,'remote':rm},'invalid_hash_partition':invalid,'onet_prefix_metrics':allparts,'remote_prefix_metrics':rs,'output_bytes':cap(out,cfg['max_output_bytes'],'persistent output'),'completed_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
  atomic_json(out/'support_audit_report.json',report);atomic_json(out/'COMPLETE',{'status':'complete','report_sha256':sha(out/'support_audit_report.json')});print(json.dumps({'status':'complete','output':str(out)}),flush=True)
  guard.stop();con.close();shutil.rmtree(tmp)
 finally:
  os.close(fd)
  if lock.exists():lock.unlink()
if __name__=='__main__':main()
