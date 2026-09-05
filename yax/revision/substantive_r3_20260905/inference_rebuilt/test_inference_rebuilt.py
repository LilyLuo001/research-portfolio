"""Unit tests that do not require restricted CPS microdata."""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import numpy as np


HERE = pathlib.Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "yax_r3_test_inference_rebuilt", HERE / "run_inference_rebuilt.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_full_calendar_uses_elapsed_months_and_retains_gaps():
    months = ["2022-11", "2023-01", "2023-02", "2023-04"]
    full, positions = MODULE.full_calendar_positions(months)
    assert full == ["2022-11", "2022-12", "2023-01", "2023-02", "2023-03", "2023-04"]
    assert positions.tolist() == [0, 2, 3, 5]


def test_newey_west_is_symmetric_and_includes_positive_lag():
    score = np.asarray([[1.0, 2.0], [3.0, -1.0], [2.0, 4.0]])
    lag0 = MODULE.newey_west_meat(score, 0)
    lag1 = MODULE.newey_west_meat(score, 1)
    gamma = score[1:].T @ score[:-1]
    assert np.allclose(lag0, score.T @ score)
    assert np.allclose(lag1, lag0 + 0.5 * (gamma + gamma.T))
    assert np.allclose(lag1, lag1.T)


def test_inclusion_exclusion_removes_full_within_occupation_hac():
    cube = np.asarray([
        [[[1.0]], [[2.0]], [[0.0]]],
        [[[3.0]], [[-1.0]], [[4.0]]],
    ]).reshape(2, 3, 1)
    months = ["2023-01", "2023-02", "2023-03"]
    components = MODULE.covariance_components(cube, months, 1)
    occupation = cube.sum(axis=1)
    expected = (
        occupation.T @ occupation +
        MODULE.newey_west_meat(cube.sum(axis=0), 1) -
        sum((MODULE.newey_west_meat(cube[index], 1)
             for index in range(cube.shape[0])), np.zeros((1, 1)))
    )
    assert np.allclose(components["combined_unscaled"], expected)
    assert np.allclose(components["covariance"], 2.0 * expected)


def test_parameter_labels_and_mde_factor_are_fixed():
    assert MODULE.TARGET == 3
    assert MODULE.PARAMETER_LABELS[MODULE.TARGET] == "Q5_x_post_2023_01"
    assert np.isclose(MODULE.MDE_FACTOR, 2.8015852181129683)
    assert MODULE.DRAWS == 99999
    assert MODULE.SEED == 2026090561
