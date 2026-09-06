#!/usr/bin/env python3
"""Run the R3 dependence audit on the canonical rebuilt treatment.

POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1.
The module is intentionally self-contained within ``inference_rebuilt`` and
never mutates protected inputs or the historical inference artifacts.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import pathlib
import platform
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd


HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
LABEL = "POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1"
EXPECTED_SUPPORT_HASH = "11ec58ab1004cd83d62c57785f6c0dd3ee5a8abf08b7f71a3b664e91ded8333b"
EXPECTED_MEMBERSHIP_HASH = "c76eb85956e4a413e130bab53fe8c50616cf6d7a02c81c266ec369879dd56bc1"
EXPECTED_BRIDGE_HASH = "0bd2f63c72e24bed2cc1cb414395c3cbddf7c00011e47ec1c1de6ae534fd1dcc"
EXPECTED_COMPUTERIZATION_HASH = "352cb40834ec83225f747d316eb3e03fce1d1c5c65d80720c558177f85801fdd"
EXPECTED_MICRODATA_HASH = "3fe42477e6f2ce401e85123f0e278e758595c1c4071a8743f243a92752db38c9"
EXPECTED_REPAIR_HASH = "a4ae2ef06d66a0d47359ccceffff9a15843ac501a9f25f9a05aa8fdca9c4f911"
EXPECTED_POOLED = -0.13210945079219033
EXPECTED_CONDITIONED = -0.021674952018245923
SEED = 2026090561
DRAWS = 99_999
LAGS = (0, 1, 4, 12, 16)
Z975 = 1.959963984540054
Z80 = 0.8416212335729143
MDE_FACTOR = Z975 + Z80
TARGET = 3
PARAMETER_LABELS = (
    "Q2_x_post_2023_01", "Q3_x_post_2023_01",
    "Q4_x_post_2023_01", "Q5_x_post_2023_01",
    "Webb_z_x_post_2023_01",
)


def import_path(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import {}".format(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


COMP = import_path(
    "yax_r3_rebuilt_inference_composition",
    ROOT / "yax/revision/referee_round2_20260905/composition_influence/run_composition_influence.py",
)
CELLS = import_path(
    "yax_r3_rebuilt_inference_cells",
    ROOT / "yax/revision/referee_20260905/run_referee_cells.py",
)
FROZEN = COMP.FROZEN


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def support_hash(codes) -> str:
    payload = "".join("{}\n".format(code) for code in sorted(codes))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_csv(path: pathlib.Path, rows) -> None:
    if not rows:
        raise RuntimeError("refusing to write empty output {}".format(path))
    fields = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: pathlib.Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def higher_quantile(values: np.ndarray, share: float) -> float:
    try:
        return float(np.quantile(values, share, method="higher"))
    except TypeError:
        return float(np.quantile(values, share, interpolation="higher"))


def month_number(value: str) -> int:
    return int(value[:4]) * 12 + int(value[5:7]) - 1


def full_calendar_positions(months: list[str]) -> tuple[list[str], np.ndarray]:
    first, last = month_number(months[0]), month_number(months[-1])
    full = ["{:04d}-{:02d}".format(index // 12, index % 12 + 1)
            for index in range(first, last + 1)]
    lookup = {value: index for index, value in enumerate(full)}
    return full, np.asarray([lookup[value] for value in months], dtype=int)


def newey_west_meat(scores: np.ndarray, lag: int) -> np.ndarray:
    """Unnormalized Bartlett meat for a time-by-parameter score matrix."""
    if lag < 0:
        raise ValueError("lag must be nonnegative")
    meat = scores.T @ scores
    for ell in range(1, lag + 1):
        weight = 1.0 - ell / (lag + 1.0)
        gamma = scores[ell:].T @ scores[:-ell]
        meat += weight * (gamma + gamma.T)
    return (meat + meat.T) / 2.0


def load_contract(args) -> dict:
    observed_hashes = {
        "membership": sha256(args.membership),
        "bridge": sha256(args.bridge),
        "computerization": sha256(args.computerization),
        "microdata": sha256(args.microdata),
        "repair_microdata": sha256(args.repair_microdata),
    }
    expected_hashes = {
        "membership": EXPECTED_MEMBERSHIP_HASH,
        "bridge": EXPECTED_BRIDGE_HASH,
        "computerization": EXPECTED_COMPUTERIZATION_HASH,
        "microdata": EXPECTED_MICRODATA_HASH,
        "repair_microdata": EXPECTED_REPAIR_HASH,
    }
    mismatch = {name: {"observed": observed_hashes[name], "expected": expected}
                for name, expected in expected_hashes.items()
                if observed_hashes[name] != expected}
    if mismatch:
        raise RuntimeError("authenticated input mismatch: {}".format(mismatch))

    membership = pd.read_csv(args.membership, dtype={"occupation_code": str})
    required = {"occupation_code", "beta_quintile", "webb_z", "preperiod_weight"}
    if not required.issubset(membership.columns):
        raise RuntimeError("rebuilt membership lacks {}".format(
            sorted(required - set(membership.columns))))
    membership["occupation_code"] = membership.occupation_code.str.zfill(4)
    if membership.occupation_code.duplicated().any():
        raise RuntimeError("duplicate occupations in rebuilt membership")
    support = membership.occupation_code.tolist()
    if len(support) != 468 or support_hash(support) != EXPECTED_SUPPORT_HASH:
        raise RuntimeError("canonical rebuilt support changed")
    quintiles = pd.to_numeric(membership.beta_quintile, errors="raise").astype(int).to_numpy()
    if set(np.unique(quintiles).tolist()) - {1, 2, 3, 4, 5}:
        raise RuntimeError("rebuilt membership contains invalid quintiles")
    webb_z = pd.to_numeric(membership.webb_z, errors="raise").to_numpy(float)
    if not np.all(np.isfinite(webb_z)):
        raise RuntimeError("rebuilt Webb standardization contains nonfinite values")
    _, names, major_map = FROZEN.comp_maps(args.computerization)
    majors = np.asarray([major_map.get(code, "MISSING") for code in support], dtype=object)
    if "MISSING" in set(majors.tolist()):
        missing = [code for code, group in zip(support, majors) if group == "MISSING"]
        raise RuntimeError("SOC2 missing for rebuilt support: {}".format(missing))
    return {
        "membership": membership,
        "support": support,
        "quintiles": quintiles,
        "webb_z": webb_z,
        "majors": majors,
        "names": names,
        "input_hashes": observed_hashes,
    }


def build_regressors(quintiles: np.ndarray, webb_z: np.ndarray,
                     months: list[str]) -> np.ndarray:
    post = np.asarray([month >= "2023-01" for month in months], dtype=bool)
    columns = [
        (((quintiles == q)[:, None]) & post[None, :]).reshape(-1).astype(float)
        for q in (2, 3, 4, 5)
    ]
    columns.append((webb_z[:, None] * post[None, :]).reshape(-1))
    return np.column_stack(columns)


def second_fe(majors: np.ndarray, n_months: int, structure: str) -> np.ndarray:
    if structure == "pooled_calendar_month":
        return np.tile(np.arange(n_months), len(majors))
    if structure == "SOC2_x_calendar_month":
        levels = {value: index for index, value in enumerate(sorted(set(majors.tolist())))}
        return np.concatenate([
            levels[majors[index]] * n_months + np.arange(n_months)
            for index in range(len(majors))
        ])
    raise ValueError("unknown structure {}".format(structure))


def row_influence_cube(fit, influence: np.ndarray, details: dict,
                       young: np.ndarray, older: np.ndarray) -> np.ndarray:
    """Recover unscaled cell influences and prove they aggregate to the engine."""
    n_occ, n_month = young.shape
    total_full = (young + older).reshape(-1)
    keep = total_full > 0
    flat_occ = np.repeat(np.arange(n_occ), n_month)[keep]
    flat_month = np.tile(np.arange(n_month), n_occ)[keep]
    if len(flat_occ) != len(details["y"]):
        raise RuntimeError("positive-cell order is not aligned with fitted rows")
    residual = details["y"] - details["total"] * fit.fitted_probability
    bread = np.linalg.inv(details["information"])
    row_influence = (details["rx"] * residual[:, None]) @ bread.T
    cube = np.zeros((n_occ, n_month, row_influence.shape[1]), dtype=float)
    np.add.at(cube, (flat_occ, flat_month), row_influence)
    finite_scale = math.sqrt(n_occ / (n_occ - 1.0))
    rebuilt = cube.sum(axis=1) * finite_scale
    if not np.allclose(rebuilt, influence, rtol=1e-8, atol=1e-11):
        gap = float(np.max(np.abs(rebuilt - influence)))
        raise RuntimeError("cell influence fails occupation-score conservation: {}".format(gap))
    return cube


def fit_objects(contract: dict, cells: pd.DataFrame) -> dict:
    support = contract["support"]
    months = [month for month in sorted(cells.month.unique()) if month != "2022-12"]
    if len(months) != 113 or months[0] != "2017-01" or months[-1] != "2026-07":
        raise RuntimeError("corrected static calendar is not 113 months, 2017-01--2026-07")
    if "2025-10" in months or "2022-12" in months:
        raise RuntimeError("static calendar unexpectedly contains a protected gap/transition")
    young, older = CELLS.panel_for_ages(cells, support, months, (22, 25), (26, 65))
    if np.any(young.sum(axis=1) <= 0) or np.any(older.sum(axis=1) <= 0):
        raise RuntimeError("rebuilt support has a zero-stock fixed effect")
    x = build_regressors(contract["quintiles"], contract["webb_z"], months)
    objects = {}
    for name, structure in (
        ("pooled", "pooled_calendar_month"),
        ("conditioned", "SOC2_x_calendar_month"),
    ):
        fit, influence, details = COMP.fit_absorbed(
            young, older, x, second_fe(contract["majors"], len(months), structure)
        )
        cube = row_influence_cube(fit, influence, details, young, older)
        objects[name] = {
            "structure": structure,
            "fit": fit,
            "influence": influence,
            "details": details,
            "cube": cube,
            "estimate": float(fit.beta[TARGET]),
        }
    if not np.isclose(objects["pooled"]["estimate"], EXPECTED_POOLED, atol=1e-9, rtol=0):
        raise RuntimeError("rebuilt pooled checkpoint changed: {}".format(
            objects["pooled"]["estimate"]))
    if not np.isclose(objects["conditioned"]["estimate"], EXPECTED_CONDITIONED,
                      atol=1e-9, rtol=0):
        raise RuntimeError("rebuilt conditioned checkpoint changed: {}".format(
            objects["conditioned"]["estimate"]))
    objects["paired_movement"] = {
        "structure": "conditioned_minus_pooled",
        "estimate": objects["conditioned"]["estimate"] - objects["pooled"]["estimate"],
        "influence": objects["conditioned"]["influence"] - objects["pooled"]["influence"],
        "cube": objects["conditioned"]["cube"] - objects["pooled"]["cube"],
    }
    return {"objects": objects, "months": months, "young": young, "older": older}


def model_summary_rows(objects: dict) -> list[dict]:
    rows = []
    for name in ("pooled", "conditioned", "paired_movement"):
        item = objects[name]
        influence = item["influence"][:, TARGET]
        se = float(np.sqrt(influence @ influence))
        rows.append({
            "analysis_status": LABEL,
            "object": name,
            "structure": item["structure"],
            "estimate": item["estimate"],
            "occupation_cluster_se": se,
            "normal_ci_lower": item["estimate"] - Z975 * se,
            "normal_ci_upper": item["estimate"] + Z975 * se,
            "normal_theory_MDE80": MDE_FACTOR * se,
            "MDE_interpretation": "two-sided 5% normal approximation; precision descriptor, not rejection/equivalence rule",
        })
    return rows


def family_scores(contract: dict, objects: dict) -> tuple[list[str], dict, list[dict]]:
    levels = sorted(set(contract["majors"].tolist()))
    group_index = {value: index for index, value in enumerate(levels)}
    group = np.asarray([group_index[value] for value in contract["majors"]], dtype=int)
    scores, rows = {}, []
    for name in ("pooled", "conditioned", "paired_movement"):
        # Use unscaled occupation influence, then apply the SOC2 rather than the
        # occupation finite-cluster factor.
        occupation_scores = objects[name]["cube"][:, :, TARGET].sum(axis=1)
        values = np.zeros(len(levels), dtype=float)
        np.add.at(values, group, occupation_scores)
        scores[name] = values
        for level, value in zip(levels, values):
            rows.append({
                "analysis_status": LABEL,
                "object": name,
                "SOC2": level,
                "nuisance_adjusted_target_score": float(value),
                "score_units": "unscaled coefficient influence before SOC2 CRV1 factor",
            })
    return levels, scores, rows


def wild_rows(levels: list[str], scores: dict, objects: dict) -> list[dict]:
    if len(levels) != 22:
        raise RuntimeError("expected 22 SOC2 families, found {}".format(len(levels)))
    rng = np.random.default_rng(SEED)
    multipliers = {
        "Rademacher": rng.choice(np.asarray([-1.0, 1.0]), size=(DRAWS, len(levels))),
        "Webb_six_point": rng.choice(np.asarray([
            -math.sqrt(1.5), -1.0, -math.sqrt(0.5),
            math.sqrt(0.5), 1.0, math.sqrt(1.5),
        ]), size=(DRAWS, len(levels))),
    }
    rows = []
    for distribution, weights in multipliers.items():
        for name in ("pooled", "conditioned", "paired_movement"):
            estimate = float(objects[name]["estimate"])
            score = scores[name]
            se = math.sqrt(len(levels) / (len(levels) - 1.0) * float(score @ score))
            centered = weights @ score
            statistic = np.abs(centered / se)
            observed = abs(estimate / se)
            pvalue = float((1 + np.sum(statistic >= observed)) / (DRAWS + 1))
            critical = higher_quantile(statistic, 0.95)
            rows.append({
                "analysis_status": LABEL,
                "object": name,
                "SOC2_clusters": len(levels),
                "estimate": estimate,
                "SOC2_CRV1_se": se,
                "wild_weight_distribution": distribution,
                "wild_score_draws": DRAWS,
                "wild_score_seed": SEED,
                "fixed_studentizer": "SOC2_CRV1_se",
                "wild_score_p_value": pvalue,
                "p_value_Monte_Carlo_se": math.sqrt(pvalue * (1 - pvalue) / (DRAWS + 1)),
                "wild_score_critical": critical,
                "wild_score_ci_lower": estimate - critical * se,
                "wild_score_ci_upper": estimate + critical * se,
                "normal_theory_MDE80_SOC2_CRV1": MDE_FACTOR * se,
                "common_family_draws_across_all_objects": True,
                "draw_representation": "SOC2_FAMILY_SCORE_CONTRIBUTIONS.csv plus seed, distribution, draw count",
                "interpretation": "sensitivity to broad-family dependence; nondetection is not equivalence",
            })
    return rows


def covariance_components(cube: np.ndarray, months: list[str], lag: int) -> dict:
    n_occ, _, n_parameter = cube.shape
    full_months, positions = full_calendar_positions(months)
    full = np.zeros((n_occ, len(full_months), n_parameter), dtype=float)
    full[:, positions, :] = cube
    occupation_scores = full.sum(axis=1)
    aggregate_time_scores = full.sum(axis=0)
    occupation_meat = occupation_scores.T @ occupation_scores
    aggregate_time_hac = newey_west_meat(aggregate_time_scores, lag)
    within_occupation_hac = np.zeros_like(occupation_meat)
    for index in range(n_occ):
        within_occupation_hac += newey_west_meat(full[index], lag)
    combined_unscaled = occupation_meat + aggregate_time_hac - within_occupation_hac
    combined_unscaled = (combined_unscaled + combined_unscaled.T) / 2.0
    covariance = n_occ / (n_occ - 1.0) * combined_unscaled
    covariance = (covariance + covariance.T) / 2.0
    return {
        "full_months": full_months,
        "positions": positions,
        "occupation_meat": occupation_meat,
        "aggregate_time_hac": aggregate_time_hac,
        "within_occupation_hac": within_occupation_hac,
        "combined_unscaled": combined_unscaled,
        "covariance": covariance,
    }


def hac_rows(objects: dict, months: list[str]) -> tuple[list[dict], list[dict]]:
    summaries, matrices = [], []
    for name in ("pooled", "conditioned", "paired_movement"):
        item = objects[name]
        for lag in LAGS:
            components = covariance_components(item["cube"], months, lag)
            covariance = components["covariance"]
            eigenvalues = np.linalg.eigvalsh(covariance)
            tolerance = max(float(np.max(np.abs(eigenvalues))) * 1e-10, 1e-12)
            negative = int(np.sum(eigenvalues < -tolerance))
            target_variance = float(covariance[TARGET, TARGET])
            target_nonnegative = bool(target_variance >= 0)
            se = math.sqrt(target_variance) if target_nonnegative else None
            status = ("FULL_COVARIANCE_PSD" if negative == 0 else
                      "FULL_COVARIANCE_INDEFINITE_TARGET_DIAGONAL_REPORTED")
            summaries.append({
                "analysis_status": LABEL,
                "object": name,
                "structure": item["structure"],
                "lag_elapsed_calendar_months": lag,
                "estimate": item["estimate"],
                "occupation_cluster_se": math.sqrt(
                    len(item["cube"]) / (len(item["cube"]) - 1.0) *
                    float(item["cube"][:, :, TARGET].sum(axis=1) @
                          item["cube"][:, :, TARGET].sum(axis=1))
                ),
                "corrected_inclusion_exclusion_target_variance": target_variance,
                "corrected_inclusion_exclusion_target_se": se,
                "normal_ci_lower": item["estimate"] - Z975 * se if se is not None else None,
                "normal_ci_upper": item["estimate"] + Z975 * se if se is not None else None,
                "normal_theory_MDE80": MDE_FACTOR * se if se is not None else None,
                "occupation_meat_target": float(components["occupation_meat"][TARGET, TARGET]),
                "aggregate_time_HAC_meat_target": float(components["aggregate_time_hac"][TARGET, TARGET]),
                "within_occupation_HAC_overlap_target": float(components["within_occupation_hac"][TARGET, TARGET]),
                "combined_meat_target_before_finite_factor": float(
                    components["combined_unscaled"][TARGET, TARGET]),
                "single_finite_factor_after_combination": len(item["cube"]) / (len(item["cube"]) - 1.0),
                "full_calendar_months": len(components["full_months"]),
                "observed_model_months": len(months),
                "zero_placeholder_months": len(components["full_months"]) - len(months),
                "zero_placeholder_labels": "2022-12;2025-10",
                "minimum_covariance_eigenvalue": float(eigenvalues.min()),
                "negative_covariance_eigenvalues_at_scaled_tolerance": negative,
                "eigenvalue_tolerance": tolerance,
                "target_scalar_variance_nonnegative": target_nonnegative,
                "joint_covariance_status": status,
                "PSD_projection_applied": False,
            })
            for row_index, row_label in enumerate(PARAMETER_LABELS):
                for column_index, column_label in enumerate(PARAMETER_LABELS):
                    matrices.append({
                        "analysis_status": LABEL,
                        "object": name,
                        "lag_elapsed_calendar_months": lag,
                        "row_parameter": row_label,
                        "column_parameter": column_label,
                        "corrected_inclusion_exclusion_covariance": float(
                            covariance[row_index, column_index]),
                        "joint_covariance_status": status,
                        "PSD_projection_applied": False,
                    })
    return summaries, matrices


def occupation_influence_rows(contract: dict, objects: dict) -> list[dict]:
    rows = []
    for index, code in enumerate(contract["support"]):
        rows.append({
            "analysis_status": LABEL,
            "occupation_code": code,
            "occupation_name": contract["names"].get(code, code),
            "SOC2": contract["majors"][index],
            "pooled_Q5_target_influence_CRV1_scaled": float(objects["pooled"]["influence"][index, TARGET]),
            "conditioned_Q5_target_influence_CRV1_scaled": float(objects["conditioned"]["influence"][index, TARGET]),
            "paired_movement_Q5_target_influence_CRV1_scaled": float(objects["paired_movement"]["influence"][index, TARGET]),
        })
    return rows


def findings_text(model_rows: list[dict], wild: list[dict], hac: list[dict]) -> str:
    models = {row["object"]: row for row in model_rows}
    webb = {row["object"]: row for row in wild
            if row["wild_weight_distribution"] == "Webb_six_point"}
    lag16 = {row["object"]: row for row in hac if row["lag_elapsed_calendar_months"] == 16}
    indefinite = [row for row in hac if "INDEFINITE" in row["joint_covariance_status"]]
    return """# Findings: rebuilt-treatment inference addendum

Status: **post-outcome exploratory; not part of confirmatory YAX v1.1.**

The canonical 468-occupation, 113-month rebuilt contract gives a pooled Q5--Q1
coefficient of {pooled:.6f} (occupation-cluster SE {pooled_se:.6f}) and a
SOC2-by-calendar-month conditioned coefficient of {conditioned:.6f} (SE
{conditioned_se:.6f}). The paired conditioned-minus-pooled movement is
{movement:.6f} (SE {movement_se:.6f}); this is a change in a conditioning
comparison, not an allocated causal composition share.

Under 22-family Webb multipliers, the intervals are [{p_lo:.6f}, {p_hi:.6f}]
for the pooled coefficient, [{c_lo:.6f}, {c_hi:.6f}] for the conditioned
coefficient, and [{d_lo:.6f}, {d_hi:.6f}] for the paired movement. The common
family draws preserve the covariance relevant to that paired comparison.

At lag 16, the corrected elapsed-calendar inclusion--exclusion target SE is
{p_hac:.6f} for the pooled estimate and {c_hac:.6f} for the conditioned
estimate. The paired target SE is {d_hac:.6f}. Across all objects and lags,
{indefinite_count} of {hac_count} full five-parameter covariance matrices are
indefinite. Their target diagonals are retained and labeled, but no PSD
projection or silent eigenvalue clipping is applied.

Normal-theory MDEs are reported as precision descriptions only. A confidence
interval containing zero means that the procedure does not detect a difference;
it does not establish economic equivalence. The broad-family and time-HAC rows
are dependence sensitivities, not CPS design-based survey inference.
""".format(
        pooled=models["pooled"]["estimate"], pooled_se=models["pooled"]["occupation_cluster_se"],
        conditioned=models["conditioned"]["estimate"], conditioned_se=models["conditioned"]["occupation_cluster_se"],
        movement=models["paired_movement"]["estimate"], movement_se=models["paired_movement"]["occupation_cluster_se"],
        p_lo=webb["pooled"]["wild_score_ci_lower"], p_hi=webb["pooled"]["wild_score_ci_upper"],
        c_lo=webb["conditioned"]["wild_score_ci_lower"], c_hi=webb["conditioned"]["wild_score_ci_upper"],
        d_lo=webb["paired_movement"]["wild_score_ci_lower"], d_hi=webb["paired_movement"]["wild_score_ci_upper"],
        p_hac=lag16["pooled"]["corrected_inclusion_exclusion_target_se"],
        c_hac=lag16["conditioned"]["corrected_inclusion_exclusion_target_se"],
        d_hac=lag16["paired_movement"]["corrected_inclusion_exclusion_target_se"],
        indefinite_count=len(indefinite), hac_count=len(hac),
    )


def sanitize_cell_receipt(receipt: dict) -> dict:
    clean = dict(receipt)
    clean["microdata_files"] = [pathlib.Path(value).name
                                for value in receipt.get("microdata_files", [])]
    return clean


def execute(args) -> None:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc)
    contract = load_contract(args)
    cells, _, cell_receipt = CELLS.build_exact_age_cells(args)
    fitted = fit_objects(contract, cells)
    objects, months = fitted["objects"], fitted["months"]
    model_rows = model_summary_rows(objects)
    levels, score_map, score_rows = family_scores(contract, objects)
    wild = wild_rows(levels, score_map, objects)
    hac, covariance_matrices = hac_rows(objects, months)
    influence = occupation_influence_rows(contract, objects)
    failures = []

    write_csv(args.output_dir / "MODEL_SUMMARIES.csv", model_rows)
    write_csv(args.output_dir / "OCCUPATION_INFLUENCE.csv", influence)
    write_csv(args.output_dir / "SOC2_FAMILY_SCORE_CONTRIBUTIONS.csv", score_rows)
    write_csv(args.output_dir / "SOC2_WILD_SENSITIVITY.csv", wild)
    write_csv(args.output_dir / "CORRECTED_TIME_HAC_RESULTS.csv", hac)
    write_csv(args.output_dir / "TIME_HAC_COVARIANCE_MATRICES.csv", covariance_matrices)
    write_json(args.output_dir / "MODEL_FAILURES.json", failures)
    (args.output_dir / "FINDINGS.md").write_text(
        findings_text(model_rows, wild, hac), encoding="utf-8"
    )

    output_names = [
        "MODEL_SUMMARIES.csv", "OCCUPATION_INFLUENCE.csv",
        "SOC2_FAMILY_SCORE_CONTRIBUTIONS.csv", "SOC2_WILD_SENSITIVITY.csv",
        "CORRECTED_TIME_HAC_RESULTS.csv", "TIME_HAC_COVARIANCE_MATRICES.csv",
        "MODEL_FAILURES.json", "FINDINGS.md",
    ]
    receipt = {
        "record": "YAX R3 rebuilt-treatment dependence and inference addendum",
        "analysis_status": LABEL,
        "started_at_utc": started.isoformat(),
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "script_sha256": sha256(pathlib.Path(__file__)),
        "analysis_specification_sha256": sha256(HERE / "ANALYSIS_SPEC_BEFORE_RESULTS.md"),
        "input_hashes": contract["input_hashes"],
        "private_input_names_only": [args.microdata.name, args.repair_microdata.name],
        "cell_build_receipt": sanitize_cell_receipt(cell_receipt),
        "treatment_contract": "rebuilt_corrected_preperiod_weight",
        "support_occupations": len(contract["support"]),
        "support_hash_sha256": support_hash(contract["support"]),
        "observed_model_months": len(months),
        "full_elapsed_calendar_months": len(full_calendar_positions(months)[0]),
        "zero_placeholder_months": ["2022-12", "2025-10"],
        "SOC2_clusters": len(levels),
        "draws": DRAWS,
        "seed": SEED,
        "common_family_draws_across_objects": True,
        "paired_identity": {
            "conditioned_minus_pooled_estimate": objects["paired_movement"]["estimate"],
            "maximum_influence_identity_gap": float(np.max(np.abs(
                objects["paired_movement"]["influence"] -
                (objects["conditioned"]["influence"] - objects["pooled"]["influence"])
            ))),
        },
        "HAC_lags_elapsed_calendar_months": list(LAGS),
        "PSD_projection_applied": False,
        "machine": {
            "scheduler_job_id": os.environ.get("JOB_ID", "not_run_under_scheduler"),
            "hostname": platform.node(),
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "output_hashes": {
            name: sha256(args.output_dir / name) for name in output_names
        },
    }
    write_json(args.output_dir / "EXECUTION_RECEIPT.json", receipt)
    print(json.dumps({
        "status": "PASS_REBUILT_INFERENCE_ADDENDUM",
        "pooled": objects["pooled"]["estimate"],
        "conditioned": objects["conditioned"]["estimate"],
        "paired_movement": objects["paired_movement"]["estimate"],
        "indefinite_HAC_matrices": sum(
            "INDEFINITE" in row["joint_covariance_status"] for row in hac
        ),
    }, indent=2, sort_keys=True))


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--microdata", type=pathlib.Path, required=True)
    value.add_argument("--repair-microdata", type=pathlib.Path, required=True)
    value.add_argument(
        "--membership", type=pathlib.Path,
        default=ROOT / "yax/revision/substantive_r3_20260905/rebuilt_baseline/results/REBUILT_TREATMENT_MEMBERSHIP.csv",
    )
    value.add_argument(
        "--bridge", type=pathlib.Path,
        default=ROOT / "yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv",
    )
    value.add_argument(
        "--computerization", type=pathlib.Path,
        default=ROOT / "yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv",
    )
    value.add_argument("--output-dir", type=pathlib.Path, required=True)
    return value


def main() -> None:
    args = parser().parse_args()
    try:
        execute(args)
    except Exception as error:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        message = str(error)
        for path in (args.microdata, args.repair_microdata):
            message = message.replace(str(path), path.name)
        write_json(args.output_dir / "MODEL_FAILURES.json", [{
            "analysis_status": LABEL,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "stage": "rebuilt_inference_addendum",
            "status": "FAILED_REPORTED_NOT_SUBSTITUTED",
            "error_type": type(error).__name__,
            "message": message,
            "no_replacement_or_PSD_projection": True,
        }])
        raise


if __name__ == "__main__":
    main()
