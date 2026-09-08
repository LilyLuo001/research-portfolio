#!/usr/bin/env python3
"""Run one declared Gate 3 finite-sample validation scenario.

Each invocation is an independently schedulable scenario.  It consumes the
protected calibration NPZ, publishes replicate-level coefficients and
inference summaries only, and never publishes a cell, household code, or
private path.
"""
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
PILOT = 399
BLOCK = 400
CAP = 1999
INNER_DRAWS = 9999
MCSE_TARGET = 0.0125
SD_RELATIVE_MC_ERROR_TARGET = 0.05
OUTER_SEED = 202609081000
INNER_SEED = 202609082000
HISTORICAL_SEED = 2026090561
ALPHA = 0.05


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CORE = load_module("yax_gate3_simulation_core", HERE / "inference_engine.py")
MATH = load_module("yax_gate3_simulation_math", HERE / "math_utils.py")
ENGINE = load_module(
    "yax_gate3_simulation_engine",
    ROOT / "dax/memo/power_calcs/young_relative_employment_power.py",
)


SCENARIOS: dict[str, dict[str, Any]] = {
    "empirical_null": {"design": "empirical_gaussian_ar1", "theta": 0.0},
    "empirical_local": {"design": "empirical_gaussian_ar1", "theta": -0.05},
    "empirical_observed": {
        "design": "empirical_gaussian_ar1", "theta": "observed_family_month"},
    "adverse_null": {"design": "prior_adverse_rademacher", "theta": 0.0},
    "adverse_local": {"design": "prior_adverse_rademacher", "theta": -0.05},
    "adverse_observed": {
        "design": "prior_adverse_rademacher", "theta": "observed_pooled"},
    "sparsity_equalized_null": {"design": "sparsity_equalized", "theta": 0.0},
    "family_variance_zero_null": {"design": "family_variance_zero", "theta": 0.0},
    "serial_independent_null": {"design": "serial_independent", "theta": 0.0},
    "influence_equalized_null": {"design": "influence_equalized", "theta": 0.0},
    "occupation_ar1_null": {"design": "occupation_gaussian_ar1", "theta": 0.0},
}
TARGETS = ("pooled", "family_month", "family_month_minus_pooled")
PROCEDURES = (
    "occupation_rademacher", "occupation_webb",
    "family_rademacher", "family_webb",
    "crossfit_full_refit_oracle",
)


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
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8")


def load_calibration(npz_path: Path, receipt_path: Path) -> tuple[dict[str, np.ndarray], dict]:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(receipt.get("status") == "PASS_PRIVATE_CALIBRATION_BUILD",
            "private calibration receipt does not pass")
    require(receipt.get("private_npz_sha256") == sha256_file(npz_path),
            "private calibration NPZ hash differs")
    with np.load(npz_path, allow_pickle=False) as loaded:
        arrays = {name: loaded[name] for name in loaded.files}
    required = {
        "months", "occupations", "families", "quintiles", "webb_z",
        "total", "effective_count", "effective_integer", "pooled_nuisance_eta",
        "family_nuisance_eta", "family_shock_path", "family_information",
    }
    require(required.issubset(arrays), "private calibration inventory differs")
    require(len(arrays["occupations"]) == 468 and len(arrays["months"]) == 113,
            "private calibration support differs")
    return arrays, receipt


def resolved_theta(scenario: dict[str, Any], receipt: dict) -> float:
    value = scenario["theta"]
    if value == "observed_family_month":
        return float(receipt["observed_models"]["family_month"]["coefficient"])
    if value == "observed_pooled":
        return float(receipt["observed_models"]["pooled"]["coefficient"])
    return float(value)


def influence_equalized_total(total: np.ndarray, probability: np.ndarray,
                              families: np.ndarray, month_count: int) -> tuple[np.ndarray, dict]:
    total = np.asarray(total, float)
    probability = np.asarray(probability, float)
    family_levels = {value: index for index, value in enumerate(sorted(set(families.tolist())))}
    family_code = np.asarray([family_levels[value] for value in families], int)
    information = (total * probability * (1 - probability)).reshape(len(families), month_count)
    occupation_information = information.sum(axis=1)
    factors = np.ones(len(families))
    for family in range(len(family_levels)):
        member = family_code == family
        require(np.all(occupation_information[member] > 0),
                "cannot equalize a zero-information occupation")
        target = float(np.mean(occupation_information[member]))
        factors[member] = target / occupation_information[member]
    rescaled = total.reshape(len(families), month_count) * factors[:, None]
    before = np.bincount(family_code, weights=occupation_information,
                         minlength=len(family_levels))
    after_information = (rescaled * probability.reshape(len(families), month_count) *
                         (1 - probability.reshape(len(families), month_count))).sum(axis=1)
    after = np.bincount(family_code, weights=after_information,
                        minlength=len(family_levels))
    require(np.allclose(before, after, rtol=1e-12, atol=1e-8),
            "influence equalization changes family information total")
    within_ranges = []
    for family in range(len(family_levels)):
        member = family_code == family
        within_ranges.append(float(np.ptp(after_information[member])))
    require(max(within_ranges) <= max(1e-8, 1e-12 * float(after_information.max())),
            "occupation information was not equalized within family")
    return rescaled.reshape(-1), {
        "minimum_rescaling_factor": float(factors.min()),
        "maximum_rescaling_factor": float(factors.max()),
        "maximum_within_family_information_range": max(within_ranges),
        "maximum_family_information_total_gap": float(np.max(np.abs(before - after))),
    }


def stationary_variance_diagnostic(months: list[str], rho: float,
                                   stationary_sd: float) -> dict[str, float]:
    """Empirically challenge the stationary initialization and gap transitions."""
    rng = np.random.default_rng(202609082111)
    draws = np.asarray([
        CORE.draw_stationary_ar1(rng, 1, months, rho, stationary_sd)[0]
        for _ in range(5000)
    ])
    variance = np.var(draws, axis=0, ddof=1)
    target = stationary_sd ** 2
    if target == 0:
        maximum_relative = 0.0
    else:
        maximum_relative = float(np.max(np.abs(variance - target) / target))
    require(maximum_relative <= .08, "realized AR(1) marginal variance is not flat")
    return {
        "theoretical_marginal_variance": target,
        "minimum_realized_month_variance": float(variance.min()),
        "maximum_realized_month_variance": float(variance.max()),
        "maximum_relative_month_variance_difference": maximum_relative,
        "diagnostic_paths": len(draws),
    }


def variance_preserving_equalized_count(total: np.ndarray, probability: np.ndarray,
                                        effective_integer: np.ndarray) -> tuple[float, int]:
    """Match aggregate binomial-stock variance to the rounded baseline counts."""
    total = np.asarray(total, float)
    probability = np.asarray(probability, float)
    effective_integer = np.asarray(effective_integer, int)
    positive = effective_integer > 0
    require(np.array_equal(positive, total > 0),
            "equalized-count support differs")
    variance_weight = np.square(total[positive]) * probability[positive] * (
        1.0 - probability[positive])
    baseline_count = effective_integer[positive].astype(float)
    common_float = float(np.sum(variance_weight) /
                         np.sum(variance_weight / baseline_count))
    return common_float, max(1, int(np.rint(common_float)))


def scenario_objects(arrays: dict[str, np.ndarray], receipt: dict,
                     scenario_name: str) -> dict[str, Any]:
    definition = SCENARIOS[scenario_name]
    design_name = definition["design"]
    theta = resolved_theta(definition, receipt)
    total = np.asarray(arrays["total"], float).copy()
    effective = np.asarray(arrays["effective_integer"], int).copy()
    family_path = np.asarray(arrays["family_shock_path"], float)
    family_sd = float(receipt["family_shock_calibration"]["stationary_sd"])
    rho = float(receipt["family_shock_calibration"]["rho"])
    target = CORE.build_design(
        arrays["quintiles"], arrays["webb_z"], arrays["families"],
        arrays["months"].tolist(), "pooled",
    ).regressors[:, CORE.TARGET_INDEX]
    base = (np.asarray(arrays["pooled_nuisance_eta"], float)
            if design_name == "prior_adverse_rademacher"
            else np.asarray(arrays["family_nuisance_eta"], float))
    eta = base + theta * target
    if design_name == "prior_adverse_rademacher":
        shock = family_path[
            CORE.build_design(arrays["quintiles"], arrays["webb_z"], arrays["families"],
                              arrays["months"].tolist(), "pooled").family_codes,
            np.arange(len(total)) % len(arrays["months"]),
        ]
        mean_probability = MATH.rademacher_logit_mean(eta, shock)
        shock_law = "complete-path SOC2 Rademacher sign times archived residual path"
    elif design_name == "family_variance_zero":
        mean_probability = MATH.expit(eta)
        shock_law = "family shock variance fixed to zero"
    else:
        mean_probability = MATH.gaussian_logit_mean(eta, family_sd, order=41)
        check = MATH.gaussian_logit_mean(eta, family_sd, order=82)
        require(float(np.max(np.abs(mean_probability - check))) <= 1e-10,
                "Gaussian quadrature is not stable")
        if design_name == "serial_independent":
            shock_law = "independent Gaussian SOC2-family month shocks at fixed marginal variance"
        elif design_name == "occupation_gaussian_ar1":
            shock_law = "independent stationary Gaussian occupation-by-month AR(1) paths"
        else:
            shock_law = "stationary Gaussian SOC2-family AR(1)"
    count_rule = "rounded observed cell Kish effective count"
    diagnostics: dict[str, Any] = {}
    if design_name == "sparsity_equalized":
        positive = effective > 0
        common_float, common = variance_preserving_equalized_count(
            total, mean_probability, effective)
        effective[positive] = common
        count_rule = ("all positive cells fixed to variance-preserving weighted harmonic "
                      f"effective count {common_float:.12g}, rounded once to {common}")
        diagnostics.update({"variance_preserving_common_count_unrounded": common_float,
                            "variance_preserving_common_count_rounded": common})
    if design_name == "influence_equalized":
        total, diagnostics = influence_equalized_total(
            total, mean_probability, arrays["families"], len(arrays["months"]))
    if design_name not in {"prior_adverse_rademacher", "family_variance_zero"}:
        diagnostics["stationary_variance_diagnostic"] = stationary_variance_diagnostic(
            arrays["months"].tolist(),
            0.0 if design_name == "serial_independent" else rho,
            family_sd,
        )
    return {
        "scenario": scenario_name, "design": design_name, "theta": theta,
        "total": total, "effective_integer": effective, "eta": eta,
        "mean_probability": mean_probability, "rho": (0.0 if design_name == "serial_independent" else rho),
        "stationary_sd": (0.0 if design_name == "family_variance_zero" else family_sd),
        "family_path": family_path, "shock_law": shock_law,
        "count_rule": count_rule, "diagnostics": diagnostics,
    }


def pseudo_truth(objects: dict[str, Any], designs: dict[str, CORE.ModelDesign]) -> tuple[dict, dict]:
    expected_young = objects["total"] * objects["mean_probability"]
    fits = {
        name: CORE.fit_with_influence(ENGINE, expected_young, objects["total"], design)
        for name, design in designs.items()
    }
    pair = CORE.paired_target(fits["family_month"], fits["pooled"])
    truth = {
        "pooled": fits["pooled"].estimate,
        "family_month": fits["family_month"].estimate,
        "family_month_minus_pooled": pair["estimate"],
    }
    diagnostics = {
        name: {"iterations": fit.iterations,
               "maximum_normalized_score": fit.maximum_normalized_score}
        for name, fit in fits.items()
    }
    require(abs(truth["family_month_minus_pooled"] -
                (truth["family_month"] - truth["pooled"])) <= 1e-12,
            "pseudo-truth pairing identity failed")
    return truth, diagnostics


def draw_probability(objects: dict[str, Any], arrays: dict[str, np.ndarray],
                     replicate: int) -> np.ndarray:
    family_count = len(set(arrays["families"].tolist()))
    months = arrays["months"].tolist()
    design = CORE.build_design(
        arrays["quintiles"], arrays["webb_z"], arrays["families"], months, "pooled"
    )
    family_code = design.family_codes
    month_code = np.arange(len(objects["eta"])) % len(months)
    if objects["design"] == "prior_adverse_rademacher":
        rng = np.random.default_rng(HISTORICAL_SEED + replicate)
        signs = rng.choice(np.asarray([-1.0, 1.0]), size=family_count)
        shock = signs[:, None] * objects["family_path"]
    else:
        rng = np.random.default_rng(OUTER_SEED + replicate)
        unit_count = (len(arrays["occupations"])
                      if objects["design"] == "occupation_gaussian_ar1"
                      else family_count)
        shock = CORE.draw_stationary_ar1(
            rng, unit_count, months, objects["rho"], objects["stationary_sd"])
    shock_code = (design.occupation_codes
                  if objects["design"] == "occupation_gaussian_ar1"
                  else family_code)
    probability = MATH.expit(objects["eta"] + shock[shock_code, month_code])
    return probability


def one_replicate(objects: dict[str, Any], arrays: dict[str, np.ndarray],
                  designs: dict[str, CORE.ModelDesign], truth: dict[str, float],
                  multipliers: dict[str, np.ndarray], replicate: int) -> list[dict[str, Any]]:
    probability = draw_probability(objects, arrays, replicate)
    count_seed = ((HISTORICAL_SEED + replicate) if objects["design"] == "prior_adverse_rademacher"
                  else (OUTER_SEED + 10_000_000 + replicate))
    rng = np.random.default_rng(count_seed)
    # Historical adverse draws consume their family signs before binomial sampling.
    if objects["design"] == "prior_adverse_rademacher":
        rng.choice(np.asarray([-1.0, 1.0]), size=len(set(arrays["families"].tolist())))
    young, older = CORE.binomial_stock_draw(
        rng, objects["total"], objects["effective_integer"], probability)
    fits = {
        name: CORE.fit_with_influence(ENGINE, young, young + older, design)
        for name, design in designs.items()
    }
    pair = CORE.paired_target(fits["family_month"], fits["pooled"])
    target_objects = {
        "pooled": {
            "estimate": fits["pooled"].estimate,
            "occupation": fits["pooled"].occupation_influence[:, CORE.TARGET_INDEX],
            "family": fits["pooled"].family_influence[:, CORE.TARGET_INDEX],
            "iterations": fits["pooled"].iterations,
        },
        "family_month": {
            "estimate": fits["family_month"].estimate,
            "occupation": fits["family_month"].occupation_influence[:, CORE.TARGET_INDEX],
            "family": fits["family_month"].family_influence[:, CORE.TARGET_INDEX],
            "iterations": fits["family_month"].iterations,
        },
        "family_month_minus_pooled": {
            "estimate": pair["estimate"], "occupation": pair["occupation_influence"],
            "family": pair["family_influence"],
            "iterations": max(fits["pooled"].iterations, fits["family_month"].iterations),
        },
    }
    rows: list[dict[str, Any]] = []
    for target_name, target_object in target_objects.items():
        estimate = float(target_object["estimate"])
        occ_interval = CORE.multiplier_interval(
            estimate, target_object["occupation"], multipliers["occupation_rademacher"])
        occupation_webb = CORE.multiplier_interval(
            estimate, target_object["occupation"], multipliers["occupation_webb"])
        family_rademacher = CORE.multiplier_interval(
            estimate, target_object["family"], multipliers["family_rademacher"])
        family_webb = CORE.multiplier_interval(
            estimate, target_object["family"], multipliers["family_webb"])
        row: dict[str, Any] = {
            "scenario": objects["scenario"], "replicate": replicate,
            "target": target_name, "pseudo_truth": truth[target_name],
            "estimate": estimate, "bias": estimate - truth[target_name],
            "occupation_se": occ_interval["se"], "family_se": family_rademacher["se"],
            "iterations": target_object["iterations"],
            "pooled_separated_observations": fits["pooled"].separated_observation_count,
            "family_month_separated_observations": fits["family_month"].separated_observation_count,
            "pooled_separated_fraction": fits["pooled"].separated_observation_count / len(young),
            "family_month_separated_fraction": fits["family_month"].separated_observation_count / len(young),
        }
        for name, interval in (
            ("occupation_rademacher", occ_interval),
            ("occupation_webb", occupation_webb),
            ("family_rademacher", family_rademacher),
            ("family_webb", family_webb),
        ):
            row.update({
                f"{name}_critical": interval["critical"],
                f"{name}_lower": interval["lower"],
                f"{name}_upper": interval["upper"],
                f"{name}_covers_truth": interval["lower"] <= truth[target_name] <= interval["upper"],
                f"{name}_rejects_zero": not (interval["lower"] <= 0 <= interval["upper"]),
            })
        rows.append(row)
    return rows


def crossfit_oracle(local: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    standardized = np.abs((local.estimate.to_numpy(float) - local.pseudo_truth.to_numpy(float)) /
                          local.occupation_se.to_numpy(float))
    replicate = local.replicate.to_numpy(int)
    odd = replicate % 2 == 1
    require(odd.sum() >= 100 and (~odd).sum() >= 100, "oracle calibration halves too small")
    critical_odd = float(np.quantile(standardized[odd], .95, method="higher"))
    critical_even = float(np.quantile(standardized[~odd], .95, method="higher"))
    evaluation_critical = np.where(odd, critical_even, critical_odd)
    half = evaluation_critical * local.occupation_se.to_numpy(float)
    return (local.estimate.to_numpy(float) - half,
            local.estimate.to_numpy(float) + half,
            {"odd_calibration_critical": critical_odd,
             "even_calibration_critical": critical_even})


def empirical_sd_relative_mc_error(values: np.ndarray) -> float:
    """Delta-method MC error for an SD using the observed fourth moment."""
    values = np.asarray(values, float)
    require(len(values) > 3 and np.all(np.isfinite(values)), "invalid SD MC sample")
    centered = values - np.mean(values)
    mu2 = float(np.mean(np.square(centered)))
    require(mu2 > 0, "zero empirical simulation variance")
    mu4 = float(np.mean(centered ** 4))
    return float(math.sqrt(max(0.0, mu4 / (mu2 * mu2) - 1.0) / (4.0 * len(values))))


def reported_standard_error(local: pd.DataFrame, procedure: str) -> np.ndarray:
    """Return the studentizer associated with the procedure's cluster level."""
    if procedure == "crossfit_full_refit_oracle" or procedure.startswith("occupation_"):
        return local.occupation_se.to_numpy(float)
    require(procedure.startswith("family_"), "unknown inference procedure")
    return local.family_se.to_numpy(float)


def summarize(rows: list[dict[str, Any]], attempts: int, failures: int) -> tuple[list[dict], dict]:
    frame = pd.DataFrame(rows)
    summaries: list[dict[str, Any]] = []
    stopping_mcse: list[float] = []
    stopping_sd_rmc: list[float] = []
    for target in TARGETS:
        local = frame.loc[frame.target.eq(target)].sort_values("replicate")
        require(len(local) + failures == attempts, "attempt denominator differs")
        estimate = local.estimate.to_numpy(float)
        truth = float(local.pseudo_truth.iloc[0])
        empirical_sd = float(np.std(estimate, ddof=1))
        relative_sd_mc_error = empirical_sd_relative_mc_error(estimate)
        mean_occupation_se = float(local.occupation_se.mean())
        zero_tolerance = max(1e-10, 1e-6 * mean_occupation_se)
        truth_is_numerical_zero = abs(truth) <= zero_tolerance
        stopping_sd_rmc.append(relative_sd_mc_error)
        oracle_lower, oracle_upper, oracle_critical = crossfit_oracle(local)
        for procedure in PROCEDURES:
            if procedure == "crossfit_full_refit_oracle":
                lower, upper = oracle_lower, oracle_upper
                reported_se = reported_standard_error(local, procedure)
                critical_mean = float(np.mean(
                    np.where(local.replicate.to_numpy(int) % 2 == 1,
                             oracle_critical["even_calibration_critical"],
                             oracle_critical["odd_calibration_critical"])))
            else:
                lower = local[f"{procedure}_lower"].to_numpy(float)
                upper = local[f"{procedure}_upper"].to_numpy(float)
                reported_se = reported_standard_error(local, procedure)
                critical_mean = float(local[f"{procedure}_critical"].mean())
            coverage = (lower <= truth) & (truth <= upper)
            rejection = (lower > 0) | (upper < 0)
            coverage_rate = float(np.mean(coverage))
            rejection_rate = float(np.mean(rejection))
            coverage_mcse = MATH.binomial_monte_carlo_se(coverage_rate, len(coverage))
            rejection_mcse = MATH.binomial_monte_carlo_se(rejection_rate, len(rejection))
            stopping_mcse.append(coverage_mcse)
            if truth_is_numerical_zero:
                stopping_mcse.append(rejection_mcse)
            summaries.append({
                "scenario": str(local.scenario.iloc[0]), "target": target,
                "procedure": procedure, "structural_theta": None,
                "pseudo_truth": truth, "attempted_replications": attempts,
                "successful_joint_refits": len(local), "failed_joint_refits": failures,
                "failure_rate": failures / attempts,
                "mean_estimate": float(np.mean(estimate)),
                "bias": float(np.mean(estimate) - truth), "empirical_sd": empirical_sd,
                "mean_reported_se": float(np.mean(reported_se)),
                "mean_interval_length": float(np.mean(upper - lower)),
                "coverage": coverage_rate, "coverage_mcse": coverage_mcse,
                "zero_rejection": rejection_rate,
                "zero_rejection_is_size": truth_is_numerical_zero,
                "numerical_zero_tolerance": zero_tolerance,
                "zero_rejection_mcse": rejection_mcse,
                "mean_or_crossfit_critical": critical_mean,
                "empirical_sd_relative_mc_error": relative_sd_mc_error,
                "mean_pooled_separated_fraction": float(local.pooled_separated_fraction.mean()),
                "maximum_pooled_separated_fraction": float(local.pooled_separated_fraction.max()),
                "mean_family_month_separated_fraction": float(
                    local.family_month_separated_fraction.mean()),
                "maximum_family_month_separated_fraction": float(
                    local.family_month_separated_fraction.max()),
            })
    stopping = {
        "maximum_relevant_binomial_mcse": max(stopping_mcse),
        "maximum_empirical_sd_relative_mc_error": max(stopping_sd_rmc),
        "mcse_target": MCSE_TARGET,
        "sd_relative_mc_error_target": SD_RELATIVE_MC_ERROR_TARGET,
        "passes": (max(stopping_mcse) <= MCSE_TARGET and
                   max(stopping_sd_rmc) <= SD_RELATIVE_MC_ERROR_TARGET),
    }
    return summaries, stopping


def historical_reproduction(rows: list[dict[str, Any]], historical_path: Path,
                            scenario_name: str) -> dict[str, Any]:
    if not scenario_name.startswith("adverse_"):
        return {"applicable": False}
    old = pd.read_csv(historical_path, keep_default_na=False)
    theta = SCENARIOS[scenario_name]["theta"]
    if theta == "observed_pooled":
        effect_label = "observed_checkpoint"
    elif math.isclose(float(theta), -0.05):
        effect_label = "local_minus_0.05"
    else:
        effect_label = "null"
    old = old.loc[old.effect_label.eq(effect_label) & old.model.eq("baseline")].copy()
    new = pd.DataFrame(rows)
    new = new.loc[new.target.eq("pooled") & new.replicate.le(199),
                  ["replicate", "estimate"]]
    merged = old[["replicate", "coefficient"]].merge(new, on="replicate", how="inner")
    require(len(old) >= 190 and len(merged) == len(old),
            "historical adverse successful-draw inventory differs")
    gap = float(np.max(np.abs(merged.coefficient - merged.estimate)))
    return {"applicable": True, "compared_draws": len(merged),
            "maximum_pooled_coefficient_difference": gap,
            "tolerance": 1e-8,
            "passes_tolerance": gap <= 1e-8,
            "interpretation": ("historical pooled coefficients reproduced"
                               if gap <= 1e-8 else
                               "historical pooled coefficient gap retained; not exact reproduction")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), required=True)
    parser.add_argument("--private-calibration", type=Path, required=True)
    parser.add_argument("--calibration-receipt", type=Path, required=True)
    parser.add_argument("--historical-draws", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--fixed-replications", type=int)
    args = parser.parse_args()
    require(not args.output_dir.exists(), "refusing to overwrite scenario output")
    arrays, receipt = load_calibration(args.private_calibration, args.calibration_receipt)
    objects = scenario_objects(arrays, receipt, args.scenario)
    designs = {
        name: CORE.build_design(arrays["quintiles"], arrays["webb_z"], arrays["families"],
                                arrays["months"].tolist(), name)
        for name in ("pooled", "family_month")
    }
    truth, truth_diagnostics = pseudo_truth(objects, designs)
    multipliers = CORE.draw_multiplier_matrices(
        INNER_DRAWS, len(arrays["occupations"]), len(set(arrays["families"].tolist())),
        INNER_SEED,
    )
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    attempts = 0
    target_reps = args.fixed_replications or PILOT
    require(PILOT <= target_reps <= CAP, "fixed replication count is outside declared range")
    while True:
        for replicate in range(attempts + 1, target_reps + 1):
            if replicate == 1 or replicate % 50 == 0:
                print(json.dumps({"stage": "simulation", "scenario": args.scenario,
                                  "replicate": replicate, "target": target_reps}), flush=True)
            try:
                rows.extend(one_replicate(
                    objects, arrays, designs, truth, multipliers, replicate))
            except Exception as error:
                failures.append({"scenario": args.scenario, "replicate": replicate,
                                 "stage": "joint_full_refit", "error": repr(error)})
                if len(failures) <= 3:
                    print(json.dumps({"stage": "joint_full_refit_failure",
                                      "scenario": args.scenario,
                                      "replicate": replicate,
                                      "error": repr(error)}), flush=True)
        attempts = target_reps
        require(bool(rows), f"all joint refits failed; first failure: {failures[0]['error']}")
        summaries, stopping = summarize(rows, attempts, len(failures))
        if args.fixed_replications is not None or stopping["passes"] or attempts == CAP:
            break
        target_reps = min(CAP, attempts + BLOCK)

    for row in summaries:
        row["structural_theta"] = objects["theta"]
    history = historical_reproduction(rows, args.historical_draws, args.scenario)
    args.output_dir.mkdir(parents=True)
    write_csv(args.output_dir / "REPLICATE_RESULTS.csv", rows)
    write_csv(args.output_dir / "SIMULATION_SUMMARY.csv", summaries)
    write_json(args.output_dir / "MODEL_FAILURES.json", failures)
    dgp = {
        "scenario": args.scenario, "design": objects["design"],
        "structural_theta": objects["theta"], "pseudo_truths": truth,
        "pseudo_truth_fit_diagnostics": truth_diagnostics,
        "shock_law": objects["shock_law"], "count_rule": objects["count_rule"],
        "rho": objects["rho"], "stationary_sd": objects["stationary_sd"],
        "diagnostics": objects["diagnostics"],
        "zero_size_classification_rule": "abs(pseudo_truth) <= max(1e-10, 1e-6 * mean occupation SE); evaluated in SIMULATION_SUMMARY.csv",
        "historical_adverse_reproduction": history,
    }
    write_json(args.output_dir / "DGP_AND_TRUTHS.json", dgp)
    write_json(args.output_dir / "MONTE_CARLO_STOPPING.json", {
        **stopping, "pilot": PILOT, "block": BLOCK, "cap": CAP,
        "completed_replications": attempts, "inner_multiplier_draws": INNER_DRAWS,
        "all_attempted_draws_retained_in_denominator": True,
        "numerically_resolved": stopping["passes"],
    })
    outputs = ["REPLICATE_RESULTS.csv", "SIMULATION_SUMMARY.csv",
               "MODEL_FAILURES.json", "DGP_AND_TRUTHS.json", "MONTE_CARLO_STOPPING.json"]
    receipt_out = {
        "schema_version": "yax-gate3-simulation-scenario-receipt-v1",
        "status": ("PASS_SIMULATION_SCENARIO_RESOLVED" if stopping["passes"]
                   else "PASS_SIMULATION_SCENARIO_CAP_REACHED_UNRESOLVED"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                              cwd=ROOT, text=True).strip(),
        "sge_job_id": os.environ.get("JOB_ID"), "scenario": args.scenario,
        "private_calibration_sha256": receipt["private_npz_sha256"],
        "calibration_receipt_sha256": sha256_file(args.calibration_receipt),
        "historical_draws_sha256": sha256_file(args.historical_draws),
        "attempted_replications": attempts, "successful_joint_refits": attempts - len(failures),
        "failed_joint_refits": len(failures), "stopping": stopping,
        "output_hashes": {name: sha256_file(args.output_dir / name) for name in outputs},
        "privacy": "outputs contain coefficients and aggregate diagnostics only; no cell, route, household code, microdata row, or private path",
    }
    write_json(args.output_dir / "EXECUTION_RECEIPT.json", receipt_out)
    print(json.dumps({"status": receipt_out["status"], "scenario": args.scenario,
                      "attempts": attempts, "failures": len(failures)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
