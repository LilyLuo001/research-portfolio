"""Test whether the predecessor series stopped reporting while its registrant did not.

A trust files one N-CEN per fiscal-year-end group, and its series do not all share
a fiscal year end. So "the series is absent from the registrant's next N-CEN" is
not evidence of anything: the series may simply belong to a different FYE group.

The test that does carry information is the anniversary one. If a series last
reported for period P, and the registrant filed an N-CEN for period P+1yr (the
same fiscal year end, so the same reporting group) and the series is not in it,
the registrant has stopped reporting a fund it would otherwise have had to
report. That is the registrant speaking about this series.

The channel establishes *that* the fund stopped existing, not *when*: the bracket
it produces is (last reported period, anniversary period], up to a year wide. It
is therefore completion evidence, never date evidence.
"""
import pickle
import sys

import pandas as pd

from paths import CACHE as HERE  # data lives outside the repo; see paths.py
# a fiscal year end recurs on the same month; allow drift for 52/53-week years
ANNIV_TOL = pd.Timedelta(days=45)


def load_fri():
    cached = HERE / "fri_flat.pkl"
    if cached.exists():
        fri = pd.read_pickle(cached)
    else:
        with open(HERE / "ncen_tables.pkl", "rb") as fh:
            t = pickle.load(fh)
        s = t["SUBMISSION"]
        sub = s.assign(
            period_end=pd.to_datetime(s.REPORT_ENDING_PERIOD, errors="coerce"),
            filing_date=pd.to_datetime(s.FILING_DATE, errors="coerce"))
        fri = t["FUND_REPORTED_INFO"].merge(
            sub[["ACCESSION_NUMBER", "CIK", "period_end", "filing_date"]],
            on="ACCESSION_NUMBER", how="left")
        fri = fri[fri.SERIES_ID.str.startswith("S0", na=False)]
        fri.to_pickle(cached)
    fri["cik"] = fri.CIK.astype(str).str.lstrip("0").astype(int)
    return fri


def main():
    fri = load_fri()
    # stage2, not stage3: stage3 is built downstream of this file, so reading it
    # here would make the two scripts each other's input
    ev = pd.read_csv(HERE / "events_master_v2_stage2.csv")

    cik_per = {c: sorted(set(g.dropna())) for c, g in fri.groupby("cik").period_end}
    ser_per = {s: sorted(set(g.dropna()))
               for s, g in fri.groupby("SERIES_ID").period_end}

    rows = []
    for r in ev.itertuples(index=False):
        sp = ser_per.get(r.pre_series_id, [])
        last = max(sp) if sp else pd.NaT
        anniv = pd.NaT
        if sp:
            want = last + pd.Timedelta(days=365)
            near = [p for p in cik_per.get(int(r.pre_cik), [])
                    if abs(p - want) <= ANNIV_TOL]
            if near:
                anniv = min(near, key=lambda p: abs(p - want))
        # the registrant filed the predecessor's own next annual report and the
        # predecessor was not in it
        ceased = pd.notna(anniv)
        lo = max([d for d in (pd.to_datetime(r.n14_first_filed), last)
                  if pd.notna(d)], default=pd.NaT)
        rows.append({
            "pre_last_period": last,
            "pre_anniv_period": anniv,
            "pre_ceased_at_anniversary": ceased,
            "cease_window_lo": lo,
            "cease_window_hi": anniv,
            "cease_window_same_year": bool(
                ceased and pd.notna(lo) and lo.year == anniv.year),
        })

    d = pd.DataFrame(rows)
    out = pd.concat([ev.reset_index(drop=True), d], axis=1)
    out.to_csv(HERE / "ncen_cease_signal.csv", index=False)

    print(f"events                                : {len(out):,d}")
    print(f"predecessor ceased at its anniversary : "
          f"{int(out.pre_ceased_at_anniversary.sum()):,d}")
    print(f"  of those, window inside one year    : "
          f"{int(out.cease_window_same_year.sum()):,d}")

    # the channel is only worth using if it separates completions from
    # non-completions, so score it against whatever the last tiering decided
    prev = HERE / "events_master_v2_stage3.csv"
    if prev.exists():
        p = pd.read_csv(prev)[["pre_series_id", "post_series_id", "final_tier"]]
        j = out.merge(p, on=["pre_series_id", "post_series_id"], how="left")
        done = j[j.final_tier.str.startswith(("A_", "B_"), na=False)]
        nf = j[j.final_tier.isin(["announced_future", "cancelled_or_not_completed"])]
        print("\nseparation against the previous tiering:")
        print(f"  fires on completed        : "
              f"{int(done.pre_ceased_at_anniversary.sum())}/{len(done)}")
        print(f"  fires on future/cancelled : "
              f"{int(nf.pre_ceased_at_anniversary.sum())}/{len(nf)}")
        u = j[j.final_tier == "unresolved"]
        print(f"  fires on unresolved       : "
              f"{int(u.pre_ceased_at_anniversary.sum())}/{len(u)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
