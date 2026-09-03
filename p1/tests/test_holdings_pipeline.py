"""P1-T2 WRDS pipeline, driven end to end against a fake connection.

No credentials, no network, no CRSP — every database call goes through an
injected object, which is why this file can exist at all: the real client speaks
PostgreSQL on 9737 and can never run in a Claude Code session.

These tests pin the things that would corrupt ConvExp silently: the shrout unit
factor, aggregation across funds, the lookahead ban in the SQL, and the refusal
to impute a missing denominator.
"""
import json
import pathlib
import subprocess
import sys

import pandas as pd
import pytest

import holdings_pipeline as hp

ROOT = pathlib.Path(__file__).resolve().parents[2]

S_FUND = hp.SCHEMA["fund_header"]
S_HOLD = hp.SCHEMA["holdings"]
S_MSF = hp.SCHEMA["monthly_stock"]


class FakeDB:
    """Dispatches on the SQL the real builders produce, so the builders are
    exercised rather than bypassed."""

    def __init__(self, funds=None, holdings=None, shrout=None):
        self.funds = funds if funds is not None else pd.DataFrame(
            columns=[S_FUND["fundno"], S_FUND["name"], S_FUND["ticker"]])
        self.holdings = holdings if holdings is not None else pd.DataFrame(
            columns=[S_HOLD["fundno"], S_HOLD["permno"], S_HOLD["shares"],
                     S_HOLD["report_date"]])
        self.shrout = shrout if shrout is not None else pd.DataFrame(
            columns=[S_MSF["permno"], S_MSF["shrout"], S_MSF["price"], S_MSF["date"]])
        self.seen = []

    def raw_sql(self, sql):
        self.seen.append(" ".join(sql.split()))
        if S_FUND["table"] in sql:
            return self.funds.copy()
        if "last_rpt" in sql:
            return self.holdings.copy()
        return self.shrout.copy()


def funds_df(rows):
    return pd.DataFrame(rows, columns=[S_FUND["fundno"], S_FUND["name"], S_FUND["ticker"]])


def holdings_df(rows):
    return pd.DataFrame(rows, columns=[S_HOLD["fundno"], S_HOLD["permno"],
                                       S_HOLD["shares"], S_HOLD["report_date"]])


def shrout_df(rows):
    return pd.DataFrame(rows, columns=[S_MSF["permno"], S_MSF["shrout"],
                                       S_MSF["price"], S_MSF["date"]])


def event(name="A Fund", ticker="AAAAX", acc="0001-24-000001"):
    return {"fund_name": name, "mutual_fund_ticker": ticker,
            "source_accession": acc, "family": "Fam", "effective_date": "2021-06-11"}


WAVE = [{"wave_id": "W001", "effective_date": "2021-06-11", "is_anchor": "1",
         "source_accessions": "0001-24-000001"}]


# --------------------------------------------------------------------------- #
# the number itself                                                            #
# --------------------------------------------------------------------------- #

def test_convexp_applies_the_shrout_thousands_factor():
    """CRSP shrout is in THOUSANDS. A missing ×1000 is a silent factor-1000 error
    that would put every stock over the treated line."""
    db = FakeDB(funds=funds_df([[7, "A Fund", "AAAAX"]]),
                holdings=holdings_df([[7, 101, 1000.0, "2021-05-31"]]),
                shrout=shrout_df([[101, 100.0, 50.0, "2021-05-31"]]))
    df, unmapped, dropped, _ = hp.run(db, WAVE, [event()])
    assert unmapped == [] and dropped == []
    # 1000 shares / (100 * 1000 shares outstanding) = 0.01
    assert float(df.loc[0, "conv_exp"]) == pytest.approx(0.01)
    assert hp.SHROUT_UNITS_PER_SHARE == 1000.0


def test_shares_sum_across_funds_in_the_same_wave():
    db = FakeDB(funds=funds_df([[7, "A Fund", "AAAAX"], [8, "B Fund", "BBBBX"]]),
                holdings=holdings_df([[7, 101, 600.0, "2021-05-31"],
                                      [8, 101, 400.0, "2021-05-31"]]),
                shrout=shrout_df([[101, 100.0, 50.0, "2021-05-31"]]))
    wave = [{**WAVE[0], "source_accessions": "0001-24-000001|0001-24-000002"}]
    events = [event(), event(name="B Fund", ticker="BBBBX", acc="0001-24-000002")]
    df, _, _, _ = hp.run(db, wave, events)
    assert len(df) == 1
    assert float(df.loc[0, "conv_exp"]) == pytest.approx(0.01)
    assert int(df.loc[0, "n_funds"]) == 2


def test_missing_denominator_is_dropped_and_costed_never_imputed():
    db = FakeDB(funds=funds_df([[7, "A Fund", "AAAAX"]]),
                holdings=holdings_df([[7, 101, 1000.0, "2021-05-31"],
                                      [7, 202, 500.0, "2021-05-31"]]),
                shrout=shrout_df([[101, 100.0, 50.0, "2021-05-31"]]))   # 202 absent
    df, _, dropped, _ = hp.run(db, WAVE, [event()])
    assert list(df["permno"]) == [101]
    assert len(dropped) == 1
    d = dropped[0]
    assert d["permno"] == 202 and d["reason"] == "no_shrout_in_lookback_window"
    assert d["shares_held"] == 500.0        # numerator retained, so the drop is costable


def test_zero_or_missing_shrout_never_divides():
    db = FakeDB(funds=funds_df([[7, "A Fund", "AAAAX"]]),
                holdings=holdings_df([[7, 101, 1000.0, "2021-05-31"]]),
                shrout=shrout_df([[101, 0.0, 50.0, "2021-05-31"]]))
    df, _, dropped, _ = hp.run(db, WAVE, [event()])
    assert df.empty and len(dropped) == 1


def test_negative_crsp_price_is_a_bid_ask_average_not_a_negative_market_cap():
    db = FakeDB(funds=funds_df([[7, "A Fund", "AAAAX"]]),
                holdings=holdings_df([[7, 101, 1000.0, "2021-05-31"]]),
                shrout=shrout_df([[101, 100.0, -50.0, "2021-05-31"]]))
    df, _, _, _ = hp.run(db, WAVE, [event()])
    assert int(df.loc[0, "mcap_decile"]) >= 1        # ranked, not discarded


def test_unpriced_stock_gets_a_null_decile_not_a_zero():
    db = FakeDB(funds=funds_df([[7, "A Fund", "AAAAX"]]),
                holdings=holdings_df([[7, 101, 1000.0, "2021-05-31"]]),
                shrout=shrout_df([[101, 100.0, None, "2021-05-31"]]))
    df, _, _, _ = hp.run(db, WAVE, [event()])
    assert pd.isna(df.loc[0, "mcap_decile"])


def test_decile_ranks_span_one_to_ten_and_order_by_size():
    caps = {i: float(i) * 1e6 for i in range(1, 21)}
    d = hp.decile_ranks(caps)
    assert min(d.values()) == 1 and max(d.values()) == 10
    assert d[1] < d[20]
    assert hp.decile_ranks({1: 0.0, 2: None})[1] is None


# --------------------------------------------------------------------------- #
# the SQL                                                                      #
# --------------------------------------------------------------------------- #

def test_holdings_query_is_strictly_before_the_effective_date():
    """The lookahead ban in SQL form: a report filed on or after the conversion
    can already reflect the ETF wrapper."""
    sql = hp.sql_last_holdings_before([7], "2021-06-11")
    assert f"{S_HOLD['report_date']} < date '2021-06-11'" in " ".join(sql.split())
    assert "<=" not in sql


def test_shrout_query_takes_the_latest_observation_per_permno_in_a_window():
    sql = " ".join(hp.sql_shrout_asof([101, 202], "2021-06-11").split())
    assert f"distinct on ({S_MSF['permno']})" in sql
    assert "interval '6 months'" in sql
    assert f"order by {S_MSF['permno']}, {S_MSF['date']} desc" in sql


def test_fund_lookup_is_one_batched_query_not_one_per_fund():
    db = FakeDB(funds=funds_df([[7, "A Fund", "AAAAX"], [8, "B Fund", "BBBBX"]]))
    events = [event(), event(name="B Fund", ticker="BBBBX", acc="acc2")]
    hp.map_funds(hp.Recorder(db), events)
    assert sum(1 for s in db.seen if S_FUND["table"] in s) == 1


def test_sql_literals_escape_embedded_quotes():
    sql = hp.sql_funds_by_ticker(["O'NEIL"])
    assert "'O''NEIL'" in sql


# --------------------------------------------------------------------------- #
# mapping                                                                      #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("ticker,reason", [
    ("NA", "no_mutual_fund_ticker_in_events"),
    ("", "no_mutual_fund_ticker_in_events"),
    ("ZZZZX", "ticker_not_in_crsp_fund_header"),
])
def test_unmappable_funds_carry_a_reason_and_are_never_guessed(ticker, reason):
    db = FakeDB(funds=funds_df([[7, "A Fund", "AAAAX"]]))
    mapping, unmapped = hp.map_funds(hp.Recorder(db), [event(ticker=ticker)])
    assert mapping == []
    assert unmapped[0]["unmapped_reason"] == reason


# --------------------------------------------------------------------------- #
# outputs                                                                      #
# --------------------------------------------------------------------------- #

def test_frame_matches_the_frozen_contract(tmp_path):
    db = FakeDB(funds=funds_df([[7, "A Fund", "AAAAX"]]),
                holdings=holdings_df([[7, 101, 1000.0, "2021-05-31"]]),
                shrout=shrout_df([[101, 100.0, 50.0, "2021-05-31"]]))
    df, _, _, _ = hp.run(db, WAVE, [event()])
    assert list(df.columns) == hp.CONTRACT_COLUMNS
    out = tmp_path / "conv_exposure.parquet"
    df.to_parquet(out, index=False)
    r = subprocess.run([sys.executable, str(ROOT / "ops" / "runner" / "contracts.py"),
                        "conv_exposure", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_pre_etf_ownership_is_null_not_aliased_to_conv_exp():
    """Total pre-conversion ETF ownership needs a 13F/ETF-holdings join with no
    verified source yet. Copying conv_exp into it would look like data."""
    db = FakeDB(funds=funds_df([[7, "A Fund", "AAAAX"]]),
                holdings=holdings_df([[7, 101, 1000.0, "2021-05-31"]]),
                shrout=shrout_df([[101, 100.0, 50.0, "2021-05-31"]]))
    df, _, _, _ = hp.run(db, WAVE, [event()])
    assert pd.isna(df.loc[0, "pre_etf_ownership"])


def test_query_manifest_records_locators_and_no_rows(tmp_path):
    db = FakeDB(funds=funds_df([[7, "A Fund", "AAAAX"]]),
                holdings=holdings_df([[7, 101, 1000.0, "2021-05-31"]]),
                shrout=shrout_df([[101, 100.0, 50.0, "2021-05-31"]]))
    _, _, _, rec = hp.run(db, WAVE, [event()])
    path = tmp_path / "query_manifest.json"
    hp.write_query_manifest(rec, path=path)
    man = json.loads(path.read_text())
    assert man["queries"] and all({"sql", "rows", "sql_sha256"} <= set(q) for q in man["queries"])
    blob = path.read_text()
    for row_datum in ("1000.0", "A Fund"):        # values, as opposed to identifiers
        assert row_datum not in blob


def test_unmapped_file_is_written_even_when_empty(tmp_path):
    path = tmp_path / "unmapped_funds.csv"
    hp.write_unmapped([], path=path)
    assert path.exists() and path.read_text().strip() == "unmapped_reason"


def test_schema_lives_in_exactly_one_place():
    """Every CRSP identifier is unverified until a live account confirms it, so
    correcting one must be a single edit."""
    src = (ROOT / "p1" / "t2_wrds" / "holdings_pipeline.py").read_text()
    body = src.split('SCHEMA = {', 1)[1].split("\n}\n", 1)
    assert len(body) == 2
    after = body[1]
    for literal in ('"crsp.holdings"', '"crsp.msf"', '"crsp.fund_hdr"',
                    '"nbr_shares"', '"crsp_fundno"'):
        assert literal not in after, f"{literal} hard-coded outside SCHEMA"
