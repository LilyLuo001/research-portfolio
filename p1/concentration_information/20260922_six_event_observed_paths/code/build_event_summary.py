#!/usr/bin/env python3
"""Build the reviewed six-event summary from derived endpoints.

The report metadata below are permitted SCC aggregates independently checked
against CRSP. They are retrospective scale inputs, not event-time holdings.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVENTS = [
    ("P1-2023-08-01", "XOM", "2023-01-31", ["06:30_ET"], "SOURCE_SUPPORTED_MINUTE_CANDIDATE", "2022-12-31", "2023-01-09", 1.4099998474),
    ("P1-2023-08-03", "XOM", "2023-07-28", ["06:00_ET", "06:30_ET"], "ISSUER_WIRE_CONFLICT", "2023-06-30", "2023-07-07", 1.1699991226),
    ("P1-2023-06-02", "UNH", "2023-04-14", ["05:55_ET"], "EARLIEST_OBSERVED_WIRE_CANDIDATE", "2023-03-31", "2023-04-10", 1.2899999619),
    ("P1-2023-01-01", "AAPL", "2023-02-02", ["16:30_ET"], "SOURCE_SUPPORTED_MINUTE_CANDIDATE", "2022-12-31", "2023-01-09", 6.0499992371),
    ("P1-2023-01-03", "AAPL", "2023-08-03", ["16:30_ET"], "SOURCE_SUPPORTED_MINUTE_CANDIDATE", "2023-06-30", "2023-07-07", 7.7199974060),
    ("P1-2023-02-02", "MSFT", "2023-04-25", ["16:07_ET"], "AVAILABILITY_NOTICE_NOT_ORIGINAL_RELEASE", "2023-03-31", "2023-04-10", 6.25),
]
FIELDS = [
    "event_id", "issuer", "event_date", "anchor_variants_et", "clock_class",
    "primary_common_support", "status", "primary_plus5_spy_bp",
    "primary_plus5_stock_bp", "primary_plus5_spy_crosses_zero",
    "primary_plus5_stock_crosses_zero",
    "plus5_spy_mid_direction_agrees_xnas_arcx",
    "plus5_stock_mid_direction_agrees_xnas_arcx", "plus60_common_available",
    "report_dt", "max_eff_dt", "issuer_report_percent_tna",
    "issuer_weight_x_plus5_bp",
]


def valid(row: dict[str, str]) -> bool:
    return row["baseline_status"].startswith("VALID") and row["endpoint_status"].startswith("VALID")


def sign(value: float) -> int:
    return (value > 0) - (value < 0)


def joined(values: list[str]) -> str:
    return values[0] if len(values) == 1 else ";".join(values)


def main() -> None:
    with (ROOT / "ENDPOINTS.csv").open(newline="") as handle:
        endpoints = list(csv.DictReader(handle))
    index = {
        (r["event_id"], r["anchor"], r["feed"], r["symbol"], int(r["horizon_minutes"])): r
        for r in endpoints
    }
    output = []
    for event_id, issuer, event_date, anchors, clock_class, report_dt, eff_dt, weight in EVENTS:
        spy_changes, issuer_changes = [], []
        spy_cross, issuer_cross, spy_venue, issuer_venue, plus60 = [], [], [], [], []
        for anchor in anchors:
            x_spy = index[(event_id, anchor, "XNAS.ITCH", "SPY", 5)]
            x_issuer = index[(event_id, anchor, "XNAS.ITCH", issuer, 5)]
            a_spy = index[(event_id, anchor, "ARCX.PILLAR", "SPY", 5)]
            a_issuer = index[(event_id, anchor, "ARCX.PILLAR", issuer, 5)]
            spy_change = float(x_spy["mid_change_bps"])
            issuer_change = float(x_issuer["mid_change_bps"])
            spy_changes.append(f"{spy_change:.6f}")
            issuer_changes.append(f"{issuer_change:.6f}")
            spy_cross.append("YES" if float(x_spy["cross_spread_lower_bps"]) <= 0 <= float(x_spy["cross_spread_upper_bps"]) else "NO")
            issuer_cross.append("YES" if float(x_issuer["cross_spread_lower_bps"]) <= 0 <= float(x_issuer["cross_spread_upper_bps"]) else "NO")
            spy_venue.append("YES" if sign(spy_change) == sign(float(a_spy["mid_change_bps"])) else "NO")
            issuer_venue.append("YES" if sign(issuer_change) == sign(float(a_issuer["mid_change_bps"])) else "NO")
            plus60_rows = [
                index[(event_id, anchor, feed, symbol, 60)]
                for feed in ("XNAS.ITCH", "ARCX.PILLAR") for symbol in ("SPY", issuer)
            ]
            plus60.append("YES" if all(valid(r) for r in plus60_rows) else "NO")
        products = [f"{weight * float(change) / 100:.6f}" for change in issuer_changes]
        common = all(
            valid(index[(event_id, anchor, "XNAS.ITCH", symbol, 5)])
            for anchor in anchors for symbol in ("SPY", issuer)
        )
        output.append({
            "event_id": event_id, "issuer": issuer, "event_date": event_date,
            "anchor_variants_et": joined([a.replace("_ET", "") for a in anchors]),
            "clock_class": clock_class, "primary_common_support": "YES" if common else "NO",
            "status": "COMPUTED" if all(v == "YES" for v in plus60) else "COMPUTED_WITH_0630_PLUS60_ARCHIVE_GAP",
            "primary_plus5_spy_bp": joined(spy_changes),
            "primary_plus5_stock_bp": joined(issuer_changes),
            "primary_plus5_spy_crosses_zero": joined(spy_cross),
            "primary_plus5_stock_crosses_zero": joined(issuer_cross),
            "plus5_spy_mid_direction_agrees_xnas_arcx": joined(spy_venue),
            "plus5_stock_mid_direction_agrees_xnas_arcx": joined(issuer_venue),
            "plus60_common_available": joined(plus60), "report_dt": report_dt,
            "max_eff_dt": eff_dt, "issuer_report_percent_tna": f"{weight:.8f}".rstrip("0").rstrip("."),
            "issuer_weight_x_plus5_bp": joined(products),
        })
    with (ROOT / "EVENT_SUMMARY.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(output)

    quality_path = ROOT / "QUALITY_SUMMARY.json"
    quality = json.loads(quality_path.read_text())
    quality["purchases_usd"] = 0.015461146832
    quality["retrospective_static_report_dilution"] = {
        f"{issuer}_{date}": {"report_dt": report_dt, "max_eff_dt": eff_dt, "percent_tna": weight}
        for _, issuer, date, _, _, report_dt, eff_dt, weight in EVENTS
    }
    quality_path.write_text(json.dumps(quality, indent=2) + "\n")


if __name__ == "__main__":
    main()
