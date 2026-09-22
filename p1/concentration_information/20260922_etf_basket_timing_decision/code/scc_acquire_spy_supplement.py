#!/usr/bin/env python3
"""Acquire only the omitted SPY series for the already-downloaded basket windows."""
from __future__ import annotations

import hashlib
import json
import os
from decimal import Decimal
from pathlib import Path

import databento as db


OUT = Path("/scratch/qluo/etf_basket_timing_20260922")
REQUESTS = (
    ("P1-2023-08-01", "2023-01-31T11:15:00+00:00", "2023-01-31T12:45:00+00:00"),
    ("P1-2023-08-03", "2023-07-28T09:45:00+00:00", "2023-07-28T11:45:00+00:00"),
    ("P1-2023-06-02", "2023-04-14T09:40:00+00:00", "2023-04-14T11:10:00+00:00"),
    ("P1-2023-01-01", "2023-02-02T21:15:00+00:00", "2023-02-02T22:45:00+00:00"),
    ("P1-2023-01-03", "2023-08-03T20:15:00+00:00", "2023-08-03T21:45:00+00:00"),
    ("P1-2023-02-02", "2023-04-25T19:52:00+00:00", "2023-04-25T21:22:00+00:00"),
)
FEEDS = ("XNAS.ITCH", "ARCX.PILLAR")


def main() -> None:
    if not os.environ.get("DATABENTO_API_KEY"):
        raise RuntimeError("DATABENTO_API_KEY must be injected into the SCC process")
    client = db.Historical(os.environ["DATABENTO_API_KEY"])
    rows, total = [], Decimal("0")
    for event_id, start, end in REQUESTS:
        for feed in FEEDS:
            cost = Decimal(str(client.metadata.get_cost(dataset=feed, schema="bbo-1s", symbols=["SPY"], start=start, end=end, stype_in="raw_symbol")))
            total += cost
            rows.append({
                "event_id": event_id, "dataset": feed, "schema": "bbo-1s", "symbol": "SPY",
                "start": start, "end": end, "quoted_cost_usd": str(cost),
                "path": str(OUT / f"{event_id}_{feed.replace('.', '_')}_SPY.dbn.zst"),
            })
    quote = {"quoted_total_usd": str(total), "hard_cap_usd": "5", "requests": rows}
    (OUT / "SPY_SUPPLEMENT_COST_QUOTE.json").write_text(json.dumps(quote, indent=2) + "\n")
    if total > Decimal("5"):
        raise RuntimeError(f"SPY supplement quote {total} exceeds cap")
    for row in rows:
        path = Path(row["path"])
        if not path.exists():
            client.timeseries.get_range(
                dataset=row["dataset"], schema="bbo-1s", symbols=["SPY"], start=row["start"], end=row["end"],
                stype_in="raw_symbol", stype_out="instrument_id", path=path,
            )
        row["bytes"] = path.stat().st_size
        row["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        row["status"] = "DOWNLOADED_NATIVE_DBN_ON_SCC"
    (OUT / "SPY_SUPPLEMENT_DOWNLOAD_RECEIPT.json").write_text(json.dumps(rows, indent=2) + "\n")
    print(json.dumps({"requests": len(rows), "quoted_total_usd": str(total), "bytes": sum(row["bytes"] for row in rows)}))


if __name__ == "__main__":
    main()
