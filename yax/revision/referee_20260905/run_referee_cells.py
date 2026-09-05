#!/usr/bin/env python3
"""Build revised CPS cells and run calendar, age, sample, and estimator audits.

POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1.
The frozen cell file is read for authentication and benchmarking but is never
modified.  March 2017--2021 is restored only in the new revision namespace.
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
ROOT = pathlib.Path(__file__).resolve().parents[3]
LABEL = "POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1"
DRAWS = 999
SEED = 2026090501
PRIMARY_EXPECTED = -0.13107397642233506
PRIMARY_SUPPORT_HASH = "11ec58ab1004cd83d62c57785f6c0dd3ee5a8abf08b7f71a3b664e91ded8333b"
MARCH_GAPS = {f"{year}-03" for year in range(2017, 2022)}
# IND1990 categories mapped to the BLS leisure-and-hospitality concept as
# closely as this historical coding permits: eating/drinking; lodging;
# theaters/motion pictures; bowling; other entertainment/recreation; museums.
# Code 800 bundles motion pictures (Information in NAICS) with theaters, so
# the result is explicitly a concordance-based approximation, not exact NAICS.
LEISURE_HOSPITALITY_IND1990 = {641, 762, 770, 800, 802, 810, 872}


def import_path(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


FROZEN = import_path("yax_revision_cells_frozen", ROOT / "yax/analysis/run_frozen_v11.py")
CORE = import_path("yax_revision_cells_core", HERE / "run_referee_core.py")


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: pathlib.Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: pathlib.Path, rows: list[dict]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty output {path}")
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def month_string(frame: pd.DataFrame) -> pd.Series:
    return (frame.YEAR.astype(int).astype(str) + "-" +
            frame.MONTH.astype(int).astype(str).str.zfill(2))


def build_exact_age_cells(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    bridge = pd.read_csv(args.bridge, dtype={"census_2010": str, "census_2018": str})
    bridge["census_2010"] = bridge.census_2010.str.zfill(4)
    bridge["census_2018"] = bridge.census_2018.str.zfill(4)
    bridge["bridge_weight"] = pd.to_numeric(bridge.bridge_weight, errors="raise")
    multiplicity = bridge.groupby("census_2010").census_2018.nunique()
    bridge["split_source"] = bridge.census_2010.map(multiplicity).gt(1)
    pieces, stable_pieces = [], []
    counters = {
        "rows_read": 0, "employed_age_18_65_records": 0,
        "invalid_raw_occ_records": 0, "routed_rows": 0,
        "early_records_before_route": 0, "early_records_unmatched": 0,
        "current_records": 0, "leisure_hospitality_records": 0,
    }
    usecols = ["YEAR", "MONTH", "AGE", "EMPSTAT", "OCC", "OCC2010", "IND1990", "WTFINL"]
    for chunk in pd.read_csv(args.microdata, usecols=usecols, chunksize=500_000):
        counters["rows_read"] += len(chunk)
        age = pd.to_numeric(chunk.AGE, errors="coerce")
        weight = pd.to_numeric(chunk.WTFINL, errors="coerce")
        employed = pd.to_numeric(chunk.EMPSTAT, errors="coerce").isin([10, 12])
        keep = age.between(18, 65) & employed & np.isfinite(weight) & weight.gt(0)
        chunk = chunk.loc[keep].copy()
        counters["employed_age_18_65_records"] += len(chunk)
        chunk["month"] = month_string(chunk)
        chunk["age"] = pd.to_numeric(chunk.AGE, errors="raise").astype(int)
        chunk["industry_keep"] = ~pd.to_numeric(chunk.IND1990, errors="coerce").isin(
            LEISURE_HOSPITALITY_IND1990
        )
        counters["leisure_hospitality_records"] += int((~chunk.industry_keep).sum())
        occ = pd.to_numeric(chunk.OCC, errors="coerce")
        valid = occ.notna() & occ.between(0, 9999) & occ.mod(1).eq(0)
        counters["invalid_raw_occ_records"] += int((~valid).sum())
        chunk = chunk.loc[valid].copy()
        chunk["source_occ"] = occ.loc[chunk.index].astype(int).map(lambda value: f"{value:04d}")

        early_input = chunk.loc[chunk.YEAR.le(2019)].copy()
        counters["early_records_before_route"] += len(early_input)
        early = early_input.merge(bridge, left_on="source_occ", right_on="census_2010",
                                  how="inner", validate="many_to_many")
        matched_sources = set(early.source_occ)
        counters["early_records_unmatched"] += int((~early_input.source_occ.isin(matched_sources)).sum())
        early["occ_code"] = early.census_2018
        early["stock"] = early.WTFINL * early.bridge_weight
        early["respondent_equivalent"] = early.bridge_weight
        early["split_stock"] = early.stock * early.split_source.astype(float)
        early["route_kind"] = "probabilistic_2010_to_2018"

        current = chunk.loc[chunk.YEAR.ge(2020)].copy()
        counters["current_records"] += len(current)
        current["occ_code"] = current.source_occ
        current["stock"] = current.WTFINL
        current["respondent_equivalent"] = 1.0
        current["split_stock"] = 0.0
        current["route_kind"] = "direct_2018"
        routed = pd.concat([
            early[["occ_code", "month", "age", "industry_keep", "stock",
                   "respondent_equivalent", "split_stock", "route_kind"]],
            current[["occ_code", "month", "age", "industry_keep", "stock",
                     "respondent_equivalent", "split_stock", "route_kind"]],
        ], ignore_index=True)
        counters["routed_rows"] += len(routed)
        pieces.append(routed.groupby(
            ["occ_code", "month", "age", "industry_keep", "route_kind"],
            as_index=False, observed=True,
        )[["stock", "respondent_equivalent", "split_stock"]].sum())

        stable = chunk.copy()
        occ2010 = pd.to_numeric(stable.OCC2010, errors="coerce")
        stable = stable.loc[occ2010.notna() & occ2010.between(0, 9999) & occ2010.mod(1).eq(0)].copy()
        stable["occ_code"] = occ2010.loc[stable.index].astype(int).map(lambda value: f"{value:04d}")
        stable["stock"] = stable.WTFINL
        stable["respondent_equivalent"] = 1.0
        stable_pieces.append(stable.groupby(
            ["occ_code", "month", "age"], as_index=False, observed=True
        )[["stock", "respondent_equivalent"]].sum())
    cells = pd.concat(pieces, ignore_index=True).groupby(
        ["occ_code", "month", "age", "industry_keep", "route_kind"],
        as_index=False, observed=True,
    )[["stock", "respondent_equivalent", "split_stock"]].sum()
    stable = pd.concat(stable_pieces, ignore_index=True).groupby(
        ["occ_code", "month", "age"], as_index=False, observed=True
    )[["stock", "respondent_equivalent"]].sum()
    counters.update({
        "observed_months": sorted(cells.month.unique()),
        "observed_month_count": int(cells.month.nunique()),
        "restored_march_months": sorted(set(cells.month.unique()) & MARCH_GAPS),
        "october_2025_present": "2025-10" in set(cells.month.unique()),
        "routed_aggregate_rows": len(cells), "stable_aggregate_rows": len(stable),
        "bridge_source_codes": int(bridge.census_2010.nunique()),
        "bridge_target_codes": int(bridge.census_2018.nunique()),
        "one_to_many_source_codes": int((multiplicity > 1).sum()),
        "maximum_source_multiplicity": int(multiplicity.max()),
    })
    return cells, stable, counters


def panel_for_ages(cells: pd.DataFrame, support: list[str], months: list[str],
                   young_range: tuple[int, int], older_range: tuple[int, int],
                   value: str = "stock", industry_only: bool = False):
    selected = cells.loc[cells.occ_code.isin(support) & cells.month.isin(months)].copy()
    if industry_only:
        selected = selected.loc[selected.industry_keep]
    selected["age_group"] = np.where(
        selected.age.between(*young_range), "young",
        np.where(selected.age.between(*older_range), "older", "drop"),
    )
    selected = selected.loc[selected.age_group.ne("drop")]
    grouped = selected.groupby(["occ_code", "month", "age_group"], as_index=False)[value].sum()
    index = pd.MultiIndex.from_product([support, months], names=["occ_code", "month"])
    pivot = grouped.pivot_table(index=["occ_code", "month"], columns="age_group",
                                values=value, aggfunc="sum", fill_value=0.0).reindex(index, fill_value=0.0)
    for group in ("young", "older"):
        if group not in pivot: pivot[group] = 0.0
    young = pivot.young.to_numpy().reshape(len(support), len(months))
    older = pivot.older.to_numpy().reshape(len(support), len(months))
    return young, older


def fit_q_model(young: np.ndarray, older: np.ndarray, quintiles: np.ndarray,
                webb_z: np.ndarray, months: list[str], period_masks: list[tuple[str, np.ndarray]] | None = None,
                seasonal: bool = False):
    period_masks = period_masks or [("post_2023_2026", np.array([m >= "2023-01" for m in months]))]
    columns, labels = [], []
    for period_name, period in period_masks:
        for q in (2, 3, 4, 5):
            columns.append((((quintiles == q)[:, None]) & period[None, :]).reshape(-1).astype(float))
            labels.append(f"Q{q}_x_{period_name}")
        columns.append((webb_z[:, None] * period[None, :]).reshape(-1))
        labels.append(f"Webb_z_x_{period_name}")
    regressors = np.column_stack(columns)
    if not seasonal:
        fit, influence = FROZEN.fit_with_influence(young, older, regressors)
        return fit, influence, labels, {"fixed_effect_groups": "occupation and calendar month"}

    # Occupation-specific young-share seasonality: occupation x month-of-year
    # replaces the nested occupation FE, while calendar-month FE is retained.
    n_occ, n_month = young.shape
    total = (young + older).reshape(-1)
    original_occ = np.repeat(np.arange(n_occ), n_month)
    month = np.tile(np.arange(n_month), n_occ)
    season = np.tile(np.array([int(value[5:7]) - 1 for value in months]), n_occ)
    occ_season = original_occ * 12 + season
    # Drop unused occ-season group identifiers and remap contiguously.
    _, occ_season = np.unique(occ_season, return_inverse=True)
    fit = FROZEN.ENGINE.fit_grouped_logit_fe(
        young.reshape(-1), total, occ_season, month, regressors, max_iterations=5000
    )
    if not fit.converged:
        raise RuntimeError("occupation-specific seasonal model did not converge")
    keep = total > 0
    y, n = young.reshape(-1)[keep], total[keep]
    os, t, o, x = occ_season[keep], month[keep], original_occ[keep], regressors[keep]
    p = fit.fitted_probability[keep]
    residual = y - n * p
    weight = np.maximum(n * p * (1 - p), 1e-12)
    rx = FROZEN.ENGINE._weighted_absorb(
        x, weight, os, t, int(os.max()) + 1, n_month
    )
    bread = np.linalg.inv(rx.T @ (weight[:, None] * rx))
    scores = np.zeros((n_occ, x.shape[1]))
    np.add.at(scores, o, rx * residual[:, None])
    influence = scores @ bread.T * math.sqrt(n_occ / (n_occ - 1))
    return fit, influence, labels, {
        "fixed_effect_groups": "occupation-by-month-of-year and calendar month",
        "occupation_season_groups": int(os.max()) + 1,
        "additional_nuisance_parameters_relative_to_occupation_FE": int(n_occ * 11),
    }


def summarize_target(fit, influence: np.ndarray, target: int, signs: np.ndarray) -> dict:
    contrast = np.zeros(len(fit.beta)); contrast[target] = 1
    result, centered = CORE.bootstrap_linear(fit, influence, contrast, signs)
    return {**result, "centered_draws": centered}


def primary_setup(args: argparse.Namespace, cells: pd.DataFrame):
    frozen_pre, frozen_support, pre_months = FROZEN.read_preperiod(args.preperiod_cells)
    exposures = FROZEN.exposure_maps(args.lookup, args.rule_b_values)
    computers, names, groups = FROZEN.comp_maps(args.computerization)
    beta, webb = exposures["dv_rating_beta"]["A"], computers["webb_pct_software"]
    support = [c for c in frozen_support if np.isfinite(beta.get(c, np.nan)) and np.isfinite(webb.get(c, np.nan))]
    if len(support) != 468 or CORE.support_hash(support) != PRIMARY_SUPPORT_HASH:
        raise RuntimeError("primary support changed")
    observed = sorted(cells.month.unique())
    frozen_months = [m for m in observed if m not in MARCH_GAPS]
    frozen_static = [m for m in frozen_months if m != "2022-12"]
    young, older = panel_for_ages(cells, support, frozen_static, (22, 25), (26, 65))
    weights = (young + older).sum(axis=1)
    beta_values = np.array([beta[c] for c in support], float)
    quintiles = FROZEN.weighted_quintiles(beta_values, weights)
    webb_values = np.array([webb[c] for c in support], float)
    webb_mean, webb_sd = FROZEN.weighted_scale(webb_values, weights)
    webb_z = (webb_values - webb_mean) / webb_sd
    fit, influence, labels, _ = fit_q_model(young, older, quintiles, webb_z, frozen_static)
    coefficient = float(fit.beta[labels.index("Q5_x_post_2023_2026")])
    if not np.isclose(coefficient, PRIMARY_EXPECTED, atol=1e-8, rtol=0):
        raise RuntimeError(f"raw rebuilt primary mismatch: {coefficient} != {PRIMARY_EXPECTED}")
    return {"frozen_pre": frozen_pre, "pre_months": pre_months, "exposures": exposures,
            "computers": computers, "names": names, "groups": groups, "support": support,
            "observed_months": observed, "frozen_months": frozen_months,
            "frozen_static": frozen_static, "beta": beta, "webb": webb,
            "quintiles": quintiles, "webb_z": webb_z, "weights": weights}


def run_age_and_time(args: argparse.Namespace, cells: pd.DataFrame, setup: dict):
    support, months = setup["support"], setup["frozen_static"]
    signs = np.random.default_rng(SEED + 10).choice(np.array([-1., 1.]), size=(DRAWS, len(support)))
    comparisons = [
        ("22_25_vs_26_65", (22, 25), (26, 65)),
        ("22_25_vs_26_35", (22, 25), (26, 35)),
        ("22_25_vs_26_45", (22, 25), (26, 45)),
        ("22_25_vs_36_55", (22, 25), (36, 55)),
        ("22_25_vs_51_65", (22, 25), (51, 65)),
        ("18_21_vs_51_65", (18, 21), (51, 65)),
    ]
    rows, draw_map = [], {}
    for label, young_range, older_range in comparisons:
        young, older = panel_for_ages(cells, support, months, young_range, older_range)
        valid = (young.sum(axis=1) > 0) & (older.sum(axis=1) > 0)
        if not np.all(valid):
            # Preserve fixed classification while making the FE MLE support explicit.
            use_support = [c for c, keep in zip(support, valid) if keep]
            y, o = young[valid], older[valid]
            q, w = setup["quintiles"][valid], setup["webb_z"][valid]
            local_signs = signs[:, valid]
        else:
            use_support, y, o = support, young, older
            q, w, local_signs = setup["quintiles"], setup["webb_z"], signs
        fit, influence, labels, _ = fit_q_model(y, o, q, w, months)
        target = labels.index("Q5_x_post_2023_2026")
        item = summarize_target(fit, influence, target, local_signs)
        draw_map[label] = item.pop("centered_draws")
        rows.append({
            "analysis_status": LABEL, "comparison": label,
            "young_range": f"{young_range[0]}-{young_range[1]}",
            "older_range": f"{older_range[0]}-{older_range[1]}",
            "support_occupations": len(use_support),
            "dropped_nonexistent_FE_occupations": len(support) - len(use_support),
            "young_weighted_stock": float(y.sum()), "older_weighted_stock": float(o.sum()),
            **item,
        })
    contrast_rows = []
    base = next(row for row in rows if row["comparison"] == "22_25_vs_26_65")
    base_draw = draw_map["22_25_vs_26_65"]
    for row in rows:
        label = row["comparison"]
        if label == "22_25_vs_26_65" or row["support_occupations"] != len(support):
            continue
        delta = row["coefficient"] - base["coefficient"]
        centered = draw_map[label] - base_draw
        se = float(np.std(centered, ddof=1))
        crit = float(np.quantile(np.abs(centered / se), .95, method="higher"))
        contrast_rows.append({
            "contrast": f"{label}_minus_22_25_vs_26_65", "coefficient_difference": delta,
            "paired_se": se, "ci_lower": delta - crit * se, "ci_upper": delta + crit * se,
            "p_value": float((1 + np.sum(np.abs(centered / se) >= abs(delta / se))) / (DRAWS + 1)),
            "common_occupation_multipliers": True,
        })
    write_csv(args.output_dir / "AGE_COMPARISON_RESULTS.csv", rows)
    write_csv(args.output_dir / "AGE_COMPARISON_CONTRASTS.csv", contrast_rows)

    young, older = panel_for_ages(cells, support, months, (22, 25), (26, 65))
    periods = [
        ("2023", np.array([m[:4] == "2023" for m in months])),
        ("2024", np.array([m[:4] == "2024" for m in months])),
        ("2025_2026", np.array([m >= "2025-01" for m in months])),
    ]
    fit, influence, labels, _ = fit_q_model(young, older, setup["quintiles"], setup["webb_z"], months, periods)
    time_rows, time_draws = [], {}
    for period, _ in periods:
        target = labels.index(f"Q5_x_{period}")
        item = summarize_target(fit, influence, target, signs)
        time_draws[period] = item.pop("centered_draws")
        time_rows.append({"period": period, **item})
    for left, right in (("2024", "2023"), ("2025_2026", "2023"), ("2025_2026", "2024")):
        delta = next(r["coefficient"] for r in time_rows if r["period"] == left) - next(
            r["coefficient"] for r in time_rows if r["period"] == right)
        centered = time_draws[left] - time_draws[right]
        se = float(np.std(centered, ddof=1)); crit = float(np.quantile(np.abs(centered / se), .95, method="higher"))
        time_rows.append({"period": f"{left}_minus_{right}", "coefficient": delta,
                          "paired_bootstrap_se": se, "ci_lower": delta - crit * se,
                          "ci_upper": delta + crit * se,
                          "bootstrap_p_value": float((1 + np.sum(np.abs(centered / se) >= abs(delta / se))) /
                                                     (DRAWS + 1))})
    write_csv(args.output_dir / "TIME_HETEROGENEITY_RESULTS.csv", time_rows)
    return {"age": rows, "age_contrasts": contrast_rows, "time": time_rows}


def fit_sensitivity(cells: pd.DataFrame, setup: dict, months: list[str], label: str,
                    value: str = "stock", industry_only: bool = False,
                    support_mask: np.ndarray | None = None, recompute_q: bool = False,
                    seasonal: bool = False):
    base_support = setup["support"]
    mask = np.ones(len(base_support), dtype=bool) if support_mask is None else support_mask
    support = [c for c, keep in zip(base_support, mask) if keep]
    young, older = panel_for_ages(cells, support, months, (22, 25), (26, 65), value, industry_only)
    valid = (young.sum(axis=1) > 0) & (older.sum(axis=1) > 0)
    support = [c for c, keep in zip(support, valid) if keep]
    young, older = young[valid], older[valid]
    base_indices = np.flatnonzero(mask)[valid]
    q = setup["quintiles"][base_indices]
    w = setup["webb_z"][base_indices]
    if recompute_q:
        beta_values = np.array([setup["beta"][c] for c in support], float)
        q = FROZEN.weighted_quintiles(beta_values, (young + older).sum(axis=1))
    signs = np.random.default_rng(SEED + 20).choice(np.array([-1., 1.]), size=(DRAWS, len(support)))
    fit, influence, labels, meta = fit_q_model(young, older, q, w, months, seasonal=seasonal)
    target = labels.index("Q5_x_post_2023_2026")
    item = summarize_target(fit, influence, target, signs); item.pop("centered_draws")
    return {"analysis_status": LABEL, "specification": label, "months": len(months),
            "support_occupations": len(support), "outcome_cell_value": value,
            "industry_exclusion": industry_only, "quintiles_recomputed": recompute_q,
            "converged": bool(fit.converged), "iterations": int(fit.iterations), **meta, **item}


def run_sample_sensitivities(args: argparse.Namespace, cells: pd.DataFrame,
                             stable: pd.DataFrame, setup: dict):
    observed = setup["observed_months"]
    frozen_static = setup["frozen_static"]
    restored_static = [m for m in observed if m != "2022-12"]
    post2020 = [m for m in observed if m >= "2020-01" and m != "2022-12"]
    rows = [
        fit_sensitivity(cells, setup, frozen_static, "frozen_calendar_reproduction"),
        fit_sensitivity(cells, setup, restored_static, "restored_March_2017_2021"),
        fit_sensitivity(cells, setup, post2020, "Census2018_2020_plus_shorter_temporal_estimand"),
        fit_sensitivity(cells, setup, frozen_static, "unweighted_respondent_equivalent_cells",
                        value="respondent_equivalent"),
    ]
    # Stable Census-2010 taxonomy has its own defensible mapping, support, and
    # normalization; it is deliberately not represented as the same estimand.
    lookup = pd.read_csv(args.lookup, dtype={"occ_code": str})
    lookup = lookup.loc[lookup.lookup_role.eq("occ2010_sensitivity_all_years")].copy()
    lookup["occ_code"] = lookup.occ_code.str.zfill(4)
    beta2010 = pd.to_numeric(lookup.set_index("occ_code").dv_rating_beta, errors="coerce").to_dict()
    comp2010 = pd.read_csv(args.computerization_2010, dtype={"census2018": str, "census2010": str,
                                                           "occ_code": str, "cps_2010": str})
    code_column = next(c for c in ("cps_occ2010", "census2010", "cps_2010", "occ_code")
                       if c in comp2010.columns)
    comp2010[code_column] = comp2010[code_column].astype(str).str.zfill(4)
    webb2010 = pd.to_numeric(comp2010.set_index(code_column).webb_pct_software, errors="coerce").to_dict()
    stable_support = sorted(c for c in set(stable.occ_code)
                            if np.isfinite(beta2010.get(c, np.nan)) and np.isfinite(webb2010.get(c, np.nan)))
    stable_months = [m for m in sorted(stable.month.unique()) if m != "2022-12"]
    young, older = panel_for_ages(
        stable.assign(industry_keep=True, route_kind="stable2010", split_stock=0.0),
        stable_support, stable_months, (22, 25), (26, 65)
    )
    valid = (young.sum(axis=1) > 0) & (older.sum(axis=1) > 0)
    stable_support = [c for c, keep in zip(stable_support, valid) if keep]
    young, older = young[valid], older[valid]
    weights = (young + older).sum(axis=1)
    beta_values = np.array([beta2010[c] for c in stable_support], float)
    q = FROZEN.weighted_quintiles(beta_values, weights)
    webb_values = np.array([webb2010[c] for c in stable_support], float)
    webb_z, _, _ = CORE.standardize(webb_values, weights)
    fit, influence, labels, _ = fit_q_model(young, older, q, webb_z, stable_months)
    signs = np.random.default_rng(SEED + 21).choice(np.array([-1., 1.]), size=(DRAWS, len(stable_support)))
    item = summarize_target(fit, influence, labels.index("Q5_x_post_2023_2026"), signs)
    item.pop("centered_draws")
    rows.append({"analysis_status": LABEL, "specification": "stable_Census2010_full_calendar",
                 "months": len(stable_months), "support_occupations": len(stable_support),
                 "outcome_cell_value": "stock", "quintiles_recomputed": True,
                 "temporal_and_taxonomy_estimand_changed": True, **item})
    write_csv(args.output_dir / "CALENDAR_TAXONOMY_SENSITIVITIES.csv", rows)

    industry_rows = [
        fit_sensitivity(cells, setup, frozen_static, "IND1990_leisure_hospitality_fixed_membership",
                        industry_only=True, recompute_q=False),
        fit_sensitivity(cells, setup, frozen_static, "IND1990_leisure_hospitality_recomputed_quintiles",
                        industry_only=True, recompute_q=True),
    ]
    for row in industry_rows:
        row["IND1990_codes_excluded"] = "|".join(map(str, sorted(LEISURE_HOSPITALITY_IND1990)))
        row["coding_limit"] = "IND1990 code 800 bundles theaters and motion pictures; approximate BLS supersector concordance"
    write_csv(args.output_dir / "INDUSTRY_EXCLUSION_RESULTS.csv", industry_rows)

    counts = cells.groupby("occ_code").respondent_equivalent.sum().reindex(setup["support"]).fillna(0).to_numpy()
    size_rows = []
    for threshold in (100, 250, 500):
        size_rows.append(fit_sensitivity(
            cells, setup, frozen_static, f"minimum_full_panel_respondent_equivalent_{threshold}",
            support_mask=counts >= threshold
        ))
    write_csv(args.output_dir / "MINIMUM_SIZE_SENSITIVITIES.csv", size_rows)

    try:
        seasonal_row = fit_sensitivity(cells, setup, frozen_static,
                                       "occupation_specific_month_of_year_young_share",
                                       seasonal=True)
        seasonal_row["failure"] = ""
    except Exception as error:
        seasonal_row = {"analysis_status": LABEL,
                        "specification": "occupation_specific_month_of_year_young_share",
                        "failure": f"{type(error).__name__}: {error}",
                        "additional_nuisance_parameters_planned": len(setup["support"]) * 11}
    write_csv(args.output_dir / "SEASONALITY_SENSITIVITY.csv", [seasonal_row])
    return {"calendar_taxonomy": rows, "industry": industry_rows,
            "size": size_rows, "seasonality": seasonal_row}


def run_audits(args: argparse.Namespace, cells: pd.DataFrame, stable: pd.DataFrame,
               setup: dict, build: dict):
    months = setup["frozen_static"]
    support = setup["support"]
    young, older = panel_for_ages(cells, support, months, (22, 25), (26, 65))
    uny, uno = panel_for_ages(cells, support, months, (22, 25), (26, 65), "respondent_equivalent")
    rows = [{
        "universe": "primary_beta_Webb", "occupations": len(support), "months": len(months),
        "occupation_month_cells": len(support) * len(months),
        "weighted_young_stock": float(young.sum()), "weighted_older_stock": float(older.sum()),
        "unweighted_young_respondent_equivalent": float(uny.sum()),
        "unweighted_older_respondent_equivalent": float(uno.sum()),
        "zero_young_cells": int(np.sum(young == 0)), "zero_older_cells": int(np.sum(older == 0)),
        "empty_both_cells": int(np.sum((young + older) == 0)),
        "q1_occupations": int(np.sum(setup["quintiles"] == 1)),
        "q5_occupations": int(np.sum(setup["quintiles"] == 5)),
        "q1_employment_share": float(setup["weights"][setup["quintiles"] == 1].sum() / setup["weights"].sum()),
        "q5_employment_share": float(setup["weights"][setup["quintiles"] == 5].sum() / setup["weights"].sum()),
    }]
    write_csv(args.output_dir / "SAMPLE_CELL_AUDIT.csv", rows)
    pre = cells.loc[cells.month.lt("2020-01")]
    reconstruction = {
        "analysis_status": LABEL,
        "early_period": [str(pre.month.min()), str(pre.month.max())],
        "early_weighted_stock": float(pre.stock.sum()),
        "early_split_source_stock": float(pre.split_stock.sum()),
        "share_early_stock_from_one_to_many_sources": float(pre.split_stock.sum() / pre.stock.sum()),
        "common_conversion_proportion_property": (
            "Within each source occupation, month, and age, identical bridge weights are applied to young and older records. "
            "This preserves the source young/older ratio mechanically across all target components before aggregation with other sources."
        ),
        "bridge_source_codes": build["bridge_source_codes"],
        "one_to_many_source_codes": build["one_to_many_source_codes"],
        "maximum_source_multiplicity": build["maximum_source_multiplicity"],
        "stable_Census2010_aggregate_rows": len(stable),
    }
    write_json(args.output_dir / "RECONSTRUCTION_AUDIT.json", reconstruction)
    return {"sample": rows, "reconstruction": reconstruction}


def run(args: argparse.Namespace):
    args.output_dir.mkdir(parents=True, exist_ok=True)
    authenticated = FROZEN.validate_inputs(args)
    cells, stable, build = build_exact_age_cells(args)
    setup = primary_setup(args, cells)
    age_time = run_age_and_time(args, cells, setup)
    sensitivities = run_sample_sensitivities(args, cells, stable, setup)
    audits = run_audits(args, cells, stable, setup, build)
    outputs = [p for p in args.output_dir.iterdir() if p.is_file()]
    receipt = {
        "record": "YAX referee revision calendar-age-cell execution",
        "analysis_status": LABEL, "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "input_hashes": authenticated["hashes"], "raw_build": build,
        "baseline_coefficient_reproduced": PRIMARY_EXPECTED,
        "sections": {"age_time": age_time, "sensitivities": sensitivities, "audits": audits},
        "protected_artifacts_modified": False,
        "output_hashes": {p.name: sha256(p) for p in outputs},
    }
    write_json(args.output_dir / "CELL_EXECUTION_RECEIPT.json", receipt)
    print(json.dumps({"status": "PASS_REFEREE_CELLS", "months": build["observed_month_count"],
                      "march_restored": build["restored_march_months"],
                      "october_2025_present": build["october_2025_present"]}, indent=2))
    return receipt


def parser():
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--microdata", type=pathlib.Path, required=True)
    value.add_argument("--preperiod-cells", type=pathlib.Path, required=True)
    value.add_argument("--lookup", type=pathlib.Path, default=ROOT / "yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv")
    value.add_argument("--computerization", type=pathlib.Path, default=ROOT / "yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv")
    value.add_argument("--computerization-2010", type=pathlib.Path, default=ROOT / "yax/measurement/COMPUTERIZATION_MEASURES.csv")
    value.add_argument("--rule-b-values", type=pathlib.Path, default=ROOT / "yax/measurement/RULE_B_VALUES_CENSUS2018.csv")
    value.add_argument("--bridge", type=pathlib.Path, default=ROOT / "yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv")
    value.add_argument("--first-access-receipt", type=pathlib.Path, default=ROOT / "yax/analysis/FIRST_OUTCOME_ACCESS_RECEIPT.json")
    value.add_argument("--output-dir", type=pathlib.Path, required=True)
    return value


if __name__ == "__main__":
    run(parser().parse_args())
