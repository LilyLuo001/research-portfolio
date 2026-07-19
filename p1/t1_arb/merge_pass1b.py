#!/usr/bin/env python3
"""BOX-ONLY. Fold Pass 1b results and re-assemble.

Two products, two integrity tiers:
  1. VERBATIM ISO dates recovered from subsequent filings (485BPOS/497/N-CEN/N-8F)
     -> appended to recovered_dates.json (promotes effective_date, same as Pass 1).
  2. Conversions still without a specific day -> deterministic parse of the ORIGINAL
     held filings for VERBATIM quarter/month timing ("Q2 2025", "second quarter of
     2025", "March 2025") -> approx_dates.json. NEVER writes effective_date. Future
     periods (relative to today) are marked date_precision=pending. No LLM, no
     fabrication: every approx token is regex-verified present in the source text.

Run:  python p1/t1_arb/merge_pass1b.py
Then: python ops/runner/contracts.py events_merged p1/events_merged.csv
"""
import csv
import html
import io
import json
import re
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = ROOT / "p1" / "t1_arb"
PKG = ROOT / "p1" / "edgar_filings"
MANIFEST = PKG / "manifest.csv"
OUT1B = ROOT / "ops" / "l1" / "out" / "P1-T1-pass1b.json"
CAND = HERE / "pass1b_candidates.json"
HELD = HERE / "held_back.json"
RECOVERED = HERE / "recovered_dates.json"
APPROX = HERE / "approx_dates.json"
TODAY = time.strftime("%Y-%m-%d")

ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TAG = re.compile(r"<[^>]+>")
MONTHS = ("january february march april may june july august september "
          "october november december").split()
MIDX = {m: i + 1 for i, m in enumerate(MONTHS)}
DATE_CUES = re.compile(
    r"(on or about|close of business|effective|closing|the closing|expected to|"
    r"anticipated|scheduled to|reorganization|conversion|commence)", re.I)
W = 400
# verbatim approximate-timing patterns (no specific day)
Q_NAMED = re.compile(r"(first|second|third|fourth)\s+quarter\s+of\s+(20\d\d)", re.I)
Q_SHORT = re.compile(r"\bQ([1-4])[\s,]+?(20\d\d)\b")
Q_TAIL = re.compile(r"\b([1-4])Q[\s,]*?(20\d\d)\b")
# month + year with NO day adjacent (a day-specific date would be ISO-recoverable)
MONTHYEAR = re.compile(
    r"(?<!\d)(?<!\d[ ,])(" + "|".join(MONTHS) + r")\s+(20\d\d)", re.I)
QNAME2N = {"first": 1, "second": 2, "third": 3, "fourth": 4}


def cik_map():
    m = {}
    with open(MANIFEST) as f:
        for r in csv.DictReader(f):
            m[r["accession"]] = r["cik"]
    return m


def windows(text):
    spans = []
    for mm in DATE_CUES.finditer(text):
        lo, hi = max(0, mm.start() - W), mm.start() + W
        if spans and lo <= spans[-1][1]:
            spans[-1] = (spans[-1][0], hi)
        else:
            spans.append((lo, hi))
    return " ".join(text[lo:hi] for lo, hi in spans)


def parse(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except ValueError:
            return None
    return v if isinstance(v, dict) else None


# a period token counts as the CONVERSION timing only if one of these phrases
# immediately precedes it — excludes fund-inception ("began operations in June
# 2021"), performance dates ("drawdown during March 2020"), distribution months.
TIMING = re.compile(
    r"(effective|expected to (?:occur|close|take effect|be effective|be completed)|"
    r"(?:take|takes|taking) effect|is expected|anticipated to (?:occur|close)|"
    r"scheduled to (?:take place|occur|close)|closing|to close|to occur|"
    r"consummat\w+|complet\w+|reorganization (?:is|will)|conversion (?:is|will)|"
    r"on or about)", re.I)


def _anchored(ctx, start):
    return bool(TIMING.search(ctx[max(0, start - 70):start]))


def approx_from_text(txt):
    """Return (approx_token, precision, evidence) for the earliest conversion-timing
    quarter/month, or None. Quarter beats month. A period is accepted only if a
    conversion-timing phrase immediately precedes it (verbatim, no fabrication)."""
    ctx = windows(txt)
    best = None  # (pos, token, gran, evidence)
    for rgx, named in ((Q_NAMED, True), (Q_SHORT, False), (Q_TAIL, False)):
        for m in rgx.finditer(ctx):
            if not _anchored(ctx, m.start()):
                continue
            q = QNAME2N[m.group(1).lower()] if named else int(m.group(1))
            best = _upd(best, m.start(), f"{m.group(2)}-Q{q}", "quarter", ctx, m)
    if best and best[2] == "quarter":
        return best[1], best[2], best[3]
    for m in MONTHYEAR.finditer(ctx):
        if not _anchored(ctx, m.start()):
            continue
        mo = MIDX[m.group(1).lower()]
        best = _upd(best, m.start(), f"{m.group(2)}-{mo:02d}", "month", ctx, m)
    return (best[1], best[2], best[3]) if best else None


def _upd(best, pos, tok, gran, ctx, m):
    if best is None or pos < best[0]:
        ev = ctx[max(0, m.start() - 40):m.end() + 40].strip()
        return (pos, tok, gran, ev)
    return best


def period_is_future(token):
    """token 'YYYY-Qn' or 'YYYY-MM' -> True if its end is after today."""
    y = int(token[:4])
    if "-Q" in token:
        q = int(token.split("-Q")[1])
        end_m = q * 3
    else:
        end_m = int(token.split("-")[1])
    last_day = f"{y:04d}-{end_m:02d}-28"
    return last_day > TODAY


def main():
    out = json.loads(OUT1B.read_text())
    cand = json.loads(CAND.read_text())["conversions"]
    held = json.loads(HELD.read_text())["held"]
    ck = cik_map()
    rep2accs = {h["accessions"][0]["id"]: [a["id"] for a in h["accessions"]] for h in held}
    rep2held = {h["accessions"][0]["id"]: h for h in held}

    recovered = json.loads(RECOVERED.read_text())
    rmap = recovered.get("recovered", {})
    iso_new, still_na = 0, []
    for rid, v in out.items():
        if rid in ("S1", "S2", "S3"):
            continue
        obj = parse(v)
        eff = str((obj or {}).get("effective_date", "NA"))
        if obj and ISO.match(eff):
            iso_new += 1
            for acc in rep2accs.get(rid, [rid]):
                rmap[acc] = {"effective_date": eff,
                             "date_basis": obj.get("date_basis", "NA"),
                             "evidence": obj.get("evidence", ""),
                             "source": "subsequent-filing harvest (Pass 1b)"}
        else:
            still_na.append(rid)

    recovered["recovered"] = rmap
    recovered["_meta"]["pass1b_iso_added"] = iso_new
    recovered["_meta"]["note"] = "keyed by source_accession; Pass 1 + Pass 1b; consumed by assemble.py"
    RECOVERED.write_text(json.dumps(recovered, indent=1))

    # deterministic approx for the still-NA conversions (+ the 1 pending w/ no subsequent)
    na_reps = set(still_na) | {r for r, c in cand.items() if c.get("pending_flag")}
    approx, n_q, n_m, n_pend, no_approx = {}, 0, 0, 0, []
    for rid in sorted(na_reps):
        h = rep2held.get(rid)
        if not h:
            no_approx.append(rid)
            continue
        found = None
        for a in sorted(h["accessions"], key=lambda x: x.get("filed") or ""):
            acc = a["id"]
            cik = ck.get(acc)
            p = PKG / f"{cik}_{acc}.htm" if cik else None
            if not p or not p.exists():
                continue
            raw = io.open(p, "r", encoding="utf-8", errors="ignore").read()
            txt = re.sub(r"\s+", " ", html.unescape(TAG.sub(" ", raw))).strip()
            r = approx_from_text(txt)
            if r:
                found = (r, acc)
                break
        if not found:
            no_approx.append(rid)
            continue
        (tok, gran, ev), src_acc = found
        prec = "pending" if period_is_future(tok) else gran
        if prec == "pending":
            n_pend += 1
        elif gran == "quarter":
            n_q += 1
        else:
            n_m += 1
        for acc in rep2accs.get(rid, [rid]):
            approx[acc] = {"effective_date_approx": tok, "date_precision": prec,
                           "evidence": ev, "source_accession": src_acc,
                           "source": "verbatim quarter/month from original filing (Pass 1b approx)"}

    APPROX.write_text(json.dumps(
        {"_meta": {"approx_conversions": n_q + n_m + n_pend, "quarter": n_q, "month": n_m,
                   "pending": n_pend, "no_approx_parse": len(no_approx), "built": TODAY,
                   "note": "annotates held rows only; effective_date stays strict/NA"},
         "approx": approx}, indent=1))

    print(f"Pass 1b: +{iso_new} verbatim ISO dates (-> recovered_dates.json)")
    print(f"approx: quarter={n_q} month={n_m} pending={n_pend} | "
          f"{len(no_approx)} still no parseable timing")
    subprocess.run([sys.executable, str(HERE / "assemble.py")], check=True)


if __name__ == "__main__":
    main()
