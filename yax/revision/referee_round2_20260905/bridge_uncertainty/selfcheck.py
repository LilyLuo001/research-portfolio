#!/usr/bin/env python3
"""Fail-closed checks for the referee-round-2 bridge-uncertainty artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

import numpy as np
import pandas as pd


HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[4]
RESULTS = HERE / "results"
FROZEN = -0.13107397642233506
CORRECTED = -0.1345539535732939


def sha256(path):
    digest = hashlib.sha256()
    with pathlib.Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def run(args):
    receipt = json.loads((RESULTS / "EXECUTION_RECEIPT.json").read_text(encoding="utf-8"))
    performed = []
    for name, expected in receipt["output_hashes"].items():
        path = RESULTS / name
        check(path.is_file(), "missing output {}".format(name))
        check(sha256(path) == expected, "output hash mismatch {}".format(name))
    performed.append("all receipt output hashes")

    public_paths = {
        "analysis_spec": HERE / "ANALYSIS_SPEC.md",
        "execution_code": HERE / "run_bridge_uncertainty.py",
        "bridge": ROOT / "yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv",
        "computerization": ROOT / "yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv",
        "lookup": ROOT / "yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv",
        "rule_b": ROOT / "yax/measurement/RULE_B_VALUES_CENSUS2018.csv",
        "calendar_results": ROOT / "yax/revision/referee_20260905/results/balanced_cells/CALENDAR_TAXONOMY_SENSITIVITIES.csv",
    }
    for key, path in public_paths.items():
        check(path.is_file(), "missing public input {}".format(path))
        check(sha256(path) == receipt["input_hashes"][key], "input hash mismatch {}".format(key))
    performed.append("all repository input hashes")

    optional_private = {
        "microdata": args.microdata,
        "repair_microdata": args.repair_microdata,
        "preperiod_cells": args.preperiod_cells,
    }
    checked_private = []
    for key, path in optional_private.items():
        if path is not None:
            check(path.is_file(), "missing optional private input {}".format(path))
            check(sha256(path) == receipt["input_hashes"][key], "private input hash mismatch {}".format(key))
            checked_private.append(key)
    performed.append("optional private input hashes: {}".format(",".join(checked_private) or "not supplied"))

    calendar = receipt["calendar"]
    check(calendar["observed_months"] == 114, "observed calendar count")
    check(calendar["static_corrected_months"] == 113, "corrected static count")
    check(calendar["static_frozen_months"] == 108, "frozen static count")
    check(not calendar["October_2025_present"], "October 2025 must be absent")
    check(len(calendar["restored_March_months"]) == 5, "five March samples restored")
    performed.append("calendar identities")

    base = receipt["baseline_reproduction"]
    check(np.isclose(base["frozen_observed"], FROZEN, atol=1e-12, rtol=0), "frozen reproduction")
    check(np.isclose(base["corrected_observed"], CORRECTED, atol=1e-12, rtol=0), "corrected reproduction")
    performed.append("frozen and corrected coefficients")

    universe = receipt["universe_reconciliation"]
    check(universe["frozen_beta_complete_balanced_support"] == 490, "frozen universe")
    check(universe["raw_route_expanded_balanced_candidates"] == 539, "raw expanded universe")
    check(universe["repaired_AIOE_plus_Webb_route_expanded_support"] == 495, "AIOE-Webb universe")
    check(universe["intersection"] + universe["frozen_only"] == 490, "490 set identity")
    check(universe["intersection"] + universe["expanded_only"] == 495, "495 set identity")
    u = pd.read_csv(RESULTS / "UNIVERSE_RECONCILIATION.csv", dtype={"occupation_code": str})
    check(universe["raw_candidate_only_neither_490_nor_495"] == 20, "raw-only candidate count")
    check(universe["serialized_union_rows"] == 539, "serialized union receipt count")
    check(len(u) == universe["serialized_union_rows"],
          "universe union rows")
    check(int(u.in_frozen_490.sum()) == 490, "listed frozen support")
    check(int(u.in_route_expanded_495.sum()) == 495, "listed expanded support")
    check(int(u.in_raw_route_expanded_539.sum()) == 539, "listed raw expanded candidates")
    check(int((u.universe_relation == "raw_candidate_only_neither_490_nor_495").sum()) == 20,
          "listed raw-only candidates")
    performed.append("490/539/495 reconciliation")

    models = pd.read_csv(RESULTS / "MODEL_SENSITIVITIES.csv")
    frozen = models.loc[models.specification.eq("frozen_108_month_chronology_benchmark")].iloc[0]
    corrected = models.loc[models.specification.eq("corrected_March_113_month_substantive_baseline")].iloc[0]
    clean = models.loc[models.specification.eq("structural_one_to_one_targets_fixed_labels")].iloc[0]
    check(np.isclose(frozen.coefficient, FROZEN, atol=1e-12, rtol=0), "model frozen row")
    check(np.isclose(corrected.coefficient, CORRECTED, atol=1e-12, rtol=0), "model corrected row")
    check(int(clean.support_occupations) == 369, "clean-route support")
    check(np.isfinite(pd.to_numeric(models.coefficient)).all(), "finite model coefficients")
    performed.append("model table identities")

    routes = pd.read_csv(RESULTS / "ROUTE_SHARE_SUMMARY.csv")
    within_tail = routes.groupby(["period", "age_group", "tail_group"]).share_within_age_period_tail.sum()
    age_period = routes.groupby(["period", "age_group"]).share_of_age_period_stock.sum()
    check(np.allclose(within_tail.to_numpy(), 1.0, atol=1e-12), "within-tail route shares")
    check(np.allclose(age_period.to_numpy(), 1.0, atol=1e-12), "age-period shares")
    performed.append("route-share adding-up")

    bounds = pd.read_csv(RESULTS / "AGE_ALLOCATION_ACCOUNTING_BOUNDS.csv")
    stocks = bounds.loc[bounds.object.eq("early_2017_2019_weighted_stock")]
    check((stocks.unrestricted_allowed_route_lower <= stocks.official_common_weight_allocation).all(),
          "official stock below lower bound")
    check((stocks.official_common_weight_allocation <= stocks.unrestricted_allowed_route_upper).all(),
          "official stock above upper bound")
    performed.append("allocation accounting bounds")

    scenarios = pd.read_csv(RESULTS / "AGE_ALLOCATION_TILT_SCENARIOS.csv")
    check(np.allclose(scenarios.K_high_vs_low_young_older_relative_allocation_odds,
                      [0.5, 2.0 / 3.0, 1.0, 1.5, 2.0]), "scenario grid")
    k1 = scenarios.loc[np.isclose(scenarios.K_high_vs_low_young_older_relative_allocation_odds, 1.0)].iloc[0]
    check(np.isclose(k1.coefficient, CORRECTED, atol=1e-12, rtol=0), "K=1 baseline")
    check(float(scenarios.mass_conservation_gap.abs().max()) < 1e-3, "scenario mass conservation")
    check(scenarios.converged.astype(bool).all(), "scenario convergence")
    performed.append("allocation scenarios")

    gate = json.loads((RESULTS / "CROSSWALK_COMPATIBILITY_GATE.json").read_text(encoding="utf-8"))
    check(gate["naive_exact_code_support_with_Webb"] == 410, "naive exact support")
    check(gate["audited_bridge_repaired_support_with_Webb"] == 495, "repaired support")
    check(gate["status"].startswith("FAIL_CLOSED"), "compatibility gate must reject exact-code merge")
    performed.append("crosswalk compatibility gate")

    forbidden_columns = {"CPSIDP", "SERIAL", "PERNUM", "WTFINL", "password", "api_key", "token"}
    for path in RESULTS.glob("*.csv"):
        columns = set(pd.read_csv(path, nrows=0).columns)
        check(not columns.intersection(forbidden_columns), "sensitive column in {}".format(path.name))
    performed.append("no person identifiers, raw weights, or credential columns")

    result = {
        "status": "PASS_BRIDGE_UNCERTAINTY_SELFCHECK",
        "checks": performed,
        "selfcheck_code_sha256": sha256(pathlib.Path(__file__)),
        "execution_receipt_sha256": sha256(RESULTS / "EXECUTION_RECEIPT.json"),
        "private_inputs_rehashed": checked_private,
    }
    # Preserve the stronger SCC receipt when a local verification cannot see
    # licensed inputs.  A run supplying all three private paths replaces it.
    if len(checked_private) == 3:
        (RESULTS / "SELF_CHECK.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(json.dumps(result, indent=2, sort_keys=True))


def parser():
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--microdata", type=pathlib.Path)
    value.add_argument("--repair-microdata", type=pathlib.Path)
    value.add_argument("--preperiod-cells", type=pathlib.Path)
    return value


if __name__ == "__main__":
    run(parser().parse_args())
