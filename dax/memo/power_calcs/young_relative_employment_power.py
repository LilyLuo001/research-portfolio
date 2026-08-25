"""Outcome-sealed power gate for the CPS young-relative-employment design.

With two age groups, the registered occupation-age/month PPML conditions on
each occupation-month total and is exactly a grouped-binomial logit with
occupation and month fixed effects.  This implementation uses that conditional
likelihood, alternating Newton fixed-effect updates, and weighted absorption
for the four exposure interactions.  It needs only NumPy and remains blocked
for real data until an authenticated C1 lookup receipt is supplied.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
from dataclasses import dataclass

import numpy as np


PRE_END = "2022-11"
POST_START = (2022, 12)
POST_END = (2026, 7)
POST_GAPS = {"2025-10"}
PRIMARY_BENCHMARK = math.log(0.81)
CURRENT_ROLE = "raw_occ_main_2020_plus"
LOOKUP_OUTPUT_KEY = "dax/w2/exposure_gate/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv"
DEFAULT_EFFECTS = sorted(set(
    [0.0, math.log(0.87), math.log(0.84), PRIMARY_BENCHMARK]
    + [-value for value in np.arange(0.05, 0.326, 0.025)]
), reverse=True)


class RealPowerBlocked(RuntimeError):
    pass


@dataclass
class FitResult:
    beta: np.ndarray
    standard_error: np.ndarray
    fitted_probability: np.ndarray
    residual: np.ndarray
    converged: bool
    iterations: int


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def planned_post_months() -> list[str]:
    result = []
    for year in range(POST_START[0], POST_END[0] + 1):
        for month in range(1, 13):
            if (year, month) < POST_START or (year, month) > POST_END:
                continue
            value = f"{year:04d}-{month:02d}"
            if value not in POST_GAPS:
                result.append(value)
    return result


def validate_preperiod_cells(frame) -> None:
    required = {
        "month", "lookup_role", "occ_code", "occupation_key",
        "dv_rating_beta", "exposure_quintile", "age_group",
        "employment_headcount", "unweighted_n", "weight_sq_sum",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"cell input missing columns {sorted(missing)}")
    if len(frame) == 0:
        raise ValueError("cell input is empty")
    if frame["month"].astype(str).max() > PRE_END:
        raise ValueError("post-period outcomes prohibited in power input")
    if not set(frame["age_group"]).issubset({"young_22_25", "older_26_65"}):
        raise ValueError("unknown age_group")
    values = np.asarray(frame["employment_headcount"], dtype=float)
    if np.any(~np.isfinite(values)) or np.any(values < 0):
        raise ValueError("employment_headcount must be finite and nonnegative")


def authenticate_c1(receipt_path: pathlib.Path, lookup_path: pathlib.Path) -> dict[str, object]:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("status") != "PASS":
        raise RealPowerBlocked("real power blocked until C1 receipt status is PASS")
    expected_hash = receipt.get("lookup_sha256")
    if expected_hash is None:
        expected_hash = (
            receipt.get("outputs", {}).get(LOOKUP_OUTPUT_KEY, {}).get("sha256")
        )
    if not expected_hash or expected_hash != sha256_file(lookup_path):
        raise RealPowerBlocked("C1 lookup hash absent or does not authenticate lookup")
    measure = receipt.get("primary_exposure", receipt.get("primary_measure"))
    if measure is None:
        measure = receipt.get("design", {}).get("primary_exposure")
    if measure != "dv_rating_beta":
        raise RealPowerBlocked("C1 receipt does not freeze dv_rating_beta as primary")
    return receipt


def authenticate_cells(
    receipt_path: pathlib.Path,
    cells_path: pathlib.Path,
    lookup_path: pathlib.Path | None = None,
) -> dict[str, object]:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("status") != "PASS_PREPERIOD_CELLS":
        raise RealPowerBlocked("cell receipt is not PASS_PREPERIOD_CELLS")
    if receipt.get("post_outcomes_read") is not False:
        raise RealPowerBlocked("cell receipt does not preserve outcome seal")
    source_seal = receipt.get("source_seal", {})
    if source_seal.get("audited_split_status") != "PASS_OUTCOME_BLIND_PREPERIOD_SPLIT":
        raise RealPowerBlocked("cells do not descend from audited pre-period split")
    if receipt.get("cells_sha256") != sha256_file(cells_path):
        raise RealPowerBlocked("cell file hash does not match receipt")
    if lookup_path is not None and receipt.get("lookup_sha256") != sha256_file(lookup_path):
        raise RealPowerBlocked("cell receipt was not built from authenticated lookup")
    return receipt


def _sigmoid(value: np.ndarray) -> np.ndarray:
    clipped = np.clip(value, -700.0, 700.0)
    return 1.0 / (1.0 + np.exp(-clipped))


def _weighted_absorb(
    matrix: np.ndarray,
    weight: np.ndarray,
    occupation: np.ndarray,
    month: np.ndarray,
    occupation_count: int,
    month_count: int,
    tolerance: float = 1e-11,
    max_iterations: int = 500,
) -> np.ndarray:
    if matrix.shape[1] == 0:
        return matrix.copy()
    result = np.asarray(matrix, dtype=float).copy()
    occ_weight = np.bincount(occupation, weights=weight, minlength=occupation_count)
    month_weight = np.bincount(month, weights=weight, minlength=month_count)
    for _ in range(max_iterations):
        largest = 0.0
        for group, denominator, count in (
            (occupation, occ_weight, occupation_count),
            (month, month_weight, month_count),
        ):
            for column in range(result.shape[1]):
                numerator = np.bincount(
                    group, weights=weight * result[:, column], minlength=count
                )
                adjustment = np.divide(
                    numerator, denominator,
                    out=np.zeros_like(numerator), where=denominator > 0,
                )
                result[:, column] -= adjustment[group]
                largest = max(largest, float(np.max(np.abs(adjustment))))
        if largest < tolerance:
            return result
    raise RuntimeError("weighted fixed-effect absorption did not converge")


def fit_grouped_logit_fe(
    young: np.ndarray,
    total: np.ndarray,
    occupation: np.ndarray,
    month: np.ndarray,
    regressors: np.ndarray,
    tolerance: float = 1e-8,
    max_iterations: int = 300,
) -> FitResult:
    young = np.asarray(young, dtype=float)
    total = np.asarray(total, dtype=float)
    occupation = np.asarray(occupation, dtype=int)
    month = np.asarray(month, dtype=int)
    regressors = np.asarray(regressors, dtype=float)
    keep = total > 0
    young, total = young[keep], total[keep]
    occupation, month = occupation[keep], month[keep]
    regressors = regressors[keep]
    if len(total) == 0 or np.any(young < 0) or np.any(young > total):
        raise ValueError("invalid grouped-binomial outcomes")
    occupation_count = int(occupation.max()) + 1
    month_count = int(month.max()) + 1
    parameter_count = regressors.shape[1]
    if len(np.unique(occupation)) != occupation_count or len(np.unique(month)) != month_count:
        raise ValueError("fixed-effect indexes must be contiguous")

    overall = float(np.clip(young.sum() / total.sum(), 1e-6, 1 - 1e-6))
    occ_y = np.bincount(occupation, weights=young, minlength=occupation_count)
    occ_n = np.bincount(occupation, weights=total, minlength=occupation_count)
    occ_share = np.clip((occ_y + 0.5) / (occ_n + 1.0), 1e-6, 1 - 1e-6)
    occ_effect = np.log(occ_share / (1 - occ_share))
    occ_effect -= math.log(overall / (1 - overall))
    month_effect = np.full(month_count, math.log(overall / (1 - overall)))
    beta = np.zeros(parameter_count)
    converged = False

    for iteration in range(1, max_iterations + 1):
        largest_step = 0.0
        for _ in range(2):
            eta = occ_effect[occupation] + month_effect[month] + regressors @ beta
            probability = np.clip(_sigmoid(eta), 1e-10, 1 - 1e-10)
            residual = young - total * probability
            weight = np.maximum(total * probability * (1 - probability), 1e-12)
            score = np.bincount(occupation, weights=residual, minlength=occupation_count)
            information = np.bincount(occupation, weights=weight, minlength=occupation_count)
            step = np.clip(score / information, -1.0, 1.0)
            occ_effect += step
            largest_step = max(largest_step, float(np.max(np.abs(step))))

            eta = occ_effect[occupation] + month_effect[month] + regressors @ beta
            probability = np.clip(_sigmoid(eta), 1e-10, 1 - 1e-10)
            residual = young - total * probability
            weight = np.maximum(total * probability * (1 - probability), 1e-12)
            score = np.bincount(month, weights=residual, minlength=month_count)
            information = np.bincount(month, weights=weight, minlength=month_count)
            step = np.clip(score / information, -1.0, 1.0)
            month_effect += step
            largest_step = max(largest_step, float(np.max(np.abs(step))))
            anchor = month_effect[0]
            month_effect -= anchor
            occ_effect += anchor

        eta = occ_effect[occupation] + month_effect[month] + regressors @ beta
        probability = np.clip(_sigmoid(eta), 1e-10, 1 - 1e-10)
        residual = young - total * probability
        weight = np.maximum(total * probability * (1 - probability), 1e-12)
        if parameter_count:
            residualized = _weighted_absorb(
                regressors, weight, occupation, month,
                occupation_count, month_count,
            )
            information = residualized.T @ (weight[:, None] * residualized)
            score = residualized.T @ residual
            try:
                step = np.linalg.solve(information, score)
            except np.linalg.LinAlgError as error:
                raise RuntimeError("treatment information matrix is singular") from error
            step = np.clip(step, -1.0, 1.0)
            beta += step
            largest_step = max(largest_step, float(np.max(np.abs(step))))

        scale = max(1.0, float(total.sum()))
        fe_score = max(
            float(np.max(np.abs(np.bincount(occupation, weights=residual, minlength=occupation_count)))),
            float(np.max(np.abs(np.bincount(month, weights=residual, minlength=month_count)))),
        ) / scale
        beta_score = (
            float(np.max(np.abs(residualized.T @ residual))) / scale
            if parameter_count else 0.0
        )
        if largest_step < tolerance and max(fe_score, beta_score) < tolerance:
            converged = True
            break

    eta = occ_effect[occupation] + month_effect[month] + regressors @ beta
    probability = np.clip(_sigmoid(eta), 1e-10, 1 - 1e-10)
    residual = young - total * probability
    if parameter_count:
        weight = np.maximum(total * probability * (1 - probability), 1e-12)
        residualized = _weighted_absorb(
            regressors, weight, occupation, month, occupation_count, month_count
        )
        information = residualized.T @ (weight[:, None] * residualized)
        bread = np.linalg.inv(information)
        observation_scores = residualized * residual[:, None]
        cluster_scores = np.zeros((occupation_count, parameter_count))
        np.add.at(cluster_scores, occupation, observation_scores)
        meat = cluster_scores.T @ cluster_scores
        correction = occupation_count / (occupation_count - 1) if occupation_count > 1 else np.nan
        variance = correction * bread @ meat @ bread
        standard_error = np.sqrt(np.maximum(np.diag(variance), 0.0))
    else:
        standard_error = np.empty(0)
    return FitResult(
        beta=beta,
        standard_error=standard_error,
        fitted_probability=probability,
        residual=residual,
        converged=converged,
        iterations=iteration,
    )


def _prepare_balanced_preperiod(cells):
    import pandas as pd

    validate_preperiod_cells(cells)
    cells = cells.loc[cells["lookup_role"] == CURRENT_ROLE].copy()
    if cells.empty:
        raise ValueError("no Census-2018 target-occupation cells available")
    attributes = cells[[
        "occupation_key", "lookup_role", "occ_code", "dv_rating_beta",
        "exposure_quintile",
    ]].drop_duplicates()
    if attributes["occupation_key"].duplicated().any():
        raise ValueError("occupation route has inconsistent exposure attributes")
    attributes["exposure_quintile"] = attributes["exposure_quintile"].astype(int)
    if not set(attributes["exposure_quintile"]).issubset({1, 2, 3, 4, 5}):
        raise ValueError("exposure quintiles must be in 1..5")

    pivot = cells.pivot_table(
        index=["occupation_key", "month"], columns="age_group",
        values="employment_headcount", aggfunc="sum", fill_value=0.0,
    )
    months = sorted(cells["month"].astype(str).unique())
    occupations = sorted(attributes["occupation_key"].astype(str).tolist())
    index = pd.MultiIndex.from_product(
        [occupations, months], names=["occupation_key", "month"]
    )
    pivot = pivot.reindex(index, fill_value=0.0)
    for name in ("young_22_25", "older_26_65"):
        if name not in pivot:
            pivot[name] = 0.0
    totals = pivot.groupby(level="occupation_key")[["young_22_25", "older_26_65"]].sum()
    support = totals.index[(totals > 0).all(axis=1)].astype(str).tolist()
    if not support:
        raise ValueError("no occupations have both young and older pre-period support")
    pivot = pivot.loc[(support, slice(None)), :]
    qmap = attributes.set_index("occupation_key")["exposure_quintile"].to_dict()
    q = np.array([qmap[value] for value in support], dtype=int)
    if set(q) != {1, 2, 3, 4, 5}:
        raise ValueError("all five exposure quintiles must survive support restrictions")
    young = pivot["young_22_25"].to_numpy().reshape(len(support), len(months))
    older = pivot["older_26_65"].to_numpy().reshape(len(support), len(months))
    return {
        "occupations": np.array(support), "months": months, "quintile": q,
        "young": young, "older": older,
    }


def _design(quintile: np.ndarray, post: np.ndarray) -> np.ndarray:
    return np.column_stack([
        ((quintile[:, None] == value) & post[None, :]).reshape(-1)
        for value in (2, 3, 4, 5)
    ]).astype(float)


def run_power_simulation(
    cells,
    effects: list[float],
    repetitions: int,
    seed: int,
) -> dict[str, object]:
    prepared = _prepare_balanced_preperiod(cells)
    young_pre = prepared["young"]
    total_pre = young_pre + prepared["older"]
    occupation_count, pre_month_count = young_pre.shape
    occ_pre = np.repeat(np.arange(occupation_count), pre_month_count)
    month_pre = np.tile(np.arange(pre_month_count), occupation_count)
    null_fit = fit_grouped_logit_fe(
        young_pre.reshape(-1), total_pre.reshape(-1), occ_pre, month_pre,
        np.empty((occupation_count * pre_month_count, 0)),
    )
    if not null_fit.converged:
        raise RuntimeError("pre-period null fixed-effect fit did not converge")
    fitted_pre = (null_fit.fitted_probability * total_pre.reshape(-1)).reshape(
        occupation_count, pre_month_count
    )
    residual_pre = null_fit.residual.reshape(occupation_count, pre_month_count)

    target_months = prepared["months"] + planned_post_months()
    target_month_count = len(target_months)
    post = np.array([month >= "2022-12" for month in target_months], dtype=bool)
    regressors = _design(prepared["quintile"], post)
    occupation = np.repeat(np.arange(occupation_count), target_month_count)
    month = np.tile(np.arange(target_month_count), occupation_count)
    rng = np.random.default_rng(seed)
    normal_cutoff = 1.959963984540054
    results = []

    for effect in effects:
        estimates, standard_errors = [], []
        convergence_failures = 0
        attempts = 0
        while len(estimates) < repetitions and attempts < repetitions * 2:
            attempts += 1
            offset = int(rng.integers(0, pre_month_count))
            donors = (np.arange(target_month_count) + offset) % pre_month_count
            total = total_pre[:, donors]
            signs = rng.choice(np.array([-1.0, 1.0]), size=occupation_count)
            young_null = fitted_pre[:, donors] + signs[:, None] * residual_pre[:, donors]
            probability = np.divide(
                young_null, total, out=np.full_like(young_null, 0.5), where=total > 0
            )
            probability = np.clip(probability, 1e-9, 1 - 1e-9)
            treatment = (
                (prepared["quintile"][:, None] == 5) & post[None, :]
            )
            log_odds = np.log(probability / (1 - probability)) + effect * treatment
            simulated_probability = _sigmoid(log_odds)
            simulated_young = total * simulated_probability
            fit = fit_grouped_logit_fe(
                simulated_young.reshape(-1), total.reshape(-1),
                occupation, month, regressors,
            )
            if not fit.converged or not np.isfinite(fit.standard_error[3]) or fit.standard_error[3] <= 0:
                convergence_failures += 1
                continue
            estimates.append(float(fit.beta[3]))
            standard_errors.append(float(fit.standard_error[3]))
        estimate = np.asarray(estimates)
        se = np.asarray(standard_errors)
        if len(estimate) == 0:
            raise RuntimeError(f"every simulation fit failed for effect {effect}")
        lower, upper = estimate - normal_cutoff * se, estimate + normal_cutoff * se
        results.append({
            "true_log_effect": round(float(effect), 9),
            "successful_repetitions": int(len(estimate)),
            "convergence_failures": int(convergence_failures),
            "attempts": int(attempts),
            "rejection_probability_zero": float(np.mean((lower > 0) | (upper < 0))),
            "benchmark_exclusion_probability": float(np.mean(
                (lower > PRIMARY_BENCHMARK) | (upper < PRIMARY_BENCHMARK)
            )),
            "bias": float(np.mean(estimate - effect)),
            "rmse": float(np.sqrt(np.mean((estimate - effect) ** 2))),
            "coverage_95": float(np.mean((lower <= effect) & (upper >= effect))),
            "mean_estimate": float(np.mean(estimate)),
            "mean_cluster_se": float(np.mean(se)),
        })

    candidates = sorted(
        (abs(row["true_log_effect"]), row["true_log_effect"])
        for row in results
        if row["true_log_effect"] < 0 and row["rejection_probability_zero"] >= 0.8
    )
    employment_by_occ = total_pre.sum(axis=1)
    contrast_weight = employment_by_occ[np.isin(prepared["quintile"], [1, 5])]
    effective_occ = float(contrast_weight.sum() ** 2 / np.square(contrast_weight).sum())
    primary = min(results, key=lambda row: abs(row["true_log_effect"] - PRIMARY_BENCHMARK))
    null = min(results, key=lambda row: abs(row["true_log_effect"]))
    gate_pass = (
        abs(primary["true_log_effect"] - PRIMARY_BENCHMARK) < 1e-8
        and primary["rejection_probability_zero"] >= 0.8
        and null["benchmark_exclusion_probability"] >= 0.8
    )
    mde_effect = candidates[0][1] if candidates else None
    return {
        "status": "PASS_POWER_GATE" if gate_pass else "FAIL_POWER_GATE",
        "estimator": "grouped_binomial_conditional_equivalent_of_registered_two_age_group_PPML",
        "post_outcomes_read": False,
        "synthetic_post_constructed_only_from_preperiod_donors": True,
        "repetitions_per_effect": repetitions,
        "seed": seed,
        "occupation_clusters": occupation_count,
        "preperiod_months": pre_month_count,
        "planned_post_months": len(planned_post_months()),
        "effective_occupation_concentration_q1_q5": effective_occ,
        "primary_benchmark_rejection_probability": primary["rejection_probability_zero"],
        "null_excludes_primary_benchmark_probability": null["benchmark_exclusion_probability"],
        "empirical_mde80_log_effect": mde_effect,
        "empirical_mde80_relative_decline": (
            1.0 - math.exp(mde_effect) if mde_effect is not None else None
        ),
        "results": results,
    }


def synthetic_validation() -> dict[str, object]:
    import pandas as pd

    occupations = np.arange(100, 120)
    months = [f"2021-{month:02d}" for month in range(1, 9)]
    quintile = {occ: 1 + index % 5 for index, occ in enumerate(occupations)}
    rows = []
    for oi, occ in enumerate(occupations):
        for ti, month in enumerate(months):
            base = -1.1 + 0.025 * oi - 0.02 * ti
            p = float(_sigmoid(np.array([base]))[0])
            total = 1000.0 + 5 * oi + 3 * ti
            rows.extend([
                {"month": month, "lookup_role": CURRENT_ROLE,
                 "occ_code": f"{occ:04d}",
                 "occupation_key": f"{CURRENT_ROLE}:{occ:04d}",
                 "dv_rating_beta": float(quintile[occ]),
                 "exposure_quintile": quintile[occ], "age_group": "young_22_25",
                 "employment_headcount": total * p, "unweighted_n": 10,
                 "weight_sq_sum": 1.0},
                {"month": month, "lookup_role": CURRENT_ROLE,
                 "occ_code": f"{occ:04d}",
                 "occupation_key": f"{CURRENT_ROLE}:{occ:04d}",
                 "dv_rating_beta": float(quintile[occ]),
                 "exposure_quintile": quintile[occ], "age_group": "older_26_65",
                 "employment_headcount": total * (1 - p), "unweighted_n": 10,
                 "weight_sq_sum": 1.0},
            ])
    cells = pd.DataFrame(rows)

    # Direct estimator recovery on a noiseless target panel.
    prepared = _prepare_balanced_preperiod(cells)
    young = prepared["young"]
    older = prepared["older"]
    total = young + older
    post = np.array([False] * 4 + [True] * 4)
    true_effect = -0.2
    probability = young / total
    treatment = (prepared["quintile"][:, None] == 5) & post[None, :]
    log_odds = np.log(probability / (1 - probability)) + true_effect * treatment
    injected = total * _sigmoid(log_odds)
    fit = fit_grouped_logit_fe(
        injected.reshape(-1), total.reshape(-1),
        np.repeat(np.arange(len(occupations)), len(months)),
        np.tile(np.arange(len(months)), len(occupations)),
        _design(prepared["quintile"], post),
    )
    if not fit.converged or abs(fit.beta[3] - true_effect) > 1e-5:
        raise RuntimeError("synthetic estimator recovery failed")
    smoke = run_power_simulation(cells, [0.0, true_effect], 3, 20260825)
    return {
        "status": "PASS_SYNTHETIC_REAL_ENGINE_VALIDATION_NOT_REAL_POWER",
        "real_power_executed": False,
        "post_outcomes_read": False,
        "conditional_ppml_equivalence_exercised": True,
        "injected_log_effect": true_effect,
        "recovered_log_effect": float(fit.beta[3]),
        "recovery_absolute_error": float(abs(fit.beta[3] - true_effect)),
        "simulation_smoke_effects": len(smoke["results"]),
        "planned_post_month_count": len(planned_post_months()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--synthetic-validation", action="store_true")
    parser.add_argument("--real-power", action="store_true")
    parser.add_argument("--cells", type=pathlib.Path)
    parser.add_argument("--cells-receipt", type=pathlib.Path)
    parser.add_argument("--c1-receipt", type=pathlib.Path)
    parser.add_argument("--lookup", type=pathlib.Path)
    parser.add_argument("--repetitions", type=int, default=999)
    parser.add_argument("--seed", type=int, default=20260825)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    if args.synthetic_validation == args.real_power:
        raise SystemExit("choose exactly one of --synthetic-validation or --real-power")
    if args.synthetic_validation:
        result = synthetic_validation()
    else:
        required = [args.cells, args.cells_receipt, args.c1_receipt, args.lookup]
        if any(value is None for value in required):
            raise RealPowerBlocked("real power requires cells, cells receipt, C1 receipt, and lookup")
        if args.repetitions < 999:
            raise RealPowerBlocked("real power requires at least 999 repetitions")
        c1 = authenticate_c1(args.c1_receipt, args.lookup)
        authenticate_cells(args.cells_receipt, args.cells, args.lookup)
        import pandas as pd
        cells = pd.read_csv(args.cells)
        result = run_power_simulation(cells, DEFAULT_EFFECTS, args.repetitions, args.seed)
        result["real_power_executed"] = True
        result["cells_sha256"] = sha256_file(args.cells)
        result["lookup_sha256"] = sha256_file(args.lookup)
        result["c1_receipt_status"] = c1["status"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "real_power_executed": result.get("real_power_executed", False),
        "post_outcomes_read": result["post_outcomes_read"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
