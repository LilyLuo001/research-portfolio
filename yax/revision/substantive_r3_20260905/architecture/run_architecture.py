#!/usr/bin/env python3
"""Run the predeclared corrected-calendar YAX architecture audit.

POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1.
The specification in ANALYSIS_SPEC_BEFORE_RESULTS.md was committed before any
new output from this corrected-calendar runner was produced.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import itertools
import json
import math
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd


LABEL = "POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1"
DRAWS = 9_999
SEED = 2026090551
LAMBDA_VALUES = (0.0, 0.25, 0.5, 0.75, 1.0)
Z975 = 1.959963984540054
Z80 = 0.8416212335729143
MDE_FACTOR = Z975 + Z80
PRIMARY_SUPPORT_COUNT = 468
PRIMARY_SUPPORT_HASH = "11ec58ab1004cd83d62c57785f6c0dd3ee5a8abf08b7f71a3b664e91ded8333b"
CHAR_SUPPORT_COUNT = 408
CHAR_SUPPORT_HASH = "12e4bdcdc7958ec8a52b06762585d4887743963ddcbca7de1223b2eea44a5aca"
REBUILT_BASELINE_EXPECTED = -0.1321094507921903
IDENTITY_TOLERANCE = 1e-10


def import_path(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def support_hash(codes: list[str]) -> str:
    return hashlib.sha256("".join(f"{code}\n" for code in sorted(codes)).encode()).hexdigest()


def write_json(path: pathlib.Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: pathlib.Path, rows: list[dict]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty output {path}")
    fields: list[str] = []
    for row in rows:
        fields.extend(key for key in row if key not in fields)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def weighted_mean_sd(values: np.ndarray, weights: np.ndarray) -> tuple[float, float]:
    values = np.asarray(values, float)
    weights = np.asarray(weights, float)
    if len(values) == 0 or len(values) != len(weights):
        raise ValueError("weighted moment arrays must be nonempty and aligned")
    if np.any(~np.isfinite(values)) or np.any(~np.isfinite(weights)) or np.any(weights <= 0):
        raise ValueError("weighted moment arrays must be finite with positive weights")
    mean = float(np.average(values, weights=weights))
    sd = float(np.sqrt(np.average(np.square(values - mean), weights=weights)))
    if not np.isfinite(sd) or sd <= 0:
        raise ValueError("weighted standard deviation is not positive")
    return mean, sd


def weighted_corr(left: np.ndarray, right: np.ndarray, weights: np.ndarray) -> float:
    lm, _ = weighted_mean_sd(left, weights)
    rm, _ = weighted_mean_sd(right, weights)
    numerator = float(np.sum(weights * (left - lm) * (right - rm)))
    denominator = math.sqrt(
        float(np.sum(weights * np.square(left - lm)))
        * float(np.sum(weights * np.square(right - rm)))
    )
    if denominator <= 0:
        raise ValueError("weighted correlation denominator is not positive")
    return numerator / denominator


def higher_quantile(values: np.ndarray, probability: float) -> float:
    try:
        return float(np.quantile(values, probability, method="higher"))
    except TypeError:
        return float(np.quantile(values, probability, interpolation="higher"))


def fit_design(FROZEN, young: np.ndarray, older: np.ndarray, columns: list[np.ndarray]):
    matrix = np.column_stack([np.asarray(column, float).reshape(-1) for column in columns])
    if np.any(~np.isfinite(matrix)):
        raise RuntimeError("nonfinite design matrix")
    return FROZEN.fit_with_influence(young, older, matrix)


def categorical_design(
    quintiles: np.ndarray,
    months: list[str],
    nuisance: dict[str, np.ndarray],
) -> tuple[list[np.ndarray], list[str]]:
    post = np.asarray([month >= "2023-01" for month in months], bool)
    columns = [
        (((quintiles == q)[:, None]) & post[None, :]).astype(float)
        for q in (2, 3, 4, 5)
    ]
    labels = [f"Q{q}_x_post" for q in (2, 3, 4, 5)]
    for name, values in nuisance.items():
        columns.append(np.asarray(values, float)[:, None] * post[None, :])
        labels.append(f"{name}_x_post")
    return columns, labels


def continuous_design(
    score: np.ndarray,
    months: list[str],
    nuisance: dict[str, np.ndarray],
    score_name: str,
) -> tuple[list[np.ndarray], list[str]]:
    post = np.asarray([month >= "2023-01" for month in months], bool)
    columns = [np.asarray(score, float)[:, None] * post[None, :]]
    labels = [f"{score_name}_x_post"]
    for name, values in nuisance.items():
        columns.append(np.asarray(values, float)[:, None] * post[None, :])
        labels.append(f"{name}_x_post")
    return columns, labels


def infer_term(fit, influence: np.ndarray, target: int, signs: np.ndarray) -> tuple[dict, np.ndarray]:
    centered = signs @ influence[:, target]
    estimate = float(fit.beta[target])
    analytic_se = float(fit.standard_error[target])
    bootstrap_se = float(np.std(centered, ddof=1))
    if not np.isfinite(analytic_se) or analytic_se <= 0 or bootstrap_se <= 0:
        raise RuntimeError("nonpositive inference scale")
    critical = higher_quantile(np.abs(centered / analytic_se), 0.95)
    p_value = float(
        (1 + np.sum(np.abs(centered / analytic_se) >= abs(estimate / analytic_se)))
        / (len(centered) + 1)
    )
    return {
        "coefficient": estimate,
        "analytic_occupation_cluster_se": analytic_se,
        "bootstrap_se": bootstrap_se,
        "ci_lower": estimate - critical * analytic_se,
        "ci_upper": estimate + critical * analytic_se,
        "bootstrap_p_value": p_value,
        "bootstrap_critical": critical,
        "mde80": MDE_FACTOR * analytic_se,
        "mde_se_basis": "analytic_occupation_cluster_se",
        "draws": len(centered),
        "seed": SEED,
        "converged": bool(fit.converged),
        "iterations": int(fit.iterations),
    }, centered


def infer_contrast(
    left_name: str,
    right_name: str,
    left_estimate: float,
    right_estimate: float,
    left_draws: np.ndarray,
    right_draws: np.ndarray,
    family: str,
) -> dict:
    centered = np.asarray(left_draws) - np.asarray(right_draws)
    delta = float(left_estimate - right_estimate)
    se = float(np.std(centered, ddof=1))
    if not np.isfinite(se) or se <= 0:
        raise RuntimeError(f"nonpositive paired SE for {left_name} minus {right_name}")
    critical = higher_quantile(np.abs(centered / se), 0.95)
    return {
        "model_family": family,
        "left": left_name,
        "right": right_name,
        "coefficient_difference": delta,
        "paired_bootstrap_se": se,
        "ci_lower": delta - critical * se,
        "ci_upper": delta + critical * se,
        "paired_bootstrap_p_value": float(
            (1 + np.sum(np.abs(centered / se) >= abs(delta / se))) / (len(centered) + 1)
        ),
        "bootstrap_critical": critical,
        "mde80_difference": MDE_FACTOR * se,
        "common_multiplier_draws": True,
        "draws": len(centered),
        "seed": SEED,
        "interpretation_if_ci_contains_zero": "design does not detect a difference; not equivalence",
    }


def reconstruct_and_validate(args, BASE, CELLS, FROZEN):
    input_hashes = BASE.validate_public_and_raw_inputs(args)
    input_hashes.update({
        "characteristics": sha256(args.characteristics),
        "baseline_membership": sha256(args.baseline_membership),
        "baseline_normalization": sha256(args.baseline_normalization),
        "baseline_decomposition": sha256(args.baseline_decomposition),
    })
    cells, _, cell_receipt = CELLS.build_exact_age_cells(args)
    route_receipt = BASE.route_conservation(args, cells)
    exposures = FROZEN.exposure_maps(args.lookup, args.rule_b_values)
    computers, names, groups = FROZEN.comp_maps(args.computerization)
    # The computerization file has two otherwise valid Census-2018 rows with
    # missing labels (7640 and 8025).  Use the authenticated Rule-B table only
    # as a label fallback so every named support/exclusion output is complete;
    # this does not alter any exposure value, support rule, or fitted model.
    rule_b_labels = pd.read_csv(args.rule_b_values, dtype={"census2018": str})
    for code, occupation in zip(rule_b_labels["census2018"], rule_b_labels["occupation"]):
        if pd.notna(code) and pd.notna(occupation):
            names.setdefault(str(code).zfill(4), str(occupation))
    rebuilt = BASE.build_recomputed_contract(
        cells, exposures["dv_rating_beta"]["A"], computers["webb_pct_software"], names
    )
    support = list(rebuilt["support"])
    if len(support) != PRIMARY_SUPPORT_COUNT or support_hash(support) != PRIMARY_SUPPORT_HASH:
        raise RuntimeError("fully rebuilt primary support moved")

    stored = pd.read_csv(args.baseline_membership, dtype={"occupation_code": str})
    stored["occupation_code"] = stored.occupation_code.str.zfill(4)
    stored = stored.sort_values("occupation_code").reset_index(drop=True)
    generated = pd.DataFrame(rebuilt["membership"]).sort_values("occupation_code").reset_index(drop=True)
    if stored.occupation_code.tolist() != generated.occupation_code.tolist():
        raise RuntimeError("stored and independently rebuilt occupation supports differ")
    numeric_checks = {
        "preperiod_weight": 1e-12,
        "rule_A_beta": 1e-12,
        "webb_pct_software": 1e-12,
        "webb_z": 1e-12,
    }
    maximum_gaps = {}
    for column, rtol in numeric_checks.items():
        left = pd.to_numeric(stored[column], errors="raise").to_numpy(float)
        right = pd.to_numeric(generated[column], errors="raise").to_numpy(float)
        gap = float(np.max(np.abs(left - right)))
        maximum_gaps[column] = gap
        if not np.allclose(left, right, rtol=rtol, atol=1e-9):
            raise RuntimeError(f"stored BASE-03 column moved: {column}, gap {gap}")
    if not np.array_equal(
        stored.beta_quintile.to_numpy(int), generated.beta_quintile.to_numpy(int)
    ):
        raise RuntimeError("stored BASE-03 beta membership moved")

    normalization = json.loads(args.baseline_normalization.read_text(encoding="utf-8"))
    if normalization["support_hash_sha256"] != PRIMARY_SUPPORT_HASH:
        raise RuntimeError("stored BASE-03 normalization support hash moved")
    if not np.allclose(
        normalization["beta_quintile_cuts"], rebuilt["cuts"], atol=1e-12, rtol=0
    ):
        raise RuntimeError("stored BASE-03 beta cuts moved")

    observed = sorted(cells.month.unique())
    months = [month for month in observed if month != "2022-12"]
    if len(months) != 113 or months[0] != "2017-01" or months[-1] != "2026-07":
        raise RuntimeError(f"corrected static calendar moved: {months}")
    if "2025-10" in months or "2022-12" in months:
        raise RuntimeError("forbidden calendar month entered static model")
    young, older = CELLS.panel_for_ages(cells, support, months, (22, 25), (26, 65))
    if np.any(young.sum(axis=1) <= 0) or np.any(older.sum(axis=1) <= 0):
        raise RuntimeError("primary support contains a nonexistent occupation-age FE")
    contract_validation = {
        "support_count": len(support),
        "support_hash_sha256": support_hash(support),
        "stored_rebuilt_maximum_absolute_gaps": maximum_gaps,
        "stored_membership_exact": True,
        "stored_cut_values_reproduced": True,
        "preperiod_months": len(rebuilt["pre_months"]),
        "outcome_months": len(months),
        "route_conservation_pass": route_receipt["route_conservation_pass"],
    }
    return {
        "cells": cells,
        "cell_receipt": cell_receipt,
        "route_receipt": route_receipt,
        "exposures": exposures,
        "computers": computers,
        "names": names,
        "groups": groups,
        "rebuilt": rebuilt,
        "support": support,
        "months": months,
        "young": young,
        "older": older,
        "input_hashes": input_hashes,
        "contract_validation": contract_validation,
    }


def lambda_grid(args, data, BASE, FROZEN) -> dict:
    support = data["support"]
    months = data["months"]
    weights = np.asarray(data["rebuilt"]["weights"], float)
    young, older = data["young"], data["older"]
    exposure = data["exposures"]
    alpha = np.asarray([exposure["dv_rating_alpha"]["A"][code] for code in support], float)
    beta = np.asarray([exposure["dv_rating_beta"]["A"][code] for code in support], float)
    broad = np.asarray([exposure["dv_rating_gamma"]["A"][code] for code in support], float)
    if np.any(~np.isfinite(np.column_stack([alpha, beta, broad]))):
        raise RuntimeError("nonfinite Eloundou primitive on primary support")
    software = broad - alpha
    reconstructed_beta = alpha + 0.5 * software
    raw_gap = float(np.max(np.abs(beta - reconstructed_beta)))
    if raw_gap > IDENTITY_TOLERANCE:
        raise RuntimeError(f"Eloundou raw identity failed: {raw_gap}")

    beta_groups, beta_cuts, beta_mean, beta_sd = BASE.weighted_contract(beta, weights)
    stored_groups = np.asarray(data["rebuilt"]["quintiles"], int)
    stored_cuts = np.asarray(data["rebuilt"]["cuts"], float)
    if not np.array_equal(beta_groups, stored_groups):
        raise RuntimeError("literal beta groups fail BASE-03 reproduction")
    if not np.allclose(beta_cuts, stored_cuts, atol=1e-12, rtol=0):
        raise RuntimeError("literal beta cuts fail BASE-03 reproduction")
    webb_z = np.asarray(data["rebuilt"]["webb_z"], float)
    signs = np.random.default_rng(SEED).choice(
        np.asarray([-1.0, 1.0]), size=(DRAWS, len(support))
    )

    grid_rows: list[dict] = []
    member_rows: list[dict] = []
    model_objects: dict[str, dict] = {}
    groups_by_lambda: dict[float, np.ndarray] = {}
    raw_by_lambda: dict[float, np.ndarray] = {}
    cuts_by_lambda: dict[float, np.ndarray] = {}

    for lam in LAMBDA_VALUES:
        raw = alpha + lam * software
        groups, cuts, raw_mean, raw_sd = BASE.weighted_contract(raw, weights)
        groups_by_lambda[lam] = groups
        raw_by_lambda[lam] = raw
        cuts_by_lambda[lam] = cuts

        category_columns, category_labels = categorical_design(
            groups, months, {"Webb_software_z": webb_z}
        )
        category_fit, category_influence = fit_design(
            FROZEN, young, older, category_columns
        )
        category_target = category_labels.index("Q5_x_post")
        category_summary, category_draws = infer_term(
            category_fit, category_influence, category_target, signs
        )

        fixed_score = (raw - beta_mean) / beta_sd
        restandardized_score = (raw - raw_mean) / raw_sd
        continuous = {}
        for normalization, score in (
            ("fixed_beta_scale", fixed_score),
            ("lambda_restandardized", restandardized_score),
        ):
            columns, labels = continuous_design(
                score, months, {"Webb_software_z": webb_z}, "X_lambda"
            )
            fit, influence = fit_design(FROZEN, young, older, columns)
            summary, centered = infer_term(fit, influence, 0, signs)
            continuous[normalization] = {
                "fit": fit,
                "influence": influence,
                "labels": labels,
                "summary": summary,
                "draws": centered,
            }

        key = f"lambda_{lam:.2f}"
        model_objects[key] = {
            "category_fit": category_fit,
            "category_influence": category_influence,
            "category_summary": category_summary,
            "category_draws": category_draws,
            "continuous": continuous,
        }
        grid_rows.append({
            "analysis_status": LABEL,
            "lambda": lam,
            "support_occupations": len(support),
            "support_hash_sha256": support_hash(support),
            "raw_mean": raw_mean,
            "raw_sd": raw_sd,
            "beta_anchor_mean": beta_mean,
            "beta_anchor_sd": beta_sd,
            "raw_cuts_json": json.dumps(cuts.tolist()),
            "q1_occupations": int(np.sum(groups == 1)),
            "q5_occupations": int(np.sum(groups == 5)),
            "q1_preperiod_employment_share": float(weights[groups == 1].sum() / weights.sum()),
            "q5_preperiod_employment_share": float(weights[groups == 5].sum() / weights.sum()),
            **{f"categorical_{key}": value for key, value in category_summary.items()},
            **{
                f"fixed_{key}": value
                for key, value in continuous["fixed_beta_scale"]["summary"].items()
            },
            **{
                f"restandardized_{key}": value
                for key, value in continuous["lambda_restandardized"]["summary"].items()
            },
        })
        for code, name, weight, d_value, s_value, raw_value, q in zip(
            support, [data["names"].get(code, code) for code in support], weights,
            alpha, software, raw, groups,
        ):
            member_rows.append({
                "lambda": lam,
                "occupation_code": code,
                "occupation_name": name,
                "preperiod_weight": float(weight),
                "D_alpha": float(d_value),
                "S_broad_minus_alpha": float(s_value),
                "X_lambda": float(raw_value),
                "quintile": int(q),
                "in_Q1": bool(q == 1),
                "in_Q5": bool(q == 5),
                "tied_at_cut": bool(np.any(np.isclose(raw_value, cuts, atol=1e-14, rtol=0))),
            })

    # Independently fit literal beta, both categorical and continuous.
    beta_columns, beta_labels = categorical_design(
        beta_groups, months, {"Webb_software_z": webb_z}
    )
    beta_fit, beta_influence = fit_design(FROZEN, young, older, beta_columns)
    beta_target = beta_labels.index("Q5_x_post")
    beta_summary, beta_draws = infer_term(beta_fit, beta_influence, beta_target, signs)
    beta_z = (beta - beta_mean) / beta_sd
    beta_cont_columns, _ = continuous_design(
        beta_z, months, {"Webb_software_z": webb_z}, "literal_beta_z"
    )
    beta_cont_fit, beta_cont_influence = fit_design(FROZEN, young, older, beta_cont_columns)
    beta_cont_summary, beta_cont_draws = infer_term(
        beta_cont_fit, beta_cont_influence, 0, signs
    )
    mid = model_objects["lambda_0.50"]
    identity = {
        "analysis_status": LABEL,
        "identity": "beta = D + 0.5*S, D=alpha, S=gamma-alpha",
        "maximum_absolute_raw_score_gap": raw_gap,
        "tolerance": IDENTITY_TOLERANCE,
        "lambda_half_cut_maximum_absolute_gap": float(
            np.max(np.abs(cuts_by_lambda[0.5] - beta_cuts))
        ),
        "lambda_half_membership_mismatch_count": int(
            np.sum(groups_by_lambda[0.5] != beta_groups)
        ),
        "lambda_half_categorical_coefficient_gap": float(
            mid["category_summary"]["coefficient"] - beta_summary["coefficient"]
        ),
        "lambda_half_categorical_influence_maximum_absolute_gap": float(
            np.max(np.abs(mid["category_influence"][:, 3] - beta_influence[:, 3]))
        ),
        "lambda_half_fixed_continuous_coefficient_gap": float(
            mid["continuous"]["fixed_beta_scale"]["summary"]["coefficient"]
            - beta_cont_summary["coefficient"]
        ),
        "lambda_half_fixed_continuous_influence_maximum_absolute_gap": float(
            np.max(np.abs(
                mid["continuous"]["fixed_beta_scale"]["influence"][:, 0]
                - beta_cont_influence[:, 0]
            ))
        ),
        "lambda_half_fixed_vs_restandardized_score_maximum_absolute_gap": float(
            np.max(np.abs(
                (raw_by_lambda[0.5] - beta_mean) / beta_sd
                - (raw_by_lambda[0.5] - np.average(raw_by_lambda[0.5], weights=weights))
                / weighted_mean_sd(raw_by_lambda[0.5], weights)[1]
            ))
        ),
        "literal_beta_categorical_coefficient": beta_summary["coefficient"],
        "base03_expected_coefficient": REBUILT_BASELINE_EXPECTED,
        "base03_coefficient_gap": beta_summary["coefficient"] - REBUILT_BASELINE_EXPECTED,
        "literal_beta_continuous_fixed_scale_coefficient": beta_cont_summary["coefficient"],
        "all_identity_checks_pass": True,
    }
    identity_values = [
        identity["maximum_absolute_raw_score_gap"],
        identity["lambda_half_cut_maximum_absolute_gap"],
        abs(identity["lambda_half_categorical_coefficient_gap"]),
        identity["lambda_half_categorical_influence_maximum_absolute_gap"],
        abs(identity["lambda_half_fixed_continuous_coefficient_gap"]),
        identity["lambda_half_fixed_continuous_influence_maximum_absolute_gap"],
        identity["lambda_half_fixed_vs_restandardized_score_maximum_absolute_gap"],
        abs(identity["base03_coefficient_gap"]),
    ]
    if identity["lambda_half_membership_mismatch_count"] != 0 or max(identity_values) > IDENTITY_TOLERANCE:
        identity["all_identity_checks_pass"] = False
        write_json(args.output_dir / "CONSTRUCTION_IDENTITY_AUDIT.json", identity)
        raise RuntimeError(f"lambda-half fail-closed reproduction failed: {identity}")

    pair_rows = []
    for left_lam, right_lam in itertools.combinations(LAMBDA_VALUES, 2):
        left = model_objects[f"lambda_{left_lam:.2f}"]
        right = model_objects[f"lambda_{right_lam:.2f}"]
        pair_rows.append(infer_contrast(
            f"lambda_{left_lam:.2f}", f"lambda_{right_lam:.2f}",
            left["category_summary"]["coefficient"], right["category_summary"]["coefficient"],
            left["category_draws"], right["category_draws"], "categorical_Q5_minus_Q1",
        ))
        for normalization, family in (
            ("fixed_beta_scale", "continuous_fixed_beta_scale"),
            ("lambda_restandardized", "continuous_lambda_restandardized"),
        ):
            left_model = left["continuous"][normalization]
            right_model = right["continuous"][normalization]
            pair_rows.append(infer_contrast(
                f"lambda_{left_lam:.2f}", f"lambda_{right_lam:.2f}",
                left_model["summary"]["coefficient"], right_model["summary"]["coefficient"],
                left_model["draws"], right_model["draws"], family,
            ))

    draw_rows = []
    for draw_index in range(DRAWS):
        row = {"draw": draw_index + 1, "seed": SEED}
        for lam in LAMBDA_VALUES:
            model = model_objects[f"lambda_{lam:.2f}"]
            stem = f"lambda_{lam:.2f}".replace(".", "p")
            row[f"categorical_{stem}"] = float(model["category_draws"][draw_index])
            row[f"fixed_{stem}"] = float(
                model["continuous"]["fixed_beta_scale"]["draws"][draw_index]
            )
            row[f"restandardized_{stem}"] = float(
                model["continuous"]["lambda_restandardized"]["draws"][draw_index]
            )
        draw_rows.append(row)

    transition_rows, overlap_rows, tail_change_rows = tail_diagnostics(
        support, data["names"], weights, groups_by_lambda
    )
    write_json(args.output_dir / "CONSTRUCTION_IDENTITY_AUDIT.json", identity)
    write_csv(args.output_dir / "LAMBDA_GRID_RESULTS.csv", grid_rows)
    write_csv(args.output_dir / "LAMBDA_GRID_MEMBERSHIP.csv", member_rows)
    write_csv(args.output_dir / "LAMBDA_GRID_CENTERED_DRAWS.csv", draw_rows)
    write_csv(args.output_dir / "LAMBDA_PAIRED_DIFFERENCES.csv", pair_rows)
    write_csv(args.output_dir / "LAMBDA_QUINTILE_TRANSITIONS.csv", transition_rows)
    write_csv(args.output_dir / "LAMBDA_TAIL_OVERLAP.csv", overlap_rows)
    write_csv(args.output_dir / "LAMBDA_NAMED_TAIL_CHANGES.csv", tail_change_rows)
    return {
        "alpha": alpha,
        "beta": beta,
        "broad": broad,
        "software": software,
        "weights": weights,
        "signs": signs,
        "groups_by_lambda": groups_by_lambda,
        "raw_by_lambda": raw_by_lambda,
        "grid_rows": grid_rows,
        "model_objects": model_objects,
        "identity": identity,
        "beta_groups": beta_groups,
        "beta_mean": beta_mean,
        "beta_sd": beta_sd,
        "beta_literal_fit": beta_fit,
        "beta_literal_influence": beta_influence,
        "beta_literal_summary": beta_summary,
        "beta_literal_draws": beta_draws,
        "webb_z": webb_z,
    }


def tail_diagnostics(support, names, weights, groups_by_lambda):
    transition_rows, overlap_rows, named_rows = [], [], []
    total_weight = float(weights.sum())
    for left_lam, right_lam in itertools.combinations(LAMBDA_VALUES, 2):
        left = groups_by_lambda[left_lam]
        right = groups_by_lambda[right_lam]
        changed = left != right
        left_q1 = {code for code, q in zip(support, left) if q == 1}
        right_q1 = {code for code, q in zip(support, right) if q == 1}
        left_q5 = {code for code, q in zip(support, left) if q == 5}
        right_q5 = {code for code, q in zip(support, right) if q == 5}
        pair_kind = "adjacent" if np.isclose(right_lam - left_lam, 0.25) else "nonadjacent"
        if np.isclose(left_lam, 0.5) or np.isclose(right_lam, 0.5):
            pair_kind += "|relative_to_beta"
        for left_q in range(1, 6):
            for right_q in range(1, 6):
                mask = (left == left_q) & (right == right_q)
                transition_rows.append({
                    "left_lambda": left_lam,
                    "right_lambda": right_lam,
                    "pair_kind": pair_kind,
                    "left_quintile": left_q,
                    "right_quintile": right_q,
                    "occupation_count": int(mask.sum()),
                    "preperiod_employment_weight": float(weights[mask].sum()),
                    "preperiod_employment_share": float(weights[mask].sum() / total_weight),
                })
        overlap_rows.append({
            "left_lambda": left_lam,
            "right_lambda": right_lam,
            "pair_kind": pair_kind,
            "changed_occupation_count": int(changed.sum()),
            "changed_occupation_share": float(np.mean(changed)),
            "changed_preperiod_employment_share": float(weights[changed].sum() / total_weight),
            "Q1_intersection_count": len(left_q1 & right_q1),
            "Q1_union_count": len(left_q1 | right_q1),
            "Q1_jaccard": len(left_q1 & right_q1) / len(left_q1 | right_q1),
            "Q5_intersection_count": len(left_q5 & right_q5),
            "Q5_union_count": len(left_q5 | right_q5),
            "Q5_jaccard": len(left_q5 & right_q5) / len(left_q5 | right_q5),
        })
        tail_change = ((left == 1) != (right == 1)) | ((left == 5) != (right == 5))
        for code, weight, lq, rq, include in zip(support, weights, left, right, tail_change):
            if include:
                named_rows.append({
                    "left_lambda": left_lam,
                    "right_lambda": right_lam,
                    "pair_kind": pair_kind,
                    "occupation_code": code,
                    "occupation_name": names.get(code, code),
                    "preperiod_weight": float(weight),
                    "left_quintile": int(lq),
                    "right_quintile": int(rq),
                    "left_tail": "Q1" if lq == 1 else ("Q5" if lq == 5 else "middle"),
                    "right_tail": "Q1" if rq == 1 else ("Q5" if rq == 5 else "middle"),
                })
    return transition_rows, overlap_rows, named_rows


def characteristic_audit(args, data, grid, BASE, FROZEN, CELLS) -> dict:
    chars = pd.read_csv(args.characteristics, dtype={"census2018": str})
    chars["census2018"] = chars.census2018.str.zfill(4)
    chars = chars.set_index("census2018")
    support = [
        code for code in data["support"]
        if code in chars.index
        and np.isfinite(pd.to_numeric(chars.at[code, "onet_computers_importance"], errors="coerce"))
        and np.isfinite(pd.to_numeric(chars.at[code, "dingel_neiman_telework"], errors="coerce"))
    ]
    if len(support) != CHAR_SUPPORT_COUNT or support_hash(support) != CHAR_SUPPORT_HASH:
        raise RuntimeError("computer-use/remotability common support moved")
    index = {code: i for i, code in enumerate(data["support"])}
    base_indices = np.asarray([index[code] for code in support], int)
    weights = grid["weights"][base_indices]
    computer = pd.to_numeric(chars.loc[support, "onet_computers_importance"], errors="raise").to_numpy(float)
    remote = pd.to_numeric(chars.loc[support, "dingel_neiman_telework"], errors="raise").to_numpy(float)
    correlation_rows = []
    for lam in LAMBDA_VALUES:
        raw = grid["raw_by_lambda"][lam][base_indices]
        for label, values in (("onet_computer_use", computer), ("dingel_neiman_remotability", remote)):
            correlation_rows.append({
                "lambda": lam,
                "characteristic": label,
                "weighted_correlation": weighted_corr(raw, values, weights),
                "support_occupations": len(support),
                "support_hash_sha256": support_hash(support),
                "weights": "corrected_71_month_preperiod_employment_stock",
            })

    beta = grid["beta"][base_indices]
    beta_q, beta_cuts, _, _ = BASE.weighted_contract(beta, weights)
    webb_raw = np.asarray([data["computers"]["webb_pct_software"][code] for code in support], float)
    webb_mean, webb_sd = weighted_mean_sd(webb_raw, weights)
    computer_mean, computer_sd = weighted_mean_sd(computer, weights)
    remote_mean, remote_sd = weighted_mean_sd(remote, weights)
    standardized = {
        "Webb_software_z": (webb_raw - webb_mean) / webb_sd,
        "ONET_computer_use_z": (computer - computer_mean) / computer_sd,
        "Dingel_Neiman_remotability_z": (remote - remote_mean) / remote_sd,
    }
    young, older = CELLS.panel_for_ages(
        data["cells"], support, data["months"], (22, 25), (26, 65)
    )
    signs = np.random.default_rng(SEED).choice(
        np.asarray([-1.0, 1.0]), size=(DRAWS, len(support))
    )
    model_nuisance = {
        "beta_plus_Webb": ["Webb_software_z"],
        "beta_plus_Webb_plus_computer": ["Webb_software_z", "ONET_computer_use_z"],
        "beta_plus_Webb_plus_remote": ["Webb_software_z", "Dingel_Neiman_remotability_z"],
        "beta_plus_Webb_plus_computer_plus_remote": [
            "Webb_software_z", "ONET_computer_use_z", "Dingel_Neiman_remotability_z"
        ],
    }
    result_rows, coefficient_rows, model_objects = [], [], {}
    for model_name, nuisance_names in model_nuisance.items():
        nuisance = {name: standardized[name] for name in nuisance_names}
        columns, labels = categorical_design(beta_q, data["months"], nuisance)
        fit, influence = fit_design(FROZEN, young, older, columns)
        target = labels.index("Q5_x_post")
        summary, draws = infer_term(fit, influence, target, signs)
        result_rows.append({
            "analysis_status": LABEL,
            "model": model_name,
            "support_occupations": len(support),
            "support_hash_sha256": support_hash(support),
            "beta_cuts_json": json.dumps(beta_cuts.tolist()),
            "nuisance_terms": "|".join(nuisance_names),
            **summary,
        })
        for term_index, term in enumerate(labels):
            term_summary, _ = infer_term(fit, influence, term_index, signs)
            coefficient_rows.append({"model": model_name, "term": term, **term_summary})
        model_objects[model_name] = {
            "fit": fit, "influence": influence, "summary": summary, "draws": draws
        }

    base = model_objects["beta_plus_Webb"]
    paired_rows = []
    for model_name in model_nuisance:
        if model_name == "beta_plus_Webb":
            continue
        model = model_objects[model_name]
        paired_rows.append(infer_contrast(
            model_name, "beta_plus_Webb",
            model["summary"]["coefficient"], base["summary"]["coefficient"],
            model["draws"], base["draws"], "characteristic_conditioning_Q5_minus_Q1",
        ))
    draw_rows = []
    for draw_index in range(DRAWS):
        row = {"draw": draw_index + 1, "seed": SEED}
        for model_name, model in model_objects.items():
            row[model_name] = float(model["draws"][draw_index])
        draw_rows.append(row)
    scaling_rows = [
        {"characteristic": "Webb_software", "weighted_mean": webb_mean, "weighted_sd": webb_sd},
        {"characteristic": "ONET_computer_use", "weighted_mean": computer_mean, "weighted_sd": computer_sd},
        {"characteristic": "Dingel_Neiman_remotability", "weighted_mean": remote_mean, "weighted_sd": remote_sd},
    ]
    for row in scaling_rows:
        row.update({
            "support_occupations": len(support),
            "support_hash_sha256": support_hash(support),
            "weights": "corrected_71_month_preperiod_employment_stock",
        })
    write_csv(args.output_dir / "CHARACTERISTIC_CORRELATIONS.csv", correlation_rows)
    write_csv(args.output_dir / "CHARACTERISTIC_SCALING.csv", scaling_rows)
    write_csv(args.output_dir / "CHARACTERISTIC_CONDITIONING_RESULTS.csv", result_rows)
    write_csv(args.output_dir / "CHARACTERISTIC_CONDITIONING_COEFFICIENTS.csv", coefficient_rows)
    write_csv(args.output_dir / "CHARACTERISTIC_CONDITIONING_PAIRED.csv", paired_rows)
    write_csv(args.output_dir / "CHARACTERISTIC_CONDITIONING_DRAWS.csv", draw_rows)
    return {
        "support": support,
        "correlations": correlation_rows,
        "results": result_rows,
        "paired": paired_rows,
    }


def primitive_joint(args, data, grid, FROZEN) -> dict:
    support, months = data["support"], data["months"]
    young, older = data["young"], data["older"]
    weights = grid["weights"]
    D, S, webb_z = grid["alpha"], grid["software"], grid["webb_z"]
    d_mean, d_sd = weighted_mean_sd(D, weights)
    s_mean, s_sd = weighted_mean_sd(S, weights)
    signs = grid["signs"]
    unit_scores = {
        "raw": {"D": D, "S": S, "Webb": webb_z},
        "standardized": {
            "D": (D - d_mean) / d_sd,
            "S": (S - s_mean) / s_sd,
            "Webb": webb_z,
        },
    }
    result_rows, covariance_rows, draw_rows = [], [], []
    fitted = {}
    for units, scores in unit_scores.items():
        post = np.asarray([month >= "2023-01" for month in months], bool)
        labels = ["D_alpha_x_post", "S_software_complement_x_post", "Webb_software_z_x_post"]
        columns = [scores[name][:, None] * post[None, :] for name in ("D", "S", "Webb")]
        fit, influence = fit_design(FROZEN, young, older, columns)
        centered = signs @ influence
        analytic_cov = influence.T @ influence
        bootstrap_cov = np.cov(centered, rowvar=False, ddof=1)
        if not np.allclose(np.diag(analytic_cov), np.square(fit.standard_error), atol=1e-12, rtol=1e-9):
            raise RuntimeError(f"analytic covariance does not conserve reported SEs for {units}")
        for index, term in enumerate(labels):
            summary, term_draws = infer_term(fit, influence, index, signs)
            result_rows.append({
                "analysis_status": LABEL,
                "units": units,
                "term": term,
                "support_occupations": len(support),
                "support_hash_sha256": support_hash(support),
                "D_weighted_mean": d_mean,
                "D_weighted_sd": d_sd,
                "S_weighted_mean": s_mean,
                "S_weighted_sd": s_sd,
                **summary,
            })
            if not np.allclose(term_draws, centered[:, index], atol=1e-14, rtol=0):
                raise RuntimeError("term draw extraction failed")
        for i, left in enumerate(labels):
            for j, right in enumerate(labels):
                covariance_rows.append({
                    "units": units,
                    "row_term": left,
                    "column_term": right,
                    "analytic_occupation_cluster_covariance": float(analytic_cov[i, j]),
                    "common_draw_covariance": float(bootstrap_cov[i, j]),
                    "analytic_correlation": float(
                        analytic_cov[i, j] / math.sqrt(analytic_cov[i, i] * analytic_cov[j, j])
                    ),
                    "common_draw_correlation": float(
                        bootstrap_cov[i, j] / math.sqrt(bootstrap_cov[i, i] * bootstrap_cov[j, j])
                    ),
                })
        fitted[units] = {"fit": fit, "influence": influence, "centered": centered}

    for draw_index in range(DRAWS):
        draw_rows.append({
            "draw": draw_index + 1,
            "seed": SEED,
            "raw_D": float(fitted["raw"]["centered"][draw_index, 0]),
            "raw_S": float(fitted["raw"]["centered"][draw_index, 1]),
            "raw_Webb": float(fitted["raw"]["centered"][draw_index, 2]),
            "standardized_D": float(fitted["standardized"]["centered"][draw_index, 0]),
            "standardized_S": float(fitted["standardized"]["centered"][draw_index, 1]),
            "standardized_Webb": float(fitted["standardized"]["centered"][draw_index, 2]),
        })

    contrast_rows = []
    contrasts = {
        "one_weighted_SD_D_holding_S_fixed": np.asarray([d_sd, 0.0, 0.0]),
        "one_weighted_SD_S_holding_D_fixed": np.asarray([0.0, s_sd, 0.0]),
        "one_weighted_SD_each_D_and_S": np.asarray([d_sd, s_sd, 0.0]),
    }
    raw_fit, raw_inf = fitted["raw"]["fit"], fitted["raw"]["influence"]
    std_fit, std_inf = fitted["standardized"]["fit"], fitted["standardized"]["influence"]
    for name, raw_contrast in contrasts.items():
        standardized_contrast = np.asarray([
            raw_contrast[0] / d_sd,
            raw_contrast[1] / s_sd,
            raw_contrast[2],
        ])
        raw_estimate = float(raw_contrast @ raw_fit.beta)
        std_estimate = float(standardized_contrast @ std_fit.beta)
        raw_draws = signs @ (raw_inf @ raw_contrast)
        std_draws = signs @ (std_inf @ standardized_contrast)
        gap = float(np.max(np.abs(raw_draws - std_draws)))
        if abs(raw_estimate - std_estimate) > 1e-7 or gap > 1e-7:
            raise RuntimeError(f"raw/standardized primitive contrast failed for {name}")
        se = float(np.std(raw_draws, ddof=1))
        critical = higher_quantile(np.abs(raw_draws / se), 0.95)
        contrast_rows.append({
            "contrast": name,
            "raw_unit_estimate": raw_estimate,
            "standardized_unit_estimate": std_estimate,
            "estimate_gap": raw_estimate - std_estimate,
            "centered_draw_maximum_absolute_gap": gap,
            "paired_bootstrap_se": se,
            "ci_lower": raw_estimate - critical * se,
            "ci_upper": raw_estimate + critical * se,
            "mde80": MDE_FACTOR * se,
            "common_multiplier_draws": True,
        })
    write_csv(args.output_dir / "PRIMITIVE_JOINT_RESULTS.csv", result_rows)
    write_csv(args.output_dir / "PRIMITIVE_JOINT_COVARIANCE.csv", covariance_rows)
    write_csv(args.output_dir / "PRIMITIVE_JOINT_CENTERED_DRAWS.csv", draw_rows)
    write_csv(args.output_dir / "PRIMITIVE_ILLUSTRATIVE_CONTRASTS.csv", contrast_rows)
    return {"results": result_rows, "covariance": covariance_rows, "contrasts": contrast_rows}


def build_broader_beta_contract(cells, beta_map, names, BASE):
    pre_months = BASE.month_range(2017, 1, 2022, 11)
    pre = cells.loc[cells.month.isin(pre_months) & cells.age.between(22, 65)].copy()
    pre["age_group"] = np.where(pre.age.between(22, 25), "young", "older")
    totals = pre.groupby(["occ_code", "age_group"], observed=True).stock.sum().unstack(fill_value=0.0)
    for column in ("young", "older"):
        if column not in totals:
            totals[column] = 0.0
    support = sorted(
        code for code in totals.index
        if totals.at[code, "young"] > 0
        and totals.at[code, "older"] > 0
        and np.isfinite(beta_map.get(code, np.nan))
    )
    weights = totals.loc[support, ["young", "older"]].sum(axis=1).to_numpy(float)
    beta = np.asarray([beta_map[code] for code in support], float)
    q, cuts, mean, sd = BASE.weighted_contract(beta, weights)
    return {
        "support": support,
        "weights": weights,
        "beta": beta,
        "quintiles": q,
        "cuts": cuts,
        "mean": mean,
        "sd": sd,
        "names": names,
    }


def webb_audit(args, data, grid, BASE, FROZEN, CELLS) -> dict:
    support, months = data["support"], data["months"]
    young, older = data["young"], data["older"]
    signs = grid["signs"]
    q = grid["beta_groups"]
    with_columns, with_labels = categorical_design(
        q, months, {"Webb_software_z": grid["webb_z"]}
    )
    with_fit, with_inf = fit_design(FROZEN, young, older, with_columns)
    with_summary, with_draws = infer_term(with_fit, with_inf, with_labels.index("Q5_x_post"), signs)
    without_columns, without_labels = categorical_design(q, months, {})
    without_fit, without_inf = fit_design(FROZEN, young, older, without_columns)
    without_summary, without_draws = infer_term(
        without_fit, without_inf, without_labels.index("Q5_x_post"), signs
    )
    same_support_pair = infer_contrast(
        "beta_without_Webb_468", "beta_with_Webb_468",
        without_summary["coefficient"], with_summary["coefficient"],
        without_draws, with_draws, "Webb_conditioning_same_support",
    )

    broader = build_broader_beta_contract(
        data["cells"], data["exposures"]["dv_rating_beta"]["A"], data["names"], BASE
    )
    broad_support = broader["support"]
    broad_young, broad_older = CELLS.panel_for_ages(
        data["cells"], broad_support, months, (22, 25), (26, 65)
    )
    broad_signs = np.random.default_rng(SEED + 1).choice(
        np.asarray([-1.0, 1.0]), size=(DRAWS, len(broad_support))
    )
    broad_columns, broad_labels = categorical_design(broader["quintiles"], months, {})
    broad_fit, broad_inf = fit_design(FROZEN, broad_young, broad_older, broad_columns)
    broad_summary, _ = infer_term(
        broad_fit, broad_inf, broad_labels.index("Q5_x_post"), broad_signs
    )
    rows = [
        {
            "model": "beta_with_Webb_fixed_468_support",
            "Webb_included": True,
            "support_rule": "fully_rebuilt_beta_and_Webb_support",
            "support_occupations": len(support),
            "support_hash_sha256": support_hash(support),
            "beta_cuts_json": json.dumps(data["rebuilt"]["cuts"].tolist()),
            **with_summary,
        },
        {
            "model": "beta_without_Webb_fixed_468_support",
            "Webb_included": False,
            "support_rule": "fully_rebuilt_beta_and_Webb support held fixed",
            "support_occupations": len(support),
            "support_hash_sha256": support_hash(support),
            "beta_cuts_json": json.dumps(data["rebuilt"]["cuts"].tolist()),
            **without_summary,
        },
        {
            "model": "beta_without_Webb_broader_beta_valid_support",
            "Webb_included": False,
            "support_rule": "positive corrected preperiod stock in both ages and finite strict Rule-A beta; Webb not required",
            "support_occupations": len(broad_support),
            "support_hash_sha256": support_hash(broad_support),
            "beta_cuts_json": json.dumps(broader["cuts"].tolist()),
            **broad_summary,
        },
    ]
    additions = sorted(set(broad_support) - set(support))
    broad_index = {code: i for i, code in enumerate(broad_support)}
    addition_rows = [{
        "occupation_code": code,
        "occupation_name": data["names"].get(code, code),
        "preperiod_weight": float(broader["weights"][broad_index[code]]),
        "rule_A_beta": float(broader["beta"][broad_index[code]]),
        "broader_beta_quintile": int(broader["quintiles"][broad_index[code]]),
        "Webb_software_value": data["computers"]["webb_pct_software"].get(code, np.nan),
        "reason_not_in_468": "Webb unavailable" if not np.isfinite(
            data["computers"]["webb_pct_software"].get(code, np.nan)
        ) else "other primary-contract exclusion",
    } for code in additions]
    if not addition_rows:
        addition_rows = [{
            "occupation_code": "",
            "occupation_name": "NO_ADDITIONAL_OCCUPATIONS",
            "preperiod_weight": 0.0,
            "rule_A_beta": "",
            "broader_beta_quintile": "",
            "Webb_software_value": "",
            "reason_not_in_468": "broader beta-valid support equals the 468 support",
        }]
    support_comparison = {
        "contrast": "broader_beta_valid_without_Webb_minus_fixed_468_without_Webb",
        "coefficient_difference": broad_summary["coefficient"] - without_summary["coefficient"],
        "support_changed": support_hash(broad_support) != support_hash(support),
        "paired_inference_reported": False,
        "broader_support_occupations": len(broad_support),
        "fixed_support_occupations": len(support),
        "additional_occupations": len(additions),
        "additional_preperiod_employment_share_of_broader": float(
            sum(float(broader["weights"][broad_index[code]]) for code in additions)
            / broader["weights"].sum()
        ),
        "interpretation": "descriptive support-changing contrast; not a paired estimate",
    }
    write_csv(args.output_dir / "WEBB_AVAILABILITY_RESULTS.csv", rows)
    write_csv(args.output_dir / "WEBB_SAME_SUPPORT_PAIRED_DIFFERENCE.csv", [same_support_pair])
    write_csv(args.output_dir / "WEBB_SUPPORT_ADDITIONS.csv", addition_rows)
    write_json(args.output_dir / "WEBB_SUPPORT_CHANGE.json", support_comparison)
    return {
        "results": rows,
        "same_support_pair": same_support_pair,
        "support_change": support_comparison,
    }


def archival_and_bridge_audits(args) -> tuple[dict, dict]:
    repo = args.repo_root
    archived_paths = [
        repo / "yax/revision/referee_20260905/results/core/CONSTRUCTION_IDENTITY_AUDIT.json",
        repo / "yax/revision/referee_20260905/results/core/FG_AE_CHANGE_OF_BASIS.json",
        repo / "yax/analysis/postoutcome_v51_referee_repair/YAX_V51_FG_JOINT_MODEL_RESULTS.json",
        repo / "yax/analysis/postoutcome_v51_interpretation_audit/YAX_V51_FG_TO_AE_REPARAMETERIZATION.json",
        repo / "yax/analysis/postoutcome_v51_final_audit/YAX_V51_AE_PRESENTATION_NOTE.md",
    ]
    missing = [str(path.relative_to(repo)) for path in archived_paths if not path.is_file()]
    if missing:
        raise RuntimeError(f"archived F/G-A/E provenance inputs missing: {missing}")
    archive = {
        "analysis_status": LABEL,
        "status": "ARCHIVED_PROVENANCE_ONLY_NOT_SCIENTIFIC_EVIDENCE",
        "files": [{
            "path": str(path.relative_to(repo)),
            "sha256": sha256(path),
        } for path in archived_paths],
        "definitions": {
            "historical_family_basis": "F=(A+E)/2 and G=(A-E)/2",
            "inverse_change_of_basis": "A=F+G and E=F-G before any separately applied scale transformation",
        },
        "new_outcome_models_fit_here": 0,
        "mobility_or_rematching_reopened": False,
        "interpretation": (
            "F/G and A/E are archived coordinate changes. They are not independent exposure "
            "dimensions, validation data, or evidence of technology-induced mobility."
        ),
    }

    bridge_paths = [
        repo / "yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv",
        repo / "yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv.lineage.json",
        repo / "yax/revision/referee_round2_20260905/bridge_uncertainty/ANALYSIS_SPEC.md",
        repo / "yax/revision/referee_round2_20260905/bridge_uncertainty/INTERPRETATION_MEMO.md",
        repo / "yax/revision/referee_round2_20260905/bridge_uncertainty/results/AGE_ALLOCATION_ACCOUNTING_BOUNDS.csv",
        repo / "yax/revision/referee_round2_20260905/bridge_uncertainty/results/AGE_ALLOCATION_TILT_SCENARIOS.csv",
    ]
    missing_bridge = [str(path.relative_to(repo)) for path in bridge_paths if not path.is_file()]
    if missing_bridge:
        raise RuntimeError(f"bridge evidence inputs missing: {missing_bridge}")
    blocker = {
        "analysis_status": LABEL,
        "status": "BLOCKED_NO_GENUINE_AGE_SPECIFIC_VALIDATION_DATA",
        "requested_object": "age-specific Census-2010-to-Census-2018 occupation route probabilities",
        "available_object": "official total-population conversion proportions",
        "evidence_files": [{
            "path": str(path.relative_to(repo)),
            "sha256": sha256(path),
        } for path in bridge_paths],
        "authenticated_dual_coded_validation_dataset_present": False,
        "new_age_specific_shares_estimated": False,
        "existing_accounting_bounds_preserved": True,
        "existing_declared_tilt_sensitivities_preserved": True,
        "reason": (
            "Adjacent CPS vintages and total conversion rates do not observe the same worker "
            "under both source and target occupation codes. They cannot identify age-specific routing."
        ),
        "unblock_requirement": (
            "a versioned validation dataset containing age and both Census-2010 and Census-2018 "
            "occupation codes under a documented sampling design"
        ),
    }
    write_json(args.output_dir / "ARCHIVED_REPARAMETERIZATION_AUDIT.json", archive)
    write_json(args.output_dir / "AGE_SPECIFIC_CROSSWALK_BLOCKER.json", blocker)
    (args.output_dir / "ARCHIVED_REPARAMETERIZATION_AUDIT.md").write_text(
        "# Archived F/G and A/E provenance\n\n"
        "Status: **archived provenance only; not scientific evidence**.\n\n"
        "The historical files listed in `ARCHIVED_REPARAMETERIZATION_AUDIT.json` are retained "
        "to document the coordinate change `F=(A+E)/2`, `G=(A-E)/2`, with inverse "
        "`A=F+G`, `E=F-G` before separately applied scaling. No F/G or A/E outcome model "
        "is fit in this package. The old mobility/rematching analysis is not reopened.\n",
        encoding="utf-8",
    )
    (args.output_dir / "AGE_SPECIFIC_CROSSWALK_BLOCKER.md").write_text(
        "# Age-specific occupation-bridge blocker\n\n"
        "Status: **blocked because no genuine age-specific validation data are present**.\n\n"
        "The authenticated bridge provides total-population conversion proportions. It does not "
        "observe a validation sample with age and both occupation vintages. Accordingly, this "
        "package estimates no age-specific route share. Existing stock-accounting ranges and "
        "predeclared tilt scenarios remain preserved as sensitivities, not corrections or "
        "probabilities. The exact evidence hashes and unblock requirement are in "
        "`AGE_SPECIFIC_CROSSWALK_BLOCKER.json`.\n",
        encoding="utf-8",
    )
    return archive, blocker


def render_summary(path: pathlib.Path, grid, characteristics, primitive, webb) -> None:
    grid_map = {float(row["lambda"]): row for row in grid["grid_rows"]}
    char_map = {row["model"]: row for row in characteristics["results"]}
    with_webb, without_webb, broader = webb["results"]
    lines = [
        "# Corrected-calendar architecture audit results",
        "",
        "Status: **post-outcome exploratory; not part of confirmatory YAX v1.1**.",
        "",
        "## Lambda construction continuum",
        "",
        "| lambda | Q5-Q1 coefficient | 95% occupation wild-score interval | fixed-beta-scale continuous coefficient | restandardized continuous coefficient |",
        "|---:|---:|---:|---:|---:|",
    ]
    for lam in LAMBDA_VALUES:
        row = grid_map[lam]
        lines.append(
            f"| {lam:.2f} | {row['categorical_coefficient']:.6f} | "
            f"[{row['categorical_ci_lower']:.6f}, {row['categorical_ci_upper']:.6f}] | "
            f"{row['fixed_coefficient']:.6f} | {row['restandardized_coefficient']:.6f} |"
        )
    lines.extend([
        "",
        "Lambda 0.5 reproduces literal Rule-A beta and the BASE-03 categorical coefficient "
        f"to the declared tolerance (maximum raw identity gap "
        f"`{grid['identity']['maximum_absolute_raw_score_gap']:.3g}`). All pairwise intervals "
        "and MDEs are in `LAMBDA_PAIRED_DIFFERENCES.csv`; a null-containing interval is not "
        "an equivalence result.",
        "",
        "## Focused characteristic conditioning at lambda 0.5",
        "",
        "| model | Q5-Q1 coefficient | 95% interval |",
        "|---|---:|---:|",
    ])
    for name in (
        "beta_plus_Webb",
        "beta_plus_Webb_plus_computer",
        "beta_plus_Webb_plus_remote",
        "beta_plus_Webb_plus_computer_plus_remote",
    ):
        row = char_map[name]
        lines.append(
            f"| {name} | {row['coefficient']:.6f} | [{row['ci_lower']:.6f}, {row['ci_upper']:.6f}] |"
        )
    lines.extend([
        "",
        "These 408-occupation models hold support fixed. Computer use and remotability are "
        "static occupational characteristics, not realized adoption; conditioning does not "
        "purify a causal AI effect.",
        "",
        "## Webb conditioning versus Webb availability",
        "",
        f"On the fixed 468 support, adding Webb changes the point estimate from "
        f"{without_webb['coefficient']:.6f} to {with_webb['coefficient']:.6f}. The common-draw "
        f"paired difference and interval are reported separately. Removing the Webb availability "
        f"requirement expands support to {broader['support_occupations']} occupations and yields "
        f"{broader['coefficient']:.6f}; that support-changing comparison is descriptive and has no "
        "paired CI.",
        "",
        "## Primitive model and exclusions",
        "",
        "The direct D/S model is reported in raw and standardized units with its full covariance "
        "and common draws. The two presentations span the same fitted column space. Historical "
        "F/G and A/E rotations remain archived provenance only, mobility/rematching is not "
        "reopened, and age-specific bridge shares remain blocked absent genuine validation data.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def run(args) -> None:
    args.output_dir.mkdir(parents=True, exist_ok=False)
    repo = args.repo_root.resolve()
    BASE = import_path(
        "yax_r3_arch_base",
        repo / "yax/revision/substantive_r3_20260905/rebuilt_baseline/run_rebuilt_corrected_baseline.py",
    )
    CELLS = import_path(
        "yax_r3_arch_cells", repo / "yax/revision/referee_20260905/run_referee_cells.py"
    )
    FROZEN = import_path("yax_r3_arch_frozen", repo / "yax/analysis/run_frozen_v11.py")
    failures: list[dict] = []
    try:
        data = reconstruct_and_validate(args, BASE, CELLS, FROZEN)
        grid = lambda_grid(args, data, BASE, FROZEN)
        characteristics = characteristic_audit(args, data, grid, BASE, FROZEN, CELLS)
        primitive = primitive_joint(args, data, grid, FROZEN)
        webb = webb_audit(args, data, grid, BASE, FROZEN, CELLS)
        archive, blocker = archival_and_bridge_audits(args)
        render_summary(args.output_dir / "RESULTS_SUMMARY.md", grid, characteristics, primitive, webb)
    except Exception as error:
        failures.append({
            "stage": "architecture_runner",
            "exception_type": type(error).__name__,
            "message": str(error),
        })
        write_json(args.output_dir / "MODEL_FAILURES.json", failures)
        raise
    write_json(args.output_dir / "MODEL_FAILURES.json", failures)

    output_hashes = {
        path.name: sha256(path)
        for path in sorted(args.output_dir.iterdir())
        if path.is_file() and path.name not in {"EXECUTION_RECEIPT.json", "SELF_CHECK.json"}
    }
    receipt = {
        "record": "YAX R3 fully rebuilt corrected-calendar architecture audit",
        "analysis_status": LABEL,
        "status": "PASS_ARCHITECTURE_AUDIT",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True
        ).strip(),
        "script_sha256": sha256(pathlib.Path(__file__)),
        "analysis_spec_sha256": sha256(pathlib.Path(__file__).with_name("ANALYSIS_SPEC_BEFORE_RESULTS.md")),
        "input_hashes": data["input_hashes"],
        "contract_validation": data["contract_validation"],
        "cell_build_receipt": data["cell_receipt"],
        "route_conservation_receipt": data["route_receipt"],
        "bootstrap": {
            "draws": DRAWS,
            "seed": SEED,
            "cluster": "occupation",
            "same_ordered_support_uses_common_multiplier_matrix": True,
            "mde80_factor": MDE_FACTOR,
        },
        "lambda_values": list(LAMBDA_VALUES),
        "identity_audit": grid["identity"],
        "characteristic_support": {
            "occupations": len(characteristics["support"]),
            "support_hash_sha256": support_hash(characteristics["support"]),
        },
        "webb_support_change": webb["support_change"],
        "archived_reparameterization_status": archive["status"],
        "age_specific_bridge_status": blocker["status"],
        "model_failures": failures,
        "output_hashes": output_hashes,
        "private_row_level_data_written": False,
    }
    write_json(args.output_dir / "EXECUTION_RECEIPT.json", receipt)
    print(json.dumps({
        "status": receipt["status"],
        "lambda_half_coefficient": grid["identity"]["literal_beta_categorical_coefficient"],
        "characteristic_support": len(characteristics["support"]),
        "broader_beta_support": webb["support_change"]["broader_support_occupations"],
        "failures": len(failures),
    }, indent=2, sort_keys=True))


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--repo-root", type=pathlib.Path, required=True)
    value.add_argument("--microdata", type=pathlib.Path, required=True)
    value.add_argument("--repair-microdata", type=pathlib.Path, required=True)
    value.add_argument("--lookup", type=pathlib.Path, required=True)
    value.add_argument("--computerization", type=pathlib.Path, required=True)
    value.add_argument("--rule-b-values", type=pathlib.Path, required=True)
    value.add_argument("--bridge", type=pathlib.Path, required=True)
    value.add_argument("--characteristics", type=pathlib.Path, required=True)
    value.add_argument("--baseline-membership", type=pathlib.Path, required=True)
    value.add_argument("--baseline-normalization", type=pathlib.Path, required=True)
    value.add_argument("--baseline-decomposition", type=pathlib.Path, required=True)
    value.add_argument("--output-dir", type=pathlib.Path, required=True)
    return value


if __name__ == "__main__":
    run(parser().parse_args())
