#!/usr/bin/env python3
"""Run current-contract non-lambda architecture comparisons."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import itertools
import json
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
SEED = 202609087301
EXPECTED_POOLED = -0.13210945079219025
EXPECTED_FAMILY = -0.021674952018246537
EXPECTED_OCCUPATIONS = 468
EXPECTED_MONTHS = 113


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


MAP = load_module("yax_architecture_mapping_helpers",
                  HERE.parent / "mapping" / "run_mapping_sensitivity.py")
CORE = MAP.CORE
ENGINE = MAP.ENGINE


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    require(bool(rows), f"refusing to write empty {path.name}")
    fields: list[str] = []
    for row in rows:
        fields.extend(key for key in row if key not in fields)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_continuous_design(score_z: np.ndarray, webb_z: np.ndarray,
                            families: np.ndarray, months: list[str],
                            structure: str) -> Any:
    score_z = np.asarray(score_z, float)
    webb_z = np.asarray(webb_z, float)
    families = np.asarray(families, str)
    n_occ = len(score_z)
    n_month = len(months)
    require(n_occ > 4 and webb_z.shape == (n_occ,), "continuous attributes differ")
    require(structure in {"pooled", "family_month"}, "unknown structure")
    post = np.asarray([value >= "2023-01" for value in months], bool)
    row_post = np.tile(post, n_occ)
    regressors = np.column_stack([
        np.repeat(score_z, n_month) * row_post,
        np.repeat(webb_z, n_month) * row_post,
    ])
    occupation_codes = np.repeat(np.arange(n_occ), n_month)
    family_levels = {value: index for index, value in enumerate(sorted(set(families)))}
    family_codes = np.repeat(np.asarray([family_levels[value] for value in families]), n_month)
    first = occupation_codes.astype(object)
    if structure == "pooled":
        second = np.tile(np.arange(n_month), n_occ).astype(object)
    else:
        month_codes = np.tile(np.arange(n_month), n_occ)
        second = (family_codes * n_month + month_codes).astype(object)
    return CORE.ModelDesign(
        structure=structure, regressors=regressors,
        first_labels=first, second_labels=second,
        occupation_codes=occupation_codes, family_codes=family_codes,
        regressor_labels=("exposure_z_x_post", "Webb_z_x_post"),
        focal_target_index=0,
    )


def fit_continuous(model_id: str, structure: str, young: np.ndarray,
                   older: np.ndarray, keep: np.ndarray, score_z: np.ndarray,
                   webb_z: np.ndarray, raw_mean: float, raw_sd: float,
                   raw_min: float, raw_max: float, families: np.ndarray,
                   occupations: np.ndarray, months: list[str],
                   multipliers: dict[str, np.ndarray],
                   metadata: dict[str, Any]) -> dict[str, Any]:
    local_families = families[keep]
    design = build_continuous_design(
        score_z[keep], webb_z[keep], local_families, months, structure)
    fit = CORE.fit_with_influence(
        ENGINE, young[keep].reshape(-1),
        (young[keep] + older[keep]).reshape(-1), design)
    global_families = sorted(set(families.tolist()))
    occ_influence = np.zeros(len(occupations))
    occ_influence[keep] = fit.occupation_influence[:, 0]
    family_influence = np.zeros(len(global_families))
    local_levels = sorted(set(local_families.tolist()))
    global_lookup = {value: index for index, value in enumerate(global_families)}
    for index, value in enumerate(local_levels):
        family_influence[global_lookup[value]] = fit.family_influence[index, 0]
    estimate = float(fit.beta[0])
    occ = CORE.multiplier_interval(estimate, occ_influence, multipliers["occupation"])
    fam = CORE.multiplier_interval(estimate, family_influence, multipliers["family"])
    row = {
        "model_id": model_id, "functional_form": "continuous",
        "target_label": "exposure_z_x_post", "structure": structure,
        "support_occupations": int(keep.sum()),
        "support_hash_sha256": MAP.support_hash(occupations[keep]),
        "coefficient_target": estimate,
        "coefficient_per_weighted_sd": estimate,
        "coefficient_per_raw_unit": estimate / raw_sd,
        "raw_weighted_mean": raw_mean, "raw_weighted_sd": raw_sd,
        "raw_minimum": raw_min, "raw_maximum": raw_max,
        "occupation_se": occ["se"], "occupation_ci_lower": occ["lower"],
        "occupation_ci_upper": occ["upper"], "occupation_multiplier_p": occ["p_value"],
        "occupation_se_per_raw_unit": occ["se"] / raw_sd,
        "occupation_ci_lower_per_raw_unit": occ["lower"] / raw_sd,
        "occupation_ci_upper_per_raw_unit": occ["upper"] / raw_sd,
        "family_se": fam["se"], "family_ci_lower": fam["lower"],
        "family_ci_upper": fam["upper"], "family_multiplier_p": fam["p_value"],
        "family_se_per_raw_unit": fam["se"] / raw_sd,
        "family_ci_lower_per_raw_unit": fam["lower"] / raw_sd,
        "family_ci_upper_per_raw_unit": fam["upper"] / raw_sd,
        "iterations": fit.iterations,
        "maximum_normalized_score": fit.maximum_normalized_score,
        "separated_observations": fit.separated_observation_count,
        **metadata,
    }
    return {"row": row, "occupation_influence": occ_influence,
            "family_influence": family_influence}


def fit_categorical(model_id: str, structure: str, young: np.ndarray,
                    older: np.ndarray, keep: np.ndarray, quintiles: np.ndarray,
                    webb_z: np.ndarray, families: np.ndarray,
                    occupations: np.ndarray, months: list[str],
                    multipliers: dict[str, np.ndarray],
                    metadata: dict[str, Any]) -> dict[str, Any]:
    result = MAP.fit_model(model_id, structure, young, older, keep, quintiles,
                           webb_z, families, occupations, months, multipliers,
                           {"functional_form": "categorical",
                            "target_label": "Q5_x_post", **metadata})
    result["row"]["coefficient_target"] = result["row"]["coefficient_Q5_x_post"]
    return result


def paired_row(comparison_id: str, left: dict[str, Any], right: dict[str, Any],
               multipliers: dict[str, np.ndarray], metadata: dict[str, Any]) -> dict[str, Any]:
    estimate = left["row"]["coefficient_target"] - right["row"]["coefficient_target"]
    occupation_influence = left["occupation_influence"] - right["occupation_influence"]
    family_influence = left["family_influence"] - right["family_influence"]
    occ = CORE.multiplier_interval(estimate, occupation_influence,
                                   multipliers["occupation"])
    fam = CORE.multiplier_interval(estimate, family_influence,
                                   multipliers["family"])
    return {
        "comparison_id": comparison_id,
        "left_model": left["row"]["model_id"],
        "right_model": right["row"]["model_id"],
        "estimate_left_minus_right": estimate,
        "occupation_se": occ["se"], "occupation_ci_lower": occ["lower"],
        "occupation_ci_upper": occ["upper"], "occupation_multiplier_p": occ["p_value"],
        "family_se": fam["se"], "family_ci_lower": fam["lower"],
        "family_ci_upper": fam["upper"], "family_multiplier_p": fam["p_value"],
        "common_draws_preserve_covariance": True,
        "interpretation_if_interval_contains_zero":
            "design does not detect a difference; not equivalence",
        **metadata,
    }


def load_scores(membership_path: Path, variants_path: Path,
                webb_ai_path: Path, oecd_path: Path,
                occupations: np.ndarray) -> tuple[pd.DataFrame, pd.DataFrame]:
    membership = pd.read_csv(membership_path, dtype={"occupation_code": str},
                             float_precision="round_trip")
    membership["occupation_code"] = membership.occupation_code.str.zfill(4)
    membership = membership.set_index("occupation_code").reindex(occupations)
    require(not membership[["occupation_name", "rule_A_beta", "webb_pct_software"]]
            .isna().any().any(), "baseline membership differs")
    variants = pd.read_csv(variants_path, dtype={"census_2018": str},
                           float_precision="round_trip")
    variants["census_2018"] = variants.census_2018.str.zfill(4)
    variants = variants.set_index("census_2018").reindex(occupations)
    webb_ai = pd.read_csv(webb_ai_path, dtype={"census2018": str},
                          float_precision="round_trip")
    webb_ai["census2018"] = webb_ai.census2018.str.zfill(4)
    webb_ai = webb_ai.set_index("census2018").reindex(occupations)
    oecd = pd.read_csv(oecd_path, dtype={"census2018": str},
                       float_precision="round_trip")
    oecd["census2018"] = oecd.census2018.str.zfill(4)
    oecd = oecd.set_index("census2018").reindex(occupations)
    scores = pd.DataFrame(index=occupations)
    for column in ("aioe_admin_equal", "aioe_ability_direct",
                   "aioe_oews2018_source_weighted"):
        scores[column] = pd.to_numeric(variants[column], errors="coerce").to_numpy()
    scores["webb_ai"] = pd.to_numeric(webb_ai.webb_ai, errors="coerce").to_numpy()
    scores["oecd_ai_gap_reversed"] = pd.to_numeric(
        oecd.oecd_ai_gap_reversed, errors="coerce").to_numpy()
    return membership, scores


def validate_w06(source_dir: Path) -> dict[str, Any]:
    names = [
        "EXECUTION_RECEIPT.json", "SELF_CHECK.json", "CONSTRUCTION_IDENTITY_AUDIT.json",
        "LAMBDA_GRID_RESULTS.csv", "LAMBDA_GRID_MEMBERSHIP.csv",
        "LAMBDA_GRID_CENTERED_DRAWS.csv", "LAMBDA_PAIRED_DIFFERENCES.csv",
        "PRIMITIVE_JOINT_RESULTS.csv", "PRIMITIVE_JOINT_COVARIANCE.csv",
        "PRIMITIVE_JOINT_CENTERED_DRAWS.csv", "PRIMITIVE_ILLUSTRATIVE_CONTRASTS.csv",
        "MODEL_FAILURES.json",
    ]
    for name in names:
        require((source_dir / name).is_file(), f"W06 source missing {name}")
    receipt = json.loads((source_dir / "EXECUTION_RECEIPT.json").read_text())
    self_check = json.loads((source_dir / "SELF_CHECK.json").read_text())
    identity = json.loads((source_dir / "CONSTRUCTION_IDENTITY_AUDIT.json").read_text())
    require(receipt.get("status") == "PASS_ARCHITECTURE_AUDIT", "W06 receipt does not pass")
    require(self_check.get("status") == "PASS", "W06 self-check does not pass")
    require(identity.get("all_identity_checks_pass") is True, "lambda identity does not pass")
    require(identity.get("lambda_half_membership_mismatch_count") == 0,
            "lambda-half membership differs")
    tolerance = float(identity["tolerance"])
    identity_fields = [key for key in identity if key.endswith("gap")]
    require(max(abs(float(identity[key])) for key in identity_fields) <= tolerance,
            "lambda-half numerical identity differs")
    for name, expected in receipt["output_hashes"].items():
        require(sha256_file(source_dir / name) == expected,
                f"W06 retained hash differs for {name}")
    grid = pd.read_csv(source_dir / "LAMBDA_GRID_RESULTS.csv")
    members = pd.read_csv(source_dir / "LAMBDA_GRID_MEMBERSHIP.csv")
    pairs = pd.read_csv(source_dir / "LAMBDA_PAIRED_DIFFERENCES.csv")
    primitive = pd.read_csv(source_dir / "PRIMITIVE_JOINT_RESULTS.csv")
    covariance = pd.read_csv(source_dir / "PRIMITIVE_JOINT_COVARIANCE.csv")
    centered = pd.read_csv(source_dir / "PRIMITIVE_JOINT_CENTERED_DRAWS.csv")
    contrasts = pd.read_csv(source_dir / "PRIMITIVE_ILLUSTRATIVE_CONTRASTS.csv")
    failures = json.loads((source_dir / "MODEL_FAILURES.json").read_text())
    require(set(grid["lambda"].astype(float)) == {0, .25, .5, .75, 1},
            "lambda grid differs")
    require(len(members) == 5 * 468 and members.groupby("lambda").size().eq(468).all(),
            "lambda membership is incomplete")
    require(len(pairs) == 30 and pairs.common_multiplier_draws.astype(bool).all(),
            "lambda paired comparisons differ")
    require(set(primitive.units) == {"raw", "standardized"} and len(primitive) == 6,
            "D/S result presentation differs")
    require(len(covariance) == 18, "D/S covariance presentation differs")
    required_draw_columns = {
        "raw_D", "raw_S", "raw_Webb", "standardized_D", "standardized_S",
        "standardized_Webb",
    }
    require(len(centered) == DRAWS and required_draw_columns.issubset(centered.columns),
            "D/S centered draws are incomplete")
    require(len(contrasts) == 3 and contrasts.common_multiplier_draws.astype(bool).all(),
            "D/S illustrative contrasts differ")
    require(failures == [], "W06 retained model failures are nonempty")
    return {
        "status": "PASS_W06_CURRENT_CONTRACT_CARRY_FORWARD",
        "source_git_head": receipt.get("git_head"),
        "source_directory": MAP.public_source_path(source_dir),
        "source_hashes": {name: sha256_file(source_dir / name) for name in names},
        "lambda_values": sorted(grid["lambda"].astype(float).unique().tolist()),
        "lambda_membership_rows": len(members), "lambda_paired_rows": len(pairs),
        "primitive_result_rows": len(primitive), "primitive_covariance_rows": len(covariance),
        "primitive_centered_draw_rows": len(centered),
        "identity_maximum_absolute_gap": max(abs(float(identity[key])) for key in identity_fields),
        "identity_tolerance": tolerance, "model_failures": 0,
        "new_outcome_fit_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-calibration", type=Path, required=True)
    parser.add_argument("--calibration-receipt", type=Path, required=True)
    parser.add_argument("--membership", type=Path, required=True)
    parser.add_argument("--exposure-variants", type=Path, required=True)
    parser.add_argument("--webb-ai", type=Path, required=True)
    parser.add_argument("--oecd", type=Path, required=True)
    parser.add_argument("--w06-source-dir", type=Path, required=True)
    parser.add_argument("--aioe-workbook", type=Path, required=True)
    parser.add_argument("--aioe-evidence-ledger", type=Path, required=True)
    parser.add_argument("--historical-aioe-decomposition", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output_dir.exists(), "refusing to overwrite architecture output")
    require(sha256_file(args.membership) == MAP.MEMBERSHIP_SHA256,
            "membership hash differs")
    receipt = json.loads(args.calibration_receipt.read_text(encoding="utf-8"))
    require(receipt.get("status") == "PASS_PRIVATE_CALIBRATION_BUILD",
            "private calibration receipt does not pass")
    require(sha256_file(args.private_calibration) == receipt.get("private_npz_sha256"),
            "private calibration hash differs")
    with np.load(args.private_calibration, allow_pickle=False) as loaded:
        arrays = {name: loaded[name] for name in loaded.files}
    occupations = arrays["occupations"].astype(str)
    families = arrays["families"].astype(str)
    months = arrays["months"].astype(str).tolist()
    require(len(occupations) == EXPECTED_OCCUPATIONS and len(months) == EXPECTED_MONTHS,
            "protected contract dimensions differ")
    n_cell = len(occupations) * len(months)
    by_age = np.bincount(arrays["cellage"], weights=arrays["route_stock"],
                         minlength=2 * n_cell)
    young = by_age[:n_cell].reshape(len(occupations), len(months))
    older = by_age[n_cell:].reshape(len(occupations), len(months))
    require(np.allclose((young + older).reshape(-1), arrays["total"], rtol=0, atol=1e-7),
            "protected age stocks do not reproduce totals")
    weights = arrays["construction_weight"].astype(float)
    require(np.all(weights > 0), "construction weights are nonpositive")
    membership, scores = load_scores(
        args.membership, args.exposure_variants, args.webb_ai, args.oecd, occupations)
    beta = membership.rule_A_beta.to_numpy(float)
    webb = membership.webb_pct_software.to_numpy(float)
    require(np.allclose(beta, arrays["exposure_beta"], rtol=0, atol=1e-12),
            "Rule-A beta differs from calibration")
    global_families = sorted(set(families.tolist()))
    draws = CORE.draw_multiplier_matrices(DRAWS, len(occupations), len(global_families), SEED)
    multipliers = {"occupation": draws["occupation_rademacher"],
                   "family": draws["family_rademacher"]}
    models: dict[str, dict[str, Any]] = {}
    model_rows: list[dict[str, Any]] = []
    pair_rows: list[dict[str, Any]] = []
    member_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    def fit_contract(contract_id: str, measure: str, score: np.ndarray,
                     keep: np.ndarray, include_beta_anchor: bool) -> dict[str, dict[str, Any]]:
        alt_contract = MAP.weighted_contract(score[keep], weights[keep])
        beta_contract = MAP.weighted_contract(beta[keep], weights[keep])
        webb_mean = float(np.average(webb[keep], weights=weights[keep]))
        webb_sd = float(np.sqrt(np.average(np.square(webb[keep] - webb_mean),
                                           weights=weights[keep])))
        require(webb_sd > 0, f"{contract_id} Webb scale collapses")
        alt_q = np.zeros(len(occupations), int)
        beta_q = np.zeros(len(occupations), int)
        alt_q[keep] = alt_contract["groups"]
        beta_q[keep] = beta_contract["groups"]
        alt_z = np.zeros(len(occupations), float)
        beta_z = np.zeros(len(occupations), float)
        webb_z = np.zeros(len(occupations), float)
        alt_z[keep] = (score[keep] - alt_contract["mean"]) / alt_contract["sd"]
        beta_z[keep] = (beta[keep] - beta_contract["mean"]) / beta_contract["sd"]
        webb_z[keep] = (webb[keep] - webb_mean) / webb_sd
        for index in np.flatnonzero(keep):
            member_rows.append({
                "contract_id": contract_id, "measure": measure,
                "occupation_code": occupations[index],
                "occupation_name": membership.occupation_name.iloc[index],
                "preperiod_weight": weights[index], "raw_score": score[index],
                "score_z": alt_z[index], "measure_quintile": alt_q[index],
                "rule_A_beta": beta[index], "beta_anchor_z": beta_z[index],
                "beta_anchor_quintile": beta_q[index], "webb_software_z": webb_z[index],
            })
        fitted: dict[str, dict[str, Any]] = {}
        definitions = [("alternative", score, alt_q, alt_z, alt_contract)]
        if include_beta_anchor:
            definitions.append(("beta_anchor", beta, beta_q, beta_z, beta_contract))
        for role, raw, q_value, z_value, contract in definitions:
            raw_values = raw[keep]
            for structure in ("pooled", "family_month"):
                common = {
                    "contract_id": contract_id, "measure": measure,
                    "measure_role": role,
                    "construct_class": ("same_construct_AIOE_implementation"
                                        if measure.startswith("aioe_") else
                                        "different_exposure_construct"),
                    "raw_unit": ("published_AIOE_source_index_unit"
                                 if measure.startswith("aioe_") else
                                 "published_measure_unit"),
                }
                categorical_id = f"{contract_id}_{role}_categorical_{structure}"
                fitted[f"{role}_categorical_{structure}"] = fit_categorical(
                    categorical_id, structure, young, older, keep, q_value, webb_z,
                    families, occupations, months, multipliers, common)
                continuous_id = f"{contract_id}_{role}_continuous_{structure}"
                fitted[f"{role}_continuous_{structure}"] = fit_continuous(
                    continuous_id, structure, young, older, keep, z_value, webb_z,
                    float(contract["mean"]), float(contract["sd"]),
                    float(np.min(raw_values)), float(np.max(raw_values)), families,
                    occupations, months, multipliers, common)
        for value in fitted.values():
            models[value["row"]["model_id"]] = value
            model_rows.append(value["row"])
        return fitted

    try:
        full_keep = np.ones(len(occupations), bool)
        full = fit_contract("full_support_rule_A_beta", "rule_A_beta", beta,
                            full_keep, include_beta_anchor=False)
        require(abs(full["alternative_categorical_pooled"]["row"]["coefficient_target"]
                    - EXPECTED_POOLED) <= 1e-8, "full pooled beta does not reproduce")
        require(abs(full["alternative_categorical_family_month"]["row"]["coefficient_target"]
                    - EXPECTED_FAMILY) <= 1e-8, "full family beta does not reproduce")

        for measure in scores.columns:
            score = scores[measure].to_numpy(float)
            keep = np.isfinite(score)
            require(keep.sum() >= 400, f"{measure} support is unexpectedly small")
            fitted = fit_contract(f"native_{measure}", measure, score, keep, True)
            for functional, structure in itertools.product(
                    ("categorical", "continuous"), ("pooled", "family_month")):
                left = fitted[f"alternative_{functional}_{structure}"]
                right = fitted[f"beta_anchor_{functional}_{structure}"]
                pair_rows.append(paired_row(
                    f"{measure}_minus_beta_{functional}_{structure}", left, right,
                    multipliers, {"comparison_class": "alternative_minus_rule_A_beta",
                                  "measure": measure, "functional_form": functional,
                                  "structure": structure}))

        aioe_names = ["aioe_admin_equal", "aioe_ability_direct",
                      "aioe_oews2018_source_weighted"]
        aioe_keep = np.logical_and.reduce([
            np.isfinite(scores[name].to_numpy(float)) for name in aioe_names])
        aioe_models: dict[str, dict[str, dict[str, Any]]] = {}
        for measure in aioe_names:
            aioe_models[measure] = fit_contract(
                f"common_AIOE_{measure}", measure, scores[measure].to_numpy(float),
                aioe_keep, include_beta_anchor=False)
        for left_name, right_name in itertools.combinations(aioe_names, 2):
            for functional, structure in itertools.product(
                    ("categorical", "continuous"), ("pooled", "family_month")):
                left = aioe_models[left_name][f"alternative_{functional}_{structure}"]
                right = aioe_models[right_name][f"alternative_{functional}_{structure}"]
                pair_rows.append(paired_row(
                    f"{left_name}_minus_{right_name}_{functional}_{structure}",
                    left, right, multipliers,
                    {"comparison_class": "same_construct_AIOE_implementation",
                     "measure": f"{left_name}_minus_{right_name}",
                     "functional_form": functional, "structure": structure}))
    except Exception as error:
        failures.append({"error": repr(error)})
        raise

    w06 = validate_w06(args.w06_source_dir)
    historical = pd.read_csv(args.historical_aioe_decomposition,
                             float_precision="round_trip")
    require(historical.row.astype(int).tolist() == [1, 2, 3, 4],
            "historical AIOE decomposition differs")
    w05 = {
        "status": "PASS_W05_UNIT_AND_IMPLEMENTATION_VERIFICATION",
        "aioe_raw_unit": ("one unit of the published occupation index standardized across "
                          "source occupations without employment weighting"),
        "yax_continuous_unit": "one current-support preperiod-employment-weighted SD",
        "one_raw_unit_is_percentage": False,
        "raw_unit_and_weighted_sd_both_reported_in_current_models": True,
        "historical_four_row_contract_status":
            "RETAINED_AS_SIGNED_HISTORICAL_CONTRACT_NOT_CURRENT_OUTCOME_EVIDENCE",
        "historical_four_row_records": historical.to_dict(orient="records"),
        "published_implementation_error_attributed": False,
        "reason": "No published-paper implementation is accused without inspected code.",
        "source_hashes": {
            "AIOE_DataAppendix.xlsx": sha256_file(args.aioe_workbook),
            "EVIDENCE_LEDGER.md": sha256_file(args.aioe_evidence_ledger),
            "MAPPING_DECOMPOSITION_AUDIT.csv":
                sha256_file(args.historical_aioe_decomposition),
        },
    }

    influence_rows: list[dict[str, Any]] = []
    global_families = sorted(set(families.tolist()))
    for model in models.values():
        for code, value in zip(occupations, model["occupation_influence"]):
            influence_rows.append({"model_id": model["row"]["model_id"],
                                   "cluster_type": "occupation", "cluster_id": code,
                                   "target_influence": float(value)})
        for code, value in zip(global_families, model["family_influence"]):
            influence_rows.append({"model_id": model["row"]["model_id"],
                                   "cluster_type": "family", "cluster_id": code,
                                   "target_influence": float(value)})

    args.output_dir.mkdir(parents=True)
    outputs: dict[str, list[dict[str, Any]]] = {
        "MODEL_RESULTS.csv": model_rows,
        "PAIRED_COMPARISONS.csv": pair_rows,
        "TREATMENT_MEMBERSHIP_AND_SCALING.csv": member_rows,
        "MODEL_INFLUENCE.csv": influence_rows,
    }
    for name, rows in outputs.items():
        write_csv(args.output_dir / name, rows)
    write_json(args.output_dir / "W06_CARRY_FORWARD_VALIDATION.json", w06)
    write_json(args.output_dir / "W05_UNIT_AND_IMPLEMENTATION_VERIFICATION.json", w05)
    write_json(args.output_dir / "MODEL_FAILURES.json", failures)
    output_names = [*outputs, "W06_CARRY_FORWARD_VALIDATION.json",
                    "W05_UNIT_AND_IMPLEMENTATION_VERIFICATION.json", "MODEL_FAILURES.json"]
    run_receipt = {
        "schema_version": "yax-gate3-architecture-reconciliation-v1",
        "status": "PASS_GATE3_ARCHITECTURE_RECONCILIATION",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                              text=True).strip(),
        "sge_job_id": os.environ.get("JOB_ID"),
        "input_hashes": {
            "private_calibration": sha256_file(args.private_calibration),
            "calibration_receipt": sha256_file(args.calibration_receipt),
            "membership": sha256_file(args.membership),
            "exposure_variants": sha256_file(args.exposure_variants),
            "webb_ai": sha256_file(args.webb_ai), "oecd": sha256_file(args.oecd),
            "specification": sha256_file(HERE / "ARCHITECTURE_RECONCILIATION_SPEC.md"),
            "runner": sha256_file(Path(__file__)),
        },
        "canonical_identity": {
            "support_occupations": len(occupations), "analysis_months": len(months),
            "pooled_beta": full["alternative_categorical_pooled"]["row"]["coefficient_target"],
            "family_month_beta":
                full["alternative_categorical_family_month"]["row"]["coefficient_target"],
        },
        "model_count": len(model_rows), "paired_comparison_count": len(pair_rows),
        "model_failure_count": len(failures), "draws": DRAWS, "seed": SEED,
        "common_draws_across_models": True,
        "protected_microdata_or_identifiers_written": False,
        "output_hashes": {name: sha256_file(args.output_dir / name) for name in output_names},
    }
    write_json(args.output_dir / "EXECUTION_RECEIPT.json", run_receipt)
    print(json.dumps({"status": run_receipt["status"], "models": len(model_rows),
                      "pairs": len(pair_rows)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
