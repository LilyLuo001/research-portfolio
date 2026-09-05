#!/usr/bin/env python3
"""Audit YAX calendar, occupation-universe, and bridge-allocation uncertainty.

POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1.

Raw licensed CPS records are read only from paths supplied at execution.  This
program writes aggregate occupation/source/month/age summaries and model
diagnostics; it never writes person records or credentials.
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
PRIMARY_FROZEN = -0.13107397642233506
PRIMARY_CORRECTED = -0.1345539535732939
MARCH_GAPS = {"{}-03".format(year) for year in range(2017, 2022)}
DRAWS = 9999
SEED = 2026090517
K_GRID = (0.5, 2.0 / 3.0, 1.0, 1.5, 2.0)


def import_path(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


FROZEN = import_path("yax_bridge_uncertainty_frozen", ROOT / "yax/analysis/run_frozen_v11.py")


def sha256(path):
    digest = hashlib.sha256()
    with pathlib.Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def support_hash(codes):
    payload = "".join("{}\n".format(code) for code in sorted(codes)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def quantile(values, q):
    try:
        return float(np.quantile(values, q, method="linear"))
    except TypeError:
        return float(np.quantile(values, q, interpolation="linear"))


def write_csv(path, rows):
    if not rows:
        raise RuntimeError("refusing to write empty output {}".format(path))
    fields = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with pathlib.Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, value):
    pathlib.Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def month_string(frame):
    return (frame.YEAR.astype(int).astype(str) + "-" +
            frame.MONTH.astype(int).astype(str).str.zfill(2))


def read_aggregate_sources(paths):
    """Return early source cells and 2020+ direct target cells."""
    early_pieces = []
    direct_pieces = []
    counters = {
        "rows_read": 0,
        "employed_age_22_65_positive_weight_records": 0,
        "early_source_records": 0,
        "direct_target_records": 0,
        "input_files": [str(path) for path in paths],
    }
    usecols = ["YEAR", "MONTH", "AGE", "EMPSTAT", "OCC", "WTFINL"]
    for path in paths:
        for chunk in pd.read_csv(path, usecols=usecols, chunksize=500000):
            counters["rows_read"] += len(chunk)
            age = pd.to_numeric(chunk.AGE, errors="coerce")
            emp = pd.to_numeric(chunk.EMPSTAT, errors="coerce").isin([10, 12])
            weight = pd.to_numeric(chunk.WTFINL, errors="coerce")
            occ = pd.to_numeric(chunk.OCC, errors="coerce")
            keep = (age.between(22, 65) & emp & np.isfinite(weight) & weight.gt(0) &
                    occ.notna() & occ.between(0, 9999) & occ.mod(1).eq(0))
            chunk = chunk.loc[keep].copy()
            if chunk.empty:
                continue
            counters["employed_age_22_65_positive_weight_records"] += len(chunk)
            chunk["month"] = month_string(chunk)
            chunk["age_group"] = np.where(
                pd.to_numeric(chunk.AGE, errors="raise").between(22, 25), "young_22_25", "older_26_65"
            )
            chunk["occ_code"] = occ.loc[chunk.index].astype(int).map(lambda value: "{:04d}".format(value))
            chunk["stock"] = pd.to_numeric(chunk.WTFINL, errors="raise")
            early = chunk.loc[pd.to_numeric(chunk.YEAR, errors="raise").le(2019)]
            direct = chunk.loc[pd.to_numeric(chunk.YEAR, errors="raise").ge(2020)]
            counters["early_source_records"] += len(early)
            counters["direct_target_records"] += len(direct)
            if not early.empty:
                early_pieces.append(
                    early.groupby(["occ_code", "month", "age_group"], as_index=False, observed=True)
                    .stock.sum().rename(columns={"occ_code": "source_occ"})
                )
            if not direct.empty:
                direct_pieces.append(
                    direct.groupby(["occ_code", "month", "age_group"], as_index=False, observed=True)
                    .stock.sum().rename(columns={"occ_code": "target_occ"})
                )
    early = (pd.concat(early_pieces, ignore_index=True)
             .groupby(["source_occ", "month", "age_group"], as_index=False, observed=True).stock.sum())
    direct = (pd.concat(direct_pieces, ignore_index=True)
              .groupby(["target_occ", "month", "age_group"], as_index=False, observed=True).stock.sum())
    counters.update({
        "early_aggregate_rows": len(early),
        "direct_aggregate_rows": len(direct),
        "observed_months": sorted(set(early.month) | set(direct.month)),
    })
    return early, direct, counters


def prepare_bridge(path):
    bridge = pd.read_csv(path, dtype={"census_2010": str, "census_2018": str})
    bridge["census_2010"] = bridge.census_2010.str.zfill(4)
    bridge["census_2018"] = bridge.census_2018.str.zfill(4)
    bridge["bridge_weight"] = pd.to_numeric(bridge.bridge_weight, errors="raise")
    multiplicity = bridge.groupby("census_2010").census_2018.nunique()
    bridge["n_routes_recomputed"] = bridge.census_2010.map(multiplicity).astype(int)
    if not np.all(bridge.n_routes_recomputed.to_numpy() == pd.to_numeric(bridge.n_routes).to_numpy()):
        raise RuntimeError("bridge n_routes does not match row-level multiplicity")
    sums = bridge.groupby("census_2010").bridge_weight.sum()
    if float(np.max(np.abs(sums.to_numpy() - 1.0))) > 5e-7:
        raise RuntimeError("official route weights do not sum to one")
    bridge["route_class"] = np.where(bridge.n_routes_recomputed.gt(1), "one_to_many", "one_to_one")
    return bridge


def expand_early(early, bridge, weight_column="bridge_weight", age_specific=False):
    columns = ["census_2010", "census_2018", "route_class", "n_routes_recomputed", weight_column]
    routes = bridge[columns].copy().rename(columns={
        "census_2010": "source_occ", "census_2018": "target_occ", weight_column: "route_weight"
    })
    if age_specific:
        if "age_group" not in bridge.columns:
            raise RuntimeError("age-specific route table lacks age_group")
        columns.append("age_group")
        routes = bridge[columns].copy().rename(columns={
            "census_2010": "source_occ", "census_2018": "target_occ", weight_column: "route_weight"
        })
        merged = early.merge(routes, on=["source_occ", "age_group"], how="inner", validate="many_to_many")
    else:
        merged = early.merge(routes, on="source_occ", how="inner", validate="many_to_many")
    merged["stock"] = merged.stock * merged.route_weight
    return merged[["source_occ", "target_occ", "month", "age_group", "route_class",
                   "n_routes_recomputed", "stock"]]


def routed_frame(early_routes, direct):
    left = early_routes[["source_occ", "target_occ", "month", "age_group", "route_class", "stock"]].copy()
    right = direct.copy()
    right["source_occ"] = right.target_occ
    right["route_class"] = "direct_2018"
    return pd.concat([
        left,
        right[["source_occ", "target_occ", "month", "age_group", "route_class", "stock"]],
    ], ignore_index=True)


def to_panel(routed):
    grouped = (routed.groupby(["target_occ", "month", "age_group"], as_index=False, observed=True)
               .stock.sum().rename(columns={"target_occ": "occ_code"}))
    pivot = grouped.pivot_table(
        index=["occ_code", "month"], columns="age_group", values="stock", aggfunc="sum", fill_value=0.0
    )
    for age in ("young_22_25", "older_26_65"):
        if age not in pivot:
            pivot[age] = 0.0
    return pivot[["young_22_25", "older_26_65"]].sort_index()


def model_inputs(panel, support, months, groups, webb_z):
    young, older = FROZEN.panel_arrays(panel, support, months)
    post = np.array([month >= "2023-01" for month in months])
    columns = [
        (((groups == value)[:, None]) & post[None, :]).reshape(-1).astype(float)
        for value in (2, 3, 4, 5)
    ]
    columns.append((webb_z[:, None] * post[None, :]).reshape(-1))
    return young, older, np.column_stack(columns), 3


def fit_summary(panel, support, months, groups, webb_z, seed, include_details=False):
    young, older, regressors, target = model_inputs(panel, support, months, groups, webb_z)
    fit, influence = FROZEN.fit_with_influence(young, older, regressors)
    rng = np.random.default_rng(seed)
    signs = rng.choice(np.array([-1.0, 1.0]), size=(DRAWS, len(support)))
    shifts = signs @ influence[:, target]
    estimate = float(fit.beta[target])
    analytic_se = float(fit.standard_error[target])
    bootstrap_se = float(np.std(shifts, ddof=1))
    critical = quantile(np.abs(shifts / analytic_se), 0.95)
    summary = {
        "analysis_status": LABEL,
        "support_occupations": len(support),
        "support_hash_sha256": support_hash(support),
        "months": len(months),
        "coefficient": estimate,
        "analytic_cluster_se": analytic_se,
        "bootstrap_se": bootstrap_se,
        "ci_lower": estimate - critical * analytic_se,
        "ci_upper": estimate + critical * analytic_se,
        "bootstrap_p_value": float((1 + np.sum(np.abs(shifts / analytic_se) >= abs(estimate / analytic_se))) /
                                     (DRAWS + 1)),
        "bootstrap_critical": critical,
        "bootstrap_draws": DRAWS,
        "bootstrap_seed": seed,
        "converged": bool(fit.converged),
        "iterations": int(fit.iterations),
    }
    if not include_details:
        return summary, None

    total_full = (young + older).reshape(-1)
    young_full = young.reshape(-1)
    occ_full = np.repeat(np.arange(len(support)), len(months))
    month_full = np.tile(np.arange(len(months)), len(support))
    keep = total_full > 0
    y = young_full[keep]
    total = total_full[keep]
    occ = occ_full[keep]
    month = month_full[keep]
    x = regressors[keep]
    probability = fit.fitted_probability[keep]
    weight = np.maximum(total * probability * (1.0 - probability), 1e-12)
    rx = FROZEN.ENGINE._weighted_absorb(x, weight, occ, month, len(support), len(months))
    other = [index for index in range(rx.shape[1]) if index != target]
    residualized_target = rx[:, target].copy()
    if other:
        z = rx[:, other]
        gram = z.T @ (weight[:, None] * z)
        cross = z.T @ (weight * residualized_target)
        residualized_target -= z @ np.linalg.pinv(gram) @ cross
    positive_info = weight * np.square(residualized_target)
    cell_info = np.zeros(len(support) * len(months))
    cell_info[keep] = positive_info
    cell_info = cell_info.reshape(len(support), len(months))
    occupation_info = cell_info.sum(axis=1)
    details = {
        "young": young,
        "older": older,
        "cell_information": cell_info,
        "occupation_information": occupation_info,
        "total_conditional_information": float(occupation_info.sum()),
    }
    return summary, details


def fixed_baseline_setup(panel, frozen_support, all_months, exposures, webb_map):
    frozen_static = [month for month in all_months if month not in MARCH_GAPS and month != "2022-12"]
    corrected_static = [month for month in all_months if month != "2022-12"]
    beta_map = exposures["dv_rating_beta"]["A"]
    support = sorted(code for code in frozen_support
                     if np.isfinite(beta_map.get(code, np.nan)) and np.isfinite(webb_map.get(code, np.nan)))
    young, older = FROZEN.panel_arrays(panel, support, frozen_static)
    weights = (young + older).sum(axis=1)
    beta = np.array([beta_map[code] for code in support], float)
    quintiles = FROZEN.weighted_quintiles(beta, weights)
    webb = np.array([webb_map[code] for code in support], float)
    mean, sd = FROZEN.weighted_scale(webb, weights)
    webb_z = (webb - mean) / sd
    return {
        "support": support,
        "quintiles": quintiles,
        "webb_z": webb_z,
        "frozen_static": frozen_static,
        "corrected_static": corrected_static,
        "beta_map": beta_map,
        "webb_map": webb_map,
    }


def universe_reconciliation(panel, frozen_support, pre_months, bridge, direct, exposures, webb_map, names):
    all_targets = sorted(set(panel.index.get_level_values("occ_code")))
    young, older = FROZEN.panel_arrays(panel, all_targets, pre_months)
    positive = (young.sum(axis=1) > 0) & (older.sum(axis=1) > 0)
    raw_candidates = [code for code, keep in zip(all_targets, positive) if keep]
    repaired = exposures["aioe_admin_equal"]["A"]
    reconstructed = [code for code in raw_candidates
                     if np.isfinite(repaired.get(code, np.nan)) and
                     np.isfinite(webb_map.get(code, np.nan))]
    if len(frozen_support) != 490 or len(raw_candidates) != 539 or len(reconstructed) != 495:
        raise RuntimeError("universe reconstruction changed: frozen={}, raw-expanded={}, repaired-AIOE-Webb={}".format(
            len(frozen_support), len(raw_candidates), len(reconstructed)))
    structural_split = set(bridge.loc[bridge.n_routes_recomputed.gt(1), "census_2018"])
    direct_targets = set(direct.target_occ)
    frozen_set, reconstructed_set = set(frozen_support), set(reconstructed)
    raw_set = set(raw_candidates)
    union = sorted(raw_set | frozen_set | reconstructed_set)
    exact = exposures["aioe_exact_code_baseline"]["A"]
    beta = exposures["dv_rating_beta"]["A"]
    rows = []
    for code in union:
        if code in frozen_set and code in reconstructed_set:
            relation = "intersection"
        elif code in frozen_set:
            relation = "frozen_490_only"
        elif code in reconstructed_set:
            relation = "expanded_495_only"
        else:
            relation = "raw_candidate_only_neither_490_nor_495"
        rows.append({
            "analysis_status": LABEL,
            "occupation_code": code,
            "occupation_name": names.get(code, ""),
            "universe_relation": relation,
            "in_frozen_490": code in frozen_set,
            "in_route_expanded_495": code in reconstructed_set,
            "in_raw_route_expanded_539": code in raw_set,
            "structurally_touched_by_split_inbound_route": code in structural_split,
            "directly_observed_2020_plus": code in direct_targets,
            "finite_beta": bool(np.isfinite(beta.get(code, np.nan))),
            "finite_webb": bool(np.isfinite(webb_map.get(code, np.nan))),
            "finite_repaired_AIOE": bool(np.isfinite(repaired.get(code, np.nan))),
            "finite_naive_exact_AIOE": bool(np.isfinite(exact.get(code, np.nan))),
            "pre_young_stock": float(young[all_targets.index(code)].sum()),
            "pre_older_stock": float(older[all_targets.index(code)].sum()),
        })
    summary = {
        "frozen_beta_complete_balanced_support": len(frozen_support),
        "raw_route_expanded_balanced_candidates": len(raw_candidates),
        "repaired_AIOE_plus_Webb_route_expanded_support": len(reconstructed),
        "intersection": len(frozen_set & reconstructed_set),
        "frozen_only": len(frozen_set - reconstructed_set),
        "expanded_only": len(reconstructed_set - frozen_set),
        "raw_candidate_only_neither_490_nor_495": len(raw_set - frozen_set - reconstructed_set),
        "serialized_union_rows": len(union),
        "frozen_support_hash": support_hash(frozen_support),
        "expanded_support_hash": support_hash(reconstructed),
        "same_positive_stock_rule_but_different_measure_availability_filters": True,
        "same_66_preperiod_months": len(pre_months) == 66,
    }
    return raw_candidates, reconstructed, rows, summary


def route_share_rows(routed, setup):
    support = setup["support"]
    group_map = {code: int(group) for code, group in zip(support, setup["quintiles"])}
    work = routed.loc[routed.target_occ.isin(support)].copy()
    work = work.loc[work.month.ne("2022-12")]
    work["quintile"] = work.target_occ.map(group_map)
    work["tail_group"] = np.where(work.quintile.eq(1), "Q1",
                                   np.where(work.quintile.eq(5), "Q5", "Q2_Q4"))
    work["period"] = np.where(
        work.month.lt("2020-01"), "2017_2019_bridge",
        np.where(work.month.lt("2023-01"), "2020_2022_direct_pre", "2023_2026_direct_post")
    )
    grouped = (work.groupby(["period", "age_group", "tail_group", "route_class"], as_index=False,
                            observed=True).stock.sum())
    age_period = grouped.groupby(["period", "age_group"]).stock.transform("sum")
    age_period_tail = grouped.groupby(["period", "age_group", "tail_group"]).stock.transform("sum")
    grouped["share_of_age_period_stock"] = grouped.stock / age_period
    grouped["share_within_age_period_tail"] = grouped.stock / age_period_tail
    grouped.insert(0, "analysis_status", LABEL)
    return grouped.to_dict("records")


def route_information_rows(routed, setup, details, names, bridge):
    support, months = setup["support"], setup["corrected_static"]
    total_info = details["total_conditional_information"]
    split_targets = set(bridge.loc[bridge.n_routes_recomputed.gt(1), "census_2018"])
    early = routed.loc[routed.month.lt("2020-01") & routed.target_occ.isin(support)].copy()
    split = (early.loc[early.route_class.eq("one_to_many")]
             .groupby(["target_occ", "month"], observed=True).stock.sum())
    total = early.groupby(["target_occ", "month"], observed=True).stock.sum()
    rows = []
    proportional = 0.0
    touched_information = 0.0
    for oi, code in enumerate(support):
        occupation_info = float(details["occupation_information"][oi])
        touched = code in split_targets
        if touched:
            touched_information += occupation_info
        split_stock = float(early.loc[(early.target_occ == code) & early.route_class.eq("one_to_many"), "stock"].sum())
        early_stock = float(early.loc[early.target_occ == code, "stock"].sum())
        allocated_info = 0.0
        for mi, month in enumerate(months):
            denominator = float(total.get((code, month), 0.0))
            fraction = float(split.get((code, month), 0.0)) / denominator if denominator > 0 else 0.0
            allocated_info += float(details["cell_information"][oi, mi]) * fraction
        proportional += allocated_info
        rows.append({
            "analysis_status": LABEL,
            "occupation_code": code,
            "occupation_name": names.get(code, ""),
            "beta_quintile": int(setup["quintiles"][oi]),
            "structurally_touched_by_split_inbound_route": touched,
            "observed_early_split_stock": split_stock,
            "observed_early_total_stock": early_stock,
            "observed_early_split_stock_share": split_stock / early_stock if early_stock > 0 else 0.0,
            "conditional_target_information": occupation_info,
            "conditional_target_information_share": occupation_info / total_info,
            "proportional_split_attributed_information": allocated_info,
            "proportional_split_attributed_information_share": allocated_info / total_info,
        })
    summary = {
        "total_conditional_information": total_info,
        "structurally_split_touched_target_count": sum(code in split_targets for code in support),
        "information_share_in_structurally_split_touched_targets": touched_information / total_info,
        "proportional_split_attributed_information_share": proportional / total_info,
        "proportional_attribution_warning": (
            "cell information was multiplied by the cell's split-source stock share; this is a transparent "
            "diagnostic allocation, not an identified decomposition"
        ),
    }
    return rows, summary


def accounting_bounds(early, early_routes, bridge, setup):
    group_map = {code: int(group) for code, group in zip(setup["support"], setup["quintiles"])}
    route_groups = bridge[["census_2010", "census_2018"]].copy()
    route_groups["quintile"] = route_groups.census_2018.map(group_map)
    source_flags = []
    for source, group in route_groups.groupby("census_2010"):
        q = group.quintile
        source_flags.append({
            "source_occ": source,
            "any_Q1": bool(q.eq(1).any()), "all_Q1": bool(q.eq(1).all()),
            "any_Q5": bool(q.eq(5).any()), "all_Q5": bool(q.eq(5).all()),
        })
    flags = pd.DataFrame(source_flags)
    matched = early.loc[early.source_occ.isin(set(bridge.census_2010))].merge(flags, on="source_occ")
    official = early_routes.copy()
    official["quintile"] = official.target_occ.map(group_map)
    rows = []
    ratio_components = {}
    for age in ("young_22_25", "older_26_65"):
        age_source = matched.loc[matched.age_group.eq(age)]
        denominator = float(age_source.stock.sum())
        for tail in ("Q1", "Q5"):
            q = int(tail[1])
            lower = float(age_source.loc[age_source["all_{}".format(tail)], "stock"].sum())
            upper = float(age_source.loc[age_source["any_{}".format(tail)], "stock"].sum())
            point = float(official.loc[official.age_group.eq(age) & official.quintile.eq(q), "stock"].sum())
            row = {
                "analysis_status": LABEL,
                "object": "early_2017_2019_weighted_stock",
                "age_group": age,
                "fixed_beta_tail": tail,
                "official_common_weight_allocation": point,
                "unrestricted_allowed_route_lower": lower,
                "unrestricted_allowed_route_upper": upper,
                "matched_early_source_stock": denominator,
                "official_share": point / denominator,
                "lower_share": lower / denominator,
                "upper_share": upper / denominator,
                "bound_scope": "sharp accounting bound across officially allowed routes; not a coefficient bound",
            }
            rows.append(row)
            ratio_components[(age, tail)] = (lower, point, upper)
    for tail in ("Q1", "Q5"):
        yl, yp, yu = ratio_components[("young_22_25", tail)]
        ol, op, ou = ratio_components[("older_26_65", tail)]
        rows.append({
            "analysis_status": LABEL,
            "object": "early_2017_2019_young_to_older_stock_ratio",
            "age_group": "young_over_older",
            "fixed_beta_tail": tail,
            "official_common_weight_allocation": yp / op if op > 0 else np.nan,
            "unrestricted_allowed_route_lower": yl / ou if ou > 0 else np.nan,
            "unrestricted_allowed_route_upper": yu / ol if ol > 0 else np.inf,
            "bound_scope": "ratio of separate sharp stock bounds; not a coefficient bound",
        })
    return rows


def scenario_route_table(bridge, beta_map, webb_map, k_value):
    work = bridge.copy()
    work["beta"] = work.census_2018.map(beta_map)
    work["webb"] = work.census_2018.map(webb_map)
    eligible_sources = set()
    ranks = np.zeros(len(work))
    for source, index in work.groupby("census_2010").groups.items():
        idx = np.asarray(list(index), dtype=int)
        if len(idx) <= 1:
            continue
        values = work.loc[idx, "beta"].to_numpy(float)
        webb = work.loc[idx, "webb"].to_numpy(float)
        if not np.isfinite(values).all() or not np.isfinite(webb).all() or np.ptp(values) <= 0:
            continue
        order = pd.Series(values).rank(method="average").to_numpy(float)
        scaled = (order - order.min()) / (order.max() - order.min()) - 0.5
        ranks[idx] = scaled
        eligible_sources.add(source)
    theta = 0.5 * math.log(k_value)
    frames = []
    for age, sign in (("young_22_25", 1.0), ("older_26_65", -1.0)):
        age_table = work.copy()
        multiplier = np.ones(len(age_table))
        eligible = age_table.census_2010.isin(eligible_sources).to_numpy()
        multiplier[eligible] = np.exp(sign * theta * ranks[eligible])
        age_table["scenario_weight"] = age_table.bridge_weight.to_numpy() * multiplier
        totals = age_table.groupby("census_2010").scenario_weight.transform("sum")
        official_mass = age_table.groupby("census_2010").bridge_weight.transform("sum")
        age_table["scenario_weight"] = age_table.scenario_weight / totals * official_mass
        age_table["age_group"] = age
        frames.append(age_table)
    return pd.concat(frames, ignore_index=True), eligible_sources


def scenario_results(early, direct, bridge, panel_official, setup):
    matched = early.loc[early.source_occ.isin(set(bridge.census_2010))]
    rows = []
    for position, k_value in enumerate(K_GRID):
        scenario_bridge, eligible_sources = scenario_route_table(
            bridge, setup["beta_map"], setup["webb_map"], k_value
        )
        expanded = expand_early(early, scenario_bridge, "scenario_weight", age_specific=True)
        routed = routed_frame(expanded, direct)
        panel = to_panel(routed)
        result, _ = fit_summary(
            panel, setup["support"], setup["corrected_static"], setup["quintiles"], setup["webb_z"],
            SEED + 100 + position,
        )
        official_total = float(matched.stock.sum())
        scenario_total = float(expanded.stock.sum())
        eligible_stock = float(matched.loc[matched.source_occ.isin(eligible_sources), "stock"].sum())
        row = {
            "analysis_status": LABEL,
            "scenario": "exposure_directed_age_allocation_tilt",
            "K_high_vs_low_young_older_relative_allocation_odds": k_value,
            "theta_half_log_K": 0.5 * math.log(k_value),
            "eligible_split_sources": len(eligible_sources),
            "eligible_source_stock_share_of_matched_early_stock": eligible_stock / official_total,
            "ineligible_split_sources_retain_official_weights": True,
            "mass_conservation_gap": scenario_total - official_total,
            "fixed_support_treatment_and_webb_scale": True,
            **result,
        }
        rows.append(row)
    official_row = next(row for row in rows if np.isclose(row[
        "K_high_vs_low_young_older_relative_allocation_odds"], 1.0))
    if not np.isclose(official_row["coefficient"], PRIMARY_CORRECTED, atol=1e-10, rtol=0):
        raise RuntimeError("K=1 scenario failed to reproduce corrected baseline")
    if max(abs(row["mass_conservation_gap"]) for row in rows) > max(1e-3, official_total * 1e-12):
        raise RuntimeError("allocation scenario failed aggregate mass conservation")
    return rows


def run(args):
    args.output_dir.mkdir(parents=True, exist_ok=True)
    authenticated = FROZEN.validate_inputs(args)
    input_hashes = dict(authenticated["hashes"])
    input_hashes["repair_microdata"] = sha256(args.repair_microdata)
    input_hashes["analysis_spec"] = sha256(HERE / "ANALYSIS_SPEC.md")
    input_hashes["execution_code"] = sha256(pathlib.Path(__file__))
    input_hashes["calendar_results"] = sha256(args.calendar_results)

    frozen_pre, frozen_support, pre_months = FROZEN.read_preperiod(args.preperiod_cells)
    del frozen_pre
    bridge = prepare_bridge(args.bridge)
    early, direct, raw_counters = read_aggregate_sources([args.microdata, args.repair_microdata])
    all_months = sorted(set(early.month) | set(direct.month))
    if len(all_months) != 114 or not MARCH_GAPS.issubset(set(all_months)) or "2025-10" in all_months:
        raise RuntimeError("corrected survey calendar failed: {} months".format(len(all_months)))
    early_routes = expand_early(early, bridge)
    official_routed = routed_frame(early_routes, direct)
    panel = to_panel(official_routed)

    exposures = FROZEN.exposure_maps(args.lookup, args.rule_b_values)
    computers, names, _ = FROZEN.comp_maps(args.computerization)
    webb_map = computers["webb_pct_software"]
    raw_candidates, reconstructed, universe_rows, universe_summary = universe_reconciliation(
        panel, frozen_support, pre_months, bridge, direct, exposures, webb_map, names
    )
    write_csv(args.output_dir / "UNIVERSE_RECONCILIATION.csv", universe_rows)

    setup = fixed_baseline_setup(panel, frozen_support, all_months, exposures, webb_map)
    if len(setup["support"]) != 468 or len(setup["frozen_static"]) != 108 or len(setup["corrected_static"]) != 113:
        raise RuntimeError("primary setup support/calendar changed")
    frozen_result, _ = fit_summary(
        panel, setup["support"], setup["frozen_static"], setup["quintiles"], setup["webb_z"], SEED
    )
    corrected_result, corrected_details = fit_summary(
        panel, setup["support"], setup["corrected_static"], setup["quintiles"], setup["webb_z"],
        SEED + 1, include_details=True
    )
    if not np.isclose(frozen_result["coefficient"], PRIMARY_FROZEN, atol=1e-10, rtol=0):
        raise RuntimeError("frozen baseline failed")
    if not np.isclose(corrected_result["coefficient"], PRIMARY_CORRECTED, atol=1e-10, rtol=0):
        raise RuntimeError("corrected baseline failed")

    split_targets = set(bridge.loc[bridge.n_routes_recomputed.gt(1), "census_2018"])
    clean_mask = np.array([code not in split_targets for code in setup["support"]])
    clean_support = [code for code, keep in zip(setup["support"], clean_mask) if keep]
    clean_fixed, _ = fit_summary(
        panel, clean_support, setup["corrected_static"], setup["quintiles"][clean_mask],
        setup["webb_z"][clean_mask], SEED + 2
    )
    cy, co = FROZEN.panel_arrays(panel, clean_support, setup["corrected_static"])
    clean_weights = (cy + co).sum(axis=1)
    clean_beta = np.array([setup["beta_map"][code] for code in clean_support], float)
    clean_q = FROZEN.weighted_quintiles(clean_beta, clean_weights)
    clean_webb = np.array([setup["webb_map"][code] for code in clean_support], float)
    clean_mean, clean_sd = FROZEN.weighted_scale(clean_webb, clean_weights)
    clean_recomputed, _ = fit_summary(
        panel, clean_support, setup["corrected_static"], clean_q,
        (clean_webb - clean_mean) / clean_sd, SEED + 3
    )

    existing_calendar = pd.read_csv(args.calendar_results)
    stable = existing_calendar.loc[existing_calendar.specification.eq(
        "stable_Census2010_observed_calendar")].iloc[0]
    model_rows = []
    for label, role, item in (
        ("frozen_108_month_chronology_benchmark", "chronology_only", frozen_result),
        ("corrected_March_113_month_substantive_baseline", "substantive_baseline", corrected_result),
        ("structural_one_to_one_targets_fixed_labels", "clean_route_same_treatment_labels", clean_fixed),
        ("structural_one_to_one_targets_recomputed_labels", "clean_route_changed_comparison_population", clean_recomputed),
    ):
        model_rows.append({"specification": label, "interpretation_role": role, **item})
    model_rows.append({
        "analysis_status": LABEL,
        "specification": "stable_Census2010_observed_calendar_prior_audit",
        "interpretation_role": "stable_taxonomy_changed_temporal_and_occupational_estimand",
        "support_occupations": int(stable.support_occupations),
        "months": int(stable.months),
        "coefficient": float(stable.coefficient),
        "analytic_cluster_se": float(stable.analytic_or_paired_se),
        "bootstrap_se": float(stable.paired_bootstrap_se),
        "ci_lower": float(stable.ci_lower),
        "ci_upper": float(stable.ci_upper),
        "bootstrap_p_value": float(stable.bootstrap_p_value),
        "source_artifact": str(args.calendar_results.relative_to(ROOT)),
        "source_artifact_sha256": sha256(args.calendar_results),
    })
    write_csv(args.output_dir / "MODEL_SENSITIVITIES.csv", model_rows)

    write_csv(args.output_dir / "ROUTE_SHARE_SUMMARY.csv", route_share_rows(official_routed, setup))
    target_rows, information_summary = route_information_rows(
        official_routed, setup, corrected_details, names, bridge
    )
    write_csv(args.output_dir / "TARGET_ROUTE_INFORMATION.csv", target_rows)
    bounds_rows = accounting_bounds(early, early_routes, bridge, setup)
    write_csv(args.output_dir / "AGE_ALLOCATION_ACCOUNTING_BOUNDS.csv", bounds_rows)
    scenario_rows = scenario_results(early, direct, bridge, panel, setup)
    write_csv(args.output_dir / "AGE_ALLOCATION_TILT_SCENARIOS.csv", scenario_rows)

    exact = exposures["aioe_exact_code_baseline"]["A"]
    repaired = exposures["aioe_admin_equal"]["A"]
    expanded_exact = [code for code in reconstructed
                      if np.isfinite(exact.get(code, np.nan)) and np.isfinite(webb_map.get(code, np.nan))]
    expanded_repaired = [code for code in reconstructed
                         if np.isfinite(repaired.get(code, np.nan)) and np.isfinite(webb_map.get(code, np.nan))]
    if len(expanded_exact) != 410 or len(expanded_repaired) != 495:
        raise RuntimeError("exact/repaired crosswalk supports changed")
    compatibility = {
        "analysis_status": LABEL,
        "gate": "occupation_taxonomy_compatibility_before_exact_code_merge",
        "status": "FAIL_CLOSED_EXACT_CODE_NOT_A_DEFENSIBLE_HARMONIZATION",
        "native_measure_taxonomy": "AIOE published on SOC 2010",
        "outcome_target_taxonomy": "Census 2018 occupation codes",
        "naive_exact_code_support_with_Webb": len(expanded_exact),
        "audited_bridge_repaired_support_with_Webb": len(expanded_repaired),
        "route_expanded_candidate_universe": len(reconstructed),
        "raw_route_expanded_candidate_universe": len(raw_candidates),
        "lost_occupations_under_naive_exact_code": len(set(expanded_repaired) - set(expanded_exact)),
        "diagnostic_rule": (
            "when source and outcome taxonomies have different vintages, exact string/code equality is rejected; "
            "an explicit versioned bridge with route mass and multiplicity is required"
        ),
        "implementation_error_not_alternative_construct": True,
    }
    write_json(args.output_dir / "CROSSWALK_COMPATIBILITY_GATE.json", compatibility)

    output_files = sorted(path for path in args.output_dir.iterdir() if path.is_file())
    receipt = {
        "analysis_status": LABEL,
        "record": "YAX referee-round-2 taxonomy bridge uncertainty audit",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "input_hashes": input_hashes,
        "raw_build_aggregate_counters": raw_counters,
        "calendar": {
            "observed_months": len(all_months),
            "static_corrected_months": len(setup["corrected_static"]),
            "static_frozen_months": len(setup["frozen_static"]),
            "restored_March_months": sorted(MARCH_GAPS & set(all_months)),
            "October_2025_present": "2025-10" in all_months,
        },
        "universe_reconciliation": universe_summary,
        "primary_support": {
            "occupations": len(setup["support"]),
            "hash": support_hash(setup["support"]),
            "structural_one_to_one_target_occupations": len(clean_support),
            "structural_one_to_one_target_hash": support_hash(clean_support),
        },
        "baseline_reproduction": {
            "frozen_expected": PRIMARY_FROZEN,
            "frozen_observed": frozen_result["coefficient"],
            "corrected_expected": PRIMARY_CORRECTED,
            "corrected_observed": corrected_result["coefficient"],
        },
        "information_route_summary": information_summary,
        "allocation_scenarios": {
            "K_grid": list(K_GRID),
            "interpretation": (
                "parameterized age-allocation scenarios on officially allowed routes; not identified bounds or probabilities"
            ),
        },
        "crosswalk_compatibility_gate": compatibility,
        "raw_microdata_written": False,
        "protected_confirmatory_artifacts_modified": False,
        "output_hashes": {path.name: sha256(path) for path in output_files},
    }
    write_json(args.output_dir / "EXECUTION_RECEIPT.json", receipt)
    print(json.dumps({
        "status": "PASS_BRIDGE_UNCERTAINTY",
        "frozen_490": len(frozen_support),
        "route_expanded_495": len(reconstructed),
        "corrected_coefficient": corrected_result["coefficient"],
        "clean_route_coefficient": clean_fixed["coefficient"],
    }, indent=2, sort_keys=True))


def parser():
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--microdata", type=pathlib.Path, required=True)
    value.add_argument("--repair-microdata", type=pathlib.Path, required=True)
    value.add_argument("--preperiod-cells", type=pathlib.Path, required=True)
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
    value.add_argument("--calendar-results", type=pathlib.Path,
                       default=ROOT / "yax/revision/referee_20260905/results/balanced_cells/CALENDAR_TAXONOMY_SENSITIVITIES.csv")
    value.add_argument("--output-dir", type=pathlib.Path, default=HERE / "results")
    return value


if __name__ == "__main__":
    run(parser().parse_args())
