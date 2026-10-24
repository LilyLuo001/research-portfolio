#!/usr/bin/env python3
"""Frozen Batch069 fixed10k empirical aggregates. Never reads advertisement text."""
from __future__ import annotations

import argparse, csv, hashlib, json, math, os, shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

KEY = ["JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW"]
FAMILIES = (
    "technology_category_and_role", "experience_object", "experience_strength",
    "experience_literal_years", "qualification_conditions_and_alternatives",
    "entry_wording_and_scope", "current_responsibility_subject_and_relation",
)
EXP = ("general_work", "occupation_task", "industry_domain", "tool_specific")
DUTY = ("independent_judgment", "client_ownership", "people_supervision", "training_mentoring")
MAJORS = ("11", "13", "15", "17")
GA = "genai_use_with_or_without_software"
GB = "traditional_software_use_no_ai"
USABLE = {"known", "not_applicable"}
ACTIVE = {"use_tool_for_work", "develop_technology", "implement_deploy_technology"}

def sha(p: Path) -> str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024), b""): h.update(b)
    return h.hexdigest()

def write_csv(path: Path, rows: list[dict]):
    df=pd.DataFrame(rows)
    df.to_csv(path,index=False,quoting=csv.QUOTE_MINIMAL)

def key_of(x):
    y=x.get("canonical_key",x)
    return tuple(str(y[k]) for k in KEY)

def yn(v):
    return {"present":1, "not_mentioned":0}.get(v)

def tech_detail(status, value):
    if status not in USABLE or not isinstance(value,dict): return "uncertain_technology"
    items=value.get("items",[]); inv=value.get("inventory_status")
    if inv == "unknown" or any(x.get("family")=="unresolved" or x.get("role")=="unresolved" for x in items): return "uncertain_technology"
    active=[x for x in items if x.get("role") in ACTIVE]
    gu=any(x.get("family")=="generative_ai" and x.get("role")=="use_tool_for_work" for x in active)
    tu=any(x.get("family")=="traditional_software_system" and x.get("role")=="use_tool_for_work" for x in active)
    pred=any(x.get("family")=="predictive_ml_ai" and x.get("role") in ACTIVE for x in items)
    aidev=any(x.get("family") in {"generative_ai","predictive_ml_ai"} and x.get("role") in {"develop_technology","implement_deploy_technology"} for x in active)
    background=any(x.get("role")=="background_mention" for x in items)
    if aidev:return "ai_develop_implement_other"
    if pred:return "predictive_ai_or_mixed"
    if gu and tu:return "genai_traditional_overlap"
    if background and not (gu or tu):return "background_or_mixed"
    if gu:return "genai_use_only"
    if tu:return GB
    if not items and inv=="not_mentioned_after_full_review":return "no_relevant_technology_mentioned"
    return "other_explicit_technology"

def group(detail): return GA if detail in {"genai_use_only","genai_traditional_overlap"} else detail

def entry_value(status,value,target,unconditional=False):
    if status not in USABLE or not isinstance(value,dict): return None
    outs=value.get("outcomes",{}); base=yn(outs.get(target))
    items=[x for x in value.get("items",[]) if x.get("target")==target]
    if not unconditional:return base
    if any(x.get("conditionality")=="unconditional" for x in items):return 1
    if base==1 and items and all(x.get("conditionality")=="conditional" for x in items):return 0
    return 0 if base==0 else None

def duty_value(status,value,dim):
    if status not in USABLE or not isinstance(value,dict):return None
    o=yn(value.get("outcomes",{}).get(dim))
    if o is None:return None
    return int(any(x.get("dimension")==dim and x.get("subject")=="advertised_worker" and x.get("relation")=="current_duty" for x in value.get("items",[])))

def rate(rows, field, subset=lambda r:True):
    rr=[r for r in rows if subset(r)]; vals=[r.get(field) for r in rr]
    pos=sum(v==1 for v in vals); known=sum(v in (0,1) for v in vals); unk=len(vals)-known
    return {"total_ads":len(rr),"known_ads":known,"positive_ads":pos,"unknown_ads":unk,
            "point":None if not known else pos/known,
            "lower":None if not rr else pos/len(rr),"upper":None if not rr else (pos+unk)/len(rr)}

def direct_q1(rows, frame):
    out=[]
    scopes=[("raw",lambda r:True),("frozen_common_support",lambda r:str(r["occupation_major"]) in MAJORS)]
    scopes += [("major_"+m,lambda r,m=m:str(r["occupation_major"])==m) for m in MAJORS]
    measures=["experience_"+x for x in EXP]
    for e in EXP:
      measures += [f"strength_{e}_{s}" for s in ("required","preferred","explicitly_waived")]
      measures += [f"numeric_years_{e}",f"conditional_{e}",f"alternative_branch_{e}",f"alternative_or_branch_{e}",f"alternative_and_branch_{e}"]
    for measure in measures:
      field=measure
      for scope,sc in scopes:
        gs={}
        for g in (GA,GB):
          z=rate(rows,measure,lambda r,g=g,sc=sc:sc(r) and r["technology_group"]==g); gs[g]=z
          out.append({"frame":frame,"weight":"1","scope":scope,"measure":field,"row_type":"group_rate","group":g,**z})
        a,b=gs[GA],gs[GB]
        out.append({"frame":frame,"weight":"1","scope":scope,"measure":field,"row_type":"difference","group":"GenAI_minus_software","total_ads":None,"known_ads":None,"positive_ads":None,"unknown_ads":None,
                    "point":None if a["point"] is None or b["point"] is None else a["point"]-b["point"],
                    "lower":None if a["lower"] is None or b["upper"] is None else a["lower"]-b["upper"],
                    "upper":None if a["upper"] is None or b["lower"] is None else a["upper"]-b["lower"]})
      for g in (GA,GB):
        parts=[rate(rows,measure,lambda r,g=g,m=m:r["technology_group"]==g and str(r["occupation_major"])==m) for m in MAJORS]
        point_ok=all(x["known_ads"]>0 for x in parts); bounds_ok=all(x["total_ads"]>0 for x in parts)
        z={"point":sum(x["point"] for x in parts)/4 if point_ok else None,
           "lower":sum(x["lower"] for x in parts)/4 if bounds_ok else None,
           "upper":sum(x["upper"] for x in parts)/4 if bounds_ok else None}
        out.append({"frame":frame,"weight":"1","scope":"equal_0.25_major_standardization","measure":field,"row_type":"group_rate","group":g,"total_ads":sum(x["total_ads"] for x in parts),"known_ads":sum(x["known_ads"] for x in parts),"positive_ads":sum(x["positive_ads"] for x in parts),"unknown_ads":sum(x["unknown_ads"] for x in parts),**z})
      aa=next(x for x in out if x["frame"]==frame and x["scope"]=="equal_0.25_major_standardization" and x["measure"]==field and x["group"]==GA)
      bb=next(x for x in out if x["frame"]==frame and x["scope"]=="equal_0.25_major_standardization" and x["measure"]==field and x["group"]==GB)
      out.append({"frame":frame,"weight":"1","scope":"equal_0.25_major_standardization","measure":field,"row_type":"difference","group":"GenAI_minus_software","total_ads":None,"known_ads":None,"positive_ads":None,"unknown_ads":None,
                  "point":None if aa["point"] is None or bb["point"] is None else aa["point"]-bb["point"],
                  "lower":None if aa["lower"] is None or bb["upper"] is None else aa["lower"]-bb["upper"],
                  "upper":None if aa["upper"] is None or bb["lower"] is None else aa["upper"]-bb["lower"]})
    return out

def direct_q2(rows,frame):
    defs=("explicit_new_graduate","explicit_new_graduate_unconditional","explicit_no_experience","explicit_no_experience_unconditional","graduate_or_noexperience","graduate_or_noexperience_unconditional")
    measures=[("duty_"+d,"current_duty; strength unavailable") for d in DUTY]+[("duty_any","any current duty; strength unavailable")]+[("experience_"+e,"experience outcome") for e in EXP]
    for d in (*DUTY,"any"): measures += [(f"duty_{d}_conditional","current duty conditionality"),(f"duty_{d}_unconditional","current duty conditionality")]
    for e in EXP:
      measures += [(f"strength_{e}_{s}","experience-clause strength; overlapping ad indicator") for s in ("required","preferred","explicitly_waived")]
      measures += [(f"numeric_years_{e}","literal numeric year clause; not job minimum"),(f"conditional_{e}","experience clause condition"),(f"alternative_branch_{e}","experience branch-bound clause"),(f"alternative_or_branch_{e}","experience OR branch"),(f"alternative_and_branch_{e}","experience AND branch")]
    out=[]
    for ed in defs:
      pos=[r for r in rows if r.get(ed)==1]; eunk=sum(r.get(ed) is None for r in rows)
      for m,note in measures:
        z=rate(pos,m)
        out.append({"frame":frame,"weight":"1","eligibility_definition":ed,"measure":m,"eligibility_positive_ads":len(pos),"eligibility_unknown_ads":eunk,"duty_strength":"NA_no_schema_field" if m.startswith("duty_") else None,"interpretation":note,**z})
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--ledger",required=True); ap.add_argument("--fixed",required=True); ap.add_argument("--exclusions",required=True); ap.add_argument("--uncertainty",required=True); ap.add_argument("--final-receipt",required=True); ap.add_argument("--isolation-register",required=True); ap.add_argument("--formal-public",required=True); ap.add_argument("--published-research",required=True); ap.add_argument("--global-t4",required=True); ap.add_argument("--output",required=True); ap.add_argument("--private-output",required=True); a=ap.parse_args()
    out=Path(a.output); priv=Path(a.private_output); done=out/"RUN_RECEIPT_PUBLIC.json"
    if done.exists(): raise SystemExit("guard: completed receipt already exists")
    out.mkdir(parents=True,exist_ok=True); (out/"figures").mkdir(exist_ok=True); priv.mkdir(parents=True,exist_ok=True)
    final_receipt=json.loads(Path(a.final_receipt).read_text())
    if final_receipt.get("status")!="pass":raise RuntimeError("Batch069 final receipt is not pass")
    if sha(Path(a.ledger))!=final_receipt["outputs"]["private_ledger_sha256"]:raise RuntimeError("ledger hash is not Batch069 final")
    if sha(Path(a.uncertainty))!=final_receipt["outputs"]["private_uncertainty_sha256"]:raise RuntimeError("uncertainty hash is not Batch069 final")
    if sha(Path(a.isolation_register))!=final_receipt["inputs"]["isolation_register_sha256"]:raise RuntimeError("isolation register hash mismatch")
    if final_receipt["counts"]["blocked_contexts"]!=14 or final_receipt["counts"]["remaining_unfinished_contexts"]!=14 or final_receipt["counts"]["remaining_reviewed_uncertainty_contexts"]!=1002:raise RuntimeError("Batch069 frozen counts mismatch")
    uncertainty_contexts=set()
    with open(a.uncertainty) as f:
      for line in f: uncertainty_contexts.add(json.loads(line)["normalized_context_sha256"])
    if len(uncertainty_contexts)!=1002:raise RuntimeError("uncertainty context count != 1002")
    isolated_contexts=set()
    with open(a.isolation_register) as f:
      for line in f: isolated_contexts.add(json.loads(line)["normalized_context_sha256"])
    if len(isolated_contexts)!=14:raise RuntimeError("isolation context count != 14")
    fixed_cols=[*KEY,"OCCUPATION_MAJOR","CENSUS_REGION","created_year","arm","exact_text_sha256"]
    frame=pd.read_parquet(a.fixed,columns=fixed_cols)
    if len(frame)!=10000: raise RuntimeError("fixed frame != 10000")
    frame_records=frame.to_dict("records")
    data={}
    with open(a.ledger) as f:
      for line in f:
        x=json.loads(line); k=key_of(x); fam=x["field_family"]
        if fam not in FAMILIES:raise RuntimeError("unexpected family")
        d=data.setdefault(k,{"normalized_context_sha256":x.get("normalized_context_sha256")})
        if fam in d:raise RuntimeError("duplicate ad-family")
        d[fam]={"status":x["status"],"value":x.get("structured_value"),"rule":x.get("resolution_rule")}
    if len(data)!=10000 or any(len([f for f in FAMILIES if f in d])!=7 for d in data.values()): raise RuntimeError("ledger is not 10k x rich7")
    exraw=set(); exnorm=set()
    with open(a.exclusions) as f:
      for line in f:
        x=json.loads(line)
        if x["hash_scope"] in {"raw","raw_exact"}:exraw.add(x["sha256"])
        elif x["hash_scope"]=="normalized":exnorm.add(x["sha256"])
    raw_by_key={key_of(z):z["exact_text_sha256"] for z in frame_records}
    exnorm.update(d["normalized_context_sha256"] for k,d in data.items() if raw_by_key[k] in exraw)
    rows=[]
    for rec in frame_records:
      k=key_of(rec); d=data[k]; r={q:rec[q] for q in fixed_cols}; r["normalized_context_sha256"]=d["normalized_context_sha256"]
      r["occupation_major"]=rec["OCCUPATION_MAJOR"]
      r["original9282eligible"]=rec["exact_text_sha256"] not in exraw and d["normalized_context_sha256"] not in exnorm
      for fam in FAMILIES:r["status_"+fam]=d[fam]["status"]
      tv=d["technology_category_and_role"]; r["technology_detail"]=tech_detail(tv["status"],tv["value"]); r["technology_group"]=group(r["technology_detail"])
      eo=d["experience_object"]
      for e in EXP:r["experience_"+e]=yn(eo["value"].get(e)) if eo["status"] in USABLE and isinstance(eo["value"],dict) else None
      en=d["entry_wording_and_scope"]
      for target in ("explicit_new_graduate","explicit_no_experience"):
        r[target]=entry_value(en["status"],en["value"],target,False); r[target+"_unconditional"]=entry_value(en["status"],en["value"],target,True)
      def either(x,y): return 1 if 1 in (x,y) else 0 if x==0 and y==0 else None
      r["graduate_or_noexperience"]=either(r["explicit_new_graduate"],r["explicit_no_experience"])
      r["graduate_or_noexperience_unconditional"]=either(r["explicit_new_graduate_unconditional"],r["explicit_no_experience_unconditional"])
      dv=d["current_responsibility_subject_and_relation"]
      for dim in DUTY:
       r["duty_"+dim]=duty_value(dv["status"],dv["value"],dim)
       for cond in ("conditional","unconditional"):
        r[f"duty_{dim}_{cond}"]=None if dv["status"] not in USABLE else int(any(x.get("dimension")==dim and x.get("subject")=="advertised_worker" and x.get("relation")=="current_duty" and x.get("conditionality")==cond for x in (dv["value"] or {}).get("items",[])))
      vv=[r["duty_"+x] for x in DUTY]; r["duty_any"]=1 if 1 in vv else 0 if all(x==0 for x in vv) else None
      for cond in ("conditional","unconditional"):
       cvv=[r[f"duty_{x}_{cond}"] for x in DUTY];r[f"duty_any_{cond}"]=1 if 1 in cvv else 0 if all(x==0 for x in cvv) else None
      ss=d["experience_strength"]; yy=d["experience_literal_years"]; cc=d["qualification_conditions_and_alternatives"]
      for e in EXP:
       sl=ss["value"] if ss["status"] in USABLE and isinstance(ss["value"],list) else None
       yl=yy["value"] if yy["status"] in USABLE and isinstance(yy["value"],list) else None
       cv=cc["value"] if cc["status"] in USABLE and isinstance(cc["value"],dict) else None
       for strength in ("required","preferred","explicitly_waived"):
        r[f"strength_{e}_{strength}"]=None if sl is None else int(any(x.get("object")==e and x.get("strength")==strength for x in sl))
       r[f"numeric_years_{e}"]=None if yl is None else int(any(x.get("object")==e and (x.get("years_min") is not None or x.get("years_max") is not None) for x in yl))
       r[f"conditional_{e}"]=None if cv is None else int(any(x.get("object")==e and x.get("conditionality")=="conditional" for x in cv.get("clauses",[])))
       rel_groups={x.get("group"):x.get("relation") for x in cv.get("qualification_alternatives",[])} if cv is not None else {}
       r[f"alternative_branch_{e}"]=None if cv is None else int(any(x.get("object")==e and x.get("alternative_group") in rel_groups and x.get("alternative_branch") is not None for x in cv.get("clauses",[])))
       for rel in ("OR","AND"):
        r[f"alternative_{rel.lower()}_branch_{e}"]=None if cv is None else int(any(x.get("object")==e and rel_groups.get(x.get("alternative_group"))==rel and x.get("alternative_branch") is not None for x in cv.get("clauses",[])))
      rows.append(r)
    if sum(r["original9282eligible"] for r in rows)!=9282:raise RuntimeError("exact exclusion recovery != 9282")
    pd.DataFrame(rows).to_parquet(priv/"AD_LEVEL_JOINED_ANALYSIS_PRIVATE.parquet",index=False)
    frames={"complete_fixed10k":rows,"original9282eligible":[r for r in rows if r["original9282eligible"]]}
    t1=[{"section":"frame","frame":n,"field_family":None,"status":None,"ads":len(rr),"contexts":len({r["normalized_context_sha256"] for r in rr}),"note":"advertisement denominators; contexts never subtracted"} for n,rr in frames.items()]
    t1.append({"section":"frame","frame":"published_Formal800","field_family":None,"status":None,"ads":800,"contexts":719,"note":"published w3 panel unchanged"})
    for n,rr in frames.items():
      for fam in FAMILIES:
       for st,c in Counter(r["status_"+fam] for r in rr).items():t1.append({"section":"family_status","frame":n,"field_family":fam,"status":st,"ads":c,"contexts":len({r["normalized_context_sha256"] for r in rr if r["status_"+fam]==st}),"note":"rich7 family mask"})
    # Isolated/blocked contexts are the surviving never-reviewed/partial contexts; count ads separately.
    iso=[r for r in rows if r["normalized_context_sha256"] in isolated_contexts]
    if {r["normalized_context_sha256"] for r in iso} != isolated_contexts:raise RuntimeError("not all 14 isolated contexts intersect fixed frame")
    t1.append({"section":"isolated_context_accounting","frame":"complete_fixed10k","field_family":"all","status":"preserved","ads":len(iso),"contexts":len({r["normalized_context_sha256"] for r in iso}),"note":"context and ad counts distinct; receipt frozen blocked_contexts=14"})
    write_csv(out/"T1_COVERAGE_AND_ACCOUNTING.csv",t1)
    # T2 family-level clause attributes. Separate families are never joined by
    # list position because the ledger does not expose a cross-family clause ID.
    t2=[]
    for fn,rr in frames.items():
      agg=Counter()
      for r in rr:
       d=data[key_of(r)]
       ss=d["experience_strength"]
       scope=(r["technology_group"],str(r["occupation_major"]))
       if ss["status"] in USABLE and isinstance(ss["value"],list):
        for x in ss["value"]:agg[(*scope,"strength",x.get("object"),x.get("strength"),None,None,None,None,None)]+=1
       yy=d["experience_literal_years"]
       if yy["status"] in USABLE and isinstance(yy["value"],list):
        for x in yy["value"]:agg[(*scope,"literal_years",x.get("object"),None,None,x.get("years_relation"),x.get("years_min"),x.get("years_max"),None)]+=1
       cc=d["qualification_conditions_and_alternatives"]
       if cc["status"] in USABLE and isinstance(cc["value"],dict):
        rel={x.get("group"):x.get("relation") for x in cc["value"].get("qualification_alternatives",[])}
        for x in cc["value"].get("clauses",[]):agg[(*scope,"condition_or_branch",x.get("object"),None,x.get("conditionality"),None,None,None,(rel.get(x.get("alternative_group")),x.get("alternative_branch") is not None))]+=1
        for x in cc["value"].get("qualification_alternatives",[]):agg[(*scope,"alternative_relation",None,None,None,None,None,None,(x.get("relation"),None))]+=1
      for k,v in agg.items():
       pair=k[9] if isinstance(k[9],tuple) else (None,k[9])
       t2.append(dict(frame=fn,domain="all_ads",technology_group=k[0],occupation_major=k[1],weight="1",family_attribute=k[2],object=k[3],strength=k[4],conditionality=k[5],years_relation=k[6],years_min=k[7],years_max=k[8],alternative_relation=pair[0],branch_identifier_known=pair[1],clause_count=v,ad_count=None,literal_clause_not_unique_job_minimum=True,cross_family_binding="NA_no_joint_clause_id"))
      # Per-ad overlapping strength/years/condition/alternative indicators.
      for domain,pred in (("all_ads",lambda x:True),("explicit_new_graduate",lambda x:x["explicit_new_graduate"]==1),("explicit_no_experience",lambda x:x["explicit_no_experience"]==1)):
       for e in EXP:
        for measure in [f"strength_{e}_{s}" for s in ("required","preferred","explicitly_waived")]+[f"numeric_years_{e}",f"conditional_{e}",f"alternative_branch_{e}",f"alternative_or_branch_{e}",f"alternative_and_branch_{e}"]:
         z=rate(rr,measure,pred);t2.append(dict(frame=fn,domain=domain,technology_group="all",occupation_major="all",weight="1",family_attribute="overlapping_ad_indicator",object=e,strength=measure.split("_")[-1] if measure.startswith("strength_") else None,conditionality="conditional" if measure.startswith("conditional_") else None,years_relation="numeric_present" if measure.startswith("numeric_years_") else None,years_min=None,years_max=None,alternative_relation="OR" if measure.startswith("alternative_branch_") else None,branch_identifier_known=None,clause_count=None,ad_count=z["positive_ads"],literal_clause_not_unique_job_minimum=True,cross_family_binding="not_used"))
    write_csv(out/"T2_EXPERIENCE_CLAUSES.csv",t2)
    # T3 technology detail/overlap and four-experience combinations.
    t3=[]
    for fn,rr in frames.items():
      for td,c in Counter(r["technology_detail"] for r in rr).items():t3.append({"frame":fn,"section":"technology_role_group","technology":td,"experience_combination":None,"ads":c})
      for (tech,combo),c in Counter((r["technology_group"],tuple("unknown" if r["experience_"+e] is None else str(r["experience_"+e]) for e in EXP)) for r in rr).items():t3.append({"frame":fn,"section":"experience_combination_by_technology","technology":tech,"experience_combination":"|".join(f"{e}={v}" for e,v in zip(EXP,combo)),"ads":c})
    write_csv(out/"T3_TECHNOLOGY_AND_EXPERIENCE_COMBINATIONS.csv",t3)
    # T4 only supported created_year; unavailable fields are explicit rows.
    t4=[]
    for fn,rr in frames.items():
      for (year,tech),c in Counter((r["created_year"],r["technology_group"]) for r in rr).items():t4.append({"frame":fn,"analysis":"annual_descriptive","created_year":year,"technology_group":tech,"ads":c,"valid_date_denominator":sum(x["created_year"]==year for x in rr),"status":"available","reason":"existing created_year"})
      for analysis in ("quarter_crossing","cut_2022_11_30","cut_2023_01_01","same_company_similar_job_first_seen"):
       t4.append({"frame":fn,"analysis":analysis,"created_year":None,"technology_group":None,"ads":None,"valid_date_denominator":None,"status":"NA","reason":"verified fixed10k metadata has no exact date/company/title; no raw text or semantic matcher used"})
    write_csv(out/"T4_TIME_COHORT_DIAGNOSTICS.csv",t4)
    gt=out/"global_T4_reused_unchanged";gt.mkdir()
    gtm=[]
    for src in sorted(Path(a.global_t4).iterdir()):
      if src.is_file():
       dst=gt/src.name;shutil.copy2(src,dst);gtm.append({"file":src.name,"sha256":sha(dst),"scope":"global_204774035_rows_2464_shards_reused; not fixed10k"})
    write_csv(out/"T4_GLOBAL_REUSE_MANIFEST.csv",gtm)
    q1=[];q2=[]
    for fn,rr in frames.items():q1+=direct_q1(rr,fn);q2+=direct_q2(rr,fn)
    write_csv(out/"T5_Q1_DIRECT_COMPARISONS.csv",q1);write_csv(out/"T5_Q2_DIRECT_COMPARISONS.csv",q2)
    co=[]
    for fn,rr in frames.items():
     for ed in ("explicit_new_graduate","explicit_new_graduate_unconditional","explicit_no_experience","explicit_no_experience_unconditional"):
      er=[r for r in rr if r[ed]==1]
      for d in DUTY:
       for e in EXP:
        cnt=Counter((r["duty_"+d],r["experience_"+e]) for r in er)
        co.append({"frame":fn,"eligibility_definition":ed,"duty":d,"experience":e,"eligible_ads":len(er),"both_known_ads":sum(v for (a,b),v in cnt.items() if a in (0,1) and b in (0,1)),"both_positive_ads":cnt[(1,1)],"duty_positive_experience_zero_ads":cnt[(1,0)],"duty_zero_experience_positive_ads":cnt[(0,1)],"either_unknown_ads":sum(v for (a,b),v in cnt.items() if a is None or b is None)})
      combos=Counter((tuple("unknown" if r["experience_"+e] is None else str(r["experience_"+e]) for e in EXP),"unknown" if r["duty_any"] is None else str(r["duty_any"])) for r in er)
      for (combo,dany),n in combos.items():
       co.append({"frame":fn,"eligibility_definition":ed,"duty":"any="+dany,"experience":"|".join(f"{e}={v}" for e,v in zip(EXP,combo)),"eligible_ads":len(er),"both_known_ads":None,"both_positive_ads":n,"duty_positive_experience_zero_ads":None,"duty_zero_experience_positive_ads":None,"either_unknown_ads":None})
    write_csv(out/"T5_Q2_DUTY_EXPERIENCE_COOCCURRENCES.csv",co)
    # T6: family unknown, technology membership unknown, occupational sensitivity and claim status.
    t6=[]
    for fn,rr in frames.items():
      for fam in FAMILIES:
       c=Counter(r["status_"+fam] for r in rr)
       t6.append({"frame":fn,"section":"field_family_status","item":fam,"known":c.get("known",0),"not_applicable":c.get("not_applicable",0),"unknown_or_conflict":c.get("unknown_or_conflict",0),"partial":c.get("partial",0),"candidate_only":c.get("candidate_only",0),"value":None,"claim_status":"point estimates only use known/not_applicable; full family mask preserved"})
      t6.append({"frame":fn,"section":"technology_membership_unknown","item":"uncertain_technology","known":None,"not_applicable":None,"unknown_or_conflict":None,"partial":None,"candidate_only":None,"value":sum(r["technology_detail"]=="uncertain_technology" for r in rr),"claim_status":"separate from outcome-family bounds"})
      for m,c in Counter(str(r["occupation_major"]) for r in rr if r["technology_group"] in {GA,GB}).items():t6.append({"frame":fn,"section":"occupational_composition","item":"major_"+m,"known":None,"not_applicable":None,"unknown_or_conflict":None,"partial":None,"candidate_only":None,"value":c,"claim_status":"raw/common-support/within-major/equal-0.25 shown in T5"})
    t6.append({"frame":"published_Formal800","section":"claim_status","item":"design_intervals","known":None,"not_applicable":None,"unknown_or_conflict":None,"partial":None,"candidate_only":None,"value":None,"claim_status":"published w3 estimates and design CIs preserved unchanged; no new direct reweighting"})
    write_csv(out/"T6_SENSITIVITY_BOUNDS_AND_CLAIMS.csv",t6)
    # Copy published artifacts unchanged into a labeled panel.
    pub=out/"published_Formal800_unchanged";pub.mkdir()
    names=["COMPARISON_1_EXPERIENCE.csv","COMPARISON_2_ENTRY_DUTY.csv","T6_SENSITIVITY_AND_BOUNDS.csv","ANALYSIS_RECEIPT.json"]
    pm=[]
    for n in names:
      src=Path(a.formal_public)/n; dst=pub/n; shutil.copy2(src,dst); pm.append({"file":n,"sha256":sha(dst),"label":"published_Formal800_original_w3_unchanged"})
    write_csv(out/"PUBLISHED_FORMAL800_MANIFEST.csv",pm)
    latest=out/"published_Formal800_latest_unchanged";latest.mkdir();latestm=[]
    for src in sorted(Path(a.published_research).iterdir()):
      if src.is_file() and src.suffix in {".csv",".json"}:
       dst=latest/src.name;shutil.copy2(src,dst);latestm.append({"file":src.name,"sha256":sha(dst),"label":"published_Formal800_latest_w3_unchanged"})
    write_csv(out/"PUBLISHED_FORMAL800_LATEST_MANIFEST.csv",latestm)
    # Two plots: points and recorded-family-unknown bounds are visibly distinct.
    plotrows=[x for x in q1 if x["row_type"]=="difference" and x["scope"]=="equal_0.25_major_standardization" and x["point"] is not None]
    fig,ax=plt.subplots(figsize=(10,5)); y=np.arange(len(plotrows)); p=np.array([x["point"] for x in plotrows]); lo=np.array([x["lower"] for x in plotrows]); hi=np.array([x["upper"] for x in plotrows]);ax.errorbar(p,y,xerr=[p-lo,hi-p],fmt="o",capsize=3,label="point + recorded-field-unknown bounds");ax.axvline(0,color="black",lw=.8);ax.set_yticks(y,[f'{x["frame"]}: {x["measure"]}' for x in plotrows]);ax.set_xlabel("GenAI minus traditional-software rate");ax.legend();fig.tight_layout();fig.savefig(out/"figures"/"FIG1_Q1_POINT_AND_UNKNOWN_BOUNDS.png",dpi=180);plt.close(fig)
    plot2=[x for x in q2 if x["eligibility_definition"]=="explicit_new_graduate" and x["measure"].startswith("duty_") and x["point"] is not None]
    fig,ax=plt.subplots(figsize=(10,5));y=np.arange(len(plot2));p=np.array([x["point"] for x in plot2]);lo=np.array([x["lower"] for x in plot2]);hi=np.array([x["upper"] for x in plot2]);ax.errorbar(p,y,xerr=[p-lo,hi-p],fmt="o",capsize=3);ax.set_yticks(y,[f'{x["frame"]}: {x["measure"]}' for x in plot2]);ax.set_xlim(0,1);ax.set_xlabel("Rate among explicit-graduate-positive ads: point and recorded-duty-unknown bounds");fig.tight_layout();fig.savefig(out/"figures"/"FIG2_Q2_POINT_AND_UNKNOWN_BOUNDS.png",dpi=180);plt.close(fig)
    inputs={str(Path(p)):{"sha256":sha(Path(p)),"bytes":Path(p).stat().st_size} for p in (a.ledger,a.fixed,a.exclusions,a.uncertainty,a.final_receipt,a.isolation_register)}
    inputs["global_T4_reuse"]={"files":{p.name:sha(p) for p in sorted(Path(a.global_t4).iterdir()) if p.is_file()},"scope":"existing global results; no reconstruction"}
    outputs={str(p.relative_to(out)):{"sha256":sha(p),"bytes":p.stat().st_size} for p in sorted(out.rglob("*")) if p.is_file()}
    receipt={"version":"fixed10k-empirical-batch069-v1","status":"pass","created_utc":datetime.now(timezone.utc).isoformat(),"code_sha256":sha(Path(__file__)),"inputs":inputs,"outputs":outputs,"checks":{"fixed10k_ads":len(rows)==10000,"original_eligible_ads":sum(r["original9282eligible"] for r in rows)==9282,"rich7_rows":len(data)*7==70000,"no_text_columns_read":True,"weight_10k_panels":"1","published_formal800":"copied byte-for-byte; w3 unchanged","standardization_fail_closed":"implemented; any missing required cell => NA"},"limits":{"finite_sample":"descriptive points/bounds; no census10k sampling CI","technology_membership_unknown":"separate from outcome bounds","T4":"fixed10k created_year only; exact dates/company/title unavailable; global T4 copied unchanged and separately scoped","duty_strength":"NA; schema has no field","clauses":"literal family rows; no unique job minimum; no cross-family positional binding"},"private_output":{"path":str(priv/"AD_LEVEL_JOINED_ANALYSIS_PRIVATE.parquet"),"sha256":sha(priv/"AD_LEVEL_JOINED_ANALYSIS_PRIVATE.parquet")}}
    done.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")

if __name__=="__main__":main()
