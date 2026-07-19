#!/usr/bin/env python3
"""BOX-ONLY. Build the deepseek TARGET-TYPE confirmation spec for the recheck
queue (rows the owner quarantined because 'the acquirer is an ETF' alone did not
prove the TARGET was an open-end/mutual fund). Reads raw p1/edgar_filings via
manifest.csv, cuts windows around target-identity language, emits
ops/l1/P1-T1-recheck.yaml.

Run:  python p1/t1_arb/build_recheck_spec.py
Then: python ops/l1/run_mopup.py P1-T1-recheck --live
Then: python p1/t1_arb/merge_recheck.py
"""
import csv
import html
import io
import json
import re
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
QUEUE = ROOT / "p1" / "t1_arb" / "recheck_queue.json"
PKG = ROOT / "p1" / "edgar_filings"
MANIFEST = PKG / "manifest.csv"
OUT = ROOT / "ops" / "l1" / "P1-T1-recheck.yaml"

TAG = re.compile(r"<[^>]+>")
CUES = re.compile(
    r"(open-end|mutual fund|currently operates as|is a series of|the Target Fund|"
    r"the Acquired Fund|Predecessor (?:Mutual )?Fund|closed-end|exchange-traded fund|"
    r"an ETF|Acquiring Fund|reorganiz|convert|ticker|Class [A-Z]\b|shares of beneficial interest)", re.I)
W, MAXW, CAP = 350, 10, 9000

RULES = """【任务: 判定"目标基金"结构类型 (仅此一件事)。给定某基金的相关备案节选。
问题: 该转换的 TARGET/被并入/被转换的基金, 在转换前是不是"开放式/共同基金"(open-end
mutual fund)? 判据必须来自节选原文, 不得凭记忆。
规则: (a) 若原文明示 target 是 open-end / mutual fund / has Class A/C/I shares /
"currently operates as a mutual fund" → is_open_end_mutual_fund="yes";
(b) 若原文明示 target 本身已是 ETF / exchange-traded fund / 是 closed-end fund /
是 ETP/commodity pool → "no" 并在 target_structure 注明(ETF/CEF/ETP);
(c) 无法从节选判断 → "unclear"。
另抽 mutual_fund_ticker(若原文给出目标基金的共同基金代码, 2-6位大写, 否则 NA)。
输出一个 JSON 对象: {"is_open_end_mutual_fund":"yes|no|unclear",
"target_structure":"mutual_fund|ETF|CEF|ETP|unclear","mutual_fund_ticker":"XXXXX|NA",
"evidence":"≤25词原文引用"}。】"""

SENTINELS = """sentinels:
  - id: S1
    prompt: "Filing excerpt: 'The Board of Trustees of Ridgeline Funds Trust approved the conversion of the Ridgeline Mid-Cap Growth Fund, a mutual fund (ticker: RMCGX), into an actively managed exchange-traded fund (ticker: RMCG), expected to become effective on or about April 22, 2022.' What is the MUTUAL FUND ticker in this excerpt? Reply with the ticker only."
    expect: "RMCGX"
  - id: S2
    prompt: "Filing excerpt: 'The Board of Trustees of Ridgeline Funds Trust approved the conversion of the Ridgeline Mid-Cap Growth Fund, a mutual fund (ticker: RMCGX), into an actively managed exchange-traded fund (ticker: RMCG), expected to become effective on or about April 22, 2022.' On what date is the conversion expected to become effective? Reply with YYYY-MM-DD only."
    expect: "2022-04-22"
  - id: S3
    prompt: "Filing excerpt: 'The Board of Trustees of Ridgeline Funds Trust approved the conversion of the Ridgeline Mid-Cap Growth Fund, a mutual fund (ticker: RMCGX), into an actively managed exchange-traded fund (ticker: RMCG), expected to become effective on or about April 22, 2022.' What is the name of the trust in this excerpt? Reply with the trust name only."
    expect: "Ridgeline Funds Trust"
"""


def windows(text):
    spans = []
    for m in CUES.finditer(text):
        lo, hi = max(0, m.start() - W), m.start() + W
        if spans and lo <= spans[-1][1]:
            spans[-1] = (spans[-1][0], hi)
        else:
            spans.append((lo, hi))
        if len(spans) >= MAXW:
            break
    return " […] ".join(text[lo:hi] for lo, hi in spans)


def main():
    if not MANIFEST.exists():
        raise SystemExit("NEED_INFO: run on the box with the raw harvest present")
    cik = {r["accession"]: r["cik"] for r in csv.DictReader(open(MANIFEST))}
    q = json.loads(QUEUE.read_text())["items"]
    # one spec item per (accession, fund_name) recheck row
    items, skipped = [], []
    for it in q:
        acc = it["source_accession"]; c = cik.get(acc)
        p = PKG / f"{c}_{acc}.htm" if c else None
        if not p or not p.exists():
            skipped.append(acc); continue
        raw = io.open(p, "r", encoding="utf-8", errors="ignore").read()
        txt = re.sub(r"\s+", " ", html.unescape(TAG.sub(" ", raw))).strip()
        ctx = windows(txt)[:CAP]
        if not ctx:
            skipped.append(acc); continue
        rid = f"{acc}::{re.sub(r'[^A-Za-z0-9]+','-', it['fund_name'])[:40]}"
        prompt = RULES + f"\n目标基金候选名: {it['fund_name']}。\n节选:\n" + ctx
        items.append({"id": rid, "_acc": acc, "_fund": it["fund_name"], "prompt": prompt})

    body = ["# P1-T1-recheck — target-fund-type confirmation for owner-rechecked rows",
            "# BUILT ON BOX by p1/t1_arb/build_recheck_spec.py from raw EDGAR filings.",
            "worker: deepseek", "web_search: false", "max_items_per_call: 6",
            f"est_cost: {round(len(items)*0.12,2)}", "items:"]
    for it in items:
        body.append(f'  - id: "{it["id"]}"')
        body.append(f'    _acc: "{it["_acc"]}"')
        body.append(f'    _fund: {json.dumps(it["_fund"], ensure_ascii=False)}')
        body.append("    prompt: |")
        for line in it["prompt"].splitlines():
            body.append("      " + line)
    body.append(SENTINELS)
    OUT.write_text("\n".join(body) + "\n")
    print(f"wrote {OUT}: {len(items)} recheck items | {len(set(skipped))} filings missing/no-cue")


if __name__ == "__main__":
    main()
