"""Build the exact quote request matrix and reconcile it to the SCC manifest.

This reads metadata only. It does not open DBN files or call Databento APIs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


DATASETS = ("XNAS.ITCH", "BATS.PITCH", "ARCX.PILLAR", "XNYS.PILLAR")
FIRST_DOWNLOAD_DATASETS = ("XNAS.ITCH", "BATS.PITCH")
SECOND_DOWNLOAD_DATASETS = ("ARCX.PILLAR", "XNYS.PILLAR")
THIRD_DOWNLOAD_DATASETS = ("EQUS.MINI",)
SCHEMA = "bbo-1s"
SOURCE_SYMBOLS = {"Exxon Mobil Corp.": ["XOM"]}
PRESENT_PREFIXES = ("DOWNLOADED_", "RECOVERED_")


def parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clock", required=True, type=Path)
    parser.add_argument("--event-symbols", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    with args.clock.open(newline="") as handle:
        events = [row for row in csv.DictReader(handle) if row["supports_5m"] in {"YES", "CONDITIONAL"}]
    assert events and all(row["earliest_bound_et"] and row["latest_bound_et"] for row in events)
    with args.event_symbols.open(newline="") as handle:
        event_symbols = list(csv.DictReader(handle))
    event_receiver_map = {}
    for row in event_symbols:
        event_receiver_map.setdefault(row["event_id"], []).append(row["symbol"])
    assert all(len(symbols) == 20 and len(set(symbols)) == 20 for symbols in event_receiver_map.values())
    with args.manifest.open(newline="") as handle:
        manifest = list(csv.DictReader(handle))

    request_rows = []
    for event in events:
        lower, upper = parse(event["earliest_bound_et"]), parse(event["latest_bound_et"])
        start, end = lower - timedelta(minutes=15), upper + timedelta(minutes=75)
        symbols = sorted(
            set(event_receiver_map[event["event_id"]])
            | {"QQQ", "SPY"}
            | set(SOURCE_SYMBOLS.get(event["issuer"], []))
        )
        assert SOURCE_SYMBOLS.get(event["issuer"]), event["issuer"]
        for dataset in DATASETS:
            for symbol in symbols:
                key = "|".join((event["event_id"], dataset, symbol, utc(start), utc(end)))
                request_rows.append({
                    "request_id": hashlib.sha256(key.encode()).hexdigest()[:20],
                    "event_id": event["event_id"],
                    "issuer": event["issuer"],
                    "dataset": dataset,
                    "schema": SCHEMA,
                    "symbol": symbol,
                    "start_utc": utc(start),
                    "end_utc": utc(end),
                    "clock_lower_et": event["earliest_bound_et"],
                    "clock_upper_et": event["latest_bound_et"],
                    "minimum_supported_horizon": "5m",
                })

    gap_rows = []
    for request in request_rows:
        start, end = parse(request["start_utc"]), parse(request["end_utc"])
        exact = []
        overlap = []
        for row in manifest:
            if row["dataset"] != request["dataset"] or row["schema"] != request["schema"]:
                continue
            if request["symbol"] not in set(filter(None, row["symbols"].split(";"))):
                continue
            row_start, row_end = parse(row["start"]), parse(row["end"])
            if row_start < end and row_end > start:
                overlap.append(row)
            if row_start <= start and row_end >= end and row["completion_status"].startswith(PRESENT_PREFIXES):
                exact.append(row)
        usable = [row for row in exact if Path(row["path"]).is_file()]
        if usable:
            status = "EXISTING_FILE_COVERS_INTERVAL"
        elif exact:
            status = "MANIFEST_COVERAGE_FILE_NOT_FOUND"
        elif overlap:
            status = "PARTIAL_INTERVAL_OVERLAP"
        else:
            status = "MISSING_REQUEST"
        access = sorted({row["analysis_access"] for row in usable})
        gap_rows.append({
            **request,
            "coverage_status": status,
            "covering_manifest_rows": len(usable),
            "overlapping_manifest_rows": len(overlap),
            "existing_analysis_access": ";".join(access),
        })

    request_fields = list(request_rows[0])
    gap_fields = list(gap_rows[0])
    write_csv(args.out / "REQUEST_MATRIX.csv", request_rows, request_fields)
    write_csv(args.out / "COVERAGE_GAP.csv", gap_rows, gap_fields)

    # The first purchase is deliberately a two-venue technical pilot, not the
    # four-venue research panel. Bundle symbols by event and venue so cost and
    # record-count calls use the exact request that would later be downloaded.
    # Existing files marked archive-only do not reduce this proposal.
    def build_proposal(datasets: tuple[str, ...], purpose: str) -> list[dict]:
        proposal = []
        for event in events:
            event_rows = [
                row for row in request_rows
                if row["event_id"] == event["event_id"]
            ]
            for dataset in datasets:
                rows = [row for row in event_rows if row["dataset"] == dataset]
                if not rows:
                    # A discovered composite dataset reuses the exact frozen
                    # clock/symbol window; it does not enter the four-venue matrix.
                    rows = [row for row in event_rows if row["dataset"] == "XNAS.ITCH"]
                symbols = sorted({row["symbol"] for row in rows})
                assert len(symbols) == 23
                key = "|".join((event["event_id"], dataset, rows[0]["start_utc"], rows[0]["end_utc"], *symbols))
                proposal.append({
                    "bundle_id": hashlib.sha256(key.encode()).hexdigest()[:20],
                    "event_id": event["event_id"],
                    "issuer": event["issuer"],
                    "dataset": dataset,
                    "schema": SCHEMA,
                    "symbols_semicolon": ";".join(symbols),
                    "symbol_count": len(symbols),
                    "start_utc": rows[0]["start_utc"],
                    "end_utc": rows[0]["end_utc"],
                    "stype_in": "raw_symbol",
                    "purpose": purpose,
                    "scientific_status": "NOT_A_POWER_OR_IDENTIFICATION_TEST",
                })
        return proposal

    proposal_rows = build_proposal(
        FIRST_DOWNLOAD_DATASETS, "TWO_EVENT_TWO_VENUE_TECHNICAL_MEASUREMENT_ONLY"
    )
    second_proposal_rows = build_proposal(
        SECOND_DOWNLOAD_DATASETS, "TWO_EVENT_ALTERNATIVE_VENUE_COVERAGE_DIAGNOSTIC"
    )
    third_proposal_rows = build_proposal(
        THIRD_DOWNLOAD_DATASETS, "TWO_EVENT_DERIVED_COMPOSITE_COVERAGE_DIAGNOSTIC"
    )
    write_csv(args.out / "FIRST_DOWNLOAD_PROPOSAL.csv", proposal_rows, list(proposal_rows[0]))
    write_csv(args.out / "SECOND_DOWNLOAD_PROPOSAL.csv", second_proposal_rows, list(second_proposal_rows[0]))
    write_csv(args.out / "THIRD_DOWNLOAD_PROPOSAL.csv", third_proposal_rows, list(third_proposal_rows[0]))
    third_late_rows = [row for row in third_proposal_rows if row["start_utc"] >= "2023-03-28T00:00:00Z"]
    write_csv(args.out / "THIRD_LATE_ONLY_PROPOSAL.csv", third_late_rows, list(third_late_rows[0]))
    status_counts = {}
    for row in gap_rows:
        status_counts[row["coverage_status"]] = status_counts.get(row["coverage_status"], 0) + 1
    summary = {
        "status": "METADATA_ONLY_NO_DBN_OPENED_NO_API_CALL",
        "eligible_events": len(events),
        "event_ids": [row["event_id"] for row in events],
        "receiver_symbols_per_event": 20,
        "symbols_per_event": len(request_rows) // len(events) // len(DATASETS),
        "datasets": list(DATASETS),
        "physical_requests": len(request_rows),
        "coverage_counts": status_counts,
        "missing_requests": sum(row["coverage_status"] != "EXISTING_FILE_COVERS_INTERVAL" for row in gap_rows),
        "first_download_proposal": {
            "bundled_requests": len(proposal_rows),
            "datasets": list(FIRST_DOWNLOAD_DATASETS),
            "symbols_per_bundle": 23,
            "scope": "two clock-qualified events; technical measurement only",
            "does_not_establish": "power, identification, or research GO",
        },
        "inputs": {
            "clock_sha256": hash_file(args.clock),
            "event_symbols_sha256": hash_file(args.event_symbols),
            "manifest_sha256": hash_file(args.manifest),
        },
        "boundaries": "No DBN read; no price/quote values; no Databento API call or purchase",
    }
    (args.out / "QUOTE_GAP_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
