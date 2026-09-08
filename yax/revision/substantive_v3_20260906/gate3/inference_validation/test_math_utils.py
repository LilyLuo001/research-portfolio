from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("yax_gate3_math", HERE / "math_utils.py")
MATH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MATH)


def test_rademacher_logit_mean_is_exact_two_point_average():
    eta = np.asarray([-2.0, 0.0, 1.5])
    amplitude = np.asarray([0.3, 2.0, 0.7])
    expected = (MATH.expit(eta + amplitude) + MATH.expit(eta - amplitude)) / 2.0
    assert np.array_equal(MATH.rademacher_logit_mean(eta, amplitude), expected)
    assert MATH.rademacher_logit_mean(np.asarray([0.0]), np.asarray([4.0]))[0] == 0.5


def test_gaussian_logit_mean_handles_zero_scale_and_symmetry():
    eta = np.asarray([-3.0, 0.0, 2.0])
    assert np.allclose(MATH.gaussian_logit_mean(eta, 0.0), MATH.expit(eta),
                       rtol=0, atol=2e-16)
    for scale in (0.1, 1.0, 4.0):
        assert abs(MATH.gaussian_logit_mean(np.asarray([0.0]), scale)[0] - 0.5) < 2e-15


def test_gaussian_quadrature_stability_at_declared_orders():
    eta = np.linspace(-5.0, 5.0, 41)
    sigma = np.linspace(0.0, 1.5, 41)
    low = MATH.gaussian_logit_mean(eta, sigma, order=41)
    high = MATH.gaussian_logit_mean(eta, sigma, order=82)
    assert np.max(np.abs(low - high)) < 2e-12


def test_webb_support_has_equal_weight_mean_zero_and_variance_one():
    values = MATH.webb_six_point_support()
    assert len(values) == 6
    assert abs(values.mean()) < 1e-16
    assert abs(np.mean(values ** 2) - 1.0) < 1e-16


def test_crossfit_is_deterministic_complete_and_disjoint():
    replicate = np.arange(1, 2000)
    fold = MATH.crossfit_fold(replicate)
    assert set(fold.tolist()) == {0, 1}
    assert np.all(fold[replicate % 2 == 1] == 0)
    assert np.all(fold[replicate % 2 == 0] == 1)
    with pytest.raises(ValueError):
        MATH.crossfit_fold(np.asarray([0, 1]))


def test_outer_accuracy_rule_requires_expansion_when_rate_is_noisy():
    assert not MATH.outer_replications_resolved(0.5, 399)
    assert MATH.outer_replications_resolved(0.5, 1999)
    assert MATH.outer_replications_resolved(0.05, 399)
    assert abs(MATH.empirical_sd_relative_monte_carlo_error(399) -
               1 / np.sqrt(796)) < 1e-16
