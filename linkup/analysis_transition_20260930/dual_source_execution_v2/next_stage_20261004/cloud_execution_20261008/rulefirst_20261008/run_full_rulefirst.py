#!/usr/bin/env python3
"""Run frozen rules on 7,635 unique texts and expand mechanically to fixed 10,000.

All public tables are unweighted descriptions of the frozen sample. Sampling
weights are preserved unchanged in the private expanded binding, not used here.
"""
import argparse, collections, csv, datetime as dt, hashlib, json, os, socket, subprocess, sys, time
from multiprocessing import Pool
from pathlib import Path

WEIGHTS=("frame_count_a","frame_count_b","selected_cell_arm_n","inclusion_probability","design_weight","W_h","stable_rank_in_cell_arm","sample_rank_in_cell_arm","nested_frame_cell_arm_N","next_selected_cell_arm_n","original_inclusion_probability","conditional_inclusion_probability","total_inclusion_probability","nested_design_weight","pooled_cell_standardization_weight")
SENSITIVITIES=("all_years_evidence","exclude_needs_review_clauses","unconditional_only","required_only","extreme_exclude_entire_review_document","extreme_clean_document_required_only")

def read(path):
    with open(path,encoding="utf-8") as f:
        for n,line in enumerate(f,1):
            if line.strip(): yield n,json.loads(line)
def digest(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()
def worker(pair):
    i,row=pair; import rule_engine
    text=row.get("original_text"); sha=row.get("exact_text_sha256")
    if not isinstance(text,str) or hashlib.sha256(text.encode()).hexdigest()!=sha:
        return {"queue_position_1based":i,"exact_text_sha256":sha,"status":"source_hash_error"}
    try:
        out=rule_engine.extract(text)
        if out.get("source_text_sha256")!=sha: raise RuntimeError("engine source SHA mismatch")
        return {"queue_position_1based":i,"exact_text_sha256":sha,"status":"complete","result":out}
    except Exception as e:
        return {"queue_position_1based":i,"exact_text_sha256":sha,"status":"engine_error","error_type":type(e).__name__,"error":str(e)[:500]}
def csvout(path,rows,fields):
    with open(path,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
def crows(counter,names):
    return [dict(zip(names,k if isinstance(k,tuple) else (k,)),count=v) for k,v in sorted(counter.items(),key=lambda z:str(z[0]))]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--queue",required=True); ap.add_argument("--represented",required=True)
    ap.add_argument("--output-dir",required=True); ap.add_argument("--engine-dir",required=True); ap.add_argument("--synthetic-test",required=True); ap.add_argument("--workers",type=int,default=4)
    a=ap.parse_args(); start=time.time(); sys.path.insert(0,a.engine_dir); os.environ["PYTHONPATH"]=a.engine_dir+os.pathsep+os.environ.get("PYTHONPATH","")
    subprocess.run([sys.executable,a.synthetic_test],check=True,env=os.environ.copy())
    import rule_engine
    queue=list(read(a.queue)); represented=list(read(a.represented))
    if len(queue)!=7635 or len(represented)!=10000: raise SystemExit("frozen row counts changed")
    queue_shas={r["exact_text_sha256"] for _,r in queue}
    if len(queue_shas)!=7635: raise SystemExit("queue SHA not unique")
    represented_shas={r.get("exact_text_sha256") for _,r in represented}
    if represented_shas!=queue_shas: raise SystemExit("represented and queue SHA sets differ")
    positions=[r.get("fixed_sample_position_1based") for _,r in represented]
    if positions!=list(range(1,10001)) or len(set(positions))!=10000: raise SystemExit("represented positions are not ordered unique 1..10000")
    arms_by_sha=collections.defaultdict(set)
    for _,r in represented: arms_by_sha[r.get("exact_text_sha256")].add(r.get("arm"))
    if any(len(v)!=1 for v in arms_by_sha.values()): raise SystemExit("an exact SHA spans sampling arms")
    with Pool(a.workers) as p: unique=list(p.imap(worker,queue,chunksize=16))
    bysha={r["exact_text_sha256"]:r for r in unique}
    out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True)
    unique_path=out/"FULL7635_RULE_OUTPUTS_PRIVATE.jsonl"
    with open(unique_path,"w",encoding="utf-8") as f:
        for r in unique: f.write(json.dumps(r,ensure_ascii=False,separators=(",",":"))+"\n")
    os.chmod(unique_path,0o600)

    expanded_path=out/"EXPANDED10000_BINDING_PRIVATE.jsonl"
    expanded=[]; arms=collections.Counter()
    with open(expanded_path,"w",encoding="utf-8") as f:
        for _,meta in represented:
            sha=meta.get("exact_text_sha256"); u=bysha.get(sha)
            if u is None: raise SystemExit("represented SHA absent from unique outputs")
            weights=meta.get("weights")
            if not isinstance(weights,dict) or any(k not in weights for k in WEIGHTS): raise SystemExit("nested frozen weights missing")
            row={"fixed_sample_position_1based":meta.get("fixed_sample_position_1based"),"exact_text_sha256":sha,"canonical_key":meta.get("canonical_key"),"arm":meta.get("arm"),"cell":meta.get("cell"),"weights":weights,"unique_rule_status":u["status"],"queue_position_1based":u["queue_position_1based"]}
            f.write(json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\n"); expanded.append((row,u)); arms[row["arm"]]+=1
    os.chmod(expanded_path,0o600)
    if arms!={"A":4000,"B":4000,"C":2000}: raise SystemExit("arm denominators changed")

    t1=collections.Counter(); t2post=collections.Counter(); t2ev=collections.Counter(); t3post=collections.Counter(); t3ev=collections.Counter(); t3over=collections.Counter(); t4=collections.Counter(); t5=collections.Counter(); t6post=collections.Counter(); t6ev=collections.Counter()
    coord_n=coord_err=0
    for meta,u in expanded:
        arm=meta["arm"]; t1[(arm,"represented_total")]+=1; status=u["status"]; t1[(arm,status)]+=1
        year=(meta.get("cell") or {}).get("created_year"); t4[(year,arm,"represented_total")]+=1
        if status!="complete":
            t4[(year,arm,status)]+=1
            for name in SENSITIVITIES:
                t6post[(arm,name,"processing_error")]+=1
                t6ev[(arm,name,"processing_error")]+=0
            continue
        r=u["result"]; norm=r.get("normalized_text",""); flags={k for k,v in r.get("flags",{}).items() if v is True}; t4[(year,arm,r.get("experience_status","missing"))]+=1
        for e in r.get("evidence",[]):
            coord_n+=1
            if norm[e.get("start"):e.get("end")]!=e.get("quote"): coord_err+=1
        exp=[e for e in r.get("evidence",[]) if e.get("kind")=="experience"]
        if not exp: t2post[(arm,"NO_MATCH","NO_MATCH","NO_MATCH","NO_MATCH","NO_MATCH",None,None)]+=1
        seen=set()
        for e in exp:
            rawobjs=e.get("objects") or []
            objs=["ambiguous_multiobject"] if len(rawobjs)>1 else (rawobjs or ["unresolved"])
            d=e.get("duration") or {}; keybase=(e.get("outcome_status","unknown"),e.get("strength","unknown"),e.get("scope","unknown"),d.get("kind","no_duration"),d.get("lower_years"),d.get("upper_years"))
            for obj in objs:
                key=(arm,obj)+keybase; t2ev[key]+=1; seen.add(key)
        for key in seen: t2post[key]+=1
        tech=[e for e in r.get("evidence",[]) if e.get("kind")=="technology"]
        seen=set()
        for e in tech:
            key=(arm,e.get("technology","unknown"),e.get("role_cue","unknown"),bool(e.get("negated"))); t3ev[key]+=1; seen.add(key)
        for key in seen:t3post[key]+=1
        active=tuple(sorted({e.get("technology") for e in tech if not e.get("negated") and e.get("technology")})) or ("NO_MATCH",)
        t3over[(arm,"+".join(active))]+=1
        relation="general" if "experience_general_work" in flags else ("related" if any("experience_"+x in flags for x in ("occupation_task","industry_domain","tool")) else "NO_MATCH")
        entry=tuple(sorted(x for x in ("explicit_no_experience","graduate_language","entry_junior_text") if x in flags)) or ("NO_MATCH",)
        tasks=tuple(sorted(x[5:] for x in flags if x.startswith("task_"))) or ("NO_MATCH",)
        t5[(arm,relation,"+".join(entry),"+".join(tasks))]+=1
        clean_doc=r.get("experience_status")!="needs_review"; years=[e for e in exp if e.get("duration") is not None]
        sensitivity={"all_years_evidence":years,"exclude_needs_review_clauses":[e for e in years if e.get("outcome_status")=="explicit_rule_candidate"],"unconditional_only":[e for e in years if e.get("outcome_status")=="explicit_rule_candidate" and e.get("scope")=="unconditional_explicit_clause"],"required_only":[e for e in years if e.get("outcome_status")=="explicit_rule_candidate" and e.get("scope")=="unconditional_explicit_clause" and e.get("strength")=="required"],"extreme_exclude_entire_review_document":years if clean_doc else [],"extreme_clean_document_required_only":[e for e in years if clean_doc and e.get("outcome_status")=="explicit_rule_candidate" and e.get("scope")=="unconditional_explicit_clause" and e.get("strength")=="required"]}
        for name,evs in sensitivity.items():
            availability="usable" if evs else "no_usable_evidence"
            t6post[(arm,name,availability)]+=1; t6ev[(arm,name,availability)]+=len(evs)

    if coord_err: raise SystemExit(f"evidence coordinate errors: {coord_err}/{coord_n}")
    tables={
      "T1_EXPANSION_COMPLETENESS.csv":(crows(t1,["arm","status"]),["arm","status","count"]),
      "T2_EXPERIENCE_OBJECT_STRENGTH_SCOPE_YEARS.csv":([dict(zip(["arm","object","clause_status","strength","scope","duration_kind","lower_years","upper_years"],k),posting_count=t2post[k],evidence_count=t2ev[k]) for k in sorted(set(t2post)|set(t2ev),key=str)],["arm","object","clause_status","strength","scope","duration_kind","lower_years","upper_years","posting_count","evidence_count"]),
      "T3_TECH_ROLE_CUES.csv":([dict(zip(["arm","technology","role_cue","negated"],k),posting_count=t3post[k],evidence_count=t3ev[k]) for k in sorted(set(t3post)|set(t3ev),key=str)],["arm","technology","role_cue","negated","posting_count","evidence_count"]),
      "T3_TECH_OVERLAP.csv":(crows(t3over,["arm","technology_combination"]),["arm","technology_combination","count"]),
      "T4_CREATED_YEAR_SNAPSHOT.csv":(crows(t4,["created_year","arm","status"]),["created_year","arm","status","count"]),
      "T5_ENTRY_EXPERIENCE_TASK_COOCCURRENCE.csv":(crows(t5,["arm","experience_relation","entry_text_cues","task_responsibility_cues"]),["arm","experience_relation","entry_text_cues","task_responsibility_cues","count"]),
      "T6_SENSITIVITY_AVAILABILITY.csv":([dict(arm=k[0],sensitivity=k[1],availability=k[2],posting_count=v,evidence_count=t6ev[k]) for k,v in sorted(t6post.items())],["arm","sensitivity","availability","posting_count","evidence_count"]),
    }
    for name,(rs,fs) in tables.items():csvout(out/name,rs,fs)
    outputs=[unique_path,expanded_path]+[out/x for x in tables]
    receipt={"created_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"status":"complete","job_id":os.environ.get("JOB_ID"),"host":socket.gethostname(),"elapsed_seconds":round(time.time()-start,3),"engine_version":rule_engine.VERSION,"engine_sha256":digest(Path(a.engine_dir)/"rule_engine.py"),"legacy_sha256":digest(Path(a.engine_dir)/"legacy_v5_frozen.py"),"synthetic_test_sha256":digest(a.synthetic_test),"input_sha256":{"unique_queue":digest(a.queue),"represented_fixed10000":digest(a.represented)},"unique_rows":len(unique),"represented_rows":len(expanded),"unique_sha_set_matches_represented":True,"represented_positions_ordered_unique_1_to_10000":True,"one_arm_per_exact_sha":True,"unique_status":dict(collections.Counter(x["status"] for x in unique)),"represented_arms":dict(arms),"evidence_coordinate_checks":coord_n,"evidence_coordinate_errors":coord_err,"weight_fields_preserved":list(WEIGHTS),"estimator":"none; public tables are unweighted descriptions of the frozen fixed sample","sensitivity_denominator":"Every sensitivity retains all represented postings by arm; usable means at least one explicit numeric duration clause survives that sensitivity.","boundaries":["A/B/C are legacy sampling arms, not current rule-defined technology roles","C is residual within a technology-prefiltered frame, not ordinary jobs","created_year is snapshot metadata, not historical-text proof","flag omission is not validated absence","multiobject duration clauses remain ambiguous_multiobject and are not assigned to each object","no within-employer claim; canonical metadata is not used as a verified employer key"],"outputs_sha256":{p.name:digest(p) for p in outputs}}
    (out/"FULL_RUN_RECEIPT_PUBLIC.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")

if __name__=="__main__":main()
