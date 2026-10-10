#!/usr/bin/env python3
"""Finalize D67's 69-shard additive release with bounded per-shard joins."""
import argparse, collections, csv, datetime as dt, hashlib, json, os, platform
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq

VERSION="d67-expansion-final-v1"
KEY=("JOB_HASH","SOURCE_FILE","SOURCE_ROW","RECORD_SOURCE_ROW")
THRESHOLD=20

def sha(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def atomic(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=Path(str(path)+".tmp");tmp.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n");os.replace(tmp,path)
def write_csv(path,rows,fields=None):
 if not rows:raise RuntimeError("refuse empty public table")
 fields=fields or list(rows[0]);tmp=Path(str(path)+".tmp")
 with open(tmp,"w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 os.replace(tmp,path)
def key(row):return tuple(row[x] for x in KEY)
def frac(a,b):return a/b if b else None

def partition_metadata(metadata,manifest,temp_root):
 by_source={x["source_file"]:x["shard_id"] for x in manifest["shards"]}
 if len(by_source)!=69:raise RuntimeError("source file must uniquely identify frozen shard")
 pf=pq.ParquetFile(metadata);schema=pf.schema_arrow;writers={};buffers=collections.defaultdict(list);counts=collections.Counter()
 temp_root.mkdir(parents=True,exist_ok=True)
 try:
  for batch in pf.iter_batches(batch_size=65536):
   vals=batch.to_pydict();names=list(vals)
   for i in range(batch.num_rows):
    row={n:vals[n][i] for n in names};sid=by_source.get(row["SOURCE_FILE"])
    if sid is None:raise RuntimeError("metadata row outside frozen source files")
    buffers[sid].append(row);counts[sid]+=1
    if len(buffers[sid])>=1024:
     if sid not in writers:writers[sid]=pq.ParquetWriter(temp_root/(sid+".parquet"),schema,compression="zstd")
     writers[sid].write_table(pa.Table.from_pylist(buffers[sid],schema=schema));buffers[sid]=[]
  for sid,rows in buffers.items():
   if rows:
    if sid not in writers:writers[sid]=pq.ParquetWriter(temp_root/(sid+".parquet"),schema,compression="zstd")
    writers[sid].write_table(pa.Table.from_pylist(rows,schema=schema))
  for w in writers.values():w.close()
 except Exception:
  for w in writers.values():
   try:w.close()
   except Exception:pass
  raise
 if len(counts)!=69 or sum(counts.values())!=manifest["current_posting_rows"]:raise RuntimeError("metadata partition denominator mismatch")
 return counts

def overlay_path(shard,wz_dir,ks_dir):
 root=Path(wz_dir if shard["region"]=="wuzhen" else ks_dir);return root/(shard["shard_id"]+".additive.parquet")

def iter_rows(path,columns=None):
 for batch in pq.ParquetFile(path).iter_batches(batch_size=32768,columns=columns):
  vals=batch.to_pydict();names=list(vals)
  for i in range(batch.num_rows):yield {n:vals[n][i] for n in names}

def responsibility(row,name):
 if name=="current_independent_responsibility_wording":return row[name]
 if name=="current_client_ownership_wording":return row[name]
 if name=="current_people_supervision_wording":return row[name]
 if name=="current_d57_duty_mentoring_candidate":return row[name]
 if name=="current_any_broad_responsibility_wording":return any(row[x] for x in ("current_independent_responsibility_wording","current_client_ownership_wording","current_people_supervision_wording","current_d57_duty_mentoring_candidate"))
 if name=="current_strict_duty_responsibility_candidate":return row[name]
 raise ValueError(name)

def main():
 p=argparse.ArgumentParser();p.add_argument("--manifest",required=True);p.add_argument("--wz-overlay-dir",required=True);p.add_argument("--ks-overlay-dir",required=True)
 p.add_argument("--metadata69",required=True);p.add_argument("--metadata-receipt",required=True);p.add_argument("--metadata-qa",required=True);p.add_argument("--private-output",required=True);p.add_argument("--public-output",required=True);a=p.parse_args()
 manifest=json.load(open(a.manifest));
 if manifest.get("shard_count")!=69 or manifest.get("current_posting_rows")!=5804936:raise RuntimeError("frozen denominator mismatch")
 metadata_sha=sha(a.metadata69);metadata_receipt=json.load(open(a.metadata_receipt));metadata_qa=json.load(open(a.metadata_qa))
 if metadata_receipt.get("status")!="complete" or metadata_receipt.get("output_rows")!=manifest["current_posting_rows"] or metadata_receipt.get("output_sha256")!=metadata_sha:raise RuntimeError("metadata receipt status/row/SHA gate failed")
 if metadata_qa.get("status")!="pass" or metadata_qa.get("rows")!=manifest["current_posting_rows"] or not all(metadata_qa.get("checks",{}).values()):raise RuntimeError("independent metadata QA gate failed")
 private=Path(a.private_output);public=Path(a.public_output);private.mkdir(parents=True,exist_ok=True);public.mkdir(parents=True,exist_ok=True)
 meta_tmp=private/"metadata_by_shard_tmp";meta_counts=partition_metadata(a.metadata69,manifest,meta_tmp)
 coverage=[];global_counts=collections.Counter();population_counts=collections.Counter();metadata_status_counts=collections.Counter();version_groups=collections.Counter();cells=collections.Counter();cell_sums=collections.Counter();entry_counts=collections.Counter();measure_counts=collections.Counter();outputs=[]
 dims=("general_work","tool","industry_domain","occupation_task")
 responsibilities=("current_independent_responsibility_wording","current_client_ownership_wording","current_people_supervision_wording","current_d57_duty_mentoring_candidate","current_any_broad_responsibility_wording","current_strict_duty_responsibility_candidate")
 entry_names=("old_explicit_noexperience_candidate","old_explicit_noexperience_applicant_context_candidate","current_explicit_noexperience_candidate","current_explicit_noexperience_unconditional_candidate","current_graduate_wording_candidate","current_noexperience_or_graduate_wording_union")
 for shard in manifest["shards"]:
  sid=shard["shard_id"];op=overlay_path(shard,a.wz_overlay_dir,a.ks_overlay_dir);rp=Path(str(op).replace(".additive.parquet",".additive.receipt.json"))
  receipt=json.load(open(rp));
  if receipt.get("status")!="complete" or receipt["output"]["sha256"]!=sha(op) or receipt["output"]["rows"]!=shard["posting_rows"]:raise RuntimeError("overlay receipt mismatch "+sid)
  metadata={key(r):r for r in iter_rows(meta_tmp/(sid+".parquet"))}
  if len(metadata)!=meta_counts[sid]:raise RuntimeError("duplicate metadata key "+sid)
  enriched=private/(sid+".enriched.parquet");tmp=Path(str(enriched)+".tmp");writer=None;rows_out=[];n=matched=usable=processed=metadata_occ=metadata_company=0
  overlay_schema=pq.ParquetFile(op).schema_arrow;metadata_schema=pq.ParquetFile(meta_tmp/(sid+".parquet")).schema_arrow
  extra_names=("records_join_status","company_status","created_alignment_status","geography_status","official_occupation_status","CENSUS_REGION","OCCUPATION_MAJOR","metadata_complete_for_occ_region","metadata_complete_for_company_occ_region")
  output_schema=pa.schema(list(overlay_schema)+[metadata_schema.field(name) for name in extra_names if name not in overlay_schema.names])
  shard_counts=collections.Counter()
  def flush():
   nonlocal writer,rows_out
   if rows_out:
    table=pa.Table.from_pylist(rows_out,schema=output_schema)
    if writer is None:writer=pq.ParquetWriter(tmp,table.schema,compression="zstd")
    writer.write_table(table);rows_out=[]
  try:
   for row in iter_rows(op):
    n+=1;md=metadata.pop(key(row),None)
    if md is None:raise RuntimeError("missing exact metadata key "+sid)
    row["metadata_status"]="joined_verified_with_explicit_missing_states"
    row["COMPANY_ID"]=md["COMPANY_ID"];row["ONET_OCCUPATION_CODE"]=md["ONET_OCCUPATION_CODE"]
    row["CREATED"]=md["POSTING_CREATED"];row["STATE"]=md["RECORD_STATE"]
    for name in ("records_join_status","company_status","created_alignment_status","geography_status","official_occupation_status","CENSUS_REGION","OCCUPATION_MAJOR","metadata_complete_for_occ_region","metadata_complete_for_company_occ_region"):
     row[name]=md[name]
    rows_out.append(row)
    if len(rows_out)>=8192:flush()
    cur=row["current_processing_status"]=="processed";old=row["old_match"] is True;use=old and row["old_usable"] is True
    if row["old_occupation_task_available"] is not False or row["old_occupation_task_broad"] is not None or row["old_occupation_task_main"] is not None:
     raise RuntimeError("old occupation/task must remain unavailable typed NA")
    global_counts["old_occupation_task_verified_NA_rows"]+=1
    processed+=cur;matched+=old;usable+=use
    occ_ok=md["official_occupation_status"]=="official_code" and bool(md["ONET_OCCUPATION_CODE"]);company_ok=bool(md["COMPANY_ID"])
    metadata_occ+=occ_ok;metadata_company+=company_ok and occ_ok
    for field in ("records_join_status","company_status","created_alignment_status","geography_status","official_occupation_status"):
     metadata_status_counts[(shard["region"],field,str(md[field]))]+=1
    group=row["current_technology_group"];arm="software_only" if group=="software_only" else ("any_ai" if group in ("ai_only","software_and_ai") else None)
    populations=[]
    if cur and old:populations.append("old_matched_current_processed")
    if cur and use:populations.append("old_usable_current_processed")
    for pop in populations:population_counts[pop]+=1
    if occ_ok and arm:
     for pop in populations:
      occ=md["ONET_OCCUPATION_CODE"];cells[(pop,occ,arm)]+=1
      for dim in dims:
       olddim="specific_tool" if dim=="tool" else dim
       values=[("current","broad",row["current_%s_broad"%dim]),("current","main",row["current_%s_main"%dim])]
       if dim!="occupation_task":values += [("old","broad",row["old_exp_%s_broad"%olddim]),("old","main",row["old_exp_%s_main"%olddim])]
       for version,measure,value in values:
        cell_sums[(pop,occ,arm,dim,version,measure)]+=int(value is True)
    if cur and old:
     entries={"old_explicit_noexperience_candidate":row["old_explicit_noexperience_candidate"],
      "old_explicit_noexperience_applicant_context_candidate":row["old_explicit_noexperience_applicant_context_candidate"],
      "current_explicit_noexperience_candidate":row["current_explicit_noexperience_candidate"],
      "current_explicit_noexperience_unconditional_candidate":row["current_explicit_noexperience_unconditional_candidate"],
      "current_graduate_wording_candidate":row["current_graduate_wording_candidate"],
      "current_noexperience_or_graduate_wording_union":row["current_explicit_noexperience_candidate"] or row["current_graduate_wording_candidate"]}
     for e in entry_names:
      for rname in responsibilities:entry_counts[(e,rname,bool(entries[e]),bool(responsibility(row,rname)))]+=1
    for denom,eligible in (("current_processed",cur),("old_usable_current_processed",cur and use)):
     if eligible:
      measure_counts[(denom,"denominator")]+=1
      for name in ("current_numeric_literal_candidate","current_conditional_or_alternative_candidate","current_experience_unknown","current_explicit_noexperience_candidate","current_explicit_noexperience_unconditional_candidate","current_graduate_wording_candidate","current_independent_responsibility_wording","current_client_ownership_wording","current_people_supervision_wording","current_d57_duty_mentoring_candidate","current_strict_duty_responsibility_candidate","old_v6_audit_row_present","old_explicit_noexperience_candidate","old_explicit_noexperience_applicant_context_candidate","old_explicit_noexperience_negated_or_optional","old_qualification_alternative_candidate","old_equivalent_experience_candidate","old_qualification_relation_unresolved","old_mixed_requirement_scope","old_context_conflict","old_audit_only_numeric_literal_candidate"):
       measure_counts[(denom,name)]+=int(row[name] is True)
   flush()
   if writer is None:raise RuntimeError("empty overlay")
   writer.close();writer=None;os.replace(tmp,enriched)
  finally:
   if writer is not None:writer.close()
  if metadata or n!=shard["posting_rows"]:raise RuntimeError("per-shard join conservation "+sid)
  coverage.append({"region":shard["region"],"current_rows":n,"current_processed":processed,"exact_old_matches":matched,"old_usable_matches":usable,"metadata_official_occupation":metadata_occ,"metadata_company_and_official_occupation":metadata_company})
  global_counts.update({"current_rows":n,"current_processed":processed,"exact_old_matches":matched,"old_usable_matches":usable,"metadata_official_occupation":metadata_occ,"metadata_company_and_official_occupation":metadata_company})
  version_groups[(shard["region"],shard["runner_sha256"],shard["rule_engine_sha256"],shard["overlay_sha256"],shard["old_narrow_version"])]+=n
  outputs.append({"shard_id":sid,"region":shard["region"],"source_file":shard["source_file"],"input_overlay":str(op),"input_overlay_sha256":receipt["output"]["sha256"],"enriched_path":str(enriched),"enriched_sha256":sha(enriched),"rows":n})

 funnel=[]
 for metric in ("current_rows","current_processed","exact_old_matches","old_usable_matches","metadata_official_occupation","metadata_company_and_official_occupation"):
  denom=global_counts["current_rows"] if metric!="old_usable_matches" else global_counts["exact_old_matches"]
  funnel.append({"metric":metric,"count":global_counts[metric],"denominator":denom,"fraction":frac(global_counts[metric],denom),"status":"observed_preserve_missing"})
 byregion=collections.defaultdict(collections.Counter)
 for r in coverage:byregion[r["region"]].update({k:v for k,v in r.items() if k!="region"})
 metadata_rows=[]
 for region,c in sorted(byregion.items()):
  metadata_rows.append({"region":region,**dict(c),"official_occupation_fraction":frac(c["metadata_official_occupation"],c["current_rows"]),"company_and_official_occupation_fraction":frac(c["metadata_company_and_official_occupation"],c["current_rows"])})
 metadata_status_rows=[]
 for region,c in sorted(byregion.items()):
  for field in ("records_join_status","company_status","created_alignment_status","geography_status","official_occupation_status"):
   if sum(count for (r,f,s),count in metadata_status_counts.items() if r==region and f==field)!=c["current_rows"]:
    raise RuntimeError("metadata status denominator does not conserve region rows")
 for (region,field,status),count in sorted(metadata_status_counts.items()):
  denominator=byregion[region]["current_rows"]
  metadata_status_rows.append({"region":region,"field":field,"status":status,"count":count,"denominator":denominator,"fraction":frac(count,denominator),"interpretation":"explicit_join_or_missing_state_preserved"})
 support=[];core=[]
 for pop in ("old_matched_current_processed","old_usable_current_processed"):
  occs={o for p,o,a in cells if p==pop};kept={o for o in occs if cells[(pop,o,"software_only")]>=THRESHOLD and cells[(pop,o,"any_ai")]>=THRESHOLD};tw=sum(min(cells[(pop,o,"software_only")],cells[(pop,o,"any_ai")]) for o in kept)
  valid={arm:sum(cells[(pop,o,arm)] for o in occs) for arm in ("software_only","any_ai")};ret={arm:sum(cells[(pop,o,arm)] for o in kept) for arm in valid}
  support.append({"population":pop,"population_n":population_counts[pop],"occupation_threshold_each_arm":THRESHOLD,"eligible_occupation_count":len(kept),"software_only_valid_occupation_n":valid["software_only"],"any_ai_valid_occupation_n":valid["any_ai"],"software_only_retained_n":ret["software_only"],"any_ai_retained_n":ret["any_ai"],"total_min_count_weight":tw,"weight_check_sum":sum(min(cells[(pop,o,"software_only")],cells[(pop,o,"any_ai")])/tw for o in kept) if tw else None})
  for dim in dims:
   for version in ("old","current"):
    for measure in ("broad","main"):
     unavailable=version=="old" and dim=="occupation_task"
     row={"population":pop,"comparison":"software_only_vs_any_ai","technology_group_source":"fixed_current_rule_v1_2_nonnegated_lexical_group","occupation_threshold_each_arm":THRESHOLD,"eligible_occupation_count":len(kept),"weight_basis":"min(software_only_n,any_ai_n)_normalized","dimension":dim,"measurement_version":version,"measure":measure,"status":"unavailable_old_occupation_task_unmeasured" if unavailable else ("estimated_candidate_wording" if tw else "unavailable_no_supported_cells")}
     for arm in ("software_only","any_ai"):
      if unavailable:
       row[arm+"_raw_common_support_rate"]=None;row[arm+"_standardized_rate"]=None
      else:
       numerator=sum(cell_sums[(pop,o,arm,dim,version,measure)] for o in kept);denominator=sum(cells[(pop,o,arm)] for o in kept)
       weighted=sum((min(cells[(pop,o,"software_only")],cells[(pop,o,"any_ai")])/tw)*(cell_sums[(pop,o,arm,dim,version,measure)]/cells[(pop,o,arm)]) for o in kept) if tw else None
       row[arm+"_raw_common_support_rate"]=frac(numerator,denominator);row[arm+"_standardized_rate"]=weighted
     l=row["software_only_standardized_rate"];r=row["any_ai_standardized_rate"];row["difference_any_ai_minus_software_percentage_points"]=(r-l)*100 if l is not None else None;core.append(row)
 entry=[];denom=global_counts["exact_old_matches"]
 for e in entry_names:
  for rname in responsibilities:
   a1=entry_counts[(e,rname,True,True)];b=entry_counts[(e,rname,True,False)];c=entry_counts[(e,rname,False,True)];d=entry_counts[(e,rname,False,False)]
   entry.append({"population":"old_matched_current_processed","entry_marker":e,"responsibility_marker":rname,"entry_yes_responsibility_yes":a1,"entry_yes_responsibility_no_observed":b,"entry_no_observed_responsibility_yes":c,"neither_rule_observed":d,"denominator":a1+b+c+d,"cooccurrence_rate_within_entry_marker":frac(a1,a1+b),"interpretation":"wording_candidate_cooccurrence_not_eligibility_authority_or_seniority"})
 measures=[]
 for denom_name in ("current_processed","old_usable_current_processed"):
  d=measure_counts[(denom_name,"denominator")]
  for (denom2,name),count in sorted(measure_counts.items()):
   if denom2==denom_name and name!="denominator":measures.append({"population":denom_name,"measure":name,"count":count,"denominator":d,"fraction":frac(count,d),"status":"candidate_detected" if not name.startswith("old_v6_audit") else "selected_audit_coverage"})
 versions=[{"region":k[0],"runner_sha256":k[1],"rule_engine_sha256":k[2],"relation_overlay_sha256":k[3],"old_narrow_version":k[4],"rows":v,"shards":sum(1 for s in manifest["shards"] if (s["region"],s["runner_sha256"],s["rule_engine_sha256"],s["overlay_sha256"],s["old_narrow_version"])==k)} for k,v in sorted(version_groups.items())]
 files={"COVERAGE_FUNNEL_PUBLIC.csv":funnel,"METADATA_COVERAGE_PUBLIC.csv":metadata_rows,"METADATA_STATUS_COUNTS_PUBLIC.csv":metadata_status_rows,"SHARD_VERSION_COVERAGE_PUBLIC.csv":versions,"COMMON_SUPPORT_PUBLIC.csv":support,"CORE_EXPERIENCE_COMPARISON_PUBLIC.csv":core,"ENTRY_RESPONSIBILITY_COOCCURRENCE_PUBLIC.csv":entry,"QUALIFICATION_UNKNOWN_COVERAGE_PUBLIC.csv":measures}
 for name,rows in files.items():write_csv(public/name,rows)
 global_manifest={"version":VERSION,"status":"complete","created_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"frozen_manifest_sha256":sha(a.manifest),"metadata69":{"path":a.metadata69,"sha256":metadata_sha,"rows":pq.ParquetFile(a.metadata69).metadata.num_rows,"receipt_path":a.metadata_receipt,"receipt_sha256":sha(a.metadata_receipt),"independent_qa_path":a.metadata_qa,"independent_qa_sha256":sha(a.metadata_qa)},"shards":outputs,"rows":sum(x["rows"] for x in outputs)}
 gm=private/"GLOBAL_OUTPUT_MANIFEST_PRIVATE.json";atomic(gm,global_manifest)
 summary={"version":VERSION,"status":"complete","frozen_shards":69,"current_rows":global_counts["current_rows"],"exact_old_matches":global_counts["exact_old_matches"],"old_usable_matches":global_counts["old_usable_matches"],"metadata_official_occupation":global_counts["metadata_official_occupation"],"scope":"frozen completed-output KS13 plus WZ56 convenience wave; not a probability sample","limits":["old occupation/task remains unavailable NA","old numeric literal is audit-only in D67; D66 experience+audit union applies only to its first5 scope","general_work is the rule category for experience without a more specific object; it is not all general experience or general human capital","old/current rule differences are not accuracy or AI effects","responsibility and entry measures are wording candidates","sparse audit non-detection is not semantic absence"],"company_occupation_sensitivity":"not_delivered;metadata fields and coverage retained but no company-by-occupation estimate is reported"}
 atomic(public/"SUMMARY_PUBLIC.json",summary)
 names=list(files)+["SUMMARY_PUBLIC.json"]
 receipt={"version":VERSION,"status":"pass","created_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"scheduler":{"job_id":os.environ.get("SLURM_JOB_ID"),"host":platform.node()},"counts":dict(global_counts),"checks":{"frozen_69":len(outputs)==69,"row_conservation":sum(x["rows"] for x in outputs)==manifest["current_posting_rows"],"metadata_receipt_status_row_sha":True,"metadata_independent_qa_pass":True,"metadata_exact_join":True,"metadata_status_denominators_conserve":True,"old_occupation_task_NA":global_counts["old_occupation_task_verified_NA_rows"]==manifest["current_posting_rows"],"fixed_current_technology_groups":True,"same_common_support_and_weights":True},"global_private_manifest":{"path":str(gm),"sha256":sha(gm),"rows":global_manifest["rows"]},"public_outputs":{n:{"sha256":sha(public/n),"bytes":(public/n).stat().st_size} for n in names},"api_calls":0,"model_calls":0,"full_text_reads":0,"claim_boundary":"completed-output candidate wording; no full-corpus prevalence, semantic accuracy, causal, seniority or authority claim"}
 atomic(public/"RUN_RECEIPT_PUBLIC.json",receipt)

if __name__=="__main__":main()
