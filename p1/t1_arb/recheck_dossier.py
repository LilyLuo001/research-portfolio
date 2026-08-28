#!/usr/bin/env python3
"""Build the evidence dossier for the owner-gate recheck pool.

`assemble.py` drops every event record whose `_spotcheck.disposition` is
`recheck`, `defer` or `not_event`. The 2026-07-18 gate assigned one of those to
111 records across 66 funds — but only 4 were `not_event`. The other 107 were
parked with reasons that are all one question:

    the excerpt proves a reorganization INTO an ETF, but does it prove the
    TARGET was an open-end mutual fund, rather than a closed-end fund or
    another ETF?

That question is answerable from evidence this repo already carries.
`p1/t1_channelA_wip/handoff/cb_*.txt` holds 3.6 MB of condensed filing excerpts
covering all 1,418 accessions — it never needed `sec.gov`, which is
EGRESS_BLOCKED from the working container (re-verified 2026-08-27 by curl, the
agent-proxy status endpoint, and WebFetch).

This script does the mechanical half: for each gated record it locates the
filing's excerpt and pulls the sentences carrying the decisive vocabulary, so a
human or a third channel adjudicates against quoted text rather than from
memory. It makes NO verdict of its own — the classifier fields it emits are
candidate signals, and `resolve_recheck.py` is where a verdict with a quote gets
recorded.

  python p1/t1_arb/recheck_dossier.py            # write recheck_dossier.md + .json
  python p1/t1_arb/recheck_dossier.py --stats    # counts only
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
P1 = HERE.parent
ROOT = P1.parent
FINAL = P1 / "t1_events_final.json"
WORKLIST = P1 / "t1_channelA_wip" / "handoff" / "worklist.jsonl"
BATCHES = sorted((P1 / "t1_channelA_wip" / "handoff").glob("cb_*.txt"))
OUT_MD = HERE / "recheck_dossier.md"
OUT_JSON = HERE / "recheck_dossier.json"

GATED = ("recheck", "defer", "not_event")

# Decisive vocabulary, per the frozen scope rule in
# p1/t1_channelA_wip/POLICY.md: an event is a mutual fund -> ETF reorganisation
# (including acquisition of a MF by an existing ETF). MF->MF, ETF->ETF, CEF and
# acquiring-ETF-prospectus-only are NOT events.
#
# These are SIGNALS for a reader, deliberately not a decision procedure. The
# same sentence can carry an open-end marker for the acquirer and say nothing
# about the target, which is exactly the ambiguity the gate flagged.
MARKERS = {
    # target is an open-end mutual fund
    "openend": [
        r"open-?end(?:ed)? management investment compan",
        r"open-?end(?:ed)? investment compan",
        r"open-?end(?:ed)? fund",
        r"a series of [A-Z][^.,;]{0,80}(?:Fund|Trust|Funds|Inc\.|Portfolios?)",
        r"registered (?:under|as) the Investment Company Act",
        r"mutual fund",
    ],
    # target is a closed-end fund -> NOT an event
    "closedend": [
        r"closed-?end(?:ed)? (?:management )?investment compan",
        r"closed-?end(?:ed)? fund",
        r"\bCEF\b",
    ],
    # target is already an ETF -> NOT an event
    "etf_target": [
        r"(?:Acquired|Target)\s+(?:Fund|Portfolio|ETF)[^.]{0,120}\bexchange-?traded fund",
        r"(?:Acquired|Target)\s+ETF\b",
        r"reorganization of[^.]{0,80}ETF[^.]{0,40}into[^.]{0,80}ETF",
    ],
    # the conversion statement itself
    "conversion": [
        r"reorganiz\w+ into[^.]{0,120}exchange-?traded fund",
        r"convert\w* (?:in)?to[^.]{0,120}exchange-?traded fund",
        r"convert\w* (?:in)?to an ETF",
        r"will be reorganized into[^.]{0,120}ETF",
        r"acquisition of the assets and assumption of the liabilities",
        r"Acquired (?:Fund|Portfolio)",
    ],
    # share-class aging / MF->MF, both out of scope
    "outofscope": [
        r"Class [A-Z] shares? (?:will )?(?:automatically )?convert(?:ing)? (?:in)?to Class",
        r"merger of[^.]{0,80}into[^.]{0,80}(?:Fund|Portfolio)\b(?![^.]{0,40}ETF)",
    ],
}
COMPILED = {k: [re.compile(p, re.I) for p in v] for k, v in MARKERS.items()}

SENT = re.compile(r"(?<=[.;])\s+")


def load_gated() -> list[dict]:
    """Every event record the owner gate parked, with its reason."""
    final = json.loads(FINAL.read_text())
    out = []
    for fid, v in final.items():
        if fid == "_meta" or v.get("no_event") or v.get("NEED_HUMAN"):
            continue
        for idx, e in enumerate(v.get("events") or [v]):
            sc = e.get("_spotcheck")
            if sc and sc.get("disposition") in GATED:
                out.append({
                    "accession": fid,
                    "event_index": idx,
                    "fund_name": e.get("fund_name"),
                    "family": e.get("family"),
                    "effective_date": e.get("effective_date"),
                    "announce_date": e.get("announce_date"),
                    "asset_class": e.get("asset_class"),
                    "confidence": e.get("confidence"),
                    "channel_evidence": e.get("evidence"),
                    "gate_disposition": sc.get("disposition"),
                    "gate_reason": sc.get("reason"),
                })
    return out


def excerpt_index() -> dict[str, str]:
    """accession -> the condensed excerpt text for its filing group.

    cb_*.txt blocks are delimited by a `=== <hash> n=… | … ===` header line, and
    worklist.jsonl maps every accession to its group hash. Several accessions
    can share one excerpt (amendments of one filing were deduplicated upstream).
    """
    h_for_acc: dict[str, str] = {}
    for line in WORKLIST.read_text().splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        for m in d["members"]:
            h_for_acc[m["accession"]] = d["h"]

    text_for_h: dict[str, str] = {}
    header = re.compile(r"^=== ([0-9a-f]{6,}) n=\d+ \|", re.M)
    for path in BATCHES:
        raw = path.read_text(errors="replace")
        hits = list(header.finditer(raw))
        for i, m in enumerate(hits):
            end = hits[i + 1].start() if i + 1 < len(hits) else len(raw)
            text_for_h[m.group(1)] = raw[m.start():end]
    return {acc: text_for_h[h] for acc, h in h_for_acc.items() if h in text_for_h}


def sentences_matching(text: str, patterns, limit=6) -> list[str]:
    out, seen = [], set()
    for chunk in SENT.split(text):
        c = " ".join(chunk.split())
        if len(c) < 25 or c in seen:
            continue
        if any(p.search(c) for p in patterns):
            seen.add(c)
            out.append(c[:600])
            if len(out) >= limit:
                break
    return out


def build() -> list[dict]:
    gated = load_gated()
    idx = excerpt_index()
    rows = []
    for g in gated:
        text = idx.get(g["accession"], "")
        signals = {k: sentences_matching(text, pats) for k, pats in COMPILED.items()}
        rows.append({**g,
                     "excerpt_found": bool(text),
                     "excerpt_chars": len(text),
                     "signals": signals})
    return rows


def render(rows: list[dict]) -> str:
    by_acc: dict[str, list[dict]] = {}
    for r in rows:
        by_acc.setdefault(r["accession"], []).append(r)

    L = ["# Recheck pool — evidence dossier", "",
         "_Generated by `p1/t1_arb/recheck_dossier.py`. Every quote below is from",
         "`p1/t1_channelA_wip/handoff/cb_*.txt`, the committed condensed excerpts of",
         "the filings themselves. No verdicts here — see `recheck_resolution.json`._",
         "",
         f"**{len(rows)} gated event records across {len(by_acc)} accessions.**", ""]
    for acc, recs in by_acc.items():
        L.append(f"## {acc}")
        L.append("")
        for r in recs:
            L.append(f"- **{r['fund_name']}** ({r['family']}) — eff `{r['effective_date']}` "
                     f"· class `{r['asset_class']}` · gate `{r['gate_disposition']}`: "
                     f"_{r['gate_reason']}_")
        r0 = recs[0]
        if not r0["excerpt_found"]:
            L += ["", "  ⚠️ NO EXCERPT FOUND — cannot adjudicate offline.", ""]
            continue
        for key, label in [("openend", "open-end / mutual-fund markers"),
                           ("closedend", "closed-end markers"),
                           ("etf_target", "target-is-already-an-ETF markers"),
                           ("conversion", "conversion statement"),
                           ("outofscope", "share-class / MF-to-MF markers")]:
            hits = r0["signals"][key]
            if hits:
                L.append(f"  **{label}:**")
                for h in hits:
                    L.append(f"  > {h}")
                L.append("")
        L.append("")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", action="store_true")
    a = ap.parse_args()
    rows = build()
    if a.stats:
        n_acc = len({r["accession"] for r in rows})
        no_ex = sum(1 for r in rows if not r["excerpt_found"])
        print(f"gated records          : {len(rows)}")
        print(f"gated accessions       : {n_acc}")
        print(f"records with no excerpt: {no_ex}")
        for k in COMPILED:
            n = sum(1 for r in rows if r["signals"][k])
            print(f"  records with {k:11s} signal: {n}")
        return
    OUT_JSON.write_text(json.dumps(
        {"_meta": {"n_records": len(rows),
                   "n_accessions": len({r["accession"] for r in rows}),
                   "source": "p1/t1_channelA_wip/handoff/cb_*.txt",
                   "purpose": "evidence for adjudicating the owner-gate recheck pool"},
         "records": rows}, indent=2, ensure_ascii=False) + "\n")
    OUT_MD.write_text(render(rows))
    print(f"wrote {OUT_MD.relative_to(ROOT)} and {OUT_JSON.relative_to(ROOT)}")
    print(f"{len(rows)} records / {len({r['accession'] for r in rows})} accessions")


if __name__ == "__main__":
    main()
