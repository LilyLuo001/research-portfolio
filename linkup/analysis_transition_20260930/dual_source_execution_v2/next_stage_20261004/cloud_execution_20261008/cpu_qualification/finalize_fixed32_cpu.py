#!/usr/bin/env python3
"""Run the frozen D43 field exporter and compare with accepted adjudicated candidates."""
import argparse,hashlib,json,sys
from collections import Counter
from pathlib import Path
OBJECTS=("general_work","occupation_task","industry_domain")
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(path,n=32):
 lines=Path(path).read_text(encoding="utf-8").splitlines()
 if len(lines)!=n or any(not x for x in lines): raise ValueError(f"{path}: expected {n} nonblank rows")
 return [json.loads(x) for x in lines]
def unwrap(raw):
 try: value,end=json.JSONDecoder().raw_decode(raw.lstrip())
 except json.JSONDecodeError: return raw,False
 tail=raw.lstrip()[end:].strip()
 return (json.dumps(value,ensure_ascii=False,separators=(",",":")),True) if tail=="[end of text]" else (raw,False)
def objmap(row): return {x["object"]:x for x in row["objects"]}
def years(obj): return tuple((x["status"],x.get("model_duration") if x["status"]=="candidate" else None) for x in obj["duration_assessments"])
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--source",required=True); ap.add_argument("--reference",required=True); ap.add_argument("--run-root",required=True); ap.add_argument("--exporter-dir",required=True); ap.add_argument("--output",required=True)
 a=ap.parse_args(); sys.path.insert(0,a.exporter_dir); import export_candidates as ex
 src,ref=read(a.source),read(a.reference); out=Path(a.output); out.mkdir(parents=True,exist_ok=False); wrappers=[]; task_states=[]; envelopes=0
 for i,s in enumerate(src,1):
  d=Path(a.run_root)/"tasks"/f"record_{i:02d}"; rp=d/"TASK_RECEIPT.json"; rawp=d/"raw.stdout"
  receipt=json.loads(rp.read_text()) if rp.is_file() else None
  ok=bool(receipt and receipt.get("status")=="complete" and receipt.get("process_exit")==0 and rawp.is_file())
  raw=rawp.read_text(encoding="utf-8") if rawp.is_file() else ""
  # A nonzero/truncated task can end on syntactically complete JSON. Never promote it.
  normalized,removed=unwrap(raw) if ok else ("__PROCESS_INCOMPLETE__",False); envelopes+=removed
  rid=str(s["record_id"]); text=s["original_text"]
  wrappers.append({"processing_position_1based":i,"record_id":rid,"source_text_sha256":hashlib.sha256(text.encode()).hexdigest(),"raw_output_line_sha256":hashlib.sha256(normalized.encode()).hexdigest(),"raw_output":normalized})
  task_states.append({"index":i,"task_receipt_present":rp.is_file(),"process_completed":ok,"runtime_envelope_removed":removed,"raw_bytes":len(raw.encode())})
 exports=ex.export_rows(src,wrappers)
 (out/"FIELD_CANDIDATES_PRIVATE.jsonl").write_text(ex.serialize_jsonl(exports),encoding="utf-8")
 agree=Counter(); denom=Counter(); detail=[]
 for i,(got,want) in enumerate(zip(exports,ref),1):
  if str(want.get("record_id"))!=str(src[i-1]["record_id"]) or want.get("source_text_sha256")!=hashlib.sha256(src[i-1]["original_text"].encode()).hexdigest(): raise ValueError(f"reference binding mismatch row {i}")
  gm,wm=objmap(got),objmap(want); row={"index":i,"objects":{}}
  for o in OBJECTS:
   g,w=gm[o],wm[o]
   if g["outcome_status"] in {"unknown","error"} and g["main_prior_required_unconditional"] is not None: raise AssertionError("noncandidate main must be null")
   status_match=g["outcome_status"]==w["outcome_status"]
   state_eligible=g["outcome_status"]!="error" and w["outcome_status"]!="error" and g.get("model_state") is not None and w.get("model_state") is not None
   main_eligible=g["outcome_status"]=="candidate" and w["outcome_status"]=="candidate" and g["main_prior_required_unconditional"] in (0,1) and w["main_prior_required_unconditional"] in (0,1)
   years_eligible=g["outcome_status"]=="candidate" and w["outcome_status"]=="candidate" and all(x["status"]=="candidate" for x in g["duration_assessments"]+w["duration_assessments"])
   vals={"status":{"eligible":True,"match":status_match},"state":{"eligible":state_eligible,"match":state_eligible and g.get("model_state")==w.get("model_state")},"main":{"eligible":main_eligible,"match":main_eligible and g["main_prior_required_unconditional"]==w["main_prior_required_unconditional"]},"years":{"eligible":years_eligible,"match":years_eligible and years(g)==years(w)}}
   for k,v in vals.items():
    if v["eligible"]: denom[(o,k)]+=1; agree[(o,k)]+=bool(v["match"])
   row["objects"][o]=vals
  detail.append(row)
 private={"schema_version":"linkup-cpu-fixed32-qualification-v2","records":32,"task_states":task_states,"runtime_envelopes_removed":envelopes,"semantic_repairs":0,"comparisons":detail,"source_sha256":sha(a.source),"accepted_reference_sha256":sha(a.reference)}
 (out/"QUALIFICATION_PRIVATE.json").write_text(json.dumps(private,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 public={"schema_version":"linkup-cpu-fixed32-public-v2","status":"completed_with_failures" if any(not x["process_completed"] for x in task_states) else "complete","records":32,"process_completed":sum(x["process_completed"] for x in task_states),"process_missing_or_failed":32-sum(x["process_completed"] for x in task_states),"raw_outputs_preserved":True,"semantic_repairs":0,"comparison_scope":"agreement with accepted adjudicated Batch002 candidates; not accuracy","denominator_rule":"status uses all 32 rows; state/main/years use only mutually eligible decided fields, with coverage reported against 32","agreement":{f"{o}.{k}":{"agree":agree[(o,k)],"comparable":denom[(o,k)],"coverage_denominator":32} for o in OBJECTS for k in ("status","state","main","years")}}
 (out/"QUALIFICATION_PUBLIC.json").write_text(json.dumps(public,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 return 0
if __name__=="__main__": raise SystemExit(main())
