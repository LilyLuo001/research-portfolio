#!/usr/bin/env python3
"""Validate/apply any sequential fixed10k continuation Batch >= 005."""
import argparse, collections, datetime as dt, hashlib, importlib.util, json, os
from pathlib import Path

FAMILIES=("technology_category_and_role","experience_object","experience_strength","experience_literal_years","qualification_conditions_and_alternatives","entry_wording_and_scope","current_responsibility_subject_and_relation")
CORE={"record_id","context_sha256","full_document","assignment"}; REQUIRED={"partial","candidate_only","source_unavailable"}
def sha(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def rows(path):
 with open(path,encoding="utf-8") as f:return [json.loads(x) for x in f if x.strip()]
def write_jsonl(path,values):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=Path(str(path)+".tmp")
 with open(tmp,"w",encoding="utf-8") as f:
  for x in values:f.write(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n")
 os.chmod(str(tmp),0o600);os.replace(str(tmp),str(path))
def write_json(path,value,private=False):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=Path(str(path)+".tmp");tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 if private:os.chmod(str(tmp),0o600)
 os.replace(str(tmp),str(path))
def packet_map(path,expected,batch):
 result={};prefix="fixed10k-prod-b{:03d}-".format(batch)
 for row in rows(path):
  if not CORE<=set(row) or not row["record_id"].startswith(prefix) or row["record_id"] in result:raise RuntimeError("invalid packet record")
  if row["assignment"].get("batch_number")!=batch or row["assignment"].get("batch_position_1based") not in range(1,101):raise RuntimeError("packet assignment mismatch")
  required=row.get("required_new_review_families");whitelist=row.get("required_field_whitelist")
  if not isinstance(required,list) or not required or required!=whitelist or len(required)!=len(set(required)) or any(x not in FAMILIES for x in required):raise RuntimeError("invalid required_field_whitelist")
  projections=row.get("existing_family_projections");projected={x.get("field_family"):x for x in projections} if isinstance(projections,list) else {}
  if set(projected)!=set(FAMILIES) or any(projected[x].get("status") not in REQUIRED for x in required):raise RuntimeError("invalid frozen projections")
  result[row["record_id"]]=row
 if len(result)!=expected:raise RuntimeError("packet row count mismatch")
 return result
def make_core(a):
 packet=packet_map(a.enriched_packet,a.expected_records,a.batch_number);write_jsonl(a.output,[{k:x[k] for k in CORE} for _,x in sorted(packet.items())])
def load_module(path):
 spec=importlib.util.spec_from_file_location("coverage",path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def validate_receipts(receipts,validated,all_reviews,expected):
 if len(receipts)!=5 or len(validated)!=5:raise RuntimeError("five validation artifacts required")
 combined=[];loaded=[]
 for rp,vp in zip(receipts,validated):
  receipt=json.load(open(rp,encoding="utf-8"));errors=Path(str(vp).replace("VALIDATED_PACKET_","VALIDATION_ERRORS_PACKET_"))
  packet_rows=rows(vp)
  if receipt.get("status")!="pass" or receipt.get("counts",{}).get("validated_records")!=len(packet_rows) or receipt.get("private_outputs",{}).get("validated_sha256")!=sha(vp):raise RuntimeError("validator receipt failed")
  if errors.exists() and errors.stat().st_size:raise RuntimeError("validator errors file is nonempty")
  combined.extend(packet_rows);loaded.append(receipt)
 if rows(all_reviews)!=combined or len(combined)!=expected:raise RuntimeError("combined validation mismatch")
 return loaded
def queue_row(context,ledger,old):
 fam={x["field_family"]:x for x in ledger};statuses={f:fam[f]["status"] for f in FAMILIES};required=[f for f in FAMILIES if statuses[f] in REQUIRED];uncertain=[f for f in FAMILIES if statuses[f]=="unknown_or_conflict"]
 common={"normalized_context_sha256":context,"raw_exact_text_sha256_values":sorted({x["raw_exact_text_sha256"] for x in ledger}),"represented_ad_count":len({tuple(sorted(x["canonical_key"].items())) for x in ledger}),"family_status":statuses,"resolution_rules":{f:[fam[f]["resolution_rule"]] for f in FAMILIES},"queue_category_counts":{"complete":sum(x in ("known","not_applicable") for x in statuses.values()),"reviewed_unknown_or_conflict":len(uncertain),"partial":sum(x=="partial" for x in statuses.values()),"never_reviewed_or_candidate_only":sum(x in ("candidate_only","source_unavailable") for x in statuses.values())},"source_exposure":sorted({p["source"] for row in ledger for p in row.get("provenance",[])}),"historical_development_evaluation_exposure":any(x.get("historical_development_evaluation_exposure",False) for x in ledger),"representative_canonical_key":old["representative_canonical_key"],"frame_input_locator":old["frame_input_locator"]}
 return (dict(common,required_new_review_families=required,overlaps_reviewed_uncertainty=bool(uncertain)) if required else None,dict(common,reviewed_uncertain_families=uncertain,overlaps_required_new_review=bool(required)) if uncertain else None)
def finalize(a):
 batch=a.batch_number
 if batch<5:raise RuntimeError("continuation finalizer requires Batch >= 005")
 expected_records=a.expected_records
 if expected_records<1 or expected_records>100:raise RuntimeError("batch size must be 1..100")
 packet=packet_map(a.enriched_packet,expected_records,batch);validation=validate_receipts(a.validation_receipts,a.validated_packets,a.validated_reviews,expected_records);reviews=rows(a.validated_reviews)
 if {x.get("record_id") for x in reviews}!=set(packet):raise RuntimeError("reviews do not cover trusted batch")
 paths={"ledger":Path(a.existing_ledger),"queue":Path(a.existing_queue),"uncertainty":Path(a.existing_uncertainty)};prior=json.load(open(a.prior_receipt,encoding="utf-8"))
 if prior.get("status")!="pass":raise RuntimeError("prior receipt failed")
 if batch==5:
  if prior.get("record_batch",{}).get("batch_number")!=4:raise RuntimeError("Batch005 must chain from Batch004")
 else:
  if prior.get("record_batch",{}).get("batch_number")!=batch-1:raise RuntimeError("nonsequential prior receipt")
 names={"ledger":"private_ledger_sha256","queue":"private_queue_sha256","uncertainty":"private_uncertainty_sha256"}
 if any(prior.get("outputs",{}).get(v)!=sha(paths[k]) for k,v in names.items()):raise RuntimeError("prior hash chain mismatch")
 isolation=rows(a.isolation_register);blocked={x["normalized_context_sha256"] for x in isolation}
 if not blocked or len(blocked)!=len(isolation) or any(not x.get("work_queue_excluded") for x in isolation):raise RuntimeError("blocked register mismatch")
 packet_contexts={x["context_sha256"] for x in packet.values()}
 newly_blocked=packet_contexts & blocked
 if any(x.get("isolation_batch")!=batch or x.get("recovery_attempts")!=1 for x in isolation if x["normalized_context_sha256"] in newly_blocked):raise RuntimeError("current isolation lacks one recovery attempt")
 old_ledger,raw_queue,old_uncertainty=(rows(paths[k]) for k in ("ledger","queue","uncertainty"));old_queue=[x for x in raw_queue if x["normalized_context_sha256"] not in (blocked-newly_blocked)]
 expected={x["normalized_context_sha256"] for x in old_queue[:expected_records]}
 if packet_contexts!=expected:raise RuntimeError("packet is not exact next work contexts")
 target=packet_contexts-blocked
 old_q={x["normalized_context_sha256"]:x for x in old_queue};by=collections.defaultdict(list)
 for x in old_ledger:by[x["normalized_context_sha256"]].append(x)
 pctx={x["context_sha256"]:x for x in packet.values()}
 for c in target:
  priorfam={x["field_family"]:x for x in by[c]};proj={x["field_family"]:x for x in pctx[c]["existing_family_projections"]}
  if set(priorfam)!=set(FAMILIES) or any(priorfam[f]["status"]!=proj[f]["status"] for f in FAMILIES):raise RuntimeError("packet projection differs from chained ledger")
 coverage=load_module(a.coverage_module);review_sha=sha(a.validated_reviews);add={}
 for review in reviews:
  context=review["context_sha256"]
  if context!=packet[review["record_id"]]["context_sha256"]:raise RuntimeError("review context mismatch")
  converted={}
  for item0 in coverage.formal_judgments(review,review_sha):
   item=dict(item0);item["source"]="fixed10k_batch{:03d}".format(batch);item["scope"]="batch{:03d}_full_document_required_field_whitelist".format(batch);item["notes"]=list(item.get("notes",[]))+["validated_new_batch{:03d}".format(batch)];converted[item["family"]]=item
  if set(converted)!=set(FAMILIES):raise RuntimeError("judgment adapter family mismatch")
  add[context]=converted
 required={c:set(pctx[c]["required_field_whitelist"]) for c in target};source="fixed10k_batch{:03d}".format(batch);new=[];updated=0
 for row in old_ledger:
  c,f=row["normalized_context_sha256"],row["field_family"]
  if c not in target or f not in required[c]:new.append(row);continue
  item=add[c][f];replacement=dict(row);replacement.update({"status":item["status"],"structured_value":item["value"],"resolution_rule":"batch{:03d}_validated_required_family_review".format(batch),"historical_source_exposure":sorted(set(row.get("historical_source_exposure",[]))|{source}),"provenance":[dict(item,binding_mode="direct_context_assignment")]});new.append(replacement);updated+=1
 old_identity={(x["normalized_context_sha256"],x["field_family"],tuple(sorted(x["canonical_key"].items()))):x for x in old_ledger}
 for row in new:
  identity=(row["normalized_context_sha256"],row["field_family"],tuple(sorted(row["canonical_key"].items())))
  if (identity[0] not in target or identity[1] not in required[identity[0]]) and row!=old_identity[identity]:raise RuntimeError("non-whitelisted ledger row changed")
 new_by=collections.defaultdict(list)
 for x in new:new_by[x["normalized_context_sha256"]].append(x)
 new_queue=[x for x in old_queue if x["normalized_context_sha256"] not in (target|blocked)];new_unc=[x for x in old_uncertainty if x["normalized_context_sha256"] not in target]
 for c in sorted(target):
  q,u=queue_row(c,new_by[c],old_q[c])
  if q:new_queue.append(q)
  if u:new_unc.append(u)
 new_queue.sort(key=lambda x:x["normalized_context_sha256"]);new_unc.sort(key=lambda x:x["normalized_context_sha256"])
 counts=collections.Counter((x["field_family"],x["status"]) for x in new);ledger_rows=len(old_ledger);ads=ledger_rows//7
 if len(new)!=ledger_rows or any(sum(n for (f,_),n in counts.items() if f==family)!=ads for family in FAMILIES):raise RuntimeError("ledger conservation failed")
 cells=sum(map(len,required.values()));covered={tuple(sorted(x["canonical_key"].items())) for x in new if x["normalized_context_sha256"] in target};delta={"updated_contexts":len(target),"reviewed_contexts":expected_records,"newly_isolated_contexts":len(newly_blocked),"updated_context_family_cells":cells,"updated_ad_field_rows":updated,"covered_ads":len(covered),"reused_prior_family_cells":len(target)*7-cells,"final_unknown_contexts_in_batch":sum(any(x["status"]=="unknown_or_conflict" for x in new_by[c]) for c in target),"remaining_work_contexts":len(new_queue),"blocked_contexts":len(blocked),"remaining_unfinished_contexts":len(new_queue)+len(blocked),"remaining_reviewed_uncertainty_contexts":len(new_unc)}
 public={"version":"fixed10k-semantic-production-batch{:03d}-v1".format(batch),"record_batch":{"batch_number":batch,"contexts":expected_records,"work_queue_positions_in_predecessor":[1,expected_records]},"claim_boundary":"validated full-document judgments applied only to frozen required field whitelist; isolated contexts remain separately unfinished and are not written as final reviewed unknown","batch":{"trusted_contexts":expected_records,"validated_contexts":expected_records,"source":source,"required_family_cells":cells},"delta":delta,"isolation":{"register_sha256":sha(a.isolation_register),"blocked_contexts":len(blocked)},"field_status_ad_counts":[{"field_family":f,"status":s,"ad_count":n} for (f,s),n in sorted(counts.items())],"validation":{"receipt_sha256s":[sha(x) for x in a.validation_receipts],"validated_reviews_sha256":review_sha,"validator_statuses":[x["status"] for x in validation]}}
 write_jsonl(a.private_ledger,new);write_jsonl(a.private_queue,new_queue);write_jsonl(a.private_uncertainty,new_unc);write_json(a.public_counts,public)
 receipt={"version":public["version"],"record_batch":public["record_batch"],"status":"pass","created_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"code_sha256":sha(__file__),"prior_receipt":{"path":a.prior_receipt,"sha256":sha(a.prior_receipt),"version":prior.get("version")},"inputs":{"enriched_packet_sha256":sha(a.enriched_packet),"validated_reviews_sha256":review_sha,"validation_receipt_sha256s":[sha(x) for x in a.validation_receipts],"existing_ledger_sha256":sha(paths["ledger"]),"existing_queue_sha256":sha(paths["queue"]),"existing_uncertainty_sha256":sha(paths["uncertainty"]),"isolation_register_sha256":sha(a.isolation_register)},"outputs":{"private_ledger_sha256":sha(a.private_ledger),"private_queue_sha256":sha(a.private_queue),"private_uncertainty_sha256":sha(a.private_uncertainty),"public_counts_sha256":sha(a.public_counts)},"counts":delta,"checks":{"all_batch_records_validated":True,"required_field_whitelist_only":True,"non_required_rows_copied_through":True,"blocked_context_excluded_from_work_queue":True,"unfinished_conserved_with_separate_blocked_count":True,"prior_receipt_chain_bound":True,"ledger_rows_conserved":True,"each_family_ads_conserved":True}}
 write_json(a.receipt,receipt)
def main():
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest="command",required=True);core=sub.add_parser("core-packet")
 for n in ("enriched_packet","output"):core.add_argument("--"+n.replace("_","-"),required=True)
 core.add_argument("--expected-records",type=int,required=True);core.add_argument("--batch-number",type=int,required=True)
 final=sub.add_parser("finalize")
 for n in ("enriched_packet","validated_reviews","coverage_module","prior_receipt","existing_ledger","existing_queue","existing_uncertainty","isolation_register","private_ledger","private_queue","private_uncertainty","public_counts","receipt"):final.add_argument("--"+n.replace("_","-"),required=True)
 final.add_argument("--batch-number",type=int,required=True);final.add_argument("--expected-records",type=int,required=True);final.add_argument("--validation-receipts",nargs="+",required=True);final.add_argument("--validated-packets",nargs="+",required=True);a=p.parse_args();make_core(a) if a.command=="core-packet" else finalize(a)
if __name__=="__main__":main()
