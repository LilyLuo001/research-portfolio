#!/usr/bin/env python3
"""Recompute public Gate 3 architecture-reconciliation identities."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


RUN = load_module("yax_architecture_output_runner", HERE / "run_architecture_reconciliation.py")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def close(left: float, right: float, tolerance: float = 1e-12) -> bool:
    return bool(abs(float(left) - float(right)) <= tolerance)


def validate(results: Path) -> dict:
    required = [
        "MODEL_RESULTS.csv", "PAIRED_COMPARISONS.csv",
        "TREATMENT_MEMBERSHIP_AND_SCALING.csv", "MODEL_INFLUENCE.csv",
        "W06_CARRY_FORWARD_VALIDATION.json",
        "W05_UNIT_AND_IMPLEMENTATION_VERIFICATION.json", "MODEL_FAILURES.json",
        "EXECUTION_RECEIPT.json",
    ]
    for name in required:
        require((results / name).is_file(), f"missing output {name}")
    receipt = json.loads((results / "EXECUTION_RECEIPT.json").read_text())
    require(receipt.get("status") == "PASS_GATE3_ARCHITECTURE_RECONCILIATION",
            "execution receipt does not pass")
    for name, expected in receipt["output_hashes"].items():
        require(RUN.sha256_file(results / name) == expected, f"output hash differs: {name}")
    models = pd.read_csv(results / "MODEL_RESULTS.csv", float_precision="round_trip")
    pairs = pd.read_csv(results / "PAIRED_COMPARISONS.csv", float_precision="round_trip")
    members = pd.read_csv(results / "TREATMENT_MEMBERSHIP_AND_SCALING.csv",
                          dtype={"occupation_code": str}, float_precision="round_trip")
    influence = pd.read_csv(results / "MODEL_INFLUENCE.csv",
                            dtype={"cluster_id": str}, float_precision="round_trip")
    failures = json.loads((results / "MODEL_FAILURES.json").read_text())
    w05 = json.loads((results / "W05_UNIT_AND_IMPLEMENTATION_VERIFICATION.json").read_text())
    w06 = json.loads((results / "W06_CARRY_FORWARD_VALIDATION.json").read_text())
    require(len(models) == 56 and models.model_id.nunique() == 56, "model inventory differs")
    require(len(pairs) == 32 and pairs.comparison_id.nunique() == 32,
            "paired inventory differs")
    require(len(members) == 4068, "membership inventory differs")
    require(len(influence) == 56 * (468 + 22), "influence inventory differs")
    require(failures == [], "model failures are nonempty")
    require(w05.get("status") == "PASS_W05_UNIT_AND_IMPLEMENTATION_VERIFICATION",
            "W05 verification does not pass")
    require(w06.get("status") == "PASS_W06_CURRENT_CONTRACT_CARRY_FORWARD",
            "W06 validation does not pass")
    require(not bool(w05["published_implementation_error_attributed"]),
            "unsupported published implementation error was attributed")
    require(models.maximum_normalized_score.max() <= 1e-7, "model score certificate fails")
    require(models.separated_observations.ge(0).all(), "invalid separation count")

    full = models.loc[(models.contract_id == "full_support_rule_A_beta") &
                      (models.functional_form == "categorical")]
    require(len(full) == 2, "full-support beta anchors differ")
    pooled = full.loc[full.structure.eq("pooled"), "coefficient_target"].iloc[0]
    family = full.loc[full.structure.eq("family_month"), "coefficient_target"].iloc[0]
    require(close(pooled, RUN.EXPECTED_POOLED, 1e-8), "pooled beta identity differs")
    require(close(family, RUN.EXPECTED_FAMILY, 1e-8), "family beta identity differs")

    continuous = models.loc[models.functional_form.eq("continuous")]
    require(np.allclose(
        continuous.coefficient_per_raw_unit,
        continuous.coefficient_per_weighted_sd / continuous.raw_weighted_sd,
        rtol=0, atol=1e-14), "raw-unit coefficient transform differs")
    require(np.allclose(
        continuous.occupation_se_per_raw_unit,
        continuous.occupation_se / continuous.raw_weighted_sd,
        rtol=0, atol=1e-14), "raw-unit SE transform differs")

    occ_ids = sorted(influence.loc[influence.cluster_type.eq("occupation"),
                                   "cluster_id"].unique().tolist())
    fam_ids = sorted(influence.loc[influence.cluster_type.eq("family"),
                                   "cluster_id"].unique().tolist())
    require(len(occ_ids) == 468 and len(fam_ids) == 22, "cluster inventory differs")
    draws = RUN.CORE.draw_multiplier_matrices(RUN.DRAWS, 468, 22, RUN.SEED)
    multipliers = {"occupation": draws["occupation_rademacher"],
                   "family": draws["family_rademacher"]}
    by_model: dict[str, dict[str, np.ndarray]] = {}
    model_lookup = models.set_index("model_id")
    maximum_gap = 0.0
    for model_id, row in model_lookup.iterrows():
        block = influence.loc[influence.model_id.eq(model_id)]
        oi = (block.loc[block.cluster_type.eq("occupation")].set_index("cluster_id")
              .reindex(occ_ids).target_influence.to_numpy(float))
        fi = (block.loc[block.cluster_type.eq("family")].set_index("cluster_id")
              .reindex(fam_ids).target_influence.to_numpy(float))
        require(np.all(np.isfinite(oi)) and np.all(np.isfinite(fi)),
                f"nonfinite influence: {model_id}")
        by_model[model_id] = {"occupation": oi, "family": fi}
        for cluster, values in (("occupation", oi), ("family", fi)):
            rebuilt = RUN.CORE.multiplier_interval(
                float(row.coefficient_target), values, multipliers[cluster])
            for field, key in (("se", f"{cluster}_se"),
                               ("lower", f"{cluster}_ci_lower"),
                               ("upper", f"{cluster}_ci_upper"),
                               ("p_value", f"{cluster}_multiplier_p")):
                gap = abs(float(rebuilt[field]) - float(row[key]))
                maximum_gap = max(maximum_gap, gap)
                require(gap <= 1e-12, f"model inference differs: {model_id} {key}")

    maximum_pair_gap = 0.0
    for _, row in pairs.iterrows():
        left = model_lookup.loc[row.left_model]
        right = model_lookup.loc[row.right_model]
        estimate = float(left.coefficient_target - right.coefficient_target)
        require(close(estimate, row.estimate_left_minus_right),
                f"paired estimate differs: {row.comparison_id}")
        for cluster in ("occupation", "family"):
            values = (by_model[row.left_model][cluster] -
                      by_model[row.right_model][cluster])
            rebuilt = RUN.CORE.multiplier_interval(estimate, values, multipliers[cluster])
            for field, key in (("se", f"{cluster}_se"),
                               ("lower", f"{cluster}_ci_lower"),
                               ("upper", f"{cluster}_ci_upper"),
                               ("p_value", f"{cluster}_multiplier_p")):
                gap = abs(float(rebuilt[field]) - float(row[key]))
                maximum_pair_gap = max(maximum_pair_gap, gap)
                require(gap <= 1e-12, f"paired inference differs: {row.comparison_id} {key}")
    require(pairs.common_draws_preserve_covariance.astype(bool).all(),
            "paired comparison lacks common draws")
    return {
        "schema_version": "yax-gate3-architecture-reconciliation-validation-v1",
        "status": "PASS_RECOMPUTED_VALIDATION",
        "model_count": len(models), "paired_comparison_count": len(pairs),
        "membership_rows": len(members), "influence_rows": len(influence),
        "maximum_model_inference_absolute_gap": maximum_gap,
        "maximum_paired_inference_absolute_gap": maximum_pair_gap,
        "canonical_identity": {"pooled": float(pooled), "family_month": float(family)},
        "w05_status": w05["status"], "w06_status": w06["status"],
        "model_failures": len(failures),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = validate(args.results)
    RUN.write_json(args.output, report)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
