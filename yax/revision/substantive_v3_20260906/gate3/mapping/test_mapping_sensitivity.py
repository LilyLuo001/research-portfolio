from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


RUN = load_module("test_yax_gate3_mapping", HERE / "run_mapping_sensitivity.py")


def route_fixture() -> pd.DataFrame:
    return pd.DataFrame({
        "census_2010": ["1000", "1000", "2000"],
        "census_2018": ["1010", "1020", "2010"],
        "bridge_weight": [0.25, 0.5, 0.8],
        "supported_mass": [0.75, 0.75, 0.8],
        "beta": [0.1, 0.9, 0.4],
        "webb": [1.0, 2.0, 3.0],
        "rank": [-0.5, 0.5, 0.0],
        "eligible": [True, True, False],
    })


def test_no_tilt_is_bit_exact_official_weight():
    routes = route_fixture()
    result = RUN.allocation_table(routes, 1.0, 1.0)
    for age in ("young", "older"):
        observed = result.loc[result.age_group.eq(age), "scenario_weight"].to_numpy()
        assert np.array_equal(observed, routes.bridge_weight.to_numpy())


def test_symmetric_parameter_is_relative_age_odds():
    routes = route_fixture()
    k_value = 4.0
    result = RUN.allocation_table(routes, np.sqrt(k_value), 1 / np.sqrt(k_value))
    source = result.loc[result.census_2010.eq("1000")]
    young = source.loc[source.age_group.eq("young")].sort_values("rank")
    older = source.loc[source.age_group.eq("older")].sort_values("rank")
    young_ratio = (young.scenario_weight.iloc[-1] / young.bridge_weight.iloc[-1]) / (
        young.scenario_weight.iloc[0] / young.bridge_weight.iloc[0])
    older_ratio = (older.scenario_weight.iloc[-1] / older.bridge_weight.iloc[-1]) / (
        older.scenario_weight.iloc[0] / older.bridge_weight.iloc[0])
    assert np.isclose(young_ratio / older_ratio, k_value, atol=1e-14, rtol=0)


def test_independent_age_odds_and_supported_mass_are_preserved():
    routes = route_fixture()
    result = RUN.allocation_table(routes, 20.0, 0.05)
    sums = result.groupby(["age_group", "census_2010"]).scenario_weight.sum()
    assert np.isclose(sums.loc[("young", "1000")], 0.75)
    assert np.isclose(sums.loc[("older", "1000")], 0.75)
    assert np.isclose(sums.loc[("young", "2000")], 0.8)
    assert np.isclose(sums.loc[("older", "2000")], 0.8)
    single = result.loc[result.census_2010.eq("2000")]
    assert np.array_equal(single.scenario_weight.to_numpy(),
                          single.bridge_weight.to_numpy())


def test_weighted_contract_matches_left_closed_tie_rule():
    values = np.arange(10, dtype=float)
    weights = np.ones(10)
    result = RUN.weighted_contract(values, weights)
    assert np.array_equal(result["cuts"], np.array([1.0, 3.0, 5.0, 7.0]))
    assert np.array_equal(result["groups"],
                          np.array([1, 1, 2, 2, 3, 3, 4, 4, 5, 5]))


def test_source_age_month_mass_conservation_in_panel_expansion():
    routes = route_fixture()
    allocation = RUN.allocation_table(routes, 4.0, 0.25)
    early = pd.DataFrame({
        "source_occ": ["1000", "1000"], "month": ["2019-01", "2019-01"],
        "age_group": ["young", "older"], "stock": [100.0, 200.0],
    })
    direct = pd.DataFrame({
        "target_occ": ["1010", "1020"], "month": ["2020-01", "2020-01"],
        "age_group": ["young", "older"], "stock": [10.0, 20.0],
    })
    young, older, check = RUN.expand_panel(
        early, direct, allocation, ["1010", "1020"], ["2019-01", "2020-01"])
    assert np.isclose(young[:, 0].sum(), 75.0)
    assert np.isclose(older[:, 0].sum(), 150.0)
    assert np.isclose(young[:, 1].sum(), 10.0)
    assert np.isclose(older[:, 1].sum(), 20.0)
    assert check["maximum_relative_source_age_month_gap"] < 1e-14


def test_historical_deletion_order_is_fixed_and_current_support_contains_it():
    membership = pd.read_csv(
        HERE.parents[4] /
        "yax/revision/substantive_v3_20260906/runs/gate1_baseline/results/REBUILT_TREATMENT_MEMBERSHIP.csv",
        dtype={"occupation_code": str},
    )
    support = set(membership.occupation_code.str.zfill(4))
    assert len(RUN.HISTORICAL_DELETION_ORDER) == 20
    assert len(set(RUN.HISTORICAL_DELETION_ORDER)) == 20
    assert set(RUN.HISTORICAL_DELETION_ORDER).issubset(support)


def test_specification_forbids_false_bound_and_error_matrix_claims():
    text = (HERE / "MAPPING_SENSITIVITY_SPEC.md").read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    assert "explored adverse envelope" in normalized
    assert "not a sharp or global coefficient bound" in normalized
    assert "No separate numerator, denominator, or tail" in normalized
    assert "no authenticated dual-coded validation sample" in normalized.lower()
    assert "SOC33 protective" in normalized


def test_current_carry_forward_sources_exist_with_required_rows():
    root = HERE.parents[4]
    timing = pd.read_csv(
        root / "yax/revision/substantive_v3_20260906/runs/"
        "gate2_timing_extensions_authoritative_20260908/MODEL_RESULTS.csv"
    )
    assert set(["post_2020_unconditioned", "post_2020_family_month"]).issubset(
        set(timing.model_id))
    stable = pd.read_csv(
        root / "yax/revision/referee_20260905/results/balanced_cells/"
        "CALENDAR_TAXONOMY_SENSITIVITIES.csv"
    )
    assert (stable.specification == "stable_Census2010_observed_calendar").sum() == 1


def test_current_carry_forward_schema_is_consumed_end_to_end():
    root = HERE.parents[4]
    timing_path = (
        root / "yax/revision/substantive_v3_20260906/runs/"
        "gate2_timing_extensions_authoritative_20260908/MODEL_RESULTS.csv"
    )
    stable_path = (
        root / "yax/revision/referee_20260905/results/balanced_cells/"
        "CALENDAR_TAXONOMY_SENSITIVITIES.csv"
    )
    rows = RUN.carry_forward_rows(stable_path, timing_path)
    assert [row["model_id"] for row in rows] == [
        "stable_Census2010_observed_calendar",
        "post_2020_family_month",
        "post_2020_unconditioned",
    ]
    timing = pd.read_csv(timing_path, float_precision="round_trip").set_index("model_id")
    for row in rows[1:]:
        source = timing.loc[row["model_id"]]
        assert row["occupation_se"] == source["occupation_cluster_se"]
        assert row["occupation_ci_lower"] == source["ci_lower"]
        assert row["occupation_ci_upper"] == source["ci_upper"]


def test_public_source_path_accepts_repo_relative_and_absolute_inputs():
    relative = Path("yax/revision/example.csv")
    assert RUN.public_source_path(relative) == relative.as_posix()
    absolute = RUN.ROOT / relative
    assert RUN.public_source_path(absolute) == relative.as_posix()
