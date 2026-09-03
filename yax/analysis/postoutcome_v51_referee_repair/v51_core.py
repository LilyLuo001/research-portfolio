"""Pure helpers for the closed YAX V5.1 referee repair."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


CATEGORIES = (-1, 0, 1)


def weighted_mean_sd(values: np.ndarray, weights: np.ndarray) -> tuple[float, float]:
    values = np.asarray(values, float)
    weights = np.asarray(weights, float)
    if len(values) == 0 or len(values) != len(weights):
        raise ValueError("invalid weighted moments")
    if np.any(~np.isfinite(values)) or np.any(~np.isfinite(weights)) or np.any(weights <= 0):
        raise ValueError("moments require finite values and positive weights")
    mean = float(np.average(values, weights=weights))
    sd = float(np.sqrt(np.average(np.square(values - mean), weights=weights)))
    if not sd > 0:
        raise ValueError("weighted standard deviation is not positive")
    return mean, sd


def weighted_corr(x: np.ndarray, y: np.ndarray, weights: np.ndarray) -> float:
    mx, sx = weighted_mean_sd(x, weights)
    my, sy = weighted_mean_sd(y, weights)
    return float(np.average((np.asarray(x) - mx) * (np.asarray(y) - my), weights=weights) / (sx * sy))


def average_rank(values: np.ndarray) -> np.ndarray:
    return pd.Series(np.asarray(values, float)).rank(method="average").to_numpy(float)


def cohen_kappa(a: np.ndarray, b: np.ndarray, weights: np.ndarray) -> dict[str, float]:
    a, b, weights = np.asarray(a, int), np.asarray(b, int), np.asarray(weights, float)
    if not (len(a) == len(b) == len(weights)) or len(a) == 0:
        raise ValueError("invalid kappa arrays")
    if not set(np.unique(np.r_[a, b])).issubset(CATEGORIES):
        raise ValueError("labels must be -1, 0, or +1")
    if np.any(~np.isfinite(weights)) or np.any(weights <= 0):
        raise ValueError("kappa weights must be positive and finite")
    total = float(weights.sum())
    observed = float(np.sum(weights * (a == b)) / total)
    expected = 0.0
    for category in CATEGORIES:
        expected += float(np.sum(weights[a == category]) / total) * float(np.sum(weights[b == category]) / total)
    kappa = (observed - expected) / (1 - expected) if expected < 1 else float("nan")
    return {
        "raw_exact_agreement": observed,
        "expected_agreement": expected,
        "cohen_kappa": float(kappa),
        "opposite_sign_conflict": float(np.sum(weights[(a * b) < 0]) / total),
        "any_tie": float(np.sum(weights[(a == 0) | (b == 0)]) / total),
    }


def fleiss_kappa(labels: np.ndarray, weights: np.ndarray) -> dict[str, float]:
    labels, weights = np.asarray(labels, int), np.asarray(weights, float)
    if labels.ndim != 2 or labels.shape[0] != len(weights) or labels.shape[1] < 2:
        raise ValueError("invalid Fleiss arrays")
    if not set(np.unique(labels)).issubset(CATEGORIES):
        raise ValueError("labels must be -1, 0, or +1")
    if np.any(~np.isfinite(weights)) or np.any(weights <= 0):
        raise ValueError("Fleiss weights must be positive and finite")
    n_raters = labels.shape[1]
    counts = np.column_stack([(labels == category).sum(axis=1) for category in CATEGORIES])
    item_agreement = (np.square(counts).sum(axis=1) - n_raters) / (n_raters * (n_raters - 1))
    observed = float(np.average(item_agreement, weights=weights))
    category_share = np.average(counts / n_raters, axis=0, weights=weights)
    expected = float(np.square(category_share).sum())
    value = (observed - expected) / (1 - expected) if expected < 1 else float("nan")
    return {
        "fleiss_kappa": float(value),
        "observed_pair_agreement": observed,
        "expected_pair_agreement": expected,
    }


def cluster_meat(scores: np.ndarray, groups: np.ndarray) -> tuple[np.ndarray, int]:
    scores = np.asarray(scores, float)
    codes, levels = pd.factorize(np.asarray(groups), sort=True)
    grouped = np.zeros((len(levels), scores.shape[1]))
    np.add.at(grouped, codes, scores)
    return grouped.T @ grouped, len(levels)


def two_way_cluster_covariance(
    bread: np.ndarray,
    observation_scores: np.ndarray,
    occupation: np.ndarray,
    month: np.ndarray,
) -> dict[str, np.ndarray | int]:
    """CGM inclusion-exclusion covariance with fixed finite-cluster factors."""
    bread = np.asarray(bread, float)
    scores = np.asarray(observation_scores, float)
    if scores.ndim != 2 or bread.shape != (scores.shape[1], scores.shape[1]):
        raise ValueError("bread/score dimensions differ")
    occ_meat, n_occ = cluster_meat(scores, occupation)
    month_meat, n_month = cluster_meat(scores, month)
    cell_meat = scores.T @ scores
    n_cell = len(scores)
    if min(n_occ, n_month, n_cell) <= 1:
        raise ValueError("two-way clustering requires multiple clusters")
    variance = bread @ (
        n_occ / (n_occ - 1) * occ_meat
        + n_month / (n_month - 1) * month_meat
        - n_cell / (n_cell - 1) * cell_meat
    ) @ bread
    variance = (variance + variance.T) / 2
    return {
        "covariance": variance,
        "occupation_clusters": n_occ,
        "month_clusters": n_month,
        "nonzero_cells": n_cell,
    }


def wild_score_summary(
    estimates: np.ndarray,
    analytic_se: np.ndarray,
    influence: np.ndarray,
    seed: int,
    draws: int = 999,
) -> dict:
    estimates, analytic_se, influence = map(lambda x: np.asarray(x, float), (estimates, analytic_se, influence))
    if influence.shape[1] != len(estimates) or len(analytic_se) != len(estimates):
        raise ValueError("wild-score dimensions differ")
    if np.any(analytic_se <= 0):
        raise ValueError("standard errors must be positive")
    rng = np.random.default_rng(seed)
    multipliers = rng.choice(np.array([-1.0, 1.0]), size=(draws, influence.shape[0]))
    shifts = multipliers @ influence
    rows = []
    for index, estimate in enumerate(estimates):
        tstar = np.abs(shifts[:, index] / analytic_se[index])
        critical = float(np.quantile(tstar, 0.95, method="higher"))
        rows.append({
            "coefficient": float(estimate),
            "analytic_cluster_se": float(analytic_se[index]),
            "bootstrap_se": float(np.std(shifts[:, index], ddof=1)),
            "wild_score_p_value": float((1 + np.sum(tstar >= abs(estimate / analytic_se[index]))) / (draws + 1)),
            "wild_score_critical": critical,
            "wild_score_ci_lower": float(estimate - critical * analytic_se[index]),
            "wild_score_ci_upper": float(estimate + critical * analytic_se[index]),
        })
    observed_max = float(np.max(np.abs(estimates / analytic_se)))
    simulated_max = np.max(np.abs(shifts / analytic_se[None, :]), axis=1)
    return {
        "rows": rows,
        "centered_shift_covariance": np.cov(shifts, rowvar=False, ddof=1),
        "joint_max_abs_t": observed_max,
        "joint_max_abs_t_p_value": float((1 + np.sum(simulated_max >= observed_max)) / (draws + 1)),
        "draws": draws,
        "seed": seed,
    }
