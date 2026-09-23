#!/usr/bin/env python3
"""Quote and acquire the bounded Phase 2 market package directly onto SCC.

No credential is accepted on the command line or written to a receipt.  The
script reads ``DATABENTO_API_KEY`` from the process environment.  Raw DBN files
remain under the supplied SCC directory.  Quote receipts are checkpoints, not
a new approval gate.
"""
from __future__ import annotations

import argparse
import json
import os
from decimal import Decimal
from pathlib import Path

import databento as db
import pandas as pd


DATES = [
    "2023-01-17", "2023-01-18", "2023-01-19", "2023-01-20", "2023-01-23",
    "2023-01-24", "2023-01-25", "2023-01-26", "2023-01-27", "2023-01-30",
    "2023-01-31",
]
EVENT_DATE = "2023-01-24"
TICK_REFERENCE_DATES = {"2023-01-23", EVENT_DATE}
EQUITY_DATASETS = ("XNYS.PILLAR", "XNAS.ITCH", "ARCX.PILLAR")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temp.replace(path)


def get_client() -> db.Historical:
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise RuntimeError("DATABENTO_API_KEY is absent from this SCC process")
    return db.Historical(key)


def dataset_symbols(roster: pd.DataFrame, dataset: str) -> list[str]:
    base = roster["ticker"].astype(str).str.strip()
    share_class = roster["shrcls"].astype("string").str.strip()
    # CRSP's class field is populated for many issuers whose market ticker has
    # no suffix (e.g. V or META).  Only the two symbols found unresolved in the
    # first API pass require an explicit market-symbol separator.
    has_class = base.isin(["BF", "BRK"]) & share_class.notna() & share_class.ne("")
    separator = "." if dataset == "XNAS.ITCH" else " "
    base = base.where(~has_class, base + separator + share_class.fillna(""))
    return ["SPY", *base.tolist()]


def build_requests(roster_path: Path, class_supplement: bool = False) -> list[dict]:
    roster = pd.read_parquet(roster_path)
    if len(roster) != 503:
        raise RuntimeError(f"expected 503-row roster, got {len(roster)}")
    if class_supplement:
        # The initial CRSP tsymbol-based quote identified exactly these two
        # unresolved class symbols (BFB and BRKB) on every equity feed.
        roster = roster[roster["ticker"].isin(["BF", "BRK"])].copy()
        if set(roster["ticker"]) != {"BF", "BRK"}:
            raise RuntimeError("unexpected historical share-class supplement set")
    requests: list[dict] = []
    for date in DATES:
        start = f"{date}T14:25:00Z"
        end = f"{date}T16:30:00Z"
        for dataset in EQUITY_DATASETS:
            symbols = dataset_symbols(roster, dataset)
            if class_supplement:
                symbols = symbols[1:]
            for schema in ("bbo-1s", "trades"):
                requests.append(
                    {
                        "request_id": f"{date}_{dataset.replace('.', '_')}_{schema}",
                        "dataset": dataset,
                        "schema": schema,
                        "symbols": symbols,
                        "stype_in": "raw_symbol",
                        "start": start,
                        "end": end,
                        "purpose": "common-path and venue activity",
                    }
                )
            if dataset == "XNYS.PILLAR":
                for schema in ("status", "statistics", "imbalance"):
                    requests.append(
                        {
                            "request_id": f"{date}_XNYS_PILLAR_{schema}",
                            "dataset": dataset,
                            "schema": schema,
                            "symbols": symbols,
                            "stype_in": "raw_symbol",
                            "start": start,
                            "end": end,
                            "purpose": "opening-auction and security-state classification",
                        }
                    )
            if date in TICK_REFERENCE_DATES:
                requests.append(
                    {
                        "request_id": f"{date}_{dataset.replace('.', '_')}_mbp-1",
                        "dataset": dataset,
                        "schema": "mbp-1",
                        "symbols": symbols,
                        "stype_in": "raw_symbol",
                        "start": start,
                        "end": end,
                        "purpose": "event versus nearest-pre-day quote-update activity",
                    }
                )
        if not class_supplement:
            requests.append(
                {
                    "request_id": f"{date}_GLBX_MDP3_ESH3_mbp-1",
                    "dataset": "GLBX.MDP3",
                    "schema": "mbp-1",
                    "symbols": ["ESH3"],
                    "stype_in": "raw_symbol",
                    "start": start,
                    "end": end,
                    "purpose": "traded futures path and activity",
                }
            )
    return requests


def api_args(row: dict) -> dict:
    return {
        "dataset": row["dataset"],
        "schema": row["schema"],
        "symbols": row["symbols"],
        "stype_in": row["stype_in"],
        "start": row["start"],
        "end": row["end"],
    }


def quote(roster: Path, receipt_path: Path, class_supplement: bool = False) -> None:
    cl = get_client()
    rows = build_requests(roster, class_supplement=class_supplement)
    output = []
    for idx, row in enumerate(rows, start=1):
        current = {k: v for k, v in row.items() if k != "symbols"}
        current["requested_symbol_count"] = len(row["symbols"])
        try:
            resolved = cl.symbology.resolve(
                dataset=row["dataset"], symbols=row["symbols"],
                stype_in=row["stype_in"], stype_out="instrument_id",
                start_date=row["start"][:10],
                end_date=str((pd.Timestamp(row["end"][:10]) + pd.Timedelta(days=1)).date()),
            )
            result = resolved.get("result", {}) if isinstance(resolved, dict) else {}
            usable = [symbol for symbol in row["symbols"] if result.get(symbol)]
            unresolved = [symbol for symbol in row["symbols"] if symbol not in usable]
            current["symbols"] = usable
            current["resolved_symbol_count"] = len(usable)
            current["unresolved_symbols"] = unresolved
            args = api_args({**row, "symbols": usable})
            current["quoted_cost_usd"] = str(Decimal(str(cl.metadata.get_cost(**args))))
            current["billable_uncompressed_bytes"] = int(cl.metadata.get_billable_size(**args))
            current["estimated_record_count"] = int(cl.metadata.get_record_count(**args))
            current["quote_status"] = "QUOTED"
        except Exception as exc:  # preserve precise API failure without a blind retry
            current["quote_status"] = "ERROR"
            current["quote_error"] = f"{type(exc).__name__}: {exc}"
        output.append(current)
        write_json(
            receipt_path,
            {
                "status": "IN_PROGRESS",
                "sdk_version": getattr(db, "__version__", "NOT_OBSERVED"),
                "completed": idx,
                "total": len(rows),
                "requests": output,
            },
        )

    valid = [r for r in output if r["quote_status"] == "QUOTED"]
    receipt = {
        "status": "QUOTED",
        "sdk_version": getattr(db, "__version__", "NOT_OBSERVED"),
        "api_methods": [
            "symbology.resolve", "metadata.get_cost",
            "metadata.get_billable_size", "metadata.get_record_count",
        ],
        "request_count": len(output),
        "quote_error_count": len(output) - len(valid),
        "quoted_total_usd": str(sum((Decimal(r["quoted_cost_usd"]) for r in valid), Decimal("0"))),
        "billable_uncompressed_bytes": sum(r["billable_uncompressed_bytes"] for r in valid),
        "estimated_record_count": sum(r["estimated_record_count"] for r in valid),
        "requests": output,
        "credential_serialized": False,
    }
    write_json(receipt_path, receipt)
    print(json.dumps({k: receipt[k] for k in receipt if k != "requests"}, sort_keys=True))


def download(quote_path: Path, out_dir: Path, max_usd: Decimal, max_bytes: int) -> None:
    receipt = json.loads(quote_path.read_text())
    if receipt.get("status") != "QUOTED" or receipt.get("quote_error_count"):
        raise RuntimeError("complete error-free quote receipt required")
    if Decimal(receipt["quoted_total_usd"]) > max_usd:
        raise RuntimeError("bounded package exceeds supplied spending cap")
    if int(receipt["billable_uncompressed_bytes"]) > max_bytes:
        raise RuntimeError("bounded package exceeds supplied SCC size guard")
    out_dir.mkdir(parents=True, exist_ok=True)
    cl = get_client()
    states = []
    run_receipt = out_dir / "DOWNLOAD_RECEIPT.json"
    for row in receipt["requests"]:
        target = out_dir / f"{row['request_id']}.dbn.zst"
        state = {
            "request_id": row["request_id"], "dataset": row["dataset"],
            "schema": row["schema"], "start": row["start"], "end": row["end"],
            "resolved_symbol_count": row["resolved_symbol_count"], "path": str(target),
        }
        if target.exists() and target.stat().st_size > 0:
            state.update(status="REUSED_EXISTING", bytes=target.stat().st_size)
        else:
            state["status"] = "DOWNLOAD_STARTED_NO_BLIND_RETRY"
            states.append(state)
            write_json(run_receipt, {"status": "IN_PROGRESS", "files": states})
            cl.timeseries.get_range(
                dataset=row["dataset"], schema=row["schema"], symbols=row["symbols"],
                stype_in=row["stype_in"], stype_out="instrument_id",
                start=row["start"], end=row["end"], path=target,
            )
            state.update(status="DOWNLOADED_NATIVE_DBN_ON_SCC", bytes=target.stat().st_size)
        if state not in states:
            states.append(state)
        write_json(run_receipt, {"status": "IN_PROGRESS", "files": states})
    final = {
        "status": "COMPLETE_NATIVE_DBN_ON_SCC",
        "quoted_total_usd": receipt["quoted_total_usd"],
        "file_count": len(states),
        "total_compressed_bytes": sum(x["bytes"] for x in states),
        "files": states,
        "credential_serialized": False,
        "full_file_hashing_skipped_for_speed": True,
    }
    write_json(run_receipt, final)
    print(json.dumps({k: final[k] for k in final if k != "files"}, sort_keys=True))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)
    q = sub.add_parser("quote")
    q.add_argument("--roster", type=Path, required=True)
    q.add_argument("--receipt", type=Path, required=True)
    q.add_argument("--class-supplement", action="store_true")
    d = sub.add_parser("download")
    d.add_argument("--quote", type=Path, required=True)
    d.add_argument("--out-dir", type=Path, required=True)
    d.add_argument("--max-usd", type=Decimal, default=Decimal("100"))
    d.add_argument("--max-uncompressed-gb", type=int, default=100)
    args = ap.parse_args()
    if args.mode == "quote":
        quote(args.roster, args.receipt, class_supplement=args.class_supplement)
    else:
        download(args.quote, args.out_dir, args.max_usd, args.max_uncompressed_gb * 10**9)


if __name__ == "__main__":
    main()
