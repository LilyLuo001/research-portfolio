#!/usr/bin/env python3
"""Run current-contract Gate 3 bridge, service, and influence sensitivities."""
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
SEED = 202609086401
MEMBERSHIP_SHA256 = "c76eb85956e4a413e130bab53fe8c50616cf6d7a02c81c266ec369879dd56bc1"
BRIDGE_SHA256 = "0bd2f63c72e24bed2cc1cb414395c3cbddf7c00011e47ec1c1de6ae534fd1dcc"
EXPECTED_POOLED = -0.13210945079219025
EXPECTED_FAMILY = -0.021674952018246537
SYMMETRIC_K = (0.25, 0.5, 2.0 / 3.0, 1.0, 1.5, 2.0, 4.0)
ADVERSE_K = (0.05, 0.25, 1.0, 4.0, 20.0)
MARCH_REPAIRS = {f"{year}-03" for year in range(2017, 2022)}
HISTORICAL_DELETION_ORDER = (
    "4055", "5240", "3601", "1108", "5860", "5740", "4030", "9620", "4850", "1021",
    "1430", "6355", "5120", "5840", "4510", "2350", "0630", "0910", "5100", "4600",
)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CORE = load_module("yax_mapping_core", HERE.parent / "inference_validation" /
                   "inference_engine.py")
ENGINE = load_module("yax_mapping_engine",
                     ROOT / "dax/memo/power_calcs/young_relative_employment_power.py")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def support_hash(codes: list[str] | np.ndarray) -> str:
    payload = "".join(f"{value}\n" for value in np.asarray(codes, str).tolist())
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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


def weighted_contract(values: np.ndarray, weights: np.ndarray) -> dict[str, Any]:
    values = np.asarray(values, float)
    weights = np.asarray(weights, float)
    require(values.shape == weights.shape and len(values) > 4,
            "contract arrays are empty or misaligned")
    require(np.all(np.isfinite(values)) and np.all(np.isfinite(weights))
            and np.all(weights > 0), "contract values or weights are invalid")
    order = np.argsort(values, kind="mergesort")
    cumulative = np.cumsum(weights[order])
    cuts = np.asarray([
        values[order[min(np.searchsorted(cumulative, share * cumulative[-1], side="left"),
                         len(values) - 1)]]
        for share in (0.2, 0.4, 0.6, 0.8)
    ])
    require(np.all(cuts[:-1] < cuts[1:]), "weighted quintile cuts collapse")
    groups = np.searchsorted(cuts, values, side="left") + 1
    mean = float(np.average(values, weights=weights))
    sd = float(np.sqrt(np.average(np.square(values - mean), weights=weights)))
    require(np.isfinite(sd) and sd > 0, "weighted scale collapses")
    return {"groups": groups.astype(int), "cuts": cuts, "mean": mean, "sd": sd}


def month_string(frame: pd.DataFrame) -> pd.Series:
    return (pd.to_numeric(frame.YEAR, errors="raise").astype(int).astype(str) + "-" +
            pd.to_numeric(frame.MONTH, errors="raise").astype(int).astype(str).str.zfill(2))


def read_source_cells(wide: Path, repair: Path, months: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    early_parts: list[pd.DataFrame] = []
    direct_parts: list[pd.DataFrame] = []
    counters: dict[str, Any] = {
        "raw_rows": 0, "wide_repair_month_rows_removed": 0,
        "active_records": 0, "early_source_records": 0,
        "direct_target_records": 0,
    }
    usecols = ["YEAR", "MONTH", "AGE", "EMPSTAT", "OCC", "WTFINL"]
    for source, path in (("wide", wide), ("repair", repair)):
        for chunk in pd.read_csv(path, usecols=usecols, chunksize=500_000):
            counters["raw_rows"] += len(chunk)
            chunk["month"] = month_string(chunk)
            if source == "wide":
                bad = chunk.month.isin(MARCH_REPAIRS)
                counters["wide_repair_month_rows_removed"] += int(bad.sum())
                chunk = chunk.loc[~bad].copy()
            else:
                require(set(chunk.month.unique()).issubset(MARCH_REPAIRS),
                        "March-repair file contains another month")
            age = pd.to_numeric(chunk.AGE, errors="coerce")
            weight = pd.to_numeric(chunk.WTFINL, errors="coerce")
            occ = pd.to_numeric(chunk.OCC, errors="coerce")
            keep = (age.between(22, 65) &
                    pd.to_numeric(chunk.EMPSTAT, errors="coerce").isin([10, 12]) &
                    np.isfinite(weight) & weight.gt(0) & occ.notna() &
                    occ.between(0, 9999) & occ.mod(1).eq(0) & chunk.month.isin(months))
            chunk = chunk.loc[keep].copy()
            if chunk.empty:
                continue
            chunk["age_group"] = np.where(age.loc[chunk.index].between(22, 25),
                                                "young", "older")
            chunk["occ"] = occ.loc[chunk.index].astype(int).map(lambda value: f"{value:04d}")
            chunk["stock"] = weight.loc[chunk.index].astype(float)
            counters["active_records"] += len(chunk)
            early = chunk.loc[pd.to_numeric(chunk.YEAR, errors="raise").le(2019)]
            direct = chunk.loc[pd.to_numeric(chunk.YEAR, errors="raise").ge(2020)]
            counters["early_source_records"] += len(early)
            counters["direct_target_records"] += len(direct)
            if not early.empty:
                early_parts.append(early.groupby(["occ", "month", "age_group"], as_index=False,
                                                 observed=True).stock.sum()
                                   .rename(columns={"occ": "source_occ"}))
            if not direct.empty:
                direct_parts.append(direct.groupby(["occ", "month", "age_group"], as_index=False,
                                                   observed=True).stock.sum()
                                    .rename(columns={"occ": "target_occ"}))
    require(bool(early_parts) and bool(direct_parts), "raw aggregation produced an empty period")
    early = (pd.concat(early_parts, ignore_index=True)
             .groupby(["source_occ", "month", "age_group"], as_index=False,
                      observed=True).stock.sum())
    direct = (pd.concat(direct_parts, ignore_index=True)
              .groupby(["target_occ", "month", "age_group"], as_index=False,
                       observed=True).stock.sum())
    counters["early_aggregate_rows"] = len(early)
    counters["direct_aggregate_rows"] = len(direct)
    return early, direct, counters


def prepare_bridge(path: Path, support: list[str], beta: dict[str, float],
                   webb: dict[str, float]) -> tuple[pd.DataFrame, pd.DataFrame, set[str]]:
    full = pd.read_csv(path, dtype={"census_2010": str, "census_2018": str},
                       float_precision="round_trip")
    required = {"census_2010", "census_2018", "bridge_weight"}
    require(required.issubset(full.columns), "bridge schema differs")
    full["census_2010"] = full.census_2010.str.zfill(4)
    full["census_2018"] = full.census_2018.str.zfill(4)
    full["bridge_weight"] = pd.to_numeric(full.bridge_weight, errors="raise")
    require(not full[["census_2010", "census_2018"]].duplicated().any(),
            "bridge route duplicates")
    sums = full.groupby("census_2010").bridge_weight.sum().to_numpy(float)
    require(float(np.max(np.abs(sums - 1))) <= 5e-7,
            "full official bridge does not conserve source mass")
    multiplicity = full.groupby("census_2010").census_2018.nunique()
    split_sources = set(multiplicity[multiplicity > 1].index)
    split_targets = set(full.loc[full.census_2010.isin(split_sources), "census_2018"])
    routed = full.loc[full.census_2018.isin(support)].copy()
    routed["supported_mass"] = routed.groupby("census_2010").bridge_weight.transform("sum")
    routed["beta"] = routed.census_2018.map(beta)
    routed["webb"] = routed.census_2018.map(webb)
    routed["rank"] = 0.0
    routed["eligible"] = False
    for _, index in routed.groupby("census_2010", sort=False).groups.items():
        idx = np.asarray(list(index), int)
        values = routed.loc[idx, "beta"].to_numpy(float)
        software = routed.loc[idx, "webb"].to_numpy(float)
        eligible = (len(idx) >= 2 and np.all(np.isfinite(values)) and
                    np.all(np.isfinite(software)) and np.ptp(values) > 0)
        if not eligible:
            continue
        ranks = pd.Series(values).rank(method="average").to_numpy(float)
        ranks = (ranks - ranks.min()) / (ranks.max() - ranks.min()) - 0.5
        routed.loc[idx, "rank"] = ranks
        routed.loc[idx, "eligible"] = True
    return full, routed, split_targets


def allocation_table(routes: pd.DataFrame, young_k: float,
                     older_k: float) -> pd.DataFrame:
    require(young_k > 0 and older_k > 0, "allocation odds must be positive")
    frames: list[pd.DataFrame] = []
    for age, value in (("young", young_k), ("older", older_k)):
        work = routes.copy()
        if value == 1.0:
            work["scenario_weight"] = work.bridge_weight
        else:
            multiplier = np.ones(len(work))
            eligible = work.eligible.to_numpy(bool)
            multiplier[eligible] = np.exp(math.log(value) * work.loc[eligible, "rank"].to_numpy(float))
            work["scenario_weight"] = work.bridge_weight.to_numpy(float) * multiplier
            denominator = work.groupby("census_2010").scenario_weight.transform("sum")
            work["scenario_weight"] *= work.supported_mass / denominator
        work["age_group"] = age
        frames.append(work)
    result = pd.concat(frames, ignore_index=True)
    sums = result.groupby(["age_group", "census_2010"]).scenario_weight.sum()
    targets = result.groupby(["age_group", "census_2010"]).supported_mass.first()
    require(float(np.max(np.abs(sums.to_numpy() - targets.to_numpy()))) <= 1e-12,
            "allocation table changes supported source mass")
    return result


def expand_panel(early: pd.DataFrame, direct: pd.DataFrame, allocation: pd.DataFrame,
                 support: list[str], months: list[str]) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    routes = allocation[["census_2010", "census_2018", "age_group", "scenario_weight"]]
    expanded = early.merge(routes, left_on=["source_occ", "age_group"],
                           right_on=["census_2010", "age_group"], how="inner",
                           validate="many_to_many")
    expanded["routed_stock"] = expanded.stock * expanded.scenario_weight
    official = routes.copy()
    official["official_weight"] = allocation.bridge_weight.to_numpy(float)
    official = official.drop(columns="scenario_weight")
    expected = early.merge(official, left_on=["source_occ", "age_group"],
                           right_on=["census_2010", "age_group"], how="inner",
                           validate="many_to_many")
    expected["official_stock"] = expected.stock * expected.official_weight
    observed_mass = expanded.groupby(["source_occ", "month", "age_group"]).routed_stock.sum()
    expected_mass = expected.groupby(["source_occ", "month", "age_group"]).official_stock.sum()
    aligned = observed_mass.to_frame("observed").join(expected_mass.to_frame("expected"), how="outer").fillna(0)
    absolute = float(np.max(np.abs(aligned.observed - aligned.expected)))
    relative = float(np.max(np.abs(aligned.observed - aligned.expected) /
                            np.maximum(aligned.expected, 1.0)))
    require(relative <= 1e-11, "source-age-month routed mass changed")
    left = expanded[["census_2018", "month", "age_group", "routed_stock"]].rename(
        columns={"census_2018": "target_occ", "routed_stock": "stock"})
    right = direct.loc[direct.target_occ.isin(support),
                       ["target_occ", "month", "age_group", "stock"]]
    combined = pd.concat([left, right], ignore_index=True)
    grouped = combined.groupby(["target_occ", "month", "age_group"], as_index=False,
                               observed=True).stock.sum()
    index = pd.MultiIndex.from_product([support, months], names=["target_occ", "month"])
    pivot = grouped.pivot_table(index=["target_occ", "month"], columns="age_group",
                                values="stock", aggfunc="sum", fill_value=0.0).reindex(index).fillna(0)
    for column in ("young", "older"):
        if column not in pivot:
            pivot[column] = 0.0
    return (pivot.young.to_numpy(float).reshape(len(support), len(months)),
            pivot.older.to_numpy(float).reshape(len(support), len(months)),
            {"maximum_absolute_source_age_month_gap": absolute,
             "maximum_relative_source_age_month_gap": relative})


def pad_influence(fit: Any, keep: np.ndarray, families: np.ndarray,
                  global_families: list[str]) -> tuple[np.ndarray, np.ndarray]:
    occupation = np.zeros(len(keep))
    occupation[keep] = fit.occupation_influence[:, CORE.TARGET_INDEX]
    family = np.zeros(len(global_families))
    local = sorted(set(families[keep].tolist()))
    lookup = {value: index for index, value in enumerate(global_families)}
    for index, value in enumerate(local):
        family[lookup[value]] = fit.family_influence[index, CORE.TARGET_INDEX]
    return occupation, family


def fit_model(model_id: str, structure: str, young: np.ndarray, older: np.ndarray,
              keep: np.ndarray, quintiles: np.ndarray, webb_z: np.ndarray,
              families: np.ndarray, occupations: np.ndarray,
              months: list[str], multipliers: dict[str, np.ndarray],
              metadata: dict[str, Any]) -> dict[str, Any]:
    require(keep.shape == (len(occupations),) and keep.sum() > 4, "invalid model support")
    require(set(quintiles[keep].tolist()) == {1, 2, 3, 4, 5},
            f"{model_id} loses an exposure quintile")
    design = CORE.build_design(quintiles[keep], webb_z[keep], families[keep], months, structure)
    fit = CORE.fit_with_influence(
        ENGINE, young[keep].reshape(-1), (young[keep] + older[keep]).reshape(-1), design)
    global_families = sorted(set(families.tolist()))
    occ_influence, fam_influence = pad_influence(fit, keep, families, global_families)
    occ = CORE.multiplier_interval(fit.estimate, occ_influence,
                                   multipliers["occupation"])
    fam = CORE.multiplier_interval(fit.estimate, fam_influence,
                                   multipliers["family"])
    row = {
        "model_id": model_id, "structure": structure,
        "support_occupations": int(keep.sum()),
        "support_hash_sha256": support_hash(occupations[keep]),
        "coefficient_Q5_x_post": fit.estimate,
        "occupation_se": occ["se"], "occupation_ci_lower": occ["lower"],
        "occupation_ci_upper": occ["upper"], "occupation_multiplier_p": occ["p_value"],
        "family_se": fam["se"], "family_ci_lower": fam["lower"],
        "family_ci_upper": fam["upper"], "family_multiplier_p": fam["p_value"],
        "iterations": fit.iterations,
        "maximum_normalized_score": fit.maximum_normalized_score,
        "separated_observations": fit.separated_observation_count,
        **metadata,
    }
    return {"row": row, "occupation_influence": occ_influence,
            "family_influence": fam_influence}


def paired_row(comparison: str, left: dict[str, Any], right: dict[str, Any],
               multipliers: dict[str, np.ndarray]) -> dict[str, Any]:
    estimate = left["row"]["coefficient_Q5_x_post"] - right["row"]["coefficient_Q5_x_post"]
    oi = left["occupation_influence"] - right["occupation_influence"]
    fi = left["family_influence"] - right["family_influence"]
    occ = CORE.multiplier_interval(estimate, oi, multipliers["occupation"])
    fam = CORE.multiplier_interval(estimate, fi, multipliers["family"])
    return {
        "comparison": comparison, "left_model": left["row"]["model_id"],
        "right_model": right["row"]["model_id"],
        "estimate_left_minus_right": estimate,
        "occupation_se": occ["se"], "occupation_ci_lower": occ["lower"],
        "occupation_ci_upper": occ["upper"], "occupation_multiplier_p": occ["p_value"],
        "family_se": fam["se"], "family_ci_lower": fam["lower"],
        "family_ci_upper": fam["upper"], "family_multiplier_p": fam["p_value"],
        "common_draws_preserve_covariance": True,
        "interpretation_if_interval_contains_zero": "design does not detect a difference; not equivalence",
    }


def rebuilt_labels(beta: np.ndarray, webb: np.ndarray, young: np.ndarray,
                   older: np.ndarray, months: list[str]) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    pre = np.asarray([value <= "2022-11" for value in months], bool)
    weights = (young[:, pre] + older[:, pre]).sum(axis=1)
    contract = weighted_contract(beta, weights)
    webb_mean = float(np.average(webb, weights=weights))
    webb_sd = float(np.sqrt(np.average(np.square(webb - webb_mean), weights=weights)))
    require(np.isfinite(webb_sd) and webb_sd > 0, "rebuilt Webb scale collapses")
    return contract["groups"], (webb - webb_mean) / webb_sd, {
        "construction_weight_total": float(weights.sum()),
        "beta_cut_1": float(contract["cuts"][0]), "beta_cut_2": float(contract["cuts"][1]),
        "beta_cut_3": float(contract["cuts"][2]), "beta_cut_4": float(contract["cuts"][3]),
        "webb_mean": webb_mean, "webb_sd": webb_sd,
    }


def influence_rows(model: dict[str, Any], occupations: np.ndarray,
                   families: list[str]) -> list[dict[str, Any]]:
    rows = [{"model_id": model["row"]["model_id"], "cluster_type": "occupation",
             "cluster_id": code, "influence_Q5_x_post": float(value)}
            for code, value in zip(occupations, model["occupation_influence"])]
    rows.extend({"model_id": model["row"]["model_id"], "cluster_type": "family",
                 "cluster_id": code, "influence_Q5_x_post": float(value)}
                for code, value in zip(families, model["family_influence"]))
    return rows


def carry_forward_rows(stable_path: Path, timing_path: Path) -> list[dict[str, Any]]:
    stable = pd.read_csv(stable_path, float_precision="round_trip")
    row = stable.loc[stable.specification.eq("stable_Census2010_observed_calendar")]
    require(len(row) == 1, "stable-Census2010 result is absent")
    stable_row = row.iloc[0]
    timing = pd.read_csv(timing_path, float_precision="round_trip")
    selected = timing.loc[timing.model_id.isin(
        ["post_2020_unconditioned", "post_2020_family_month"])]
    require(len(selected) == 2, "post-2020 current-contract rows are absent")
    result = [{
        "source_block": "stable_Census2010_prior_audit",
        "model_id": "stable_Census2010_observed_calendar",
        "coefficient_Q5_x_post": float(stable_row.coefficient),
        "occupation_se": float(stable_row.analytic_or_paired_se),
        "occupation_ci_lower": float(stable_row.ci_lower),
        "occupation_ci_upper": float(stable_row.ci_upper),
        "support_occupations": int(stable_row.support_occupations),
        "months": int(stable_row.months),
        "changed_population_or_labels": True,
        "interpretation": "stable Census-2010 taxonomy; changed occupation population, exposure mapping, and labels",
        "source_path": str(stable_path.relative_to(ROOT)),
        "source_sha256": sha256_file(stable_path),
    }]
    for _, value in selected.sort_values("model_id").iterrows():
        result.append({
            "source_block": "current_contract_post_2020_gate2",
            "model_id": value.model_id,
            "coefficient_Q5_x_post": float(value.coefficient),
            "occupation_se": float(value.occupation_se),
            "occupation_ci_lower": float(value.occupation_ci_lower),
            "occupation_ci_upper": float(value.occupation_ci_upper),
            "support_occupations": int(value.support_occupations),
            "months": int(value.months),
            "changed_population_or_labels": False,
            "interpretation": "current 468-occupation labels; post-2020 coding-stable calendar",
            "source_path": str(timing_path.relative_to(ROOT)),
            "source_sha256": sha256_file(timing_path),
        })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--microdata", type=Path, required=True)
    parser.add_argument("--repair-microdata", type=Path, required=True)
    parser.add_argument("--bridge", type=Path, required=True)
    parser.add_argument("--membership", type=Path, required=True)
    parser.add_argument("--private-calibration", type=Path, required=True)
    parser.add_argument("--calibration-receipt", type=Path, required=True)
    parser.add_argument("--stable-taxonomy-results", type=Path, required=True)
    parser.add_argument("--timing-model-results", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output_dir.exists(), "refusing to overwrite mapping output")
    require(sha256_file(args.membership) == MEMBERSHIP_SHA256, "membership hash differs")
    require(sha256_file(args.bridge) == BRIDGE_SHA256, "bridge hash differs")
    receipt = json.loads(args.calibration_receipt.read_text(encoding="utf-8"))
    require(receipt.get("status") == "PASS_PRIVATE_CALIBRATION_BUILD",
            "private calibration receipt does not pass")
    require(sha256_file(args.private_calibration) == receipt.get("private_npz_sha256"),
            "private calibration hash differs")
    require(sha256_file(args.microdata) == receipt["input_hashes"]["wide_microdata"],
            "wide microdata hash differs")
    require(sha256_file(args.repair_microdata) == receipt["input_hashes"]["march_repair"],
            "March repair hash differs")
    with np.load(args.private_calibration, allow_pickle=False) as loaded:
        arrays = {name: loaded[name] for name in loaded.files}
    occupations = arrays["occupations"].astype(str)
    months = arrays["months"].astype(str).tolist()
    families = arrays["families"].astype(str)
    require(len(occupations) == 468 and len(months) == 113,
            "canonical calibration dimensions differ")
    membership = pd.read_csv(args.membership, dtype={"occupation_code": str},
                             float_precision="round_trip")
    membership["occupation_code"] = membership.occupation_code.str.zfill(4)
    membership = membership.set_index("occupation_code").reindex(occupations)
    require(not membership.isna().any().any(), "membership does not align to calibration support")
    beta = membership.rule_A_beta.to_numpy(float)
    fixed_q = membership.beta_quintile.to_numpy(int)
    webb = membership.webb_pct_software.to_numpy(float)
    fixed_webb_z = membership.webb_z.to_numpy(float)
    names = membership.occupation_name.astype(str).to_numpy()
    require(np.array_equal(fixed_q, arrays["quintiles"]), "calibration quintiles differ")
    require(np.allclose(fixed_webb_z, arrays["webb_z"], rtol=0, atol=1e-12),
            "calibration Webb normalization differs")
    beta_map = dict(zip(occupations, beta))
    webb_map = dict(zip(occupations, webb))
    early, direct, counters = read_source_cells(args.microdata, args.repair_microdata, months)
    full_bridge, routes, split_targets = prepare_bridge(
        args.bridge, occupations.tolist(), beta_map, webb_map)
    official_allocation = allocation_table(routes, 1.0, 1.0)
    official_young, official_older, official_mass = expand_panel(
        early, direct, official_allocation, occupations.tolist(), months)
    calibrated_young = arrays["total"].reshape(468, 113) * 0
    # Recover the protected canonical age cells from the route representation.
    n_cell = 468 * 113
    stock_by_age = np.bincount(arrays["cellage"], weights=arrays["route_stock"],
                               minlength=2 * n_cell)
    calibrated_young = stock_by_age[:n_cell].reshape(468, 113)
    calibrated_older = stock_by_age[n_cell:].reshape(468, 113)
    cell_absolute_gap = float(max(np.max(np.abs(official_young - calibrated_young)),
                                  np.max(np.abs(official_older - calibrated_older))))
    cell_relative_gap = float(max(
        np.max(np.abs(official_young - calibrated_young) / np.maximum(calibrated_young, 1.0)),
        np.max(np.abs(official_older - calibrated_older) / np.maximum(calibrated_older, 1.0)),
    ))
    require(cell_relative_gap <= 1e-10, "official no-tilt cells differ from calibration")
    rebuilt_q, rebuilt_webb_z, rebuilt_detail = rebuilt_labels(
        beta, webb, official_young, official_older, months)
    require(np.array_equal(rebuilt_q, fixed_q), "official no-tilt quintiles differ")
    require(np.allclose(rebuilt_webb_z, fixed_webb_z, rtol=0, atol=1e-10),
            "official no-tilt Webb normalization differs")

    families_global = sorted(set(families.tolist()))
    draws = CORE.draw_multiplier_matrices(DRAWS, len(occupations), len(families_global), SEED)
    multipliers = {"occupation": draws["occupation_rademacher"],
                   "family": draws["family_rademacher"]}
    all_keep = np.ones(len(occupations), bool)
    models: dict[str, dict[str, Any]] = {}
    model_rows: list[dict[str, Any]] = []
    pair_rows: list[dict[str, Any]] = []
    member_rows: list[dict[str, Any]] = []
    mass_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    def add_model(model_id: str, structure: str, young: np.ndarray, older: np.ndarray,
                  keep: np.ndarray, quintiles: np.ndarray, webbz: np.ndarray,
                  metadata: dict[str, Any]) -> dict[str, Any]:
        try:
            model = fit_model(model_id, structure, young, older, keep, quintiles,
                              webbz, families, occupations, months, multipliers, metadata)
        except Exception as error:
            failures.append({"model_id": model_id, "error": repr(error)})
            raise
        models[model_id] = model
        model_rows.append(model["row"])
        return model

    # W02: symmetric bridge tilt with fixed and rebuilt treatment definitions.
    for k_value in SYMMETRIC_K:
        allocation = allocation_table(routes, math.sqrt(k_value), 1.0 / math.sqrt(k_value))
        young, older, mass = expand_panel(early, direct, allocation,
                                          occupations.tolist(), months)
        q_new, webb_new, detail = rebuilt_labels(beta, webb, young, older, months)
        for index, code in enumerate(occupations):
            member_rows.append({
                "scenario": "symmetric_odds_tilt", "K_relative_young_older": k_value,
                "occupation_code": code, "occupation_name": names[index],
                "fixed_beta_quintile": int(fixed_q[index]),
                "rebuilt_beta_quintile": int(q_new[index]),
                "rebuilt_webb_z": float(webb_new[index]),
                "preperiod_construction_weight": float(
                    (young[index, np.asarray([value <= "2022-11" for value in months])] +
                     older[index, np.asarray([value <= "2022-11" for value in months])]).sum()),
            })
        mass_rows.append({"scenario": "symmetric_odds_tilt", "young_K": math.sqrt(k_value),
                          "older_K": 1.0 / math.sqrt(k_value),
                          "relative_young_older_K": k_value, **mass})
        for label_mode, q_value, webb_value in (
            ("fixed_labels", fixed_q, fixed_webb_z),
            ("rebuilt_treatment", q_new, webb_new),
        ):
            for structure in ("pooled", "family_month"):
                model_id = f"symmetric_K_{k_value:.12g}_{label_mode}_{structure}"
                add_model(model_id, structure, young, older, all_keep, q_value, webb_value, {
                    "block": "W02_symmetric_odds_tilt", "label_mode": label_mode,
                    "young_high_low_odds": math.sqrt(k_value),
                    "older_high_low_odds": 1.0 / math.sqrt(k_value),
                    "relative_young_older_high_low_odds": k_value,
                    "beta_cut_1": detail["beta_cut_1"], "beta_cut_2": detail["beta_cut_2"],
                    "beta_cut_3": detail["beta_cut_3"], "beta_cut_4": detail["beta_cut_4"],
                    "occupations_changing_quintile": int(np.sum(q_new != fixed_q)),
                    "jointly_feasible_source_age_month_allocation": True,
                })
    for label_mode in ("fixed_labels", "rebuilt_treatment"):
        for structure in ("pooled", "family_month"):
            base_id = f"symmetric_K_1_{label_mode}_{structure}"
            for k_value in SYMMETRIC_K:
                if k_value == 1.0:
                    continue
                model_id = f"symmetric_K_{k_value:.12g}_{label_mode}_{structure}"
                pair_rows.append(paired_row(f"{model_id}_minus_{base_id}",
                                            models[model_id], models[base_id], multipliers))

    pooled_base = models["symmetric_K_1_fixed_labels_pooled"]
    family_base = models["symmetric_K_1_fixed_labels_family_month"]
    require(abs(pooled_base["row"]["coefficient_Q5_x_post"] - EXPECTED_POOLED) <= 1e-8,
            "no-tilt pooled coefficient differs")
    require(abs(family_base["row"]["coefficient_Q5_x_post"] - EXPECTED_FAMILY) <= 1e-8,
            "no-tilt family coefficient differs")
    require(abs(models["symmetric_K_1_rebuilt_treatment_pooled"]["row"]
                ["coefficient_Q5_x_post"] - EXPECTED_POOLED) <= 1e-8,
            "rebuilt no-tilt pooled coefficient differs")

    # W03: independently varied age-specific odds, fixed labels, pooled target.
    adverse_rows: list[dict[str, Any]] = []
    for young_k in ADVERSE_K:
        for older_k in ADVERSE_K:
            allocation = allocation_table(routes, young_k, older_k)
            young, older, mass = expand_panel(early, direct, allocation,
                                              occupations.tolist(), months)
            model_id = f"adverse_y{young_k:.12g}_o{older_k:.12g}_fixed_pooled"
            model = add_model(model_id, "pooled", young, older, all_keep,
                              fixed_q, fixed_webb_z, {
                                  "block": "W03_joint_adverse_grid", "label_mode": "fixed_labels",
                                  "young_high_low_odds": young_k,
                                  "older_high_low_odds": older_k,
                                  "relative_young_older_high_low_odds": young_k / older_k,
                                  "jointly_feasible_source_age_month_allocation": True,
                                  "grid_not_sharp_bound": True,
                              })
            adverse_rows.append({
                "young_high_low_odds": young_k, "older_high_low_odds": older_k,
                "relative_young_older_high_low_odds": young_k / older_k,
                "coefficient_Q5_x_post": model["row"]["coefficient_Q5_x_post"], **mass,
            })
    min_row = min(adverse_rows, key=lambda row: row["coefficient_Q5_x_post"])
    max_row = max(adverse_rows, key=lambda row: row["coefficient_Q5_x_post"])

    # W04: current clean-route support, holding labels fixed and rebuilding them.
    clean_keep = ~np.isin(occupations, sorted(split_targets))
    require(clean_keep.sum() > 4, "clean-route support is empty")
    clean_q_local, clean_webb_local, clean_detail = rebuilt_labels(
        beta[clean_keep], webb[clean_keep], official_young[clean_keep],
        official_older[clean_keep], months)
    clean_q = fixed_q.copy()
    clean_z = fixed_webb_z.copy()
    clean_q[clean_keep] = clean_q_local
    clean_z[clean_keep] = clean_webb_local
    for label_mode, q_value, z_value in (
        ("fixed_labels", fixed_q, fixed_webb_z),
        ("rebuilt_treatment", clean_q, clean_z),
    ):
        for structure in ("pooled", "family_month"):
            model_id = f"clean_route_{label_mode}_{structure}"
            add_model(model_id, structure, official_young, official_older, clean_keep,
                      q_value, z_value, {
                          "block": "W04_clean_route_support", "label_mode": label_mode,
                          "changed_population": True,
                          "occupations_changing_quintile": int(
                              np.sum(clean_q_local != fixed_q[clean_keep])),
                          "beta_cut_1": clean_detail["beta_cut_1"],
                          "beta_cut_2": clean_detail["beta_cut_2"],
                          "beta_cut_3": clean_detail["beta_cut_3"],
                          "beta_cut_4": clean_detail["beta_cut_4"],
                      })

    # W01: rule-based service exclusions and exact inherited deletion sets.
    q1 = fixed_q == 1
    exclusions = {
        "exclude_all_SOC35": families == "35",
        "exclude_Q1_SOC35": (families == "35") & q1,
        "exclude_all_SOC35_37_39": np.isin(families, ["35", "37", "39"]),
        "exclude_Q1_SOC35_37_39": np.isin(families, ["35", "37", "39"]) & q1,
        "exclude_inherited_fast_food_4055": occupations == "4055",
        "exclude_inherited_top5": np.isin(occupations, HISTORICAL_DELETION_ORDER[:5]),
        "exclude_inherited_top10": np.isin(occupations, HISTORICAL_DELETION_ORDER[:10]),
        "exclude_inherited_top20": np.isin(occupations, HISTORICAL_DELETION_ORDER[:20]),
    }
    service_rows: list[dict[str, Any]] = []
    total_preweight = float(membership.preperiod_weight.sum())
    for label, exclusion in exclusions.items():
        keep = ~exclusion
        model = add_model(label, "pooled", official_young, official_older, keep,
                          fixed_q, fixed_webb_z, {
                              "block": "W01_service_and_inherited_influence_deletions",
                              "label_mode": "fixed_labels", "changed_population": True,
                              "outcome_informed_historical_selection": label.startswith("exclude_inherited"),
                              "excluded_occupations": int(exclusion.sum()),
                              "excluded_preperiod_stock_share": float(
                                  membership.preperiod_weight.to_numpy(float)[exclusion].sum() /
                                  total_preweight),
                          })
        pair_rows.append(paired_row(f"{label}_minus_current_baseline", model,
                                    pooled_base, multipliers))
        service_rows.append({
            "model_id": label, "excluded_occupations": int(exclusion.sum()),
            "excluded_codes": "|".join(occupations[exclusion].tolist()),
            "excluded_names": "|".join(names[exclusion].tolist()),
            "classification_basis": ("Census-2018 SOC major groups; SOC33 is not included"
                                     if "SOC" in label else
                                     "fixed inherited historical influence ranking; not reselected"),
        })

    base_influence = pooled_base["occupation_influence"]
    influence_square = np.square(base_influence)
    influence_share = influence_square / influence_square.sum()
    effective = float(1.0 / np.sum(np.square(influence_share)))
    order = np.argsort(-influence_share, kind="mergesort")
    diagnostic_rows = []
    for rank, index in enumerate(order, start=1):
        diagnostic_rows.append({
            "occupation_code": occupations[index], "occupation_name": names[index],
            "beta_quintile": int(fixed_q[index]), "SOC2_family": families[index],
            "occupation_influence_Q5_x_post": float(base_influence[index]),
            "squared_influence_share": float(influence_share[index]),
            "squared_influence_rank": rank,
            "cumulative_squared_influence_share": float(influence_share[order[:rank]].sum()),
            "effective_contributing_occupation_count": effective,
            "interpretation": "local influence-function diagnostic; not exact leave-one-out refit",
        })

    eligible_sources = sorted(routes.loc[routes.eligible, "census_2010"].unique())
    supported_sources = set(routes.census_2010)
    source_stock = early.groupby("source_occ").stock.sum()
    source_supported_mass = routes.groupby("census_2010").supported_mass.first()
    supported_route_stock = (source_stock.reindex(source_supported_mass.index).fillna(0) *
                             source_supported_mass)
    eligible_stock = float(supported_route_stock.reindex(eligible_sources).fillna(0).sum())
    supported_stock = float(supported_route_stock.sum())
    eligibility_rows = []
    for source, group in routes.groupby("census_2010"):
        raw_source_stock = float(source_stock.get(source, 0.0))
        routed_source_stock = raw_source_stock * float(group.supported_mass.iloc[0])
        eligibility_rows.append({
            "source_occ": source, "supported_targets": int(group.census_2018.nunique()),
            "eligible_for_tilt": bool(group.eligible.all()),
            "supported_official_route_mass": float(group.bridge_weight.sum()),
            "early_raw_source_weighted_stock": raw_source_stock,
            "early_weighted_stock_routed_to_current_support": routed_source_stock,
            "share_of_supported_early_routed_stock": routed_source_stock / supported_stock,
            "target_codes": "|".join(group.census_2018.tolist()),
        })

    carry = carry_forward_rows(args.stable_taxonomy_results, args.timing_model_results)
    influence_output: list[dict[str, Any]] = []
    for model in models.values():
        influence_output.extend(influence_rows(model, occupations, families_global))

    args.output_dir.mkdir(parents=True)
    outputs: dict[str, list[dict[str, Any]]] = {
        "MODEL_RESULTS.csv": model_rows,
        "PAIRED_MOVEMENTS.csv": pair_rows,
        "MODEL_INFLUENCE.csv": influence_output,
        "SYMMETRIC_TILT_MEMBERSHIP.csv": member_rows,
        "MASS_CONSERVATION.csv": mass_rows,
        "ADVERSE_GRID.csv": adverse_rows,
        "ROUTE_ELIGIBILITY.csv": eligibility_rows,
        "SERVICE_AND_DELETION_MEMBERS.csv": service_rows,
        "BASELINE_INFLUENCE_DIAGNOSTICS.csv": diagnostic_rows,
        "CARRY_FORWARD_RESULTS.csv": carry,
    }
    for name, rows in outputs.items():
        write_csv(args.output_dir / name, rows)
    write_json(args.output_dir / "ADVERSE_ENVELOPE.json", {
        "status": "EXPLORED_FEASIBLE_GRID_NOT_A_SHARP_OR_GLOBAL_BOUND",
        "young_grid": list(ADVERSE_K), "older_grid": list(ADVERSE_K),
        "minimum": min_row, "maximum": max_row,
        "constraints": "official structural zeros and source-age-month supported route mass preserved",
        "all_age_target_margins_imposed": False,
        "outcome_directed_optimization_performed": False,
    })
    write_json(args.output_dir / "CODING_ERROR_DISPOSITION.json", {
        "requirement": "L02",
        "status": "NOT_EXECUTED_NO_VALIDATED_ERROR_MATRIX",
        "reason": ("No authenticated dual-coded CPS validation sample or external symmetric "
                   "misclassification matrix is available. Immediate occupation reversals mix "
                   "real mobility, proxy response, editing, and coding error."),
        "arbitrary_symmetric_error_rate_fabricated": False,
        "completed_related_analysis": "jointly feasible source-age-month bridge allocation sensitivities",
    })
    write_json(args.output_dir / "MODEL_FAILURES.json", failures)
    output_names = [*outputs, "ADVERSE_ENVELOPE.json", "CODING_ERROR_DISPOSITION.json",
                    "MODEL_FAILURES.json"]
    run_receipt = {
        "schema_version": "yax-gate3-mapping-sensitivity-v1",
        "status": "PASS_GATE3_MAPPING_SENSITIVITY" if not failures else "FAILED_MODELS_RETAINED",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                              text=True).strip(),
        "sge_job_id": os.environ.get("JOB_ID"),
        "input_hashes": {
            "wide_microdata": sha256_file(args.microdata),
            "march_repair": sha256_file(args.repair_microdata),
            "bridge": sha256_file(args.bridge), "membership": sha256_file(args.membership),
            "private_calibration": sha256_file(args.private_calibration),
            "calibration_receipt": sha256_file(args.calibration_receipt),
            "stable_taxonomy_results": sha256_file(args.stable_taxonomy_results),
            "timing_model_results": sha256_file(args.timing_model_results),
            "specification": sha256_file(HERE / "MAPPING_SENSITIVITY_SPEC.md"),
            "runner": sha256_file(Path(__file__)),
        },
        "canonical_identity": {
            "support_occupations": len(occupations), "support_hash_sha256": support_hash(occupations),
            "analysis_months": len(months), "cell_maximum_absolute_gap": cell_absolute_gap,
            "cell_maximum_relative_gap": cell_relative_gap,
            "pooled_coefficient": pooled_base["row"]["coefficient_Q5_x_post"],
            "family_month_coefficient": family_base["row"]["coefficient_Q5_x_post"],
            "official_rebuilt_labels_exact": True,
            "official_rebuilt_webb_maximum_absolute_gap": float(
                np.max(np.abs(rebuilt_webb_z - fixed_webb_z))),
        },
        "route_constraints": {
            "full_bridge_sources": int(full_bridge.census_2010.nunique()),
            "supported_bridge_sources": len(supported_sources),
            "eligible_split_sources": len(eligible_sources),
            "eligible_stock_share_of_supported_early_source_stock": float(
                eligible_stock / supported_stock),
            "source_age_month_mass_preserved": True,
            "structural_route_zeros_preserved": True,
            "all_age_target_margins_imposed": False,
        },
        "official_mass_check": official_mass,
        "raw_aggregate_counters": counters,
        "model_count": len(model_rows), "paired_comparisons": len(pair_rows),
        "model_failures": len(failures), "draws": DRAWS, "seed": SEED,
        "common_draws_across_all_models": True,
        "adverse_envelope_status": "EXPLORED_FEASIBLE_GRID_NOT_A_SHARP_OR_GLOBAL_BOUND",
        "raw_microdata_or_identifiers_written": False,
        "output_hashes": {name: sha256_file(args.output_dir / name) for name in output_names},
    }
    write_json(args.output_dir / "EXECUTION_RECEIPT.json", run_receipt)
    print(json.dumps({"status": run_receipt["status"], "models": len(model_rows),
                      "paired": len(pair_rows), "failures": len(failures)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
