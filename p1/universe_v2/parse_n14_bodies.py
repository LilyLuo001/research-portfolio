"""Parse the proposed closing date and the shareholder meeting date out of each N-14 body.

The header gives the parties; only the body gives the date the filer proposed to
close. That date is what anchors a pair before any completion evidence exists,
and it is what the elapsed-completion channel tests against, so it has to come
from the document rather than from a guess about filing lags.

Two things make this harder than finding a date. Roughly half of these proxies
ship the closing date as an unfilled placeholder -- "on or about [    ], 2022" --
because the sponsor does not know it when the proxy is printed, and a parser that
reaches for the nearest date will happily return the printing date instead. So a
date is only taken from a sentence that also says what is happening on it. And an
N-14 body is mostly prospectus: it names dozens of dates belonging to fee tables,
fiscal year ends and performance histories. Matching on a transaction verb near
"on or about" is what separates the closing from all of them.

The meeting date is parsed separately and is not a substitute for the closing
date. Shareholders approve on one day and the reorganization closes on another,
usually weeks later; treating the meeting as the close would move every event
earlier by that gap.
"""
import html
import pathlib
import re
import sys

import pandas as pd

import fetchlib
from paths import BODIES, CACHE

MONTH = (r"(?:January|February|March|April|May|June|July|August|September|"
         r"October|November|December)")
DATE = re.compile(rf"{MONTH}\s+\d{{1,2}},?\s+(?:19|20)\d{{2}}")
TAGS = re.compile(r"(?is)<(script|style|head)[^>]*>.*?</\1>")

# the transaction, not the printing: a closing date is stated as something that
# happens to the Reorganization, so the verb has to be in the same sentence
CLOSE = re.compile(
    r"(?is)(?:reorganization|conversion|transaction|closing|exchange)"
    r"[^.;]{0,200}?"
    r"(?:is |are |will |to |expected to |anticipated to |scheduled to )"
    r"[^.;]{0,80}?"
    r"(?:occur|take place|be (?:effective|consummated|completed)|close)"
    r"[^.;]{0,60}?on or about\s+(" + MONTH + r"\s+\d{1,2},?\s+(?:19|20)\d{2})")
CLOSE_ALT = re.compile(
    r"(?is)(?:closing date|effective time|effective date)[^.;]{0,120}?"
    r"on or about\s+(" + MONTH + r"\s+\d{1,2},?\s+(?:19|20)\d{2})")
# a shareholder meeting that has not happened yet, which is what a proxy notices.
# "at a meeting held on August 25, 2022, the Board approved" is a board meeting in
# the past and taking it would put a date in this column that no shareholder ever
# voted on, so the verb has to be forward-looking and the board excluded. Filers
# routinely leave the printer's bracket in around a date they did fill.
MEET = re.compile(
    r"(?is)(?<!board )(?<!trustees )(?:special |annual |joint )*meeting"
    r"(?:\s+of\s+(?:the\s+)?(?:share|stock)holders)?"
    r"[^.;]{0,200}?"
    r"(?:will be|to be|is to be|is scheduled to be|are to be)\s+held"
    r"[^.;]{0,200}?(?:on\s+)?(?:\w+day,?\s+)?[\[\(]?\s*(" + MONTH
    + r"\s+\d{1,2},?\s+(?:19|20)\d{2})")


def text(path):
    with open(path, "rb") as fh:
        raw = TAGS.sub(" ", fh.read().decode("utf8", "ignore"))
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(html.unescape(raw)))


def day(s):
    return pd.to_datetime(re.sub(r"\s+", " ", s).replace(" ,", ","),
                          errors="coerce")


def main():
    ev = pd.read_csv(CACHE / "events_master_v2_stage1.csv")
    accs = []
    for s in ev.supporting_accessions.fillna(""):
        accs += [a for a in str(s).split(";") if a]
    accs = sorted(set(accs))

    sub = pd.read_parquet(CACHE / "submissions_flat.parquet")
    loc = sub.drop_duplicates("acc").set_index("acc")[["cik", "doc"]]

    rows, missing = [], 0
    for n, acc in enumerate(accs, 1):
        if acc not in loc.index:
            missing += 1
            continue
        cik, doc = int(loc.at[acc, "cik"]), loc.at[acc, "doc"]
        p = fetchlib.get(
            f"https://www.sec.gov/Archives/edgar/data/{cik}/"
            f"{acc.replace('-', '')}/{doc}",
            BODIES / f"{acc}.html", accession=acc, kind="n14_body")
        if p is None:
            missing += 1
            continue
        t = text(p)
        m = CLOSE.search(t) or CLOSE_ALT.search(t)
        k = MEET.search(t)
        rows.append({"acc": acc, "cik": cik,
                     "proposed_close": day(m.group(1)).date() if m and
                     pd.notna(day(m.group(1))) else None,
                     "meeting_date": day(k.group(1)).date() if k and
                     pd.notna(day(k.group(1))) else None,
                     "chars": len(t)})
        if n % 25 == 0:
            print(f"  {n}/{len(accs)}", flush=True)

    d = pd.DataFrame(rows)
    out = CACHE / "n14_body_dates.csv"
    d.to_csv(out, index=False)
    fetchlib.record(out, kind="derived", parser="parse_n14_bodies.py",
                    extra={"lineage": "raw/n14_bodies/*.html",
                           "accessions": len(d)})

    print(f"\naccessions      : {len(accs)}")
    print(f"bodies parsed   : {len(d)}   (unfetchable/unindexed: {missing})")
    print(f"proposed_close  : {int(d.proposed_close.notna().sum())} "
          f"({d.proposed_close.notna().mean():.0%})")
    print(f"meeting_date    : {int(d.meeting_date.notna().sum())} "
          f"({d.meeting_date.notna().mean():.0%})")

    # The snapshot stage2 is the only surviving record of what the lost parser
    # produced, so it is the reproducibility baseline -- and it must be read from
    # the snapshot, not from the cache, which this rebuild overwrites.
    #
    # proposed_close reproduces exactly (117 events). meeting_date does not, and
    # the difference is a defect corrected rather than a regression: a permissive
    # rule recovers the old 150, but it does so by reading "the Board considered
    # the Conversions at meetings held on July 9, 2019" as a shareholder meeting.
    # Those are board deliberations, often years before the proxy. Eight events
    # would take an anchor_year earlier than their own N-14 filing that way.
    s2 = pathlib.Path.home() / "p1_universe_v2_snapshot" / "events_master_v2_stage2.csv"
    if s2.exists():
        old = pd.read_csv(s2)
        print(f"\nsnapshot stage2 baseline (event level, not accession):")
        print(f"  proposed_close  : {int(old.proposed_close.notna().sum())}")
        print(f"  meeting_date    : {int(old.meeting_date.notna().sum())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
