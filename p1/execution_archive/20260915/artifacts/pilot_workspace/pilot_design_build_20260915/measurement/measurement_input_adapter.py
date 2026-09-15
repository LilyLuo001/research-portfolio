#!/usr/bin/env python3
"""Fail-closed metadata adapter for the P2 clock/session census.

This program deliberately accepts metadata only.  It never opens quote archives,
does not calculate a response, and does not infer a source clock from a displayed
time.  A definitive classification requires: a named source timezone, closed
uncertainty bounds, and a named calendar with the applicable session boundaries.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

EVENT_REQUIRED = {
    "association_id", "wave_id", "permno", "sample_period", "announcement_date",
    "announcement_times_all", "mapping_status", "date_valid_raw_symbol",
    "date_valid_ncusip",
}
EVENT_ALLOWLIST = EVENT_REQUIRED | {"pends", "tier", "liquidity_stratum", "analyst_count_90d", "sue_analyst_min2_coverage"}
INTERVAL_REQUIRED = {
    "association_id", "source_id", "source_timezone", "interval_lower",
    "interval_upper", "calendar_id",
}
CALENDAR_REQUIRED = {"calendar_id", "session_date", "calendar_timezone", "open_local", "close_local"}
GAP_ALLOWLIST = {"association_id", "sample_period", "symbol_role", "leg", "job_id", "symbol", "file_status", "mapping_status"}


def read_csv(path: Path, allowlist: set[str] | None = None) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if allowlist is None:
            return list(reader)
        missing = allowlist - set(reader.fieldnames or [])
        # Callers pass the exact required schema as their allowlist, so an
        # omitted projected field fails before any row is used.
        if missing:
            raise ValueError(f"{path.name}: missing projected columns {sorted(missing)}")
        # Explicitly project the permitted metadata fields; arbitrary columns
        # (including any future value-like additions) never reach callers.
        return [{key: row.get(key, "") for key in allowlist} for row in reader]


def require_columns(rows: list[dict[str, str]], required: set[str], label: str) -> None:
    if not rows:
        raise ValueError(f"{label}: empty input")
    missing = required - set(rows[0])
    if missing:
        raise ValueError(f"{label}: missing required columns {sorted(missing)}")


def parse_zoned(value: str, timezone: str) -> datetime:
    """Parse an ISO local or offset timestamp into a timezone-aware datetime."""
    candidate = datetime.fromisoformat(value.replace("Z", "+00:00"))
    zone = ZoneInfo(timezone)
    if candidate.tzinfo is None:
        first, second = candidate.replace(tzinfo=zone, fold=0), candidate.replace(tzinfo=zone, fold=1)
        if first.utcoffset() != second.utcoffset():
            raise ValueError("ambiguous local timestamp")
        if first.astimezone(ZoneInfo("UTC")).astimezone(zone).replace(tzinfo=None) != candidate:
            raise ValueError("nonexistent local timestamp")
        return first
    return candidate.astimezone(zone)


def calendar_bound(row: dict[str, str]) -> tuple[datetime, datetime]:
    zone = ZoneInfo(row["calendar_timezone"])
    day = datetime.fromisoformat(row["session_date"]).date()
    start = datetime.fromisoformat(f"{day.isoformat()}T{row['open_local']}").replace(tzinfo=zone)
    end = datetime.fromisoformat(f"{day.isoformat()}T{row['close_local']}").replace(tzinfo=zone)
    if end <= start:
        raise ValueError("calendar close must be after open")
    return start, end


def classify(interval: dict[str, str], calendar: dict[tuple[str, str], dict[str, str]]) -> dict[str, str]:
    """Return definitive only when the whole interval fits one named session.

    The result is RTH_60_ELIGIBLE only for an interval entirely in
    [open, close - 60 minutes]. Any absent provenance or boundary crossing is
    UNKNOWN; this avoids treating a minute display as a seconds-error bound.
    """
    identifier = interval["association_id"]
    needed = ("source_id", "source_timezone", "interval_lower", "interval_upper", "calendar_id")
    if any(not interval.get(k, "").strip() for k in needed):
        return {"association_id": identifier, "classification": "UNKNOWN", "reason": "MISSING_SOURCE_TIMEZONE_OR_BOUNDS_OR_CALENDAR"}
    try:
        lower = parse_zoned(interval["interval_lower"], interval["source_timezone"])
        upper = parse_zoned(interval["interval_upper"], interval["source_timezone"])
    except (ValueError, KeyError):
        return {"association_id": identifier, "classification": "UNKNOWN", "reason": "UNPARSEABLE_INTERVAL_OR_TIMEZONE"}
    if upper < lower:
        return {"association_id": identifier, "classification": "UNKNOWN", "reason": "REVERSED_UNCERTAINTY_BOUNDS"}
    # Calendar boundaries have their own explicit zone; source-zone values may
    # be UTC and must not be treated as local exchange clock values.
    calendar_zone = None
    calendar_id = interval["calendar_id"]
    candidate_sessions = [v for (key_id, _), v in calendar.items() if key_id == calendar_id]
    if not candidate_sessions:
        return {"association_id": identifier, "classification": "UNKNOWN", "reason": "CALENDAR_SESSION_NOT_SUPPLIED"}
    zones = {v.get('calendar_timezone', '') for v in candidate_sessions}
    if len(zones) != 1 or not next(iter(zones)):
        return {"association_id": identifier, "classification": "UNKNOWN", "reason": "CONFLICTING_OR_MISSING_CALENDAR_TIMEZONES"}
    try:
        calendar_zone = ZoneInfo(candidate_sessions[0]["calendar_timezone"])
    except (KeyError, ValueError):
        return {"association_id": identifier, "classification": "UNKNOWN", "reason": "INVALID_CALENDAR_TIMEZONE"}
    lower, upper = lower.astimezone(calendar_zone), upper.astimezone(calendar_zone)
    if lower.date() != upper.date():
        return {"association_id": identifier, "classification": "UNKNOWN", "reason": "INTERVAL_SPANS_CALENDAR_DATES"}
    key = (calendar_id, lower.date().isoformat())
    session = calendar.get(key)
    if session is None:
        return {"association_id": identifier, "classification": "UNKNOWN", "reason": "CALENDAR_SESSION_NOT_SUPPLIED"}
    try:
        opening, close = calendar_bound(session)
    except ValueError:
        return {"association_id": identifier, "classification": "UNKNOWN", "reason": "INVALID_CALENDAR_SESSION"}
    if upper < opening:
        return {"association_id": identifier, "classification": "DEFINITIVE_NON_RTH", "reason": "ENTIRE_INTERVAL_PREOPEN"}
    if lower >= close:
        return {"association_id": identifier, "classification": "DEFINITIVE_NON_RTH", "reason": "ENTIRE_INTERVAL_AFTERCLOSE"}
    if lower < opening or upper >= close:
        return {"association_id": identifier, "classification": "UNKNOWN", "reason": "INTERVAL_CROSSES_SESSION_BOUNDARY"}
    cutoff = close - timedelta(minutes=60)
    if upper <= cutoff:
        return {"association_id": identifier, "classification": "DEFINITIVE_RTH_60_ELIGIBLE", "reason": "ENTIRE_INTERVAL_BEFORE_RTH60_CUTOFF"}
    if lower > cutoff:
        return {"association_id": identifier, "classification": "DEFINITIVE_RTH_BUT_NOT_RTH_60", "reason": "ENTIRE_INTERVAL_AFTER_RTH60_CUTOFF"}
    return {"association_id": identifier, "classification": "UNKNOWN", "reason": "INTERVAL_CROSSES_RTH60_CUTOFF"}


def candidate_repairs(events: list[dict[str, str]], gaps: list[dict[str, str]]) -> list[dict[str, str]]:
    selected = {r["association_id"] for r in events}
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in gaps:
        if row["association_id"] in selected:
            grouped.setdefault(row["association_id"], []).append(row)
    result = []
    for association_id, rows in sorted(grouped.items()):
        symbols = sorted({r["symbol"] for r in rows if r["symbol_role"] == "STOCK"})
        if "CRD" in symbols:
            action = "CANDIDATE_CRD_CLASS_B_REPAIR_REQUIRED_FOR_EXISTING_CORE_LEGS"
        elif "GDEN" in symbols:
            action = "CANDIDATE_GDEN_TRANSPORT_RETRY_REQUIRED_FOR_EXISTING_CORE_LEG"
        else:
            action = "CANDIDATE_NON_STOCK_OR_UNRESOLVED_GAP"
        result.append({
            "association_id": association_id,
            "sample_period": rows[0]["sample_period"],
            "stock_symbols_with_gap": ";".join(symbols) or "NONE",
            "gap_row_count": str(len(rows)),
            "candidate_action": action,
            "final_eligibility": "NOT_CERTIFIED",
            "purchase_or_retry_authorized": "NO",
        })
    return result


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--mapping-gaps", type=Path, required=True)
    parser.add_argument("--intervals", type=Path, required=True, help="Custodian-produced metadata interval projection")
    parser.add_argument("--calendar", type=Path, required=True, help="Approved exchange-session projection")
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    events = read_csv(args.events, EVENT_ALLOWLIST)
    gaps = read_csv(args.mapping_gaps, GAP_ALLOWLIST)
    intervals = read_csv(args.intervals, INTERVAL_REQUIRED)
    sessions = read_csv(args.calendar, CALENDAR_REQUIRED)
    require_columns(events, EVENT_REQUIRED, "events")
    # An empty but schema-valid interval projection is a valid fail-closed
    # input: every manifest association is then classified UNKNOWN.
    require_columns(sessions, CALENDAR_REQUIRED, "calendar")
    event_ids = [r["association_id"] for r in events]
    if len(set(event_ids)) != len(event_ids):
        raise ValueError("events: duplicate association_id")
    calendar = {}
    for row in sessions:
        key = (row["calendar_id"], row["session_date"])
        if key in calendar:
            raise ValueError(f"calendar: duplicate key {key}")
        calendar[key] = row
    by_event: dict[str, list[dict[str, str]]] = {}
    for row in intervals:
        if row["association_id"] in set(event_ids):
            by_event.setdefault(row["association_id"], []).append(row)
    classifications = []
    for association_id in event_ids:
        candidates = by_event.get(association_id, [])
        if not candidates:
            classifications.append({"association_id": association_id, "classification": "UNKNOWN", "reason": "MISSING_INTERVAL_PROJECTION"})
        elif len(candidates) != 1:
            classifications.append({"association_id": association_id, "classification": "UNKNOWN", "reason": "DUPLICATE_OR_CONFLICTING_INTERVAL_PROJECTION"})
        else:
            classifications.append(classify(candidates[0], calendar))
    args.outdir.mkdir(parents=True, exist_ok=True)
    write_csv(args.outdir / "clock_session_census.csv", classifications)
    write_csv(args.outdir / "candidate_repair_associations.csv", candidate_repairs(events, gaps))
    summary = {
        "status": "METADATA_INTERFACE_PREPARED_NOT_MEASUREMENT_RUN",
        "event_rows_input": len(events),
        "interval_rows_received": len(intervals),
        "classification_rows_written": len(classifications),
        "classification_counts": dict(sorted(Counter(r["classification"] for r in classifications).items())),
        "unknown_reason_counts": dict(sorted(Counter(r["reason"] for r in classifications if r["classification"] == "UNKNOWN").items())),
        "candidate_repairs_are_not_final_eligibility": True,
        "financial_values_read_or_written": False,
        "quote_archives_read": False,
    }
    (args.outdir / "measurement_adapter_receipt.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
