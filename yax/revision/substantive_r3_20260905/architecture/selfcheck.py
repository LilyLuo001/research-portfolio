#!/usr/bin/env python3
"""Mechanical checks for the corrected-calendar architecture package."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

import numpy as np
import pandas as pd


PRIMARY_SUPPORT_HASH = "11ec58ab1004cd83d62c57785f6c0dd3ee5a8abf08b7f71a3b664e91ded8333b"
CHAR_SUPPORT_HASH = "12e4bdcdc7958ec8a52b06762585d4887743963ddcbca7de1223b2eea44a5aca"
TOLERANCE = 1e-10


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def run(results_dir: pathlib.Path) -> dict:
    checks: list[dict] = []

    def require(condition: bool, name: str, detail="") -> None:
        checks.append({"name": name, "pass": bool(condition), "detail": str(detail)})

    required = [
        "CONSTRUCTION_IDENTITY_AUDIT.json",
        "LAMBDA_GRID_RESULTS.csv",
        "LAMBDA_GRID_MEMBERSHIP.csv",
        "LAMBDA_GRID_CENTERED_DRAWS.csv",
        "LAMBDA_PAIRED_DIFFERENCES.csv",
        "LAMBDA_QUINTILE_TRANSITIONS.csv",
        "LAMBDA_TAIL_OVERLAP.csv",
        "LAMBDA_NAMED_TAIL_CHANGES.csv",
        "CHARACTERISTIC_CORRELATIONS.csv",
        "CHARACTERISTIC_SCALING.csv",
        "CHARACTERISTIC_CONDITIONING_RESULTS.csv",
        "CHARACTERISTIC_CONDITIONING_COEFFICIENTS.csv",
        "CHARACTERISTIC_CONDITIONING_PAIRED.csv",
        "CHARACTERISTIC_CONDITIONING_DRAWS.csv",
        "PRIMITIVE_JOINT_RESULTS.csv",
        "PRIMITIVE_JOINT_COVARIANCE.csv",
        "PRIMITIVE_JOINT_CENTERED_DRAWS.csv",
        "PRIMITIVE_ILLUSTRATIVE_CONTRASTS.csv",
        "WEBB_AVAILABILITY_RESULTS.csv",
        "WEBB_SAME_SUPPORT_PAIRED_DIFFERENCE.csv",
        "WEBB_SUPPORT_ADDITIONS.csv",
        "WEBB_SUPPORT_CHANGE.json",
        "ARCHIVED_REPARAMETERIZATION_AUDIT.json",
        "ARCHIVED_REPARAMETERIZATION_AUDIT.md",
        "AGE_SPECIFIC_CROSSWALK_BLOCKER.json",
        "AGE_SPECIFIC_CROSSWALK_BLOCKER.md",
        "MODEL_FAILURES.json",
        "RESULTS_SUMMARY.md",
        "EXECUTION_RECEIPT.json",
    ]
    for name in required:
        require((results_dir / name).is_file(), f"required output: {name}")
    if not all(item["pass"] for item in checks):
        result = {"status": "FAIL", "checks": checks}
        (results_dir / "SELF_CHECK.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        raise SystemExit("missing required architecture outputs")

    receipt = json.loads((results_dir / "EXECUTION_RECEIPT.json").read_text(encoding="utf-8"))
    identity = json.loads((results_dir / "CONSTRUCTION_IDENTITY_AUDIT.json").read_text(encoding="utf-8"))
    grid = pd.read_csv(results_dir / "LAMBDA_GRID_RESULTS.csv")
    members = pd.read_csv(results_dir / "LAMBDA_GRID_MEMBERSHIP.csv", dtype={"occupation_code": str})
    draws = pd.read_csv(results_dir / "LAMBDA_GRID_CENTERED_DRAWS.csv")
    pairs = pd.read_csv(results_dir / "LAMBDA_PAIRED_DIFFERENCES.csv")
    transitions = pd.read_csv(results_dir / "LAMBDA_QUINTILE_TRANSITIONS.csv")
    overlaps = pd.read_csv(results_dir / "LAMBDA_TAIL_OVERLAP.csv")
    correlations = pd.read_csv(results_dir / "CHARACTERISTIC_CORRELATIONS.csv")
    conditioning = pd.read_csv(results_dir / "CHARACTERISTIC_CONDITIONING_RESULTS.csv")
    conditioning_pairs = pd.read_csv(results_dir / "CHARACTERISTIC_CONDITIONING_PAIRED.csv")
    primitive = pd.read_csv(results_dir / "PRIMITIVE_JOINT_RESULTS.csv")
    covariance = pd.read_csv(results_dir / "PRIMITIVE_JOINT_COVARIANCE.csv")
    primitive_draws = pd.read_csv(results_dir / "PRIMITIVE_JOINT_CENTERED_DRAWS.csv")
    primitive_contrasts = pd.read_csv(results_dir / "PRIMITIVE_ILLUSTRATIVE_CONTRASTS.csv")
    webb = pd.read_csv(results_dir / "WEBB_AVAILABILITY_RESULTS.csv")
    archive = json.loads((results_dir / "ARCHIVED_REPARAMETERIZATION_AUDIT.json").read_text(encoding="utf-8"))
    blocker = json.loads((results_dir / "AGE_SPECIFIC_CROSSWALK_BLOCKER.json").read_text(encoding="utf-8"))
    failures = json.loads((results_dir / "MODEL_FAILURES.json").read_text(encoding="utf-8"))

    require(receipt["status"] == "PASS_ARCHITECTURE_AUDIT", "execution receipt passes")
    require(receipt["contract_validation"]["support_hash_sha256"] == PRIMARY_SUPPORT_HASH,
            "primary support hash")
    require(receipt["contract_validation"]["support_count"] == 468, "primary support count")
    require(receipt["contract_validation"]["outcome_months"] == 113, "corrected calendar count")
    require(receipt["contract_validation"]["preperiod_months"] == 71, "corrected preperiod count")
    require(receipt["contract_validation"]["route_conservation_pass"], "route conservation")
    require(receipt["bootstrap"]["draws"] == 9999, "bootstrap draw count")
    require(receipt["bootstrap"]["same_ordered_support_uses_common_multiplier_matrix"],
            "common multipliers recorded")
    require(failures == [], "zero model failures", failures)

    require(identity["all_identity_checks_pass"], "identity audit passes")
    require(identity["maximum_absolute_raw_score_gap"] <= TOLERANCE, "raw beta identity")
    require(identity["lambda_half_membership_mismatch_count"] == 0, "lambda half membership")
    for key in (
        "lambda_half_cut_maximum_absolute_gap",
        "lambda_half_categorical_coefficient_gap",
        "lambda_half_categorical_influence_maximum_absolute_gap",
        "lambda_half_fixed_continuous_coefficient_gap",
        "lambda_half_fixed_continuous_influence_maximum_absolute_gap",
        "lambda_half_fixed_vs_restandardized_score_maximum_absolute_gap",
        "base03_coefficient_gap",
    ):
        require(abs(identity[key]) <= TOLERANCE, f"identity tolerance: {key}", identity[key])

    expected_lambda = {0.0, 0.25, 0.5, 0.75, 1.0}
    require(len(grid) == 5 and set(grid["lambda"]) == expected_lambda, "five lambda rows")
    require(len(members) == 5 * 468, "complete lambda membership")
    require(set(members.groupby("lambda").size()) == {468}, "468 occupations at every lambda")
    require(len(draws) == 9999, "lambda draw representation complete")
    require(len(pairs) == 30, "all ten pairwise contrasts in three model families")
    require(pairs.common_multiplier_draws.astype(bool).all(), "paired lambda common draws")
    require(len(transitions) == 10 * 25, "complete pairwise quintile transition matrices")
    require(len(overlaps) == 10, "complete pairwise tail overlap")

    require(len(correlations) == 10, "five-by-two characteristic correlations")
    require((correlations.support_occupations == 408).all(), "correlation support count")
    require(set(correlations.support_hash_sha256) == {CHAR_SUPPORT_HASH}, "correlation support hash")
    require(len(conditioning) == 4, "four focused conditioning models")
    require((conditioning.support_occupations == 408).all(), "conditioning support count")
    require(set(conditioning.support_hash_sha256) == {CHAR_SUPPORT_HASH}, "conditioning support hash")
    require(len(conditioning_pairs) == 3, "three augmented-minus-base paired contrasts")
    require(conditioning_pairs.common_multiplier_draws.astype(bool).all(),
            "conditioning uses common draws")

    require(len(primitive) == 6, "raw and standardized three-term primitive results")
    require(set(primitive.units) == {"raw", "standardized"}, "primitive unit presentations")
    require(len(covariance) == 18, "two complete three-by-three covariance matrices")
    require(len(primitive_draws) == 9999, "primitive common draws complete")
    require(len(primitive_contrasts) == 3, "three illustrative primitive contrasts")
    require((primitive_contrasts.estimate_gap.abs() <= 1e-7).all(),
            "raw-standardized illustrative estimates agree")
    require((primitive_contrasts.centered_draw_maximum_absolute_gap.abs() <= 1e-7).all(),
            "raw-standardized illustrative draws agree")

    require(len(webb) == 3, "three Webb availability rows")
    fixed = webb.loc[webb.support_occupations.eq(468)]
    require(len(fixed) == 2, "two fixed-support Webb rows")
    require(fixed.support_hash_sha256.nunique() == 1 and fixed.support_hash_sha256.iloc[0] == PRIMARY_SUPPORT_HASH,
            "Webb same-support hash")
    require(bool(receipt["webb_support_change"]["paired_inference_reported"]) is False,
            "no paired inference on support change")

    require(archive["status"] == "ARCHIVED_PROVENANCE_ONLY_NOT_SCIENTIFIC_EVIDENCE",
            "F/G-A/E archived only")
    require(archive["new_outcome_models_fit_here"] == 0, "no archived-basis outcome refit")
    require(archive["mobility_or_rematching_reopened"] is False, "mobility not reopened")
    require(blocker["status"] == "BLOCKED_NO_GENUINE_AGE_SPECIFIC_VALIDATION_DATA",
            "age-specific bridge precisely blocked")
    require(blocker["new_age_specific_shares_estimated"] is False,
            "no age-specific share fabricated")

    for name, expected_hash in receipt["output_hashes"].items():
        require((results_dir / name).is_file(), f"hashed output exists: {name}")
        require(sha256(results_dir / name) == expected_hash, f"hashed output authenticates: {name}")
    require("SELF_CHECK.json" not in receipt["output_hashes"], "self-check excluded from receipt hash set")
    require("EXECUTION_RECEIPT.json" not in receipt["output_hashes"], "receipt excluded from own hash set")

    passed = all(check["pass"] for check in checks)
    result = {
        "status": "PASS" if passed else "FAIL",
        "checks_passed": sum(check["pass"] for check in checks),
        "checks_total": len(checks),
        "checks": checks,
    }
    (results_dir / "SELF_CHECK.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not passed:
        failed = [check for check in checks if not check["pass"]]
        raise SystemExit(f"architecture self-check failed: {failed}")
    print(json.dumps({"status": result["status"], "checks": len(checks)}, sort_keys=True))
    return result


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--results-dir", type=pathlib.Path, required=True)
    return value


if __name__ == "__main__":
    run(parser().parse_args().results_dir)
