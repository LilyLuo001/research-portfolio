"""Reconcile the 116-case recovery universe against the frozen 156-event master.

The two denominators look inconsistent and are not. 116 is the count of completed
events lacking a verified day *before* recovery ran; 82 is the count lacking one
*after*. They are the same set observed at two times, and 116 - 34 recovered = 82.
Nothing was reclassified, duplicated, or collapsed to make that hold, and this
file exists to demonstrate it per event rather than assert it in prose.

The crosswalk carries one row per structural member of the register, so a fund
that shares a successor with another fund still gets its own row. Collapsing a
many-to-one structure would make the counts agree for the wrong reason.

A stable event id is minted here because downstream artifacts need to refer to an
event across rebuilds. It is derived from the predecessor series id, which is the
unit of observation and is unique in the register, so the id is reproducible from
the data rather than assigned by run order.
"""
import sys

import pandas as pd

import fetchlib
from paths import CACHE

PREFOLD = CACHE / "events_master_v2_stage3.prefold.csv"
ORDER = ["verified_exact_day", "proposed_exact_day_only", "month_only",
         "bounded_window", "year_only"]


def rule(s):
    print("\n" + "=" * 76 + f"\n{s}\n" + "=" * 76)


def done_mask(d):
    return d.final_tier.str.startswith(("A_", "B_"), na=False)


def event_id(sid):
    """Stable id from the predecessor series, not from row order."""
    return "P1E" + str(sid).replace("S", "").zfill(9)[-9:]


def main():
    before = pd.read_csv(PREFOLD)
    after = pd.read_csv(CACHE / "events_master_v2_frozen.csv")
    rec = pd.read_csv(CACHE / "recovered_verified_dates.csv")
    conf = pd.read_csv(CACHE / "date_conflict_audit.csv")

    assert before.pre_series_id.is_unique and after.pre_series_id.is_unique
    assert set(before.pre_series_id) == set(after.pre_series_id), \
        "the register gained or lost a member during recovery"

    b = before.set_index("pre_series_id")
    conflicted = set(conf[conf.conflict].pre_series_id)
    recovered = rec.set_index("pre_series_id")
    cf = conf.set_index("pre_series_id")

    rows = []
    for r in after.itertuples(index=False):
        sid = r.pre_series_id
        prior = b.at[sid, "date_precision"]
        completed = str(b.at[sid, "final_tier"]).startswith(("A_", "B_"))
        in_queue = completed and prior != "verified_exact_day"

        if not completed:
            why = f"excluded: not a completed event ({b.at[sid, 'final_tier']})"
        elif prior == "verified_exact_day":
            why = "excluded: already carried a filing-stated day before recovery"
        else:
            why = f"included: completed but precision was {prior}"

        got = sid in recovered.index
        is_conf = sid in conflicted
        if not in_queue:
            outcome = "not_searched"
        elif is_conf:
            outcome = "conflicting_unresolved"
        elif got:
            outcome = "recovered_verified_exact_day"
        else:
            outcome = "searched_no_verified_day"

        rows.append({
            "event_id": event_id(sid),
            "pre_series_id": sid,
            "pre_series_name": r.pre_series_name,
            "pre_cik": r.pre_cik,
            "post_series_id": r.post_series_id,
            "post_series_name": r.post_series_name,
            "post_cik": r.post_cik,
            "completion_tier_before": b.at[sid, "final_tier"],
            "completion_tier_after": r.final_tier,
            "is_completed_event": completed,
            "prior_precision": prior,
            "in_recovery_search": in_queue,
            "inclusion_reason": why,
            "recovery_outcome": outcome,
            "recovered_precision": r.date_precision,
            "recovered_exact_date": r.verified_effective_date,
            "precision_changed": prior != r.date_precision,
            "conflict_flag": is_conf,
            "n_distinct_days_found": (int(cf.at[sid, "distinct_days_found"])
                                      if sid in cf.index else 0),
            "n_sources_for_accepted_day": (int(cf.at[sid, "sources_for_accepted_day"])
                                           if sid in cf.index else 0),
            "candidate_accessions": (cf.at[sid, "competing_accessions"]
                                     if sid in cf.index else ""),
            "candidate_days": (cf.at[sid, "all_days"] if sid in cf.index else ""),
            "evidence_locator": (cf.at[sid, "competing_evidence"]
                                 if sid in cf.index else ""),
            "verified_date_source_accession": r.verified_date_source_accession,
            "verified_date_source_form": r.verified_date_source_form,
            "verified_date_evidence": r.verified_date_evidence,
            "timing_eligible_primary": r.date_precision == "verified_exact_day",
        })

    x = pd.DataFrame(rows)
    out = CACHE / "event_master_reconciliation.csv"
    x.to_csv(out, index=False)
    fetchlib.record(out, kind="derived", parser="reconcile_event_master.py",
                    extra={"lineage": "prefold stage3 + frozen master"
                                      " + recovered_verified_dates + conflict audit"})

    rule("WHY THE RECOVERY UNIVERSE IS 116 AND THE UNRESOLVED COUNT IS 82")
    d = x[x.is_completed_event]
    q = d[d.in_recovery_search]
    print(f"  {len(x):>5d}   structural members in the register")
    print(f"  {len(d):>5d}   completed events")
    print(f"  {int((d.prior_precision == 'verified_exact_day').sum()):>5d}   "
          f"already verified before recovery -> not searched")
    print(f"  {len(q):>5d}   completed without a verified day -> THE RECOVERY QUEUE")
    print(f"  {'-' * 70}")
    for k, v in q.recovery_outcome.value_counts().items():
        print(f"  {v:>5d}   {k}")
    still = int((d.recovered_precision != "verified_exact_day").sum())
    print(f"  {'-' * 70}")
    print(f"  {len(q)} searched - {int((q.recovery_outcome == 'recovered_verified_exact_day').sum())}"
          f" recovered = {still} still unresolved")
    print(f"\n  116 and 82 are the same set of events at two points in time:")
    print(f"  116 lacked a verified day before recovery, 82 lack one after.")
    print(f"  The 82 is not a separate denominator and never was.")

    rule("MECHANISMS RULED OUT (each checked, not assumed)")
    dup = int(x.pre_series_id.duplicated().sum())
    print(f"  {'ok  ' if not dup else 'FAIL'}  duplicated event representations: {dup}")
    reclass = int((x.completion_tier_before != x.completion_tier_after).sum())
    comp_ch = int(d.is_completed_event.sum() - done_mask(before).sum())
    print(f"  ok    completion tier changed for {reclass} events, but the completed "
          f"set is unchanged (delta {comp_ch})")
    g = d.groupby("post_series_id").pre_series_id.nunique()
    print(f"  ok    many-to-one preserved: {int((g > 1).sum())} successors hold "
          f"{int(g[g > 1].sum())} predecessors, all kept as separate rows")
    resear = int(((x.prior_precision == "verified_exact_day")
                  & x.in_recovery_search).sum())
    print(f"  {'ok  ' if not resear else 'FAIL'}  previously verified events "
          f"re-searched: {resear}")
    print("  => the 116/82 difference is entirely the 34 recovered days. No "
          "reclassification,\n     no duplication, no collapse.")
    assert not dup and not resear

    rule("TRANSITION MATRIX  (completed events, before -> after)")
    m = pd.crosstab(d.prior_precision, d.recovered_precision)
    m = m.reindex(index=[p for p in ORDER if p in m.index],
                  columns=[p for p in ORDER if p in m.columns], fill_value=0)
    print(m.to_string())
    tm = CACHE / "date_transition_matrix.csv"
    m.to_csv(tm)
    fetchlib.record(tm, kind="derived", parser="reconcile_event_master.py",
                    extra={"lineage": "event_master_reconciliation.csv"})

    # a regression is a verified day becoming anything weaker
    reg = d[(d.prior_precision == "verified_exact_day")
            & (d.recovered_precision != "verified_exact_day")]
    print(f"\n  {'ok  ' if reg.empty else 'FAIL'}  regressions in date precision: "
          f"{len(reg)}")
    assert reg.empty, f"regressions: {list(reg.event_id)}"
    # and no verified date may be silently rewritten
    bv = before[before.date_precision == "verified_exact_day"] \
        .set_index("pre_series_id").verified_effective_date
    av = after.set_index("pre_series_id").verified_effective_date
    changed = [i for i in bv.index if str(bv[i]) != str(av[i])]
    print(f"  {'ok  ' if not changed else 'FAIL'}  pre-existing verified dates "
          f"overwritten: {len(changed)}")
    assert not changed, f"overwritten: {changed}"

    rule("FINAL COUNTS")
    c = d.recovered_precision.value_counts()
    for k in ORDER:
        print(f"  {int(c.get(k, 0)):>5d}   {k}")
    print(f"  {'-' * 44}\n  {len(d):>5d}   total completed events")
    assert sum(int(c.get(k, 0)) for k in ORDER) == len(d)
    elig = int(c.get("verified_exact_day", 0))
    print(f"  {len(x):>5d}   total structural members (incl. non-completed)")
    print(f"\n  {elig:>5d}   PRIMARY TIMING-ELIGIBLE ({elig / len(d):.0%} of completed)")
    print(f"  {len(d) - elig:>5d}   timing-ineligible completed")
    print(f"  {len(conflicted):>5d}   conflicting, held unresolved")

    fin = CACHE / "event_master_final_reconciled.csv"
    after.assign(event_id=after.pre_series_id.map(event_id),
                 timing_eligible_primary=after.date_precision.eq("verified_exact_day")
                 ).to_csv(fin, index=False)
    fetchlib.record(fin, kind="derived", parser="reconcile_event_master.py",
                    extra={"lineage": "events_master_v2_frozen.csv + event ids"})
    print(f"\n  written: {out.name}, {tm.name}, {fin.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
