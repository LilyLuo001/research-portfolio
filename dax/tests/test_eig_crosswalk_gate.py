"""Regression tests for the measurement-only SOC-vintage gate."""
import importlib.util
from pathlib import Path

import pandas as pd
import pytest


MODULE = Path(__file__).resolve().parents[1] / "w2/exposure_gate/reproduce_eig_crosswalk.py"
SPEC = importlib.util.spec_from_file_location("reproduce_eig_crosswalk", MODULE)
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


def test_source_vintage_weights_apply_to_source_codes():
    rows = pd.DataFrame(
        {
            "AIOE": [1.0, 3.0],
            "tot_emp_2018": [3.0, 1.0],
        }
    )
    assert GATE.weighted_value(rows) == pytest.approx(1.5)


def test_missing_source_employment_never_becomes_a_zero_weighted_value():
    rows = pd.DataFrame(
        {
            "AIOE": [1.0, 3.0],
            "tot_emp_2018": [None, None],
        }
    )
    assert pd.isna(GATE.weighted_value(rows))


def test_archive_reader_refuses_ambiguous_members(tmp_path):
    import zipfile

    archive = tmp_path / "two_books.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("a/Abilities.xlsx", b"a")
        zipped.writestr("b/Abilities.xlsx", b"b")
    with pytest.raises(ValueError, match="expected one"):
        GATE.archive_xlsx(archive, "Abilities.xlsx")


def test_onet_detail_collapse_preserves_named_rater_variants(tmp_path):
    source = tmp_path / "occupation.csv"
    pd.DataFrame(
        {
            "code": ["11-1011.00", "11-1011.01", "11-1021.00"],
            "alpha": [0.0, 1.0, 0.2],
            "beta": [0.5, 1.0, 0.4],
        }
    ).to_csv(source, index=False)
    mapping = pd.DataFrame(
        {
            "soc_2018": ["11-1011", "11-1021"],
            "census_2018": ["0010", "0010"],
        }
    )
    employment = pd.DataFrame(
        {
            "soc_2018": ["11-1011", "11-1021"],
            "target_soc_employment": [3.0, 1.0],
        }
    )
    result = GATE.onet_detail_to_census(
        source, "code", ("alpha", "beta"), mapping, employment
    ).iloc[0]
    # First average detail rows within SOC, then use target-SOC employment.
    assert result.alpha == pytest.approx(0.5 * 0.75 + 0.2 * 0.25)
    assert result.beta == pytest.approx(0.75 * 0.75 + 0.4 * 0.25)
    assert result.target_soc_weight_basis == "oews_2021_employment"


def test_onet_to_census_missing_component_fails_closed(tmp_path):
    source = tmp_path / "occupation.csv"
    pd.DataFrame({"code": ["11-1011.00"], "beta": [0.5]}).to_csv(
        source, index=False
    )
    mapping = pd.DataFrame(
        {
            "soc_2018": ["11-1011", "11-1021"],
            "census_2018": ["0010", "0010"],
        }
    )
    employment = pd.DataFrame(
        {
            "soc_2018": ["11-1011", "11-1021"],
            "target_soc_employment": [3.0, 1.0],
        }
    )
    result = GATE.onet_detail_to_census(
        source, "code", ("beta",), mapping, employment
    ).iloc[0]
    assert pd.isna(result.beta)
    assert result.beta_target_soc_covered_weight == pytest.approx(0.75)
    assert result.beta_target_soc_partial_weighted_sum == pytest.approx(0.375)
