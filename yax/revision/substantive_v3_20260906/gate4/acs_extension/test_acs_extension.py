from __future__ import annotations

import importlib.util
import io
from pathlib import Path
import sys
import zipfile

import numpy as np
import pandas as pd
import pytest


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("acs_extension_tested", HERE / "run_acs_extension.py")
assert spec and spec.loader
MOD = importlib.util.module_from_spec(spec)
sys.modules["acs_extension_tested"] = MOD
spec.loader.exec_module(MOD)


def weight_frame(rows: int, value: float = 10.0) -> pd.DataFrame:
    return pd.DataFrame({column: np.full(rows, value + index / 100.0)
                         for index, column in enumerate(MOD.WEIGHT_COLUMNS)})


def test_population_sequence_and_group_quarters():
    frame = pd.DataFrame({
        "ESR": [1, 2, 4, 1, 1, 1], "COW": [1, 8, 1, 6, 1, np.nan],
        "WKHP": [40, 40, 40, 40, 20, 40], "TYPEHUGQ": [1, 1, 1, 1, 2, 1],
    })
    masks = MOD.population_masks(frame)
    assert masks["all_employed"].tolist() == [True] * 6
    assert masks["civilian_employed"].tolist() == [True, True, False, True, True, True]
    assert masks["civilian_no_unpaid_family"].tolist() == [True, False, False, True, True, False]
    assert masks["civilian_wage_salary"].tolist() == [True, False, False, False, True, False]
    assert masks["full_time_civilian_wage_salary"].tolist() == [True, False, False, False, False, False]
    assert masks["all_employed_household_only"].tolist() == [True, True, True, True, False, True]


def test_valid_occ_preserves_leading_zeros_and_rejects_text():
    result = MOD.valid_occ(pd.Series([10, "0020", "bad", "", 10000, 1.5]))
    assert result.iloc[0] == "0010"
    assert result.iloc[1] == "0020"
    assert result.iloc[2:].isna().all()


def test_benchmark_statistic_is_difference_in_growth_factors():
    block = pd.DataFrame({
        "year": [2022, 2022, 2024, 2024], "age_group": ["young"] * 4,
        "quintile": [1, 5, 1, 5], "PWGTP": [100.0, 200.0, 110.0, 180.0],
    })
    estimate, g1, g5 = MOD.benchmark_statistic(block, "PWGTP", "PWGTP")
    assert g1 == pytest.approx(1.1)
    assert g5 == pytest.approx(0.9)
    assert estimate == pytest.approx(-0.2)


def test_sdr_variance_uses_official_factor_and_complete_blocks():
    values = np.arange(160.0) / 1000.0
    assert MOD.sdr_variance(values) == pytest.approx((4.0 / 80.0) * (values @ values))
    with pytest.raises(RuntimeError, match="invalid SDR"):
        MOD.sdr_variance(values[:-1])


def test_benchmark_pairing_differences_common_replicates():
    results = [
        {"definition": "d", "population": "all_employed",
         "estimate_Q5_minus_Q1_growth_factor": 0.2},
        {"definition": "d", "population": "full_time_civilian_wage_salary",
         "estimate_Q5_minus_Q1_growth_factor": 0.1},
    ]
    # Add the other required definitions/populations so the routine's declared
    # comparison grid is complete.
    populations = list(MOD.BENCHMARK_POPULATIONS)
    definitions = ["BCC_analogue_primary_equal", "YAX_primary_fixed",
                   "BCC_analogue_broader_equal"]
    results = [{"definition": d, "population": p,
                "estimate_Q5_minus_Q1_growth_factor": 0.2 + .01 * i}
               for i, (d, p) in enumerate((d, p) for d in definitions for p in populations)]
    reps = []
    for result in results:
        for year in [2022, 2024]:
            for replicate in range(1, 81):
                reps.append({**result, "perturbed_year": year, "replicate": replicate,
                             "estimate": result["estimate_Q5_minus_Q1_growth_factor"] +
                                         replicate / 10000.0})
    paired = MOD.benchmark_paired_results(results, reps)
    assert len(paired) == 15
    assert max(abs(row["ACS_paired_SDR_se"]) for row in paired) < 1e-12


def test_annual_design_has_declared_post_and_nesting():
    q = np.asarray([1, 5, 3])
    f = np.asarray(["11", "11", "15"])
    years = (2017, 2021, 2023, 2024)
    pooled = MOD.annual_design(q, f, years, "pooled")
    family = MOD.annual_design(q, f, years, "family_year")
    assert pooled.regressors.shape == (12, 4)
    assert pooled.regressors[4:8, 3].tolist() == [0.0, 0.0, 1.0, 1.0]
    assert len(set(pooled.second_labels)) == 4
    assert len(set(family.second_labels)) == 8


def test_fixed_support_requires_young_and_older_preperiod_stock():
    years = (2017, 2021, 2023)
    young = np.asarray([[1, 0, 1], [0, 0, 1], [1, 0, 0]], float)
    older = np.asarray([[1, 0, 1], [1, 0, 1], [0, 0, 1]], float)
    assert MOD.fixed_model_support(young, older, years).tolist() == [True, False, False]


def test_cell_weight_cube_orders_occupation_year_weight():
    rows = []
    for occ in ["0010", "0020"]:
        for year in MOD.YEARS:
            row = {"occ_code": occ, "year": year, "age_group": "young"}
            row.update({column: int(occ) + year + index
                        for index, column in enumerate(MOD.WEIGHT_COLUMNS)})
            rows.append(row)
    cube = MOD.cell_weight_cube(pd.DataFrame(rows), np.asarray(["0020", "0010"]), "young")
    assert cube.shape == (2, 7, 81)
    assert cube[0, 0, 0] == 20 + 2017
    assert cube[1, -1, 80] == 10 + 2024 + 80


def test_zip_member_selection_and_aggregate_current_year(tmp_path):
    frame = pd.DataFrame({
        "AGEP": [23, 40], "ESR": [1, 4], "OCCP": ["0010", "0020"],
        "COW": [1, 1], "WKHP": [40, 40], "TYPEHUGQ": [1, 2],
    })
    frame = pd.concat([frame, weight_frame(2)], axis=1)
    path = tmp_path / "acs.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("housing.csv", "wrong,file\n")
        archive.writestr("psam_pusa.csv", frame.to_csv(index=False))
    bridge = pd.DataFrame({
        "census_2010": ["0010"], "census_2018": ["0010"], "bridge_weight": [1.0]})
    cells, receipt = MOD.aggregate_year(2024, path, bridge, {"0010", "0020"})
    assert receipt["raw_rows"] == 2
    assert set(cells.population) == set(MOD.BENCHMARK_POPULATIONS)
    assert cells.loc[cells.population.eq("full_time_civilian_wage_salary"), "PWGTP"].sum() == 10
    assert cells.loc[cells.population.eq("all_employed"), "PWGTP"].sum() == 20
    assert cells.loc[cells.population.eq("all_employed_household_only"), "PWGTP"].sum() == 10


def test_2017_routes_replicates_without_renormalizing(tmp_path):
    frame = pd.DataFrame({
        "AGEP": [23], "ESR": [1], "OCCP": ["0010"], "COW": [1],
        "WKHP": [40], "TYPE": [1],
    })
    frame = pd.concat([frame, weight_frame(1, 20.0)], axis=1)
    path = tmp_path / "acs.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("psam_pusa.csv", frame.to_csv(index=False))
    bridge = pd.DataFrame({
        "census_2010": ["0010", "0010"], "census_2018": ["0010", "0020"],
        "bridge_weight": [0.25, 0.75],
    })
    cells, _ = MOD.aggregate_year(2017, path, bridge, {"0010", "0020"})
    all_emp = cells.loc[cells.population.eq("all_employed")].sort_values("occ_code")
    assert all_emp.PWGTP.tolist() == pytest.approx([5.0, 15.0])
    assert all_emp.PWGTP80.tolist() == pytest.approx([5.2, 15.6])
    assert all_emp.respondent_equivalent.tolist() == pytest.approx([0.25, 0.75])


def test_membership_definitions_have_fixed_expected_support():
    definitions, audit = MOD.load_memberships(
        MOD.ROOT / "yax/revision/substantive_v3_20260906/runs/gate1_baseline/results/REBUILT_TREATMENT_MEMBERSHIP.csv",
        MOD.ROOT / "yax/revision/substantive_v3_20260906/runs/gate2_broader_support_authoritative_20260908/BROADER_SUPPORT_MEMBERSHIP.csv")
    assert audit["definition_counts"] == {
        "BCC_analogue_primary_equal": 468,
        "YAX_primary_fixed": 468,
        "BCC_analogue_broader_equal": 490,
    }
    assert all("occ_code" in value.columns for value in definitions.values())
    assert all(set(value.quintile) == {1, 2, 3, 4, 5}
               for value in definitions.values())


def test_fit_annual_refuses_silent_separation(monkeypatch):
    class Fit:
        separated_observation_count = 1
        active_occupation_count = 5
        active_family_count = 2

    monkeypatch.setattr(MOD.CORE, "fit_with_influence", lambda *args, **kwargs: Fit())
    with pytest.raises(RuntimeError, match="silently changed"):
        MOD.fit_annual(
            np.ones((5, 2)), np.ones((5, 2)), np.arange(1, 6),
            np.asarray(["11", "11", "15", "15", "15"]),
            (2021, 2023), "pooled")


def test_family_multiplier_support_is_six_point_unit_variance():
    support = np.asarray(MOD.CORE.WEBB_SUPPORT, float)
    assert len(support) == 6
    assert support.mean() == pytest.approx(0.0)
    assert np.mean(np.square(support)) == pytest.approx(1.0)
