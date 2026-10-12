#!/usr/bin/env python3
"""Verify immutable Wave02 aggregate outputs without a self-referential receipt hash."""
import argparse, datetime as dt, hashlib, json, os
from pathlib import Path

EXPECTED = {
    "BEFORE_AFTER_FIELDS_PUBLIC.csv",
    "ENTRY_COHORT_FIELDS_PUBLIC.csv",
    "ENTRY_RESPONSIBILITY_CROSSTAB_PUBLIC.csv",
    "REVIEW_ONLY_OUTCOMES_PUBLIC.csv",
    "SUMMARY_PUBLIC.json",
}

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def write_json(path,value):
    t=Path(str(path)+".tmp")
    t.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    os.replace(str(t),str(path))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--aggregate-dir",required=True)
    p.add_argument("--executed-code-archive",required=True)
    p.add_argument("--postrun-source",required=True)
    p.add_argument("--executed-code-sha256",required=True)
    p.add_argument("--postrun-source-sha256",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    root=Path(a.aggregate_dir)
    receipt_path=root/"RUN_RECEIPT_PUBLIC.json"
    receipt=json.load(open(receipt_path,encoding="utf-8"))
    listed=set(receipt.get("outputs",{}))-{"RUN_RECEIPT_PUBLIC.json"}
    if receipt.get("status")!="pass" or listed!=EXPECTED:
        raise RuntimeError("aggregate receipt status/non-self output set gate failed")
    verified={}
    for name in sorted(EXPECTED):
        path=root/name; actual=sha(path); expected=receipt["outputs"][name]["sha256"]
        verified[name]={"actual_sha256":actual,"receipt_sha256":expected,"match":actual==expected,"bytes":path.stat().st_size}
    if not all(x["match"] for x in verified.values()): raise RuntimeError("aggregate artifact hash mismatch")
    executed=sha(a.executed_code_archive); postrun=sha(a.postrun_source)
    if executed!=a.executed_code_sha256 or postrun!=a.postrun_source_sha256:
        raise RuntimeError("aggregate source provenance hash mismatch")
    self_entry=receipt.get("outputs",{}).get("RUN_RECEIPT_PUBLIC.json")
    actual_receipt=sha(receipt_path)
    if not self_entry or self_entry.get("sha256")==actual_receipt:
        raise RuntimeError("expected stale self-reference was absent or unexpectedly matched")
    value={
      "version":"wave02-aggregate-output-verification-v1","status":"pass",
      "created_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
      "scheduler_job_id":os.environ.get("SLURM_JOB_ID"),
      "aggregate_jobs":{"first":"124253429","second_after_ambiguous_ssh_response":"124253432","final_writer_bound_in_original_receipt":receipt.get("scheduler",{}).get("job_id")},
      "duplicate_submission_note":"The same frozen script was submitted twice after an SSH response timeout made the first submission ambiguous; both completed 0:0. No additional semantic review or corpus scan was performed.",
      "original_aggregate_receipt":{"path":str(receipt_path),"sha256":actual_receipt,"bytes":receipt_path.stat().st_size},
      "receipt_self_reference":{"status":"rejected_stale_predecessor_entry","recorded_sha256":self_entry.get("sha256"),"actual_sha256":actual_receipt,"policy":"receipt cannot authenticate itself; only the five non-self artifacts are verified here"},
      "verified_nonself_outputs":verified,
      "source_provenance":{"executed_source_sha256":executed,"postrun_self_glob_fix_source_sha256":postrun,"postrun_change":"exclude RUN_RECEIPT_PUBLIC.json from future output glob; numerical outputs unchanged and not rerun"},
    }
    write_json(a.output,value)

if __name__=="__main__": main()
