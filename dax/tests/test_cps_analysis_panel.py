"""The analysis panel must not repeat the pre-event builder's assumptions.

Extract 7's inventory found three things that would each have produced a wrong
panel silently: EMPSTAT carries eight codes rather than the two the pre-event
builder retained as employed; UHRSWORKT mixes sentinels with a genuine zero;
and one calendar month, 2025-10, has no CPS sample at all.
"""

import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "cps_analysis", ROOT / "w2" / "build_cps_analysis_panel.py")
assert SPEC and SPEC.loader
B = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(B)

HEAD = "YEAR,MONTH,AGE,WTFINL,EMPSTAT,UHRSWORKT,CPSIDP,OCC2010\n"
# every EMPSTAT code the real extract carries, including armed forces as "1"
ROWS = (
    "2025,9,22,1000,10,40,1,1010\n"
    "2025,9,23,1000,1,40,2,1010\n"      # armed forces
    "2025,9,24,1000,21,999,3,1010\n"    # unemployed, experienced
    "2025,9,25,1000,34,999,4,1010\n"    # NILF
    "2025,11,22,1000,12,0,5,1010\n"     # employed, GENUINE zero hours
    "2025,11,23,1000,10,997,6,1010\n"   # employed, hours vary
    "2025,12,24,1000,32,999,7,1010\n"
)


def _extract(tmp_path, body=ROWS):
    p = tmp_path / "cps.csv"
    p.write_text(HEAD + body, encoding="utf-8")
    return p


def _run(tmp_path, extra=None, body=ROWS):
    out = tmp_path / "panel.parquet"
    code = B.main(["--extract", str(_extract(tmp_path, body)), "--output", str(out),
                   "--receipt", str(tmp_path / "none.json"),
                   "--employed-codes", "10,12"] + (extra or []))
    return code, out


def test_month_index_is_absolute_so_a_gap_shows_as_a_jump():
    assert B.month_index("2025-11") - B.month_index("2025-09") == 2
    assert B.month_index("2026-01") - B.month_index("2025-12") == 1


def test_the_missing_month_is_recorded_and_flagged_in_the_data(tmp_path):
    """2025-10 has no CPS sample. A naive lag would span it as one step."""
    pytest.importorskip("pandas"); pytest.importorskip("pyarrow")
    import pandas as pd
    code, out = _run(tmp_path)
    assert code == 0
    rec = json.loads(out.with_suffix(".receipt.json").read_text())
    assert rec["missing_months"] == ["2025-10"]
    assert rec["months_present"] == 3
    assert rec["calendar_months_spanned"] == 4
    df = pd.read_parquet(out)
    # rows in 2025-11 must be flagged: their preceding month is absent
    nov = df[df["month"] == "2025-11"]
    assert (nov["prev_month_present"] == 0).all()
    dec = df[df["month"] == "2025-12"]
    assert (dec["prev_month_present"] == 1).all()


def test_no_rows_are_dropped_for_being_non_employed(tmp_path):
    """Filtering to {10,12} would delete the employment rate's denominator."""
    pytest.importorskip("pandas"); pytest.importorskip("pyarrow")
    import pandas as pd
    code, out = _run(tmp_path)
    df = pd.read_parquet(out)
    assert len(df) == 7, "every row retained; employment is flagged, not filtered"
    assert df["employed"].sum() == 3
    rec = json.loads(out.with_suffix(".receipt.json").read_text())
    assert rec["recodes"]["empstat_treated_not_employed"] == [1, 21, 32, 34]


def test_a_genuine_zero_hours_is_kept_and_hours_vary_is_not(tmp_path):
    """0 is a real value for an employed person; 997 is unobserved."""
    pytest.importorskip("pandas"); pytest.importorskip("pyarrow")
    import pandas as pd
    code, out = _run(tmp_path)
    df = pd.read_parquet(out).set_index("cpsidp")
    assert df.loc[5, "employed"] == 1
    assert df.loc[5, "hours_unconditional"] == 0.0
    assert df.loc[5, "hours_observed"] == 1, "a real zero is observed"
    assert df.loc[6, "employed"] == 1
    assert pd.isna(df.loc[6, "hours_unconditional"])
    assert df.loc[6, "hours_observed"] == 0


def test_asec_rows_are_refused_not_silently_mixed(tmp_path):
    body = HEAD.rstrip("\n") + ",ASECFLAG\n" + "2025,9,22,1000,10,40,1,1010,1\n"
    p = tmp_path / "asec.csv"
    p.write_text(body, encoding="utf-8")
    out = tmp_path / "p.parquet"
    assert B.main(["--extract", str(p), "--output", str(out),
                   "--receipt", str(tmp_path / "none.json"),
                   "--employed-codes", "10,12"]) == 2
    assert not out.exists()


def test_an_employed_row_with_a_not_in_universe_hours_code_is_refused(tmp_path):
    code, out = _run(tmp_path, body="2025,9,22,1000,10,999,1,1010\n")
    assert code == 2
    assert not out.exists()
