"""Independent regressions for the fail-closed exact-PSD wrapper.

These tests address only numerical input validation and conservative projection.
They do not validate an empirical covariance, a critical value, or data support.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest


METHOD = Path(__file__).resolve().parents[1] / "method"
sys.path.insert(0, str(METHOD))

from estimator import (  # noqa: E402
    InputRejected,
    _psd_covariance,
    joint_covariance_from_event_score_sums,
    ratio_contrast_outer_bound,
)


def project(covariance, theta=(2.0, 4.0, 1.0, 5.0), q=1.0):
    return ratio_contrast_outer_bound(
        theta,
        covariance,
        joint_critical_squared=q,
        calibration_status="SYNTHETIC_REVIEW_ONLY",
    )


def test_formerly_decisive_near_indefinite_input_is_rejected():
    covariance = np.eye(4)
    covariance[0, 1] = covariance[1, 0] = 1.0 + 5e-11
    assert np.linalg.eigvalsh(covariance).min() < 0.0
    with pytest.raises(InputRejected, match="negative principal minor"):
        project(covariance)


def test_all_principal_minors_not_only_leading_minors_are_enforced():
    # Every leading principal determinant is zero, but principal minor (1, 2)
    # is -3.  A leading-minors-only semidefinite check would accept it.
    covariance = np.array(
        [
            [0.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 2.0, 0.0],
            [0.0, 2.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 0.0],
        ]
    )
    with pytest.raises(InputRejected, match=r"principal minor \(1, 2\)"):
        _psd_covariance(covariance)


def test_exact_symmetry_rejects_one_ulp_and_never_symmetrizes():
    covariance = np.eye(4)
    covariance[0, 1] = np.nextafter(0.0, 1.0)
    with pytest.raises(InputRejected, match="not exactly symmetric"):
        _psd_covariance(covariance)


def test_tiny_negative_variance_is_rejected_without_clipping():
    covariance = np.eye(4)
    covariance[0, 0] = -np.nextafter(0.0, 1.0)
    with pytest.raises(InputRejected, match="negative principal minor"):
        _psd_covariance(covariance)


@pytest.mark.parametrize(
    "covariance",
    [
        np.zeros((4, 4)),
        np.ones((4, 4)),
        np.diag([1e-300, 1e300, 1.0, 0.0]),
        np.outer(np.array([0.5, 1.0, 2.0, 4.0]), np.array([0.5, 1.0, 2.0, 4.0])),
    ],
)
def test_exactly_psd_inputs_are_returned_unchanged_as_a_copy(covariance):
    validated = _psd_covariance(covariance)
    assert np.array_equal(validated, covariance)
    assert not np.shares_memory(validated, covariance)


def test_invalid_small_block_cannot_be_hidden_by_large_other_units():
    invalid = np.eye(4)
    invalid[0, 1] = invalid[1, 0] = 1.0001
    units = np.diag([1e-150, 1e-150, 1e150, 1e150])
    with pytest.raises(InputRejected):
        project(units @ invalid @ units)


def test_wrapper_policy_label_reaches_bounded_and_weak_denominator_results():
    bounded = project(np.eye(4) * 0.01)
    weak = project(np.eye(4) * 0.01, theta=(2.0, 0.0, 1.0, 5.0))
    assert bounded["kind"] == "BOUNDED_INTERVAL"
    assert weak["kind"] == "ALL_REAL"
    for result in (bounded, weak):
        assert result["covariance_input_policy"] == (
            "EXACT_RATIONAL_PRINCIPAL_MINORS_OF_BINARY_FLOATS_NO_REPAIR"
        )


def test_score_helper_uses_wrapped_validation_and_keeps_cross_products():
    scores = np.array([[1.0, 2.0, 4.0, 8.0], [-1.0, 0.0, 2.0, -2.0]])
    result = joint_covariance_from_event_score_sums(scores)
    assert np.array_equal(np.asarray(result["joint_covariance"]), scores.T @ scores)
    assert result["cluster_count"] == 2
    assert "NOT_ESTIMATED_EMPIRICAL_PIPELINE_ABSENT" in result["covariance_status"]


def test_random_points_from_valid_ellipsoid_remain_enclosed():
    covariance = np.array(
        [
            [0.16, 0.08, 0.06, -0.02],
            [0.08, 0.25, -0.04, 0.03],
            [0.06, -0.04, 0.36, 0.09],
            [-0.02, 0.03, 0.09, 0.49],
        ]
    )
    q = 5.0
    result = project(covariance, q=q)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    factor = eigenvectors @ np.diag(np.sqrt(eigenvalues))
    rng = np.random.default_rng(9212026)
    for _ in range(1000):
        direction = rng.normal(size=4)
        direction /= np.linalg.norm(direction)
        point = np.array([2.0, 4.0, 1.0, 5.0]) + factor @ direction * np.sqrt(q) * rng.random() ** 0.25
        contrast = point[0] / point[1] - point[2] / point[3]
        assert result["interval"][0] <= contrast <= result["interval"][1]
