"""One row per residual case, or per hypothesis that could occupy a missing benchmark slot.

The residual to the Fed's 125 splits into two kinds of thing, and they are not
interchangeable. Some of it is funds we hold and did not count: those are named,
one row each, with the evidence that is actually missing. The rest is slots --
funds the benchmark counted that have no row here at all. A slot cannot be named
from our side, so the honest unit is the hypothesis that would fill it, carried
with a measured magnitude and a verdict rather than an assertion.

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

    def add(kind, name, why):
        rows.append({"kind": kind, "case": name, "strongest_explanation": why})

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

    rule(f"MISSING BENCHMARK SLOTS  ({slots}) -- one row per hypothesis")
    H = [
        ("benchmark cutoff is later than 2024-12-31",
         f"our cumulative completions reach {FED} on 2025-09-30 "
         f"({int((d.dt <= '2024-12-31').sum())} at 2024-12-31, "
         f"{int((d.dt <= '2025-06-30').sum())} at 2025-06-30)",
         "PLAUSIBLE, UNTESTED -- would close the residual exactly, which is "
         "precisely why it must not be assumed; needs the benchmark's stated "
         "as-of date, which we do not hold"),
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
         f"three independent measurements: in-place conversions = 0; "
         f"LEGACY_GOLD N-14 recall = 100% (82/82); all {noev} acquirers the "
         f"classifier rejected for want of ETF evidence are plainly mutual funds",
         "REJECTED -- no evidence of a discovery miss from any channel"),
    ]
    for i, (h, meas, verdict) in enumerate(H, 1):
        print(f"\n  {i}. {h}")
        print(f"     measured : {meas}")
        print(f"     verdict  : {verdict}")

    for h, meas, verdict in H:
        rows.append({"kind": "missing benchmark slot (hypothesis)", "case": h,
                     "strongest_explanation": f"{meas} -- {verdict}"})
    pd.DataFrame(rows).to_csv(HERE / "fed_residual_cases.csv", index=False)

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
