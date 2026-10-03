#!/usr/bin/env python3
"""Build full-frame T4 observation-risk aggregates and bounded annual keys."""
from __future__ import annotations
import argparse,csv,fcntl,glob,hashlib,json,os,shutil,tempfile,threading,time
from pathlib import Path
import pyarrow.parquet as pq
VERSION='full_time_risk_v2';PREFIXES='0123456789abcdef';SNAPSHOT='2026-09-06';SEED='20261003'
GIB=1<<30;_SPACE_BASELINES={}
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def q(x):return str(x).replace("'","''")
def sql_files(xs):return ','.join("'%s'"%q(x) for x in xs)
def atomic_json(p,v):
 p=Path(p);t=Path(str(p)+'.tmp');t.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n');os.replace(t,p)
def tree_bytes(path):
 total=0
 for base,dirs,files in os.walk(path):
  for name in files:
   try:total+=os.stat(os.path.join(base,name),follow_symlinks=False).st_size
   except FileNotFoundError:pass
 return total
class GuardedConnection:
 def __init__(self,con,temp,scope,monitor):
  self._con=con;self._temp=Path(temp);self._scope=Path(scope);self._stop=threading.Event();self._violation=None;self.space_monitor_active=monitor
  if monitor:
   key=str(self._scope.resolve());_SPACE_BASELINES.setdefault(key,tree_bytes(self._scope));self._baseline=_SPACE_BASELINES[key]
   self._thread=threading.Thread(target=self._watch,name='t4-space-monitor',daemon=True);self._thread.start()
  else:self._thread=None
 def _watch(self):
  while not self._stop.wait(1.0):
   temp_bytes=tree_bytes(self._temp);added=max(0,tree_bytes(self._scope)-self._baseline);free=shutil.disk_usage(self._scope).free
   if temp_bytes>4*GIB:self._violation='T4 temp directory exceeded 4GiB soft limit'
   elif added>20*GIB:self._violation='T4 work-directory growth exceeded 20GiB soft limit'
   elif free<8*GIB:self._violation='filesystem free space fell below 8GiB reserve'
   if self._violation:
    self._con.interrupt();return
 def execute(self,*args,**kwargs):
  if self._violation:
   message=self._violation;self.close();raise RuntimeError(message+'; completion receipt not written')
  try:return self._con.execute(*args,**kwargs)
  except Exception as e:
   if self._violation:
    self.close();raise RuntimeError(self._violation+'; current DuckDB operation interrupted, completion receipt not written') from e
   raise
 def close(self):
  self._stop.set()
  if self._thread and self._thread is not threading.current_thread():self._thread.join(timeout=2)
  return self._con.close()
 def __getattr__(self,name):return getattr(self._con,name)
def connect(threads,memory,temp):
 import duckdb
 temp=Path(temp);scope=temp.parent.parent;temp.mkdir(parents=True,exist_ok=True);c=duckdb.connect();c.execute('SET threads=%d'%threads);c.execute("SET memory_limit='%s'"%q(memory));c.execute("SET temp_directory='%s'"%q(temp));supported=True
 try:c.execute("SET max_temp_directory_size='4GB'")
 except duckdb.CatalogException as e:
  if 'unrecognized configuration parameter' not in str(e).lower():raise
  supported=False
 return GuardedConnection(c,temp,scope,not supported)
def query_rows(c,s):
 cur=c.execute(s);names=[x[0] for x in cur.description];return [dict(zip(names,x)) for x in cur.fetchall()]
def write_csv(p,data,fields=None):
 if not data and not fields:return
 t=Path(str(p)+'.tmp')
 with t.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields or list(data[0]));w.writeheader();w.writerows(data)
 os.replace(t,p)
def inventory_sha(paths):return hashlib.sha256(json.dumps([{'path':x,'size':Path(x).stat().st_size,'mtime_ns':Path(x).stat().st_mtime_ns} for x in paths],sort_keys=True).encode()).hexdigest()
def norm(alias):return "trim(regexp_replace(regexp_replace(lower(%s.TITLE),'[[:punct:]]+',' ','g'),'\\s+',' ','g'))"%alias
def annual_candidate_sql(raw,key_glob,dups,groups,seed):
 n=norm('r')
 return """WITH k AS (SELECT JOB_HASH FROM read_parquet('%s',hive_partitioning=true) ANTI JOIN (SELECT JOB_HASH FROM read_parquet([%s],union_by_name=true)) USING(JOB_HASH)),g AS (SELECT * FROM read_parquet('%s')),x AS (SELECT r.JOB_HASH,r.COMPANY_ID,r.TITLE,%s normalized_title,r.CITY,try_cast(r.CREATED AS TIMESTAMP) CREATED,try_cast(r.LAST_UPDATED AS TIMESTAMP) LAST_UPDATED,try_cast(r.LAST_CHECKED AS TIMESTAMP) LAST_CHECKED,try_cast(r.DELETE_DATE AS TIMESTAMP) DELETE_DATE,r.BASE_HASH,r.URL,row_number() OVER(PARTITION BY r.COMPANY_ID,%s,r.CITY,date_part('year',try_cast(r.CREATED AS TIMESTAMP)) ORDER BY md5(r.JOB_HASH||'%s')) yrank FROM read_parquet([%s],union_by_name=true) r JOIN k USING(JOB_HASH) JOIN g ON r.COMPANY_ID=g.COMPANY_ID AND %s=g.normalized_title AND r.CITY=g.CITY WHERE upper(trim(r.COUNTRY)) IN ('US','USA','UNITED STATES')) SELECT * EXCLUDE(yrank) FROM x WHERE yrank<=3 ORDER BY md5(cast(COMPANY_ID AS VARCHAR)||'|'||normalized_title||'|'||CITY||'|%s'),CREATED,md5(JOB_HASH||'%s') LIMIT 200"""%(key_glob,sql_files(dups),q(groups),n,n,seed,sql_files(raw),n,seed,seed)
def main():
 p=argparse.ArgumentParser();p.add_argument('--narrow-dir',type=Path,required=True);p.add_argument('--narrow-batch-receipt',type=Path,required=True);p.add_argument('--global-key-audit',type=Path,required=True);p.add_argument('--global-key-dir',type=Path,required=True);p.add_argument('--duplicate-dir',type=Path,required=True);p.add_argument('--records-index-root',type=Path,required=True);p.add_argument('--raw-records-glob',required=True);p.add_argument('--onet-glob',required=True);p.add_argument('--official-codes',type=Path,required=True);p.add_argument('--work-dir',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--threads',type=int,default=8);p.add_argument('--memory-limit',default='12GB');a=p.parse_args()
 a.work_dir.mkdir(parents=True,exist_ok=True);a.output_dir.mkdir(parents=True,exist_ok=True);lock=(a.work_dir/'.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 narrow=sorted(str(x) for x in a.narrow_dir.glob('*.parquet') if not x.name.endswith('.durations.parquet'));raw=sorted(glob.glob(a.raw_records_glob));onet=sorted(glob.glob(a.onet_glob));dups=sorted(str(x) for x in a.duplicate_dir.glob('*.parquet'));keyfiles=sorted(str(x) for x in a.global_key_dir.rglob('*.parquet'))
 required={'JOB_HASH','COMPANY_ID','TITLE','CITY','COUNTRY','CREATED','LAST_UPDATED','LAST_CHECKED','DELETE_DATE','BASE_HASH','URL'};actual=set(pq.ParquetFile(raw[0]).schema_arrow.names)
 if not required<=actual:raise RuntimeError('raw Records missing '+','.join(sorted(required-actual)))
 batch=json.loads(a.narrow_batch_receipt.read_text());audit=json.loads(a.global_key_audit.read_text())
 if batch.get('status')!='complete' or batch.get('shards')!=2464 or len(narrow)!=2464:raise RuntimeError('exact complete 2,464-shard narrow batch required')
 if audit.get('status')!='complete' or audit.get('rows')!=204774035 or len(dups)!=16 or not keyfiles:raise RuntimeError('complete full global JOB_HASH audit/partitions required')
 identity={'script_sha256':sha(__file__),'batch_receipt_sha256':sha(a.narrow_batch_receipt),'global_key_audit_sha256':sha(a.global_key_audit),'global_key_inventory_sha256':inventory_sha(keyfiles),'records_complete_sha256':sha(a.records_index_root/'COMPLETE'),'official_codes_sha256':sha(a.official_codes),'raw_inventory_sha256':inventory_sha(raw),'onet_inventory_sha256':inventory_sha(onet)}
 cfg=a.work_dir/'RUN_CONFIG.json'
 if cfg.exists() and json.loads(cfg.read_text())!=identity:raise RuntimeError('T4 work-dir identity changed')
 if not cfg.exists():atomic_json(cfg,identity)
 import csv as _csv
 with a.official_codes.open(encoding='utf-8-sig',newline='') as f:names=next(_csv.reader(f))
 field=next(x for x in names if x.lower().replace(' ','') in {'o*net-soccode','o*net-soc2019code','onetsoccode','onetsoc2019code','code'})
 summaries=a.work_dir/'prefix_summaries';summaries.mkdir(exist_ok=True)
 for prefix in PREFIXES:
  done=summaries/(prefix+'.receipt.json');outputs=[summaries/(prefix+s) for s in ('.cohort.parquet','.concentration.parquet')]
  try:
   old=json.loads(done.read_text())
   if old.get('identity')==identity and all(x.is_file() and sha(x)==old['outputs'][i]['sha256'] for i,x in enumerate(outputs)):continue
  except (OSError,ValueError,TypeError,KeyError,IndexError):pass
  for x in outputs+[done]:
   if x.exists():x.unlink()
  k=glob.glob(str(a.global_key_dir/('hash_prefix='+prefix)/'*.parquet'));d=[str(a.duplicate_dir/(prefix+'.parquet'))];r=glob.glob(str(a.records_index_root/('hash_prefix='+prefix)/'*.parquet'))
  c=connect(a.threads,a.memory_limit,a.work_dir/'duckdb_tmp'/prefix);c.execute("CREATE VIEW k0 AS SELECT JOB_HASH FROM read_parquet([%s],hive_partitioning=true)"%sql_files(k));c.execute("CREATE VIEW d AS SELECT JOB_HASH FROM read_parquet([%s])"%sql_files(d));c.execute('CREATE VIEW k AS SELECT JOB_HASH FROM k0 ANTI JOIN d USING(JOB_HASH)');c.execute("CREATE VIEW r AS SELECT * EXCLUDE(hash_prefix) FROM read_parquet([%s],hive_partitioning=true)"%sql_files(r));c.execute("CREATE VIEW o AS SELECT JOB_HASH,ONET_OCCUPATION_CODE FROM read_parquet([%s],union_by_name=true) WHERE substr(lower(JOB_HASH),1,1)='%s'"%(sql_files(onet),prefix));c.execute("CREATE TABLE official AS SELECT trim(cast(\"%s\" AS VARCHAR)) code FROM read_csv_auto('%s',header=true)"%(field.replace('"','""'),q(a.official_codes)))
  base="""WITH rc AS (SELECT JOB_HASH,any_value(COMPANY_ID) COMPANY_ID,any_value(STATE) STATE,any_value(try_cast(CREATED AS TIMESTAMP)) CREATED,any_value(try_cast(LAST_CHECKED AS TIMESTAMP)) LAST_CHECKED,any_value(try_cast(DELETE_DATE AS TIMESTAMP)) DELETE_DATE,count(*) matches FROM r GROUP BY 1),oc AS (SELECT JOB_HASH,any_value(ONET_OCCUPATION_CODE) OCC,count(*) matches FROM o GROUP BY 1),j AS (SELECT k.JOB_HASH,rc.*,oc.OCC,oc.matches onet_matches,x.code official_code FROM k LEFT JOIN rc USING(JOB_HASH) LEFT JOIN oc USING(JOB_HASH) LEFT JOIN official x ON trim(oc.OCC)=x.code) SELECT * FROM j"""
  auditrow=query_rows(c,"SELECT count(*) rows,count(*) FILTER(WHERE matches IS NULL) records_0,count(*) FILTER(WHERE matches=1) records_1,count(*) FILTER(WHERE matches>1) records_gt1,count(*) FILTER(WHERE onet_matches IS NULL) onet_0,count(*) FILTER(WHERE onet_matches=1) onet_1,count(*) FILTER(WHERE onet_matches>1) onet_gt1 FROM (%s)"%base)[0]
  if auditrow['records_gt1'] or auditrow['onet_gt1']:raise RuntimeError('T4 one-to-many in prefix '+prefix)
  c.execute('CREATE VIEW j AS '+base);valid="CREATED IS NOT NULL AND LAST_CHECKED IS NOT NULL AND CREATED<=LAST_CHECKED AND LAST_CHECKED<=TIMESTAMP '%s'"%SNAPSHOT;risk="count(*) ads,count(*) FILTER(WHERE %s) valid_interval_ads,count(*) FILTER(WHERE NOT (%s) OR (%s) IS NULL) invalid_or_incomplete_interval_ads,count(*) FILTER(WHERE %s AND date_trunc('quarter',CREATED)<>date_trunc('quarter',LAST_CHECKED)) crosses_quarter_ads,count(*) FILTER(WHERE %s AND date_part('year',CREATED)<>date_part('year',LAST_CHECKED)) crosses_year_ads,count(*) FILTER(WHERE %s AND CREATED<TIMESTAMP '2022-11-30' AND LAST_CHECKED>=TIMESTAMP '2022-11-30') crosses_2022_11_30_ads,count(*) FILTER(WHERE %s AND CREATED<TIMESTAMP '2023-01-01' AND LAST_CHECKED>=TIMESTAMP '2023-01-01') crosses_2023_01_01_ads"%(valid,valid,valid,valid,valid,valid,valid)
  c.execute("COPY (SELECT date_part('year',CREATED)::INTEGER created_year,date_part('quarter',CREATED)::INTEGER created_quarter,%s FROM j GROUP BY 1,2) TO '%s' (FORMAT PARQUET)"%(risk,q(outputs[0])));c.execute("COPY (SELECT 'company_id' dimension,cast(COMPANY_ID AS VARCHAR) dimension_value,%s FROM j WHERE COMPANY_ID IS NOT NULL GROUP BY 1,2 UNION ALL SELECT 'state',cast(STATE AS VARCHAR),%s FROM j WHERE STATE IS NOT NULL GROUP BY 1,2 UNION ALL SELECT 'occupation_major',substr(official_code,1,2),%s FROM j WHERE official_code IS NOT NULL GROUP BY 1,2) TO '%s' (FORMAT PARQUET)"%(risk,risk,risk,q(outputs[1])))
  riskrow=query_rows(c,"SELECT count(*) canonical_ads,count(*) FILTER(WHERE matches=1) records_matched,count(*) FILTER(WHERE CREATED IS NULL) missing_created,count(*) FILTER(WHERE LAST_CHECKED IS NULL) missing_last_checked,count(*) FILTER(WHERE %s) valid_main_interval,count(*) FILTER(WHERE %s AND date_trunc('quarter',CREATED)<>date_trunc('quarter',LAST_CHECKED)) crosses_quarter,count(*) FILTER(WHERE %s AND date_part('year',CREATED)<>date_part('year',LAST_CHECKED)) crosses_year,count(*) FILTER(WHERE %s AND CREATED<TIMESTAMP '2022-11-30' AND LAST_CHECKED>=TIMESTAMP '2022-11-30') crosses_2022_11_30,count(*) FILTER(WHERE %s AND CREATED<TIMESTAMP '2023-01-01' AND LAST_CHECKED>=TIMESTAMP '2023-01-01') crosses_2023_01_01,count(*) FILTER(WHERE DELETE_DATE<LAST_CHECKED) stale_delete_or_reappearance FROM j"%(valid,valid,valid,valid,valid))[0];c.close();atomic_json(done,{'status':'complete','identity':identity,'prefix':prefix,'linkage':auditrow,'risk':riskrow,'outputs':[{'path':str(x),'sha256':sha(x)} for x in outputs]})
 con=connect(a.threads,a.memory_limit,a.work_dir/'duckdb_tmp'/'merge');keyglob=str(a.global_key_dir/'hash_prefix=*'/'*.parquet');counts=a.work_dir/'T4_ANNUAL_GROUP_COUNTS_PRIVATE.parquet'
 if counts.exists():counts.unlink()
 n=norm('r');con.execute("COPY (WITH k AS (SELECT JOB_HASH FROM read_parquet('%s',hive_partitioning=true) ANTI JOIN (SELECT JOB_HASH FROM read_parquet([%s],union_by_name=true)) USING(JOB_HASH)) SELECT r.COMPANY_ID,%s normalized_title,r.CITY,date_part('year',try_cast(r.CREATED AS TIMESTAMP))::INTEGER created_year,count(DISTINCT r.JOB_HASH) distinct_job_hashes FROM read_parquet([%s],union_by_name=true) r JOIN k USING(JOB_HASH) WHERE upper(trim(r.COUNTRY)) IN ('US','USA','UNITED STATES') AND r.COMPANY_ID IS NOT NULL AND r.TITLE IS NOT NULL AND trim(r.TITLE)<>'' AND r.CITY IS NOT NULL AND trim(r.CITY)<>'' AND r.CREATED IS NOT NULL GROUP BY 1,2,3,4) TO '%s' (FORMAT PARQUET,COMPRESSION ZSTD)"%(q(keyglob),sql_files(dups),n,sql_files(raw),q(counts)))
 if counts.stat().st_size>16*(1<<30):raise RuntimeError('private annual aggregate exceeds 16GiB post-write acceptance gate')
 groups=a.work_dir/'T4_SELECTED_ANNUAL_GROUPS_PRIVATE.parquet';
 if groups.exists():groups.unlink()
 con.execute("COPY (SELECT COMPANY_ID,normalized_title,CITY,count(DISTINCT created_year) years FROM read_parquet('%s') GROUP BY 1,2,3 HAVING count(DISTINCT created_year)>=3 ORDER BY md5(cast(COMPANY_ID AS VARCHAR)||'|'||normalized_title||'|'||CITY||'|%s') LIMIT 20) TO '%s' (FORMAT PARQUET)"%(q(counts),SEED,q(groups)))
 selectedbase=a.work_dir/'T4_SELECTED_ANNUAL_BASE_PRIVATE.parquet'
 if selectedbase.exists():selectedbase.unlink()
 con.execute("COPY (%s) TO '%s' (FORMAT PARQUET)"%(annual_candidate_sql(raw,keyglob,dups,groups,SEED),q(selectedbase)))
 con.execute("CREATE VIEW n AS SELECT JOB_HASH,SOURCE_FILE,SOURCE_ROW,RECORD_SOURCE_ROW,usable FROM read_parquet([%s],union_by_name=true)"%sql_files(narrow));con.execute("CREATE TABLE official AS SELECT trim(cast(\"%s\" AS VARCHAR)) code FROM read_csv_auto('%s',header=true)"%(field.replace('"','""'),q(a.official_codes)))
 selected=query_rows(con,"""WITH s AS (SELECT * FROM read_parquet('%s')),oo AS (SELECT o.JOB_HASH,o.ONET_OCCUPATION_CODE FROM read_parquet([%s],union_by_name=true) o JOIN s USING(JOB_HASH)) SELECT s.*,n.SOURCE_FILE,n.SOURCE_ROW,n.RECORD_SOURCE_ROW,n.usable,substr(x.code,1,2) OCCUPATION_MAJOR FROM s JOIN n USING(JOB_HASH) LEFT JOIN oo USING(JOB_HASH) LEFT JOIN official x ON trim(oo.ONET_OCCUPATION_CODE)=x.code"""%(q(selectedbase),sql_files(onet)))
 if len(selected)!=pq.ParquetFile(selectedbase).metadata.num_rows:raise RuntimeError('selected enrichment expanded/lost rows')
 private=a.work_dir/'T4_SELECTED_ANNUAL_KEYS_PRIVATE.csv';fields=['COMPANY_ID','TITLE','normalized_title','CITY','JOB_HASH','CREATED','LAST_UPDATED','LAST_CHECKED','DELETE_DATE','BASE_HASH','URL','SOURCE_FILE','SOURCE_ROW','RECORD_SOURCE_ROW','usable','OCCUPATION_MAJOR'];write_csv(private,selected,fields)
 cohorts=glob.glob(str(summaries/'*.cohort.parquet'));concs=glob.glob(str(summaries/'*.concentration.parquet'));receipts=[json.loads((summaries/(x+'.receipt.json')).read_text()) for x in PREFIXES]
 write_csv(a.output_dir/'T4_TIME_RISK.csv',[{'metric':k,'numerator':sum(x['risk'][k] for x in receipts),'denominator':sum(x['risk']['valid_main_interval'] for x in receipts) if k.startswith('crosses_') else sum(x['risk']['canonical_ads'] for x in receipts),'interpretation':'delivery observation interval; not text-effective or rewrite timing'} for k in receipts[0]['risk']])
 cohort=query_rows(con,"SELECT created_year,created_quarter,sum(ads)::BIGINT ads,sum(valid_interval_ads)::BIGINT valid_interval_ads,sum(invalid_or_incomplete_interval_ads)::BIGINT invalid_or_incomplete_interval_ads,sum(crosses_quarter_ads)::BIGINT crosses_quarter_ads,sum(crosses_year_ads)::BIGINT crosses_year_ads,sum(crosses_2022_11_30_ads)::BIGINT crosses_2022_11_30_ads,sum(crosses_2023_01_01_ads)::BIGINT crosses_2023_01_01_ads FROM read_parquet([%s]) GROUP BY 1,2 ORDER BY 1,2"%sql_files(cohorts))
 for row in cohort:
  for m in ('crosses_quarter','crosses_year','crosses_2022_11_30','crosses_2023_01_01'):row[m+'_rate_among_valid']=row[m+'_ads']/row['valid_interval_ads'] if row['valid_interval_ads'] else None
  row['period_status']='partial_quarter_through_2026-09-06' if row['created_year']==2026 and row['created_quarter']==3 else 'complete_calendar_period_in_delivery_not_coverage_guarantee'
 write_csv(a.output_dir/'T4_CREATED_COHORT.csv',cohort);annual=query_rows(con,"SELECT created_year,count(*) group_years,sum(distinct_job_hashes)::BIGINT distinct_job_hashes FROM read_parquet('%s') GROUP BY 1 ORDER BY 1"%q(counts));write_csv(a.output_dir/'T4_ANNUAL_COVERAGE.csv',annual)
 g={}
 for x in selected:g.setdefault((x['COMPANY_ID'],x['normalized_title'],x['CITY']),[]).append(x)
 gs=[]
 for i,items in enumerate(g.values(),1):
  parents={str(x['BASE_HASH']) for x in items if x.get('BASE_HASH') not in (None,'')};hashes={x['JOB_HASH'] for x in items};years={str(x['CREATED'])[:4] for x in items};gs.append({'anonymous_group_id':'annual_group_%02d'%i,'created_years':len(years),'selected_job_hashes':len(hashes),'selected_distinct_parent_listing_hashes':len(parents) if parents else None,'parent_listing_shared_across_selected_keys':'observed' if parents and len(parents)<len(hashes) else 'not_observed_or_unavailable','interpretation':'BASE_HASH links parent listings/multi-location splits; not a content digest'})
 write_csv(a.output_dir/'T4_SELECTED_ANNUAL_GROUP_SUMMARY.csv',gs,['anonymous_group_id','created_years','selected_job_hashes','selected_distinct_parent_listing_hashes','parent_listing_shared_across_selected_keys','interpretation'])
 total=sum(x['risk']['canonical_ads'] for x in receipts);grouped="SELECT dimension,dimension_value,sum(ads)::DOUBLE ads,sum(valid_interval_ads)::DOUBLE valid_interval_ads,sum(invalid_or_incomplete_interval_ads)::DOUBLE invalid_or_incomplete_interval_ads,sum(crosses_quarter_ads)::DOUBLE crosses_quarter_ads,sum(crosses_year_ads)::DOUBLE crosses_year_ads,sum(crosses_2022_11_30_ads)::DOUBLE crosses_2022_11_30_ads,sum(crosses_2023_01_01_ads)::DOUBLE crosses_2023_01_01_ads FROM read_parquet([%s]) GROUP BY 1,2"%sql_files(concs)
 summary=query_rows(con,"WITH g AS (%s),r AS (SELECT *,sum(ads) OVER(PARTITION BY dimension) mapped_ads,row_number() OVER(PARTITION BY dimension ORDER BY ads DESC,dimension_value) rn FROM g) SELECT dimension,count(*) categories,max(mapped_ads)::BIGINT mapped_ads,sum(power(ads/mapped_ads,2)) hhi,max(ads)/max(mapped_ads) top1_share,sum(ads) FILTER(WHERE rn<=10)/max(mapped_ads) top10_share FROM r GROUP BY dimension ORDER BY dimension"%grouped)
 for x in summary:x['canonical_ads_denominator']=total;x['missing_or_unmapped_ads']=total-x['mapped_ads']
 top=query_rows(con,"WITH g AS (%s),r AS (SELECT *,sum(ads) OVER(PARTITION BY dimension) mapped_ads,row_number() OVER(PARTITION BY dimension ORDER BY ads DESC,dimension_value) rank FROM g) SELECT dimension,rank,dimension_value,cast(ads AS BIGINT) ads,ads/mapped_ads share_within_mapped,cast(valid_interval_ads AS BIGINT) valid_interval_ads,cast(invalid_or_incomplete_interval_ads AS BIGINT) invalid_or_incomplete_interval_ads,cast(crosses_quarter_ads AS BIGINT) crosses_quarter_ads,crosses_quarter_ads/nullif(valid_interval_ads,0) crosses_quarter_rate_among_valid,cast(crosses_year_ads AS BIGINT) crosses_year_ads,crosses_year_ads/nullif(valid_interval_ads,0) crosses_year_rate_among_valid,cast(crosses_2022_11_30_ads AS BIGINT) crosses_2022_11_30_ads,crosses_2022_11_30_ads/nullif(valid_interval_ads,0) crosses_2022_11_30_rate_among_valid,cast(crosses_2023_01_01_ads AS BIGINT) crosses_2023_01_01_ads,crosses_2023_01_01_ads/nullif(valid_interval_ads,0) crosses_2023_01_01_rate_among_valid FROM r WHERE rank<=20 ORDER BY dimension,rank"%grouped)
 for x in top:
  if x['dimension']=='company_id':x['dimension_value']='company_rank_%02d'%x['rank']
 write_csv(a.output_dir/'T4_CONCENTRATION.csv',summary);write_csv(a.output_dir/'T4_CONCENTRATION_TOP20.csv',top)
 outputs={x.name:sha(x) for x in a.output_dir.glob('T4_*.csv')};atomic_json(a.output_dir/'T4_RECEIPT.json',{'status':'complete','version':VERSION,'identity':identity,'outputs':outputs,'private_annual_counts':{'path':str(counts),'sha256':sha(counts),'post_write_acceptance_gate_bytes':16*(1<<30)},'private_selected_keys':{'path':str(private),'rows':len(selected),'sha256':sha(private)},'space_plan':'reuse global key and Records partitions; no O*NET or raw row-level projection; unsupported DuckDB temp quota uses an in-process 1-second soft-limit monitor','limits':['16GiB annual-aggregate check is post-write acceptance, not a filesystem quota','DuckDB 0.9.2 soft monitor interrupts at temp>4GiB, workdir growth>20GiB, or filesystem free<8GiB; sampling interval permits bounded overshoot','observation dates are not text-effective dates','new JOB_HASH is not an archived historical body version','BASE_HASH is not a content digest','current snapshot occupation mapping']})
if __name__=='__main__':main()
