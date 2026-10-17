#!/usr/bin/env python3
"""Record an unrecoverable disposition after the one source-locator attempt failed."""
import argparse, datetime as dt, hashlib, json, os
from pathlib import Path

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()
def rows(path):
    with open(path,encoding="utf-8") as f:
        for line in f:
            if line.strip(): yield json.loads(line)
def atomic(path,value,lines=False):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); tmp=Path(str(path)+".tmp")
    with open(tmp,"w",encoding="utf-8") as f:
        if lines:
            for x in value: f.write(json.dumps(x,sort_keys=True,separators=(",",":"))+"\n")
        else: f.write(json.dumps(value,indent=2,sort_keys=True)+"\n")
    os.chmod(str(tmp),0o600); os.replace(str(tmp),str(path))
def main():
    p=argparse.ArgumentParser()
    for n in ("attempt_marker","claim_manifest","packet","source_map","failed_job_stderr","receipt","isolation_register"):
        p.add_argument("--"+n.replace("_","-"),required=True)
    a=p.parse_args()
    if not Path(a.attempt_marker).is_file() or Path(a.receipt).exists(): raise RuntimeError("missing unique failed attempt or receipt already exists")
    target="fixed10k-prod-b004-084"
    m=next(x for x in rows(a.claim_manifest) if x["record_id"]==target)
    packet=next(x for x in rows(a.packet) if x["record_id"]==target)
    if m["context_sha256"]!=packet["context_sha256"]: raise RuntimeError("target binding mismatch")
    error=Path(a.failed_job_stderr).read_text(encoding="utf-8",errors="replace")
    if "target source shard absent from frozen locator" not in error: raise RuntimeError("failed attempt reason not verified")
    isolation=[{"record_id":target,"normalized_context_sha256":packet["context_sha256"],"status":"source_truncated_unrecoverable","work_queue_excluded":True,"ledger_changed":False,"original_queue_changed":False,"recovery_attempts":1,"failure_stage":"frozen_source_locator_path_unavailable"}]
    atomic(a.isolation_register,isolation,True)
    receipt={"version":"fixed10k-truncated-004-084-recovery-v1","status":"source_truncated_unrecoverable","created_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"attempts":1,"attempt_job":"46773992","method":"frozen source locator only; no alternate source search or retry","inputs":{"attempt_marker_sha256":sha(a.attempt_marker),"claim_manifest_sha256":sha(a.claim_manifest),"packet_sha256":sha(a.packet),"source_map_sha256":sha(a.source_map),"failed_job_stderr_sha256":sha(a.failed_job_stderr)},"comparison":{"performed":False,"reason":"frozen locator target path unavailable on WZ; no raw source row read; no candidate replacement/context-key change"},"disposition":"isolated from work queue; remains unfinished; ledger and predecessor queue unchanged"}
    atomic(a.receipt,receipt)
if __name__=="__main__": main()
