#!/usr/bin/env python3
"""BOX-ONLY. Build the deepseek date-recovery spec for the 109 held-back
conversions (events confirmed, but no effective_date in the original excerpt
windows). Reads the raw local EDGAR filings — p1/edgar_filings/{cik}_{acc}.htm,
located via p1/edgar_filings/manifest.csv — and cuts DATE-focused windows (the
original condense targeted conversion phrases, not closing dates, so the date
often fell outside the window). Emits ops/l1/P1-T1-daterecover.yaml.

Run:  python p1/t1_arb/build_daterecover_spec.py
Then: python ops/l1/run_mopup.py P1-T1-daterecover --live
Then: python p1/t1_arb/merge_daterecover.py
"""
import csv
import html
import io
import json
import os
import re
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
HELD = ROOT / "p1" / "t1_arb" / "held_back.json"
PKG = ROOT / "p1" / "edgar_filings"
MANIFEST = PKG / "manifest.csv"
OUT = ROOT / "ops" / "l1" / "P1-T1-daterecover.yaml"

TAG = re.compile(r"<[^>]+>")
# closing/effective-date language + explicit month-day-year dates
DATE_CUES = re.compile(
    r"(on or about|close of business|effective date|closing date|the closing|"
    r"will (?:occur|take place|be completed|commence)|is expected to (?:occur|close)|"
    r"anticipated to (?:occur|close)|scheduled to (?:take place|occur|close)|"
    r"reorganization (?:is|will|occurred|closed|was completed)|"
    r"commenced operations|as the successor to|completion of the (?:reorganization|conversion)|"
    r"[A-Z][a-z]+ \d{1,2},? \d{4})", re.I)
W = 400          # window half-width around each cue
MAX_WIN = 8      # windows per filing
CAP_PER_ITEM = 9000   # chars of date-context per conversion (across its filings)

RULES = """【任务: 抽取转换生效日. 本条目是一个"共同基金→ETF"转换事件, 已确认为 event,
但生效日缺失. 给你该转换相关备案的"日期上下文"节选(可能来自多个备案: N-14/497等).
只做一件事: 找出该转换实际(或预定)生效/交割/完成日 effective_date。
规则: (1) effective_date = 声明的 closing/生效/完成日, 输出 YYYY-MM-DD;
(2) 只有月份或季度(如 "Q3 2021","in October 2023")→ NA; 含糊→ NA;
(3) 若多个备案给不同日期, 取最新备案所述日期(修订会推迟交割), 并在 evidence 注明;
(4) 不得凭记忆补充; 抽不到→ NA。
输出一个 JSON 对象: {"effective_date": "YYYY-MM-DD"|"NA", "date_basis": "closing|expected|retrospective|NA",
"evidence": "≤25词原文引用"}。】"""

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


def raw_path(cik, acc):
    return PKG / f"{cik}_{acc}.htm"


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
    if not MANIFEST.exists():
        raise SystemExit(f"NEED_INFO: {MANIFEST} missing — run on the box with the raw harvest present")
    cik_of = {}
    with open(MANIFEST) as f:
        for r in csv.DictReader(f):
            cik_of[r["accession"]] = r["cik"]

    held = json.loads(HELD.read_text())["held"]
    items, skipped = [], []
    for h in held:
        key = re.sub(r"[^a-z0-9]+", "-", (h["fund_name"] or "NA").lower()).strip("-")[:48]
        ctx, used = [], []
        for a in sorted(h["accessions"], key=lambda x: x.get("filed") or ""):
            acc = a["id"]; cik = cik_of.get(acc)
            if not cik:
                continue
            p = raw_path(cik, acc)
            if not p.exists():
                continue
            raw = io.open(p, "r", encoding="utf-8", errors="ignore").read()
            txt = re.sub(r"\s+", " ", html.unescape(TAG.sub(" ", raw))).strip()
            w = date_windows(txt)
            if w:
                ctx.append(f"[备案 {acc} form {a.get('form')} filed {a.get('filed')}]: {w}")
                used.append(acc)
            if sum(len(c) for c in ctx) > CAP_PER_ITEM:
                break
        if not ctx:
            skipped.append(h["fund_name"])
            continue
        item_id = f"{h['accessions'][0]['id']}"       # representative = first filing's accession
        prompt = (RULES + f"\n转换基金: {h['fund_name']} ({h['family']})。\n"
                  + "日期上下文:\n" + ("\n".join(ctx))[:CAP_PER_ITEM])
        items.append({"id": item_id, "_fund": h["fund_name"], "_accessions": used, "prompt": prompt})

    body = ["# P1-T1-daterecover — full-text effective-date recovery for held-back conversions",
            "# BUILT ON BOX by p1/t1_arb/build_daterecover_spec.py from raw EDGAR filings.",
            "# Channel A family (deepseek); date-only extraction, no verdicts.",
            "worker: deepseek", "web_search: false", "max_items_per_call: 6",
            f"est_cost: {round(len(items)*0.12,2)}", "items:"]
    import yaml
    for it in items:
        body.append(f'  - id: "{it["id"]}"')
        body.append(f'    _fund: {json.dumps(it["_fund"], ensure_ascii=False)}')
        body.append(f'    _accessions: {json.dumps(it["_accessions"])}')
        body.append("    prompt: |")
        for line in it["prompt"].splitlines():
            body.append("      " + line)
    body.append(SENTINELS)
    OUT.write_text("\n".join(body) + "\n")
    print(f"wrote {OUT}: {len(items)} conversions with date-context "
          f"| {len(skipped)} had no date cues in raw text (report to owner): {skipped[:6]}")


if __name__ == "__main__":
    main()
