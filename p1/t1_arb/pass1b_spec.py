#!/usr/bin/env python3
"""BOX-ONLY. Build the deepseek extraction spec for Pass 1b: recover the
COMPLETED effective_date from each undated conversion's SUBSEQUENT filings
(485BPOS/497/N-CEN/N-8F, harvested by pass1b_harvest.py into
p1/edgar_filings_1b/ + pass1b_candidates.json).

One item per conversion, keyed by the conversion's representative accession (so
merge_pass1b.py folds the recovered date straight onto the conversion). The
prompt anchors HARD on the target fund name/family because a 485BPOS or N-CEN
covers a whole trust — the model must return the date for OUR fund only, else NA.

Run:  python p1/t1_arb/pass1b_spec.py
Then: python ops/l1/run_mopup.py P1-T1-pass1b --live
Then: python p1/t1_arb/merge_pass1b.py
"""
import html
import io
import json
import os
import re
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
CAND = ROOT / "p1" / "t1_arb" / "pass1b_candidates.json"
OUT = ROOT / "ops" / "l1" / "P1-T1-pass1b.yaml"

TAG = re.compile(r"<[^>]+>")
# completion / effective-date language + explicit month-day-year dates. Adds the
# retrospective "successor to X ... reorganization on <date>" cue that dominates
# post-close 485BPOS/N-CEN filings.
DATE_CUES = re.compile(
    r"(on or about|close of business|effective date|closing date|the closing|"
    r"completed on|was completed|occurred on|took place on|consummated on|"
    r"as the successor to|successor fund|reorganization (?:was |occurred |closed )|"
    r"reorganization on|acquired the assets|as a result of (?:a |the )?reorganization|"
    r"commenced operations on|[A-Z][a-z]+ \d{1,2},? \d{4})", re.I)
W = 350
MAX_WIN = 10
CAP_PER_ITEM = 11000

RULES = """【任务: 从"后续备案"中回收共同基金→ETF转换的实际生效/完成日。
给你的是该转换发生之后提交的备案节选(485BPOS/497/N-CEN/N-8F等), 这些备案常以
回溯语气陈述完成日, 例如 "the Fund is the successor to the X Fund as a result of a
reorganization completed on <date>"。
关键: 一个备案(尤其 485BPOS/N-CEN)可能覆盖同一信托下的多只基金及多个日期。
你必须只返回"目标基金"这一次转换的完成/生效日; 若节选中的日期属于其它基金、或无法
确认属于目标基金 → 输出 NA。
规则: (1) 输出实际完成/生效日 YYYY-MM-DD; (2) 只有月份或季度→ NA; 含糊→ NA;
(3) 多个候选日期时取明确归属目标基金的那个; (4) 不得凭记忆补充, 抽不到→ NA。
输出一个 JSON 对象: {"effective_date":"YYYY-MM-DD"|"NA","date_basis":"retrospective|closing|expected|NA",
"evidence":"≤25词原文引用(须含目标基金名或代码)"}。】"""

SENTINELS = """sentinels:
  - id: S1
    prompt: "Filing excerpt: 'The Fund is the successor to the Ridgeline Mid-Cap Growth Fund as a result of a reorganization completed on April 22, 2022.' On what date was the reorganization completed? Reply with YYYY-MM-DD only."
    expect: "2022-04-22"
  - id: S2
    prompt: "Filing excerpt: 'The Acme Value ETF commenced operations on March 3, 2023, as successor to the Acme Value Fund.' On what date did the ETF commence operations? Reply with YYYY-MM-DD only."
    expect: "2023-03-03"
  - id: S3
    prompt: "Filing excerpt: 'Effective as of the close of business on January 20, 2023, the reorganization of the Beacon Equity Fund into the Beacon Equity ETF was consummated.' On what date was it consummated? Reply with YYYY-MM-DD only."
    expect: "2023-01-20"
"""


def date_windows(text):
    spans = []
    for m in DATE_CUES.finditer(text):
        lo, hi = max(0, m.start() - W), m.start() + W
        if spans and lo <= spans[-1][1]:
            spans[-1] = (spans[-1][0], hi)
        else:
            spans.append((lo, hi))
        if len(spans) >= MAX_WIN:
            break
    return " […] ".join(text[lo:hi] for lo, hi in spans)


def main():
    data = json.loads(CAND.read_text())["conversions"]
    items, no_ctx, pending = [], [], []
    for rep, c in data.items():
        if c["pending_flag"] or not c["cands"]:
            pending.append(rep)
            continue
        ctx, used = [], []
        for cd in sorted(c["cands"], key=lambda x: x["filed"]):
            p = pathlib.Path(cd["path"])
            if not p.exists():
                continue
            raw = io.open(p, "r", encoding="utf-8", errors="ignore").read()
            txt = re.sub(r"\s+", " ", html.unescape(TAG.sub(" ", raw))).strip()
            w = date_windows(txt)
            if w:
                ctx.append(f"[后续备案 {cd['accession']} form {cd['form']} filed {cd['filed']}]: {w}")
                used.append(cd["accession"])
            if sum(len(x) for x in ctx) > CAP_PER_ITEM:
                break
        if not ctx:
            no_ctx.append(rep)
            continue
        fund = c["fund"] if c["fund"] not in ("NA", "", None) else "(未具名, 见 family)"
        prompt = (RULES + f"\n目标基金: {fund} ({c['family']})。原公告日: {c['announce']}。\n"
                  + "后续备案日期上下文:\n" + ("\n".join(ctx))[:CAP_PER_ITEM])
        items.append({"id": rep, "_fund": c["fund"], "_accessions": used, "prompt": prompt})

    body = ["# P1-T1-pass1b — subsequent-filing effective-date recovery (Pass 1b)",
            "# BUILT ON BOX by p1/t1_arb/pass1b_spec.py from p1/edgar_filings_1b/.",
            "# Channel A family (deepseek); date-only extraction, no verdicts.",
            "worker: deepseek", "web_search: false", "max_items_per_call: 6",
            f"est_cost: {round(len(items)*0.12,2)}", "items:"]
    for it in items:
        body.append(f'  - id: "{it["id"]}"')
        body.append(f'    _fund: {json.dumps(it["_fund"], ensure_ascii=False)}')
        body.append(f'    _accessions: {json.dumps(it["_accessions"])}')
        body.append("    prompt: |")
        for line in it["prompt"].splitlines():
            body.append("      " + line)
    body.append(SENTINELS)
    OUT.write_text("\n".join(body) + "\n")
    print(f"wrote {OUT}: {len(items)} conversions with subsequent date-context | "
          f"{len(no_ctx)} had candidates but no date cue | {len(pending)} pending/no-subsequent")


if __name__ == "__main__":
    main()
