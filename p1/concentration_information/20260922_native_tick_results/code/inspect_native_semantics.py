#!/usr/bin/env python3
"""Aggregate action/side/flag semantics without exporting licensed tick rows."""

import csv
from collections import Counter
from pathlib import Path

import databento as db
from databento_dbn import MBP1Msg


ROOT = Path("/scratch/qluo/native_tick_pilot_20260922")


def value(x):
    return str(getattr(x, "value", x))


rows = []
for path in sorted(ROOT.glob("*_mbp1.dbn.zst")):
    store = db.DBNStore.from_file(path)
    mapping = {}
    for raw, spans in store.metadata.mappings.items():
        for span in spans:
            mapping[int(span["symbol"])] = raw.upper().strip()
    counts = Counter()
    for record in store:
        if not isinstance(record, MBP1Msg):
            continue
        symbol = mapping.get(int(record.instrument_id), "UNKNOWN")
        counts[(symbol, value(record.action), value(record.side), int(record.flags))] += 1
    for (symbol, action, side, flags), n in sorted(counts.items()):
        rows.append({
            "file": path.name,
            "symbol": symbol,
            "action": action,
            "side": side,
            "flags_integer": flags,
            "records": n,
        })

out = ROOT / "SOURCE_SEMANTICS_COUNTS.csv"
with out.open("w", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
print(f"wrote {len(rows)} aggregate rows to {out}")
