#!/usr/bin/env python3
"""Build the Gate 1 FOMC calendar and assignment/FOMC support map.

This module is deliberately a daily-calendar audit.  It does not use returns,
construct monetary-policy factors, assess intraday quote availability, or make
minimum-detectable-effect claims.

The FOMC observations are a reviewed, deterministic transcription of official
Board of Governors annual calendar/historical pages.  Scheduled policy
statement meetings are eligible common-news observations.  Officially labelled
unscheduled meetings, notation votes, and the cancelled March 2020 meeting are
retained as explicit exceptions but are not eligible support observations.

The support builder consumes ``rebalance_event_ledger.csv`` when it is present.
Every missing stage date is emitted as an unresolved row rather than inferred.
Distances count NYSE trading sessions crossed, not weekdays or calendar days.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, Mapping, Sequence
from xml.etree import ElementTree as ET
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
RETRIEVAL_DATE = "2026-09-08"
FED_BASE = "https://www.federalreserve.gov"

FED_HISTORICAL_INDEX_URL = (
    "https://www.federalreserve.gov/monetarypolicy/fomc_historical.htm"
)
FED_CURRENT_CALENDAR_URL = (
    "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
)
USMPD_PAGE_URL = (
    "https://www.frbsf.org/research-and-insights/data-and-indicators/"
    "us-monetary-policy-event-study-database/"
)
USMPD_DOWNLOAD_URL = (
    "https://www.frbsf.org/wp-content/uploads/USMPD.xlsx?2026-09-04="
)
USMPD_REGISTRY_ID = "FRBSF_USMPD_20260803"

NYSE_HOURS_URL = "https://www.nyse.com/trade/hours-calendars"
NYSE_TRADING_DAYS_URL = "https://www.nyse.com/publicdocs/Trading_Days.pdf"
NYSE_BUSH_CLOSURE_URL = (
    "https://www.nyse.com/publicdocs/nyse/markets/arca-options/"
    "rule-interpretations/2018/NYSE%20Arca%20Options%2018-06.pdf"
)
NYSE_CARTER_CLOSURE_URL = (
    "https://www.nyse.com/publicdocs/nyse/markets/american-options/"
    "rule-interpretations/2025/National_Day_of_Mourning_20250102.pdf"
)
NYSE_JUNETEENTH_RULE_URL = (
    "https://www.nyse.com/publicdocs/nyse/markets/nyse-national/"
    "rule-filings/federal-registers/2021/"
    "NYSENAT-2021-18%2C%2086%20FR%2055033%20%2810-5-21%29.pdf"
)
TRADING_CALENDAR_SOURCE_ID = "NYSE_RULES_SPECIAL_CLOSURES_V1"


CALENDAR_FIELDS = [
    "evidence_key",
    "meeting_id",
    "meeting_package_id",
    "calendar_scope",
    "meeting_start_date",
    "meeting_end_date",
    "statement_date",
    "meeting_status",
    "scheduled_status",
    "is_scheduled_regular",
    "has_policy_statement",
    "eligible_common_news",
    "has_sep",
    "has_press_conference",
    "communication_package",
    "statement_url",
    "source_id",
    "source_url",
    "retrieval_date",
    "usmpd_registry_id",
    "usmpd_row_match_status",
    "status",
    "notes",
]


ANCHOR_FIELDS = [
    "input_reference_date",
    "earliest_public_announcement_date",
    "pro_forma_available_date",
    "implementation_close_date",
    "effective_open_date",
    "secondary_adjustment_date",
    "next_intervention_date",
]


ANCHOR_ALIASES = {
    "input_reference_date": (
        "input_reference_date",
        "reference_date",
        "reference_input_date",
    ),
    "earliest_public_announcement_date": (
        "earliest_public_announcement_date",
        "earliest_documented_public_announcement_date",
        "announcement_date",
    ),
    "pro_forma_available_date": (
        "pro_forma_available_date",
        "pro_forma_date",
        "proforma_date",
    ),
    "implementation_close_date": (
        "implementation_close_date",
        "implementation_date",
        "rebalance_close_date",
    ),
    "effective_open_date": (
        "effective_open_date",
        "effective_date",
    ),
    "secondary_adjustment_date": (
        "secondary_adjustment_date",
        "secondary_check_date",
    ),
    "next_intervention_date": (
        "next_intervention_date",
        "next_rebalance_date",
    ),
}


SUPPORT_FIELDS = [
    "evidence_key",
    "event_id",
    "event_evidence_key",
    "event_group_id",
    "basket_assignment_id",
    "anchor",
    "anchor_date",
    "intervention_date",
    "intervention_date_basis",
    "common_rebalance_group_id",
    "meeting_id",
    "fomc_evidence_key",
    "common_news_group_id",
    "statement_date",
    "temporal_relation",
    "trading_day_distance_signed",
    "calendar_day_distance_signed",
    "nearest_pre",
    "nearest_post",
    "same_day",
    "within_20td",
    "within_40td",
    "within_60td",
    "pre_count_20td",
    "post_count_20td",
    "total_count_20td",
    "pre_count_40td",
    "post_count_40td",
    "total_count_40td",
    "pre_count_60td",
    "post_count_60td",
    "total_count_60td",
    "band_20_overlaps_anticipation",
    "band_40_overlaps_anticipation",
    "band_60_overlaps_anticipation",
    "band_20_overlaps_next_intervention",
    "band_40_overlaps_next_intervention",
    "band_60_overlaps_next_intervention",
    "other_intervention_group_count_20td",
    "other_intervention_group_count_40td",
    "other_intervention_group_count_60td",
    "meeting_in_anticipation_interval",
    "meeting_on_or_after_next_intervention",
    "has_sep",
    "has_press_conference",
    "communication_package",
    "source_id",
    "source_url",
    "event_source_id",
    "event_source_url",
    "trading_calendar_source_id",
    "trading_calendar_source_url",
    "shared_stock_overlap_status",
    "comparison_id",
    "status",
    "notes",
]


SOURCE_REGISTRY_FIELDS = [
    "evidence_key",
    "source_id",
    "publisher",
    "title",
    "source_url",
    "retrieval_date",
    "source_role",
    "status",
    "notes",
]


USMPD_REGISTRY_FIELDS = [
    "evidence_key",
    "registry_id",
    "dataset_name",
    "publisher",
    "page_updated",
    "retrieval_date",
    "page_url",
    "download_url",
    "workbook_sha256",
    "sheet_name",
    "observed_row_count",
    "observed_date_min",
    "observed_date_max",
    "metadata_columns",
    "event_window_definition",
    "row_level_classification_status",
    "status",
    "notes",
]


def _historical_url(year: int) -> str:
    return f"{FED_BASE}/monetarypolicy/fomchistorical{year}.htm"


def _statement_url(statement_day: str) -> str:
    compact = statement_day.replace("-", "")
    return f"{FED_BASE}/newsevents/pressreleases/monetary{compact}a.htm"


def _calendar_scope(year: int) -> str:
    if year < 2018:
        return "boundary_context"
    if year <= 2025:
        return "primary_2018_2025"
    return "partial_extension_2026_realized_through_2026-07-29"


def _record(
    meeting_start: str,
    meeting_end: str,
    *,
    statement_day: str | None = None,
    has_sep: bool = False,
    has_press_conference: bool = False,
    scheduled_status: str = "scheduled_regular",
    meeting_status: str = "held",
    meeting_id: str | None = None,
    statement_url: str | None = None,
    notes: str = "",
) -> dict[str, str]:
    """Construct one reviewed official-calendar record."""

    start = date.fromisoformat(meeting_start)
    end = date.fromisoformat(meeting_end)
    if statement_day is None and meeting_status == "held":
        statement_day = meeting_end
    has_statement = bool(statement_day)
    regular = scheduled_status == "scheduled_regular"
    eligible = regular and meeting_status == "held" and has_statement
    if meeting_id is None:
        suffix = {
            "scheduled_regular": "REGULAR",
            "unscheduled": "UNSCHEDULED",
            "notation_vote": "NOTATION",
            "cancelled_scheduled": "CANCELLED",
        }[scheduled_status]
        meeting_id = f"{meeting_start.replace('-', '')}_{suffix}"
    if statement_url is None and statement_day:
        statement_url = _statement_url(statement_day)

    if not has_statement:
        package = "none"
    elif has_sep and has_press_conference:
        package = "statement+press_conference+SEP"
    elif has_press_conference:
        package = "statement+press_conference"
    elif has_sep:
        package = "statement+SEP"
    else:
        package = "statement_only"

    year = start.year
    if year <= 2020:
        source_id = f"FED_FOMC_HIST_{year}"
        source_url = _historical_url(year)
    else:
        source_id = "FED_FOMC_CAL_2021_2027"
        source_url = FED_CURRENT_CALENDAR_URL

    if eligible:
        status = "VERIFIED_OFFICIAL_SCHEDULED_STATEMENT"
    elif meeting_status == "cancelled":
        status = "VERIFIED_OFFICIAL_CANCELLED_NO_STATEMENT"
    else:
        status = "VERIFIED_OFFICIAL_INELIGIBLE_EXCEPTION"

    default_note = (
        "Official Board calendar/historical record; phases in this package are "
        "dependent and count as one FOMC meeting."
    )
    return {
        "evidence_key": f"FOMC:{meeting_id}",
        "meeting_id": meeting_id,
        "meeting_package_id": f"FOMC_PACKAGE:{meeting_id}",
        "calendar_scope": _calendar_scope(year),
        "meeting_start_date": start.isoformat(),
        "meeting_end_date": end.isoformat(),
        "statement_date": statement_day or "",
        "meeting_status": meeting_status,
        "scheduled_status": scheduled_status,
        "is_scheduled_regular": str(int(regular)),
        "has_policy_statement": str(int(has_statement)),
        "eligible_common_news": str(int(eligible)),
        "has_sep": str(int(has_sep)),
        "has_press_conference": str(int(has_press_conference)),
        "communication_package": package,
        "statement_url": statement_url or "",
        "source_id": source_id,
        "source_url": source_url,
        "retrieval_date": RETRIEVAL_DATE,
        "usmpd_registry_id": USMPD_REGISTRY_ID,
        "usmpd_row_match_status": "NOT_ROW_MATCHED_METADATA_SCREEN_ONLY",
        "status": status,
        "notes": f"{default_note} {notes}".strip(),
    }


def calendar_records(include_2026_partial: bool = True) -> list[dict[str, str]]:
    """Return the reviewed official FOMC calendar snapshot.

    One 2017 row is retained solely to provide the nearest pre-meeting for
    intervention anchors at the start of the 2018 screening window.  The 2026
    rows are realized meetings through July 29 and are labelled partial.
    """

    rows = [
        # Independently verified boundary context.
        _record(
            "2017-12-12",
            "2017-12-13",
            has_sep=True,
            has_press_conference=True,
            notes="Boundary context only for early-2018 nearest-pre support.",
        ),
        # 2018 historical page.
        _record("2018-01-30", "2018-01-31"),
        _record("2018-03-20", "2018-03-21", has_sep=True, has_press_conference=True),
        _record("2018-05-01", "2018-05-02"),
        _record("2018-06-12", "2018-06-13", has_sep=True, has_press_conference=True),
        _record("2018-07-31", "2018-08-01"),
        _record("2018-09-25", "2018-09-26", has_sep=True, has_press_conference=True),
        _record("2018-11-07", "2018-11-08"),
        _record("2018-12-18", "2018-12-19", has_sep=True, has_press_conference=True),
        # 2019 historical page.  The October 4 entry is explicitly unscheduled;
        # its official page says the statement was released October 11.
        _record("2019-01-29", "2019-01-30", has_press_conference=True),
        _record("2019-03-19", "2019-03-20", has_sep=True, has_press_conference=True),
        _record("2019-04-30", "2019-05-01", has_press_conference=True),
        _record("2019-06-18", "2019-06-19", has_sep=True, has_press_conference=True),
        _record("2019-07-30", "2019-07-31", has_press_conference=True),
        _record("2019-09-17", "2019-09-18", has_sep=True, has_press_conference=True),
        _record(
            "2019-10-04",
            "2019-10-04",
            statement_day="2019-10-11",
            scheduled_status="unscheduled",
            notes=(
                "Official page labels the October 4 meeting unscheduled and the "
                "statement released October 11; excluded from scheduled support."
            ),
        ),
        _record("2019-10-29", "2019-10-30", has_press_conference=True),
        _record("2019-12-10", "2019-12-11", has_sep=True, has_press_conference=True),
        # 2020 historical page.  Preserve emergency/cancelled exceptions.
        _record("2020-01-28", "2020-01-29", has_press_conference=True),
        _record(
            "2020-03-02",
            "2020-03-02",
            statement_day="2020-03-03",
            has_press_conference=True,
            scheduled_status="unscheduled",
            notes="Official page labels this an unscheduled meeting; excluded.",
        ),
        _record(
            "2020-03-15",
            "2020-03-15",
            has_press_conference=True,
            scheduled_status="unscheduled",
            notes="Official page labels this an unscheduled meeting; excluded.",
        ),
        _record(
            "2020-03-17",
            "2020-03-18",
            statement_day=None,
            scheduled_status="cancelled_scheduled",
            meeting_status="cancelled",
            notes=(
                "Official page labels the scheduled March 17-18 meeting "
                "cancelled; it has no statement observation."
            ),
        ),
        _record(
            "2020-03-23",
            "2020-03-23",
            scheduled_status="notation_vote",
            notes="Official page labels this a notation vote; excluded.",
        ),
        _record("2020-04-28", "2020-04-29", has_press_conference=True),
        _record("2020-06-09", "2020-06-10", has_sep=True, has_press_conference=True),
        _record("2020-07-28", "2020-07-29", has_press_conference=True),
        _record("2020-09-15", "2020-09-16", has_sep=True, has_press_conference=True),
        _record("2020-11-04", "2020-11-05", has_press_conference=True),
        _record("2020-12-15", "2020-12-16", has_sep=True, has_press_conference=True),
        # 2021 current calendar.
        _record("2021-01-26", "2021-01-27", has_press_conference=True),
        _record("2021-03-16", "2021-03-17", has_sep=True, has_press_conference=True),
        _record("2021-04-27", "2021-04-28", has_press_conference=True),
        _record("2021-06-15", "2021-06-16", has_sep=True, has_press_conference=True),
        _record("2021-07-27", "2021-07-28", has_press_conference=True),
        _record("2021-09-21", "2021-09-22", has_sep=True, has_press_conference=True),
        _record("2021-11-02", "2021-11-03", has_press_conference=True),
        _record("2021-12-14", "2021-12-15", has_sep=True, has_press_conference=True),
        # 2022 current calendar.
        _record("2022-01-25", "2022-01-26", has_press_conference=True),
        _record("2022-03-15", "2022-03-16", has_sep=True, has_press_conference=True),
        _record("2022-05-03", "2022-05-04", has_press_conference=True),
        _record("2022-06-14", "2022-06-15", has_sep=True, has_press_conference=True),
        _record("2022-07-26", "2022-07-27", has_press_conference=True),
        _record("2022-09-20", "2022-09-21", has_sep=True, has_press_conference=True),
        _record("2022-11-01", "2022-11-02", has_press_conference=True),
        _record("2022-12-13", "2022-12-14", has_sep=True, has_press_conference=True),
        # 2023 current calendar.
        _record("2023-01-31", "2023-02-01", has_press_conference=True),
        _record("2023-03-21", "2023-03-22", has_sep=True, has_press_conference=True),
        _record("2023-05-02", "2023-05-03", has_press_conference=True),
        _record("2023-06-13", "2023-06-14", has_sep=True, has_press_conference=True),
        _record("2023-07-25", "2023-07-26", has_press_conference=True),
        _record("2023-09-19", "2023-09-20", has_sep=True, has_press_conference=True),
        _record("2023-10-31", "2023-11-01", has_press_conference=True),
        _record("2023-12-12", "2023-12-13", has_sep=True, has_press_conference=True),
        # 2024 current calendar.
        _record("2024-01-30", "2024-01-31", has_press_conference=True),
        _record("2024-03-19", "2024-03-20", has_sep=True, has_press_conference=True),
        _record("2024-04-30", "2024-05-01", has_press_conference=True),
        _record("2024-06-11", "2024-06-12", has_sep=True, has_press_conference=True),
        _record("2024-07-30", "2024-07-31", has_press_conference=True),
        _record("2024-09-17", "2024-09-18", has_sep=True, has_press_conference=True),
        _record("2024-11-06", "2024-11-07", has_press_conference=True),
        _record("2024-12-17", "2024-12-18", has_sep=True, has_press_conference=True),
        # 2025 current calendar.
        _record("2025-01-28", "2025-01-29", has_press_conference=True),
        _record("2025-03-18", "2025-03-19", has_sep=True, has_press_conference=True),
        _record("2025-05-06", "2025-05-07", has_press_conference=True),
        _record("2025-06-17", "2025-06-18", has_sep=True, has_press_conference=True),
        _record("2025-07-29", "2025-07-30", has_press_conference=True),
        _record("2025-09-16", "2025-09-17", has_sep=True, has_press_conference=True),
        _record("2025-10-28", "2025-10-29", has_press_conference=True),
        _record("2025-12-09", "2025-12-10", has_sep=True, has_press_conference=True),
    ]

    if include_2026_partial:
        rows.extend(
            [
                _record("2026-01-27", "2026-01-28", has_press_conference=True),
                _record(
                    "2026-03-17",
                    "2026-03-18",
                    has_sep=True,
                    has_press_conference=True,
                ),
                _record("2026-04-28", "2026-04-29", has_press_conference=True),
                _record(
                    "2026-06-16",
                    "2026-06-17",
                    has_sep=True,
                    has_press_conference=True,
                ),
                _record("2026-07-28", "2026-07-29", has_press_conference=True),
            ]
        )

    return sorted(
        rows,
        key=lambda row: (
            row["statement_date"] or row["meeting_end_date"],
            row["meeting_start_date"],
        ),
    )


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    if month == 12:
        first_next = date(year + 1, 1, 1)
    else:
        first_next = date(year, month + 1, 1)
    candidate = first_next - timedelta(days=1)
    return candidate - timedelta(days=(candidate.weekday() - weekday) % 7)


def _gregorian_easter(year: int) -> date:
    """Meeus/Jones/Butcher Gregorian Easter algorithm."""

    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    ell = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ell) // 451
    month = (h + ell - 7 * m + 114) // 31
    day = (h + ell - 7 * m + 114) % 31 + 1
    return date(year, month, day)


def _observed_fixed_holiday(
    year: int, month: int, day: int, *, saturday_previous: bool = True
) -> date | None:
    holiday = date(year, month, day)
    if holiday.weekday() == 5:
        return holiday - timedelta(days=1) if saturday_previous else None
    if holiday.weekday() == 6:
        return holiday + timedelta(days=1)
    return holiday


def nyse_holidays(year: int) -> set[date]:
    """Return full-day NYSE equity-market closures for one year.

    The recurring schedule follows the official NYSE holiday calendar.  The
    exchange does not observe New Year's Day on the preceding Friday when
    January 1 is Saturday.  Juneteenth enters the exchange schedule in 2022.
    The two one-off national days of mourning inside the audit horizon are
    included from the official NYSE notices linked in the source registry.
    Early-close days remain trading sessions.
    """

    holidays: set[date] = {
        _nth_weekday(year, 1, 0, 3),  # Martin Luther King Jr. Day
        _nth_weekday(year, 2, 0, 3),  # Washington's Birthday
        _gregorian_easter(year) - timedelta(days=2),  # Good Friday
        _last_weekday(year, 5, 0),  # Memorial Day
        _nth_weekday(year, 9, 0, 1),  # Labor Day
        _nth_weekday(year, 11, 3, 4),  # Thanksgiving
    }
    new_year = _observed_fixed_holiday(
        year, 1, 1, saturday_previous=False
    )
    independence = _observed_fixed_holiday(year, 7, 4)
    christmas = _observed_fixed_holiday(year, 12, 25)
    for holiday in (new_year, independence, christmas):
        if holiday is not None and holiday.year == year:
            holidays.add(holiday)
    if year >= 2022:
        juneteenth = _observed_fixed_holiday(year, 6, 19)
        if juneteenth is not None and juneteenth.year == year:
            holidays.add(juneteenth)
    if year == 2018:
        holidays.add(date(2018, 12, 5))  # President George H.W. Bush
    if year == 2025:
        holidays.add(date(2025, 1, 9))  # President Jimmy Carter
    return holidays


def trading_sessions(start: date, end: date) -> list[date]:
    """Generate NYSE full and early-close trading dates, inclusive."""

    if end < start:
        raise ValueError("end precedes start")
    holidays_by_year = {
        year: nyse_holidays(year) for year in range(start.year, end.year + 1)
    }
    sessions: list[date] = []
    current = start
    while current <= end:
        if current.weekday() < 5 and current not in holidays_by_year[current.year]:
            sessions.append(current)
        current += timedelta(days=1)
    return sessions


def signed_trading_day_distance(
    anchor: date, target: date, sessions: Sequence[date]
) -> int:
    """Count signed NYSE sessions crossed from ``anchor`` to ``target``.

    If target is later, this counts sessions ``anchor < s <= target``.  If
    target is earlier, it returns minus the count of sessions
    ``target <= s < anchor``.  The same calendar date is always zero.  This
    definition remains explicit when an announcement anchor falls on a weekend.
    """

    if target == anchor:
        return 0
    if target > anchor:
        return sum(anchor < session <= target for session in sessions)
    return -sum(target <= session < anchor for session in sessions)


def _parse_date(value: object) -> tuple[date | None, str | None]:
    text = "" if value is None else str(value).strip()
    if not text:
        return None, None
    try:
        return date.fromisoformat(text), None
    except ValueError:
        return None, f"invalid ISO date: {text}"


def _field(row: Mapping[str, object], canonical: str) -> str:
    for alias in ANCHOR_ALIASES[canonical]:
        value = str(row.get(alias, "") or "").strip()
        if value:
            return value
    return ""


def read_ledger(path: Path) -> tuple[list[dict[str, str]], str | None]:
    if not path.exists():
        return [], f"ledger not found: {path}"
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return [], f"ledger has no header: {path}"
        rows = [
            {key: (value or "").strip() for key, value in row.items()}
            for row in reader
        ]
    if not rows:
        return [], f"ledger has no event rows: {path}"
    return rows, None


def _canonical_intervention_date(
    event: Mapping[str, object],
) -> tuple[date | None, str]:
    for field in (
        "implementation_close_date",
        "effective_open_date",
        "secondary_adjustment_date",
        "earliest_public_announcement_date",
        "input_reference_date",
    ):
        parsed, error = _parse_date(_field(event, field))
        if parsed is not None and error is None:
            return parsed, field
    return None, ""


def _event_id(event: Mapping[str, object], row_number: int) -> str:
    return str(event.get("event_id", "") or "").strip() or f"ROW_{row_number}_UNRESOLVED"


def _event_group_id(
    event: Mapping[str, object], event_id: str, intervention_date: date | None
) -> str:
    supplied = str(event.get("event_group_id", "") or "").strip()
    if supplied:
        return supplied
    if intervention_date:
        return f"DATE:{intervention_date.isoformat()}"
    return f"EVENT:{event_id}"


def _event_group_dates(
    events: Sequence[Mapping[str, object]],
) -> dict[str, set[date]]:
    result: dict[str, set[date]] = defaultdict(set)
    for index, event in enumerate(events, start=1):
        event_id = _event_id(event, index)
        intervention, _ = _canonical_intervention_date(event)
        group = _event_group_id(event, event_id, intervention)
        if intervention:
            result[group].add(intervention)
    return result


def _base_support_row(
    event: Mapping[str, object],
    row_number: int,
    anchor: str,
    anchor_date: str,
    meeting_id: str,
) -> dict[str, str]:
    event_id = _event_id(event, row_number)
    intervention, intervention_basis = _canonical_intervention_date(event)
    group = _event_group_id(event, event_id, intervention)
    basket_assignment = (
        str(event.get("basket_assignment_id", "") or "").strip() or event_id
    )
    return {
        field: "" for field in SUPPORT_FIELDS
    } | {
        "evidence_key": f"SUPPORT:{event_id}:{meeting_id}:{anchor}",
        "event_id": event_id,
        "event_evidence_key": (
            str(event.get("evidence_key", "") or "").strip()
            or f"EVENT:{event_id}"
        ),
        "event_group_id": group,
        "basket_assignment_id": basket_assignment,
        "anchor": anchor,
        "anchor_date": anchor_date,
        "intervention_date": intervention.isoformat() if intervention else "",
        "intervention_date_basis": intervention_basis,
        "common_rebalance_group_id": group,
        "meeting_id": meeting_id,
        "event_source_id": str(event.get("source_id", "") or "").strip(),
        "event_source_url": str(event.get("source_url", "") or "").strip(),
        "trading_calendar_source_id": TRADING_CALENDAR_SOURCE_ID,
        "trading_calendar_source_url": NYSE_HOURS_URL,
        "shared_stock_overlap_status": (
            str(event.get("shared_stock_overlap_status", "") or "").strip()
            or "NOT_EVALUATED_NO_CONSTITUENT_INPUT"
        ),
        "comparison_id": str(event.get("comparison_id", "") or "").strip(),
    }


def missing_ledger_support_row(reason: str) -> dict[str, str]:
    row = {field: "" for field in SUPPORT_FIELDS}
    row.update(
        {
            "evidence_key": "SUPPORT:LEDGER_MISSING:UNRESOLVED:ledger_input",
            "event_id": "LEDGER_MISSING",
            "anchor": "ledger_input",
            "meeting_id": "UNRESOLVED",
            "trading_calendar_source_id": TRADING_CALENDAR_SOURCE_ID,
            "trading_calendar_source_url": NYSE_HOURS_URL,
            "shared_stock_overlap_status": "NOT_EVALUATED_NO_CONSTITUENT_INPUT",
            "status": "BLOCKED_INPUT",
            "notes": (
                f"{reason}. Re-run this script after Stage B writes the ledger; "
                "no event dates or support counts were inferred."
            ),
        }
    )
    return row


def build_support(
    calendar: Sequence[Mapping[str, str]],
    events: Sequence[Mapping[str, object]],
) -> list[dict[str, str]]:
    """Intersect Stage B dates with eligible official FOMC statement dates."""

    eligible = [
        row
        for row in calendar
        if row.get("eligible_common_news") == "1" and row.get("statement_date")
    ]
    if not events:
        return [missing_ledger_support_row("ledger has no event rows")]

    all_dates: list[date] = [
        date.fromisoformat(row["statement_date"]) for row in eligible
    ]
    for event in events:
        for anchor in ANCHOR_FIELDS:
            parsed, _ = _parse_date(_field(event, anchor))
            if parsed:
                all_dates.append(parsed)
    session_start = min(all_dates) - timedelta(days=400)
    session_end = max(all_dates) + timedelta(days=400)
    sessions = trading_sessions(session_start, session_end)
    group_dates = _event_group_dates(events)
    output: list[dict[str, str]] = []

    for event_number, event in enumerate(events, start=1):
        event_id = _event_id(event, event_number)
        intervention, _ = _canonical_intervention_date(event)
        own_group = _event_group_id(event, event_id, intervention)
        announcement, announcement_error = _parse_date(
            _field(event, "earliest_public_announcement_date")
        )
        anticipation_end, anticipation_end_error = _parse_date(
            _field(event, "effective_open_date")
            or _field(event, "implementation_close_date")
        )
        anticipation_valid = (
            announcement is not None
            and anticipation_end is not None
            and announcement <= anticipation_end
            and announcement_error is None
            and anticipation_end_error is None
        )
        next_intervention, next_error = _parse_date(
            _field(event, "next_intervention_date")
        )

        for anchor in ANCHOR_FIELDS:
            raw_anchor = _field(event, anchor)
            anchor_day, anchor_error = _parse_date(raw_anchor)
            if anchor_day is None:
                row = _base_support_row(
                    event, event_number, anchor, raw_anchor, "UNRESOLVED"
                )
                row["source_id"] = row["event_source_id"]
                row["source_url"] = row["event_source_url"]
                row["status"] = (
                    "INVALID_DATE" if anchor_error else "UNRESOLVED_ANCHOR"
                )
                row["notes"] = (
                    f"{anchor_error or 'Stage B did not establish this date'}; "
                    "no FOMC distance or band count computed."
                )
                output.append(row)
                continue

            meeting_distances: list[tuple[Mapping[str, str], date, int]] = []
            for meeting in eligible:
                statement = date.fromisoformat(meeting["statement_date"])
                distance = signed_trading_day_distance(
                    anchor_day, statement, sessions
                )
                meeting_distances.append((meeting, statement, distance))

            pre_candidates = [item for item in meeting_distances if item[1] < anchor_day]
            post_candidates = [item for item in meeting_distances if item[1] > anchor_day]
            nearest_pre_id = (
                min(pre_candidates, key=lambda item: (abs(item[2]), -item[1].toordinal()))[
                    0
                ]["meeting_id"]
                if pre_candidates
                else ""
            )
            nearest_post_id = (
                min(post_candidates, key=lambda item: (abs(item[2]), item[1]))[0][
                    "meeting_id"
                ]
                if post_candidates
                else ""
            )

            counts: dict[int, tuple[int, int, int]] = {}
            anticipation_overlap: dict[int, int] = {}
            next_overlap: dict[int, int] = {}
            other_counts: dict[int, int] = {}
            for band in (20, 40, 60):
                in_band = [item for item in meeting_distances if abs(item[2]) <= band]
                pre_count = sum(item[1] < anchor_day for item in in_band)
                post_count = sum(item[1] > anchor_day for item in in_band)
                counts[band] = (pre_count, post_count, len(in_band))
                anticipation_overlap[band] = int(
                    anticipation_valid
                    and any(
                        announcement <= item[1] <= anticipation_end
                        for item in in_band
                    )
                )
                next_overlap[band] = int(
                    next_intervention is not None
                    and next_error is None
                    and next_intervention > anchor_day
                    and abs(
                        signed_trading_day_distance(
                            anchor_day, next_intervention, sessions
                        )
                    )
                    <= band
                )
                other_counts[band] = len(
                    {
                        group
                        for group, dates in group_dates.items()
                        if group != own_group
                        and any(
                            abs(
                                signed_trading_day_distance(
                                    anchor_day, intervention_day, sessions
                                )
                            )
                            <= band
                            for intervention_day in dates
                        )
                    }
                )

            selected = [
                item
                for item in meeting_distances
                if abs(item[2]) <= 60
                or item[0]["meeting_id"] in {nearest_pre_id, nearest_post_id}
                or item[1] == anchor_day
            ]
            for meeting, statement, distance in selected:
                row = _base_support_row(
                    event,
                    event_number,
                    anchor,
                    anchor_day.isoformat(),
                    meeting["meeting_id"],
                )
                if statement < anchor_day:
                    relation = "pre"
                elif statement > anchor_day:
                    relation = "post"
                else:
                    relation = "same_day"
                row.update(
                    {
                        "fomc_evidence_key": meeting["evidence_key"],
                        "common_news_group_id": meeting["meeting_id"],
                        "statement_date": statement.isoformat(),
                        "temporal_relation": relation,
                        "trading_day_distance_signed": str(distance),
                        "calendar_day_distance_signed": str(
                            (statement - anchor_day).days
                        ),
                        "nearest_pre": str(
                            int(meeting["meeting_id"] == nearest_pre_id)
                        ),
                        "nearest_post": str(
                            int(meeting["meeting_id"] == nearest_post_id)
                        ),
                        "same_day": str(int(statement == anchor_day)),
                        "within_20td": str(int(abs(distance) <= 20)),
                        "within_40td": str(int(abs(distance) <= 40)),
                        "within_60td": str(int(abs(distance) <= 60)),
                        "meeting_in_anticipation_interval": str(
                            int(
                                anticipation_valid
                                and announcement <= statement <= anticipation_end
                            )
                        ),
                        "meeting_on_or_after_next_intervention": str(
                            int(
                                next_intervention is not None
                                and next_error is None
                                and statement >= next_intervention
                            )
                        ),
                        "has_sep": meeting["has_sep"],
                        "has_press_conference": meeting["has_press_conference"],
                        "communication_package": meeting[
                            "communication_package"
                        ],
                        "source_id": meeting["source_id"],
                        "source_url": meeting["statement_url"]
                        or meeting["source_url"],
                        "status": "COMPUTED_DAILY_CALENDAR_SUPPORT",
                        "notes": (
                            "Descriptive daily support only. FOMC statement, "
                            "press-conference, and SEP phases share one meeting "
                            "package and are not independent macro shocks. This "
                            "row makes no intraday-feasibility or MDE claim."
                        ),
                    }
                )
                for band in (20, 40, 60):
                    pre_count, post_count, total_count = counts[band]
                    row[f"pre_count_{band}td"] = str(pre_count)
                    row[f"post_count_{band}td"] = str(post_count)
                    row[f"total_count_{band}td"] = str(total_count)
                    row[f"band_{band}_overlaps_anticipation"] = str(
                        anticipation_overlap[band]
                    )
                    row[f"band_{band}_overlaps_next_intervention"] = str(
                        next_overlap[band]
                    )
                    row[f"other_intervention_group_count_{band}td"] = str(
                        other_counts[band]
                    )
                output.append(row)

    keys = [row["evidence_key"] for row in output]
    if len(keys) != len(set(keys)):
        duplicates = sorted(key for key in set(keys) if keys.count(key) > 1)
        raise ValueError(f"duplicate support evidence keys: {duplicates[:5]}")
    return sorted(
        output,
        key=lambda row: (
            row["event_id"],
            ANCHOR_FIELDS.index(row["anchor"])
            if row["anchor"] in ANCHOR_FIELDS
            else len(ANCHOR_FIELDS),
            row["statement_date"],
            row["meeting_id"],
        ),
    )


def source_registry_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for year in range(2017, 2021):
        rows.append(
            {
                "evidence_key": f"SOURCE:FED_FOMC_HIST_{year}",
                "source_id": f"FED_FOMC_HIST_{year}",
                "publisher": "Board of Governors of the Federal Reserve System",
                "title": f"Federal Open Market Committee historical materials: {year}",
                "source_url": _historical_url(year),
                "retrieval_date": RETRIEVAL_DATE,
                "source_role": "meeting dates; statements; SEP and press-conference package",
                "status": "USED_OFFICIAL_PRIMARY_SOURCE",
                "notes": "Rendered headings and linked official statement materials reviewed.",
            }
        )
    rows.extend(
        [
            {
                "evidence_key": "SOURCE:FED_FOMC_CAL_2021_2027",
                "source_id": "FED_FOMC_CAL_2021_2027",
                "publisher": "Board of Governors of the Federal Reserve System",
                "title": "Meeting calendars, statements, and minutes (2021-2027)",
                "source_url": FED_CURRENT_CALENDAR_URL,
                "retrieval_date": RETRIEVAL_DATE,
                "source_role": "meeting dates; statements; SEP and press-conference package",
                "status": "USED_OFFICIAL_PRIMARY_SOURCE",
                "notes": "2026 is retained only through the latest realized July 29 meeting.",
            },
            {
                "evidence_key": "SOURCE:FED_FOMC_HISTORICAL_INDEX",
                "source_id": "FED_FOMC_HISTORICAL_INDEX",
                "publisher": "Board of Governors of the Federal Reserve System",
                "title": "Transcripts and other historical materials",
                "source_url": FED_HISTORICAL_INDEX_URL,
                "retrieval_date": RETRIEVAL_DATE,
                "source_role": "document definitions and historical-page routing",
                "status": "USED_OFFICIAL_PRIMARY_SOURCE",
                "notes": "Defines policy statements and SEP publication history.",
            },
            {
                "evidence_key": "SOURCE:FRBSF_USMPD_20260803",
                "source_id": USMPD_REGISTRY_ID,
                "publisher": "Federal Reserve Bank of San Francisco",
                "title": "U.S. Monetary Policy Event-Study Database",
                "source_url": USMPD_PAGE_URL,
                "retrieval_date": RETRIEVAL_DATE,
                "source_role": "availability and metadata screening only",
                "status": "SCREENED_OFFICIAL_PUBLIC_DATASET",
                "notes": (
                    "No USMPD surprise, return, or event classification is assigned "
                    "to calendar rows in this audit."
                ),
            },
            {
                "evidence_key": "SOURCE:NYSE_HOLIDAY_CALENDAR",
                "source_id": "NYSE_HOLIDAY_CALENDAR",
                "publisher": "New York Stock Exchange",
                "title": "Holidays and trading hours",
                "source_url": NYSE_HOURS_URL,
                "retrieval_date": RETRIEVAL_DATE,
                "source_role": "recurring full-day exchange closures",
                "status": "USED_OFFICIAL_PRIMARY_SOURCE",
                "notes": "Early closes remain trading sessions for daily-distance counts.",
            },
            {
                "evidence_key": "SOURCE:NYSE_TRADING_DAYS",
                "source_id": "NYSE_TRADING_DAYS",
                "publisher": "New York Stock Exchange",
                "title": "NYSE trading-day counts",
                "source_url": NYSE_TRADING_DAYS_URL,
                "retrieval_date": RETRIEVAL_DATE,
                "source_role": "annual trading-session count cross-check",
                "status": "USED_OFFICIAL_PRIMARY_SOURCE",
                "notes": "Cross-check for the codified recurring holiday calendar.",
            },
            {
                "evidence_key": "SOURCE:NYSE_BUSH_CLOSURE_20181205",
                "source_id": "NYSE_BUSH_CLOSURE_20181205",
                "publisher": "New York Stock Exchange",
                "title": "National Day of Mourning closure: December 5, 2018",
                "source_url": NYSE_BUSH_CLOSURE_URL,
                "retrieval_date": RETRIEVAL_DATE,
                "source_role": "one-off full-day exchange closure",
                "status": "USED_OFFICIAL_PRIMARY_SOURCE",
                "notes": "Included in the trading-session calendar.",
            },
            {
                "evidence_key": "SOURCE:NYSE_CARTER_CLOSURE_20250109",
                "source_id": "NYSE_CARTER_CLOSURE_20250109",
                "publisher": "New York Stock Exchange",
                "title": "National Day of Mourning closure: January 9, 2025",
                "source_url": NYSE_CARTER_CLOSURE_URL,
                "retrieval_date": RETRIEVAL_DATE,
                "source_role": "one-off full-day exchange closure",
                "status": "USED_OFFICIAL_PRIMARY_SOURCE",
                "notes": "Included in the trading-session calendar.",
            },
            {
                "evidence_key": "SOURCE:NYSE_JUNETEENTH_RULE_2021",
                "source_id": "NYSE_JUNETEENTH_RULE_2021",
                "publisher": "New York Stock Exchange",
                "title": "Exchange rule filing adding Juneteenth holiday",
                "source_url": NYSE_JUNETEENTH_RULE_URL,
                "retrieval_date": RETRIEVAL_DATE,
                "source_role": "Juneteenth closure effective for 2022 onward",
                "status": "USED_OFFICIAL_PRIMARY_SOURCE",
                "notes": "Juneteenth is not backcast before 2022.",
            },
        ]
    )
    return rows


_XLSX_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_XLSX_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_XLSX_PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def _xlsx_sheet_rows(archive: ZipFile, target: str) -> list[dict[str, str]]:
    namespace = {"m": _XLSX_MAIN_NS}
    root = ET.fromstring(archive.read(target))
    rows: list[dict[str, str]] = []
    for row_element in root.findall(".//m:sheetData/m:row", namespace):
        values: dict[str, str] = {}
        for cell in row_element.findall("m:c", namespace):
            reference = cell.attrib.get("r", "")
            column = reference.rstrip("0123456789")
            if cell.attrib.get("t") == "inlineStr":
                value = "".join(
                    item.text or ""
                    for item in cell.findall(".//m:t", namespace)
                )
            else:
                value_element = cell.find("m:v", namespace)
                value = value_element.text if value_element is not None else ""
            values[column] = value
        rows.append(values)
    return rows


def inspect_usmpd_xlsx(path: Path) -> list[dict[str, str]]:
    """Screen the public USMPD workbook structure without importing factors."""

    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    main_ns = {"m": _XLSX_MAIN_NS, "r": _XLSX_REL_NS}
    with ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(
            archive.read("xl/_rels/workbook.xml.rels")
        )
        relationship_targets = {
            item.attrib["Id"]: item.attrib["Target"]
            for item in relationships.findall(
                f"{{{_XLSX_PACKAGE_REL_NS}}}Relationship"
            )
        }
        sheets: dict[str, str] = {}
        for sheet in workbook.findall(".//m:sheets/m:sheet", main_ns):
            relationship_id = sheet.attrib[f"{{{_XLSX_REL_NS}}}id"]
            target = relationship_targets[relationship_id]
            if target.startswith("/"):
                target = target.lstrip("/")
            else:
                target = f"xl/{target}"
            sheets[sheet.attrib["name"]] = target

        window_definitions = {
            "Statements": "30 minutes: -10 to +20 around statement release",
            "Press Conferences": "70 minutes: -10 to +60 around press-conference start",
            "Monetary Events": (
                "100 minutes: -10 before statement to +60 after press-conference "
                "start; statement window when no press conference"
            ),
            "Minutes": "30 minutes: -10 to +20 around minutes release",
        }
        output: list[dict[str, str]] = []
        for sheet_name in (
            "Statements",
            "Press Conferences",
            "Monetary Events",
            "Minutes",
        ):
            rows = _xlsx_sheet_rows(archive, sheets[sheet_name])
            header = rows[0]
            data = rows[1:]
            excel_dates = [float(row["A"]) for row in data if row.get("A")]
            epoch = datetime(1899, 12, 30)
            observed_min = (epoch + timedelta(days=min(excel_dates))).date()
            observed_max = (epoch + timedelta(days=max(excel_dates))).date()
            output.append(
                {
                    "evidence_key": (
                        f"SOURCE:{USMPD_REGISTRY_ID}:{sheet_name.upper().replace(' ', '_')}"
                    ),
                    "registry_id": USMPD_REGISTRY_ID,
                    "dataset_name": "U.S. Monetary Policy Event-Study Database",
                    "publisher": "Federal Reserve Bank of San Francisco",
                    "page_updated": "2026-08-03",
                    "retrieval_date": RETRIEVAL_DATE,
                    "page_url": USMPD_PAGE_URL,
                    "download_url": USMPD_DOWNLOAD_URL,
                    "workbook_sha256": digest,
                    "sheet_name": sheet_name,
                    "observed_row_count": str(len(data)),
                    "observed_date_min": observed_min.isoformat(),
                    "observed_date_max": observed_max.isoformat(),
                    "metadata_columns": "|".join(header.values()),
                    "event_window_definition": window_definitions[sheet_name],
                    "row_level_classification_status": (
                        "METADATA_SCREEN_ONLY_NO_ROW_CLASSIFICATION_ASSIGNED"
                    ),
                    "status": "SCREENED_OFFICIAL_PUBLIC_WORKBOOK",
                    "notes": (
                        "Coverage and schema are availability evidence only; no "
                        "factor, surprise, return, or row-level event class was "
                        "imported into the Gate 1 calendar."
                    ),
                }
            )
    return output


def unscreened_usmpd_registry_row() -> dict[str, str]:
    row = {field: "" for field in USMPD_REGISTRY_FIELDS}
    row.update(
        {
            "evidence_key": f"SOURCE:{USMPD_REGISTRY_ID}:DATASET",
            "registry_id": USMPD_REGISTRY_ID,
            "dataset_name": "U.S. Monetary Policy Event-Study Database",
            "publisher": "Federal Reserve Bank of San Francisco",
            "page_updated": "2026-08-03",
            "retrieval_date": RETRIEVAL_DATE,
            "page_url": USMPD_PAGE_URL,
            "download_url": USMPD_DOWNLOAD_URL,
            "row_level_classification_status": (
                "METADATA_SCREEN_ONLY_NO_ROW_CLASSIFICATION_ASSIGNED"
            ),
            "status": "PUBLIC_DOWNLOAD_REGISTERED_NOT_LOCALLY_INSPECTED_THIS_RUN",
            "notes": "Pass --usmpd-xlsx to record workbook hash, sheets, and coverage.",
        }
    )
    return row


def write_csv(path: Path, rows: Iterable[Mapping[str, object]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def validate_calendar(rows: Sequence[Mapping[str, str]]) -> None:
    if not rows:
        raise ValueError("calendar is empty")
    keys = [row["evidence_key"] for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("calendar evidence keys are not unique")
    for row in rows:
        if not row["evidence_key"].startswith("FOMC:"):
            raise ValueError(f"invalid FOMC evidence key: {row['evidence_key']}")
        if row["eligible_common_news"] == "1":
            if row["scheduled_status"] != "scheduled_regular":
                raise ValueError(f"eligible row is not scheduled: {row['meeting_id']}")
            if not row["statement_date"] or not row["statement_url"]:
                raise ValueError(f"eligible row lacks statement: {row['meeting_id']}")
            statement = date.fromisoformat(row["statement_date"])
            if statement.weekday() >= 5 or statement in nyse_holidays(statement.year):
                raise ValueError(
                    f"eligible statement is not an NYSE session: {row['meeting_id']}"
                )


def _build_log_lines(
    calendar: Sequence[Mapping[str, str]],
    support: Sequence[Mapping[str, str]],
    ledger_path: Path,
    ledger_issue: str | None,
) -> list[str]:
    core = [row for row in calendar if row["calendar_scope"] == "primary_2018_2025"]
    core_eligible = [row for row in core if row["eligible_common_news"] == "1"]
    partial = [
        row for row in calendar if row["calendar_scope"].startswith("partial_extension")
    ]
    resolved_support = [
        row for row in support if row["status"] == "COMPUTED_DAILY_CALENDAR_SUPPORT"
    ]
    event_ids = {
        row["event_id"] for row in resolved_support if row["event_id"]
    }
    meeting_ids = {
        row["meeting_id"] for row in resolved_support if row["meeting_id"]
    }
    intervention_groups = {
        row["common_rebalance_group_id"]
        for row in resolved_support
        if row["common_rebalance_group_id"]
    }
    basket_ids = {
        row["basket_assignment_id"]
        for row in resolved_support
        if row["basket_assignment_id"]
    }
    lines = [
        f"retrieval_date={RETRIEVAL_DATE}",
        f"calendar_rows_total={len(calendar)}",
        f"calendar_rows_primary_2018_2025={len(core)}",
        f"eligible_scheduled_statement_meetings_primary_2018_2025={len(core_eligible)}",
        f"calendar_rows_partial_2026={len(partial)}",
        f"ledger_path={ledger_path}",
        f"ledger_issue={ledger_issue or ''}",
        f"support_rows_total={len(support)}",
        f"support_rows_resolved={len(resolved_support)}",
        f"resolved_unique_event_ids={len(event_ids)}",
        f"resolved_unique_intervention_groups={len(intervention_groups)}",
        f"resolved_unique_basket_assignment_ids={len(basket_ids)}",
        f"resolved_unique_fomc_meeting_ids={len(meeting_ids)}",
        "counting_note=Meeting, intervention-group, and basket-assignment counts are distinct concepts; none is labelled an independent-observation count.",
        "measurement_note=No intraday feasibility, quote-data availability, factor construction, power, or MDE claim is made.",
    ]
    return lines


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ledger",
        type=Path,
        default=ROOT / "rebalance_event_ledger.csv",
        help="Stage B event ledger (missing input yields an explicit scaffold row)",
    )
    parser.add_argument(
        "--calendar-output", type=Path, default=ROOT / "fomc_calendar.csv"
    )
    parser.add_argument(
        "--support-output",
        type=Path,
        default=ROOT / "assignment_and_fomc_support.csv",
    )
    parser.add_argument(
        "--source-registry-output",
        type=Path,
        default=ROOT / "logs" / "stage_e_sources.csv",
    )
    parser.add_argument(
        "--usmpd-registry-output",
        type=Path,
        default=ROOT / "logs" / "stage_e_usmpd_registry.csv",
    )
    parser.add_argument(
        "--usmpd-xlsx",
        type=Path,
        help="Optional official public workbook downloaded from the registered URL",
    )
    parser.add_argument(
        "--build-log-output",
        type=Path,
        default=ROOT / "logs" / "stage_e_build.log",
    )
    parser.add_argument(
        "--exclude-2026-partial",
        action="store_true",
        help="Omit the separately labelled realized 2026 extension",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    calendar = calendar_records(include_2026_partial=not args.exclude_2026_partial)
    validate_calendar(calendar)
    write_csv(args.calendar_output, calendar, CALENDAR_FIELDS)

    events, ledger_issue = read_ledger(args.ledger)
    support = (
        [missing_ledger_support_row(ledger_issue)]
        if ledger_issue
        else build_support(calendar, events)
    )
    write_csv(args.support_output, support, SUPPORT_FIELDS)
    write_csv(args.source_registry_output, source_registry_rows(), SOURCE_REGISTRY_FIELDS)

    if args.usmpd_xlsx:
        usmpd_rows = inspect_usmpd_xlsx(args.usmpd_xlsx)
    else:
        usmpd_rows = [unscreened_usmpd_registry_row()]
    write_csv(args.usmpd_registry_output, usmpd_rows, USMPD_REGISTRY_FIELDS)

    args.build_log_output.parent.mkdir(parents=True, exist_ok=True)
    args.build_log_output.write_text(
        "\n".join(
            _build_log_lines(calendar, support, args.ledger, ledger_issue)
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"wrote {len(calendar)} calendar rows and {len(support)} support rows; "
        f"ledger_status={'BLOCKED_INPUT' if ledger_issue else 'CONSUMED'}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
