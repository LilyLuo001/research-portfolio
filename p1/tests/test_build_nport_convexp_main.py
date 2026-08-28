"""Integration smoke test for `build_nport_convexp.main()`.

Every other test in this file's neighbourhood calls `_cell_rows` directly,
because main() needs the network. That gap is not hypothetical: the
UnboundLocalError removed on 2026-08-27 lived in main() for weeks behind a green
suite, and would have crashed the ConvExp rebuild *after* every EDGAR fetch had
been paid for.

So this test patches only the three network boundaries — `ticker_cik_map`,
`pick_nport_for_fund`, `shares_outstanding` — and lets the real main() do the
real aggregation, decile, and write. Anything that breaks the wiring between
those steps fails here rather than three hours into a live run.
"""
import csv
import pathlib

import pandas as pd
import pytest

import build_nport_convexp as b

AAPL = "037833100"
MSFT = "594918104"
GHOST = "999999999"          # holding whose ticker never resolves to a CIK

MEMBER_COLS = ["wave_id", "effective_date", "fund_name", "family",
               "mutual_fund_ticker", "etf_ticker", "source_accession",
               "source_url"]


def _member(wave, eff, fund):
    return {"wave_id": wave, "effective_date": eff, "fund_name": fund,
            "family": "Test Family", "mutual_fund_ticker": "NA",
            "etf_ticker": "NA", "source_accession": "0000000-00-000000",
            "source_url": "https://www.sec.gov/Archives/edgar/data/123/x.htm"}


def _holding(cusip, ticker, shares, val):
    return {"cusip": cusip, "ticker": ticker, "name": ticker or "unknown",
            "shares": shares, "valUSD": val, "asset_cat": "EC"}


def _parsed(acc, asof, holdings):
    return {"accession": acc, "filed": "2021-07-01", "series_name": "S",
            "series_id": "S000001", "report_date": asof,
            "rep_pd_end": asof, "holdings": holdings}


@pytest.fixture
def run(tmp_path, monkeypatch):
    """Drive main() end to end with no network and no writes outside tmp_path."""
    members = [
        # one wave, two funds, overlapping in AAPL -> must aggregate
        _member("W002", "2021-06-11", "Alpha Fund"),
        _member("W002", "2021-06-11", "Beta Fund"),
        # a second wave, so the groupby-per-wave decile path is exercised
        _member("W007", "2021-09-24", "Gamma Fund"),
    ]
    mpath = tmp_path / "waves_members.csv"
    with open(mpath, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MEMBER_COLS)
        w.writeheader()
        w.writerows(members)
    wpath = tmp_path / "waves.csv"
    wpath.write_text("wave_id,effective_date,n_funds,is_anchor\n"
                     "W002,2021-06-11,2,1\nW007,2021-09-24,1,0\n")

    holdings = {
        "Alpha Fund": _parsed("0001-21-000001", "2021-05-31", [
            _holding(AAPL, "AAPL", 1_000.0, 150_000.0),
            _holding(GHOST, "NOSUCH", 500.0, 5_000.0)]),
        "Beta Fund": _parsed("0001-21-000002", "2021-05-31", [
            _holding(AAPL, "AAPL", 3_000.0, 450_000.0)]),
        "Gamma Fund": _parsed("0001-21-000003", "2021-08-31", [
            _holding(MSFT, "MSFT", 2_000.0, 500_000.0)]),
    }

    monkeypatch.setattr(b, "WAVES", wpath)
    monkeypatch.setattr(b, "MEMBERS", mpath)
    monkeypatch.setattr(b, "OUT", tmp_path / "conv_exposure_free.parquet")
    monkeypatch.setattr(b, "DIAG", tmp_path / "diagnostics.md")
    monkeypatch.setattr(b, "NH_FUNDS", tmp_path / "NEED_HUMAN_funds.csv")
    monkeypatch.setattr(b, "NH_STOCKS", tmp_path / "NEED_HUMAN_stocks.csv")
    monkeypatch.setattr(b, "DROPPED_CELLS", tmp_path / "dropped_cells.csv")
    monkeypatch.setattr(b, "DROPPED_SIDECAR", tmp_path / "dropped_cells.csv")
    monkeypatch.setattr(b, "LOGFILE", tmp_path / "run.log")
    monkeypatch.setattr(b, "_setup_run", lambda: None)

    # --- the three network boundaries, and only these ---------------------- #
    monkeypatch.setattr(b, "ticker_cik_map",
                        lambda: {"AAPL": 320193, "MSFT": 789019})
    monkeypatch.setattr(
        b, "pick_nport_for_fund",
        lambda url_cik, fund, eff: (holdings[fund], "series_matched(test)", 123))
    monkeypatch.setattr(
        b, "shares_outstanding",
        lambda cik, on_date: (1_000_000.0, "2021-03-31"))

    b.main()
    return tmp_path


def _df(run):
    return pd.read_parquet(run / "conv_exposure_free.parquet")


def test_main_completes_and_writes_the_parquet(run):
    """The regression: main() used to raise UnboundLocalError on the first cell."""
    assert (run / "conv_exposure_free.parquet").exists()
    assert not _df(run).empty


def test_two_funds_in_one_wave_aggregate_their_shares(run):
    df = _df(run)
    cell = df[(df.cusip == AAPL) & (df.wave_id == "W002")]
    assert len(cell) == 1, "one row per (cusip, wave)"
    # 1,000 (Alpha) + 3,000 (Beta) against 1,000,000 outstanding
    assert cell.iloc[0]["shares_held"] == pytest.approx(4_000.0)
    assert cell.iloc[0]["conv_exp"] == pytest.approx(0.004)
    assert cell.iloc[0]["n_funds"] == 2


def test_val_usd_reaches_the_parquet_under_that_exact_name(run):
    """`val_usd`, not `valusd` — this is the name to declare in the contract."""
    df = _df(run)
    assert "val_usd" in df.columns
    assert "valusd" not in df.columns
    cell = df[(df.cusip == AAPL) & (df.wave_id == "W002")]
    assert cell.iloc[0]["val_usd"] == pytest.approx(600_000.0)


def test_pre_etf_ownership_is_null_not_an_alias_of_conv_exp(run):
    """Integration-level guard for the aliasing defect fixed on the free path."""
    df = _df(run)
    assert df["pre_etf_ownership"].isna().all(), (
        "pre_etf_ownership must stay missing until a real pre-ETF ownership "
        "measure exists; it must never be conv_exp under another name")
    assert not df["pre_etf_ownership"].equals(df["conv_exp"])


def test_unresolvable_ticker_is_dropped_to_need_human_not_imputed(run):
    df = _df(run)
    assert GHOST not in set(df.cusip), "a cell with no CIK must not reach the parquet"
    nh = list(csv.DictReader(open(run / "NEED_HUMAN_stocks.csv", newline="")))
    assert any(r["cusip"] == GHOST for r in nh)


def test_both_waves_survive_to_the_output(run):
    assert set(_df(run).wave_id) == {"W002", "W007"}
