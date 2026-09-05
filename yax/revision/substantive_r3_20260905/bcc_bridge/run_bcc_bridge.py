#!/usr/bin/env python3
"""Run the registered R3 public BCC-grouping CPS stock bridge.

POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1.
This is an approximate public-grouping bridge, not an ADP replication.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np


HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[4]
LABEL = "POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1"
BCC_VERSION = "2026-08-12"
DRAWS = 9999
SEED = 2026090561
MDE_FACTOR = 1.959963984540054 + 0.8416212335729143
REFERENCE_BIN = "2022Q4"
GROUPINGS = (
    "historical_YAX_employment_weighted_approximation",
    "public_dashboard_equal_occupation_approximation",
)
STRUCTURES = (
    "occupation_plus_calendar_month_FE",
    "SOC2_x_post",
    "SOC2_x_calendar_month",
)
DYNAMIC_STRUCTURES = (
    "occupation_plus_calendar_month_FE",
    "SOC2_x_calendar_month",
)


def import_path(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


COMP = import_path(
    "yax_r3_bcc_composition",
    ROOT / "yax/revision/referee_round2_20260905/composition_influence/run_composition_influence.py",
)
FROZEN = COMP.FROZEN
CELLS = COMP.CELLS


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
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: pathlib.Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def quantile(values, probability):
    try:
        return float(np.quantile(values, probability, method="higher"))
    except TypeError:
        return float(np.quantile(values, probability, interpolation="higher"))


def weighted_quintiles_with_cuts(values, weights):
    values = np.asarray(values, float)
    weights = np.asarray(weights, float)
    if len(values) != len(weights) or len(values) == 0:
        raise ValueError("values and weights must have the same positive length")
    if not np.all(np.isfinite(values)) or not np.all(np.isfinite(weights)):
        raise ValueError("nonfinite values or weights")
    if np.any(weights <= 0):
        raise ValueError("cut weights must be positive")
    order = np.argsort(values, kind="mergesort")
    cumulative = np.cumsum(weights[order])
    cuts = np.array([
        values[order[min(
            np.searchsorted(cumulative, share * cumulative[-1], side="left"),
            len(values) - 1,
        )]]
        for share in (.2, .4, .6, .8)
    ])
    if np.any(cuts[:-1] >= cuts[1:]):
        raise RuntimeError("quintile cuts collapsed: {}".format(cuts.tolist()))
    # Scores exactly equal to a cut stay in the lower group.  All tied scores
    # therefore receive the same assignment.
    quintiles = np.searchsorted(cuts, values, side="left") + 1
    return quintiles.astype(int), cuts


def quarter(month: str) -> str:
    year, number = month.split("-")
    return "{}Q{}".format(year, (int(number) - 1) // 3 + 1)


def fixed_effect_codes(majors, n_month, structure):
    if structure in ("occupation_plus_calendar_month_FE", "SOC2_x_post"):
        return np.tile(np.arange(n_month), len(majors))
    if structure == "SOC2_x_calendar_month":
        levels = {value: index for index, value in enumerate(sorted(set(majors.tolist())))}
        return np.concatenate([
            levels[majors[index]] * n_month + np.arange(n_month)
            for index in range(len(majors))
        ])
    raise ValueError("unknown fixed-effect structure {}".format(structure))


def common_metadata(grouping_name, grouping_description, cut_rule, cuts, structure,
                    first_month, last_month, contrast):
    return {
        "analysis_status": LABEL,
        "bcc_version": BCC_VERSION,
        "bridge_status": "approximate_public_grouping_bridge_not_replication",
        "source_population": "national CPS employed persons with positive final person weights",
        "outcome_unit": "CPS weighted person employment stock aggregated to occupation-month-age group",
        "young_age_band": "22-25",
        "comparison_age_band": "26-65",
        "first_month": first_month,
        "last_month": last_month,
        "contrast": contrast,
        "exposure_measure": "Eloundou_et_al_GPT4_beta_Rule_A_Census2018",
        "grouping_name": grouping_name,
        "grouping_description": grouping_description,
        "cut_rule": cut_rule,
        "cut_values_json": json.dumps([float(value) for value in cuts]),
        "tie_rule": "ties_preserved; score_equal_to_cut_assigned_to_lower_quintile",
        "membership_concordance_status": "UNVERIFIED_no_complete_public_BCC_membership_or_tie_algorithm",
        "regression_weight": "CPS_WTFINL_stock_in_grouped_binomial_cell_totals",
        "conditioning_structure": structure,
        "inference": "occupation_cluster_sandwich_and_9999_common_Rademacher_wild_score_draws",
    }


def build_static_regressors(high, webb_z, post, majors, stock, structure):
    columns = [((high[:, None]) & post[None, :]).reshape(-1).astype(float)]
    labels = ["top_two_vs_bottom_three_x_post"]
    columns.append((webb_z[:, None] * post[None, :]).reshape(-1))
    labels.append("Webb_software_historical_z_x_post")
    reference = ""
    if structure == "SOC2_x_post":
        levels = sorted(set(majors.tolist()))
        weights = {group: float(stock[majors == group].sum()) for group in levels}
        reference = max(levels, key=lambda group: (weights[group], group))
        for group in levels:
            if group == reference:
                continue
            columns.append(
                (((majors == group)[:, None]) & post[None, :]).reshape(-1).astype(float)
            )
            labels.append("SOC2_{}_x_post".format(group))
    return np.column_stack(columns), labels, reference


def scalar_result(estimate, influence, signs):
    influence = np.asarray(influence, float)
    centered = signs @ influence
    se = float(np.sqrt(np.sum(np.square(influence))))
    bootstrap_se = float(np.std(centered, ddof=1))
    if not np.isfinite(se) or se <= 0:
        raise RuntimeError("nonpositive cluster standard error")
    critical = quantile(np.abs(centered / se), .95)
    statistic = abs(estimate / se)
    return {
        "coefficient": float(estimate),
        "occupation_cluster_se": se,
        "bootstrap_se": bootstrap_se,
        "ci_lower": float(estimate - critical * se),
        "ci_upper": float(estimate + critical * se),
        "wild_score_p_value": float(
            (1 + np.sum(np.abs(centered / se) >= statistic)) / (len(centered) + 1)
        ),
        "bootstrap_critical": critical,
        "normal_theory_MDE80": float(MDE_FACTOR * se),
        "bootstrap_draws": int(len(centered)),
    }, centered


def paired_result(left_estimate, left_influence, right_estimate, right_influence, signs):
    delta = float(left_estimate - right_estimate)
    influence = np.asarray(left_influence, float) - np.asarray(right_influence, float)
    summary, centered = scalar_result(delta, influence, signs)
    summary.update({
        "coefficient_difference": summary.pop("coefficient"),
        "paired_occupation_cluster_se": summary.pop("occupation_cluster_se"),
        "paired_bootstrap_se": summary.pop("bootstrap_se"),
        "common_occupation_multipliers": True,
    })
    return summary, centered


def joint_zero(beta, influence, signs):
    beta = np.asarray(beta, float)
    influence = np.asarray(influence, float)
    covariance = influence.T @ influence
    inverse = np.linalg.pinv(covariance)
    statistic = float(beta @ inverse @ beta)
    centered = signs @ influence
    draws = np.einsum("ij,jk,ik->i", centered, inverse, centered)
    return {
        "wald_statistic": statistic,
        "wild_score_p_value": float((1 + np.sum(draws >= statistic)) / (len(draws) + 1)),
        "restrictions": int(len(beta)),
        "covariance_rank": int(np.linalg.matrix_rank(covariance)),
        "bootstrap_draws": int(len(draws)),
    }


def fit_static(grouping_name, high, webb_z, young, older, months, majors, signs,
               metadata):
    n_occ, n_month = young.shape
    post = np.array([month >= "2023-01" for month in months])
    stock = (young + older).sum(axis=1)
    models = {}
    result_rows, information_rows, failures = [], [], []
    for structure in STRUCTURES:
        try:
            regressors, labels, reference = build_static_regressors(
                high, webb_z, post, majors, stock, structure,
            )
            second = fixed_effect_codes(majors, n_month, structure)
            fit, influence, details = COMP.fit_absorbed(young, older, regressors, second)
            if influence.shape[0] != n_occ:
                raise RuntimeError("occupation influence dimension changed")
            summary, centered = scalar_result(float(fit.beta[0]), influence[:, 0], signs)
            analytic = float(fit.standard_error[0])
            if not np.isclose(analytic, summary["occupation_cluster_se"], rtol=1e-7, atol=1e-10):
                raise RuntimeError("fitted and stored-influence cluster SEs disagree")
            info = COMP.conditional_information(details, 0)
            row = {
                **metadata[structure],
                "model_id": "{}_{}".format(grouping_name, structure),
                "months": n_month,
                "support_occupations": n_occ,
                "support_hash_sha256": support_hash(metadata["support"]),
                "high_occupation_count": int(high.sum()),
                "low_occupation_count": int((~high).sum()),
                "high_corrected_calendar_stock_share": float(stock[high].sum() / stock.sum()),
                "slope_labels_json": json.dumps(labels),
                "SOC2_post_reference": reference,
                "positive_total_rows": int(details["positive_total_rows"]),
                "zero_total_rows": int(details["zero_total_rows"]),
                **summary,
                **{key: value for key, value in info.items() if key != "occupation_information"},
            }
            result_rows.append(row)
            for index, code in enumerate(metadata["support"]):
                information_rows.append({
                    "analysis_status": LABEL,
                    "bcc_version": BCC_VERSION,
                    "grouping_name": grouping_name,
                    "conditioning_structure": structure,
                    "occupation_code": code,
                    "occupation_name": metadata["names"].get(code, code),
                    "SOC2": majors[index],
                    "high_group": bool(high[index]),
                    "corrected_calendar_stock": float(stock[index]),
                    "conditional_target_information": float(info["occupation_information"][index]),
                    "conditional_target_information_share": float(
                        info["occupation_information"][index] /
                        info["conditional_target_information"]
                    ) if info["conditional_target_information"] > 0 else np.nan,
                })
            models[structure] = {
                "fit": fit,
                "influence": influence,
                "details": details,
                "centered": centered,
                "row": row,
            }
        except Exception as error:
            failures.append({
                "analysis_status": LABEL,
                "module": "static",
                "grouping_name": grouping_name,
                "conditioning_structure": structure,
                "error_type": type(error).__name__,
                "message": str(error),
            })
    return models, result_rows, information_rows, failures


def build_dynamic_regressors(high, webb_z, months):
    month_bins = np.array([quarter(month) for month in months], object)
    bins = sorted(set(month_bins.tolist()))
    if REFERENCE_BIN not in bins:
        raise RuntimeError("dynamic reference bin is absent")
    event_bins = [value for value in bins if value != REFERENCE_BIN]
    columns, labels, target_indices = [], [], []
    for event_bin in event_bins:
        period = month_bins == event_bin
        columns.append(
            ((high[:, None]) & period[None, :]).reshape(-1).astype(float)
        )
        labels.append("top_two_vs_bottom_three_x_{}".format(event_bin))
        target_indices.append(len(columns) - 1)
        columns.append((webb_z[:, None] * period[None, :]).reshape(-1))
        labels.append("Webb_historical_z_x_{}".format(event_bin))
    return np.column_stack(columns), labels, target_indices, event_bins, month_bins


def fit_dynamics(grouping_name, high, webb_z, young, older, months, majors, signs,
                 metadata):
    n_occ, n_month = young.shape
    paths, joint_rows, covariance_rows, influence_rows, failures = [], [], [], [], []
    models = {}
    regressors, labels, targets, event_bins, month_bins = build_dynamic_regressors(
        high, webb_z, months,
    )
    for structure in DYNAMIC_STRUCTURES:
        try:
            second = fixed_effect_codes(majors, n_month, structure)
            fit, influence, details = COMP.fit_absorbed(young, older, regressors, second)
            target_beta = fit.beta[targets]
            target_influence = influence[:, targets]
            covariance = target_influence.T @ target_influence
            ses = np.sqrt(np.maximum(np.diag(covariance), 0.0))
            if np.any(ses <= 0):
                raise RuntimeError("dynamic target has nonpositive cluster SE")
            centered = signs @ target_influence
            simultaneous = quantile(np.max(np.abs(centered / ses[None, :]), axis=1), .95)
            for index, (event_bin, estimate, se) in enumerate(zip(event_bins, target_beta, ses)):
                summary, _ = scalar_result(estimate, target_influence[:, index], signs)
                paths.append({
                    **metadata[structure],
                    "model_id": "{}_dynamic_{}".format(grouping_name, structure),
                    "event_bin": event_bin,
                    "reference_bin": REFERENCE_BIN,
                    "observed_months_in_bin": int(np.sum(month_bins == event_bin)),
                    "simultaneous_path_ci_lower": float(estimate - simultaneous * se),
                    "simultaneous_path_ci_upper": float(estimate + simultaneous * se),
                    "simultaneous_path_critical": simultaneous,
                    **summary,
                })
            for subset_name, subset in (
                ("pre_reference", np.array([value < REFERENCE_BIN for value in event_bins])),
                ("post_2022", np.array([value >= "2023Q1" for value in event_bins])),
            ):
                joint_rows.append({
                    **metadata[structure],
                    "model_id": "{}_dynamic_{}".format(grouping_name, structure),
                    "test": "all_{}_dynamic_coefficients_zero".format(subset_name),
                    **joint_zero(target_beta[subset], target_influence[:, subset], signs),
                })
            for left_index, left in enumerate(event_bins):
                for right_index, right in enumerate(event_bins):
                    covariance_rows.append({
                        "analysis_status": LABEL,
                        "bcc_version": BCC_VERSION,
                        "grouping_name": grouping_name,
                        "conditioning_structure": structure,
                        "row_event_bin": left,
                        "column_event_bin": right,
                        "occupation_cluster_covariance": float(covariance[left_index, right_index]),
                    })
            for occupation_index, code in enumerate(metadata["support"]):
                row = {
                    "analysis_status": LABEL,
                    "bcc_version": BCC_VERSION,
                    "grouping_name": grouping_name,
                    "conditioning_structure": structure,
                    "occupation_code": code,
                    "occupation_name": metadata["names"].get(code, code),
                    "SOC2": majors[occupation_index],
                }
                for event_index, event_bin in enumerate(event_bins):
                    row["influence_{}".format(event_bin)] = float(
                        target_influence[occupation_index, event_index]
                    )
                influence_rows.append(row)
            models[structure] = {
                "beta": target_beta,
                "influence": target_influence,
                "event_bins": event_bins,
                "simultaneous": simultaneous,
            }
        except Exception as error:
            failures.append({
                "analysis_status": LABEL,
                "module": "dynamic",
                "grouping_name": grouping_name,
                "conditioning_structure": structure,
                "error_type": type(error).__name__,
                "message": str(error),
            })
    return models, paths, joint_rows, covariance_rows, influence_rows, failures


def paired_dynamic_rows(equal_models, weighted_models, signs):
    rows = []
    for structure in DYNAMIC_STRUCTURES:
        if structure not in equal_models or structure not in weighted_models:
            continue
        left, right = equal_models[structure], weighted_models[structure]
        if left["event_bins"] != right["event_bins"]:
            raise RuntimeError("paired dynamic event bins differ")
        delta = left["beta"] - right["beta"]
        influence = left["influence"] - right["influence"]
        ses = np.sqrt(np.maximum(np.diag(influence.T @ influence), 0.0))
        centered = signs @ influence
        valid = ses > 0
        simultaneous = quantile(
            np.max(np.abs(centered[:, valid] / ses[None, valid]), axis=1), .95
        ) if np.any(valid) else np.nan
        for index, event_bin in enumerate(left["event_bins"]):
            if ses[index] > 0:
                summary, _ = scalar_result(delta[index], influence[:, index], signs)
                lower = float(delta[index] - simultaneous * ses[index])
                upper = float(delta[index] + simultaneous * ses[index])
            else:
                summary = {
                    "coefficient": float(delta[index]),
                    "occupation_cluster_se": 0.0,
                    "bootstrap_se": 0.0,
                    "ci_lower": float(delta[index]),
                    "ci_upper": float(delta[index]),
                    "wild_score_p_value": np.nan,
                    "bootstrap_critical": np.nan,
                    "normal_theory_MDE80": 0.0,
                    "bootstrap_draws": DRAWS,
                }
                lower, upper = float(delta[index]), float(delta[index])
            rows.append({
                "analysis_status": LABEL,
                "bcc_version": BCC_VERSION,
                "contrast": "equal_occupation_approximation_minus_historical_employment_weighted_approximation",
                "conditioning_structure": structure,
                "event_bin": event_bin,
                "reference_bin": REFERENCE_BIN,
                "common_support_and_multipliers": True,
                "simultaneous_path_ci_lower": lower,
                "simultaneous_path_ci_upper": upper,
                "simultaneous_path_critical": simultaneous,
                **summary,
            })
    return rows


def endpoint_growth(young, older, months, high, grouping_name, metadata):
    start_month, end_month = "2022-11", "2026-06"
    start, end = months.index(start_month), months.index(end_month)
    low = ~high
    rows = []
    for age_name, values in (("young_22_25", young), ("older_26_65", older)):
        low_start, low_end = values[low, start].sum(), values[low, end].sum()
        high_start, high_end = values[high, start].sum(), values[high, end].sum()
        low_growth = float(low_end / low_start - 1)
        high_growth = float(high_end / high_start - 1)
        rows.append({
            **metadata["occupation_plus_calendar_month_FE"],
            "grouping_name": grouping_name,
            "age_group": age_name,
            "endpoint_start": start_month,
            "endpoint_end": end_month,
            "low_group_start_stock": float(low_start),
            "low_group_end_stock": float(low_end),
            "high_group_start_stock": float(high_start),
            "high_group_end_stock": float(high_end),
            "low_group_growth": low_growth,
            "high_group_growth": high_growth,
            "high_group_kept_pace_relative_to_low": float(
                (high_end / high_start) / (low_end / low_start) - 1
            ),
            "interpretation_limit": "descriptive_CPS_stock_growth_not_hiring_or_ADP_worker_firm_match_growth",
        })
    return rows


def findings_text(static_rows, paired_rows, group_summary, dynamic_paths, failures):
    lookup = {(row["grouping_name"], row["conditioning_structure"]): row
              for row in static_rows}
    lines = [
        "# R3 public BCC-grouping bridge findings",
        "",
        "Status: post-outcome exploratory; approximate CPS stock bridge, not an ADP replication.",
        "",
        "## Static corrected-calendar estimates",
        "",
        "Both constructions use the same 468 occupations and March-restored January 2017--July 2026 CPS stock calendar. The only grouping difference is the weight used to form GPT-4 beta quintile cutoffs.",
        "",
        "| grouping | no SOC2 conditioning | SOC2 x post | SOC2 x month |",
        "|---|---:|---:|---:|",
    ]
    for grouping in GROUPINGS:
        values = []
        for structure in STRUCTURES:
            row = lookup.get((grouping, structure))
            values.append("{:.4f} [{:.4f}, {:.4f}]".format(
                row["coefficient"], row["ci_lower"], row["ci_upper"]
            ) if row else "FAILED")
        lines.append("| `{}` | {} | {} | {} |".format(grouping, *values))
    lines.extend(["", "## Membership", ""])
    for row in group_summary:
        lines.append(
            "- `{}` assigns {} of {} occupations to Q4--Q5, representing {:.2f}% of corrected-calendar stock.".format(
                row["grouping_name"], row["high_occupation_count"],
                row["support_occupations"], 100 * row["high_corrected_calendar_stock_share"],
            )
        )
    grouping_pairs = [row for row in paired_rows if row["contrast_type"] == "grouping_rule"]
    lines.extend(["", "## Paired grouping-rule changes", ""])
    for row in grouping_pairs:
        lines.append(
            "- {}: equal-occupation minus historical employment-weighted = {:.4f} [{:.4f}, {:.4f}].".format(
                row["conditioning_structure"], row["coefficient_difference"],
                row["ci_lower"], row["ci_upper"],
            )
        )
    lines.extend([
        "",
        "These comparisons do not establish BCC membership concordance. The official dashboard documents equal occupation weights, but the complete occupation universe, cutoff/tie implementation, and membership file remain unavailable.",
        "",
        "## Dynamics and failures",
        "",
        "The quarterly companion produced {} path rows. {} model failures were retained in `MODEL_FAILURES.json`.".format(
            len(dynamic_paths), len(failures)
        ),
        "",
        "Intervals containing zero are described as nondetection, never as economic equivalence.",
        "",
    ])
    return "\n".join(lines)


def run(args):
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = COMP.CORE.load_data(args)
    prepared, historical_q, majors, _ = COMP.primary_setup(data, args)
    support = list(prepared["occupations"])
    if len(support) != 468:
        raise RuntimeError("historical common support changed from 468 occupations")
    if any(group == "MISSING" for group in majors):
        raise RuntimeError("SOC2 group missing on common support")

    cells, _, build_receipt = CELLS.build_exact_age_cells(args)
    months = [month for month in sorted(cells.month.unique()) if month != "2022-12"]
    if len(months) != 113 or months[0] != "2017-01" or months[-1] != "2026-07":
        raise RuntimeError("corrected static calendar is not January 2017--July 2026 with 113 months")
    if "2025-10" in months:
        raise RuntimeError("October 2025 must remain an actual collection gap")
    young, older = CELLS.panel_for_ages(cells, support, months, (22, 25), (26, 65))
    if np.any(young.sum(axis=1) <= 0) or np.any(older.sum(axis=1) <= 0):
        raise RuntimeError("common support contains an unidentified occupation fixed effect")

    beta_map = data["exposures"]["dv_rating_beta"]["A"]
    beta = np.array([beta_map[code] for code in support], float)
    historical_weights = np.asarray(prepared["weights"], float)
    weighted_q, weighted_cuts = weighted_quintiles_with_cuts(beta, historical_weights)
    if not np.array_equal(weighted_q, np.asarray(historical_q, int)):
        raise RuntimeError("historical YAX employment-weighted classifications did not reproduce")
    equal_q, equal_cuts = weighted_quintiles_with_cuts(beta, np.ones(len(beta)))

    webb_map = data["computers"]["webb_pct_software"]
    webb = np.array([webb_map[code] for code in support], float)
    webb_mean, webb_sd = FROZEN.weighted_scale(webb, historical_weights)
    webb_z = (webb - webb_mean) / webb_sd
    corrected_stock = (young + older).sum(axis=1)
    signs = np.random.default_rng(SEED).choice(
        np.array([-1.0, 1.0]), size=(DRAWS, len(support)),
    )

    definitions = {
        GROUPINGS[0]: {
            "quintiles": weighted_q,
            "cuts": weighted_cuts,
            "description": "historical YAX employment-weighted tie-preserving beta quintiles; Q4-Q5 versus Q1-Q3",
            "cut_rule": "historical_108_month_young_plus_older_CPS_stock_weighted_quintiles_including_postperiod",
        },
        GROUPINGS[1]: {
            "quintiles": equal_q,
            "cuts": equal_cuts,
            "description": "equal-occupation tie-preserving beta quintiles on fixed YAX common support; Q4-Q5 versus Q1-Q3",
            "cut_rule": "one_equal_cut_weight_per_YAX_support_occupation",
        },
    }

    membership_rows, group_rows = [], []
    static_rows, information_rows, failures = [], [], []
    static_models, metadata_by_group = {}, {}
    growth_rows = []
    for grouping_name, definition in definitions.items():
        high = definition["quintiles"] >= 4
        metadata = {
            structure: common_metadata(
                grouping_name, definition["description"], definition["cut_rule"],
                definition["cuts"], structure, months[0], months[-1],
                "Q4-Q5_vs_Q1-Q3_high_x_post_in_young_relative_CPS_stock",
            )
            for structure in STRUCTURES
        }
        metadata["support"] = support
        metadata["names"] = data["names"]
        metadata_by_group[grouping_name] = metadata
        models, rows, info, model_failures = fit_static(
            grouping_name, high, webb_z, young, older, months, majors, signs, metadata,
        )
        static_models[grouping_name] = models
        static_rows.extend(rows)
        information_rows.extend(info)
        failures.extend(model_failures)
        growth_rows.extend(endpoint_growth(
            young, older, months, high, grouping_name, metadata,
        ))
        group_rows.append({
            "analysis_status": LABEL,
            "bcc_version": BCC_VERSION,
            "grouping_name": grouping_name,
            "cut_rule": definition["cut_rule"],
            "tie_rule": "ties_preserved_lower_bin_at_cut",
            "cut_values_json": json.dumps(definition["cuts"].tolist()),
            "support_occupations": len(support),
            "support_hash_sha256": support_hash(support),
            "low_occupation_count": int((~high).sum()),
            "high_occupation_count": int(high.sum()),
            "high_historical_cut_weight_share": float(
                historical_weights[high].sum() / historical_weights.sum()
            ),
            "high_corrected_calendar_stock_share": float(
                corrected_stock[high].sum() / corrected_stock.sum()
            ),
            "membership_concordance_status": "UNVERIFIED_no_complete_public_BCC_membership_or_tie_algorithm",
        })

    for index, code in enumerate(support):
        membership_rows.append({
            "analysis_status": LABEL,
            "bcc_version": BCC_VERSION,
            "occupation_code": code,
            "occupation_name": data["names"].get(code, code),
            "SOC2": majors[index],
            "beta_raw": float(beta[index]),
            "historical_cut_weight": float(historical_weights[index]),
            "corrected_calendar_stock": float(corrected_stock[index]),
            "historical_YAX_quintile": int(weighted_q[index]),
            "historical_YAX_group": "Q4_Q5_high" if weighted_q[index] >= 4 else "Q1_Q3_low",
            "equal_occupation_quintile": int(equal_q[index]),
            "equal_occupation_group": "Q4_Q5_high" if equal_q[index] >= 4 else "Q1_Q3_low",
            "same_quintile": bool(weighted_q[index] == equal_q[index]),
            "same_binary_group": bool((weighted_q[index] >= 4) == (equal_q[index] >= 4)),
        })

    concordance = {
        "analysis_status": LABEL,
        "bcc_version": BCC_VERSION,
        "support_occupations": len(support),
        "same_quintile_occupations": int(np.sum(weighted_q == equal_q)),
        "same_quintile_share": float(np.mean(weighted_q == equal_q)),
        "same_binary_group_occupations": int(np.sum((weighted_q >= 4) == (equal_q >= 4))),
        "same_binary_group_share": float(np.mean((weighted_q >= 4) == (equal_q >= 4))),
        "switched_binary_group_occupations": int(np.sum((weighted_q >= 4) != (equal_q >= 4))),
        "switched_binary_group_corrected_stock_share": float(
            corrected_stock[(weighted_q >= 4) != (equal_q >= 4)].sum() /
            corrected_stock.sum()
        ),
        "external_BCC_membership_concordance": "UNVERIFIED",
        "reason": "complete published occupation membership and tie algorithm unavailable",
    }

    paired_rows = []
    # Pair cut-weight definitions within the same model and support.
    left_models = static_models[GROUPINGS[1]]
    right_models = static_models[GROUPINGS[0]]
    for structure in STRUCTURES:
        if structure not in left_models or structure not in right_models:
            continue
        left, right = left_models[structure], right_models[structure]
        paired, _ = paired_result(
            left["fit"].beta[0], left["influence"][:, 0],
            right["fit"].beta[0], right["influence"][:, 0], signs,
        )
        paired_rows.append({
            "analysis_status": LABEL,
            "bcc_version": BCC_VERSION,
            "contrast_type": "grouping_rule",
            "contrast": "equal_occupation_approximation_minus_historical_employment_weighted_approximation",
            "conditioning_structure": structure,
            "support_occupations": len(support),
            "support_hash_sha256": support_hash(support),
            "left_coefficient": float(left["fit"].beta[0]),
            "right_coefficient": float(right["fit"].beta[0]),
            **paired,
        })
    # Pair each SOC2-conditioned model with its own no-SOC2 baseline.
    for grouping_name in GROUPINGS:
        models = static_models[grouping_name]
        if "occupation_plus_calendar_month_FE" not in models:
            continue
        baseline = models["occupation_plus_calendar_month_FE"]
        for structure in ("SOC2_x_post", "SOC2_x_calendar_month"):
            if structure not in models:
                continue
            conditioned = models[structure]
            paired, _ = paired_result(
                conditioned["fit"].beta[0], conditioned["influence"][:, 0],
                baseline["fit"].beta[0], baseline["influence"][:, 0], signs,
            )
            paired_rows.append({
                "analysis_status": LABEL,
                "bcc_version": BCC_VERSION,
                "contrast_type": "conditioning_change",
                "contrast": "{}_minus_no_SOC2_conditioning".format(structure),
                "grouping_name": grouping_name,
                "conditioning_structure": structure,
                "support_occupations": len(support),
                "support_hash_sha256": support_hash(support),
                "left_coefficient": float(conditioned["fit"].beta[0]),
                "right_coefficient": float(baseline["fit"].beta[0]),
                **paired,
            })

    dynamic_paths, dynamic_joint, dynamic_covariance, dynamic_influence = [], [], [], []
    dynamic_models = {}
    for grouping_name, definition in definitions.items():
        high = definition["quintiles"] >= 4
        metadata = metadata_by_group[grouping_name]
        # Dynamic metadata uses the quarterly contrast but otherwise retains
        # all static bridge labels.
        dynamic_metadata = {}
        for structure in DYNAMIC_STRUCTURES:
            row = dict(metadata[structure])
            row["contrast"] = "quarter_specific_Q4-Q5_vs_Q1-Q3_in_young_relative_CPS_stock"
            row["conditioning_structure"] = structure
            dynamic_metadata[structure] = row
        dynamic_metadata["support"] = support
        dynamic_metadata["names"] = data["names"]
        models, paths, joint, covariance, influence, model_failures = fit_dynamics(
            grouping_name, high, webb_z, young, older, months, majors, signs,
            dynamic_metadata,
        )
        dynamic_models[grouping_name] = models
        dynamic_paths.extend(paths)
        dynamic_joint.extend(joint)
        dynamic_covariance.extend(covariance)
        dynamic_influence.extend(influence)
        failures.extend(model_failures)
    dynamic_paired = paired_dynamic_rows(
        dynamic_models.get(GROUPINGS[1], {}),
        dynamic_models.get(GROUPINGS[0], {}),
        signs,
    )

    write_csv(args.output_dir / "BRIDGE_MEMBERSHIP.csv", membership_rows)
    write_csv(args.output_dir / "BRIDGE_GROUP_SUMMARY.csv", group_rows)
    write_json(args.output_dir / "BRIDGE_MEMBERSHIP_CONCORDANCE.json", concordance)
    write_csv(args.output_dir / "STATIC_MODEL_RESULTS.csv", static_rows)
    write_csv(args.output_dir / "STATIC_PAIRED_DIFFERENCES.csv", paired_rows)
    write_csv(args.output_dir / "STATIC_INFORMATION_BY_OCCUPATION.csv", information_rows)
    write_csv(args.output_dir / "STATIC_GROWTH_ENDPOINTS.csv", growth_rows)
    if dynamic_paths:
        write_csv(args.output_dir / "DYNAMIC_PATHS.csv", dynamic_paths)
        write_csv(args.output_dir / "DYNAMIC_JOINT_TESTS.csv", dynamic_joint)
        write_csv(args.output_dir / "DYNAMIC_TARGET_COVARIANCE.csv", dynamic_covariance)
        write_csv(args.output_dir / "DYNAMIC_TARGET_INFLUENCE.csv", dynamic_influence)
    if dynamic_paired:
        write_csv(args.output_dir / "DYNAMIC_PAIRED_GROUPING_DIFFERENCES.csv", dynamic_paired)
    write_json(args.output_dir / "MODEL_FAILURES.json", failures)
    findings = findings_text(static_rows, paired_rows, group_rows, dynamic_paths, failures)
    (args.output_dir / "FINDINGS.md").write_text(findings, encoding="utf-8")

    output_hashes = {
        path.name: sha256(path) for path in sorted(args.output_dir.iterdir())
        if path.is_file() and path.name not in {"EXECUTION_RECEIPT.json", "SELF_CHECK.json"}
    }
    receipt = {
        "record": "YAX R3 public BCC-grouping CPS stock bridge",
        "analysis_status": LABEL,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
        ).strip(),
        "registry_scope": ["BCC-01", "BCC-02", "BCC-03"],
        "bcc_version": BCC_VERSION,
        "bridge_status": "approximate_public_grouping_bridge_not_replication",
        "unresolved": [
            "complete BCC occupation membership",
            "complete BCC cutoff and tie algorithm",
            "concordance between BCC proprietary SOC/title universe and YAX Census-2018 support",
            "BCC ADP outcomes, firm panel, firm-time controls, hires, and separations",
        ],
        "support_occupations": len(support),
        "support_hash_sha256": support_hash(support),
        "calendar": {
            "first_month": months[0], "last_month": months[-1],
            "months": len(months), "transition_month_excluded": "2022-12" not in months,
            "october_2025_present": "2025-10" in months,
        },
        "corrected_cell_build": build_receipt,
        "grouping_definitions": {
            key: {
                "cut_rule": value["cut_rule"],
                "cuts": value["cuts"].tolist(),
                "high_occupation_count": int(np.sum(value["quintiles"] >= 4)),
            }
            for key, value in definitions.items()
        },
        "membership_concordance": concordance,
        "static_models_completed": len(static_rows),
        "dynamic_models_completed": len({
            (row["grouping_name"], row["conditioning_structure"])
            for row in dynamic_paths
        }),
        "dynamic_path_rows": len(dynamic_paths),
        "failures": failures,
        "bootstrap": {
            "draws": DRAWS, "seed": SEED,
            "common_occupation_Rademacher_multipliers": True,
        },
        "implementation": {
            "script": str(pathlib.Path(__file__).resolve().relative_to(ROOT)),
            "script_sha256": sha256(pathlib.Path(__file__).resolve()),
            "analysis_spec": str((HERE / "ANALYSIS_SPEC.md").relative_to(ROOT)),
            "analysis_spec_sha256": sha256(HERE / "ANALYSIS_SPEC.md"),
            "source_audit": "yax/revision/substantive_r3_20260905/literature_evidence/BCC_VERSION_AUDIT.md",
            "source_audit_sha256": sha256(
                ROOT / "yax/revision/substantive_r3_20260905/literature_evidence/BCC_VERSION_AUDIT.md"
            ),
        },
        "input_hashes": {
            **data["authenticated"]["hashes"],
            "repair_microdata": sha256(args.repair_microdata),
        },
        "output_hashes": output_hashes,
    }
    write_json(args.output_dir / "EXECUTION_RECEIPT.json", receipt)
    print(json.dumps({
        "status": "PASS_R3_BCC_BRIDGE" if not failures else "PASS_WITH_RETAINED_FAILURES",
        "static_models": static_rows,
        "membership_concordance": concordance,
        "dynamic_path_rows": len(dynamic_paths),
        "failures": failures,
    }, indent=2, sort_keys=True))


def parser():
    value = COMP.parser()
    value.description = __doc__
    return value


if __name__ == "__main__":
    run(parser().parse_args())
