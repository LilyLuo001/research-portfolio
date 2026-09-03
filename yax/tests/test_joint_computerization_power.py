import importlib.util
import pathlib
import sys

import numpy as np


ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "power" / "joint_computerization_power.py"
SPEC = importlib.util.spec_from_file_location("joint_computerization_power", PATH)
P = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = P
SPEC.loader.exec_module(P)


def test_v5_static_post_window_excludes_transition_and_known_gap():
    months = P.planned_post_months()
    assert months[0] == "2023-01"
    assert months[-1] == "2026-07"
    assert "2022-12" not in months
    assert "2025-10" not in months


def test_weighted_scale_centers_and_standardizes():
    values = np.array([1.0, 2.0, 4.0])
    weights = np.array([1.0, 2.0, 1.0])
    mean, sd = P.weighted_scale(values, weights)
    z = (values - mean) / sd
    assert abs(np.sum(weights * z)) < 1e-12
    assert abs(np.sum(weights * z * z) / weights.sum() - 1) < 1e-12


def test_weighted_quintiles_preserve_ties_and_all_five_bins():
    values = np.repeat(np.arange(1.0, 6.0), 2)
    quintiles = P.weighted_quintiles(values, np.ones(10))
    assert set(quintiles) == {1, 2, 3, 4, 5}
    for value in np.unique(values):
        assert len(set(quintiles[values == value])) == 1


def test_mde_interpolation_crosses_inside_grid():
    rows = [
        {"true_log_effect": -0.01, "rejection_probability_zero": 0.2},
        {"true_log_effect": -0.05, "rejection_probability_zero": 0.7},
        {"true_log_effect": -0.10, "rejection_probability_zero": 0.9},
    ]
    value = P.interpolate_mde(rows)
    assert 1 - np.exp(-0.05) < value < 1 - np.exp(-0.10)
