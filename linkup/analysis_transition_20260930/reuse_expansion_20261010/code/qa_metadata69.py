#!/usr/bin/env python3
"""Independent bounded-memory QA for the D67 69-shard metadata union."""
import argparse, collections, hashlib, importlib.util, json, os, shutil
from pathlib import Path
import pyarrow.parquet as pq

PREFIXES=tuple("0123456789abcdef");EXPECTED=5804936

def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()

def base_load(p):
 s=importlib.util.spec_from_file_location("d67qbase",p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def main():
 p=argparse.ArgumentParser();p.add_argument("--metadata",required=True);p.add_argument("--receipt",required=True);p.add_argument("--base-code",required=True);p.add_argument("--first5-key-dir",required=True);p.add_argument("--key64-dir",required=True);p.add_argument("--work",required=True);p.add_argument("--output",required=True);a=p.parse_args()
 base=base_load(a.base_code);rec=json.load(open(a.receipt));meta=Path(a.metadata)
 if rec.get("status")!="complete" or rec.get("output_rows")!=EXPECTED or rec.get("output_sha256")!=sha(meta):raise RuntimeError("metadata receipt binding failed")
 work=Path(a.work);shutil.rmtree(work,ignore_errors=True);work.mkdir(parents=True)
 paths={x:work/("actual_%s.parquet"%x) for x in PREFIXES};writers={x:pq.ParquetWriter(paths[x],base.KEY_SCHEMA,compression="zstd") for x in PREFIXES};buffers={x:[] for x in PREFIXES}
 counts=collections.Counter();rows=0
 cols=list(base.CANONICAL_KEY)+["POSTING_CREATED","RECORD_STATE","records_join_status","onet_join_status","company_status","geography_status","official_occupation_status","created_alignment_status"]
 try:
  for batch in pq.ParquetFile(meta).iter_batches(batch_size=65536,columns=cols):
   for row in base.arrow_rows(batch):
    pref=row["JOB_HASH"][0];buffers[pref].append({"JOB_HASH":row["JOB_HASH"],"SOURCE_FILE":row["SOURCE_FILE"],"SOURCE_ROW":row["SOURCE_ROW"],"RECORD_SOURCE_ROW":row["RECORD_SOURCE_ROW"],"POSTING_CREATED":row["POSTING_CREATED"],"POSTING_STATE":row["RECORD_STATE"]})
    for name in ("records_join_status","onet_join_status","company_status","geography_status","official_occupation_status","created_alignment_status"):counts[name+":"+str(row[name])]+=1
    rows+=1
    if len(buffers[pref])>=8192:writers[pref].write_table(base.rows_table(buffers[pref],base.KEY_SCHEMA));buffers[pref]=[]
  for pref in PREFIXES:
   if buffers[pref]:writers[pref].write_table(base.rows_table(buffers[pref],base.KEY_SCHEMA))
   writers[pref].close()
 except Exception:
  for w in writers.values():
   try:w.close()
   except Exception:pass
  raise
 errors=[];unique=0
 for pref in PREFIXES:
  expected=set()
  for root in (Path(a.first5_key_dir),Path(a.key64_dir)):
   for batch in pq.ParquetFile(root/("keys_%s.parquet"%pref)).iter_batches(batch_size=32768,columns=list(base.CANONICAL_KEY)):
    expected.update(tuple(r[x] for x in base.CANONICAL_KEY) for r in base.arrow_rows(batch))
  actual=[]
  for batch in pq.ParquetFile(paths[pref]).iter_batches(batch_size=32768,columns=list(base.CANONICAL_KEY)):
   actual.extend(tuple(r[x] for x in base.CANONICAL_KEY) for r in base.arrow_rows(batch))
  aset=set(actual);unique+=len(aset)
  if len(aset)!=len(actual):errors.append(pref+":duplicate")
  if aset!=expected:errors.append(pref+":key_set_mismatch")
 cardinality=(counts["records_join_status:one_to_many_unresolved"]+counts["onet_join_status:one_to_many_unresolved"])
 disagreements=counts["created_alignment_status:calendar_date_disagreement"]
 partitions={name:sum(v for k,v in counts.items() if k.startswith(name+":")) for name in ("records_join_status","onet_join_status","company_status","geography_status","official_occupation_status","created_alignment_status")}
 checks={"row_conservation_5804936":rows==EXPECTED,"canonical_keys_unique_and_exact_target":unique==EXPECTED and not errors,
  "all_status_partitions_conserve_denominator":all(v==EXPECTED for v in partitions.values()),"no_unresolved_one_to_many":cardinality==0,
  "no_created_calendar_disagreement":disagreements==0,"output_hash_bound":True}
 result={"version":"d67-metadata69-independent-qa-v1","status":"pass" if all(checks.values()) else "fail","checks":checks,"rows":rows,"status_partition_sums":partitions,"errors":errors[:50],"scope":"Engineering metadata linkage QA; no semantic validation or historical-text claim."}
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);tmp=Path(str(out)+".tmp");tmp.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n");os.replace(tmp,out)
 if result["status"]!="pass":raise SystemExit("metadata QA failed")
if __name__=="__main__":main()
