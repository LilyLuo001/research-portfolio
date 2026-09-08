from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np


HERE = Path(__file__).resolve().parent


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BATCH = load("yax_gate3_household_batch", "run_household_refit_batch.py")
SUMMARY = load("yax_gate3_household_summary", "summarize_household_refits.py")


def test_household_multiplier_is_common_across_routes():
    arrays = {
        "total": np.zeros(3),
        "route_stock": np.asarray([2.0, 3.0, 5.0, 7.0]),
        "household_code": np.asarray([0, 0, 1, 1]),
        "cellage": np.asarray([0, 3, 1, 4]),
    }
    young, older = BATCH.cells_from_multiplier(arrays, np.asarray([10.0, 100.0]))
    assert np.array_equal(young, np.asarray([20.0, 500.0, 0.0]))
    assert np.array_equal(older, np.asarray([30.0, 700.0, 0.0]))


def test_regenerated_labels_are_weighted_and_webb_standardized():
    exposure = np.arange(1, 11, dtype=float)
    webb = np.linspace(-2, 2, 10)
    weights = np.ones(10)
    q, z, diagnostics = BATCH.weighted_labels(exposure, webb, weights)
    assert set(q) == {1, 2, 3, 4, 5}
    assert abs(np.average(z, weights=weights)) < 1e-12
    assert abs(np.average(z * z, weights=weights) - 1) < 1e-12
    assert diagnostics["q1_cut"] < diagnostics["q4_cut"]


def test_endpoint_monte_carlo_error_is_deterministic():
    shifts = np.random.default_rng(77).normal(size=399)
    left = SUMMARY.endpoint_monte_carlo_error(shifts, 88)
    right = SUMMARY.endpoint_monte_carlo_error(shifts, 88)
    assert left == right
    assert left["shift_q025_mcse"] > 0
    assert left["shift_q975_mcse"] > 0


def test_household_module_never_adds_cluster_variances():
    source = (HERE / "summarize_household_refits.py").read_text(encoding="utf-8")
    assert "mechanically_combined_with_cluster_variance\": False" in source
    assert "occupation_se +" not in source
