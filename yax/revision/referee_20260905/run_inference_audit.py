#!/usr/bin/env python3
"""Assemble inference diagnostics and test full wild-refit feasibility.

POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import pathlib

import numpy as np
import pandas as pd

import run_referee_core as CORE


HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[3]
FROZEN = CORE.FROZEN
LABEL = "POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1"
SEED = 2026090503
REFIT_DRAWS = 199


def write_csv(path: pathlib.Path, rows: list[dict]) -> None:
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def write_json(path: pathlib.Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def inference_table(args):
    rows = pd.read_csv(args.joint_sign)
    rows["coefficient_percent_relative_stock_ratio"] = (
        100 * np.expm1(rows.coefficient_log_points))
    rows["simultaneous_upper_percent_relative_stock_ratio"] = (
        100 * np.expm1(rows.simultaneous_one_sided_upper_95))
    rows["intersection_union_p"] = rows.marginal_one_sided_tail_area.max()
    rows["iut_rule"] = "max of six valid marginal one-sided p-values"
    rows["simultaneous_critical"] = 2.26035887801162
    rows["predeclared_simultaneous_all_negative"] = bool(
        rows.upper_bound_below_zero.astype(bool).all())
    rows["interpretation"] = (
        "IUT p=.045 and failed simultaneous upper-band criterion are distinct deliverables")
    return rows.to_dict("records")


def information_table(args):
    residual = pd.read_csv(args.residual_support)
    residual = residual.loc[
        residual.ai_measure.eq("dv_rating_beta") &
        residual.computerization_measure.eq("webb_pct_software")].iloc[0]
    fitted = pd.read_csv(args.fitted_information).iloc[0]
    loco = json.loads(args.loco_results.read_text())["primary"]
    return [{
        "analysis_status": LABEL,
        "specification": "primary_beta_Webb",
        "nominal_occupation_clusters": int(fitted.occupations),
        "continuous_residual_effective_occupations": float(
            residual.effective_identifying_occupations),
        "continuous_residual_top_five_share": float(
            residual.top_five_residual_variance_share),
        "fitted_information_effective_occupations": float(
            fitted.headline_information_effective_occupations),
        "fitted_information_top_five_share": float(
            fitted.headline_information_top_five_share),
        "largest_LOCO_absolute_coefficient_movement": float(
            loco["maximum_absolute_movement"]),
        "LOCO_sign_changes": int(loco["sign_changes"]),
        "warning": (
            "residual support, fitted curvature, cluster-score influence, LOCO movement, "
            "and independent sampling clusters are different objects"),
    }]


def fit_inputs(young, older, regressors):
    n_occ, n_month = young.shape
    total = (young + older).reshape(-1)
    occupation = np.repeat(np.arange(n_occ), n_month)
    month = np.tile(np.arange(n_month), n_occ)
    fit = FROZEN.ENGINE.fit_grouped_logit_fe(
        young.reshape(-1), total, occupation, month, regressors, max_iterations=5000)
    return fit, total, occupation, month


def refit_feasibility(label, young, older, regressors, signs):
    fit, total, occupation, month = fit_inputs(young, older, regressors)
    mu = total * fit.fitted_probability
    residual = young.reshape(-1) - mu
    rows = []
    valid_refits = 0
    for draw_index, multiplier in enumerate(signs, 1):
        pseudo = mu + multiplier[occupation] * residual
        positive = total > 0
        invalid_low = int(np.sum(pseudo[positive] < 0))
        invalid_high = int(np.sum(pseudo[positive] > total[positive]))
        converged = False
        if invalid_low == 0 and invalid_high == 0:
            trial = FROZEN.ENGINE.fit_grouped_logit_fe(
                pseudo, total, occupation, month, regressors, max_iterations=5000)
            converged = bool(trial.converged)
            valid_refits += int(converged)
        rows.append({
            "analysis_status": LABEL, "model": label, "draw": draw_index,
            "invalid_below_zero_cells": invalid_low,
            "invalid_above_total_cells": invalid_high,
            "admissible_grouped_binomial_pseudo_outcome": invalid_low + invalid_high == 0,
            "full_refit_converged": converged,
        })
    summary = {
        "model": label, "requested_common_Rademacher_draws": len(signs),
        "admissible_draws": int(sum(row["admissible_grouped_binomial_pseudo_outcome"]
                                    for row in rows)),
        "converged_full_refits": valid_refits,
        "status": ("PASS" if valid_refits == len(signs)
                   else "FAILED_GROUPED_BINOMIAL_OUTCOME_BOUNDS"),
        "interpretation": (
            "The literal residual wild pseudo-outcome must stay in [0,total] for the "
            "grouped-binomial engine. No clipping or different bootstrap was substituted."),
    }
    return rows, summary


def refit_audit(args, data):
    webb_map = data["computers"]["webb_pct_software"]
    prepared = FROZEN.prepare_model(
        data["panel"], data["occupations"], data["static_months"],
        data["exposures"]["dv_rating_beta"]["A"], webb_map, scale="q5_q1")
    signs_primary = np.random.default_rng(SEED).choice(
        np.array([-1., 1.]), size=(REFIT_DRAWS, len(prepared["occupations"])))
    all_rows, primary_summary = refit_feasibility(
        "primary_beta_Webb", prepared["young"], prepared["older"],
        prepared["regressors"], signs_primary)
    summaries = [primary_summary]

    chars = pd.read_csv(args.characteristics, dtype={"census2018": str})
    chars.census2018 = chars.census2018.str.zfill(4)
    chars = chars.set_index("census2018")
    supports = [set(code for code in data["occupations"]
                    if np.isfinite(data["exposures"][measure]["A"].get(code, np.nan)) and
                    np.isfinite(webb_map.get(code, np.nan))) for measure in CORE.MEASURES]
    common = sorted(set.intersection(*supports))
    pre_weights = chars.loc[common, "preperiod_employment_weight"].to_numpy(float)
    z = {}
    for measure in CORE.MEASURES:
        values = np.array([data["exposures"][measure]["A"][code] for code in common])
        z[measure] = CORE.standardize(values, pre_weights)[0]
    A = np.mean(np.column_stack([z[value] for value in CORE.AIOE]), axis=1)
    E = np.mean(np.column_stack([z["dv_rating_beta"], z["dv_rating_gamma"]]), axis=1)
    F, G = (A + E) / 2, (A - E) / 2
    webb = np.array([webb_map[code] for code in common])
    raw = {"F": F, "G": G, "Webb": webb}
    standardized = np.column_stack([CORE.standardize(value, pre_weights)[0]
                                    for value in raw.values()])
    post = np.array([month >= "2023-01" for month in data["static_months"]])
    regressors = np.column_stack(
        [(standardized[:, index, None] * post[None, :]).reshape(-1)
         for index in range(standardized.shape[1])])
    young, older = FROZEN.panel_arrays(data["panel"], common, data["static_months"])
    signs_fg = np.random.default_rng(SEED).choice(
        np.array([-1., 1.]), size=(REFIT_DRAWS, len(common)))
    rows, summary = refit_feasibility(
        "no_alpha_F_G_Webb", young, older, regressors, signs_fg)
    all_rows.extend(rows); summaries.append(summary)
    return all_rows, summaries


def run(args):
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = CORE.load_data(args)
    inference = inference_table(args)
    information = information_table(args)
    refit_rows, refit_summary = refit_audit(args, data)
    write_csv(args.output_dir / "INFERENCE_AUDIT.csv", inference)
    write_csv(args.output_dir / "INFORMATION_OBJECTS.csv", information)
    write_csv(args.output_dir / "FULL_WILD_REFIT_FEASIBILITY.csv", refit_rows)
    write_json(args.output_dir / "FULL_WILD_REFIT_SUMMARY.json", refit_summary)
    two_way = pd.read_csv(args.two_way)
    write_csv(args.output_dir / "DEPENDENCE_SENSITIVITY.csv", two_way.to_dict("records"))
    precision = {
        "primary": {"prospective_se": .0121696, "realized_se": .0444098,
                    "ratio": .0444098 / .0121696, "same_estimand_support_units": True},
        "paired_beta_minus_alpha": {"prospective_se": .0116715,
                    "realized_se": .036968, "ratio": .036968 / .0116715,
                    "same_estimand_support_units": True},
        "identified_explanation": None,
        "conclusion": (
            "The synthetic DGP materially understated realized uncertainty. Existing artifacts "
            "do not separately identify the contributions of post-period common shocks, "
            "cross-occupation covariance, survey noise, structural composition, and misspecification."),
    }
    write_json(args.output_dir / "PRECISION_GAP_AUDIT.json", precision)
    print(json.dumps({"status": "PASS_INFERENCE_AUDIT",
                      "baseline": data["baseline_reproduced"],
                      "full_refit": refit_summary}, indent=2))


def parser():
    value = CORE.parser()
    value.description = __doc__
    value.add_argument("--joint-sign", type=pathlib.Path,
                       default=ROOT / "yax/analysis/postoutcome_phase3_final/YAX_PHASE3_JOINT_SIGN_INFERENCE.csv")
    value.add_argument("--residual-support", type=pathlib.Path,
                       default=ROOT / "yax/analysis/audit/TEST_B_IDENTIFYING_VARIATION_FULL.csv")
    value.add_argument("--fitted-information", type=pathlib.Path,
                       default=ROOT / "yax/analysis/postoutcome_v3_supplementary/HEADLINE_INFORMATION_SUPPORT_SUMMARY.csv")
    value.add_argument("--loco-results", type=pathlib.Path,
                       default=ROOT / "yax/analysis/postoutcome_v51_final_audit/YAX_V51_LOCO_RESULTS.json")
    value.add_argument("--two-way", type=pathlib.Path,
                       default=ROOT / "yax/analysis/postoutcome_v51_referee_repair/YAX_V51_TWOWAY_CLUSTER_SENSITIVITY.csv")
    return value


if __name__ == "__main__":
    run(parser().parse_args())
