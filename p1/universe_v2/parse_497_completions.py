"""Extract explicit completion statements and exact closing days from 497 supplements.

This is the tier-A evidence channel. The phrasings below were not guessed: they
were read off 497s filed within days of conversions whose exact date is known
independently from LEGACY_GOLD, e.g.

    "Effective as of the close of business on June 10, 2022, the assets of the
     Fund were transferred to JPMorgan International Research Enhanced Equity ETF"

A hit is only attributed to an event if the document also names that event's
predecessor -- by series name tokens or by one of its tickers -- because a trust
files 497s for every series it runs, most of which have nothing to do with the
reorganization.
"""
import html
import re
import sys

import pandas as pd

from paths import CACHE as HERE  # data lives outside the repo; see paths.py
CACHE = HERE / "sup497"

MONTH = (r"(?:January|February|March|April|May|June|July|August|September|"
         r"October|November|December)")
D = rf"{MONTH}\s+\d{{1,2}},\s+\d{{4}}"
MOVE = r"(?:transferred|reorganized|converted|acquired|exchanged)"

PATS = [
    (rf"(?i)effective\s+(?:as\s+of\s+)?(?:the\s+close\s+of\s+business\s+on\s+)?({D})"
     rf"[^.]{{0,160}}?\b(?:assets|shares)\b[^.]{{0,80}}?\b(?:were|was)\s+{MOVE}", "effective_assets_moved"),
    (rf"(?i)(?:reorganization|conversion)[^.]{{0,80}}?"
     rf"(?:was|has\s+been)\s+(?:completed|consummated|effected)[^.]{{0,40}}?on\s+({D})", "reorg_completed_on"),
    (rf"(?i)on\s+({D})[^.]{{0,120}}?\bfund\b[^.]{{0,100}}?\b(?:was|were)\s+{MOVE}", "on_date_fund_moved"),
    (rf"(?i)effective\s+(?:as\s+of\s+)?(?:the\s+close\s+of\s+business\s+on\s+)?({D})"
     rf"[^.]{{0,160}}?(?:reorganization|conversion)", "effective_reorg"),
    (rf"(?i)(?:reorganization|conversion)[^.]{{0,120}}?"
     rf"(?:occurred|closed|took\s+place)[^.]{{0,40}}?on\s+({D})", "reorg_occurred_on"),
]
PATS = [(re.compile(p), n) for p, n in PATS]
TAG = re.compile(r"(?is)<(script|style|head)[^>]*>.*?</\1>")

# A 497 also carries pro forma capitalization tables ("as of June 10, 2025, if
# the Reorganization were to have closed") and recitals of unrelated deals from a
# decade ago. Both state a date next to the word Reorganization without the
# transaction having happened, so a hit inside this language is discarded.
NEG = re.compile(r"(?i)pro\s*forma|if\s+the\s+reorganization|were\s+to\s+have|"
                 r"assuming|hypothetical|had\s+the\s+reorganization|"
                 r"is\s+expected|will\s+be\s+|would\s+be\s+|proposed|"
                 # a share-class conversion inside one fund is not a fund event
                 r"class\s+shares?\s+(?:of\s+the\s+fund\s+)?(?:were|was)\s+converted|"
                 r"converted\s+into\s+\w+\s+class\s+shares")


def text_of(p):
    raw = TAG.sub(" ", p.read_bytes().decode("utf8", "ignore"))
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(html.unescape(raw)))


def main():
    files = sorted(CACHE.glob("*.html"))
    print(f"497 supplements available: {len(files):,d}", flush=True)
    rows = []
    for i, p in enumerate(files, 1):
        t = text_of(p)
        for pat, nm in PATS:
            hit = None
            for m in pat.finditer(t):
                ctx = t[max(0, m.start() - 250):m.end() + 450]
                if NEG.search(ctx):
                    continue
                hit = (m, ctx)
                break
            if hit:
                m, ctx = hit
                rows.append({"acc": p.stem, "close_raw": m.group(1),
                             "pattern": nm, "context": ctx})
                break
        if i % 250 == 0:
            print(f"  parsed {i}/{len(files)}", flush=True)

    d = pd.DataFrame(rows)
    if d.empty:
        print("no completion statements found")
        return 0
    d["close_date"] = pd.to_datetime(d.close_raw, errors="coerce")
    d = d[d.close_date.notna()]
    d.to_csv(HERE / "sup497_completions.csv", index=False)
    print(f"\ndocs with an explicit completion statement: {len(d):,d}")
    print(d.pattern.value_counts().to_string())
    print(f"close-date range: {d.close_date.min():%Y-%m-%d} .. {d.close_date.max():%Y-%m-%d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
