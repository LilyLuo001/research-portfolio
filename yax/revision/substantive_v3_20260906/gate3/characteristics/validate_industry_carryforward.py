#!/usr/bin/env python3
"""Authenticate and re-express the prior protected industry-cell run for V3.

This program reads public retained outputs only.  It does not refit the model or
read CPS microdata.  The carry-forward is allowed only when the prior receipt,
all receipt-governed outputs, the current canonical treatment membership, and
the paired score algebra all reproduce.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


EXPECTED_MODELS = {
    "valid_industry_aggregate_baseline",
    "industry_cell_baseline",
    "industry_conditioned",
}
EXPECTED_CONTRASTS = {
    "industry_cell_minus_valid_industry_aggregate",
    "industry_conditioned_minus_industry_cell",
    "industry_conditioned_minus_valid_industry_aggregate",
}
EXPECTED_MEMBERSHIP_SHA256 = (
    "c76eb85956e4a413e130bab53fe8c50616cf6d7a02c81c266ec369879dd56bc1"
)
Z975 = 1.959963984540054
Z80 = 0.8416212335729143


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def quantile_higher(values: np.ndarray, q: float) -> float:
    try:
        return float(np.quantile(values, q, method="higher"))
    except TypeError:  # NumPy before 1.22
        return float(np.quantile(values, q, interpolation="higher"))


def close(observed: float, expected: float, tolerance: float = 2e-12) -> float:
    gap = abs(float(observed) - float(expected))
    require(gap <= tolerance,
            f"numerical reconstruction gap {gap} exceeds {tolerance}")
    return gap


def vector(frame: pd.DataFrame, model: str) -> np.ndarray:
    selected = frame.loc[frame.model.eq(model)].copy()
    require(len(selected) == 468, f"{model} does not have 468 occupation scores")
    require(not selected.occupation_code.duplicated().any(),
            f"{model} has duplicate occupation scores")
    return selected.sort_values("occupation_code", kind="mergesort").target_influence.to_numpy(float)


def scalar_reconstruction(estimate: float, influence: np.ndarray,
                          signs: np.ndarray) -> dict[str, float]:
    se = float(np.sqrt(influence @ influence))
    shifts = signs @ influence
    critical = quantile_higher(np.abs(shifts / se), 0.95)
    return {
        "estimate": float(estimate),
        "analytic_se": se,
        "bootstrap_se": float(np.std(shifts, ddof=1)),
        "ci_lower": float(estimate - critical * se),
        "ci_upper": float(estimate + critical * se),
        "bootstrap_p_value": float(
            (1 + np.sum(np.abs(shifts / se) >= abs(estimate / se))) /
            (len(shifts) + 1)
        ),
        "critical": critical,
        "mde80": float((Z975 + Z80) * se),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prior-results", type=Path, required=True)
    parser.add_argument("--current-membership", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    receipt_path = args.prior_results / "EXECUTION_RECEIPT.json"
    selfcheck_path = args.prior_results / "SELF_CHECK.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    selfcheck = json.loads(selfcheck_path.read_text(encoding="utf-8"))
    require(receipt.get("failures") == [], "prior protected run retained failures")
    require(selfcheck.get("status") == "PASS"
            and selfcheck.get("passed") == selfcheck.get("total") == 81,
            "prior public self-check is not 81/81 PASS")
    for name, expected in receipt["output_hashes"].items():
        require(sha256_file(args.prior_results / name) == expected,
                f"prior receipt hash differs for {name}")

    current_membership_hash = sha256_file(args.current_membership)
    require(current_membership_hash == EXPECTED_MEMBERSHIP_SHA256,
            "current membership is not the canonical 468-occupation file")
    require(receipt["input_hashes"]["membership"] == current_membership_hash,
            "prior and current treatment membership bytes differ")

    contract = json.loads(
        (args.prior_results / "INFERENCE_CONTRACT.json").read_text(encoding="utf-8")
    )
    require(contract["draws"] == 9_999
            and contract["seeds"]["industry"] == 2026090552
            and contract["common_within_each_paired_family"] is True,
            "prior industry inference contract differs")
    models_all = pd.read_csv(args.prior_results / "HETEROGENEITY_MODEL_RESULTS.csv")
    paired_all = pd.read_csv(args.prior_results / "HETEROGENEITY_PAIRED_DIFFERENCES.csv")
    influences = pd.read_csv(
        args.prior_results / "MODEL_OCCUPATION_INFLUENCE.csv",
        dtype={"occupation_code": str}, keep_default_na=False,
    )
    models = models_all.loc[models_all.model.isin(EXPECTED_MODELS)].copy()
    paired = paired_all.loc[paired_all.contrast.isin(EXPECTED_CONTRASTS)].copy()
    require(set(models.model) == EXPECTED_MODELS and len(models) == 3,
            "industry model inventory differs")
    require(set(paired.contrast) == EXPECTED_CONTRASTS and len(paired) == 3,
            "industry paired inventory differs")
    require(set(influences.loc[influences.model.isin(EXPECTED_MODELS), "model"])
            == EXPECTED_MODELS, "industry influence inventory differs")

    signs = np.random.default_rng(2026090552).choice(
        np.array([-1.0, 1.0]), size=(9_999, 468)
    )
    maximum_gap = 0.0
    carried_models: list[dict] = []
    model_lookup = models.set_index("model")
    influence_lookup: dict[str, np.ndarray] = {}
    for model in sorted(EXPECTED_MODELS):
        row = model_lookup.loc[model]
        influence = vector(influences, model)
        influence_lookup[model] = influence
        reconstructed = scalar_reconstruction(float(row.coefficient), influence, signs)
        for source, target in [
            ("analytic_occupation_cluster_se", "analytic_se"),
            ("bootstrap_se", "bootstrap_se"),
            ("ci_lower", "ci_lower"), ("ci_upper", "ci_upper"),
            ("bootstrap_p_value", "bootstrap_p_value"),
            ("bootstrap_critical", "critical"),
            ("normal_theory_mde80", "mde80"),
        ]:
            maximum_gap = max(maximum_gap, close(row[source], reconstructed[target]))
        carried_models.append({
            "model": model,
            "panel": row.panel,
            "coefficient_Q5_x_post": float(row.coefficient),
            "occupation_cluster_se": float(row.analytic_occupation_cluster_se),
            "ci_lower": float(row.ci_lower),
            "ci_upper": float(row.ci_upper),
            "bootstrap_p_value": float(row.bootstrap_p_value),
            "occupations": int(row.clusters),
            "row_fixed_effects": int(row.row_fixed_effects),
            "second_fixed_effects": int(row.second_fixed_effects),
            "slope_parameters": int(row.slope_parameters),
            "conditional_target_information": float(row.conditional_target_information),
            "relative_information_to_full_microdata_baseline": float(
                row.relative_information_to_full_microdata_baseline
            ),
            "interpretation": (
                "different industry-cell objective" if model == "industry_cell_baseline"
                else "descriptive broad-industry conditioning" if model == "industry_conditioned"
                else "valid-industry occupation-month reference"
            ),
        })

    carried_pairs: list[dict] = []
    for _, row in paired.sort_values("contrast", kind="mergesort").iterrows():
        left = str(row.left_model)
        right = str(row.right_model)
        estimate = float(model_lookup.at[left, "coefficient"] - model_lookup.at[right, "coefficient"])
        reconstructed = scalar_reconstruction(
            estimate, influence_lookup[left] - influence_lookup[right], signs
        )
        for source, target in [
            ("coefficient_difference", "estimate"),
            ("paired_analytic_se", "analytic_se"),
            ("paired_bootstrap_se", "bootstrap_se"),
            ("paired_ci_lower", "ci_lower"),
            ("paired_ci_upper", "ci_upper"),
            ("paired_bootstrap_p_value", "bootstrap_p_value"),
            ("paired_bootstrap_critical", "critical"),
            ("normal_theory_paired_mde80", "mde80"),
        ]:
            maximum_gap = max(maximum_gap, close(row[source], reconstructed[target]))
        carried_pairs.append({
            "contrast": row.contrast,
            "left_model": left, "right_model": right,
            "coefficient_difference": float(row.coefficient_difference),
            "paired_occupation_se": float(row.paired_analytic_se),
            "paired_ci_lower": float(row.paired_ci_lower),
            "paired_ci_upper": float(row.paired_ci_upper),
            "paired_bootstrap_p_value": float(row.paired_bootstrap_p_value),
            "paired_mde80": float(row.normal_theory_paired_mde80),
            "common_occupation_multipliers": True,
            "interpretation": "descriptive sensitivity; no causal industry share",
        })

    args.output_dir.mkdir(parents=True, exist_ok=True)
    model_path = args.output_dir / "INDUSTRY_CURRENT_CONTRACT_RESULTS.csv"
    paired_path = args.output_dir / "INDUSTRY_CURRENT_CONTRACT_PAIRED.csv"
    pd.DataFrame(carried_models).to_csv(model_path, index=False, lineterminator="\n")
    pd.DataFrame(carried_pairs).to_csv(paired_path, index=False, lineterminator="\n")
    report = {
        "schema_version": "yax-gate3-industry-carryforward-v1",
        "status": "PASS_GATE3_INDUSTRY_CARRYFORWARD",
        "source_kind": "authenticated public carry-forward; no refit",
        "prior_receipt_sha256": sha256_file(receipt_path),
        "prior_selfcheck_sha256": sha256_file(selfcheck_path),
        "current_membership_sha256": current_membership_hash,
        "models": len(carried_models),
        "paired_comparisons": len(carried_pairs),
        "occupation_multiplier_draws": 9_999,
        "occupation_multiplier_seed": 2026090552,
        "maximum_recomputed_gap": maximum_gap,
        "protected_microdata_read": False,
        "output_hashes": {
            model_path.name: sha256_file(model_path),
            paired_path.name: sha256_file(paired_path),
        },
    }
    report_path = args.output_dir / "VALIDATION_REPORT.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps({
        "status": report["status"], "models": report["models"],
        "paired_comparisons": report["paired_comparisons"],
        "maximum_gap": maximum_gap,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
