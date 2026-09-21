"""Synthetic-only conservative projection for a joint ratio contrast.

This module does not estimate responses or calibrate a confidence region.  It
only maps a *caller-supplied*, simultaneous four-coefficient Wald ellipsoid to
a conservative outer interval for ``N_TOP/k_TOP - N_REST/k_REST``.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np


class InputRejected(ValueError):
    """Raised when a proposed joint-region input is invalid or incomplete."""


ORDER = ("N_TOP", "k_TOP", "N_REST", "k_REST")
NOT_ESTIMATED = "NOT_ESTIMATED_EMPIRICAL_PIPELINE_ABSENT"


def _finite_array(value: Any, name: str, ndim: int) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.ndim != ndim or not np.all(np.isfinite(array)):
        raise InputRejected(f"{name} must be a finite {ndim}-D numeric array")
    return array


def _psd_covariance(value: Any, name: str = "joint_covariance") -> np.ndarray:
    covariance = _finite_array(value, name, 2)
    if covariance.shape != (4, 4):
        raise InputRejected(f"{name} must have shape (4, 4) in ORDER")
    diagonal = np.diag(covariance)
    if np.any(diagonal < 0.0):
        raise InputRejected(f"{name} has a negative diagonal variance")
    positive = diagonal > 0.0
    # A PSD zero-variance coordinate has zero covariance with every coordinate.
    # This explicit rule also avoids division by zero in correlation units.
    for index in np.flatnonzero(~positive):
        if np.any(covariance[index, :] != 0.0) or np.any(covariance[:, index] != 0.0):
            raise InputRejected(f"{name} has nonzero covariance for a zero-variance coordinate")
    if not np.any(positive):
        return covariance
    # Congruence-normalize by each coordinate's standard deviation, rather than
    # a global matrix scale: this makes symmetry and PSD decisions invariant to
    # heterogeneous coefficient units and prevents extreme finite entries from
    # overflowing eigensystem arithmetic.
    roots = np.sqrt(diagonal[positive])
    normalized = covariance[np.ix_(positive, positive)] / np.outer(roots, roots)
    if not np.allclose(normalized, normalized.T, atol=1e-12, rtol=1e-12):
        raise InputRejected(f"{name} must be symmetric")
    normalized = (normalized + normalized.T) / 2.0
    # Correlation-scale eigensystem is stable for finite, nonzero variances.
    if not np.all(np.isfinite(normalized)) or float(np.linalg.eigvalsh(normalized).min()) < -1e-10:
        raise InputRejected(f"{name} must be positive semidefinite")
    # Returning the original finite input avoids a potentially overflowing
    # covariance + covariance.T reconstruction.  Later arithmetic is guarded.
    return covariance


def joint_covariance_from_event_score_sums(event_score_sums: Any, *,
                                           small_sample_multiplier: float = 1.0) -> dict[str, Any]:
    """Form a synthetic cluster-score covariance for all four coefficients.

    ``event_score_sums[g, :]`` must already be the joint coefficient influence
    (including any bread transformation) summed within event ``g``.  Thus the
    cross-group/shared-news covariance is retained in off-diagonal products.
    This helper is deliberately not an empirical covariance pipeline: it does
    not construct scores, choose clusters, or calibrate a critical value.
    """
    scores = _finite_array(event_score_sums, "event_score_sums", 2)
    if scores.shape[1:] != (4,) or scores.shape[0] < 2:
        raise InputRejected("at least two event score sums with four coefficients are required")
    if not np.isfinite(small_sample_multiplier) or small_sample_multiplier <= 0:
        raise InputRejected("small_sample_multiplier must be finite and positive")
    covariance = small_sample_multiplier * scores.T @ scores
    return {
        "joint_covariance": _psd_covariance(covariance, "score covariance").tolist(),
        "coefficient_order": list(ORDER),
        "covariance_status": "SYNTHETIC_EVENT_SCORE_SUMS_ONLY; " + NOT_ESTIMATED,
        "cluster_count": int(scores.shape[0]),
    }


def _ratio_bounds(numerator: tuple[float, float], denominator: tuple[float, float]) -> tuple[float, float]:
    limit = np.finfo(float).max
    values = []
    for n in numerator:
        for d in denominator:
            # Test before division so valid inputs never create an overflow
            # warning or a non-finite transient result.
            if n != 0.0 and abs(n) / limit > abs(d):
                raise InputRejected("ratio interval arithmetic exceeds supported finite floating-point range")
            value = n / d
            if not np.isfinite(value):
                raise InputRejected("ratio interval arithmetic exceeds supported finite floating-point range")
            values.append(value)
    return float(min(values)), float(max(values))


def ratio_contrast_outer_bound(theta_hat: Sequence[float], joint_covariance: Any, *,
                               joint_critical_squared: float,
                               calibration_status: str) -> dict[str, Any]:
    """Conservatively project one supplied joint Wald ellipsoid.

    The required ellipsoid is ``{theta_hat + A u: ||u||^2 <= q}``, where
    ``A A' = joint_covariance`` and ``q = joint_critical_squared``.  Coordinate
    ranges from that *single* region are theta_i +/- sqrt(q V_ii).  Their box
    contains the ellipsoid.  When both denominator ranges avoid zero, interval
    arithmetic maps the box to an outer interval for the contrast.  The result
    is therefore conservative and not an exact Fieller inversion.

    There is intentionally no normal-95 default.  ``calibration_status`` is a
    caller declaration, not evidence that covariance, clustering, or q is valid.
    """
    theta = _finite_array(theta_hat, "theta_hat", 1)
    if theta.shape != (4,):
        raise InputRejected("theta_hat must contain four coefficients in ORDER")
    covariance = _psd_covariance(joint_covariance)
    q = float(joint_critical_squared)
    if not np.isfinite(q) or q <= 0:
        raise InputRejected("joint_critical_squared must be finite and positive; no default is supplied")
    if not isinstance(calibration_status, str) or not calibration_status.strip():
        raise InputRejected("a nonempty caller-supplied calibration_status is required")

    diagonal = np.diag(covariance)
    # A PSD covariance cannot have a negative variance, including at a tiny
    # scale; do not clip one away.  Normalize only for validation above.
    if np.any(diagonal < 0):
        raise InputRejected("joint_covariance has a negative diagonal variance")
    root_q, root_diagonal = np.sqrt(q), np.sqrt(diagonal)
    limit = np.finfo(float).max
    if any(value != 0.0 and np.log(root_q) + np.log(value) > np.log(limit)
           for value in root_diagonal.tolist()):
        raise InputRejected("joint-region coordinate radii exceed supported finite floating-point range")
    radii = root_q * root_diagonal
    if not np.all(np.isfinite(radii)):
        raise InputRejected("joint-region coordinate radii exceed supported finite floating-point range")
    if np.any(radii > limit - np.abs(theta)):
        raise InputRejected("joint-region coordinate enclosure exceeds supported finite floating-point range")
    coordinate_box = np.column_stack((theta - radii, theta + radii))
    if not np.all(np.isfinite(coordinate_box)):
        raise InputRejected("joint-region coordinate enclosure exceeds supported finite floating-point range")
    top_denominator = tuple(coordinate_box[1])
    rest_denominator = tuple(coordinate_box[3])
    common = {
        "status": "PROPOSED_CONSERVATIVE_OUTER_BOUND",
        "coefficient_order": list(ORDER),
        "joint_critical_squared": q,
        "calibration_status": calibration_status,
        "covariance_status": "CALLER_SUPPLIED; " + NOT_ESTIMATED,
        "coordinate_box": {name: [float(a), float(b)] for name, (a, b) in zip(ORDER, coordinate_box)},
        "method": "ONE_JOINT_4_COEFFICIENT_ELLIPSOID_TO_AXIS_ALIGNED_BOX_INTERVAL_ARITHMETIC",
        "dependence_note": "Off-diagonal covariance is retained in the supplied joint region but does not tighten this box outer bound.",
        "not_exact_fieller_difference": True,
    }
    if top_denominator[0] <= 0 <= top_denominator[1] or rest_denominator[0] <= 0 <= rest_denominator[1]:
        return common | {
            "kind": "ALL_REAL",
            "reason": "A denominator coordinate enclosure touches zero; returned as conservative fallback.",
            "estimand_note": "A true zero denominator makes the ratio estimand undefined, not zero.",
        }
    top = _ratio_bounds(tuple(coordinate_box[0]), top_denominator)
    rest = _ratio_bounds(tuple(coordinate_box[2]), rest_denominator)
    interval = [float(top[0] - rest[1]), float(top[1] - rest[0])]
    if not np.all(np.isfinite(interval)):
        raise InputRejected("contrast interval arithmetic exceeds supported finite floating-point range")
    return common | {
        "kind": "BOUNDED_INTERVAL",
        "interval": interval,
        "top_ratio_box_interval": list(top),
        "rest_ratio_box_interval": list(rest),
        "validity": "Conditional on valid simultaneous coverage of the caller-supplied joint ellipsoid and nonzero true denominators.",
    }
