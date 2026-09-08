import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("yax_shortfall_engine", HERE / "shortfall_engine.py")
SHORT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SHORT
SPEC.loader.exec_module(SHORT)


def calendar():
    return [f"{year}-{month:02d}" for year in range(2017, 2023)
            for month in range(1, 13) if f"{year}-{month:02d}" <= "2022-11"]


def test_shortfalls_bound_impossible_linear_predictions():
    months = calendar()
    # Total and young share both trend through zero if extrapolated unchecked.
    total = np.r_[np.linspace(100.0, 20.0, 36), np.full(35, 20.0)]
    share = np.r_[np.linspace(.2, .01, 36), np.full(35, .01)]
    young = (total * share)[None, :]
    older = (total * (1 - share))[None, :]
    result = SHORT.corrected_shortfalls(young, older, months)
    assert result["total_negative_predictions_before_bound"][0] > 0
    assert result["share_out_of_bounds_predictions_before_bound"][0] > 0
    assert np.isfinite(result["total"][0])
    assert np.isfinite(result["young_relative"][0])


def test_one_to_one_mask_requires_target_level_bijection():
    bridge = pd.DataFrame([
        {"census_2010": "1000", "census_2018": "1000", "bridge_weight": 1,
         "n_routes": 1, "ambiguity_status": "one_to_one"},
        {"census_2010": "2000", "census_2018": "2001", "bridge_weight": .2,
         "n_routes": 2, "ambiguity_status": "one_to_many_diffuse"},
        {"census_2010": "2000", "census_2018": "2002", "bridge_weight": .8,
         "n_routes": 2, "ambiguity_status": "one_to_many_diffuse"},
        {"census_2010": "3000", "census_2018": "3001", "bridge_weight": 1,
         "n_routes": 1, "ambiguity_status": "one_to_one"},
        {"census_2010": "3002", "census_2018": "3001", "bridge_weight": 1,
         "n_routes": 1, "ambiguity_status": "one_to_one"},
        # Even internally inconsistent metadata must not admit a source split
        # across two targets.
        {"census_2010": "4000", "census_2018": "4001", "bridge_weight": 1,
         "n_routes": 1, "ambiguity_status": "one_to_one"},
        {"census_2010": "4000", "census_2018": "4002", "bridge_weight": 1,
         "n_routes": 1, "ambiguity_status": "one_to_one"},
    ])
    observed = SHORT.one_to_one_mask(
        np.asarray(["1000", "2001", "2002", "3001", "4001", "4002"]), bridge)
    assert observed.tolist() == [True, False, False, False, False, False]


def test_weighted_standardization_is_centered_and_unit_variance():
    values = np.asarray([1.0, 2.0, 9.0])
    weights = np.asarray([1.0, 3.0, 100.0])
    support = np.asarray([True, True, False])
    z, diagnostics = SHORT.weighted_standardize(values, weights, support)
    assert np.isclose(np.average(z[support], weights=weights[support]), 0)
    assert np.isclose(np.average(z[support] ** 2, weights=weights[support]), 1)
    assert np.isnan(z[~support]).all()
    assert diagnostics["standardization_weight"] == 4.0
