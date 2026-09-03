"""Prove the universe partitions: every pair in exactly one status, every completion dated.

Two censuses are printed and both are asserted to sum to their totals. The point
is not presentation. Earlier reporting quoted year counts and precision counts
that did not add up to the universe, because rows whose year could not be
established were quietly absent from one table and rows dated from a proposal
were absent from the other. A bucket that is easy to forget is exactly the bucket
that hides an unresolved case, so the arithmetic is checked rather than trusted.

Date-precision vocabulary, weakest claim last:

  verified_exact_day       a filing states the day the transaction closed
  proposed_exact_day_only  the proxy's proposed day, which has passed, with the
                           successor now reporting. Completion is established,
                           the day is not: reorganizations slip, and no filing
                           here says this one did not. It may not build a wave.
  month_only               the registrant's N-CEN termination month
  year_only                bracketed between two N-CEN periods inside one year
  bounded_window           bracketed, but the bracket crosses a year boundary
  unknown                  no completion, so nothing to date

Only verified_exact_day licenses wave construction. The line between it and
proposed_exact_day_only is the line between a date SEC filings assert and a date
this pipeline inferred, and collapsing the two would put inferred dates into the
event-time axis of the study.
"""
import sys

import pandas as pd

from paths import CACHE as HERE  # data lives outside the repo; see paths.py
CUTOFF = pd.Timestamp("2026-08-29")

PRECISION = ["verified_exact_day", "proposed_exact_day_only", "month_only", "year_only",
             "bounded_window", "unknown"]
STATUS = ["A_explicit_completion", "B_structural_completion", "announced_future",
          "cancelled_or_not_completed", "unresolved"]


def rule(s):
    print("\n" + "=" * 76)
    print(s)
    print("=" * 76)


def advisers(done):
    """Adviser name per predecessor series, from N-CEN ADVISER.

    The successor registrant CIK is a poor proxy for sponsor: one trust can host
    funds from unrelated advisers, and one adviser can spread funds across
    several trusts. ADVISER keys on FUND_ID, whose tail is the series id, so the
    join needs no separate crosswalk.
    """
    import pickle
    p = HERE / "ncen_tables.pkl"
    if not p.exists():
        return None
    with open(p, "rb") as fh:
        a = pickle.load(fh).get("ADVISER")
    if a is None:
        return None
    a = a[a.ADVISER_TYPE.eq("Advisor") & a.FUND_ID.notna()].copy()
    a["sid"] = a.FUND_ID.str.rsplit("_", n=1).str[-1]
    m = a.drop_duplicates("sid", keep="last").set_index("sid").ADVISER_NAME
    return done.pre_series_id.map(m)


def main():
    ev = pd.read_csv(HERE / "events_master_v2_stage3.csv")
    n = len(ev)
    done = ev[ev.final_tier.str.startswith(("A_", "B_"), na=False)]

    rule(f"STATUS CENSUS  (all {n} structural MF->ETF pairs, mutually exclusive)")
    vc = ev.final_tier.value_counts()
    for k in STATUS:
        print(f"  {int(vc.get(k, 0)):>4d}   {k}")
    print(f"  {'-' * 60}")
    print(f"  {int(vc.reindex(STATUS).fillna(0).sum()):>4d}   total")
    assert set(ev.final_tier) <= set(STATUS), set(ev.final_tier) - set(STATUS)
    assert int(vc.reindex(STATUS).fillna(0).sum()) == n

    rule(f"YEAR CENSUS  (the {len(done)} verified-completed pairs, mutually exclusive)")
    y = done.final_year
    for yy in sorted(y.dropna().unique()):
        print(f"  {int((y == yy).sum()):>4d}   {int(yy)}")
    amb = int(y.isna().sum())
    print(f"  {amb:>4d}   year not established (bracket crosses a year boundary)")
    print(f"  {'-' * 60}")
    print(f"  {int(y.notna().sum()) + amb:>4d}   total verified completed")
    assert int(y.notna().sum()) + amb == len(done)

    rule(f"DATE-PRECISION CENSUS  (all {n} pairs, mutually exclusive)")
    print(f"  {'':<22}{'completed':>10}{'not completed':>15}{'total':>8}")
    for k in PRECISION:
        a = int((done.final_precision == k).sum())
        b = int((ev.final_precision == k).sum()) - a
        print(f"  {k:<22}{a:>10d}{b:>15d}{a + b:>8d}")
    print(f"  {'-' * 55}")
    print(f"  {'total':<22}{len(done):>10d}{n - len(done):>15d}{n:>8d}")
    assert set(ev.final_precision) <= set(PRECISION)
    assert int(ev.final_precision.isin(PRECISION).sum()) == n
    # every completed pair must carry a date claim, and no other pair may
    assert not (done.final_precision == "unknown").any()
    assert (ev[~ev.index.isin(done.index)].final_precision == "unknown").all()

    rule("DATE COVERAGE OF THE VERIFIED-COMPLETED UNIVERSE")
    ver = int((done.final_precision == "verified_exact_day").sum())
    prop = int((done.final_precision == "proposed_exact_day_only").sum())
    print(f"  {ver:>4d}   verified_exact_day       ({ver / len(done):.0%})  "
          f"<- the only class that may build a wave")
    print(f"  {prop:>4d}   proposed_exact_day_only  (completed; day not verified)")
    print(f"  {int((done.final_precision == 'month_only').sum()):>4d}   month_only")
    print(f"  {int((done.final_precision == 'year_only').sum()):>4d}   year_only")
    print(f"  {int((done.final_precision == 'bounded_window').sum()):>4d}   bounded_window")
    print(f"  {len(done) - ver:>4d}   still owed a verified day")
    print(f"  {int(done.final_year.notna().sum()):>4d}   "
          f"year established  ({done.final_year.notna().mean():.0%})")

    rule("WAVE GEOMETRY ON VERIFIED DATES ONLY")
    exact = done[done.final_precision == "verified_exact_day"].copy()
    exact["d"] = pd.to_datetime(exact.final_verified_day, errors="coerce")
    waves = exact.groupby("d").size().sort_values(ascending=False)
    print(f"  {len(done):>4d}   completed predecessor mutual funds")
    print(f"  {done.post_series_id.nunique():>4d}   successor ETFs")
    print(f"  {ver:>4d}   with a VERIFIED exact effective date")
    print(f"  {len(waves):>4d}   distinct verified conversion dates (waves)")
    print(f"  {done.post_cik.nunique():>4d}   successor registrants (CIK)")
    print(f"  {done.pre_cik.nunique():>4d}   predecessor registrants (CIK)")
    if len(waves):
        print(f"\n  funds per wave: median {waves.median():.0f}, "
              f"max {waves.max()}, singletons {(waves == 1).sum()}")
        print(f"  largest wave share : {waves.max() / waves.sum():.1%} "
              f"({waves.index[0]:%Y-%m-%d}, {waves.max()} funds)")
    spon = done.post_cik.value_counts()
    print(f"  largest registrant share: {spon.max() / spon.sum():.1%} "
          f"({spon.max()} of {len(done)} funds in one successor registrant)")

    adv = advisers(done)
    if adv is not None and len(adv):
        print(f"\n  {adv.nunique():>4d}   distinct advisers "
              f"({int(adv.notna().sum())} of {len(done)} funds mapped)")
        v = adv.value_counts()
        print(f"  largest adviser share  : {v.max() / v.sum():.1%} "
              f"({v.max()} funds, {v.index[0][:46]})")
        print(f"  top 3 advisers         : {v.head(3).sum() / v.sum():.1%}")

    print(f"\n  PROVISIONAL. {len(done) - ver} completed funds still lack a verified")
    print("  day, so this wave set is a lower bound on wave count and an upper")
    print("  bound on largest-wave share. Not frozen for P1 until date recovery ends.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
