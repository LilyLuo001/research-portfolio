#!/usr/bin/env python3
"""Scheduled metadata-only preflight for the Formal800 fixed10k cache."""
import argparse, collections, datetime as dt, hashlib, json, os, platform
from pathlib import Path
import pyarrow.parquet as pq

def sha(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--frame",required=True);p.add_argument("--output",required=True);a=p.parse_args()
 pf=pq.ParquetFile(a.frame); cols=pf.schema_arrow.names
 required=["arm","exact_text_sha256","original_text","total_inclusion_probability","nested_design_weight","JOB_HASH","SOURCE_FILE","SOURCE_ROW","RECORD_SOURCE_ROW"]
 missing=[x for x in required if x not in cols]
 arm_counts=collections.Counter()
 if not missing:
  for b in pf.iter_batches(batch_size=8192,columns=["arm"]):arm_counts.update(b.column(0).to_pylist())
 out={"version":"formal800-preflight-v1","status":"pass" if not missing else "fail_missing_columns","scheduler":{"job_id":os.getenv("SLURM_JOB_ID"),"host":platform.node()},"created_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"frame":{"path":a.frame,"sha256":sha(a.frame),"rows":pf.metadata.num_rows,"columns":cols,"missing_required_columns":missing,"arm_counts":dict(arm_counts)},"purpose":"metadata-only cache footer and arm-marginal check; no exclusion calculation, sampling, packet output, model inference, or semantic processing","privacy":"no row identities or text emitted"}
 target=Path(a.output);target.parent.mkdir(parents=True,exist_ok=True);tmp=Path(str(target)+".tmp");tmp.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n");os.replace(tmp,target)
if __name__=="__main__":main()
