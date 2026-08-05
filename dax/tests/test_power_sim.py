import importlib.util
import pathlib
import sys


import numpy as np
import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "memo" / "power_calcs" / "simulate_power.py"
SPEC = importlib.util.spec_from_file_location("simulate_power", MODULE_PATH)
assert SPEC and SPEC.loader
POWER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = POWER
SPEC.loader.exec_module(POWER)


def test_cluster_estimator_recovers_injected_effect():
    rng = np.random.default_rng(7)
    clusters = np.repeat(np.arange(20), 8)
    n = len(clusters)
    nuisance = np.column_stack([np.ones(n), np.tile(np.arange(8), 20)])
    x = rng.normal(size=n)
    weights = np.ones(n)
    estimator = POWER.FWLClusterEstimator(x, nuisance, weights, clusters)
    y = 0.25 * x + nuisance @ np.array([2.0, -0.1])
    beta, se = estimator.fit(y)
    assert beta == pytest.approx(0.25, abs=1e-10)
    assert se < 1e-10


def test_add_months_handles_year_boundaries():
    assert POWER.add_months(POWER.dt.date(2024, 1, 1), -2) == POWER.dt.date(2023, 11, 1)
    assert POWER.add_months(POWER.dt.date(2024, 11, 1), 3) == POWER.dt.date(2025, 2, 1)


def test_post_event_cells_are_rejected(tmp_path):
    path = tmp_path / "cells.csv"
    path.write_text(
        "cps_occ,month,industry,education_group,n_unweighted,weight_sum,weight_sq_sum,employment_rate,hours_mean_unconditional,hours_variance_unconditional,employment_hours_covariance,dose_sd_within_cps,max_crosswalk_weight\n"
        "1,2023-03-01,A,college,10,10,10,0.8,30,100,2,0.05,0.8\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="post-event month prohibited"):
        POWER.load_cells(path)
