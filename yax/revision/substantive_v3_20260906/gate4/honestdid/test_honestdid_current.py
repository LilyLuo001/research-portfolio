from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


PREP = load("yax_honestdid_test_prep", "prepare_honestdid_inputs.py")
VALIDATE = load("yax_honestdid_test_validate", "validate_honestdid_outputs.py")


def test_quarter_sequence_is_calendar_exact():
    assert PREP.quarters_between("2021Q1", "2022Q3") == [
        "2021Q1", "2021Q2", "2021Q3", "2021Q4",
        "2022Q1", "2022Q2", "2022Q3",
    ]
    assert len(PREP.quarters_between("2017Q1", "2022Q3")) == 23
    assert PREP.quarter_number("2022Q3") + 1 == PREP.quarter_number("2022Q4")


def test_smoothness_matrix_is_signed_second_difference_with_reference_removed():
    obtained = PREP.smoothness_matrix(2, 2)
    positive = np.asarray([
        [1.0, -2.0, 0.0, 0.0],
        [0.0, 1.0, 1.0, 0.0],
        [0.0, 0.0, -2.0, 1.0],
    ])
    assert np.array_equal(obtained, np.vstack((positive, -positive)))
    assert np.array_equal(obtained, VALIDATE.reconstruct_smooth(2, 2))


@pytest.mark.parametrize("num_pre,num_post", [(2, 1), (3, 2), (7, 15), (23, 15)])
@pytest.mark.parametrize("mbar", PREP.RELATIVE_GRID)
@pytest.mark.parametrize("max_positive", [True, False])
def test_relative_matrix_matches_independent_consecutive_change_construction(
        num_pre: int, num_post: int, mbar: float, max_positive: bool):
    for s in range(-(num_pre - 1), 1):
        obtained = PREP.relative_matrix(num_pre, num_post, mbar, s, max_positive)
        expected = VALIDATE.reconstruct_relative(
            num_pre, num_post, mbar, s, max_positive)
        assert np.array_equal(obtained, expected)


def test_relative_matrix_zero_rows_are_removed_before_reference_column():
    matrix = PREP.relative_matrix(2, 1, 1.0, 0, True)
    assert matrix.shape[1] == 3
    assert np.all(np.sum(matrix * matrix, axis=1) > 1e-10)


def test_invalid_relative_anchor_is_rejected():
    with pytest.raises(RuntimeError, match="outside preperiod"):
        PREP.relative_matrix(7, 15, 1.0, -7, True)


def test_declared_windows_are_contiguous_and_not_gapped():
    for start, end, count in PREP.WINDOWS.values():
        labels = PREP.quarters_between(start, end)
        assert len(labels) == count
        assert all(PREP.quarter_number(right) - PREP.quarter_number(left) == 1
                   for left, right in zip(labels, labels[1:]))
        assert PREP.quarter_number(labels[-1]) + 1 == PREP.quarter_number(PREP.REFERENCE)


def test_post_grid_and_target_contract_are_fixed():
    assert PREP.SMOOTH_GRID == (0.0, 0.005, 0.01, 0.02, 0.03, 0.04, 0.05)
    assert PREP.RELATIVE_GRID == (0.0, 0.5, 1.0, 1.5, 2.0)
    assert PREP.STRUCTURES == ("unconditioned", "family_month")

