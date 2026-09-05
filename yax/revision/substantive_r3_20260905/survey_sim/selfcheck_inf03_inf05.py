#!/usr/bin/env python3
"""Fail-closed checks for INF-03/INF-05 aggregate outputs."""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np
import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=pathlib.Path, required=True)
    parser.add_argument("--household-draws", type=int, default=199)
    parser.add_argument("--simulation-draws", type=int, default=199)
    args = parser.parse_args()
    receipt = json.loads((args.results / "EXECUTION_RECEIPT.json").read_text())
    feasibility = json.loads((args.results / "HOUSEHOLD_RESAMPLING_FEASIBILITY.json").read_text())
    dgp = json.loads((args.results / "FINITE_SAMPLE_DGP.json").read_text())
    failures = json.loads((args.results / "MODEL_FAILURES.json").read_text())
    household = pd.read_csv(args.results / "HOUSEHOLD_BOOTSTRAP_DRAWS.csv")
    hs = pd.read_csv(args.results / "HOUSEHOLD_BOOTSTRAP_SUMMARY.csv")
    simulation = pd.read_csv(args.results / "FINITE_SAMPLE_SIMULATION_DRAWS.csv")
    ss = pd.read_csv(args.results / "FINITE_SAMPLE_SIMULATION_SUMMARY.csv")
    checks = []

    def check(condition, message):
        checks.append({"check": message, "pass": bool(condition)})
        if not condition:
            raise RuntimeError(message)

    check(abs(receipt["unperturbed_models"]["baseline"] - (-0.1321094507921903)) < 5e-10, "baseline checkpoint")
    check(receipt["treatment_weight_reproduction"]["maximum_relative_gap"] < 1e-10, "preperiod weight reproduction")
    check(feasibility["march_gate_status"] == "PASS_FUNCTIONAL_REPLACEMENT", "March gate")
    check(feasibility["design_based_CPS_inference_available"] is False, "no false design-based claim")
    check(feasibility["route_and_unit_counts"]["active_source_records_with_nonpositive_CPSID"] == 0, "positive CPSID on active records")
    check(set(household.classification_mode) == {"fixed_corrected_labels", "rebuilt_preperiod_labels"}, "both classification targets")
    check(household.groupby("classification_mode").draw.nunique().min() == args.household_draws, "all household draws refit")
    check(len(hs) == 6 and hs.successful_full_refits.min() == args.household_draws, "household summaries complete")
    check(set(np.round(ss.true_Q5_post_effect, 9)) == set(np.round([0, -0.05, -0.1321094507921903], 9)), "three simulation effects")
    check(set(ss.model) == {"baseline", "SOC2_post"} and len(ss) == 6, "two simulation models")
    check(ss.successful_full_refits.min() == args.simulation_draws, "all simulation refits converge")
    check(len(simulation) == 3 * 2 * args.simulation_draws, "simulation draw rows complete")
    check(np.isfinite(ss[["bias", "empirical_SD", "mean_reported_occupation_cluster_SE", "normal_95_CI_coverage"]].to_numpy(float)).all(), "finite simulation summaries")
    check(dgp["diagnostics"]["cells_Kish_n_eff_below_10"] > 0, "sparse cells represented")
    check(dgp["diagnostics"]["SOC2_families"] >= 20, "broad families represented")
    check(len(failures) == 0, "no retained model failures")
    forbidden = {"SERIAL", "CPSID", "CPSIDP", "CPSIDV", "WTFINL"}
    check(not (forbidden & set(household.columns)), "no microdata identifiers/weights serialized")
    check(not (forbidden & set(simulation.columns)), "no microdata identifiers/weights in simulation")
    (args.results / "SELF_CHECK_INF03_INF05.json").write_text(
        json.dumps({"status": "PASS", "checks": checks}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
