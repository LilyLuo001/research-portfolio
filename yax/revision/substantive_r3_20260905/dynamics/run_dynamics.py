#!/usr/bin/env python3
"""Execute registered YAX R3 dynamics analyses DYN-01--DYN-04.

POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1.
Protected inputs are authenticated and read only. Historical treatment is the
required first panel. A rebuilt-preperiod treatment panel is added only when an
explicit, authenticated membership artifact is supplied; it never replaces the
historical panel silently.
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
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd


HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(
    os.environ.get("YAX_REPO_ROOT", str(pathlib.Path(__file__).resolve().parents[4]))
).resolve()
LABEL = "POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1"
DRAWS = 9999
SEED = 2026090529
MDE_FACTOR = 1.959963984540054 + 0.8416212335729143
REFERENCE_BIN = "2022Q4"
TRANSITION = "2022-12"
ONSET_DATES = (
    "2022-11", "2022-12", "2023-01", "2023-02",
    "2023-03", "2023-04", "2023-05", "2023-06",
)
EXPECTED_SUPPORT_HASH = "11ec58ab1004cd83d62c57785f6c0dd3ee5a8abf08b7f71a3b664e91ded8333b"
EXPECTED_CORRECTED_BASELINE = -0.1345539535732939
EXPECTED_MICRODATA_HASH = "3fe42477e6f2ce401e85123f0e278e758595c1c4071a8743f243a92752db38c9"
EXPECTED_REPAIR_HASH = "a4ae2ef06d66a0d47359ccceffff9a15843ac501a9f25f9a05aa8fdca9c4f911"
REPAIR_MARCH_CODES = {year * 100 + 3 for year in range(2017, 2022)}


def import_path(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import {}".format(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


COMP = import_path(
    "yax_r3_dynamics_composition",
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


def quantile(values, share):
    try:
        return float(np.quantile(values, share, method="higher"))
    except TypeError:
        return float(np.quantile(values, share, interpolation="higher"))


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


def progress(stage: str, **details) -> None:
    print(json.dumps({
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        **details,
    }, sort_keys=True), flush=True)


def quarter(month: str) -> str:
    return "{}Q{}".format(month[:4], (int(month[5:7]) - 1) // 3 + 1)


def march_repair_preflight(args):
    """Prove append and replace are identical on analysis-eligible March stock.

    The wide extract's 2017--2021 March samples are ASEC records, while the
    repair file contains the Basic Monthly samples. Appending is safe only if
    the wide ASEC rows contribute zero analysis-eligible positive-WTFINL stock.
    """
    observed_hashes = {
        "wide_microdata": sha256(args.microdata),
        "march_basic_repair": sha256(args.repair_microdata),
    }
    expected = {
        "wide_microdata": EXPECTED_MICRODATA_HASH,
        "march_basic_repair": EXPECTED_REPAIR_HASH,
    }
    if observed_hashes != expected:
        raise RuntimeError("March-repair preflight input hash mismatch")
    audits = {}
    identifiers = {}
    usecols = ["YEAR", "MONTH", "AGE", "EMPSTAT", "OCC", "WTFINL", "CPSIDP"]
    for source, path in (("wide_ASEC", args.microdata),
                         ("repair_Basic_Monthly", args.repair_microdata)):
        rows_read = target_rows = eligible_rows = duplicate_rows = 0
        eligible_stock = 0.0
        ids_by_month = {code: set() for code in REPAIR_MARCH_CODES}
        month_eligible = {code: 0 for code in REPAIR_MARCH_CODES}
        month_stock = {code: 0.0 for code in REPAIR_MARCH_CODES}
        for chunk in pd.read_csv(path, usecols=usecols, chunksize=500_000):
            rows_read += len(chunk)
            month_code = (
                pd.to_numeric(chunk.YEAR, errors="coerce") * 100 +
                pd.to_numeric(chunk.MONTH, errors="coerce")
            )
            chunk = chunk.loc[month_code.isin(REPAIR_MARCH_CODES)].copy()
            if chunk.empty:
                continue
            chunk["month_code"] = month_code.loc[chunk.index].astype(int)
            target_rows += len(chunk)
            age = pd.to_numeric(chunk.AGE, errors="coerce")
            emp = pd.to_numeric(chunk.EMPSTAT, errors="coerce").isin([10, 12])
            weight = pd.to_numeric(chunk.WTFINL, errors="coerce")
            occ = pd.to_numeric(chunk.OCC, errors="coerce")
            valid_occ = occ.notna() & occ.between(0, 9999) & occ.mod(1).eq(0)
            keep = age.between(18, 65) & emp & weight.gt(0) & np.isfinite(weight) & valid_occ
            selected = chunk.loc[keep, ["month_code", "CPSIDP"]].copy()
            selected["weight"] = weight.loc[selected.index].astype(float)
            eligible_rows += len(selected)
            eligible_stock += float(selected.weight.sum())
            for code, group in selected.groupby("month_code"):
                code = int(code)
                ids = pd.to_numeric(group.CPSIDP, errors="coerce").dropna().astype("int64")
                ids = ids.loc[ids.gt(0)]
                unique_ids = set(ids.tolist())
                duplicate_rows += int(ids.duplicated().sum())
                duplicate_rows += len(unique_ids & ids_by_month[code])
                ids_by_month[code].update(unique_ids)
                month_eligible[code] += len(group)
                month_stock[code] += float(group.weight.sum())
        audits[source] = {
            "rows_read": rows_read,
            "target_March_rows": target_rows,
            "analysis_eligible_positive_weight_rows": eligible_rows,
            "analysis_eligible_positive_weight_stock": eligible_stock,
            "eligible_CPSIDP_duplicate_rows_within_month": duplicate_rows,
            "eligible_rows_by_month": {str(key): value for key, value in sorted(month_eligible.items())},
            "eligible_stock_by_month": {str(key): value for key, value in sorted(month_stock.items())},
        }
        identifiers[source] = ids_by_month
    overlap = {
        str(code): len(identifiers["wide_ASEC"][code] & identifiers["repair_Basic_Monthly"][code])
        for code in sorted(REPAIR_MARCH_CODES)
    }
    passed = (
        audits["wide_ASEC"]["analysis_eligible_positive_weight_rows"] == 0 and
        audits["wide_ASEC"]["analysis_eligible_positive_weight_stock"] == 0 and
        audits["repair_Basic_Monthly"]["analysis_eligible_positive_weight_rows"] > 0 and
        all(value > 0 for value in audits["repair_Basic_Monthly"]["eligible_rows_by_month"].values()) and
        audits["repair_Basic_Monthly"]["eligible_CPSIDP_duplicate_rows_within_month"] == 0 and
        all(value == 0 for value in overlap.values())
    )
    receipt = {
        "status": "PASS_APPEND_EQUIVALENT_TO_REPLACE_ON_ANALYSIS_ELIGIBLE_STOCK" if passed else "FAIL_MARCH_REPAIR_POLICY",
        "policy": "append Basic Monthly repair only because wide ASEC contributes zero positive-WTFINL analysis-eligible stock",
        "analysis_eligibility": "age 18-65, employed EMPSTAT 10/12, valid OCC 0000-9999, finite WTFINL > 0",
        "input_hashes": observed_hashes,
        "source_audits": audits,
        "eligible_CPSIDP_overlap_by_month": overlap,
        "no_interpolation_or_duplicate_reweighting": True,
    }
    if not passed:
        raise RuntimeError("March repair append/replace equivalence failed: {}".format(receipt))
    return receipt


def fe_codes(majors: np.ndarray, n_month: int, structure: str) -> np.ndarray:
    if structure == "unconditioned":
        return np.tile(np.arange(n_month), len(majors))
    if structure == "SOC2_x_calendar_month":
        levels = {value: index for index, value in enumerate(sorted(set(majors.tolist())))}
        return np.concatenate([
            levels[majors[index]] * n_month + np.arange(n_month)
            for index in range(len(majors))
        ])
    raise ValueError("unknown structure {}".format(structure))


def fit_absorbed(young, older, regressors, majors, structure):
    second = fe_codes(majors, young.shape[1], structure)
    return COMP.fit_absorbed(young, older, regressors, second)


def fit_seasonal(young, older, regressors, majors, months, structure):
    """Absorb occupation-by-month-of-year and the declared calendar FE."""
    n_occ, n_month = young.shape
    total_full = (young + older).reshape(-1)
    young_full = young.reshape(-1)
    original_occ = np.repeat(np.arange(n_occ), n_month)
    season = np.tile(np.array([int(value[5:7]) - 1 for value in months]), n_occ)
    first_full = original_occ * 12 + season
    second_full = fe_codes(majors, n_month, structure)
    keep = total_full > 0
    y, total, x = young_full[keep], total_full[keep], regressors[keep]
    original_occ_fit = original_occ[keep]
    _, first = np.unique(first_full[keep], return_inverse=True)
    _, second = np.unique(second_full[keep], return_inverse=True)
    first_count = int(first.max()) + 1
    second_count = int(second.max()) + 1
    fit = FROZEN.ENGINE.fit_grouped_logit_fe(
        y, total, first, second, x, max_iterations=5000,
    )
    if not fit.converged:
        raise RuntimeError("seasonal grouped-binomial model did not converge")
    p = fit.fitted_probability
    residual = y - total * p
    weight = np.maximum(total * p * (1.0 - p), 1e-12)
    rx = FROZEN.ENGINE._weighted_absorb(
        x, weight, first, second, first_count, second_count,
    )
    information = rx.T @ (weight[:, None] * rx)
    bread = np.linalg.inv(information)
    scores = np.zeros((n_occ, x.shape[1]))
    np.add.at(scores, original_occ_fit, rx * residual[:, None])
    influence = scores @ bread.T
    influence *= math.sqrt(n_occ / (n_occ - 1))
    covariance = influence.T @ influence
    return fit, influence, {
        "information": information,
        "occupation_cluster_covariance": covariance,
        "occupation_count": n_occ,
        "first_fe_count": first_count,
        "second_fe_count": second_count,
        "positive_total_rows": int(keep.sum()),
        "additional_occupation_season_FE_relative_to_occupation_FE": int(first_count - n_occ),
    }


def build_dynamic_regressors(quintiles, webb_z, months):
    month_bins = np.array([quarter(value) for value in months], object)
    bins = sorted(set(month_bins.tolist()))
    if REFERENCE_BIN not in bins:
        raise RuntimeError("dynamic reference bin is absent")
    event_bins = [value for value in bins if value != REFERENCE_BIN]
    columns, labels, target_indices = [], [], []
    for event_bin in event_bins:
        period = month_bins == event_bin
        for q in (2, 3, 4, 5):
            columns.append(
                (((quintiles == q)[:, None]) & period[None, :]).reshape(-1).astype(float)
            )
            labels.append("Q{}_x_{}".format(q, event_bin))
            target_indices.append(len(columns) - 1)
        columns.append((webb_z[:, None] * period[None, :]).reshape(-1))
        labels.append("Webb_z_x_{}".format(event_bin))
    return np.column_stack(columns), labels, target_indices, event_bins, month_bins


def build_static_regressors(quintiles, webb_z, months, onset="2023-01",
                            quintile_month_of_year=False):
    post = np.array([month >= onset for month in months])
    columns, labels = [], []
    for q in (2, 3, 4, 5):
        columns.append(
            (((quintiles == q)[:, None]) & post[None, :]).reshape(-1).astype(float)
        )
        labels.append("Q{}_x_post_from_{}".format(q, onset))
    columns.append((webb_z[:, None] * post[None, :]).reshape(-1))
    labels.append("Webb_z_x_post_from_{}".format(onset))
    if quintile_month_of_year:
        # January is the omitted season. Quintile main effects are absorbed by
        # occupation FE, and common month-of-year effects by calendar-month FE.
        month_numbers = np.array([int(value[5:7]) for value in months])
        for q in (2, 3, 4, 5):
            for month_number in range(2, 13):
                columns.append((
                    ((quintiles == q)[:, None]) &
                    ((month_numbers == month_number)[None, :])
                ).reshape(-1).astype(float))
                labels.append("Q{}_x_month_of_year_{:02d}".format(q, month_number))
    return np.column_stack(columns), labels


def bootstrap_scalar(estimate, influence, signs):
    centered = signs @ influence
    se = float(np.sqrt(np.sum(np.square(influence))))
    bootstrap_se = float(np.std(centered, ddof=1))
    if not np.isfinite(se) or se <= 0:
        raise RuntimeError("nonpositive occupation-cluster standard error")
    critical = quantile(np.abs(centered / se), .95)
    pvalue = float((1 + np.sum(np.abs(centered / se) >= abs(estimate / se))) /
                   (len(centered) + 1))
    return {
        "coefficient": float(estimate),
        "occupation_cluster_se": se,
        "bootstrap_se": bootstrap_se,
        "ci_lower": float(estimate - critical * se),
        "ci_upper": float(estimate + critical * se),
        "wild_score_p_value": pvalue,
        "critical": critical,
        "normal_theory_MDE80": float(MDE_FACTOR * se),
    }, centered


def joint_zero(beta, influence, signs):
    covariance = influence.T @ influence
    inverse = np.linalg.pinv(covariance)
    observed = float(beta @ inverse @ beta)
    centered = signs @ influence
    draw_stat = np.einsum("ij,jk,ik->i", centered, inverse, centered)
    return {
        "joint_wald_statistic": observed,
        "wild_score_p_value": float((1 + np.sum(draw_stat >= observed)) / (len(draw_stat) + 1)),
        "restrictions": int(len(beta)),
        "covariance_rank": int(np.linalg.matrix_rank(covariance)),
        "bootstrap_draws": int(len(draw_stat)),
    }


def setup_historical(args, cells):
    setup = CELLS.primary_setup(args, cells)
    support = list(setup["support"])
    if len(support) != 468 or support_hash(support) != EXPECTED_SUPPORT_HASH:
        raise RuntimeError("historical support changed")
    months = [month for month in setup["observed_months"] if month != TRANSITION]
    if len(months) != 113 or "2025-10" in months:
        raise RuntimeError("corrected dynamic calendar is not the expected 113 months")
    return {
        "treatment_contract": "historical_production_full_static_weight",
        "support": support,
        "quintiles": np.asarray(setup["quintiles"], int),
        "webb_z": np.asarray(setup["webb_z"], float),
        "majors": np.array([setup["groups"].get(code, "MISSING") for code in support], object),
        "months": months,
        "names": setup["names"],
        "historical_setup": setup,
    }


def setup_rebuilt(path, historical, cells):
    if path is None or not path.is_file():
        return None
    frame = pd.read_csv(path, dtype={"occupation_code": str})
    required = {"occupation_code", "beta_quintile", "webb_z"}
    if not required.issubset(frame.columns):
        raise RuntimeError("rebuilt membership lacks {}".format(sorted(required - set(frame.columns))))
    frame["occupation_code"] = frame.occupation_code.str.zfill(4)
    if frame.occupation_code.duplicated().any():
        raise RuntimeError("rebuilt membership has duplicate occupations")
    support = frame.occupation_code.tolist()
    quintiles = pd.to_numeric(frame.beta_quintile, errors="raise").astype(int).to_numpy()
    webb_z = pd.to_numeric(frame.webb_z, errors="raise").to_numpy(float)
    if not set(np.unique(quintiles)).issubset({1, 2, 3, 4, 5}):
        raise RuntimeError("rebuilt membership has invalid quintiles")
    groups = historical["historical_setup"]["groups"]
    months = list(historical["months"])
    young, older = CELLS.panel_for_ages(cells, support, months, (22, 25), (26, 65))
    exists = (young.sum(axis=1) > 0) & (older.sum(axis=1) > 0)
    if not np.all(exists):
        raise RuntimeError("rebuilt treatment contains nonexistent fixed effects")
    return {
        "treatment_contract": "rebuilt_corrected_preperiod_weight",
        "support": support,
        "quintiles": quintiles,
        "webb_z": webb_z,
        "majors": np.array([groups.get(code, "MISSING") for code in support], object),
        "months": months,
        "names": historical["names"],
        "historical_setup": historical["historical_setup"],
        "membership_sha256": sha256(path),
    }


def dynamic_model(contract, cells, structure, signs, output_dir):
    support = contract["support"]
    months = contract["months"]
    young, older = CELLS.panel_for_ages(cells, support, months, (22, 25), (26, 65))
    x, labels, target_indices, event_bins, month_bins = build_dynamic_regressors(
        contract["quintiles"], contract["webb_z"], months,
    )
    fit, influence, details = fit_absorbed(young, older, x, contract["majors"], structure)
    covariance = influence.T @ influence
    expected_se = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    if not np.allclose(expected_se, fit.standard_error, rtol=1e-7, atol=1e-10):
        raise RuntimeError("stored influence covariance does not reproduce fitted cluster SE")
    shifts = signs @ influence
    target_shifts = shifts[:, target_indices]
    target_se = expected_se[target_indices]
    simultaneous_all = quantile(np.max(np.abs(target_shifts / target_se[None, :]), axis=1), .95)
    q5_indices = [labels.index("Q5_x_{}".format(value)) for value in event_bins]
    q5_shifts = shifts[:, q5_indices]
    q5_se = expected_se[q5_indices]
    simultaneous_q5 = quantile(np.max(np.abs(q5_shifts / q5_se[None, :]), axis=1), .95)
    target_rows, q5_rows = [], []
    for target in target_indices:
        label = labels[target]
        event_bin = label.rsplit("_", 1)[1]
        q = int(label[1])
        summary, _ = bootstrap_scalar(float(fit.beta[target]), influence[:, target], signs)
        target_rows.append({
            "analysis_status": LABEL,
            "treatment_contract": contract["treatment_contract"],
            "structure": structure,
            "event_bin": event_bin,
            "quintile": q,
            "reference_bin": REFERENCE_BIN,
            "transition_month_excluded": True,
            "observed_month_count_in_bin": int(np.sum(month_bins == event_bin)),
            "simultaneous_all_targets_ci_lower": float(fit.beta[target] - simultaneous_all * expected_se[target]),
            "simultaneous_all_targets_ci_upper": float(fit.beta[target] + simultaneous_all * expected_se[target]),
            **summary,
        })
        if q == 5:
            q5_rows.append({
                **target_rows[-1],
                "simultaneous_q5_ci_lower": float(fit.beta[target] - simultaneous_q5 * expected_se[target]),
                "simultaneous_q5_ci_upper": float(fit.beta[target] + simultaneous_q5 * expected_se[target]),
            })

    # Store the exact joint target covariance and occupation influence representation.
    target_labels = [labels[index] for index in target_indices]
    target_cov = covariance[np.ix_(target_indices, target_indices)]
    covariance_rows = []
    for left_index, left in enumerate(target_labels):
        for right_index, right in enumerate(target_labels):
            covariance_rows.append({
                "treatment_contract": contract["treatment_contract"],
                "structure": structure,
                "row_target": left,
                "column_target": right,
                "occupation_cluster_covariance": float(target_cov[left_index, right_index]),
            })
    influence_rows = []
    for occupation_index, code in enumerate(support):
        row = {
            "treatment_contract": contract["treatment_contract"],
            "structure": structure,
            "occupation_code": code,
            "occupation_name": contract["names"].get(code, code),
            "SOC2": contract["majors"][occupation_index],
        }
        for target, label in zip(target_indices, target_labels):
            row[label] = float(influence[occupation_index, target])
        influence_rows.append(row)
    suffix = "{}_{}".format(contract["treatment_contract"], structure)
    write_csv(output_dir / "TARGET_COVARIANCE_{}.csv".format(suffix), covariance_rows)
    write_csv(output_dir / "TARGET_INFLUENCE_{}.csv".format(suffix), influence_rows)

    # Pretrend joint test and an anchored-at-reference linear slope diagnostic.
    pre_positions = [index for index, value in enumerate(event_bins) if value < REFERENCE_BIN]
    pre_indices = [q5_indices[index] for index in pre_positions]
    pre_beta = fit.beta[pre_indices]
    pre_influence = influence[:, pre_indices]
    pre_shifts = signs @ pre_influence
    pre_se = np.sqrt(np.maximum(np.diag(pre_influence.T @ pre_influence), 0.0))
    simultaneous_pre = quantile(np.max(np.abs(pre_shifts / pre_se[None, :]), axis=1), .95)
    joint = joint_zero(pre_beta, pre_influence, signs)
    time_to_reference = np.arange(-len(pre_indices), 0, dtype=float)
    slope_weights = time_to_reference / float(time_to_reference @ time_to_reference)
    slope_estimate = float(slope_weights @ pre_beta)
    slope_influence = pre_influence @ slope_weights
    slope_summary, _ = bootstrap_scalar(slope_estimate, slope_influence, signs)
    pretrend_rows = [{
        "analysis_status": LABEL,
        "treatment_contract": contract["treatment_contract"],
        "structure": structure,
        "test": "all_pre_Q5_coefficients_jointly_zero",
        "reference_bin": REFERENCE_BIN,
        "pre_bins": len(pre_indices),
        "simultaneous_pre_critical": simultaneous_pre,
        "maximum_absolute_pre_coefficient": float(np.max(np.abs(pre_beta))),
        "minimum_pointwise_MDE80": float(MDE_FACTOR * np.min(pre_se)),
        "median_pointwise_MDE80": float(MDE_FACTOR * np.median(pre_se)),
        "maximum_pointwise_MDE80": float(MDE_FACTOR * np.max(pre_se)),
        **joint,
    }, {
        "analysis_status": LABEL,
        "treatment_contract": contract["treatment_contract"],
        "structure": structure,
        "test": "linear_pretrend_slope_anchored_at_reference",
        "reference_bin": REFERENCE_BIN,
        "pre_bins": len(pre_indices),
        "slope_unit": "log_points_per_quarter",
        "slope_weight_rule": "t/sum(t^2), t=-K,...,-1; reference coefficient fixed at zero",
        **slope_summary,
    }]

    # Declared dynamic post functional: equal observed-calendar-month weights.
    post_positions = [index for index, value in enumerate(event_bins) if value >= "2023Q1"]
    post_q5_indices = [q5_indices[index] for index in post_positions]
    counts = np.array([np.sum(month_bins == event_bins[index]) for index in post_positions], float)
    functional_weights = counts / counts.sum()
    functional_estimate = float(functional_weights @ fit.beta[post_q5_indices])
    functional_influence = influence[:, post_q5_indices] @ functional_weights
    functional_summary, functional_draws = bootstrap_scalar(functional_estimate, functional_influence, signs)
    weight_rows = [{
        "treatment_contract": contract["treatment_contract"],
        "structure": structure,
        "event_bin": event_bins[position],
        "observed_post_months": int(count),
        "functional_weight": float(weight),
    } for position, count, weight in zip(post_positions, counts, functional_weights)]
    write_csv(output_dir / "POST_FUNCTIONAL_WEIGHTS_{}.csv".format(suffix), weight_rows)

    return {
        "contract": contract,
        "structure": structure,
        "fit": fit,
        "influence": influence,
        "details": details,
        "young": young,
        "older": older,
        "signs": signs,
        "labels": labels,
        "target_indices": target_indices,
        "event_bins": event_bins,
        "month_bins": month_bins,
        "target_rows": target_rows,
        "q5_rows": q5_rows,
        "pretrend_rows": pretrend_rows,
        "functional": {
            "estimate": functional_estimate,
            "influence": functional_influence,
            "draws": functional_draws,
            "weights": functional_weights,
            "post_q5_indices": post_q5_indices,
            **functional_summary,
        },
        "parameter_count": len(labels),
        "target_covariance_rank": int(np.linalg.matrix_rank(target_cov)),
        "target_covariance_dimension": int(target_cov.shape[0]),
        "simultaneous_all_critical": simultaneous_all,
        "simultaneous_q5_critical": simultaneous_q5,
        "covariance_file": "TARGET_COVARIANCE_{}.csv".format(suffix),
        "influence_file": "TARGET_INFLUENCE_{}.csv".format(suffix),
    }


def fit_static(contract, cells, structure, months=None, onset="2023-01",
               seasonal="none"):
    support = contract["support"]
    months = list(contract["months"] if months is None else months)
    young, older = CELLS.panel_for_ages(cells, support, months, (22, 25), (26, 65))
    x, labels = build_static_regressors(
        contract["quintiles"], contract["webb_z"], months, onset,
        quintile_month_of_year=seasonal == "quintile_month_of_year",
    )
    if seasonal == "occupation_month_of_year":
        fit, influence, details = fit_seasonal(
            young, older, x, contract["majors"], months, structure,
        )
    else:
        fit, influence, details = fit_absorbed(
            young, older, x, contract["majors"], structure,
        )
    target = labels.index("Q5_x_post_from_{}".format(onset))
    return {
        "fit": fit, "influence": influence, "details": details,
        "target": target, "labels": labels, "months": months,
        "young": young, "older": older,
    }


def dynamic_static_mapping(dynamic, cells):
    contract = dynamic["contract"]
    structure = dynamic["structure"]
    static = fit_static(contract, cells, structure)
    signs = dynamic["signs"]
    target = static["target"]
    static_estimate = float(static["fit"].beta[target])
    static_summary, static_draws = bootstrap_scalar(
        static_estimate, static["influence"][:, target], signs,
    )
    functional = dynamic["functional"]
    delta = functional["estimate"] - static_estimate
    delta_influence = functional["influence"] - static["influence"][:, target]
    delta_summary, delta_draws = bootstrap_scalar(delta, delta_influence, signs)
    if (contract["treatment_contract"] == "historical_production_full_static_weight"
            and structure == "unconditioned"
            and not np.isclose(static_estimate, EXPECTED_CORRECTED_BASELINE, atol=1e-8, rtol=0)):
        raise RuntimeError("corrected static mapping model failed baseline reproduction")
    return {
        "row": {
            "analysis_status": LABEL,
            "treatment_contract": contract["treatment_contract"],
            "structure": structure,
            "static_estimand": "grouped-binomial Q5-vs-Q1 post-from-2023-01 coefficient",
            "dynamic_functional": "observed-calendar-month-weighted average of post-2022 quarterly Q5-vs-Q1 coefficients",
            "mapping_rule": "separate nonlinear estimands; equality is not assumed or imposed",
            "static_coefficient": static_estimate,
            "static_occupation_cluster_se": static_summary["occupation_cluster_se"],
            "static_ci_lower": static_summary["ci_lower"],
            "static_ci_upper": static_summary["ci_upper"],
            "dynamic_functional_coefficient": functional["estimate"],
            "dynamic_functional_occupation_cluster_se": functional["occupation_cluster_se"],
            "dynamic_functional_ci_lower": functional["ci_lower"],
            "dynamic_functional_ci_upper": functional["ci_upper"],
            "dynamic_minus_static": delta,
            "paired_se": delta_summary["occupation_cluster_se"],
            "paired_ci_lower": delta_summary["ci_lower"],
            "paired_ci_upper": delta_summary["ci_upper"],
            "paired_p_value": delta_summary["wild_score_p_value"],
            "paired_MDE80": delta_summary["normal_theory_MDE80"],
            "common_occupation_multipliers": True,
            "post_observed_months_in_functional": int(sum(
                month >= "2023-01" for month in contract["months"]
            )),
        },
        "static": static,
        "static_draws": static_draws,
        "delta_draws": delta_draws,
    }


def run_grid(contract, cells, structures, signs, kind):
    fits = []
    failures = []
    if kind == "onset":
        variants = [(value, contract["months"], value) for value in ONSET_DATES]
    elif kind == "endpoint":
        full = contract["months"]
        variants = [
            ("through_2024_12", [m for m in full if m <= "2024-12"], "2023-01"),
            ("through_2025_09", [m for m in full if m <= "2025-09"], "2023-01"),
            ("through_2025_12_actual_gap", [m for m in full if m <= "2025-12"], "2023-01"),
            ("full_excluding_September_and_November_2025", [m for m in full if m not in {"2025-09", "2025-11"}], "2023-01"),
            ("full_through_2026_07_excluding_late_2025", [m for m in full if m not in {"2025-11", "2025-12"}], "2023-01"),
            ("full_through_2026_07", full, "2023-01"),
            ("post_2020_coding_stable_through_2026_07", [m for m in full if m >= "2020-01"], "2023-01"),
        ]
    else:
        raise ValueError(kind)
    for structure in structures:
        local = []
        for label, months, onset in variants:
            progress("{}_variant_started".format(kind),
                     treatment_contract=contract["treatment_contract"],
                     structure=structure, variant=label)
            try:
                result = fit_static(contract, cells, structure, months=months, onset=onset)
                target = result["target"]
                estimate = float(result["fit"].beta[target])
                summary, centered = bootstrap_scalar(
                    estimate, result["influence"][:, target], signs,
                )
                local.append({
                    "label": label, "months": months, "onset": onset,
                    "result": result, "estimate": estimate, "summary": summary,
                    "centered": centered, "status": "PASS",
                })
                progress("{}_variant_finished".format(kind),
                         treatment_contract=contract["treatment_contract"],
                         structure=structure, variant=label, status="PASS")
            except Exception as error:
                failure = {
                    "analysis_status": LABEL,
                    "treatment_contract": contract["treatment_contract"],
                    "structure": structure,
                    "grid": kind,
                    "variant": label,
                    "onset": onset,
                    "first_month": months[0],
                    "last_month": months[-1],
                    "months": len(months),
                    "status": "FAILED_REPORTED_NOT_SUBSTITUTED",
                    "error_type": type(error).__name__,
                    "message": str(error),
                }
                failures.append(failure)
                fits.append(failure)
                progress("{}_variant_finished".format(kind),
                         treatment_contract=contract["treatment_contract"],
                         structure=structure, variant=label,
                         status="FAILED_REPORTED_NOT_SUBSTITUTED",
                         error_type=type(error).__name__)
        if not local:
            continue
        matrix = np.column_stack([item["centered"] for item in local])
        ses = np.array([item["summary"]["occupation_cluster_se"] for item in local])
        simultaneous = quantile(np.max(np.abs(matrix / ses[None, :]), axis=1), .95)
        reference_label = "2023-01" if kind == "onset" else "full_through_2026_07"
        reference_item = next(
            (item for item in local if item["label"] == reference_label), None,
        )
        for item, se in zip(local, ses):
            difference = ""
            paired = {
                "occupation_cluster_se": "", "ci_lower": "", "ci_upper": "",
                "wild_score_p_value": "", "normal_theory_MDE80": "",
            }
            if reference_item is not None:
                difference = item["estimate"] - reference_item["estimate"]
                difference_influence = (
                    item["result"]["influence"][:, item["result"]["target"]] -
                    reference_item["result"]["influence"][:, reference_item["result"]["target"]]
                )
            if reference_item is not None and np.allclose(
                    difference_influence, 0, atol=1e-16, rtol=0):
                paired = {
                    "coefficient": 0.0, "occupation_cluster_se": 0.0,
                    "ci_lower": 0.0, "ci_upper": 0.0, "wild_score_p_value": 1.0,
                    "normal_theory_MDE80": 0.0,
                }
            elif reference_item is not None:
                paired, _ = bootstrap_scalar(difference, difference_influence, signs)
            row = {
                "analysis_status": LABEL,
                "treatment_contract": contract["treatment_contract"],
                "structure": structure,
                "grid": kind,
                "variant": item["label"],
                "onset": item["onset"],
                "status": "PASS",
                "first_month": item["months"][0],
                "last_month": item["months"][-1],
                "months": len(item["months"]),
                "transition_month_excluded": TRANSITION not in item["months"],
                "october_2025_present": "2025-10" in item["months"],
                "late_2025_Nov_Dec_present": any(m in item["months"] for m in ("2025-11", "2025-12")),
                "simultaneous_grid_critical": simultaneous,
                "simultaneous_ci_lower": float(item["estimate"] - simultaneous * se),
                "simultaneous_ci_upper": float(item["estimate"] + simultaneous * se),
                "paired_comparison_reference": reference_label,
                "difference_vs_reference": difference,
                "paired_se_vs_reference": paired["occupation_cluster_se"],
                "paired_ci_lower_vs_reference": paired["ci_lower"],
                "paired_ci_upper_vs_reference": paired["ci_upper"],
                "paired_p_value_vs_reference": paired["wild_score_p_value"],
                "paired_MDE80_vs_reference": paired["normal_theory_MDE80"],
                "common_occupation_multipliers_for_pair": True,
                **item["summary"],
            }
            fits.append(row)
    return fits, failures


def seasonality_rows(contract, cells, structures, signs, mapping_by_structure):
    rows = []
    for structure in structures:
        baseline = mapping_by_structure[structure]["static"]
        specifications = (
            ("quintile_by_month_of_year", "quintile_month_of_year"),
            ("occupation_by_month_of_year", "occupation_month_of_year"),
        )
        for specification, mode in specifications:
          try:
            seasonal = fit_static(contract, cells, structure, seasonal=mode)
            target = seasonal["target"]
            estimate = float(seasonal["fit"].beta[target])
            summary, centered = bootstrap_scalar(estimate, seasonal["influence"][:, target], signs)
            base_target = baseline["target"]
            delta = estimate - float(baseline["fit"].beta[base_target])
            delta_influence = seasonal["influence"][:, target] - baseline["influence"][:, base_target]
            delta_summary, _ = bootstrap_scalar(delta, delta_influence, signs)
            rows.append({
                "analysis_status": LABEL,
                "treatment_contract": contract["treatment_contract"],
                "structure": structure,
                "specification": specification + "_plus_declared_calendar_FE",
                "status": "PASS",
                "target_preserved": "Q5-vs-Q1 post-from-2023-01 grouped-binomial coefficient",
                "parameter_burden_slope_parameters": len(seasonal["labels"]),
                "occupation_season_FE_groups": seasonal["details"].get("first_fe_count", ""),
                "additional_occupation_season_FE_relative_to_occupation_FE": seasonal["details"].get("additional_occupation_season_FE_relative_to_occupation_FE", 0),
                "additional_quintile_month_of_year_slopes": 44 if mode == "quintile_month_of_year" else 0,
                "second_FE_groups": seasonal["details"]["second_fe_count"],
                **summary,
                "seasonal_minus_nonseasonal": delta,
                "paired_se": delta_summary["occupation_cluster_se"],
                "paired_ci_lower": delta_summary["ci_lower"],
                "paired_ci_upper": delta_summary["ci_upper"],
                "paired_p_value": delta_summary["wild_score_p_value"],
                "common_occupation_multipliers": True,
            })
          except Exception as error:
            rows.append({
                "analysis_status": LABEL,
                "treatment_contract": contract["treatment_contract"],
                "structure": structure,
                "specification": specification + "_plus_declared_calendar_FE",
                "status": "FAILED_REPORTED_NOT_SUBSTITUTED",
                "error_type": type(error).__name__,
                "message": str(error),
                "planned_additional_FE_upper_bound": (
                    len(contract["support"]) * 11 if mode == "occupation_month_of_year" else 0
                ),
                "planned_additional_slopes": 44 if mode == "quintile_month_of_year" else 0,
            })
    return rows


def rambachan_roth_decision(dynamic_models, output_dir):
    # The official method is not reimplemented ad hoc. We expose all required
    # inputs and let the SCC wrapper call the official HonestDiD package if it is
    # available. This file records the substantive applicability determination.
    rows = []
    for model in dynamic_models:
        event_bins = model["event_bins"]
        q5_indices = [model["labels"].index("Q5_x_{}".format(value)) for value in event_bins]
        covariance = model["influence"][:, q5_indices].T @ model["influence"][:, q5_indices]
        post = [index for index, value in enumerate(event_bins) if value >= "2023Q1"]
        pre = [index for index, value in enumerate(event_bins) if value < REFERENCE_BIN]
        valid = (
            len(pre) > 0 and len(post) > 0 and
            np.all(np.isfinite(covariance)) and
            np.linalg.matrix_rank(covariance) == len(event_bins) and
            REFERENCE_BIN not in event_bins
        )
        suffix = "{}_{}".format(model["contract"]["treatment_contract"], model["structure"])
        vector_rows = []
        post_month_counts = np.array([
            np.sum(model["month_bins"] == event_bins[index]) for index in post
        ], float)
        post_weights = post_month_counts / post_month_counts.sum()
        for index, event_bin in enumerate(event_bins):
            vector_rows.append({
                "event_bin": event_bin,
                "coefficient_q5_vs_q1": float(model["fit"].beta[q5_indices[index]]),
                "is_pre": index in pre,
                "is_post": index in post,
                "l_vec_post_functional_weight": (
                    float(post_weights[post.index(index)]) if index in post else 0.0
                ),
                "reference_bin_omitted": REFERENCE_BIN,
            })
        write_csv(output_dir / "HONESTDID_EVENT_VECTOR_{}.csv".format(suffix), vector_rows)
        cov_rows = []
        for i, left in enumerate(event_bins):
            for j, right in enumerate(event_bins):
                cov_rows.append({
                    "row_event_bin": left, "column_event_bin": right,
                    "covariance": float(covariance[i, j]),
                })
        write_csv(output_dir / "HONESTDID_COVARIANCE_{}.csv".format(suffix), cov_rows)
        rows.append({
            "analysis_status": LABEL,
            "treatment_contract": model["contract"]["treatment_contract"],
            "structure": model["structure"],
            "event_vector_valid": bool(valid),
            "event_coefficients": len(event_bins),
            "pre_coefficients": len(pre),
            "post_coefficients": len(post),
            "reference_bin": REFERENCE_BIN,
            "reference_bin_omitted": REFERENCE_BIN not in event_bins,
            "covariance_dimension": len(event_bins),
            "covariance_rank": int(np.linalg.matrix_rank(covariance)),
            "declared_linear_post_functional": "observed-calendar-month-weighted average",
            "weights_sum": float(post_weights.sum()),
            "official_implementation_required": True,
            "ad_hoc_python_reimplementation_prohibited": True,
            "execution_status": "READY_FOR_OFFICIAL_HONESTDID" if valid else "PRINCIPLED_NON_ADOPTION_INVALID_INPUT",
            "interpretation_limit": "companion dynamic estimand; not the nonlinear static coefficient",
        })
    return rows


def run(args):
    args.output_dir.mkdir(parents=True, exist_ok=True)
    progress("march_repair_preflight_started")
    repair_receipt = march_repair_preflight(args)
    write_json(args.output_dir / "MARCH_REPAIR_POLICY_RECEIPT.json", repair_receipt)
    progress("march_repair_preflight_passed")
    progress("corrected_cell_build_started")
    cells, _, cell_receipt = CELLS.build_exact_age_cells(args)
    progress("corrected_cell_build_finished", aggregate_rows=len(cells))
    historical = setup_historical(args, cells)
    contracts = [historical]
    rebuilt = setup_rebuilt(args.rebuilt_membership, historical, cells)
    if rebuilt is not None:
        contracts.append(rebuilt)

    dynamic_models = []
    target_rows, q5_rows, pretrend_rows, mapping_rows = [], [], [], []
    onset_rows, endpoint_rows, seasonal = [], [], []
    model_failures = []
    structures = ("unconditioned", "SOC2_x_calendar_month")
    contract_receipts = []
    for contract_index, contract in enumerate(contracts):
        signs = np.random.default_rng(SEED + contract_index).choice(
            np.array([-1.0, 1.0]), size=(DRAWS, len(contract["support"])),
        )
        mappings = {}
        for structure in structures:
            progress("dynamic_model_started", treatment_contract=contract["treatment_contract"],
                     structure=structure)
            try:
                dynamic = dynamic_model(contract, cells, structure, signs, args.output_dir)
            except Exception as error:
                failure = {
                    "analysis_status": LABEL,
                    "component": "quarterly_dynamic_core",
                    "treatment_contract": contract["treatment_contract"],
                    "structure": structure,
                    "status": "FAILED_REPORTED_NOT_SUBSTITUTED",
                    "error_type": type(error).__name__,
                    "message": str(error),
                }
                model_failures.append(failure)
                progress("dynamic_model_finished",
                         treatment_contract=contract["treatment_contract"],
                         structure=structure,
                         status="FAILED_REPORTED_NOT_SUBSTITUTED",
                         error_type=type(error).__name__)
                continue
            progress("dynamic_model_finished", treatment_contract=contract["treatment_contract"],
                     structure=structure, converged=bool(dynamic["fit"].converged),
                     iterations=int(dynamic["fit"].iterations))
            dynamic_models.append(dynamic)
            target_rows.extend(dynamic["target_rows"])
            q5_rows.extend(dynamic["q5_rows"])
            pretrend_rows.extend(dynamic["pretrend_rows"])
            try:
                mapping = dynamic_static_mapping(dynamic, cells)
            except Exception as error:
                failure = {
                    "analysis_status": LABEL,
                    "component": "static_dynamic_mapping",
                    "treatment_contract": contract["treatment_contract"],
                    "structure": structure,
                    "status": "FAILED_REPORTED_NOT_SUBSTITUTED",
                    "error_type": type(error).__name__,
                    "message": str(error),
                }
                model_failures.append(failure)
                continue
            mappings[structure] = mapping
            mapping_rows.append(mapping["row"])
        progress("onset_grid_started", treatment_contract=contract["treatment_contract"])
        onset_result, onset_failures = run_grid(contract, cells, structures, signs, "onset")
        onset_rows.extend(onset_result)
        model_failures.extend(onset_failures)
        progress("onset_grid_finished", treatment_contract=contract["treatment_contract"])
        progress("endpoint_grid_started", treatment_contract=contract["treatment_contract"])
        endpoint_result, endpoint_failures = run_grid(
            contract, cells, structures, signs, "endpoint",
        )
        endpoint_rows.extend(endpoint_result)
        model_failures.extend(endpoint_failures)
        progress("endpoint_grid_finished", treatment_contract=contract["treatment_contract"])
        progress("seasonality_models_started", treatment_contract=contract["treatment_contract"])
        seasonal_structures = tuple(value for value in structures if value in mappings)
        seasonal.extend(seasonality_rows(
            contract, cells, seasonal_structures, signs, mappings,
        ))
        model_failures.extend([
            row for row in seasonal
            if row.get("treatment_contract") == contract["treatment_contract"]
            and row.get("status") == "FAILED_REPORTED_NOT_SUBSTITUTED"
        ])
        progress("seasonality_models_finished", treatment_contract=contract["treatment_contract"])
        contract_receipts.append({
            "treatment_contract": contract["treatment_contract"],
            "support_occupations": len(contract["support"]),
            "support_hash_sha256": support_hash(contract["support"]),
            "membership_sha256": contract.get("membership_sha256", "historical_contract_rebuilt_in_memory"),
            "quintile_counts": {str(q): int(np.sum(contract["quintiles"] == q)) for q in range(1, 6)},
        })

    historical_core = {
        model["structure"] for model in dynamic_models
        if model["contract"]["treatment_contract"] == "historical_production_full_static_weight"
    }
    if historical_core != set(structures):
        write_json(args.output_dir / "MODEL_FAILURES.json", model_failures)
        raise RuntimeError(
            "historical quarterly core incomplete; failures recorded without substitution"
        )

    write_csv(args.output_dir / "DYNAMIC_TARGET_PROFILE.csv", target_rows)
    write_csv(args.output_dir / "DYNAMIC_Q5_Q1_PROFILE.csv", q5_rows)
    write_csv(args.output_dir / "PRETREND_TESTS.csv", pretrend_rows)
    write_csv(args.output_dir / "STATIC_DYNAMIC_MAPPING.csv", mapping_rows)
    write_csv(args.output_dir / "ONSET_DATE_SENSITIVITY.csv", onset_rows)
    write_csv(args.output_dir / "ENDPOINT_SENSITIVITY.csv", endpoint_rows)
    write_csv(args.output_dir / "SEASONALITY_SENSITIVITY.csv", seasonal)
    write_json(args.output_dir / "MODEL_FAILURES.json", model_failures)
    rr_rows = rambachan_roth_decision(dynamic_models, args.output_dir)
    write_csv(args.output_dir / "RAMBACHAN_ROTH_APPLICABILITY.csv", rr_rows)

    output_hashes = {
        path.name: sha256(path) for path in sorted(args.output_dir.iterdir())
        if path.is_file() and path.name != "EXECUTION_RECEIPT.json"
    }
    receipt = {
        "record": "YAX R3 DYN-01--DYN-04 corrected dynamics",
        "analysis_status": LABEL,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "script_sha256": sha256(pathlib.Path(__file__)),
        "march_repair_policy_receipt": repair_receipt,
        "cell_build_receipt": cell_receipt,
        "calendar": {
            "corrected_months": len(historical["months"]),
            "first_month": historical["months"][0],
            "last_month": historical["months"][-1],
            "transition_month": TRANSITION,
            "transition_excluded": TRANSITION not in historical["months"],
            "reference_bin": REFERENCE_BIN,
            "reference_observed_months": [m for m in historical["months"] if quarter(m) == REFERENCE_BIN],
            "october_2025_missing": "2025-10" not in historical["months"],
            "october_2025_interpolated": False,
        },
        "dynamic_specification": {
            "aggregation": "calendar quarter",
            "reason": "monthly Q2-Q5 plus Webb interactions would require 565 slope parameters; quarter bins retain the estimand and lower instability",
            "quintile_interactions": [2, 3, 4, 5],
            "omitted_quintile": 1,
            "computerization_control": "Webb software z interacted with every nonreference quarter",
            "structures": list(structures),
            "bootstrap_draws": DRAWS,
            "seed_by_contract": {value["treatment_contract"]: SEED + index for index, value in enumerate(contracts)},
            "common_occupation_Rademacher_multipliers_within_contract": True,
            "joint_covariance_and_influence_stored": True,
            "SCC_linear_algebra_threads_requested": int(os.environ.get("OPENBLAS_NUM_THREADS", "0")),
        },
        "treatment_contracts": contract_receipts,
        "model_receipts": [{
            "treatment_contract": model["contract"]["treatment_contract"],
            "structure": model["structure"],
            "slope_parameters": model["parameter_count"],
            "target_parameters": len(model["target_indices"]),
            "event_bins": len(model["event_bins"]),
            "target_covariance_rank": model["target_covariance_rank"],
            "target_covariance_dimension": model["target_covariance_dimension"],
            "second_FE_groups": model["details"]["second_fe_count"],
            "converged": bool(model["fit"].converged),
            "iterations": int(model["fit"].iterations),
            "covariance_file": model["covariance_file"],
            "influence_file": model["influence_file"],
        } for model in dynamic_models],
        "rambachan_roth": rr_rows,
        "model_failures": model_failures,
        "output_hashes": output_hashes,
    }
    write_json(args.output_dir / "EXECUTION_RECEIPT.json", receipt)
    print(json.dumps({
        "status": "PASS_R3_DYN_01_THROUGH_04",
        "contracts": [value["treatment_contract"] for value in contracts],
        "dynamic_models": len(dynamic_models),
        "onset_rows": len(onset_rows),
        "endpoint_rows": len(endpoint_rows),
        "seasonality_rows": len(seasonal),
    }, indent=2, sort_keys=True))


def parser():
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--microdata", type=pathlib.Path, required=True)
    value.add_argument("--repair-microdata", type=pathlib.Path, required=True)
    value.add_argument("--preperiod-cells", type=pathlib.Path, required=True)
    value.add_argument("--lookup", type=pathlib.Path, default=ROOT / "yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv")
    value.add_argument("--computerization", type=pathlib.Path, default=ROOT / "yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv")
    value.add_argument("--rule-b-values", type=pathlib.Path, default=ROOT / "yax/measurement/RULE_B_VALUES_CENSUS2018.csv")
    value.add_argument("--bridge", type=pathlib.Path, default=ROOT / "yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv")
    value.add_argument("--first-access-receipt", type=pathlib.Path, default=ROOT / "yax/analysis/FIRST_OUTCOME_ACCESS_RECEIPT.json")
    value.add_argument("--rebuilt-membership", type=pathlib.Path)
    value.add_argument("--output-dir", type=pathlib.Path, required=True)
    return value


if __name__ == "__main__":
    run(parser().parse_args())
