#!/usr/bin/env python3
"""Execute BASE-03, the fully rebuilt corrected-treatment YAX baseline.

POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1.
The rebuilt treatment contract is completed and written before the historical
sealed pre-period support is read. Protected inputs are read-only.
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


LABEL = "POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1"
DRAWS = 9_999
SEED = 2026090521
HISTORICAL_EXPECTED = -0.13107397642233506
CALENDAR_CORRECTED_EXPECTED = -0.1345539535732939
MARCH_GAPS = {f"{year}-03" for year in range(2017, 2022)}
EXPECTED_HASHES = {
    "microdata": "3fe42477e6f2ce401e85123f0e278e758595c1c4071a8743f243a92752db38c9",
    "repair_microdata": "a4ae2ef06d66a0d47359ccceffff9a15843ac501a9f25f9a05aa8fdca9c4f911",
    "historical_preperiod_cells": "4b8c8b96caeebc4121ad4914adbadf7ebfa98d677a80b32b78a9f905956ea800",
    "lookup": "c6eb70623ea598bfc41f2352391add7a342a8809a4e57b02f2af0e75dd0223f8",
    "computerization": "352cb40834ec83225f747d316eb3e03fce1d1c5c65d80720c558177f85801fdd",
    "rule_b_values": "8092f0eef57aaf4271a7dc563a4820e2f9a6d13519bcac9372837bc7a2c991e6",
    "bridge": "0bd2f63c72e24bed2cc1cb414395c3cbddf7c00011e47ec1c1de6ae534fd1dcc",
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


def support_hash(codes) -> str:
    payload = "".join(f"{code}\n" for code in sorted(codes))
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
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def month_range(start_year: int, start_month: int, end_year: int, end_month: int) -> list[str]:
    result = []
    year, month = start_year, start_month
    while (year, month) <= (end_year, end_month):
        result.append(f"{year:04d}-{month:02d}")
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return result


def weighted_contract(values: np.ndarray, weights: np.ndarray) -> tuple[np.ndarray, np.ndarray, float, float]:
    if len(values) != len(weights) or len(values) == 0:
        raise ValueError("values and weights must be nonempty and aligned")
    if not np.all(np.isfinite(values)) or not np.all(np.isfinite(weights)) or np.any(weights <= 0):
        raise ValueError("contract inputs must be finite with strictly positive weights")
    order = np.argsort(values, kind="mergesort")
    cumulative = np.cumsum(weights[order])
    cuts = np.array([
        values[order[min(np.searchsorted(cumulative, share * cumulative[-1], side="left"), len(values) - 1)]]
        for share in (0.2, 0.4, 0.6, 0.8)
    ], dtype=float)
    if np.any(cuts[:-1] >= cuts[1:]):
        raise ValueError(f"collapsed employment-weighted cuts: {cuts.tolist()}")
    groups = np.searchsorted(cuts, values, side="left") + 1
    mean = float(np.average(values, weights=weights))
    sd = float(np.sqrt(np.average(np.square(values - mean), weights=weights)))
    if not np.isfinite(sd) or sd <= 0:
        raise ValueError("weighted scale has zero variance")
    return groups.astype(int), cuts, mean, sd


def validate_public_and_raw_inputs(args) -> dict:
    paths = {
        "microdata": args.microdata,
        "repair_microdata": args.repair_microdata,
        "lookup": args.lookup,
        "computerization": args.computerization,
        "rule_b_values": args.rule_b_values,
        "bridge": args.bridge,
    }
    observed = {name: sha256(path) for name, path in paths.items()}
    failures = {name: [observed[name], EXPECTED_HASHES[name]] for name in observed
                if observed[name] != EXPECTED_HASHES[name]}
    if failures:
        raise RuntimeError(f"input authentication failed before treatment construction: {failures}")
    return observed


def route_conservation(args, cells: pd.DataFrame) -> dict:
    bridge = pd.read_csv(args.bridge, dtype={"census_2010": str})
    bridge["census_2010"] = bridge.census_2010.str.zfill(4)
    bridge["bridge_weight"] = pd.to_numeric(bridge.bridge_weight, errors="raise")
    mass = bridge.groupby("census_2010").bridge_weight.sum().to_dict()
    raw_early_valid = raw_early_matched = expected_early_routed = 0.0
    raw_current_valid = 0.0
    rows = 0
    for path in (args.microdata, args.repair_microdata):
        for chunk in pd.read_csv(
            path, usecols=["YEAR", "AGE", "EMPSTAT", "OCC", "WTFINL"], chunksize=500_000
        ):
            rows += len(chunk)
            age = pd.to_numeric(chunk.AGE, errors="coerce")
            weight = pd.to_numeric(chunk.WTFINL, errors="coerce")
            employed = pd.to_numeric(chunk.EMPSTAT, errors="coerce").isin([10, 12])
            keep = age.between(18, 65) & employed & np.isfinite(weight) & weight.gt(0)
            chunk = chunk.loc[keep].copy()
            occ = pd.to_numeric(chunk.OCC, errors="coerce")
            valid = occ.notna() & occ.between(0, 9999) & occ.mod(1).eq(0)
            chunk = chunk.loc[valid].copy()
            chunk["source_occ"] = occ.loc[chunk.index].astype(int).map(lambda value: f"{value:04d}")
            chunk["weight"] = weight.loc[chunk.index].astype(float)
            early = chunk.loc[chunk.YEAR.le(2019)].copy()
            current = chunk.loc[chunk.YEAR.ge(2020)].copy()
            raw_early_valid += float(early.weight.sum())
            raw_current_valid += float(current.weight.sum())
            route_mass = early.source_occ.map(mass)
            matched = route_mass.notna()
            raw_early_matched += float(early.loc[matched, "weight"].sum())
            expected_early_routed += float((early.loc[matched, "weight"] * route_mass.loc[matched]).sum())
    actual_early = float(cells.loc[cells.route_kind.eq("probabilistic_2010_to_2018"), "stock"].sum())
    actual_current = float(cells.loc[cells.route_kind.eq("direct_2018"), "stock"].sum())
    early_gap = actual_early - expected_early_routed
    current_gap = actual_current - raw_current_valid
    early_scale = max(abs(expected_early_routed), 1.0)
    current_scale = max(abs(raw_current_valid), 1.0)
    passed = abs(early_gap) / early_scale < 1e-10 and abs(current_gap) / current_scale < 1e-10
    receipt = {
        "raw_rows_scanned": rows,
        "raw_early_valid_stock": raw_early_valid,
        "raw_early_matched_stock": raw_early_matched,
        "expected_early_routed_stock": expected_early_routed,
        "actual_early_routed_stock": actual_early,
        "early_absolute_gap": early_gap,
        "early_relative_gap": early_gap / early_scale,
        "raw_current_valid_stock": raw_current_valid,
        "actual_current_direct_stock": actual_current,
        "current_absolute_gap": current_gap,
        "current_relative_gap": current_gap / current_scale,
        "bridge_source_count": len(mass),
        "bridge_mass_min": float(min(mass.values())),
        "bridge_mass_max": float(max(mass.values())),
        "unmatched_early_stock": raw_early_valid - raw_early_matched,
        "early_valid_stock_route_coverage": raw_early_matched / raw_early_valid,
        "route_conservation_pass": passed,
    }
    if not passed:
        raise RuntimeError(f"source-route conservation failed: {receipt}")
    return receipt


def build_recomputed_contract(cells: pd.DataFrame, beta_map: dict, webb_map: dict, names: dict) -> dict:
    """Build BASE-03 from corrected raw cells; no sealed support is accepted or read."""
    expected_pre = month_range(2017, 1, 2022, 11)
    observed_pre = sorted(cells.loc[cells.month.between("2017-01", "2022-11"), "month"].unique())
    if observed_pre != expected_pre or len(observed_pre) != 71:
        raise RuntimeError(f"corrected preperiod calendar failed: {observed_pre}")
    pre = cells.loc[cells.month.isin(expected_pre)].copy()
    if pre.empty or pre.month.max() > "2022-11":
        raise RuntimeError("preperiod filter admitted postperiod stock")
    pre["age_group"] = np.where(
        pre.age.between(22, 25), "young",
        np.where(pre.age.between(26, 65), "older", "drop"),
    )
    pre = pre.loc[pre.age_group.ne("drop")]
    totals = pre.groupby(["occ_code", "age_group"], observed=True).stock.sum().unstack(fill_value=0.0)
    for group in ("young", "older"):
        if group not in totals:
            totals[group] = 0.0
    rows = []
    eligible = []
    for code in sorted(totals.index):
        young = float(totals.at[code, "young"])
        older = float(totals.at[code, "older"])
        beta = beta_map.get(code, np.nan)
        webb = webb_map.get(code, np.nan)
        reasons = []
        if not (np.isfinite(young) and young > 0): reasons.append("nonpositive_young_preperiod_stock")
        if not (np.isfinite(older) and older > 0): reasons.append("nonpositive_older_preperiod_stock")
        if not np.isfinite(beta): reasons.append("nonfinite_rule_A_beta")
        if not np.isfinite(webb): reasons.append("nonfinite_webb_software")
        include = not reasons
        if include: eligible.append(code)
        rows.append({
            "occupation_code": code, "occupation_name": names.get(code, code),
            "young_preperiod_stock": young, "older_preperiod_stock": older,
            "total_preperiod_stock": young + older,
            "rule_A_beta": beta if np.isfinite(beta) else "",
            "webb_pct_software": webb if np.isfinite(webb) else "",
            "eligible": include, "exclusion_reasons": ";".join(reasons),
        })
    if not eligible:
        raise RuntimeError("rebuilt support is empty")
    weights = np.array([float(totals.loc[code, ["young", "older"]].sum()) for code in eligible])
    beta_values = np.array([float(beta_map[code]) for code in eligible])
    webb_values = np.array([float(webb_map[code]) for code in eligible])
    quintiles, cuts, beta_mean, beta_sd = weighted_contract(beta_values, weights)
    _, _, webb_mean, webb_sd = weighted_contract(webb_values, weights)
    webb_z = (webb_values - webb_mean) / webb_sd
    membership = []
    for code, weight, beta, webb, wz, quintile in zip(
        eligible, weights, beta_values, webb_values, webb_z, quintiles
    ):
        membership.append({
            "occupation_code": code, "occupation_name": names.get(code, code),
            "preperiod_weight": float(weight), "rule_A_beta": float(beta),
            "beta_quintile": int(quintile), "webb_pct_software": float(webb),
            "webb_z": float(wz),
            "beta_tied_at_cut": bool(np.any(np.isclose(beta, cuts, rtol=0, atol=1e-14))),
        })
    total_weight = float(weights.sum())
    qrows = []
    for q in range(1, 6):
        mask = quintiles == q
        qrows.append({
            "quintile": q, "occupation_count": int(mask.sum()),
            "preperiod_stock": float(weights[mask].sum()),
            "preperiod_stock_share": float(weights[mask].sum() / total_weight),
            "minimum_beta": float(beta_values[mask].min()),
            "maximum_beta": float(beta_values[mask].max()),
        })
    return {
        "pre_months": expected_pre, "support": eligible, "support_rows": rows,
        "weights": weights, "beta_values": beta_values, "webb_values": webb_values,
        "quintiles": quintiles, "cuts": cuts, "webb_z": webb_z,
        "membership": membership, "quintile_rows": qrows,
        "normalization": {
            "construction_months": len(expected_pre), "construction_start": expected_pre[0],
            "construction_end": expected_pre[-1], "weight_definition": "young_plus_older_preperiod_stock",
            "beta_weighted_mean": beta_mean, "beta_weighted_sd": beta_sd,
            "webb_weighted_mean": webb_mean, "webb_weighted_sd": webb_sd,
            "total_preperiod_stock": total_weight,
            "no_postperiod_stock_used": True, "postperiod_stock_used": 0.0,
            "quintile_side_rule": "left: values equal to a cut remain in the lower quintile",
        },
    }


def regressors(quintiles: np.ndarray, webb_z: np.ndarray, months: list[str]) -> tuple[np.ndarray, list[str]]:
    post = np.array([month >= "2023-01" for month in months])
    columns = [
        (((quintiles == q)[:, None]) & post[None, :]).reshape(-1).astype(float)
        for q in (2, 3, 4, 5)
    ]
    columns.append((webb_z[:, None] * post[None, :]).reshape(-1))
    return np.column_stack(columns), ["Q2_x_post", "Q3_x_post", "Q4_x_post", "Q5_x_post", "Webb_z_x_post"]


def fit_model(FROZEN, CELLS, cells, support, months, quintiles, webb_z):
    young, older = CELLS.panel_for_ages(cells, support, months, (22, 25), (26, 65))
    x, labels = regressors(np.asarray(quintiles), np.asarray(webb_z), months)
    fit, influence = FROZEN.fit_with_influence(young, older, x)
    return fit, influence, labels, young, older


def quantile(values, share):
    try:
        return float(np.quantile(values, share, method="higher"))
    except TypeError:
        return float(np.quantile(values, share, interpolation="higher"))


def scalar_result(label, support, months, fit, influence, signs, target=3) -> tuple[dict, np.ndarray]:
    shifts = signs @ influence[:, target]
    estimate = float(fit.beta[target])
    analytic_se = float(fit.standard_error[target])
    bootstrap_se = float(np.std(shifts, ddof=1))
    studentizer = analytic_se if analytic_se > 0 else bootstrap_se
    critical = quantile(np.abs(shifts / studentizer), 0.95)
    pvalue = float((1 + np.sum(np.abs(shifts / studentizer) >= abs(estimate / studentizer))) /
                   (len(shifts) + 1))
    return ({
        "row_id": label, "analysis_status": LABEL, "coefficient": estimate,
        "analytic_cluster_se": analytic_se, "bootstrap_se": bootstrap_se,
        "ci_lower": estimate - critical * studentizer,
        "ci_upper": estimate + critical * studentizer,
        "bootstrap_p_value": pvalue, "bootstrap_critical": critical,
        "draws": len(shifts), "seed": SEED,
        "occupations": len(support), "support_hash_sha256": support_hash(support),
        "months": len(months), "first_month": months[0], "last_month": months[-1],
        "december_2022_excluded": "2022-12" not in months,
        "october_2025_present": "2025-10" in months,
    }, shifts)


def paired_delta(label, left_row, left_influence, right_row, right_influence, signs) -> tuple[dict, np.ndarray]:
    if left_row["support_hash_sha256"] != right_row["support_hash_sha256"]:
        raise RuntimeError("paired contrast attempted on unequal supports")
    centered = signs @ (left_influence[:, 3] - right_influence[:, 3])
    delta = left_row["coefficient"] - right_row["coefficient"]
    se = float(np.std(centered, ddof=1))
    critical = quantile(np.abs(centered / se), 0.95)
    pvalue = float((1 + np.sum(np.abs(centered / se) >= abs(delta / se))) / (len(centered) + 1))
    return ({
        "contrast": label, "left_row": left_row["row_id"], "right_row": right_row["row_id"],
        "coefficient_difference": delta, "paired_bootstrap_se": se,
        "ci_lower": delta - critical * se, "ci_upper": delta + critical * se,
        "paired_bootstrap_p_value": pvalue, "bootstrap_critical": critical,
        "draws": len(centered), "seed": SEED,
        "common_multipliers": True, "common_support_only": True,
        "support_hash_sha256": left_row["support_hash_sha256"],
        "occupations": left_row["occupations"],
    }, centered)


def native_contract_rows(label, support, weights, beta_values, quintiles, webb_values, webb_z, names):
    cuts = weighted_contract(np.asarray(beta_values), np.asarray(weights))[1]
    return [{
        "contract": label, "occupation_code": code, "occupation_name": names.get(code, code),
        "construction_weight": float(weight), "rule_A_beta": float(beta),
        "beta_quintile": int(q), "webb_pct_software": float(webb), "webb_z": float(wz),
        "beta_tied_at_cut": bool(np.any(np.isclose(beta, cuts, rtol=0, atol=1e-14))),
    } for code, weight, beta, q, webb, wz in zip(
        support, weights, beta_values, quintiles, webb_values, webb_z
    )]


def run(args):
    args.output_dir.mkdir(parents=True, exist_ok=True)
    repo = args.repo_root.resolve()
    FROZEN = import_path("yax_r3_rebuilt_frozen", repo / "yax/analysis/run_frozen_v11.py")
    CELLS = import_path("yax_r3_rebuilt_cells", repo / "yax/revision/referee_20260905/run_referee_cells.py")

    failures = []
    input_hashes = validate_public_and_raw_inputs(args)
    corrected_cells, _, cell_receipt = CELLS.build_exact_age_cells(args)
    route_receipt = route_conservation(args, corrected_cells)
    exposures = FROZEN.exposure_maps(args.lookup, args.rule_b_values)
    computers, names, major_groups = FROZEN.comp_maps(args.computerization)
    beta_map = exposures["dv_rating_beta"]["A"]
    webb_map = computers["webb_pct_software"]

    # This is intentionally completed before the historical sealed support is read.
    rebuilt = build_recomputed_contract(corrected_cells, beta_map, webb_map, names)
    observed = sorted(corrected_cells.month.unique())
    corrected_static = [month for month in observed if month != "2022-12"]
    if len(corrected_static) != 113 or "2025-10" in corrected_static or "2022-12" in corrected_static:
        raise RuntimeError(f"corrected static calendar failed: {corrected_static}")
    calendar_receipt = {
        "preperiod_months": rebuilt["pre_months"], "preperiod_month_count": len(rebuilt["pre_months"]),
        "preperiod_exact_January_2017_through_November_2022": True,
        "all_observed_month_count": len(observed), "all_observed_months": observed,
        "corrected_static_month_count": len(corrected_static),
        "december_2022_present_in_raw": "2022-12" in observed,
        "december_2022_excluded_static": "2022-12" not in corrected_static,
        "october_2025_missing": "2025-10" not in observed,
        "october_2025_interpolated": False,
        "restored_march_basic_months": sorted(set(observed) & MARCH_GAPS),
    }
    write_json(args.output_dir / "CALENDAR_RECEIPT.json", calendar_receipt)
    write_json(args.output_dir / "ROUTE_CONSERVATION_RECEIPT.json", route_receipt)
    write_csv(args.output_dir / "REBUILT_ELIGIBLE_UNIVERSE.csv", rebuilt["support_rows"])
    write_csv(args.output_dir / "REBUILT_TREATMENT_MEMBERSHIP.csv", rebuilt["membership"])
    write_csv(args.output_dir / "REBUILT_QUINTILE_SUPPORT.csv", rebuilt["quintile_rows"])
    write_json(args.output_dir / "REBUILT_NORMALIZATION_AND_CUTS.json", {
        **rebuilt["normalization"], "beta_quintile_cuts": rebuilt["cuts"].tolist(),
        "support_occupations": len(rebuilt["support"]),
        "support_hash_sha256": support_hash(rebuilt["support"]),
    })
    prefit = {
        "status": "PASS_PREFIT_REBUILT_CONTRACT",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "historical_sealed_support_read": False,
        "rebuilt_from_corrected_cells_only": True,
        "no_postperiod_stock_used": rebuilt["normalization"]["no_postperiod_stock_used"],
        "rule_A_beta_required": True, "finite_webb_required": True,
        "positive_preperiod_stock_both_age_groups_required": True,
        "route_conservation_pass": route_receipt["route_conservation_pass"],
        "calendar_pass": calendar_receipt["preperiod_exact_January_2017_through_November_2022"],
        "support_hash_sha256": support_hash(rebuilt["support"]),
        "input_hashes_excluding_historical_sealed_cells": input_hashes,
    }
    write_json(args.output_dir / "PREFIT_GATE.json", prefit)

    # Historical comparison artifacts may be read only after PREFIT_GATE exists.
    if not (args.output_dir / "PREFIT_GATE.json").is_file():
        raise RuntimeError("historical access attempted before the rebuilt-contract prefit gate")
    historical_hash = sha256(args.historical_preperiod_cells)
    if historical_hash != EXPECTED_HASHES["historical_preperiod_cells"]:
        raise RuntimeError("historical sealed preperiod hash mismatch")
    input_hashes["historical_preperiod_cells"] = historical_hash
    args.preperiod_cells = args.historical_preperiod_cells
    authenticated_historical_inputs = FROZEN.validate_inputs(args)
    historical = CELLS.primary_setup(args, corrected_cells)
    h_support = historical["support"]
    h_beta = np.array([beta_map[code] for code in h_support], float)
    h_webb = np.array([webb_map[code] for code in h_support], float)
    h_q = np.asarray(historical["quintiles"], int)
    h_wz = np.asarray(historical["webb_z"], float)
    h_weights = np.asarray(historical["weights"], float)
    _, h_cuts, h_beta_mean, h_beta_sd = weighted_contract(h_beta, h_weights)
    _, _, h_webb_mean, h_webb_sd = weighted_contract(h_webb, h_weights)
    native_rows = native_contract_rows(
        "historical_production_full_static_weight", h_support, h_weights, h_beta, h_q, h_webb, h_wz, names
    )
    native_rows.extend(native_contract_rows(
        "rebuilt_corrected_preperiod_weight", rebuilt["support"], rebuilt["weights"],
        rebuilt["beta_values"], rebuilt["quintiles"], rebuilt["webb_values"], rebuilt["webb_z"], names
    ))
    write_csv(args.output_dir / "NATIVE_TREATMENT_CONTRACTS.csv", native_rows)
    write_csv(args.output_dir / "TREATMENT_CONTRACT_SUMMARY.csv", [
        {
            "contract": "historical_production_full_static_weight",
            "construction_window": "historical 108-month full static panel including postperiod",
            "support_occupations": len(h_support), "support_hash_sha256": support_hash(h_support),
            "total_construction_stock": float(h_weights.sum()),
            "beta_weighted_mean": h_beta_mean, "beta_weighted_sd": h_beta_sd,
            "beta_quintile_cuts_json": json.dumps(h_cuts.tolist()),
            "webb_weighted_mean": h_webb_mean, "webb_weighted_sd": h_webb_sd,
            "postperiod_stock_used": True,
        },
        {
            "contract": "rebuilt_corrected_preperiod_weight",
            "construction_window": "2017-01 through 2022-11 corrected 71-month preperiod",
            "support_occupations": len(rebuilt["support"]),
            "support_hash_sha256": support_hash(rebuilt["support"]),
            "total_construction_stock": rebuilt["normalization"]["total_preperiod_stock"],
            "beta_weighted_mean": rebuilt["normalization"]["beta_weighted_mean"],
            "beta_weighted_sd": rebuilt["normalization"]["beta_weighted_sd"],
            "beta_quintile_cuts_json": json.dumps(rebuilt["cuts"].tolist()),
            "webb_weighted_mean": rebuilt["normalization"]["webb_weighted_mean"],
            "webb_weighted_sd": rebuilt["normalization"]["webb_weighted_sd"],
            "postperiod_stock_used": False,
        },
    ])

    h_signs = np.random.default_rng(SEED).choice(np.array([-1.0, 1.0]), size=(DRAWS, len(h_support)))
    h_fit, h_inf, _, _, _ = fit_model(
        FROZEN, CELLS, corrected_cells, h_support, historical["frozen_static"], h_q, h_wz
    )
    row1, shift1 = scalar_result(
        "historical_108_historical_treatment", h_support, historical["frozen_static"], h_fit, h_inf, h_signs
    )
    if not np.isclose(row1["coefficient"], HISTORICAL_EXPECTED, atol=1e-8, rtol=0):
        raise RuntimeError(f"historical baseline failed: {row1['coefficient']}")
    c_hist_fit, c_hist_inf, _, _, _ = fit_model(
        FROZEN, CELLS, corrected_cells, h_support, corrected_static, h_q, h_wz
    )
    row2, shift2 = scalar_result(
        "corrected_113_historical_treatment", h_support, corrected_static,
        c_hist_fit, c_hist_inf, h_signs
    )
    if not np.isclose(row2["coefficient"], CALENDAR_CORRECTED_EXPECTED, atol=1e-8, rtol=0):
        raise RuntimeError(f"calendar-corrected baseline failed: {row2['coefficient']}")

    r_support = rebuilt["support"]
    r_signs = np.random.default_rng(SEED).choice(np.array([-1.0, 1.0]), size=(DRAWS, len(r_support)))
    r_fit, r_inf, _, _, _ = fit_model(
        FROZEN, CELLS, corrected_cells, r_support, corrected_static,
        rebuilt["quintiles"], rebuilt["webb_z"]
    )
    row3, shift3 = scalar_result(
        "corrected_113_recomputed_preperiod_treatment", r_support, corrected_static,
        r_fit, r_inf, r_signs
    )
    models = [row1, row2, row3]
    pairs = []
    pair_draw_rows = []
    calendar_pair, calendar_centered = paired_delta(
        "corrected_calendar_minus_historical_calendar_same_treatment",
        row2, c_hist_inf, row1, h_inf, h_signs,
    )
    pairs.append(calendar_pair)
    pair_draw_rows.extend({"contrast": calendar_pair["contrast"], "draw": i + 1, "centered_draw": float(value)}
                          for i, value in enumerate(calendar_centered))

    common = sorted(set(h_support) & set(r_support))
    h_index = {code: i for i, code in enumerate(h_support)}
    r_index = {code: i for i, code in enumerate(r_support)}
    h_common_q = np.array([h_q[h_index[code]] for code in common], int)
    h_common_wz = np.array([h_wz[h_index[code]] for code in common], float)
    r_common_q = np.array([rebuilt["quintiles"][r_index[code]] for code in common], int)
    r_common_wz = np.array([rebuilt["webb_z"][r_index[code]] for code in common], float)
    support_changed = row2["support_hash_sha256"] != row3["support_hash_sha256"]
    comparison_rows = [{
        "contrast": "recomputed_treatment_minus_historical_treatment_native_supports",
        "left_row": row3["row_id"], "right_row": row2["row_id"],
        "coefficient_difference": row3["coefficient"] - row2["coefficient"],
        "support_changed": support_changed, "paired_inference_valid": not support_changed,
        "paired_result_reported": False if support_changed else True,
        "interpretation": (
            "descriptive support-changing difference; not a paired treatment contrast"
            if support_changed else "same-support treatment contrast"
        ),
        "historical_support_occupations": len(h_support),
        "rebuilt_support_occupations": len(r_support),
        "common_support_occupations": len(common),
        "historical_only_occupations": len(set(h_support) - set(r_support)),
        "rebuilt_only_occupations": len(set(r_support) - set(h_support)),
    }]
    if support_changed:
        common_signs = np.random.default_rng(SEED).choice(
            np.array([-1.0, 1.0]), size=(DRAWS, len(common))
        )
        hc_fit, hc_inf, _, _, _ = fit_model(
            FROZEN, CELLS, corrected_cells, common, corrected_static, h_common_q, h_common_wz
        )
        rc_fit, rc_inf, _, _, _ = fit_model(
            FROZEN, CELLS, corrected_cells, common, corrected_static, r_common_q, r_common_wz
        )
        row4h, _ = scalar_result(
            "corrected_113_common_support_native_historical_treatment", common, corrected_static,
            hc_fit, hc_inf, common_signs
        )
        row4r, _ = scalar_result(
            "corrected_113_common_support_native_recomputed_treatment", common, corrected_static,
            rc_fit, rc_inf, common_signs
        )
        models.extend([row4h, row4r])
        reclass_pair, reclass_centered = paired_delta(
            "native_recomputed_minus_native_historical_on_fixed_common_support",
            row4r, rc_inf, row4h, hc_inf, common_signs,
        )
        reclass_pair["changed_quintile_memberships"] = int(np.sum(h_common_q != r_common_q))
        reclass_pair["interpretation"] = (
            "fixed outcome/support comparison of native weighting, cut, membership, and Webb-normalization contracts"
        )
        pairs.append(reclass_pair)
        pair_draw_rows.extend({
            "contrast": reclass_pair["contrast"], "draw": i + 1,
            "centered_draw": float(value),
        } for i, value in enumerate(reclass_centered))
    else:
        direct, centered = paired_delta(
            "recomputed_treatment_minus_historical_treatment_same_support",
            row3, r_inf, row2, c_hist_inf, r_signs,
        )
        direct["changed_quintile_memberships"] = int(np.sum(h_common_q != r_common_q))
        direct["interpretation"] = (
            "native treatment contracts on an exactly identical occupation support"
        )
        pairs.append(direct)
        pair_draw_rows.extend({"contrast": direct["contrast"], "draw": i + 1, "centered_draw": float(value)}
                              for i, value in enumerate(centered))

    common_rows = []
    for code, hq, rq, hwz, rwz in zip(common, h_common_q, r_common_q, h_common_wz, r_common_wz):
        common_rows.append({
            "occupation_code": code, "occupation_name": names.get(code, code),
            "soc_major_group": major_groups.get(code, ""),
            "historical_native_quintile": int(hq), "rebuilt_native_quintile": int(rq),
            "quintile_changed": bool(hq != rq),
            "historical_native_webb_z": float(hwz), "rebuilt_native_webb_z": float(rwz),
        })
    write_csv(args.output_dir / "BASELINE_DECOMPOSITION.csv", models)
    write_csv(args.output_dir / "PAIRED_COMPARISONS.csv", pairs)
    write_csv(args.output_dir / "PAIRED_CENTERED_DRAWS.csv", pair_draw_rows)
    write_csv(args.output_dir / "SUPPORT_CHANGING_COMPARISONS.csv", comparison_rows)
    write_csv(args.output_dir / "COMMON_SUPPORT_RECLASSIFICATION.csv", common_rows)
    write_json(args.output_dir / "MODEL_FAILURES.json", failures)

    output_hashes = {
        path.name: sha256(path) for path in sorted(args.output_dir.iterdir())
        if path.is_file()
        and path.name not in {"EXECUTION_RECEIPT.json", "SELF_CHECK.json"}
    }
    receipt = {
        "record": "YAX BASE-03 fully rebuilt corrected-treatment baseline",
        "analysis_status": LABEL, "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
        "script_sha256": sha256(pathlib.Path(__file__)),
        "analysis_spec_sha256": sha256(pathlib.Path(__file__).with_name("ANALYSIS_SPEC.md")),
        "input_hashes": input_hashes,
        "frozen_input_authentication": authenticated_historical_inputs,
        "historical_sealed_support_read_only_after_prefit_gate": True,
        "prefit_gate_sha256": sha256(args.output_dir / "PREFIT_GATE.json"),
        "calendar_receipt": calendar_receipt, "cell_build_receipt": cell_receipt,
        "route_conservation_receipt": route_receipt,
        "rebuilt_contract": {
            **rebuilt["normalization"], "beta_quintile_cuts": rebuilt["cuts"].tolist(),
            "support_occupations": len(r_support), "support_hash_sha256": support_hash(r_support),
        },
        "historical_contract": {
            "support_occupations": len(h_support), "support_hash_sha256": support_hash(h_support),
            "treatment_weight_window": "historical 108-month full static panel including postperiod",
        },
        "common_support": {
            "occupations": len(common), "support_hash_sha256": support_hash(common),
            "changed_quintile_memberships": int(np.sum(h_common_q != r_common_q)),
        },
        "bootstrap": {"draws": DRAWS, "seed": SEED, "cluster": "occupation",
                      "common_multipliers_only_on_exact_common_support": True},
        "model_rows": models, "paired_comparisons": pairs,
        "support_changing_comparisons": comparison_rows, "failures": failures,
        "output_hashes": output_hashes,
    }
    write_json(args.output_dir / "EXECUTION_RECEIPT.json", receipt)
    print(json.dumps({
        "status": "PASS_BASE_03_REBUILT_BASELINE",
        "historical": row1["coefficient"], "calendar_corrected": row2["coefficient"],
        "fully_rebuilt": row3["coefficient"], "historical_support": len(h_support),
        "rebuilt_support": len(r_support), "common_support": len(common),
        "changed_common_quintiles": int(np.sum(h_common_q != r_common_q)),
    }, indent=2, sort_keys=True))


def parser():
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--repo-root", type=pathlib.Path, required=True)
    value.add_argument("--microdata", type=pathlib.Path, required=True)
    value.add_argument("--repair-microdata", type=pathlib.Path, required=True)
    value.add_argument("--historical-preperiod-cells", type=pathlib.Path, required=True)
    value.add_argument("--lookup", type=pathlib.Path, required=True)
    value.add_argument("--computerization", type=pathlib.Path, required=True)
    value.add_argument("--rule-b-values", type=pathlib.Path, required=True)
    value.add_argument("--bridge", type=pathlib.Path, required=True)
    value.add_argument("--first-access-receipt", type=pathlib.Path, required=True)
    value.add_argument("--output-dir", type=pathlib.Path, required=True)
    return value


if __name__ == "__main__":
    run(parser().parse_args())
