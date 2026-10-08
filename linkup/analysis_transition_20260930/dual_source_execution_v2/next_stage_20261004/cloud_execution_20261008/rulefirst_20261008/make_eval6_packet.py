#!/usr/bin/env python3
"""Select fixed first two evaluation rows per arm, independent of results."""
import argparse, hashlib, json, os
from pathlib import Path
def load(path):
    with open(path,encoding="utf-8") as f:return [json.loads(x) for x in f if x.strip()]
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--source",required=True); ap.add_argument("--results",required=True); ap.add_argument("--output",required=True); a=ap.parse_args()
    src=load(a.source); res=load(a.results)
    if len(src)!=80 or len(res)!=80: raise SystemExit("evaluation inputs/results must each have 80 rows")
    bysha={x.get("exact_text_sha256"):x for x in res}
    if len(bysha)!=80: raise SystemExit("evaluation result SHA not unique")
    chosen=[]
    for arm in "ABC":
        rows=[x for x in src if x.get("arm")==arm][:2]
        if len(rows)!=2: raise SystemExit("insufficient fixed rows in arm")
        for s in rows:
            sha=s["exact_text_sha256"]
            if hashlib.sha256(s["original_text"].encode()).hexdigest()!=sha: raise SystemExit("source SHA mismatch")
            r=bysha.get(sha)
            if not r or r.get("status")!="complete": raise SystemExit("selected evaluation result incomplete")
            chosen.append({"selection_rule":"first_two_by_frozen_eval_selection_order_within_arm_not_result_selected","selection_index_1based":s.get("selection_index_1based"),"arm":arm,"exact_text_sha256":sha,"source_length_characters":len(s["original_text"]),"original_text":s["original_text"],"all_rule_evidence":r["result"].get("evidence",[]),"flags":r["result"].get("flags",{}),"review_reasons":r["result"].get("review_reasons",[])})
    p=Path(a.output)
    with open(p,"w",encoding="utf-8") as f:
        for x in chosen:f.write(json.dumps(x,ensure_ascii=False,separators=(",",":"))+"\n")
    os.chmod(p,0o600)
if __name__=="__main__":main()
