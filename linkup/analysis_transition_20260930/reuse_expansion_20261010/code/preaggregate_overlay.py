#!/usr/bin/env python3
"""D67 totals and wording cooccurrences that do not require metadata."""
import argparse,collections,csv,datetime as dt,hashlib,json,os,platform
from pathlib import Path
import pyarrow.parquet as pq
KEY=("JOB_HASH","SOURCE_FILE","SOURCE_ROW","RECORD_SOURCE_ROW")
VERSION="d67-overlay-preaggregate-v1"
def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def atomic(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=Path(str(p)+".tmp");t.write_text(json.dumps(x,indent=2,sort_keys=True)+"\n");os.replace(t,p)
def write_csv(p,rows):
 if not rows:raise RuntimeError("empty output")
 t=Path(str(p)+".tmp")
 with open(t,"w",newline="",encoding="utf-8") as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 os.replace(t,p)
def frac(a,b):return a/b if b else None
def overlay(shard,wz,ks):return Path(wz if shard["region"]=="wuzhen" else ks)/(shard["shard_id"]+".additive.parquet")
def resp(r,n):
 if n=="any_broad":return any(r[x] for x in ("current_independent_responsibility_wording","current_client_ownership_wording","current_people_supervision_wording","current_d57_duty_mentoring_candidate"))
 return r[n]
def main():
 p=argparse.ArgumentParser();p.add_argument("--manifest",required=True);p.add_argument("--wz-dir",required=True);p.add_argument("--ks-dir",required=True);p.add_argument("--private-output",required=True);p.add_argument("--public-output",required=True);a=p.parse_args()
 m=json.load(open(a.manifest));private=Path(a.private_output);public=Path(a.public_output);private.mkdir(parents=True,exist_ok=True);public.mkdir(parents=True,exist_ok=True)
 counts=collections.Counter();measures=collections.Counter();matrix=collections.Counter();outputs=[]
 entries=("old_explicit_noexperience_candidate","old_explicit_noexperience_applicant_context_candidate","current_explicit_noexperience_candidate","current_explicit_noexperience_unconditional_candidate","current_graduate_wording_candidate","current_noexperience_or_graduate_wording_union")
 responsibilities=("current_independent_responsibility_wording","current_client_ownership_wording","current_people_supervision_wording","current_d57_duty_mentoring_candidate","any_broad","current_strict_duty_responsibility_candidate")
 measure_names=("current_numeric_literal_candidate","current_conditional_or_alternative_candidate","current_experience_unknown","current_explicit_noexperience_candidate","current_explicit_noexperience_unconditional_candidate","current_graduate_wording_candidate","current_independent_responsibility_wording","current_client_ownership_wording","current_people_supervision_wording","current_d57_duty_mentoring_candidate","current_strict_duty_responsibility_candidate","old_v6_audit_row_present","old_explicit_noexperience_candidate","old_explicit_noexperience_applicant_context_candidate","old_explicit_noexperience_negated_or_optional","old_qualification_alternative_candidate","old_equivalent_experience_candidate","old_qualification_relation_unresolved","old_mixed_requirement_scope","old_context_conflict","old_audit_only_numeric_literal_candidate")
 cols=["current_processing_status","old_match","old_usable","old_occupation_task_available","old_occupation_task_broad","old_occupation_task_main"]+list(set(measure_names)|set(responsibilities)-{"any_broad"})
 for s in m["shards"]:
  path=overlay(s,a.wz_dir,a.ks_dir);receipt_path=Path(str(path).replace(".additive.parquet",".additive.receipt.json"));r=json.load(open(receipt_path))
  if r.get("status")!="complete" or r["output"]["sha256"]!=sha(path) or r["output"]["rows"]!=s["posting_rows"]:raise RuntimeError("overlay identity mismatch")
  n=0
  for batch in pq.ParquetFile(path).iter_batches(batch_size=65536,columns=cols):
   d=batch.to_pydict();names=list(d)
   for i in range(batch.num_rows):
    x={k:d[k][i] for k in names};n+=1;cur=x["current_processing_status"]=="processed";old=x["old_match"] is True;use=old and x["old_usable"] is True
    if x["old_occupation_task_available"] is not False or x["old_occupation_task_broad"] is not None or x["old_occupation_task_main"] is not None:raise RuntimeError("old occupation task not NA")
    counts.update({"current_rows":1,"current_processed":int(cur),"exact_old_matches":int(old),"old_usable_matches":int(use),"old_occupation_task_verified_NA_rows":1})
    es={name:x[name] for name in entries if name!="current_noexperience_or_graduate_wording_union"};es["current_noexperience_or_graduate_wording_union"]=x["current_explicit_noexperience_candidate"] or x["current_graduate_wording_candidate"]
    if cur and old:
     counts["old_matched_current_processed"]+=1
     for e in entries:
      for rr in responsibilities:matrix[(e,rr,bool(es[e]),bool(resp(x,rr)))]+=1
    for denom,ok in (("current_processed",cur),("old_usable_current_processed",cur and use)):
     if ok:
      measures[(denom,"denominator")]+=1
      for name in measure_names:measures[(denom,name)]+=int(x[name] is True)
  if n!=s["posting_rows"]:raise RuntimeError("row conservation")
  outputs.append({"shard_id":s["shard_id"],"region":s["region"],"path":str(path),"sha256":r["output"]["sha256"],"rows":n})
 if len(outputs)!=69 or counts["current_rows"]!=5804936 or counts["old_occupation_task_verified_NA_rows"]!=5804936:raise RuntimeError("global conservation")
 coverage=[]
 for name in ("current_rows","current_processed","exact_old_matches","old_usable_matches","old_occupation_task_verified_NA_rows"):
  den=counts["exact_old_matches"] if name=="old_usable_matches" else counts["current_rows"];coverage.append({"metric":name,"count":counts[name],"denominator":den,"fraction":frac(counts[name],den),"status":"observed_preserve_missing"})
 measurement=[]
 for denom in ("current_processed","old_usable_current_processed"):
  den=measures[(denom,"denominator")]
  for name in measure_names:measurement.append({"population":denom,"measure":name,"count":measures[(denom,name)],"denominator":den,"fraction":frac(measures[(denom,name)],den),"status":"audit_only_candidate" if name=="old_audit_only_numeric_literal_candidate" else "candidate_detected_or_selected_audit_coverage"})
 co=[]
 for e in entries:
  for rr in responsibilities:
   aa=matrix[(e,rr,True,True)];b=matrix[(e,rr,True,False)];c=matrix[(e,rr,False,True)];d=matrix[(e,rr,False,False)]
   co.append({"population":"old_matched_current_processed","entry_marker":e,"responsibility_marker":rr,"entry_yes_responsibility_yes":aa,"entry_yes_responsibility_no_observed":b,"entry_no_observed_responsibility_yes":c,"neither_rule_observed":d,"denominator":aa+b+c+d,"cooccurrence_rate_within_entry_marker":frac(aa,aa+b),"interpretation":"wording_candidate_cooccurrence_not_eligibility_authority_or_seniority"})
 write_csv(public/"PREMETADATA_COVERAGE_PUBLIC.csv",coverage);write_csv(public/"PREMETADATA_MEASUREMENT_COVERAGE_PUBLIC.csv",measurement);write_csv(public/"PREMETADATA_ENTRY_RESPONSIBILITY_PUBLIC.csv",co)
 gm=private/"OVERLAY_GLOBAL_MANIFEST_PRIVATE.json";atomic(gm,{"version":VERSION,"status":"complete","frozen_manifest_sha256":sha(a.manifest),"rows":counts["current_rows"],"shards":outputs})
 receipt={"version":VERSION,"status":"pass","created_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"scheduler":{"job_id":os.environ.get("SLURM_JOB_ID"),"host":platform.node()},"counts":dict(counts),"checks":{"69_shards":len(outputs)==69,"row_conservation":counts["current_rows"]==5804936,"old_occupation_task_NA":counts["old_occupation_task_verified_NA_rows"]==5804936,"matrix_conservation":all(sum(matrix[(e,r,x,y)] for x in (False,True) for y in (False,True))==counts["old_matched_current_processed"] for e in entries for r in responsibilities)},"global_private_manifest_sha256":sha(gm),"public_outputs":{n:sha(public/n) for n in ("PREMETADATA_COVERAGE_PUBLIC.csv","PREMETADATA_MEASUREMENT_COVERAGE_PUBLIC.csv","PREMETADATA_ENTRY_RESPONSIBILITY_PUBLIC.csv")},"claim_boundary":"candidate wording in frozen completed-output wave; metadata-dependent occupation comparisons pending"}
 atomic(public/"PREMETADATA_RECEIPT_PUBLIC.json",receipt)
if __name__=="__main__":main()
