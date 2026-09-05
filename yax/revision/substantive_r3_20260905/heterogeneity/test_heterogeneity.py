"""Unit tests for the pure CHAR-03/CHAR-04 construction helpers."""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import numpy as np
import pandas as pd


HERE = pathlib.Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("yax_r3_heterogeneity_tested", HERE / "run_heterogeneity.py")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_industry_boundaries_and_invalid_codes():
    codes = pd.Series([10, 32, 40, 50, 60, 100, 392, 400, 472, 500, 571, 580, 691,
                       700, 712, 721, 760, 761, 791, 800, 810, 812, 893, 900, 932,
                       0, 940, 960, 998])
    groups = MODULE.industry_group(codes)
    assert groups.iloc[0] == groups.iloc[1] == "agriculture"
    assert groups.iloc[2] == groups.iloc[3] == "mining"
    assert groups.iloc[4] == "construction"
    assert groups.iloc[5] == groups.iloc[6] == "manufacturing"
    assert groups.iloc[21] == groups.iloc[22] == "professional_related_services"
    assert groups.iloc[23] == groups.iloc[24] == "public_administration"
    assert set(groups.iloc[25:]) == {"__invalid__"}
    assert len(set(groups.iloc[:25])) == 13


def test_education_and_enrollment_contracts():
    values = pd.Series([0, 1, 2, 73, 110, 111, 120, 125, 999])
    observed = MODULE.education_group(values).tolist()
    assert observed == ["__invalid__", "__invalid__", "non_BA", "non_BA", "non_BA",
                        "BA_plus", "BA_plus", "BA_plus", "__invalid__"]
    school = MODULE.school_group(pd.Series([0, 1, 2, 3, 4, 5, 9])).tolist()
    assert school == ["__invalid__", "enrolled", "enrolled", "enrolled", "enrolled",
                      "not_enrolled", "__invalid__"]


def test_panel_keeps_one_sided_and_zero_month_cells():
    frame = pd.DataFrame({
        "occ_code": ["0010", "0010", "0020"],
        "month": ["2023-01", "2023-02", "2023-01"],
        "age_group": ["young", "older", "young"],
        "stock": [2.0, 3.0, 1.0],
    })
    rows, young, older = MODULE.build_panel(frame, ["occ_code"], ["2023-01", "2023-02"])
    assert rows.occ_code.tolist() == ["0010", "0020"]
    np.testing.assert_array_equal(young, np.array([[2.0, 0.0], [1.0, 0.0]]))
    np.testing.assert_array_equal(older, np.array([[0.0, 3.0], [0.0, 0.0]]))


def test_paired_summary_uses_joint_influence():
    signs = np.array([[1.0, 1.0], [1.0, -1.0], [-1.0, 1.0], [-1.0, -1.0]])
    left = {"name": "left", "coefficient": 2.0, "influence": np.array([0.2, 0.3])}
    right = {"name": "right", "coefficient": 1.5, "influence": np.array([0.1, 0.1])}
    row = MODULE.paired_summary("left_minus_right", left, right, signs)
    assert np.isclose(row["coefficient_difference"], 0.5)
    assert np.isclose(row["paired_analytic_se"], np.sqrt(0.1 ** 2 + 0.2 ** 2))
    assert row["common_occupation_multipliers"] is True
