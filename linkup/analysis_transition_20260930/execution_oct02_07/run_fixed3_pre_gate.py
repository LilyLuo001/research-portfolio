#!/usr/bin/env python3
"""Run the frozen builder on a fixed published-intersection diagnostic3 manifest."""
import argparse, hashlib, json, os, subprocess, sys, time
from pathlib import Path

def load(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def atomic(p, value):
    p=Path(p); t=Path(str(p)+".tmp"); t.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n"); os.replace(t,p)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--manifest",type=Path,required=True)
    ap.add_argument("--builder",type=Path,required=True); ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args(); rows=[json.loads(x) for x in a.manifest.read_text().splitlines() if x.strip()]
    if len(rows)!=3 or {r["region"] for r in rows}!={"kunshan","wuzhen"}: raise RuntimeError("fixed3 region/count mismatch")
    if len({r["shard_id"] for r in rows})!=3: raise RuntimeError("fixed3 duplicate shard")
    a.output.mkdir(parents=True,exist_ok=False); (a.output/"summaries").mkdir(); started=time.time(); summaries=[]
    for r in rows:
        shard=Path(r["shard_dir"]); receipt=Path(r["receipt"]); complete=shard/"SHARD_COMPLETE.json"
        wrap=load(receipt)
        if wrap.get("status")!="published_verified" or wrap.get("shard_id")!=r["shard_id"]: raise RuntimeError("receipt identity mismatch")
        if not complete.is_file() or sha(complete)!=wrap.get("shard_complete_sha256") or load(complete)!=wrap.get("shard_complete"): raise RuntimeError("SHARD_COMPLETE mismatch")
        target=a.output/"summaries"/(r["shard_id"]+".json")
        subprocess.run([sys.executable,str(a.builder),"shard","--shard-dir",str(shard),"--receipt",str(receipt),"--output",str(target)],check=True)
        summaries.append(target)
    tables=a.output/"tables"
    subprocess.run([sys.executable,str(a.builder),"merge","--summaries",*map(str,summaries),"--output-dir",str(tables)],check=True)
    report=load(tables/"CONSERVATION_REPORT.json")
    if report.get("status")!="complete" or report.get("shards")!=3: raise RuntimeError("merge conservation failed")
    atomic(a.output/"PRE_GATE_DIAGNOSTIC3_RECEIPT.json",{"status":"complete","acceptance_status":"pre_gate_diagnostic_not_global_acceptance",
      "selection":"lowest SHA256(seed:shard_id) within the 2418-shard published intersection at freeze time; one KS, one WZ, then next global; no semantic output used",
      "seed":"oct02-release-first-pilot-v1","shard_ids":[r["shard_id"] for r in rows],"builder_sha256":sha(a.builder),
      "manifest_sha256":sha(a.manifest),"conservation_report_sha256":sha(tables/"CONSERVATION_REPORT.json"),"wall_seconds":time.time()-started,
      "interpretation":"technology x experience cells are ad-level candidate co-occurrence, not proof that a technology binds a specific experience requirement"})
if __name__=="__main__": main()
