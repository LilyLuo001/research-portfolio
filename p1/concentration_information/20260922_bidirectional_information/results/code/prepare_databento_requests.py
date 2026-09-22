#!/usr/bin/env python3
"""Emit the exact bounded MBP-1 request plan without contacting Databento."""
from __future__ import annotations

import argparse, csv, json
from pathlib import Path
import pandas as pd

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roster", type=Path, required=True)
    ap.add_argument("--dates", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(); args.out.mkdir(parents=True, exist_ok=True)
    roster, dates = pd.read_csv(args.roster), pd.read_csv(args.dates)
    symbols = ["SPY", *roster.symbol.tolist()]
    rows = []
    for date in dates.date:
        # 10:00--10:30 ET plus the stipulated one-minute lead/tail, localized
        # before conversion so pre/post DST UTC timestamps are exact.
        start = pd.Timestamp(f"{date} 09:59:00", tz="America/New_York").tz_convert("UTC")
        end = pd.Timestamp(f"{date} 10:31:00", tz="America/New_York").tz_convert("UTC")
        for venue in ("XNAS.ITCH", "ARCX.PILLAR"):
            rows.append({"request_id": f"{venue.replace('.', '_')}_{date}", "dataset": venue,
                         "schema": "mbp-1", "stype_in": "raw_symbol", "symbols": ";".join(symbols),
                         "symbol_count": len(symbols), "start_utc": start.isoformat(), "end_utc": end.isoformat(),
                         "coverage_status": "MISSING_EXACT_WINDOW", "quote_status": "NOT_ATTEMPTED_NO_API_KEY",
                         "download_status": "NOT_STARTED"})
    (args.out / "REQUEST_MANIFEST.json").write_text(json.dumps({"request_count": len(rows), "symbols": symbols,
        "fixed_design": "24 stocks + SPY; 24 dates; 09:59-10:31 ET; mbp-1; XNAS.ITCH and ARCX.PILLAR",
        "requests": rows}, indent=2) + "\n")
    with (args.out / "COVERAGE.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["venue", "date", "schema", "status", "detail"]); w.writeheader()
        for r in rows: w.writerow({"venue": r["dataset"], "date": r["start_utc"][:10], "schema": "mbp-1", "status": r["coverage_status"], "detail": "No existing exact-design file identified; quote/download require injected DATABENTO_API_KEY."})
    ledger = {"status": "NO_PURCHASES_AUTHORIZED", "currency": "USD", "new_requests": [], "new_debit_usd": None,
              "reason": "DATABENTO_API_KEY absent in both SCC noninteractive and local environments; authenticated metadata/cost cannot be queried.",
              "prepared_request_count": len(rows), "budget_adaptation": "Not selected: no authenticated quote or verifiable balance."}
    (args.out / "PURCHASE_LEDGER.json").write_text(json.dumps(ledger, indent=2) + "\n")

if __name__ == "__main__": main()
