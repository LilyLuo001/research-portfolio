#!/usr/bin/env python3
"""Prepare bounded P2 diagnostics from local metadata without session labels."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from measurement_input_adapter import candidate_repairs, read_csv, write_csv


ROOT = Path(__file__).resolve().parents[2]
EVENTS = ROOT / "missing_data_round_20260914/union_v2_earnings_inputs/selected_event_metadata.csv"
GAPS = ROOT / "gate1_20260915/core_mapping_gap_locators.csv"
CALENDAR = ROOT / "missing_data_round_20260914/union_v2_event_calendar_actions/trading_calendar.csv"
CALENDAR_RECEIPT = ROOT / "missing_data_round_20260914/union_v2_event_calendar_actions/receipt.json"
OUT = Path(__file__).parent / "prepared"


def main() -> None:
    events, gaps, days = read_csv(EVENTS), read_csv(GAPS), read_csv(CALENDAR)
    OUT.mkdir(exist_ok=True)
    hours = Counter()
    unparseable = 0
    for row in events:
        # This is a source-clock candidate diagnostic only: it never adds ET,
        # uncertainty bounds, market session labels, or first-release semantics.
        match = re.search(r"(?:^|[^0-9])(0?[0-9]|1[0-9]|2[0-3]):[0-5][0-9]", row["announcement_times_all"])
        if match:
            hours[(row["sample_period"], f"hour_{int(match.group(1)):02d}")] += 1
        else:
            unparseable += 1
    write_csv(OUT / "source_clock_time_of_day_histogram.csv", [
        {"sample_period": period, "source_clock_hour_candidate": hour, "association_count": str(count),
         "diagnostic_scope": "IF_EASTERN_CANDIDATE_ONLY_NO_SESSION_LABEL"}
        for (period, hour), count in sorted(hours.items())
    ])
    repairs = candidate_repairs(events, gaps)
    write_csv(OUT / "candidate_repair_associations.csv", repairs)
    calendar_columns = set(days[0]) if days else set()
    receipt = json.loads(CALENDAR_RECEIPT.read_text(encoding="utf-8"))
    strict = {
        "strict_clock_session_status": "UNKNOWN_FOR_ALL_852",
        "reason": "NO_SOURCE_SPECIFIC_TIMEZONE_AND_NO_UNCERTAINTY_BOUNDS; existing calendar lacks intraday open/close fields",
        "existing_calendar_version_sha256": receipt["calendar_sha256"],
        "existing_calendar_fields": sorted(calendar_columns),
        "required_but_absent_calendar_fields": ["calendar_id", "calendar_timezone", "open_local", "close_local"],
        "source_clock_session_if_eastern": "NOT_COMPUTABLE: existing calendar supplies observed trading dates only, not intraday boundaries",
        "source_clock_time_of_day_histogram": "WRITTEN_WITHOUT_MARKET_SESSION_LABELS",
        "source_clock_candidate_interpretation": "Eastern/DST is documentary support for checked records only; not a full-population timezone or first-public-release certification",
        "source_clock_time_parseable_rows": sum(hours.values()),
        "source_clock_time_unparseable_rows": unparseable,
        "candidate_repair_associations": len(repairs),
        "financial_values_read_or_written": False,
        "quote_archives_read": False,
        "sha256": {
            "events": hashlib.sha256(EVENTS.read_bytes()).hexdigest(),
            "calendar": hashlib.sha256(CALENDAR.read_bytes()).hexdigest(),
        },
    }
    (OUT / "strict_clock_and_calendar_gap_receipt.json").write_text(json.dumps(strict, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
