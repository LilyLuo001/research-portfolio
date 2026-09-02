"""Attach the proposed closing date from the N-14 bodies to each structural pair.

An event is carried by several N-14 accessions -- an initial filing plus
amendments, and one proxy often covers a whole slate of funds. The body parse is
per document, so the dates have to be folded back onto the event through its
supporting accessions.

The latest document wins. An amended proxy is filed precisely because something
in the original changed, and the closing date is one of the things that moves;
taking the earliest would systematically prefer the superseded date.
"""
import sys

import pandas as pd

from paths import CACHE as HERE  # data lives outside the repo; see paths.py


def main():
    ev = pd.read_csv(HERE / "events_master_v2_stage1.csv")
    body = pd.read_csv(HERE / "n14_body_dates.csv")
    body["proposed_close"] = pd.to_datetime(body.proposed_close, errors="coerce")
    body["meeting_date"] = pd.to_datetime(body.meeting_date, errors="coerce")
    idx = body.set_index("acc")

    sub = pd.read_parquet(HERE / "submissions_flat.parquet")
    filed = pd.to_datetime(sub.drop_duplicates("acc").set_index("acc").filed,
                           errors="coerce")

    close, meet, last = [], [], []
    for r in ev.itertuples(index=False):
        accs = [a for a in str(r.supporting_accessions or "").split(";") if a]
        rows = idx.reindex(accs)
        rows = rows.assign(filed=filed.reindex(accs).values) \
                   .sort_values("filed")
        c = rows.proposed_close.dropna()
        m = rows.meeting_date.dropna()
        close.append(c.iloc[-1] if len(c) else pd.NaT)
        meet.append(m.iloc[-1] if len(m) else pd.NaT)
        last.append(rows.filed.max())

    ev["proposed_close"] = close
    ev["meeting_date"] = meet
    ev["n14_last"] = last

    # The year a transaction is anchored to before any completion evidence exists.
    # Roughly half the proxies ship the closing date as an unfilled placeholder
    # ("on or about [ ], 2022"), so a pair with no parsed date still has to be
    # placeable, or the unresolved population cannot be reported by year at all.
    # The fallback is ordered by how close each field sits to the actual closing.
    # a termination month that predates the proxy proposing it belongs to some
    # earlier event of the same series, so it cannot anchor this one
    term = pd.to_datetime(ev.ncen_termination_month, errors="coerce")
    first = pd.to_datetime(ev.n14_first_filed, errors="coerce")
    ev["term_coherent"] = term.where(term >= first - pd.Timedelta(days=90))

    src = pd.Series("proposed_close", index=ev.index)
    yr = pd.to_datetime(ev.proposed_close, errors="coerce").dt.year
    for col, nm in (("term_coherent", "ncen_termination"),
                    ("meeting_date", "shareholder_meeting"),
                    ("n14_last", "n14_filed")):
        fill = pd.to_datetime(ev[col], errors="coerce").dt.year
        src = src.mask(yr.isna() & fill.notna(), nm)
        yr = yr.fillna(fill)
    ev["anchor_year"] = yr
    ev["anchor_year_source"] = src.where(yr.notna())
    ev.to_csv(HERE / "events_master_v2_stage2.csv", index=False)

    print(f"events                       : {len(ev):,d}")
    print(f"  with a proposed close date : {int(ev.proposed_close.notna().sum()):,d}"
          f"  ({ev.proposed_close.notna().mean():.0%})")
    print(f"  with a meeting date        : {int(ev.meeting_date.notna().sum()):,d}")
    print("\nanchor year:")
    print(ev.anchor_year.value_counts().sort_index().to_string())
    print("\nanchor year came from:")
    print(ev.anchor_year_source.value_counts().to_string())
    print(f"  no anchor at all: {int(ev.anchor_year.isna().sum())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
