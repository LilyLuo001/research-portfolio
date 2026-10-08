#!/usr/bin/env python3
"""Mechanical parallel runner for the frozen root-authored rule engine."""
import argparse, collections, csv, datetime as dt, hashlib, importlib, json, os, re, socket, subprocess, sys, time
from multiprocessing import Pool
from pathlib import Path


def jsonl(path):
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if line.strip():
                yield n, json.loads(line)


def worker(item):
    i, row = item
    import rule_engine
    text, claimed = row.get("original_text"), row.get("exact_text_sha256")
    actual = hashlib.sha256(text.encode("utf-8")).hexdigest() if isinstance(text, str) else None
    if actual != claimed:
        return {"input_index_1based": i, "exact_text_sha256": claimed, "arm": row.get("arm"),
                "status": "source_hash_error", "error": "source SHA mismatch"}
    try:
        result = rule_engine.extract(text)
        if result.get("source_text_sha256") != claimed:
            raise RuntimeError("engine returned a different source SHA")
        return {"input_index_1based": i, "exact_text_sha256": claimed, "arm": row.get("arm"),
                "queue_position_1based": row.get("queue_position_1based"), "status": "complete",
                "result": result}
    except Exception as exc:
        return {"input_index_1based": i, "exact_text_sha256": claimed, "arm": row.get("arm"),
                "status": "engine_error", "error_type": type(exc).__name__, "error": str(exc)[:500]}


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)


def bounded_quote(value, limit=200):
    value = value if isinstance(value, str) else ""
    return {"quote": value[:limit], "quote_truncated": len(value) > limit}


def main():
    started = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--expected", type=int, required=True)
    ap.add_argument("--engine-dir", required=True)
    ap.add_argument("--synthetic-test", required=True,
                    help="Root-provided public synthetic test program; must exit zero before private processing")
    args = ap.parse_args()
    sys.path.insert(0, args.engine_dir)
    os.environ["PYTHONPATH"] = args.engine_dir + os.pathsep + os.environ.get("PYTHONPATH", "")
    if not Path(args.synthetic_test).is_file():
        raise SystemExit("required root-reviewed synthetic test is absent")
    # Run the reviewed unittest program in a clean argv context before data access.
    subprocess.run([sys.executable, args.synthetic_test], check=True, env=os.environ.copy())
    engine = importlib.import_module("rule_engine")

    records = list(jsonl(args.input))
    if len(records) != args.expected:
        raise SystemExit(f"expected {args.expected} rows, found {len(records)}")
    shas = [r.get("exact_text_sha256") for _, r in records]
    if len(set(shas)) != len(shas):
        raise SystemExit("input contains duplicate exact-text SHA")
    if args.expected == 120 and collections.Counter(r.get("arm") for _, r in records) != {"A":40,"B":40,"C":40}:
        raise SystemExit("development-120 arm allocation differs from 40/40/40")

    outdir = Path(args.output_dir); outdir.mkdir(parents=True, exist_ok=True)
    with Pool(processes=args.workers) as pool:
        outputs = list(pool.imap(worker, records, chunksize=4))
    private = outdir / "RULE_OUTPUTS_PRIVATE.jsonl"
    with open(private, "w", encoding="utf-8") as f:
        for row in outputs: f.write(json.dumps(row, ensure_ascii=False, sort_keys=True)+"\n")
    os.chmod(private, 0o600)

    funnel, flags, exp, cooccur, reasons = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
    diagnostic_year_skill=collections.Counter(); compact_all=[]; coordinate_checks=0; coordinate_errors=0
    for row in outputs:
        arm=row.get("arm") or "UNKNOWN"; funnel[(arm,"all_input")]+=1
        if row["status"] != "complete":
            funnel[(arm,row["status"])]+=1
            compact_all.append({"exact_text_sha256":row.get("exact_text_sha256"),"arm":arm,"status":row["status"],"issues":[row.get("error_type","processing_error")],"review_priority":1000})
            continue
        result=row["result"]; funnel[(arm,"processed")]+=1
        normalized=result.get("normalized_text","")
        for evidence in result.get("evidence",[]):
            coordinate_checks += 1
            start,end=evidence.get("start"),evidence.get("end")
            if not isinstance(start,int) or not isinstance(end,int) or normalized[start:end] != evidence.get("quote"):
                coordinate_errors += 1
        funnel[(arm,result.get("experience_status","missing_status"))]+=1
        fset={k for k,v in result.get("flags",{}).items() if v is True}
        if not fset: funnel[(arm,"no_true_flags")]+=1
        for flag in fset: flags[(arm,flag)]+=1
        tech=sorted(x for x in fset if x.startswith("tech_")); task=sorted(x for x in fset if x.startswith("task_"))
        for t in task:
            for h in tech: cooccur[(arm,t,h)]+=1
        for reason in result.get("review_reasons",[]): reasons[(arm,reason)]+=1
        clauses=[x for x in result.get("evidence",[]) if x.get("kind")=="experience"]
        task_clauses=[x for x in result.get("evidence",[]) if x.get("kind")=="task"]
        if not clauses: exp[(arm,"NO_MATCH","NO_MATCH","NO_MATCH","NO_MATCH")]+=1
        for e in clauses:
            objs=e.get("objects") or ["unresolved"]
            dur=(e.get("duration") or {}).get("kind","no_duration")
            for obj in objs: exp[(arm,obj,e.get("strength","unknown"),e.get("scope","unknown"),dur)]+=1
        year_skill_candidate = (not clauses and bool(engine.YEARS.search(normalized)) and
                                bool(re.search(r'\b(?:proficien(?:cy|t)|ability|capabilit(?:y|ies))\b', normalized, re.I)))
        if year_skill_candidate: diagnostic_year_skill[arm]+=1
        compact_all.append({
          "exact_text_sha256":row["exact_text_sha256"], "arm":arm, "status":"complete",
          "flags":sorted(fset), "issues":result.get("review_reasons",[]),
          "experience_evidence":[dict({
             "objects":e.get("objects",[]), "strength":e.get("strength"), "scope":e.get("scope"),
             "duration":e.get("duration")}, **bounded_quote(e.get("quote"))) for e in clauses[:3]],
          "experience_evidence_omitted_count":max(0,len(clauses)-3),
          "task_evidence":[dict({"task_family":e.get("task_family")}, **bounded_quote(e.get("quote"))) for e in task_clauses[:3]],
          "task_evidence_omitted_count":max(0,len(task_clauses)-3),
          "diagnostic_year_plus_proficiency_or_ability_without_experience_evidence":year_skill_candidate,
          "review_priority":100*len(result.get("review_reasons",[]))+10*len(clauses)+5*len(task_clauses)+int(year_skill_candidate)+len(fset),
        })

    # Compact root-review view: at most 80, stratified 27/27/26 across frozen
    # sampling arms and prioritized by issue/evidence density. Full 120 outputs
    # remain in RULE_OUTPUTS_PRIVATE.jsonl.
    quotas={"A":27,"B":27,"C":26}; compact=[]
    for arm in "ABC":
        arm_rows=[x for x in compact_all if x.get("arm")==arm]
        compact.extend(sorted(arm_rows,key=lambda x:(-x.get("review_priority",0),x.get("exact_text_sha256") or ""))[:quotas[arm]])
    for x in compact: x.pop("review_priority",None)
    compact_path=outdir/("DEV120_COMPACT_DIAGNOSTIC_PRIVATE.jsonl" if args.expected==120 else "EVAL80_COMPACT_DIAGNOSTIC_PRIVATE.jsonl")
    with open(compact_path,"w",encoding="utf-8") as f:
        for row in compact: f.write(json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\n")
    os.chmod(compact_path,0o600)

    def counter_rows(c, names): return [dict(zip(names,k if isinstance(k,tuple) else (k,)),count=v) for k,v in sorted(c.items())]
    tables={
      "coverage_funnel.csv":(counter_rows(funnel,["arm","stage"]),["arm","stage","count"]),
      "flag_counts_by_arm.csv":(counter_rows(flags,["arm","flag"]),["arm","flag","count"]),
      "experience_evidence.csv":(counter_rows(exp,["arm","object","strength","scope","duration_kind"]),["arm","object","strength","scope","duration_kind","count"]),
      "task_technology_cooccurrence.csv":(counter_rows(cooccur,["arm","task_flag","technology_flag"]),["arm","task_flag","technology_flag","count"]),
      "review_reasons.csv":(counter_rows(reasons,["arm","reason"]),["arm","reason","count"]),
      "diagnostic_year_skill_candidates.csv":(counter_rows(diagnostic_year_skill,["arm"]),["arm","count"]),
    }
    for name,(data,fields) in tables.items(): write_csv(outdir/name,data,fields)
    def h(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    receipt={
      "created_utc":dt.datetime.now(dt.timezone.utc).isoformat(), "status":"complete",
      "engine_version":engine.VERSION, "input_rows":len(records), "unique_source_hashes":len(set(shas)),
      "workers":args.workers, "completed":sum(x["status"]=="complete" for x in outputs),
      "errors":sum(x["status"]!="complete" for x in outputs),
      "job_id":os.environ.get("JOB_ID"), "host":socket.gethostname(), "elapsed_seconds":round(time.time()-started,3),
      "engine_sha256":h(Path(args.engine_dir)/"rule_engine.py"),
      "legacy_sha256":h(Path(args.engine_dir)/"legacy_v5_frozen.py"),
      "synthetic_test_sha256":h(args.synthetic_test),
      "evidence_coordinate_checks":coordinate_checks, "evidence_coordinate_errors":coordinate_errors,
      "compact_review_rows":len(compact), "compact_review_by_arm":dict(collections.Counter(x.get("arm") for x in compact)),
      "interpretation_boundary":"Counts are deterministic rule observations. Flag false/omission is not validated absence. No weighted population estimate is reported because this runner has no separately documented estimator contract.",
      "year_cohort_boundary":"Any later created_year table is descriptive posting-time composition, not proof of historical text or technology adoption.",
      "diagnostic_year_plus_proficiency_or_ability_without_experience_evidence":dict(sorted(diagnostic_year_skill.items())),
      "diagnostic_boundary":"The year-plus-proficiency/ability count is an omission-review candidate only, not a classified experience requirement; year coverage is not claimed complete.",
      "outputs_sha256":{p.name:h(p) for p in [private,compact_path]+[outdir/x for x in tables]},
    }
    (outdir/"RUN_RECEIPT_PUBLIC.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")

if __name__ == "__main__": main()
