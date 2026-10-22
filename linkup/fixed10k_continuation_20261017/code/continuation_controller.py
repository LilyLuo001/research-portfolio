#!/usr/bin/env python3
"""Cloud controller: submit ready validator/backfill batches in strict sequence."""
import argparse, datetime as dt, hashlib, json, os, subprocess, time
from pathlib import Path

TERMINAL={"COMPLETED","FAILED","CANCELLED","TIMEOUT","OUT_OF_MEMORY","NODE_FAIL","PREEMPTED","BOOT_FAIL","DEADLINE"}
def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def sha(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def jsonl_rows(path):
 values=[]
 with open(path,encoding="utf-8") as f:
  for line in f:
   if not line.strip():raise RuntimeError("blank JSONL line in "+str(path))
   value=json.loads(line)
   if not isinstance(value,dict):raise RuntimeError("non-object JSONL in "+str(path))
   values.append(value)
 return values
def record_identities(values,path,context_key):
 identities=[]
 for value in values:
  pair=(value.get("record_id"),value.get(context_key))
  if not all(isinstance(x,str) and x for x in pair):raise RuntimeError("missing record/context identity in "+str(path))
  identities.append(pair)
 if len(identities)!=len(set(identities)) or len({x[0] for x in identities})!=len(identities) or len({x[1] for x in identities})!=len(identities):raise RuntimeError("duplicate record/context identity in "+str(path))
 return set(identities)
def atomic(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=Path(str(path)+".tmp");tmp.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8");os.chmod(str(tmp),0o600);os.replace(str(tmp),str(path))
def state(job):
 result=subprocess.run(["sacct","-j",str(job),"--format=JobIDRaw,State,ExitCode","-n","-P"],universal_newlines=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
 for line in result.stdout.splitlines():
  parts=line.split("|")
  if parts and parts[0]==str(job):return parts[1].split()[0],parts[2]
 return "PENDING","unknown"
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",required=True);p.add_argument("--first-batch",type=int,default=5);p.add_argument("--last-batch",type=int,default=69);p.add_argument("--poll-seconds",type=int,default=30);p.add_argument("--max-idle-seconds",type=int,default=42000);p.add_argument("--receipt",required=True);a=p.parse_args()
 root=Path(a.root);c=root/"private/continuation";receipt_path=Path(a.receipt);events=[]
 old={};resume_batch=None;resume_job=None
 if receipt_path.exists():
  old=json.load(open(receipt_path,encoding="utf-8"));events=old.get("events",[])
  if old.get("status")=="validator_backfill_running" and old.get("running_batch") and old.get("running_job"):
   resume_batch=int(old["running_batch"]);resume_job=str(old["running_job"])
 controller={"version":"fixed10k-continuation-controller-v1","started_utc":now(),"status":"running","range":[a.first_batch,a.last_batch],"controller_code_sha256":sha(__file__),"finalizer_code_sha256":sha(c/"code/finalize_continuation.py"),"wrapper_sha256":sha(c/"code/wz_finalize_continuation.sbatch"),"events":events}
 idle_start=time.monotonic()
 for batch in range(a.first_batch,a.last_batch+1):
  b="{:03d}".format(batch);final_receipt=c/("receipts/BATCH%s_FINALIZE_RECEIPT.json"%b);expected=99 if batch==69 else 100;expected_remaining=None;expected_review_records=expected;registered_isolated=0
  if resume_batch==batch and not final_receipt.exists():
   while True:
    job_state,exit_code=state(resume_job)
    if job_state in TERMINAL:break
    controller.update(status="validator_backfill_running",running_batch=batch,running_job=resume_job,resumed_existing_job=True,updated_utc=now());atomic(receipt_path,controller);time.sleep(a.poll_seconds)
   if job_state!="COMPLETED" or exit_code!="0:0" or not final_receipt.exists():
    controller.update(status="paused_batch_failure",paused_batch=batch,failed_job=resume_job,scheduler_state=job_state,exit_code=exit_code,resumed_existing_job=True,updated_utc=now());atomic(receipt_path,controller);raise RuntimeError("resumed validator/backfill batch failed")
   events.append({"utc":now(),"batch":batch,"action":"resumed_existing_validator_backfill","job_id":resume_job,"scheduler_state":job_state,"exit_code":exit_code})
   resume_batch=None;resume_job=None
  prior_counts={} if batch==5 else json.load(open(c/("receipts/BATCH%03d_FINALIZE_RECEIPT.json"%(batch-1)),encoding="utf-8"))["counts"]
  prior_remaining=6500 if batch==5 else prior_counts["remaining_unfinished_contexts"]
  if final_receipt.exists():
   final=json.load(open(final_receipt,encoding="utf-8"))
   cnt=final.get("counts",{}); counts=cnt; expected_remaining=prior_remaining-cnt.get("updated_contexts",expected)
   if final.get("status")!="pass" or cnt.get("remaining_unfinished_contexts")!=expected_remaining or cnt.get("remaining_work_contexts",0)+cnt.get("blocked_contexts",0)!=expected_remaining:
    controller.update(status="paused_conservation_failure",paused_batch=batch,updated_utc=now());atomic(receipt_path,controller);raise RuntimeError("existing finalize receipt fails conservation")
   events.append({"utc":now(),"batch":batch,"action":"skip_already_successful","finalize_receipt_sha256":sha(final_receipt),"remaining_unfinished_contexts":expected_remaining});atomic(receipt_path,controller);continue
  batchdir=c/("prepared/batch%s"%b);packets=[batchdir/("packets/PACKET_%02d_PRIVATE.jsonl"%n) for n in range(1,6)];reviews=[batchdir/("reviews/REVIEW_PACKET_%02d_PRIVATE.jsonl"%n) for n in range(1,6)]
  while True:
   missing=[str(x) for x in reviews if not x.is_file()]
   packet_missing=[str(x) for x in packets if not x.is_file()]
   if packet_missing:
    controller.update(status="waiting_for_prepared_packets",waiting_batch=batch,missing=packet_missing,updated_utc=now());atomic(receipt_path,controller)
   elif not missing:
    try:
     packet_rows=[jsonl_rows(x) for x in packets];review_rows=[jsonl_rows(x) for x in reviews];packet_counts=list(map(len,packet_rows));review_counts=list(map(len,review_rows))
     if sum(packet_counts)!=expected:raise RuntimeError("packet batch size wrong")
     isolation_path=c/"isolation/BLOCKED_CONTEXTS_PRIVATE.jsonl";isolation=jsonl_rows(isolation_path)
     current=[x for x in isolation if x.get("isolation_batch",4)==batch]
     if any(x.get("status")!="source_truncated_unrecoverable" or not x.get("work_queue_excluded") or x.get("recovery_attempts")!=1 for x in current):raise RuntimeError("current isolation status mismatch")
     isolated={(x.get("record_id"),x.get("normalized_context_sha256")) for x in current}
     if len(isolated)!=len(current) or any(not all(isinstance(y,str) and y for y in x) for x in isolated):raise RuntimeError("current isolation identity mismatch")
     all_packet=set().union(*(record_identities(x,p,"context_sha256") for x,p in zip(packet_rows,packets)))
     if len(all_packet)!=expected or not isolated<=all_packet:raise RuntimeError("registered isolation does not exactly match current packet")
     for packet_path,review_path,packet_values,review_values in zip(packets,reviews,packet_rows,review_rows):
      packet_ids=record_identities(packet_values,packet_path,"context_sha256");review_ids=record_identities(review_values,review_path,"context_sha256")
      if review_ids!=packet_ids-isolated:raise RuntimeError("reviews do not exactly cover non-isolated packet records")
     registered_isolated=len(isolated);expected_review_records=expected-registered_isolated
     if sum(review_counts)!=expected_review_records:raise RuntimeError("review batch size wrong after registered isolation")
     break
    except Exception as exc:
     controller.update(status="paused_readiness_validation_failure",paused_batch=batch,error=str(exc),updated_utc=now());atomic(receipt_path,controller);raise
   else:
    controller.update(status="waiting_for_reviews",waiting_batch=batch,missing=missing,updated_utc=now());atomic(receipt_path,controller)
   if time.monotonic()-idle_start>=a.max_idle_seconds:
    controller.update(status="checkpoint_idle_exit",updated_utc=now());atomic(receipt_path,controller);return
   time.sleep(a.poll_seconds)
  idle_start=time.monotonic();cmd=["sbatch","--parsable",str(c/"code/wz_finalize_continuation.sbatch"),str(batch)]+[str(x) for x in reviews]
  submit=subprocess.run(cmd,universal_newlines=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True);job=submit.stdout.strip().split(";")[0]
  event={"utc":now(),"batch":batch,"action":"submitted_validator_backfill","job_id":job,"review_sha256s":[sha(x) for x in reviews],"expected_records":expected,"expected_review_records":expected_review_records,"registered_isolated_records":registered_isolated};events.append(event);controller.update(status="validator_backfill_running",running_batch=batch,running_job=job,updated_utc=now());atomic(receipt_path,controller)
  while True:
   job_state,exit_code=state(job)
   if job_state in TERMINAL:break
   time.sleep(a.poll_seconds)
  event.update(completed_utc=now(),scheduler_state=job_state,exit_code=exit_code)
  if job_state!="COMPLETED" or exit_code!="0:0" or not final_receipt.exists():
   controller.update(status="paused_batch_failure",paused_batch=batch,failed_job=job,scheduler_state=job_state,exit_code=exit_code,updated_utc=now());atomic(receipt_path,controller);raise RuntimeError("validator/backfill batch failed")
  final=json.load(open(final_receipt,encoding="utf-8"));counts=final.get("counts",{})
  expected_remaining=prior_remaining-counts.get("updated_contexts",expected)
  if final.get("status")!="pass" or counts.get("reviewed_contexts")!=expected_review_records or counts.get("updated_contexts")!=expected_review_records or counts.get("newly_isolated_contexts")!=registered_isolated or counts.get("updated_contexts",0)+counts.get("newly_isolated_contexts",0)!=expected or counts.get("remaining_unfinished_contexts")!=expected_remaining or counts.get("remaining_work_contexts",0)+counts.get("blocked_contexts",0)!=expected_remaining:
   controller.update(status="paused_conservation_failure",paused_batch=batch,failed_job=job,observed_counts=counts,expected_remaining_unfinished=expected_remaining,updated_utc=now());atomic(receipt_path,controller);raise RuntimeError("post-backfill conservation failed")
  event.update(finalize_receipt_sha256=sha(final_receipt),remaining_work_contexts=counts["remaining_work_contexts"],blocked_contexts=counts["blocked_contexts"],remaining_unfinished_contexts=counts["remaining_unfinished_contexts"])
  controller.update(status="checkpoint_pass",last_completed_batch=batch,updated_utc=now());atomic(receipt_path,controller)
 controller.update(status="all_available_packets_backfilled_with_isolated_unfinished",completed_utc=now(),last_completed_batch=a.last_batch,remaining_unfinished_contexts=counts["remaining_unfinished_contexts"],blocked_contexts=counts["blocked_contexts"]);atomic(receipt_path,controller)
if __name__=="__main__":main()
