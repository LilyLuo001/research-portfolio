#!/usr/bin/env python3
"""Mechanical context-pack and request-budget builder; makes no model calls."""
import argparse, collections, csv, datetime as dt, hashlib, json, os, re
from pathlib import Path

BROAD=re.compile(r"\b(?:experience|experienced|years?|months?|proficien(?:cy|t)|qualifications?|in lieu of|substitut(?:e|ion)|equivalent|alternative|bachelor(?:'s)?|master(?:'s)?|degree|diploma|GED|high school)\b",re.I)
ALT=re.compile(r"\b(?:or|in lieu of|substitut(?:e|ion)|equivalent|alternative)\b",re.I)
DEGREE=re.compile(r"\b(?:bachelor(?:'s)?|master(?:'s)?|degree|diploma|GED|high school)\b",re.I)
YEAR=re.compile(r"\b(?:\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty)\s*(?:\+\s*)?(?:years?|months?)\b",re.I)
EVIDENCE_KINDS={"experience","entry","knowledge"}
CATEGORIES=("experience_scope","technology_role","task_responsibility")

def rows(path):
    with open(path,encoding="utf-8") as f:
        for line in f:
            if line.strip():yield json.loads(line)
def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()
def merge(spans):
    out=[]
    for a,b in sorted(spans):
        if out and a<=out[-1][1]:out[-1][1]=max(out[-1][1],b)
        else:out.append([a,b])
    return out
def line_records(text,legacy):
    rec=[];section="unknown";start=0
    for line in text.split("\n"):
        heading=legacy._heading_context(line)
        if heading:section=heading
        rec.append((line,start,start+len(line),section,heading));start+=len(line)+1
    return rec
def request_bytes(prompt,schema,text):
    return len(json.dumps({"instructions":prompt,"schema":schema,"input_text":text},ensure_ascii=False,separators=(",",":")).encode())
def serialize_windows(text,spans,anchors):
    parts=[]
    for s,e in spans:
        heads=[]
        for a in anchors:
            h=a.get("nearest_heading")
            if a["start"]<e and a["end"]>s and h and not(s<=h["start"] and h["end"]<=e):
                key=(h["start"],h["end"],h["text"])
                if key not in heads:heads.append(key)
        prefix="".join("[NEAREST_HEADING %s:%s]\n%s\n"%(x,y,z) for x,y,z in heads)
        parts.append("[CONTEXT %s:%s]\n%s%s"%(s,e,prefix,text[s:e]))
    return "\n\n[CONTEXT_WINDOW_BREAK]\n\n".join(parts)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--queue",required=True);ap.add_argument("--represented",required=True);ap.add_argument("--full-results",required=True);ap.add_argument("--engine-dir",required=True);ap.add_argument("--output-dir",required=True);ap.add_argument("--budget-contract",required=True);ap.add_argument("--pricing",required=True);ap.add_argument("--variable-contract",required=True)
    a=ap.parse_args(); import sys;sys.path.insert(0,a.engine_dir);import legacy_v5_frozen as legacy
    queue=list(rows(a.queue));represented=list(rows(a.represented));results=list(rows(a.full_results))
    if len(queue)!=7635 or len(represented)!=10000 or len(results)!=7635:raise SystemExit("frozen counts changed")
    qby={x["exact_text_sha256"]:x for x in queue};rby={x["exact_text_sha256"]:x for x in results}
    if len(qby)!=len(queue) or len(rby)!=len(results):raise SystemExit("duplicate SHA in queue or results")
    if set(qby)!=set(rby) or {x["exact_text_sha256"] for x in represented}!=set(qby):raise SystemExit("source/result/represented SHA sets differ")
    positions=[x.get("fixed_sample_position_1based") for x in represented]
    if positions!=list(range(1,10001)) or len(set(positions))!=10000:raise SystemExit("represented positions are not ordered unique 1..10000")
    arms=collections.defaultdict(set)
    for x in represented:arms[x["exact_text_sha256"]].add(x["arm"])
    if any(len(v)!=1 for v in arms.values()):raise SystemExit("SHA spans arms")
    out=Path(a.output_dir);out.mkdir(parents=True,exist_ok=True); pack=[]; counts=collections.Counter();scope_counts=collections.Counter()
    for q in queue:
        h=q["exact_text_sha256"];u=rby[h];res=u.get("result",{});text=res.get("normalized_text","");lines=line_records(text,legacy)
        anchors=[]
        for e in res.get("evidence",[]):
            kind=e.get("kind")
            if kind in EVIDENCE_KINDS:anchors.append({"source":"frozen_evidence","kind":kind,"start":e.get("start"),"end":e.get("end"),"section":e.get("section")})
        for m in BROAD.finditer(text):anchors.append({"source":"broad_retrieval","kind":"lexical_anchor","start":m.start(),"end":m.end(),"term":m.group(0)})
        anchors.sort(key=lambda x:(x["start"],x["end"],x["source"]));ded=[];seen=set()
        for x in anchors:
            k=(x["start"],x["end"],x["source"],x["kind"])
            if k not in seen:seen.add(k);ded.append(x)
        anchors=ded; spans=[]
        for x in anchors:
            lo=max(0,x["start"]-1200);hi=min(len(text),x["end"]+1200)
            involved=[i for i,z in enumerate(lines) if not(z[2]<lo or z[1]>hi)]
            if involved:lo=lines[max(0,min(involved)-1)][1];hi=lines[min(len(lines)-1,max(involved)+1)][2]
            heading=None
            for line,s,e,section,ishead in reversed([z for z in lines if z[1]<=x["start"]]):
                if ishead:heading={"text":line,"start":s,"end":e,"section":ishead};break
            x["nearest_heading"]=heading;x["window_start"]=lo;x["window_end"]=hi;spans.append((lo,hi))
        spans=merge(spans);covered=sum(b-a for a,b in spans);coverage=(covered/len(text)) if text else 0
        longline=any(len(z[0])>1500 for z in lines)
        multiline_alt=any(DEGREE.search(" ".join(z[0] for z in lines[i:i+4])) and YEAR.search(" ".join(z[0] for z in lines[i:i+4])) and ALT.search(" ".join(z[0] for z in lines[i:i+4])) for i in range(len(lines)))
        reasons=[]
        if longline:reasons.append("line_over_1500_characters")
        if multiline_alt:reasons.append("multiline_education_experience_alternative_risk")
        if coverage>0.70:reasons.append("merged_window_coverage_over_70_percent")
        fallback=bool(reasons);noanchor=not anchors
        windows=[{"start":s,"end":e,"text":text[s:e]} for s,e in spans]
        context=("[FULL_TEXT_FALLBACK 0:%s]\n%s"%(len(text),text)) if fallback else serialize_windows(text,spans,anchors)
        arm=next(iter(arms[h])); ev=res.get("evidence",[]); tech=[x for x in ev if x.get("kind")=="technology"];tasks=[x for x in ev if x.get("kind")=="task"]
        exp=[x for x in ev if x.get("kind")=="experience"]
        counts[(arm,"experience_scope","unique_texts")]+=1;counts[(arm,"experience_scope","texts_needing_context")]+=int(bool(anchors));counts[(arm,"experience_scope","anchors")]+=len(anchors);counts[(arm,"experience_scope","evidence_clause_anchors")]+=sum(x["source"]=="frozen_evidence" for x in anchors);counts[(arm,"experience_scope","no_anchor_unknown")]+=int(noanchor);counts[(arm,"experience_scope","full_fallback")]+=int(fallback);counts[(arm,"experience_scope","context_characters")]+=len(context);counts[(arm,"experience_scope","context_utf8_bytes")]+=len(context.encode());counts[(arm,"experience_scope","source_characters")]+=len(text);counts[(arm,"experience_scope","source_utf8_bytes")]+=len(text.encode())
        for reason in reasons:counts[(arm,"experience_scope","fallback_"+reason)]+=1
        for cat,clauses in (("technology_role",tech),("task_responsibility",tasks)):
            counts[(arm,cat,"unique_texts")]+=1;counts[(arm,cat,"texts_needing_context")]+=1;counts[(arm,cat,"evidence_clause_anchors")]+=len(clauses);counts[(arm,cat,"source_characters")]+=len(text);counts[(arm,cat,"source_utf8_bytes")]+=len(text.encode())
        groups=collections.Counter()
        for e in exp:
            objs=e.get("objects") or []
            obj="ambiguous_multiobject" if len(objs)>1 else (objs[0] if objs else "unresolved")
            groups[("experience_scope","object:"+obj)]+=1;groups[("experience_scope","strength:"+str(e.get("strength","unknown")))]+=1;groups[("experience_scope","scope:"+str(e.get("scope","unknown")))]+=1
        for e in tech:
            groups[("technology_role","technology:"+str(e.get("technology","unknown")))]+=1;groups[("technology_role","role_cue:"+str(e.get("role_cue","unknown")))]+=1
        for e in tasks:groups[("task_responsibility","task_family:"+str(e.get("task_family","unknown")))]+=1
        groups[("technology_role","all_full_joint")]+=0;groups[("task_responsibility","all_full_joint")]+=0
        for (cat,group),clause_n in groups.items():
            scope_counts[(arm,cat,group,"unique_texts")]+=1;scope_counts[(arm,cat,group,"clauses")]+=clause_n
            scope_counts[(arm,cat,group,"deduplicated_context_characters")]+=len(context) if cat=="experience_scope" else len(text)
            scope_counts[(arm,cat,group,"full_text_characters")]+=len(text)
        pack.append({"context_pack_position_1based":len(pack)+1,"exact_text_sha256":h,"arm":arm,"queue_position_1based":q.get("queue_position_1based"),"raw_source_reference":{"path":"imported/production_standard_20261008/private/full_queue/UNIQUE_EXACT_TEXT_QUEUE_PRIVATE.jsonl","queue_position_1based":q.get("queue_position_1based")},"normalized_full_reference":{"path":"run/full/FULL7635_RULE_OUTPUTS_PRIVATE.jsonl","queue_position_1based":q.get("queue_position_1based"),"field":"result.normalized_text","base_offset":0,"declared_full":True},"normalized_text_sha256":res.get("normalized_text_sha256"),"anchors":anchors,"windows":windows,"no_anchor_unknown":noanchor,"full_text_fallback":fallback,"fallback_reasons":reasons,"source_characters":len(text),"source_utf8_bytes":len(text.encode()),"context_characters":len(context),"context_utf8_bytes":len(context.encode()),"merged_window_coverage":coverage,"context_text":context,"reliability_boundary":"Experience, qualification, technology-role, and task-responsibility scope remain unresolved until adjudicated; false/no-hit is not a pass."})
    packp=out/"CONTEXT_PACK_7635_PRIVATE.jsonl"
    with open(packp,"w",encoding="utf-8") as f:
        for x in pack:f.write(json.dumps(x,ensure_ascii=False,separators=(",",":"))+"\n")
    os.chmod(packp,0o600);pos={x["exact_text_sha256"]:x["context_pack_position_1based"] for x in pack}
    bind=out/"CONTEXT_TO_FIXED10000_BINDING_PRIVATE.jsonl"
    with open(bind,"w",encoding="utf-8") as f:
        for x in represented:f.write(json.dumps({"fixed_sample_position_1based":x["fixed_sample_position_1based"],"exact_text_sha256":x["exact_text_sha256"],"arm":x["arm"],"context_pack_position_1based":pos[x["exact_text_sha256"]],"canonical_key":x.get("canonical_key"),"cell":x.get("cell"),"weights":x.get("weights")},ensure_ascii=False,separators=(",",":"))+"\n")
    os.chmod(bind,0o600)
    cp=out/"CONTEXT_COUNTS_BY_ARM_PUBLIC.csv"
    with open(cp,"w",newline="") as f:
        w=csv.writer(f);w.writerow(["arm","category","metric","count"])
        for arm in "ABC":
            for cat in CATEGORIES:
                for m in sorted({k[2] for k in counts}):w.writerow([arm,cat,m,counts[(arm,cat,m)]])
    sp=out/"SCOPE_COUNTS_BY_ARM_PUBLIC.csv"
    with open(sp,"w",newline="") as f:
        w=csv.writer(f);w.writerow(["arm","category","scope_group","metric","count"])
        for k,v in sorted(scope_counts.items()):w.writerow([*k,v])
    # Budget behavior is root-authored in JSON: each scenario names prompt/schema,
    # text_source=context|full, and selector=all|anchored|full_fallback.
    contract=json.loads(Path(a.budget_contract).read_text());pricing=json.loads(Path(a.pricing).read_text());variables=json.loads(Path(a.variable_contract).read_text());budget=[]; contract_hashes={}
    for name,spec in contract["scenarios"].items():
        prompt=Path(spec["prompt_path"]).read_text();schema=json.loads(Path(spec["schema_path"]).read_text()); selected=[]
        contract_hashes[spec["prompt_path"]]=sha(spec["prompt_path"]);contract_hashes[spec["schema_path"]]=sha(spec["schema_path"])
        for x in pack:
            if spec["selector"]=="anchored" and x["no_anchor_unknown"]:continue
            if spec["selector"]=="full_fallback" and not x["full_text_fallback"]:continue
            if spec["text_source"]=="full":
                normalized=rby[x["exact_text_sha256"]]["result"]["normalized_text"]
                text="[FULL_TEXT base_offset=0 declared_full=true]\n"+normalized
            else:text=x["context_text"]
            selected.append(request_bytes(prompt,schema,text))
        for divisor in (5,4,3):
            approx=sum((b+divisor-1)//divisor for b in selected)
            for reasoning in contract["output_caps"]:
                outtokens=reasoning*len(selected)
                for service,rates in pricing["services"].items():budget.append({"scenario":name,"model":variables["future_recommended_model"],"reasoning_effort":variables["future_initial_effort"],"selector":spec["selector"],"text_source":spec["text_source"],"service":service,"bytes_per_token_planning_divisor":divisor,"output_cap_per_request":reasoning,"request_count":len(selected),"serialized_utf8_bytes":sum(selected),"max_request_serialized_utf8_bytes":max(selected) if selected else 0,"approx_input_tokens":approx,"max_request_approx_input_tokens":max(((b+divisor-1)//divisor for b in selected),default=0),"potential_long_context_request_count":sum((b+2)//3>272000 for b in selected),"reasoning_output_tokens_budget":outtokens,"estimated_usd":approx*rates["input_usd_per_million"]/1e6+outtokens*rates["output_usd_per_million"]/1e6})
    # Scenario C is deliberately additive accounting, not a third request.
    bykey={(x["scenario"],x["service"],x["bytes_per_token_planning_divisor"],x["reasoning_output_tokens_budget"]//max(1,x["request_count"])):x for x in budget}
    for service in pricing["services"]:
        for divisor in (5,4,3):
            for cap in contract["output_caps"]:
                left=bykey[("A_experience_context",service,divisor,cap)];right=bykey[("B_full_joint",service,divisor,cap)]
                budget.append({"scenario":"C_additive_A_plus_B_diagnostic","model":variables["future_recommended_model"],"reasoning_effort":variables["future_initial_effort"],"selector":"additive_not_new_requests","text_source":"A_context_plus_B_full","service":service,"bytes_per_token_planning_divisor":divisor,"output_cap_per_request":cap,"request_count":left["request_count"]+right["request_count"],"serialized_utf8_bytes":left["serialized_utf8_bytes"]+right["serialized_utf8_bytes"],"max_request_serialized_utf8_bytes":max(left["max_request_serialized_utf8_bytes"],right["max_request_serialized_utf8_bytes"]),"approx_input_tokens":left["approx_input_tokens"]+right["approx_input_tokens"],"max_request_approx_input_tokens":max(left["max_request_approx_input_tokens"],right["max_request_approx_input_tokens"]),"potential_long_context_request_count":left["potential_long_context_request_count"]+right["potential_long_context_request_count"],"reasoning_output_tokens_budget":left["reasoning_output_tokens_budget"]+right["reasoning_output_tokens_budget"],"estimated_usd":left["estimated_usd"]+right["estimated_usd"]})
    bp=out/"BUDGET_SCENARIOS_PUBLIC.csv"
    with open(bp,"w",newline="") as f:
        fields=list(budget[0]);w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(budget)
    nonadd=[x for x in budget if not x["scenario"].startswith("C_")]
    receipt={"created_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"status":"complete_no_model_calls","job_id":os.environ.get("JOB_ID"),"model":variables["future_recommended_model"],"reasoning_effort":variables["future_initial_effort"],"rows":{"unique_context_pack":len(pack),"represented_binding":len(represented)},"integrity":{"represented_positions_ordered_unique_1_to_10000":True,"unique_sha_sets_aligned":True},"request_size_summary":{"max_request_serialized_utf8_bytes":max(x["max_request_serialized_utf8_bytes"] for x in nonadd),"potential_long_context_request_count_by_scenario":{name:max(x["potential_long_context_request_count"] for x in nonadd if x["scenario"]==name) for name in contract["scenarios"]}},"input_sha256":{"queue":sha(a.queue),"represented":sha(a.represented),"full_v1_2_results":sha(a.full_results),"budget_contract":sha(a.budget_contract),"pricing":sha(a.pricing),"variable_contract":sha(a.variable_contract),"builder":sha(__file__),"legacy_v5":sha(legacy.__file__)},"prompt_schema_sha256":contract_hashes,"outputs_sha256":{p.name:sha(p) for p in (packp,bind,cp,sp,bp)},"token_boundary":"UTF-8 bytes divided by 5, 4, or 3 is planning approximation, not tokenizer measurement or guaranteed bounds. Serialized prompt, schema, and input text are included; no cache discount assumed.","semantic_boundary":"Pack construction does not adjudicate experience relationships, qualification scope, technology role, or task responsibility. No-hit is unknown, not false/pass."}
    (out/"CONTEXT_HANDOFF_RECEIPT_PUBLIC.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
if __name__=="__main__":main()
