#!/usr/bin/env python3
"""Resumable, cardinality-audited Records/O*NET join for frozen C1/C2 inputs."""
from __future__ import annotations

import argparse
import concurrent.futures
import glob
import hashlib
import json
import os
import shutil
import tempfile
import fcntl
from pathlib import Path

import pyarrow.parquet as pq

VERSION="comparison_join_v1"
PREFIXES="0123456789abcdef"
SNAPSHOT="2026-09-06"


def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1<<20),b""): h.update(block)
    return h.hexdigest()


def atomic_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=Path(str(path)+".tmp")
    tmp.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n");os.replace(tmp,path)


def q(value): return str(value).replace("'","''")
def sql_files(paths): return ",".join("'%s'"%q(x) for x in paths)


def inventory(paths):
    return [{"path":str(p),"size":Path(p).stat().st_size,"mtime_ns":Path(p).stat().st_mtime_ns} for p in paths]


def same_inputs(left,right):
    return {k:v for k,v in left.items() if k!="script_sha256"}=={k:v for k,v in right.items() if k!="script_sha256"}


def connect(threads,memory,temp_directory=None):
    import duckdb
    con=duckdb.connect();con.execute("SET threads=%d"%threads);con.execute("SET memory_limit='%s'"%q(memory))
    if temp_directory:
        Path(temp_directory).mkdir(parents=True,exist_ok=True);con.execute("SET temp_directory='%s'"%q(temp_directory))
    return con


def parquet_rows(root):
    return sum(pq.ParquetFile(path).metadata.num_rows for path in Path(root).rglob("*.parquet"))


def remove_temps(work_dir,prefix):
    for path in Path(work_dir).glob(prefix+".tmp.*"):
        if path.is_dir(): shutil.rmtree(path)
        else: path.unlink()


def region_case(state="r.STATE"):
    groups={
      "Northeast":"CT,ME,MA,NH,RI,VT,NJ,NY,PA",
      "Midwest":"IN,IL,MI,OH,WI,IA,KS,MN,MO,NE,ND,SD",
      "South":"DE,FL,GA,MD,NC,SC,VA,DC,WV,AL,KY,MS,TN,AR,LA,OK,TX",
      "West":"AZ,CO,ID,NM,MT,UT,NV,WY,AK,CA,HI,OR,WA"}
    clauses=[]
    for label,codes in groups.items(): clauses.append("WHEN upper(trim(%s)) IN (%s) THEN '%s'"%(state,",".join("'%s'"%x for x in codes.split(",")),label))
    return "CASE %s ELSE NULL END"%" ".join(clauses)


def prepare(args,identity,narrow_files,onet_files):
    receipt=args.work_dir/"PREPARE_RECEIPT.json"; candidate_dir=args.work_dir/"candidate_narrow"; onet_dir=args.work_dir/"candidate_onet"
    keys_dir=args.work_dir/"global_job_hash_keys"; duplicate_dir=args.work_dir/"duplicate_job_hashes"; audit_path=args.work_dir/"GLOBAL_JOB_HASH_AUDIT.json"
    onet_receipt=args.work_dir/"CANDIDATE_ONET_RECEIPT.json"
    if receipt.is_file():
        old=json.loads(receipt.read_text())
        if (old.get("identity")==identity and old.get("status")=="complete"
                and candidate_dir.is_dir() and onet_dir.is_dir() and keys_dir.is_dir() and duplicate_dir.is_dir()
                and parquet_rows(candidate_dir)==old.get("candidate_rows")
                and parquet_rows(onet_dir)==old.get("candidate_onet_rows")
                and parquet_rows(keys_dir)==old.get("canonical_narrow_rows")
                and old.get("global_job_hash_audit_sha256")==sha256(audit_path)): return old
        raise RuntimeError("prepare receipt exists with different or incomplete identity")
    con=connect(args.threads,args.memory_limit,args.work_dir/"duckdb_tmp"/"prepare")
    con.execute("CREATE TEMP VIEW narrow AS SELECT * FROM read_parquet([%s],union_by_name=true)"%sql_files(narrow_files))
    required={"JOB_HASH","SOURCE_FILE","SOURCE_ROW","RECORD_SOURCE_ROW","CREATED","usable",
      "tech_generative_ai_use_explicit","tech_generative_ai_develop_explicit","tech_traditional_software_use_explicit","tech_traditional_software_develop_explicit",
      "tech_generative_ai_detected","tech_predictive_ai_detected","tech_unspecified_ai_detected"}
    cols={row[0] for row in con.execute("DESCRIBE narrow").fetchall()}
    if not required<=cols: raise RuntimeError("semantic narrow missing comparison fields: "+str(sorted(required-cols)))
    candidate="(tech_generative_ai_use_explicit OR tech_generative_ai_develop_explicit OR tech_traditional_software_use_explicit OR tech_traditional_software_develop_explicit)"
    totals=con.execute("""SELECT count(*),count(*) FILTER(WHERE %s),
      count(*) FILTER(WHERE JOB_HASH IS NULL OR NOT regexp_full_match(JOB_HASH,'[0-9a-f]{32}')),
      count(*) FILTER(WHERE SOURCE_FILE IS NULL OR trim(SOURCE_FILE)='' OR contains(SOURCE_FILE,'/') OR contains(SOURCE_FILE,'\\\\') OR SOURCE_ROW IS NULL OR SOURCE_ROW<0 OR RECORD_SOURCE_ROW IS NULL OR RECORD_SOURCE_ROW<0)
      FROM narrow"""%candidate).fetchone()
    if totals[2]: raise RuntimeError("semantic narrow contains a noncanonical JOB_HASH; expected exactly 32 lowercase hexadecimal characters")
    if totals[3]: raise RuntimeError("semantic narrow source locator namespace invalid; require basename SOURCE_FILE plus nonnegative SOURCE_ROW and RECORD_SOURCE_ROW")
    audit=None
    try:
        value=json.loads(audit_path.read_text())
        files=value["duplicate_files"]
        if (value.get("status")=="complete" and same_inputs(value.get("identity",{}),identity) and value.get("rows")==totals[0]
                and parquet_rows(keys_dir)==totals[0]
                and all(Path(x["path"]).is_file() and sha256(x["path"])==x["sha256"] for x in files)):
            audit=value
    except (OSError,ValueError,TypeError,KeyError): pass
    if audit is None:
        for target in (keys_dir,duplicate_dir):
            if target.exists(): shutil.rmtree(target)
        if audit_path.exists(): audit_path.unlink()
        remove_temps(args.work_dir,"global_job_hash_keys")
        con.execute("SET threads=1")
        temp=Path(tempfile.mkdtemp(prefix="global_job_hash_keys.tmp.",dir=args.work_dir))
        con.execute("COPY (SELECT JOB_HASH,substr(lower(JOB_HASH),1,1) hash_prefix FROM narrow) TO '%s' (FORMAT PARQUET,COMPRESSION ZSTD,PARTITION_BY(hash_prefix))"%q(temp))
        os.replace(temp,keys_dir); duplicate_dir.mkdir();con.execute("SET threads=%d"%args.threads)
        global_counts={"rows":0,"distinct_job_hashes":0,"duplicate_job_hashes":0,"duplicate_occurrences":0};duplicate_files=[]
        for prefix in PREFIXES:
            source=sorted(glob.glob(str(keys_dir/("hash_prefix="+prefix)/"*.parquet")))
            if not source: raise RuntimeError("global JOB_HASH audit missing prefix "+prefix)
            grouped="SELECT JOB_HASH,count(*) occurrences FROM read_parquet([%s],union_by_name=true) GROUP BY JOB_HASH"%sql_files(source)
            values=con.execute("SELECT coalesce(sum(occurrences),0),count(*),count(*) FILTER(WHERE occurrences>1),coalesce(sum(occurrences) FILTER(WHERE occurrences>1),0) FROM (%s)"%grouped).fetchone()
            for key,value in zip(global_counts,values): global_counts[key]+=value
            target=duplicate_dir/(prefix+".parquet")
            con.execute("COPY (SELECT * FROM (%s) WHERE occurrences>1) TO '%s' (FORMAT PARQUET,COMPRESSION ZSTD)"%(grouped,q(target)))
            duplicate_files.append(str(target))
        if global_counts["rows"]!=totals[0]: raise RuntimeError("global JOB_HASH audit does not conserve narrow rows")
        atomic_json(audit_path,{"status":"complete","identity":identity,**global_counts,
            "resolution":"all occurrences of duplicate JOB_HASH excluded from main comparisons; no trusted full-text digest is present in semantic narrow input",
            "canonical_namespace":"JOB_HASH + basename SOURCE_FILE + SOURCE_ROW + RECORD_SOURCE_ROW; row numbers are never joined without their file/hash namespace",
            "duplicate_files":[{"path":path,"rows":pq.ParquetFile(path).metadata.num_rows,"sha256":sha256(path)} for path in duplicate_files]})
        audit=json.loads(audit_path.read_text())
    global_counts={key:audit[key] for key in ("rows","distinct_job_hashes","duplicate_job_hashes","duplicate_occurrences")}
    duplicate_files=[x["path"] for x in audit["duplicate_files"]]
    con.execute("CREATE TEMP VIEW duplicate_keys AS SELECT JOB_HASH FROM read_parquet([%s],union_by_name=true)"%sql_files(duplicate_files))
    excluded_candidate_rows=con.execute("SELECT count(*) FROM narrow n JOIN duplicate_keys d USING(JOB_HASH) WHERE %s"%candidate).fetchone()[0]
    candidate_rows=totals[1]-excluded_candidate_rows
    if not candidate_dir.is_dir() or parquet_rows(candidate_dir)!=candidate_rows:
        if candidate_dir.exists(): shutil.rmtree(candidate_dir)
        remove_temps(args.work_dir,"candidate_narrow");con.execute("SET threads=1")
        temp=Path(tempfile.mkdtemp(prefix="candidate_narrow.tmp.",dir=args.work_dir))
        con.execute("COPY (SELECT n.*,substr(lower(n.JOB_HASH),1,1) hash_prefix FROM narrow n ANTI JOIN duplicate_keys d USING(JOB_HASH) WHERE %s) TO '%s' (FORMAT PARQUET,COMPRESSION ZSTD,PARTITION_BY(hash_prefix))"%(candidate,q(temp)))
        os.replace(temp,candidate_dir);con.execute("SET threads=%d"%args.threads)
    candidate_prefixes=sorted(path.name.split("=",1)[1] for path in candidate_dir.glob("hash_prefix=*") if path.is_dir())
    if candidate_rows and not candidate_prefixes: raise RuntimeError("candidate partition publication failed")
    con.execute("CREATE TEMP VIEW candidate_keys AS SELECT DISTINCT JOB_HASH FROM read_parquet('%s/*/*.parquet',hive_partitioning=true)"%q(candidate_dir))
    con.execute("CREATE TEMP VIEW onet AS SELECT JOB_HASH,ONET_OCCUPATION_CODE FROM read_parquet([%s],union_by_name=true)"%sql_files(onet_files))
    onet_state=None
    try:
        value=json.loads(onet_receipt.read_text())
        if (value.get("status")=="complete" and value.get("identity")==identity
                and all(Path(x["path"]).is_file() and sha256(x["path"])==x["sha256"] for x in value["files"])): onet_state=value
    except (OSError,ValueError,TypeError,KeyError): pass
    if onet_state is None:
        if onet_dir.exists(): shutil.rmtree(onet_dir)
        if onet_receipt.exists(): onet_receipt.unlink()
        remove_temps(args.work_dir,"candidate_onet");temp=Path(tempfile.mkdtemp(prefix="candidate_onet.tmp.",dir=args.work_dir));all_onet=temp/"candidate_onet_all.parquet"
        con.execute("SET threads=1")
        con.execute("COPY (SELECT o.* FROM onet o JOIN candidate_keys k USING(JOB_HASH)) TO '%s' (FORMAT PARQUET,COMPRESSION ZSTD)"%q(all_onet))
        candidate_onet_rows=pq.ParquetFile(all_onet).metadata.num_rows
        for prefix in candidate_prefixes:
            target=temp/("hash_prefix="+prefix);target.mkdir()
            con.execute("COPY (SELECT * FROM read_parquet('%s') WHERE substr(lower(JOB_HASH),1,1)='%s') TO '%s' (FORMAT PARQUET,COMPRESSION ZSTD)"%(q(all_onet),prefix,q(target/"data.parquet")))
        all_onet.unlink();os.replace(temp,onet_dir)
        files=sorted(onet_dir.rglob("*.parquet"));atomic_json(onet_receipt,{"status":"complete","identity":identity,"rows":candidate_onet_rows,
            "files":[{"path":str(path),"rows":pq.ParquetFile(path).metadata.num_rows,"sha256":sha256(path)} for path in files]})
    else: candidate_onet_rows=onet_state["rows"]
    con.close()
    result={"status":"complete","version":VERSION,"identity":identity,"canonical_narrow_rows":totals[0],"raw_candidate_rows":totals[1],
            "excluded_duplicate_job_hash_candidate_occurrences":excluded_candidate_rows,"candidate_rows":candidate_rows,"global_job_hash_audit":global_counts,
            "global_job_hash_audit_sha256":sha256(audit_path),
            "candidate_prefixes":candidate_prefixes,
            "candidate_onet_rows":candidate_onet_rows,"narrow_files":len(narrow_files),"onet_source_files":len(onet_files),
            "candidate_definition":"any explicit GenAI/traditional-software use/develop role flag"}
    atomic_json(receipt,result);return result


def official_field(path):
    import csv
    with Path(path).open(encoding="utf-8-sig",newline="") as f: names=next(csv.reader(f))
    field=next((x for x in names if x.lower().replace(" ","") in {"o*net-soccode","o*net-soc2019code","onetsoccode","onetsoc2019code","code"}),None)
    if not field: raise RuntimeError("official code file lacks code column")
    return field


def prefix_paths(args,prefix):
    output=args.work_dir/"joined"/(prefix+".parquet");return output,output.with_suffix(".receipt.json")


def prefix_valid(args,prefix,identity):
    output,receipt=prefix_paths(args,prefix)
    try:
        r=json.loads(receipt.read_text())
        return r.get("status")=="complete" and r.get("linkage_accepted") is True and r.get("identity")==identity and r.get("output_sha256")==sha256(output) and pq.ParquetFile(output).metadata.num_rows==r.get("output_rows")
    except (OSError,ValueError,TypeError): return False


def run_prefix(args,prefix,identity,code_field):
    if prefix_valid(args,prefix,identity): return "resumed"
    narrow=sorted(glob.glob(str(args.work_dir/"candidate_narrow"/("hash_prefix="+prefix)/"*.parquet")))
    onet=sorted(glob.glob(str(args.work_dir/"candidate_onet"/("hash_prefix="+prefix)/"*.parquet")))
    records=sorted(glob.glob(str(args.records_root/("hash_prefix="+prefix)/"*.parquet")))
    output,receipt=prefix_paths(args,prefix);output.parent.mkdir(parents=True,exist_ok=True)
    if not narrow:
        raise RuntimeError(prefix+": candidate narrow partition absent")
    if not records: raise RuntimeError(prefix+": Records index partition absent")
    con=connect(1,"1200MB",args.work_dir/"duckdb_tmp"/prefix)
    con.execute("CREATE TEMP VIEW n AS SELECT * EXCLUDE(hash_prefix) FROM read_parquet([%s],union_by_name=true,hive_partitioning=true)"%sql_files(narrow))
    con.execute("CREATE TEMP VIEW r AS SELECT JOB_HASH,RECORD_SOURCE_ROW,COMPANY_ID,try_cast(CREATED AS TIMESTAMP) CREATED,try_cast(LAST_CHECKED AS TIMESTAMP) LAST_CHECKED,try_cast(DELETE_DATE AS TIMESTAMP) DELETE_DATE,STATE FROM read_parquet([%s],union_by_name=true)"%sql_files(records))
    if onet: con.execute("CREATE TEMP VIEW o AS SELECT JOB_HASH,ONET_OCCUPATION_CODE FROM read_parquet([%s],union_by_name=true,hive_partitioning=true)"%sql_files(onet))
    else: con.execute("CREATE TEMP VIEW o AS SELECT NULL::VARCHAR JOB_HASH,NULL::VARCHAR ONET_OCCUPATION_CODE WHERE false")
    con.execute("CREATE TEMP TABLE official AS SELECT trim(cast(\"%s\" AS VARCHAR)) code FROM read_csv_auto('%s',header=true)"%(q(code_field),q(args.official_codes)))
    audit=con.execute("""WITH rc AS (SELECT JOB_HASH,RECORD_SOURCE_ROW,count(*) n FROM r GROUP BY 1,2),oc AS (SELECT JOB_HASH,count(*) n FROM o GROUP BY 1),j AS (
      SELECT n.*,r.COMPANY_ID record_company_id,r.CREATED r_created,r.LAST_CHECKED,r.DELETE_DATE,r.STATE record_state,o.ONET_OCCUPATION_CODE,x.code official_code,
             coalesce(rc.n,0) record_matches,coalesce(oc.n,0) onet_matches
      FROM n LEFT JOIN rc USING(JOB_HASH,RECORD_SOURCE_ROW) LEFT JOIN r USING(JOB_HASH,RECORD_SOURCE_ROW)
      LEFT JOIN oc USING(JOB_HASH) LEFT JOIN o USING(JOB_HASH) LEFT JOIN official x ON trim(o.ONET_OCCUPATION_CODE)=x.code)
      SELECT count(*) joined_rows,count(DISTINCT (JOB_HASH,SOURCE_FILE,SOURCE_ROW,RECORD_SOURCE_ROW)) canonical_rows,
       count(*) FILTER(WHERE record_matches=0),count(*) FILTER(WHERE record_matches=1),count(*) FILTER(WHERE record_matches>1),
       count(*) FILTER(WHERE onet_matches=0),count(*) FILTER(WHERE onet_matches=1),count(*) FILTER(WHERE onet_matches>1),
       count(*) FILTER(WHERE CREATED IS NOT NULL AND r_created IS NOT NULL AND cast(CREATED AS DATE)<>cast(r_created AS DATE)),
       count(*) FILTER(WHERE r_created IS NULL),count(*) FILTER(WHERE official_code IS NULL),count(*) FILTER(WHERE record_state IS NULL),
       count(*) FILTER(WHERE record_state IS NOT NULL AND (%s) IS NULL),count(*) FILTER(WHERE record_company_id IS NULL),
       count(*) FILTER(WHERE r_created IS NULL OR LAST_CHECKED IS NULL OR r_created>LAST_CHECKED OR LAST_CHECKED>TIMESTAMP '%s'),
       count(*) FILTER(WHERE r_created IS NOT NULL AND LAST_CHECKED IS NOT NULL AND DELETE_DATE IS NOT NULL AND r_created<=LAST_CHECKED AND LAST_CHECKED<=DELETE_DATE AND DELETE_DATE<=TIMESTAMP '%s'),
       count(*) FILTER(WHERE LAST_CHECKED IS NOT NULL AND DELETE_DATE IS NOT NULL AND DELETE_DATE<LAST_CHECKED)
      FROM j"""%(region_case("record_state"),SNAPSHOT,SNAPSHOT)).fetchone()
    names=("joined_rows","canonical_rows","records_0","records_1","records_gt1","onet_0","onet_1","onet_gt1","created_disagreement","missing_created","missing_official_occupation","missing_state","unmapped_region","missing_company","crossing_flag_null","valid_closed_interval","stale_delete_or_reappearance")
    report=dict(zip(names,audit)); accepted=report["joined_rows"]==report["canonical_rows"] and report["records_gt1"]==0 and report["onet_gt1"]==0 and report["created_disagreement"]==0
    if not accepted: raise RuntimeError(prefix+": linkage cardinality/CREATED gate failed: "+str(report))
    region=region_case("STATE")
    temp=Path(str(output)+".tmp")
    con.execute("""COPY (WITH rc AS (SELECT JOB_HASH,RECORD_SOURCE_ROW,any_value(COMPANY_ID) COMPANY_ID,any_value(CREATED) CREATED,any_value(LAST_CHECKED) LAST_CHECKED,any_value(DELETE_DATE) DELETE_DATE,any_value(STATE) STATE,count(*) n FROM r GROUP BY 1,2),
      oc AS (SELECT JOB_HASH,any_value(ONET_OCCUPATION_CODE) ONET_OCCUPATION_CODE,count(*) n FROM o GROUP BY 1), j AS (
      SELECT n.* EXCLUDE(CREATED,STATE),r.COMPANY_ID,cast(r.CREATED AS TIMESTAMP) CREATED,r.LAST_CHECKED,r.DELETE_DATE,r.STATE,o.ONET_OCCUPATION_CODE,x.code official_code
      FROM n LEFT JOIN rc r USING(JOB_HASH,RECORD_SOURCE_ROW) LEFT JOIN oc o USING(JOB_HASH) LEFT JOIN official x ON trim(o.ONET_OCCUPATION_CODE)=x.code)
      SELECT j.* EXCLUDE(LAST_CHECKED,DELETE_DATE,STATE,ONET_OCCUPATION_CODE,official_code),substr(official_code,1,2) OCCUPATION_MAJOR,%s CENSUS_REGION,
       CASE WHEN CREATED IS NOT NULL AND LAST_CHECKED IS NOT NULL AND CREATED<=LAST_CHECKED AND LAST_CHECKED<=TIMESTAMP '%s' THEN (CREATED<TIMESTAMP '2022-11-30' AND LAST_CHECKED>=TIMESTAMP '2022-11-30') ELSE NULL END CROSSES_2022_11_30,
       CASE WHEN CREATED IS NOT NULL AND LAST_CHECKED IS NOT NULL AND DELETE_DATE IS NOT NULL AND CREATED<=LAST_CHECKED AND LAST_CHECKED<=DELETE_DATE AND DELETE_DATE<=TIMESTAMP '%s' THEN DELETE_DATE ELSE NULL END OBSERVATION_END,
       CASE WHEN CREATED IS NOT NULL AND LAST_CHECKED IS NOT NULL AND DELETE_DATE IS NOT NULL AND CREATED<=LAST_CHECKED AND LAST_CHECKED<=DELETE_DATE AND DELETE_DATE<=TIMESTAMP '%s' THEN true ELSE false END OBSERVATION_CLOSED,
       CASE WHEN CREATED IS NOT NULL AND LAST_CHECKED IS NOT NULL AND DELETE_DATE IS NOT NULL AND CREATED<=LAST_CHECKED AND LAST_CHECKED<=DELETE_DATE AND DELETE_DATE<=TIMESTAMP '%s' THEN true ELSE false END DATE_COMPLETE,
       CASE WHEN LAST_CHECKED IS NOT NULL AND DELETE_DATE IS NOT NULL THEN DELETE_DATE<LAST_CHECKED ELSE NULL END STALE_DELETE_OR_REAPPEARANCE
      FROM j) TO '%s' (FORMAT PARQUET,COMPRESSION ZSTD,ROW_GROUP_SIZE 65536)"""%(region,SNAPSHOT,SNAPSHOT,SNAPSHOT,SNAPSHOT,q(temp)))
    os.replace(temp,output);con.close();report.update({"status":"complete","version":VERSION,"prefix":prefix,"identity":identity,"linkage_accepted":True,"output_rows":pq.ParquetFile(output).metadata.num_rows,"output_sha256":sha256(output),"date_semantics":"CREATED first observed; LAST_CHECKED last observed present; DELETE_DATE observed absent; not text-effective dates"})
    atomic_json(receipt,report);return "built"


def main():
    p=argparse.ArgumentParser();p.add_argument("--narrow-dir",type=Path,required=True);p.add_argument("--narrow-batch-receipt",type=Path,required=True);p.add_argument("--source-manifest",type=Path,required=True)
    p.add_argument("--records-root",type=Path,required=True);p.add_argument("--onet-glob",required=True);p.add_argument("--official-codes",type=Path,required=True);p.add_argument("--work-dir",type=Path,required=True)
    p.add_argument("--threads",type=int,default=8);p.add_argument("--memory-limit",default="16GB");p.add_argument("--expected-shards",type=int,default=2464);args=p.parse_args()
    if not 1<=args.threads<=8: raise SystemExit("threads must be 1..8")
    args.work_dir.mkdir(parents=True,exist_ok=True)
    lock=(args.work_dir/".comparison_join.lock").open("w")
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        raise RuntimeError("another comparison join is already using this work-dir")
    narrow=sorted(str(x) for x in args.narrow_dir.glob("*.parquet") if not x.name.endswith(".durations.parquet"));onet=sorted(glob.glob(args.onet_glob))
    batch=json.loads(args.narrow_batch_receipt.read_text())
    batch_count_ok=(batch.get("shards")==args.expected_shards)
    if args.expected_shards==1 and batch.get("canonical_ads") is not None and len(narrow)==1:
        batch_count_ok=(pq.ParquetFile(narrow[0]).metadata.num_rows==batch.get("canonical_ads"))
    if batch.get("status")!="complete" or not batch_count_ok or len(narrow)!=args.expected_shards: raise RuntimeError("complete exact expected-shard narrow input required")
    identity={"script_sha256":sha256(Path(__file__)),"expected_shards":args.expected_shards,"narrow_batch_receipt_sha256":sha256(args.narrow_batch_receipt),"source_manifest_sha256":sha256(args.source_manifest),
              "official_codes_sha256":sha256(args.official_codes),"records_complete_sha256":sha256(args.records_root/"COMPLETE"),
              "narrow_file_inventory_sha256":hashlib.sha256(json.dumps(inventory(narrow),sort_keys=True).encode()).hexdigest(),"onet_file_inventory_sha256":hashlib.sha256(json.dumps(inventory(onet),sort_keys=True).encode()).hexdigest()}
    config=args.work_dir/"RUN_CONFIG.json"
    if config.exists():
        old_config=json.loads(config.read_text())
        if old_config!=identity:
            if not same_inputs(old_config,identity): raise RuntimeError("join work-dir input identity changed")
            atomic_json(args.work_dir/"SCRIPT_RECOVERY.json",{"status":"approved_io_only_recovery","prior_script_sha256":old_config["script_sha256"],"current_script_sha256":identity["script_sha256"]})
            atomic_json(config,identity)
    else: atomic_json(config,identity)
    prep=prepare(args,identity,narrow,onet);field=official_field(args.official_codes);actions={"built":0,"resumed":0};active=prep["candidate_prefixes"]
    if not active: raise RuntimeError("no comparison-arm candidate rows after duplicate-JOB_HASH isolation")
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as pool:
        futures=[pool.submit(run_prefix,args,prefix,identity,field) for prefix in active]
        for future in concurrent.futures.as_completed(futures): actions[future.result()]+=1
    if not all(prefix_valid(args,prefix,identity) for prefix in active): raise RuntimeError("not all active prefix joins verified")
    receipts=[json.loads(prefix_paths(args,p)[1].read_text()) for p in active]; files=[prefix_paths(args,p)[0] for p in active]
    manifest={"status":"complete","version":VERSION,"identity":identity,"prefixes":len(active),"candidate_prefixes":active,"canonical_narrow_rows":prep["canonical_narrow_rows"],
              "global_job_hash_audit":prep["global_job_hash_audit"],"raw_candidate_rows":prep["raw_candidate_rows"],
              "excluded_duplicate_job_hash_candidate_occurrences":prep["excluded_duplicate_job_hash_candidate_occurrences"],
              "candidate_rows":prep["candidate_rows"],"output_rows":sum(x["output_rows"] for x in receipts),
              "records_matches":{"0":sum(x["records_0"] for x in receipts),"1":sum(x["records_1"] for x in receipts),">1":sum(x["records_gt1"] for x in receipts)},
              "onet_matches":{"0":sum(x["onet_0"] for x in receipts),"1":sum(x["onet_1"] for x in receipts),">1":sum(x["onet_gt1"] for x in receipts)},
              "created_disagreement":sum(x["created_disagreement"] for x in receipts),"missing_created":sum(x["missing_created"] for x in receipts),
              "missing_official_occupation":sum(x["missing_official_occupation"] for x in receipts),"missing_state":sum(x["missing_state"] for x in receipts),
              "unmapped_region":sum(x["unmapped_region"] for x in receipts),"missing_company":sum(x["missing_company"] for x in receipts),
              "crossing_flag_null":sum(x["crossing_flag_null"] for x in receipts),"valid_closed_interval":sum(x["valid_closed_interval"] for x in receipts),
              "stale_delete_or_reappearance":sum(x["stale_delete_or_reappearance"] for x in receipts),"actions":actions,
              "files":[{"path":str(x),"rows":pq.ParquetFile(x).metadata.num_rows,"size":x.stat().st_size,"sha256":sha256(x)} for x in files],
              "limits":["current delivered snapshot O*NET occupation; not historical occupation evidence","Records dates are observation metadata; not text-effective dates","COMPANY_ID is a company-scrape entity, not a verified legal firm or consolidated group"]}
    if manifest["output_rows"]!=manifest["candidate_rows"] or manifest["records_matches"][">1"] or manifest["onet_matches"][">1"]: raise RuntimeError("final join conservation failed")
    atomic_json(args.work_dir/"JOIN_MANIFEST.json",manifest)


if __name__=="__main__":main()
