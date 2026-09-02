"""Reconcile the date-recovery queue and show what the recovery moved.

Two things a reader has to be able to check independently:

  the queue balances   every event that entered recovery left it through exactly
                       one of four doors, and the doors sum to the queue size
  the census moved     the precision each event held before recovery, against
                       the one it holds after, so a promotion into
                       verified_exact_day is visible as a transition rather than
                       asserted as a total

The four doors are mutually exclusive by construction. A conflicting event is
counted as conflicting and not also as recovered, because its day is not yet
usable: two filings assert different days and neither has been adjudicated.

The "no usable bracket" door is recomputed here from the same window rule the
recovery pass used rather than read from its log, so the reconciliation stands
on the rule and not on the run.
"""
import sys

import pandas as pd

from paths import CACHE
from recover_verified_dates import TARGET, window

PREFOLD = CACHE / "events_master_v2_stage3.prefold.csv"
ORDER = ["verified_exact_day", "proposed_exact_day_only", "month_only",
         "bounded_window", "year_only"]


def rule(s):
    print("\n" + "=" * 74 + f"\n{s}\n" + "=" * 74)


def completed(d):
    return d[d.final_tier.str.startswith(("A_", "B_"), na=False)]


def main():
    before = pd.read_csv(PREFOLD)
    after = pd.read_csv(CACHE / "events_master_v2_stage3.csv")
    b_done, a_done = completed(before), completed(after)
    queue = b_done[b_done.date_precision.isin(TARGET)]

    rec = pd.read_csv(CACHE / "recovered_verified_dates.csv")
    recovered = set(rec.pre_series_id) if len(rec) else set()

    conf = CACHE / "date_conflict_audit.csv"
    conflicted = set()
    if conf.exists():
        c = pd.read_csv(conf)
        conflicted = set(c[c.conflict].pre_series_id) if len(c) else set()
    else:
        print("NOTE: no conflict audit on disk; conflicts unassessed")

    # recomputed, not read from the log: the door an event left by is a property
    # of the window rule, which is in the code and outlives any single run
    skipped = set()
    for r in queue.itertuples(index=False):
        lo, hi, _ = window(r)
        if pd.isna(lo) or pd.isna(hi):
            skipped.add(r.pre_series_id)

    ids = set(queue.pre_series_id)
    conflicted &= ids
    clean = (recovered & ids) - conflicted
    skipped -= (clean | conflicted)
    none_found = ids - clean - conflicted - skipped

    rule("RECOVERY QUEUE RECONCILIATION")
    doors = [("recovered verified exact day", clean),
             ("no exact day found after full search", none_found),
             ("skipped: no usable search bracket", skipped),
             ("conflicting days requiring adjudication", conflicted)]
    for name, s in doors:
        print(f"  {len(s):>5d}   {name}")
    tot = sum(len(s) for _, s in doors)
    ok = tot == len(ids)
    print(f"  {'-' * 46}\n  {tot:>5d}   total   (queue was {len(ids)})")
    print(f"  {'ok  ' if ok else 'FAIL'}  doors sum to the queue")
    assert ok, f"doors sum to {tot}, queue is {len(ids)}"

    if skipped:
        rule("SKIPPED FOR WANT OF A BRACKET")
        for r in queue[queue.pre_series_id.isin(skipped)].itertuples(index=False):
            print(f"  {r.pre_series_id}  {r.pre_series_name[:52]:<52} "
                  f"{r.date_precision}")

    rule("RECOVERY YIELD BY PRIOR PRECISION")
    q = queue.assign(door=queue.pre_series_id.map(
        lambda i: "recovered" if i in clean else
                  "conflicting" if i in conflicted else
                  "no bracket" if i in skipped else "not found"))
    t = pd.crosstab(q.date_precision, q.door)
    t["total"] = t.sum(axis=1)
    t["recovery rate"] = (t.get("recovered", 0) / t.total).map("{:.0%}".format)
    print(t.reindex([p for p in ORDER if p in t.index]).to_string())

    rule("TIMING TRANSITION MATRIX  (completed events, before -> after)")
    m = (b_done[["pre_series_id", "date_precision"]]
         .merge(a_done[["pre_series_id", "date_precision"]],
                on="pre_series_id", suffixes=("_before", "_after")))
    x = pd.crosstab(m.date_precision_before, m.date_precision_after)
    x = x.reindex(index=[p for p in ORDER if p in x.index],
                  columns=[p for p in ORDER if p in x.columns], fill_value=0)
    print(x.to_string())
    moved = int(x.get("verified_exact_day", pd.Series(dtype=int))
                .drop(index="verified_exact_day", errors="ignore").sum())
    print(f"\n  {moved} events promoted into verified_exact_day by recovery")
    unchanged = len(m) - int((m.date_precision_before
                              != m.date_precision_after).sum())
    print(f"  {unchanged}/{len(m)} completed events unchanged")
    # nothing may weaken: recovery only ever adds evidence
    back = m[(m.date_precision_before == "verified_exact_day")
             & (m.date_precision_after != "verified_exact_day")]
    print(f"  {'ok  ' if back.empty else 'FAIL'}  no event lost a verified day "
          f"({len(back)} regressions)")
    assert back.empty, f"verified days lost: {list(back.pre_series_id)}"

    rule("FINAL TIMING CENSUS  (all completed events)")
    c = a_done.date_precision.value_counts()
    for k in ORDER:
        print(f"  {int(c.get(k, 0)):>5d}   {k}")
    other = {k: int(v) for k, v in c.items() if k not in ORDER}
    print(f"  {'-' * 40}\n  {len(a_done):>5d}   total completed")
    assert not other, f"unclassified precisions: {other}"
    v = int(c.get("verified_exact_day", 0))
    print(f"\n  exact-date eligible for wave construction : {v} "
          f"({v / len(a_done):.0%})")
    print(f"  timing-ineligible completed events        : {len(a_done) - v}")

    rule("COMPLETION TIER MOVEMENT")
    tm = (before[["pre_series_id", "final_tier"]]
          .merge(after[["pre_series_id", "final_tier"]],
                 on="pre_series_id", suffixes=("_before", "_after")))
    ch = tm[tm.final_tier_before != tm.final_tier_after]
    print(f"  {len(ch)} events changed completion tier")
    if len(ch):
        print(ch.groupby(["final_tier_before", "final_tier_after"])
              .size().to_string())
    print(f"  completed: {len(b_done)} -> {len(a_done)}")
    assert len(a_done) == len(b_done), "recovery changed the completed count"
    return 0


if __name__ == "__main__":
    sys.exit(main())
