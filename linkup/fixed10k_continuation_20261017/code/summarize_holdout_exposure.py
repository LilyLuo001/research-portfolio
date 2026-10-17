#!/usr/bin/env python3
"""Summarize existing exposure flags for the already-frozen final holdout."""
import argparse, collections, datetime as dt, hashlib, json, os
from pathlib import Path
HOLDOUT_SHA="5d37e0d5840d99f6d9f52d7cc6e2573bd0ca89d7bc948d121a7c9684b36e5de1"
QUEUE_SHA="ad8d5687a34e5f9ea11a4ea5db77615ca128face9502a35b027abbaf946b9a51"
LEDGER_SHA="527b4f6ec11fadde96ed66484f6d2578184d6ef9035069fbbd0db1d78320ba60"
def sha(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def rows(path):
 with open(path,encoding="utf-8") as f:return [json.loads(x) for x in f if x.strip()]
def atomic(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=Path(str(path)+".tmp");tmp.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8");os.chmod(str(tmp),0o600);os.replace(str(tmp),str(path))
def main():
 p=argparse.ArgumentParser()
 for n in ("holdout","queue","ledger","prep_005_014","prep_015_069","output"):p.add_argument("--"+n.replace("_","-"),required=True)
 a=p.parse_args()
 if sha(a.holdout)!=HOLDOUT_SHA or sha(a.queue)!=QUEUE_SHA or sha(a.ledger)!=LEDGER_SHA:raise RuntimeError("frozen input hash mismatch")
 holdout_rows=rows(a.holdout);holdout={x["normalized_context_sha256"] for x in holdout_rows};queue={x["normalized_context_sha256"]:x for x in rows(a.queue)}
 if len(holdout)!=1331 or not holdout<=set(queue):raise RuntimeError("holdout membership mismatch")
 exposed_contexts={c for c in holdout if queue[c].get("historical_development_evaluation_exposure")}
 field_counts=collections.Counter();exposed_cells=0;seen=collections.Counter()
 for row in rows(a.ledger):
  context=row["normalized_context_sha256"]
  if context in holdout:
   seen[context]+=1
   if row.get("historical_development_evaluation_exposure"):
    field_counts[row["field_family"]]+=1;exposed_cells+=1
 if set(seen)!=holdout or any(n<7 for n in seen.values()):raise RuntimeError("holdout ledger coverage mismatch")
 first=json.load(open(a.prep_005_014,encoding="utf-8"));second=json.load(open(a.prep_015_069,encoding="utf-8"))
 receipt={"version":"fixed10k-final-evaluation-holdout-exposure-v1","status":"pass","created_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"inputs":{"holdout_sha256":HOLDOUT_SHA,"queue_sha256":QUEUE_SHA,"ledger_sha256":LEDGER_SHA,"prep_005_014_sha256":sha(a.prep_005_014),"prep_015_069_sha256":sha(a.prep_015_069)},"membership":{"contexts":1331,"rule":first["final_evaluation_holdout"]["rule"],"unchanged_across_second_prep":second["checks"]["holdout_file_not_rewritten"]},"historical_exposure":{"contexts_with_existing_development_evaluation_exposure":len(exposed_contexts),"contexts_without_recorded_development_evaluation_exposure":1331-len(exposed_contexts),"context_family_cells_with_existing_exposure":exposed_cells,"field_family_counts":dict(sorted(field_counts.items())),"interpretation":"members with prior exposure are reported separately; the final evaluation is not described as wholly blind"},"future_training_contract":{"exclude_all_1331_contexts_from_final_training":True,"exclude_all_fields_for_each_held_out_context":True,"excluded_context_family_memberships":1331*7,"latest_compatible_training_ledger_sha_to_be_frozen_only_after_A_completion":True},"future_evaluation_contract":{"report_each_field_on_eligible_final_reference_only":True,"do_not_use_final_holdout_for_model_selection":True,"report_positive_negative_and_research_comparison_groups":True},"claim_boundary":"existing metadata flags only; no new sample, semantic review, model training, or evaluation"}
 atomic(a.output,receipt)
if __name__=="__main__":main()
