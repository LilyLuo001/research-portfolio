#!/usr/bin/env python3
"""Independent count/conservation QA for D66 measurement coverage projection."""
import argparse,csv,hashlib,json,os
import pyarrow.parquet as pq

FIELDS={
"old_numeric_experience_candidate":"old_numeric_literal_candidate","current_numeric_experience_candidate":"current_numeric_literal_candidate",
"old_v6_audit_row_coverage":"old_audit_row_present","old_explicit_noexperience_candidate":"old_explicit_noexperience_candidate",
"old_explicit_noexperience_applicant_context_candidate":"old_explicit_noexperience_applicant_context_candidate",
"old_qualification_alternative_candidate":"old_qualification_alternative_candidate","old_equivalent_experience_candidate":"old_equivalent_experience_candidate",
"old_qualification_relation_unresolved":"old_qualification_relation_unresolved","old_mixed_requirement_scope":"old_mixed_requirement_scope",
"old_context_conflict":"old_context_conflict","current_conditional_or_alternative_experience_candidate":"current_conditional_or_alternative_candidate",
"current_experience_unknown":"current_experience_unknown","current_explicit_noexperience_candidate":"current_explicit_noexperience_candidate",
"current_explicit_noexperience_unconditional_candidate":"current_explicit_noexperience_unconditional_candidate",
"current_graduate_wording_candidate_scope_unknown":"current_graduate_wording_candidate",
"current_independent_work_or_responsibility_wording":"current_independent_work_or_responsibility_wording",
"current_client_responsibility_wording":"current_client_responsibility_wording","current_people_supervision_wording":"current_people_supervision_wording",
"current_d57_current_duty_mentoring_candidate":"current_d57_duty_mentoring_candidate",
"current_duty_context_restricted_responsibility_candidate":"current_duty_context_restricted_responsibility_candidate"}

def sha(path): return hashlib.sha256(open(path,"rb").read()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--overlay",required=True);p.add_argument("--coverage",required=True);p.add_argument("--receipt",required=True);p.add_argument("--output",required=True);a=p.parse_args()
 published=list(csv.DictReader(open(a.coverage,encoding="utf-8",newline=""))); observed={(r["population"],r["metric"]):r for r in published}
 if len(published)!=40 or len(observed)!=40: raise RuntimeError("coverage rectangularity failed")
 cols=["current_processing_status","old_match","old_usable"]+sorted(set(FIELDS.values())); expected={}; denominators={}
 rows=0
 for batch in pq.ParquetFile(a.overlay).iter_batches(columns=cols,batch_size=65536):
  for r in batch.to_pylist():
   rows+=1
   for pop,keep in (("current_processed",r["current_processing_status"]=="processed"),("old_usable_current_processed",r["current_processing_status"]=="processed" and r["old_match"] is True and r["old_usable"] is True)):
    if not keep: continue
    denominators[pop]=denominators.get(pop,0)+1
    for metric,field in FIELDS.items(): expected[(pop,metric)]=expected.get((pop,metric),0)+(r[field] is True)
 errors=[]
 for k,n in expected.items():
  r=observed[k]; d=denominators[k[0]]
  if int(r["numerator"])!=n or int(r["denominator"])!=d: errors.append("count:"+str(k))
  if int(r["numerator"])+int(r["not_detected_n"])+int(r["na_n"])!=d: errors.append("conservation:"+str(k))
  if int(r["numerator"])>d or int(r["source_coverage_n"])>d: errors.append("bound:"+str(k))
 receipt=json.load(open(a.receipt,encoding="utf-8"))
 checks={"overlay_424226_row_conservation":rows==424226,"exact_40_population_metric_rows":len(observed)==40,
  "counts_independently_recomputed":not errors,"counts_do_not_exceed_denominator":not any(x.startswith("bound") for x in errors),
  "numerator_not_detected_na_conserve":not any(x.startswith("conservation") for x in errors),"coverage_hash_bound":receipt["output"]["sha256"]==sha(a.coverage)}
 result={"version":"d66-measurement-coverage-independent-qa-v1","status":"pass" if all(checks.values()) else "fail","checks":checks,"errors":errors[:50],"population_denominators":denominators}
 tmp=a.output+".tmp";open(tmp,"w").write(json.dumps(result,indent=2,sort_keys=True)+"\n");os.replace(tmp,a.output)
 if result["status"]!="pass": raise SystemExit("measurement coverage QA failed")
if __name__=="__main__":main()
