#!/usr/bin/env python3
"""Publish cloud receipt metadata only; never reads private research data."""
import datetime as dt,json
from pathlib import Path
base=Path(__file__).resolve().parents[1]
receipts=sorted(base.joinpath("receipts").glob("BATCH*_FINALIZE_RECEIPT.json"))
rr=[json.loads(p.read_text()) for p in receipts]
rr=[r for r in rr if r["record_batch"]["batch_number"]>=5]
r=rr[-1]; batch=r["record_batch"]["batch_number"]; d=r["counts"]
summary=json.loads((base/"EXECUTION_RESULTS_PUBLIC.json").read_text())
new=sum(x["counts"]["updated_contexts"] for x in rr)
reviewed=sum(x["counts"].get("reviewed_contexts",x["counts"]["updated_contexts"]) for x in rr)
elapsed=(dt.datetime.fromisoformat(r["created_utc"])-dt.datetime.fromisoformat("2026-10-17T08:35:13+00:00")).total_seconds()
summary.update(as_of_utc=r["created_utc"],last_backfilled_batch=batch)
summary["A"].update(new_contexts_backfilled_this_turn=new,actual_reviewed_contexts_in_finalized_batches=reviewed,
 required_context_family_cells=sum(x["counts"]["updated_context_family_cells"] for x in rr),
 prior_family_cells_reused_within_new_batch=sum(x["counts"]["reused_prior_family_cells"] for x in rr),
 new_batch_final_unknown_contexts=sum(x["counts"]["final_unknown_contexts_in_batch"] for x in rr),
 cumulative_reviewed_uncertainty_contexts=d["remaining_reviewed_uncertainty_contexts"],
 remaining_unfinished_contexts=d["remaining_unfinished_contexts"],remaining_work_contexts=d["remaining_work_contexts"],
 isolated_unfinished_contexts=d["blocked_contexts"],elapsed_wall_seconds_including_preparation_and_corrections=elapsed,
 backfilled_contexts_per_hour_since_turn_start=new*3600/elapsed,
 active_continuation="Batch%03d onward; packets are checkpoints, not stopping limits"%(batch+1))
t="/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/continuation/prepared/batch%03d/final/"%batch
summary["latest_private_artifacts"]={"ledger":t+"FIELD_PROVENANCE_LEDGER_PRIVATE.jsonl","queue":t+"REQUIRED_NEW_CONTEXT_QUEUE_PRIVATE.jsonl","uncertainty":t+"REVIEWED_UNCERTAINTY_REGISTER_PRIVATE.jsonl"}
summary["artifact_sha256"]=r["outputs"]
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+"\n")
write(base/"EXECUTION_RESULTS_PUBLIC.json",summary)
statepath=base.parent/"retrospective_20261012/PROJECT_STATE.json"; state=json.loads(statepath.read_text())
state["active_scope"].update(current_backfilled_remaining=d["remaining_unfinished_contexts"],work_queue=d["remaining_work_contexts"],isolated_unfinished=d["blocked_contexts"],latest_backfilled_batch=batch,next_batch=batch+1,latest_private_artifacts=summary["latest_private_artifacts"],latest_artifact_hashes=r["outputs"])
state["latest_completed_semantic_wave"].update(name="fixed10k_continuation_20261017/batch%03d"%batch,reviewed_contexts=d.get("reviewed_contexts",d["updated_contexts"]),covered_ads=d["covered_ads"])
write(statepath,state)
write(base.parents[2]/"retrospective_20261012/PROJECT_STATE.json",state)
fields=json.loads((base/"FIELD_PRODUCTION_STATUS.json").read_text()); fields["reference_semantics"]["source_isolation"]="%d unavailable truncated contexts remain separately unfinished"%d["blocked_contexts"]
write(base/"FIELD_PRODUCTION_STATUS.json",fields)
print(json.dumps({"latest_batch":batch,"new_backfilled":new,"reviewed":reviewed,"remaining":d["remaining_unfinished_contexts"]}))
