from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "yax_test_public_benchmark", HERE / "run_public_benchmark.py")
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_equal_occupation_quintiles_preserve_ties_at_lower_cut():
    groups, cuts = MOD.equal_occupation_quintiles(np.arange(10.0))
    assert groups.tolist() == [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]
    assert cuts.tolist() == [1.0, 3.0, 5.0, 7.0]
    tied, _ = MOD.equal_occupation_quintiles(
        np.array([0, 0, 1, 2, 3, 4, 5, 6, 7, 8], float))
    assert tied[0] == tied[1]


def test_population_rule_includes_only_wage_salary_and_valid_full_time_hours():
    worker_class = pd.Series([20, 21, 22, 23, 24, 25, 27, 28,
                              10, 13, 14, 26, 29, 0, 99])
    hours = pd.Series([35, 40, 99, 35, 35, 35, 35, 35,
                       40, 40, 40, 40, 40, 40, 40])
    result = MOD.full_time_civilian_wage_salary(worker_class, hours)
    assert result.tolist() == [True] * 8 + [False] * 7
    assert not MOD.full_time_civilian_wage_salary(
        pd.Series([21, 21, 21, 21]), pd.Series([34, 997, 999, np.nan])).any()


def test_growth_influence_closes_and_common_growth_has_zero_contrast():
    start = np.arange(1.0, 11.0)
    end = np.empty_like(start)
    for first in range(0, 10, 2):
        second = first + 1
        end[first] = start[first] * 1.35
        end[second] = start[second] * (
            1.25 - 0.10 * start[first] / start[second])
    quintile = np.repeat(np.arange(1, 6), 2)
    signs = np.random.default_rng(4).choice([-1.0, 1.0], size=(999, 10))
    for contrast in ("Q5_vs_Q1_growth_factor_difference",
                     "top_two_vs_bottom_three_kept_pace"):
        result = MOD.aggregate_contrast(start, end, quintile, contrast, signs)
        assert abs(result["estimate"]) < 1e-14
        assert abs(result["influence"].sum()) < 1e-14


def test_kept_pace_formula_and_linearization_match_finite_difference():
    start = np.arange(2.0, 12.0)
    end = start * np.linspace(0.8, 1.3, 10)
    quintile = np.repeat(np.arange(1, 6), 2)
    signs = np.random.default_rng(5).choice([-1.0, 1.0], size=(999, 10))
    result = MOD.aggregate_contrast(
        start, end, quintile, "top_two_vs_bottom_three_kept_pace", signs)
    high, low = quintile >= 4, quintile <= 3
    expected = ((end[high].sum() / start[high].sum()) /
                (end[low].sum() / start[low].sum()) - 1)
    assert result["estimate"] == pytest.approx(expected)
    direction = np.linspace(-0.4, 0.3, 10)
    epsilon = 1e-6
    shifted = MOD.aggregate_contrast(
        start, end + epsilon * direction, quintile,
        "top_two_vs_bottom_three_kept_pace", signs)
    derivative = (shifted["estimate"] - result["estimate"]) / epsilon
    # End-stock perturbation is a cluster-size perturbation, so recompute its
    # exact analytic directional derivative directly.
    rh = end[high].sum() / start[high].sum()
    rl = end[low].sum() / start[low].sum()
    expected_derivative = (direction[high].sum() / start[high].sum()) / rl
    expected_derivative -= (rh / rl**2) * (
        direction[low].sum() / start[low].sum())
    assert derivative == pytest.approx(expected_derivative, rel=1e-6, abs=1e-8)


def test_wls_long_difference_recovers_weighted_group_means():
    occupations = np.asarray([f"{value:04d}" for value in range(15)])
    quintiles = np.repeat(np.arange(1, 6), 3)
    start = np.linspace(10, 30, 15)
    effects = np.asarray([0.01, 0.02, -0.03, -0.05, -0.09])
    end = start * (1 + effects[quintiles - 1])
    rows, keep, influence = MOD.wls_long_difference(
        start, end, quintiles, occupations, "all_employed", "test")
    estimates = {row["coefficient_label"]: row["estimate"] for row in rows}
    assert keep.all()
    assert estimates["intercept_Q1"] == pytest.approx(effects[0])
    for value in range(2, 6):
        assert estimates[f"Q{value}_vs_Q1"] == pytest.approx(
            effects[value - 1] - effects[0])
    assert influence.shape == (15, 5)


def test_panel_design_inventory_and_target_positions():
    q = np.tile(np.arange(1, 6), 2)
    webb = np.linspace(-1, 1, 10)
    families = np.asarray(["11"] * 5 + ["13"] * 5)
    months = ["2022-11", "2023-01", "2023-02"]
    for contrast, target in (("Q5_vs_Q1", 3),
                             ("top_two_vs_bottom_three", 0)):
        for webb_rule in MOD.WEBB_RULES:
            for structure in MOD.STRUCTURES:
                design, labels, actual = MOD.panel_design(
                    q, webb, families, months, structure, contrast, webb_rule, "11")
                assert actual == target == design.focal_target_index
                assert design.regressors.shape[0] == 30
                assert len(labels) == design.regressors.shape[1]
                if structure == "family_month":
                    assert len(set(design.second_labels)) == 6
                else:
                    assert len(set(design.second_labels)) == 3


def test_panel_fitter_handles_binary_family_post_target_without_borrowing_profile():
    occupations = np.asarray([f"{value:04d}" for value in range(20)])
    quintiles = np.tile(np.arange(1, 6), 4)
    families = np.asarray(["11", "13"] * 10)
    webb = np.linspace(-1, 1, 20)
    months = ["2022-09", "2022-10", "2022-11", "2023-01", "2023-02", "2023-03"]
    post = np.asarray([month >= "2023-01" for month in months], float)
    eta = (-2.0 + 0.15 * (quintiles >= 4)[:, None] * post[None, :] +
           0.03 * np.arange(len(months))[None, :])
    probability = 1 / (1 + np.exp(-eta))
    total = np.full_like(probability, 1000.0)
    young = total * probability
    older = total - young
    draws = MOD.CORE.draw_multiplier_matrices(999, 20, 2, 991)
    model = MOD.fit_panel_model(
        "synthetic", young, older, np.ones(20, bool), quintiles, webb,
        families, occupations, months, "family_post", "top_two_vs_bottom_three",
        "no_Webb_public_benchmark", "11",
        {"occupation": draws["occupation_rademacher"],
         "family": draws["family_rademacher"]}, "all_employed")
    assert model["row"]["coefficient_label"] == "top_two_vs_bottom_three_x_post"
    assert model["row"]["coefficient"] == pytest.approx(0.15, abs=1e-7)
    assert "Webb" not in model["row"]["regressor_labels_json"]


def test_scan_removes_wide_march_before_inserting_repair_and_routes_population(tmp_path):
    columns = ["YEAR", "MONTH", "AGE", "EMPSTAT", "OCC", "WTFINL",
               "CLASSWKR", "UHRSWORKT"]
    wide = pd.DataFrame([
        [2017, 3, 22, 10, 100, 100.0, 21, 40],  # must be removed
        [2017, 4, 22, 10, 100, 20.0, 21, 40],
        [2020, 4, 22, 10, 200, 30.0, 13, 40],
        [2020, 4, 22, 10, 200, 40.0, 21, 34],
        [2020, 4, 22, 10, 200, 50.0, 28, 35],
    ], columns=columns)
    repair = pd.DataFrame([
        [2017, 3, 22, 10, 100, 10.0, 21, 40],
    ], columns=columns)
    bridge = pd.DataFrame({
        "census_2010": ["0100"], "census_2018": ["0200"],
        "bridge_weight": [1.0],
    })
    wide_path = tmp_path / "wide.csv.gz"
    repair_path = tmp_path / "repair.csv.gz"
    bridge_path = tmp_path / "bridge.csv"
    wide.to_csv(wide_path, index=False)
    repair.to_csv(repair_path, index=False)
    bridge.to_csv(bridge_path, index=False)
    routed, audit, counters = MOD.scan_sources(
        wide_path, repair_path, bridge_path, {"0200"},
        {"2017-03", "2017-04", "2020-04"})
    result = routed.set_index(["occ_code", "month", "age"])
    assert result.at[("0200", "2017-03", 22), "all_employed_stock"] == 10.0
    assert result.at[("0200", "2017-04", 22), "all_employed_stock"] == 20.0
    assert result.at[("0200", "2020-04", 22), "all_employed_stock"] == 120.0
    assert result.at[("0200", "2020-04", 22),
                     "full_time_civilian_wage_salary_stock"] == 50.0
    assert counters["wide_march_rows_removed"] == 1
    assert counters["full_time_wage_salary_rows"] == 3
    assert audit


def test_runner_never_reads_person_or_household_identifiers():
    source = (HERE / "run_public_benchmark.py").read_text(encoding="utf-8")
    for forbidden in ("CPSID", "CPSIDP", "CPSIDV", "SERIAL", "PERNUM"):
        assert f'"{forbidden}"' not in source
    assert '"CLASSWKR"' in source and '"UHRSWORKT"' in source
