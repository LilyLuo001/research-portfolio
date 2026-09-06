#!/usr/bin/env python3
"""Run the round-2 YAX precision, cell-support, and time-dependence audits.

POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1.

The frozen estimator and inputs are imported read-only.  This program writes
only beneath ``referee_round2_20260905/precision_rotation``.  Its canonical
interval convention is one fixed 9,999-draw occupation-Rademacher array for
the primary estimate.  Pairwise architecture intervals use a separate common
draw array on each pair's common support and are never substituted for the
canonical primary interval.
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
SEED = 2026090511
DRAWS = 9999
Z_975 = 1.959963984540054
Z_80 = 0.8416212335729143
NORMAL_MDE_MULTIPLIER = Z_975 + Z_80
PRIMARY_EXPECTED = -0.13107397642233506
MEASURES = (
    "aioe_admin_equal", "aioe_ability_direct", "aioe_oews2018_source_weighted",
    "dv_rating_alpha", "dv_rating_beta", "dv_rating_gamma",
)


def import_path(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


FROZEN = import_path("yax_round2_frozen", ROOT / "yax/analysis/run_frozen_v11.py")
CORE = import_path(
    "yax_round2_core", ROOT / "yax/revision/referee_20260905/run_referee_core.py"
)
CELLS = import_path(
    "yax_round2_cells", ROOT / "yax/revision/referee_20260905/run_referee_cells.py"
)
POWER = import_path("yax_round2_power", ROOT / "yax/power/joint_computerization_power.py")


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def support_hash(codes: list[str]) -> str:
    return hashlib.sha256("".join(f"{x}\n" for x in sorted(codes)).encode()).hexdigest()


def write_csv(path: pathlib.Path, rows: list[dict]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty file: {path}")
    fields: list[str] = []
    for row in rows:
        fields.extend(key for key in row if key not in fields)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: pathlib.Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def quantile_higher(values: np.ndarray, q: float) -> float:
    try:
        return float(np.quantile(values, q, method="higher"))
    except TypeError:  # NumPy on the SCC compatibility environment.
        return float(np.quantile(values, q, interpolation="higher"))


def exact_cluster_se(influence: np.ndarray, contrast: np.ndarray) -> float:
    vector = influence @ contrast
    return float(np.sqrt(np.sum(np.square(vector))))


def summarize_linear(fit, influence: np.ndarray, contrast: np.ndarray,
                     signs: np.ndarray, interval_role: str) -> tuple[dict, np.ndarray]:
    estimate = float(contrast @ fit.beta)
    centered = signs @ (influence @ contrast)
    se = exact_cluster_se(influence, contrast)
    critical = quantile_higher(np.abs(centered / se), .95)
    return ({
        "estimate_log_points": estimate,
        "occupation_cluster_se": se,
        "ci_lower": estimate - critical * se,
        "ci_upper": estimate + critical * se,
        "wild_score_critical": critical,
        "wild_score_p_value": float(
            (1 + np.sum(np.abs(centered / se) >= abs(estimate / se))) / (len(centered) + 1)
        ),
        "normal_theory_mde80_log_points": NORMAL_MDE_MULTIPLIER * se,
        "normal_theory_mde80_relative_percent": 100 * math.expm1(NORMAL_MDE_MULTIPLIER * se),
        "draws": len(centered),
        "interval_role": interval_role,
    }, centered)


def frame_to_panel(cells: pd.DataFrame, occupations: list[str], months: list[str],
                   value: str = "stock") -> pd.DataFrame:
    young, older = CELLS.panel_for_ages(
        cells, occupations, months, (22, 25), (26, 65), value=value
    )
    index = pd.MultiIndex.from_product([occupations, months], names=["occ_code", "month"])
    return pd.DataFrame({
        "young_22_25": young.reshape(-1),
        "older_26_65": older.reshape(-1),
    }, index=index)


def read_external_map(path: pathlib.Path, column: str) -> dict[str, float]:
    frame = pd.read_csv(path, dtype={"census2018": str})
    frame["census2018"] = frame.census2018.str.zfill(4)
    return pd.to_numeric(frame.set_index("census2018")[column], errors="coerce").to_dict()


def fit_architecture(panel: pd.DataFrame, support: list[str], months: list[str],
                     exposure: dict[str, float], webb: dict[str, float]):
    young, older = FROZEN.panel_arrays(panel, support, months)
    weights = (young + older).sum(axis=1)
    values = np.array([exposure[code] for code in support], float)
    groups = FROZEN.weighted_quintiles(values, weights)
    fit, influence, _, labels = CORE.fit_group_model(panel, support, months, groups, webb)
    target = labels.index("group_5_vs_1_x_post")
    return fit, influence, target, weights, groups


def canonical_and_paired_architectures(args, cells, setup, panel) -> dict:
    months = setup["frozen_static"]
    primary_support = setup["support"]
    webb = setup["webb"]
    primary = setup["beta"]
    fit, influence, target, _, _ = fit_architecture(
        panel, primary_support, months, primary, webb
    )
    if not np.isclose(fit.beta[target], PRIMARY_EXPECTED, atol=1e-8, rtol=0):
        raise RuntimeError("canonical primary no longer reproduces the frozen coefficient")
    signs = np.random.default_rng(SEED).choice(
        np.array([-1., 1.]), size=(DRAWS, len(primary_support))
    )
    contrast = np.zeros(len(fit.beta)); contrast[target] = 1
    primary_row, primary_draws = summarize_linear(
        fit, influence, contrast, signs, "CANONICAL_PRIMARY_INTERVAL"
    )
    primary_row.update({
        "analysis_status": LABEL, "specification": "frozen_beta_by_Webb",
        "support_occupations": len(primary_support),
        "support_hash_sha256": support_hash(primary_support),
        "bootstrap_seed": SEED,
        "coefficient_matches_frozen": True,
    })
    write_csv(args.output_dir / "CANONICAL_PRIMARY_INTERVAL.csv", [primary_row])

    external = {
        "webb_ai_patent_task": read_external_map(args.webb_ai_map, "webb_ai"),
        "oecd_ai_capability_gap_reversed": read_external_map(
            args.oecd_ai_map, "oecd_ai_gap_reversed"
        ),
    }
    alternatives = {
        **{name: setup["exposures"][name]["A"] for name in MEASURES if name != "dv_rating_beta"},
        **external,
    }
    pair_rows = []
    for pair_index, (name, alternative) in enumerate(alternatives.items()):
        support = sorted(
            code for code in setup["frozen_support"]
            if np.isfinite(primary.get(code, np.nan))
            and np.isfinite(alternative.get(code, np.nan))
            and np.isfinite(webb.get(code, np.nan))
        )
        beta_fit, beta_inf, beta_target, weights, beta_groups = fit_architecture(
            panel, support, months, primary, webb
        )
        alt_fit, alt_inf, alt_target, _, alt_groups = fit_architecture(
            panel, support, months, alternative, webb
        )
        pair_signs = np.random.default_rng(SEED + 100 + pair_index).choice(
            np.array([-1., 1.]), size=(DRAWS, len(support))
        )
        beta_contrast = np.zeros(len(beta_fit.beta)); beta_contrast[beta_target] = 1
        alt_contrast = np.zeros(len(alt_fit.beta)); alt_contrast[alt_target] = 1
        beta_item, beta_centered = summarize_linear(
            beta_fit, beta_inf, beta_contrast, pair_signs, "PAIRED_ANALYSIS_MEMBER_INTERVAL"
        )
        alt_item, alt_centered = summarize_linear(
            alt_fit, alt_inf, alt_contrast, pair_signs, "PAIRED_ANALYSIS_MEMBER_INTERVAL"
        )
        delta = beta_item["estimate_log_points"] - alt_item["estimate_log_points"]
        delta_centered = beta_centered - alt_centered
        delta_se = float(np.sqrt(np.sum(np.square(
            beta_inf @ beta_contrast - alt_inf @ alt_contrast
        ))))
        delta_critical = quantile_higher(np.abs(delta_centered / delta_se), .95)
        pair_rows.append({
            "analysis_status": LABEL,
            "contrast": f"dv_rating_beta_minus_{name}",
            "support_occupations": len(support),
            "support_hash_sha256": support_hash(support),
            "bootstrap_seed": SEED + 100 + pair_index,
            "common_occupation_multipliers": True,
            "beta_pair_estimate": beta_item["estimate_log_points"],
            "beta_pair_se": beta_item["occupation_cluster_se"],
            "beta_pair_ci_lower": beta_item["ci_lower"],
            "beta_pair_ci_upper": beta_item["ci_upper"],
            "alternative_estimate": alt_item["estimate_log_points"],
            "alternative_se": alt_item["occupation_cluster_se"],
            "alternative_ci_lower": alt_item["ci_lower"],
            "alternative_ci_upper": alt_item["ci_upper"],
            "difference_beta_minus_alternative": delta,
            "paired_se_difference": delta_se,
            "paired_ci_lower": delta - delta_critical * delta_se,
            "paired_ci_upper": delta + delta_critical * delta_se,
            "paired_wild_score_critical": delta_critical,
            "paired_p_value": float(
                (1 + np.sum(np.abs(delta_centered / delta_se) >= abs(delta / delta_se)))
                / (DRAWS + 1)
            ),
            "paired_normal_theory_mde80_log_points": NORMAL_MDE_MULTIPLIER * delta_se,
            "paired_normal_theory_mde80_relative_percent": 100 * math.expm1(
                NORMAL_MDE_MULTIPLIER * delta_se
            ),
            "q5_jaccard": len(set(np.array(support)[beta_groups == 5]) &
                                  set(np.array(support)[alt_groups == 5])) /
                           len(set(np.array(support)[beta_groups == 5]) |
                               set(np.array(support)[alt_groups == 5])),
            "draws": DRAWS,
            "interval_note": (
                "Member intervals are pair-specific; neither replaces the canonical primary interval"
            ),
        })
    write_csv(args.output_dir / "PAIRED_ARCHITECTURE_PRECISION.csv", pair_rows)

    reference_defs = {
        "Q5_minus_Q1": np.array([0., 0., 0., 1., 0.]),
        "Q5_minus_Q2": np.array([-1., 0., 0., 1., 0.]),
        "Q5_minus_Q3": np.array([0., -1., 0., 1., 0.]),
        "Q5_minus_Q4": np.array([0., 0., -1., 1., 0.]),
        "Q4_minus_Q2": np.array([-1., 0., 1., 0., 0.]),
    }
    reference_rows = []
    for name, vector in reference_defs.items():
        item, _ = summarize_linear(
            fit, influence, vector, signs,
            "CANONICAL_PRIMARY_INTERVAL" if name == "Q5_minus_Q1" else "ALTERNATIVE_COMPARISON_INTERVAL",
        )
        item.update({
            "analysis_status": LABEL, "contrast": name,
            "support_occupations": len(primary_support),
            "support_hash_sha256": support_hash(primary_support),
            "bootstrap_seed": SEED,
        })
        reference_rows.append(item)
    write_csv(args.output_dir / "REFERENCE_CONTRAST_PRECISION.csv", reference_rows)
    return {"primary": primary_row, "architecture_pairs": pair_rows,
            "reference_contrasts": reference_rows}


def distribution_row(label: str, values: np.ndarray, period: str, group: str) -> dict:
    flat = np.asarray(values, float).reshape(-1)
    return {
        "analysis_status": LABEL, "measure": label, "period": period, "age_group": group,
        "cells": len(flat), "zero_share": float(np.mean(flat == 0)),
        "below_5_share": float(np.mean(flat < 5)),
        "p10": float(np.quantile(flat, .10)), "median": float(np.quantile(flat, .50)),
        "p90": float(np.quantile(flat, .90)), "mean": float(np.mean(flat)),
        "minimum": float(np.min(flat)), "maximum": float(np.max(flat)),
    }


def fit_masked_cells(young, older, keep_cell, groups, webb_z, months, signs, label):
    y = np.where(keep_cell, young, 0.0)
    o = np.where(keep_cell, older, 0.0)
    valid_occ = (y + o).sum(axis=1) > 0
    fit, influence, labels, _ = CELLS.fit_q_model(
        y[valid_occ], o[valid_occ], groups[valid_occ], webb_z[valid_occ], months
    )
    target = labels.index("Q5_x_post_2023_2026")
    contrast = np.zeros(len(fit.beta)); contrast[target] = 1
    item, _ = summarize_linear(
        fit, influence, contrast, signs[:, valid_occ], "BOUNDARY_SELECTION_DIAGNOSTIC_INTERVAL"
    )
    return {
        "analysis_status": LABEL, "specification": label,
        "support_occupations": int(valid_occ.sum()),
        "retained_occupation_month_cells": int(keep_cell[valid_occ].sum()),
        "retained_cell_share": float(keep_cell[valid_occ].mean()),
        "selection_warning": (
            "Threshold conditions directly on realized respondent counts and changes the estimand; diagnostic only"
        ),
        **item,
    }


def respondent_boundary_and_quarterly(args, cells, setup) -> dict:
    support, months = setup["support"], setup["frozen_static"]
    young, older = CELLS.panel_for_ages(cells, support, months, (22, 25), (26, 65), "stock")
    count_y, count_o = CELLS.panel_for_ages(
        cells, support, months, (22, 25), (26, 65), "respondent_equivalent"
    )
    period_masks = {
        "all_frozen_months": np.ones(len(months), dtype=bool),
        "probabilistically_bridged_2017_2019": np.array([m < "2020-01" for m in months]),
        "direct_2020_plus": np.array([m >= "2020-01" for m in months]),
    }
    count_rows = []
    for period, mask in period_masks.items():
        for group, values in (("young_22_25", count_y[:, mask]),
                              ("older_26_65", count_o[:, mask])):
            count_rows.append(distribution_row(
                "respondent_equivalent" if period != "direct_2020_plus" else "exact_respondent_count",
                values, period, group,
            ))
        count_rows.append(distribution_row(
            "respondent_equivalent" if period != "direct_2020_plus" else "exact_respondent_count",
            np.stack([count_y[:, mask], count_o[:, mask]], axis=2), period, "pooled_cell_age_groups",
        ))
    write_csv(args.output_dir / "RESPONDENT_COUNT_DISTRIBUTION.csv", count_rows)

    total = young + older
    boundary = [{
        "analysis_status": LABEL, "universe": "primary_beta_Webb_frozen_calendar",
        "occupation_month_cells": int(total.size),
        "age_specific_cells": int(2 * total.size),
        "zero_young_cells": int(np.sum(young == 0)),
        "zero_older_cells": int(np.sum(older == 0)),
        "empty_both_cells_dropped_by_likelihood": int(np.sum(total == 0)),
        "young_boundary_share_all_occupation_month_cells": float(np.mean(young == 0)),
        "older_boundary_share_all_occupation_month_cells": float(np.mean(older == 0)),
        "any_one_sided_boundary_share": float(np.mean(((young == 0) ^ (older == 0)))),
        "both_empty_share": float(np.mean(total == 0)),
        "positive_total_cells_used_by_likelihood": int(np.sum(total > 0)),
        "conditional_likelihood_behavior": (
            "y=0 and y=n cells are valid finite grouped-binomial contributions; only n=0 cells are removed"
        ),
    }]
    write_csv(args.output_dir / "BOUNDARY_CELL_DIAGNOSTICS.csv", boundary)

    signs = np.random.default_rng(SEED + 300).choice(
        np.array([-1., 1.]), size=(DRAWS, len(support))
    )
    selected_rows = [
        fit_masked_cells(young, older, count_y >= 5, setup["quintiles"], setup["webb_z"],
                         months, signs, "at_least_5_young_respondent_equivalents"),
        fit_masked_cells(young, older, (count_y >= 5) & (count_o >= 5), setup["quintiles"],
                         setup["webb_z"], months, signs,
                         "at_least_5_respondent_equivalents_in_each_age_group"),
    ]
    write_csv(args.output_dir / "BOUNDARY_SELECTION_ESTIMATES.csv", selected_rows)

    # The repaired 113-month calendar is the substantive descriptive baseline.
    # The immutable 108-month estimate remains the chronology benchmark and
    # receives the sole canonical-primary interval above.
    repaired_months = [m for m in setup["observed_months"] if m != "2022-12"]
    repaired_y, repaired_o = CELLS.panel_for_ages(
        cells, support, repaired_months, (22, 25), (26, 65), "stock"
    )
    repaired_fit, repaired_inf, repaired_labels, _ = CELLS.fit_q_model(
        repaired_y, repaired_o, setup["quintiles"], setup["webb_z"], repaired_months
    )
    repaired_target = repaired_labels.index("Q5_x_post_2023_2026")
    repaired_vector = np.zeros(len(repaired_fit.beta)); repaired_vector[repaired_target] = 1
    repaired_item, _ = summarize_linear(
        repaired_fit, repaired_inf, repaired_vector, signs,
        "REPAIRED_CALENDAR_SUBSTANTIVE_BASELINE_INTERVAL",
    )
    repaired_rows = [{
        "analysis_status": LABEL,
        "specification": "repaired_113_month_monthly_substantive_baseline",
        "role": "substantive descriptive baseline",
        "support_occupations": len(support), "months": len(repaired_months),
        "frozen_quintile_membership_retained": True,
        "frozen_Webb_scaling_retained": True,
        "contrast_with_frozen_chronology_benchmark": PRIMARY_EXPECTED,
        **repaired_item,
    }]
    write_csv(args.output_dir / "REPAIRED_MONTHLY_BASELINE.csv", repaired_rows)

    quarterly_rows = []
    quarterly_counts = []
    for spec, selected_months in (
        ("frozen_108_month_calendar", setup["frozen_static"]),
        ("repaired_113_month_calendar", [m for m in setup["observed_months"] if m != "2022-12"]),
    ):
        y, o = CELLS.panel_for_ages(cells, support, selected_months, (22, 25), (26, 65), "stock")
        cy, co = CELLS.panel_for_ages(
            cells, support, selected_months, (22, 25), (26, 65), "respondent_equivalent"
        )
        quarters = [f"{m[:4]}-Q{(int(m[5:7]) - 1) // 3 + 1}" for m in selected_months]
        quarter_levels = list(dict.fromkeys(quarters))
        yq = np.column_stack([y[:, np.array(quarters) == q].sum(axis=1) for q in quarter_levels])
        oq = np.column_stack([o[:, np.array(quarters) == q].sum(axis=1) for q in quarter_levels])
        cyq = np.column_stack([cy[:, np.array(quarters) == q].sum(axis=1) for q in quarter_levels])
        coq = np.column_stack([co[:, np.array(quarters) == q].sum(axis=1) for q in quarter_levels])
        post = np.array([q >= "2023-Q1" for q in quarter_levels])
        fit, influence, labels, _ = CELLS.fit_q_model(
            yq, oq, setup["quintiles"], setup["webb_z"], quarter_levels,
            period_masks=[("post_2023_2026", post)],
        )
        target = labels.index("Q5_x_post_2023_2026")
        vector = np.zeros(len(fit.beta)); vector[target] = 1
        item, _ = summarize_linear(
            fit, influence, vector, signs, "QUARTERLY_OCCUPATION_CLUSTER_INTERVAL"
        )
        months_per_quarter = pd.Series(quarters).value_counts()
        quarterly_rows.append({
            "analysis_status": LABEL, "specification": spec,
            "support_occupations": len(support), "quarters": len(quarter_levels),
            "minimum_observed_months_in_quarter": int(months_per_quarter.min()),
            "maximum_observed_months_in_quarter": int(months_per_quarter.max()),
            "incomplete_quarters": int(np.sum(months_per_quarter < 3)),
            "post_start": "2023-Q1", "transition_treatment": "December 2022 omitted before aggregation",
            "quintiles": "frozen primary monthly classification retained",
            "fixed_effects": "occupation and calendar quarter",
            **item,
        })
        for group, values in (("young_22_25", cyq), ("older_26_65", coq)):
            quarterly_counts.append(distribution_row(
                "quarterly_respondent_equivalent", values, spec, group
            ))
    write_csv(args.output_dir / "QUARTERLY_ESTIMATES.csv", quarterly_rows)
    write_csv(args.output_dir / "QUARTERLY_RESPONDENT_COUNTS.csv", quarterly_counts)
    return {"counts": count_rows, "boundary": boundary,
            "boundary_estimates": selected_rows, "repaired_monthly": repaired_rows,
            "quarterly": quarterly_rows}


def score_objects(young: np.ndarray, older: np.ndarray, regressors: np.ndarray):
    n_occ, n_month = young.shape
    total_full = (young + older).reshape(-1)
    occ_full = np.repeat(np.arange(n_occ), n_month)
    month_full = np.tile(np.arange(n_month), n_occ)
    fit = FROZEN.ENGINE.fit_grouped_logit_fe(
        young.reshape(-1), total_full, occ_full, month_full, regressors, max_iterations=5000
    )
    if not fit.converged:
        raise RuntimeError("score-object model did not converge")
    keep = total_full > 0
    y, n = young.reshape(-1)[keep], total_full[keep]
    occ, month, x = occ_full[keep], month_full[keep], regressors[keep]
    p = fit.fitted_probability[keep]
    residual = y - n * p
    weight = np.maximum(n * p * (1 - p), 1e-12)
    rx = FROZEN.ENGINE._weighted_absorb(x, weight, occ, month, n_occ, n_month)
    information = rx.T @ (weight[:, None] * rx)
    bread = np.linalg.inv(information)
    scores = rx * residual[:, None]
    return fit, bread, scores, occ, month


def grouped_scores(scores: np.ndarray, groups: np.ndarray, n_groups: int) -> np.ndarray:
    result = np.zeros((n_groups, scores.shape[1]))
    np.add.at(result, groups, scores)
    return result


def newey_west_meat(time_scores: np.ndarray, lag: int) -> np.ndarray:
    meat = time_scores.T @ time_scores
    for ell in range(1, lag + 1):
        weight = 1.0 - ell / (lag + 1.0)
        gamma = time_scores[ell:].T @ time_scores[:-ell]
        meat += weight * (gamma + gamma.T)
    return meat


def rotation_hac(args, cells, setup) -> list[dict]:
    support, months = setup["support"], setup["frozen_static"]
    young, older = CELLS.panel_for_ages(cells, support, months, (22, 25), (26, 65), "stock")
    post = np.array([m >= "2023-01" for m in months])
    columns = [
        (((setup["quintiles"] == q)[:, None]) & post[None, :]).reshape(-1).astype(float)
        for q in (2, 3, 4, 5)
    ]
    columns.append((setup["webb_z"][:, None] * post[None, :]).reshape(-1))
    regressors = np.column_stack(columns)
    fit, bread, scores, occ, month = score_objects(young, older, regressors)
    n_occ, n_month, n_cell = len(support), len(months), len(scores)
    occ_scores = grouped_scores(scores, occ, n_occ)
    time_scores = grouped_scores(scores, month, n_month)
    occ_meat = n_occ / (n_occ - 1) * (occ_scores.T @ occ_scores)
    cell_meat = n_cell / (n_cell - 1) * (scores.T @ scores)
    rows = []
    for lag in (0, 1, 4, 12, 16):
        time_meat = n_month / (n_month - 1) * newey_west_meat(time_scores, lag)
        covariance = bread @ (occ_meat + time_meat - cell_meat) @ bread
        covariance = (covariance + covariance.T) / 2
        variance = float(covariance[3, 3])
        se = math.sqrt(variance) if variance >= 0 else float("nan")
        rows.append({
            "analysis_status": LABEL,
            "specification": "occupation_cluster_plus_time_HAC_minus_cell_intersection",
            "time_HAC_lag_months": lag,
            "coefficient": float(fit.beta[3]),
            "se": se,
            "normal_ci_lower": float(fit.beta[3] - Z_975 * se) if np.isfinite(se) else "",
            "normal_ci_upper": float(fit.beta[3] + Z_975 * se) if np.isfinite(se) else "",
            "normal_theory_mde80_log_points": NORMAL_MDE_MULTIPLIER * se if np.isfinite(se) else "",
            "occupation_cluster_only_se": float(fit.standard_error[3]),
            "nominal_occupations": n_occ, "months": n_month,
            "minimum_covariance_eigenvalue": float(np.linalg.eigvalsh(covariance).min()),
            "interpretation": (
                "Score-covariance sensitivity allowing occupation dependence plus contemporaneous and "
                "lagged dependence in cross-occupation aggregate monthly scores; not CPS design-based inference"
            ),
            "rotation_note": (
                "Occupation clustering already permits arbitrary serial dependence within an occupation. "
                "The HAC addition targets cross-occupation covariance across nearby months, including overlap-related covariance."
            ),
        })
    write_csv(args.output_dir / "ROTATION_TIME_HAC_SENSITIVITY.csv", rows)
    return rows


def pseudo_breaks(args, cells, setup) -> dict:
    months = [m for m in setup["observed_months"] if "2017-01" <= m <= "2019-12"]
    if months != [f"{y:04d}-{m:02d}" for y in range(2017, 2020) for m in range(1, 13)]:
        raise RuntimeError("repaired pre-2020 calendar is not a continuous 36-month panel")
    candidate_support = [
        code for code in setup["frozen_support"]
        if np.isfinite(setup["beta"].get(code, np.nan))
        and np.isfinite(setup["webb"].get(code, np.nan))
    ]
    young, older = CELLS.panel_for_ages(
        cells, candidate_support, months, (22, 25), (26, 65), "stock"
    )
    valid = (young.sum(axis=1) > 0) & (older.sum(axis=1) > 0)
    support = [code for code, keep in zip(candidate_support, valid) if keep]
    young, older = young[valid], older[valid]
    weights = (young + older).sum(axis=1)
    beta = np.array([setup["beta"][code] for code in support])
    pre_AI_groups = FROZEN.weighted_quintiles(beta, weights)
    webb_raw = np.array([setup["webb"][code] for code in support])
    webb_mean, webb_sd = FROZEN.weighted_scale(webb_raw, weights)
    pre_AI_webb_z = (webb_raw - webb_mean) / webb_sd
    frozen_q_map = dict(zip(setup["support"], setup["quintiles"]))
    frozen_webb_map = dict(zip(setup["support"], setup["webb_z"]))
    frozen_groups = np.array([frozen_q_map[code] for code in support], int)
    frozen_webb_z = np.array([frozen_webb_map[code] for code in support], float)
    classifications = (
        ("pre_AI_2017_2019_weights", pre_AI_groups, pre_AI_webb_z,
         "Both quintiles and Webb scaling use only the fully pre-2020 placebo window"),
        ("frozen_primary_model_period_weights", frozen_groups, frozen_webb_z,
         "Holds the realized frozen-primary classification and Webb scaling fixed for exact classification comparability"),
    )
    signs = np.random.default_rng(SEED + 400).choice(
        np.array([-1., 1.]), size=(DRAWS, len(support))
    )
    rows = []
    for classification, groups, webb_z, classification_note in classifications:
        for break_index in range(2, len(months)):  # >=1 pre month after transition; >=1 post.
            break_month = months[break_index]
            transition = months[break_index - 1]
            kept_months = [m for m in months if m != transition]
            keep_index = np.array([m != transition for m in months])
            y, o = young[:, keep_index], older[:, keep_index]
            post = np.array([m >= break_month for m in kept_months])
            fit, influence, labels, _ = CELLS.fit_q_model(
                y, o, groups, webb_z, kept_months,
                period_masks=[("pseudo_post", post)],
            )
            target = labels.index("Q5_x_pseudo_post")
            vector = np.zeros(len(fit.beta)); vector[target] = 1
            item, _ = summarize_linear(
                fit, influence, vector, signs, "PSEUDO_BREAK_OCCUPATION_CLUSTER_INTERVAL"
            )
            pre_count, post_count = int(np.sum(~post)), int(np.sum(post))
            rows.append({
                "analysis_status": LABEL, "classification_rule": classification,
                "classification_note": classification_note,
                "pseudo_break": break_month,
                "omitted_transition_month": transition,
                "window_start": months[0], "window_end": months[-1],
                "pre_months": pre_count, "post_months": post_count,
                "balanced_at_least_12_months_each_side": pre_count >= 12 and post_count >= 12,
                "support_occupations": len(support), "support_hash_sha256": support_hash(support),
                **item,
            })
    write_csv(args.output_dir / "PSEUDO_BREAK_DISTRIBUTION_2017_2019.csv", rows)
    by_classification = {}
    for classification, _, _, note in classifications:
        selected = [row for row in rows if row["classification_rule"] == classification]
        coefficients = np.array([row["estimate_log_points"] for row in selected])
        balanced = np.array([row["balanced_at_least_12_months_each_side"] for row in selected])
        by_classification[classification] = {
            "classification_note": note,
            "candidate_breaks": len(selected), "balanced_breaks": int(balanced.sum()),
            "all_breaks_coefficient_quantiles": {
                "p05": float(np.quantile(coefficients, .05)),
                "median": float(np.quantile(coefficients, .5)),
                "p95": float(np.quantile(coefficients, .95)),
            },
            "balanced_breaks_coefficient_quantiles": {
                "p05": float(np.quantile(coefficients[balanced], .05)),
                "median": float(np.quantile(coefficients[balanced], .5)),
                "p95": float(np.quantile(coefficients[balanced], .95)),
            },
            "one_sided_empirical_tail_all": float(
                (1 + np.sum(coefficients <= PRIMARY_EXPECTED)) / (len(coefficients) + 1)
            ),
            "one_sided_empirical_tail_balanced": float(
                (1 + np.sum(coefficients[balanced] <= PRIMARY_EXPECTED)) / (balanced.sum() + 1)
            ),
        }
    summary = {
        "analysis_status": LABEL,
        "requested_years": [2015, 2016, 2017, 2018, 2019],
        "unavailable_years": [2015, 2016],
        "unavailable_reason": "Authenticated YAX CPS extract begins in January 2017",
        "pre_AI_window": [months[0], months[-1]],
        "actual_post_2022_outcomes_used_in_pseudo_break_models": False,
        "candidate_rule": (
            "All breaks with at least one retained month before and after, after omitting the immediately preceding transition month"
        ),
        "candidate_breaks_per_classification": len(rows) // len(classifications),
        "balanced_rule": "At least 12 retained months before and 12 months after the pseudo-break",
        "observed_primary_benchmark": PRIMARY_EXPECTED,
        "classification_sensitivities": by_classification,
        "warning": (
            "Overlapping pseudo-break estimates are dependent; the empirical tail is a descriptive time-placebo diagnostic, not an exact randomization p-value"
        ),
    }
    write_json(args.output_dir / "PSEUDO_BREAK_SUMMARY.json", summary)
    return {"rows": rows, "summary": summary}


def run_main(args) -> dict:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    authenticated = FROZEN.validate_inputs(args)
    authenticated["hashes"]["repair_microdata"] = sha256(args.repair_microdata)
    cells, _, build = CELLS.build_exact_age_cells(args)
    setup = CELLS.primary_setup(args, cells)
    setup["frozen_support"] = FROZEN.read_preperiod(args.preperiod_cells)[1]
    base_panel = frame_to_panel(cells, setup["frozen_support"], setup["frozen_static"])
    sections = {
        "canonical_and_paired": canonical_and_paired_architectures(args, cells, setup, base_panel),
        "respondent_boundary_quarterly": respondent_boundary_and_quarterly(args, cells, setup),
        "rotation_HAC": rotation_hac(args, cells, setup),
        "pseudo_breaks": pseudo_breaks(args, cells, setup),
    }
    receipt = {
        "record": "YAX round-2 precision and rotation audit",
        "analysis_status": LABEL,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "canonical_draws": DRAWS, "canonical_seed": SEED,
        "normal_MDE80_formula": "(1.959963984540054 + 0.8416212335729143) * realized SE",
        "input_hashes": authenticated["hashes"],
        "private_paths_recorded": False,
        "raw_build_aggregate": {
            key: value for key, value in build.items() if key != "microdata_files"
        },
        "protected_artifacts_modified": False,
        "sections": sections,
    }
    write_json(args.output_dir / "MAIN_EXECUTION_RECEIPT.json", receipt)
    return receipt


def covariance_preserving_simulation(args) -> dict:
    """Change only the occupation-sign rule in the historical beta/Webb DGP.

    A single global sign retains each donor month's complete cross-occupation
    residual vector, whereas the historical independent occupation signs make
    off-diagonal residual covariance zero in expectation.  Offset x global-sign
    combinations are enumerated exactly, so this sensitivity has no Monte Carlo
    error conditional on the 66 historical donor offsets.
    """
    args.output_dir.mkdir(parents=True, exist_ok=True)
    prepared = POWER.prepare(
        args.preperiod_cells, args.lookup, args.computerization,
        "dv_rating_beta", "webb_pct_software",
    )
    dgp = POWER.build_dgp(prepared, "q5_q1")
    n_occ, n_pre = dgp["total_pre"].shape
    effects = (0.0, -0.005, -0.015, -0.03, -0.05, -0.08, -0.12, -0.18)
    results = []
    raw_rows = []
    rejection_vectors = {}
    null_t = None
    all_draws = {}
    for effect in effects:
        estimates, ses, raw_t = [], [], []
        for offset in range(n_pre):
            donors = (np.arange(dgp["target_month_count"]) + offset) % n_pre
            total = dgp["total_pre"][:, donors]
            for global_sign in (-1.0, 1.0):
                young_null = dgp["fitted_pre"][:, donors] + global_sign * dgp["residual_pre"][:, donors]
                probability = np.divide(
                    young_null, total, out=np.full_like(young_null, .5), where=total > 0
                )
                probability = np.clip(probability, 1e-9, 1 - 1e-9)
                treatment = (prepared["ai_quintile"] == 5).astype(float)
                shift = ((effect * treatment[:, None] +
                          POWER.DEFAULT_BETA_C * prepared["comp_z"][:, None]) *
                         dgp["post"][None, :])
                injected = total * FROZEN.ENGINE._sigmoid(
                    np.log(probability / (1 - probability)) + shift
                )
                fit = FROZEN.ENGINE.fit_grouped_logit_fe(
                    injected.reshape(-1), total.reshape(-1), dgp["occupation"],
                    dgp["month"], dgp["regressors"], max_iterations=5000,
                )
                if not fit.converged:
                    raise RuntimeError(f"covariance-preserving fit failed at {effect}, {offset}, {global_sign}")
                estimate = float(fit.beta[dgp["target_index"]])
                se = float(fit.standard_error[dgp["target_index"]])
                estimates.append(estimate); ses.append(se); raw_t.append(estimate / se)
                raw_rows.append({
                    "analysis_status": LABEL, "true_log_effect": effect,
                    "donor_offset": offset, "global_residual_sign": global_sign,
                    "estimate": estimate, "occupation_cluster_se": se,
                })
        estimates, ses, raw_t = map(np.asarray, (estimates, ses, raw_t))
        all_draws[effect] = (estimates, ses, raw_t)
        if effect == 0:
            null_t = raw_t
    critical = quantile_higher(np.abs(null_t), .95)
    for effect in effects:
        estimates, ses, raw_t = all_draws[effect]
        rejected = np.abs(raw_t) > critical
        rejection_vectors[effect] = rejected
        results.append({
            "true_log_effect": effect, "enumerated_draws": len(estimates),
            "rejection_probability_zero": float(rejected.mean()),
            "mean_estimate": float(estimates.mean()),
            "empirical_sd_estimate": float(estimates.std(ddof=1)),
            "mean_occupation_cluster_se": float(ses.mean()),
            "rmse": float(np.sqrt(np.mean(np.square(estimates - effect)))),
        })
    mde = POWER.interpolate_mde(results)
    published_old = 0.012169648511417098
    realized = 0.04440978614525461
    null = results[0]
    analytic_fraction = (
        (null["mean_occupation_cluster_se"] - published_old) / (realized - published_old)
    )
    published_old_empirical = 0.012493732077825115
    empirical_fraction = (
        (null["empirical_sd_estimate"] - published_old_empirical) /
        (realized - published_old_empirical)
    )
    summary = {
        "analysis_status": LABEL,
        "simulation_role": "historical precision sensitivity; not a new outcome model",
        "design_held_fixed": (
            "Original beta/Webb Q5-Q1 grouped-binomial DGP, 66 preperiod donors, 42 synthetic post months, fixed computerization shift"
        ),
        "only_changed_rule": (
            "One global residual sign per draw replaces independent occupation signs, preserving each donor month's complete cross-occupation residual vector"
        ),
        "enumeration": "All 66 cyclic donor offsets times both global signs",
        "draws_per_effect": 2 * n_pre,
        "critical_value_two_sided": critical,
        "empirical_mde80_relative_decline": mde,
        "results": results,
        "precision_gap": {
            "published_independent_sign_mean_SE": published_old,
            "covariance_preserving_mean_SE": null["mean_occupation_cluster_se"],
            "realized_primary_occupation_cluster_SE": realized,
            "fraction_of_analytic_SE_gap_closed": analytic_fraction,
            "published_independent_sign_null_RMSE": published_old_empirical,
            "covariance_preserving_empirical_SD": null["empirical_sd_estimate"],
            "fraction_of_empirical_SD_gap_closed": empirical_fraction,
        },
        "limitations": [
            "Global-sign preservation is a sharp full-covariance sensitivity, not a uniquely identified residual DGP.",
            "The finite donor process has only 132 unique offset-sign paths.",
            "Occupation-cluster SEs still condition on realized aggregate cells and are not CPS replicate-weight variances.",
            "A fraction below zero or above one is reported as computed and is not truncated.",
            "This exercise cannot uniquely attribute the prospective-realized precision gap.",
        ],
        "post_2022_outcomes_read_by_simulation": False,
        "input_hashes": {
            "preperiod_cells": sha256(args.preperiod_cells),
            "lookup": sha256(args.lookup),
            "computerization": sha256(args.computerization),
        },
    }
    write_csv(args.output_dir / "HISTORICAL_CROSS_OCCUPATION_DRAWS.csv", raw_rows)
    write_json(args.output_dir / "HISTORICAL_CROSS_OCCUPATION_SIMULATION.json", summary)
    return summary


def finalize_receipt(args, status: str) -> None:
    files = sorted(path for path in args.output_dir.iterdir()
                   if path.is_file() and path.name != "OUTPUT_MANIFEST.json")
    write_json(args.output_dir / "OUTPUT_MANIFEST.json", {
        "record": "YAX precision/rotation output manifest",
        "analysis_status": LABEL, "stage": status,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "output_hashes": {path.name: sha256(path) for path in files},
        "protected_refs": {
            "v1.1-design-freeze": subprocess.check_output(
                ["git", "rev-parse", "v1.1-design-freeze^{}"], cwd=ROOT, text=True
            ).strip(),
            "v1.1-confirmatory-results": subprocess.check_output(
                ["git", "rev-parse", "v1.1-confirmatory-results^{}"], cwd=ROOT, text=True
            ).strip(),
        },
    })


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--stage", choices=("main", "simulation", "all"), default="all")
    value.add_argument("--microdata", type=pathlib.Path)
    value.add_argument("--repair-microdata", type=pathlib.Path)
    value.add_argument("--preperiod-cells", type=pathlib.Path, required=True)
    value.add_argument("--lookup", type=pathlib.Path,
                       default=ROOT / "yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv")
    value.add_argument("--computerization", type=pathlib.Path,
                       default=ROOT / "yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv")
    value.add_argument("--computerization-2010", type=pathlib.Path,
                       default=ROOT / "yax/measurement/COMPUTERIZATION_MEASURES.csv")
    value.add_argument("--rule-b-values", type=pathlib.Path,
                       default=ROOT / "yax/measurement/RULE_B_VALUES_CENSUS2018.csv")
    value.add_argument("--bridge", type=pathlib.Path,
                       default=ROOT / "yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv")
    value.add_argument("--first-access-receipt", type=pathlib.Path,
                       default=ROOT / "yax/analysis/FIRST_OUTCOME_ACCESS_RECEIPT.json")
    value.add_argument("--webb-ai-map", type=pathlib.Path,
                       default=ROOT / "yax/revision/referee_20260905/results/external/WEBB_AI_CENSUS2018_MAP.csv")
    value.add_argument("--oecd-ai-map", type=pathlib.Path,
                       default=ROOT / "yax/revision/referee_20260905/results/external/OECD_CENSUS2018_MAP.csv")
    value.add_argument("--output-dir", type=pathlib.Path, default=HERE / "results")
    return value


def main() -> int:
    args = parser().parse_args()
    if args.stage in ("main", "all"):
        if args.microdata is None or args.repair_microdata is None:
            raise SystemExit("main stage requires --microdata and --repair-microdata")
        run_main(args)
    if args.stage in ("simulation", "all"):
        covariance_preserving_simulation(args)
    finalize_receipt(args, args.stage)
    print(json.dumps({"status": "PASS_PRECISION_ROTATION", "stage": args.stage,
                      "output_dir": str(args.output_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
