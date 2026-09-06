#!/usr/bin/env python3
"""Unit tests for pure architecture-audit construction helpers."""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import numpy as np


HERE = pathlib.Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("yax_r3_architecture_tested", HERE / "run_architecture.py")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_eloundou_primitive_identity():
    direct = np.array([0.0, 0.2, 0.8])
    broad = np.array([0.4, 0.8, 1.0])
    software = broad - direct
    beta = (direct + broad) / 2
    np.testing.assert_allclose(direct + 0.5 * software, beta, atol=0, rtol=0)


def test_common_draw_paired_contrast_preserves_covariance():
    left = np.array([1.0, -1.0, 2.0, -2.0])
    right = np.array([0.5, -0.5, 1.0, -1.0])
    result = MODULE.infer_contrast("left", "right", 0.2, 0.1, left, right, "test")
    assert result["coefficient_difference"] == 0.1
    assert np.isclose(result["paired_bootstrap_se"], np.std(left - right, ddof=1))
    assert result["common_multiplier_draws"] is True
    assert result["mde80_difference"] > 0


def test_tail_transition_accounting_conserves_occupations_and_weight():
    support = [f"{value:04d}" for value in range(10)]
    names = {code: code for code in support}
    weights = np.arange(1, 11, dtype=float)
    groups = {
        0.0: np.array([1, 1, 2, 2, 3, 3, 4, 4, 5, 5]),
        0.25: np.array([1, 2, 1, 2, 3, 4, 3, 4, 5, 5]),
        0.5: np.array([1, 2, 2, 1, 3, 4, 4, 3, 5, 5]),
        0.75: np.array([2, 1, 2, 1, 3, 4, 4, 3, 5, 5]),
        1.0: np.array([2, 1, 2, 1, 4, 3, 4, 3, 5, 5]),
    }
    transitions, overlaps, named = MODULE.tail_diagnostics(support, names, weights, groups)
    assert len(transitions) == 250
    assert len(overlaps) == 10
    first = [row for row in transitions if row["left_lambda"] == 0.0 and row["right_lambda"] == 0.25]
    assert sum(row["occupation_count"] for row in first) == len(support)
    assert np.isclose(sum(row["preperiod_employment_weight"] for row in first), weights.sum())
    assert named


def test_raw_and_standardized_one_sd_contrast_algebra():
    raw_beta = np.array([2.0, -3.0, 0.5])
    d_sd, s_sd = 0.2, 0.4
    standardized_beta = np.array([raw_beta[0] * d_sd, raw_beta[1] * s_sd, raw_beta[2]])
    raw_contrast = np.array([d_sd, s_sd, 0.0])
    standardized_contrast = np.array([1.0, 1.0, 0.0])
    assert np.isclose(raw_contrast @ raw_beta, standardized_contrast @ standardized_beta)
