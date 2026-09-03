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
    rows = []
    for index, occ in enumerate(range(100, 105)):
        for age in (22, 40):
            rows.append({
                "YEAR": 2017, "MONTH": 2, "AGE": age, "EMPSTAT": 10,
                "OCC": occ, "OCC2010": 9999 if occ == 100 else 1020,
                "CLASSWKR": 20 if occ == 100 else 22, "WKSTAT": 11,
                "WTFINL": 1.0,
            })
    rows.append({
        "YEAR": 2017, "MONTH": 3, "AGE": 22, "EMPSTAT": 10,
        "OCC": 100, "OCC2010": 1020, "CLASSWKR": 22, "WKSTAT": 11,
        "WTFINL": 100.0,
    })
    return pd.DataFrame(rows)


def lookup_fixture():
    return pd.DataFrame({
        "lookup_role": [CELLS.CURRENT_ROLE] * 5,
        "occ_code": [f"{value:04d}" for value in range(100, 105)],
        "dv_rating_beta": [1.0, 2.0, 3.0, 4.0, 5.0],
        "dv_rating_beta_covered_route_mass": [1.0] * 5,
    })


def bridge_fixture():
    return pd.DataFrame({
        "census_2010": [f"{value:04d}" for value in range(100, 105)],
        "census_2018": [f"{value:04d}" for value in range(100, 105)],
        "bridge_weight": [1.0] * 5,
    })


def test_cells_use_raw_occ_role_join_and_omit_asec_march():
    cells, receipt = CELLS.build_cells(
        fixture(), CONTRACT, lookup_fixture(), bridge_fixture(),
        require_complete_months=False,
    )
    assert receipt["rows_structural_asec_omitted"] == 1
    assert receipt["rows_employed_primary_age"] == 10
    assert receipt["excluded_total_weight"] == 0
    assert receipt["covered_route_mass_fraction"] == 1.0
    assert receipt["general_wage_salary_code20_rows"] == 2
    assert receipt["private_wage_salary_sensitivity_ready"] is False
    assert cells["employment_headcount"].sum() == pytest.approx(10.0)
    assert set(cells["age_group"]) == {"young_22_25", "older_26_65"}
    assert set(cells["lookup_role"]) == {CELLS.CURRENT_ROLE}
    assert set(cells["occupation_key"]) == {
        f"census2018:{value:04d}" for value in range(100, 105)
    }
    assert set(cells["exposure_quintile"]) == {1, 2, 3, 4, 5}
    assert "OCC2010" not in cells.columns and "occ2010" not in cells.columns
    assert receipt["primary_occupation_variable"] == "OCC"
    assert receipt["occ2010_role"] == "sensitivity_only"


def test_nonfull_route_coverage_and_duplicate_lookup_fail_closed():
    frame = fixture()
    extra = pd.DataFrame([
        {"YEAR": 2017, "MONTH": 2, "AGE": age, "EMPSTAT": 10,
         "OCC": 105, "OCC2010": 1020, "CLASSWKR": 22,
         "WKSTAT": 11, "WTFINL": 1.0}
        for age in (22, 40)
    ])
    frame = pd.concat([frame, extra], ignore_index=True)
    bridge = pd.concat([bridge_fixture(), pd.DataFrame({
        "census_2010": ["0105"], "census_2018": ["0105"],
        "bridge_weight": [1.0],
    })], ignore_index=True)
    lookup = lookup_fixture().copy()
    cells, receipt = CELLS.build_cells(
        frame, CONTRACT, lookup, bridge,
        require_complete_months=False,
    )
    assert receipt["status"] == "FAIL_PRIMARY_EXPOSURE_COVERAGE"
    assert receipt["covered_route_mass_fraction"] == pytest.approx(10 / 12)
    assert not cells.empty
    duplicate = pd.concat([lookup_fixture(), lookup_fixture().iloc[[0]]])
    with pytest.raises(ValueError, match=r"duplicate lookup_role\+occ_code"):
        CELLS.build_cells(
            fixture(), CONTRACT, duplicate, bridge_fixture(),
            require_complete_months=False,
        )


def test_role_switches_at_2020_and_occ_code_is_zero_padded():
    frame = fixture()
    frame["YEAR"] = 2020
    lookup = lookup_fixture().assign(lookup_role=CELLS.CURRENT_ROLE)
    cells, _ = CELLS.build_cells(
        frame, CONTRACT, lookup, bridge_fixture(), require_complete_months=False
    )
    assert set(cells["lookup_role"]) == {CELLS.CURRENT_ROLE}
    assert set(cells["occ_code"]) == {"0100", "0101", "0102", "0103", "0104"}


def test_post_rows_are_rejected():
    frame = fixture()
    frame.loc[0, ["YEAR", "MONTH"]] = [2022, 12]
    with pytest.raises(ValueError, match="post-period rows prohibited"):
        CELLS.build_cells(
            frame, CONTRACT, lookup_fixture(), bridge_fixture(),
            require_complete_months=False,
        )


def test_pre2020_one_to_many_bridge_preserves_weight_and_target_units():
    frame = fixture().iloc[:10].copy()
    lookup = pd.DataFrame({
        "lookup_role": [CELLS.CURRENT_ROLE] * 6,
        "occ_code": ["0100", "0101", "0102", "0103", "0104", "0105"],
        "dv_rating_beta": [1.0, 2.0, 3.0, 4.0, 5.0, 1.5],
        "dv_rating_beta_covered_route_mass": [1.0] * 6,
    })
    bridge = pd.DataFrame({
        "census_2010": ["0100", "0100", "0101", "0102", "0103", "0104"],
        "census_2018": ["0100", "0105", "0101", "0102", "0103", "0104"],
        "bridge_weight": [0.7, 0.3, 1.0, 1.0, 1.0, 1.0],
    })
    cells, receipt = CELLS.build_cells(
        frame, CONTRACT, lookup, bridge, require_complete_months=False
    )
    assert cells["employment_headcount"].sum() == pytest.approx(10.0)
    assert cells.loc[cells["occ_code"] == "0105", "employment_headcount"].sum() == pytest.approx(0.6)
    assert receipt["covered_route_mass_fraction"] == pytest.approx(1.0)


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


def test_split_receipt_hash_and_outcome_seal_are_binding(tmp_path):
    source = tmp_path / "pre.csv"
    source.write_text("YEAR,MONTH\n2022,11\n", encoding="utf-8")
    receipt_path = tmp_path / "split.json"
    receipt_path.write_text(json.dumps({
        "status": "PASS_OUTCOME_BLIND_PREPERIOD_SPLIT",
        "cutoff_month": "2022-11",
        "protected_fields_decoded_for_rejected_rows": False,
        "postperiod_rows_written": False,
        "output_sha256": CELLS.sha256_file(source),
    }), encoding="utf-8")
    receipt = CELLS.validate_split_receipt(receipt_path, source)
    assert receipt["status"] == "PASS_OUTCOME_BLIND_PREPERIOD_SPLIT"
    receipt["protected_fields_decoded_for_rejected_rows"] = True
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="post-outcome seal"):
        CELLS.validate_split_receipt(receipt_path, source)
