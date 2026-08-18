"""The day-one census: schema verification and holdings-coverage measurement,
driven against a fake connection (no credentials, no CRSP, no network).

The census exists because a pipeline that silently drops a third of the funds
looks exactly like a successful pipeline. These tests pin the counting.
"""
import json
import pathlib

import pandas as pd
import pytest

import coverage_census as cc
import holdings_pipeline as hp

S_FUND = hp.SCHEMA["fund_header"]


class FakeDB:
    def __init__(self, funds=None, census=None, columns=None, fail_tables=()):
        self.funds = funds
        self.census = census
        self.columns = columns or {}
        self.fail_tables = set(fail_tables)
        self.seen = []

    def raw_sql(self, sql):
        self.seen.append(" ".join(sql.split()))
        if "information_schema.columns" in sql:
            for table, cols in self.columns.items():
                schema, _, name = table.partition(".")
                if f"'{schema}'" in sql and f"'{name}'" in sql:
                    if table in self.fail_tables:
                        raise RuntimeError("permission denied for %s" % table)
                    return pd.DataFrame({"column_name": cols,
                                         "data_type": ["text"] * len(cols)})
            return pd.DataFrame(columns=["column_name", "data_type"])
        if S_FUND["table"] in sql:
            return (self.funds if self.funds is not None
                    else pd.DataFrame(columns=[S_FUND["fundno"], S_FUND["name"],
                                               S_FUND["ticker"]]))
        return (self.census if self.census is not None
                else pd.DataFrame(columns=["fundno", "eff", "last_report",
                                           "n_position_rows"]))


def funds_df(rows):
    return pd.DataFrame(rows, columns=[S_FUND["fundno"], S_FUND["name"], S_FUND["ticker"]])


def census_df(rows):
    return pd.DataFrame(rows, columns=["fundno", "eff", "last_report", "n_position_rows"])


def event(name="A Fund", ticker="AAAAX", eff="2021-06-11", acc="acc1"):
    return {"fund_name": name, "mutual_fund_ticker": ticker, "effective_date": eff,
            "source_accession": acc, "family": "Fam"}


ALL_COLUMNS = {
    hp.SCHEMA["fund_header"]["table"]: ["crsp_fundno", "fund_name", "ticker"],
    hp.SCHEMA["holdings"]["table"]: ["crsp_fundno", "permno", "nbr_shares", "report_dt"],
    hp.SCHEMA["monthly_stock"]["table"]: ["permno", "date", "shrout", "prc"],
}


# --------------------------------------------------------------------------- #
# schema verification                                                          #
# --------------------------------------------------------------------------- #

def test_schema_check_passes_when_every_column_exists():
    rep = cc.check_schema(hp.Recorder(FakeDB(columns=ALL_COLUMNS)))
    assert all(r["table_exists"] and not r["columns_missing"] for r in rep.values())
    assert cc.schema_verdict(rep).startswith("SCHEMA OK")


def test_schema_check_names_the_entry_to_correct():
    cols = dict(ALL_COLUMNS)
    cols[hp.SCHEMA["holdings"]["table"]] = ["crsp_fundno", "permno", "report_dt"]  # no shares
    rep = cc.check_schema(hp.Recorder(FakeDB(columns=cols)))
    assert rep["holdings"]["columns_missing"] == {"shares": hp.SCHEMA["holdings"]["shares"]}
    verdict = cc.schema_verdict(rep)
    assert verdict.startswith("SCHEMA NEEDS CORRECTION") and "holdings" in verdict


def test_missing_table_is_reported_not_raised():
    rep = cc.check_schema(hp.Recorder(FakeDB(columns={})))
    assert all(r["table_exists"] is False for r in rep.values())


def test_an_unreadable_table_does_not_abort_the_sweep():
    """A permissions failure on one table must still report the other two."""
    db = FakeDB(columns=ALL_COLUMNS, fail_tables=[hp.SCHEMA["monthly_stock"]["table"]])
    rep = cc.check_schema(hp.Recorder(db))
    assert rep["monthly_stock"]["table_exists"] is False
    assert "error" in rep["monthly_stock"]
    assert rep["holdings"]["table_exists"] is True


def test_introspection_uses_portable_sql_not_a_guessed_client_helper():
    sql = cc.sql_introspect_columns("crsp.holdings")
    assert "information_schema.columns" in sql
    assert "'crsp'" in sql and "'holdings'" in sql


# --------------------------------------------------------------------------- #
# holdings census                                                              #
# --------------------------------------------------------------------------- #

def test_fund_with_a_recent_report_is_ok():
    db = FakeDB(funds=funds_df([[7, "A Fund", "AAAAX"]]),
                census=census_df([[7, "2021-06-11", "2021-05-31", 120]]))
    rows, _ = cc.census(db, [event()])
    assert rows[0]["status"] == "ok"
    assert rows[0]["staleness_days"] == 11
    assert rows[0]["n_position_rows"] == 120


def test_fund_with_an_old_report_is_flagged_stale_but_still_usable():
    db = FakeDB(funds=funds_df([[7, "A Fund", "AAAAX"]]),
                census=census_df([[7, "2021-06-11", "2020-11-30", 90]]))
    rows, _ = cc.census(db, [event()])
    assert rows[0]["status"] == "stale_holdings_report"
    assert rows[0]["staleness_days"] > cc.STALE_WARN_DAYS
    assert cc.summarize(rows)["funds_usable"] == 1        # flagged, not discarded


def test_mapped_fund_with_no_pre_conversion_report_is_counted_not_dropped():
    """The failure the census exists to make visible."""
    db = FakeDB(funds=funds_df([[7, "A Fund", "AAAAX"]]), census=census_df([]))
    rows, _ = cc.census(db, [event()])
    assert rows[0]["status"] == "no_holdings_report_before_conversion"
    assert rows[0]["last_report_before_conversion"] == ""
    s = cc.summarize(rows)
    assert s["funds_total"] == 1 and s["funds_usable"] == 0 and s["coverage_pct"] == 0.0


def test_unmapped_funds_appear_in_the_census_with_their_reason():
    db = FakeDB(funds=funds_df([]))
    rows, _ = cc.census(db, [event(ticker="NA"), event(name="B", ticker="ZZZZX", acc="a2")])
    assert {r["status"] for r in rows} == {"no_mutual_fund_ticker_in_events",
                                           "ticker_not_in_crsp_fund_header"}
    assert all(r["mapped"] == "no" for r in rows)


def test_census_is_one_query_for_all_funds():
    db = FakeDB(funds=funds_df([[7, "A", "AAAAX"], [8, "B", "BBBBX"]]),
                census=census_df([[7, "2021-06-11", "2021-05-31", 10],
                                  [8, "2021-06-11", "2021-05-31", 10]]))
    cc.census(db, [event(), event(name="B", ticker="BBBBX", acc="a2")])
    assert sum(1 for s in db.seen if "target(fundno, eff)" in s) == 1


def test_census_query_pairs_each_fund_with_its_own_effective_date():
    sql = " ".join(cc.sql_last_report_before_per_fund(
        [(7, "2021-06-11"), (8, "2022-01-03")]).split())
    assert "(7, date '2021-06-11')" in sql and "(8, date '2022-01-03')" in sql
    assert "< t.eff" in sql            # strictly before: the lookahead ban


def test_summary_percentages_are_computed_not_asserted():
    rows = [{"status": "ok", "staleness_days": 10},
            {"status": "stale_holdings_report", "staleness_days": 200},
            {"status": "no_holdings_report_before_conversion", "staleness_days": ""},
            {"status": "ticker_not_in_crsp_fund_header", "staleness_days": ""}]
    s = cc.summarize(rows)
    assert s["funds_total"] == 4 and s["funds_usable"] == 2 and s["coverage_pct"] == 50.0
    assert s["staleness_days_max"] == 200


def test_outputs_carry_no_licensed_rows(tmp_path):
    db = FakeDB(funds=funds_df([[7, "A Fund", "AAAAX"]]),
                census=census_df([[7, "2021-06-11", "2021-05-31", 120]]))
    rows, _ = cc.census(db, [event()])
    md, csvp = tmp_path / "census.md", tmp_path / "census.csv"
    cc.write_outputs(rows, cc.summarize(rows), md_path=md, csv_path=csvp)
    # fund identity + coverage counts are ours; no holding rows, prices, or shares
    body = md.read_text() + csvp.read_text()
    assert "coverage census" in body.lower()
    for leaked in ("nbr_shares", "shrout", "prc"):
        assert leaked not in body


def test_empty_census_does_not_divide_by_zero():
    s = cc.summarize([])
    assert s["funds_total"] == 0 and s["coverage_pct"] == 0.0
