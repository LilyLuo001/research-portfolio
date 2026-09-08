#!/usr/bin/env python3
"""Run the current-contract B03/B04 public benchmark alignment on SCC."""
from __future__ import annotations

import argparse
import csv
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
SEED = 202609089301
MARCH_REPAIRS = {f"{year}-03" for year in range(2017, 2022)}
WAGE_SALARY_CODES = {20, 21, 22, 23, 24, 25, 27, 28}
EXCLUDED_CLASS_CODES = {0, 10, 13, 14, 26, 29, 99}
POPULATIONS = ("all_employed", "full_time_civilian_wage_salary")
CONTRASTS = ("Q5_vs_Q1", "top_two_vs_bottom_three")
STRUCTURES = ("pooled", "family_post", "family_month")
WEBB_RULES = ("no_Webb_public_benchmark", "with_Webb_YAX_extension")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


MAP = load_module("yax_benchmark_mapping_helpers",
                  HERE.parents[1] / "gate3" / "mapping" / "run_mapping_sensitivity.py")
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


def support_hash(codes: np.ndarray) -> str:
    return hashlib.sha256("".join(f"{value}\n" for value in codes).encode()).hexdigest()


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


def month_string(frame: pd.DataFrame) -> pd.Series:
    return (pd.to_numeric(frame.YEAR, errors="raise").astype(int).astype(str) + "-" +
            pd.to_numeric(frame.MONTH, errors="raise").astype(int).astype(str).str.zfill(2))


def equal_occupation_quintiles(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(values, float)
    require(len(values) > 5 and np.all(np.isfinite(values)), "invalid exposure values")
    order = np.argsort(values, kind="mergesort")
    cumulative = np.arange(1, len(values) + 1, dtype=float)
    cuts = np.asarray([
        values[order[min(np.searchsorted(cumulative, share * len(values), side="left"),
                         len(values) - 1)]]
        for share in (0.2, 0.4, 0.6, 0.8)
    ])
    require(np.all(cuts[:-1] < cuts[1:]), "equal-occupation quintile cuts collapse")
    return (np.searchsorted(cuts, values, side="left") + 1).astype(int), cuts


def full_time_civilian_wage_salary(classwkr: pd.Series,
                                    hours: pd.Series) -> pd.Series:
    worker_class = pd.to_numeric(classwkr, errors="coerce")
    usual_hours = pd.to_numeric(hours, errors="coerce")
    return worker_class.isin(WAGE_SALARY_CODES) & usual_hours.between(35, 996)


def prepare_bridge(path: Path, support: set[str]) -> pd.DataFrame:
    bridge = pd.read_csv(path, dtype={"census_2010": str, "census_2018": str},
                         float_precision="round_trip")
    required = {"census_2010", "census_2018", "bridge_weight"}
    require(required.issubset(bridge.columns), "bridge schema differs")
    bridge["census_2010"] = bridge.census_2010.str.zfill(4)
    bridge["census_2018"] = bridge.census_2018.str.zfill(4)
    bridge["bridge_weight"] = pd.to_numeric(bridge.bridge_weight, errors="raise")
    require(not bridge[["census_2010", "census_2018"]].duplicated().any(),
            "bridge contains duplicate routes")
    sums = bridge.groupby("census_2010").bridge_weight.sum().to_numpy(float)
    require(np.max(np.abs(sums - 1.0)) <= 5e-7,
            "official bridge does not conserve source mass")
    return bridge.loc[bridge.census_2018.isin(support)].copy()


def scan_sources(wide: Path, repair: Path, bridge_path: Path,
                 support: set[str], desired_months: set[str]
                 ) -> tuple[pd.DataFrame, list[dict[str, Any]], dict[str, Any]]:
    """Aggregate employed rows; no person or household identifier is read."""
    bridge = prepare_bridge(bridge_path, support)
    parts: list[pd.DataFrame] = []
    class_counts: dict[tuple[str, int], list[float]] = {}
    counters = {
        "raw_rows": 0, "wide_march_rows_removed": 0,
        "positive_weight_employed_rows": 0, "full_time_wage_salary_rows": 0,
        "routed_descendant_rows": 0, "fractional_descendant_rows": 0,
        "unexpected_class_codes": [], "hours_100_to_996_rows": 0,
    }
    usecols = ["YEAR", "MONTH", "AGE", "EMPSTAT", "OCC", "WTFINL",
               "CLASSWKR", "UHRSWORKT"]
    for source, path in (("wide", wide), ("march_repair", repair)):
        for chunk in pd.read_csv(path, usecols=usecols, chunksize=400_000):
            counters["raw_rows"] += len(chunk)
            chunk["month"] = month_string(chunk)
            if source == "wide":
                replaced = chunk.month.isin(MARCH_REPAIRS)
                counters["wide_march_rows_removed"] += int(replaced.sum())
                chunk = chunk.loc[~replaced].copy()
            else:
                require(set(chunk.month.unique()).issubset(MARCH_REPAIRS),
                        "March repair contains a non-repair month")
            chunk = chunk.loc[chunk.month.isin(desired_months)].copy()
            if chunk.empty:
                continue
            age = pd.to_numeric(chunk.AGE, errors="coerce")
            status = pd.to_numeric(chunk.EMPSTAT, errors="coerce")
            weight = pd.to_numeric(chunk.WTFINL, errors="coerce")
            keep = (age.between(22, 65) & status.isin([10, 12]) &
                    np.isfinite(weight) & weight.gt(0))
            employed = chunk.loc[keep].copy()
            if employed.empty:
                continue
            employed["age"] = age.loc[employed.index].astype(int)
            employed["weight"] = weight.loc[employed.index].astype(float)
            employed["year"] = pd.to_numeric(employed.YEAR, errors="raise").astype(int)
            worker_class = pd.to_numeric(employed.CLASSWKR, errors="coerce")
            integral = worker_class.notna() & worker_class.mod(1).eq(0)
            observed_classes = set(worker_class.loc[integral].astype(int).unique())
            known_classes = WAGE_SALARY_CODES | EXCLUDED_CLASS_CODES
            unexpected = sorted(observed_classes - known_classes)
            if unexpected:
                counters["unexpected_class_codes"] = sorted(set(
                    counters["unexpected_class_codes"]) | set(unexpected))
            require(not unexpected, f"unexpected CLASSWKR codes {unexpected}")
            ftws = full_time_civilian_wage_salary(
                employed.CLASSWKR, employed.UHRSWORKT)
            usual_hours = pd.to_numeric(employed.UHRSWORKT, errors="coerce")
            counters["positive_weight_employed_rows"] += len(employed)
            counters["full_time_wage_salary_rows"] += int(ftws.sum())
            counters["hours_100_to_996_rows"] += int(usual_hours.between(100, 996).sum())
            employed["all_employed_stock"] = employed.weight
            employed["full_time_civilian_wage_salary_stock"] = employed.weight * ftws
            employed["source_class"] = worker_class.fillna(-999).astype(int)
            for value, group in employed.groupby("source_class"):
                key = (source, int(value))
                stored = class_counts.setdefault(key, [0.0, 0.0, 0.0])
                stored[0] += len(group)
                stored[1] += float(group.weight.sum())
                stored[2] += float(group.full_time_civilian_wage_salary_stock.sum())
            occ = pd.to_numeric(employed.OCC, errors="coerce")
            valid_occ = occ.notna() & occ.between(0, 9999) & occ.mod(1).eq(0)
            employed = employed.loc[valid_occ].copy()
            employed["source_occ"] = occ.loc[employed.index].astype(int).map(
                lambda value: f"{value:04d}")
            early = employed.loc[employed.year.le(2019)].merge(
                bridge, left_on="source_occ", right_on="census_2010", how="inner",
                validate="many_to_many")
            early["occ_code"] = early.census_2018
            early["route_weight"] = early.bridge_weight
            current = employed.loc[
                employed.year.ge(2020) & employed.source_occ.isin(support)].copy()
            current["occ_code"] = current.source_occ
            current["route_weight"] = 1.0
            routed = pd.concat([early, current], ignore_index=True, sort=False)
            if routed.empty:
                continue
            for population in POPULATIONS:
                routed[f"{population}_stock"] *= routed.route_weight
            counters["routed_descendant_rows"] += len(routed)
            counters["fractional_descendant_rows"] += int(
                np.sum(~np.isclose(routed.route_weight.to_numpy(float), 1.0)))
            parts.append(routed.groupby(
                ["occ_code", "month", "age"], as_index=False, observed=True)[
                    [f"{population}_stock" for population in POPULATIONS]].sum())
    require(bool(parts), "microdata scan produced no routed employment")
    routed = pd.concat(parts, ignore_index=True).groupby(
        ["occ_code", "month", "age"], as_index=False, observed=True)[
            [f"{population}_stock" for population in POPULATIONS]].sum()
    audit_rows = [{
        "audit_type": "CLASSWKR_distribution", "source": source,
        "CLASSWKR": code, "person_rows": int(values[0]),
        "weighted_all_employed_stock": values[1],
        "weighted_full_time_civilian_wage_salary_stock": values[2],
        "included_in_aligned_population": code in WAGE_SALARY_CODES,
    } for (source, code), values in sorted(class_counts.items())]
    return routed, audit_rows, counters


def stock_matrix(routed: pd.DataFrame, occupations: np.ndarray, months: list[str],
                 population: str, ages: tuple[int, int]) -> np.ndarray:
    column = f"{population}_stock"
    part = routed.loc[routed.age.between(*ages)].groupby(
        ["occ_code", "month"], as_index=False, observed=True)[column].sum()
    index = pd.MultiIndex.from_product([occupations.tolist(), months],
                                       names=["occ_code", "month"])
    return (part.set_index(["occ_code", "month"])[column].reindex(index, fill_value=0.0)
            .to_numpy(float).reshape(len(occupations), len(months)))


def multiplier_summary(estimate: float, influence: np.ndarray,
                       signs: np.ndarray) -> dict[str, float]:
    result = CORE.multiplier_interval(estimate, influence, signs)
    return {
        "occupation_linearized_se": result["se"],
        "occupation_multiplier_ci_lower": result["lower"],
        "occupation_multiplier_ci_upper": result["upper"],
        "occupation_multiplier_p": result["p_value"],
        "occupation_multiplier_critical": result["critical"],
    }


def growth_ratio(value0: np.ndarray, value1: np.ndarray,
                 mask: np.ndarray) -> tuple[float, np.ndarray]:
    start = float(value0[mask].sum())
    end = float(value1[mask].sum())
    require(start > 0 and end >= 0, "aggregate endpoint stock is invalid")
    ratio = end / start
    influence = np.zeros(len(value0))
    influence[mask] = value1[mask] / start - ratio * value0[mask] / start
    require(abs(float(influence.sum())) <= 1e-10,
            "growth-ratio influence does not close")
    return ratio, influence


def aggregate_contrast(value0: np.ndarray, value1: np.ndarray,
                       quintiles: np.ndarray, contrast: str,
                       signs: np.ndarray) -> dict[str, Any]:
    if contrast == "Q5_vs_Q1_growth_factor_difference":
        high, low = quintiles == 5, quintiles == 1
        high_ratio, high_if = growth_ratio(value0, value1, high)
        low_ratio, low_if = growth_ratio(value0, value1, low)
        estimate = high_ratio - low_ratio
        influence = high_if - low_if
    elif contrast == "top_two_vs_bottom_three_kept_pace":
        high, low = quintiles >= 4, quintiles <= 3
        high_ratio, high_if = growth_ratio(value0, value1, high)
        low_ratio, low_if = growth_ratio(value0, value1, low)
        require(low_ratio > 0, "bottom-three growth factor is nonpositive")
        estimate = high_ratio / low_ratio - 1.0
        influence = high_if / low_ratio - high_ratio * low_if / (low_ratio ** 2)
    else:
        raise ValueError(f"unknown aggregate contrast {contrast}")
    return {
        "estimate": float(estimate), "high_growth_factor": float(high_ratio),
        "low_growth_factor": float(low_ratio), "influence": influence,
        **multiplier_summary(float(estimate), influence, signs),
    }


def indexed_stock_rows(young: dict[str, np.ndarray], months: list[str],
                       quintiles: np.ndarray) -> list[dict[str, Any]]:
    reference = months.index("2022-11")
    definitions = [(f"Q{value}", quintiles == value) for value in range(1, 6)]
    definitions += [("bottom_three", quintiles <= 3),
                    ("top_two", quintiles >= 4),
                    ("all_support", np.ones(len(quintiles), bool))]
    rows: list[dict[str, Any]] = []
    for population, values in young.items():
        for label, mask in definitions:
            stock = values[mask].sum(axis=0)
            require(stock[reference] > 0, "November 2022 normalization stock is zero")
            for month, amount in zip(months, stock):
                rows.append({
                    "population": population, "exposure_group": label, "month": month,
                    "weighted_employment_stock": float(amount),
                    "index_November_2022_equals_1": float(amount / stock[reference]),
                    "grouping": "independent_equal_occupation_Rule_A_beta_approximation",
                })
    return rows


def wls_long_difference(start: np.ndarray, end: np.ndarray, quintiles: np.ndarray,
                        occupations: np.ndarray, population: str,
                        endpoint: str) -> tuple[list[dict[str, Any]],
                                                np.ndarray, np.ndarray]:
    keep = np.isfinite(start) & np.isfinite(end) & (start > 0) & (end >= 0)
    require(keep.sum() > 10 and set(quintiles[keep]) == {1, 2, 3, 4, 5},
            "long-difference support loses an exposure quintile")
    y = end[keep] / start[keep] - 1.0
    q = quintiles[keep]
    x = np.column_stack([np.ones(keep.sum()), *[(q == value).astype(float)
                                                for value in range(2, 6)]])
    w = start[keep]
    gram = x.T @ (w[:, None] * x)
    require(np.linalg.matrix_rank(gram) == x.shape[1], "long-difference design is singular")
    bread = np.linalg.inv(gram)
    beta = bread @ (x.T @ (w * y))
    residual = y - x @ beta
    scores = x * (w * residual)[:, None]
    correction = keep.sum() / (keep.sum() - x.shape[1])
    influence_local = math.sqrt(correction) * scores @ bread.T
    covariance = influence_local.T @ influence_local
    labels = ["intercept_Q1", "Q2_vs_Q1", "Q3_vs_Q1", "Q4_vs_Q1", "Q5_vs_Q1"]
    rows = []
    for index, label in enumerate(labels):
        se = float(np.sqrt(covariance[index, index]))
        rows.append({
            "model_id": f"{population}_{endpoint}_occupation_WLS_no_controls",
            "population": population, "endpoint": endpoint,
            "coefficient_label": label, "estimate": float(beta[index]),
            "heteroskedastic_robust_HC1_se": se,
            "normal_ci_lower": float(beta[index] - 1.959963984540054 * se),
            "normal_ci_upper": float(beta[index] + 1.959963984540054 * se),
            "support_occupations": int(keep.sum()),
            "support_hash_sha256": support_hash(occupations[keep]),
            "regression_weight": "baseline_CPS_WTFINL_employment_stock",
            "outcome": "occupation_percent_change_in_ages_22_25_employment_stock",
            "controls": "none",
            "comparison_to_BCC": "independent_CPS_analogue_not_ADP_replication",
        })
    target_if = np.zeros((len(start), len(labels)))
    target_if[keep] = influence_local
    return rows, keep, target_if


def panel_design(quintiles: np.ndarray, webb_z: np.ndarray, families: np.ndarray,
                 months: list[str], structure: str, contrast: str,
                 webb_rule: str, family_reference: str):
    n_occ, n_month = len(quintiles), len(months)
    post = np.asarray([month >= "2023-01" for month in months], bool)
    q = np.repeat(quintiles, n_month)
    row_post = np.tile(post, n_occ)
    if contrast == "Q5_vs_Q1":
        columns = [((q == value) & row_post).astype(float) for value in range(2, 6)]
        labels = [f"Q{value}_x_post" for value in range(2, 6)]
        target = 3
    elif contrast == "top_two_vs_bottom_three":
        columns = [((q >= 4) & row_post).astype(float)]
        labels = ["top_two_vs_bottom_three_x_post"]
        target = 0
    else:
        raise ValueError(f"unknown panel contrast {contrast}")
    if webb_rule == "with_Webb_YAX_extension":
        columns.append(np.repeat(webb_z, n_month) * row_post)
        labels.append("Webb_z_x_post")
    elif webb_rule != "no_Webb_public_benchmark":
        raise ValueError(f"unknown Webb rule {webb_rule}")
    if structure == "family_post":
        for family in sorted(set(families.tolist())):
            if family == family_reference:
                continue
            columns.append((np.repeat(families == family, n_month) & row_post).astype(float))
            labels.append(f"SOC2_{family}_x_post")
    occupation_codes = np.repeat(np.arange(n_occ), n_month)
    family_levels = {value: index for index, value in
                     enumerate(sorted(set(families.tolist())))}
    family_codes = np.repeat(np.asarray([family_levels[value] for value in families], int),
                             n_month)
    first = occupation_codes.astype(object)
    if structure in {"pooled", "family_post"}:
        second = np.tile(np.arange(n_month), n_occ).astype(object)
    elif structure == "family_month":
        second = (family_codes * n_month + np.tile(np.arange(n_month), n_occ)).astype(object)
    else:
        raise ValueError(f"unknown structure {structure}")
    return CORE.ModelDesign(
        structure=structure, regressors=np.column_stack(columns), first_labels=first,
        second_labels=second, occupation_codes=occupation_codes,
        family_codes=family_codes, regressor_labels=tuple(labels),
        focal_target_index=target), labels, target


def fit_panel_model(model_id: str, young: np.ndarray, older: np.ndarray,
                    keep: np.ndarray, quintiles: np.ndarray, webb_z: np.ndarray,
                    families: np.ndarray, occupations: np.ndarray, months: list[str],
                    structure: str, contrast: str, webb_rule: str,
                    family_reference: str, multipliers: dict[str, np.ndarray],
                    population: str) -> dict[str, Any]:
    design, labels, target = panel_design(
        quintiles[keep], webb_z[keep], families[keep], months, structure,
        contrast, webb_rule, family_reference)
    fit = CORE.fit_with_influence(
        ENGINE, young[keep].reshape(-1),
        (young[keep] + older[keep]).reshape(-1), design)
    estimate = float(fit.beta[target])
    occ_influence = np.zeros(len(occupations))
    occ_influence[keep] = fit.occupation_influence[:, target]
    global_families = sorted(set(families.tolist()))
    family_influence = np.zeros(len(global_families))
    local_families = sorted(set(families[keep].tolist()))
    family_lookup = {value: index for index, value in enumerate(global_families)}
    for index, family in enumerate(local_families):
        family_influence[family_lookup[family]] = fit.family_influence[index, target]
    occ = CORE.multiplier_interval(estimate, occ_influence, multipliers["occupation"])
    fam = CORE.multiplier_interval(estimate, family_influence, multipliers["family"])
    row = {
        "model_id": model_id, "population": population, "contrast": contrast,
        "structure": structure, "Webb_rule": webb_rule,
        "coefficient_label": labels[target], "coefficient": estimate,
        "occupation_se": occ["se"], "occupation_ci_lower": occ["lower"],
        "occupation_ci_upper": occ["upper"], "occupation_multiplier_p": occ["p_value"],
        "family_se": fam["se"], "family_ci_lower": fam["lower"],
        "family_ci_upper": fam["upper"], "family_multiplier_p": fam["p_value"],
        "support_occupations": int(keep.sum()),
        "support_hash_sha256": support_hash(occupations[keep]),
        "calendar_months": len(months), "transition_month_excluded": True,
        "family_post_reference": family_reference if structure == "family_post" else "",
        "regressor_labels_json": json.dumps(labels),
        "iterations": fit.iterations,
        "maximum_normalized_score": fit.maximum_normalized_score,
        "separated_observations": fit.separated_observation_count,
        "bridge_status": "separate_YAX_young_relative_extension_not_BCC_replication",
        "fixed_equal_occupation_exposure_labels": True,
    }
    return {"row": row, "occupation_influence": occ_influence,
            "family_influence": family_influence}


def paired_panel_row(comparison: str, left: dict[str, Any], right: dict[str, Any],
                     multipliers: dict[str, np.ndarray]) -> dict[str, Any]:
    estimate = left["row"]["coefficient"] - right["row"]["coefficient"]
    occ_if = left["occupation_influence"] - right["occupation_influence"]
    fam_if = left["family_influence"] - right["family_influence"]
    occ = CORE.multiplier_interval(estimate, occ_if, multipliers["occupation"])
    fam = CORE.multiplier_interval(estimate, fam_if, multipliers["family"])
    return {
        "comparison": comparison, "left_model": left["row"]["model_id"],
        "right_model": right["row"]["model_id"],
        "estimate_left_minus_right": float(estimate),
        "occupation_paired_se": occ["se"],
        "occupation_paired_ci_lower": occ["lower"],
        "occupation_paired_ci_upper": occ["upper"],
        "occupation_paired_multiplier_p": occ["p_value"],
        "family_paired_se": fam["se"], "family_paired_ci_lower": fam["lower"],
        "family_paired_ci_upper": fam["upper"],
        "family_paired_multiplier_p": fam["p_value"],
        "common_draws_preserve_covariance": True,
        "interpretation_if_interval_contains_zero":
            "the design does not detect a difference; not economic equivalence",
    }


def differences_rows() -> list[dict[str, Any]]:
    return [
        {"dimension": "data_source_and_unit",
         "BCC_public_or_ADP_target": "ADP worker-firm matches or annual ACS persons",
         "this_run": "monthly Basic CPS weighted persons aggregated to occupation-month",
         "aligned": False, "reason": "ADP employer panel and ACS survey design are unavailable here"},
        {"dimension": "age", "BCC_public_or_ADP_target": "22-25",
         "this_run": "22-25 for benchmark; 26-65 only in separate YAX extension",
         "aligned": True, "reason": "exact young age band aligned"},
        {"dimension": "employment_population",
         "BCC_public_or_ADP_target": "full-time positive-earnings ADP matches; ACS full-time civilian wage/salary sensitivity",
         "this_run": "all employed and feasible full-time civilian wage/salary CPS analogue",
         "aligned": "partial", "reason": "CPS has usual hours/class but no balanced-firm or positive-payroll-match condition"},
        {"dimension": "exposure_membership",
         "BCC_public_or_ADP_target": "Eloundou beta quintiles on undisclosed exhaustive BCC universe",
         "this_run": "equal-occupation tie-preserving beta quintiles on fixed YAX 468 support",
         "aligned": False, "reason": "complete BCC membership and tie algorithm are not public"},
        {"dimension": "endpoint",
         "BCC_public_or_ADP_target": "November 2022-June 2026 and annual 2022-2024",
         "this_run": "same named endpoints; CPS 2022 is a 12-month stock average",
         "aligned": "named_dates_only", "reason": "monthly CPS and annual ACS measurement differ"},
        {"dimension": "controls",
         "BCC_public_or_ADP_target": "no controls for public long difference; proprietary firm controls elsewhere",
         "this_run": "no controls first; Webb and family conditioning separately labeled",
         "aligned": True, "reason": "no inaccessible control is represented as reproduced"},
        {"dimension": "inference",
         "BCC_public_or_ADP_target": "HC robust for ADP long difference; ACS successive-difference replicate weights",
         "this_run": "HC1 for CPS occupation long difference; occupation/family multiplier inference for YAX extension",
         "aligned": "partial", "reason": "CPS extract has no design replicate weights"},
    ]


def findings_text(aggregate_rows: list[dict[str, Any]],
                  long_rows: list[dict[str, Any]],
                  model_rows: list[dict[str, Any]],
                  paired_rows: list[dict[str, Any]],
                  common_support_count: int) -> str:
    aggregate = pd.DataFrame(aggregate_rows)
    models = pd.DataFrame(model_rows)
    pairs = pd.DataFrame(paired_rows)
    lines = [
        "# Gate 4 public benchmark and population-alignment findings", "",
        "Status: post-outcome exploratory; the frozen v1.1 design is unchanged.", "",
        "## Public stock benchmarks", "",
        "These are independent CPS analogues using equal-occupation Rule-A beta quintiles on the fixed YAX support. They are not exact BCC occupation memberships, an ADP replication, or CPS design-based estimates.", "",
        "| population | endpoint | contrast | estimate | occupation-linearized 95% interval |",
        "|---|---|---|---:|---:|",
    ]
    shown = aggregate.loc[aggregate.population.isin(POPULATIONS)]
    for row in shown.itertuples(index=False):
        lines.append(
            f"| `{row.population}` | `{row.endpoint}` | `{row.contrast}` | "
            f"{float(row.estimate):.4f} | [{float(row.occupation_multiplier_ci_lower):.4f}, "
            f"{float(row.occupation_multiplier_ci_upper):.4f}] |")
    lines.extend([
        "", "The annual CPS comparison averages all twelve months of 2022 and all twelve months of 2024. December 2022 remains excluded from the separately defined YAX post models.", "",
        "## Occupation long differences", "",
        "The no-control occupation regressions use baseline employment-stock weights and HC1 heteroskedastic-robust standard errors, matching the public regression form as far as CPS and the reconstructed membership permit.", "",
        "| population | endpoint | Q5-Q1 estimate | HC1 95% interval | occupations |",
        "|---|---|---:|---:|---:|",
    ])
    for row in long_rows:
        if row["coefficient_label"] != "Q5_vs_Q1":
            continue
        lines.append(
            f"| `{row['population']}` | `{row['endpoint']}` | {row['estimate']:.4f} | "
            f"[{row['normal_ci_lower']:.4f}, {row['normal_ci_upper']:.4f}] | "
            f"{row['support_occupations']} |")
    lines.extend([
        "", "## Separately defined young-relative CPS extension", "",
        f"All conditional rows use one common support of {common_support_count} occupations and identical exposure labels. The no-Webb rows are shown separately from the historical YAX Webb-control extension.", "",
        "| population | contrast | Webb rule | pooled | family-post | family-month |",
        "|---|---|---|---:|---:|---:|",
    ])
    for population in POPULATIONS:
        for contrast in CONTRASTS:
            for webb_rule in WEBB_RULES:
                cells = []
                for structure in STRUCTURES:
                    row = models.loc[
                        models.population.eq(population) & models.contrast.eq(contrast) &
                        models.Webb_rule.eq(webb_rule) & models.structure.eq(structure)]
                    require(len(row) == 1, "findings model cell is not unique")
                    value = row.iloc[0]
                    cells.append(f"{value.coefficient:.4f} [{value.occupation_ci_lower:.4f}, {value.occupation_ci_upper:.4f}]")
                lines.append(f"| `{population}` | `{contrast}` | `{webb_rule}` | " +
                             " | ".join(cells) + " |")
    binary_pairs = pairs.loc[
        pairs.comparison.eq("family_month_minus_pooled") &
        pairs.left_model.str.contains("top_two_vs_bottom_three")]
    lines.extend([
        "", "The top-two/bottom-three movement has its own paired influence distribution and intervals. No Q5-Q1 rejection or precision statement is transferred to that grouping.", "",
        "## Interpretation boundary", "",
        "Family conditioning, sample alignment, and the Webb control change descriptive estimands. A confidence interval containing zero means only that this design does not detect a difference; it does not establish equivalence. None of these comparisons reproduces unavailable BCC firm controls or identifies a causal AI effect.", "",
        f"The run retained {len(binary_pairs)} population/Webb-specific paired family-month-minus-pooled comparisons for the binary BCC-style grouping.", "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--microdata", type=Path, required=True)
    parser.add_argument("--repair-microdata", type=Path, required=True)
    parser.add_argument("--bridge", type=Path, required=True)
    parser.add_argument("--membership", type=Path, required=True)
    parser.add_argument("--private-calibration", type=Path, required=True)
    parser.add_argument("--calibration-receipt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output_dir.exists(), "refusing to overwrite public benchmark output")
    require(sha256_file(args.membership) == MAP.MEMBERSHIP_SHA256,
            "membership hash differs")
    require(sha256_file(args.bridge) == MAP.BRIDGE_SHA256, "bridge hash differs")
    calibration_receipt = json.loads(args.calibration_receipt.read_text(encoding="utf-8"))
    require(calibration_receipt.get("status") == "PASS_PRIVATE_CALIBRATION_BUILD",
            "private calibration receipt does not pass")
    require(sha256_file(args.private_calibration) ==
            calibration_receipt.get("private_npz_sha256"), "private calibration hash differs")
    require(sha256_file(args.microdata) ==
            calibration_receipt["input_hashes"]["wide_microdata"], "wide microdata hash differs")
    require(sha256_file(args.repair_microdata) ==
            calibration_receipt["input_hashes"]["march_repair"], "repair hash differs")

    with np.load(args.private_calibration, allow_pickle=False) as loaded:
        arrays = {name: loaded[name] for name in loaded.files}
    occupations = arrays["occupations"].astype(str)
    families = arrays["families"].astype(str)
    model_months = arrays["months"].astype(str).tolist()
    require(len(occupations) == 468 and len(model_months) == 113,
            "current protected contract dimensions differ")
    require("2022-12" not in model_months and "2025-10" not in model_months,
            "frozen calendar gaps differ")
    benchmark_months = sorted(set(model_months) | {"2022-12"})
    require(len(benchmark_months) == 114 and benchmark_months[0] == "2017-01" and
            benchmark_months[-1] == "2026-07", "benchmark calendar differs")
    membership = pd.read_csv(args.membership, dtype={"occupation_code": str},
                             float_precision="round_trip")
    membership["occupation_code"] = membership.occupation_code.str.zfill(4)
    membership = membership.set_index("occupation_code").reindex(occupations)
    require(not membership.isna().any().any(), "membership does not align")
    equal_quintiles, equal_cuts = equal_occupation_quintiles(
        membership.rule_A_beta.to_numpy(float))
    webb_z = membership.webb_z.to_numpy(float)

    routed, code_audit, counters = scan_sources(
        args.microdata, args.repair_microdata, args.bridge,
        set(occupations.tolist()), set(benchmark_months))
    young_benchmark = {population: stock_matrix(
        routed, occupations, benchmark_months, population, (22, 25))
        for population in POPULATIONS}
    young_model = {population: stock_matrix(
        routed, occupations, model_months, population, (22, 25))
        for population in POPULATIONS}
    older_model = {population: stock_matrix(
        routed, occupations, model_months, population, (26, 65))
        for population in POPULATIONS}

    n_cell = len(occupations) * len(model_months)
    protected = np.bincount(arrays["cellage"], weights=arrays["route_stock"],
                            minlength=2 * n_cell)
    expected_young = protected[:n_cell].reshape(len(occupations), len(model_months))
    expected_older = protected[n_cell:].reshape(len(occupations), len(model_months))
    calibration_gap = float(max(
        np.max(np.abs(young_model["all_employed"] - expected_young) /
               np.maximum(expected_young, 1.0)),
        np.max(np.abs(older_model["all_employed"] - expected_older) /
               np.maximum(expected_older, 1.0))))
    require(calibration_gap <= 1e-10, "all-employed calibration does not reproduce")

    global_families = sorted(set(families.tolist()))
    draws = CORE.draw_multiplier_matrices(
        DRAWS, len(occupations), len(global_families), SEED)
    multipliers = {"occupation": draws["occupation_rademacher"],
                   "family": draws["family_rademacher"]}
    signs = multipliers["occupation"]

    index_rows = indexed_stock_rows(young_benchmark, benchmark_months, equal_quintiles)
    endpoint_vectors = {
        "annual_mean_2022_to_2024": (
            np.asarray([month.startswith("2022-") for month in benchmark_months]),
            np.asarray([month.startswith("2024-") for month in benchmark_months])),
        "November_2022_to_June_2026": (
            np.asarray([month == "2022-11" for month in benchmark_months]),
            np.asarray([month == "2026-06" for month in benchmark_months])),
    }
    aggregate_rows: list[dict[str, Any]] = []
    aggregate_objects: dict[tuple[str, str, str], dict[str, Any]] = {}
    long_rows: list[dict[str, Any]] = []
    long_influences: list[tuple[str, np.ndarray]] = []
    support_audit = list(code_audit)
    for endpoint, (start_mask, end_mask) in endpoint_vectors.items():
        require(start_mask.any() and end_mask.any(), f"{endpoint} masks are empty")
        for population in POPULATIONS:
            values = young_benchmark[population]
            start = values[:, start_mask].mean(axis=1)
            end = values[:, end_mask].mean(axis=1)
            for contrast in ("Q5_vs_Q1_growth_factor_difference",
                             "top_two_vs_bottom_three_kept_pace"):
                result = aggregate_contrast(start, end, equal_quintiles, contrast, signs)
                aggregate_objects[(population, endpoint, contrast)] = result
                aggregate_rows.append({
                    "population": population, "endpoint": endpoint,
                    "contrast": contrast, "estimate": result["estimate"],
                    "high_growth_factor": result["high_growth_factor"],
                    "low_growth_factor": result["low_growth_factor"],
                    **{key: value for key, value in result.items()
                       if key not in {"estimate", "high_growth_factor", "low_growth_factor",
                                      "influence"}},
                    "grouping": "independent_equal_occupation_Rule_A_beta_approximation",
                    "BCC_exact_membership": False,
                    "inference_scope": "occupation-linearized descriptive interval; not CPS design-based",
                })
            rows, keep, influence = wls_long_difference(
                start, end, equal_quintiles, occupations, population, endpoint)
            long_rows.extend(rows)
            model_id = rows[0]["model_id"]
            long_influences.append((model_id, influence[:, 4]))
            for quintile in range(1, 6):
                mask = keep & (equal_quintiles == quintile)
                support_audit.append({
                    "audit_type": "long_difference_support", "population": population,
                    "endpoint": endpoint, "beta_quintile": quintile,
                    "occupation_count": int(mask.sum()),
                    "baseline_weighted_stock": float(start[mask].sum()),
                })
        for contrast in ("Q5_vs_Q1_growth_factor_difference",
                         "top_two_vs_bottom_three_kept_pace"):
            left = aggregate_objects[("full_time_civilian_wage_salary", endpoint, contrast)]
            right = aggregate_objects[("all_employed", endpoint, contrast)]
            estimate = left["estimate"] - right["estimate"]
            influence = left["influence"] - right["influence"]
            aggregate_rows.append({
                "population": "full_time_civilian_wage_salary_minus_all_employed",
                "endpoint": endpoint, "contrast": contrast,
                "estimate": float(estimate), "high_growth_factor": "",
                "low_growth_factor": "", **multiplier_summary(estimate, influence, signs),
                "grouping": "independent_equal_occupation_Rule_A_beta_approximation",
                "BCC_exact_membership": False,
                "inference_scope": "paired occupation-linearized sample-alignment difference",
            })

    pre = np.asarray([month <= "2022-11" for month in model_months], bool)
    common_keep = np.ones(len(occupations), bool)
    for population in POPULATIONS:
        common_keep &= young_model[population][:, pre].sum(axis=1) > 0
        common_keep &= older_model[population][:, pre].sum(axis=1) > 0
    require(common_keep.sum() > 10 and set(equal_quintiles[common_keep]) == {1, 2, 3, 4, 5},
            "conditional common support loses an exposure quintile")
    pre_stock = (young_model["all_employed"][:, pre] +
                 older_model["all_employed"][:, pre]).sum(axis=1)
    family_stock = {family: float(pre_stock[common_keep & (families == family)].sum())
                    for family in global_families}
    family_reference = max(family_stock, key=lambda value: (family_stock[value], value))
    for quintile in range(1, 6):
        mask = common_keep & (equal_quintiles == quintile)
        support_audit.append({
            "audit_type": "conditional_common_support", "population": "both_populations",
            "endpoint": "2017-01_to_2026-07_transition_excluded",
            "beta_quintile": quintile, "occupation_count": int(mask.sum()),
            "baseline_weighted_stock": float(pre_stock[mask].sum()),
        })

    models: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    model_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for population in POPULATIONS:
        for contrast in CONTRASTS:
            for webb_rule in WEBB_RULES:
                for structure in STRUCTURES:
                    model_id = f"{population}_{contrast}_{webb_rule}_{structure}"
                    try:
                        model = fit_panel_model(
                            model_id, young_model[population], older_model[population],
                            common_keep, equal_quintiles, webb_z, families, occupations,
                            model_months, structure, contrast, webb_rule,
                            family_reference, multipliers, population)
                    except Exception as error:
                        failures.append({"model_id": model_id, "error": repr(error)})
                        raise
                    models[(population, contrast, webb_rule, structure)] = model
                    model_rows.append(model["row"])
    paired_rows: list[dict[str, Any]] = []
    for population in POPULATIONS:
        for contrast in CONTRASTS:
            for webb_rule in WEBB_RULES:
                pooled = models[(population, contrast, webb_rule, "pooled")]
                family_post = models[(population, contrast, webb_rule, "family_post")]
                family_month = models[(population, contrast, webb_rule, "family_month")]
                paired_rows.extend([
                    paired_panel_row("family_post_minus_pooled", family_post, pooled,
                                     multipliers),
                    paired_panel_row("family_month_minus_pooled", family_month, pooled,
                                     multipliers),
                    paired_panel_row("family_month_minus_family_post", family_month,
                                     family_post, multipliers),
                ])
    for contrast in CONTRASTS:
        for webb_rule in WEBB_RULES:
            for structure in STRUCTURES:
                paired_rows.append(paired_panel_row(
                    "full_time_civilian_wage_salary_minus_all_employed",
                    models[("full_time_civilian_wage_salary", contrast, webb_rule, structure)],
                    models[("all_employed", contrast, webb_rule, structure)], multipliers))

    influence_rows: list[dict[str, Any]] = []
    for model in models.values():
        influence_rows.extend({
            "model_id": model["row"]["model_id"], "cluster_type": "occupation",
            "cluster_id": code, "target_influence": float(value),
        } for code, value in zip(occupations, model["occupation_influence"]))
        influence_rows.extend({
            "model_id": model["row"]["model_id"], "cluster_type": "SOC2_family",
            "cluster_id": family, "target_influence": float(value),
        } for family, value in zip(global_families, model["family_influence"]))
    for model_id, influence in long_influences:
        influence_rows.extend({
            "model_id": model_id, "cluster_type": "occupation",
            "cluster_id": code, "target_influence": float(value),
        } for code, value in zip(occupations, influence))

    require(len(model_rows) == 24 and len(paired_rows) == 36 and not failures,
            "conditional model inventory is incomplete")
    args.output_dir.mkdir(parents=True)
    outputs = {
        "INDEXED_STOCK_SERIES.csv": index_rows,
        "AGGREGATE_BENCHMARKS.csv": aggregate_rows,
        "LONG_DIFFERENCE_RESULTS.csv": long_rows,
        "CONDITIONAL_MODEL_RESULTS.csv": model_rows,
        "CONDITIONAL_PAIRED_COMPARISONS.csv": paired_rows,
        "SUPPORT_AND_POPULATION_AUDIT.csv": support_audit,
        "BENCHMARK_DIFFERENCES.csv": differences_rows(),
        "MODEL_INFLUENCE.csv": influence_rows,
    }
    for name, rows in outputs.items():
        write_csv(args.output_dir / name, rows)
    write_json(args.output_dir / "MODEL_FAILURES.json", failures)
    (args.output_dir / "FINDINGS.md").write_text(
        findings_text(aggregate_rows, long_rows, model_rows, paired_rows,
                      int(common_keep.sum())), encoding="utf-8")
    output_names = [*outputs, "MODEL_FAILURES.json", "FINDINGS.md"]
    receipt = {
        "schema_version": "yax-gate4-public-benchmark-v1",
        "status": "PASS_GATE4_PUBLIC_BENCHMARK",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                              text=True).strip(),
        "sge_job_id": os.environ.get("JOB_ID"),
        "requirements": ["B03", "B04"],
        "input_hashes": {
            "wide_microdata": sha256_file(args.microdata),
            "march_repair": sha256_file(args.repair_microdata),
            "bridge": sha256_file(args.bridge),
            "membership": sha256_file(args.membership),
            "private_calibration": sha256_file(args.private_calibration),
            "calibration_receipt": sha256_file(args.calibration_receipt),
            "specification": sha256_file(HERE / "PUBLIC_BENCHMARK_SPEC.md"),
            "runner": sha256_file(Path(__file__)),
        },
        "all_employed_calibration_maximum_relative_gap": calibration_gap,
        "support_occupations": len(occupations),
        "conditional_common_support_occupations": int(common_keep.sum()),
        "conditional_common_support_hash_sha256": support_hash(occupations[common_keep]),
        "model_calendar_months": len(model_months),
        "benchmark_calendar_months": len(benchmark_months),
        "annual_2022_month_count": int(sum(month.startswith("2022-")
                                             for month in benchmark_months)),
        "December_2022_in_annual_benchmark": "2022-12" in benchmark_months,
        "December_2022_in_conditional_models": "2022-12" in model_months,
        "October_2025_treated_as_collection_gap": "2025-10" not in benchmark_months,
        "grouping": {
            "name": "independent_equal_occupation_Rule_A_beta_approximation",
            "cuts": equal_cuts.tolist(), "tie_rule": "cut_value_stays_in_lower_bin",
            "BCC_exact_membership": False,
        },
        "population_rule": {
            "wage_salary_CLASSWKR_codes": sorted(WAGE_SALARY_CODES),
            "armed_forces_code_excluded": 26,
            "full_time_rule": "35 <= UHRSWORKT < 997",
            "ADP_balanced_firm_or_positive_earnings_match_reproduced": False,
        },
        "model_count": len(model_rows), "paired_model_comparison_count": len(paired_rows),
        "aggregate_row_count": len(aggregate_rows),
        "long_difference_row_count": len(long_rows),
        "model_failure_count": len(failures), "draws": DRAWS, "seed": SEED,
        "common_draws_preserve_covariance": True,
        "scan_counters": counters,
        "person_or_household_identifiers_read": False,
        "protected_person_rows_written": False,
        "output_hashes": {name: sha256_file(args.output_dir / name)
                          for name in output_names},
    }
    write_json(args.output_dir / "EXECUTION_RECEIPT.json", receipt)
    print(json.dumps({"status": receipt["status"], "models": len(model_rows),
                      "paired": len(paired_rows), "aggregate": len(aggregate_rows)},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
