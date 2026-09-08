from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np


HERE = Path(__file__).resolve().parent


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CORE = load("yax_gate3_inference_engine", HERE / "inference_engine.py")
ENGINE = load(
    "yax_gate3_legacy_grouped_engine",
    HERE.parents[4] / "dax/memo/power_calcs/young_relative_employment_power.py",
)


def synthetic():
    rng = np.random.default_rng(9301)
    quintile = np.repeat(np.arange(1, 6), 2)
    webb = np.linspace(-1, 1, len(quintile))
    family = np.asarray(["A"] * 5 + ["B"] * 5, object)
    months = ["2022-10", "2022-11", "2023-01", "2023-02"]
    total = rng.integers(80, 240, size=len(quintile) * len(months)).astype(float)
    eta = np.repeat(np.linspace(-2.5, -1.0, len(quintile)), len(months))
    eta += np.tile(np.asarray([0.0, .1, -.05, .05]), len(quintile))
    eta += .25 * ((np.repeat(quintile, len(months)) == 5) &
                  (np.tile(np.asarray(months), len(quintile)) >= "2023-01"))
    probability = 1 / (1 + np.exp(-eta))
    young = rng.binomial(total.astype(int), probability).astype(float)
    return quintile, webb, family, months, young, total


def test_central_designs_differ_only_in_second_fixed_effect_partition():
    q, w, f, months, _, _ = synthetic()
    pooled = CORE.build_design(q, w, f, months, "pooled")
    conditioned = CORE.build_design(q, w, f, months, "family_month")
    assert np.array_equal(pooled.regressors, conditioned.regressors)
    assert np.array_equal(pooled.first_labels, conditioned.first_labels)
    assert not np.array_equal(pooled.second_labels, conditioned.second_labels)
    assert pooled.regressor_labels[pooled.focal_target_index] == "Q5_x_post"


def test_fit_influences_reproduce_covariance_and_pairing():
    q, w, f, months, young, total = synthetic()
    pooled = CORE.fit_with_influence(
        ENGINE, young, total, CORE.build_design(q, w, f, months, "pooled"))
    conditioned = CORE.fit_with_influence(
        ENGINE, young, total, CORE.build_design(q, w, f, months, "family_month"))
    pair = CORE.paired_target(conditioned, pooled)
    direct = (conditioned.occupation_influence[:, CORE.TARGET_INDEX] -
              pooled.occupation_influence[:, CORE.TARGET_INDEX])
    assert np.isclose(pair["occupation_se"] ** 2, direct @ direct)
    assert np.isclose(pair["estimate"], conditioned.estimate - pooled.estimate)
    draws = CORE.draw_multiplier_matrices(999, len(q), len(set(f)), 44)
    interval = CORE.multiplier_interval(pair["estimate"], direct,
                                        draws["occupation_rademacher"])
    assert interval["lower"] < pair["estimate"] < interval["upper"]
    assert draws["occupation_webb"].shape == draws["occupation_rademacher"].shape


def test_calendar_ar1_respects_two_month_gap():
    rng = np.random.default_rng(11)
    months = ["2022-11", "2023-01"]
    rho = .5
    draws = np.asarray([
        CORE.draw_stationary_ar1(rng, 1, months, rho, 1.0)[0]
        for _ in range(50_000)
    ])
    correlation = np.corrcoef(draws.T)[0, 1]
    assert abs(correlation - rho ** 2) < .02


def test_ar1_calibration_reports_leave_family_range():
    rng = np.random.default_rng(12)
    shocks = np.vstack([
        np.cumsum(rng.normal(size=10)) * .02 for _ in range(4)
    ])
    result = CORE.estimate_ar1(shocks, np.ones_like(shocks),
                               [f"2023-{month:02d}" for month in range(1, 11)])
    assert -0.98 <= result["rho"] <= .98
    assert result["consecutive_pairs"] == 36
    assert result["leave_one_family_rho_min"] <= result["leave_one_family_rho_max"]


def test_binomial_stock_draw_preserves_weighted_total_and_zeros():
    total = np.asarray([100.0, 0.0, 350.0])
    count = np.asarray([10, 0, 7])
    young, older = CORE.binomial_stock_draw(
        np.random.default_rng(13), total, count, np.asarray([.2, .5, .8]))
    assert np.array_equal(young + older, total)
    assert young[1] == older[1] == 0


def test_webb_support_has_zero_mean_and_unit_variance():
    assert abs(float(CORE.WEBB_SUPPORT.mean())) < 1e-15
    assert abs(float(np.mean(CORE.WEBB_SUPPORT ** 2)) - 1.0) < 1e-15


def test_fixed_effect_separation_is_trimmed_iteratively_to_closure():
    young = np.asarray([0.0, 10.0, 0.0, 5.0])
    total = np.full(4, 10.0)
    first = np.asarray(["A", "A", "B", "B"], object)
    second = np.asarray(["X", "Y", "X", "Y"], object)
    active, diagnostics = CORE.drop_separated_fixed_effect_groups(
        young, total, first, second)
    assert active.tolist() == [False, False, False, True]
    assert diagnostics == {
        "separated_observation_count": 3,
        "separated_first_group_count": 1,
        "separated_second_group_count": 1,
    }


def test_nonseparated_sample_is_unchanged():
    young = np.asarray([2.0, 8.0, 3.0, 7.0])
    total = np.full(4, 10.0)
    first = np.asarray(["A", "A", "B", "B"], object)
    second = np.asarray(["X", "Y", "X", "Y"], object)
    active, diagnostics = CORE.drop_separated_fixed_effect_groups(
        young, total, first, second)
    assert active.all()
    assert diagnostics["separated_observation_count"] == 0
