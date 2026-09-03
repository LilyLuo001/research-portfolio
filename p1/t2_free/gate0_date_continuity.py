#!/usr/bin/env python3
"""Cross-check each verified conversion date against when its fund stopped reporting.

A predecessor series files N-PORT until it ceases to exist, so its last holdings
report is an independent witness to when the conversion actually happened. That
witness comes from a different filing type than the one the date was read from,
which is what makes the check worth running: a date recovered from a proxy or a
supplement can be wrong in ways no amount of re-reading that same document will
reveal, but a fund still reporting holdings a year after its own conversion date
is a contradiction on the face of it.

This decides nothing. It ranks events by how far the predecessor kept reporting
past its recorded date so a human can adjudicate the outliers, and it counts the
filings it could not read, because a missed filing hides exactly the late report
the check is looking for.
"""
import sys

import pandas as pd

import nport_gate0 as G

OUT = G.HERE / "gate0_predecessor_continuity.csv"
TOLERANCE = 45  # a quarter-end stub report can legitimately land just after


def main():
    g = pd.read_csv(G.EVENT_OUT)
    cache, rows = {}, []
    for i, r in enumerate(g.itertuples(index=False), 1):
        eff = pd.Timestamp(r.effective_date)
        fils = cache.setdefault(r.pre_series_id, G.series_filings(r.pre_series_id))
        reps, unread = [], 0
        for f in fils:
            p = G.read_nport(f)
            if p and p["report_date"]:
                reps.append(p["report_date"])
            else:
                unread += 1
        if not reps:
            continue
        last = max(reps)
        rows.append({"event_id": r.event_id, "effective_date": r.effective_date,
                     "pre_series_id": r.pre_series_id,
                     "pre_series_name": r.pre_series_name,
                     "n_filings": len(fils), "n_unreadable": unread,
                     "last_pre_series_report": last,
                     "days_after_event": (pd.Timestamp(last) - eff).days})
        G.log.info("[%3d/%d] %s last=%s (%+d d)", i, len(g), r.event_id, last,
                   rows[-1]["days_after_event"])

    d = pd.DataFrame(rows).sort_values("days_after_event", ascending=False)
    d.to_csv(OUT, index=False)

    print("\n" + "=" * 76 + "\nPREDECESSOR REPORTING PAST ITS OWN CONVERSION DATE\n"
          + "=" * 76)
    bad = d[d.days_after_event > TOLERANCE]
    for r in bad.itertuples(index=False):
        print(f"  {r.days_after_event:>5d}d  {r.event_id}  {r.effective_date}  "
              f"{str(r.pre_series_name)[:42]:<42}  last={r.last_pre_series_report}")
    if bad.empty:
        print("  none")
    print(f"\n  {len(bad):>5d}/{len(d)}   report more than {TOLERANCE}d after the event")
    print(f"  {int((d.days_after_event <= 0).sum()):>5d}/{len(d)}   stop on or before it")
    unread = int(d.n_unreadable.sum())
    print(f"  {'ok  ' if not unread else 'WARN'}  unreadable filings: {unread} "
          f"across {int((d.n_unreadable > 0).sum())} events"
          + ("" if not unread else "  <- a hidden late report would be missed"))
    print(f"\n  written: {OUT.name}. This is a flag for adjudication, not a verdict.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
