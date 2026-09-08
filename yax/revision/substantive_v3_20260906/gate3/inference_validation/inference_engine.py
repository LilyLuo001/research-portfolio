#!/usr/bin/env python3
"""Same-target fitting, influence, and simulation primitives for Gate 3.

The module contains no file access and publishes no protected object.  Its
purpose is to make the scientific invariants testable before the SCC runner is
allowed to read aggregate cells or microdata.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np


TARGET_INDEX = 3
TARGET_LABEL = "Q5_x_post"
REGRESSOR_LABELS = (
    "Q2_x_post", "Q3_x_post", "Q4_x_post", "Q5_x_post",
    "Webb_z_x_post",
)
WEBB_SUPPORT = np.asarray([
    -math.sqrt(3.0 / 2.0), -1.0, -math.sqrt(1.0 / 2.0),
    math.sqrt(1.0 / 2.0), 1.0, math.sqrt(3.0 / 2.0),
])


@dataclass(frozen=True)
class ModelDesign:
    structure: str
    regressors: np.ndarray
    first_labels: np.ndarray
    second_labels: np.ndarray
    occupation_codes: np.ndarray
    family_codes: np.ndarray
    regressor_labels: tuple[str, ...] = REGRESSOR_LABELS
    focal_target_index: int = TARGET_INDEX


@dataclass(frozen=True)
class FitArtifacts:
    structure: str
    beta: np.ndarray
    fitted_probability: np.ndarray
    residual: np.ndarray
    occupation_influence: np.ndarray
    family_influence: np.ndarray
    active_occupation_count: int
    active_family_count: int
    separated_observation_count: int
    separated_first_group_count: int
    separated_second_group_count: int
    iterations: int
    maximum_normalized_score: float

    @property
    def estimate(self) -> float:
        return float(self.beta[TARGET_INDEX])

    @property
    def occupation_se(self) -> float:
        value = self.occupation_influence[:, TARGET_INDEX]
        return float(np.sqrt(value @ value))

    @property
    def family_se(self) -> float:
        value = self.family_influence[:, TARGET_INDEX]
        return float(np.sqrt(value @ value))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def month_number(value: str) -> int:
    year, month = (int(part) for part in value.split("-"))
    require(1 <= month <= 12, f"invalid calendar month {value}")
    return year * 12 + month - 1


def elapsed_month_gaps(months: list[str]) -> np.ndarray:
    values = np.asarray([month_number(value) for value in months], int)
    require(len(values) > 0 and np.all(np.diff(values) > 0),
            "months must be strictly increasing")
    return np.diff(values)


def build_design(quintiles: np.ndarray, webb_z: np.ndarray,
                 families: np.ndarray, months: list[str],
                 structure: str) -> ModelDesign:
    """Build the two central Gate 2 designs on identical row order."""
    quintiles = np.asarray(quintiles, int)
    webb_z = np.asarray(webb_z, float)
    families = np.asarray(families, object)
    n_occ = len(quintiles)
    require(n_occ > 1 and webb_z.shape == (n_occ,) and families.shape == (n_occ,),
            "occupation attributes are misaligned")
    require(set(quintiles.tolist()) == {1, 2, 3, 4, 5},
            "all five fixed quintiles are required")
    require(structure in {"pooled", "family_month"}, "unknown central structure")
    n_month = len(months)
    require(n_month > 1 and len(set(months)) == n_month, "month support differs")
    post = np.asarray([value >= "2023-01" for value in months], bool)
    q = np.repeat(quintiles, n_month)
    row_post = np.tile(post, n_occ)
    regressors = np.column_stack([
        ((q == value) & row_post).astype(float) for value in (2, 3, 4, 5)
    ] + [np.repeat(webb_z, n_month) * row_post])
    occupation_codes = np.repeat(np.arange(n_occ), n_month)
    family_levels = {value: index for index, value in enumerate(sorted(set(families.tolist())))}
    family_codes = np.repeat(np.asarray([family_levels[value] for value in families], int), n_month)
    first = occupation_codes.astype(object)
    if structure == "pooled":
        second = np.tile(np.arange(n_month), n_occ).astype(object)
    else:
        month_codes = np.tile(np.arange(n_month), n_occ)
        second = (family_codes * n_month + month_codes).astype(object)
    return ModelDesign(
        structure=structure, regressors=regressors,
        first_labels=first, second_labels=second,
        occupation_codes=occupation_codes, family_codes=family_codes,
    )


def _active_contiguous(labels: np.ndarray, active: np.ndarray) -> tuple[np.ndarray, int]:
    labels = np.asarray(labels, object)
    active_values = sorted(set(labels[active].tolist()))
    require(bool(active_values), "fixed-effect dimension is empty")
    lookup = {value: index for index, value in enumerate(active_values)}
    codes = np.zeros(len(labels), int)
    codes[active] = np.asarray([lookup[value] for value in labels[active]], int)
    return codes, len(active_values)


def drop_separated_fixed_effect_groups(
        young: np.ndarray, total: np.ndarray,
        first_labels: np.ndarray, second_labels: np.ndarray,
        absolute_tolerance: float = 1e-10) -> tuple[np.ndarray, dict[str, int]]:
    """Iteratively remove fixed-effect groups with one-sided outcomes.

    A grouped-logit fixed effect has no finite maximizer when every retained
    observation in its group is all-young or all-older. Such a group supplies
    no within-group coefficient information. Removing it may create a new
    one-sided group in the other fixed-effect dimension, so trimming iterates
    to closure.
    """
    young = np.asarray(young, float).reshape(-1)
    total = np.asarray(total, float).reshape(-1)
    first_labels = np.asarray(first_labels, object)
    second_labels = np.asarray(second_labels, object)
    require(len(young) == len(total) == len(first_labels) == len(second_labels),
            "separation-trim arrays differ")
    active = total > 0
    initial = int(active.sum())
    dropped_first: set[Any] = set()
    dropped_second: set[Any] = set()
    while True:
        changed = False
        for labels, dropped in ((first_labels, dropped_first),
                                (second_labels, dropped_second)):
            levels, inverse = np.unique(labels[active], return_inverse=True)
            require(len(levels) > 0, "separation trimming removed every observation")
            group_young = np.bincount(
                inverse, weights=young[active], minlength=len(levels))
            group_total = np.bincount(
                inverse, weights=total[active], minlength=len(levels))
            separated = ((group_young <= absolute_tolerance) |
                         (group_total - group_young <= absolute_tolerance))
            if np.any(separated):
                values = levels[separated]
                dropped.update(values.tolist())
                active &= ~np.isin(labels, values)
                changed = True
        if not changed:
            break
    return active, {
        "separated_observation_count": initial - int(active.sum()),
        "separated_first_group_count": len(dropped_first),
        "separated_second_group_count": len(dropped_second),
    }


def fit_with_influence(engine: Any, young: np.ndarray, total: np.ndarray,
                       design: ModelDesign, max_iterations: int = 5000) -> FitArtifacts:
    """Fit one central grouped logit and form alternative cluster influences."""
    young = np.asarray(young, float).reshape(-1)
    total = np.asarray(total, float).reshape(-1)
    x = np.asarray(design.regressors, float)
    require(len(young) == len(total) == len(x), "outcome/design rows differ")
    require(np.all(np.isfinite(young)) and np.all(np.isfinite(total)),
            "outcomes are nonfinite")
    require(np.all(total >= 0) and np.all(young >= 0) and np.all(young <= total),
            "invalid grouped-binomial outcome")
    active, separation = drop_separated_fixed_effect_groups(
        young, total, design.first_labels, design.second_labels)
    first, n_first = _active_contiguous(design.first_labels, active)
    second, n_second = _active_contiguous(design.second_labels, active)
    fit_young = young.copy()
    fit_total = total.copy()
    fit_young[~active] = 0.0
    fit_total[~active] = 0.0
    fit = engine.fit_grouped_logit_fe(
        fit_young, fit_total, first, second, x,
        tolerance=1e-8, max_iterations=max_iterations,
    )
    require(bool(fit.converged), f"{design.structure} grouped-logit fit did not converge")
    y = young[active]
    n = total[active]
    xa = x[active]
    first_a = first[active]
    second_a = second[active]
    probability = np.asarray(fit.fitted_probability, float)[active]
    residual = y - n * probability
    weight = np.maximum(n * probability * (1.0 - probability), 1e-12)
    rx = engine._weighted_absorb(xa, weight, first_a, second_a, n_first, n_second)
    information = rx.T @ (weight[:, None] * rx)
    bread = np.linalg.inv(information)
    observation_scores = rx * residual[:, None]

    occ = design.occupation_codes[active]
    n_occ = int(design.occupation_codes.max()) + 1
    occ_scores = np.zeros((n_occ, x.shape[1]))
    np.add.at(occ_scores, occ, observation_scores)
    active_occ = np.unique(occ)
    require(len(active_occ) > 1, "fewer than two active occupations")
    occ_influence = occ_scores @ bread.T
    occ_influence *= math.sqrt(len(active_occ) / (len(active_occ) - 1.0))

    family = design.family_codes[active]
    n_family = int(design.family_codes.max()) + 1
    family_scores = np.zeros((n_family, x.shape[1]))
    np.add.at(family_scores, family, observation_scores)
    active_family = np.unique(family)
    require(len(active_family) > 1, "fewer than two active families")
    family_influence = family_scores @ bread.T
    family_influence *= math.sqrt(len(active_family) / (len(active_family) - 1.0))

    normalized_score = float(np.max(np.abs(rx.T @ residual)) / max(1.0, n.sum()))
    require(normalized_score <= 1e-7, f"{design.structure} score certificate failed")
    target = design.focal_target_index
    require(np.isclose(occ_influence[:, target] @ occ_influence[:, target],
                       float(fit.standard_error[target]) ** 2,
                       rtol=1e-7, atol=1e-12),
            "occupation influence does not reproduce estimator covariance")
    return FitArtifacts(
        structure=design.structure, beta=np.asarray(fit.beta, float),
        fitted_probability=np.asarray(fit.fitted_probability, float),
        residual=np.asarray(fit.residual, float),
        occupation_influence=occ_influence, family_influence=family_influence,
        active_occupation_count=len(active_occ), active_family_count=len(active_family),
        separated_observation_count=separation["separated_observation_count"],
        separated_first_group_count=separation["separated_first_group_count"],
        separated_second_group_count=separation["separated_second_group_count"],
        iterations=int(fit.iterations), maximum_normalized_score=normalized_score,
    )


def paired_target(left: FitArtifacts, right: FitArtifacts) -> dict[str, Any]:
    """Return a covariance-preserving paired movement representation."""
    require(left.occupation_influence.shape == right.occupation_influence.shape,
            "occupation influence universes differ")
    require(left.family_influence.shape == right.family_influence.shape,
            "family influence universes differ")
    occ = left.occupation_influence[:, TARGET_INDEX] - right.occupation_influence[:, TARGET_INDEX]
    family = left.family_influence[:, TARGET_INDEX] - right.family_influence[:, TARGET_INDEX]
    return {
        "estimate": left.estimate - right.estimate,
        "occupation_influence": occ,
        "family_influence": family,
        "occupation_se": float(np.sqrt(occ @ occ)),
        "family_se": float(np.sqrt(family @ family)),
    }


def multiplier_interval(estimate: float, influence: np.ndarray,
                        multipliers: np.ndarray, alpha: float = 0.05) -> dict[str, float]:
    """Fixed-studentizer multiplier interval using a retained common draw matrix."""
    influence = np.asarray(influence, float)
    multipliers = np.asarray(multipliers, float)
    require(multipliers.ndim == 2 and multipliers.shape[1] == len(influence),
            "multiplier/influence dimensions differ")
    se = float(np.sqrt(influence @ influence))
    require(np.isfinite(se) and se > 0, "invalid multiplier studentizer")
    centered = multipliers @ influence
    critical = float(np.quantile(np.abs(centered / se), 1.0 - alpha, method="higher"))
    return {
        "se": se,
        "critical": critical,
        "lower": float(estimate - critical * se),
        "upper": float(estimate + critical * se),
        "p_value": float((1 + np.sum(np.abs(centered / se) >= abs(estimate / se))) /
                         (len(centered) + 1)),
    }


def draw_multiplier_matrices(draws: int, occupation_count: int,
                             family_count: int, seed: int) -> dict[str, np.ndarray]:
    """Draw once so all models and paired targets use common multipliers."""
    require(draws >= 999 and occupation_count > 1 and family_count > 1,
            "multiplier inventory is uninformative")
    rng = np.random.default_rng(seed)
    return {
        "occupation_rademacher": rng.choice(
            np.asarray([-1.0, 1.0]), size=(draws, occupation_count)),
        "occupation_webb": rng.choice(WEBB_SUPPORT, size=(draws, occupation_count)),
        "family_rademacher": rng.choice(
            np.asarray([-1.0, 1.0]), size=(draws, family_count)),
        "family_webb": rng.choice(WEBB_SUPPORT, size=(draws, family_count)),
    }


def estimate_ar1(shocks: np.ndarray, weights: np.ndarray,
                 months: list[str]) -> dict[str, Any]:
    """Calibrate a pooled, zero-mean AR(1) from consecutive observed months."""
    shocks = np.asarray(shocks, float)
    weights = np.asarray(weights, float)
    require(shocks.shape == weights.shape and shocks.shape[1] == len(months),
            "AR(1) calibration arrays differ")
    gaps = elapsed_month_gaps(months)
    pair = gaps == 1
    require(bool(pair.any()), "no consecutive calendar pairs")

    def one(keep_family: np.ndarray) -> tuple[float, float, float, int]:
        x = shocks[keep_family][:, :-1][:, pair].reshape(-1)
        y = shocks[keep_family][:, 1:][:, pair].reshape(-1)
        w = np.sqrt(weights[keep_family][:, :-1][:, pair] *
                    weights[keep_family][:, 1:][:, pair]).reshape(-1)
        good = np.isfinite(x) & np.isfinite(y) & np.isfinite(w) & (w > 0)
        x, y, w = x[good], y[good], w[good]
        require(len(x) > 2 and float(np.sum(w * x * x)) > 0,
                "AR(1) calibration support is empty")
        rho = float(np.sum(w * x * y) / np.sum(w * x * x))
        rho = float(np.clip(rho, -0.98, 0.98))
        innovation = y - rho * x
        innovation_sd = float(np.sqrt(np.average(np.square(innovation), weights=w)))
        stationary_sd = float(innovation_sd / math.sqrt(1.0 - rho * rho))
        return rho, innovation_sd, stationary_sd, len(x)

    full = one(np.ones(shocks.shape[0], bool))
    leave_one = [one(np.arange(shocks.shape[0]) != index) for index in range(shocks.shape[0])]
    return {
        "rho": full[0], "innovation_sd": full[1],
        "stationary_sd": full[2], "consecutive_pairs": full[3],
        "leave_one_family_rho_min": min(value[0] for value in leave_one),
        "leave_one_family_rho_max": max(value[0] for value in leave_one),
        "leave_one_family_stationary_sd_min": min(value[2] for value in leave_one),
        "leave_one_family_stationary_sd_max": max(value[2] for value in leave_one),
    }


def draw_stationary_ar1(rng: np.random.Generator, family_count: int,
                        months: list[str], rho: float,
                        stationary_sd: float) -> np.ndarray:
    """Draw a stationary family process while respecting actual calendar gaps."""
    require(abs(rho) < 1 and stationary_sd >= 0, "invalid AR(1) parameters")
    result = np.zeros((family_count, len(months)))
    if stationary_sd == 0:
        return result
    result[:, 0] = rng.normal(scale=stationary_sd, size=family_count)
    for index, gap in enumerate(elapsed_month_gaps(months), start=1):
        persistence = rho ** int(gap)
        innovation_sd = stationary_sd * math.sqrt(max(0.0, 1.0 - persistence ** 2))
        result[:, index] = (persistence * result[:, index - 1] +
                            rng.normal(scale=innovation_sd, size=family_count))
    return result


def binomial_stock_draw(rng: np.random.Generator, total: np.ndarray,
                        effective_count: np.ndarray,
                        probability: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Draw integer pseudo-counts and map them back to fixed weighted totals."""
    total = np.asarray(total, float)
    effective_count = np.asarray(effective_count, int)
    probability = np.asarray(probability, float)
    require(total.shape == effective_count.shape == probability.shape,
            "DGP arrays differ")
    active = effective_count > 0
    require(np.array_equal(active, total > 0), "effective-count support differs")
    require(np.all((probability >= 0) & (probability <= 1)), "invalid DGP probability")
    count = np.zeros_like(effective_count)
    count[active] = rng.binomial(effective_count[active], probability[active])
    young = np.zeros_like(total)
    older = np.zeros_like(total)
    young[active] = total[active] * count[active] / effective_count[active]
    older[active] = total[active] * (effective_count[active] - count[active]) / effective_count[active]
    require(np.all(young >= 0) and np.all(older >= 0), "negative simulated stock")
    require(np.allclose(young + older, total, rtol=5e-15, atol=1e-8),
            "simulated stocks do not preserve cell total")
    return young, older
