#!/usr/bin/env python3
"""Build two compact, balanced review-input partitions from the cloud selector."""
import argparse, collections, datetime as dt, hashlib, json, os, platform
from pathlib import Path


def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()


def dump_jsonl(path, rows):
    t=Path(str(path)+".tmp")
    with open(t,"w",encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n")
    os.replace(t,path)


def main():
    p=argparse.ArgumentParser(); p.add_argument("--packet",required=True); p.add_argument("--schema",required=True)
    p.add_argument("--instructions",required=True); p.add_argument("--private-output",required=True); p.add_argument("--public-output",required=True)
    a=p.parse_args(); rows=[json.loads(x) for x in open(a.packet,encoding="utf-8") if x.strip()]
    if len(rows)!=96 or {r["selection_index_1based"] for r in rows}!=set(range(1,97)): raise RuntimeError("selector packet gate")
    compact=[]
    for r in rows:
        fields=[]
        for name,value in sorted(r["baseline_flags"].items()): fields.append({"field":name,"value":value})
        for name,value in sorted(r["strength_summary"].items()): fields.append({"field":"strength_summary."+name,"value":value})
        ck=dict(zip(("JOB_HASH","SOURCE_FILE","SOURCE_ROW","RECORD_SOURCE_ROW"),r["canonical_key"]))
        compact.append({
            "record_id":"wave02-%03d"%r["selection_index_1based"], "selection_index_1based":r["selection_index_1based"],
            "canonical_key":ck, "source_exact_text_sha256":r["source_text_sha256"], "context_sha256":r["normalized_text_sha256"],
            "question":"experience_4dims" if r["question_group"]=="experience" else "entry_responsibility_4dims",
            "selection_stratum":r["selection_stratum"], "technology_arm":r["technology_arm"], "occupation_code":r["occupation_code"],
            "coverage_scope":{"level":"full_document","exhaustiveness_certification":"full_document",
                              "description":"Complete frozen normalized document plus all retained evidence for the target dimension."},
            "frozen_before":{"field_snapshot":fields,
                             "candidate_evidence_indices_0based":sorted({e["evidence_index"] for e in r["evidence"] if isinstance(e.get("evidence_index"),int)})},
            "review_text":r["review_text"], "target_evidence":r["evidence"],
            "review_instruction":r["review_instruction"],
            "required_output":{"schema_path":a.schema,"schema_sha256":sha(a.schema),"instructions_sha256":sha(a.instructions),
                               "note":"Return one schema-valid decision record; do not propagate to unreviewed ads."}
        })
    parts={"A":[r for r in compact if r["selection_index_1based"]%2==1],
           "B":[r for r in compact if r["selection_index_1based"]%2==0]}
    out=Path(a.private_output); pub=Path(a.public_output); out.mkdir(parents=True,exist_ok=True); pub.mkdir(parents=True,exist_ok=True)
    outputs={}
    for name,vals in parts.items():
        path=out/("WAVE02_REVIEW_%s_PRIVATE.jsonl"%name); dump_jsonl(path,vals)
        arms=collections.Counter(x["technology_arm"] for x in vals); qs=collections.Counter(x["question"] for x in vals)
        if len(vals)!=48 or arms!={"software_only":24,"any_ai":24} or qs!={"experience_4dims":30,"entry_responsibility_4dims":18}:
            raise RuntimeError("review partition imbalance "+name+repr((arms,qs)))
        outputs[path.name]={"path":str(path),"rows":48,"sha256":sha(path),"arm_counts":dict(arms),"question_counts":dict(qs)}
    blind=[{"selection_index_1based":r["selection_index_1based"],"record_id":r["record_id"],
            "question":r["question"],"review_text":r["review_text"]}
           for r in compact if r["selection_index_1based"] in (1,24,49,72)]
    blind_path=out/"ROOT_BLIND4_PRIVATE.jsonl"; dump_jsonl(blind_path,blind)
    outputs[blind_path.name]={"path":str(blind_path),"rows":4,"sha256":sha(blind_path),
                             "contents":"review text and question only; no arm, frozen fields, evidence labels, or rule outputs"}
    receipt={"version":"pro-wave02-review-partitions-v1","status":"pass","created_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
             "scheduler":{"job_id":os.environ.get("SLURM_JOB_ID"),"host":platform.node()},"selector_packet_sha256":sha(a.packet),
             "schema_sha256":sha(a.schema),"instructions_sha256":sha(a.instructions),"outputs":outputs,
             "method":"odd/even deterministic interleave; each reviewer receives 24 per arm, 30 experience and 18 entry-responsibility",
             "claim_boundary":"purposeful review input; no decisions, accuracy estimates, or population propagation"}
    rp=pub/"REVIEW_PARTITION_RECEIPT_PUBLIC.json"; t=Path(str(rp)+".tmp"); t.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n"); os.replace(t,rp)

if __name__=="__main__": main()
