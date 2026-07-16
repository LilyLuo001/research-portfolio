#!/usr/bin/env python3
"""Deterministic condense of the worklist excerpts for in-session reading.
Keeps: full head (first ~1200 chars: filer/fund/supplement-date zone) + up to
4 windows around STRONG conversion-family phrases + (if none) one window
around the first ETF mention so no_event can be judged. Pure text surgery —
no classification is made here; every item still gets a model verdict."""
import json, re, pathlib

D = pathlib.Path(__file__).parent
STRONG = re.compile(
    r"(conver(?:sion|t(?:ed|ing)?)\s+(?:of\s+)?(?:the\s+|each\s+|your\s+)?fund"
    r"|conver(?:sion|t(?:ed|ing)?)\s+(?:from\s+)?a?\s*mutual\s+fund"
    r"|mutual\s+fund\s+to\s+an?\s+(?:exchange-traded\s+fund|ETF)"
    r"|into\s+an?\s+(?:exchange-traded\s+fund|ETF)"
    r"|reorganiz(?:ation|ed?)\s+of\s+.{0,120}?into\s+"
    r"|will\s+be\s+conver(?:ted)"
    r"|approved\s+the\s+conversion"
    r"|semi-transparent|proxy\s+portfolio|activeshares)", re.I)
ETF = re.compile(r"exchange-traded fund|\bETF\b", re.I)
HEAD, W = 1300, 650

def condense(text):
    parts, spans = [], []
    for m in STRONG.finditer(text):
        if m.start() < HEAD:  # already inside head
            continue
        lo, hi = m.start() - W, m.start() + W
        if spans and lo <= spans[-1][1]:
            spans[-1] = (spans[-1][0], hi)
        else:
            spans.append((lo, hi))
        if len(spans) >= 4:
            break
    if not spans:
        m = ETF.search(text, HEAD)
        if m:
            spans = [(m.start() - W, m.start() + W)]
    parts = [text[:HEAD]] + [text[max(0, lo):hi] for lo, hi in spans]
    return " […] ".join(parts)

rows = [json.loads(l) for l in open(D / "worklist.jsonl")]
CAP = 42_000
batch, size, bn, tot = [], 0, 0, 0
def flush():
    global batch, size, bn
    if not batch: return
    bn += 1
    (D / f"cb_{bn:03d}.txt").write_text("\n\n".join(batch))
    batch, size = [], 0

for r in rows:
    # excerpt lives only in worklist? no — re-read from worklist row
    pass

# worklist.jsonl didn't store excerpts... rebuild from spec via build_worklist's groups
import hashlib, yaml
SPEC = pathlib.Path("/home/user/research-portfolio/ops/l1/P1-T1-events.yaml")
HDR = re.compile(
    r"文件: (?P<accession>\S+) \(form (?P<form>[^,]+), filed (?P<filed>[\d-]+), "
    r"(?P<company>.*?)\)\nsource_url: (?P<url>\S+)\n节选:\n(?P<excerpt>.*)\Z", re.S)
spec = yaml.safe_load(SPEC.read_text())
ex_by_h = {}
for it in spec["items"]:
    m = HDR.search(it["prompt"])
    ex = m.group("excerpt").strip()
    h = hashlib.sha1(ex.encode()).hexdigest()[:12]
    ex_by_h[h] = ex

for r in rows:
    m0 = r["members"][0]
    c = condense(ex_by_h[r["h"]])
    tot += len(c)
    head = (f"=== {r['h']} n={r['n']} | {m0['company']} | form {m0['form']} "
            f"filed {m0['filed']} | acc {m0['id']} ===")
    entry = head + "\n" + c
    if size + len(entry) > CAP:
        flush()
    batch.append(entry); size += len(entry)
flush()
print(f"batches: {bn}  condensed bytes: {tot}  (from 13.2MB)")
