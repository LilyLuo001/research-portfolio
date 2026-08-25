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
