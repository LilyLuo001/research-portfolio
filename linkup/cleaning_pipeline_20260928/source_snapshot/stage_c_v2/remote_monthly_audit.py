#!/usr/bin/env python3
"""Single-scan calendar audit of the raw remote support table."""
import argparse,datetime as dt,glob,hashlib,json,os
from pathlib import Path
import duckdb,pyarrow.parquet as pq

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def atomic_json(p,x):
 t=Path(str(p)+'.tmp');t.write_text(json.dumps(x,indent=2,sort_keys=True,default=str)+'\n');os.replace(t,p)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--out',required=True);ap.add_argument('--threads',type=int,default=8);a=ap.parse_args()
 out=Path(a.out);out.mkdir(parents=True,exist_ok=True); lock=out/'.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
 try:
  files=sorted(glob.glob(a.source));
  if not files:raise RuntimeError('remote source glob empty')
  manifest=[]
  for x in files:
   p=Path(x);pf=pq.ParquetFile(p);manifest.append({'name':p.name,'bytes':p.stat().st_size,'rows':pf.metadata.num_rows,'schema':str(pf.schema_arrow)})
  identity={'code_sha256':sha(__file__),'source_fingerprint':hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()}
  ip=out/'identity.json'
  if ip.exists() and json.loads(ip.read_text())!=identity:raise RuntimeError('output identity mismatch')
  atomic_json(ip,identity);atomic_json(out/'source_manifest.json',manifest)
  con=duckdb.connect();con.execute('SET threads=%d'%a.threads);con.execute("SET memory_limit='7GB'")
  tmp=out/'remote_start_month.parquet.tmp';final=out/'remote_start_month.parquet'
  src=a.source.replace("'","''");dst=str(tmp).replace("'","''")
  con.execute(f"""COPY (WITH b AS (SELECT REMOTE_STATUS,REMOTE_DETAIL,START_DATE,END_DATE,
    try_cast(nullif(trim(START_DATE),'') AS TIMESTAMP) s,try_cast(nullif(trim(END_DATE),'') AS TIMESTAMP) e
    FROM read_parquet('{src}',union_by_name=true))
   SELECT date_trunc('month',s) start_month,REMOTE_STATUS,REMOTE_DETAIL,
    CASE WHEN START_DATE IS NULL OR trim(START_DATE)='' THEN 'missing' WHEN s IS NULL THEN 'invalid' ELSE 'parsed' END start_parse_status,
    CASE WHEN END_DATE IS NULL OR trim(END_DATE)='' THEN 'open_or_missing' WHEN e IS NULL THEN 'invalid' ELSE 'parsed' END end_parse_status,
    count(*) row_count,min(s) min_parsed_start,max(s) max_parsed_start,min(e) min_parsed_end,max(e) max_parsed_end
   FROM b GROUP BY 1,2,3,4,5) TO '{dst}' (FORMAT PARQUET,COMPRESSION ZSTD)""")
  os.replace(tmp,final);t=pq.read_table(final)
  if final.stat().st_size>100_000_000:raise RuntimeError('monthly output exceeds 100MB')
  rows=t.to_pylist();total=sum(x['row_count'] for x in rows);expected=sum(x['rows'] for x in manifest)
  if total!=expected:raise RuntimeError('row conservation failed')
  by_start={};by_status={}
  for x in rows:
   by_start[x['start_parse_status']]=by_start.get(x['start_parse_status'],0)+x['row_count']
   k='NULL' if x['REMOTE_STATUS'] is None else str(x['REMOTE_STATUS']).lower();by_status[k]=by_status.get(k,0)+x['row_count']
  report={'status':'complete','source_files':len(files),'source_rows':expected,'aggregate_rows':len(rows),'start_parse_counts':by_start,'remote_status_counts':by_status,
   'min_parsed_start':min((x['min_parsed_start'] for x in rows if x['min_parsed_start'] is not None),default=None),
   'max_parsed_start':max((x['max_parsed_start'] for x in rows if x['max_parsed_start'] is not None),default=None),
   'min_parsed_end':min((x['min_parsed_end'] for x in rows if x['min_parsed_end'] is not None),default=None),
   'max_parsed_end':max((x['max_parsed_end'] for x in rows if x['max_parsed_end'] is not None),default=None),
   'interpretation':'Calendar distribution of support-table rows only. REMOTE_STATUS=false means not tagged remote, not confirmed onsite. It is not historical label coverage for job CREATED cohorts.',
   'completed_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'output_sha256':sha(final)}
  atomic_json(out/'remote_monthly_report.json',report);atomic_json(out/'COMPLETE',{'status':'complete','report_sha256':sha(out/'remote_monthly_report.json')});print(json.dumps(report,default=str),flush=True)
 finally:
  os.close(fd)
  if lock.exists():lock.unlink()
if __name__=='__main__':main()
