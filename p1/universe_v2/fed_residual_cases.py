"""One row per residual case, per unnamed block of benchmark slots, and per hypothesis.

The residual to the Fed's 125 splits into two kinds of thing, and they are not
interchangeable. Some of it is funds we hold and did not count: those are named,
one row each, with the evidence that is actually missing. The rest is slots --
funds the benchmark counted that have no row here at all. A slot cannot be named
from our side, so it is carried as one block row of known size, and the
hypotheses that might fill it are carried separately, each with a measured
magnitude and a verdict rather than an assertion.

SCHEMA AND AGGREGATION RULE. Earlier this file had 17 rows against a 26-unit
residual and no way to tell which rows were units and which were commentary, so
the denominator was ambiguous. Every row now declares what it counts:

  unit     what one unit of n_units is
  n_units  how many units of the residual this row accounts for

  kind                                unit                n_units
  completed, year unresolved          predecessor fund    1 per row
  unresolved completion               predecessor fund    1 per row
  definitional exclusion              predecessor fund    1 per row
  missing benchmark slots             benchmark slot      the whole block, once
  missing benchmark slot (hypothesis) none                0

The aggregation rule is therefore: sum n_units over all rows, and that sum is
asserted to equal the residual exactly. Hypothesis rows count zero because they
are competing explanations of the SAME block, not additional units -- adding them
would double-count the block, which is how the old file drifted.

Nothing here moves a fund into the through-2024 set. FED_125_RECONCILIATION
stays OPEN.
"""
import sys

import pandas as pd

from paths import CACHE as HERE  # data lives outside the repo; see paths.py
FED, FED_YEAR = 125, 2024
DEFN = ["listed_but_preexisting_dual_share_class_mf", "ncen_mixed_flag_dual_share_class"]


def rule(s):
    print("\n" + "=" * 78)
    print(s)
    print("=" * 78)


def main():
    ev = pd.read_csv(HERE / "events_master_v2_stage3.csv")
    led = pd.read_csv(HERE / "classification_ledger.csv")
    led["filed"] = pd.to_datetime(led.filed, errors="coerce")
    done = ev[ev.final_tier.str.startswith(("A_", "B_"), na=False)]
    have = int((done.final_year <= FED_YEAR).sum())

    rows = []

    def add(kind, name, why, unit="predecessor fund", n=1):
        rows.append({"kind": kind, "case": name, "unit": unit, "n_units": n,
                     "strongest_explanation": why})

    # ---- named: completed, but the year could not be pinned to 2024 or earlier
    amb = done[done.final_year.isna() & (done.anchor_year <= FED_YEAR)]
    for r in amb.itertuples(index=False):
        add("completed, year unresolved", r.pre_series_name,
            f"closed inside {r.cease_lo[:10]}..{r.cease_hi[:10]}, a bracket that "
            f"crosses a year boundary; no filing states the day and no N-CEN "
            f"termination month exists, so it cannot be assigned to {FED_YEAR}")

    # ---- named: no completion channel speaks at all
    unres = ev[(ev.final_tier == "unresolved") & (ev.anchor_year <= FED_YEAR)]
    for r in unres.itertuples(index=False):
        add("unresolved completion", r.pre_series_name,
            f"proxy anchored {int(r.anchor_year)}; predecessor has no N-CEN "
            f"termination record, did not reach an N-CEN anniversary absent, and "
            f"per-event escalation read the window without finding an "
            f"attributable completion sentence")

    # ---- named: excluded by the frozen definition
    rej = led[(~led.acq_is_etf | ~led.tgt_is_mf) & (led.filed <= f"{FED_YEAR}-12-31")]
    for r in rej[rej.acq_evidence.isin(DEFN)].drop_duplicates("tgt_series_id") \
            .itertuples(index=False):
        add("definitional exclusion", r.tgt_series_name,
            f"merged into {r.acq_series_name}, a mutual fund that carries an ETF "
            f"share class; the surviving vehicle is not an ETF, so under the "
            f"frozen P1 definition no conversion occurred")

    named = pd.DataFrame(rows)
    slots = FED - have - len(named)

    rule(f"RESIDUAL TO THE FED BENCHMARK  ({have} held vs {FED}; residual {FED - have})")
    print(f"  {len(named):>4d}   named cases in this register (rows below)")
    print(f"  {slots:>4d}   missing benchmark slots -- no row exists on our side")

    for k in ["completed, year unresolved", "unresolved completion",
              "definitional exclusion"]:
        g = named[named.kind == k]
        rule(f"{k.upper()}  ({len(g)})")
        for i, r in enumerate(g.itertuples(index=False), 1):
            print(f"  {i}. {r.case}")
            print(f"     {r.strongest_explanation}")

    # ------------------------------------------------------------------ slots
    d = done.copy()
    d["dt"] = pd.to_datetime(d.final_effective_date, errors="coerce")
    cls24 = d[d.final_year <= FED_YEAR].pre_class_ids.fillna("").apply(
        lambda s: len([x for x in str(s).split(";") if x.strip()])).sum()
    redatable = int(((d.final_year == FED_YEAR + 1)
                     & (pd.to_datetime(d.cease_lo, errors="coerce").dt.year <= FED_YEAR)
                     & (d.final_precision == "month_only")).sum())
    # a register keyed on announcement counts a pair from its first proxy, so the
    # right field is the N-14 filing date, not the year the close is anchored to
    n14 = pd.to_datetime(ev.n14_first_filed, errors="coerce")
    counted24 = set(done[done.final_year <= FED_YEAR].pre_series_id)
    ann = int(((n14 <= f"{FED_YEAR}-12-31")
               & ~ev.pre_series_id.isin(counted24)).sum())
    noev = led[(led.acq_evidence == "no_evidence")
               & (led.filed <= f"{FED_YEAR}-12-31")].acq_series_id.nunique()

    # the independent N-CEN discovery probe, if it has been run
    p = HERE / "discovery_probe_triage.csv"
    if p.exists():
        tri = pd.read_csv(p)
        a = tri.adjudication.value_counts()
        probe = {"n": len(tri), "conv": int(a.get("is_a_conversion", 0)),
                 "mf": int(tri.master_feeder.sum()), "liq": int(a.get("liquidated", 0)),
                 "open": int(a.get("unadjudicated", 0))}
    else:
        probe = {"n": 0, "conv": 0, "mf": 0, "liq": 0, "open": 0}

    rule(f"MISSING BENCHMARK SLOTS  ({slots} units, one block) -- "
         f"competing explanations, each counting zero")
    H = [
        ("benchmark cutoff is later than 2024-12-31",
         f"our cumulative completions reach {FED} on 2025-09-30 "
         f"({int((d.dt <= '2024-12-31').sum())} at 2024-12-31, "
         f"{int((d.dt <= '2025-06-30').sum())} at 2025-06-30)",
         "REJECTED AS AN EXPLANATION -- the benchmark states an end-2024 cutoff, "
         "and we hold no independent evidence that its stated cutoff is "
         "inaccurate, so a later one may not be invoked to close the gap. The "
         "arithmetic is recorded because it would become relevant if the "
         "benchmark's as-of date were ever shown to differ, but a residual that "
         "vanishes only by moving the benchmark's own goalposts is not explained"),
        ("benchmark counts announced conversions, not completed ones",
         f"{ann} pairs filed their first N-14 by {FED_YEAR}-12-31 but are not in "
         f"our through-{FED_YEAR} completed set, so an announcement-keyed "
         f"register would hold {have + ann} where we hold {have}",
         f"PLAUSIBLE BUT INSUFFICIENT -- a register built from proxy filings "
         f"runs ahead of a completion-verified one by construction, but even "
         f"counting every announced pair leaves {FED - have - ann} short of "
         f"{FED}, and it subsumes the {len(named)} named cases rather than "
         f"adding to them"),
        ("benchmark counts share classes, not funds",
         f"our {have} through-{FED_YEAR} funds carry {int(cls24)} predecessor "
         f"share classes",
         f"REJECTED as a whole -- {int(cls24)} overshoots {FED}; could explain "
         f"slots only in a mixed-unit construction"),
        ("our 2025-dated funds actually closed in 2024",
         f"{redatable} funds dated {FED_YEAR + 1} have a bracket opening in "
         f"{FED_YEAR}, but each rests on a registrant-reported "
         f"{FED_YEAR + 1} N-CEN termination month",
         f"WEAK -- bounded above by {redatable}, and taking it would mean "
         f"overriding the registrant's own filing with a bracket"),
        ("benchmark includes closed-end funds / BDCs converting to an ETF",
         "14 open-end N-14s carry no MERGER block; every one was read and is a "
         "closed-end fund or BDC. 0 of 377 N-14 8C filings come from an ETF trust",
         "OUT OF THE FROZEN DEFINITION -- real conversions, but not MF->ETF"),
        ("the N-14 spine missed a completed MF->ETF conversion",
         f"in-place conversions = 0; LEGACY_GOLD N-14 recall = 100% (82/82); all "
         f"{noev} acquirers the classifier rejected for want of ETF evidence are "
         f"plainly mutual funds; and an N-CEN-only probe that never consults N-14 "
         f"shortlisted {probe['n']} fund pairs outside the register, of which "
         f"{probe['conv']} are demonstrated conversions, {probe['mf']} are "
         f"master-feeder pairs, {probe['liq']} have a filing-stated closure and "
         f"{probe['open']} remain unadjudicated",
         "NOT DEMONSTRATED, NOT EXCLUDED -- the first three measurements are all "
         "taken against the N-14 spine or its own prior output, so none of them "
         "can see an event both discovery systems missed. The N-CEN probe is the "
         "only channel here that can, and it found no conversion; but it left "
         f"{probe['open']} terminated funds whose destination could not be "
         "established, so this hypothesis is bounded, not closed"),
    ]
    for i, (h, meas, verdict) in enumerate(H, 1):
        print(f"\n  {i}. {h}")
        print(f"     measured : {meas}")
        print(f"     verdict  : {verdict}")

    # the block itself carries the slot count; the hypotheses below it are
    # competing explanations of this one block and therefore count nothing
    add("missing benchmark slots",
        f"{slots} funds the benchmark counted with no row on our side",
        "not nameable from our data: the benchmark's own list is not published, "
        "so these can be counted but not identified. The hypothesis rows that "
        "follow are candidate explanations of this block, not further units.",
        unit="benchmark slot", n=slots)
    for h, meas, verdict in H:
        rows.append({"kind": "missing benchmark slot (hypothesis)", "case": h,
                     "unit": "none (annotation)", "n_units": 0,
                     "strongest_explanation": f"{meas} -- {verdict}"})

    out = pd.DataFrame(rows)[["kind", "case", "unit", "n_units",
                              "strongest_explanation"]]
    out.to_csv(HERE / "fed_residual_cases.csv", index=False)

    rule("FILE SCHEMA AND AGGREGATION  (no ambiguous denominator)")
    print(f"  rows in fed_residual_cases.csv : {len(out)}")
    print(f"  residual to be accounted for   : {FED - have}\n")
    print(f"  {'kind':<38}{'rows':>6}{'unit':>20}{'n_units':>9}")
    for k, g in out.groupby("kind", sort=False):
        print(f"  {k:<38}{len(g):>6}{g.unit.iloc[0]:>20}{int(g.n_units.sum()):>9}")
    print(f"  {'-' * 72}")
    print(f"  {'TOTAL':<38}{len(out):>6}{'':>20}{int(out.n_units.sum()):>9}")
    print("\n  row count and unit count are different numbers on purpose: the six")
    print("  hypothesis rows explain the slot block rather than adding to it.")
    assert int(out.n_units.sum()) == FED - have, (int(out.n_units.sum()), FED - have)

    rule("DEFINITIONAL EXCLUSIONS: WOULD THE BENCHMARK COUNT THIS ARCHITECTURE?")
    print("  The five above are targets that merged into a mutual fund carrying an")
    print("  ETF share class. Shareholders can end up holding an exchange-listed")
    print("  interest, so a register keyed on 'did the money end up in an ETF'")
    print("  would count them; a register keyed on 'did a fund become an ETF',")
    print("  which is the frozen P1 definition, does not -- the surviving")
    print("  registered vehicle is still an open-end mutual fund.")
    print("\n  We do not hold the benchmark's published wording or its construction")
    print("  code, so this is NOT RESOLVED. The five stay outside the P1 universe")
    print("  and are carried in fed_residual_cases.csv so that including them")
    print("  later is a one-line decision rather than a rebuild.")

    print("\nFED_125_RECONCILIATION = OPEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
