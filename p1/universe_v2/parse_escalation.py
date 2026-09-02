"""Extract completion statements from the wider filing chain, both sides of the deal.

parse_497_completions reads the predecessor's own supplements, where the deal is
described looking forward out of the fund that is disappearing ("the assets of the
Fund were transferred to X ETF"). The successor describes the same event looking
backward, in its prospectus and shareholder reports, and uses a different family
of sentences:

    "The Fund is the successor to the Cannabis Growth Fund following the
     reorganization of the Predecessor Fund, which occurred on July 9, 2021"

Those are the SUCCESSOR_PATS below. The predecessor-side patterns are reused
unchanged so a document is read the same way whichever trust filed it.

The negative guard is inherited too: a successor prospectus is exactly the kind of
document that also carries pro forma tables and recitals of older reorganizations.
"""
import html
import re
import sys

import pandas as pd

from parse_497_completions import D, NEG, PATS as PRE_PATS, TAG

from paths import CACHE as HERE  # data lives outside the repo; see paths.py
CACHE = HERE / "escalation"

# the successor's own account of where it came from
SUCCESSOR_PATS = [
    (rf"(?i)(?:predecessor\s+(?:fund|mutual\s+fund)|reorganization)[^.]{{0,140}}?"
     rf"which\s+(?:occurred|closed|took\s+place|was\s+completed)\s+on\s+({D})",
     "predecessor_reorg_occurred_on"),
    (rf"(?i)successor\s+to[^.]{{0,160}}?\b(?:on|effective)\s+({D})",
     "successor_to_on_date"),
    (rf"(?i)(?:acquired|assumed)\s+(?:substantially\s+all\s+of\s+)?the\s+assets"
     rf"[^.]{{0,140}}?\bon\s+({D})", "acquired_assets_on"),
    (rf"(?i)prior\s+to\s+({D})[^.]{{0,140}}?"
     rf"(?:operated|was\s+organized|existed)\s+as[^.]{{0,60}}?"
     rf"(?:open-end\s+)?mutual\s+fund", "prior_to_operated_as_mf"),
    (rf"(?i)convert(?:ed|sion)[^.]{{0,120}}?exchange[- ]traded\s+fund"
     rf"[^.]{{0,80}}?on\s+({D})", "converted_to_etf_on"),
]
SUCCESSOR_PATS = [(re.compile(p), n) for p, n in SUCCESSOR_PATS]
ALL_PATS = PRE_PATS + SUCCESSOR_PATS


def text_of(p):
    raw = TAG.sub(" ", p.read_bytes().decode("utf8", "ignore"))
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(html.unescape(raw)))


def main():
    files = sorted(CACHE.glob("*.html"))
    print(f"escalation documents available: {len(files):,d}", flush=True)
    rows = []
    for i, p in enumerate(files, 1):
        try:
            t = text_of(p)
        except Exception:
            continue
        # every pattern is tried, not just the first that fires: one prospectus can
        # describe several reorganizations and the right one is picked later, by
        # matching the fund names against a specific event
        for pat, nm in ALL_PATS:
            for m in pat.finditer(t):
                ctx = t[max(0, m.start() - 250):m.end() + 450]
                if NEG.search(ctx):
                    continue
                rows.append({"acc": p.stem, "close_raw": m.group(1),
                             "pattern": nm, "context": ctx})
                break
        if i % 250 == 0:
            print(f"  parsed {i}/{len(files)} hits={len(rows)}", flush=True)

    d = pd.DataFrame(rows)
    if d.empty:
        print("no completion statements found")
        return 0
    d["close_date"] = pd.to_datetime(d.close_raw, errors="coerce")
    d = d[d.close_date.notna()].drop_duplicates(["acc", "close_date", "pattern"])
    d.to_csv(HERE / "escalation_completions.csv", index=False)
    print(f"\ncompletion statements: {len(d):,d} in {d.acc.nunique():,d} documents")
    print(d.pattern.value_counts().to_string())
    print(f"close-date range: {d.close_date.min():%Y-%m-%d} .. "
          f"{d.close_date.max():%Y-%m-%d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
