#!/usr/bin/env python3
"""Quote, select, and download the bounded bidirectional MBP-1 pilot on SCC.

The credential is read only from ``DATABENTO_API_KEY``. It is never printed,
serialized, hashed, or accepted as a command-line argument. Quote mode makes
only symbology and metadata calls. Download mode requires the matching quote
receipt and writes native DBN files only to the caller-supplied SCC directory.
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
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def client() -> db.Historical:
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise RuntimeError("DATABENTO_API_KEY absent")
    return db.Historical(key)


def load_manifest(path: Path) -> tuple[list[str], list[dict]]:
    value = json.loads(path.read_text())
    rows = value["requests"]
    if len(rows) != 48 or {r["dataset"] for r in rows} != {"XNAS.ITCH", "ARCX.PILLAR"}:
        raise RuntimeError("expected exact 48-row/two-venue manifest")
    if {r["schema"] for r in rows} != {"mbp-1"}:
        raise RuntimeError("unexpected schema")
    return value["symbols"], rows


def variants(symbols: list[str], rows: list[dict]) -> list[tuple[str, list[str], list[dict]]]:
    # Preserve dates before venues, symbols, or clock window as predeclared.
    stocks = symbols[1:]
    first12 = []
    for tier_block in (stocks[0:8], stocks[8:16], stocks[16:24]):
        first12.extend(tier_block[:2] + tier_block[4:6])
    primary = [r for r in rows if r["dataset"] == "XNAS.ITCH"]
    shortened = []
    for row in primary:
        copy = dict(row)
        # The request begins one minute before 10:00 ET; 15-minute core plus
        # the one-minute tail ends at 10:16 ET, 15 minutes before full end.
        import pandas as pd
        copy["end_utc"] = (pd.Timestamp(copy["end_utc"]) - pd.Timedelta(minutes=15)).isoformat()
        shortened.append(copy)
    return [
        ("V1_24_STOCK_TWO_VENUE_30M", symbols, rows),
        ("V2_24_STOCK_XNAS_30M", symbols, primary),
        ("V3_12_STOCK_XNAS_30M", ["SPY", *first12], primary),
        ("V4_12_STOCK_XNAS_15M", ["SPY", *first12], shortened),
    ]


def resolve_symbols(cl: db.Historical, dataset: str, symbols: list[str], start: str, end: str) -> tuple[list[str], list[str]]:
    import pandas as pd
    start_date = pd.Timestamp(start).date()
    end_date = max(pd.Timestamp(end).date(), start_date + pd.Timedelta(days=1))
    response = cl.symbology.resolve(
        dataset=dataset, symbols=symbols, stype_in="raw_symbol",
        stype_out="instrument_id", start_date=str(start_date), end_date=str(end_date),
    )
    result = response.get("result", {}) if isinstance(response, dict) else {}
    resolved = [s for s in symbols if result.get(s)]
    return resolved, [s for s in symbols if s not in resolved]


def quote(manifest: Path, out: Path, max_usd: Decimal) -> None:
    symbols, base_rows = load_manifest(manifest)
    cl = client()
    all_variants = []
    chosen = None
    for variant_id, requested_symbols, rows in variants(symbols, base_rows):
        quoted, unresolved_union = [], set()
        for row in rows:
            resolved, unresolved = resolve_symbols(
                cl, row["dataset"], requested_symbols, row["start_utc"], row["end_utc"]
            )
            unresolved_union.update(unresolved)
            if "SPY" not in resolved:
                raise RuntimeError(f"SPY unresolved for {row['request_id']}")
            common = dict(
                dataset=row["dataset"], schema="mbp-1", symbols=resolved,
                stype_in="raw_symbol", start=row["start_utc"], end=row["end_utc"],
            )
            cost = Decimal(str(cl.metadata.get_cost(**common)))
            count = int(cl.metadata.get_record_count(**common))
            quoted.append({
                "request_id": row["request_id"], "dataset": row["dataset"],
                "start_utc": row["start_utc"], "end_utc": row["end_utc"],
                "symbols": resolved, "unresolved_symbols": unresolved,
                "quoted_cost_usd": str(cost), "estimated_record_count": count,
            })
        total = sum((Decimal(x["quoted_cost_usd"]) for x in quoted), Decimal("0"))
        record = {
            "variant_id": variant_id, "request_count": len(rows),
            "requested_symbol_count": len(requested_symbols),
            "unresolved_symbols": sorted(unresolved_union),
            "quoted_total_usd": str(total),
            "estimated_record_count": sum(x["estimated_record_count"] for x in quoted),
            "requests": quoted,
        }
        all_variants.append(record)
        if chosen is None and total <= max_usd and all(x["estimated_record_count"] > 0 for x in quoted):
            chosen = record
            break
    receipt = {
        "status": "QUOTED_SELECTED" if chosen else "STOPPED_NO_VARIANT_WITHIN_CAP",
        "manifest_sha256": digest(manifest), "sdk_version": getattr(db, "__version__", "NOT_OBSERVED"),
        "api_methods": ["symbology.resolve", "metadata.get_cost", "metadata.get_record_count"],
        "hard_cap_usd": str(max_usd), "selected_variant_id": chosen and chosen["variant_id"],
        "variants_quoted": all_variants, "download_calls": 0,
    }
    write_json(out, receipt)
    print(json.dumps({"status": receipt["status"], "selected_variant_id": receipt["selected_variant_id"]}))


def download(manifest: Path, quote_path: Path, out_dir: Path, max_usd: Decimal) -> None:
    receipt = json.loads(quote_path.read_text())
    if receipt.get("status") != "QUOTED_SELECTED" or receipt.get("manifest_sha256") != digest(manifest):
        raise RuntimeError("matching successful quote receipt required")
    selected = next(x for x in receipt["variants_quoted"] if x["variant_id"] == receipt["selected_variant_id"])
    total = Decimal(selected["quoted_total_usd"])
    if total > max_usd:
        raise RuntimeError("selected quote exceeds download cap")
    cl = client()
    out_dir.mkdir(parents=True, exist_ok=True)
    completed = []
    run_receipt = out_dir / "DOWNLOAD_RECEIPT.json"
    for row in selected["requests"]:
        target = out_dir / f"{row['request_id']}.dbn.zst"
        if target.exists():
            raise RuntimeError(f"refusing to overwrite existing file: {target}")
        state = {"request_id": row["request_id"], "path": str(target), "status": "SUBMISSION_STARTED_NO_RETRY"}
        completed.append(state)
        write_json(run_receipt, {"status": "IN_PROGRESS", "selected_variant": selected, "files": completed})
        cl.timeseries.get_range(
            dataset=row["dataset"], schema="mbp-1", symbols=row["symbols"],
            stype_in="raw_symbol", stype_out="instrument_id",
            start=row["start_utc"], end=row["end_utc"], path=target,
        )
        state.update(status="DOWNLOADED_NATIVE_DBN_ON_SCC", bytes=target.stat().st_size)
    write_json(run_receipt, {
        "status": "COMPLETE_NATIVE_DBN_ON_SCC", "manifest_sha256": digest(manifest),
        "quote_sha256": digest(quote_path), "selected_variant": selected, "files": completed,
    })
    print(json.dumps({"status": "COMPLETE_NATIVE_DBN_ON_SCC", "files": len(completed)}))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("quote", "download"))
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--quote-receipt", type=Path)
    ap.add_argument("--max-usd", type=Decimal, default=Decimal("100"))
    args = ap.parse_args()
    if args.mode == "quote":
        quote(args.manifest, args.out, args.max_usd)
    else:
        if args.quote_receipt is None:
            raise RuntimeError("--quote-receipt is required")
        download(args.manifest, args.quote_receipt, args.out, args.max_usd)


if __name__ == "__main__":
    main()
