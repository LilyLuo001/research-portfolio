"""The OEWS builder must refuse the traps this source actually sets."""

import hashlib
import importlib.util
import io
import json
import pathlib
import zipfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("oews", ROOT / "w2" / "build_oews_wages.py")
assert SPEC and SPEC.loader
B = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(B)

HEADER = ["OCC_CODE", "OCC_TITLE", "O_GROUP", "TOT_EMP", "A_MEAN", "H_MEAN",
          "ANNUAL", "HOURLY"]
ROWS = [
    ["00-0000", "All Occupations", "total", "139099570", "58260", "28.01", "", ""],
    ["15-0000", "Computer Occupations", "major", "4600000", "97430", "46.84", "", ""],
    ["15-1252", "Software Developers", "detailed", "1425900", "120730", "58.04", "TRUE", ""],
    ["29-1141", "Registered Nurses", "detailed", "3047530", "82750", "39.78", "", ""],
    ["35-3023", "Fast Food Workers", "detailed", "3673500", "*", "11.47", "", "TRUE"],
    ["29-1024", "Prosthodontists", "detailed", "660", "#", "#", "TRUE", ""],
    # 41-9012 Models in the real 2021 national file releases NEITHER mean.
    ["41-9012", "Models", "detailed", "3000", "*", "*", "", ""],
]


def _xlsx(sheet_name="national_M2021_dl", header=HEADER, rows=ROWS) -> bytes:
    """Minimal xlsx the stdlib reader can parse: inline strings, no shared table."""
    def cell(col, val):
        ref = f"{chr(65 + col)}1"
        return f'<c r="{ref}" t="inlineStr"><is><t>{val}</t></is></c>'
    xml_rows = []
    for r, line in enumerate([header] + rows, start=1):
        cells = "".join(
            f'<c r="{chr(65+i)}{r}" t="inlineStr"><is><t>{v}</t></is></c>'
            for i, v in enumerate(line))
        xml_rows.append(f'<row r="{r}">{cells}</row>')
    sheet = ('<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org'
             '/spreadsheetml/2006/main"><sheetData>' + "".join(xml_rows)
             + "</sheetData></worksheet>")
    wb = ('<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org'
          '/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org'
          f'/officeDocument/2006/relationships"><sheets><sheet name="{sheet_name}"'
          ' sheetId="1" r:id="rId1"/></sheets></workbook>')
    rels = ('<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats'
            '.org/package/2006/relationships"><Relationship Id="rId1" Target='
            '"worksheets/sheet1.xml" Type="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships/worksheet"/></Relationships>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/workbook.xml", wb)
        z.writestr("xl/_rels/workbook.xml.rels", rels)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    return buf.getvalue()


def _archive(tmp_path, **kw) -> pathlib.Path:
    p = tmp_path / "oesm21nat.zip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("oesm21nat/national_M2021_dl.xlsx", _xlsx(**kw))
    return p


def _run(tmp_path, archive, extra=None):
    out = tmp_path / "oews.parquet"
    code = B.main(["--archive", str(archive), "--output", str(out),
                   "--allow-unpinned"] + (extra or []))
    return code, out


def test_an_html_block_page_cannot_masquerade_as_the_archive(tmp_path):
    """BLS answers an unidentified agent with a 1,323-byte Access Denied page.

    Without --allow-unpinned the SHA check refuses it, which is the whole
    class: this builder never downloads, so it cannot be fooled mid-flight.
    """
    fake = tmp_path / "oesm21nat.zip"
    fake.write_bytes(b"<html><body>Access Denied</body></html>")
    out = tmp_path / "o.parquet"
    assert B.main(["--archive", str(fake), "--output", str(out)]) == 2
    assert not out.exists()


def test_o_group_filter_prevents_double_counting(tmp_path):
    pytest.importorskip("pandas"); pytest.importorskip("pyarrow")
    import pandas as pd
    code, out = _run(tmp_path, _archive(tmp_path))
    assert code == 0
    df = pd.read_parquet(out)
    assert len(df) == 5, "total and major rows must be excluded"
    assert set(df["occ_code"]) == {"15-1252", "29-1141", "35-3023", "29-1024", "41-9012"}
    rec = json.loads(out.with_suffix(".receipt.json").read_text())
    assert rec["rows_by_o_group"]["total"] == 1
    assert rec["rows_by_o_group"]["major"] == 1
    assert rec["o_group_filter"] == "detailed"


def test_suppression_markers_are_never_coerced_to_zero(tmp_path):
    """'*' not released and '#' at-or-above-top-code are not numbers.

    Zeroing them understates a wage bill; dropping them silently loses
    occupations. Both are preserved as null with a flag and counted.
    """
    pytest.importorskip("pandas"); pytest.importorskip("pyarrow")
    import pandas as pd
    code, out = _run(tmp_path, _archive(tmp_path))
    assert code == 0
    df = pd.read_parquet(out).set_index("occ_code")
    assert pd.isna(df.loc["35-3023", "a_mean"])
    assert df.loc["35-3023", "a_mean_suppression"] == "not_released"
    assert pd.isna(df.loc["29-1024", "a_mean"])
    assert df.loc["29-1024", "a_mean_suppression"] == "at_or_above_top_code"
    assert (df["a_mean"] == 0).sum() == 0
    rec = json.loads(out.with_suffix(".receipt.json").read_text())
    assert rec["suppression_counts"]["not_released"] == 3
    assert rec["suppression_counts"]["at_or_above_top_code"] == 2


def test_annual_and_hourly_flags_are_carried_not_dropped(tmp_path):
    pytest.importorskip("pandas"); pytest.importorskip("pyarrow")
    import pandas as pd
    code, out = _run(tmp_path, _archive(tmp_path))
    df = pd.read_parquet(out).set_index("occ_code")
    assert bool(df.loc["15-1252", "annual_only"]) is True
    assert bool(df.loc["35-3023", "hourly_only"]) is True
    assert bool(df.loc["29-1141", "annual_only"]) is False


def test_a_missing_required_column_reports_the_observed_header(tmp_path):
    short = [c for c in HEADER if c != "O_GROUP"]
    rows = [[v for i, v in enumerate(r) if HEADER[i] != "O_GROUP"] for r in ROWS]
    code, out = _run(tmp_path, _archive(tmp_path, header=short, rows=rows))
    assert code == 2
    assert not out.exists()


def test_an_unknown_o_group_value_is_refused_with_what_was_seen(tmp_path):
    code, out = _run(tmp_path, _archive(tmp_path), extra=["--o-group", "nonexistent"])
    assert code == 2
    assert not out.exists()


def test_no_crosswalk_is_invented(tmp_path):
    """OEWS is SOC coded; O*NET is 8-digit. That join is a separate artifact."""
    pytest.importorskip("pandas"); pytest.importorskip("pyarrow")
    import pandas as pd
    code, out = _run(tmp_path, _archive(tmp_path))
    df = pd.read_parquet(out)
    assert not any("onet" in c.lower() for c in df.columns)
    rec = json.loads(out.with_suffix(".receipt.json").read_text())
    assert rec["crosswalk"].startswith("NOT PERFORMED")


def test_an_occupation_releasing_neither_mean_is_a_known_gap_not_a_zero(tmp_path):
    """41-9012 Models releases neither an annual nor an hourly mean.

    Surfaced by the first real SCC run. A wage-bill step reaching for
    `a_mean or h_mean * 2080` gets nothing for such an occupation; unless the
    receipt names it, that becomes a silent zero in the wage bill rather than a
    known gap.
    """
    pytest.importorskip("pandas"); pytest.importorskip("pyarrow")
    import pandas as pd
    code, out = _run(tmp_path, _archive(tmp_path))
    assert code == 0
    rec = json.loads(out.with_suffix(".receipt.json").read_text())
    assert "41-9012" in rec["no_wage_released"]
    assert "29-1024" in rec["no_wage_released"], "top-coded both ways is also a gap"
    assert "15-1252" not in rec["no_wage_released"]
    assert "KNOWN GAP" in rec["no_wage_rule"]
    df = pd.read_parquet(out).set_index("occ_code")
    assert pd.isna(df.loc["41-9012", "a_mean"]) and pd.isna(df.loc["41-9012", "h_mean"])
