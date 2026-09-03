#!/usr/bin/env python3
"""
sample_scenarios.py — P1-B1: how many treated stocks survive each sample rule?

Answers the two open owner decisions with numbers instead of adjectives:
  V-1  the DFA question       — W002 is 92.8% of treated mass at >=0.5%
  V-6  the international sleeve — Option A / A-strict

and the interaction between them, which is worse than either alone.

Everything is computed from committed files. No network, no WRDS. Re-run it
after any change to the event set or ConvExp and the table regenerates.

  python p1/t1_reconcile/sample_scenarios.py            # print the table
  python p1/t1_reconcile/sample_scenarios.py --csv OUT  # also write it

Power floor (33 treated stocks) is the T2a simulation's line, carried in
p1/output/convexp_coverage_audit/international_sleeve_options.md. It is a
property of the design, not of this script — if T2a is re-run, update POWER_FLOOR.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
EVENTS = REPO / "p1" / "events_merged.csv"
MEMBERS = REPO / "p1" / "t2_wrds" / "waves_members.csv"
CONVEXP = REPO / "p1" / "conv_exposure_free.parquet"

POWER_FLOOR = 33          # T2a: minimum treated stocks for adequate power
ANCHOR_WAVE = "W002"      # 2021-06-11, four DFA funds
DOSE_TIERS = [(0.005, ">=0.5%"), (0.01, ">=1%")]


def load():
    ev = pd.read_csv(EVENTS)
    mem = pd.read_csv(MEMBERS)
    ce = pd.read_parquet(CONVEXP)
    # wave -> the asset classes of its member funds (NaN class stays absent)
    mm = mem.merge(ev[["fund_name", "effective_date", "asset_class"]],
                   on=["fund_name", "effective_date"], how="left")
    cls = mm.groupby("wave_id")["asset_class"].apply(lambda s: set(s.dropna()))
    return ev, mm, ce, cls


def wave_sets(cls: pd.Series) -> tuple[set, set]:
    """pure_intl: every classified member is equity_intl.
    touch_intl: at least one member is equity_intl."""
    pure = {w for w, s in cls.items() if s and s <= {"equity_intl"}}
    touch = {w for w, s in cls.items() if "equity_intl" in s}
    return pure, touch


def scenarios(ce: pd.DataFrame, pure: set, touch: set) -> pd.DataFrame:
    rows = []
    for thr, lab in DOSE_TIERS:
        tr = ce[ce["conv_exp"] >= thr]
        no_dfa = tr["wave_id"] != ANCHOR_WAVE
        for name, sel in [
            ("ALL (as built)", tr),
            ("Option A — drop pure-intl waves", tr[~tr["wave_id"].isin(pure)]),
            ("A-strict — drop any intl-touching wave", tr[~tr["wave_id"].isin(touch)]),
            ("excl DFA (W002)", tr[no_dfa]),
            ("excl DFA + Option A", tr[no_dfa & ~tr["wave_id"].isin(pure)]),
            ("excl DFA + A-strict", tr[no_dfa & ~tr["wave_id"].isin(touch)]),
        ]:
            n = sel["cusip"].nunique()
            rows.append({"dose_tier": lab, "scenario": name, "stocks": n,
                         "cells": len(sel), "waves": sel["wave_id"].nunique(),
                         "powered": bool(n >= POWER_FLOOR)})
    return pd.DataFrame(rows)


def classification_gap(ev: pd.DataFrame, mm: pd.DataFrame, ce: pd.DataFrame) -> dict:
    """How much treated mass depends on an unclassified event being classified?

    If this is 0, fixing asset_class cannot change any sample scenario above —
    which is what makes the DFA finding robust to the classification backlog.
    """
    na = ev[ev["asset_class"].isna()]
    unc_waves = set(mm.loc[mm["asset_class"].isna(), "wave_id"])
    at_stake = {}
    for thr, lab in DOSE_TIERS:
        tr = ce[ce["conv_exp"] >= thr]
        at_stake[lab] = int(len(tr[tr["wave_id"].isin(unc_waves)]))
    return {"unclassified_events": len(na), "total_events": len(ev),
            "unclassified_accessions": int(na["source_accession"].nunique()),
            "treated_cells_at_stake": at_stake}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=None, help="write the scenario table here")
    args = ap.parse_args()

    ev, mm, ce, cls = load()
    pure, touch = wave_sets(cls)
    tab = scenarios(ce, pure, touch)
    gap = classification_gap(ev, mm, ce)

    print(f"events {len(ev)} | waves with treated mass "
          f"{ce[ce.conv_exp >= 0.005].wave_id.nunique()} | power floor {POWER_FLOOR}\n")
    for tier in tab["dose_tier"].unique():
        sub = tab[tab["dose_tier"] == tier]
        print(f"  dose tier {tier}")
        for r in sub.itertuples():
            flag = "" if r.powered else "   ** BELOW POWER FLOOR **"
            print(f"    {r.scenario:<42}{r.stocks:>5} stocks  {r.waves:>2} waves{flag}")
        print()

    print(f"classification backlog: {gap['unclassified_events']}/{gap['total_events']} events "
          f"have no asset_class ({gap['unclassified_accessions']} accessions)")
    print(f"treated cells at stake from it: {gap['treated_cells_at_stake']}")
    if not any(gap["treated_cells_at_stake"].values()):
        print("  -> ZERO. Classifying them cannot change any scenario above.")

    if args.csv:
        Path(args.csv).parent.mkdir(parents=True, exist_ok=True)
        tab.to_csv(args.csv, index=False)
        print(f"\nwrote {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
