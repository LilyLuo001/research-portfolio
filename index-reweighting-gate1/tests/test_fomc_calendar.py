import csv
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import build_fomc_calendar as fomc  # noqa: E402


def _by_start(rows, start):
    return next(row for row in rows if row["meeting_start_date"] == start)


def _example_event(**overrides):
    event = {
        "evidence_key": "EVENT:EXAMPLE",
        "event_id": "EXAMPLE",
        "event_group_id": "INTERVENTION:2024-06-21",
        "basket_assignment_id": "BASKET:EXAMPLE",
        "input_reference_date": "2024-06-14",
        "earliest_public_announcement_date": "2024-06-14",
        "pro_forma_available_date": "2024-06-14",
        "implementation_close_date": "2024-06-21",
        "effective_open_date": "2024-06-24",
        "secondary_adjustment_date": "",
        "next_intervention_date": "2024-09-20",
        "source_id": "OFFICIAL_EVENT_SOURCE",
        "source_url": "https://example.test/official",
    }
    event.update(overrides)
    return event


def test_calendar_schema_and_evidence_keys_are_stable():
    rows = fomc.calendar_records()
    assert fomc.CALENDAR_FIELDS[0] == "evidence_key"
    assert len(rows) == 78
    assert len({row["evidence_key"] for row in rows}) == len(rows)
    assert all(row["evidence_key"] == f"FOMC:{row['meeting_id']}" for row in rows)


def test_primary_calendar_and_partial_extension_are_separate():
    rows = fomc.calendar_records()
    scopes = Counter(row["calendar_scope"] for row in rows)
    assert scopes == {
        "boundary_context": 1,
        "primary_2018_2025": 72,
        "partial_extension_2026_realized_through_2026-07-29": 5,
    }
    without_partial = fomc.calendar_records(include_2026_partial=False)
    assert len(without_partial) == 73
    assert not any(row["meeting_start_date"].startswith("2026") for row in without_partial)


def test_scheduled_statement_counts_preserve_2020_exception():
    rows = [
        row
        for row in fomc.calendar_records()
        if row["calendar_scope"] == "primary_2018_2025"
        and row["eligible_common_news"] == "1"
    ]
    counts = Counter(row["statement_date"][:4] for row in rows)
    assert counts == {
        "2018": 8,
        "2019": 8,
        "2020": 7,
        "2021": 8,
        "2022": 8,
        "2023": 8,
        "2024": 8,
        "2025": 8,
    }
    assert len(rows) == 63


def test_unscheduled_notation_and_cancelled_rows_are_ineligible():
    rows = fomc.calendar_records()
    march_2 = _by_start(rows, "2020-03-02")
    march_15 = _by_start(rows, "2020-03-15")
    cancelled = _by_start(rows, "2020-03-17")
    notation = _by_start(rows, "2020-03-23")
    assert march_2["statement_date"] == "2020-03-03"
    assert march_2["scheduled_status"] == "unscheduled"
    assert march_15["scheduled_status"] == "unscheduled"
    assert cancelled["meeting_status"] == "cancelled"
    assert cancelled["statement_date"] == ""
    assert notation["scheduled_status"] == "notation_vote"
    assert {march_2["eligible_common_news"], march_15["eligible_common_news"], cancelled["eligible_common_news"], notation["eligible_common_news"]} == {"0"}


def test_all_official_notation_votes_are_retained_but_ineligible():
    rows = fomc.calendar_records()
    expected = {
        "2020-03-19",
        "2020-03-23",
        "2020-03-31",
        "2020-08-27",
        "2025-08-22",
    }
    observed = {
        row["meeting_start_date"]
        for row in rows
        if row["scheduled_status"] == "notation_vote"
    }
    assert observed == expected
    assert all(
        row["eligible_common_news"] == "0"
        for row in rows
        if row["scheduled_status"] == "notation_vote"
    )
    march_19 = _by_start(rows, "2020-03-19")
    assert march_19["has_policy_statement"] == "0"
    assert march_19["communication_package"] == "press_release"


def test_2019_delayed_unscheduled_statement_is_not_misdated_or_eligible():
    row = _by_start(fomc.calendar_records(), "2019-10-04")
    assert row["statement_date"] == "2019-10-11"
    assert row["scheduled_status"] == "unscheduled"
    assert row["eligible_common_news"] == "0"
    assert row["statement_url"].endswith("monetary20191011a.htm")


def test_package_metadata_distinguishes_press_conference_and_sep():
    rows = fomc.calendar_records()
    january_2018 = _by_start(rows, "2018-01-30")
    march_2018 = _by_start(rows, "2018-03-20")
    january_2019 = _by_start(rows, "2019-01-29")
    assert january_2018["communication_package"] == "statement_only"
    assert march_2018["communication_package"] == "statement+press_conference+SEP"
    assert january_2019["communication_package"] == "statement+press_conference"
    assert january_2019["has_sep"] == "0"


def test_every_eligible_statement_is_an_nyse_session():
    rows = fomc.calendar_records()
    for row in rows:
        if row["eligible_common_news"] != "1":
            continue
        statement = date.fromisoformat(row["statement_date"])
        assert statement.weekday() < 5
        assert statement not in fomc.nyse_holidays(statement.year)
    fomc.validate_calendar(rows)


def test_nyse_session_counts_include_special_closures_and_juneteenth():
    expected = {
        2018: 251,
        2019: 252,
        2020: 253,
        2021: 252,
        2022: 251,
        2023: 250,
        2024: 252,
        2025: 250,
        2026: 251,
    }
    actual = {
        year: len(fomc.trading_sessions(date(year, 1, 1), date(year, 12, 31)))
        for year in expected
    }
    assert actual == expected
    assert date(2018, 12, 5) in fomc.nyse_holidays(2018)
    assert date(2025, 1, 9) in fomc.nyse_holidays(2025)
    assert date(2021, 6, 18) not in fomc.nyse_holidays(2021)
    assert date(2022, 6, 20) in fomc.nyse_holidays(2022)


def test_signed_trading_day_distance_handles_weekend_and_holiday():
    sessions = fomc.trading_sessions(date(2024, 6, 1), date(2024, 7, 10))
    assert fomc.signed_trading_day_distance(date(2024, 6, 14), date(2024, 6, 17), sessions) == 1
    assert fomc.signed_trading_day_distance(date(2024, 6, 15), date(2024, 6, 17), sessions) == 1
    assert fomc.signed_trading_day_distance(date(2024, 6, 20), date(2024, 6, 19), sessions) == 0
    assert fomc.signed_trading_day_distance(date(2024, 6, 21), date(2024, 6, 12), sessions) == -6
    assert fomc.signed_trading_day_distance(date(2024, 6, 21), date(2024, 6, 21), sessions) == 0


def test_support_has_nearest_rows_and_band_counts_without_unscheduled_dates():
    support = fomc.build_support(fomc.calendar_records(), [_example_event()])
    rows = [row for row in support if row["anchor"] == "implementation_close_date"]
    june = next(row for row in rows if row["statement_date"] == "2024-06-12")
    july = next(row for row in rows if row["statement_date"] == "2024-07-31")
    assert june["trading_day_distance_signed"] == "-6"
    assert june["nearest_pre"] == "1"
    assert june["within_20td"] == "1"
    assert july["nearest_post"] == "1"
    assert july["trading_day_distance_signed"] == "27"
    assert june["pre_count_20td"] == "1"
    assert june["post_count_20td"] == "0"
    assert june["total_count_20td"] == "1"
    assert all(row["meeting_id"] != "20200302_UNSCHEDULED" for row in support)
    assert {row["support_role"] for row in rows} == {
        "UNCLASSIFIED_EVENT_CONTEXT"
    }
    assert june["fomc_calendar_scope"] == "primary_2018_2025"


def test_band_overlap_flags_interval_intersection_not_meeting_membership():
    support = fomc.build_support(fomc.calendar_records(), [_example_event()])
    row = next(
        row
        for row in support
        if row["anchor"] == "implementation_close_date"
        and row["statement_date"] == "2024-06-12"
    )
    assert row["band_20_overlaps_anticipation"] == "1"
    assert row["band_40_overlaps_anticipation"] == "1"
    assert row["band_60_overlaps_anticipation"] == "1"


def test_missing_anchor_is_explicit_and_has_no_computed_counts():
    support = fomc.build_support(fomc.calendar_records(), [_example_event()])
    row = next(row for row in support if row["anchor"] == "secondary_adjustment_date")
    assert row["meeting_id"] == "UNRESOLVED"
    assert row["status"] == "UNRESOLVED_ANCHOR"
    assert row["trading_day_distance_signed"] == ""
    assert row["total_count_60td"] == ""
    assert row["evidence_key"] == "SUPPORT:EXAMPLE:UNRESOLVED:secondary_adjustment_date"


def test_intervention_and_news_groups_remain_separate():
    events = [
        _example_event(event_id="SECTOR_A", basket_assignment_id="BASKET_A"),
        _example_event(event_id="SECTOR_B", basket_assignment_id="BASKET_B"),
    ]
    support = fomc.build_support(fomc.calendar_records(), events)
    rows = [
        row
        for row in support
        if row["anchor"] == "implementation_close_date"
        and row["statement_date"] == "2024-06-12"
    ]
    assert len(rows) == 2
    assert len({row["event_id"] for row in rows}) == 2
    assert len({row["basket_assignment_id"] for row in rows}) == 2
    assert {row["common_rebalance_group_id"] for row in rows} == {"INTERVENTION:2024-06-21"}
    assert {row["common_news_group_id"] for row in rows} == {"20240611_REGULAR"}


def test_support_source_pairs_resolve_to_source_registry():
    registry = {row["source_id"]: row["source_url"] for row in fomc.source_registry_rows()}
    support = fomc.build_support(fomc.calendar_records(), [_example_event()])
    for row in support:
        if row["status"] != "CALENDAR_INTERSECTION_COMPUTED":
            continue
        assert row["source_id"] in registry
        assert row["source_url"] == registry[row["source_id"]]
        assert row["trading_calendar_source_id"] in registry
        assert row["trading_calendar_source_url"] == registry[
            row["trading_calendar_source_id"]
        ]


def test_missing_ledger_scaffold_is_explicit():
    row = fomc.missing_ledger_support_row("ledger not found")
    assert fomc.SUPPORT_FIELDS[0] == "evidence_key"
    assert row["evidence_key"] == "SUPPORT:LEDGER_MISSING:UNRESOLVED:ledger_input"
    assert row["status"] == "BLOCKED_INPUT"
    assert row["trading_day_distance_signed"] == ""


def test_support_carries_event_binding_and_evidence_semantics():
    event = _example_event(
        binding_status="confirmed_binding",
        status="CONFIRMED_BINDING",
        classification_evidence_grade="B",
        assignment_evidence_grade="B",
        assignment_observability="documented_binding_vector_incomplete",
    )
    support = fomc.build_support(fomc.calendar_records(), [event])
    row = next(
        item
        for item in support
        if item["status"] == "CALENDAR_INTERSECTION_COMPUTED"
    )
    assert row["event_binding_status"] == "confirmed_binding"
    assert row["event_status"] == "CONFIRMED_BINDING"
    assert row["event_classification_evidence_grade"] == "B"
    assert row["event_assignment_evidence_grade"] == "B"
    assert row["event_assignment_observability"] == (
        "documented_binding_vector_incomplete"
    )
    assert row["support_role"] == "CONFIRMED_BINDING_EVENT_SUPPORT"

    outside = fomc.build_support(
        fomc.calendar_records(),
        [_example_event(binding_status="outside_applicable_regime")],
    )
    assert {
        item["support_role"]
        for item in outside
    } == {"OUTSIDE_REGIME_CONTEXT"}


def test_unknown_anticipation_and_next_intervention_are_not_false_zeros():
    event = _example_event(
        earliest_public_announcement_date="",
        next_intervention_date="",
    )
    support = fomc.build_support(fomc.calendar_records(), [event])
    rows = [
        row
        for row in support
        if row["status"] == "CALENDAR_INTERSECTION_COMPUTED"
    ]
    assert rows
    for row in rows:
        assert row["anticipation_window_status"].startswith("UNRESOLVED")
        assert row["next_intervention_status"].startswith("UNRESOLVED")
        assert row["meeting_in_anticipation_interval"] == ""
        assert row["meeting_on_or_after_next_intervention"] == ""
        for band in (20, 40, 60):
            assert row[f"band_{band}_overlaps_anticipation"] == ""
            assert row[f"band_{band}_overlaps_next_intervention"] == ""


def test_other_event_counts_separate_dated_binding_and_undated_context():
    focal = _example_event(
        event_id="FOCAL",
        event_group_id="GROUP:FOCAL",
        binding_status="confirmed_binding",
    )
    other = _example_event(
        event_id="OTHER",
        event_group_id="GROUP:OTHER",
        binding_status="confirmed_other_intervention",
        implementation_close_date="2024-06-18",
        effective_open_date="2024-06-20",
    )
    undated = _example_event(
        event_id="UNDATED",
        event_group_id="GROUP:UNDATED",
        binding_status="uncertain",
        input_reference_date="",
        earliest_public_announcement_date="",
        pro_forma_available_date="",
        implementation_close_date="",
        effective_open_date="",
        secondary_adjustment_date="",
        next_intervention_date="",
    )
    support = fomc.build_support(
        fomc.calendar_records(), [focal, other, undated]
    )
    row = next(
        item
        for item in support
        if item["event_id"] == "FOCAL"
        and item["anchor"] == "implementation_close_date"
        and item["status"] == "CALENDAR_INTERSECTION_COMPUTED"
    )
    assert row["dated_other_event_group_count_20td"] == "1"
    assert row["dated_other_confirmed_intervention_group_count_20td"] == "1"
    assert row["dated_other_confirmed_binding_group_count_20td"] == "0"
    assert row["undated_other_event_group_count"] == "1"


def test_cli_consumes_ledger_and_writes_declared_schemas(tmp_path):
    ledger = tmp_path / "ledger.csv"
    with ledger.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(_example_event().keys()))
        writer.writeheader()
        writer.writerow(_example_event())

    calendar_output = tmp_path / "fomc.csv"
    support_output = tmp_path / "support.csv"
    source_output = tmp_path / "sources.csv"
    usmpd_output = tmp_path / "usmpd.csv"
    build_log = tmp_path / "build.log"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "src" / "build_fomc_calendar.py"),
            "--ledger",
            str(ledger),
            "--calendar-output",
            str(calendar_output),
            "--support-output",
            str(support_output),
            "--source-registry-output",
            str(source_output),
            "--usmpd-registry-output",
            str(usmpd_output),
            "--build-log-output",
            str(build_log),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "ledger_status=CONSUMED" in result.stdout
    with calendar_output.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        assert next(reader) == fomc.CALENDAR_FIELDS
    with support_output.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == fomc.SUPPORT_FIELDS
        rows = list(reader)
    assert any(row["status"] == "CALENDAR_INTERSECTION_COMPUTED" for row in rows)
    assert "No intraday" in build_log.read_text(encoding="utf-8")


def test_usmpd_registry_never_assigns_a_row_classification_without_matching():
    row = fomc.unscreened_usmpd_registry_row()
    assert row["row_level_classification_status"] == (
        "METADATA_SCREEN_ONLY_NO_ROW_CLASSIFICATION_ASSIGNED"
    )
    assert row["event_window_definition"] == ""
    source = next(
        item
        for item in fomc.source_registry_rows()
        if item["source_id"] == fomc.USMPD_REGISTRY_ID
    )
    assert source["source_role"] == "availability and metadata screening only"
