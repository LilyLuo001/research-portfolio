#!/usr/bin/env python3
"""Project the frozen D66 private overlay to public measurement coverage counts."""
import argparse, collections, csv, datetime as dt, hashlib, json, os, platform
import pyarrow.parquet as pq

VERSION = "d66-first5-measurement-coverage-v1"
POPULATIONS = (
    ("current_processed", lambda r: r["current_processing_status"] == "processed"),
    ("old_usable_current_processed", lambda r: r["current_processing_status"] == "processed" and r["old_match"] is True and r["old_usable"] is True),
)
METRICS = (
    ("old", "old_numeric_literal_candidate", "old_numeric_experience_candidate",
     "typed_experience_or_v6_literal_candidate", "candidate_not_detected; no universal minimum is inferred"),
    ("current", "current_numeric_literal_candidate", "current_numeric_experience_candidate",
     "current_rule_duration_literal_candidate", "candidate_not_detected; no universal minimum is inferred"),
    ("old", "old_audit_row_present", "old_v6_audit_row_coverage",
     "selected_v6_audit_row_presence", "no audit row means outside selected audit evidence, not semantic absence"),
    ("old", "old_explicit_noexperience_candidate", "old_explicit_noexperience_candidate",
     "selected_v6_audit_candidate", "candidate_not_detected; not unconditional eligibility"),
    ("old", "old_explicit_noexperience_applicant_context_candidate", "old_explicit_noexperience_applicant_context_candidate",
     "selected_v6_audit_candidate", "candidate_not_detected; retained applicant-context flag"),
    ("old", "old_qualification_alternative_candidate", "old_qualification_alternative_candidate",
     "selected_v6_audit_candidate", "candidate_not_detected; broad alternative candidate, not degree-or-experience certification"),
    ("old", "old_equivalent_experience_candidate", "old_equivalent_experience_candidate",
     "selected_v6_audit_candidate", "candidate_not_detected; reported separately from qualification-alternative union"),
    ("old", "old_qualification_relation_unresolved", "old_qualification_relation_unresolved",
     "selected_v6_audit_uncertainty", "candidate_not_detected; unresolved remains unknown"),
    ("old", "old_mixed_requirement_scope", "old_mixed_requirement_scope",
     "selected_v6_audit_uncertainty", "candidate_not_detected; mixed scope remains unknown"),
    ("old", "old_context_conflict", "old_context_conflict",
     "selected_v6_audit_uncertainty", "candidate_not_detected; conflict remains unknown"),
    ("current", "current_conditional_or_alternative_candidate", "current_conditional_or_alternative_experience_candidate",
     "current_rule_scope_candidate", "candidate_not_detected; conditional/alternative is not universal requirement"),
    ("current", "current_experience_unknown", "current_experience_unknown",
     "current_rule_uncertainty", "candidate_not_detected; unresolved semantics are not filled"),
    ("current", "current_explicit_noexperience_candidate", "current_explicit_noexperience_candidate",
     "current_rule_entry_candidate", "candidate_not_detected; not unconditional eligibility"),
    ("current", "current_explicit_noexperience_unconditional_candidate", "current_explicit_noexperience_unconditional_candidate",
     "current_rule_entry_candidate", "candidate_not_detected; rule-scoped candidate only"),
    ("current", "current_graduate_wording_candidate", "current_graduate_wording_candidate_scope_unknown",
     "current_rule_entry_candidate", "candidate_not_detected; scope is unknown and not unconditional eligibility"),
    ("current", "current_independent_work_or_responsibility_wording", "current_independent_work_or_responsibility_wording",
     "current_rule_responsibility_wording", "candidate_not_detected; wording is not advanced judgment"),
    ("current", "current_client_responsibility_wording", "current_client_responsibility_wording",
     "current_rule_responsibility_wording", "candidate_not_detected; wording is not confirmed authority"),
    ("current", "current_people_supervision_wording", "current_people_supervision_wording",
     "current_rule_responsibility_wording", "candidate_not_detected; wording is not confirmed seniority"),
    ("current", "current_d57_duty_mentoring_candidate", "current_d57_current_duty_mentoring_candidate",
     "current_rule_d57_candidate", "candidate_not_detected; current-duty context candidate only"),
    ("current", "current_duty_context_restricted_responsibility_candidate", "current_duty_context_restricted_responsibility_candidate",
     "current_rule_duties_heading_filter", "candidate_not_detected; context filter is not confirmed authority or seniority"),
)

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def atomic_json(path,value):
    tmp=path+".tmp"
    with open(tmp,"w",encoding="utf-8") as f: json.dump(value,f,indent=2,sort_keys=True); f.write("\n")
    os.replace(tmp,path)

def main():
    p=argparse.ArgumentParser(); p.add_argument("--overlay",required=True); p.add_argument("--public-dir",required=True); p.add_argument("--output",required=True); p.add_argument("--receipt",required=True)
    a=p.parse_args(); producer=json.load(open(os.path.join(a.public_dir,"RUN_RECEIPT_PUBLIC.json"),encoding="utf-8"))
    protected={n:m["sha256"] for n,m in producer["public_outputs"].items()}
    protected["RUN_RECEIPT_PUBLIC.json"]=sha(os.path.join(a.public_dir,"RUN_RECEIPT_PUBLIC.json"))
    overlay_hash=sha(a.overlay)
    if overlay_hash!=producer["private_output"]["sha256"]: raise RuntimeError("overlay is not bound to accepted D66 producer receipt")
    columns=sorted(set(["current_processing_status","old_match","old_usable","old_audit_row_present"]+[x[1] for x in METRICS]))
    counts={name:collections.Counter() for name,_ in POPULATIONS}; den=collections.Counter()
    rows_seen=0
    for batch in pq.ParquetFile(a.overlay).iter_batches(columns=columns,batch_size=65536):
        data=batch.to_pylist(); rows_seen+=len(data)
        for row in data:
            for pop,pred in POPULATIONS:
                if not pred(row): continue
                den[pop]+=1
                for _,field,metric,_,_ in METRICS: counts[pop][metric]+=row[field] is True
    if rows_seen!=424226: raise RuntimeError("overlay row conservation failed")
    out=[]
    for pop,_ in POPULATIONS:
        audit_n=counts[pop]["old_v6_audit_row_coverage"]
        for version,field,metric,source,meaning in METRICS:
            n=counts[pop][metric]; d=den[pop]
            source_n=audit_n if source.startswith("selected_v6_audit") else d
            out.append({"population":pop,"denominator":d,"measurement_version":version,"metric":metric,
                "numerator":n,"fraction":n/d if d else None,"not_detected_n":d-n,"na_n":0,
                "source_coverage_n":source_n,"source_coverage_fraction":source_n/d if d else None,
                "availability_status":"selected_audit_candidate_flag" if source.startswith("selected_v6_audit") else "candidate_flag_available",
                "source_measure":source,"false_or_missing_meaning":meaning})
    tmp=a.output+".tmp"
    with open(tmp,"w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    os.replace(tmp,a.output)
    unchanged=all(sha(os.path.join(a.public_dir,n))==h for n,h in protected.items())
    if not unchanged: raise RuntimeError("protected original public result changed")
    receipt={"version":VERSION,"status":"pass","created_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "scheduler":{"job_id":os.environ.get("SLURM_JOB_ID"),"host":platform.node(),"cpus":os.environ.get("SLURM_CPUS_PER_TASK")},
        "input":{"overlay_sha256":overlay_hash,"overlay_rows":rows_seen,"producer_receipt_sha256":protected["RUN_RECEIPT_PUBLIC.json"]},
        "population_denominators":dict(den),"metric_count":len(METRICS),"output_rows":len(out),
        "checks":{"overlay_424226_rows":True,"numerators_not_above_denominator":all(r["numerator"]<=r["denominator"] for r in out),
            "not_detected_conservation":all(r["numerator"]+r["not_detected_n"]+r["na_n"]==r["denominator"] for r in out),
            "protected_original_public_hashes_unchanged":unchanged},
        "output":{"path":a.output,"bytes":os.path.getsize(a.output),"sha256":sha(a.output)},
        "api_calls":0,"model_calls":0,"full_text_reads":0,
        "claim_boundary":"candidate and engineering coverage only; false means not detected under the named rule, not semantic absence"}
    atomic_json(a.receipt,receipt)

if __name__=="__main__": main()
