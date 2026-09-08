from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np


HERE = Path(__file__).resolve().parent


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


RUN = load_module("test_yax_equal_occupation", HERE / "run_equal_occupation.py")


def test_equal_objective_gives_every_occupation_unit_total_weight():
    young = np.array([[1.0, 2.0, 0.0], [0.0, 3.0, 2.0]])
    older = np.array([[1.0, 2.0, 0.0], [0.0, 1.0, 6.0]])
    y_value, o_value, weight = RUN.equal_occupation_cells(young, older)
    assert np.allclose(weight.sum(axis=1), 1.0, rtol=0, atol=1e-15)
    assert np.array_equal(weight[0], [0.5, 0.5, 0.0])
    assert np.array_equal(weight[1], [0.0, 0.5, 0.5])
    assert np.allclose(y_value + o_value, weight)
    assert np.isclose(y_value[0, 0] / weight[0, 0], 0.5)
    assert np.isclose(y_value[1, 2] / weight[1, 2], 0.25)


def test_equal_objective_rejects_occupation_without_positive_month():
    young = np.array([[1.0], [0.0]])
    older = np.array([[1.0], [0.0]])
    try:
        RUN.equal_occupation_cells(young, older)
    except RuntimeError as error:
        assert "no positive-employment month" in str(error)
    else:
        raise AssertionError("empty occupation did not fail closed")


def test_spec_keeps_cps_weights_and_defines_changed_estimand():
    text = " ".join((HERE / "EQUAL_OCCUPATION_SPEC.md").read_text().split())
    assert "Every occupation therefore contributes exactly one unit" in text
    assert "`WTFINL` remains load-bearing" in text
    assert "It is not the employment-stock-weighted population association" in text
    assert "does not establish equivalence" in text

