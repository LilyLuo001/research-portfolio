#!/usr/bin/env python3
"""Export only aggregate DBN initialization diagnostics from SCC-native files."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path

import databento as db

NS = 1_000_000_000


def utc(value: int) -> str:
    return datetime.fromtimestamp(value / NS, timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    with args.manifest.open(newline="") as handle:
        files = list(csv.DictReader(handle))
    rows: list[dict[str, object]] = []
    for item in files:
        target = int(datetime.fromisoformat(item["baseline_target_utc"].replace("Z", "+00:00")).timestamp() * NS)
        store = db.DBNStore.from_file(item["dbn_path"])
        mapping: dict[int, str] = {}
        for raw_symbol, intervals in store.metadata.mappings.items():
            for interval in intervals:
                mapping[int(interval["symbol"])] = raw_symbol
        prior, warmup, kinds = set(), set(), set()
        records, first, last = 0, None, None
        for record in store:
            records += 1
            kinds.add(type(record).__name__)
            timestamp = int(record.ts_recv)
            first = timestamp if first is None or timestamp < first else first
            last = timestamp if last is None or timestamp > last else last
            symbol = mapping.get(int(record.instrument_id))
            if symbol and timestamp <= target:
                prior.add(symbol)
            if symbol and target - 600 * NS <= timestamp <= target:
                warmup.add(symbol)
        rows.append({
            "event_id": item["event_id"], "dataset": item["dataset"],
            "mapped_symbols": len(set(mapping.values())), "records": records,
            "record_types": ";".join(sorted(kinds)),
            "symbols_with_any_prior_or_at_baseline": len(prior),
            "symbols_with_update_in_available_10m_warmup": len(warmup),
            "baseline_target_utc": item["baseline_target_utc"],
            "first_record_utc": utc(first) if first is not None else "",
            "last_record_utc": utc(last) if last is not None else "",
            "interpretation": "RECORD_PRESENCE_ONLY_NO_STATUS_OR_VALIDITY_TEST",
        })
    fields = list(rows[0])
    with args.out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
