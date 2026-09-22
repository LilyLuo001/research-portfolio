#!/usr/bin/env python3
"""Quote then download the 72 frozen external-test requests on SCC only.

Credentials are only read from ``DATABENTO_API_KEY`` in the environment.  The
script never accepts, prints, serializes, or hashes a key.  Quote mode does
not purchase data; download mode refuses a changed manifest and records every
completed native DBN path under the SCC output root.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import databento as db


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def put(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def client() -> db.Historical:
    key = os.getenv("DATABENTO_API_KEY")
    if not key:
        raise RuntimeError("DATABENTO_API_KEY absent from authenticated SCC environment")
    return db.Historical(key)


def load(manifest: Path) -> list[dict]:
    value = json.loads(manifest.read_text())
    rows = value["requests"]
    equity = [r for r in rows if r["dataset"] in {"XNAS.ITCH", "ARCX.PILLAR"}]
    futures = [r for r in rows if r["dataset"] == "GLBX.MDP3"]
    if len(rows) != 72 or len(equity) != 48 or len(futures) != 24:
        raise RuntimeError("requires the exact 72-request external manifest")
    return rows


def resolved_es(client: db.Historical, row: dict) -> tuple[str, str]:
    day = date.fromisoformat(row["date"])
    first = client.symbology.resolve(dataset="GLBX.MDP3", symbols=["ES.v.0"],
        stype_in="continuous", stype_out="instrument_id", start_date=str(day), end_date=str(day + timedelta(days=1)))
    value = first.get("result", {}).get("ES.v.0", [])
    flat = json.dumps(value)
    found = re.findall(r'"s"\s*:\s*"?(\d+)"?', flat)
    if not found:
        raise RuntimeError(f"{row['date']}: ES.v.0 did not resolve to an instrument id")
    iid = found[0]
    second = client.symbology.resolve(dataset="GLBX.MDP3", symbols=[iid], stype_in="instrument_id",
        stype_out="raw_symbol", start_date=str(day), end_date=str(day + timedelta(days=1)))
    raw = re.findall(r'ES[HMUZ][0-9]{1,2}', json.dumps(second).upper())
    if not raw:
        raise RuntimeError(f"{row['date']}: instrument id did not resolve to an ES raw symbol")
    return iid, raw[0]


def resolve_equity(client: db.Historical, row: dict) -> tuple[list[str], list[str]]:
    requested = row["symbols"].split(";")
    start = date.fromisoformat(row["date"])
    response = client.symbology.resolve(dataset=row["dataset"], symbols=requested, stype_in="raw_symbol",
        stype_out="instrument_id", start_date=str(start), end_date=str(start + timedelta(days=1)))
    result = response.get("result", {})
    resolved = [symbol for symbol in requested if result.get(symbol)]
    unresolved = [symbol for symbol in requested if symbol not in resolved]
    if "SPY" not in resolved:
        raise RuntimeError(f"{row['request_id']}: SPY unresolved")
    return resolved, unresolved


def quote(manifest: Path, out: Path) -> None:
    c = client(); quoted = []
    for row in load(manifest):
        item = dict(row)
        if row["dataset"] == "GLBX.MDP3":
            iid, raw = resolved_es(c, row); symbols = ["ES.v.0"]
            item.update(instrument_id=iid, actual_raw_symbol=raw, unresolved_symbols=[])
        else:
            symbols, missing = resolve_equity(c, row); item.update(unresolved_symbols=missing)
        spec = {"dataset": row["dataset"], "schema": "mbp-1", "symbols": symbols,
                "stype_in": row["stype_in"], "start": row["start_utc"], "end": row["end_utc"]}
        item.update(resolved_symbols=symbols, quoted_cost_usd=str(Decimal(str(c.metadata.get_cost(**spec)))),
                    estimated_record_count=int(c.metadata.get_record_count(**spec)))
        quoted.append(item)
    total = sum((Decimal(item["quoted_cost_usd"]) for item in quoted), Decimal("0"))
    put(out, {"status": "QUOTED_NO_DOWNLOAD", "manifest_sha256": digest(manifest),
              "sdk_version": getattr(db, "__version__", "NOT_OBSERVED"), "request_count": len(quoted),
              "total_quoted_cost_usd": str(total), "requests": quoted})


def download(manifest: Path, quote_path: Path, raw_root: Path) -> None:
    quote = json.loads(quote_path.read_text())
    if quote.get("status") != "QUOTED_NO_DOWNLOAD" or quote.get("manifest_sha256") != digest(manifest):
        raise RuntimeError("matching completed quote receipt required")
    c = client(); completed = []
    for row in quote["requests"]:
        target = raw_root / (row["request_id"] + ".dbn.zst")
        # A previous partial 2024 run may already have native input.  Reuse a
        # nonempty exact request file after hashing it; never overwrite it or
        # reissue a paid request.  Empty files are not valid reusable input.
        if target.exists() and target.stat().st_size > 0:
            item = dict(row); item.update(path=str(target), status="REUSED_EXISTING_NATIVE_DBN_ON_SCC",
                bytes=target.stat().st_size, sha256=digest(target))
            completed.append(item)
            continue
        if target.exists():
            raise RuntimeError(f"refusing to overwrite incomplete target: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        item = dict(row); item.update(path=str(target), status="SUBMISSION_STARTED_NO_RETRY")
        completed.append(item)
        put(raw_root / "DOWNLOAD_RECEIPT.json", {"status": "IN_PROGRESS", "selected_variant": {"requests": quote["requests"]}, "files": completed})
        c.timeseries.get_range(dataset=row["dataset"], schema="mbp-1", symbols=row["resolved_symbols"],
            stype_in=row["stype_in"], stype_out="instrument_id", start=row["start_utc"], end=row["end_utc"], path=target)
        item.update(status="DOWNLOADED_NATIVE_DBN_ON_SCC", bytes=target.stat().st_size, sha256=digest(target))
    put(raw_root / "DOWNLOAD_RECEIPT.json", {"status": "COMPLETE_NATIVE_DBN_ON_SCC", "manifest_sha256": digest(manifest),
        "quote_sha256": digest(quote_path), "selected_variant": {"requests": quote["requests"]}, "files": completed})


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("mode", choices=("quote", "download"))
    ap.add_argument("--manifest", required=True, type=Path); ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--quote-receipt", type=Path); ap.add_argument("--raw-root", type=Path)
    args = ap.parse_args()
    if args.mode == "quote": quote(args.manifest, args.out)
    else:
        if args.quote_receipt is None or args.raw_root is None: raise RuntimeError("download needs --quote-receipt and --raw-root")
        download(args.manifest, args.quote_receipt, args.raw_root)


if __name__ == "__main__":
    main()
