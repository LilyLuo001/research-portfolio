#!/usr/bin/env python3
"""Combine the eight completed SCC model shards into aggregate-only outputs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


TABLES = (
    "MODEL_COMPARISON.csv",
    "DAILY_LOSS_DIFFERENCES.csv",
    "AGGREGATE_COMPARISON.csv",
    "DATE_SENSITIVITY.csv",
    "REVERSE_CHECK.csv",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    receipts = sorted(args.parts.glob("*/MODEL_RECEIPT.json"))
    if len(receipts) != 8:
        raise RuntimeError(f"expected 8 completed shards; found {len(receipts)}")
    cells = []
    for path in receipts:
        receipt = json.loads(path.read_text())
        if receipt.get("status") != "COMPLETE_FUTURES_CONTROL_MODELS":
            raise RuntimeError(f"incomplete receipt: {path}")
        cell = receipt["cell_filter"]
        key = (cell["venue"], int(cell["grid_shift_ms"]), cell["family"])
        cells.append(key)
    if len(set(cells)) != 8:
        raise RuntimeError(f"duplicate shard cells: {cells}")

    args.out.mkdir(parents=True, exist_ok=True)
    output_rows = {}
    output_hashes = {}
    for name in TABLES:
        paths = [p.parent / name for p in receipts]
        missing = [str(p) for p in paths if not p.exists()]
        if missing:
            raise RuntimeError(f"missing {name}: {missing}")
        frame = pd.concat([pd.read_csv(p) for p in paths], ignore_index=True)
        sort_cols = [c for c in ("venue", "grid_shift_ms", "family", "es_cutoff", "support", "symbol", "date", "contrast", "omitted_date") if c in frame]
        if sort_cols:
            frame = frame.sort_values(sort_cols, kind="mergesort").reset_index(drop=True)
        target = args.out / name
        frame.to_csv(target, index=False)
        output_rows[name] = len(frame)
        output_hashes[name] = sha256(target)

    receipt = {
        "status": "COMPLETE_EIGHT_SHARD_COMBINE",
        "cells": [dict(venue=v, grid_shift_ms=s, family=f) for v, s, f in sorted(cells)],
        "shard_receipt_hashes": {str(p.relative_to(args.parts)): sha256(p) for p in receipts},
        "output_rows": output_rows,
        "output_hashes": output_hashes,
        "row_level_features_or_predictions_exported": False,
    }
    (args.out / "MODEL_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
