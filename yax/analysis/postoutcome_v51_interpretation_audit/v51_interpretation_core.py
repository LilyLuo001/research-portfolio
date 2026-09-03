"""Pure algebra and treatment-only helpers for the closed YAX V5.1 audit.

Nothing in this module fits or refits a labor-outcome model.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    values = np.asarray(values, float)
    weights = np.asarray(weights, float)
    if len(values) == 0 or len(values) != len(weights):
        raise ValueError("invalid weighted arrays")
    if np.any(~np.isfinite(values)) or np.any(~np.isfinite(weights)) or np.any(weights <= 0):
        raise ValueError("weighted arrays must be finite with positive weights")
    return float(np.average(values, weights=weights))


def weighted_sd(values: np.ndarray, weights: np.ndarray) -> float:
    mean = weighted_mean(values, weights)
    sd = math.sqrt(weighted_mean(np.square(np.asarray(values, float) - mean), weights))
    if not sd > 0:
        raise ValueError("weighted SD must be positive")
    return float(sd)


def weighted_covariance(left: np.ndarray, right: np.ndarray, weights: np.ndarray) -> float:
    ml = weighted_mean(left, weights)
    mr = weighted_mean(right, weights)
    return weighted_mean((np.asarray(left, float) - ml) * (np.asarray(right, float) - mr), weights)


def weighted_correlation(left: np.ndarray, right: np.ndarray, weights: np.ndarray) -> float:
    return weighted_covariance(left, right, weights) / (weighted_sd(left, weights) * weighted_sd(right, weights))


def average_rank(values: np.ndarray) -> np.ndarray:
    return pd.Series(np.asarray(values, float)).rank(method="average").to_numpy(float)


def weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    values = np.asarray(values, float)
    weights = np.asarray(weights, float)
    if not 0 <= q <= 1:
        raise ValueError("q must lie in [0,1]")
    order = np.argsort(values, kind="mergesort")
    cumulative = np.cumsum(weights[order])
    index = min(int(np.searchsorted(cumulative, q * cumulative[-1], side="left")), len(values) - 1)
    return float(values[order[index]])


def tail_masks(values: np.ndarray, weights: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    low = weighted_quantile(values, weights, 0.2)
    high = weighted_quantile(values, weights, 0.8)
    values = np.asarray(values, float)
    return values <= low, values > high


def overlap_retention(reference: np.ndarray, candidate: np.ndarray, weights: np.ndarray) -> float:
    denominator = float(np.sum(weights[reference]))
    if denominator <= 0:
        raise ValueError("empty reference tail")
    return float(np.sum(weights[reference & candidate]) / denominator)


def covariance_contributions(
    target: np.ndarray,
    components: dict[str, np.ndarray],
    coefficients: dict[str, float],
    weights: np.ndarray,
) -> dict[str, float]:
    variance = weighted_covariance(target, target, weights)
    result = {
        name: float(coefficients[name] * weighted_covariance(values, target, weights) / variance)
        for name, values in components.items()
    }
    if not math.isclose(sum(result.values()), 1.0, abs_tol=1e-10):
        raise RuntimeError("covariance contributions do not sum to one")
    return result


def transform_fg_to_ae(
    coefficient_fg: np.ndarray,
    covariance_fg: np.ndarray,
    s_f: float,
    s_g: float,
    s_a: float,
    s_e: float,
) -> dict[str, np.ndarray]:
    """Transform coefficients/covariance from standardized F,G to raw and SD A,E."""
    coefficient_fg = np.asarray(coefficient_fg, float)
    covariance_fg = np.asarray(covariance_fg, float)
    if coefficient_fg.shape != (2,) or covariance_fg.shape != (2, 2):
        raise ValueError("F/G coefficient and covariance dimensions must be 2 and 2x2")
    if min(s_f, s_g, s_a, s_e) <= 0:
        raise ValueError("all scales must be positive")
    raw_map = np.array([
        [0.5 / s_f, 0.5 / s_g],
        [0.5 / s_f, -0.5 / s_g],
    ])
    sd_map = np.diag([s_a, s_e]) @ raw_map
    return {
        "raw_map": raw_map,
        "sd_map": sd_map,
        "coefficient_raw": raw_map @ coefficient_fg,
        "coefficient_sd": sd_map @ coefficient_fg,
        "covariance_raw": raw_map @ covariance_fg @ raw_map.T,
        "covariance_sd": sd_map @ covariance_fg @ sd_map.T,
    }


def normal_interval(coefficient: float, variance: float) -> tuple[float, float]:
    se = math.sqrt(float(variance))
    critical = 1.959963984540054
    return coefficient - critical * se, coefficient + critical * se


def predictor_identity(
    a: np.ndarray,
    e: np.ndarray,
    means: dict[str, float],
    scales: dict[str, float],
    coefficient_fg: np.ndarray,
    coefficient_ae_raw: np.ndarray,
) -> float:
    a = np.asarray(a, float)
    e = np.asarray(e, float)
    f = (a + e) / 2
    g = (a - e) / 2
    fg = coefficient_fg[0] * (f - means["F"]) / scales["F"]
    fg += coefficient_fg[1] * (g - means["G"]) / scales["G"]
    ae = coefficient_ae_raw[0] * (a - means["A"])
    ae += coefficient_ae_raw[1] * (e - means["E"])
    return float(np.max(np.abs(fg - ae)))
