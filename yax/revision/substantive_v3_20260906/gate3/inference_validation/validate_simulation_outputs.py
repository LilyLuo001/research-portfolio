#!/usr/bin/env python3
"""Independently recompute the public Gate 3 simulation summaries.

This validator consumes only public scenario artifacts, the public calibration
receipt, and the archived public adverse-design draws.  It does not import the
simulation producer and cannot access the protected calibration NPZ.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SCENARIOS = (
    "empirical_null", "empirical_local", "empirical_observed",
    "adverse_null", "adverse_local", "adverse_observed",
    "sparsity_equalized_null", "family_variance_zero_null",
    "serial_independent_null", "influence_equalized_null",
    "occupation_ar1_null",
)
TARGETS = ("pooled", "family_month", "family_month_minus_pooled")
PROCEDURES = (
    "occupation_rademacher", "occupation_webb",
    "family_rademacher", "family_webb", "crossfit_full_refit_oracle",
)
OUTPUTS = (
    "REPLICATE_RESULTS.csv", "SIMULATION_SUMMARY.csv", "MODEL_FAILURES.json",
    "DGP_AND_TRUTHS.json", "MONTE_CARLO_STOPPING.json",
)
ALLOWED_ATTEMPTS = (399, 799, 1199, 1599, 1999)
MCSE_TARGET = 0.0125
SD_RELATIVE_MC_ERROR_TARGET = 0.05


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def close(actual: Any, expected: Any, label: str, atol: float = 2e-13) -> None:
    a, e = float(actual), float(expected)
    require(math.isfinite(a) and math.isfinite(e), f"{label}: nonfinite value")
    require(math.isclose(a, e, rel_tol=2e-12, abs_tol=atol),
            f"{label}: {a!r} != {e!r}")


def empirical_sd_relative_mc_error(values: np.ndarray) -> float:
    centered = values - np.mean(values)
    mu2 = float(np.mean(centered ** 2))
    mu4 = float(np.mean(centered ** 4))
    require(mu2 > 0, "zero empirical variance")
    return math.sqrt(max(0.0, mu4 / mu2 ** 2 - 1.0) / (4.0 * len(values)))


def binomial_mcse(rate: float, n: int) -> float:
    return math.sqrt(rate * (1.0 - rate) / n)


def oracle_intervals(local: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    estimate = local.estimate.to_numpy(float)
    se = local.occupation_se.to_numpy(float)
    standardized = np.abs((estimate - local.pseudo_truth.to_numpy(float)) / se)
    odd = local.replicate.to_numpy(int) % 2 == 1
    require(odd.sum() >= 100 and (~odd).sum() >= 100, "oracle halves too small")
    odd_critical = float(np.quantile(standardized[odd], .95, method="higher"))
    even_critical = float(np.quantile(standardized[~odd], .95, method="higher"))
    critical = np.where(odd, even_critical, odd_critical)
    return estimate - critical * se, estimate + critical * se, critical


def expected_summary(frame: pd.DataFrame, attempts: int, failure_count: int
                     ) -> tuple[pd.DataFrame, dict[str, float | bool]]:
    records: list[dict[str, Any]] = []
    stopping_binomial: list[float] = []
    stopping_sd: list[float] = []
    for target in TARGETS:
        local = frame.loc[frame.target.eq(target)].sort_values("replicate")
        require(len(local) + failure_count == attempts,
                f"{target}: attempted-draw denominator mismatch")
        estimate = local.estimate.to_numpy(float)
        truth_values = local.pseudo_truth.to_numpy(float)
        require(np.ptp(truth_values) == 0, f"{target}: pseudo-truth changes by draw")
        truth = float(truth_values[0])
        empirical_sd = float(np.std(estimate, ddof=1))
        sd_mc_error = empirical_sd_relative_mc_error(estimate)
        mean_occ_se = float(local.occupation_se.mean())
        zero_tolerance = max(1e-10, 1e-6 * mean_occ_se)
        truth_is_zero = abs(truth) <= zero_tolerance
        stopping_sd.append(sd_mc_error)
        for procedure in PROCEDURES:
            if procedure == "crossfit_full_refit_oracle":
                lower, upper, critical = oracle_intervals(local)
                reported_se = local.occupation_se.to_numpy(float)
            else:
                lower = local[f"{procedure}_lower"].to_numpy(float)
                upper = local[f"{procedure}_upper"].to_numpy(float)
                critical = local[f"{procedure}_critical"].to_numpy(float)
                reported_se = (local.occupation_se.to_numpy(float)
                               if procedure.startswith("occupation_")
                               else local.family_se.to_numpy(float))
            coverage = (lower <= truth) & (truth <= upper)
            rejection = (lower > 0) | (upper < 0)
            coverage_rate = float(np.mean(coverage))
            rejection_rate = float(np.mean(rejection))
            coverage_mcse = binomial_mcse(coverage_rate, len(local))
            rejection_mcse = binomial_mcse(rejection_rate, len(local))
            stopping_binomial.append(coverage_mcse)
            if truth_is_zero:
                stopping_binomial.append(rejection_mcse)
            records.append({
                "scenario": str(local.scenario.iloc[0]), "target": target,
                "procedure": procedure, "pseudo_truth": truth,
                "attempted_replications": attempts,
                "successful_joint_refits": len(local),
                "failed_joint_refits": failure_count,
                "failure_rate": failure_count / attempts,
                "mean_estimate": float(np.mean(estimate)),
                "bias": float(np.mean(estimate) - truth),
                "empirical_sd": empirical_sd,
                "mean_reported_se": float(np.mean(reported_se)),
                "mean_interval_length": float(np.mean(upper - lower)),
                "coverage": coverage_rate, "coverage_mcse": coverage_mcse,
                "zero_rejection": rejection_rate,
                "zero_rejection_is_size": truth_is_zero,
                "numerical_zero_tolerance": zero_tolerance,
                "zero_rejection_mcse": rejection_mcse,
                "mean_or_crossfit_critical": float(np.mean(critical)),
                "empirical_sd_relative_mc_error": sd_mc_error,
                "mean_pooled_separated_fraction": float(
                    local.pooled_separated_fraction.mean()),
                "maximum_pooled_separated_fraction": float(
                    local.pooled_separated_fraction.max()),
                "mean_family_month_separated_fraction": float(
                    local.family_month_separated_fraction.mean()),
                "maximum_family_month_separated_fraction": float(
                    local.family_month_separated_fraction.max()),
            })
    maximum_binomial = max(stopping_binomial)
    maximum_sd = max(stopping_sd)
    stopping = {
        "maximum_relevant_binomial_mcse": maximum_binomial,
        "maximum_empirical_sd_relative_mc_error": maximum_sd,
        "passes": maximum_binomial <= MCSE_TARGET and maximum_sd <= SD_RELATIVE_MC_ERROR_TARGET,
    }
    return pd.DataFrame(records), stopping


def validate_scenario(directory: Path, calibration_receipt: Path,
                      historical_draws: Path, expected_head: str) -> dict[str, Any]:
    scenario = directory.name
    require(scenario in SCENARIOS, f"unexpected scenario directory {scenario}")
    for name in (*OUTPUTS, "EXECUTION_RECEIPT.json"):
        require((directory / name).is_file(), f"{scenario}: missing {name}")
    receipt = load_json(directory / "EXECUTION_RECEIPT.json")
    stopping = load_json(directory / "MONTE_CARLO_STOPPING.json")
    failures = load_json(directory / "MODEL_FAILURES.json")
    dgp = load_json(directory / "DGP_AND_TRUTHS.json")
    require(receipt["scenario"] == scenario == dgp["scenario"],
            f"{scenario}: scenario identity mismatch")
    require(receipt["git_head"] == expected_head, f"{scenario}: git-head mismatch")
    require(receipt["calibration_receipt_sha256"] == sha256_file(calibration_receipt),
            f"{scenario}: calibration-receipt hash mismatch")
    calibration = load_json(calibration_receipt)
    require(receipt["private_calibration_sha256"] == calibration["private_npz_sha256"],
            f"{scenario}: protected calibration identity mismatch")
    require(receipt["historical_draws_sha256"] == sha256_file(historical_draws),
            f"{scenario}: historical-draw hash mismatch")
    for name in OUTPUTS:
        require(receipt["output_hashes"][name] == sha256_file(directory / name),
                f"{scenario}: {name} hash mismatch")
    attempts = int(receipt["attempted_replications"])
    require(attempts in ALLOWED_ATTEMPTS, f"{scenario}: undeclared replication count")
    require(len(failures) == int(receipt["failed_joint_refits"]),
            f"{scenario}: failure inventory mismatch")
    frame = pd.read_csv(directory / "REPLICATE_RESULTS.csv", keep_default_na=False)
    require(len(frame) == 3 * int(receipt["successful_joint_refits"]),
            f"{scenario}: replicate-row count mismatch")
    require(set(frame.scenario) == {scenario}, f"{scenario}: row scenario mismatch")
    grouped = frame.groupby("replicate").target.agg(list)
    require(all(set(values) == set(TARGETS) and len(values) == 3 for values in grouped),
            f"{scenario}: incomplete target triplet")
    require(len(grouped) + len(failures) == attempts,
            f"{scenario}: successful-plus-failed denominator mismatch")
    for replicate, local in frame.groupby("replicate"):
        values = local.set_index("target")
        close(values.loc["family_month_minus_pooled", "estimate"],
              values.loc["family_month", "estimate"] - values.loc["pooled", "estimate"],
              f"{scenario}/draw {replicate}: paired estimate", 3e-15)
    close((frame.estimate - frame.pseudo_truth - frame.bias).abs().max(), 0.0,
          f"{scenario}: stored bias identity", 3e-15)
    for procedure in PROCEDURES[:-1]:
        recomputed_cover = ((frame[f"{procedure}_lower"] <= frame.pseudo_truth) &
                            (frame.pseudo_truth <= frame[f"{procedure}_upper"]))
        recomputed_reject = ((frame[f"{procedure}_lower"] > 0) |
                             (frame[f"{procedure}_upper"] < 0))
        require(np.array_equal(recomputed_cover.to_numpy(bool),
                               frame[f"{procedure}_covers_truth"].to_numpy(bool)),
                f"{scenario}/{procedure}: stored coverage flags differ")
        require(np.array_equal(recomputed_reject.to_numpy(bool),
                               frame[f"{procedure}_rejects_zero"].to_numpy(bool)),
                f"{scenario}/{procedure}: stored rejection flags differ")
    expected, expected_stopping = expected_summary(frame, attempts, len(failures))
    observed = pd.read_csv(directory / "SIMULATION_SUMMARY.csv", keep_default_na=False)
    keys = ["scenario", "target", "procedure"]
    merged = observed.merge(expected, on=keys, suffixes=("_observed", "_expected"),
                            validate="one_to_one")
    require(len(merged) == len(expected) == 15, f"{scenario}: summary inventory mismatch")
    for column in expected.columns:
        if column in keys:
            continue
        a, e = merged[f"{column}_observed"], merged[f"{column}_expected"]
        if pd.api.types.is_bool_dtype(e):
            require(np.array_equal(a.to_numpy(bool), e.to_numpy(bool)),
                    f"{scenario}/{column}: boolean summary mismatch")
        else:
            require(np.allclose(a.to_numpy(float), e.to_numpy(float),
                                rtol=2e-12, atol=2e-13),
                    f"{scenario}/{column}: numeric summary mismatch")
    for name, expected_value in expected_stopping.items():
        if isinstance(expected_value, bool):
            require(bool(stopping[name]) == expected_value,
                    f"{scenario}: stopping {name} mismatch")
        else:
            close(stopping[name], expected_value, f"{scenario}: stopping {name}")
    require(stopping["completed_replications"] == attempts,
            f"{scenario}: stopping count mismatch")
    require(stopping["inner_multiplier_draws"] == 9999,
            f"{scenario}: inner-draw count mismatch")
    require(stopping["pilot"] == 399 and stopping["block"] == 400 and stopping["cap"] == 1999,
            f"{scenario}: expansion contract mismatch")
    require(stopping["passes"] or attempts == 1999,
            f"{scenario}: stopped before passing or cap")
    expected_status = ("PASS_SIMULATION_SCENARIO_RESOLVED" if stopping["passes"]
                       else "PASS_SIMULATION_SCENARIO_CAP_REACHED_UNRESOLVED")
    require(receipt["status"] == expected_status,
            f"{scenario}: receipt status mismatch")
    for target in TARGETS:
        truth = float(frame.loc[frame.target.eq(target), "pseudo_truth"].iloc[0])
        close(dgp["pseudo_truths"][target], truth, f"{scenario}/{target}: DGP truth")
    if scenario.startswith("adverse_"):
        history = dgp["historical_adverse_reproduction"]
        require(history["applicable"] and history["passes_tolerance"],
                f"{scenario}: historical reproduction failed")
        old = pd.read_csv(historical_draws, keep_default_na=False)
        label = ("observed_checkpoint" if scenario == "adverse_observed" else
                 "local_minus_0.05" if scenario == "adverse_local" else "null")
        old = old.loc[old.effect_label.eq(label) & old.model.eq("baseline")]
        new = frame.loc[frame.target.eq("pooled") & frame.replicate.le(199),
                        ["replicate", "estimate"]]
        comparison = old[["replicate", "coefficient"]].merge(new, on="replicate")
        require(len(comparison) == len(old) >= 190,
                f"{scenario}: historical inventory mismatch")
        gap = float(np.max(np.abs(comparison.coefficient - comparison.estimate)))
        close(history["maximum_pooled_coefficient_difference"], gap,
              f"{scenario}: historical maximum gap", 3e-15)
    else:
        require(not dgp["historical_adverse_reproduction"]["applicable"],
                f"{scenario}: inapplicable history marked applicable")
    return {
        "scenario": scenario, "status": receipt["status"], "attempts": attempts,
        "failures": len(failures),
        "maximum_binomial_mcse": expected_stopping["maximum_relevant_binomial_mcse"],
        "maximum_sd_relative_mc_error": expected_stopping[
            "maximum_empirical_sd_relative_mc_error"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--calibration-receipt", type=Path, required=True)
    parser.add_argument("--historical-draws", type=Path, required=True)
    parser.add_argument("--expected-git-head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(args.run_root.is_dir(), "run root is absent")
    observed_dirs = {path.name for path in args.run_root.iterdir()
                     if path.is_dir() and path.name != "logs"}
    require(observed_dirs == set(SCENARIOS),
            f"scenario directory inventory differs: {sorted(observed_dirs)}")
    results = [validate_scenario(args.run_root / scenario, args.calibration_receipt,
                                 args.historical_draws, args.expected_git_head)
               for scenario in SCENARIOS]
    report = {
        "schema_version": "yax-gate3-simulation-independent-validation-v1",
        "status": "PASS_INDEPENDENT_PUBLIC_SIMULATION_VALIDATION",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "expected_git_head": args.expected_git_head,
        "calibration_receipt_sha256": sha256_file(args.calibration_receipt),
        "historical_draws_sha256": sha256_file(args.historical_draws),
        "scenario_count": len(results), "scenarios": results,
        "privacy": "validated public aggregate simulation artifacts only; protected NPZ not read",
    }
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps({"status": report["status"], "scenarios": len(results)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
