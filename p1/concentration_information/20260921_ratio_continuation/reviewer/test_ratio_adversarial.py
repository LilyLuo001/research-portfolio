"""Independent finite/adversarial checks for the proposed ratio projection."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest


METHOD = Path(__file__).resolve().parents[1] / "method"
sys.path.insert(0, str(METHOD))

from estimator import (  # noqa: E402
    InputRejected,
    joint_covariance_from_event_score_sums,
    ratio_contrast_outer_bound,
)


THETA = np.array([2.0, 4.0, 1.0, 5.0])
Q = 5.0
CALIBRATION = "SYNTHETIC_CALLER_DECLARATION_ONLY"


def project(theta=THETA, covariance=None, q=Q, calibration=CALIBRATION):
    if covariance is None:
        covariance = np.diag([0.16, 0.25, 0.36, 0.49])
    return ratio_contrast_outer_bound(
        theta,
        covariance,
        joint_critical_squared=q,
        calibration_status=calibration,
    )


def contains(result, value):
    return result["interval"][0] <= value <= result["interval"][1]


def test_random_points_from_one_correlated_ellipsoid_are_enclosed():
    covariance = np.array(
        [
            [0.16, 0.08, 0.06, -0.02],
            [0.08, 0.25, -0.04, 0.03],
            [0.06, -0.04, 0.36, 0.09],
            [-0.02, 0.03, 0.09, 0.49],
        ]
    )
    result = project(covariance=covariance)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    factor = eigenvectors @ np.diag(np.sqrt(np.maximum(eigenvalues, 0.0)))
    rng = np.random.default_rng(9212026)
    for _ in range(3000):
        direction = rng.normal(size=4)
        direction /= np.linalg.norm(direction)
        radius = rng.random() ** 0.25
        point = THETA + factor @ direction * np.sqrt(Q) * radius
        contrast = point[0] / point[1] - point[2] / point[3]
        assert contains(result, contrast)


def test_singular_ellipsoid_support_points_are_enclosed():
    loading = np.array([0.2, -0.1, 0.3, 0.15])
    covariance = np.outer(loading, loading)
    result = project(covariance=covariance)
    for scalar in np.linspace(-np.sqrt(Q), np.sqrt(Q), 501):
        point = THETA + loading * scalar
        contrast = point[0] / point[1] - point[2] / point[3]
        assert contains(result, contrast)


def test_same_diagonal_different_dependence_does_not_tighten_box():
    diagonal = np.diag([0.01, 0.01, 0.01, 0.01])
    loading = np.array([0.1, -0.1, 0.1, -0.1])
    correlated = np.outer(loading, loading)
    first = project(covariance=diagonal, q=1.0)
    second = project(covariance=correlated, q=1.0)
    assert first["coordinate_box"] == second["coordinate_box"]
    assert first["interval"] == second["interval"]
    assert "does not tighten" in first["dependence_note"]


def test_required_joint_q_and_calibration_declaration():
    covariance = np.eye(4)
    for bad_q in (0.0, -1.0, np.nan, np.inf):
        with pytest.raises(InputRejected):
            project(covariance=covariance, q=bad_q)
    for bad_status in ("", "   ", None, 7):
        with pytest.raises(InputRejected):
            project(covariance=covariance, calibration=bad_status)


def test_zero_touching_denominator_is_only_a_conservative_fallback():
    result = project(theta=[1.0, 0.1, 1.0, 2.0], covariance=np.diag([0.01] * 4), q=1.0)
    assert result["kind"] == "ALL_REAL"
    assert "conservative fallback" in result["reason"]
    assert "undefined" in result["estimand_note"]


def test_zero_covariance_and_negative_nonzero_denominators_are_supported():
    point = project(covariance=np.zeros((4, 4)), q=1.0)
    assert point["kind"] == "BOUNDED_INTERVAL"
    assert np.allclose(point["interval"], [0.3, 0.3])
    negative = project(theta=[2.0, -4.0, 1.0, -5.0], covariance=np.zeros((4, 4)), q=1.0)
    assert negative["kind"] == "BOUNDED_INTERVAL"
    assert np.allclose(negative["interval"], [-0.3, -0.3])


@pytest.mark.parametrize(
    "covariance",
    [
        np.diag([-1e-12, 1e-12, 1e-12, 1e-12]),
        np.array(
            [
                [1e-12, 1.0001e-12, 0.0, 0.0],
                [1.0001e-12, 1e-12, 0.0, 0.0],
                [0.0, 0.0, 1e-12, 0.0],
                [0.0, 0.0, 0.0, 1e-12],
            ]
        ),
    ],
)
def test_invalid_psd_is_rejected_even_at_small_units(covariance):
    with pytest.raises(InputRejected):
        project(covariance=covariance, q=1.0)
    with pytest.raises(InputRejected):
        project(covariance=covariance * 1e12, q=1.0)


def test_asymmetry_rejection_is_scale_invariant():
    covariance = np.array(
        [
            [1e-12, 1e-13, 0.0, 0.0],
            [0.0, 1e-12, 0.0, 0.0],
            [0.0, 0.0, 1e-12, 0.0],
            [0.0, 0.0, 0.0, 1e-12],
        ]
    )
    with pytest.raises(InputRejected):
        project(covariance=covariance, q=1.0)
    with pytest.raises(InputRejected):
        project(covariance=covariance * 1e12, q=1.0)


def test_invalid_small_block_cannot_be_hidden_by_other_group_units():
    indefinite = np.array(
        [
            [1.0, 1.0001, 0.0, 0.0],
            [1.0001, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )
    asymmetric = np.eye(4)
    asymmetric[0, 1] = 0.1
    units = np.diag([1e-6, 1e-6, 1.0, 1.0])
    for invalid in (indefinite, asymmetric):
        with pytest.raises(InputRejected):
            project(covariance=invalid, q=1.0)
        with pytest.raises(InputRejected):
            project(covariance=units @ invalid @ units, q=1.0)


def test_near_indefinite_matrix_is_not_treated_as_an_existing_ellipsoid():
    covariance = np.eye(4)
    covariance[0, 1] = covariance[1, 0] = 1.0 + 5e-11
    assert np.linalg.eigvalsh(covariance).min() < 0.0
    with pytest.raises(InputRejected):
        project(covariance=covariance, q=1.0)


def test_extreme_finite_geometry_never_emits_nonfinite_bounded_output():
    with np.errstate(over="ignore", invalid="ignore"):
        extreme = project(covariance=np.diag([1e308] * 4), q=1e308)
        assert extreme["kind"] == "ALL_REAL"
        assert np.all(np.isfinite(np.array(list(extreme["coordinate_box"].values()))))
        with pytest.raises(InputRejected):
            project(theta=[1e308, 1e-308, 1.0, 2.0], covariance=np.zeros((4, 4)), q=1.0)


def test_groupwise_common_unit_scaling_preserves_interval():
    covariance = np.array(
        [
            [0.16, 0.08, 0.06, -0.02],
            [0.08, 0.25, -0.04, 0.03],
            [0.06, -0.04, 0.36, 0.09],
            [-0.02, 0.03, 0.09, 0.49],
        ]
    )
    original = project(covariance=covariance)
    scale = np.array([1e-6, 1e-6, 1e6, 1e6])
    scaled = project(theta=THETA * scale, covariance=scale[:, None] * covariance * scale[None, :])
    assert np.allclose(original["interval"], scaled["interval"], rtol=1e-12, atol=1e-12)


def test_score_helper_is_only_supplied_joint_influence_cross_products():
    scores = np.array([[1.0, 2.0, 3.0, 4.0], [-1.0, 0.0, 2.0, -2.0], [2.0, -1.0, 0.0, 1.0]])
    multiplier = 1.25
    result = joint_covariance_from_event_score_sums(scores, small_sample_multiplier=multiplier)
    assert np.allclose(result["joint_covariance"], multiplier * scores.T @ scores)
    assert result["coefficient_order"] == ["N_TOP", "k_TOP", "N_REST", "k_REST"]
    assert "NOT_ESTIMATED_EMPIRICAL_PIPELINE_ABSENT" in result["covariance_status"]
    assert result["cluster_count"] == len(scores)


def test_score_helper_rejects_incomplete_or_nonfinite_inputs():
    for bad in (np.ones((1, 4)), np.ones((2, 3)), [[1, 2, 3, np.nan], [1, 2, 3, 4]]):
        with pytest.raises(InputRejected):
            joint_covariance_from_event_score_sums(bad)
    for bad_multiplier in (0, -1, np.nan, np.inf):
        with pytest.raises(InputRejected):
            joint_covariance_from_event_score_sums(np.ones((2, 4)), small_sample_multiplier=bad_multiplier)
