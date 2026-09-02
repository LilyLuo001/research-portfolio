"""Find a filing-stated closing day for every completion that does not have one.

115 of the 154 completed pairs are known to have closed but carry no day that a
filing actually asserts: 87 have only the registrant's N-CEN termination month,
20 have only the day their proxy proposed, 8 have only a bracket. Wave
construction needs asserted days, so each of these is searched for one.

What makes this search well-posed, and different from the earlier hunt for
unresolved completions, is that the answer is already bracketed. A month_only
event has the registrant's own statement that the series terminated in month M,
so a candidate day is accepted only if it falls in M -- two independent channels
agreeing on the same transaction. A proposed_exact_day_only event is bracketed by
the proposed day, generously, because reorganizations slip forward but rarely
move earlier. A window event is bracketed by the N-CEN periods that surround it.

Documents are read in ascending distance from the expected close, and the event
stops at its first attributable hit. Completion language appears in a supplement
filed days after closing and again in an annual report filed months later, so the
window extends well past the close; ordering, not truncation, is what keeps the
cost down.
"""
import sys

import pandas as pd

import fetchlib
import parse_escalation as PE
from build_completion_evidence import names_match
from paths import CACHE, ESCALATION
from resolve_unresolved import statements

FORMS = ["497", "497K", "485BPOS", "N-CSR", "N-CSRS", "N-14/A", "N-1A", "N-30D"]
MAX_PER_EVENT = 90
TARGET = ["month_only", "proposed_exact_day_only", "year_only", "bounded_window"]


def window(r):
    """(accept_lo, accept_hi, expected) for one event, from its existing evidence."""
    if r.final_precision == "month_only":
        m = pd.to_datetime(r.term_month)
        # the registrant reported the month; a stated day must land inside it,
        # with a few days' grace for filings that date the deregistration rather
        # than the closing
        return (m - pd.Timedelta(days=5),
                m + pd.offsets.MonthEnd(1) + pd.Timedelta(days=5), m + pd.Timedelta(days=14))
    if r.final_precision == "proposed_exact_day_only":
        p = pd.to_datetime(r.final_proposed_day)
        return p - pd.Timedelta(days=150), p + pd.Timedelta(days=300), p
    lo, hi = pd.to_datetime(r.cease_lo), pd.to_datetime(r.cease_hi)
    return lo, hi, lo + (hi - lo) / 2


def fetch(acc, cik, doc):
    for d in (ESCALATION, CACHE / "sup497"):
        p = d / f"{acc}.html"
        if p.exists() and p.stat().st_size:
            return p
    url = (f"https://www.sec.gov/Archives/edgar/data/{cik}/"
           f"{acc.replace('-', '')}/{doc}")
    return fetchlib.get(url, ESCALATION / f"{acc}.html",
                        accession=acc, kind="completion_doc")


def main():
    ev = pd.read_csv(CACHE / "events_master_v2_stage3.csv")
    done = ev[ev.final_tier.str.startswith(("A_", "B_"), na=False)]
    open_ = done[done.final_precision.isin(TARGET)]
    print(f"completed pairs owed a verified day: {len(open_)}")
    print(open_.final_precision.value_counts().to_string(), flush=True)

    sub = pd.read_parquet(CACHE / "submissions_flat.parquet")
    sub["filed"] = pd.to_datetime(sub.filed, errors="coerce")
    sub = sub[sub.form.isin(FORMS)].drop_duplicates(["cik", "acc"])

    rows = []
    for n, r in enumerate(open_.itertuples(index=False), 1):
        lo, hi, expected = window(r)
        if pd.isna(lo) or pd.isna(hi):
            continue
        ciks = {int(c) for c in (r.pre_cik, r.post_cik) if pd.notna(c)}
        # read from just before the window to well after it: the statement is
        # made after the fact, sometimes only in the next annual report
        g = sub[sub.cik.isin(ciks) & (sub.filed >= lo - pd.Timedelta(days=30))
                & (sub.filed <= hi + pd.Timedelta(days=400))].copy()
        g["d"] = (g.filed - expected).abs()
        g = g.sort_values("d").head(MAX_PER_EVENT)

        hit = None
        for k, x in enumerate(g.itertuples(index=False), 1):
            p = fetch(x.acc, x.cik, x.doc)
            if p is None:
                continue
            for d, nm, ctx in statements(p):
                if not (lo <= d <= hi):
                    continue
                if not names_match(ctx, r.pre_series_name, r.post_series_name):
                    continue
                hit = {"pre_series_id": r.pre_series_id,
                       "pre_series_name": r.pre_series_name,
                       "prior_precision": r.final_precision,
                       "prior_date": r.final_effective_date,
                       "verified_day": d.strftime("%Y-%m-%d"),
                       "acc": x.acc, "form": x.form, "pattern": nm,
                       "context": ctx[:400], "docs_read": k}
                break
            if hit:
                break
        if hit:
            rows.append(hit)
            print(f"  [{n}/{len(open_)}] {r.pre_series_name[:42]:<42} "
                  f"{r.final_precision[:12]:<12} -> {hit['verified_day']} "
                  f"({hit['docs_read']} docs)", flush=True)
        else:
            print(f"  [{n}/{len(open_)}] {r.pre_series_name[:42]:<42} "
                  f"{r.final_precision[:12]:<12} -> none in {len(g)} docs", flush=True)

    d = pd.DataFrame(rows)
    out = CACHE / "recovered_verified_dates.csv"
    d.to_csv(out, index=False)
    fetchlib.record(out, kind="derived", parser="recover_verified_dates.py")

    print(f"\nrecovered: {len(d)}/{len(open_)}")
    if len(d):
        # a recovered day that lands inside the registrant's own reported month
        # is two channels agreeing, which is the strongest corroboration available
        mo = d[d.prior_precision == "month_only"]
        if len(mo):
            same = (pd.to_datetime(mo.verified_day).dt.to_period("M")
                    == pd.to_datetime(mo.prior_date).dt.to_period("M")).mean()
            print(f"  month_only recoveries landing in the reported month: {same:.0%}")
        print(d.prior_precision.value_counts().to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
