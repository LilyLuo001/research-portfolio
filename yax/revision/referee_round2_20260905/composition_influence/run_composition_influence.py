#!/usr/bin/env python3
"""Run YAX referee-round-2 composition and influence diagnostics.

POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1.

The program authenticates and reproduces the frozen primary model, then writes
only new revision-round artifacts.  It never mutates frozen inputs/results.
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
import pandas as pd


HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[4]
LABEL = "POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1"
PRIMARY_EXPECTED = -0.13107397642233506
CORRECTED_CALENDAR_EXPECTED = -0.1345539535732939
MEASURES = (
    "aioe_admin_equal", "aioe_ability_direct", "aioe_oews2018_source_weighted",
    "dv_rating_alpha", "dv_rating_beta", "dv_rating_gamma",
)
DRAWS = 9999
SEED = 2026090511


def import_path(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CORE = import_path(
    "yax_round2_composition_core",
    ROOT / "yax/revision/referee_20260905/run_referee_core.py",
)
FROZEN = CORE.FROZEN
CELLS = import_path(
    "yax_round2_composition_cells",
    ROOT / "yax/revision/referee_20260905/run_referee_cells.py",
)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def support_hash(codes) -> str:
    payload = "".join("{}\n".format(code) for code in sorted(codes))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_json(path: pathlib.Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def quantile(values, q):
    """NumPy-version-tolerant linear quantile."""
    try:
        return float(np.quantile(values, q, method="linear"))
    except TypeError:
        return float(np.quantile(values, q, interpolation="linear"))


def primary_setup(data, args):
    exposure = data["exposures"]["dv_rating_beta"]["A"]
    webb = data["computers"]["webb_pct_software"]
    prepared = FROZEN.prepare_model(
        data["panel"], data["occupations"], data["static_months"],
        exposure, webb, scale="q5_q1",
    )
    support = prepared["occupations"]
    values = np.array([exposure[code] for code in support], float)
    quintiles = FROZEN.weighted_quintiles(values, prepared["weights"])
    _, _, major_map = FROZEN.comp_maps(args.computerization)
    majors = np.array([major_map.get(code, "MISSING") for code in support], object)
    return prepared, quintiles, majors, major_map


def fit_absorbed(young, older, regressors, second_fe):
    """Fit grouped logit with occupation and arbitrary second fixed effect."""
    n_occ, n_month = young.shape
    if regressors.shape[0] != n_occ * n_month:
        raise ValueError("regressor rows do not match occupation-month panel")
    total_full = (young + older).reshape(-1)
    young_full = young.reshape(-1)
    occupation_full = np.repeat(np.arange(n_occ), n_month)
    second_full = np.asarray(second_fe).reshape(-1)
    keep = total_full > 0
    y, total, x = young_full[keep], total_full[keep], regressors[keep]
    _, occupation = np.unique(occupation_full[keep], return_inverse=True)
    _, second = np.unique(second_full[keep], return_inverse=True)
    occupation_count = int(occupation.max()) + 1
    second_count = int(second.max()) + 1
    fit = FROZEN.ENGINE.fit_grouped_logit_fe(
        y, total, occupation, second, x, max_iterations=5000,
    )
    if not fit.converged:
        raise RuntimeError("grouped-binomial model did not converge")
    probability = fit.fitted_probability
    residual = y - total * probability
    weight = np.maximum(total * probability * (1.0 - probability), 1e-12)
    rx = FROZEN.ENGINE._weighted_absorb(
        x, weight, occupation, second, occupation_count, second_count,
    )
    information = rx.T @ (weight[:, None] * rx)
    bread = np.linalg.inv(information)
    scores = np.zeros((occupation_count, x.shape[1]))
    np.add.at(scores, occupation, rx * residual[:, None])
    influence = scores @ bread.T
    influence *= math.sqrt(occupation_count / (occupation_count - 1))
    return fit, influence, {
        "y": y, "total": total, "x": x, "occupation": occupation,
        "second": second, "weight": weight, "rx": rx,
        "information": information, "scores": scores,
        "occupation_count": occupation_count, "second_fe_count": second_count,
        "positive_total_rows": int(keep.sum()), "zero_total_rows": int((~keep).sum()),
    }


def scalar_summary(fit, influence, target, signs):
    estimate = float(fit.beta[target])
    analytic_se = float(fit.standard_error[target])
    shifts = signs @ influence[:, target]
    bootstrap_se = float(np.std(shifts, ddof=1))
    critical = quantile(np.abs(shifts / analytic_se), .95)
    statistic = abs(estimate / analytic_se)
    pvalue = float((1 + np.sum(np.abs(shifts / analytic_se) >= statistic)) /
                   (len(shifts) + 1))
    return {
        "coefficient": estimate,
        "analytic_cluster_se": analytic_se,
        "bootstrap_se": bootstrap_se,
        "ci_lower": estimate - critical * analytic_se,
        "ci_upper": estimate + critical * analytic_se,
        "bootstrap_p_value": pvalue,
        "bootstrap_critical": critical,
        "bootstrap_draws": len(shifts),
    }, shifts


def conditional_information(details, target):
    rx = details["rx"]
    weight = details["weight"]
    other = [index for index in range(rx.shape[1]) if index != target]
    residual = rx[:, target].copy()
    if other:
        z = rx[:, other]
        cross = z.T @ (weight * residual)
        try:
            projection = np.linalg.solve(z.T @ (weight[:, None] * z), cross)
        except np.linalg.LinAlgError:
            projection = np.linalg.lstsq(z.T @ (weight[:, None] * z), cross, rcond=None)[0]
        residual -= z @ projection
    contribution = np.bincount(
        details["occupation"], weights=weight * np.square(residual),
        minlength=details["occupation_count"],
    )
    total = float(contribution.sum())
    effective = float(total * total / np.square(contribution).sum()) if total > 0 else 0.0
    top = np.sort(contribution)[::-1]
    eigen = np.linalg.eigvalsh(details["information"])
    positive = eigen[eigen > max(float(eigen.max()) * 1e-12, 1e-12)]
    condition = float(positive.max() / positive.min()) if len(positive) else float("inf")
    return {
        "conditional_target_information": total,
        "conditional_target_residual_weighted_sd": float(
            math.sqrt(total / weight.sum()) if total > 0 else 0.0
        ),
        "effective_occupation_information_count": effective,
        "top_five_information_share": float(top[:5].sum() / total) if total > 0 else np.nan,
        "information_matrix_rank": int(np.linalg.matrix_rank(details["information"])),
        "information_matrix_columns": int(details["information"].shape[0]),
        "information_matrix_condition_number_positive_spectrum": condition,
        "occupation_information": contribution,
    }


def composition_models(data, args, prepared, quintiles, majors, signs,
                       calendar, months, young, older, baseline_x):
    n_occ, n_month = young.shape
    month_fe = np.tile(np.arange(n_month), n_occ)
    group_levels = sorted(set(majors.tolist()))
    calendar_weights = (young + older).sum(axis=1)
    group_weights = {
        group: float(calendar_weights[majors == group].sum()) for group in group_levels
    }
    reference = max(group_levels, key=lambda value: (group_weights[value], value))
    post = np.array([month >= "2023-01" for month in months])
    group_post_columns = [
        (((majors == group)[:, None]) & post[None, :]).reshape(-1).astype(float)
        for group in group_levels if group != reference
    ]
    model_specs = [
        ("frozen_baseline", baseline_x, month_fe,
         "occupation and calendar-month fixed effects"),
        ("SOC2_x_post", np.column_stack([baseline_x, *group_post_columns]), month_fe,
         "occupation and calendar-month fixed effects plus SOC2-by-post slopes"),
    ]
    group_index = {group: index for index, group in enumerate(group_levels)}
    group_month_fe = np.concatenate([
        group_index[majors[index]] * n_month + np.arange(n_month)
        for index in range(n_occ)
    ])
    model_specs.append((
        "SOC2_x_calendar_month", baseline_x, group_month_fe,
        "occupation and absorbed SOC2-by-calendar-month fixed effects",
    ))
    rows, info_rows, failures, fitted = [], [], [], {}
    for model_name, regressors, second_fe, description in model_specs:
        try:
            fit, influence, details = fit_absorbed(young, older, regressors, second_fe)
            target = prepared["target"]
            summary, shifts = scalar_summary(fit, influence, target, signs)
            info = conditional_information(details, target)
            rows.append({
                "analysis_status": LABEL, "model": model_name,
                "calendar": calendar,
                "interval_role": "round2_9999_common_draw_interval_not_frozen_canonical_interval",
                "fixed_effects": description, "support_occupations": n_occ,
                "months": n_month, "SOC2_groups": len(group_levels),
                "SOC2_post_reference_group": reference if model_name == "SOC2_x_post" else "",
                "absorbed_second_FE_groups": details["second_fe_count"],
                "slope_parameters": regressors.shape[1],
                **summary,
                **{key: value for key, value in info.items() if key != "occupation_information"},
            })
            for index, code in enumerate(prepared["occupations"]):
                info_rows.append({
                    "analysis_status": LABEL, "model": model_name,
                    "calendar": calendar,
                    "occupation_code": code,
                    "occupation_name": data["names"].get(code, ""),
                    "SOC2": majors[index], "quintile": int(quintiles[index]),
                    "employment_weight": float((young + older).sum(axis=1)[index]),
                    "conditional_target_information": float(info["occupation_information"][index]),
                    "conditional_target_information_share": float(
                        info["occupation_information"][index] /
                        info["conditional_target_information"]
                    ) if info["conditional_target_information"] > 0 else np.nan,
                })
            fitted[model_name] = (fit, influence, details, shifts)
        except Exception as error:
            failures.append({
                "analysis_status": LABEL, "model": model_name,
                "error_type": type(error).__name__, "message": str(error),
            })
    if "frozen_baseline" not in fitted:
        raise RuntimeError("baseline composition model failed")
    reproduced = float(fitted["frozen_baseline"][0].beta[prepared["target"]])
    expected = (PRIMARY_EXPECTED if calendar == "frozen_108_month"
                else CORRECTED_CALENDAR_EXPECTED)
    if not np.isclose(reproduced, expected, atol=1e-10, rtol=0):
        raise RuntimeError("{} baseline failed: {} != {}".format(calendar, reproduced, expected))
    support_rows = []
    for group in group_levels:
        mask = majors == group
        row = {
            "analysis_status": LABEL, "calendar": calendar, "SOC2": group,
            "occupations": int(mask.sum()),
            "employment_weight": float((young + older).sum(axis=1)[mask].sum()),
            "employment_share": float((young + older).sum(axis=1)[mask].sum() /
                                      (young + older).sum()),
            "distinct_quintiles": int(len(np.unique(quintiles[mask]))),
            "contains_Q1": bool(np.any(quintiles[mask] == 1)),
            "contains_Q5": bool(np.any(quintiles[mask] == 5)),
            "contains_Q1_and_Q5": bool(np.any(quintiles[mask] == 1) and np.any(quintiles[mask] == 5)),
        }
        for q in range(1, 6):
            row["Q{}_occupations".format(q)] = int(np.sum(mask & (quintiles == q)))
            row["Q{}_employment_share_within_SOC2".format(q)] = float(
                (young + older).sum(axis=1)[mask & (quintiles == q)].sum() /
                (young + older).sum(axis=1)[mask].sum()
            )
        support_rows.append(row)
    return rows, info_rows, support_rows, failures, fitted


def paired_composition_differences(calendar, fitted, target):
    baseline_fit, _, _, baseline_shifts = fitted["frozen_baseline"]
    baseline = float(baseline_fit.beta[target])
    rows = []
    for model in ("SOC2_x_post", "SOC2_x_calendar_month"):
        if model not in fitted:
            continue
        fit, _, _, shifts = fitted[model]
        estimate = float(fit.beta[target])
        delta = estimate - baseline
        centered = shifts - baseline_shifts
        se = float(np.std(centered, ddof=1))
        critical = quantile(np.abs(centered / se), .95)
        rows.append({
            "analysis_status": LABEL, "calendar": calendar,
            "contrast": "{}_minus_calendar_baseline".format(model),
            "baseline_coefficient": baseline, "composition_coefficient": estimate,
            "coefficient_difference": delta, "paired_bootstrap_se": se,
            "ci_lower": delta - critical * se,
            "ci_upper": delta + critical * se,
            "paired_bootstrap_p_value": float(
                (1 + np.sum(np.abs(centered / se) >= abs(delta / se))) /
                (len(centered) + 1)
            ),
            "bootstrap_critical": critical, "bootstrap_draws": len(centered),
            "common_occupation_multipliers": True,
        })
    return rows


def profile_tests(prepared, baseline_fit, baseline_influence, signs):
    beta = baseline_fit.beta
    covariance = baseline_influence.T @ baseline_influence
    r_equal = np.zeros((3, len(beta)))
    r_equal[0, 0:2] = [1.0, -1.0]
    r_equal[1, 1:3] = [1.0, -1.0]
    r_equal[2, 2:4] = [1.0, -1.0]
    difference = r_equal @ beta
    rv = r_equal @ covariance @ r_equal.T
    inverse = np.linalg.pinv(rv)
    wald = float(difference @ inverse @ difference)
    shifts = signs @ baseline_influence
    r_shifts = shifts @ r_equal.T
    wild_wald = np.einsum("ij,jk,ik->i", r_shifts, inverse, r_shifts)
    equality = {
        "analysis_status": LABEL,
        "null": "b2=b3=b4=b5",
        "restrictions": 3,
        "wald_statistic": wald,
        "wild_score_p_value": float((1 + np.sum(wild_wald >= wald)) / (DRAWS + 1)),
        "bootstrap_draws": DRAWS,
        "coefficient_profile_Q1_to_Q5": [0.0, *[float(x) for x in beta[:4]]],
    }

    # Adjacent difference is next quintile minus previous quintile.  A monotone
    # non-increasing profile requires every difference to be <= 0.
    r_mono = np.zeros((4, len(beta)))
    r_mono[0, 0] = 1.0
    r_mono[1, 0:2] = [-1.0, 1.0]
    r_mono[2, 1:3] = [-1.0, 1.0]
    r_mono[3, 2:4] = [-1.0, 1.0]
    adjacent = r_mono @ beta
    adjacent_shifts = shifts @ r_mono.T
    se = np.sqrt(np.maximum(np.diag(r_mono @ covariance @ r_mono.T), 1e-20))
    t_observed = adjacent / se
    t_star = adjacent_shifts / se[None, :]
    max_observed = float(np.max(t_observed))
    max_star = np.max(t_star, axis=1)
    critical = quantile(max_star, .95)
    pvalue = float((1 + np.sum(max_star >= max_observed)) / (DRAWS + 1))
    upper = adjacent + critical * se
    lower = adjacent - critical * se
    if pvalue < .05:
        verdict = "REJECT_MONOTONE_NONINCREASING_AT_5_PERCENT"
    elif np.all(upper <= 0):
        verdict = "SIMULTANEOUS_UPPER_BOUNDS_SUPPORT_MONOTONE_NONINCREASING"
    else:
        verdict = "UNRESOLVED_NOT_REJECTED_AND_NOT_ESTABLISHED"
    rows = []
    for index, label in enumerate(("Q2-Q1", "Q3-Q2", "Q4-Q3", "Q5-Q4")):
        rows.append({
            "analysis_status": LABEL, "adjacent_difference": label,
            "estimate_next_minus_previous": float(adjacent[index]),
            "cluster_se": float(se[index]), "t_statistic": float(t_observed[index]),
            "simultaneous_one_sided_lower": float(lower[index]),
            "simultaneous_one_sided_upper": float(upper[index]),
            "required_for_monotone_nonincreasing": "<=0",
        })
    monotonicity = {
        "analysis_status": LABEL,
        "null": "all adjacent next-minus-previous differences are <= 0",
        "least_favorable_boundary": "all four adjacent differences equal zero",
        "max_t_statistic": max_observed,
        "one_sided_max_t_critical_95": critical,
        "one_sided_max_t_p_value": pvalue,
        "verdict": verdict,
        "bootstrap_draws": DRAWS,
        "adjacent": rows,
    }
    return equality, monotonicity, rows


def stable_tail_model(data, prepared, signs):
    webb = data["computers"]["webb_pct_software"]
    supports = [
        set(code for code in data["occupations"]
            if np.isfinite(data["exposures"][measure]["A"].get(code, np.nan))
            and np.isfinite(webb.get(code, np.nan)))
        for measure in MEASURES
    ]
    common = sorted(set.intersection(*supports))
    young, older = FROZEN.panel_arrays(data["panel"], common, data["static_months"])
    weights = (young + older).sum(axis=1)
    memberships = []
    for measure in MEASURES:
        values = np.array([data["exposures"][measure]["A"][code] for code in common], float)
        memberships.append(FROZEN.weighted_quintiles(values, weights))
    matrix = np.column_stack(memberships)
    stable_q1 = np.all(matrix == 1, axis=1)
    stable_q5 = np.all(matrix == 5, axis=1)
    keep = stable_q1 | stable_q5
    selected = [code for code, flag in zip(common, keep) if flag]
    y, o = young[keep], older[keep]
    high = stable_q5[keep]
    post = np.array([month >= "2023-01" for month in data["static_months"]])
    webb_values = np.array([webb[code] for code in selected], float)
    webb_mean, webb_sd = FROZEN.weighted_scale(webb_values, (y + o).sum(axis=1))
    webb_z = (webb_values - webb_mean) / webb_sd
    x = np.column_stack([
        (high[:, None] & post[None, :]).reshape(-1).astype(float),
        (webb_z[:, None] * post[None, :]).reshape(-1),
    ])
    month_fe = np.tile(np.arange(len(data["static_months"])), len(selected))
    fit, influence, details = fit_absorbed(y, o, x, month_fe)
    local_signs = signs[:, [prepared["occupations"].index(code) for code in selected]]
    summary, _ = scalar_summary(fit, influence, 0, local_signs)
    info = conditional_information(details, 0)
    membership_rows = []
    for index, code in enumerate(common):
        if not keep[index]:
            continue
        membership_rows.append({
            "analysis_status": LABEL, "occupation_code": code,
            "occupation_name": data["names"].get(code, ""),
            "stable_class": "always_Q5" if stable_q5[index] else "always_Q1",
            "employment_weight": float(weights[index]),
            **{"q_{}".format(measure): int(matrix[index, j])
               for j, measure in enumerate(MEASURES)},
        })
    result = {
        "analysis_status": LABEL,
        "model": "always_Q5_vs_always_Q1_with_Webb_post",
        "common_support_occupations": len(common),
        "selected_occupations": len(selected),
        "always_Q1_occupations": int(stable_q1.sum()),
        "always_Q5_occupations": int(stable_q5.sum()),
        "always_Q1_common_support_employment_share": float(weights[stable_q1].sum() / weights.sum()),
        "always_Q5_common_support_employment_share": float(weights[stable_q5].sum() / weights.sum()),
        "selected_common_support_employment_share": float(weights[keep].sum() / weights.sum()),
        **summary,
        **{key: value for key, value in info.items() if key != "occupation_information"},
        "interpretation_limit": "estimate applies only to occupations stably assigned to an extreme across all six implementations",
    }
    return result, membership_rows


def refit_subset(prepared, keep, signs, stock_multiplier=None):
    n_occ, n_month = prepared["young"].shape
    cube = prepared["regressors"].reshape(n_occ, n_month, -1)
    y, o = prepared["young"][keep].copy(), prepared["older"][keep].copy()
    if stock_multiplier is not None:
        multiplier = np.asarray(stock_multiplier)[keep]
        y *= multiplier[:, None]
        o *= multiplier[:, None]
    x = cube[keep].reshape(int(keep.sum()) * n_month, cube.shape[2])
    month_fe = np.tile(np.arange(n_month), int(keep.sum()))
    fit, influence, details = fit_absorbed(y, o, x, month_fe)
    summary, _ = scalar_summary(fit, influence, prepared["target"], signs[:, keep])
    info = conditional_information(details, prepared["target"])
    return summary, info


def influence_models(data, args, prepared, quintiles, majors, signs):
    loco = pd.read_csv(args.loco, dtype={"deleted_census2018": str})
    loco["deleted_census2018"] = loco.deleted_census2018.str.zfill(4)
    if len(loco) != len(prepared["occupations"]) or loco.deleted_census2018.nunique() != len(loco):
        raise RuntimeError("frozen LOCO file does not match 468-occupation primary support")
    if not np.allclose(loco.frozen_full_estimate, PRIMARY_EXPECTED, atol=1e-12, rtol=0):
        raise RuntimeError("frozen LOCO baseline changed")
    order = {code: index for index, code in enumerate(prepared["occupations"])}
    loco = loco.assign(_index=loco.deleted_census2018.map(order))
    if loco._index.isna().any():
        raise RuntimeError("LOCO contains code outside primary support")
    loco = loco.sort_values(["absolute_movement", "deleted_census2018"], ascending=[False, True])
    rows, member_rows = [], []
    for k in (5, 10, 20):
        chosen = loco.head(k)
        deleted = set(chosen.deleted_census2018)
        keep = np.array([code not in deleted for code in prepared["occupations"]])
        summary, info = refit_subset(prepared, keep, signs)
        rows.append({
            "analysis_status": LABEL, "specification": "joint_leave_top_{}_frozen_LOCO".format(k),
            "data_adaptive": True, "deleted_occupations": k,
            "deleted_codes": "|".join(chosen.deleted_census2018),
            "deleted_names": "|".join(chosen.deleted_occupation.fillna("")),
            "deleted_stock_share": float(chosen.deleted_full_sample_stock_weight.sum() /
                                         loco.deleted_full_sample_stock_weight.sum()),
            **summary,
            **{key: value for key, value in info.items() if key != "occupation_information"},
        })
        for rank, (_, item) in enumerate(chosen.iterrows(), start=1):
            member_rows.append({
                "analysis_status": LABEL, "specification": "joint_leave_top_{}".format(k),
                "rank_within_deletion": rank,
                "occupation_code": item.deleted_census2018,
                "occupation_name": item.deleted_occupation,
                "frozen_LOCO_signed_movement": float(item.signed_movement),
                "frozen_LOCO_absolute_movement": float(item.absolute_movement),
            })

    signed = loco.sort_values(["signed_movement", "deleted_census2018"])
    tail_count = int(math.ceil(.025 * len(signed)))
    trim = pd.concat([signed.head(tail_count), signed.tail(tail_count)]).drop_duplicates(
        "deleted_census2018"
    )
    deleted = set(trim.deleted_census2018)
    keep = np.array([code not in deleted for code in prepared["occupations"]])
    summary, info = refit_subset(prepared, keep, signs)
    rows.append({
        "analysis_status": LABEL,
        "specification": "trim_2.5pct_each_signed_frozen_LOCO_tail",
        "data_adaptive": True, "deleted_occupations": int((~keep).sum()),
        "deleted_codes": "|".join(trim.deleted_census2018),
        "deleted_names": "|".join(trim.deleted_occupation.fillna("")),
        "deleted_stock_share": float(trim.deleted_full_sample_stock_weight.sum() /
                                     loco.deleted_full_sample_stock_weight.sum()),
        **summary,
        **{key: value for key, value in info.items() if key != "occupation_information"},
    })

    movement = np.zeros(len(prepared["occupations"]))
    for _, item in loco.iterrows():
        movement[int(item._index)] = float(item.signed_movement)
    median = float(np.median(movement))
    distance = np.abs(movement - median)
    cutoff = quantile(distance, .95)
    multiplier = np.ones_like(distance)
    positive = distance > 0
    multiplier[positive] = np.minimum(1.0, cutoff / distance[positive])
    keep_all = np.ones(len(multiplier), dtype=bool)
    summary, info = refit_subset(prepared, keep_all, signs, multiplier)
    rows.append({
        "analysis_status": LABEL,
        "specification": "Huber_downweight_above_p95_absolute_LOCO_deviation",
        "data_adaptive": True, "deleted_occupations": 0,
        "downweighted_occupations": int(np.sum(multiplier < 1)),
        "LOCO_signed_median": median, "LOCO_absolute_deviation_p95_cutoff": cutoff,
        "minimum_occupation_weight_multiplier": float(multiplier.min()),
        "effective_occupation_count_from_multipliers": float(
            multiplier.sum() ** 2 / np.square(multiplier).sum()
        ),
        **summary,
        **{key: value for key, value in info.items() if key != "occupation_information"},
    })
    for index, code in enumerate(prepared["occupations"]):
        if multiplier[index] < 1:
            item = loco.loc[loco.deleted_census2018.eq(code)].iloc[0]
            member_rows.append({
                "analysis_status": LABEL, "specification": "Huber_downweight_p95",
                "rank_within_deletion": "", "occupation_code": code,
                "occupation_name": data["names"].get(code, ""),
                "frozen_LOCO_signed_movement": float(item.signed_movement),
                "frozen_LOCO_absolute_movement": float(item.absolute_movement),
                "stock_multiplier": float(multiplier[index]),
            })
    return rows, member_rows


def occupation_exclusions(data, prepared, quintiles, majors, signs):
    definitions = [
        ("exclude_all_SOC35_food_preparation_and_serving", (majors == "35")),
        ("exclude_Q1_SOC35_food_preparation_and_serving", (majors == "35") & (quintiles == 1)),
        ("exclude_all_SOC35_37_39_in_person_services", np.isin(majors, ["35", "37", "39"])),
        ("exclude_Q1_SOC35_37_39_in_person_services", np.isin(majors, ["35", "37", "39"]) & (quintiles == 1)),
    ]
    rows, members = [], []
    for label, exclusion in definitions:
        keep = ~exclusion
        summary, info = refit_subset(prepared, keep, signs)
        codes = [code for code, flag in zip(prepared["occupations"], exclusion) if flag]
        rows.append({
            "analysis_status": LABEL, "specification": label,
            "excluded_occupations": len(codes),
            "excluded_codes": "|".join(codes),
            "excluded_stock_share": float(prepared["weights"][exclusion].sum() /
                                          prepared["weights"].sum()),
            "quintiles_recomputed": False,
            "classification_basis": "Census-2018 occupation SOC major groups",
            **summary,
            **{key: value for key, value in info.items() if key != "occupation_information"},
        })
        for index, code in enumerate(prepared["occupations"]):
            if exclusion[index]:
                members.append({
                    "analysis_status": LABEL, "specification": label,
                    "occupation_code": code,
                    "occupation_name": data["names"].get(code, ""),
                    "SOC2": majors[index], "frozen_beta_quintile": int(quintiles[index]),
                    "employment_weight": float(prepared["weights"][index]),
                })
    return rows, members


def run(args):
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = CORE.load_data(args)
    prepared, quintiles, majors, _ = primary_setup(data, args)
    if len(prepared["occupations"]) != 468:
        raise RuntimeError("primary support changed from 468 occupations")
    signs = np.random.default_rng(SEED).choice(
        np.array([-1.0, 1.0]), size=(DRAWS, len(prepared["occupations"])),
    )

    comp_rows, info_rows, support_rows, failures, fitted = composition_models(
        data, args, prepared, quintiles, majors, signs,
        "frozen_108_month", data["static_months"], prepared["young"],
        prepared["older"], prepared["regressors"],
    )
    paired_composition_rows = paired_composition_differences(
        "frozen_108_month", fitted, prepared["target"]
    )
    equality, monotonicity, adjacent_rows = profile_tests(
        prepared, fitted["frozen_baseline"][0], fitted["frozen_baseline"][1], signs,
    )
    stable, stable_members = stable_tail_model(data, prepared, signs)
    influence_rows, influence_members = influence_models(
        data, args, prepared, quintiles, majors, signs,
    )
    exclusion_rows, exclusion_members = occupation_exclusions(
        data, prepared, quintiles, majors, signs,
    )

    corrected_build = None
    if args.repair_microdata is not None and args.repair_microdata.exists():
        corrected_cells, _, corrected_build = CELLS.build_exact_age_cells(args)
        corrected_months = [
            month for month in sorted(corrected_cells.month.unique())
            if month != "2022-12"
        ]
        if len(corrected_months) != 113:
            raise RuntimeError("corrected calendar did not contain 113 static months")
        corrected_young, corrected_older = CELLS.panel_for_ages(
            corrected_cells, prepared["occupations"], corrected_months,
            (22, 25), (26, 65),
        )
        webb = data["computers"]["webb_pct_software"]
        webb_values = np.array([webb[code] for code in prepared["occupations"]], float)
        webb_mean, webb_sd = FROZEN.weighted_scale(webb_values, prepared["weights"])
        webb_z = (webb_values - webb_mean) / webb_sd
        post = np.array([month >= "2023-01" for month in corrected_months])
        corrected_x = np.column_stack([
            *[(((quintiles == q)[:, None]) & post[None, :]).reshape(-1).astype(float)
              for q in (2, 3, 4, 5)],
            (webb_z[:, None] * post[None, :]).reshape(-1),
        ])
        c_rows, c_info, c_support, c_failures, c_fitted = composition_models(
            data, args, prepared, quintiles, majors, signs,
            "March_repaired_113_month", corrected_months,
            corrected_young, corrected_older, corrected_x,
        )
        comp_rows.extend(c_rows)
        info_rows.extend(c_info)
        support_rows.extend(c_support)
        failures.extend(c_failures)
        paired_composition_rows.extend(paired_composition_differences(
            "March_repaired_113_month", c_fitted, prepared["target"]
        ))
    else:
        failures.append({
            "analysis_status": LABEL, "calendar": "March_repaired_113_month",
            "model": "all", "error_type": "MissingRepairMicrodata",
            "message": "No repair extract was supplied; corrected-calendar composition models not approximated.",
        })

    write_csv(args.output_dir / "COMPOSITION_MODELS.csv", comp_rows)
    write_csv(args.output_dir / "COMPOSITION_PAIRED_DIFFERENCES.csv", paired_composition_rows)
    write_csv(args.output_dir / "COMPOSITION_OCCUPATION_INFORMATION.csv", info_rows)
    write_csv(args.output_dir / "SOC2_QUINTILE_SUPPORT.csv", support_rows)
    write_json(args.output_dir / "COMPOSITION_MODEL_FAILURES.json", failures)
    write_json(args.output_dir / "QUINTILE_PROFILE_TESTS.json", {
        "equality": equality, "monotonicity": monotonicity,
    })
    write_csv(args.output_dir / "MONOTONICITY_ADJACENT_DIFFERENCES.csv", adjacent_rows)
    write_json(args.output_dir / "STABLE_TAIL_RESULT.json", stable)
    write_csv(args.output_dir / "STABLE_TAIL_MEMBERS.csv", stable_members)
    write_csv(args.output_dir / "JOINT_DELETION_AND_ROBUST_INFLUENCE.csv", influence_rows)
    write_csv(args.output_dir / "INFLUENCE_ADJUSTMENT_MEMBERS.csv", influence_members)
    write_csv(args.output_dir / "OCCUPATION_SERVICE_EXCLUSIONS.csv", exclusion_rows)
    write_csv(args.output_dir / "OCCUPATION_SERVICE_EXCLUSION_MEMBERS.csv", exclusion_members)

    output_hashes = {
        path.name: sha256(path) for path in sorted(args.output_dir.iterdir())
        if path.is_file() and path.name != "EXECUTION_RECEIPT.json"
    }
    receipt = {
        "record": "YAX referee round 2 composition and influence diagnostics",
        "analysis_status": LABEL,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "protected_refs": {
            "v1.1-design-freeze": subprocess.check_output(
                ["git", "rev-parse", "v1.1-design-freeze^{}"], cwd=ROOT, text=True
            ).strip(),
            "v1.1-confirmatory-results": subprocess.check_output(
                ["git", "rev-parse", "v1.1-confirmatory-results^{}"], cwd=ROOT, text=True
            ).strip(),
        },
        "frozen_primary_reproduced": data["baseline_reproduced"],
        "input_hashes": data["authenticated"]["hashes"],
        "repair_microdata_sha256": (
            sha256(args.repair_microdata)
            if args.repair_microdata is not None and args.repair_microdata.exists() else None
        ),
        "corrected_calendar_build": corrected_build,
        "frozen_LOCO_sha256": sha256(args.loco),
        "implementation_source": {
            "script": str(pathlib.Path(__file__).resolve().relative_to(ROOT)),
            "script_sha256": sha256(pathlib.Path(__file__).resolve()),
            "analysis_spec": str((HERE / "ANALYSIS_SPEC.md").relative_to(ROOT)),
            "analysis_spec_sha256": sha256(HERE / "ANALYSIS_SPEC.md"),
        },
        "bootstrap": {"draws": DRAWS, "seed": SEED,
                      "common_occupation_Rademacher_multipliers": True},
        "composition_model_failures": failures,
        "output_hashes": output_hashes,
    }
    write_json(args.output_dir / "EXECUTION_RECEIPT.json", receipt)
    print(json.dumps({
        "status": "PASS_COMPOSITION_INFLUENCE",
        "baseline": data["baseline_reproduced"],
        "composition": comp_rows,
        "profile_equality": equality,
        "profile_monotonicity": monotonicity,
        "stable_tail": stable,
        "influence": influence_rows,
        "exclusions": exclusion_rows,
        "failures": failures,
    }, indent=2, sort_keys=True))


def parser():
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--microdata", type=pathlib.Path, required=True)
    value.add_argument("--preperiod-cells", type=pathlib.Path, required=True)
    value.add_argument("--repair-microdata", type=pathlib.Path)
    value.add_argument("--lookup", type=pathlib.Path,
                       default=ROOT / "yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv")
    value.add_argument("--computerization", type=pathlib.Path,
                       default=ROOT / "yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv")
    value.add_argument("--rule-b-values", type=pathlib.Path,
                       default=ROOT / "yax/measurement/RULE_B_VALUES_CENSUS2018.csv")
    value.add_argument("--bridge", type=pathlib.Path,
                       default=ROOT / "yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv")
    value.add_argument("--first-access-receipt", type=pathlib.Path,
                       default=ROOT / "yax/analysis/FIRST_OUTCOME_ACCESS_RECEIPT.json")
    value.add_argument("--characteristics", type=pathlib.Path,
                       default=ROOT / "yax/measurement/test_a/TEST_A_OCCUPATION_CHARACTERISTICS.csv")
    value.add_argument("--loco", type=pathlib.Path,
                       default=ROOT / "yax/analysis/postoutcome_v51_final_audit/YAX_V51_LOCO_PRIMARY.csv")
    value.add_argument("--output-dir", type=pathlib.Path, required=True)
    return value


if __name__ == "__main__":
    run(parser().parse_args())
