#!/usr/bin/env python3
"""Quote and acquire only the fixed earnings request manifest on SCC.

The API credential is read from the process environment and is never printed,
serialized, hashed, or written.  Existing nonempty targets are reused; an
empty or partial target stops rather than being overwritten and potentially
charged twice.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from decimal import Decimal
from pathlib import Path

import databento as db


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for part in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def put(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def client() -> db.Historical:
    key = os.getenv("DATABENTO_API_KEY")
    if not key:
        raise RuntimeError("DATABENTO_API_KEY absent from authenticated SCC shell")
    return db.Historical(key)


def load(path: Path) -> list[dict]:
    payload = json.loads(path.read_text())
    rows = payload.get("requests_detail", [])
    counts = {dataset: sum(r["dataset"] == dataset for r in rows) for dataset in ("XNAS.ITCH", "ARCX.PILLAR", "GLBX.MDP3")}
    if payload.get("status") != "PREPARED_UNQUOTED" or len(rows) != 288 or counts != {"XNAS.ITCH": 96, "ARCX.PILLAR": 96, "GLBX.MDP3": 96}:
        raise RuntimeError(f"requires exact fixed 288-row earnings manifest; got {len(rows)} {counts}")
    return rows


def request_spec(row: dict) -> dict:
    return {
        "dataset": row["dataset"], "schema": "mbp-1",
        "symbols": row["symbols"].split(";") if row["dataset"] != "GLBX.MDP3" else ["ES.v.0"],
        "stype_in": row["stype_in"], "start": row["start_utc"], "end": row["end_utc"],
    }


def quote(manifest: Path, out: Path) -> None:
    api = client()
    quoted = []
    for number, row in enumerate(load(manifest), 1):
        spec = request_spec(row)
        item = dict(row)
        item["resolved_symbols"] = spec["symbols"]
        item["quoted_cost_usd"] = str(Decimal(str(api.metadata.get_cost(**spec))))
        item["estimated_record_count"] = int(api.metadata.get_record_count(**spec))
        quoted.append(item)
        if number % 24 == 0:
            put(out, {"status": "QUOTE_IN_PROGRESS", "manifest_sha256": digest(manifest), "quoted_requests": len(quoted), "requests": quoted})
    put(out, {
        "status": "QUOTED_NO_DOWNLOAD", "manifest_sha256": digest(manifest),
        "request_count": len(quoted),
        "total_quoted_cost_usd": str(sum((Decimal(r["quoted_cost_usd"]) for r in quoted), Decimal(0))),
        "requests": quoted,
    })


def download(manifest: Path, quote_path: Path, raw_root: Path) -> None:
    quoted = json.loads(quote_path.read_text())
    if quoted.get("status") != "QUOTED_NO_DOWNLOAD" or quoted.get("manifest_sha256") != digest(manifest) or len(quoted.get("requests", [])) != 288:
        raise RuntimeError("matching completed 288-row quote receipt required")
    api = client()
    raw_root.mkdir(parents=True, exist_ok=True)
    receipt_path = raw_root / "DOWNLOAD_RECEIPT.json"
    completed = []
    for row in quoted["requests"]:
        target = raw_root / f"{row['request_id']}.dbn.zst"
        item = dict(row)
        item["path"] = str(target)
        if target.exists() and target.stat().st_size > 0:
            item.update(status="REUSED_EXISTING_NATIVE_DBN_ON_SCC", bytes=target.stat().st_size, sha256=digest(target))
            completed.append(item)
            continue
        if target.exists():
            raise RuntimeError(f"refusing to overwrite empty/partial target: {target}")
        item["status"] = "SUBMISSION_STARTED_NO_BLIND_RETRY"
        completed.append(item)
        put(receipt_path, {"status": "IN_PROGRESS", "manifest_sha256": digest(manifest), "files": completed})
        spec = request_spec(row)
        api.timeseries.get_range(**spec, stype_out="instrument_id", path=target)
        item.update(status="DOWNLOADED_NATIVE_DBN_ON_SCC", bytes=target.stat().st_size, sha256=digest(target))
    put(receipt_path, {
        "status": "COMPLETE_NATIVE_DBN_ON_SCC", "manifest_sha256": digest(manifest),
        "quote_sha256": digest(quote_path), "quoted_total_usd": quoted["total_quoted_cost_usd"],
        "files": completed,
    })


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("quote", "download"))
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--quote-receipt", type=Path)
    ap.add_argument("--raw-root", type=Path)
    args = ap.parse_args()
    if args.mode == "quote":
        if args.out is None:
            raise RuntimeError("quote requires --out")
        quote(args.manifest, args.out)
    else:
        if args.quote_receipt is None or args.raw_root is None:
            raise RuntimeError("download requires --quote-receipt and --raw-root")
        download(args.manifest, args.quote_receipt, args.raw_root)


if __name__ == "__main__":
    main()
