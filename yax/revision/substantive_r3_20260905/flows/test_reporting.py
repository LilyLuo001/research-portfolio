#!/usr/bin/env python3
"""Numerical consistency checks for the compact flow reporting layer."""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd


ROOT = pathlib.Path(__file__).resolve().parent
R3 = ROOT.parent


def main() -> int:
    compact = pd.read_csv(ROOT / "COMPACT_CORE_FLOW_TABLE.csv").set_index("model_id")
    results = pd.read_csv(ROOT / "results" / "FLOW_AND_WORKER_OUTCOME_RESULTS.csv").set_index("model_id")
    household = pd.read_csv(
        ROOT / "results_household" / "PERSON_HOUSEHOLD_CLUSTER_SENSITIVITY.csv"
    ).set_index("model_id")
    counts = (
        pd.read_csv(ROOT / "results" / "FLOW_RISK_EVENT_COUNTS.csv")
        .loc[lambda x: x.weighting.eq("official")]
        .set_index(["horizon", "margin"])
    )
    assert len(compact) == 6 and compact.index.is_unique
    mappings = {
        "coefficient": "coefficient",
        "primary_occupation_cluster_se": "analytic_occupation_cluster_se",
        "primary_wild_ci_lower": "wild_score_ci_lower",
        "primary_wild_ci_upper": "wild_score_ci_upper",
        "primary_normal_mde80": "normal_theory_MDE80",
    }
    for compact_name, result_name in mappings.items():
        assert np.array_equal(
            compact[compact_name].to_numpy(),
            results.loc[compact.index, result_name].to_numpy(),
        )
    for name in [
        "household_cluster_se",
        "household_normal_ci_lower",
        "household_normal_ci_upper",
        "household_normal_mde80",
    ]:
        assert np.array_equal(compact[name].to_numpy(), household.loc[compact.index, name].to_numpy())
    for model_id, row in compact.iterrows():
        horizon, margin, _ = model_id.split("__")
        source = counts.loc[(horizon, margin)]
        assert int(row.risk_or_entry_raw_records) == int(source.risk_raw_records)
        assert int(row.event_raw_records) == int(source.event_raw_records)

    core = results.loc[household.index]
    assert ((core.wild_score_ci_lower <= 0) & (core.wild_score_ci_upper >= 0)).all()
    assert (
        (household.household_normal_ci_lower <= 0)
        & (household.household_normal_ci_upper >= 0)
    ).all()
    unweighted = results.loc[
        [
            "adjacent_month__employment_exit__unweighted",
            "adjacent_month__labor_force_exit__unweighted",
        ]
    ]
    assert (unweighted.wild_score_ci_lower > 0).all()

    ledger = pd.read_csv(R3 / "RESULTS_LEDGER.csv").set_index("spec_id")
    ledger_map = {
        "FLOW-01-ADJ-EXIT": "adjacent_month__employment_exit__official",
        "FLOW-01-ADJ-OCC": "adjacent_month__occupational_outflow__official",
        "FLOW-01-ADJ-ENTRY": "adjacent_month__entry_destination__official",
        "FLOW-01-ANN-EXIT": "twelve_month__employment_exit__official",
        "FLOW-01-ANN-OCC": "twelve_month__occupational_outflow__official",
        "FLOW-01-ANN-ENTRY": "twelve_month__entry_destination__official",
    }
    for ledger_id, model_id in ledger_map.items():
        assert abs(float(ledger.loc[ledger_id, "estimate"]) - float(results.loc[model_id, "coefficient"])) < 5e-10
        assert abs(float(ledger.loc[ledger_id, "se"]) - float(results.loc[model_id, "analytic_occupation_cluster_se"])) < 5e-10

    assert json.loads((ROOT / "results" / "SELF_CHECK.json").read_text())["status"] == "PASS"
    assert json.loads((ROOT / "results_household" / "SELF_CHECK.json").read_text())["status"] == "PASS"
    summary = (ROOT / "RESULTS_SUMMARY.md").read_text(encoding="utf-8")
    summary = summary.replace("-\n", "").replace("\n", " ")
    for phrase in [
        "statistically distinguishable",
        "employment-finding probability",
        "employer hiring rate",
        "do not reproduce the CPS sample design",
        "implementation deviation",
    ]:
        assert phrase.lower() in summary.lower()
    print("flow reporting consistency PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
