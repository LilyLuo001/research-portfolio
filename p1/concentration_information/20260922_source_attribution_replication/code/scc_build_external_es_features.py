#!/usr/bin/env python3
"""Build the 24-date ES feature panel using frozen validated primitives."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd


NS = 1_000_000_000


def load(path: Path):
    spec = importlib.util.spec_from_file_location("frozen_es", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--download-receipt", required=True, type=Path)
    ap.add_argument("--validated-es-builder", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--receipt", required=True, type=Path)
    args = ap.parse_args(); prior = load(args.validated_es_builder)
    receipt = json.loads(args.download_receipt.read_text())
    items = [item for item in receipt.get("files", []) if item.get("dataset") == "GLBX.MDP3"]
    if receipt.get("status") != "COMPLETE_NATIVE_DBN_ON_SCC" or len(items) != 24:
        raise RuntimeError("complete 24-file external ES receipt required")
    frames, contracts = [], []
    for item in items:
        decoded = prior.decode(Path(item["path"]))
        if len(decoded) != 1:
            raise RuntimeError(f"{item['path']}: exactly one ES contract required")
        metadata_symbol, data = next(iter(decoded.items()))
        # A continuous request saved with stype_out=instrument_id retains
        # `ES.v.0` as the DBN metadata mapping key even though the pre-request
        # symbology receipt resolves that instrument id to ESH4/ESM4/etc.
        if metadata_symbol.upper() not in {item["actual_raw_symbol"].upper(), "ES.V.0"}:
            raise RuntimeError(f"{item['date']}: unexpected DBN metadata symbol {metadata_symbol}")
        start, end = int(pd.Timestamp(item["start_utc"]).value), int(pd.Timestamp(item["end_utc"]).value)
        for shift in (0, 500):
            grid = np.arange(start + 60 * NS + shift * 1_000_000, end - 60 * NS, NS, dtype=np.int64)
            values, lag = prior.values(data, grid), prior.values(data, grid - NS)
            frame = pd.DataFrame({"date": item["date"], "grid_shift_ms": shift,
                "second_index": np.arange(len(grid), dtype=int), "t_ns": grid,
                "contract": item["actual_raw_symbol"], "requested_contract": "ES.v.0"})
            for key, value in values.items(): frame[key] = value
            for key, value in lag.items(): frame["lag1_" + key] = value
            frames.append(frame)
        contracts.append({"date": item["date"], "actual_raw_symbol": item["actual_raw_symbol"],
            "dbn_metadata_symbol": metadata_symbol, "instrument_id": item["instrument_id"],
            "raw_path": item["path"], "raw_sha256": item["sha256"]})
    table = pd.concat(frames, ignore_index=True)
    keys = ["date", "grid_shift_ms", "second_index"]
    if len(table) != 24 * 2 * 1800 or table.duplicated(keys).any():
        raise RuntimeError("unexpected external ES panel shape")
    args.out.parent.mkdir(parents=True, exist_ok=True); table.to_parquet(args.out, index=False)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps({"status": "COMPLETE_EXTERNAL_ES_FEATURES_ON_SCC", "feature_path": str(args.out),
        "feature_sha256": sha(args.out), "dates": 24, "rows": len(table), "keys": keys,
        "ts_basis": "ts_event; source records ordered by ts_event, sequence, source order",
        "contracts": contracts, "native_rows_stay_on_scc": True}, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
