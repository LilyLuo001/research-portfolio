#!/usr/bin/env python3
"""BOX-ONLY. Re-categorization recovery pass: redeploy deepseek v4-pro on the
FULL raw filing text (not the narrow excerpt windows the first pass saw) for the
"dropped" no_event pools most likely to hide real MF->ETF conversions.

Root cause of the false negatives: the original spec only fed HEAD + a few
conversion-keyword windows, so a filing whose conversion language sat elsewhere
got coded MENTION / MF_TO_MF. With the raw filings now on the box, deepseek can
read the whole document and re-decide with the frozen v2 STEP rules.

Default targets (override with --reasons): MENTION, recheck_noevent. Add
MF_TO_MF with --reasons MENTION,MF_TO_MF,recheck_noevent for the widest sweep
(bigger + lower yield). ETF_TO_ETF / SHARECLASS / CEF / INTERVAL are excluded —
they are out-of-scope by definition; pass them explicitly if you want a spot check.

Run:  python p1/t1_arb/build_recat_spec.py            # MENTION + recheck_noevent
Then: python ops/l1/run_mopup.py P1-T1-recat --live
Then: python p1/t1_arb/merge_recat.py
"""
import argparse
import csv
import html
import io
import json
import re
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
FINAL = ROOT / "p1" / "t1_events_final.json"
PKG = ROOT / "p1" / "edgar_filings"
MANIFEST = PKG / "manifest.csv"
OUT = ROOT / "ops" / "l1" / "P1-T1-recat.yaml"
TAG = re.compile(r"<[^>]+>")
BODY_CAP = 14000     # chars of full-text body per filing (deepseek v4-pro context is ample)

# the frozen v2 STEP categorization rules (same as P1-T1-events v2), full-text edition
RULES = """【规则 v2 (manual §T1). 这是"再判定"任务: 给你某备案的完整正文(而非节选)。
STEP 1 找出所有 reorganization/conversion, 指明 TARGET(被并入/被转换方) 与 ACQUIRER(存续方)。
STEP 2 用原文判定二者结构: TARGET 是否 open-end mutual fund(多类别/按 NAV 申赎);
ACQUIRER 是否 ETF(exchange-traded fund/上市交易)。
STEP 3 判定: 仅当 TARGET=open-end mutual fund 且 ACQUIRER=ETF → event(含 shell 转换、
被现有 ETF 收购、以及已完成转换的追溯陈述)。否则 no_event 并给 reason:
MF_TO_MF / ETF_TO_ETF / CEF / INTERVAL / SHARECLASS / MENTION。
输出一个 JSON 对象: {"verdict":"event|no_event","reason":"<若 no_event>",
"fund_name":"目标共同基金名","mutual_fund_ticker":"XXXXX|NA","etf_ticker":"XXXX|NA",
"announce_date":"YYYY-MM-DD|NA","effective_date":"YYYY-MM-DD|NA",
"asset_class":"equity_US|equity_intl|fixed_income|other|NA","confidence":"H|M|L",
"evidence":"≤25词原文引用(event 必引证 ACQUIRER 为 ETF 且 TARGET 为共同基金)"}。
不得凭记忆; 原文找不到的字段填 NA。】"""

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reasons", default="MENTION,recheck_noevent",
                    help="comma list of no_event reasons / recheck_noevent to re-read")
    a = ap.parse_args()
    want = set(a.reasons.split(","))
    if not MANIFEST.exists():
        raise SystemExit("NEED_INFO: run on the box with the raw harvest present")
    cik = {r["accession"]: r["cik"] for r in csv.DictReader(open(MANIFEST))}
    final = json.loads(FINAL.read_text())

    targets = []
    for fid, v in final.items():
        if fid == "_meta" or not v.get("no_event"):
            continue
        fsc = v.get("_spotcheck") or {}
        tag = fsc.get("disposition") if fsc.get("disposition") == "recheck_noevent" else v.get("reason")
        if tag in want:
            targets.append(fid)

    items, skipped = [], []
    for acc in targets:
        c = cik.get(acc)
        p = PKG / f"{c}_{acc}.htm" if c else None
        if not p or not p.exists():
            skipped.append(acc); continue
        raw = io.open(p, "r", encoding="utf-8", errors="ignore").read()
        txt = re.sub(r"\s+", " ", html.unescape(TAG.sub(" ", raw))).strip()[:BODY_CAP]
        if not txt:
            skipped.append(acc); continue
        items.append({"id": acc, "prompt": RULES + "\n完整正文:\n" + txt})

    body = ["# P1-T1-recat — full-text re-categorization recovery (deepseek v4-pro)",
            f"# BUILT ON BOX; targets reasons={sorted(want)}. Re-reads whole filings.",
            "worker: deepseek", "web_search: false", "max_items_per_call: 4",
            f"est_cost: {round(len(items)*0.2,2)}", "items:"]
    for it in items:
        body.append(f'  - id: "{it["id"]}"')
        body.append("    prompt: |")
        for line in it["prompt"].splitlines():
            body.append("      " + line)
    body.append(SENTINELS)
    OUT.write_text("\n".join(body) + "\n")
    print(f"wrote {OUT}: {len(items)} filings to re-categorize (reasons={sorted(want)}) "
          f"| {len(set(skipped))} missing raw file")


if __name__ == "__main__":
    main()
