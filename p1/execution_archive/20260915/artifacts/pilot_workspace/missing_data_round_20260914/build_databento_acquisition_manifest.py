#!/usr/bin/env python3
"""Compile outcome-independent quotation requests for the 480-event data round.

The broad date slices deliberately avoid treating the unverified IBES ANNTIMS
timezone as an analysis clock.  They contain the narrower release/open/close
windows requested by the historical pilot plan and can be trimmed only after
clock certification.  This compiler makes no API call.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd


ROOT = Path(__file__).resolve().parent
EVENTS = Path(os.environ.get("P1_DATABENTO_EVENTS", ROOT / "supported_earnings_inputs/selected_event_metadata.csv"))
CALENDAR = Path(os.environ.get("P1_DATABENTO_CALENDAR", ROOT / "event_calendar_actions/event_calendar_and_action_flags.csv"))
OUT = Path(os.environ.get("P1_DATABENTO_OUTPUT", ROOT / "databento_acquisition"))
EXPECTED_EVENTS_SHA256 = os.environ.get(
    "P1_DATABENTO_EVENTS_SHA256",
    "d2f113fe770ed9efb959652f0b4aef99442138056d3a08311771e1cc408bab52",
)
EXPECTED_CALENDAR_SHA256 = os.environ.get(
    "P1_DATABENTO_CALENDAR_SHA256",
    "ce2c0b0e53953dac411c9a463abb292affd69a11d638b752dc1cc761424f364d",
)
EXPECTED_EVENTS = int(os.environ.get("P1_DATABENTO_EVENT_ROWS", "480"))
NY = ZoneInfo("America/New_York")
UTC = timezone.utc


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def utc(local_date: str, clock: str) -> str:
    value = datetime.fromisoformat(f"{local_date}T{clock}:00").replace(tzinfo=NY)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"refuse empty output: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    if sha256(EVENTS) != EXPECTED_EVENTS_SHA256:
        raise ValueError("event input hash mismatch")
    if sha256(CALENDAR) != EXPECTED_CALENDAR_SHA256:
        raise ValueError("calendar input hash mismatch")
    if OUT.exists():
        raise FileExistsError(f"preserve output: {OUT}")
    OUT.mkdir()

    events = pd.read_csv(EVENTS)
    calendar = pd.read_csv(CALENDAR)
    merged = events.merge(
        calendar[
            [
                "association_id", "announcement_date_is_observed_session", "previous_session",
                "reaction_session", "next_session", "second_next_session", "calendar_basis",
            ]
        ],
        on="association_id",
        validate="one_to_one",
    )
    if len(merged) != EXPECTED_EVENTS or not merged.symbol_status.eq("DATE_VALID_UNIQUE").all():
        raise ValueError(f"{EXPECTED_EVENTS}-event/symbol invariant failed")

    legs = [
        ("PREVIOUS_CLOSE_NEIGHBORHOOD", "previous_session", "15:40", "16:10"),
        ("ANNOUNCEMENT_DATE_EXTENDED", "reaction_session", "04:00", "20:00"),
        ("NEXT_SESSION_EXTENDED", "next_session", "04:00", "20:00"),
        ("SECOND_NEXT_CLOSE_NEIGHBORHOOD", "second_next_session", "15:40", "16:10"),
    ]
    physical: dict[tuple, dict] = {}
    membership: defaultdict[tuple, list[dict]] = defaultdict(list)
    for row in merged.itertuples(index=False):
        analysis_access = "ARCHIVE_ONLY_NO_RESPONSE_ANALYSIS" if row.sample_period == "POST" else "DEVELOPMENT_PRE_ONLY"
        for role, symbol in [("STOCK", row.date_valid_raw_symbol), ("BENCHMARK", "SPY")]:
            for leg, date_field, start_clock, end_clock in legs:
                local_date = str(getattr(row, date_field))
                key = ("XNAS.ITCH", "bbo-1s", symbol, local_date, start_clock, end_clock)
                if key not in physical:
                    physical[key] = {
                        "dataset": key[0],
                        "schema": key[1],
                        "symbols": key[2],
                        "stype_in": "raw_symbol",
                        "start": utc(local_date, start_clock),
                        "end": utc(local_date, end_clock),
                        "local_date": local_date,
                        "local_start": start_clock,
                        "local_end": end_clock,
                        "timezone": "America/New_York",
                        "analysis_access": analysis_access,
                        "clock_basis": "DATE_WIDE_ACQUISITION_ANNTIMS_TIMEZONE_UNVERIFIED",
                    }
                elif analysis_access.startswith("ARCHIVE"):
                    physical[key]["analysis_access"] = "ARCHIVE_ONLY_NO_RESPONSE_ANALYSIS"
                membership[key].append({
                    "association_id": row.association_id,
                    "wave_id": row.wave_id,
                    "permno": int(row.permno),
                    "sample_period": row.sample_period,
                    "symbol_role": role,
                    "leg": leg,
                })

    requests = []
    request_id_by_key = {}
    for number, key in enumerate(sorted(physical, key=lambda x: (x[3], x[2], x[4], x[5])), 1):
        request_id = f"ACQ_XNAS_{number:05d}"
        request_id_by_key[key] = request_id
        event_ids = sorted({m["association_id"] for m in membership[key]})
        requests.append({
            "request_id": request_id,
            **physical[key],
            "association_ids": ";".join(event_ids),
            "association_count": len(event_ids),
            "bundle": "CORE_XNAS_BBO1S_DATE_WIDE",
        })

    mapping = []
    for key in sorted(membership, key=lambda x: (x[3], x[2], x[4], x[5])):
        for member in membership[key]:
            mapping.append({"request_id": request_id_by_key[key], **member})
    if len(mapping) != EXPECTED_EVENTS * 2 * 4:
        raise ValueError(f"event-request map should have {EXPECTED_EVENTS * 8:,} rows")

    # Identical slices for alternative single venues.  These are quoted as
    # separate alternatives and are never silently summed into a national NBBO.
    alternatives = []
    alt_number = 0
    for dataset in ["ARCX.PILLAR", "BATS.PITCH", "XNYS.PILLAR"]:
        for row in requests:
            alt_number += 1
            alternatives.append({
                **row,
                "request_id": f"ACQ_ALT_{alt_number:05d}",
                "dataset": dataset,
                "bundle": f"ALTERNATIVE_{dataset}_BBO1S_DATE_WIDE",
                "market_scope": "SINGLE_VENUE_NOT_NBBO",
                "execution_status": "QUOTE_AND_COVERAGE_CHECK_BEFORE_SELECTION",
            })

    # Ten real events are named for later update-level validation, but clocks
    # are not converted or purchased until the timezone/provenance is certified.
    validation_events = []
    for wave, group in merged.groupby("wave_id"):
        for side in ["PRE", "POST"]:
            row = group[group.sample_period.eq(side)].sort_values(
                ["tier", "liquidity_stratum", "permno", "announcement_date", "association_id"]
            ).iloc[0]
            validation_events.append({
                "association_id": row.association_id,
                "wave_id": wave,
                "sample_period": side,
                "date_valid_raw_symbol": row.date_valid_raw_symbol,
                "announcement_date": row.announcement_date,
                "announcement_times_all": row.announcement_times_all,
                "requested_schema": "mbp-1",
                "status": "NAMED_PREPARE_ONLY_CLOCK_TIMEZONE_NOT_CERTIFIED",
            })

    write_csv(OUT / "core_xnas_bbo1s_requests.csv", requests)
    write_csv(OUT / "event_request_map.csv", mapping)
    write_csv(OUT / "alternative_single_venue_requests.csv", alternatives)
    write_csv(OUT / "update_validation_events_prepare_only.csv", validation_events)
    user_balance = {
        "reported_remaining_credits_usd": "123.00",
        "source": "owner message 2026-09-14",
        "cash_spending_authorized_usd": "0.00",
        "credit_spending_hard_cap_usd": "123.00",
        "credential_present_in_process": False,
    }
    (OUT / "OWNER_BUDGET.json").write_text(json.dumps(user_balance, indent=2) + "\n")
    hours = sum(
        (datetime.fromisoformat(r["end"].replace("Z", "+00:00")) - datetime.fromisoformat(r["start"].replace("Z", "+00:00"))).total_seconds() / 3600
        for r in requests
    )
    receipt = {
        "status": "ACQUISITION_MANIFEST_COMPILED_NOT_QUOTED",
        "purpose": "DATA_ACQUISITION_ONLY_NOT_FINAL_ANALYSIS_ROSTER",
        "events": len(merged),
        "stock_wave_units": merged[["wave_id", "permno"]].drop_duplicates().shape[0],
        "core_physical_requests_after_deduplication": len(requests),
        "event_request_mapping_rows": len(mapping),
        "core_symbol_hours": hours,
        "alternative_physical_requests": len(alternatives),
        "named_update_validation_events": len(validation_events),
        "earliest_local_date": min(r["local_date"] for r in requests),
        "latest_local_date": max(r["local_date"] for r in requests),
        "event_input_sha256": sha256(EVENTS),
        "calendar_input_sha256": sha256(CALENDAR),
        "output_hashes": {
            name: sha256(OUT / name)
            for name in [
                "core_xnas_bbo1s_requests.csv", "event_request_map.csv",
                "alternative_single_venue_requests.csv", "update_validation_events_prepare_only.csv",
                "OWNER_BUDGET.json",
            ]
        },
        "anndats_timezone_assumed": False,
        "databento_api_calls": 0,
        "market_data_downloads": 0,
    }
    (OUT / "manifest_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
