"""Pure helpers for the frozen YAX Phase 3 implementation.

POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1.
The functions here contain no file I/O and estimate no labor outcome model.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd


LABEL = "POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1"
AIOE = (
    "aioe_admin_equal",
    "aioe_ability_direct",
    "aioe_oews2018_source_weighted",
)
ELOUNDOU = ("dv_rating_alpha", "dv_rating_beta", "dv_rating_gamma")
MEASURES = AIOE + ELOUNDOU


@dataclass(frozen=True)
class ComponentMoments:
    mean: dict[str, float]
    sd: dict[str, float]


def weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    valid = np.isfinite(values) & np.isfinite(weights) & (weights > 0)
    if not valid.any():
        raise ValueError("no positive-weight finite observations")
    return float(np.average(values[valid], weights=weights[valid]))


def weighted_sd(values: np.ndarray, weights: np.ndarray) -> float:
    mean = weighted_mean(values, weights)
    variance = weighted_mean(np.square(np.asarray(values, float) - mean), weights)
    sd = math.sqrt(max(variance, 0.0))
    if not np.isfinite(sd) or sd <= 0:
        raise ValueError("weighted standard deviation is not positive")
    return sd


def weighted_quantile(values: np.ndarray, weights: np.ndarray, quantile: float) -> float:
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    valid = np.isfinite(values) & np.isfinite(weights) & (weights > 0)
    if not 0 <= quantile <= 1 or not valid.any():
        raise ValueError("invalid weighted quantile request")
    values, weights = values[valid], weights[valid]
    order = np.argsort(values, kind="mergesort")
    cumulative = np.cumsum(weights[order])
    index = min(
        int(np.searchsorted(cumulative, quantile * cumulative[-1], side="left")),
        len(values) - 1,
    )
    return float(values[order[index]])


def weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    return weighted_quantile(values, weights, 0.5)


def tie_preserving_weighted_bins(
    values: np.ndarray, weights: np.ndarray, shares: tuple[float, ...] = (0.2, 0.4, 0.6, 0.8)
) -> tuple[np.ndarray, np.ndarray]:
    cuts = np.array([weighted_quantile(values, weights, share) for share in shares])
    if np.any(cuts[:-1] >= cuts[1:]):
        raise ValueError(f"weighted bin cuts are not distinct: {cuts.tolist()}")
    bins = np.searchsorted(cuts, np.asarray(values, float), side="left") + 1
    return bins.astype(int), cuts


def fit_component_moments(frame: pd.DataFrame, weights: np.ndarray) -> ComponentMoments:
    missing = [measure for measure in MEASURES if measure not in frame]
    if missing:
        raise ValueError(f"missing exposure columns: {missing}")
    means, sds = {}, {}
    for measure in MEASURES:
        values = frame[measure].to_numpy(float)
        means[measure] = weighted_mean(values, weights)
        sds[measure] = weighted_sd(values, weights)
    return ComponentMoments(means, sds)


def component_arrays(frame: pd.DataFrame, moments: ComponentMoments) -> pd.DataFrame:
    result = pd.DataFrame(index=frame.index)
    for measure in MEASURES:
        result[f"z__{measure}"] = (
            pd.to_numeric(frame[measure], errors="coerce") - moments.mean[measure]
        ) / moments.sd[measure]
    result["A"] = result[[f"z__{measure}" for measure in AIOE]].mean(axis=1)
    result["E"] = result[[f"z__{measure}" for measure in ELOUNDOU]].mean(axis=1)
    result["F"] = (result.A + result.E) / 2
    result["G"] = (result.A - result.E) / 2
    for measure in MEASURES:
        result[f"R__{measure}"] = result[f"z__{measure}"] - result.F
    return result


def component_maps(
    maps: dict[str, dict[str, float]], moments: ComponentMoments
) -> dict[str, dict[str, float]]:
    codes = sorted(set.intersection(*(
        {code for code, value in maps[measure].items() if np.isfinite(value)}
        for measure in MEASURES
    )))
    raw = pd.DataFrame({measure: [maps[measure][code] for code in codes] for measure in MEASURES})
    components = component_arrays(raw, moments)
    output: dict[str, dict[str, float]] = {}
    for column in components:
        output[column] = dict(zip(codes, components[column].to_numpy(float)))
    return output


def weighted_corr(x: np.ndarray, y: np.ndarray, weights: np.ndarray) -> float:
    x, y, weights = np.asarray(x, float), np.asarray(y, float), np.asarray(weights, float)
    mx, my = weighted_mean(x, weights), weighted_mean(y, weights)
    covariance = weighted_mean((x - mx) * (y - my), weights)
    return covariance / (weighted_sd(x, weights) * weighted_sd(y, weights))


def hamilton_counts(weights: np.ndarray, units: int) -> tuple[np.ndarray, np.ndarray]:
    weights = np.asarray(weights, dtype=float)
    if units <= 0 or np.any(~np.isfinite(weights)) or np.any(weights < 0) or weights.sum() <= 0:
        raise ValueError("invalid Hamilton allocation")
    expected = weights / weights.sum() * units
    counts = np.floor(expected).astype(int)
    remainder = int(units - counts.sum())
    order = np.argsort(-(expected - counts), kind="mergesort")
    counts[order[:remainder]] += 1
    if counts.sum() != units:
        raise RuntimeError("Hamilton allocation did not sum to requested units")
    return counts, expected


def repair_self_matches_within_groups(
    origin: np.ndarray,
    destination: np.ndarray,
    groups: np.ndarray,
    rng: np.random.Generator,
    max_attempts: int = 20,
) -> tuple[np.ndarray, int, int]:
    """Randomly rematch destinations inside groups and remove all self-pairs.

    Destinations are swapped only within group, so every group-specific detailed
    destination margin is preserved exactly. The function retries a fresh
    random ordering if a local swap repair reaches an impasse.
    """
    origin = np.asarray(origin)
    destination = np.asarray(destination)
    groups = np.asarray(groups)
    if not (len(origin) == len(destination) == len(groups)):
        raise ValueError("rematch arrays differ in length")
    if len(origin) == 0:
        raise ValueError("cannot rematch an empty pseudo-population")
    order_by_group = np.argsort(groups, kind="mergesort")
    if not np.array_equal(order_by_group, np.arange(len(groups))):
        raise ValueError("groups must be contiguous and sorted")
    boundaries = np.r_[0, 1 + np.flatnonzero(groups[1:] != groups[:-1]), len(groups)]

    for attempt in range(1, max_attempts + 1):
        keys = rng.random(len(destination))
        shuffled_order = np.lexsort((keys, groups))
        candidate = destination[shuffled_order].copy()
        if not np.array_equal(groups[shuffled_order], groups):
            raise RuntimeError("a destination crossed a hard-benchmark stratum")
        repairs = 0
        failed = False
        for start, stop in zip(boundaries[:-1], boundaries[1:]):
            local_origin = origin[start:stop]
            local_destination = candidate[start:stop]
            for _ in range(max(1, 4 * (stop - start))):
                bad = np.flatnonzero(local_origin == local_destination)
                if len(bad) == 0:
                    break
                i = int(bad[0])
                feasible = np.flatnonzero(
                    (np.arange(stop - start) != i)
                    & (local_destination != local_origin[i])
                    & (local_destination[i] != local_origin)
                )
                if len(feasible) == 0:
                    failed = True
                    break
                j = int(feasible[rng.integers(len(feasible))])
                local_destination[i], local_destination[j] = (
                    local_destination[j], local_destination[i]
                )
                repairs += 1
            if failed or np.any(local_origin == local_destination):
                failed = True
                break
            candidate[start:stop] = local_destination
        if not failed:
            if np.any(origin == candidate):
                raise RuntimeError("self-transition survived repair")
            return candidate, repairs, attempt
    raise RuntimeError("hard-benchmark within-stratum self-match repair failed")


def classify_hard_benchmark(
    gap: float, realized: float, p975: float, fallback_support: float = 1.0
) -> str:
    if fallback_support < 0.90 or gap < 0.01:
        return "HB-C"
    if gap >= 0.0401 and realized > p975:
        return "HB-A"
    return "HB-B"


def classify_reallocation_component(
    primary_low_minus_high: float,
    primary_h_ratio: float,
    persistent_low_minus_high: float,
) -> str:
    if (
        primary_low_minus_high >= 0.15
        and primary_h_ratio >= 1.25
        and persistent_low_minus_high >= 0.10
    ):
        return "SC-R1"
    if (
        primary_low_minus_high >= 0.05
        and primary_h_ratio >= 1.10
        and persistent_low_minus_high > 0
    ):
        return "SC-R2"
    return "SC-R3"


def classify_shared_stock(coefficient: float, ci_upper: float) -> str:
    if coefficient >= 0:
        return "SC-C"
    if ci_upper < 0 and abs(coefficient) >= 0.07385795:
        return "SC-A"
    return "SC-B"


def simultaneous_one_sided_upper_bounds(
    estimates: np.ndarray,
    standard_errors: np.ndarray,
    centered_shifts: np.ndarray,
    level: float = 0.95,
) -> dict:
    estimates = np.asarray(estimates, float)
    standard_errors = np.asarray(standard_errors, float)
    centered_shifts = np.asarray(centered_shifts, float)
    if centered_shifts.ndim != 2 or centered_shifts.shape[1] != len(estimates):
        raise ValueError("joint shift matrix has wrong shape")
    if np.any(standard_errors <= 0):
        raise ValueError("joint inference requires positive standard errors")
    max_stat = np.max(-centered_shifts / standard_errors[None, :], axis=1)
    critical = float(np.quantile(max_stat, level, method="higher"))
    upper = estimates + critical * standard_errors
    observed = estimates / standard_errors
    marginal_p = np.array([
        (1 + np.sum(centered_shifts[:, index] / standard_errors[index] <= observed[index]))
        / (len(centered_shifts) + 1)
        for index in range(len(estimates))
    ])
    return {
        "critical": critical,
        "upper_bounds": upper,
        "marginal_one_sided_p": marginal_p,
        "intersection_union_p": float(marginal_p.max()),
        "all_upper_bounds_negative": bool(np.all(upper < 0)),
    }


def select_phase3_path(hb: str, sc_r: str, sc: str) -> str:
    if (hb, sc_r, sc) == ("HB-A", "SC-R1", "SC-A"):
        return "PATH-P3-A"
    if hb == "HB-C" or sc_r == "SC-R3" or sc == "SC-C":
        return "PATH-P3-C"
    return "PATH-P3-B"
