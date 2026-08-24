"""The pre-event CPS builder must never guess a recode."""

import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("cps_pre", ROOT / "w2" / "build_cps_preevent.py")
assert SPEC and SPEC.loader
B = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(B)

ROWS = (
    "YEAR,MONTH,AGE,WTFINL,EMPSTAT,UHRSWORKT,CPSIDP\n"
    "2021,11,22,1000.5,10,40,1\n"
    "2021,12,23,1100.0,21,999,2\n"     # not employed, hours missing code
    "2022,06,24,900.25,12,35,3\n"
    "2023,02,25,1200.0,32,999,4\n"     # not employed
    "2023,06,22,1300.0,10,40,5\n"      # OUTSIDE the frozen window
)


def _extract(tmp_path):
    p = tmp_path / "cps.csv"
    p.write_text(ROWS, encoding="utf-8")
    return p


def test_code_ranges_parse():
    assert B._codes("10,12") == {10, 12}
    assert B._codes("10-12") == {10, 11, 12}
    assert B._codes("") == set()


def test_refuses_without_employed_codes(tmp_path, capsys):
    out = tmp_path / "o.parquet"
    code = B.main(["--extract", str(_extract(tmp_path)), "--output", str(out),
                   "--receipt", str(tmp_path / "none.json")])
    assert code == 2
    assert not out.exists()
    assert "never guessed" in capsys.readouterr().err


def test_refuses_a_code_that_does_not_occur(tmp_path, capsys):
    """A typo'd code must fail loudly, not silently classify everyone as jobless."""
    out = tmp_path / "o.parquet"
    code = B.main(["--extract", str(_extract(tmp_path)), "--output", str(out),
                   "--receipt", str(tmp_path / "none.json"), "--employed-codes", "99"])
    assert code == 2
    assert not out.exists()
    assert "do not occur" in capsys.readouterr().err


def test_refuses_an_unpinned_extract(tmp_path, capsys):
    receipt = tmp_path / "rec.json"
    receipt.write_text(json.dumps({"files": {"data": {"sha256": "0" * 64}}}))
    out = tmp_path / "o.parquet"
    code = B.main(["--extract", str(_extract(tmp_path)), "--output", str(out),
                   "--receipt", str(receipt), "--employed-codes", "10,12"])
    assert code == 2
    assert not out.exists()
    assert "does not match the pinned" in capsys.readouterr().err


def test_builds_the_frozen_window_with_the_columns_the_standard_needs(tmp_path):
    pytest.importorskip("pandas"); pytest.importorskip("pyarrow")
    import pandas as pd
    out = tmp_path / "o.parquet"
    assert B.main(["--extract", str(_extract(tmp_path)), "--output", str(out),
                   "--receipt", str(tmp_path / "none.json"),
                   "--employed-codes", "10,12",
                   "--hours-missing-codes", "999"]) == 0
    df = pd.read_parquet(out)
    # freeze_power_standard.py requires exactly these
    assert {"month", "age", "wtfinl", "employed", "hours_unconditional"} <= set(df.columns)
    # the 2023-06 row is outside 2021-11..2023-02 and must be dropped
    assert df["month"].max() == "2023-02"
    assert len(df) == 4
    # unconditional hours: zero for the non-employed, not missing
    assert df.loc[df["employed"] == 0, "hours_unconditional"].eq(0.0).all()
    assert df.loc[df["employed"] == 1, "hours_unconditional"].tolist() == [40.0, 35.0]
    rec = json.loads((out.with_suffix(".receipt.json")).read_text())
    assert rec["recodes"]["employed_empstat_codes"] == [10, 12]
    assert rec["empstat_treated_not_employed"] == [21, 32]
    assert rec["scope"].startswith("PRE-EVENT WINDOW ONLY")
