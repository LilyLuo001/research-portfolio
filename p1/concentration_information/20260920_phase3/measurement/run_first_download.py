#!/usr/bin/env python3
"""Quote or execute the frozen two-event/two-venue technical pilot.

The API key is read only from DATABENTO_API_KEY.  Quote mode uses metadata and
symbology methods only.  Download mode is guarded by an exact quote receipt,
an owner flag, and a dollar ceiling.  Native DBN stays in the specified SCC
output directory; this script never decodes quote values.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def sdk_client():
    try:
        import databento as db
    except ImportError as exc:
        raise RuntimeError("official Databento SDK is unavailable") from exc
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise RuntimeError("DATABENTO_API_KEY is absent")
    return db.Historical(key), getattr(db, "__version__", "NOT_OBSERVED")


def load_proposal(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) in (1, 2, 4)
    datasets = {row["dataset"] for row in rows}
    assert len(datasets) in (1, 2)
    assert datasets <= {"XNAS.ITCH", "BATS.PITCH", "ARCX.PILLAR", "XNYS.PILLAR", "EQUS.MINI"}
    assert {row["schema"] for row in rows} == {"bbo-1s"}
    assert all(int(row["symbol_count"]) == 23 for row in rows)
    return rows


def resolution_dates(row: dict[str, str]) -> tuple[str, str]:
    start = datetime.fromisoformat(row["start_utc"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(row["end_utc"].replace("Z", "+00:00"))
    return start.date().isoformat(), max(end.date(), start.date() + timedelta(days=1)).isoformat()


def quote(proposal: Path, out: Path) -> None:
    rows = load_proposal(proposal)
    client, sdk_version = sdk_client()
    entries = []
    for row in rows:
        symbols = row["symbols_semicolon"].split(";")
        start_date, end_date = resolution_dates(row)
        resolved = client.symbology.resolve(
            dataset=row["dataset"], symbols=symbols,
            stype_in=row["stype_in"], stype_out="instrument_id",
            start_date=start_date, end_date=end_date,
        )
        result = resolved.get("result", {}) if isinstance(resolved, dict) else {}
        unresolved = sorted(symbol for symbol in symbols if not result.get(symbol))
        cost = Decimal(str(client.metadata.get_cost(
            dataset=row["dataset"], schema=row["schema"], symbols=symbols,
            stype_in=row["stype_in"], start=row["start_utc"], end=row["end_utc"],
        )))
        records = int(client.metadata.get_record_count(
            dataset=row["dataset"], schema=row["schema"], symbols=symbols,
            stype_in=row["stype_in"], start=row["start_utc"], end=row["end_utc"],
        ))
        entries.append({
            "bundle_id": row["bundle_id"], "dataset": row["dataset"],
            "event_id": row["event_id"], "symbol_count": len(symbols),
            "unresolved_symbols": unresolved, "quoted_cost_usd": str(cost),
            "estimated_record_count": records,
        })
    if any(entry["unresolved_symbols"] for entry in entries):
        status = "BLOCKED_UNRESOLVED_SYMBOLS"
    else:
        status = "QUOTED_NO_DOWNLOAD"
    receipt = {
        "status": status,
        "proposal_sha256": digest(proposal),
        "sdk_version": sdk_version,
        "api_scope": ["symbology.resolve", "metadata.get_cost", "metadata.get_record_count"],
        "requests": entries,
        "total_quoted_cost_usd": str(sum((Decimal(e["quoted_cost_usd"]) for e in entries), Decimal("0"))),
        "total_estimated_records": sum(e["estimated_record_count"] for e in entries),
        "download_calls": 0,
    }
    write_json(out, receipt)
    print(json.dumps({k: receipt[k] for k in ("status", "total_quoted_cost_usd", "total_estimated_records")}))


def download(proposal: Path, quote_path: Path, out_dir: Path, max_usd: Decimal, owner_approved: bool) -> None:
    if not owner_approved:
        raise RuntimeError("download requires --owner-approved-download")
    rows = load_proposal(proposal)
    receipt = json.loads(quote_path.read_text())
    if receipt.get("status") != "QUOTED_NO_DOWNLOAD" or receipt.get("proposal_sha256") != digest(proposal):
        raise RuntimeError("exact successful quote receipt does not match proposal")
    total = Decimal(receipt["total_quoted_cost_usd"])
    if total > max_usd:
        raise RuntimeError(f"quoted total {total} exceeds guard {max_usd}")
    quotes = {row["bundle_id"]: row for row in receipt["requests"]}
    if set(quotes) != {row["bundle_id"] for row in rows}:
        raise RuntimeError("quote request set differs from proposal")
    client, sdk_version = sdk_client()
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for row in rows:
        path = out_dir / f"{row['bundle_id']}.dbn.zst"
        if path.exists():
            raise RuntimeError(f"refusing to overwrite existing file: {path}")
        symbols = row["symbols_semicolon"].split(";")
        record = {
            "bundle_id": row["bundle_id"], "dataset": row["dataset"],
            "event_id": row["event_id"], "path": str(path),
            "quoted_cost_usd": quotes[row["bundle_id"]]["quoted_cost_usd"],
            "status": "SUBMISSION_STARTED_NO_RETRY",
        }
        manifest.append(record)
        write_json(out_dir / "DOWNLOAD_RECEIPT.json", {
            "status": "IN_PROGRESS", "sdk_version": sdk_version,
            "proposal_sha256": digest(proposal), "quote_sha256": digest(quote_path),
            "quoted_total_usd": str(total), "files": manifest,
        })
        client.timeseries.get_range(
            dataset=row["dataset"], schema=row["schema"], symbols=symbols,
            stype_in=row["stype_in"], stype_out="instrument_id",
            start=row["start_utc"], end=row["end_utc"], path=path,
        )
        record.update(status="DOWNLOADED_NATIVE_DBN_UNOPENED", bytes=path.stat().st_size, sha256=digest(path))
    write_json(out_dir / "DOWNLOAD_RECEIPT.json", {
        "status": "COMPLETE_NATIVE_DBN_UNOPENED", "sdk_version": sdk_version,
        "proposal_sha256": digest(proposal), "quote_sha256": digest(quote_path),
        "quoted_total_usd": str(total), "actual_billing": "RECONCILE_WITH_VENDOR",
        "files": manifest,
    })
    print(json.dumps({"status": "COMPLETE_NATIVE_DBN_UNOPENED", "files": len(manifest), "quoted_total_usd": str(total)}))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("quote", "download"))
    parser.add_argument("--proposal", required=True, type=Path)
    parser.add_argument("--quote-receipt", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--max-usd", type=Decimal, default=Decimal("10"))
    parser.add_argument("--owner-approved-download", action="store_true")
    args = parser.parse_args()
    if args.mode == "quote":
        quote(args.proposal, args.out)
    else:
        if not args.quote_receipt:
            raise RuntimeError("--quote-receipt is required")
        download(args.proposal, args.quote_receipt, args.out, args.max_usd, args.owner_approved_download)


if __name__ == "__main__":
    main()
