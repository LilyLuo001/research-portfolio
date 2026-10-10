#!/usr/bin/env python3
"""Independent streaming QA for D67 enriched outputs and public aggregates."""
import argparse, collections, csv, hashlib, json, math, os
from pathlib import Path
import pyarrow.parquet as pq

KEY=("JOB_HASH","SOURCE_FILE","SOURCE_ROW","RECORD_SOURCE_ROW");TH=20
DIMS=("general_work","tool","industry_domain","occupation_task")
OLD={"general_work":"general_work","tool":"specific_tool","industry_domain":"industry_domain"}
RESP=("current_independent_responsibility_wording","current_client_ownership_wording","current_people_supervision_wording","current_d57_duty_mentoring_candidate","current_any_broad_responsibility_wording","current_strict_duty_responsibility_candidate")
ENTRY=("old_explicit_noexperience_candidate","old_explicit_noexperience_applicant_context_candidate","current_explicit_noexperience_candidate","current_explicit_noexperience_unconditional_candidate","current_graduate_wording_candidate","current_noexperience_or_graduate_wording_union")

def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def rows(p):
 with open(p,newline="",encoding="utf-8") as f:return list(csv.DictReader(f))
def num(x):return None if x in (None,"") else float(x)
def close(a,b):return (a is None and b is None) if a is None or b is None else math.isclose(a,b,rel_tol=1e-11,abs_tol=1e-11)
def val(row,name):
 if name=="current_any_broad_responsibility_wording":return any(row[x] is True for x in RESP[:4])
 if name=="current_noexperience_or_graduate_wording_union":return row["current_explicit_noexperience_candidate"] is True or row["current_graduate_wording_candidate"] is True
 return row[name] is True

def main():
 p=argparse.ArgumentParser();p.add_argument("--global-manifest",required=True);p.add_argument("--public-dir",required=True);p.add_argument("--run-receipt",required=True);p.add_argument("--output",required=True);a=p.parse_args()
 gm=json.load(open(a.global_manifest));receipt=json.load(open(a.run_receipt));pub=Path(a.public_dir)
 cells=collections.Counter();sums=collections.Counter();pops=collections.Counter();entry=collections.Counter();meta=collections.Counter();globalc=collections.Counter();errors=[]
 manifest_binding=receipt.get("global_private_manifest",{})
 if receipt.get("status")!="pass" or manifest_binding.get("sha256")!=sha(a.global_manifest) or manifest_binding.get("rows")!=gm.get("rows"):errors.append("global_manifest_receipt_binding")
 shard_items=gm.get("shards",[]);shard_ids=[x.get("shard_id") for x in shard_items];source_files=[x.get("source_file") for x in shard_items]
 if len(shard_items)!=69 or len(set(shard_ids))!=69 or len(set(source_files))!=69:errors.append("global_manifest_69_unique_shards")
 total=0
 old_fields=["old_exp_%s_%s"%(o,m) for o in ("general_work","specific_tool","industry_domain") for m in ("broad","main")]
 needed=list(KEY)+["current_processing_status","old_match","old_usable","current_technology_group","ONET_OCCUPATION_CODE","official_occupation_status","old_occupation_task_available","old_occupation_task_broad","old_occupation_task_main"]+old_fields
 for d in DIMS:needed += ["current_%s_broad"%d,"current_%s_main"%d]
 needed += list(RESP[:4])+["current_strict_duty_responsibility_candidate"]+list(ENTRY[:5])+["records_join_status","company_status","created_alignment_status","geography_status"]
 for item in shard_items:
  path=item["enriched_path"]
  if sha(path)!=item["enriched_sha256"] or pq.ParquetFile(path).metadata.num_rows!=item["rows"]:errors.append("output_binding:"+item["shard_id"]);continue
  seen=set();n=0
  for batch in pq.ParquetFile(path).iter_batches(batch_size=32768,columns=needed):
   data=batch.to_pydict();names=list(data)
   for i in range(batch.num_rows):
    r={x:data[x][i] for x in names};k=tuple(r[x] for x in KEY)
    if k in seen:errors.append("duplicate_key:"+item["shard_id"])
    seen.add(k);n+=1;total+=1
    if r["old_occupation_task_available"] is not False or r["old_occupation_task_broad"] is not None or r["old_occupation_task_main"] is not None:errors.append("old_task_not_NA")
    if r["old_match"] is not True and any(r[x] is not None for x in old_fields):errors.append("unmatched_old_not_null")
    cur=r["current_processing_status"]=="processed";old=r["old_match"] is True;usable=old and r["old_usable"] is True
    globalc["current_rows"]+=1;globalc["current_processed"]+=cur;globalc["exact_old_matches"]+=old;globalc["old_usable_matches"]+=usable
    for f in ("records_join_status","company_status","created_alignment_status","geography_status","official_occupation_status"):meta[(item["region"],f,str(r[f]))]+=1
    arm="software_only" if r["current_technology_group"]=="software_only" else ("any_ai" if r["current_technology_group"] in ("ai_only","software_and_ai") else None)
    ps=[]
    if cur and old:ps.append("old_matched_current_processed")
    if cur and usable:ps.append("old_usable_current_processed")
    for pop in ps:pops[pop]+=1
    if r["official_occupation_status"]=="official_code" and r["ONET_OCCUPATION_CODE"] and arm:
     occ=r["ONET_OCCUPATION_CODE"]
     for pop in ps:
      cells[(pop,occ,arm)]+=1
      for d in DIMS:
       for m in ("broad","main"):sums[(pop,occ,arm,d,"current",m)]+=int(r["current_%s_%s"%(d,m)] is True)
       if d!="occupation_task":
        od=OLD[d]
        for m in ("broad","main"):sums[(pop,occ,arm,d,"old",m)]+=int(r["old_exp_%s_%s"%(od,m)] is True)
    if cur and old:
     for e in ENTRY:
      for q in RESP:entry[(e,q,val(r,e),val(r,q))]+=1
  if n!=item["rows"]:errors.append("row_count:"+item["shard_id"])
  del seen
 if total!=5804936 or gm.get("rows")!=5804936:errors.append("global_denominator")

 support=rows(pub/"COMMON_SUPPORT_PUBLIC.csv");core=rows(pub/"CORE_EXPERIENCE_COMPARISON_PUBLIC.csv")
 for pop in ("old_matched_current_processed","old_usable_current_processed"):
  occs={o for p,o,arm in cells if p==pop};kept={o for o in occs if cells[(pop,o,"software_only")]>=TH and cells[(pop,o,"any_ai")]>=TH};weights={o:min(cells[(pop,o,"software_only")],cells[(pop,o,"any_ai")]) for o in kept};tw=sum(weights.values())
  sr=next((x for x in support if x["population"]==pop),None)
  if len([x for x in core if x["population"]==pop])!=16:errors.append("core_row_count:"+pop)
  expected={"population_n":pops[pop],"eligible_occupation_count":len(kept),"total_min_count_weight":tw,"software_only_retained_n":sum(cells[(pop,o,"software_only")] for o in kept),"any_ai_retained_n":sum(cells[(pop,o,"any_ai")] for o in kept)}
  if sr is None:errors.append("missing_support:"+pop)
  else:
   for k,v in expected.items():
    if int(sr[k])!=v:errors.append("support:%s:%s"%(pop,k))
   if tw and not close(num(sr["weight_check_sum"]),1.0):errors.append("weights:"+pop)
  for out in [x for x in core if x["population"]==pop]:
   d,version,m=out["dimension"],out["measurement_version"],out["measure"]
   unavailable=version=="old" and d=="occupation_task"
   if unavailable:
    if out["status"]!="unavailable_old_occupation_task_unmeasured" or any(num(out[x]) is not None for x in ("software_only_raw_common_support_rate","software_only_standardized_rate","any_ai_raw_common_support_rate","any_ai_standardized_rate","difference_any_ai_minus_software_percentage_points")):errors.append("old_task_public_not_NA")
    continue
   rates={}
   for arm in ("software_only","any_ai"):
    numerator=sum(sums[(pop,o,arm,d,version,m)] for o in kept);den=sum(cells[(pop,o,arm)] for o in kept);raw=numerator/den if den else None
    std=sum(weights[o]/tw*sums[(pop,o,arm,d,version,m)]/cells[(pop,o,arm)] for o in kept) if tw else None;rates[arm]=std
    if not close(num(out[arm+"_raw_common_support_rate"]),raw):errors.append("core_raw")
    if not close(num(out[arm+"_standardized_rate"]),std):errors.append("core_std")
   diff=(rates["any_ai"]-rates["software_only"])*100 if rates["software_only"] is not None else None
   if not close(num(out["difference_any_ai_minus_software_percentage_points"]),diff):errors.append("core_diff")

 erows=rows(pub/"ENTRY_RESPONSIBILITY_COOCCURRENCE_PUBLIC.csv")
 for out in erows:
  e,q=out["entry_marker"],out["responsibility_marker"];vals=[entry[(e,q,True,True)],entry[(e,q,True,False)],entry[(e,q,False,True)],entry[(e,q,False,False)]]
  names=("entry_yes_responsibility_yes","entry_yes_responsibility_no_observed","entry_no_observed_responsibility_yes","neither_rule_observed")
  if any(int(out[n])!=v for n,v in zip(names,vals)) or int(out["denominator"])!=sum(vals):errors.append("entry_matrix")
 mrows=rows(pub/"METADATA_STATUS_COUNTS_PUBLIC.csv")
 for out in mrows:
  if int(out["count"])!=meta[(out["region"],out["field"],out["status"])]:errors.append("metadata_status")
 for region in ("kunshan","wuzhen"):
  region_n=sum(v for (r,f,s),v in meta.items() if r==region and f=="records_join_status")
  for f in ("records_join_status","company_status","created_alignment_status","geography_status","official_occupation_status"):
   if sum(v for (r,ff,s),v in meta.items() if r==region and ff==f)!=region_n:errors.append("metadata_partition")
 hashes=all(sha(pub/name)==x["sha256"] for name,x in receipt["public_outputs"].items())
 checks={"global_manifest_receipt_and_69_unique_shards":not any(x.startswith("global_manifest_") for x in errors),"global_69_row_and_key_conservation":total==5804936 and not any(x.startswith(("duplicate_key","row_count","global_denominator")) for x in errors),"unmatched_old_is_null":not any(x=="unmatched_old_not_null" for x in errors),"old_occupation_task_is_NA":not any("old_task" in x for x in errors),"common_support_same_weights_and_arithmetic":not any(x.startswith(("support","weights","core")) for x in errors),"entry_matrix_recomputed":not any(x=="entry_matrix" for x in errors),"metadata_missing_state_denominators_recomputed":not any(x.startswith("metadata_") for x in errors),"output_hash_bindings":hashes}
 result={"version":"d67-expansion-independent-qa-v1","status":"pass" if all(checks.values()) and not errors else "fail","checks":checks,"rows":total,"arithmetic_errors":errors[:100],"scope":"Independent engineering and numerical QA; no semantic validation."}
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);tmp=Path(str(out)+".tmp");tmp.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n");os.replace(tmp,out)
 if result["status"]!="pass":raise SystemExit("D67 independent QA failed")
if __name__=="__main__":main()
