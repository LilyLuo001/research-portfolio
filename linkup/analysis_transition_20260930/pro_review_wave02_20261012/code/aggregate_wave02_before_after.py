#!/usr/bin/env python3
"""Apply exact Wave02 reviews to the KS13 subset and report same-universe deltas."""
import argparse, collections, csv, datetime as dt, hashlib, json, os, platform
from pathlib import Path
import pyarrow.parquet as pq

KEY=("JOB_HASH","SOURCE_FILE","SOURCE_ROW","RECORD_SOURCE_ROW")
ARMS=("software_only","any_ai")
EXP_DIMS=("general_work","occupation_task","industry_domain","tool_specific")
RESP_DIMS=("independent_judgment","client_ownership","people_supervision","training_mentoring")
VERSION="pro-wave02-ks13-before-after-v1"

def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""): h.update(b)
 return h.hexdigest()

def rows(p,cols):
 for b in pq.ParquetFile(p).iter_batches(batch_size=32768,columns=cols):
  d=b.to_pydict()
  for i in range(b.num_rows): yield {n:d[n][i] for n in d}

def key(r): return tuple(r[x] for x in KEY)
def arm(v): return "software_only" if v=="software_only" else ("any_ai" if v in ("ai_only","software_and_ai") else None)
def read_jsonl(p): return [json.loads(x) for x in open(p,encoding="utf-8") if x.strip()]
def write_csv(p,vals):
 if not vals: raise RuntimeError("empty output "+str(p))
 t=Path(str(p)+".tmp")
 with open(t,"w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=list(vals[0])); w.writeheader(); w.writerows(vals)
 os.replace(t,p)
def write_json(p,v):
 t=Path(str(p)+".tmp"); t.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n"); os.replace(t,p)

def baseline(row,f):
 f=f or {}; z={}
 for dim in EXP_DIMS:
  old="tool" if dim=="tool_specific" else dim
  broad=row["current_%s_broad"%old] is True
  z["experience."+dim]=broad
  req=f.get("current_%s_required_any_scope"%old) is True
  pref=f.get("current_%s_preferred_any_scope"%old) is True
  mixed=f.get("current_%s_mixed_any_scope"%old) is True
  su=f.get("current_%s_strength_unknown"%old) is True
  ou=f.get("current_%s_outcome_unknown"%old) is True
  for n,v in (("required",req),("preferred",pref),("unspecified",broad and not(req or pref or mixed or su or ou)),
              ("unresolved",mixed or su or ou)): z["experience_strength.%s.%s"%(dim,n)]=v
  uncond=any(f.get("current_%s_%s_unconditional"%(old,s)) is True for s in ("required","preferred","mixed"))
  cond=any(f.get("current_%s_%s_conditional_or_alternative"%(old,s)) is True for s in ("required","preferred","mixed"))
  unk=any(f.get("current_%s_%s_unknown_scope"%(old,s)) is True for s in ("required","preferred","mixed")) or ou
  for n,v in (("unconditional",uncond),("conditional",cond),("unspecified",broad and not(uncond or cond or unk)),
              ("unresolved",unk)): z["experience_conditionality.%s.%s"%(dim,n)]=v
 z["entry.explicit_target_wording"]=row["current_explicit_noexperience_candidate"] is True or row["current_graduate_wording_candidate"] is True
 for dim,field in (("independent_judgment","current_independent_responsibility_wording"),
                   ("client_ownership","current_client_ownership_wording"),
                   ("people_supervision","current_people_supervision_wording"),
                   ("training_mentoring","current_d57_duty_mentoring_candidate")):
  z["responsibility."+dim]=row[field] is True
 z["responsibility.any_broad"]=any(z["responsibility."+d] for d in RESP_DIMS)
 z["responsibility.any_strict_current_duty"]=row["current_strict_duty_responsibility_candidate"] is True
 return z

def apply_review(before,review):
 after=dict(before); unresolved=[]; q=review["question"]; d=review["decision"]
 if q=="experience_4dims":
  clauses=d["clauses"]
  for item in d["dimension_outcomes"]:
   dim=item["dimension"]; status=item["ad_level_presence"]; prefix="experience."+dim
   if status=="unknown": unresolved.append(prefix); continue
   present=status=="present"; after[prefix]=present
   all_selected=[c for c in clauses if c["resulting_dimension"]==dim]
   selected=[c for c in all_selected if c["candidate_resolution"] in ("confirmed","corrected")]
   strengths={c["strength"] for c in selected if c["strength"]!="unresolved"}
   conds={c["conditionality"] for c in selected if c["conditionality"]!="unresolved"}
   if present and not all_selected: strengths={"unspecified"}; conds={"unspecified"}
   strength_unresolved=present and any(c["candidate_resolution"]=="unresolved" or c["strength"]=="unresolved" for c in all_selected)
   conditionality_unresolved=present and any(c["candidate_resolution"]=="unresolved" or c["conditionality"]=="unresolved" for c in all_selected)
   for x in ("required","preferred","unspecified"):
    field="experience_strength.%s.%s"%(dim,x)
    if not present: after[field]=False
    elif x in strengths: after[field]=True
    elif not strength_unresolved: after[field]=False
   if strength_unresolved:
    unresolved.append("experience_strength.%s"%dim)
   else: after["experience_strength.%s.unresolved"%dim]=False
   for x in ("unconditional","conditional","unspecified"):
    field="experience_conditionality.%s.%s"%(dim,x)
    if not present: after[field]=False
    elif x in conds: after[field]=True
    elif not conditionality_unresolved: after[field]=False
   if conditionality_unresolved:
    unresolved.append("experience_conditionality.%s"%dim)
   else: after["experience_conditionality.%s.unresolved"%dim]=False
 elif q=="entry_responsibility_4dims":
  e=d["entry"]; es=e["ad_level_presence"]
  if es=="unknown": unresolved.append("entry.explicit_target_wording")
  else:
   target=e["target"]
   after["entry.explicit_target_wording"]=es=="present" and target in ("explicit_no_experience","explicit_new_graduate")
  strict=[]
  for item in d["responsibilities"]:
   dim=item["dimension"]; status=item["ad_level_presence"]; field="responsibility."+dim
   if status=="unknown": unresolved.append(field); strict.append(None); continue
   broad=(status=="present" and item["subject"]=="advertised_worker" and
          item["relation"] in ("current_duty","required_capability"))
   after[field]=broad
   strict.append(status=="present" and item["subject"]=="advertised_worker" and item["relation"]=="current_duty")
  after["responsibility.any_broad"]=any(after["responsibility."+x] for x in RESP_DIMS)
  if None not in strict: after["responsibility.any_strict_current_duty"]=any(strict)
  else: unresolved.append("responsibility.any_strict_current_duty")
 return after,unresolved

def reviewed_unknown_count(counter,field,ar):
 if field.startswith("experience.") or field.startswith("experience_strength.") or field.startswith("experience_conditionality."):
  dim=field.split(".")[1]; return counter[("experience_4dims",dim,ar,"unknown")]
 if field.startswith("entry."):
  return counter[("entry_responsibility_4dims","entry",ar,"unknown")]
 if field.startswith("responsibility.") and field.split(".")[1] in RESP_DIMS:
  return counter[("entry_responsibility_4dims",field.split(".")[1],ar,"unknown")]
 return 0

def main():
 p=argparse.ArgumentParser(); p.add_argument("--global-manifest",required=True); p.add_argument("--frozen-manifest",required=True)
 p.add_argument("--closing-root",required=True); p.add_argument("--review-overlay",required=True); p.add_argument("--validation-receipt",required=True)
 p.add_argument("--selection-receipt",required=True); p.add_argument("--output",required=True); a=p.parse_args()
 gm=json.load(open(a.global_manifest)); frozen=json.load(open(a.frozen_manifest)); vr=json.load(open(a.validation_receipt)); sr=json.load(open(a.selection_receipt))
 if gm.get("status")!="complete" or gm.get("rows")!=5804936 or len(gm.get("shards",[]))!=69: raise RuntimeError("global gate")
 if (vr.get("status")!="pass" or vr.get("checks",{}).get("schema_validated") is not True or
     vr.get("environment",{}).get("jsonschema_available") is not True):
  raise RuntimeError("review validation did not pass full Draft202012 schema gate")
 reviews=read_jsonl(a.review_overlay)
 if len(reviews)!=96: raise RuntimeError("expected 96 exact review rows")
 review_by_key={tuple(x["canonical_key"][k] for k in KEY):x for x in reviews}
 if len(review_by_key)!=96: raise RuntimeError("duplicate review canonical key")
 frozen_by={x["shard_id"]:x for x in frozen["shards"]}; ks=[x for x in gm["shards"] if x["region"]=="kunshan"]
 global_cells=collections.Counter(); ks_cells=collections.Counter()
 basic=["current_processing_status","old_usable","current_technology_group","ONET_OCCUPATION_CODE","official_occupation_status"]
 for it in gm["shards"]:
  n=0
  for r in rows(it["enriched_path"],basic):
   n+=1; ar=arm(r["current_technology_group"])
   if r["current_processing_status"]=="processed" and r["old_usable"] is True and ar and r["official_occupation_status"]=="official_code" and r["ONET_OCCUPATION_CODE"]:
    global_cells[(r["ONET_OCCUPATION_CODE"],ar)]+=1
    if it["region"]=="kunshan": ks_cells[(r["ONET_OCCUPATION_CODE"],ar)]+=1
  if n!=it["rows"]: raise RuntimeError("global row gate")
 full={o for o,ar in global_cells if all(global_cells[(o,x)]>=20 for x in ARMS)}
 weights={o:min(global_cells[(o,x)] for x in ARMS) for o in full}
 if len(full)!=332 or sum(weights.values())!=103820: raise RuntimeError("published support gate")
 support={o for o in full if all(ks_cells[(o,x)]>0 for x in ARMS)}; tw=sum(weights[o] for o in support)
 feat=[]
 for d in ("general_work","occupation_task","industry_domain","tool"):
  for s in ("required","preferred","mixed"):
   feat += ["current_%s_%s_%s"%(d,s,sc) for sc in ("any_scope","unconditional","conditional_or_alternative","unknown_scope")]
  feat += ["current_%s_strength_unknown"%d,"current_%s_outcome_unknown"%d]
 ecols=list(KEY)+basic+["current_%s_broad"%d for d in ("general_work","occupation_task","industry_domain","tool")]+[
  "current_explicit_noexperience_candidate","current_graduate_wording_candidate","current_independent_responsibility_wording",
  "current_client_ownership_wording","current_people_supervision_wording","current_d57_duty_mentoring_candidate",
  "current_strict_duty_responsibility_candidate"]
 num=collections.Counter(); cohort_den=collections.Counter(); cohort_num=collections.Counter(); cross=collections.Counter(); review_out=collections.Counter(); seen=set()
 for it in ks:
  sid=it["shard_id"]; fp=Path(a.closing_root)/(sid+".strength_features.parquet"); fs={key(r):r for r in rows(fp,list(KEY)+feat)}
  for r in rows(it["enriched_path"],ecols):
   k=key(r); ar=arm(r["current_technology_group"]); occ=r["ONET_OCCUPATION_CODE"]
   if not(r["current_processing_status"]=="processed" and r["old_usable"] is True and ar and r["official_occupation_status"]=="official_code" and occ in support): continue
   before=baseline(r,fs.get(k)); after=dict(before); unresolved=[]; rev=review_by_key.get(k)
   if rev:
    after,unresolved=apply_review(before,rev); seen.add(k)
   for field in before:
    num[("before",field,occ,ar)]+=before[field] is True; num[("after",field,occ,ar)]+=after[field] is True
   for ver,z in (("before",before),("after",after)):
    entry=z["entry.explicit_target_wording"]; resp=z["responsibility.any_broad"]
    cross[(ver,ar,entry,resp)]+=1
    if entry:
     cohort_den[(ver,occ,ar)]+=1
     for field in z: cohort_num[(ver,field,occ,ar)]+=z[field] is True
   if rev:
    q=rev["question"]
    if q=="experience_4dims":
     for x in rev["decision"]["dimension_outcomes"]: review_out[(q,x["dimension"],ar,x["ad_level_presence"])]+=1
    else:
     review_out[(q,"entry",ar,rev["decision"]["entry"]["ad_level_presence"])]+=1
     review_out[(q,"entry_target."+rev["decision"]["entry"]["target"],ar,rev["decision"]["entry"]["ad_level_presence"])]+=1
     review_out[(q,"entry_conditionality."+rev["decision"]["entry"]["conditionality"],ar,rev["decision"]["entry"]["ad_level_presence"])]+=1
     for x in rev["decision"]["responsibilities"]: review_out[(q,x["dimension"],ar,x["ad_level_presence"])]+=1
    for field in unresolved: review_out[(q,field,ar,"unchanged_unresolved")]+=1
 if seen!=set(review_by_key): raise RuntimeError("not all reviewed keys found in KS support universe")
 fields=sorted({k[1] for k in num}); result=[]
 for field in fields:
  for ar in ARMS:
   den=sum(ks_cells[(o,ar)] for o in support)
   vals={}
   for ver in ("before","after"):
    n=sum(num[(ver,field,o,ar)] for o in support); rate=sum(weights[o]/tw*num[(ver,field,o,ar)]/ks_cells[(o,ar)] for o in support)
    vals[ver]=(n,rate)
   reviewed_unknown=reviewed_unknown_count(review_out,field,ar)
   result.append({"scope":"KS13_same_universe_local_both_arm_support","technology_arm":ar,"field":field,"denominator_ads":den,
    "before_candidate_n":vals["before"][0],"after_candidate_plus_resolved_correction_n":vals["after"][0],
    "before_no_candidate_n":den-vals["before"][0],"after_no_candidate_or_resolved_absence_n":den-vals["after"][0],
    "reviewed_unknown_n_retained_before":reviewed_unknown,
    "before_standardized_rate":vals["before"][1],"after_standardized_rate":vals["after"][1],
    "difference_percentage_points":100*(vals["after"][1]-vals["before"][1]),
    "interpretation":"original rule candidates plus exact reviewed-row corrections; not semantic population prevalence"})
 review_rows=[]
 for q,field,ar,status in sorted(review_out): review_rows.append({"question":q,"field":field,"technology_arm":ar,"review_outcome":status,"ads":review_out[(q,field,ar,status)]})
 for q,fields_q in (("experience_4dims",EXP_DIMS),("entry_responsibility_4dims",("entry",)+RESP_DIMS)):
  for ar in ARMS:
   reviewed=len([x for x in reviews if x["question"]==q and x["technology_arm"]==ar])
   den=sum(ks_cells[(o,ar)] for o in support)
   for field in fields_q: review_rows.append({"question":q,"field":field,"technology_arm":ar,"review_outcome":"unreviewed","ads":den-reviewed})
 cross_rows=[{"version":ver,"technology_arm":ar,"entry_candidate":entry,"any_broad_responsibility":resp,"ads":cross[(ver,ar,entry,resp)],
              "universe":"same KS13 locally both-arm-supported ads"} for ver in ("before","after") for ar in ARMS for entry in (False,True) for resp in (False,True)]
 # Freeze one entry-cohort occupation support across both arms and both versions.
 entry_support={o for o in support if all(cohort_den[(ver,o,ar)]>0 for ver in ("before","after") for ar in ARMS)}
 entry_tw=sum(weights[o] for o in entry_support)
 cohort=[]
 for ver in ("before","after"):
  for ar in ARMS:
   den=sum(cohort_den[(ver,o,ar)] for o in support)
   for field in fields:
    n=sum(cohort_num[(ver,field,o,ar)] for o in support)
    rate=sum(weights[o]/entry_tw*cohort_num[(ver,field,o,ar)]/cohort_den[(ver,o,ar)] for o in entry_support) if entry_tw else None
    cohort.append({"version":ver,"technology_arm":ar,"entry_cohort_denominator_ads":den,"field":field,"candidate_n":n,
                   "standardized_rate_within_entry_cohort":rate,"fixed_common_entry_support_occupations":len(entry_support),
                   "retained_weight_mass":entry_tw,"removed_support_weight":tw-entry_tw,
                   "note":"entry membership may change; raw before/after denominators differ, while the same positive-cohort support and original weights are frozen once"})
 out=Path(a.output); out.mkdir(parents=True,exist_ok=True)
 write_csv(out/"BEFORE_AFTER_FIELDS_PUBLIC.csv",result); write_csv(out/"REVIEW_ONLY_OUTCOMES_PUBLIC.csv",review_rows)
 write_csv(out/"ENTRY_RESPONSIBILITY_CROSSTAB_PUBLIC.csv",cross_rows); write_csv(out/"ENTRY_COHORT_FIELDS_PUBLIC.csv",cohort)
 summary={"version":VERSION,"status":"pass","scope":"KS13 subset of frozen69","reviewed_exact_records":96,"full69_baseline_is_separate":True,
  "support":{"full69_occupations":332,"ks_local_both_arm_occupations":len(support),"full69_weight_sum":103820,"retained_weight_sum":tw,
             "fixed_common_entry_support_occupations":len(entry_support),"fixed_common_entry_weight_sum":entry_tw,
             "entry_removed_support_weight":tw-entry_tw},
  "method":"exact reviewed-row updates only; unknown review outcomes retain frozen candidate state and are separately counted",
  "technology_group_boundary":"software_only and any_ai are frozen rule-classified technology groups, not verified AI adoption",
  "entry_boundary":"explicit graduate wording is an explicit entry-target wording candidate, not validated first-career or entry-level status; conditionality is reported separately",
  "responsibility_mapping":{"broad":"present for advertised worker with relation current_duty or required_capability",
                            "strict":"present for advertised worker with relation current_duty only"},
  "limits":["purposeful 96 is not an accuracy sample","unreviewed rule candidates remain candidates","small changes do not establish robustness","no propagation beyond exact reviewed key",
            "frozen any-AI group can include law-degree LLM wording and employer/recruiting technology background",
            "current-text descriptions do not establish historical change, AI causality, or a seniorization trend"]}
 write_json(out/"SUMMARY_PUBLIC.json",summary)
 receipt={"version":VERSION,"status":"pass","created_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"scheduler":{"job_id":os.environ.get("SLURM_JOB_ID"),"host":platform.node()},
  "inputs":{"review_overlay_sha256":sha(a.review_overlay),"validation_receipt_sha256":sha(a.validation_receipt),"selection_receipt_sha256":sha(a.selection_receipt),"global_manifest_sha256":sha(a.global_manifest)},
  "checks":{"review_count_96":True,"exact_keys_unique":True,"all_review_keys_in_same_KS_support_universe":True,"frozen_332_weights_reproduced":True,"unknown_retains_before":True,"unreviewed_unchanged":True},
  "outputs":{p.name:{"sha256":sha(p),"bytes":p.stat().st_size} for p in out.iterdir() if p.is_file() and p.name != "RUN_RECEIPT_PUBLIC.json"},"api_calls":0,"model_calls":0}
 write_json(out/"RUN_RECEIPT_PUBLIC.json",receipt)

if __name__=="__main__": main()
