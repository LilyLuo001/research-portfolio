import importlib.util
import json
import pathlib
import sys

import pandas as pd
import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "w2" / "build_young_relative_employment_cells.py"
SPEC = importlib.util.spec_from_file_location("build_young_relative_employment_cells", PATH)
assert SPEC and SPEC.loader
CELLS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CELLS
SPEC.loader.exec_module(CELLS)
CONTRACT = json.loads(
    (ROOT / "memo" / "power_calcs" / "cps_recode_contract_v1.json")
    .read_text(encoding="utf-8")
)


def fixture():
    return pd.DataFrame({
        "YEAR": [2017, 2017, 2017, 2017, 2017, 2017],
        "MONTH": [2, 2, 2, 2, 2, 3],
        "AGE": [22, 40, 25, 30, 30, 22],
        "EMPSTAT": [10, 12, 21, 10, 10, 10],
        "OCC": [1005, 1005, 1005, 0, 1005, 1005],
        "OCC2010": [1020, 1020, 1020, 9999, 1020, 1020],
        "CLASSWKR": [22, 23, 22, 22, 20, 22],
        "WKSTAT": [11, 13, 50, 11, 11, 11],
        "WTFINL": [2.0, 3.0, 4.0, 5.0, 7.0, 100.0],
    })


def test_cells_use_employed_codes_weights_age_groups_and_omit_asec_march():
    cells, receipt = CELLS.build_cells(fixture(), CONTRACT, require_complete_months=False)
    assert receipt["rows_structural_asec_omitted"] == 1
    assert receipt["rows_employed_primary_age"] == 4
    assert receipt["rows_unmatched_occupation"] == 1
    assert receipt["general_wage_salary_code20_rows"] == 1
    assert receipt["private_wage_salary_sensitivity_ready"] is False
    assert cells["employment_headcount"].sum() == pytest.approx(12.0)
    assert set(cells["age_group"]) == {"young_22_25", "older_26_65"}
    assert 9999 not in set(cells["occ2010"])


def test_post_rows_are_rejected():
    frame = fixture()
    frame.loc[0, ["YEAR", "MONTH"]] = [2022, 12]
    with pytest.raises(ValueError, match="post-period rows prohibited"):
        CELLS.build_cells(frame, CONTRACT, require_complete_months=False)


def test_file_seal_checks_only_dates_before_refusing_post(monkeypatch, tmp_path):
    calls = []

    def fake_read_csv(path, usecols):
        calls.append(tuple(usecols))
        return pd.DataFrame({"YEAR": [2022], "MONTH": [12]})

    monkeypatch.setattr(pd, "read_csv", fake_read_csv)
    with pytest.raises(ValueError, match="REFUSED before reading outcome columns"):
        CELLS.read_preperiod_source(tmp_path / "post.csv.gz")
    assert calls == [("YEAR", "MONTH")]


def test_expected_preperiod_has_five_asec_gaps():
    months = CELLS.expected_pre_months(set(CONTRACT["structural_gaps"]["omit_months"]))
    assert len(months) == 66
    assert months[0] == "2017-01" and months[-1] == "2022-11"
    assert all(f"{year}-03" not in months for year in range(2017, 2022))
