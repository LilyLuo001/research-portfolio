"""Unit tests for the R3 dynamic design helpers (no protected outcomes)."""
from __future__ import annotations

import importlib.util
import pathlib
import sys
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest


PATH = pathlib.Path(__file__).with_name("run_dynamics.py")
SPEC = importlib.util.spec_from_file_location("yax_r3_dynamics_tested", PATH)
DYN = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = DYN
SPEC.loader.exec_module(DYN)

SELFCHECK_PATH = pathlib.Path(__file__).with_name("selfcheck.py")
SELFCHECK_SPEC = importlib.util.spec_from_file_location(
    "yax_r3_dynamics_selfcheck_tested", SELFCHECK_PATH,
)
SELFCHECK = importlib.util.module_from_spec(SELFCHECK_SPEC)
sys.modules[SELFCHECK_SPEC.name] = SELFCHECK
SELFCHECK_SPEC.loader.exec_module(SELFCHECK)


def test_quarter_mapping_and_reference_omission():
    months = ["2022-07", "2022-08", "2022-09", "2022-10", "2022-11",
              "2023-01", "2023-02", "2023-03"]
    quintiles = np.array([1, 2, 3, 4, 5])
    webb = np.linspace(-1, 1, 5)
    matrix, labels, targets, bins, month_bins = DYN.build_dynamic_regressors(
        quintiles, webb, months,
    )
    assert bins == ["2022Q3", "2023Q1"]
    assert "2022Q4" not in bins
    assert set(month_bins) == {"2022Q3", "2022Q4", "2023Q1"}
    assert matrix.shape == (len(months) * len(quintiles), 10)
    assert len(targets) == 8
    assert "Q5_x_2023Q1" in labels


def test_fully_interacted_quintiles_preserve_q1_reference():
    months = ["2022-10", "2022-11", "2023-01", "2023-02", "2023-03"]
    quintiles = np.array([1, 2, 3, 4, 5])
    matrix, labels, _, _, _ = DYN.build_dynamic_regressors(
        quintiles, np.zeros(5), months,
    )
    q_labels = [label for label in labels if label.startswith("Q")]
    assert q_labels == [
        "Q2_x_2023Q1", "Q3_x_2023Q1", "Q4_x_2023Q1", "Q5_x_2023Q1",
    ]
    reshaped = matrix[:, labels.index("Q5_x_2023Q1")].reshape(5, len(months))
    assert not reshaped[0].any()
    assert reshaped[4, -3:].all()


def test_soc2_calendar_codes_are_nested_and_complete():
    majors = np.array(["11", "11", "15"], object)
    codes = DYN.fe_codes(majors, 4, "SOC2_x_calendar_month")
    assert codes.tolist() == [0, 1, 2, 3, 0, 1, 2, 3, 4, 5, 6, 7]


def test_static_onset_exclusion_is_explicit():
    months = ["2022-11", "2023-01", "2023-02"]
    quintiles = np.array([1, 2, 3, 4, 5])
    matrix, labels = DYN.build_static_regressors(
        quintiles, np.zeros(5), months, onset="2022-12",
    )
    q5 = matrix[:, labels.index("Q5_x_post_from_2022-12")].reshape(5, 3)
    assert q5[4].tolist() == [0.0, 1.0, 1.0]


def test_lower_dimensional_seasonality_adds_declared_44_slopes():
    months = ["2022-10", "2022-11", "2023-01", "2023-02", "2023-03"]
    quintiles = np.array([1, 2, 3, 4, 5])
    matrix, labels = DYN.build_static_regressors(
        quintiles, np.zeros(5), months, onset="2023-01",
        quintile_month_of_year=True,
    )
    assert matrix.shape[1] == 5 + 44
    assert len([value for value in labels if "month_of_year" in value]) == 44
    assert "Q5_x_month_of_year_12" in labels


def test_march_repair_preflight_proves_append_replace_equivalence(tmp_path, monkeypatch):
    columns = ["YEAR", "MONTH", "AGE", "EMPSTAT", "OCC", "WTFINL", "CPSIDP"]
    wide = pd.DataFrame([
        [year, 3, 30, 10, 1234, 0.0, 100000 + year] for year in range(2017, 2022)
    ], columns=columns)
    repair = pd.DataFrame([
        [year, 3, 30, 10, 1234, 100.0, 200000 + year] for year in range(2017, 2022)
    ], columns=columns)
    wide_path = tmp_path / "wide.csv.gz"
    repair_path = tmp_path / "repair.csv.gz"
    wide.to_csv(wide_path, index=False)
    repair.to_csv(repair_path, index=False)
    monkeypatch.setattr(DYN, "EXPECTED_MICRODATA_HASH", DYN.sha256(wide_path))
    monkeypatch.setattr(DYN, "EXPECTED_REPAIR_HASH", DYN.sha256(repair_path))
    receipt = DYN.march_repair_preflight(SimpleNamespace(
        microdata=wide_path, repair_microdata=repair_path,
    ))
    assert receipt["status"].startswith("PASS_APPEND_EQUIVALENT")
    assert receipt["source_audits"]["wide_ASEC"]["analysis_eligible_positive_weight_rows"] == 0
    assert all(value == 0 for value in receipt["eligible_CPSIDP_overlap_by_month"].values())


def test_march_repair_preflight_rejects_positive_wide_stock(tmp_path, monkeypatch):
    columns = ["YEAR", "MONTH", "AGE", "EMPSTAT", "OCC", "WTFINL", "CPSIDP"]
    wide = pd.DataFrame([
        [2017, 3, 30, 10, 1234, 100.0, 100001],
    ], columns=columns)
    repair = pd.DataFrame([
        [year, 3, 30, 10, 1234, 100.0, 200000 + year] for year in range(2017, 2022)
    ], columns=columns)
    wide_path = tmp_path / "wide.csv.gz"
    repair_path = tmp_path / "repair.csv.gz"
    wide.to_csv(wide_path, index=False)
    repair.to_csv(repair_path, index=False)
    monkeypatch.setattr(DYN, "EXPECTED_MICRODATA_HASH", DYN.sha256(wide_path))
    monkeypatch.setattr(DYN, "EXPECTED_REPAIR_HASH", DYN.sha256(repair_path))
    with pytest.raises(RuntimeError, match="append/replace equivalence failed"):
        DYN.march_repair_preflight(SimpleNamespace(
            microdata=wide_path, repair_microdata=repair_path,
        ))


@pytest.mark.parametrize(
    "value, expected",
    [(True, True), (False, False), ("TRUE", True), ("FALSE", False), (1, True), (0, False)],
)
def test_selfcheck_boolean_parser(value, expected):
    assert SELFCHECK.parse_bool(value) is expected


def test_selfcheck_boolean_parser_rejects_missing_value():
    with pytest.raises(RuntimeError, match="unrecognized Boolean"):
        SELFCHECK.parse_bool("")
