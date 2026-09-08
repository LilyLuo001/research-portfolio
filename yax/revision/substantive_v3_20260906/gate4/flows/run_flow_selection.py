#!/usr/bin/env python3
"""Build aggregate-only Gate 4 flow selection, bounds, and timing evidence."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
LEGACY_PATH = ROOT / "yax/revision/substantive_r3_20260905/flows/run_flows_outcomes.py"
SPEC_PATH = HERE / "FLOW_SELECTION_SPEC.md"
LABEL = "POST-OUTCOME REFEREE-DIRECTED FLOW SELECTION EXTENSION"
SEED = 202609089401
DRAWS = 9_999
WAGE_SALARY_CODES = {20, 21, 22, 23, 24, 25, 27, 28}
MARGINS = ("employment_exit", "unemployment_entry", "labor_force_exit")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


LEGACY = load_module("yax_gate4_flow_legacy", LEGACY_PATH)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


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


def load_frame(wide: Path, repair: Path, patch: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Use the certified R3 reconstruction while retaining EDUC for selection audit."""
    original = list(LEGACY.MICRODATA_COLUMNS)
    try:
        if "EDUC" not in LEGACY.MICRODATA_COLUMNS:
            LEGACY.MICRODATA_COLUMNS = [*LEGACY.MICRODATA_COLUMNS, "EDUC"]
        frame, receipt = LEGACY.load_corrected_frame(wide, repair, patch)
    finally:
        LEGACY.MICRODATA_COLUMNS = original
    require("EDUC" in frame, "authorized extract lacks EDUC required by the fixed audit")
    frame["EDUC"] = pd.to_numeric(frame.EDUC, errors="coerce").fillna(-1).astype(int)
    frame["education_group"] = np.select(
        [frame.EDUC.eq(111) | frame.EDUC.between(120, 125), frame.EDUC.between(2, 110)],
        ["BA_plus", "non_BA"], default="invalid",
    )
    frame["full_time_35plus"] = frame.UHRSWORKT.between(35, 99)
    frame["wage_salary_class"] = frame.CLASSWKR.isin(WAGE_SALARY_CODES)
    return frame, receipt


def horizon_contract(horizon: str) -> tuple[int, set[int], int, str]:
    if horizon == "adjacent_month":
        return 1, {1, 2, 3, 5, 6, 7}, 1, "LNKFW1MWT"
    if horizon == "twelve_month":
        return 12, {1, 2, 3, 4}, 4, "LNKFW1YWT"
    raise ValueError(horizon)


def period_label(month: pd.Series, horizon: str) -> pd.Series:
    if horizon == "adjacent_month":
        return pd.Series(np.select(
            [month.le("2022-11"), month.eq("2022-12"), month.ge("2023-01")],
            ["pre", "transition_2022_12", "post"], default="outside"), index=month.index)
    return pd.Series(np.select(
        [month.le("2021-11"), month.between("2021-12", "2022-12"), month.ge("2023-01")],
        ["pre", "straddling_or_transition", "post"], default="outside"), index=month.index)


def eligibility_accounting(frame: pd.DataFrame, horizon: str) -> tuple[pd.DataFrame, pd.DataFrame,
                                                                            list[dict[str, Any]]]:
    gap, allowed, _, weight = horizon_contract(horizon)
    observed = set(frame.month_ord.unique())
    candidates = frame.loc[frame.AGE.between(22, 65)].copy()
    candidates["target_ord"] = candidates.month_ord + gap
    candidates["period"] = period_label(candidates.month, horizon)
    candidates["origin_state"] = np.select(
        [candidates.employed, candidates.unemployed, candidates.nilf],
        ["employed", "unemployed", "not_in_labor_force"], default="other")
    target_absent = candidates.loc[~candidates.target_ord.isin(observed)]
    all_origins = candidates.loc[candidates.target_ord.isin(observed)].copy()
    all_origins["period"] = period_label(all_origins.month, horizon)
    all_origins["origin_state"] = np.select(
        [all_origins.employed, all_origins.unemployed, all_origins.nilf],
        ["employed", "unemployed", "not_in_labor_force"], default="other")
    all_origins["rotation_eligible"] = all_origins.MISH.isin(allowed)
    all_origins["identifier_eligible"] = all_origins.CPSIDV.ne(0)

    pairs, linked, _ = LEGACY.build_pairs(frame, horizon)
    pairs["period"] = period_label(pairs.month, horizon)
    pairs["origin_state"] = np.select(
        [pairs.employed, pairs.unemployed, pairs.nilf],
        ["employed", "unemployed", "not_in_labor_force"], default="other")

    statuses = [
        ("rotation_ineligible", ~all_origins.rotation_eligible),
        ("rotation_eligible_missing_identifier",
         all_origins.rotation_eligible & ~all_origins.identifier_eligible),
    ]
    rows: list[dict[str, Any]] = []
    for keys, group in target_absent.groupby(["period", "age_group", "origin_state"],
                                             observed=True):
        rows.append({
            "analysis_status": LABEL, "horizon": horizon,
            "eligibility_status": "target_calendar_month_absent",
            "period": keys[0], "age_group": keys[1], "origin_state": keys[2],
            "origin_records": int(len(group)), "origin_WTFINL": float(group.WTFINL.sum()),
            "official_link_weight": weight,
        })
    for status, mask in statuses:
        selected = all_origins.loc[mask]
        for keys, group in selected.groupby(["period", "age_group", "origin_state"], observed=True):
            rows.append({
                "analysis_status": LABEL, "horizon": horizon, "eligibility_status": status,
                "period": keys[0], "age_group": keys[1], "origin_state": keys[2],
                "origin_records": int(len(group)), "origin_WTFINL": float(group.WTFINL.sum()),
                "official_link_weight": weight,
            })
    pair_statuses = [
        ("eligible_no_validated_endpoint", ~pairs.validated_rotation),
        ("eligible_validated_zero_official_weight",
         pairs.validated_rotation & ~pairs.positive_official_weight),
        ("eligible_positive_official_weight_link", pairs.analysis_link),
    ]
    for status, mask in pair_statuses:
        selected = pairs.loc[mask]
        for keys, group in selected.groupby(["period", "age_group", "origin_state"], observed=True):
            rows.append({
                "analysis_status": LABEL, "horizon": horizon, "eligibility_status": status,
                "period": keys[0], "age_group": keys[1], "origin_state": keys[2],
                "origin_records": int(len(group)), "origin_WTFINL": float(group.WTFINL.sum()),
                "official_link_weight": weight,
            })
    return pairs, linked, rows


def route_origin_records(records: pd.DataFrame, bridge: pd.DataFrame,
                         qmap: dict[str, int], webb: dict[str, float]) -> pd.DataFrame:
    base = records.loc[records.employed & records.OCC.gt(0)].copy()
    base["source_occ"] = base.OCC.astype(int).map(lambda value: f"{value:04d}")
    base["source_record_id"] = np.arange(len(base), dtype=np.int64)
    early = base.loc[base.YEAR.le(2019)].merge(
        bridge[["census_2010", "census_2018", "bridge_weight"]],
        left_on="source_occ", right_on="census_2010", how="inner", validate="many_to_many")
    early["occ_code"] = early.census_2018
    early["route_fraction"] = early.bridge_weight
    current = base.loc[base.YEAR.ge(2020)].copy()
    current["occ_code"] = current.source_occ
    current["route_fraction"] = 1.0
    routed = pd.concat([early, current], ignore_index=True, sort=False)
    routed["quintile"] = routed.occ_code.map(qmap)
    routed["webb_z"] = routed.occ_code.map(webb)
    routed = routed.loc[routed.quintile.notna() & routed.webb_z.notna()].copy()
    routed["quintile"] = routed.quintile.astype(int)
    routed["origin_weight"] = routed.WTFINL * routed.route_fraction
    return routed


def transition_flags(frame: pd.DataFrame, horizon: str) -> dict[str, pd.Series]:
    employed_d = frame.employed_d.fillna(False).astype(bool)
    nonemployed_d = frame.nonemployed_d.fillna(False).astype(bool)
    unemployed_d = frame.unemployed_d.fillna(False).astype(bool)
    nilf_d = frame.nilf_d.fillna(False).astype(bool)
    taxonomy_ok = frame.month.ne("2019-12") if horizon == "adjacent_month" else frame.YEAR.ne(2019)
    outflow_risk = (employed_d & frame.OCC2010.gt(0) & frame.OCC2010_d.fillna(0).gt(0)
                    & taxonomy_ok)
    return {
        "employment_exit": nonemployed_d,
        "unemployment_entry": unemployed_d,
        "labor_force_exit": nilf_d,
        "occupational_outflow_risk": outflow_risk,
        "occupational_outflow": outflow_risk & frame.OCC2010.ne(frame.OCC2010_d),
    }


def baseline_rows(routed: pd.DataFrame, horizon: str) -> list[dict[str, Any]]:
    _, _, _, link_weight = horizon_contract(horizon)
    flags = transition_flags(routed, horizon)
    routed = routed.copy()
    routed["period"] = period_label(routed.month, horizon)
    routed["official_weight"] = routed[link_weight] * routed.route_fraction
    group_columns = ["period", "age_group", "quintile"]
    rows: list[dict[str, Any]] = []
    for keys, group in routed.groupby(group_columns, observed=True):
        eligible_weight = float(group.origin_weight.sum())
        retained = group.analysis_link
        retained_origin_weight = float(group.loc[retained, "origin_weight"].sum())
        rows.append({
            "analysis_status": LABEL, "horizon": horizon, "period": keys[0],
            "age_group": keys[1], "beta_quintile": int(keys[2]),
            "margin": "link_retention", "denominator": "eligible employed origin",
            "raw_fractional_risk": float(group.route_fraction.sum()),
            "raw_fractional_event": float(group.loc[retained, "route_fraction"].sum()),
            "risk_weight": eligible_weight, "event_weight": retained_origin_weight,
            "probability": retained_origin_weight / eligible_weight if eligible_weight else None,
            "weight_used": "origin WTFINL for both numerator and denominator",
        })
        linked = group.loc[retained]
        for margin in (*MARGINS, "occupational_outflow"):
            risk = (pd.Series(True, index=linked.index) if margin != "occupational_outflow"
                    else flags["occupational_outflow_risk"].loc[linked.index])
            event = flags[margin].loc[linked.index] & risk
            risk_weight = float(linked.loc[risk, "official_weight"].sum())
            event_weight = float(linked.loc[event, "official_weight"].sum())
            rows.append({
                "analysis_status": LABEL, "horizon": horizon, "period": keys[0],
                "age_group": keys[1], "beta_quintile": int(keys[2]), "margin": margin,
                "denominator": ("retained employed origin" if margin != "occupational_outflow"
                                else "retained employed origin, employed endpoint, valid same-taxonomy occupations"),
                "raw_fractional_risk": float(linked.loc[risk, "route_fraction"].sum()),
                "raw_fractional_event": float(linked.loc[event, "route_fraction"].sum()),
                "risk_weight": risk_weight, "event_weight": event_weight,
                "probability": event_weight / risk_weight if risk_weight else None,
                "weight_used": link_weight,
            })
    return rows


def balance_rows(routed: pd.DataFrame, horizon: str) -> list[dict[str, Any]]:
    data = routed.loc[routed.period.isin(["pre", "post"])].copy()
    data["link_status"] = np.where(data.analysis_link,
                                    "retained_positive_official_weight",
                                    "eligible_not_retained")
    characteristics = {
        "age_years": data.AGE.astype(float),
        "BA_plus": data.education_group.eq("BA_plus").astype(float),
        "full_time_35plus": data.full_time_35plus.astype(float),
        "wage_salary_class": data.wage_salary_class.astype(float),
    }
    for name, values in characteristics.items():
        data[name] = values
    rows: list[dict[str, Any]] = []
    groups = ["period", "age_group", "quintile", "link_status"]
    for keys, group in data.groupby(groups, observed=True):
        weight = group.origin_weight.to_numpy(float)
        for characteristic in characteristics:
            value = group[characteristic].to_numpy(float)
            rows.append({
                "analysis_status": LABEL, "horizon": horizon, "period": keys[0],
                "age_group": keys[1], "beta_quintile": int(keys[2]),
                "link_status": keys[3], "characteristic": characteristic,
                "weighted_mean": float(np.average(value, weights=weight)),
                "origin_WTFINL": float(weight.sum()),
                "raw_fractional_records": float(group.route_fraction.sum()),
                "comparison_weight": "origin WTFINL times bridge route fraction",
            })
    return rows


def poststratified_rows(routed: pd.DataFrame, horizon: str) -> tuple[list[dict[str, Any]],
                                                                    list[dict[str, Any]]]:
    _, _, _, link_weight = horizon_contract(horizon)
    data = routed.loc[routed.period.isin(["pre", "post"])].copy()
    flags = transition_flags(data, horizon)
    data["calendar_year"] = data.YEAR.astype(int)
    data["hours_group"] = np.where(data.full_time_35plus, "hours_35plus", "hours_under35_or_invalid")
    strata = ["AGE", "calendar_year", "MISH", "education_group", "hours_group"]
    result: list[dict[str, Any]] = []
    contrasts: list[dict[str, Any]] = []
    group_columns = ["period", "age_group", "quintile"]
    for keys, group in data.groupby(group_columns, observed=True):
        eligible = group.groupby(strata, observed=True).origin_weight.sum().rename("eligible_weight")
        linked = group.loc[group.analysis_link]
        linked_weight = linked.groupby(strata, observed=True).origin_weight.sum().rename("linked_weight")
        table = eligible.to_frame().join(linked_weight, how="left").fillna({"linked_weight": 0.0})
        table["factor"] = np.where(table.linked_weight > 0,
                                    table.eligible_weight / table.linked_weight, np.nan)
        unsupported = float(table.loc[table.linked_weight.eq(0), "eligible_weight"].sum())
        linked = linked.join(table.factor, on=strata)
        linked["poststrat_weight"] = linked.origin_weight * linked.factor
        finite_factors = table.loc[np.isfinite(table.factor) & table.linked_weight.gt(0)]
        for margin in MARGINS:
            event = flags[margin].loc[linked.index].astype(float)
            official = linked[link_weight] * linked.route_fraction
            origin = linked.origin_weight
            ps = linked.poststrat_weight
            def mean(v: pd.Series, w: pd.Series) -> float | None:
                good = np.isfinite(w) & w.gt(0)
                return float(np.average(v.loc[good], weights=w.loc[good])) if good.any() else None
            ps_good = np.isfinite(ps) & ps.gt(0)
            ess = (float(ps.loc[ps_good].sum()) ** 2 /
                   float(np.square(ps.loc[ps_good]).sum())) if ps_good.any() else 0.0
            result.append({
                "analysis_status": LABEL, "horizon": horizon, "period": keys[0],
                "age_group": keys[1], "beta_quintile": int(keys[2]), "margin": margin,
                "official_link_probability": mean(event, official),
                "origin_WTFINL_complete_case_probability": mean(event, origin),
                "observable_poststratified_probability": mean(event, ps),
                "eligible_origin_WTFINL": float(group.origin_weight.sum()),
                "linked_origin_WTFINL": float(linked.origin_weight.sum()),
                "unsupported_eligible_WTFINL": unsupported,
                "unsupported_eligible_share": unsupported / float(group.origin_weight.sum()),
                "supported_strata": int(table.linked_weight.gt(0).sum()),
                "unsupported_strata": int(table.linked_weight.eq(0).sum()),
                "poststrat_factor_min": float(finite_factors.factor.min()),
                "poststrat_factor_median": float(finite_factors.factor.median()),
                "poststrat_factor_p99": float(np.quantile(finite_factors.factor, .99)),
                "poststrat_factor_max": float(finite_factors.factor.max()),
                "poststrat_effective_sample_size_fractional": ess,
                "assumption": "outcome missingness independent of linkage within fixed observed strata",
                "factors_trimmed_or_capped": False,
            })
    rates = pd.DataFrame(result)
    signs = {
        ("post", "young_22_25", 5): 1, ("post", "older_26_65", 5): -1,
        ("post", "young_22_25", 1): -1, ("post", "older_26_65", 1): 1,
        ("pre", "young_22_25", 5): -1, ("pre", "older_26_65", 5): 1,
        ("pre", "young_22_25", 1): 1, ("pre", "older_26_65", 1): -1,
    }
    methods = ["official_link_probability", "origin_WTFINL_complete_case_probability",
               "observable_poststratified_probability"]
    for margin in MARGINS:
        selected = rates.loc[rates.margin.eq(margin)].set_index(
            ["period", "age_group", "beta_quintile"])
        require(set(signs).issubset(set(selected.index)), f"missing contrast cell: {horizon} {margin}")
        for method in methods:
            value = sum(sign * float(selected.at[key, method]) for key, sign in signs.items())
            contrasts.append({
                "analysis_status": LABEL, "horizon": horizon, "margin": margin,
                "weighting_method": method,
                "linear_probability_Q5_minus_Q1_young_minus_older_post_minus_pre": value,
                "interpretation": "descriptive triple difference in probabilities; not the nonlinear regression coefficient",
            })
    return result, contrasts


def missing_outcome_bounds(routed: pd.DataFrame, horizon: str) -> tuple[list[dict[str, Any]],
                                                                       list[dict[str, Any]]]:
    data = routed.loc[routed.period.isin(["pre", "post"])].copy()
    flags = transition_flags(data, horizon)
    rows: list[dict[str, Any]] = []
    for keys, group in data.groupby(["period", "age_group", "quintile"], observed=True):
        linked = group.analysis_link
        eligible_w = float(group.origin_weight.sum())
        linked_w = float(group.loc[linked, "origin_weight"].sum())
        ell = linked_w / eligible_w
        for margin in MARGINS:
            event_w = float(group.loc[linked & flags[margin], "origin_weight"].sum())
            p_linked = event_w / linked_w if linked_w else float("nan")
            rows.append({
                "analysis_status": LABEL, "horizon": horizon, "period": keys[0],
                "age_group": keys[1], "beta_quintile": int(keys[2]), "margin": margin,
                "eligible_origin_WTFINL": eligible_w, "linked_origin_WTFINL": linked_w,
                "link_share_ell": ell, "linked_probability_pL": p_linked,
                "probability_lower": ell * p_linked,
                "probability_upper": ell * p_linked + 1 - ell,
                "population_weight": "origin WTFINL times bridge route fraction",
            })
    frame = pd.DataFrame(rows)
    signs = {
        ("post", "young_22_25", 5): 1, ("post", "older_26_65", 5): -1,
        ("post", "young_22_25", 1): -1, ("post", "older_26_65", 1): 1,
        ("pre", "young_22_25", 5): -1, ("pre", "older_26_65", 5): 1,
        ("pre", "young_22_25", 1): 1, ("pre", "older_26_65", 1): -1,
    }
    contrasts: list[dict[str, Any]] = []
    for margin in MARGINS:
        selected = frame.loc[frame.margin.eq(margin)].set_index(
            ["period", "age_group", "beta_quintile"])
        require(set(signs).issubset(set(selected.index)), f"missing bound cell: {horizon} {margin}")
        denominators = {key: float(selected.at[key, "eligible_origin_WTFINL"])
                        for key in signs}
        observed_component = 0.0
        missing_coefficients: dict[int, float] = {}
        for key, sign in signs.items():
            period, age, quintile = key
            part = data.loc[data.period.eq(period) & data.age_group.eq(age) &
                            data.quintile.eq(quintile)]
            event = flags[margin].loc[part.index]
            observed_component += sign * float(
                part.loc[part.analysis_link & event, "origin_weight"].sum()
            ) / denominators[key]
            missing = part.loc[~part.analysis_link]
            for source_id, value in missing.groupby("source_record_id").origin_weight.sum().items():
                missing_coefficients[int(source_id)] = (
                    missing_coefficients.get(int(source_id), 0.0) +
                    sign * float(value) / denominators[key]
                )
        negative = float(sum(min(0.0, value) for value in missing_coefficients.values()))
        positive = float(sum(max(0.0, value) for value in missing_coefficients.values()))
        linear_lower = observed_component + negative
        linear_upper = observed_component + positive
        log_lower, log_upper = 0.0, 0.0
        for key, sign in signs.items():
            lower = float(selected.at[key, "probability_lower"])
            upper = float(selected.at[key, "probability_upper"])
            if sign > 0:
                log_lower += math.log(lower) if lower > 0 else -math.inf
                log_upper += math.log(upper) if upper > 0 else -math.inf
            else:
                log_lower += -math.log(upper) if upper > 0 else math.inf
                log_upper += -math.log(lower) if lower > 0 else math.inf
        contrasts.append({
            "analysis_status": LABEL, "horizon": horizon, "margin": margin,
            "linear_probability_contrast_lower": linear_lower,
            "linear_probability_contrast_upper": linear_upper,
            "log_relative_contrast_lower": log_lower,
            "log_relative_contrast_upper": log_upper,
            "finite_log_interval": bool(np.isfinite(log_lower) and np.isfinite(log_upper)),
            "observed_linear_contrast_component": observed_component,
            "missing_negative_coefficient_sum": negative,
            "missing_positive_coefficient_sum": positive,
            "missing_source_record_count": len(missing_coefficients),
            "joint_feasibility_scope": "sharp linear interval with one common outcome per source record and all bridge descendants; margin-specific",
            "log_interval_scope": "conservative marginal outer interval; not asserted sharp under bridge coupling",
            "Lee_trimming_used": False, "probabilities_clipped": False,
        })
    return rows, contrasts


def entry_rows(pairs: pd.DataFrame, horizon: str, bridge: pd.DataFrame,
               qmap: dict[str, int]) -> tuple[list[dict[str, Any]], list[dict[str, Any]],
                                              list[dict[str, Any]]]:
    _, _, _, link_weight = horizon_contract(horizon)
    risk = pairs.loc[pairs.analysis_link & pairs.nonemployed].copy()
    risk["period"] = period_label(risk.month, horizon)
    risk["entry_id"] = np.arange(len(risk), dtype=np.int64)
    base_columns = ["entry_id", "period", "age_group", link_weight]
    categories: list[pd.DataFrame] = []
    remaining = risk.loc[risk.nonemployed_d, base_columns].copy()
    remaining["destination_category"] = "remaining_nonemployed"
    remaining["category_fraction"] = 1.0
    categories.append(remaining)
    missing_occ = risk.loc[risk.employed_d & risk.OCC_d.fillna(0).le(0), base_columns].copy()
    missing_occ["destination_category"] = "employed_missing_or_invalid_destination_occupation"
    missing_occ["category_fraction"] = 1.0
    categories.append(missing_occ)
    valid = risk.loc[risk.employed_d & risk.OCC_d.fillna(0).gt(0)].copy()
    valid["source_occ"] = valid.OCC_d.astype(int).map(lambda value: f"{value:04d}")
    early = valid.loc[valid.YEAR_d.le(2019)].merge(
        bridge[["census_2010", "census_2018", "bridge_weight"]],
        left_on="source_occ", right_on="census_2010", how="left", validate="many_to_many")
    early["occ_code"] = early.census_2018
    early["category_fraction"] = early.bridge_weight.fillna(1.0)
    current = valid.loc[valid.YEAR_d.ge(2020)].copy()
    current["occ_code"] = current.source_occ
    current["category_fraction"] = 1.0
    routed = pd.concat([early, current], ignore_index=True, sort=False)
    routed["quintile"] = routed.occ_code.map(qmap)
    routed["destination_category"] = np.where(
        routed.quintile.notna(), "destination_Q" + routed.quintile.fillna(0).astype(int).astype(str),
        "employed_valid_occupation_outside_support")
    categories.append(routed[[*base_columns, "destination_category", "category_fraction"]])
    category = pd.concat(categories, ignore_index=True)
    per_id = category.groupby("entry_id").category_fraction.sum()
    require(len(per_id) == len(risk) and np.max(np.abs(per_id.to_numpy() - 1)) <= 1e-10,
            "entry destination categories do not exhaust every retained nonemployed origin")
    category["event_weight"] = category[link_weight] * category.category_fraction
    risks = risk.groupby(["period", "age_group"], observed=True).agg(
        risk_raw_records=("entry_id", "size"), risk_weight=(link_weight, "sum")).reset_index()
    grouped = category.groupby(["period", "age_group", "destination_category"],
                               observed=True).agg(
        event_fractional_records=("category_fraction", "sum"),
        event_weight=("event_weight", "sum")).reset_index()
    grouped = grouped.merge(risks, on=["period", "age_group"], validate="many_to_one")
    grouped["probability"] = grouped.event_weight / grouped.risk_weight
    probability_rows = [dict({"analysis_status": LABEL, "horizon": horizon,
                              "denominator": "all retained nonemployed origins",
                              "weight_used": link_weight}, **row)
                        for row in grouped.to_dict("records")]
    reconciliation: list[dict[str, Any]] = []
    allocation: list[dict[str, Any]] = []
    for keys, group in grouped.groupby(["period", "age_group"], observed=True):
        entry = group.loc[group.destination_category.ne("remaining_nonemployed")]
        supported = entry.loc[entry.destination_category.str.match(r"destination_Q[1-5]$")]
        reconciliation.append({
            "analysis_status": LABEL, "horizon": horizon, "period": keys[0],
            "age_group": keys[1], "risk_weight": float(group.risk_weight.iloc[0]),
            "sum_all_destination_weights": float(group.event_weight.sum()),
            "all_destination_probability_sum": float(group.probability.sum()),
            "total_employment_entry_weight": float(entry.event_weight.sum()),
            "sum_employed_destination_weights": float(entry.event_weight.sum()),
            "employment_entry_probability": float(entry.event_weight.sum() / group.risk_weight.iloc[0]),
            "identity_error": float(group.event_weight.sum() - group.risk_weight.iloc[0]),
        })
        denominator = float(supported.event_weight.sum())
        for row in supported.itertuples(index=False):
            allocation.append({
                "analysis_status": LABEL, "horizon": horizon, "period": keys[0],
                "age_group": keys[1], "destination_quintile": row.destination_category,
                "supported_entry_weight": float(row.event_weight),
                "all_supported_entry_weight": denominator,
                "conditional_allocation_share": float(row.event_weight / denominator) if denominator else None,
                "denominator": "observed entries into retained Q1-Q5 support only",
                "not_a_hiring_rate": True,
            })
    return probability_rows, reconciliation, allocation


def exposure_duration(month: str) -> float:
    year, value = map(int, month.split("-"))
    start = year * 12 + value
    onset = 2023 * 12 + 1
    return sum(start + step >= onset for step in range(1, 13)) / 12.0


def design_with_intensity(cells: pd.DataFrame, intensity: dict[str, float]) -> dict[str, Any]:
    data = LEGACY.design_from_cells(cells)
    q = cells.drop_duplicates("occ_code").set_index("occ_code").quintile.reindex(
        data["occupations"]).to_numpy(int)
    webb = cells.drop_duplicates("occ_code").set_index("occ_code").webb_z.reindex(
        data["occupations"]).to_numpy(float)
    dose = np.array([intensity[month] for month in data["months"]], float)
    columns = [((q[:, None] == value) * dose[None, :]).reshape(-1).astype(float)
               for value in [2, 3, 4, 5]]
    columns.append((webb[:, None] * dose[None, :]).reshape(-1))
    data["regressors"] = np.column_stack(columns)
    return data


def timing_fit(cells: pd.DataFrame, model_id: str, intensity: dict[str, float],
               canonical: list[str], signs: np.ndarray, components: dict[str, int],
               component_signs: np.ndarray) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    data = design_with_intensity(cells, intensity)
    panel = data["panel"]
    n_occ, n_month = len(data["occupations"]), len(data["months"])
    y = panel.xs("young_22_25", level="age_group").event.to_numpy().reshape(n_occ, n_month)
    o = panel.xs("older_26_65", level="age_group").event.to_numpy().reshape(n_occ, n_month)
    ry = panel.xs("young_22_25", level="age_group").risk.to_numpy().reshape(n_occ, n_month)
    ro = panel.xs("older_26_65", level="age_group").risk.to_numpy().reshape(n_occ, n_month)
    valid = (ry > 0) & (ro > 0)
    total = (y + o).reshape(-1)
    total[~valid.reshape(-1)] = 0
    offset = np.log(np.clip(ry, 1e-12, None) / np.clip(ro, 1e-12, None)).reshape(-1)
    fit = LEGACY.fit_offset(y.reshape(-1), total, data["occ_index"], data["month_index"],
                            data["regressors"], offset)
    target = 3
    beta = float(fit["beta"][target])
    used = [data["occupations"][int(i)] for i in fit["used_occ_indices"]]
    primary, influence = LEGACY._wild_summary(
        beta, fit["raw_influence"][:, target], used, canonical, signs)
    lineage = LEGACY._lineage_summary(
        beta, fit["raw_influence"][:, target], used, components, component_signs)
    for row in influence:
        row.update({"analysis_status": LABEL, "model_id": model_id})
    return ({
        "analysis_status": LABEL, "model_id": model_id,
        "coefficient_Q5_x_young_x_timing": beta, **primary, **lineage,
        "months": n_month, "first_month": data["months"][0], "last_month": data["months"][-1],
        "occupations": len(used), "timing_units": "zero-to-one annual onset exposure",
    }, influence)


def annual_timing(routed: pd.DataFrame, bridge: pd.DataFrame, qmap: dict[str, int],
                  webb: dict[str, float], components: dict[str, int]) -> tuple[list[dict[str, Any]],
                                                                               list[dict[str, Any]],
                                                                               list[dict[str, Any]]]:
    data = routed.loc[routed.analysis_link].copy()
    data["official_weight"] = data.LNKFW1YWT * data.route_fraction
    flags = transition_flags(data, "twelve_month")
    canonical = sorted(qmap)
    rng = np.random.default_rng(SEED)
    signs = rng.choice(np.array([-1.0, 1.0]), size=(DRAWS, len(canonical)))
    component_signs = rng.choice(np.array([-1.0, 1.0]),
                                 size=(DRAWS, len(set(components.values()))))
    rows: list[dict[str, Any]] = []
    influence_rows: list[dict[str, Any]] = []
    timing_audit: list[dict[str, Any]] = []
    for month, group in data.groupby("month", observed=True):
        target_ord = int(group.target_ord.iloc[0])
        destination_year = (target_ord - 1) // 12
        destination_month_number = (target_ord - 1) % 12 + 1
        timing_audit.append({
            "analysis_status": LABEL, "origin_month": month,
            "destination_month": f"{destination_year}-{destination_month_number:02d}",
            "origin_period_exclusion_rule": str(period_label(pd.Series([month]), "twelve_month").iloc[0]),
            "post_onset_destination_month_share": exposure_duration(month),
            "positive_weight_link_records_fractional": float(group.route_fraction.sum()),
            "positive_weight_link_weight": float(group.official_weight.sum()),
            "age_26_crossings_fractional": float(group.loc[
                group.AGE.le(25) & group.AGE_d.ge(26), "route_fraction"].sum()),
            "crosses_occupation_taxonomy": bool(int(month[:4]) == 2019),
        })
    for margin in (*MARGINS, "occupational_outflow"):
        risk = (pd.Series(True, index=data.index) if margin != "occupational_outflow"
                else flags["occupational_outflow_risk"])
        event = flags[margin] & risk
        working = data.copy()
        working["risk"] = np.where(risk, working.official_weight, 0.0)
        working["event"] = np.where(event, working.official_weight, 0.0)
        cells_all = working.groupby(
            ["occ_code", "month", "age_group", "quintile", "webb_z"], as_index=False,
            observed=True)[["risk", "event"]].sum()
        for rule in ("exclusion", "exposure_duration"):
            if rule == "exclusion":
                cells = cells_all.loc[
                    cells_all.month.le("2021-11") | cells_all.month.ge("2023-01")].copy()
                intensity = {month: float(month >= "2023-01") for month in cells.month.unique()}
            else:
                cells = cells_all.copy()
                intensity = {month: exposure_duration(month) for month in cells.month.unique()}
            model_id = f"annual_{margin}_{rule}"
            row, influence = timing_fit(cells, model_id, intensity, canonical, signs,
                                        components, component_signs)
            row.update({"margin": margin, "timing_rule": rule,
                        "straddling_origins_included": rule == "exposure_duration"})
            rows.append(row)
            influence_rows.extend(influence)
    return rows, influence_rows, timing_audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--microdata", required=True, type=Path)
    parser.add_argument("--repair-microdata", required=True, type=Path)
    parser.add_argument("--weight-patch", required=True, type=Path)
    parser.add_argument("--membership", required=True, type=Path)
    parser.add_argument("--bridge", required=True, type=Path)
    parser.add_argument("--legacy-membership", required=True, type=Path)
    parser.add_argument("--legacy-flow-results", required=True, type=Path)
    parser.add_argument("--legacy-household-results", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    require(sha256_file(args.membership) == sha256_file(args.legacy_membership),
            "current membership differs from the membership behind certified R3 flow estimates")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    inputs = {name: sha256_file(path) for name, path in {
        "microdata": args.microdata, "repair_microdata": args.repair_microdata,
        "weight_patch": args.weight_patch, "membership": args.membership,
        "legacy_membership": args.legacy_membership, "bridge": args.bridge,
        "legacy_flow_results": args.legacy_flow_results,
        "legacy_household_results": args.legacy_household_results,
        "spec": SPEC_PATH, "runner": Path(__file__), "legacy_runner": LEGACY_PATH,
    }.items()}
    frame, reconstruction = load_frame(args.microdata, args.repair_microdata, args.weight_patch)
    bridge, qmap, webb, components, map_receipt = LEGACY.load_maps(args.membership, args.bridge)
    outputs: dict[str, list[dict[str, Any]]] = {
        "LINK_ELIGIBILITY_ACCOUNTING.csv": [], "FLOW_BASELINE_PROBABILITIES.csv": [],
        "LINKED_UNLINKED_BALANCE.csv": [], "SELECTION_REWEIGHTED_RATES.csv": [],
        "SELECTION_REWEIGHTED_CONTRASTS.csv": [], "MISSING_OUTCOME_GROUP_BOUNDS.csv": [],
        "MISSING_OUTCOME_CONTRAST_BOUNDS.csv": [], "ENTRY_DESTINATION_PROBABILITIES.csv": [],
        "ENTRY_RECONCILIATION.csv": [], "CONDITIONAL_ENTRY_ALLOCATION.csv": [],
    }
    routed_by_horizon: dict[str, pd.DataFrame] = {}
    for horizon in ("adjacent_month", "twelve_month"):
        pairs, _, accounting = eligibility_accounting(frame, horizon)
        routed = route_origin_records(pairs, bridge, qmap, webb)
        routed["period"] = period_label(routed.month, horizon)
        routed_by_horizon[horizon] = routed
        outputs["LINK_ELIGIBILITY_ACCOUNTING.csv"].extend(accounting)
        outputs["FLOW_BASELINE_PROBABILITIES.csv"].extend(baseline_rows(routed, horizon))
        outputs["LINKED_UNLINKED_BALANCE.csv"].extend(balance_rows(routed, horizon))
        rates, contrasts = poststratified_rows(routed, horizon)
        outputs["SELECTION_REWEIGHTED_RATES.csv"].extend(rates)
        outputs["SELECTION_REWEIGHTED_CONTRASTS.csv"].extend(contrasts)
        groups, bound_contrasts = missing_outcome_bounds(routed, horizon)
        outputs["MISSING_OUTCOME_GROUP_BOUNDS.csv"].extend(groups)
        outputs["MISSING_OUTCOME_CONTRAST_BOUNDS.csv"].extend(bound_contrasts)
        entry, reconcile, allocation = entry_rows(pairs, horizon, bridge, qmap)
        outputs["ENTRY_DESTINATION_PROBABILITIES.csv"].extend(entry)
        outputs["ENTRY_RECONCILIATION.csv"].extend(reconcile)
        outputs["CONDITIONAL_ENTRY_ALLOCATION.csv"].extend(allocation)
    timing, timing_influence, timing_audit = annual_timing(
        routed_by_horizon["twelve_month"], bridge, qmap, webb, components)
    legacy_flow = pd.read_csv(args.legacy_flow_results, float_precision="round_trip")
    legacy_household = pd.read_csv(args.legacy_household_results,
                                   float_precision="round_trip")
    core_ids = set(legacy_household.model_id)
    core = legacy_flow.loc[legacy_flow.model_id.isin(core_ids)].merge(
        legacy_household, on=["model_id", "coefficient", "coefficient_units"],
        suffixes=("_occupation", "_person_household"), validate="one_to_one")
    require(len(core) == 10 and set(core.model_id) == core_ids,
            "certified core flow and person/household inventories do not align")
    legacy_lookup = legacy_flow.set_index("model_id").coefficient
    for row in timing:
        if row["timing_rule"] != "exclusion" or row["margin"] == "entry_destination":
            continue
        legacy_id = f"twelve_month__{row['margin']}__official"
        require(legacy_id in legacy_lookup.index and
                abs(row["coefficient_Q5_x_young_x_timing"] -
                    float(legacy_lookup.at[legacy_id])) <= 1e-10,
                f"annual exclusion timing coefficient does not reproduce {legacy_id}")
    outputs["CORE_FLOW_REGRESSION_REFERENCE.csv"] = core.to_dict("records")
    outputs["ANNUAL_TIMING_SENSITIVITY.csv"] = timing
    outputs["ANNUAL_TIMING_INFLUENCE.csv"] = timing_influence
    outputs["ANNUAL_TIMING_AUDIT.csv"] = timing_audit
    for name, rows in outputs.items():
        write_csv(args.output_dir / name, rows)
    findings = args.output_dir / "FLOW_SELECTION_FINDINGS.md"
    findings.write_text(
        f"# Gate 4 flow selection findings\n\n> **{LABEL}**\n\n"
        "This file is generated after the aggregate audit. Interpret the tables before "
        "adding result-specific prose. Link-rate differences do not sign selection bias. "
        "Observable post-stratification requires conditional missing-at-random; accounting "
        "bounds do not. Entry probabilities share one retained nonemployment denominator, "
        "while conditional allocation is a separate object and is not a hiring rate. Annual "
        "endpoints are not sums of monthly transitions. Full-window earnings remain blocked "
        "until an authorized EARNWEEK2 extract exists.\n",
        encoding="utf-8")
    published = [args.output_dir / name for name in outputs] + [findings]
    receipt = {
        "schema_version": "yax-gate4-flow-selection-v1",
        "status": "PASS_GATE4_FLOW_SELECTION",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                              text=True).strip(),
        "input_hashes": inputs, "reconstruction": reconstruction, "mapping": map_receipt,
        "current_and_legacy_membership_byte_identical": True,
        "protected_identifiers_written": False,
        "observable_selection_assumption": "conditional missing-at-random within fixed strata",
        "poststratification_trimmed_or_capped": False,
        "Lee_trimming_used": False, "probability_bounds_clipped": False,
        "entry_denominator": "all retained nonemployed origins",
        "annual_primary_rule": "exclude 2021-12 through 2022-12 origins",
        "annual_sensitivity_rule": "fraction of t+1 through t+12 months at or after 2023-01",
        "EARNWEEK2_full_window_status": "BLOCKED_AUTHORIZED_INPUT_ABSENT",
        "output_hashes": {path.name: sha256_file(path) for path in published},
    }
    write_json(args.output_dir / "EXECUTION_RECEIPT.json", receipt)
    print(json.dumps({"status": receipt["status"],
                      "outputs": len(published), "timing_models": len(timing)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
