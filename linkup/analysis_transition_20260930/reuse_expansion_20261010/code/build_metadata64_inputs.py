#!/usr/bin/env python3
"""Bind the 64 non-first-five key projections after the small WZ-to-KS transfer."""
import argparse, hashlib, json, os
from pathlib import Path

FIRST5={"b605d84d410013b1","b9376a87ec3e8b7c","fc4fc3a546b62738","3d07a85fc3160eed","41305ab79b0f9fcd"}

def sha(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()

def main():
 p=argparse.ArgumentParser();p.add_argument("--frozen",required=True);p.add_argument("--wz-dir",required=True);p.add_argument("--ks-dir",required=True);p.add_argument("--output",required=True);a=p.parse_args()
 frozen=json.load(open(a.frozen));files=[]
 for shard in frozen["shards"]:
  if shard["short_id"] in FIRST5:continue
  root=Path(a.wz_dir if shard["region"]=="wuzhen" else a.ks_dir);sid=shard["shard_id"]
  path=root/(sid+".keys.parquet");receipt_path=root/(sid+".keys.receipt.json");receipt=json.load(open(receipt_path))
  if receipt.get("status")!="complete" or receipt.get("shard_id")!=sid or receipt.get("output_rows")!=shard["posting_rows"]:raise RuntimeError("key receipt mismatch "+sid)
  if receipt.get("output_sha256")!=sha(path):raise RuntimeError("key projection SHA mismatch "+sid)
  files.append({"shard_id":sid,"short_id":shard["short_id"],"region":shard["region"],"path":str(path),"sha256":receipt["output_sha256"],"rows":receipt["output_rows"],"receipt":str(receipt_path)})
 if len(files)!=64 or sum(x["rows"] for x in files)!=5380710:raise RuntimeError("metadata64 target denominator mismatch")
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);tmp=Path(str(out)+".tmp");tmp.write_text(json.dumps({"version":"d67-metadata64-inputs-v1","status":"ready","files":files,"rows":5380710},indent=2,sort_keys=True)+"\n");os.replace(tmp,out)
if __name__=="__main__":main()
