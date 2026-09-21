"""Independent algebra and guard checks for the bounded synthetic method."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest


METHOD = Path(__file__).resolve().parents[1] / "method"
sys.path.insert(0, str(METHOD))

from estimator import (  # noqa: E402
    InputRejected,
    PairedQuote,
    composition_decomposition,
    fieller_set,
    fixed_common_support_weights,
    fit_joint_standardized_slopes,
    paired_response,
)


def test_pairing_rejects_displaced_instrument_windows():
    etf = PairedQuote(100, 101, 102, True, True, True, (0, 0), (2, 2), (4, 4))
    basket = PairedQuote(100, 101, 102, True, True, True, (100, 100), (102, 102), (104, 104))
    with pytest.raises(InputRejected):
        paired_response(etf, basket, actual_basket=True, basket_kind="ACTUAL_HOLDINGS", quote_side="mid")


def test_x_is_weight_times_signal_and_linear_standardization_is_recovered():
    # Vary w independently of z: the fitted outcome is generated from x=w*z,
    # so passing z would target a visibly different coefficient.
    z_event = np.array([-2.0, -1.0, 1.0, 2.0, -1.5, -0.5, 0.5, 1.5])
    issuer_weight_event = np.array([0.10, 0.25, 0.40, 0.55, 0.15, 0.30, 0.45, 0.60])
    x_event = issuer_weight_event * z_event
    x = np.repeat(x_event, 2)
    z = np.repeat(z_event, 2)
    event_ids = np.repeat([f"e{k}" for k in range(8)], 2)
    cells = np.repeat(["low"] * 4 + ["high"] * 4, 2)
    y = np.column_stack([0.7 * x, 0.2 * x, 1.0 * x, 1.0 * x])
    kwargs = {
        "cell_ids": cells,
        "fstar_cells": ("low", "high"),
        "standardization_cell_weights": {"low": 0.25, "high": 0.75},
    }
    result_x = fit_joint_standardized_slopes(
        x, y, np.repeat(1 / len(x), len(x)), event_ids, **kwargs
    )
    result_z = fit_joint_standardized_slopes(
        z, y, np.repeat(1 / len(z), len(z)), event_ids, **kwargs
    )
    assert np.allclose(result_x["slopes"], [0.7, 0.2, 1.0, 1.0])
    assert np.isclose(result_x["early_difference"], 0.5)
    assert np.isclose(result_x["terminal_response"], 1.0)
    assert not np.allclose(result_z["slopes"], result_x["slopes"])


def test_event_cluster_covariance_matches_independent_sandwich_reconstruction():
    x_event = np.array([-2.0, -0.7, 0.8, 1.9, -1.8, -0.6, 0.9, 2.1])
    x = np.repeat(x_event, 2)
    event_ids = np.repeat([f"cluster{k}" for k in range(8)], 2)
    cells = np.repeat(["low"] * 4 + ["high"] * 4, 2)
    row_noise = np.column_stack([
        np.sin(np.arange(len(x))),
        np.cos(np.arange(len(x))),
        (-1.0) ** np.arange(len(x)),
        np.linspace(-0.3, 0.3, len(x)),
    ]) * 0.03
    y = np.column_stack([0.7 * x, 0.2 * x, x, x]) + row_noise
    weights = np.repeat(1 / len(x), len(x))
    result = fit_joint_standardized_slopes(
        x,
        y,
        weights,
        event_ids,
        cell_ids=cells,
        fstar_cells=("low", "high"),
        standardization_cell_weights={"low": 0.4, "high": 0.6},
    )

    raw = np.zeros((len(x), 4))
    for k, cell in enumerate(("low", "high")):
        mask = cells == cell
        raw[mask, 2 * k] = 1.0
        raw[mask, 2 * k + 1] = x[mask]
    design = raw * np.sqrt(weights)[:, None]
    wy = y * np.sqrt(weights)[:, None]
    inv = np.linalg.inv(design.T @ design)
    beta = inv @ design.T @ wy
    residual = wy - design @ beta
    scores = {}
    for row, error, cluster in zip(design, residual, event_ids):
        leverage = inv @ row
        scores.setdefault(cluster, np.zeros(8))
        scores[cluster] += np.concatenate([leverage[1] * error, leverage[3] * error])
    cluster_cov = sum(np.outer(score, score) for score in scores.values()) * 8 / 7
    standardizer = np.zeros((4, 8))
    standardizer[:, :4] = np.eye(4) * 0.4
    standardizer[:, 4:] = np.eye(4) * 0.6
    assert np.allclose(result["cell_specific_joint_covariance"], cluster_cov)
    assert np.allclose(result["joint_covariance"], standardizer @ cluster_cov @ standardizer.T)


def test_etf_within_event_then_events_within_issuer_weight_order():
    rows = [
        {"cell": "c", "group": "TOP", "issuer_id": "A", "event_id": "a0", "etf_id": "E1"},
        {"cell": "c", "group": "TOP", "issuer_id": "A", "event_id": "a0", "etf_id": "E2"},
        {"cell": "c", "group": "TOP", "issuer_id": "A", "event_id": "a1", "etf_id": "E1"},
        {"cell": "c", "group": "TOP", "issuer_id": "A", "event_id": "a1", "etf_id": "E2"},
        {"cell": "c", "group": "TOP", "issuer_id": "B", "event_id": "b0", "etf_id": "E1"},
    ]
    weights = fixed_common_support_weights(
        rows,
        fstar_cells=("c",),
        groups=("TOP",),
        issuer_weights={("c", "TOP"): {"A": 0.6, "B": 0.4}},
        event_etf_weights={
            ("c", "TOP", "a0"): {"E1": 0.25, "E2": 0.75},
            ("c", "TOP", "a1"): {"E1": 0.80, "E2": 0.20},
            ("c", "TOP", "b0"): {"E1": 1.0},
        },
    )
    assert np.allclose(weights, [0.075, 0.225, 0.24, 0.06, 0.4])
    assert np.isclose(sum(weights[:4]), 0.6)
    assert np.isclose(weights.sum(), 1.0)


def test_symmetric_composition_identity_randomized():
    rng = np.random.default_rng(20260921)
    for _ in range(20):
        p0 = rng.dirichlet(np.ones(5))
        p1 = rng.dirichlet(np.ones(5))
        d0 = rng.normal(size=5)
        d1 = rng.normal(size=5)
        result = composition_decomposition(p0, p1, d0, d1)
        assert np.isclose(
            result["total_change"],
            result["within_response_change"] + result["composition_change"],
        )


@pytest.mark.parametrize(
    ("n", "d", "cov", "kind"),
    [
        (1.0, 2.0, [[0.01, 0.0], [0.0, 0.01]], "BOUNDED"),
        (0.05, 0.0, [[0.01, 0.0], [0.0, 0.01]], "ALL_REAL"),
        (2.0, 0.1, [[0.01, 0.0], [0.0, 0.01]], "TWO_UNBOUNDED_RAYS"),
    ],
)
def test_fieller_shapes_against_direct_quadratic(n, d, cov, kind):
    result = fieller_set(n, d, cov)
    assert result["kind"] == kind


def _fieller_contains(result, value):
    if result["kind"] == "ALL_REAL":
        return True
    if result["kind"] == "EMPTY":
        return False
    if result["kind"] == "BOUNDED":
        return result["boundaries"][0] <= value <= result["boundaries"][1]
    if result["kind"] == "TWO_UNBOUNDED_RAYS":
        return value <= result["boundaries"][0] or value >= result["boundaries"][1]
    if result["kind"] == "HALF_LINE":
        return value <= result["boundary"] if result["direction"] == "LE" else value >= result["boundary"]
    raise AssertionError(result)


def test_fieller_set_matches_direct_test_inversion_randomized():
    rng = np.random.default_rng(20260922)
    critical = 1.96
    for _ in range(50):
        n, d = rng.normal(size=2)
        factor = rng.normal(size=(2, 2))
        cov = (factor @ factor.T) * 0.05
        result = fieller_set(n, d, cov, critical=critical)
        for ratio in np.linspace(-20, 20, 161):
            contrast = n - ratio * d
            variance = cov[0, 0] - 2 * ratio * cov[0, 1] + ratio * ratio * cov[1, 1]
            quadratic = contrast * contrast - critical * critical * variance
            if abs(quadratic) > 1e-9:  # avoid floating-point boundary ties
                assert _fieller_contains(result, ratio) == (quadratic <= 0)
