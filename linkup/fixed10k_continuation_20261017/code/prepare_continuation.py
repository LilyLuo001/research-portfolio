#!/usr/bin/env python3
"""Prepare ordered fixed10k continuation packets without changing semantic state."""
import argparse, collections, datetime as dt, hashlib, importlib.util, json, os, platform
from pathlib import Path
import pyarrow.parquet as pq

VERSION = "fixed10k-semantic-continuation-prep-v1"
KEY = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")
FAMILIES = (
    "technology_category_and_role", "experience_object", "experience_strength",
    "experience_literal_years", "qualification_conditions_and_alternatives",
    "entry_wording_and_scope", "current_responsibility_subject_and_relation")
ALLOWED_REQUIRED = {"partial", "candidate_only", "source_unavailable"}
EXPECTED = {
    "queue": "ad8d5687a34e5f9ea11a4ea5db77615ca128face9502a35b027abbaf946b9a51",
    "ledger": "527b4f6ec11fadde96ed66484f6d2578184d6ef9035069fbbd0db1d78320ba60",
    "uncertainty": "60b146ca296f800262c7ddcc189efc654584ed90b6913d8d8b8320b7a8edcdce",
    "prior_receipt": "2751596a4562669a1e6f271c9c585c2211cf48d913846659d7d4ef4e3d976902",
    "frame": "e6083ccacbdfe5a64548168a22ceb11fdce9d6d4bb89943a11f4bae54a17de35",
    "normalizer": "336242bed5372e446dbdc2b2d02944e906024ee90138a2fa424b866aee7293dd",
}

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()
def sha_text(v): return hashlib.sha256(v.encode("utf-8")).hexdigest()
def read_jsonl(path):
    with open(path,encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]
def write_jsonl(path, rows, mode=0o600):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); tmp=Path(str(path)+".tmp")
    with open(tmp,"w",encoding="utf-8") as f:
        for row in rows: f.write(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n")
    os.chmod(str(tmp),mode); os.replace(str(tmp),str(path))
def write_json(path, value, mode=0o600):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); tmp=Path(str(path)+".tmp")
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    os.chmod(str(tmp),mode); os.replace(str(tmp),str(path))
def load_normalizer(path):
    spec=importlib.util.spec_from_file_location("frozen_normalizer",path); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def normalize(m,text):
    result=m._normalize_with_flags(text); value=result[0] if isinstance(result,tuple) else result
    if not isinstance(value,str): raise RuntimeError("normalizer returned non-string")
    return value
def canonical(value): return tuple(value[x] for x in KEY)

def main():
    p=argparse.ArgumentParser()
    for n in ("queue","ledger","uncertainty","prior_receipt","frame","normalizer","formal_schema","formal_instructions","formal_validator","isolation_register","recovery_receipt","private_output","public_receipt","holdout_private"):
        p.add_argument("--"+n.replace("_","-"),required=True)
    p.add_argument("--first-batch",type=int,default=5); p.add_argument("--batch-count",type=int,default=10)
    p.add_argument("--work-offset",type=int,default=0)
    p.add_argument("--context-count",type=int)
    p.add_argument("--manifest-name",default="CLAIM_MANIFEST_PRIVATE.jsonl")
    p.add_argument("--holdout-expected-sha")
    p.add_argument("--repository-commit",required=True); args=p.parse_args(); os.umask(0o077)
    if args.first_batch < 5 or args.batch_count < 1: raise RuntimeError("continuation begins at Batch005")
    paths={k:getattr(args,k) for k in EXPECTED}; hashes={k:sha(v) for k,v in paths.items()}
    for k,v in EXPECTED.items():
        if hashes[k]!=v: raise RuntimeError("frozen input SHA mismatch: "+k)
    prior=json.load(open(args.prior_receipt,encoding="utf-8"))
    if prior.get("status")!="pass" or prior.get("code_sha256")!="84e28d06faa0f0ab196f689d0e186dd4670d78d1271bac2cfb232be1d488d09d": raise RuntimeError("Batch004 receipt/code mismatch")
    if prior.get("outputs",{}).get("private_queue_sha256")!=EXPECTED["queue"] or prior.get("counts",{}).get("remaining_required_contexts")!=6500: raise RuntimeError("Batch004 continuation binding mismatch")
    recovery=json.load(open(args.recovery_receipt,encoding="utf-8")); isolated=read_jsonl(args.isolation_register)
    if recovery.get("attempts")!=1 or len(isolated)!=1 or not isolated[0].get("work_queue_excluded"): raise RuntimeError("single blocked context isolation missing")
    blocked={x["normalized_context_sha256"] for x in isolated}
    queue=read_jsonl(args.queue)
    if len(queue)!=6500 or len(blocked)!=1 or not blocked <= {x["normalized_context_sha256"] for x in queue}: raise RuntimeError("6500=6499+1 queue conservation failed")
    work=[x for x in queue if x["normalized_context_sha256"] not in blocked]
    if len(work)!=6499: raise RuntimeError("work queue must contain 6499 contexts")
    claim_n=args.context_count if args.context_count is not None else args.batch_count*100
    if claim_n < 1 or claim_n > args.batch_count*100: raise RuntimeError("context count incompatible with batch capacity")
    if args.work_offset < 0 or args.work_offset+claim_n>len(work): raise RuntimeError("claim exceeds work queue")
    claimed=work[args.work_offset:args.work_offset+claim_n]
    for row in claimed:
        required=row.get("required_new_review_families")
        if not isinstance(required,list) or not required or len(required)!=len(set(required)): raise RuntimeError("invalid required whitelist")
        if any(f not in FAMILIES or row["family_status"].get(f) not in ALLOWED_REQUIRED for f in required): raise RuntimeError("required whitelist violates status contract")
        if any(row["family_status"].get(f)=="unknown_or_conflict" for f in required): raise RuntimeError("reviewed unknown re-entered required work")

    # Freeze one final model-evaluation membership before any continuation labels exist.
    holdout=[]
    for position,row in enumerate(work,1):
        context=row["normalized_context_sha256"]
        bucket=int(hashlib.sha256(("baseline-holdout-v1|"+context).encode("utf-8")).hexdigest(),16)%5
        if bucket==0: holdout.append({"normalized_context_sha256":context,"work_queue_position_1based":position,"split":"final_evaluation"})
    if args.holdout_expected_sha:
        if not Path(args.holdout_private).is_file() or sha(args.holdout_private)!=args.holdout_expected_sha:
            raise RuntimeError("frozen final-evaluation holdout changed or missing")
        if len(read_jsonl(args.holdout_private))!=len(holdout): raise RuntimeError("frozen holdout row count changed")
    else:
        write_jsonl(args.holdout_private,holdout)

    reps={canonical(x["representative_canonical_key"]):x for x in claimed}
    needed=set(reps); frames={}; pf=pq.ParquetFile(args.frame)
    for batch in pf.iter_batches(columns=list(KEY)+["exact_text_sha256","original_text"],batch_size=2048):
        for row in batch.to_pylist():
            key=tuple(row[x] for x in KEY)
            if key in needed:
                if key in frames or sha_text(row["original_text"])!=row["exact_text_sha256"]: raise RuntimeError("frame representative failure")
                frames[key]=row
    if set(frames)!=needed: raise RuntimeError("representative absent from frame")
    ledger_index=collections.defaultdict(dict)
    for row in read_jsonl(args.ledger):
        key=canonical(row["canonical_key"])
        if key in needed: ledger_index[key][row["field_family"]]=row
    if any(set(ledger_index[k])!=set(FAMILIES) for k in needed): raise RuntimeError("representative lacks seven ledger families")
    normalizer=load_normalizer(args.normalizer); out=Path(args.private_output)
    packets={}; templates={}; manifest=[]; required_counts=collections.Counter(); status_counts=collections.Counter()
    original_positions={x["normalized_context_sha256"]:i for i,x in enumerate(queue,1)}
    for local_pos,qrow in enumerate(claimed,1):
        work_pos=args.work_offset+local_pos
        batch_offset=(local_pos-1)//100; batch_number=args.first_batch+batch_offset; batch_pos=(local_pos-1)%100+1
        packet_number=(batch_pos-1)//20+1; packet_pos=(batch_pos-1)%20+1
        key=canonical(qrow["representative_canonical_key"]); frame=frames[key]; normalized=normalize(normalizer,frame["original_text"]); context=sha_text(normalized)
        if context!=qrow["normalized_context_sha256"]: raise RuntimeError("queue/frame context mismatch")
        projections=[]
        for family in FAMILIES:
            item=ledger_index[key][family]
            if item["normalized_context_sha256"]!=context or item["status"]!=qrow["family_status"][family]: raise RuntimeError("queue/ledger binding mismatch")
            status_counts[(family,item["status"])]+=1
            projections.append({"field_family":family,"status":item["status"],"structured_value":item.get("structured_value"),"resolution_rule":item.get("resolution_rule"),"historical_source_exposure":item.get("historical_source_exposure",[]),"historical_development_evaluation_exposure":bool(item.get("historical_development_evaluation_exposure"))})
        required=list(qrow["required_new_review_families"]); required_counts.update(required)
        rid="fixed10k-prod-b{:03d}-{:03d}".format(batch_number,batch_pos)
        assignment={"packet_id":"fixed10k-prod-b{:03d}-p{:02d}".format(batch_number,packet_number),"reviewer_role":"primary","provenance":VERSION,"predecessor_queue_position_1based":original_positions[context],"work_queue_position_1based":work_pos,"production_position_1based":400+work_pos,"batch_number":batch_number,"batch_position_1based":batch_pos,"packet_position_1based":packet_pos}
        packet={"schema_version":VERSION,"record_id":rid,"context_sha256":context,"full_document":normalized,"assignment":assignment,"required_new_review_families":required,"required_field_whitelist":required,"existing_family_projections":projections}
        template={"record_id":rid,"context_sha256":context,"document_status":None,"reviewed_families":required,"family_updates":[{"family":f,"value":None} for f in required],"unresolved_notes":[]}
        packets.setdefault((batch_number,packet_number),[]).append(packet); templates.setdefault((batch_number,packet_number),[]).append(template)
        manifest.append({"predecessor_queue_position_1based":original_positions[context],"work_queue_position_1based":work_pos,"production_position_1based":400+work_pos,"batch_number":batch_number,"batch_position_1based":batch_pos,"packet_number":packet_number,"packet_position_1based":packet_pos,"record_id":rid,"context_sha256":context,"representative_canonical_key":qrow["representative_canonical_key"],"required_new_review_families":required,"required_field_whitelist":required})
    packet_receipts=[]
    for batch_number in range(args.first_batch,args.first_batch+args.batch_count):
        packet_numbers=sorted(p for b,p in packets if b==batch_number)
        for packet_number in packet_numbers:
            pp=out/("batch{:03d}".format(batch_number))/"packets"/("PACKET_{:02d}_PRIVATE.jsonl".format(packet_number)); tp=out/("batch{:03d}".format(batch_number))/"templates"/("REVIEW_TEMPLATE_{:02d}_PRIVATE.jsonl".format(packet_number))
            write_jsonl(pp,packets[(batch_number,packet_number)]); write_jsonl(tp,templates[(batch_number,packet_number)])
            packet_receipts.append({"batch_number":batch_number,"packet_number":packet_number,"rows":len(packets[(batch_number,packet_number)]),"packet_path":str(pp),"packet_sha256":sha(pp),"template_path":str(tp),"template_sha256":sha(tp)})
    mp=out/args.manifest_name; write_jsonl(mp,manifest)
    receipt={"version":VERSION,"status":"pass","created_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"scheduler":{"job_id":os.environ.get("SLURM_JOB_ID"),"host":platform.node()},"repository_commit":args.repository_commit,
      "inputs":{k:{"path":paths[k],"sha256":hashes[k]} for k in paths},"isolation":{"recovery_receipt_sha256":sha(args.recovery_receipt),"register_sha256":sha(args.isolation_register),"blocked_contexts":1,"work_contexts":6499,"unfinished_conservation":6500,"ledger_and_predecessor_queue_unchanged":True},
      "claim":{"rule":"{} rows at frozen work-queue offset {} after one explicit isolation, relative order preserved".format(claim_n,args.work_offset),"contexts":claim_n,"batches":args.batch_count,"packets":len(packet_receipts),"nominal_rows_per_packet":20,"last_packet_rows":packet_receipts[-1]["rows"],"batch_numbers":[args.first_batch,args.first_batch+args.batch_count-1],"work_queue_positions":[args.work_offset+1,args.work_offset+claim_n],"production_positions":[401+args.work_offset,400+args.work_offset+claim_n],"required_field_whitelist_recorded":True},
      "final_evaluation_holdout":{"rule":"sha256('baseline-holdout-v1|'+context) integer modulo 5 equals 0","source_population":"Batch004 unfinished work queue excluding isolated context","population_count":6499,"count":len(holdout),"private_path":str(args.holdout_private),"private_sha256":sha(args.holdout_private),"frozen_before_continuation_labels":True,"not_used_for_model_selection":True},
      "required_family_counts":{k:required_counts[k] for k in FAMILIES},"existing_family_status_counts":{"{}|{}".format(k[0],k[1]):v for k,v in sorted(status_counts.items())},"outputs":{"private_manifest":{"path":str(mp),"rows":claim_n,"sha256":sha(mp)},"packets":packet_receipts},
      "checks":{"batch004_hashes_pinned":True,"queue_order_preserved_after_isolation":True,"explicit_work_queue_offset_applied":True,"partial_final_batch_supported":True,"one_blocked_not_dropped_from_unfinished_total":True,"full_normalized_document_hash_exact":True,"seven_existing_family_projections_present":True,"required_field_whitelist_only":True,"reviewed_unknown_not_claimed":True,"holdout_membership_frozen":True,"holdout_file_not_rewritten":bool(args.holdout_expected_sha)},"claim_boundary":"mechanical prefetch only; no semantic reading, new sample, completed-field overwrite, reviewed-unknown re-entry, model training, prediction, or queue completion"}
    write_json(args.public_receipt,receipt,0o644)

if __name__=="__main__": main()
