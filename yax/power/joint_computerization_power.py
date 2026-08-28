#!/usr/bin/env python3
"""Outcome-sealed power simulation for YAX's joint AI/computerization model.

The two-age-group PPML in plan section 5 is estimated through its exact
grouped-binomial conditional likelihood. Synthetic post months are constructed
only from the sealed 66-month pre-period cells. Rademacher multipliers are drawn
at the occupation level. An independent null set supplies the wild-cluster
bootstrap critical value used for primary rejection decisions.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import pathlib
import sys

import numpy as np
import pandas as pd


ROOT = pathlib.Path(__file__).resolve().parents[2]
ENGINE_PATH = ROOT / "dax" / "memo" / "power_calcs" / "young_relative_employment_power.py"
SPEC = importlib.util.spec_from_file_location("young_relative_employment_power", ENGINE_PATH)
ENGINE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ENGINE
SPEC.loader.exec_module(ENGINE)

LOOKUP_ROLE = "raw_occ_main_2020_plus"
POST_START = "2023-01"
TRANSITION_EXCLUDED = "2022-12"
DEFAULT_EFFECTS = (0.0, -0.005, -0.015, -0.03, -0.05, -0.08, -0.12, -0.18)
DEFAULT_BETA_C = math.log(0.95)
TARGET_POWER = 0.80


def planned_post_months():
    """Frozen v5 static window; the engine's v1 helper still starts 2022-12."""
    return [month for month in ENGINE.planned_post_months()
            if month >= POST_START and month != TRANSITION_EXCLUDED]


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def weighted_scale(values, weights):
    mean = float(np.sum(values * weights) / np.sum(weights))
    variance = float(np.sum(weights * np.square(values - mean)) / np.sum(weights))
    if variance <= 0:
        raise ValueError("exposure has zero weighted variance")
    return mean, math.sqrt(variance)


def read_lookup(path, measure):
    with pathlib.Path(path).open(newline="", encoding="utf-8-sig") as handle:
        rows = [row for row in csv.DictReader(handle)
                if row["lookup_role"] == LOOKUP_ROLE and row.get(measure)]
    return {row["occ_code"].zfill(4): float(row[measure]) for row in rows}


def read_computerization(path, measure):
    with pathlib.Path(path).open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    result = {}
    for row in rows:
        if row.get(measure):
            result[row["census2018"].zfill(4)] = {
                "value": float(row[measure]),
                "occupation": row.get("occupation") or f"Census 2018 OCC {row['census2018']}",
                "soc_major_group": row.get("soc_major_group") or "unknown",
            }
    return result


def validate_receipts(cells, cells_receipt, lookup, lookup_receipt,
                      computerization, computerization_receipt):
    cr = json.loads(pathlib.Path(cells_receipt).read_text(encoding="utf-8"))
    if cr.get("post_outcomes_read") is not False:
        raise ValueError("cells receipt does not preserve the outcome seal")
    if cr.get("cells_sha256") != sha256(cells):
        raise ValueError("cells hash does not match receipt")
    lr = json.loads(pathlib.Path(lookup_receipt).read_text(encoding="utf-8"))
    if lr.get("status") != "PASS":
        raise ValueError("exposure lookup receipt is not PASS")
    outputs = lr.get("outputs", {})
    expected = next((v.get("sha256") for k, v in outputs.items()
                     if k.endswith("CPS_OCCUPATION_EXPOSURE_LOOKUP.csv")), None)
    if expected != sha256(lookup):
        raise ValueError("exposure lookup hash does not match receipt")
    mr = json.loads(pathlib.Path(computerization_receipt).read_text(encoding="utf-8"))
    target = mr.get("census2018_output", {})
    if mr.get("status") != "PASS" or target.get("sha256") != sha256(computerization):
        raise ValueError("computerization target file is not authenticated")
    return cr, lr, mr


def prepare(cells_path, lookup_path, computerization_path, ai_measure, comp_measure):
    cells = pd.read_csv(cells_path)
    required = {"month", "lookup_role", "occ_code", "age_group",
                "employment_headcount"}
    missing = required - set(cells.columns)
    if missing:
        raise ValueError(f"cells missing {sorted(missing)}")
    if str(cells["month"].max()) > "2022-11":
        raise ValueError("post-period outcomes prohibited")
    cells = cells.loc[cells["lookup_role"] == LOOKUP_ROLE].copy()
    cells["occ_code"] = cells["occ_code"].astype(str).str.zfill(4)
    pivot = cells.pivot_table(
        index=["occ_code", "month"], columns="age_group",
        values="employment_headcount", aggfunc="sum", fill_value=0.0,
    )
    months = sorted(cells["month"].astype(str).unique())
    occupations = sorted(cells["occ_code"].unique())
    index = pd.MultiIndex.from_product([occupations, months], names=["occ_code", "month"])
    pivot = pivot.reindex(index, fill_value=0.0)
    for age in ("young_22_25", "older_26_65"):
        if age not in pivot:
            pivot[age] = 0.0
    totals = pivot.groupby(level="occ_code")[["young_22_25", "older_26_65"]].sum()
    balanced = totals.index[(totals > 0).all(axis=1)].astype(str).tolist()
    if len(balanced) != 490:
        raise ValueError(f"expected 490 balanced primary clusters, got {len(balanced)}")

    ai = read_lookup(lookup_path, ai_measure)
    comp = read_computerization(computerization_path, comp_measure)
    support = [code for code in balanced if code in ai and code in comp]
    if len(support) < 30:
        raise ValueError("fewer than 30 joint-support occupations")
    selected = pivot.loc[(support, slice(None)), :]
    young = selected["young_22_25"].to_numpy().reshape(len(support), len(months))
    older = selected["older_26_65"].to_numpy().reshape(len(support), len(months))
    weights = (young + older).sum(axis=1)

    # AI scaling is pinned on all balanced target occupations carrying the AI
    # measure, so changing the computerization control does not redefine one SD.
    balanced_weights = totals.sum(axis=1).to_dict()
    ai_codes = [code for code in balanced if code in ai]
    ai_values_all = np.array([ai[code] for code in ai_codes], dtype=float)
    ai_weights_all = np.array([balanced_weights[code] for code in ai_codes], dtype=float)
    ai_mean, ai_sd = weighted_scale(ai_values_all, ai_weights_all)

    # Each computerization measure has its own published support. Its scaling is
    # fixed across alpha/beta runs on every balanced target code it covers.
    comp_codes = [code for code in balanced if code in comp]
    comp_values_all = np.array([comp[code]["value"] for code in comp_codes], dtype=float)
    comp_weights_all = np.array([balanced_weights[code] for code in comp_codes], dtype=float)
    comp_mean, comp_sd = weighted_scale(comp_values_all, comp_weights_all)
    ai_z = np.array([(ai[code] - ai_mean) / ai_sd for code in support])
    comp_z = np.array([(comp[code]["value"] - comp_mean) / comp_sd for code in support])
    return {
        "occupations": support,
        "occupation_names": [comp[code]["occupation"] for code in support],
        "soc_major_groups": [comp[code]["soc_major_group"] for code in support],
        "months": months,
        "young": young,
        "older": older,
        "weights": weights,
        "ai_z": ai_z,
        "comp_z": comp_z,
        "ai_scale": {"mean": ai_mean, "sd": ai_sd,
                     "reference_occupations": len(ai_codes)},
        "comp_scale": {"mean": comp_mean, "sd": comp_sd,
                       "reference_occupations": len(comp_codes)},
        "balanced_primary_clusters": len(balanced),
    }


def identifying_support(prepared):
    x, c, w = prepared["ai_z"], prepared["comp_z"], prepared["weights"]
    design = np.column_stack([np.ones(len(c)), c])
    coef = np.linalg.solve(design.T @ (w[:, None] * design), design.T @ (w * x))
    residual = x - design @ coef
    contribution = w * np.square(residual)
    total = float(contribution.sum())
    effective = float(total ** 2 / np.square(contribution).sum())
    order = np.argsort(-contribution)
    named = [{
        "census2018": prepared["occupations"][i],
        "occupation": prepared["occupation_names"][i],
        "soc_major_group": prepared["soc_major_groups"][i],
        "residual_variance_share": float(contribution[i] / total),
    } for i in order[:15]]
    return {
        "effective_occupations_identifying_beta_ai": effective,
        "top_five_influence_share": float(contribution[order[:5]].sum() / total),
        "largest_residual_variance_contributors": named,
        "weighted_partial_variance_ai_given_computerization": (
            float(total / np.sum(w * np.square(x - np.sum(w * x) / np.sum(w))))
        ),
    }


def build_dgp(prepared):
    young_pre = prepared["young"]
    total_pre = young_pre + prepared["older"]
    n_occ, n_pre = young_pre.shape
    fit = ENGINE.fit_grouped_logit_fe(
        young_pre.reshape(-1), total_pre.reshape(-1),
        np.repeat(np.arange(n_occ), n_pre), np.tile(np.arange(n_pre), n_occ),
        np.empty((n_occ * n_pre, 0)),
    )
    if not fit.converged:
        raise RuntimeError("pre-period fixed-effect fit did not converge")
    fitted = (fit.fitted_probability * total_pre.reshape(-1)).reshape(n_occ, n_pre)
    residual = fit.residual.reshape(n_occ, n_pre)
    months = prepared["months"] + planned_post_months()
    post = np.array([month >= POST_START for month in months], dtype=bool)
    regressors = np.column_stack([
        (prepared["ai_z"][:, None] * post[None, :]).reshape(-1),
        (prepared["comp_z"][:, None] * post[None, :]).reshape(-1),
    ])
    return {
        "total_pre": total_pre, "fitted_pre": fitted, "residual_pre": residual,
        "post": post, "regressors": regressors,
        "occupation": np.repeat(np.arange(n_occ), len(months)),
        "month": np.tile(np.arange(len(months)), n_occ),
        "target_month_count": len(months),
    }


def simulate(prepared, dgp, effect, beta_c, repetitions, seed):
    rng = np.random.default_rng(seed)
    n_occ, n_pre = dgp["total_pre"].shape
    estimates, standard_errors, t_stats = [], [], []
    failures = attempts = 0
    while len(estimates) < repetitions and attempts < repetitions * 2:
        attempts += 1
        offset = int(rng.integers(0, n_pre))
        donors = (np.arange(dgp["target_month_count"]) + offset) % n_pre
        total = dgp["total_pre"][:, donors]
        signs = rng.choice(np.array([-1.0, 1.0]), size=n_occ)
        young_null = dgp["fitted_pre"][:, donors] + signs[:, None] * dgp["residual_pre"][:, donors]
        probability = np.divide(young_null, total,
                                out=np.full_like(young_null, 0.5), where=total > 0)
        probability = np.clip(probability, 1e-9, 1 - 1e-9)
        shift = ((effect * prepared["ai_z"][:, None]
                  + beta_c * prepared["comp_z"][:, None])
                 * dgp["post"][None, :])
        injected = total * ENGINE._sigmoid(np.log(probability / (1 - probability)) + shift)
        fit = ENGINE.fit_grouped_logit_fe(
            injected.reshape(-1), total.reshape(-1), dgp["occupation"], dgp["month"],
            dgp["regressors"],
        )
        if (not fit.converged or not np.isfinite(fit.standard_error[0])
                or fit.standard_error[0] <= 0):
            failures += 1
            continue
        estimate, se = float(fit.beta[0]), float(fit.standard_error[0])
        estimates.append(estimate)
        standard_errors.append(se)
        t_stats.append(estimate / se)
    if len(estimates) < repetitions:
        raise RuntimeError(f"only {len(estimates)} successful fits for effect {effect}")
    return {"estimate": np.asarray(estimates), "se": np.asarray(standard_errors),
            "t": np.asarray(t_stats), "failures": failures, "attempts": attempts}


def interpolate_mde(results, field="rejection_probability_zero"):
    points = sorted((1 - math.exp(row["true_log_effect"]), row[field])
                    for row in results if row["true_log_effect"] < 0)
    for (d0, p0), (d1, p1) in zip(points, points[1:]):
        if p0 < TARGET_POWER <= p1:
            return d0 + (TARGET_POWER - p0) * (d1 - d0) / (p1 - p0)
    return None


def mde_interval(rejections, effects, draws, seed):
    rng = np.random.default_rng(seed)
    values = []
    n = len(next(iter(rejections.values())))
    for _ in range(draws):
        rows = []
        for effect in effects:
            index = rng.integers(0, n, size=n)
            rows.append({"true_log_effect": effect,
                         "rejection_probability_zero": float(rejections[effect][index].mean())})
        value = interpolate_mde(rows)
        if value is not None:
            values.append(value)
    if not values:
        return {"draws": draws, "successful_draws": 0, "lower": None, "upper": None}
    return {"draws": draws, "successful_draws": len(values),
            "lower": float(np.quantile(values, 0.025)),
            "upper": float(np.quantile(values, 0.975))}


def run(args):
    validate_receipts(args.cells, args.cells_receipt, args.lookup, args.lookup_receipt,
                      args.computerization, args.computerization_receipt)
    prepared = prepare(args.cells, args.lookup, args.computerization,
                       args.ai_measure, args.computerization_measure)
    dgp = build_dgp(prepared)
    scenario = f"{args.ai_measure}__{args.computerization_measure}__{args.beta_c:.9f}"
    scenario_offset = int(hashlib.sha256(scenario.encode()).hexdigest()[:8], 16)
    calibration_seed = args.seed + scenario_offset
    calibration = simulate(prepared, dgp, 0.0, args.beta_c,
                           args.bootstrap_draws, calibration_seed)
    critical = float(np.quantile(np.abs(calibration["t"]), 0.95, method="higher"))
    results, rejection_vectors = [], {}
    for index, effect in enumerate(args.effects):
        draw = simulate(prepared, dgp, effect, args.beta_c, args.repetitions,
                        args.seed + scenario_offset + 1000003 + index * 10007)
        rejected = np.abs(draw["t"]) > critical
        rejection_vectors[effect] = rejected
        lower = draw["estimate"] - critical * draw["se"]
        upper = draw["estimate"] + critical * draw["se"]
        results.append({
            "true_log_effect": effect,
            "successful_repetitions": args.repetitions,
            "convergence_failures": draw["failures"],
            "attempts": draw["attempts"],
            "rejection_probability_zero": float(rejected.mean()),
            "coverage_95": float(np.mean((lower <= effect) & (upper >= effect))),
            "mean_estimate": float(draw["estimate"].mean()),
            "mean_cluster_se": float(draw["se"].mean()),
            "bias": float(np.mean(draw["estimate"] - effect)),
            "rmse": float(np.sqrt(np.mean(np.square(draw["estimate"] - effect)))),
        })
    mde = interpolate_mde(results)
    interval = mde_interval(rejection_vectors, args.effects, args.mde_bootstrap_draws,
                            args.seed + scenario_offset + 9000001)
    null = next(row for row in results if abs(row["true_log_effect"]) < 1e-12)
    return {
        "record_version": "yax-joint-computerization-power-v2",
        "status": "PASS_SIMULATION_COMPLETE",
        "post_outcomes_read": False,
        "synthetic_post_constructed_only_from_preperiod_donors": True,
        "equation": "grouped-binomial conditional equivalent of plan section 5 PPML",
        "ai_measure": args.ai_measure,
        "computerization_measure": args.computerization_measure,
        "beta_c": args.beta_c,
        "beta_c_interpretation": "fixed log effect per one weighted-SD of computerization",
        "effect_scale": "log effect per one weighted-SD of AI exposure",
        "seed": args.seed,
        "repetitions_per_effect": args.repetitions,
        "occupation_clusters": len(prepared["occupations"]),
        "balanced_primary_clusters_before_measure_overlap": prepared["balanced_primary_clusters"],
        "preperiod_months": len(prepared["months"]),
        "planned_post_months": len(planned_post_months()),
        "design": {
            "post_start": POST_START,
            "transition_excluded": TRANSITION_EXCLUDED,
            "post_end": "2026-07",
            "post_gaps": sorted(ENGINE.POST_GAPS),
        },
        "ai_scale": prepared["ai_scale"],
        "computerization_scale": prepared["comp_scale"],
        "inputs": {
            "cells": {"path": str(args.cells), "sha256": sha256(args.cells)},
            "lookup": {"path": str(args.lookup), "sha256": sha256(args.lookup)},
            "computerization": {"path": str(args.computerization),
                                "sha256": sha256(args.computerization)},
        },
        "bootstrap": {
            "primary_inference": True,
            "distribution": "Rademacher",
            "cluster": "occupation",
            "calibration_draws": args.bootstrap_draws,
            "calibration_seed": calibration_seed,
            "critical_value_two_sided": critical,
            "independent_null_evaluation_size": null["rejection_probability_zero"],
            "mde_monte_carlo_interval": interval,
        },
        "empirical_mde80_relative_decline": mde,
        "identifying_support": identifying_support(prepared),
        "results": results,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells", type=pathlib.Path, required=True)
    parser.add_argument("--cells-receipt", type=pathlib.Path, required=True)
    parser.add_argument("--lookup", type=pathlib.Path, required=True)
    parser.add_argument("--lookup-receipt", type=pathlib.Path, required=True)
    parser.add_argument("--computerization", type=pathlib.Path, required=True)
    parser.add_argument("--computerization-receipt", type=pathlib.Path, required=True)
    parser.add_argument("--ai-measure", choices=("dv_rating_beta", "dv_rating_alpha"), required=True)
    parser.add_argument("--computerization-measure",
                        choices=("onet_computers_importance", "webb_pct_software"),
                        required=True)
    parser.add_argument("--beta-c", type=float, default=DEFAULT_BETA_C)
    parser.add_argument("--effects", type=lambda text: tuple(float(v) for v in text.split(",")),
                        default=DEFAULT_EFFECTS)
    parser.add_argument("--repetitions", type=int, default=999)
    parser.add_argument("--bootstrap-draws", type=int, default=999)
    parser.add_argument("--mde-bootstrap-draws", type=int, default=999)
    parser.add_argument("--seed", type=int, default=20260827)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args(argv)
    if args.repetitions < 999 or args.bootstrap_draws < 999:
        raise SystemExit("NEED_HUMAN: frozen simulation requires at least 999 repetitions/draws")
    if 0.0 not in args.effects or len([v for v in args.effects if v < 0]) < 2:
        raise SystemExit("NEED_HUMAN: effect grid must include zero and at least two declines")
    result = run(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"],
                      "scenario": [result["ai_measure"], result["computerization_measure"]],
                      "mde80": result["empirical_mde80_relative_decline"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
