#!/usr/bin/env python3
"""Independently reconstruct public Gate 3 characteristic-block outputs."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
DRAWS = 9_999
SEED = 202609085700
EXPECTED_MODELS = {
    "matched_baseline", "matched_computer_only", "matched_family_only",
    "matched_combined", "static_common_baseline", "static_common_computer_use",
    "static_common_remotability", "static_common_wage",
    "static_common_education_requirement", "static_common_routine_task_intensity",
    "static_common_manual_physical", "static_common_all", "static_common_family",
    "static_common_family_all",
}
EXPECTED_COMPARISONS = {
    "computer_only_minus_baseline", "family_only_minus_baseline",
    "combined_minus_computer_only", "combined_minus_family_only",
    "combined_minus_baseline", "computer_use_minus_static_baseline",
    "remotability_minus_static_baseline", "wage_minus_static_baseline",
    "education_requirement_minus_static_baseline",
    "routine_task_intensity_minus_static_baseline",
    "manual_physical_minus_static_baseline", "all_static_minus_baseline",
    "family_minus_static_baseline", "family_all_minus_family",
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CORE = load_module("yax_characteristic_validation_core",
                   HERE.parent / "inference_validation" / "inference_engine.py")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def close(left: float, right: float, tolerance: float = 2e-12) -> float:
    gap = abs(float(left) - float(right))
    require(gap <= tolerance, f"numerical reconstruction gap {gap} exceeds {tolerance}")
    return gap


def influence_vector(frame: pd.DataFrame, model: str, cluster: str,
                     regressor: str) -> np.ndarray:
    selected = frame.loc[
        frame.model_id.eq(model) & frame.cluster_type.eq(cluster)
        & frame.regressor.eq(regressor)
    ].copy()
    require(len(selected) > 1 and not selected.cluster_id.duplicated().any(),
            f"invalid {model}/{cluster}/{regressor} influence")
    selected = selected.sort_values("cluster_id", kind="mergesort")
    return selected.influence.to_numpy(float)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    receipt_path = args.run_dir / "EXECUTION_RECEIPT.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(receipt.get("status") == "PASS_GATE3_CHARACTERISTIC_BLOCK",
            "characteristic receipt does not pass")
    for name, digest in receipt["output_hashes"].items():
        require(sha256_file(args.run_dir / name) == digest,
                f"retained output hash differs for {name}")
    require(receipt["failures"] == 0
            and json.loads((args.run_dir / "MODEL_FAILURES.json").read_text()) == [],
            "model failures are retained")

    models = pd.read_csv(args.run_dir / "MODEL_RESULTS.csv")
    coefficients = pd.read_csv(args.run_dir / "MODEL_COEFFICIENTS.csv")
    influences = pd.read_csv(args.run_dir / "MODEL_INFLUENCE.csv",
                             dtype={"cluster_id": str})
    paired = pd.read_csv(args.run_dir / "PAIRED_MOVEMENTS.csv")
    scaling = pd.read_csv(args.run_dir / "CHARACTERISTIC_SCALING.csv")
    support = pd.read_csv(args.run_dir / "SUPPORT_ACCOUNTING.csv")
    overlap = pd.read_csv(args.run_dir / "COMPUTER_OVERLAP_BY_QUINTILE.csv")
    require(set(models.model_id) == EXPECTED_MODELS and len(models) == len(EXPECTED_MODELS),
            "model inventory differs")
    require(set(paired.comparison) == EXPECTED_COMPARISONS
            and len(paired) == len(EXPECTED_COMPARISONS),
            "paired comparison inventory differs")
    require(set(overlap.beta_quintile.astype(int)) == {1, 2, 3, 4, 5},
            "computer overlap quintiles differ")
    counts = support.set_index("support").occupations.to_dict()
    require(int(counts["computer_use"]) == 455
            and int(counts["remotability"]) == 408
            and int(counts["static_common"]) == 347,
            "support-accounting counts differ")
    require(support.construction_weight_coverage.between(0, 1).all(),
            "support coverage leaves the unit interval")

    maximum_gap = 0.0
    block_cache: dict[str, dict[str, np.ndarray]] = {}
    for block, block_models in models.groupby("block", sort=False):
        first_model = str(block_models.iloc[0].model_id)
        n_occ = len(influence_vector(influences, first_model, "occupation", "Q5_x_post"))
        n_family = len(influence_vector(influences, first_model, "family", "Q5_x_post"))
        seed = SEED if block == "matched_computer_family_2x2" else SEED + 1
        draws = CORE.draw_multiplier_matrices(DRAWS, n_occ, n_family, seed)
        block_cache[block] = {
            "occupation": draws["occupation_rademacher"],
            "family": draws["family_rademacher"],
        }

    coefficient_lookup: dict[tuple[str, str], pd.Series] = {}
    for _, row in coefficients.iterrows():
        key = (str(row.model_id), str(row.regressor))
        require(key not in coefficient_lookup, "duplicate model coefficient row")
        coefficient_lookup[key] = row
        q_occ = influence_vector(influences, key[0], "occupation", "Q5_x_post")
        q_fam = influence_vector(influences, key[0], "family", "Q5_x_post")
        occ = influence_vector(influences, key[0], "occupation", key[1])
        fam = influence_vector(influences, key[0], "family", key[1])
        for observed, expected in [
            (row.occupation_se, np.sqrt(occ @ occ)),
            (row.family_se, np.sqrt(fam @ fam)),
            (row.occupation_covariance_with_Q5, occ @ q_occ),
            (row.family_covariance_with_Q5, fam @ q_fam),
        ]:
            maximum_gap = max(maximum_gap, close(observed, expected))

    for _, row in models.iterrows():
        model = str(row.model_id)
        block = str(row.block)
        coefficient = coefficient_lookup[(model, "Q5_x_post")]
        maximum_gap = max(maximum_gap,
                          close(row.coefficient_Q5_x_post,
                                coefficient.coefficient_standardized))
        for cluster in ("occupation", "family"):
            influence = influence_vector(influences, model, cluster, "Q5_x_post")
            result = CORE.multiplier_interval(
                float(row.coefficient_Q5_x_post), influence,
                block_cache[block][cluster])
            for name in ("se", "ci_lower", "ci_upper"):
                source = f"{cluster}_{name}"
                target = "se" if name == "se" else name.split("_", 1)[1]
                maximum_gap = max(maximum_gap, close(row[source], result[target]))
            maximum_gap = max(maximum_gap,
                              close(row[f"{cluster}_multiplier_p"], result["p_value"]))

    for _, row in paired.iterrows():
        block = str(row.block)
        left = models.set_index("model_id").loc[str(row.left_model)]
        right = models.set_index("model_id").loc[str(row.right_model)]
        estimate = float(left.coefficient_Q5_x_post - right.coefficient_Q5_x_post)
        maximum_gap = max(maximum_gap, close(row.estimate_left_minus_right, estimate))
        for cluster in ("occupation", "family"):
            left_i = influence_vector(influences, str(row.left_model), cluster, "Q5_x_post")
            right_i = influence_vector(influences, str(row.right_model), cluster, "Q5_x_post")
            result = CORE.multiplier_interval(
                estimate, left_i - right_i, block_cache[block][cluster])
            maximum_gap = max(maximum_gap, close(row[f"{cluster}_se"], result["se"]))
            maximum_gap = max(maximum_gap,
                              close(row[f"{cluster}_ci_lower"], result["lower"]))
            maximum_gap = max(maximum_gap,
                              close(row[f"{cluster}_ci_upper"], result["upper"]))
            maximum_gap = max(maximum_gap,
                              close(row[f"{cluster}_multiplier_p"], result["p_value"]))

    computer_scale = scaling.loc[
        scaling.support.eq("computer_maximal")
        & scaling.characteristic.eq("computer_use")
    ]
    require(len(computer_scale) == 1, "computer scaling row differs")
    computer_sd = float(computer_scale.iloc[0].weighted_sd)
    computer_rows = coefficients.loc[
        coefficients.block.eq("matched_computer_family_2x2")
        & coefficients.regressor.eq("computer_use_z_x_post")
    ]
    require(set(computer_rows.model_id) == {"matched_computer_only", "matched_combined"},
            "computer coefficient rows differ")
    for _, row in computer_rows.iterrows():
        maximum_gap = max(maximum_gap,
                          close(row.coefficient_raw_unit,
                                row.coefficient_standardized / computer_sd))
        maximum_gap = max(maximum_gap,
                          close(row.occupation_se_raw_unit,
                                row.occupation_se / computer_sd))
        maximum_gap = max(maximum_gap,
                          close(row.family_se_raw_unit,
                                row.family_se / computer_sd))

    report = {
        "schema_version": "yax-gate3-characteristic-public-validation-v1",
        "status": "PASS_GATE3_CHARACTERISTIC_PUBLIC_VALIDATION",
        "receipt_sha256": sha256_file(receipt_path),
        "models": len(models), "coefficient_rows": len(coefficients),
        "influence_rows": len(influences), "paired_comparisons": len(paired),
        "maximum_recomputed_gap": maximum_gap,
        "support_counts": {str(key): int(value) for key, value in counts.items()},
        "common_draw_covariance_reconstructed": True,
    }
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(json.dumps({"status": report["status"], "models": len(models),
                      "maximum_gap": maximum_gap}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
