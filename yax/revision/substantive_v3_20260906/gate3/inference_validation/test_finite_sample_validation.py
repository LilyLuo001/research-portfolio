from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "yax_gate3_finite_sample", HERE / "run_finite_sample_validation.py")
SIM = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = SIM
spec.loader.exec_module(SIM)


def test_scenario_inventory_has_declared_dgps_and_ablations():
    designs = {value["design"] for value in SIM.SCENARIOS.values()}
    assert designs == {
        "empirical_gaussian_ar1", "prior_adverse_rademacher",
        "sparsity_equalized", "family_variance_zero",
        "serial_independent", "influence_equalized", "occupation_gaussian_ar1",
    }
    assert len(SIM.SCENARIOS) == 11


def test_influence_equalization_preserves_family_information():
    families = np.asarray(["A", "A", "B", "B"], object)
    months = 3
    total = np.asarray([
        100, 100, 100, 400, 400, 400, 50, 50, 50, 200, 200, 200,
    ], float)
    probability = np.full_like(total, .2)
    rescaled, diagnostics = SIM.influence_equalized_total(
        total, probability, families, months)
    before = (total * probability * (1 - probability)).reshape(4, 3).sum(axis=1)
    after = (rescaled * probability * (1 - probability)).reshape(4, 3).sum(axis=1)
    assert np.isclose(before[:2].sum(), after[:2].sum())
    assert np.isclose(before[2:].sum(), after[2:].sum())
    assert np.isclose(after[0], after[1]) and np.isclose(after[2], after[3])
    assert diagnostics["maximum_family_information_total_gap"] < 1e-8


def test_crossfit_oracle_never_calibrates_on_evaluation_half():
    frame = pd.DataFrame({
        "replicate": np.arange(1, 401), "estimate": np.linspace(-.2, .2, 400),
        "pseudo_truth": np.zeros(400), "occupation_se": np.full(400, .1),
    })
    lower, upper, critical = SIM.crossfit_oracle(frame)
    odd_standardized = np.abs(frame.loc[frame.replicate % 2 == 1, "estimate"] / .1)
    even_standardized = np.abs(frame.loc[frame.replicate % 2 == 0, "estimate"] / .1)
    assert critical["odd_calibration_critical"] == np.quantile(odd_standardized, .95, method="higher")
    assert critical["even_calibration_critical"] == np.quantile(even_standardized, .95, method="higher")
    assert np.allclose((upper - lower) / .2,
                       np.where(frame.replicate.to_numpy() % 2 == 1,
                                critical["even_calibration_critical"],
                                critical["odd_calibration_critical"]))


def test_multiplier_methods_are_alternatives_not_variance_sums():
    source = (HERE / "run_finite_sample_validation.py").read_text(encoding="utf-8")
    assert "occupation_se + family_se" not in source
    assert "occupation_se ** 2 + family_se ** 2" not in source
    assert SIM.PROCEDURES[:4] == (
        "occupation_rademacher", "occupation_webb",
        "family_rademacher", "family_webb")


def test_stopping_constants_match_declared_design():
    assert (SIM.PILOT, SIM.BLOCK, SIM.CAP, SIM.INNER_DRAWS) == (399, 400, 1999, 9999)
    assert SIM.MCSE_TARGET == .0125
    assert SIM.SD_RELATIVE_MC_ERROR_TARGET == .05


def test_summary_executes_all_targets_and_procedures():
    rows = []
    for replicate in range(1, 400):
        estimate = .01 * np.sin(replicate)
        for target in SIM.TARGETS:
            row = {
                "scenario": "synthetic", "replicate": replicate, "target": target,
                "pseudo_truth": 0.0, "estimate": estimate, "bias": estimate,
                "occupation_se": .01, "family_se": .02, "iterations": 2,
                "pooled_separated_fraction": 0.0,
                "family_month_separated_fraction": 0.0,
            }
            for procedure, half in (
                ("occupation_rademacher", .02),
                ("occupation_webb", .02),
                ("family_rademacher", .03),
                ("family_webb", .03),
            ):
                row.update({
                    f"{procedure}_critical": 2.0,
                    f"{procedure}_lower": estimate - half,
                    f"{procedure}_upper": estimate + half,
                    f"{procedure}_covers_truth": True,
                    f"{procedure}_rejects_zero": False,
                })
            rows.append(row)
    summary, stopping = SIM.summarize(rows, 399, 0)
    assert len(summary) == len(SIM.TARGETS) * len(SIM.PROCEDURES)
    assert stopping["passes"]


def test_sd_mc_error_uses_observed_fourth_moment():
    normal = np.random.default_rng(90).normal(size=5000)
    heavy = np.random.default_rng(91).standard_t(df=5, size=5000)
    assert SIM.empirical_sd_relative_mc_error(heavy) > SIM.empirical_sd_relative_mc_error(normal)


def test_stationary_variance_diagnostic_checks_all_months():
    months = ["2022-10", "2022-11", "2023-01", "2023-02"]
    result = SIM.stationary_variance_diagnostic(months, .6, .1)
    assert result["diagnostic_paths"] == 5000
    assert result["maximum_theoretical_relative_month_variance_difference"] <= 1e-14
    assert result["finite_simulation_maximum_is_diagnostic_not_pass_fail"] is True
    assert result["maximum_relative_month_variance_difference"] >= 0


def test_sparsity_equalization_matches_rounded_baseline_counts():
    total = np.asarray([10.0, 20.0])
    probability = np.asarray([.5, .5])
    rounded_baseline = np.asarray([2, 4])
    common_float, common = SIM.variance_preserving_equalized_count(
        total, probability, rounded_baseline)
    expected = (25.0 + 100.0) / (25.0 / 2.0 + 100.0 / 4.0)
    assert common_float == expected
    assert common == 3


def test_occupation_webb_reports_occupation_studentizer():
    local = pd.DataFrame({"occupation_se": [.01, .02], "family_se": [.10, .20]})
    assert np.array_equal(
        SIM.reported_standard_error(local, "occupation_webb"), [.01, .02])
    assert np.array_equal(
        SIM.reported_standard_error(local, "family_webb"), [.10, .20])


def test_historical_null_label_and_failed_gap_are_retained(tmp_path):
    old = pd.DataFrame({
        "effect_label": ["null"] * 195,
        "model": ["baseline"] * 195,
        "replicate": np.arange(1, 196),
        "coefficient": np.linspace(-.1, .1, 195),
    })
    path = tmp_path / "historical.csv"
    old.to_csv(path, index=False)
    rows = [
        {"target": "pooled", "replicate": int(row.replicate),
         "estimate": float(row.coefficient + .01)}
        for row in old.itertuples()
    ]
    result = SIM.historical_reproduction(rows, path, "adverse_null")
    assert result["compared_draws"] == 195
    assert not result["passes_tolerance"]
    assert np.isclose(result["maximum_pooled_coefficient_difference"], .01)


def test_successful_run_does_not_index_empty_failure_inventory():
    source = (HERE / "run_finite_sample_validation.py").read_text(encoding="utf-8")
    assert 'require(bool(rows), f"all joint refits failed' not in source
    assert 'if not rows:' in source
