"""Check whether any recovered closing day is contradicted by another filing.

recover_verified_dates.py stops at an event's first attributable hit, which is
the right rule for finding a day but says nothing about whether a second filing
in the same bracket asserts a different one. Without that check the recovery
census cannot honestly report a "conflicting dates" category: it would be zero
by construction rather than by evidence.

So this re-reads each recovered event's full candidate set, keeps every
attributable day instead of the first, and reports the events where more than
one distinct day survives. Only recovered events can conflict; an event that
found no day has nothing to contradict.

Adjudication is deliberately not automated. A conflict is reported with every
competing day and the sentence that asserts it, because choosing between two
filings is a judgement about which document speaks to the closing rather than
something a rule can settle.

Run before folding recovered days into stage3: the bracket is derived from the
precision the recovery pass saw, which the fold overwrites.
"""
import sys

import pandas as pd

from build_completion_evidence import names_match
from paths import CACHE
from recover_verified_dates import MAX_PER_EVENT, FORMS, fetch, window
from resolve_unresolved import statements


def main():
    rec = pd.read_csv(CACHE / "recovered_verified_dates.csv")
    ev = pd.read_csv(CACHE / "events_master_v2_stage3.csv")
    if not len(rec):
        print("no recovered days to audit")
        return 0

    # the bracket has to be the one the recovery pass used, so the precision
    # comes from the recovery record rather than from stage3's current value
    q = ev.merge(rec[["pre_series_id", "prior_precision", "verified_day", "acc"]],
                 on="pre_series_id", how="inner")
    q["final_precision"] = q.prior_precision

    sub = pd.read_parquet(CACHE / "submissions_flat.parquet")
    sub["filed"] = pd.to_datetime(sub.filed, errors="coerce")
    sub = sub[sub.form.isin(FORMS)].drop_duplicates(["cik", "acc"])

    rows = []
    for n, r in enumerate(q.itertuples(index=False), 1):
        lo, hi, expected = window(r)
        ciks = {int(c) for c in (r.pre_cik, r.post_cik) if pd.notna(c)}
        g = sub[sub.cik.isin(ciks) & (sub.filed >= lo - pd.Timedelta(days=30))
                & (sub.filed <= hi + pd.Timedelta(days=400))].copy()
        g["d"] = (g.filed - expected).abs()
        g = g.sort_values("d").head(MAX_PER_EVENT)

        found = {}
        for x in g.itertuples(index=False):
            p = fetch(x.acc, x.cik, x.doc)
            if p is None:
                continue
            for d, nm, ctx in statements(p):
                if not (lo <= d <= hi):
                    continue
                if not names_match(ctx, r.pre_series_name, r.post_series_name):
                    continue
                found.setdefault(d.strftime("%Y-%m-%d"),
                                 {"acc": x.acc, "form": x.form, "pattern": nm,
                                  "context": ctx[:300]})

        days = sorted(found)
        span = ((pd.to_datetime(days[-1]) - pd.to_datetime(days[0])).days
                if len(days) > 1 else 0)
        rows.append({
            "pre_series_id": r.pre_series_id,
            "pre_series_name": r.pre_series_name,
            "prior_precision": r.prior_precision,
            "accepted_day": r.verified_day,
            "accepted_from_accession": r.acc,
            "distinct_days_found": len(days),
            "all_days": ";".join(days),
            "day_span_days": span,
            "competing_accessions": ";".join(found[d]["acc"] for d in days),
            "competing_evidence": " || ".join(
                f"{d} [{found[d]['form']} {found[d]['acc']}] {found[d]['context']}"
                for d in days),
            "conflict": len(days) > 1,
        })
        mark = "CONFLICT" if len(days) > 1 else "ok      "
        print(f"  [{n}/{len(q)}] {mark} {r.pre_series_name[:40]:<40} "
              f"{len(days)} day(s): {';'.join(days)}", flush=True)

    d = pd.DataFrame(rows)
    out = CACHE / "date_conflict_audit.csv"
    d.to_csv(out, index=False)

    c = d[d.conflict]
    print("\n" + "=" * 74)
    print(f"  {len(d) - len(c)}/{len(d)} recovered days uncontradicted; "
          f"{len(c)} conflicting")
    for r in c.itertuples(index=False):
        print(f"\n  {r.pre_series_name} ({r.pre_series_id})")
        print(f"    accepted {r.accepted_day}; filings assert {r.all_days} "
              f"(span {r.day_span_days}d)")
        print(f"    {r.competing_evidence[:600]}")
    print(f"\n  written: {out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
