from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "yax_gate3_hac_validation", HERE / "run_hac_validation.py")
HAC = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = HAC
spec.loader.exec_module(HAC)


def test_elapsed_calendar_inserts_both_actual_gaps():
    months = ["2022-11", "2023-01", "2025-09", "2025-11"]
    full, positions = HAC.full_calendar_positions(months)
    assert "2022-12" in full and "2025-10" in full
    assert np.array_equal(np.diff(positions), np.asarray([2, 32, 2]))


def test_newey_west_includes_positive_and_negative_lag_cross_products():
    scores = np.asarray([[1.0], [2.0], [4.0]])
    observed = HAC.newey_west_meat(scores, 1)[0, 0]
    expected = 1 + 4 + 16 + 2 * .5 * (2 * 1 + 4 * 2)
    assert observed == expected


def test_lag_zero_is_two_way_cluster_inclusion_exclusion():
    cube = np.asarray([
        [[1.0], [2.0]],
        [[3.0], [5.0]],
    ])
    result = HAC.covariance_components(cube, ["2023-01", "2023-02"], 0)
    occupation = (1 + 2) ** 2 + (3 + 5) ** 2
    time = (1 + 3) ** 2 + (2 + 5) ** 2
    intersection = 1 ** 2 + 2 ** 2 + 3 ** 2 + 5 ** 2
    assert result["covariance"][0, 0] == 2 / 1 * (occupation + time - intersection)


def test_cross_model_contrast_uses_joint_covariance():
    rng = np.random.default_rng(22)
    cube_a = rng.normal(size=(8, 6, 2))
    cube_b = rng.normal(size=(8, 6, 2))
    joint = HAC.covariance_components(
        np.concatenate([cube_a, cube_b], axis=2),
        [f"2023-{month:02d}" for month in range(1, 7)], 1)["covariance"]
    contrast = np.asarray([0, -1, 0, 1], float)
    direct = HAC.covariance_components(
        (cube_b[:, :, 1] - cube_a[:, :, 1])[:, :, None],
        [f"2023-{month:02d}" for month in range(1, 7)], 1)["covariance"][0, 0]
    assert np.isclose(contrast @ joint @ contrast, direct)


def test_full_calendar_month_number_round_trip_across_year_boundary():
    full, positions = HAC.full_calendar_positions(["2023-12", "2024-02"])
    assert full == ["2023-12", "2024-01", "2024-02"]
    assert positions.tolist() == [0, 2]
