#!/usr/bin/env python3
"""Generate the frozen 2024 external-test dates and minimal MBP-1 orders.

The calendar is deliberately implemented from NYSE full-day closures.  It is
a closed, auditable 2024 period: early closes remain sessions and there were
no exceptional full-day closures affecting the selected dates.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import pandas as pd


NYSE_CLOSED_2024_H1 = (
    "2024-01-01", "2024-01-15", "2024-02-19", "2024-03-29",
    "2024-05-27", "2024-06-19", "2024-07-04", "2024-09-02",
    "2024-11-28", "2024-12-25",
)
EXPECTED = [
    ("2024-01-08", 5), ("2024-01-23", 15),
    ("2024-02-07", 5), ("2024-02-22", 15),
    ("2024-03-07", 5), ("2024-03-21", 15),
    ("2024-04-05", 5), ("2024-04-19", 15),
    ("2024-05-07", 5), ("2024-05-21", 15),
    ("2024-06-07", 5), ("2024-06-24", 15),
    ("2024-07-08", 5), ("2024-07-22", 15),
    ("2024-08-07", 5), ("2024-08-21", 15),
    ("2024-09-09", 5), ("2024-09-23", 15),
    ("2024-10-07", 5), ("2024-10-21", 15),
    ("2024-11-07", 5), ("2024-11-21", 15),
    ("2024-12-06", 5), ("2024-12-20", 15),
]
EXCLUDED_UNOBSERVED_ROSTER_SYMBOLS = {"BF"}


def sessions() -> list[tuple[str, int]]:
    closed = pd.to_datetime(list(NYSE_CLOSED_2024_H1))
    days = pd.bdate_range("2024-01-01", "2024-12-31").difference(closed)
    out: list[tuple[str, int]] = []
    for month in range(1, 13):
        part = days[days.month == month]
        for ordinal in (5, 15):
            out.append((str(part[ordinal - 1].date()), ordinal))
    if out != EXPECTED:
        raise RuntimeError(f"NYSE calendar mismatch: {out}")
    return out


def utc(day: str, clock: str) -> str:
    return pd.Timestamp(f"{day} {clock}", tz="America/New_York").tz_convert("UTC").isoformat()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roster", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    roster = pd.read_csv(args.roster)
    required = {"symbol", "permno", "report_weight"}
    if len(roster) != 24 or not required <= set(roster):
        raise RuntimeError("the source roster with its one unobserved symbol is required")
    # BF was present in the historical roster file but failed symbology and
    # never entered the frozen DIRECTIONAL_FEATURES panel.  External testing
    # must preserve the observed 23-stock design rather than add a new stock.
    roster = roster.loc[~roster.symbol.isin(EXCLUDED_UNOBSERVED_ROSTER_SYMBOLS)].copy()
    if len(roster) != 23:
        raise RuntimeError("expected 23 stocks observed in the frozen feature panel")
    selected = sessions()
    dates = pd.DataFrame(selected, columns=["date", "nyse_session_ordinal"])
    dates["window_et"] = "10:00:00-10:30:00"
    dates["grid_shifts_ms"] = "0;500"
    dates["split"] = "external_test"
    dates["selection_rule"] = "5th_or_15th_NYSE_session_of_month"
    dates.to_csv(args.out / "DATE_MANIFEST.csv", index=False)

    symbols = ["SPY", *roster.symbol.tolist()]
    rows: list[dict[str, object]] = []
    for day, ordinal in selected:
        start, end = utc(day, "09:59:00"), utc(day, "10:31:00")
        for dataset in ("XNAS.ITCH", "ARCX.PILLAR"):
            rows.append({"request_id": f"{dataset.replace('.', '_')}_{day}", "date": day,
                         "nyse_session_ordinal": ordinal, "dataset": dataset, "schema": "mbp-1",
                         "stype_in": "raw_symbol", "symbols": ";".join(symbols), "symbol_count": len(symbols),
                         "start_utc": start, "end_utc": end, "core_window_et": "10:00:00-10:30:00",
                         "reuse_status": "MISSING_EXACT_WINDOW", "raw_path": "PENDING_QUOTE"})
        rows.append({"request_id": f"GLBX_MDP3_{day}_ESV0_MBP1", "date": day,
                     "nyse_session_ordinal": ordinal, "dataset": "GLBX.MDP3", "schema": "mbp-1",
                     "stype_in": "continuous", "symbols": "ES.v.0", "symbol_count": 1,
                     "start_utc": start, "end_utc": end, "core_window_et": "10:00:00-10:30:00",
                     "reuse_status": "MISSING_EXACT_WINDOW", "raw_path": "PENDING_QUOTE"})
    if len(rows) != 72:
        raise RuntimeError("expected 48 equity plus 24 shared-futures requests")
    fields = list(rows[0])
    with (args.out / "REQUEST_MANIFEST.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    (args.out / "REQUEST_MANIFEST.json").write_text(json.dumps({
        "status": "PREPARED_UNQUOTED", "request_count": 72, "equity_request_count": 48,
        "shared_futures_request_count": 24, "symbols": symbols,
        "design": "24 fixed 2024 external-test dates (each month's fifth and fifteenth NYSE session); mbp-1; 09:59-10:31 ET; XNAS/ARCX each include SPY plus the 23 stocks observed in the frozen 2023 feature panel; BF is excluded because it never entered that panel; one ES.v.0 request is shared by both equity venues.",
        "requests": rows,
    }, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
