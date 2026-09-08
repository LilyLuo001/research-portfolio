from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


RUN = load("yax_cohort_enrollment_test_runner", "run_cohort_enrollment.py")
VALIDATE = load("yax_cohort_enrollment_test_validator",
                "validate_cohort_enrollment_outputs.py")


def test_school_group_never_calls_invalid_code_nonenrolled() -> None:
    result = RUN.school_group(pd.Series([0, 1, 2, 3, 4, 5, 9, np.nan])).tolist()
    assert result == ["invalid", "enrolled", "enrolled", "enrolled", "enrolled",
                      "not_enrolled", "invalid", "invalid"]


def test_age_bucket_respects_enrollment_universe_boundary() -> None:
    result = RUN.age_bucket(pd.Series([16, 21, 22, 25, 26, 54, 55, 65, 66])).tolist()
    assert result == ["16_21", "16_21", "22_25", "22_25", "26_54", "26_54",
                      "55_65", "55_65", "outside_audit"]


def test_fixed_age_standardization_preserves_month_population() -> None:
    months = ["2022-10", "2022-11", "2023-01"]
    population_rows = []
    routed_rows = []
    for age in range(26, 66):
        for month_index, month in enumerate(months):
            population_rows.append({"age": age, "month": month,
                                    "weighted_persons": float(age + month_index + 1)})
            routed_rows.append({"occ_code": "0010", "age": age, "month": month,
                                "stock": float(age - 20), "year": int(month[:4]),
                                "education_group": "non_BA", "school_group": "not_enrolled",
                                "respondent_equivalent": 1.0})
    population = pd.DataFrame(population_rows)
    routed = pd.DataFrame(routed_rows)
    standardized, rows, gap = RUN.fixed_age_standardization(population, routed, months)
    assert gap <= 1e-12
    assert len(rows) == 40
    assert np.isclose(sum(row["preperiod_reference_population_share"] for row in rows), 1)
    assert (standardized.standardization_factor > 0).all()


def test_prepositive_uses_only_declared_pre_months() -> None:
    first = np.array([[1.0, 0.0], [0.0, 5.0]])
    second = np.array([[2.0, 0.0], [1.0, 0.0]])
    keep = RUN.prepositive(first, second, pre=np.array([True, False]))
    assert keep.tolist() == [True, False]


def test_model_inventory_is_exact() -> None:
    assert len(VALIDATE.expected_models()) == 20
    assert "d05_22_25_vs_26_65_fixed_age_family_month" in VALIDATE.expected_models()
    assert "d06_nonenrolled_22_25_vs_nonenrolled_26_54_pooled" in VALIDATE.expected_models()


def test_national_profile_code_has_no_exposure_merge() -> None:
    source = (HERE / "run_cohort_enrollment.py").read_text()
    block = source.split("national_young =", 1)[1].split("audit_rows =", 1)[0]
    assert "beta_quintile" not in block
    assert "occ_code" not in block


def test_source_scan_replaces_wide_march_before_routing(tmp_path: Path) -> None:
    columns = ["YEAR", "MONTH", "AGE", "EMPSTAT", "OCC", "EDUC", "SCHLCOLL", "WTFINL"]
    wide = pd.DataFrame([
        [2019, 3, 23, 10, 111, 110, 5, 999.0],  # must be removed
        [2020, 1, 23, 10, 1111, 110, 5, 20.0],
        [2020, 1, 23, 20, 0, 110, 1, 30.0],  # national population only
    ], columns=columns)
    repair = pd.DataFrame([
        [2019, 3, 23, 10, 111, 110, 5, 10.0],
    ], columns=columns)
    bridge = pd.DataFrame({"census_2010": ["0111"], "census_2018": ["1111"],
                           "bridge_weight": [0.5]})
    wide_path, repair_path, bridge_path = (
        tmp_path / "wide.csv", tmp_path / "repair.csv", tmp_path / "bridge.csv")
    wide.to_csv(wide_path, index=False)
    repair.to_csv(repair_path, index=False)
    bridge.to_csv(bridge_path, index=False)
    routed, population, audit, counters = RUN.scan_sources(
        wide_path, repair_path, bridge_path, {"1111"}, ["2019-03", "2020-01"])
    assert np.isclose(routed.stock.sum(), 25.0)
    assert 999.0 not in routed.stock.tolist()
    assert counters["wide_march_rows_removed"] == 1
    assert np.isclose(population.weighted_persons.sum(), 60.0)
    assert set(audit.source) == {"wide", "march_repair"}
