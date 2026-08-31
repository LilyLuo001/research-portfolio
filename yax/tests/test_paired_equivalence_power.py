import importlib.util
import pathlib
import sys

import numpy as np


ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "yax" / "power" / "paired_equivalence_power.py"
SPEC = importlib.util.spec_from_file_location("paired_equivalence_power", PATH)
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_post_window_excludes_transition_and_known_gap():
    months = MOD.post_months()
    assert months[0] == "2023-01"
    assert months[-1] == "2026-07"
    assert "2022-12" not in months
    assert "2025-10" not in months


def test_same_ranking_produces_same_weighted_quintiles():
    values = np.arange(1.0, 11.0)
    weights = np.ones(10)
    first = MOD.weighted_quintiles(values, weights)
    second = MOD.weighted_quintiles(2 * values + 5, weights)
    assert np.array_equal(first, second)
    assert set(first) == {1, 2, 3, 4, 5}


def test_equal_scores_are_not_split_across_quintiles():
    values = np.repeat(np.arange(1.0, 6.0), 2)
    quintiles = MOD.weighted_quintiles(values, np.ones(10))
    for value in np.unique(values):
        assert len(set(quintiles[values == value])) == 1


def test_equivalence_power_is_monotone_in_fixed_margin():
    delta = np.linspace(-0.01, 0.01, 999)
    critical = MOD.quantile_higher(np.abs(delta), 0.95)
    small = MOD.equivalence_power(delta, critical, 0.011)
    large = MOD.equivalence_power(delta, critical, 0.030)
    assert large >= small


def test_difference_mde_reaches_target_power():
    delta = np.linspace(-0.01, 0.01, 999)
    critical = MOD.quantile_higher(np.abs(delta), 0.95)
    mde = MOD.difference_mde80(delta, critical)
    centered = delta - delta.mean()
    assert np.mean(np.abs(centered + mde) > critical) >= 0.80
