"""Small deterministic utilities for the Gate 3 inference validation.

These functions contain no project data and do not fit a scientific model.
They make the DGP-mean integration, multiplier support, cross-fit split, and
Monte Carlo stopping calculations independently testable before SCC execution.
"""
from __future__ import annotations

import math

import numpy as np


def expit(value: np.ndarray | float) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    return 1.0 / (1.0 + np.exp(-np.clip(array, -700.0, 700.0)))


def rademacher_logit_mean(eta: np.ndarray, amplitude: np.ndarray) -> np.ndarray:
    """Return E[logit^{-1}(eta + s*amplitude)] for equiprobable s in {-1,1}."""
    eta_array, amplitude_array = np.broadcast_arrays(
        np.asarray(eta, dtype=float), np.asarray(amplitude, dtype=float))
    return (expit(eta_array + amplitude_array) +
            expit(eta_array - amplitude_array)) / 2.0


def gaussian_logit_mean(eta: np.ndarray, sigma: np.ndarray | float,
                        order: int = 41) -> np.ndarray:
    """Integrate a mean-zero Gaussian logit shock by Gauss--Hermite quadrature."""
    if order < 3:
        raise ValueError("quadrature order must be at least three")
    eta_array, sigma_array = np.broadcast_arrays(
        np.asarray(eta, dtype=float), np.asarray(sigma, dtype=float))
    if np.any(~np.isfinite(eta_array)) or np.any(~np.isfinite(sigma_array)):
        raise ValueError("quadrature inputs must be finite")
    if np.any(sigma_array < 0):
        raise ValueError("Gaussian shock scale cannot be negative")
    nodes, weights = np.polynomial.hermite.hermgauss(order)
    values = expit(
        eta_array[..., None] + math.sqrt(2.0) * sigma_array[..., None] * nodes)
    return np.sum(values * weights, axis=-1) / math.sqrt(math.pi)


def webb_six_point_support() -> np.ndarray:
    """Equal-probability Webb multipliers with mean zero and variance one."""
    return np.asarray([
        -math.sqrt(1.5), -1.0, -math.sqrt(0.5),
        math.sqrt(0.5), 1.0, math.sqrt(1.5),
    ])


def crossfit_fold(replicate: np.ndarray | int) -> np.ndarray:
    """Return 0 for odd and 1 for even positive replicate identifiers."""
    values = np.asarray(replicate)
    if np.any(values < 1) or np.any(values != np.floor(values)):
        raise ValueError("replicate identifiers must be positive integers")
    return (values.astype(np.int64) + 1) % 2


def binomial_monte_carlo_se(rate: float, attempts: int) -> float:
    if attempts < 1 or not 0.0 <= rate <= 1.0:
        raise ValueError("invalid rate or attempt count")
    return math.sqrt(rate * (1.0 - rate) / attempts)


def empirical_sd_relative_monte_carlo_error(attempts: int) -> float:
    """Large-sample relative MC error of a standard deviation estimate."""
    if attempts < 2:
        raise ValueError("at least two attempts are required")
    return 1.0 / math.sqrt(2.0 * (attempts - 1.0))


def outer_replications_resolved(rate: float, attempts: int) -> bool:
    """Apply the frozen draft's two outer-replication accuracy criteria."""
    return (binomial_monte_carlo_se(rate, attempts) <= 0.0125 and
            empirical_sd_relative_monte_carlo_error(attempts) <= 0.05)
