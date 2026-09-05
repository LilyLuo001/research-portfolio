#!/usr/bin/env python3
"""Automated integrity checks for CHAR-03/CHAR-04 aggregate outputs."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

import numpy as np
import pandas as pd


EXPECTED_BASELINE = -0.1321094508


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def run(results: pathlib.Path) -> int:
    checks = []

    def check(name: str, condition: bool, detail=""):
        checks.append({"check": name, "passed": bool(condition), "detail": str(detail)})

    required = [
        "EXECUTION_RECEIPT.json", "MICRODATA_SCAN_RECEIPT.json", "SUPPORT_SUMMARY.json",
        "HETEROGENEITY_MODEL_RESULTS.csv", "HETEROGENEITY_PAIRED_DIFFERENCES.csv",
        "INDUSTRY_SUPPORT.csv", "EDUCATION_SUPPORT.csv", "AGE_SUPPORT.csv",
        "SIMULTANEOUS_INTERVALS.csv", "TARGET_COVARIANCE_MATRICES.csv",
        "MODEL_OCCUPATION_INFLUENCE.csv", "AGE_EQUALITY_TEST.csv",
        "AGE_EDUCATION_COMPOSITION_BY_YEAR_QUINTILE.csv",
        "AGE_EDUCATION_COMPOSITION_BY_PERIOD_QUINTILE.csv", "MODEL_FAILURES.json",
        "INFERENCE_CONTRACT.json",
    ]
    for name in required:
        check(f"required_{name}", (results / name).is_file())
    if not all(item["passed"] for item in checks):
        payload = {"status": "FAIL", "checks": checks}
        (results / "SELF_CHECK.json").write_text(json.dumps(payload, indent=2) + "\n")
        return 1

    receipt = json.loads((results / "EXECUTION_RECEIPT.json").read_text())
    support = json.loads((results / "SUPPORT_SUMMARY.json").read_text())
    inference = json.loads((results / "INFERENCE_CONTRACT.json").read_text())
    failures = json.loads((results / "MODEL_FAILURES.json").read_text())
    models = pd.read_csv(results / "HETEROGENEITY_MODEL_RESULTS.csv")
    paired = pd.read_csv(results / "HETEROGENEITY_PAIRED_DIFFERENCES.csv")
    simultaneous = pd.read_csv(results / "SIMULTANEOUS_INTERVALS.csv")
    influence = pd.read_csv(results / "MODEL_OCCUPATION_INFLUENCE.csv", dtype={"occupation_code": str})
    covariance = pd.read_csv(results / "TARGET_COVARIANCE_MATRICES.csv")
    composition_period = pd.read_csv(results / "AGE_EDUCATION_COMPOSITION_BY_PERIOD_QUINTILE.csv")

    baseline = models.loc[models.model.eq("full_microdata_rebuilt_baseline")]
    check("one_rebuilt_baseline", len(baseline) == 1, len(baseline))
    if len(baseline) == 1:
        check("rebuilt_baseline_exact", np.isclose(float(baseline.iloc[0].coefficient), EXPECTED_BASELINE, atol=5e-9, rtol=0), baseline.iloc[0].coefficient)
    check("calendar_113", receipt["calendar"]["static_months"] == 113)
    check("preperiod_71", receipt["calendar"]["preperiod_months"] == 71)
    check("october_2025_absent", receipt["calendar"]["October_2025_present"] is False)
    check("base_support_468", support["BASE03_occupations"] == 468)
    check("industry_support_nonempty", support["industry_preconnected_occupations"] > 0)
    check("education_support_nonempty", support["education_common_support_occupations"] > 0)
    check("age_support_nonempty", support["age_common_support_occupations"] > 0)
    check("thirteen_industries_declared", len(support["industry_groups"]) == 13, support["industry_groups"])
    check("draws_9999", inference["draws"] == 9999)
    check("common_multipliers", inference["common_within_each_paired_family"] is True)
    check("paired_common_draw_flag", paired.common_occupation_multipliers.astype(bool).all())
    check("paired_ci_order", (paired.paired_ci_lower <= paired.coefficient_difference).all() and (paired.coefficient_difference <= paired.paired_ci_upper).all())
    check("paired_mde_positive", (paired.normal_theory_paired_mde80 > 0).all())
    check("model_ci_order", (models.ci_lower <= models.coefficient).all() and (models.coefficient <= models.ci_upper).all())
    check("model_information_positive", (models.conditional_target_information > 0).all())
    check("model_rank_full", (models.information_matrix_rank == models.information_matrix_columns).all())
    check("simultaneous_ci_order", (simultaneous.simultaneous_ci_lower <= simultaneous.coefficient).all() and (simultaneous.coefficient <= simultaneous.simultaneous_ci_upper).all())
    check("education_family_two", (simultaneous.family == "BA_plus_and_non_BA").sum() == 2)
    check("age_family_four", (simultaneous.family == "single_ages_22_23_24_25").sum() == 4)
    check("education_pair_present", paired.contrast.eq("BA_plus_minus_non_BA").sum() == 1)
    check("four_age_pairs_present", paired.contrast.str.match(r"age_(22|23|24|25)_minus_pooled_22_25").sum() == 4)
    if failures:
        check("industry_failure_serialized", any(item.get("workstream") == "CHAR-03" for item in failures), failures)
    else:
        expected_industry = {"valid_industry_aggregate_baseline", "industry_cell_baseline", "industry_conditioned"}
        check("industry_models_complete", expected_industry.issubset(set(models.model)), set(models.model))
        check("industry_pairs_complete", paired.contrast.str.startswith("industry_").sum() == 3)
    expected_education = {"education_common_support_pooled", "education_BA_plus", "education_non_BA"}
    check("education_models_complete", expected_education.issubset(set(models.model)), set(models.model))
    expected_age = {"age_common_support_22_25_pooled", "exact_age_22_vs_26_65", "exact_age_23_vs_26_65", "exact_age_24_vs_26_65", "exact_age_25_vs_26_65"}
    check("age_models_complete", expected_age.issubset(set(models.model)), set(models.model))
    check("influence_models_match", set(models.model) == set(influence.model), (set(models.model) - set(influence.model), set(influence.model) - set(models.model)))
    check("covariance_symmetric_rows", len(covariance) == 20, len(covariance))
    check("composition_two_periods_five_quintiles", len(composition_period) == 10, len(composition_period))
    check("composition_shares_bounded", composition_period.filter(regex="share").apply(lambda x: x.between(0, 1)).all().all())
    scan = receipt["scan"]
    check("route_early_conserved", abs(scan["early_route_conservation_absolute_gap"]) < max(1.0, scan["early_matched_source_weight"]) * 1e-10)
    check("route_current_conserved", abs(scan["current_route_conservation_absolute_gap"]) < max(1.0, scan["current_source_weight"]) * 1e-10)
    for name, expected in receipt["output_hashes"].items():
        check(f"hash_{name}", sha256(results / name) == expected)
    combined_text = "\n".join(path.read_text(errors="ignore") for path in results.iterdir() if path.is_file())
    check("no_private_absolute_path", "/projectnb/" not in combined_text and "/project/econdept/" not in combined_text)

    passed = sum(item["passed"] for item in checks)
    payload = {"status": "PASS" if passed == len(checks) else "FAIL", "passed": passed, "total": len(checks), "checks": checks}
    (results / "SELF_CHECK.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "passed": passed, "total": len(checks)}, indent=2))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=pathlib.Path, required=True)
    sys.exit(run(parser.parse_args().results_dir))
