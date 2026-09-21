#!/usr/bin/env python3
"""Quote and download the eight exact missing six-event BBO windows on SCC.

The API key is read only from DATABENTO_API_KEY and is never serialized,
printed, or hashed. Each request is submitted at most once in a run. Native
DBN files stay on SCC; the repository receives only the request manifest and
the key-free receipt.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from decimal import Decimal
from pathlib import Path

import databento as db


def write_receipt(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--max-usd", type=Decimal, default=Decimal("10.00"))
    args = parser.parse_args()

    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise RuntimeError("DATABENTO_API_KEY absent")
    with args.requests.open(newline="") as handle:
        requests = list(csv.DictReader(handle))
    if len(requests) != 8 or len({r["request_id"] for r in requests}) != 8:
        raise RuntimeError("expected eight unique exact requests")
    if {r["dataset"] for r in requests} != {"XNAS.ITCH", "ARCX.PILLAR"}:
        raise RuntimeError("unexpected dataset scope")
    if {r["schema"] for r in requests} != {"bbo-1s"}:
        raise RuntimeError("unexpected schema")

    client = db.Historical(key)
    quoted = []
    for row in requests:
        symbols = row["symbols"].split(";")
        common = dict(
            dataset=row["dataset"], schema=row["schema"], symbols=symbols,
            stype_in="raw_symbol", start=row["start_utc"], end=row["end_utc"],
        )
        cost = Decimal(str(client.metadata.get_cost(**common)))
        records = int(client.metadata.get_record_count(**common))
        quoted.append({
            "request_id": row["request_id"], "event_id": row["event_id"],
            "stock": row["stock"], "dataset": row["dataset"],
            "start_utc": row["start_utc"], "end_utc": row["end_utc"],
            "symbols": symbols, "quoted_cost_usd": str(cost),
            "estimated_record_count": records, "status": "QUOTED",
        })
    total = sum((Decimal(r["quoted_cost_usd"]) for r in quoted), Decimal("0"))
    receipt = {
        "status": "QUOTED", "sdk_version": getattr(db, "__version__", "NOT_OBSERVED"),
        "api_methods": ["metadata.get_cost", "metadata.get_record_count"],
        "hard_cap_usd": str(args.max_usd), "quoted_total_usd": str(total),
        "requests": quoted,
    }
    write_receipt(args.receipt, receipt)
    if total > args.max_usd:
        receipt["status"] = "STOPPED_QUOTE_EXCEEDS_HARD_CAP"
        write_receipt(args.receipt, receipt)
        raise RuntimeError("quoted cost exceeds hard cap")
    if any(r["estimated_record_count"] <= 0 for r in quoted):
        receipt["status"] = "STOPPED_ZERO_ESTIMATED_RECORDS"
        write_receipt(args.receipt, receipt)
        raise RuntimeError("one or more requests has zero estimated records")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    by_id = {r["request_id"]: r for r in quoted}
    receipt["api_methods"].append("timeseries.get_range")
    receipt["status"] = "DOWNLOAD_IN_PROGRESS"
    for row in requests:
        item = by_id[row["request_id"]]
        target = args.out_dir / f"{row['request_id']}.dbn.zst"
        item["scc_path"] = str(target)
        if target.exists():
            item["status"] = "EXISTING_FILE_REFUSED_NO_OVERWRITE"
            receipt["status"] = "STOPPED_EXISTING_FILE"
            write_receipt(args.receipt, receipt)
            raise RuntimeError(f"refusing to overwrite {target}")
        item["status"] = "SUBMISSION_STARTED_NO_BLIND_RETRY"
        write_receipt(args.receipt, receipt)
        try:
            client.timeseries.get_range(
                dataset=row["dataset"], schema=row["schema"],
                symbols=row["symbols"].split(";"), stype_in="raw_symbol",
                stype_out="instrument_id", start=row["start_utc"],
                end=row["end_utc"], path=target,
            )
            item["bytes"] = target.stat().st_size
            item["status"] = "DOWNLOADED_NATIVE_DBN_ON_SCC"
        except Exception as exc:
            item["status"] = "UNCERTAIN_STOPPED_NO_RETRY"
            item["error_type"] = type(exc).__name__
            receipt["status"] = "STOPPED_ON_DOWNLOAD_ERROR"
            write_receipt(args.receipt, receipt)
            raise
    receipt["status"] = "COMPLETE_NATIVE_DBN_ON_SCC"
    write_receipt(args.receipt, receipt)
    print(json.dumps({
        "status": receipt["status"], "requests": len(requests),
        "quoted_total_usd": str(total),
        "estimated_records": sum(r["estimated_record_count"] for r in quoted),
    }))


if __name__ == "__main__":
    main()
