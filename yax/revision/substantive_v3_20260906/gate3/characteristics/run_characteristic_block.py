#!/usr/bin/env python3
"""Run the Gate 3 matched-support occupational-characteristic block."""
from __future__ import annotations

import argparse
import csv
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
DRAWS = 9_999
SEED = 202609085700
CHARACTERISTICS_SHA256 = "88311c3bc26f00fde4aa792888491ae4a1e340c601d1c62147d52727afbf207c"
MEMBERSHIP_SHA256 = "c76eb85956e4a413e130bab53fe8c50616cf6d7a02c81c266ec369879dd56bc1"
CHARACTERISTICS = {
    "computer_use": "onet_computers_importance",
    "remotability": "dingel_neiman_telework",
    "wage": "log_mean_annual_wage",
    "education_requirement": "required_education_category_index",
    "routine_task_intensity": "rti_autor_dorn",
    "manual_physical": "manual_physical_ability_importance",
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CORE = load_module("yax_characteristic_core", HERE.parent / "inference_validation" /
                   "inference_engine.py")
HH = load_module("yax_characteristic_household", HERE.parent / "inference_validation" /
                 "run_household_refit_batch.py")
ENGINE = load_module("yax_characteristic_engine",
                     ROOT / "dax/memo/power_calcs/young_relative_employment_power.py")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def support_hash(codes: np.ndarray) -> str:
    payload = "".join(f"{value}\n" for value in np.asarray(codes, str).tolist())
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    require(bool(rows), f"refusing to write empty {path.name}")
    fields: list[str] = []
    for row in rows:
        fields.extend(key for key in row if key not in fields)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def weighted_scale(values: np.ndarray, weights: np.ndarray) -> tuple[np.ndarray, dict[str, float]]:
    values = np.asarray(values, float)
    weights = np.asarray(weights, float)
    require(values.shape == weights.shape and np.all(np.isfinite(values))
            and np.all(weights > 0), "invalid characteristic scaling inputs")
    mean = float(np.average(values, weights=weights))
    sd = float(np.sqrt(np.average(np.square(values - mean), weights=weights)))
    require(np.isfinite(sd) and sd > 0, "characteristic scale collapses")
    return (values - mean) / sd, {"weighted_mean": mean, "weighted_sd": sd,
                                  "standardization_weight": float(weights.sum())}


def weighted_corr(left: np.ndarray, right: np.ndarray, weights: np.ndarray) -> float:
    lz, _ = weighted_scale(left, weights)
    rz, _ = weighted_scale(right, weights)
    return float(np.average(lz * rz, weights=weights))


def augment_design(base: Any, controls: dict[str, np.ndarray], months: list[str]) -> Any:
    if not controls:
        return base
    n_occ = len(base.occupation_codes) // len(months)
    post = np.asarray([value >= "2023-01" for value in months], float)
    columns = []
    labels = []
    for name, value in controls.items():
        value = np.asarray(value, float)
        require(value.shape == (n_occ,) and np.all(np.isfinite(value)),
                f"{name} control support differs")
        columns.append(np.repeat(value, len(months)) * np.tile(post, n_occ))
        labels.append(f"{name}_z_x_post")
    return replace(base,
                   regressors=np.column_stack([base.regressors, *columns]),
                   regressor_labels=tuple(base.regressor_labels) + tuple(labels))


def information_diagnostics(fit: Any, design: Any, young: np.ndarray,
                            total: np.ndarray) -> dict[str, float]:
    young = np.asarray(young, float).reshape(-1)
    total = np.asarray(total, float).reshape(-1)
    active, _ = CORE.drop_separated_fixed_effect_groups(
        young, total, design.first_labels, design.second_labels)
    first, n_first = CORE._active_contiguous(design.first_labels, active)
    second, n_second = CORE._active_contiguous(design.second_labels, active)
    x = np.asarray(design.regressors, float)[active]
    probability = np.asarray(fit.fitted_probability, float)[active]
    weight = np.maximum(total[active] * probability * (1.0 - probability), 1e-12)
    rx = ENGINE._weighted_absorb(
        x, weight, first[active], second[active], n_first, n_second)
    information = rx.T @ (weight[:, None] * rx)
    rank = int(np.linalg.matrix_rank(information, tol=1e-10 * max(1.0, np.linalg.norm(information, 2))))
    require(rank == information.shape[0], "characteristic information matrix is rank deficient")
    inverse = np.linalg.inv(information)
    conditional = float(1.0 / inverse[CORE.TARGET_INDEX, CORE.TARGET_INDEX])
    raw_column = ENGINE._weighted_absorb(
        x[:, [CORE.TARGET_INDEX]], weight, first[active], second[active],
        n_first, n_second)[:, 0]
    raw = float(np.sum(weight * np.square(raw_column)))
    diagonal = np.sqrt(np.diag(information))
    correlation = information / np.outer(diagonal, diagonal)
    eigenvalues = np.linalg.eigvalsh((correlation + correlation.T) / 2)
    positive = eigenvalues[eigenvalues > 1e-10]
    require(len(positive) == information.shape[0], "scaled information spectrum collapses")
    result = {
        "fixed_effect_adjusted_raw_target_information": raw,
        "conditional_target_information": conditional,
        "information_retention": conditional / raw,
        "target_vif_like": raw / conditional,
        "information_matrix_rank": rank,
        "information_matrix_columns": information.shape[0],
        "scaled_information_condition_number": float(positive.max() / positive.min()),
    }
    computer_label = "computer_use_z_x_post"
    if computer_label in design.regressor_labels:
        target = CORE.TARGET_INDEX
        computer = design.regressor_labels.index(computer_label)
        other = [index for index in range(x.shape[1]) if index not in (target, computer)]
        pair = rx[:, [target, computer]].copy()
        if other:
            nuisance = rx[:, other]
            gram = nuisance.T @ (weight[:, None] * nuisance)
            pair -= nuisance @ np.linalg.solve(gram, nuisance.T @ (weight[:, None] * pair))
        numerator = float(np.sum(weight * pair[:, 0] * pair[:, 1]))
        denominator = math.sqrt(float(np.sum(weight * np.square(pair[:, 0])))
                                * float(np.sum(weight * np.square(pair[:, 1]))))
        result["partial_information_correlation_Q5_computer"] = numerator / denominator
    return result


def interval(estimate: float, influence: np.ndarray,
             multipliers: np.ndarray) -> dict[str, float]:
    return CORE.multiplier_interval(estimate, influence, multipliers)


def fit_one(model_id: str, structure: str, support: np.ndarray,
            control_names: list[str], arrays: dict[str, np.ndarray],
            young_matrix: np.ndarray, older_matrix: np.ndarray,
            scaled: dict[str, np.ndarray], multipliers: dict[str, np.ndarray],
            block: str) -> dict[str, Any]:
    months = arrays["months"].tolist()
    base = CORE.build_design(arrays["quintiles"][support], arrays["webb_z"][support],
                             arrays["families"][support], months, structure)
    controls = {name: scaled[name][support] for name in control_names}
    design = augment_design(base, controls, months)
    young = young_matrix[support].reshape(-1)
    total = (young_matrix[support] + older_matrix[support]).reshape(-1)
    fit = CORE.fit_with_influence(ENGINE, young, total, design)
    occ_q5 = fit.occupation_influence[:, CORE.TARGET_INDEX]
    fam_q5 = fit.family_influence[:, CORE.TARGET_INDEX]
    occ_interval = interval(fit.estimate, occ_q5, multipliers["occupation"])
    fam_interval = interval(fit.estimate, fam_q5, multipliers["family"])
    row = {
        "block": block, "model_id": model_id, "structure": structure,
        "controls": "|".join(control_names) if control_names else "none",
        "support_occupations": int(support.sum()),
        "support_hash_sha256": support_hash(arrays["occupations"][support]),
        "coefficient_Q5_x_post": fit.estimate,
        "occupation_se": occ_interval["se"],
        "occupation_ci_lower": occ_interval["lower"],
        "occupation_ci_upper": occ_interval["upper"],
        "occupation_multiplier_p": occ_interval["p_value"],
        "family_se": fam_interval["se"],
        "family_ci_lower": fam_interval["lower"],
        "family_ci_upper": fam_interval["upper"],
        "family_multiplier_p": fam_interval["p_value"],
        "iterations": fit.iterations,
        "separated_observations": fit.separated_observation_count,
        **information_diagnostics(fit, design, young, total),
    }
    coefficients = []
    influence_rows = []
    occupation_levels = arrays["occupations"][support].astype(str).tolist()
    family_levels = sorted(set(arrays["families"][support].astype(str).tolist()))
    for index, label in enumerate(design.regressor_labels):
        occ = fit.occupation_influence[:, index]
        fam = fit.family_influence[:, index]
        occ_result = interval(float(fit.beta[index]), occ, multipliers["occupation"])
        fam_result = interval(float(fit.beta[index]), fam, multipliers["family"])
        coefficients.append({
            "block": block, "model_id": model_id, "structure": structure,
            "regressor": label, "coefficient_standardized": float(fit.beta[index]),
            "occupation_se": occ_result["se"],
            "occupation_ci_lower": occ_result["lower"],
            "occupation_ci_upper": occ_result["upper"],
            "family_se": fam_result["se"],
            "family_ci_lower": fam_result["lower"],
            "family_ci_upper": fam_result["upper"],
            "occupation_covariance_with_Q5": float(occ @ occ_q5),
            "family_covariance_with_Q5": float(fam @ fam_q5),
        })
        influence_rows.extend({
            "block": block, "model_id": model_id,
            "cluster_type": "occupation", "cluster_id": cluster,
            "regressor": label, "influence": float(value),
        } for cluster, value in zip(occupation_levels, occ))
        influence_rows.extend({
            "block": block, "model_id": model_id,
            "cluster_type": "family", "cluster_id": cluster,
            "regressor": label, "influence": float(value),
        } for cluster, value in zip(family_levels, fam))
    return {"row": row, "fit": fit, "design": design,
            "coefficients": coefficients, "influence": influence_rows}


def paired_row(comparison: str, left: dict[str, Any], right: dict[str, Any],
               multipliers: dict[str, np.ndarray]) -> dict[str, Any]:
    li = left["fit"].occupation_influence[:, CORE.TARGET_INDEX]
    ri = right["fit"].occupation_influence[:, CORE.TARGET_INDEX]
    lf = left["fit"].family_influence[:, CORE.TARGET_INDEX]
    rf = right["fit"].family_influence[:, CORE.TARGET_INDEX]
    estimate = left["fit"].estimate - right["fit"].estimate
    occ = interval(estimate, li - ri, multipliers["occupation"])
    fam = interval(estimate, lf - rf, multipliers["family"])
    return {
        "block": left["row"]["block"], "comparison": comparison,
        "left_model": left["row"]["model_id"],
        "right_model": right["row"]["model_id"],
        "estimate_left_minus_right": estimate,
        "occupation_se": occ["se"], "occupation_ci_lower": occ["lower"],
        "occupation_ci_upper": occ["upper"], "occupation_multiplier_p": occ["p_value"],
        "family_se": fam["se"], "family_ci_lower": fam["lower"],
        "family_ci_upper": fam["upper"], "family_multiplier_p": fam["p_value"],
        "common_draws_preserve_covariance": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-calibration", type=Path, required=True)
    parser.add_argument("--calibration-receipt", type=Path, required=True)
    parser.add_argument("--characteristics", type=Path, required=True)
    parser.add_argument("--membership", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output_dir.exists(), "refusing to overwrite characteristic output")
    receipt = json.loads(args.calibration_receipt.read_text(encoding="utf-8"))
    require(receipt.get("status") == "PASS_PRIVATE_CALIBRATION_BUILD",
            "private calibration receipt does not pass")
    require(sha256_file(args.private_calibration) == receipt.get("private_npz_sha256"),
            "private calibration hash differs")
    require(sha256_file(args.characteristics) == CHARACTERISTICS_SHA256,
            "characteristics hash differs")
    require(sha256_file(args.membership) == MEMBERSHIP_SHA256,
            "canonical membership hash differs")
    with np.load(args.private_calibration, allow_pickle=False) as loaded:
        arrays = {name: loaded[name] for name in loaded.files}
    occupations = arrays["occupations"].astype(str)
    n_occ, n_month = len(occupations), len(arrays["months"])
    require(n_occ == 468 and n_month == 113, "canonical panel dimensions differ")
    membership = pd.read_csv(args.membership, dtype={"occupation_code": str},
                             float_precision="round_trip")
    membership["occupation_code"] = membership.occupation_code.str.zfill(4)
    membership = membership.set_index("occupation_code").reindex(occupations)
    require(not membership.index.has_duplicates and membership.notna().all().all(),
            "canonical membership does not align")
    require(np.array_equal(membership.beta_quintile.to_numpy(int), arrays["quintiles"]),
            "canonical quintiles differ")
    require(np.allclose(membership.webb_z.to_numpy(float), arrays["webb_z"],
                        rtol=0, atol=1e-12), "canonical Webb values differ")
    characteristics = pd.read_csv(args.characteristics, dtype={"census2018": str})
    characteristics["census2018"] = characteristics.census2018.str.zfill(4)
    require(not characteristics.census2018.duplicated().any(),
            "characteristic occupation codes duplicate")
    characteristics = characteristics.set_index("census2018").reindex(occupations)

    household_count = int(arrays["household_count"][0])
    young, older = HH.cells_from_multiplier(arrays, np.ones(household_count))
    young_matrix = young.reshape(n_occ, n_month)
    older_matrix = older.reshape(n_occ, n_month)
    total_matrix = young_matrix + older_matrix
    pre = np.asarray(["2017-01" <= value <= "2019-12"
                      for value in arrays["months"].tolist()])
    pre_weight = total_matrix[:, pre].sum(axis=1)
    require(np.all(pre_weight > 0), "canonical occupation lacks preperiod stock")

    raw = {name: pd.to_numeric(characteristics[column], errors="coerce").to_numpy(float)
           for name, column in CHARACTERISTICS.items()}
    supports = {name: np.isfinite(value) for name, value in raw.items()}
    computer_support = supports["computer_use"]
    static_support = np.logical_and.reduce(list(supports.values()))
    require(int(computer_support.sum()) == 455, "computer-use support count differs")
    require(int(supports["remotability"].sum()) == 408,
            "remotability support count differs")
    require(int(static_support.sum()) == 347, "static common support count differs")
    require(set(arrays["quintiles"][computer_support].tolist()) == {1, 2, 3, 4, 5}
            and set(arrays["quintiles"][static_support].tolist()) == {1, 2, 3, 4, 5},
            "a characteristic support loses an exposure quintile")

    scaled: dict[str, np.ndarray] = {}
    scaling_rows: list[dict[str, Any]] = []
    for support_name, support in (("computer_maximal", computer_support),
                                  ("static_common", static_support)):
        for name, values in raw.items():
            if not np.all(np.isfinite(values[support])):
                continue
            z, details = weighted_scale(values[support], pre_weight[support])
            full = np.full(n_occ, np.nan)
            full[support] = z
            scaled[f"{support_name}:{name}"] = full
            scaling_rows.append({
                "support": support_name, "characteristic": name,
                "support_occupations": int(support.sum()), **details,
            })

    def block_multipliers(support: np.ndarray, seed: int) -> dict[str, np.ndarray]:
        family_count = len(set(arrays["families"][support].tolist()))
        value = CORE.draw_multiplier_matrices(DRAWS, int(support.sum()), family_count, seed)
        return {"occupation": value["occupation_rademacher"],
                "family": value["family_rademacher"]}

    model_rows: list[dict[str, Any]] = []
    coefficient_rows: list[dict[str, Any]] = []
    influence_rows: list[dict[str, Any]] = []
    paired_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    c02_scaled = {name: value for key, value in scaled.items()
                  if key.startswith("computer_maximal:")
                  for name in [key.split(":", 1)[1]]}
    c02_multipliers = block_multipliers(computer_support, SEED)
    c02_specs = [
        ("matched_baseline", "pooled", []),
        ("matched_computer_only", "pooled", ["computer_use"]),
        ("matched_family_only", "family_month", []),
        ("matched_combined", "family_month", ["computer_use"]),
    ]
    c02: dict[str, dict[str, Any]] = {}
    for model_id, structure, controls in c02_specs:
        try:
            fitted = fit_one(model_id, structure, computer_support, controls, arrays,
                             young_matrix, older_matrix, c02_scaled,
                             c02_multipliers, "matched_computer_family_2x2")
            c02[model_id] = fitted
            model_rows.append(fitted["row"])
            coefficient_rows.extend(fitted["coefficients"])
            influence_rows.extend(fitted["influence"])
        except Exception as error:
            failures.append({"model_id": model_id, "error": repr(error)})
    require(len(c02) == 4, "a mandatory matched 2x2 model failed")
    for name, left, right in [
        ("computer_only_minus_baseline", "matched_computer_only", "matched_baseline"),
        ("family_only_minus_baseline", "matched_family_only", "matched_baseline"),
        ("combined_minus_computer_only", "matched_combined", "matched_computer_only"),
        ("combined_minus_family_only", "matched_combined", "matched_family_only"),
        ("combined_minus_baseline", "matched_combined", "matched_baseline"),
    ]:
        paired_rows.append(paired_row(name, c02[left], c02[right], c02_multipliers))

    c06_scaled = {name: value for key, value in scaled.items()
                  if key.startswith("static_common:")
                  for name in [key.split(":", 1)[1]]}
    c06_multipliers = block_multipliers(static_support, SEED + 1)
    all_controls = list(CHARACTERISTICS)
    c06_specs = [("static_common_baseline", "pooled", [])]
    c06_specs.extend((f"static_common_{name}", "pooled", [name])
                     for name in all_controls)
    c06_specs.extend([
        ("static_common_all", "pooled", all_controls),
        ("static_common_family", "family_month", []),
        ("static_common_family_all", "family_month", all_controls),
    ])
    c06: dict[str, dict[str, Any]] = {}
    for model_id, structure, controls in c06_specs:
        try:
            fitted = fit_one(model_id, structure, static_support, controls, arrays,
                             young_matrix, older_matrix, c06_scaled,
                             c06_multipliers, "static_characteristic_common_support")
            c06[model_id] = fitted
            model_rows.append(fitted["row"])
            coefficient_rows.extend(fitted["coefficients"])
            influence_rows.extend(fitted["influence"])
        except Exception as error:
            failures.append({"model_id": model_id, "error": repr(error)})
    require(len(c06) == len(c06_specs), "a mandatory static characteristic model failed")
    for name in all_controls:
        paired_rows.append(paired_row(
            f"{name}_minus_static_baseline", c06[f"static_common_{name}"],
            c06["static_common_baseline"], c06_multipliers))
    paired_rows.extend([
        paired_row("all_static_minus_baseline", c06["static_common_all"],
                   c06["static_common_baseline"], c06_multipliers),
        paired_row("family_minus_static_baseline", c06["static_common_family"],
                   c06["static_common_baseline"], c06_multipliers),
        paired_row("family_all_minus_family", c06["static_common_family_all"],
                   c06["static_common_family"], c06_multipliers),
    ])

    coverage_rows = []
    total_construction_weight = float(np.sum(arrays["construction_weight"]))
    for name, support in [*supports.items(), ("static_common", static_support)]:
        coverage_rows.append({
            "support": name, "occupations": int(support.sum()),
            "support_hash_sha256": support_hash(occupations[support]),
            "construction_weight_coverage": float(
                np.sum(arrays["construction_weight"][support]) / total_construction_weight),
            "fixed_canonical_assignments": True,
        })
    computer_overlap_rows = []
    beta = arrays["exposure_beta"][computer_support]
    computer = raw["computer_use"][computer_support]
    weights = pre_weight[computer_support]
    q = arrays["quintiles"][computer_support]
    beta_computer_correlation = weighted_corr(beta, computer, weights)
    for quintile in range(1, 6):
        keep = q == quintile
        computer_overlap_rows.append({
            "beta_quintile": quintile, "occupations": int(keep.sum()),
            "preperiod_weight": float(weights[keep].sum()),
            "weighted_mean_beta": float(np.average(beta[keep], weights=weights[keep])),
            "weighted_mean_computer_use": float(np.average(computer[keep], weights=weights[keep])),
            "minimum_computer_use": float(np.min(computer[keep])),
            "maximum_computer_use": float(np.max(computer[keep])),
            "full_support_weighted_beta_computer_correlation": beta_computer_correlation,
        })

    # Add raw O*NET-point units for the computer coefficient without changing
    # the standardized fitting parameterization.
    computer_sd = next(row["weighted_sd"] for row in scaling_rows
                       if row["support"] == "computer_maximal"
                       and row["characteristic"] == "computer_use")
    for row in coefficient_rows:
        if row["block"] == "matched_computer_family_2x2" and row["regressor"] == "computer_use_z_x_post":
            row["raw_unit"] = "one O*NET computer-use importance point"
            row["coefficient_raw_unit"] = row["coefficient_standardized"] / computer_sd
            row["occupation_se_raw_unit"] = row["occupation_se"] / computer_sd
            row["family_se_raw_unit"] = row["family_se"] / computer_sd

    args.output_dir.mkdir(parents=True)
    outputs = {
        "MODEL_RESULTS.csv": model_rows,
        "MODEL_COEFFICIENTS.csv": coefficient_rows,
        "MODEL_INFLUENCE.csv": influence_rows,
        "PAIRED_MOVEMENTS.csv": paired_rows,
        "CHARACTERISTIC_SCALING.csv": scaling_rows,
        "SUPPORT_ACCOUNTING.csv": coverage_rows,
        "COMPUTER_OVERLAP_BY_QUINTILE.csv": computer_overlap_rows,
    }
    for name, rows in outputs.items():
        write_csv(args.output_dir / name, rows)
    (args.output_dir / "MODEL_FAILURES.json").write_text(
        json.dumps(failures, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output_names = [*outputs, "MODEL_FAILURES.json"]
    run_receipt = {
        "schema_version": "yax-gate3-characteristic-block-v1",
        "status": "PASS_GATE3_CHARACTERISTIC_BLOCK" if not failures else "FAILED_MODELS_RETAINED",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                              cwd=ROOT, text=True).strip(),
        "sge_job_id": os.environ.get("JOB_ID"),
        "input_hashes": {
            "private_calibration": receipt["private_npz_sha256"],
            "calibration_receipt": sha256_file(args.calibration_receipt),
            "characteristics": sha256_file(args.characteristics),
            "membership": sha256_file(args.membership),
        },
        "support_counts": {"canonical": n_occ, "computer": int(computer_support.sum()),
                           "remotability": int(supports["remotability"].sum()),
                           "static_common": int(static_support.sum()),
                           "historical_all_including_superseded_shortfall": 341},
        "model_count": len(model_rows), "coefficient_rows": len(coefficient_rows),
        "influence_rows": len(influence_rows),
        "paired_comparisons": len(paired_rows), "failures": len(failures),
        "draws": DRAWS, "common_draws_within_block": True,
        "output_hashes": {name: sha256_file(args.output_dir / name)
                          for name in output_names},
        "privacy": "outputs contain coefficients and aggregate diagnostics only",
    }
    (args.output_dir / "EXECUTION_RECEIPT.json").write_text(
        json.dumps(run_receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": run_receipt["status"],
                      "models": len(model_rows), "failures": len(failures)},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
