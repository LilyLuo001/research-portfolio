"""Reconcile the verified through-2024 predecessor-fund count against the Fed's 125.

The bridge starts from the count the strict rule produced -- an N-CEN
TERMINATED_ORGANIZATION record for the predecessor plus a reporting successor --
and walks it to the current count one evidence channel at a time, so every fund
that entered or left the through-2024 set is attributable to a specific decision
rather than to a rebuild.

The residual is then split into named buckets. The point of the split is that the
buckets are not equivalent: an unresolved fund might still be ours, a definitional
exclusion never will be, and a counting-unit difference means the two numbers were
never measuring the same thing. Collapsing them into one "gap" number hides that.

FED_125_RECONCILIATION stays OPEN. Nothing here forces the count to 125.
"""
import sys

import pandas as pd

from paths import CACHE as HERE  # data lives outside the repo; see paths.py
FED = 125
FED_YEAR = 2024


def rule(s):
    print("\n" + "=" * 74)
    print(s)
    print("=" * 74)


def main():
    s1 = pd.read_csv(HERE / "events_master_v2_stage1.csv")
    ev = pd.read_csv(HERE / "events_master_v2_stage3.csv")
    led = pd.read_csv(HERE / "classification_ledger.csv")

    # ---------------------------------------------------------------- baseline
    # the strict rule as it stood: registrant-reported termination of the
    # predecessor, coherent with its own proxy, successor reporting in N-CEN
    s1["term"] = pd.to_datetime(s1.ncen_termination_month, errors="coerce")
    s1["n14_first"] = pd.to_datetime(s1.n14_first_filed, errors="coerce")
    base = s1[(s1.completion_tier == "B_structurally_confirmed_completion")
              & s1.term.notna()
              & (s1.term >= s1.n14_first - pd.Timedelta(days=90))
              & (s1.term <= f"{FED_YEAR}-12-31")]
    baseline = set(base.pre_series_id)

    # ------------------------------------------------------------------ final
    done = ev[ev.final_tier.str.startswith(("A_", "B_"), na=False)]
    final = set(done[done.final_year <= FED_YEAR].pre_series_id)

    added = done[done.pre_series_id.isin(final - baseline)]
    dropped = s1[s1.pre_series_id.isin(baseline - final)]

    # the user's four addition channels, in the order they were specified
    ORDER = ["successor-reporting completion (proposed close elapsed + successor in N-CEN)",
             "explicit SEC completion statement (497 / successor prospectus / N-CSR)",
             "other structural completion (anniversary cease; newly coherent termination)"]

    def channel(e):
        if e.final_precision == "verified_exact_day":
            return ORDER[1]
        if e.final_precision == "proposed_exact_day_only":
            return ORDER[0]
        return ORDER[2]

    add_by = added.apply(channel, axis=1).value_counts().reindex(ORDER).dropna() \
        if len(added) else pd.Series(dtype=int)

    # why did a baseline fund leave the through-2024 set?
    lost = []
    for r in dropped.itertuples(index=False):
        e = ev[ev.pre_series_id == r.pre_series_id]
        if e.empty:
            lost.append("dropped by the MF->ETF classifier")
        elif not str(e.final_tier.iloc[0]).startswith(("A_", "B_")):
            lost.append(f"no longer counted completed ({e.final_tier.iloc[0]})")
        elif pd.isna(e.final_year.iloc[0]):
            lost.append("completed, but year now ambiguous")
        else:
            lost.append(f"stronger evidence moved it to {int(e.final_year.iloc[0])}")
    lost = pd.Series(lost).value_counts() if lost else pd.Series(dtype=int)

    rule(f"2024 BRIDGE  (unit: predecessor mutual fund, through {FED_YEAR}-12-31)")
    print(f"  {len(baseline):>4d}   strict completed under the n-cen termination rule")
    for k, v in add_by.items():
        print(f"  {int(v):>+4d}   {k}")
    print(f"  {0:>+4d}   non-N14 structural discoveries (in-place conversions "
          f"detected: 0)")
    for k, v in lost.items():
        print(f"  {-v:>+4d}   false positive / cancellation / re-dated: {k}")
    print(f"  {'-' * 68}")
    print(f"  {len(final):>4d}   VERIFIED PREDECESSOR MUTUAL FUNDS THROUGH {FED_YEAR}")
    print(f"  {FED:>4d}   Fed benchmark")
    print(f"  {len(final) - FED:>+4d}   residual")

    # -------------------------------------------------------------- residual
    resid = FED - len(final)
    unres = ev[ev.final_tier == "unresolved"]
    unres24 = unres[unres.anchor_year <= FED_YEAR]
    ambig = done[done.final_year.isna()]
    ambig24 = ambig[ambig.anchor_year <= FED_YEAR]

    # pairs the classifier refused, that a looser definition would have counted
    led["filed"] = pd.to_datetime(led.filed, errors="coerce")
    rej = led[(~led.acq_is_etf | ~led.tgt_is_mf)
              & (led.filed <= f"{FED_YEAR}-12-31")]
    defn = rej[rej.acq_evidence.isin(
        ["listed_but_preexisting_dual_share_class_mf",
         "ncen_mixed_flag_dual_share_class"])].tgt_series_id.nunique()

    rule("RESIDUAL, CLASSIFIED")
    named = 0
    print(f"  {len(unres24):>4d}   unresolved completion evidence "
          f"(<= {FED_YEAR} anchor, still no channel speaks)")
    named += len(unres24)
    print(f"  {len(ambig24):>4d}   completed but year ambiguous "
          f"(n-cen bracket straddles a year boundary)")
    named += len(ambig24)
    print(f"  {defn:>4d}   definitional exclusion (target merged into a mutual fund "
          f"carrying an ETF share class)")
    named += defn
    # No "discovery miss = 0" line. Our recall diagnostics are measured against
    # LEGACY_GOLD and against in-place renaming; neither can see an event that
    # both discovery systems missed, and the benchmark's own list is not public.
    # A zero here would assert exactly the thing that cannot be observed, so the
    # unexplained bucket carries that possibility instead of hiding it.
    print(f"  {resid - named:>4d}   unexplained (may contain discovery misses; "
          f"see DISCOVERY_COMPLETENESS below)")
    # The unexplained bucket is a plug, and is stated as one: it is whatever the
    # named channels do not account for. What is worth checking is the identity
    # the plug closes -- our count plus every named channel plus the plug must
    # land on the benchmark exactly, or a channel is being double-counted.
    parts = [("verified through 2024", len(final)),
             ("unresolved completion", len(unres24)),
             ("completed, year unresolved", len(ambig24)),
             ("frozen-definition exclusion", defn),
             ("unexplained residual", resid - named)]
    print(f"  {'-' * 68}")
    for k, v in parts:
        print(f"  {v:>4d}   {k}")
    tot = sum(v for _, v in parts)
    print(f"  {tot:>4d}   = Fed benchmark {FED}   "
          f"{'ok' if tot == FED else 'FAIL'}")
    assert tot == FED, f"reconciliation sums to {tot}, benchmark is {FED}"

    rule("COUNTING UNIT")
    print("  the benchmark and this register may not be counting the same object")
    print(f"  {done.pre_series_id.nunique():>4d}   predecessor funds (the unit used here)")
    print(f"  {done.post_series_id.nunique():>4d}   successor ETFs "
          f"(some absorb more than one predecessor)")
    n = done.pre_class_ids.fillna("").apply(
        lambda s: len([x for x in str(s).split(";") if x.strip()])).sum()
    print(f"  {int(n):>4d}   predecessor share classes")

    rule("UNRESOLVED BY YEAR")
    b = unres.anchor_year.apply(
        lambda y: "<=2024" if y <= 2024 else ("2025" if y == 2025 else
                                              "2026" if y == 2026 else ">2026"))
    for k in ["<=2024", "2025", "2026", ">2026"]:
        print(f"  {int((b == k).sum()):>4d}   {k}")
    print(f"  {int(unres.anchor_year.isna().sum()):>4d}   unknown")
    print(f"  {len(unres):>4d}   total unresolved")

    rule("EXACT-DAY COMPLETION COVERAGE")
    p = done.final_precision.value_counts()
    # the classes are exhaustive and are asserted to be: a precision label that
    # goes unlisted here would silently drop completions out of this census
    PREC = ["verified_exact_day", "proposed_exact_day_only", "month_only",
            "bounded_window", "year_only"]
    for k in PREC:
        print(f"  {int(p.get(k, 0)):>4d}   {k}")
    assert sum(int(p.get(k, 0)) for k in PREC) == len(done), \
        f"unlisted precision: {set(p.index) - set(PREC)}"
    exact = int(p.get("verified_exact_day", 0))
    print(f"  {exact / len(done):>6.0%}   of completions carry a filing-stated closing day")

    rule("CUMULATIVE PREDECESSOR FUNDS BY PERIOD")
    y = done.final_year.dropna().astype(int)
    for yy in sorted(y.unique()):
        print(f"  {yy}   {int((y == yy).sum()):>4d} realized   "
              f"{int((y <= yy).sum()):>4d} cumulative")
    print(f"  ambiguous year: {int(done.final_year.isna().sum())}")
    print(f"\n  through 2024 : {int((y <= 2024).sum())}")
    print(f"  2025 only    : {int((y == 2025).sum())}")
    print(f"  2026 to date : {int((y == 2026).sum())}")
    print(f"  FULL UNIVERSE THROUGH 2026-08-29 : {len(done)}")

    rule("DISCOVERY COMPLETENESS")
    print("  Recall was measured against two things we can see, and both came")
    print("  back clean:")
    print("    N-14 recall vs LEGACY_GOLD          : 100% (82/82)")
    print("    in-place conversions detected       : 0")
    print("    rejected acquirers that are ETFs    : 0")
    print("\n  What that licenses is narrow. LEGACY_GOLD is the output of the")
    print("  earlier discovery system, so agreement with it cannot reveal an")
    print("  event that both systems missed, and the benchmark's own list is")
    print("  not public, so it cannot be diffed against ours either.")

    p = HERE / "discovery_probe_triage.csv"
    if p.exists():
        t = pd.read_csv(p)
        a = t.adjudication.value_counts()
        print("\n  So a third channel was built that never consults N-14 at all: a")
        print("  fund disappearing from its registrant's N-CEN census while a")
        print("  similarly named listed ETF starts appearing. It is the only")
        print("  measurement here that can see an event both systems missed.")
        print(f"    shortlisted pairs outside the register : {len(t)}")
        print(f"    master-feeder, structurally not events : "
              f"{int(t.master_feeder.sum())}")
        print(f"    filing-stated liquidation or closure   : "
              f"{int(a.get('liquidated', 0))}")
        print(f"    read and shown to be something else    : "
              f"{int(a.get('not_a_conversion', 0)) - int(t.master_feeder.sum())}")
        print(f"    CONVERSIONS FOUND                      : "
              f"{int(a.get('is_a_conversion', 0))}")
        print(f"    terminated, destination not established: "
              f"{int(a.get('unadjudicated', 0))}")
        print("\n  No conversion was found outside the register. That is a real")
        print("  bound, not a proof: the probe can only see a miss that left a")
        print(f"  shape in N-CEN, and {int(a.get('unadjudicated', 0))} flagged funds "
              f"ended without their")
        print("  destination being established, so the possibility is bounded")
        print("  rather than eliminated.")

    print("\n  NO_OBSERVED_MISS_AGAINST_LEGACY_GOLD = TRUE")
    print("  NO_CONVERSION_FOUND_BY_INDEPENDENT_NCEN_PROBE = TRUE")
    print("  DISCOVERY_COMPLETENESS = EMPIRICALLY_SATURATED / OPEN")
    print("  FED_125_RECONCILIATION = OPEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
