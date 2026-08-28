"""P1-T2 free path: the cell-level drop taxonomy, the dropped-cell sidecar, and
the val_usd column (coverage-audit memo items 2 and 4).

Synthetic cells only — no EDGAR, no network. `_cell_rows` takes its
shares-outstanding lookup as an argument precisely so this is possible.
"""
import ast
import csv
import logging
import pathlib
import sys

import pytest
import yaml

import build_nport_convexp as b

ROOT = pathlib.Path(__file__).resolve().parents[2]


def cell(cusip="000000001", wid="W001", ticker="AAA", shares=1000.0,
         valusd=50000.0, funds=("Fund One",), accs=("0001-24-000001",),
         eff="2021-06-11", asof=("2021-03-31",)):
    return {(cusip, wid): {"cusip": cusip, "wave_id": wid, "effective_date": eff,
                           "ticker": ticker, "name": "A Corp",
                           "shares_held": shares, "valusd": valusd,
                           "funds": set(funds), "accs": set(accs),
                           "asof": set(asof)}}


def so(value, as_of="2021-06-30"):
    return lambda cik, eff: (value, as_of)


# --------------------------------------------------------------------------- #
# computed rows                                                                #
# --------------------------------------------------------------------------- #

def test_computed_row_carries_val_usd_and_conv_exp():
    rows, drops = b._cell_rows(cell(shares=1000.0, valusd=50000.0),
                               {"AAA": "0000320193"}, so(100000.0))
    assert drops == [] and len(rows) == 1
    r = rows[0]
    assert r["conv_exp"] == pytest.approx(0.01)
    assert r["val_usd"] == 50000.0
    assert r["shares_held"] == 1000.0 and r["shares_outstanding"] == 100000.0
    # mcap = implied price (valUSD/shares = 50) x shares_out
    assert r["_mcap"] == pytest.approx(50.0 * 100000.0)
    assert r["source_accessions"] == "0001-24-000001"


# Columns the pipeline emits that the contract does not yet declare.
# contracts.py treats a declared column as mandatory, so these may only be
# declared in the same commit that lands a rebuilt parquet carrying them.
PENDING_COLUMNS = {"val_usd", "holdings_asof_min", "holdings_asof_max"}


def test_contract_and_pipeline_columns_agree_except_the_pending_one():
    """Contract drift in either direction is how this pipeline broke once: a
    stray declared column made the validator demand data that never existed."""
    rows, _ = b._cell_rows(cell(), {"AAA": "0000320193"}, so(100000.0))
    declared = set(yaml.safe_load(
        (ROOT / "ops" / "contracts" / "conv_exposure_free.yaml").read_text())["columns"])
    emitted = set(rows[0]) - {"_mcap"}          # _mcap is dropped before write
    assert declared <= emitted, "contract demands columns the pipeline never emits: " + str(
        sorted(declared - emitted))
    assert emitted - declared == PENDING_COLUMNS, sorted(emitted - declared)


def test_committed_parquet_still_satisfies_the_contract():
    """Gate 2's GO rests on this artifact validating; a contract edit must not
    retroactively fail it before the box rebuilds the parquet."""
    import subprocess
    r = subprocess.run([sys.executable, str(ROOT / "ops" / "runner" / "contracts.py"),
                        "conv_exposure_free",
                        str(ROOT / "p1" / "conv_exposure_free.parquet")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_zero_shares_held_does_not_divide_by_zero():
    rows, _ = b._cell_rows(cell(shares=0.0, valusd=0.0),
                           {"AAA": "0000320193"}, so(100000.0))
    assert rows[0]["conv_exp"] == 0.0 and rows[0]["_mcap"] is None


# --------------------------------------------------------------------------- #
# drop taxonomy — every drop keeps its numerator                               #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("ticker,tcik,shares_out,reason", [
    ("",     {},                    100000.0, "no_ticker"),
    ("AAA",  {},                    100000.0, "ticker_not_in_sec_map"),
    ("AAA",  {"AAA": "0000320193"}, None,     "no_xbrl_shares_outstanding"),
    ("AAA",  {"AAA": "0000320193"}, 0.0,      "no_xbrl_shares_outstanding"),
])
def test_drop_reasons(ticker, tcik, shares_out, reason):
    rows, drops = b._cell_rows(cell(ticker=ticker), tcik, so(shares_out))
    assert rows == [] and len(drops) == 1
    assert drops[0]["reason"] == reason


def test_conv_exp_gt1_is_quarantined_with_the_shares_out_date():
    rows, drops = b._cell_rows(cell(shares=1000.0), {"AAA": "0000320193"},
                               so(1.0, as_of="2021-06-30"))
    assert rows == []
    assert drops[0]["reason"].startswith("conv_exp>1 (1000.000)")
    assert "2021-06-30" in drops[0]["reason"]


def test_every_drop_record_keeps_shares_held_and_val_usd():
    """Memo item 2: without these a recovered denominator cannot be turned back
    into ConvExp, and value-weighted coverage cannot be computed at all."""
    _, drops = b._cell_rows(cell(ticker="", shares=1234.0, valusd=99.5,
                                 funds=("F1", "F2"), accs=("acc-2", "acc-1")),
                            {}, so(100000.0))
    d = drops[0]
    assert d["shares_held"] == 1234.0 and d["val_usd"] == 99.5
    assert d["n_funds"] == 2
    assert d["source_accessions"] == "acc-1;acc-2"        # sorted, ';'-joined
    assert d["effective_date"] == "2021-06-11"


def test_lookup_is_only_consulted_when_a_cik_resolved():
    def boom(cik, eff):                                    # pragma: no cover
        raise AssertionError("shares_outstanding must not be fetched without a CIK")
    rows, drops = b._cell_rows(cell(ticker=""), {}, boom)
    assert rows == [] and drops[0]["reason"] == "no_ticker"


# --------------------------------------------------------------------------- #
# output files                                                                 #
# --------------------------------------------------------------------------- #

def test_need_human_stocks_keeps_its_four_column_schema(tmp_path, monkeypatch):
    monkeypatch.setattr(b, "NH_STOCKS", tmp_path / "NEED_HUMAN_stocks.csv")
    monkeypatch.setattr(b, "DROPPED_SIDECAR", tmp_path / "sidecar.csv")
    _, drops = b._cell_rows(cell(ticker=""), {}, so(1.0))
    b._write_need_human([], drops)
    with open(tmp_path / "NEED_HUMAN_stocks.csv") as f:
        rd = csv.reader(f)
        assert next(rd) == ["cusip", "ticker", "wave_id", "reason"]


def test_sidecar_leads_with_the_columns_recover_denominators_reads(tmp_path, monkeypatch):
    monkeypatch.setattr(b, "DROPPED_SIDECAR", tmp_path / "sidecar.csv")
    _, drops = b._cell_rows(cell(ticker="", shares=1234.0, valusd=99.5), {}, so(1.0))
    b._write_dropped_sidecar(drops)
    with open(tmp_path / "sidecar.csv") as f:
        rows = list(csv.DictReader(f))
    with open(tmp_path / "sidecar.csv") as f:
        header = next(csv.reader(f))
    assert header[:4] == ["cusip", "wave_id", "shares_held", "val_usd"]
    assert rows[0]["shares_held"] == "1234.0" and rows[0]["val_usd"] == "99.5"


def test_sidecar_is_written_alongside_need_human(tmp_path, monkeypatch):
    monkeypatch.setattr(b, "NH_STOCKS", tmp_path / "NEED_HUMAN_stocks.csv")
    monkeypatch.setattr(b, "DROPPED_SIDECAR", tmp_path / "sidecar.csv")
    _, drops = b._cell_rows(cell(ticker=""), {}, so(1.0))
    b._write_need_human([], drops)
    assert (tmp_path / "sidecar.csv").exists()


# --------------------------------------------------------------------------- #
# import safety                                                                #
# --------------------------------------------------------------------------- #

def test_importing_the_module_does_not_open_the_committed_run_log():
    """build_nport_convexp.log is committed and parsed by recover_denominators.py
    for the CONVEXP_GT1 shares_held; the handler opens it mode='w'."""
    attached = [h for h in logging.getLogger().handlers
                if isinstance(h, logging.FileHandler)
                and pathlib.Path(getattr(h, "baseFilename", "")) == b.LOGFILE]
    assert attached == []
    assert callable(b._setup_run)


def test_source_file_is_one_program_not_two():
    """Three artifacts in this pipeline have been damaged by a second program
    concatenated onto the first (the contract YAML, this file's duplicate main(),
    build_waves.py's shadowing main()). A stray module-level docstring after the
    imports is that defect's fingerprint."""
    tree = ast.parse((ROOT / "p1" / "t2_free" / "build_nport_convexp.py").read_text())
    stray = [n.lineno for n in tree.body[1:]
             if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
             and isinstance(n.value.value, str)]
    assert stray == []
    defs = {}
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            defs.setdefault(n.name, []).append(n.lineno)
    assert not {k: v for k, v in defs.items() if len(v) > 1}


# --------------------------------------------------------------------------- #
# v2.1d item 1 — holdings are dated by repPdDate, never by the filing date     #
# --------------------------------------------------------------------------- #
NPORT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<edgarSubmission xmlns="http://www.sec.gov/edgar/nport">
  <formData>
    <genInfo>
      <seriesName>Example Equity Fund</seriesName>
      <seriesId>S000012345</seriesId>
      <repPdEnd>2021-06-30</repPdEnd>
      <repPdDate>2021-03-31</repPdDate>
    </genInfo>
    <invstOrSecs>
      <invstOrSec>
        <name>A Corp</name>
        <cusip>037833100</cusip>
        <identifiers><ticker value="AAA"/></identifiers>
        <balance>1000</balance>
        <units>NS</units>
        <valUSD>50000</valUSD>
        <assetCat>EC</assetCat>
      </invstOrSec>
    </invstOrSecs>
  </formData>
</edgarSubmission>
"""


def _parse(xml, monkeypatch, filed="2021-05-28"):
    monkeypatch.setattr(b, "http_get", lambda *a, **k: xml)
    return b.parse_nport("0000320193", {"accession": "0001-21-000001",
                                        "filed": filed, "primary": "primary_doc.xml"})


def test_parse_nport_carries_the_holdings_asof_date(monkeypatch):
    p = _parse(NPORT_XML, monkeypatch)
    assert p["report_date"] == "2021-03-31"      # repPdDate — dates the shares
    assert p["rep_pd_end"] == "2021-06-30"       # repPdEnd  — dates the period
    assert p["filed"] == "2021-05-28"
    assert b.holdings_asof(p) == "2021-03-31"


def test_holdings_asof_refuses_rather_than_falling_back_to_filed(monkeypatch):
    p = _parse(NPORT_XML.replace("<repPdDate>2021-03-31</repPdDate>", ""),
               monkeypatch)
    with pytest.raises(b.MissingAsOfDate) as e:
        b.holdings_asof(p)
    assert "2021-05-28" in str(e.value)          # names the date it REFUSED to use


def test_cells_carry_the_asof_date_and_undated_cells_are_dropped():
    rows, _ = b._cell_rows(cell(asof=("2021-03-31",)), {"AAA": "0000320193"},
                           so(100000.0))
    assert rows[0]["holdings_asof_min"] == rows[0]["holdings_asof_max"] == "2021-03-31"

    # two funds whose last pre-conversion N-PORTs are different months: the
    # spread must be visible, because one factor date cannot serve both
    rows, _ = b._cell_rows(cell(asof=("2021-03-31", "2021-02-28")),
                           {"AAA": "0000320193"}, so(100000.0))
    assert rows[0]["holdings_asof_min"] == "2021-02-28"
    assert rows[0]["holdings_asof_max"] == "2021-03-31"

    _, drops = b._cell_rows(cell(asof=()), {"AAA": "0000320193"}, so(100000.0))
    assert [d["reason"] for d in drops] == ["no_holdings_asof"]
