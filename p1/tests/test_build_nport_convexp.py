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
         eff="2021-06-11"):
    return {(cusip, wid): {"cusip": cusip, "wave_id": wid, "effective_date": eff,
                           "ticker": ticker, "name": "A Corp",
                           "shares_held": shares, "valusd": valusd,
                           "funds": set(funds), "accs": set(accs)}}


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


# The only column the pipeline emits that the contract does not yet declare.
# contracts.py treats a declared column as mandatory, so `val_usd` may only be
# declared in the same commit that lands a rebuilt parquet carrying it.
PENDING_COLUMNS = {"val_usd"}


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
# fund-level asset-class filter (coverage-audit item 5 / register W-05b)       #
# --------------------------------------------------------------------------- #

MEMBERS = [
    {"wave_id": "W029", "fund_name": "US Fund", "effective_date": "2023-01-05"},
    {"wave_id": "W029", "fund_name": "Intl Fund", "effective_date": "2023-01-05"},
    {"wave_id": "W020", "fund_name": "Mirae Fund", "effective_date": "2023-04-15"},
]
EVENTS_META = [
    {"fund_name": "US Fund", "asset_class": "equity_US"},
    {"fund_name": "Intl Fund", "asset_class": "equity_intl"},
    {"fund_name": "Mirae Fund", "asset_class": "equity_intl"},
]


def test_nothing_is_excluded_by_default():
    """The sample definition is the owner's call; the pipeline does not pick one."""
    kept, dropped = b.filter_members_by_asset_class(MEMBERS, EVENTS_META, [])
    assert len(kept) == 3 and dropped == []


def test_filtering_keeps_the_us_half_of_a_mixed_wave():
    """The whole reason this lives before aggregation: cells are summed per
    (cusip, wave) across the wave's funds, so a mixed wave cannot be split
    afterwards — a filter on the finished parquet can only drop W029 entirely."""
    kept, dropped = b.filter_members_by_asset_class(
        MEMBERS, EVENTS_META, ["equity_intl"])
    assert [m["fund_name"] for m in kept] == ["US Fund"]
    assert {m["fund_name"] for m in dropped} == {"Intl Fund", "Mirae Fund"}
    assert "W029" in {m["wave_id"] for m in kept}          # the wave survives


def test_filter_is_case_insensitive_and_ignores_blank_entries():
    kept, _ = b.filter_members_by_asset_class(
        MEMBERS, EVENTS_META, ["  EQUITY_INTL ", ""])
    assert [m["fund_name"] for m in kept] == ["US Fund"]


def test_a_fund_with_no_recorded_asset_class_is_kept_not_silently_dropped():
    """25 rows of events_merged carry a blank asset_class. Dropping them on a
    filter they were never classified for would be a silent sample change."""
    members = MEMBERS + [{"wave_id": "W050", "fund_name": "Unknown Fund",
                          "effective_date": "2024-01-01"}]
    kept, _ = b.filter_members_by_asset_class(members, EVENTS_META, ["equity_intl"])
    assert "Unknown Fund" in {m["fund_name"] for m in kept}


def test_kept_members_carry_their_asset_class_for_the_manifest():
    kept, _ = b.filter_members_by_asset_class(MEMBERS, EVENTS_META, ["equity_intl"])
    assert kept[0]["asset_class"] == "equity_US"
