#!/usr/bin/env python3
"""Run sampling-oriented household refits and a finite-sample stress simulation.

POST-OUTCOME EXPLORATORY.  Outputs contain aggregate statistics only; no CPS
identifier or microdata row is serialized.
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
ROOT = HERE.parents[3]
LABEL = "POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1"
MARCH_MONTHS = {f"{year}-03" for year in range(2017, 2022)}
HOUSEHOLD_SEED = 2026090551
SIMULATION_SEED = 2026090561
Z975 = 1.959963984540054
Z80 = 0.8416212335729143
BASELINE_CHECKPOINT = -0.1321094507921903


def import_path(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


FROZEN = import_path("yax_r3_survey_frozen", ROOT / "yax/analysis/run_frozen_v11.py")
ENGINE = FROZEN.ENGINE


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


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


def write_json(path: pathlib.Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def month_range(start_year: int, start_month: int, end_year: int, end_month: int) -> list[str]:
    result = []
    year, month = start_year, start_month
    while (year, month) <= (end_year, end_month):
        result.append(f"{year:04d}-{month:02d}")
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return result


def month_string(frame: pd.DataFrame) -> pd.Series:
    return (
        pd.to_numeric(frame.YEAR, errors="raise").astype(int).astype(str)
        + "-"
        + pd.to_numeric(frame.MONTH, errors="raise").astype(int).astype(str).str.zfill(2)
    )


def weighted_contract(values: np.ndarray, weights: np.ndarray) -> tuple[np.ndarray, np.ndarray, float, float]:
    if len(values) == 0 or len(values) != len(weights):
        raise ValueError("weighted contract inputs are empty or misaligned")
    if np.any(~np.isfinite(values)) or np.any(~np.isfinite(weights)) or np.any(weights <= 0):
        raise ValueError("weighted contract requires finite values and positive weights")
    order = np.argsort(values, kind="mergesort")
    cumulative = np.cumsum(weights[order])
    cuts = np.array([
        values[order[min(np.searchsorted(cumulative, share * cumulative[-1], side="left"), len(values) - 1)]]
        for share in (0.2, 0.4, 0.6, 0.8)
    ])
    if np.any(cuts[:-1] >= cuts[1:]):
        raise RuntimeError(f"collapsed bootstrap quintile cuts: {cuts.tolist()}")
    groups = np.searchsorted(cuts, values, side="left") + 1
    mean = float(np.average(values, weights=weights))
    sd = float(np.sqrt(np.average(np.square(values - mean), weights=weights)))
    if not np.isfinite(sd) or sd <= 0:
        raise RuntimeError("invalid bootstrap Webb normalization")
    return groups.astype(int), cuts, mean, sd


def load_contract(path: pathlib.Path, computerization: pathlib.Path) -> dict:
    frame = pd.read_csv(path, dtype={"occupation_code": str})
    frame["occupation_code"] = frame.occupation_code.str.zfill(4)
    frame = frame.loc[frame.contract.eq("rebuilt_corrected_preperiod_weight")].copy()
    if len(frame) != 468 or frame.occupation_code.duplicated().any():
        raise RuntimeError("unexpected rebuilt corrected treatment contract")
    frame = frame.sort_values("occupation_code", kind="mergesort").reset_index(drop=True)
    _, names, major_map = FROZEN.comp_maps(computerization)
    majors = np.array([major_map.get(code, "MISSING") for code in frame.occupation_code], object)
    if "MISSING" in majors:
        raise RuntimeError("SOC2 missing from corrected support")
    return {
        "frame": frame,
        "support": frame.occupation_code.tolist(),
        "beta": frame.rule_A_beta.to_numpy(float),
        "fixed_quintiles": frame.beta_quintile.to_numpy(int),
        "webb": frame.webb_pct_software.to_numpy(float),
        "fixed_webb_z": frame.webb_z.to_numpy(float),
        "construction_weight": frame.construction_weight.to_numpy(float),
        "majors": majors,
        "names": names,
    }


def validate_march_gate(args) -> dict:
    receipt = json.loads(args.march_audit_receipt.read_text(encoding="utf-8"))
    if receipt.get("status") != "PASS_FUNCTIONAL_REPLACEMENT":
        raise RuntimeError("March replacement audit is not PASS_FUNCTIONAL_REPLACEMENT")
    for key, path in (("wide", args.microdata), ("repair", args.repair_microdata)):
        expected = receipt.get("input_hashes", {}).get(key)
        observed = sha256(path)
        if expected != observed:
            raise RuntimeError(f"{key} hash differs from passed March audit")
    return receipt


def build_route_contributions(args, contract: dict) -> dict:
    """Build nonserialized source-record descendants for exact cell refits."""
    support = contract["support"]
    occ_index = {code: index for index, code in enumerate(support)}
    months = [
        value for value in month_range(2017, 1, 2026, 7)
        if value not in {"2022-12", "2025-10"}
    ]
    if len(months) != 113:
        raise RuntimeError("internal static calendar is not 113 months")
    month_index = {value: index for index, value in enumerate(months)}
    n_month = len(months)
    n_cell = len(support) * n_month

    bridge = pd.read_csv(args.bridge, dtype={"census_2010": str, "census_2018": str})
    bridge["census_2010"] = bridge.census_2010.str.zfill(4)
    bridge["census_2018"] = bridge.census_2018.str.zfill(4)
    bridge["bridge_weight"] = pd.to_numeric(bridge.bridge_weight, errors="raise")
    bridge = bridge.loc[bridge.census_2018.isin(support)].copy()
    bridge_mass = bridge.groupby("census_2010").bridge_weight.sum()

    household_parts: list[np.ndarray] = []
    cellage_parts: list[np.ndarray] = []
    stock_parts: list[np.ndarray] = []
    respondent_parts: list[np.ndarray] = []
    counters = {
        "raw_rows": 0,
        "explicitly_excluded_wide_ASEC_March_rows": 0,
        "active_employed_age_22_65_source_records": 0,
        "active_source_records_with_nonpositive_CPSID": 0,
        "routed_descendant_rows_on_support": 0,
        "fractional_descendant_rows": 0,
        "repair_active_source_records": 0,
    }

    def append_routed(frame: pd.DataFrame, route_weight: np.ndarray) -> None:
        if frame.empty:
            return
        occ = frame.occ_code.map(occ_index)
        mm = frame.month.map(month_index)
        if occ.isna().any() or mm.isna().any():
            raise RuntimeError("routed contribution not in declared support/calendar")
        household = pd.to_numeric(frame.CPSID, errors="coerce")
        bad = household.isna() | household.le(0) | household.mod(1).ne(0)
        counters["active_source_records_with_nonpositive_CPSID"] += int(bad.sum())
        if bad.any():
            return
        age = pd.to_numeric(frame.AGE, errors="raise").to_numpy(int)
        group = np.where((age >= 22) & (age <= 25), 0, 1)
        cell = occ.to_numpy(int) * n_month + mm.to_numpy(int)
        cellage = group * n_cell + cell
        weight = pd.to_numeric(frame.WTFINL, errors="raise").to_numpy(float)
        route_weight = np.asarray(route_weight, float)
        household_parts.append(household.to_numpy(np.int64))
        cellage_parts.append(cellage.astype(np.int64))
        stock_parts.append(weight * route_weight)
        respondent_parts.append(route_weight)
        counters["routed_descendant_rows_on_support"] += len(frame)
        counters["fractional_descendant_rows"] += int(np.sum(~np.isclose(route_weight, 1.0)))

    usecols = ["YEAR", "MONTH", "CPSID", "AGE", "EMPSTAT", "OCC", "WTFINL"]
    for source_name, path in (("wide", args.microdata), ("repair", args.repair_microdata)):
        for chunk in pd.read_csv(path, usecols=usecols, chunksize=400_000):
            counters["raw_rows"] += len(chunk)
            chunk["month"] = month_string(chunk)
            if source_name == "wide":
                bad_march = chunk.month.isin(MARCH_MONTHS)
                counters["explicitly_excluded_wide_ASEC_March_rows"] += int(bad_march.sum())
                chunk = chunk.loc[~bad_march].copy()
            else:
                if not set(chunk.month.unique()).issubset(MARCH_MONTHS):
                    raise RuntimeError("repair file contains a non-repair month")
            if chunk.empty:
                continue
            age = pd.to_numeric(chunk.AGE, errors="coerce")
            weight = pd.to_numeric(chunk.WTFINL, errors="coerce")
            employed = pd.to_numeric(chunk.EMPSTAT, errors="coerce").isin([10, 12])
            occ = pd.to_numeric(chunk.OCC, errors="coerce")
            keep = (
                age.between(22, 65) & employed & np.isfinite(weight) & weight.gt(0)
                & occ.notna() & occ.between(0, 9999) & occ.mod(1).eq(0)
                & chunk.month.isin(month_index)
            )
            chunk = chunk.loc[keep].copy()
            if chunk.empty:
                continue
            chunk["AGE"] = age.loc[chunk.index].astype(int)
            chunk["WTFINL"] = weight.loc[chunk.index].astype(float)
            chunk["source_occ"] = occ.loc[chunk.index].astype(int).map(lambda value: f"{value:04d}")
            counters["active_employed_age_22_65_source_records"] += len(chunk)
            if source_name == "repair":
                counters["repair_active_source_records"] += len(chunk)

            early = chunk.loc[chunk.YEAR.le(2019)].merge(
                bridge, left_on="source_occ", right_on="census_2010", how="inner", validate="many_to_many"
            )
            if not early.empty:
                early["occ_code"] = early.census_2018
                append_routed(early, early.bridge_weight.to_numpy(float))
            current = chunk.loc[chunk.YEAR.ge(2020) & chunk.source_occ.isin(support)].copy()
            if not current.empty:
                current["occ_code"] = current.source_occ
                append_routed(current, np.ones(len(current)))

    if counters["active_source_records_with_nonpositive_CPSID"]:
        raise RuntimeError("positive analysis record has unavailable CPSID; no fallback permitted")
    household_id = np.concatenate(household_parts)
    cellage = np.concatenate(cellage_parts)
    stock = np.concatenate(stock_parts)
    respondent = np.concatenate(respondent_parts)
    households, household_code = np.unique(household_id, return_inverse=True)
    del household_id
    if np.any(~np.isfinite(stock)) or np.any(stock <= 0):
        raise RuntimeError("route stock contains invalid contributions")
    if np.any(respondent <= 0) or np.any(~np.isfinite(respondent)):
        raise RuntimeError("route respondent-equivalent contains invalid contributions")

    stock_by_age_cell = np.bincount(cellage, weights=stock, minlength=2 * n_cell)
    respondent_by_age_cell = np.bincount(cellage, weights=respondent, minlength=2 * n_cell)
    weight_square_by_age_cell = np.bincount(cellage, weights=np.square(stock), minlength=2 * n_cell)
    young = stock_by_age_cell[:n_cell].reshape(len(support), n_month)
    older = stock_by_age_cell[n_cell:].reshape(len(support), n_month)
    resp_young = respondent_by_age_cell[:n_cell].reshape(len(support), n_month)
    resp_older = respondent_by_age_cell[n_cell:].reshape(len(support), n_month)
    w2_young = weight_square_by_age_cell[:n_cell].reshape(len(support), n_month)
    w2_older = weight_square_by_age_cell[n_cell:].reshape(len(support), n_month)

    # Count distinct observed analysis months per contributing linked household.
    route_cell = cellage % n_cell
    route_month = route_cell % n_month
    unique_household_month = np.unique(household_code.astype(np.int64) * n_month + route_month)
    visit_counts = np.bincount((unique_household_month // n_month).astype(int), minlength=len(households))
    counters.update({
        "analysis_contributing_CPSID_units": len(households),
        "CPSID_units_observed_more_than_one_analysis_month": int(np.sum(visit_counts > 1)),
        "CPSID_analysis_month_visits_median": float(np.median(visit_counts)),
        "CPSID_analysis_month_visits_p95": float(np.quantile(visit_counts, .95)),
        "CPSID_analysis_month_visits_maximum": int(visit_counts.max()),
        "bridge_sources_on_support": int(bridge.census_2010.nunique()),
        "bridge_mass_minimum_on_support": float(bridge_mass.min()),
        "bridge_mass_maximum_on_support": float(bridge_mass.max()),
        "static_months": n_month,
        "support_occupations": len(support),
        "route_stock_total": float(stock.sum()),
        "respondent_equivalent_total": float(respondent.sum()),
    })
    return {
        "months": months,
        "household_code": household_code.astype(np.int32),
        "cellage": cellage.astype(np.int32),
        "stock": stock,
        "respondent": respondent,
        "household_count": len(households),
        "young": young,
        "older": older,
        "resp_young": resp_young,
        "resp_older": resp_older,
        "w2_young": w2_young,
        "w2_older": w2_older,
        "counters": counters,
    }


def model_design(quintiles: np.ndarray, webb_z: np.ndarray, majors: np.ndarray,
                 construction_weight: np.ndarray, months: list[str]) -> tuple[np.ndarray, np.ndarray, str]:
    n_occ, n_month = len(quintiles), len(months)
    post = np.array([value >= "2023-01" for value in months])
    base = np.column_stack([
        ((((quintiles == q)[:, None]) & post[None, :]).reshape(-1)).astype(float)
        for q in (2, 3, 4, 5)
    ] + [(webb_z[:, None] * post[None, :]).reshape(-1)])
    levels = sorted(set(majors.tolist()))
    totals = {level: float(construction_weight[majors == level].sum()) for level in levels}
    reference = max(levels, key=lambda value: (totals[value], value))
    family = [
        ((((majors == level)[:, None]) & post[None, :]).reshape(-1)).astype(float)
        for level in levels if level != reference
    ]
    conditional = np.column_stack([base, *family])
    if base.shape != (n_occ * n_month, 5):
        raise RuntimeError("baseline design shape mismatch")
    return base, conditional, reference


def fit_one(young: np.ndarray, older: np.ndarray, regressors: np.ndarray):
    n_occ, n_month = young.shape
    total = (young + older).reshape(-1)
    occupation = np.repeat(np.arange(n_occ), n_month)
    month = np.tile(np.arange(n_month), n_occ)
    fit = ENGINE.fit_grouped_logit_fe(
        young.reshape(-1), total, occupation, month, regressors, max_iterations=5000
    )
    if not fit.converged:
        raise RuntimeError("grouped-binomial refit did not converge")
    return fit


def fit_pair(young: np.ndarray, older: np.ndarray, quintiles: np.ndarray,
             webb_z: np.ndarray, contract: dict, months: list[str]) -> dict:
    base_x, conditional_x, reference = model_design(
        quintiles, webb_z, contract["majors"], contract["construction_weight"], months
    )
    base_fit = fit_one(young, older, base_x)
    conditional_fit = fit_one(young, older, conditional_x)
    return {
        "base_fit": base_fit,
        "conditional_fit": conditional_fit,
        "base_x": base_x,
        "conditional_x": conditional_x,
        "reference": reference,
        "baseline": float(base_fit.beta[3]),
        "SOC2_post": float(conditional_fit.beta[3]),
        "paired_movement": float(conditional_fit.beta[3] - base_fit.beta[3]),
    }


def cells_from_multiplier(routes: dict, multiplier: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n_cell = routes["young"].size
    weights = routes["stock"] * multiplier[routes["household_code"]]
    rebuilt = np.bincount(routes["cellage"], weights=weights, minlength=2 * n_cell)
    return rebuilt[:n_cell].reshape(routes["young"].shape), rebuilt[n_cell:].reshape(routes["older"].shape)


def household_bootstrap(args, routes: dict, contract: dict, observed: dict) -> tuple[list[dict], list[dict], dict]:
    rng = np.random.default_rng(HOUSEHOLD_SEED)
    pre = np.array([value <= "2022-11" for value in routes["months"]])
    rows: list[dict] = []
    failures: list[dict] = []
    for draw in range(1, args.household_draws + 1):
        multiplier = rng.exponential(scale=1.0, size=routes["household_count"])
        young, older = cells_from_multiplier(routes, multiplier)
        for mode in ("fixed_corrected_labels", "rebuilt_preperiod_labels"):
            if mode == "fixed_corrected_labels":
                quintiles = contract["fixed_quintiles"]
                webb_z = contract["fixed_webb_z"]
                changed = 0
                cuts = [np.nan] * 4
            else:
                weights = (young + older)[:, pre].sum(axis=1)
                try:
                    quintiles, cuts, _, _ = weighted_contract(contract["beta"], weights)
                    _, _, webb_mean, webb_sd = weighted_contract(contract["webb"], weights)
                    webb_z = (contract["webb"] - webb_mean) / webb_sd
                    changed = int(np.sum(quintiles != contract["fixed_quintiles"]))
                except Exception as error:
                    failures.append({"workstream": "INF-03", "draw": draw, "classification_mode": mode, "stage": "classification", "error": repr(error)})
                    continue
            try:
                result = fit_pair(young, older, quintiles, webb_z, contract, routes["months"])
            except Exception as error:
                failures.append({"workstream": "INF-03", "draw": draw, "classification_mode": mode, "stage": "full_refit", "error": repr(error)})
                continue
            rows.append({
                "analysis_status": LABEL,
                "draw": draw,
                "classification_mode": mode,
                "baseline_coefficient": result["baseline"],
                "SOC2_post_coefficient": result["SOC2_post"],
                "SOC2_minus_baseline": result["paired_movement"],
                "baseline_iterations": result["base_fit"].iterations,
                "SOC2_post_iterations": result["conditional_fit"].iterations,
                "occupations_reclassified": changed,
                "q1_cut": cuts[0], "q2_cut": cuts[1], "q3_cut": cuts[2], "q4_cut": cuts[3],
                "minimum_household_multiplier": float(multiplier.min()),
                "maximum_household_multiplier": float(multiplier.max()),
                "mean_household_multiplier": float(multiplier.mean()),
            })

    summaries: list[dict] = []
    observed_values = {
        "baseline": observed["baseline"],
        "SOC2_post": observed["SOC2_post"],
        "SOC2_minus_baseline": observed["paired_movement"],
    }
    for mode in ("fixed_corrected_labels", "rebuilt_preperiod_labels"):
        local = [row for row in rows if row["classification_mode"] == mode]
        for name, column in (
            ("baseline", "baseline_coefficient"),
            ("SOC2_post", "SOC2_post_coefficient"),
            ("SOC2_minus_baseline", "SOC2_minus_baseline"),
        ):
            values = np.array([row[column] for row in local], float)
            observed_value = observed_values[name]
            shifts = values - observed_value
            se = float(np.std(shifts, ddof=1))
            q025, q975 = np.quantile(shifts, [.025, .975])
            summaries.append({
                "analysis_status": LABEL,
                "classification_mode": mode,
                "object": name,
                "observed_coefficient": observed_value,
                "requested_draws": args.household_draws,
                "successful_full_refits": len(values),
                "sampling_oriented_SE": se,
                "mean_full_refit_shift": float(np.mean(shifts)),
                "basic_CI_lower": observed_value - q975,
                "basic_CI_upper": observed_value - q025,
                "normal_theory_MDE80_from_sampling_SE": (Z975 + Z80) * se,
                "SE_monte_carlo_error_approx": se / math.sqrt(2 * max(len(values) - 1, 1)),
                "tail_probability_resolution": 1.0 / (len(values) + 1),
                "design_based_CPS_interval": False,
                "mechanically_combined_with_occupation_cluster_variance": False,
            })
    reclassified = np.array([
        row["occupations_reclassified"] for row in rows
        if row["classification_mode"] == "rebuilt_preperiod_labels"
    ], float)
    diagnostics = {
        "requested_draws": args.household_draws,
        "successful_fixed_label_draws": sum(row["classification_mode"] == "fixed_corrected_labels" for row in rows),
        "successful_rebuilt_label_draws": len(reclassified),
        "failures": len([row for row in failures if row["workstream"] == "INF-03"]),
        "reclassified_occupations_median": float(np.median(reclassified)) if len(reclassified) else None,
        "reclassified_occupations_p95": float(np.quantile(reclassified, .95)) if len(reclassified) else None,
        "reclassified_occupations_maximum": int(reclassified.max()) if len(reclassified) else None,
        "sampling_unit": "positive CPSID linked household record across all observed months",
        "multiplier": "independent mean-one Exponential(1), common across months and route descendants",
        "design_based_inference": False,
    }
    return rows, summaries, {"diagnostics": diagnostics, "failures": failures}


def influence_concentration(young: np.ndarray, older: np.ndarray, x: np.ndarray) -> dict:
    fit, influence = FROZEN.fit_with_influence(young, older, x)
    squared = np.square(influence[:, 3])
    total = float(squared.sum())
    order = np.sort(squared)[::-1]
    return {
        "coefficient": float(fit.beta[3]),
        "occupation_cluster_SE": float(fit.standard_error[3]),
        "effective_occupation_influence_count": float(total * total / np.square(squared).sum()),
        "top_five_squared_influence_share": float(order[:5].sum() / total),
        "top_ten_squared_influence_share": float(order[:10].sum() / total),
    }


def dgp_objects(routes: dict, contract: dict, observed: dict) -> tuple[dict, dict]:
    young, older = routes["young"], routes["older"]
    total = (young + older).reshape(-1)
    y = young.reshape(-1)
    fit = observed["base_fit"]
    probability = np.clip(fit.fitted_probability, 1e-8, 1 - 1e-8)
    eta = np.log(probability / (1 - probability))
    target = observed["base_x"][:, 3]
    nuisance_eta = eta - target * observed["baseline"]
    residual = y - total * probability
    information = total * probability * (1 - probability)

    levels = sorted(set(contract["majors"].tolist()))
    level_index = {level: index for index, level in enumerate(levels)}
    occ_family = np.array([level_index[value] for value in contract["majors"]], int)
    n_family, n_month = len(levels), len(routes["months"])
    cell_family = np.repeat(occ_family, n_month)
    cell_month = np.tile(np.arange(n_month), len(contract["support"]))
    family_month = cell_family * n_month + cell_month
    numerator = np.bincount(family_month, weights=residual, minlength=n_family * n_month)
    denominator = np.bincount(family_month, weights=information, minlength=n_family * n_month)
    raw = np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator > 0)
    residualized = ENGINE._weighted_absorb(
        raw[:, None], np.maximum(denominator, 1e-12),
        np.repeat(np.arange(n_family), n_month), np.tile(np.arange(n_month), n_family),
        n_family, n_month,
    )[:, 0].reshape(n_family, n_month)

    sum_square = (routes["w2_young"] + routes["w2_older"]).reshape(-1)
    n_eff = np.divide(np.square(total), sum_square, out=np.zeros_like(total), where=sum_square > 0)
    n_integer = np.where(total > 0, np.maximum(1, np.rint(n_eff).astype(np.int64)), 0)
    positive = total > 0
    sparse = n_eff[positive]
    diagnostics = {
        "positive_total_cells": int(positive.sum()),
        "zero_total_cells": int((~positive).sum()),
        "one_sided_young_zero_cells": int(np.sum(positive & np.isclose(y, 0))),
        "one_sided_older_zero_cells": int(np.sum(positive & np.isclose(total - y, 0))),
        "Kish_n_eff_minimum": float(sparse.min()),
        "Kish_n_eff_p01": float(np.quantile(sparse, .01)),
        "Kish_n_eff_p05": float(np.quantile(sparse, .05)),
        "Kish_n_eff_median": float(np.median(sparse)),
        "Kish_n_eff_p95": float(np.quantile(sparse, .95)),
        "cells_Kish_n_eff_below_5": int(np.sum(sparse < 5)),
        "cells_Kish_n_eff_below_10": int(np.sum(sparse < 10)),
        "cells_Kish_n_eff_below_20": int(np.sum(sparse < 20)),
        "SOC2_families": n_family,
        "family_month_logit_shock_weighted_RMS": float(np.sqrt(np.average(np.square(residualized.reshape(-1)), weights=np.maximum(denominator, 1e-12)))),
        "family_month_logit_shock_max_abs": float(np.max(np.abs(residualized))),
        "baseline_influence": influence_concentration(young, older, observed["base_x"]),
        "SOC2_post_influence": influence_concentration(young, older, observed["conditional_x"]),
    }
    objects = {
        "total": total,
        "n_integer": n_integer,
        "nuisance_eta": nuisance_eta,
        "target": target,
        "family_shock": residualized,
        "occ_family": occ_family,
        "levels": levels,
    }
    return objects, diagnostics


def finite_sample_simulation(args, routes: dict, contract: dict, observed: dict,
                             failures: list[dict]) -> tuple[list[dict], list[dict], dict]:
    dgp, diagnostics = dgp_objects(routes, contract, observed)
    effects = (0.0, -0.05, observed["baseline"])
    rows: list[dict] = []
    total = dgp["total"]
    active = dgp["n_integer"] > 0
    n_month = len(routes["months"])
    shock_cell_family = np.repeat(dgp["occ_family"], n_month)
    for effect_index, effect in enumerate(effects):
        for replicate in range(1, args.simulation_draws + 1):
            # Reuse the same replicate seed across effects to align the family-sign stress.
            rng = np.random.default_rng(SIMULATION_SEED + replicate)
            signs = rng.choice(np.array([-1.0, 1.0]), size=len(dgp["levels"]))
            signed_family = signs[:, None] * dgp["family_shock"]
            shock = signed_family[shock_cell_family, np.tile(np.arange(n_month), len(contract["support"]))]
            eta = dgp["nuisance_eta"] + dgp["target"] * effect + shock
            probability = 1.0 / (1.0 + np.exp(-np.clip(eta, -700, 700)))
            count = np.zeros_like(dgp["n_integer"])
            count[active] = rng.binomial(dgp["n_integer"][active], probability[active])
            simulated_young = np.zeros_like(total)
            simulated_older = np.zeros_like(total)
            simulated_young[active] = total[active] * count[active] / dgp["n_integer"][active]
            # Construct the complementary stock from the complementary integer
            # count.  Subtracting the floating young stock from a very large
            # survey-weighted total can create a tiny negative roundoff error
            # when count==n; no pseudo-outcome is clipped here.
            simulated_older[active] = (
                total[active] * (dgp["n_integer"][active] - count[active])
                / dgp["n_integer"][active]
            )
            if np.any(simulated_young < 0) or np.any(simulated_older < 0):
                raise RuntimeError("integer-complement construction produced a negative stock")
            young = simulated_young.reshape(routes["young"].shape)
            older = simulated_older.reshape(routes["older"].shape)
            for model, x in (("baseline", observed["base_x"]), ("SOC2_post", observed["conditional_x"])):
                try:
                    fit = fit_one(young, older, x)
                    estimate = float(fit.beta[3])
                    se = float(fit.standard_error[3])
                    t = estimate / se
                    covered = abs((estimate - effect) / se) <= Z975
                    rejected = abs(t) > Z975
                    rows.append({
                        "analysis_status": LABEL,
                        "true_Q5_post_effect": effect,
                        "effect_label": ("null" if effect == 0 else "local_minus_0.05" if np.isclose(effect, -0.05) else "observed_checkpoint"),
                        "replicate": replicate,
                        "replicate_seed": SIMULATION_SEED + replicate,
                        "model": model,
                        "coefficient": estimate,
                        "occupation_cluster_SE": se,
                        "normal_95_CI_covers_true_effect": bool(covered),
                        "normal_two_sided_5pct_rejects_zero": bool(rejected),
                        "iterations": fit.iterations,
                    })
                except Exception as error:
                    failures.append({"workstream": "INF-05", "effect": effect, "replicate": replicate, "model": model, "stage": "simulation_full_refit", "error": repr(error)})

    summaries: list[dict] = []
    for effect in effects:
        for model in ("baseline", "SOC2_post"):
            local = [row for row in rows if np.isclose(row["true_Q5_post_effect"], effect) and row["model"] == model]
            estimate = np.array([row["coefficient"] for row in local], float)
            se = np.array([row["occupation_cluster_SE"] for row in local], float)
            coverage = np.array([row["normal_95_CI_covers_true_effect"] for row in local], float)
            rejection = np.array([row["normal_two_sided_5pct_rejects_zero"] for row in local], float)
            summaries.append({
                "analysis_status": LABEL,
                "true_Q5_post_effect": effect,
                "effect_label": local[0]["effect_label"] if local else "missing",
                "model": model,
                "requested_simulations": args.simulation_draws,
                "successful_full_refits": len(local),
                "mean_coefficient": float(estimate.mean()),
                "bias": float(estimate.mean() - effect),
                "empirical_SD": float(estimate.std(ddof=1)),
                "mean_reported_occupation_cluster_SE": float(se.mean()),
                "normal_95_CI_coverage": float(coverage.mean()),
                "coverage_monte_carlo_SE": float(math.sqrt(coverage.mean() * (1 - coverage.mean()) / len(coverage))),
                "normal_two_sided_5pct_rejection_of_zero": float(rejection.mean()),
                "rejection_monte_carlo_SE": float(math.sqrt(rejection.mean() * (1 - rejection.mean()) / len(rejection))),
                "RMSE": float(np.sqrt(np.mean(np.square(estimate - effect)))),
                "simulation_tail_probability_resolution": 1.0 / (len(local) + 1),
            })
    dgp_receipt = {
        "role": "calibrated finite-sample stress test; not full CPS design inference or an independently identified structural DGP",
        "effects": effects,
        "draws_per_effect": args.simulation_draws,
        "seed_rule": f"{SIMULATION_SEED} + replicate, common across effects",
        "sparse_sampling": "cell-level Binomial at rounded Kish effective record count; mapped back to observed weighted total",
        "broad_family_shock": "SOC2-family x month fitted score/information disturbance, family/month residualized, one sign per family over complete path",
        "support_and_labels": "fixed fully rebuilt corrected 468-occupation treatment contract",
        "inference_evaluated": "occupation-cluster sandwich normal 95% interval from each full grouped-binomial refit",
        "diagnostics": diagnostics,
    }
    return rows, summaries, dgp_receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--microdata", type=pathlib.Path, required=True)
    parser.add_argument("--repair-microdata", type=pathlib.Path, required=True)
    parser.add_argument("--bridge", type=pathlib.Path, required=True)
    parser.add_argument("--computerization", type=pathlib.Path, required=True)
    parser.add_argument("--treatment-contract", type=pathlib.Path, required=True)
    parser.add_argument("--march-audit-receipt", type=pathlib.Path, required=True)
    parser.add_argument("--analysis-spec", type=pathlib.Path, default=HERE / "INF03_INF05_ANALYSIS_SPEC.md")
    parser.add_argument("--household-draws", type=int, default=199)
    parser.add_argument("--simulation-draws", type=int, default=199)
    parser.add_argument("--output-dir", type=pathlib.Path, required=True)
    args = parser.parse_args()
    if args.household_draws < 5 or args.simulation_draws < 5:
        raise RuntimeError("refusing an uninformative run with fewer than five draws")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    march_receipt = validate_march_gate(args)
    contract = load_contract(args.treatment_contract, args.computerization)
    routes = build_route_contributions(args, contract)
    pre = np.array([value <= "2022-11" for value in routes["months"]])
    reconstructed_weight = (routes["young"] + routes["older"])[:, pre].sum(axis=1)
    maximum_weight_gap = float(np.max(np.abs(reconstructed_weight - contract["construction_weight"])))
    maximum_relative_weight_gap = float(np.max(np.abs(reconstructed_weight - contract["construction_weight"]) / np.maximum(contract["construction_weight"], 1.0)))
    if maximum_relative_weight_gap > 1e-10:
        raise RuntimeError(f"route rebuild does not reproduce treatment weights: {maximum_relative_weight_gap}")
    observed = fit_pair(
        routes["young"], routes["older"], contract["fixed_quintiles"],
        contract["fixed_webb_z"], contract, routes["months"]
    )
    if abs(observed["baseline"] - BASELINE_CHECKPOINT) > 5e-10:
        raise RuntimeError(f"unperturbed baseline checkpoint failed: {observed['baseline']}")

    household_rows, household_summary, household_extra = household_bootstrap(args, routes, contract, observed)
    failures = list(household_extra["failures"])
    simulation_rows, simulation_summary, dgp_receipt = finite_sample_simulation(
        args, routes, contract, observed, failures
    )

    write_csv(args.output_dir / "HOUSEHOLD_BOOTSTRAP_DRAWS.csv", household_rows)
    write_csv(args.output_dir / "HOUSEHOLD_BOOTSTRAP_SUMMARY.csv", household_summary)
    write_csv(args.output_dir / "FINITE_SAMPLE_SIMULATION_DRAWS.csv", simulation_rows)
    write_csv(args.output_dir / "FINITE_SAMPLE_SIMULATION_SUMMARY.csv", simulation_summary)
    write_json(args.output_dir / "FINITE_SAMPLE_DGP.json", dgp_receipt)
    write_json(args.output_dir / "MODEL_FAILURES.json", failures)
    feasibility = {
        "status": "FEASIBLE_AS_NONDSEIGN_CPSID_SENSITIVITY",
        "design_based_CPS_inference_available": False,
        "available_longitudinal_unit": "CPSID",
        "SERIAL_role": "within-year-month household identifier only; not used to preserve rotation dependence",
        "MISH_role": "rotation position; not treated as one of eight independent PSUs",
        "weight_treatment": "released WTFINL fixed; calibration and replicate-weight uncertainty not regenerated",
        "captured": "co-resident and repeated-month dependence within linked CPSID among analysis-contributing households",
        "omitted": "unavailable strata/PSU dependence, multistage selection, calibration/nonresponse-weight uncertainty, CPSID linkage error",
        "variance_combination": "not mechanically combined with occupation-cluster variance",
        "march_gate_status": march_receipt["status"],
        "route_and_unit_counts": routes["counters"],
        "classification_modes": ["fixed_corrected_labels", "rebuilt_preperiod_labels"],
        "bootstrap_diagnostics": household_extra["diagnostics"],
    }
    write_json(args.output_dir / "HOUSEHOLD_RESAMPLING_FEASIBILITY.json", feasibility)

    output_names = [
        "HOUSEHOLD_BOOTSTRAP_DRAWS.csv", "HOUSEHOLD_BOOTSTRAP_SUMMARY.csv",
        "FINITE_SAMPLE_SIMULATION_DRAWS.csv", "FINITE_SAMPLE_SIMULATION_SUMMARY.csv",
        "FINITE_SAMPLE_DGP.json", "MODEL_FAILURES.json", "HOUSEHOLD_RESAMPLING_FEASIBILITY.json",
    ]
    receipt = {
        "analysis_status": LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip(),
        "analysis_spec_sha256": sha256(args.analysis_spec),
        "inputs": {
            "microdata_sha256": sha256(args.microdata),
            "repair_microdata_sha256": sha256(args.repair_microdata),
            "bridge_sha256": sha256(args.bridge),
            "computerization_sha256": sha256(args.computerization),
            "treatment_contract_sha256": sha256(args.treatment_contract),
            "march_audit_receipt_sha256": sha256(args.march_audit_receipt),
        },
        "unperturbed_models": {
            "baseline": observed["baseline"],
            "SOC2_post": observed["SOC2_post"],
            "SOC2_minus_baseline": observed["paired_movement"],
            "baseline_occupation_cluster_SE": float(observed["base_fit"].standard_error[3]),
            "SOC2_post_occupation_cluster_SE": float(observed["conditional_fit"].standard_error[3]),
            "SOC2_reference_family": observed["reference"],
        },
        "treatment_weight_reproduction": {
            "maximum_absolute_gap": maximum_weight_gap,
            "maximum_relative_gap": maximum_relative_weight_gap,
        },
        "household_bootstrap": household_extra["diagnostics"],
        "simulation": {
            "draws_per_effect": args.simulation_draws,
            "effects": dgp_receipt["effects"],
            "DGP_role": dgp_receipt["role"],
        },
        "failure_count": len(failures),
        "nonrelease_assertion": "No raw or hashed household/person identifier, microdata row, or cell-level private stock is written.",
        "output_hashes": {name: sha256(args.output_dir / name) for name in output_names},
    }
    write_json(args.output_dir / "EXECUTION_RECEIPT.json", receipt)


if __name__ == "__main__":
    main()
