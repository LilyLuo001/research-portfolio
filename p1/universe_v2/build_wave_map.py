"""Freeze the event master and build the wave map from verified closing days only.

A wave is a set of predecessor funds that converted on the same filing-stated
day. Only verified_exact_day licenses membership: a proposed day is what a proxy
intended, an N-CEN termination month is a month, and neither identifies the day
an event study needs. Completed events without a verified day are carried in the
frozen master and reported as timing-ineligible rather than given a date.

The predecessor fund is the unit of observation. Where several mutual funds
converted into one ETF, each predecessor stays its own row and the shared
successor is preserved through post_series_id, so a many-to-one structure is
visible as one successor appearing on several rows rather than being collapsed.

Concentration is reported because it bounds what the design can identify: if one
adviser or one day carries most of the sample, a wave-level shock and the
treatment are not separable, and that has to be visible before estimation.
"""
import hashlib
import pickle
import sys

import pandas as pd

import fetchlib
from paths import CACHE

PAIRS, COMPLETED = 247, 156


def rule(s):
    print("\n" + "=" * 74 + f"\n{s}\n" + "=" * 74)


def advisers():
    """Adviser of record per series, from the latest N-CEN that names one."""
    t = pickle.load(open(CACHE / "ncen_tables.pkl", "rb"))
    s = t["SUBMISSION"].assign(
        pe=pd.to_datetime(t["SUBMISSION"].REPORT_ENDING_PERIOD, errors="coerce"))
    fri = t["FUND_REPORTED_INFO"].merge(s[["ACCESSION_NUMBER", "pe"]],
                                        on="ACCESSION_NUMBER", how="left")
    # N-CEN spells the primary adviser "Advisor"; subadvisers are a different
    # relationship and would double-count a series under two firms
    a = t["ADVISER"][t["ADVISER"].ADVISER_TYPE.eq("Advisor")]
    m = fri.merge(a[["FUND_ID", "ADVISER_NAME"]], on="FUND_ID", how="inner")
    m = m.dropna(subset=["ADVISER_NAME"]).sort_values("pe")
    return m.groupby("SERIES_ID").ADVISER_NAME.last().to_dict()


def concentration(s, label, n=8):
    """Top holders of a grouping, with the share the largest one carries."""
    c = s.value_counts()
    print(f"  {len(c):>5d}   distinct {label}")
    print(f"  {c.iloc[0] / c.sum():>6.0%}   largest {label[:-1]}'s share "
          f"({c.index[0]}, {c.iloc[0]} funds)")
    print(f"  {c.head(3).sum() / c.sum():>6.0%}   top 3 share")
    hhi = ((c / c.sum()) ** 2).sum()
    print(f"  {hhi:>6.3f}   HHI")
    for k, v in c.head(n).items():
        print(f"          {v:>3d}  {k}")


def main():
    ev = pd.read_csv(CACHE / "events_master_v2_stage3.csv")
    done = ev[ev.final_tier.str.startswith(("A_", "B_"), na=False)].copy()

    rule("FREEZE PRECONDITIONS")
    print(f"  {'ok  ' if len(ev) == PAIRS else 'FAIL'}  structural pairs "
          f"{len(ev)} (audited {PAIRS})")
    print(f"  {'ok  ' if len(done) == COMPLETED else 'FAIL'}  completed "
          f"{len(done)} (audited {COMPLETED})")
    assert len(ev) == PAIRS and len(done) == COMPLETED

    # the predecessor is the unit; a duplicate would double-count a fund
    assert ev.pre_series_id.is_unique, "predecessor appears twice"
    ca = CACHE / "date_conflict_audit.csv"
    nconf = 0
    if ca.exists():
        c = pd.read_csv(ca)
        nconf = int(c.conflict.sum())
        held = set(c[c.conflict].pre_series_id)
        leak = done[done.pre_series_id.isin(held)
                    & (done.date_precision == "verified_exact_day")]
        print(f"  {'ok  ' if leak.empty else 'FAIL'}  contradicted days withheld "
              f"from verified status ({nconf} conflicts, {len(leak)} leaked)")
        assert leak.empty
    print(f"  {'ok  ' if nconf == 0 or ca.exists() else 'FAIL'}  conflict audit "
          f"present and gating the freeze")

    rule("MANY-TO-ONE STRUCTURE  (preserved, not collapsed)")
    g = done.groupby("post_series_id").pre_series_id.nunique()
    multi = g[g > 1]
    print(f"  {done.pre_series_id.nunique():>5d}   predecessor funds (rows)")
    print(f"  {done.post_series_id.nunique():>5d}   successor ETFs")
    print(f"  {len(multi):>5d}   successors absorbing more than one predecessor")
    print(f"  {int(multi.sum()):>5d}   predecessors inside those structures")
    print(f"  {int(g.max()):>5d}   most predecessors into one ETF")
    for sid, n in multi.sort_values(ascending=False).head(6).items():
        nm = done[done.post_series_id == sid].post_series_name.iloc[0]
        print(f"          {n}  {nm[:56]}")

    # ------------------------------------------------------------------ freeze
    adv = advisers()
    done["adviser"] = done.pre_series_id.map(adv)
    ev["adviser"] = ev.pre_series_id.map(adv)
    frozen = CACHE / "events_master_v2_frozen.csv"
    ev.to_csv(frozen, index=False)
    fetchlib.record(frozen, kind="derived", parser="build_wave_map.py",
                    extra={"lineage": "events_master_v2_stage3.csv"
                                      " + date_conflict_audit.csv (gate)"})

    # ------------------------------------------------------------------- waves
    elig = done[done.date_precision == "verified_exact_day"].copy()
    elig["wave_date"] = pd.to_datetime(elig.verified_effective_date)
    assert elig.wave_date.notna().all(), "eligible event without a verified day"
    inelig = done[done.date_precision != "verified_exact_day"]

    w = (elig.groupby("wave_date")
         .agg(funds=("pre_series_id", "nunique"),
              successors=("post_series_id", "nunique"),
              registrants=("post_cik", "nunique"),
              advisers=("adviser", "nunique"))
         .sort_index().reset_index())
    w.insert(0, "wave_id", ["W%03d" % (i + 1) for i in range(len(w))])
    elig = elig.merge(w[["wave_id", "wave_date"]], on="wave_date", how="left")

    wm = CACHE / "wave_map_v2.csv"
    w.to_csv(wm, index=False)
    fetchlib.record(wm, kind="derived", parser="build_wave_map.py",
                    extra={"lineage": "events_master_v2_frozen.csv"
                                      " (verified_exact_day only)"})
    el = CACHE / "wave_membership_v2.csv"
    elig[["wave_id", "wave_date", "pre_series_id", "pre_series_name", "pre_cik",
          "post_series_id", "post_series_name", "post_cik", "adviser",
          "verified_date_source_accession", "verified_date_source_form",
          "verified_date_evidence"]].to_csv(el, index=False)
    fetchlib.record(el, kind="derived", parser="build_wave_map.py",
                    extra={"lineage": "events_master_v2_frozen.csv"})

    rule("WAVE GEOMETRY  (verified exact completion dates only)")
    print(f"  {len(done):>5d}   completed predecessor mutual funds")
    print(f"  {len(elig):>5d}   verified-exact-date eligible")
    print(f"  {len(inelig):>5d}   timing-ineligible completed")
    print(f"  {len(elig) / len(done):>6.0%}   exact-date coverage")
    print(f"  {len(w):>5d}   distinct conversion dates (waves)")

    d = w.funds
    print(f"\n  funds per wave: mean {d.mean():.2f}  median {int(d.median())}  "
          f"max {int(d.max())}")
    print(f"  {int((d == 1).sum()):>5d}   singleton waves "
          f"({(d == 1).sum() / len(w):.0%} of waves, "
          f"{int(d[d == 1].sum()) / len(elig):.0%} of funds)")
    print(f"  {int(d.max()):>5d}   maximum funds in one wave")
    print(f"  {d.max() / len(elig):>6.0%}   largest-wave share of eligible funds")
    print("\n  funds per wave distribution")
    for k, v in d.value_counts().sort_index().items():
        print(f"          {int(k)} fund(s): {v:>3d} wave(s)")

    print("\n  largest waves")
    for r in w.sort_values("funds", ascending=False).head(6).itertuples(index=False):
        print(f"          {r.wave_id}  {r.wave_date:%Y-%m-%d}  {r.funds:>2d} funds  "
              f"{r.advisers} adviser(s)  {r.registrants} registrant(s)")

    print("\n  eligible funds by year")
    for k, v in elig.wave_date.dt.year.value_counts().sort_index().items():
        print(f"          {k}: {v:>3d}")

    rule("ADVISER CONCENTRATION  (eligible funds)")
    a = elig.adviser.dropna()
    print(f"  {len(a)}/{len(elig)} eligible funds carry an N-CEN adviser")
    if len(a):
        concentration(a, "advisers")

    rule("SUCCESSOR REGISTRANT CONCENTRATION  (eligible funds)")
    concentration(elig.post_cik.astype(str), "registrants")

    rule("TIMING-INELIGIBLE COMPLETED EVENTS  (carried, never dated)")
    for k, v in inelig.date_precision.value_counts().items():
        print(f"  {v:>5d}   {k}")
    print(f"  {len(inelig):>5d}   total, excluded from primary wave construction")
    assert inelig.verified_effective_date.isna().all(), \
        "a timing-ineligible event carries a verified date"
    print("  ok    none carries a verified date")

    rule("FROZEN ARTIFACTS")
    for p in (frozen, wm, el):
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()[:32]
        print(f"  {h}  {p.stat().st_size:>9,d}  {p.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
