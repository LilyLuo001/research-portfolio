"""Synthetic checks only; no empirical inputs are read."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from estimator import InputRejected, joint_covariance_from_event_score_sums, ratio_contrast_outer_bound


def expect_rejected(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except InputRejected:
        return
    raise AssertionError("expected InputRejected")


def contains_interval(result, value):
    return result["interval"][0] - 1e-12 <= value <= result["interval"][1] + 1e-12


def main():
    passed = []
    theta = np.array([2.0, 4.0, 1.0, 5.0])
    cov = np.array([[.16, .08, .06, -.02], [.08, .25, -.04, .03],
                    [.06, -.04, .36, .09], [-.02, .03, .09, .49]])
    q = 5.0
    result = ratio_contrast_outer_bound(theta, cov, joint_critical_squared=q,
                                        calibration_status="SYNTHETIC_CALLER_CALIBRATED_Q")
    assert result["kind"] == "BOUNDED_INTERVAL"
    assert result["coordinate_box"]["k_TOP"][0] > 0
    passed.append("correlated_covariance_bounded")

    # Points parameterized in the actual correlated ellipsoid must be enclosed.
    rng = np.random.default_rng(20260921)
    A = np.linalg.cholesky(cov)
    for _ in range(2000):
        direction = rng.normal(size=4)
        direction /= np.linalg.norm(direction)
        point = theta + A @ direction * np.sqrt(q) * rng.random() ** .25
        value = point[0] / point[1] - point[2] / point[3]
        assert contains_interval(result, value)
    passed.append("random_ellipsoid_points_enclosed")

    weak = ratio_contrast_outer_bound([1, .1, 1, 2], np.diag([.01, .01, .01, .01]),
                                      joint_critical_squared=4, calibration_status="SYNTHETIC_Q")
    assert weak["kind"] == "ALL_REAL"
    passed.append("weak_denominator_all_real")

    # Negative, but bounded-away-from-zero denominators are supported.
    negative = ratio_contrast_outer_bound([2, -4, 1, -3], np.diag([.04, .04, .04, .04]),
                                          joint_critical_squared=1, calibration_status="SYNTHETIC_Q")
    assert negative["kind"] == "BOUNDED_INTERVAL"
    passed.append("negative_denominators")

    # Each group's N and k can be expressed in a different common unit.
    scale = np.array([10., 10., .3, .3])
    scaled = ratio_contrast_outer_bound(theta * scale, (scale[:, None] * cov) * scale[None, :],
                                        joint_critical_squared=q, calibration_status="SYNTHETIC_CALLER_CALIBRATED_Q")
    assert np.allclose(result["interval"], scaled["interval"])
    passed.append("groupwise_common_unit_scaling_invariance")

    singular = ratio_contrast_outer_bound(theta, np.outer([.2, .1, .3, .4], [.2, .1, .3, .4]),
                                           joint_critical_squared=q, calibration_status="SYNTHETIC_RANK_ONE_Q")
    assert singular["kind"] == "BOUNDED_INTERVAL"
    passed.append("singular_psd_covariance_supported")

    scores = np.array([[1., 2., 3., 4.], [-1., 0., 2., -2.], [2., -1., 0., 1.]])
    score_cov = joint_covariance_from_event_score_sums(scores)
    assert score_cov["joint_covariance"][0][2] != 0
    assert "NOT_ESTIMATED" in score_cov["covariance_status"]
    passed.append("joint_event_score_covariance_interface")

    expect_rejected(ratio_contrast_outer_bound, theta, np.full((4, 4), np.nan),
                    joint_critical_squared=q, calibration_status="x")
    expect_rejected(ratio_contrast_outer_bound, theta, np.diag([1, 1, 1, -1]),
                    joint_critical_squared=q, calibration_status="x")
    expect_rejected(ratio_contrast_outer_bound, theta, np.diag([-1e-12, 1e-12, 1e-12, 1e-12]),
                    joint_critical_squared=q, calibration_status="x")
    invalid_block = np.eye(4)
    invalid_block[:2, :2] = [[1., 1.0001], [1.0001, 1.]]
    heterogeneous = np.diag([1e-6, 1e-6, 1., 1.])
    expect_rejected(ratio_contrast_outer_bound, theta, heterogeneous @ invalid_block @ heterogeneous,
                    joint_critical_squared=q, calibration_status="x")
    asymmetric = np.eye(4)
    asymmetric[0, 1] = .1
    expect_rejected(ratio_contrast_outer_bound, theta, heterogeneous @ asymmetric @ heterogeneous,
                    joint_critical_squared=q, calibration_status="x")
    zero_variance_cross = np.diag([0., 1., 1., 1.])
    zero_variance_cross[0, 1] = zero_variance_cross[1, 0] = 1e-100
    expect_rejected(ratio_contrast_outer_bound, theta, zero_variance_cross,
                    joint_critical_squared=q, calibration_status="x")
    # Finite extreme inputs must be rejected cleanly, rather than overflow in
    # eigensystem or interval arithmetic and emit non-finite JSON.
    extreme = ratio_contrast_outer_bound(theta, np.diag([1e308, 1e308, 1e308, 1e308]),
                                         joint_critical_squared=1e308, calibration_status="x")
    assert extreme["kind"] == "ALL_REAL"
    assert np.all(np.isfinite(np.asarray(list(extreme["coordinate_box"].values()))))
    expect_rejected(ratio_contrast_outer_bound, [1e308, 1e-308, 1, 2], np.zeros((4, 4)),
                    joint_critical_squared=q, calibration_status="x")
    expect_rejected(ratio_contrast_outer_bound, theta, cov, joint_critical_squared=q, calibration_status="")
    passed.append("nonfinite_nonpsd_overflow_and_missing_calibration_rejected")

    payload = {"status": "SYNTHETIC_ONLY", "passed": passed, "count": len(passed),
               "source_sha256": hashlib.sha256(Path(__file__).with_name("estimator.py").read_bytes()).hexdigest()}
    Path(__file__).with_name("SYNTHETIC_TEST_RESULTS.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"{len(passed)} / {len(passed)} passed")


if __name__ == "__main__":
    main()
