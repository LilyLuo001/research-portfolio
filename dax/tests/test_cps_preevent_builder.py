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


def test_refuses_when_no_named_employed_code_occurs(tmp_path, capsys):
    """A wholly typo'd code set would classify everyone as jobless — refuse."""
    out = tmp_path / "o.parquet"
    code = B.main(["--extract", str(_extract(tmp_path)), "--output", str(out),
                   "--receipt", str(tmp_path / "none.json"), "--employed-codes", "99"])
    assert code == 2
    assert not out.exists()
    assert "none of --employed-codes" in capsys.readouterr().err


def test_a_partially_absent_code_set_warns_but_proceeds(tmp_path, capsys):
    """A rare code can be legitimately absent from a short window.

    Refusing here would block a correct build; the absence is recorded instead.
    """
    pytest.importorskip("pandas"); pytest.importorskip("pyarrow")
    out = tmp_path / "o.parquet"
    assert B.main(["--extract", str(_extract(tmp_path)), "--output", str(out),
                   "--receipt", str(tmp_path / "none.json"),
                   "--employed-codes", "10,12,13",
                   "--hours-missing-codes", "999"]) == 0
    assert "do not occur in this" in capsys.readouterr().out
    rec = json.loads(out.with_suffix(".receipt.json").read_text())
    assert rec["empstat_named_employed_but_absent"] == [13]


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


# --- hours-vary: the fault found on the SCC before the freeze ---------------
# UHRSWORKT 997 "hours vary" occurs on 3,127 records, every one of them
# EMPLOYED. The first builder zero-filled them, which would have depressed the
# baseline by ~1.65 hours and permanently tightened hours_mde_ceiling (0.5 *
# 0.13 * baseline_hours) by roughly 6%, since the standard refuses to re-freeze.

VARY_ROWS = (
    "YEAR,MONTH,AGE,WTFINL,EMPSTAT,UHRSWORKT,CPSIDP\n"
    "2021,11,22,1000.0,10,40,1\n"      # employed, 40h
    "2021,12,23,1000.0,10,997,2\n"     # employed, HOURS VARY -> unobserved
    "2022,06,24,1000.0,21,999,3\n"     # not employed -> 0h, observed
    "2022,07,25,1000.0,10,30,4\n"      # employed, 30h
)


def _vary_extract(tmp_path):
    p = tmp_path / "vary.csv"
    p.write_text(VARY_ROWS, encoding="utf-8")
    return p


def _build_vary(tmp_path, extra=None):
    out = tmp_path / "v.parquet"
    args = ["--extract", str(_vary_extract(tmp_path)), "--output", str(out),
            "--receipt", str(tmp_path / "none.json"),
            "--employed-codes", "10,12",
            "--hours-missing-codes", "999",
            "--hours-vary-codes", "997"]
    return B.main(args + (extra or [])), out


def test_hours_vary_is_unobserved_not_zero(tmp_path):
    pytest.importorskip("pandas"); pytest.importorskip("pyarrow")
    import pandas as pd, math
    code, out = _build_vary(tmp_path)
    assert code == 0
    df = pd.read_parquet(out)
    vary = df[df["cpsidp"] == 2].iloc[0]
    assert vary["employed"] == 1
    assert vary["hours_observed"] == 0
    assert math.isnan(vary["hours_unconditional"]), "hours-vary must never be zero"
    # the non-employed person IS observed, at a defined zero
    ne = df[df["cpsidp"] == 3].iloc[0]
    assert ne["employed"] == 0 and ne["hours_observed"] == 1
    assert ne["hours_unconditional"] == 0.0


def test_receipt_quantifies_the_zero_fill_bias(tmp_path):
    pytest.importorskip("pandas"); pytest.importorskip("pyarrow")
    code, out = _build_vary(tmp_path)
    assert code == 0
    m = json.loads(out.with_suffix(".receipt.json").read_text())["hours_missingness"]
    assert m["n_employed_hours_unobserved"] == 1
    # observed mean over 3 records: (40 + 0 + 30)/3 = 23.333...
    assert m["baseline_hours_over_observed"] == pytest.approx(23.333333, abs=1e-5)
    # zero-filled over 4 records: (40 + 0 + 0 + 30)/4 = 17.5
    assert m["baseline_hours_if_zero_filled"] == pytest.approx(17.5, abs=1e-9)
    assert m["zero_fill_bias"] < 0, "zero-filling must be recorded as depressing"


def test_employed_with_a_not_in_universe_code_is_refused(tmp_path, capsys):
    """A contradictory combination has no defined treatment — refuse it."""
    bad = tmp_path / "bad.csv"
    bad.write_text("YEAR,MONTH,AGE,WTFINL,EMPSTAT,UHRSWORKT,CPSIDP\n"
                   "2021,11,22,1000.0,10,999,1\n", encoding="utf-8")
    out = tmp_path / "b.parquet"
    code = B.main(["--extract", str(bad), "--output", str(out),
                   "--receipt", str(tmp_path / "none.json"),
                   "--employed-codes", "10", "--hours-missing-codes", "999"])
    assert code == 2
    assert not out.exists()
    assert "employed but carry a not-in-universe" in capsys.readouterr().err
