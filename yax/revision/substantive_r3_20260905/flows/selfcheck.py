#!/usr/bin/env python3
"""Fail-closed checks for aggregate R3 flow/outcome outputs."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib

import numpy as np
import pandas as pd


PRESPEC_COMMIT = "96801eebad9015e03aae22a599fdf66750b0b0e9"
MDE_MULTIPLIER = 2.8015852181129683


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True, type=pathlib.Path)
    args = parser.parse_args()
    root = args.results
    checks: list[dict] = []

    def require(condition: bool, description: str) -> None:
        checks.append({"description": description, "passed": bool(condition)})
        if not condition:
            raise AssertionError(description)

    receipt = json.loads((root / "EXECUTION_RECEIPT.json").read_text(encoding="utf-8"))
    require(receipt["prespec_commit"] == PRESPEC_COMMIT, "pre-results flow specification commit is authenticated")
    require(receipt["corrected_reconstruction"]["merge_unmatched"] == 0, "corrected weight patch merges without unmatched rows")
    require(receipt["corrected_reconstruction"]["duplicate_corrected_keys"] == 0, "corrected person-month merge keys are unique")
    require(receipt["corrected_reconstruction"]["march_rows_after_replacement"] > 0, "five restored March Basic samples contribute records")
    require(receipt["corrected_reconstruction"]["march_positive_LNKFW1MWT_rows"] > 0, "restored March samples carry adjacent-month weights")
    require(receipt["corrected_reconstruction"]["march_positive_LNKFW1YWT_rows"] > 0, "restored March samples carry adjacent-year weights")
    require(receipt["mapping"]["support_occupations"] == 468, "rebuilt treatment retains authenticated 468-occupation beta/Webb support")
    require(receipt["mapping"]["bridge_max_route_sum_error"] < 1e-10, "bridge route probabilities conserve source mass")
    require(receipt["models_failed"] == 0, "all fixed flow/outcome models completed without substituted specifications")
    require(receipt["stock_flow_calibration_identified"] is False, "receipt does not manufacture a stock-flow calibration")
    require(receipt["no_person_or_household_identifiers_written"] is True, "receipt attests aggregate-only outputs")

    failures = json.loads((root / "MODEL_FAILURES.json").read_text(encoding="utf-8"))
    require(failures == [], "machine-readable model failure registry is empty")
    results = pd.read_csv(root / "FLOW_AND_WORKER_OUTCOME_RESULTS.csv")
    require(results.model_id.is_unique, "each executed model has one canonical numerical row")
    expected_core = {
        f"{horizon}__{margin}__{weighting}"
        for horizon in ["adjacent_month", "twelve_month"]
        for margin in ["employment_exit", "unemployment_entry", "labor_force_exit", "occupational_outflow", "entry_destination"]
        for weighting in ["official", "unweighted", "origin_WTFINL"]
    }
    expected_extra = {
        f"adjacent_month__usual_hours_change_continuing_workers__{weighting}"
        for weighting in ["official", "unweighted", "origin_WTFINL"]
    } | {
        "cross_sectional_month__weekly_earnings_conditional_workers__EARNWT",
        "adjacent_month__employment_exit__official__older_26_30",
    }
    require(set(results.model_id) == expected_core | expected_extra, "fixed model menu is complete and contains no outcome-selected additions")
    require(np.allclose(
        results.normal_theory_MDE80,
        MDE_MULTIPLIER * results.analytic_occupation_cluster_se,
        rtol=1e-11, atol=1e-12,
    ), "every MDE uses the declared two-sided normal-theory multiplier")
    require((results.wild_score_ci_lower <= results.coefficient).all() and (results.coefficient <= results.wild_score_ci_upper).all(),
            "every wild-score interval contains its point estimate")
    require((results.bootstrap_draws == 9_999).all() and (results.bootstrap_seed == 2026090524).all(),
            "all core intervals use the common 9,999-draw seed contract")
    require((results.event_contributing_occupations > 1).all(), "every fitted target has more than one contributing occupation")

    influence = pd.read_csv(root / "TARGET_OCCUPATION_INFLUENCE.csv", dtype={"occ_code": str})
    for model_id, row in results.set_index("model_id").iterrows():
        selected = influence.loc[influence.model_id.eq(model_id)]
        require(len(selected) == int(row.event_contributing_occupations), f"{model_id}: influence rows match contributing occupations")
        require(math.isclose(
            float(np.sqrt(np.square(selected.target_influence).sum())),
            float(row.analytic_occupation_cluster_se), rel_tol=1e-9, abs_tol=1e-11,
        ), f"{model_id}: stored target influences reproduce the occupation-cluster SE")

    counts = pd.read_csv(root / "FLOW_RISK_EVENT_COUNTS.csv")
    for horizon in ["adjacent_month", "twelve_month"]:
        for weighting in ["official", "unweighted", "origin_WTFINL"]:
            block = counts.loc[counts.horizon.eq(horizon) & counts.weighting.eq(weighting)].set_index("margin")
            require(
                int(block.loc["employment_exit", "event_raw_records"])
                == int(block.loc["unemployment_entry", "event_raw_records"])
                + int(block.loc["labor_force_exit", "event_raw_records"]),
                f"{horizon}/{weighting}: unemployment and NILF events exhaust employment exits",
            )

    routes = pd.read_csv(root / "ROUTE_AND_SUPPORT_AUDIT.csv")
    require((routes.route_conservation_error.abs() <= np.maximum(1e-7, routes.absolute_routeable_input_total.abs() * 1e-10)).all(),
            "all fractional route quantities conserve routeable source mass")
    require(((routes.support_retention_rate.isna()) | routes.support_retention_rate.between(0, 1 + 1e-10)).all(),
            "support-retention rates are admissible")

    link = pd.read_csv(root / "LINK_ATTRITION_AUDIT.csv")
    require(set(link.horizon) == {"adjacent_month", "twelve_month"}, "link audit covers both declared horizons")
    require((link.validated_link_rate.dropna().between(0, 1)).all(), "link rates lie in [0,1]")
    require((link.positive_weight_rate_among_validated.dropna().between(0, 1)).all(), "positive-weight retention rates lie in [0,1]")
    transitions = pd.read_csv(root / "LINK_TRANSITION_DIAGNOSTICS.csv")
    require(set(transitions.horizon) == {"adjacent_month", "twelve_month"}, "aging and occupation diagnostics cover both horizons")

    forbidden_headers = {"CPSID", "CPSIDP", "CPSIDV", "SERIAL", "PERNUM"}
    for path in root.glob("*.csv"):
        headers = set(pd.read_csv(path, nrows=0).columns)
        require(not (headers & forbidden_headers), f"{path.name}: no restricted identifier column is written")
    limitations = (root / "OUTCOME_FEASIBILITY_AND_LIMITS.md").read_text(encoding="utf-8").lower()
    require("employer" in limitations and "hiring" in limitations,
            "limitations memo distinguishes CPS flows from employer hiring")

    for filename, expected in receipt["output_hashes"].items():
        require(filename not in {"EXECUTION_RECEIPT.json", "SELF_CHECK.json"}, "receipt avoids circular self-hashes")
        require(sha256(root / filename) == expected, f"{filename}: hash matches execution receipt")

    output = {"status": "PASS", "checks": len(checks), "details": checks}
    (root / "SELF_CHECK.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "checks": len(checks)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
