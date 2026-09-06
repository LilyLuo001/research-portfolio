#!/usr/bin/env python3
"""Execute the predeclared CHAR-03/CHAR-04 heterogeneity audit.

POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1.
Restricted CPS microdata remain on SCC; only aggregate results are written.
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
import traceback
from datetime import datetime, timezone

import numpy as np
import pandas as pd


LABEL = "POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1"
DRAWS = 9_999
SEED = 2026090551
Z975 = 1.959963984540054
Z80 = 0.8416212335729143
EXPECTED_BASELINE = -0.1321094508
PREDECLARE_COMMIT = "3d30996933a848872bd71795d87618b0f12e27c9"
MARCH_REPLACEMENTS = {f"{year}-03" for year in range(2017, 2022)}
EXPECTED_INPUT_HASHES = {
    "microdata": "3fe42477e6f2ce401e85123f0e278e758595c1c4071a8743f243a92752db38c9",
    "repair_microdata": "a4ae2ef06d66a0d47359ccceffff9a15843ac501a9f25f9a05aa8fdca9c4f911",
    "bridge": "0bd2f63c72e24bed2cc1cb414395c3cbddf7c00011e47ec1c1de6ae534fd1dcc",
    "membership": "c76eb85956e4a413e130bab53fe8c50616cf6d7a02c81c266ec369879dd56bc1",
}


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


def support_hash(values) -> str:
    payload = "".join(f"{value}\n" for value in sorted(values))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_json(path: pathlib.Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: pathlib.Path, rows: list[dict]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty output {path}")
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def quantile(values: np.ndarray, q: float) -> float:
    try:
        return float(np.quantile(values, q, method="higher"))
    except TypeError:
        return float(np.quantile(values, q, interpolation="higher"))


def chi_square_survival(value: float, degrees_of_freedom: int) -> float:
    """Chi-square upper-tail probability without an optional SciPy dependency.

    The age-equality test has at most three degrees of freedom.  The formulas
    below evaluate the regularized upper incomplete gamma function by its
    exact half-integer/integer recurrence, avoiding a silent change to the
    registered test on SCC installations whose minimal SciPy build omits
    ``scipy.stats``.
    """
    if value < 0 or degrees_of_freedom < 1:
        raise ValueError("chi-square arguments must be nonnegative with positive df")
    x = value / 2.0
    if degrees_of_freedom % 2 == 0:
        terms = degrees_of_freedom // 2
        return float(math.exp(-x) * sum(x ** j / math.factorial(j) for j in range(terms)))
    steps = (degrees_of_freedom - 1) // 2
    result = math.erfc(math.sqrt(x))
    shape = 0.5
    for _ in range(steps):
        result += math.exp(-x) * x ** shape / math.gamma(shape + 1.0)
        shape += 1.0
    return float(min(max(result, 0.0), 1.0))


def month_string(frame: pd.DataFrame) -> pd.Series:
    return frame.YEAR.astype(int).astype(str) + "-" + frame.MONTH.astype(int).astype(str).str.zfill(2)


def industry_group(code: pd.Series) -> pd.Series:
    value = pd.to_numeric(code, errors="coerce")
    conditions = [
        value.between(10, 32), value.between(40, 50), value.eq(60),
        value.between(100, 392), value.between(400, 472), value.between(500, 571),
        value.between(580, 691), value.between(700, 712), value.between(721, 760),
        value.between(761, 791), value.between(800, 810), value.between(812, 893),
        value.between(900, 932),
    ]
    labels = [
        "agriculture", "mining", "construction", "manufacturing",
        "transport_communications_utilities", "wholesale_trade", "retail_trade",
        "finance_insurance_real_estate", "business_repair_services",
        "personal_lodging_services", "entertainment_recreation",
        "professional_related_services", "public_administration",
    ]
    return pd.Series(np.select(conditions, labels, default="__invalid__"), index=code.index)


def education_group(code: pd.Series) -> pd.Series:
    value = pd.to_numeric(code, errors="coerce")
    ba = value.eq(111) | value.between(120, 125)
    nonba = value.between(2, 110)
    return pd.Series(np.select([ba, nonba], ["BA_plus", "non_BA"], default="__invalid__"), index=code.index)


def school_group(code: pd.Series) -> pd.Series:
    value = pd.to_numeric(code, errors="coerce")
    return pd.Series(
        np.select([value.isin([1, 2, 3, 4]), value.eq(5)], ["enrolled", "not_enrolled"], default="__invalid__"),
        index=code.index,
    )


def validate_inputs(args) -> dict:
    paths = {
        "microdata": args.microdata,
        "repair_microdata": args.repair_microdata,
        "bridge": args.bridge,
        "membership": args.membership,
    }
    observed = {name: sha256(path) for name, path in paths.items()}
    mismatch = {
        name: {"observed": observed[name], "expected": EXPECTED_INPUT_HASHES[name]}
        for name in observed if observed[name] != EXPECTED_INPUT_HASHES[name]
    }
    if mismatch:
        raise RuntimeError(f"input authentication failed: {mismatch}")
    return observed


def load_contract(args):
    membership = pd.read_csv(args.membership, dtype={"occupation_code": str})
    membership["occupation_code"] = membership.occupation_code.str.zfill(4)
    membership = membership.sort_values("occupation_code").reset_index(drop=True)
    if len(membership) != 468 or membership.occupation_code.nunique() != 468:
        raise RuntimeError("BASE-03 membership is not the expected 468-code contract")
    if support_hash(membership.occupation_code) != "11ec58ab1004cd83d62c57785f6c0dd3ee5a8abf08b7f71a3b664e91ded8333b":
        raise RuntimeError("BASE-03 support hash changed")
    q_map = membership.set_index("occupation_code").beta_quintile.astype(int).to_dict()
    webb_map = membership.set_index("occupation_code").webb_z.astype(float).to_dict()
    return membership, q_map, webb_map


def build_aggregates(args, support: set[str]):
    bridge = pd.read_csv(args.bridge, dtype={"census_2010": str, "census_2018": str})
    bridge["census_2010"] = bridge.census_2010.str.zfill(4)
    bridge["census_2018"] = bridge.census_2018.str.zfill(4)
    bridge["bridge_weight"] = pd.to_numeric(bridge.bridge_weight, errors="raise")
    route_mass = bridge.groupby("census_2010").bridge_weight.sum()
    if float(np.max(np.abs(route_mass.to_numpy() - 1.0))) > 1e-12:
        raise RuntimeError("bridge route probabilities do not sum to one")

    industry_pieces, education_pieces, age_pieces, composition_pieces = [], [], [], []
    counters = {
        "source_rows_read": 0,
        "wide_march_rows_explicitly_replaced": 0,
        "wide_march_positive_weight_rows_explicitly_replaced": 0,
        "repair_rows_outside_replacement_months_dropped": 0,
        "eligible_source_records_before_routing": 0,
        "routed_descendant_rows_on_support": 0,
        "routed_respondent_equivalents_on_support": 0.0,
        "routed_weighted_stock_on_support": 0.0,
        "invalid_industry_weighted_stock_on_support": 0.0,
        "invalid_education_weighted_stock_on_support": 0.0,
        "invalid_enrollment_weighted_stock_young_on_support": 0.0,
        "early_matched_source_weight": 0.0,
        "early_routed_weight_before_support": 0.0,
        "current_source_weight": 0.0,
        "current_routed_weight_before_support": 0.0,
    }
    usecols = ["YEAR", "MONTH", "AGE", "EMPSTAT", "OCC", "IND1990", "EDUC", "SCHLCOLL", "WTFINL"]
    for path, is_primary in ((args.microdata, True), (args.repair_microdata, False)):
        for chunk in pd.read_csv(path, usecols=usecols, chunksize=400_000):
            counters["source_rows_read"] += len(chunk)
            month = month_string(chunk)
            weight = pd.to_numeric(chunk.WTFINL, errors="coerce")
            if is_primary:
                replaced = month.isin(MARCH_REPLACEMENTS)
                counters["wide_march_rows_explicitly_replaced"] += int(replaced.sum())
                counters["wide_march_positive_weight_rows_explicitly_replaced"] += int((replaced & weight.gt(0)).sum())
            else:
                replaced = ~month.isin(MARCH_REPLACEMENTS)
                counters["repair_rows_outside_replacement_months_dropped"] += int(replaced.sum())
            age = pd.to_numeric(chunk.AGE, errors="coerce")
            employed = pd.to_numeric(chunk.EMPSTAT, errors="coerce").isin([10, 12])
            keep = age.between(22, 65) & employed & np.isfinite(weight) & weight.gt(0) & ~replaced
            chunk = chunk.loc[keep].copy()
            if chunk.empty:
                continue
            counters["eligible_source_records_before_routing"] += len(chunk)
            chunk["month"] = month.loc[chunk.index]
            chunk["age"] = age.loc[chunk.index].astype(int)
            chunk["source_weight"] = weight.loc[chunk.index].astype(float)
            raw_occ = pd.to_numeric(chunk.OCC, errors="coerce")
            valid_occ = raw_occ.notna() & raw_occ.between(0, 9999) & raw_occ.mod(1).eq(0)
            chunk = chunk.loc[valid_occ].copy()
            chunk["source_occ"] = raw_occ.loc[chunk.index].astype(int).map(lambda x: f"{x:04d}")

            early_source = chunk.loc[chunk.YEAR.le(2019)].copy()
            early = early_source.merge(bridge, left_on="source_occ", right_on="census_2010", how="inner", validate="many_to_many")
            counters["early_matched_source_weight"] += float(
                early_source.loc[early_source.source_occ.isin(set(early.source_occ)), "source_weight"].sum()
            )
            early["occ_code"] = early.census_2018
            early["route_weight"] = early.bridge_weight
            early["stock"] = early.source_weight * early.route_weight
            counters["early_routed_weight_before_support"] += float(early.stock.sum())

            current = chunk.loc[chunk.YEAR.ge(2020)].copy()
            current["occ_code"] = current.source_occ
            current["route_weight"] = 1.0
            current["stock"] = current.source_weight
            counters["current_source_weight"] += float(current.source_weight.sum())
            counters["current_routed_weight_before_support"] += float(current.stock.sum())

            routed = pd.concat([early, current], ignore_index=True, sort=False)
            routed = routed.loc[routed.occ_code.isin(support)].copy()
            if routed.empty:
                continue
            routed["industry_group"] = industry_group(routed.IND1990)
            routed["education_group"] = education_group(routed.EDUC)
            routed["school_group"] = school_group(routed.SCHLCOLL)
            routed["age_group"] = np.where(routed.age.between(22, 25), "young", "older")
            routed["respondent_equivalent"] = routed.route_weight
            counters["routed_descendant_rows_on_support"] += len(routed)
            counters["routed_respondent_equivalents_on_support"] += float(routed.route_weight.sum())
            counters["routed_weighted_stock_on_support"] += float(routed.stock.sum())
            counters["invalid_industry_weighted_stock_on_support"] += float(
                routed.loc[routed.industry_group.eq("__invalid__"), "stock"].sum()
            )
            counters["invalid_education_weighted_stock_on_support"] += float(
                routed.loc[routed.education_group.eq("__invalid__"), "stock"].sum()
            )
            counters["invalid_enrollment_weighted_stock_young_on_support"] += float(
                routed.loc[routed.age.between(22, 25) & routed.school_group.eq("__invalid__"), "stock"].sum()
            )

            industry_pieces.append(
                routed.groupby(["occ_code", "month", "industry_group", "age_group"], as_index=False, observed=True)[["stock", "respondent_equivalent"]].sum()
            )
            education_pieces.append(
                routed.groupby(["occ_code", "month", "education_group", "age_group"], as_index=False, observed=True)[["stock", "respondent_equivalent"]].sum()
            )
            age_pieces.append(
                routed.assign(age_cell=np.where(routed.age.between(22, 25), routed.age.astype(str), "older_26_65"))
                .groupby(["occ_code", "month", "age_cell"], as_index=False, observed=True)[["stock", "respondent_equivalent"]].sum()
            )
            young = routed.loc[routed.age.between(22, 25)].copy()
            if not young.empty:
                composition_pieces.append(
                    young.groupby(["occ_code", "month", "YEAR", "age", "education_group", "school_group"], as_index=False, observed=True)[["stock", "respondent_equivalent"]].sum()
                )

    if not industry_pieces or not education_pieces or not age_pieces:
        raise RuntimeError("microdata scan produced no heterogeneity aggregates")
    industry = pd.concat(industry_pieces, ignore_index=True).groupby(
        ["occ_code", "month", "industry_group", "age_group"], as_index=False, observed=True
    )[["stock", "respondent_equivalent"]].sum()
    education = pd.concat(education_pieces, ignore_index=True).groupby(
        ["occ_code", "month", "education_group", "age_group"], as_index=False, observed=True
    )[["stock", "respondent_equivalent"]].sum()
    age = pd.concat(age_pieces, ignore_index=True).groupby(
        ["occ_code", "month", "age_cell"], as_index=False, observed=True
    )[["stock", "respondent_equivalent"]].sum()
    composition = pd.concat(composition_pieces, ignore_index=True).groupby(
        ["occ_code", "month", "YEAR", "age", "education_group", "school_group"], as_index=False, observed=True
    )[["stock", "respondent_equivalent"]].sum()

    counters["early_route_conservation_absolute_gap"] = counters["early_routed_weight_before_support"] - counters["early_matched_source_weight"]
    counters["current_route_conservation_absolute_gap"] = counters["current_routed_weight_before_support"] - counters["current_source_weight"]
    if abs(counters["early_route_conservation_absolute_gap"]) > max(1.0, counters["early_matched_source_weight"]) * 1e-10:
        raise RuntimeError("early route conservation failed")
    if abs(counters["current_route_conservation_absolute_gap"]) > max(1.0, counters["current_source_weight"]) * 1e-10:
        raise RuntimeError("current direct-route conservation failed")
    return industry, education, age, composition, counters


def build_panel(frame: pd.DataFrame, row_columns: list[str], months: list[str]):
    rows = frame[row_columns].drop_duplicates().sort_values(row_columns).reset_index(drop=True)
    rows["_row_id"] = np.arange(len(rows))
    data = frame.merge(rows, on=row_columns, how="inner", validate="many_to_one")
    grouped = data.groupby(["_row_id", "month", "age_group"], as_index=False, observed=True).stock.sum()
    index = pd.MultiIndex.from_product([np.arange(len(rows)), months], names=["_row_id", "month"])
    pivot = grouped.pivot_table(index=["_row_id", "month"], columns="age_group", values="stock", aggfunc="sum", fill_value=0.0).reindex(index, fill_value=0.0)
    for column in ("young", "older"):
        if column not in pivot:
            pivot[column] = 0.0
    young = pivot.young.to_numpy().reshape(len(rows), len(months))
    older = pivot.older.to_numpy().reshape(len(rows), len(months))
    return rows, young, older


def build_base_design(row_occ: list[str], months: list[str], q_map: dict, webb_map: dict):
    quintiles = np.array([q_map[x] for x in row_occ], dtype=int)
    webb = np.array([webb_map[x] for x in row_occ], dtype=float)
    post = np.array([month >= "2023-01" for month in months])
    columns = [
        (((quintiles == q)[:, None]) & post[None, :]).reshape(-1).astype(float)
        for q in (2, 3, 4, 5)
    ]
    columns.append((webb[:, None] * post[None, :]).reshape(-1))
    return np.column_stack(columns), [f"Q{q}_x_post" for q in (2, 3, 4, 5)] + ["Webb_z_x_post"]


def fit_clustered(engine, young, older, regressors, second_fe, row_clusters, cluster_levels):
    n_rows, n_months = young.shape
    if regressors.shape[0] != n_rows * n_months:
        raise ValueError("regressor and panel rows differ")
    total_full = (young + older).reshape(-1)
    y_full = young.reshape(-1)
    row_full = np.repeat(np.arange(n_rows), n_months)
    second_full = np.asarray(second_fe).reshape(-1)
    cluster_lookup = {value: index for index, value in enumerate(cluster_levels)}
    cluster_row = np.array([cluster_lookup[value] for value in row_clusters], dtype=int)
    cluster_full = np.repeat(cluster_row, n_months)
    keep = total_full > 0
    y, total, x = y_full[keep], total_full[keep], regressors[keep]
    _, row_fe = np.unique(row_full[keep], return_inverse=True)
    _, second = np.unique(second_full[keep], return_inverse=True)
    fit = engine.fit_grouped_logit_fe(
        y, total, row_fe, second, x, max_iterations=5000
    )
    if not fit.converged:
        raise RuntimeError("grouped-binomial fixed-effect model did not converge")
    probability = fit.fitted_probability
    residual = y - total * probability
    weight = np.maximum(total * probability * (1.0 - probability), 1e-12)
    rx = engine._weighted_absorb(
        x, weight, row_fe, second, int(row_fe.max()) + 1, int(second.max()) + 1
    )
    information = rx.T @ (weight[:, None] * rx)
    if np.linalg.matrix_rank(information) != information.shape[0]:
        raise RuntimeError(
            f"slope information is rank deficient: {np.linalg.matrix_rank(information)}/{information.shape[0]}"
        )
    bread = np.linalg.inv(information)
    scores = np.zeros((len(cluster_levels), x.shape[1]))
    np.add.at(scores, cluster_full[keep], rx * residual[:, None])
    influence = scores @ bread.T
    influence *= math.sqrt(len(cluster_levels) / (len(cluster_levels) - 1))
    return fit, influence, {
        "weight": weight,
        "rx": rx,
        "information": information,
        "cluster": cluster_full[keep],
        "cluster_count": len(cluster_levels),
        "positive_total_cells": int(keep.sum()),
        "zero_total_cells": int((~keep).sum()),
        "row_fixed_effects": int(row_fe.max()) + 1,
        "second_fixed_effects": int(second.max()) + 1,
    }


def information_summary(details: dict, target: int) -> tuple[dict, np.ndarray]:
    rx, weight = details["rx"], details["weight"]
    other = [index for index in range(rx.shape[1]) if index != target]
    residual = rx[:, target].copy()
    raw = float(np.sum(weight * np.square(residual)))
    if other:
        z = rx[:, other]
        cross = z.T @ (weight * residual)
        projection = np.linalg.solve(z.T @ (weight[:, None] * z), cross)
        residual -= z @ projection
    contribution = np.bincount(
        details["cluster"], weights=weight * np.square(residual), minlength=details["cluster_count"]
    )
    total = float(contribution.sum())
    eigen = np.linalg.eigvalsh(details["information"])
    positive = eigen[eigen > max(float(eigen.max()) * 1e-12, 1e-12)]
    return {
        "fixed_effect_adjusted_raw_target_information": raw,
        "conditional_target_information": total,
        "information_retention_conditional_over_raw": total / raw,
        "target_vif_like_raw_over_conditional": raw / total,
        "effective_occupation_information_count": float(total * total / np.square(contribution).sum()),
        "top_five_information_share": float(np.sort(contribution)[::-1][:5].sum() / total),
        "information_matrix_rank": int(np.linalg.matrix_rank(details["information"])),
        "information_matrix_columns": int(details["information"].shape[0]),
        "information_matrix_condition_number_positive_spectrum": float(positive.max() / positive.min()),
    }, contribution


def scalar_summary(estimate: float, influence: np.ndarray, signs: np.ndarray) -> tuple[dict, np.ndarray]:
    se = float(np.sqrt(np.sum(np.square(influence))))
    shifts = signs @ influence
    critical = quantile(np.abs(shifts / se), .95)
    return {
        "coefficient": estimate,
        "analytic_occupation_cluster_se": se,
        "bootstrap_se": float(np.std(shifts, ddof=1)),
        "ci_lower": estimate - critical * se,
        "ci_upper": estimate + critical * se,
        "bootstrap_p_value": float((1 + np.sum(np.abs(shifts / se) >= abs(estimate / se))) / (len(shifts) + 1)),
        "bootstrap_critical": critical,
        "normal_theory_mde80": (Z975 + Z80) * se,
        "draws": len(shifts),
    }, shifts


def paired_summary(name: str, left: dict, right: dict, signs: np.ndarray) -> dict:
    vector = left["influence"] - right["influence"]
    estimate = left["coefficient"] - right["coefficient"]
    summary, _ = scalar_summary(estimate, vector, signs)
    return {
        "contrast": name,
        "left_model": left["name"],
        "right_model": right["name"],
        "coefficient_difference": summary.pop("coefficient"),
        "paired_analytic_se": summary.pop("analytic_occupation_cluster_se"),
        "paired_bootstrap_se": summary.pop("bootstrap_se"),
        "paired_ci_lower": summary.pop("ci_lower"),
        "paired_ci_upper": summary.pop("ci_upper"),
        "paired_bootstrap_p_value": summary.pop("bootstrap_p_value"),
        "paired_bootstrap_critical": summary.pop("bootstrap_critical"),
        "normal_theory_paired_mde80": summary.pop("normal_theory_mde80"),
        "draws": summary.pop("draws"),
        "common_occupation_multipliers": True,
    }


def register_model(name, panel, fit, influence, details, labels, signs, cluster_levels, influence_rows):
    target = labels.index("Q5_x_post")
    summary, _ = scalar_summary(float(fit.beta[target]), influence[:, target], signs)
    info, contribution = information_summary(details, target)
    row = {
        "analysis_status": LABEL,
        "model": name,
        "panel": panel,
        "target": "Q5_x_post",
        "clusters": len(cluster_levels),
        "cluster_support_hash_sha256": support_hash(cluster_levels),
        "row_fixed_effects": details["row_fixed_effects"],
        "second_fixed_effects": details["second_fixed_effects"],
        "slope_parameters": len(labels),
        "regressor_labels_json": json.dumps(labels),
        "positive_total_cells": details["positive_total_cells"],
        "zero_total_cells": details["zero_total_cells"],
        **summary,
        **info,
    }
    for code, value, info_value in zip(cluster_levels, influence[:, target], contribution):
        influence_rows.append({
            "model": name,
            "occupation_code": code,
            "target_influence": float(value),
            "conditional_target_information": float(info_value),
            "conditional_target_information_share": float(info_value / info["conditional_target_information"]),
        })
    return {"name": name, "coefficient": float(fit.beta[target]), "influence": influence[:, target], "row": row}


def simultaneous_rows(models: list[dict], signs: np.ndarray, family: str) -> tuple[list[dict], np.ndarray]:
    estimates = np.array([model["coefficient"] for model in models])
    influences = np.column_stack([model["influence"] for model in models])
    ses = np.sqrt(np.sum(np.square(influences), axis=0))
    centered = signs @ influences
    critical = quantile(np.max(np.abs(centered / ses[None, :]), axis=1), .95)
    rows = []
    for index, model in enumerate(models):
        rows.append({
            "family": family,
            "model": model["name"],
            "coefficient": estimates[index],
            "analytic_occupation_cluster_se": ses[index],
            "simultaneous_critical": critical,
            "simultaneous_ci_lower": estimates[index] - critical * ses[index],
            "simultaneous_ci_upper": estimates[index] + critical * ses[index],
            "models_in_family": len(models),
            "draws": len(signs),
            "common_occupation_multipliers": True,
        })
    return rows, influences


def simultaneous_difference_rows(models: list[dict], reference: dict, signs: np.ndarray, family: str) -> list[dict]:
    estimates = np.array([model["coefficient"] - reference["coefficient"] for model in models])
    influences = np.column_stack([model["influence"] - reference["influence"] for model in models])
    ses = np.sqrt(np.sum(np.square(influences), axis=0))
    centered = signs @ influences
    critical = quantile(np.max(np.abs(centered / ses[None, :]), axis=1), .95)
    rows = []
    for index, model in enumerate(models):
        rows.append({
            "family": family,
            "model": f"{model['name']}_minus_{reference['name']}",
            "coefficient": estimates[index],
            "analytic_occupation_cluster_se": ses[index],
            "simultaneous_critical": critical,
            "simultaneous_ci_lower": estimates[index] - critical * ses[index],
            "simultaneous_ci_upper": estimates[index] + critical * ses[index],
            "models_in_family": len(models),
            "draws": len(signs),
            "common_occupation_multipliers": True,
        })
    return rows


def stock_coverage_rows(named_frames: list[tuple[str, pd.DataFrame]], months: list[str], baseline_name: str) -> list[dict]:
    summaries = {}
    for name, frame in named_frames:
        selected = frame.loc[frame.month.isin(months)].copy()
        selected["period"] = np.where(selected.month.le("2022-11"), "pre_2017_2022m11", "post_2023_2026m07")
        grouped = selected.groupby(["period", "age_group"], observed=True)[["stock", "respondent_equivalent"]].sum()
        summaries[name] = grouped
    baseline = summaries[baseline_name]
    rows = []
    for name, grouped in summaries.items():
        for period in ["pre_2017_2022m11", "post_2023_2026m07"]:
            for age_group in ["young", "older", "total"]:
                if age_group == "total":
                    stock = float(grouped.loc[period, "stock"].sum())
                    respondent = float(grouped.loc[period, "respondent_equivalent"].sum())
                    denominator = float(baseline.loc[period, "stock"].sum())
                else:
                    stock = float(grouped.loc[(period, age_group), "stock"]) if (period, age_group) in grouped.index else 0.0
                    respondent = float(grouped.loc[(period, age_group), "respondent_equivalent"]) if (period, age_group) in grouped.index else 0.0
                    denominator = float(baseline.loc[(period, age_group), "stock"])
                rows.append({
                    "sample": name,
                    "period": period,
                    "age_group": age_group,
                    "weighted_stock": stock,
                    "respondent_equivalent": respondent,
                    "weighted_stock_share_of_full_baseline": stock / denominator,
                })
    return rows


def fit_occ_model(engine, frame, support, months, q_map, webb_map, signs, name, panel, influence_rows):
    rows, young, older = build_panel(frame, ["occ_code"], months)
    if rows.occ_code.tolist() != list(support):
        raise RuntimeError(f"{name}: occupation row support does not match declared support")
    design, labels = build_base_design(rows.occ_code.tolist(), months, q_map, webb_map)
    second = np.tile(np.arange(len(months)), len(rows))
    fit, influence, details = fit_clustered(
        engine, young, older, design, second, rows.occ_code.tolist(), list(support)
    )
    return register_model(name, panel, fit, influence, details, labels, signs, list(support), influence_rows)


def run_analysis(args):
    args.output_dir.mkdir(parents=True, exist_ok=True)
    input_hashes = validate_inputs(args)
    membership, q_map, webb_map = load_contract(args)
    support = membership.occupation_code.tolist()
    q_by_code = q_map
    engine_module = import_path("yax_heterogeneity_frozen", args.repo_root / "yax/analysis/run_frozen_v11.py")
    engine = engine_module.ENGINE

    industry, education, age, composition, scan = build_aggregates(args, set(support))
    observed = sorted(set(age.month))
    if len(observed) != 114 or "2025-10" in observed or not MARCH_REPLACEMENTS.issubset(set(observed)):
        raise RuntimeError(f"corrected observed calendar failed: {len(observed)} months")
    months = [month for month in observed if month != "2022-12"]
    if len(months) != 113:
        raise RuntimeError(f"static calendar should contain 113 months, found {len(months)}")
    premonths = [month for month in months if month <= "2022-11"]
    if len(premonths) != 71:
        raise RuntimeError(f"preperiod should contain 71 months, found {len(premonths)}")
    postmonths = [month for month in months if month >= "2023-01"]

    signs_full = np.random.default_rng(SEED).choice(np.array([-1.0, 1.0]), size=(DRAWS, len(support)))
    influence_rows: list[dict] = []
    model_rows: list[dict] = []
    paired_rows: list[dict] = []
    simultaneous: list[dict] = []
    covariance_rows: list[dict] = []
    failures: list[dict] = []

    all_age = age.copy()
    all_age["age_group"] = np.where(all_age.age_cell.eq("older_26_65"), "older", "young")
    all_occ = all_age.groupby(["occ_code", "month", "age_group"], as_index=False, observed=True)[["stock", "respondent_equivalent"]].sum()
    baseline = fit_occ_model(
        engine, all_occ, support, months, q_map, webb_map, signs_full,
        "full_microdata_rebuilt_baseline", "occupation_month_all_employed", influence_rows,
    )
    if not np.isclose(baseline["coefficient"], EXPECTED_BASELINE, atol=5e-9, rtol=0):
        raise RuntimeError(f"rebuilt baseline mismatch {baseline['coefficient']} != {EXPECTED_BASELINE}")
    model_rows.append(baseline["row"])

    # CHAR-03 fixed preperiod occupation-industry risk set.
    ind_valid = industry.loc[industry.industry_group.ne("__invalid__") & industry.month.isin(months)].copy()
    pre_ind = ind_valid.loc[ind_valid.month.isin(premonths)].groupby(
        ["occ_code", "industry_group", "age_group"], as_index=False, observed=True
    ).stock.sum()
    pre_pivot = pre_ind.pivot_table(index=["occ_code", "industry_group"], columns="age_group", values="stock", aggfunc="sum", fill_value=0.0)
    for column in ("young", "older"):
        if column not in pre_pivot:
            pre_pivot[column] = 0.0
    eligible_oi = pre_pivot.loc[(pre_pivot.young > 0) & (pre_pivot.older > 0)].reset_index()[["occ_code", "industry_group"]]
    ind_risk = ind_valid.merge(eligible_oi, on=["occ_code", "industry_group"], how="inner", validate="many_to_one")
    industry_support = sorted(eligible_oi.occ_code.unique())
    industry_signs = np.random.default_rng(SEED + 1).choice(np.array([-1.0, 1.0]), size=(DRAWS, len(industry_support)))

    industry_support_rows = []
    for group in sorted(eligible_oi.industry_group.unique()):
        strata = eligible_oi.loc[eligible_oi.industry_group.eq(group)]
        group_cells = ind_risk.loc[ind_risk.industry_group.eq(group)]
        pre_group = group_cells.loc[group_cells.month.isin(premonths)]
        post_group = group_cells.loc[group_cells.month.isin(postmonths)]
        oi_count = len(strata)
        totals = group_cells.groupby(["occ_code", "industry_group", "month"], observed=True)[["stock", "respondent_equivalent"]].sum()
        positive = int((totals.stock > 0).sum())
        thin = int(((totals.stock > 0) & (totals.respondent_equivalent < 5)).sum())
        q_values = sorted({q_map[code] for code in strata.occ_code})
        industry_support_rows.append({
            "industry_group": group,
            "eligible_occupation_industry_strata": oi_count,
            "distinct_occupations": strata.occ_code.nunique(),
            "distinct_quintiles": len(q_values),
            "quintiles_json": json.dumps(q_values),
            "contains_Q1": 1 in q_values,
            "contains_Q5": 5 in q_values,
            "preperiod_weighted_stock": float(pre_group.stock.sum()),
            "postperiod_weighted_stock": float(post_group.stock.sum()),
            "preperiod_young_stock": float(pre_group.loc[pre_group.age_group.eq("young"), "stock"].sum()),
            "preperiod_older_stock": float(pre_group.loc[pre_group.age_group.eq("older"), "stock"].sum()),
            "possible_occupation_industry_month_cells": oi_count * len(months),
            "positive_total_cells": positive,
            "zero_total_cells": oi_count * len(months) - positive,
            "positive_cells_below_five_respondent_equivalents": thin,
        })
    write_csv(args.output_dir / "INDUSTRY_SUPPORT.csv", industry_support_rows)
    oi_membership_rows = []
    eligible_oi_keys = set(zip(eligible_oi.occ_code, eligible_oi.industry_group))
    for (code, group), values in pre_pivot.iterrows():
        young_stock = float(values.get("young", 0.0))
        older_stock = float(values.get("older", 0.0))
        eligible = (code, group) in eligible_oi_keys
        reasons = []
        if young_stock <= 0: reasons.append("nonpositive_preperiod_young_stock")
        if older_stock <= 0: reasons.append("nonpositive_preperiod_older_stock")
        oi_membership_rows.append({
            "occupation_code": code,
            "occupation_name": membership.set_index("occupation_code").at[code, "occupation_name"],
            "industry_group": group,
            "beta_quintile": q_map[code],
            "preperiod_young_stock": young_stock,
            "preperiod_older_stock": older_stock,
            "eligible_preconnected_risk_set": eligible,
            "exclusion_reasons": ";".join(reasons),
        })
    write_csv(args.output_dir / "INDUSTRY_RISK_SET_MEMBERSHIP.csv", oi_membership_rows)

    try:
        ind_aggregate = ind_risk.groupby(["occ_code", "month", "age_group"], as_index=False, observed=True)[["stock", "respondent_equivalent"]].sum()
        model_ind_agg = fit_occ_model(
            engine, ind_aggregate, industry_support, months, q_map, webb_map, industry_signs,
            "valid_industry_aggregate_baseline", "occupation_month_preconnected_industry_records", influence_rows,
        )
        model_rows.append(model_ind_agg["row"])

        oi_rows, yi, oi = build_panel(ind_risk, ["occ_code", "industry_group"], months)
        base_design, base_labels = build_base_design(oi_rows.occ_code.tolist(), months, q_map, webb_map)
        second = np.tile(np.arange(len(months)), len(oi_rows))
        fit, influence, details = fit_clustered(
            engine, yi, oi, base_design, second, oi_rows.occ_code.tolist(), industry_support
        )
        model_ind_cell = register_model(
            "industry_cell_baseline", "occupation_industry_month", fit, influence, details,
            base_labels, industry_signs, industry_support, influence_rows,
        )
        model_rows.append(model_ind_cell["row"])

        pre_stock_by_group = ind_risk.loc[ind_risk.month.isin(premonths)].groupby("industry_group").stock.sum()
        reference_industry = str(pre_stock_by_group.idxmax())
        post = np.array([month >= "2023-01" for month in months])
        industry_levels = sorted(oi_rows.industry_group.unique())
        columns = [base_design]
        conditioned_labels = list(base_labels)
        for group in industry_levels:
            if group == reference_industry:
                continue
            values = (oi_rows.industry_group.to_numpy() == group)[:, None] & post[None, :]
            columns.append(values.reshape(-1, 1).astype(float))
            conditioned_labels.append(f"industry_{group}_x_post")
        conditioned_design = np.column_stack(columns)
        fit, influence, details = fit_clustered(
            engine, yi, oi, conditioned_design, second, oi_rows.occ_code.tolist(), industry_support
        )
        model_ind_conditioned = register_model(
            "industry_conditioned", "occupation_industry_month_plus_industry_post", fit, influence,
            details, conditioned_labels, industry_signs, industry_support, influence_rows,
        )
        model_ind_conditioned["row"]["industry_post_reference"] = reference_industry
        model_ind_conditioned["row"]["broad_industry_groups"] = len(industry_levels)
        model_rows.append(model_ind_conditioned["row"])
        paired_rows.extend([
            paired_summary("industry_cell_minus_valid_industry_aggregate", model_ind_cell, model_ind_agg, industry_signs),
            paired_summary("industry_conditioned_minus_industry_cell", model_ind_conditioned, model_ind_cell, industry_signs),
            paired_summary("industry_conditioned_minus_valid_industry_aggregate", model_ind_conditioned, model_ind_agg, industry_signs),
        ])
    except Exception as error:
        failures.append({
            "workstream": "CHAR-03", "stage": "industry_models",
            "error_type": type(error).__name__, "message": str(error),
            "traceback": traceback.format_exc(),
        })

    # CHAR-04 common education support, fixed using preperiod stocks only.
    edu_valid = education.loc[education.education_group.isin(["BA_plus", "non_BA"]) & education.month.isin(months)].copy()
    pre_edu = edu_valid.loc[edu_valid.month.isin(premonths)].groupby(
        ["occ_code", "education_group", "age_group"], as_index=False, observed=True
    ).stock.sum()
    edu_pivot = pre_edu.pivot_table(index="occ_code", columns=["education_group", "age_group"], values="stock", aggfunc="sum", fill_value=0.0)
    required_edu = [("BA_plus", "young"), ("BA_plus", "older"), ("non_BA", "young"), ("non_BA", "older")]
    for column in required_edu:
        if column not in edu_pivot:
            edu_pivot[column] = 0.0
    education_support = sorted(edu_pivot.index[(edu_pivot[required_edu] > 0).all(axis=1)])
    education_signs = np.random.default_rng(SEED + 2).choice(np.array([-1.0, 1.0]), size=(DRAWS, len(education_support)))
    edu_risk = edu_valid.loc[edu_valid.occ_code.isin(education_support)].copy()
    education_support_rows = []
    for group in ["BA_plus", "non_BA"]:
        for q in range(1, 6):
            codes = [code for code in education_support if q_map[code] == q]
            part = edu_risk.loc[edu_risk.education_group.eq(group) & edu_risk.occ_code.isin(codes)]
            education_support_rows.append({
                "education_group": group,
                "beta_quintile": q,
                "occupations": len(codes),
                "preperiod_young_stock": float(part.loc[part.month.isin(premonths) & part.age_group.eq("young"), "stock"].sum()),
                "preperiod_older_stock": float(part.loc[part.month.isin(premonths) & part.age_group.eq("older"), "stock"].sum()),
                "postperiod_young_stock": float(part.loc[part.month.isin(postmonths) & part.age_group.eq("young"), "stock"].sum()),
                "postperiod_older_stock": float(part.loc[part.month.isin(postmonths) & part.age_group.eq("older"), "stock"].sum()),
            })
    write_csv(args.output_dir / "EDUCATION_SUPPORT.csv", education_support_rows)
    education_common_set = set(education_support)
    education_membership_rows = []
    for code in support:
        row = {
            "occupation_code": code,
            "occupation_name": membership.set_index("occupation_code").at[code, "occupation_name"],
            "beta_quintile": q_map[code],
        }
        reasons = []
        for education_group_name, age_group_name in required_edu:
            value = float(edu_pivot.at[code, (education_group_name, age_group_name)]) if code in edu_pivot.index else 0.0
            row[f"preperiod_{education_group_name}_{age_group_name}_stock"] = value
            if value <= 0:
                reasons.append(f"nonpositive_{education_group_name}_{age_group_name}_preperiod_stock")
        row["eligible_common_support"] = code in education_common_set
        row["exclusion_reasons"] = ";".join(reasons)
        education_membership_rows.append(row)
    write_csv(args.output_dir / "EDUCATION_COMMON_SUPPORT_MEMBERSHIP.csv", education_membership_rows)

    edu_models = []
    pooled_edu = edu_risk.groupby(["occ_code", "month", "age_group"], as_index=False, observed=True)[["stock", "respondent_equivalent"]].sum()
    pooled_model = fit_occ_model(
        engine, pooled_edu, education_support, months, q_map, webb_map, education_signs,
        "education_common_support_pooled", "occupation_month_valid_education", influence_rows,
    )
    model_rows.append(pooled_model["row"])
    for group in ["BA_plus", "non_BA"]:
        frame = edu_risk.loc[edu_risk.education_group.eq(group)].copy()
        model = fit_occ_model(
            engine, frame, education_support, months, q_map, webb_map, education_signs,
            f"education_{group}", f"occupation_month_{group}", influence_rows,
        )
        model_rows.append(model["row"])
        edu_models.append(model)
        paired_rows.append(paired_summary(f"{group}_minus_education_pooled", model, pooled_model, education_signs))
    paired_rows.append(paired_summary("BA_plus_minus_non_BA", edu_models[0], edu_models[1], education_signs))
    sim_rows, edu_inf = simultaneous_rows(edu_models, education_signs, "BA_plus_and_non_BA")
    simultaneous.extend(sim_rows)
    edu_cov = edu_inf.T @ edu_inf
    for i, left in enumerate(edu_models):
        for j, right in enumerate(edu_models):
            covariance_rows.append({"family": "education", "left_model": left["name"], "right_model": right["name"], "covariance": float(edu_cov[i, j])})

    # Exact-age models on a common preperiod support.
    age = age.loc[age.month.isin(months)].copy()
    pre_age = age.loc[age.month.isin(premonths)].groupby(["occ_code", "age_cell"], as_index=False, observed=True).stock.sum()
    age_pivot = pre_age.pivot_table(index="occ_code", columns="age_cell", values="stock", aggfunc="sum", fill_value=0.0)
    required_age = ["22", "23", "24", "25", "older_26_65"]
    for column in required_age:
        if column not in age_pivot:
            age_pivot[column] = 0.0
    age_support = sorted(age_pivot.index[(age_pivot[required_age] > 0).all(axis=1)])
    age_signs = np.random.default_rng(SEED + 3).choice(np.array([-1.0, 1.0]), size=(DRAWS, len(age_support)))
    age_risk = age.loc[age.occ_code.isin(age_support)].copy()
    age_support_rows = []
    for cell in required_age:
        for q in range(1, 6):
            codes = [code for code in age_support if q_map[code] == q]
            part = age_risk.loc[age_risk.age_cell.eq(cell) & age_risk.occ_code.isin(codes)]
            age_support_rows.append({
                "age_cell": cell, "beta_quintile": q, "occupations": len(codes),
                "preperiod_weighted_stock": float(part.loc[part.month.isin(premonths), "stock"].sum()),
                "postperiod_weighted_stock": float(part.loc[part.month.isin(postmonths), "stock"].sum()),
            })
    write_csv(args.output_dir / "AGE_SUPPORT.csv", age_support_rows)
    age_common_set = set(age_support)
    age_membership_rows = []
    for code in support:
        row = {
            "occupation_code": code,
            "occupation_name": membership.set_index("occupation_code").at[code, "occupation_name"],
            "beta_quintile": q_map[code],
        }
        reasons = []
        for age_cell in required_age:
            value = float(age_pivot.at[code, age_cell]) if code in age_pivot.index else 0.0
            row[f"preperiod_{age_cell}_stock"] = value
            if value <= 0:
                reasons.append(f"nonpositive_{age_cell}_preperiod_stock")
        row["eligible_common_support"] = code in age_common_set
        row["exclusion_reasons"] = ";".join(reasons)
        age_membership_rows.append(row)
    write_csv(args.output_dir / "AGE_COMMON_SUPPORT_MEMBERSHIP.csv", age_membership_rows)

    older = age_risk.loc[age_risk.age_cell.eq("older_26_65")].copy()
    pooled_young = age_risk.loc[age_risk.age_cell.isin(["22", "23", "24", "25"])].copy()
    pooled_young["age_group"] = "young"
    older_for_model = older.copy(); older_for_model["age_group"] = "older"
    pooled_age_frame = pd.concat([pooled_young, older_for_model], ignore_index=True)
    pooled_age_model = fit_occ_model(
        engine, pooled_age_frame, age_support, months, q_map, webb_map, age_signs,
        "age_common_support_22_25_pooled", "occupation_month_22_25_vs_26_65", influence_rows,
    )
    model_rows.append(pooled_age_model["row"])
    exact_age_models = []
    for exact_age in ["22", "23", "24", "25"]:
        young_part = age_risk.loc[age_risk.age_cell.eq(exact_age)].copy(); young_part["age_group"] = "young"
        exact_frame = pd.concat([young_part, older_for_model], ignore_index=True)
        model = fit_occ_model(
            engine, exact_frame, age_support, months, q_map, webb_map, age_signs,
            f"exact_age_{exact_age}_vs_26_65", f"occupation_month_age_{exact_age}_vs_26_65", influence_rows,
        )
        model_rows.append(model["row"])
        exact_age_models.append(model)
        paired_rows.append(paired_summary(f"age_{exact_age}_minus_pooled_22_25", model, pooled_age_model, age_signs))
    sim_rows, age_inf = simultaneous_rows(exact_age_models, age_signs, "single_ages_22_23_24_25")
    simultaneous.extend(sim_rows)
    simultaneous.extend(simultaneous_difference_rows(
        exact_age_models, pooled_age_model, age_signs, "single_ages_minus_pooled_22_25"
    ))
    age_cov = age_inf.T @ age_inf
    for i, left in enumerate(exact_age_models):
        for j, right in enumerate(exact_age_models):
            covariance_rows.append({"family": "exact_age", "left_model": left["name"], "right_model": right["name"], "covariance": float(age_cov[i, j])})
    contrasts = np.array([[-1, 1, 0, 0], [-1, 0, 1, 0], [-1, 0, 0, 1]], dtype=float)
    age_estimates = np.array([model["coefficient"] for model in exact_age_models])
    difference = contrasts @ age_estimates
    variance = contrasts @ age_cov @ contrasts.T
    wald = float(difference @ np.linalg.pinv(variance) @ difference)
    write_csv(args.output_dir / "AGE_EQUALITY_TEST.csv", [{
        "null": "Q5 coefficients equal at ages 22 23 24 and 25",
        "wald_chi_square": wald,
        "df": int(np.linalg.matrix_rank(variance)),
        "asymptotic_p_value": chi_square_survival(wald, int(np.linalg.matrix_rank(variance))),
        "common_support_occupations": len(age_support),
        "common_occupation_score_covariance": True,
    }])

    # Descriptive composition; no separate cohort coefficient is estimated.
    composition = composition.loc[composition.month.isin(months)].copy()
    composition["beta_quintile"] = composition.occ_code.map(q_by_code).astype(int)
    composition["period"] = np.where(composition.month.le("2022-11"), "pre_2017_2022m11", "post_2023_2026m07")
    composition["birth_year_proxy"] = composition.YEAR.astype(int) - composition.age.astype(int)

    def composition_table(keys):
        rows = []
        for key, group in composition.groupby(keys, observed=True):
            if not isinstance(key, tuple):
                key = (key,)
            values = dict(zip(keys, key))
            total = float(group.stock.sum())
            valid_edu = group.education_group.ne("__invalid__")
            valid_school = group.school_group.ne("__invalid__")
            values.update({
                "weighted_stock": total,
                "respondent_equivalent": float(group.respondent_equivalent.sum()),
                "weighted_mean_age": float(np.average(group.age, weights=group.stock)),
                "weighted_mean_birth_year_proxy": float(np.average(group.birth_year_proxy, weights=group.stock)),
                "BA_plus_share_total": float(group.loc[group.education_group.eq("BA_plus"), "stock"].sum() / total),
                "non_BA_share_total": float(group.loc[group.education_group.eq("non_BA"), "stock"].sum() / total),
                "education_valid_share": float(group.loc[valid_edu, "stock"].sum() / total),
                "enrollment_valid_share": float(group.loc[valid_school, "stock"].sum() / total),
                "enrolled_share_among_valid": float(
                    group.loc[group.school_group.eq("enrolled"), "stock"].sum() /
                    group.loc[valid_school, "stock"].sum()
                ) if group.loc[valid_school, "stock"].sum() > 0 else np.nan,
            })
            for exact_age in [22, 23, 24, 25]:
                values[f"age_{exact_age}_share"] = float(group.loc[group.age.eq(exact_age), "stock"].sum() / total)
            rows.append(values)
        return rows

    write_csv(args.output_dir / "AGE_EDUCATION_COMPOSITION_BY_YEAR_QUINTILE.csv", composition_table(["YEAR", "beta_quintile"]))
    write_csv(args.output_dir / "AGE_EDUCATION_COMPOSITION_BY_PERIOD_QUINTILE.csv", composition_table(["period", "beta_quintile"]))

    age_common_frame = all_occ.loc[all_occ.occ_code.isin(age_support)].copy()
    education_common_frame = edu_risk.groupby(
        ["occ_code", "month", "age_group"], as_index=False, observed=True
    )[["stock", "respondent_equivalent"]].sum()
    write_csv(args.output_dir / "SAMPLE_AND_STOCK_COVERAGE.csv", stock_coverage_rows([
        ("full_BASE03_support", all_occ),
        ("all_valid_industry_records", ind_valid),
        ("preconnected_industry_risk_set", ind_risk),
        ("all_valid_education_records", edu_valid),
        ("education_common_support", education_common_frame),
        ("age_common_support", age_common_frame),
    ], months, "full_BASE03_support"))

    # Relative information is assigned after all models are known.
    baseline_info = baseline["row"]["conditional_target_information"]
    for row in model_rows:
        row["relative_information_to_full_microdata_baseline"] = row["conditional_target_information"] / baseline_info
    write_csv(args.output_dir / "HETEROGENEITY_MODEL_RESULTS.csv", model_rows)
    write_csv(args.output_dir / "HETEROGENEITY_PAIRED_DIFFERENCES.csv", paired_rows)
    write_csv(args.output_dir / "SIMULTANEOUS_INTERVALS.csv", simultaneous)
    write_csv(args.output_dir / "TARGET_COVARIANCE_MATRICES.csv", covariance_rows)
    write_csv(args.output_dir / "MODEL_OCCUPATION_INFLUENCE.csv", influence_rows)
    write_json(args.output_dir / "MODEL_FAILURES.json", failures)

    support_summary = {
        "BASE03_occupations": len(support),
        "industry_preconnected_occupations": len(industry_support),
        "industry_preconnected_strata": len(eligible_oi),
        "industry_groups": sorted(eligible_oi.industry_group.unique()),
        "education_common_support_occupations": len(education_support),
        "age_common_support_occupations": len(age_support),
        "industry_support_hash": support_hash(industry_support),
        "education_support_hash": support_hash(education_support),
        "age_support_hash": support_hash(age_support),
    }
    write_json(args.output_dir / "SUPPORT_SUMMARY.json", support_summary)
    write_json(args.output_dir / "MICRODATA_SCAN_RECEIPT.json", scan)
    write_json(args.output_dir / "INFERENCE_CONTRACT.json", {
        "draws": DRAWS,
        "base_seed": SEED,
        "seeds": {"baseline": SEED, "industry": SEED + 1, "education": SEED + 2, "age": SEED + 3},
        "multiplier": "occupation-level Rademacher",
        "common_within_each_paired_family": True,
        "stored_representation": "MODEL_OCCUPATION_INFLUENCE.csv plus seeds and deterministic NumPy default_rng generation",
        "interval": "95 percent wild-score critical value applied to occupation-cluster analytic SE",
        "mde": "(z_0.975 + z_0.80) times analytic occupation-cluster SE",
    })

    output_hashes = {
        path.name: sha256(path) for path in sorted(args.output_dir.iterdir())
        if path.is_file() and path.name not in {"EXECUTION_RECEIPT.json", "SELF_CHECK.json"}
    }
    receipt = {
        "record": "YAX R3 CHAR-03/CHAR-04 industry and education heterogeneity",
        "analysis_status": LABEL,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scc_job_id": os.environ.get("JOB_ID", "interactive_or_unrecorded"),
        "scc_hostname": os.environ.get("HOSTNAME", "unknown"),
        "predeclare_commit": PREDECLARE_COMMIT,
        "staged_repository_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=args.repo_root, text=True).strip(),
        "specification_sha256": sha256(args.specification),
        "script_sha256": sha256(pathlib.Path(__file__)),
        "input_hashes": input_hashes,
        "private_input_basenames": {"microdata": args.microdata.name, "repair_microdata": args.repair_microdata.name},
        "calendar": {"observed_months": 114, "static_months": len(months), "preperiod_months": len(premonths), "postperiod_months": len(postmonths), "December_2022_excluded": True, "October_2025_present": False},
        "support": support_summary,
        "scan": scan,
        "failures": failures,
        "output_hashes": output_hashes,
    }
    write_json(args.output_dir / "EXECUTION_RECEIPT.json", receipt)
    print(json.dumps({
        "status": "COMPLETE_WITH_SERIALIZED_CHAR03_BLOCKER" if failures else "PASS_CHAR03_CHAR04",
        "baseline": baseline["coefficient"],
        "models": len(model_rows),
        "paired_contrasts": len(paired_rows),
        "support": support_summary,
        "failures": failures,
    }, indent=2, sort_keys=True))


def parser():
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--repo-root", type=pathlib.Path, required=True)
    value.add_argument("--microdata", type=pathlib.Path, required=True)
    value.add_argument("--repair-microdata", type=pathlib.Path, required=True)
    value.add_argument("--bridge", type=pathlib.Path, required=True)
    value.add_argument("--membership", type=pathlib.Path, required=True)
    value.add_argument("--specification", type=pathlib.Path, required=True)
    value.add_argument("--output-dir", type=pathlib.Path, required=True)
    return value


if __name__ == "__main__":
    arguments = parser().parse_args()
    try:
        run_analysis(arguments)
    except Exception as error:
        arguments.output_dir.mkdir(parents=True, exist_ok=True)
        write_json(arguments.output_dir / "FATAL_ERROR.json", {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "scc_job_id": os.environ.get("JOB_ID", "interactive_or_unrecorded"),
            "error_type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc(),
        })
        raise
