"""Invariants for the public Fed/source-study reconciliation."""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "p1" / "universe_v2" / "output"


def read(name: str) -> pd.DataFrame:
    return pd.read_csv(OUT / name, dtype=str, keep_default_na=False)


def test_source_aggregate_is_preserved_without_inventing_rows():
    source = read("fed_source_event_universe.csv")
    assert len(source) == 125
    assert (source.published_row_status == "identified").sum() == 4
    assert (source.published_row_status == "unidentified_placeholder").sum() == 121
    hidden = source[source.published_row_status == "unidentified_placeholder"]
    assert (hidden.predecessor_fund_name == "").all()
    assert (hidden.successor_etf_name == "").all()
    assert (hidden.source_study_conversion_date == "").all()


def test_all_four_empirical_events_are_exact_p1_gate0_matches():
    cross = read("fed_to_p1_event_crosswalk.csv")
    empirical = cross[cross.source_scope == "empirical_sample_table_1"]
    assert len(empirical) == 4
    assert set(empirical.match_status) == {"exact_match"}
    assert set(empirical.p1_in_156_completed_universe) == {"TRUE"}
    assert set(empirical.p1_in_74_timing_eligible_universe) == {"TRUE"}
    assert set(empirical.p1_in_71_gate0_pass_universe) == {"TRUE"}
    assert set(empirical.p1_wave_id) == {"W002"}
    assert set(empirical.p1_current_effective_date) == {"2021-06-11"}


def test_excluded_82_are_complete_and_not_upgraded_by_public_fed_rows():
    audit = read("excluded_82_source_date_audit.csv")
    assert len(audit) == 82
    assert audit.final_precision.value_counts().to_dict() == {
        "month_only": 57,
        "proposed_exact_day_only": 14,
        "bounded_window": 9,
        "year_only": 2,
    }
    assert set(audit.source_study_empirical_match) == {"FALSE"}
    assert set(audit.upgradeable_from_public_source_study_evidence) == {"FALSE"}


def test_summary_keeps_noncomparable_units_explicit():
    summary = read("event_universe_reconciliation_summary.csv").set_index("metric")
    assert summary.loc["fed_reported_industry_conversions_through_2024", "value"] == "125"
    assert summary.loc["fed_empirical_sample_completed_conversions", "value"] == "4"
    assert summary.loc["p1_completed_conversions_all_years", "value"] == "156"
    assert summary.loc["p1_completed_conversions_through_2024", "value"] == "95"
    assert summary.loc["p1_verified_exact_day_timing_eligible", "value"] == "74"
    assert summary.loc["p1_gate0_pass_events", "value"] == "71"
    assert summary.loc["fed_aggregate_rows_missing_from_p1_156", "value"] == "UNKNOWN"
