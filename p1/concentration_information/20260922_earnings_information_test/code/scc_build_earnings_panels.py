#!/usr/bin/env python3
"""Build SCC-only equity and ES panels for the fixed earnings windows."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

NS = 1_000_000_000


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for part in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def attach(frame: pd.DataFrame, row: dict) -> pd.DataFrame:
    frame["sample_id"] = row["sample_id"]
    frame["event_id"] = row["event_id"]
    frame["issuer"] = row["issuer"]
    frame["sample_kind"] = row["sample_kind"]
    frame["split"] = row["split"]
    frame["anchor_utc"] = row["anchor_utc"]
    frame["anchor_et"] = row["anchor_et"]
    return frame


def build_equity(files: list[dict], feature, base, out: Path) -> dict:
    frames, status = [], []
    for row in files:
        decoded = base.decode(Path(row["path"]))
        start = int(pd.Timestamp(row["start_utc"]).value)
        end = int(pd.Timestamp(row["end_utc"]).value)
        core_start, core_end = start + 60 * NS, end - 60 * NS
        for symbol in row["resolved_symbols"]:
            if symbol not in decoded:
                status.append({"request_id": row["request_id"], "symbol": symbol, "status": "NO_ROWS"})
                continue
            for shift in (0, 500):
                part = feature.build_symbol(base, row["date"], row["dataset"], symbol, decoded[symbol], core_start, core_end, shift)
                grid = part["t_ns"].to_numpy(np.int64)
                part["mid"] = base.state_at(decoded[symbol], grid, "mid")
                half = part["spread_bp"].to_numpy(float) * part["mid"].to_numpy(float) / 20000.0
                part["bid"] = part["mid"] - half
                part["ask"] = part["mid"] + half
                part["y_5s_bp"] = base.log_return(decoded[symbol], grid, grid + 5 * NS)
                part["y_30s_bp"] = base.log_return(decoded[symbol], grid, grid + 30 * NS)
                frames.append(attach(part, row))
            status.append({"request_id": row["request_id"], "symbol": symbol, "status": "BUILT"})
    table = pd.concat(frames, ignore_index=True)
    keys = ["sample_id", "venue", "symbol", "grid_shift_ms", "second_index"]
    if table.duplicated(keys).any():
        raise RuntimeError("duplicate equity panel key")
    out.parent.mkdir(parents=True, exist_ok=True)
    table.to_parquet(out, index=False)
    return {"path": str(out), "sha256": digest(out), "rows": len(table), "samples": int(table.sample_id.nunique()), "symbols": int(table.symbol.nunique()), "venues": sorted(table.venue.unique().tolist()), "status_counts": pd.DataFrame(status).status.value_counts().to_dict()}


def build_es(files: list[dict], esmod, out: Path) -> dict:
    frames, contracts = [], []
    for row in files:
        decoded = esmod.decode(row["path"])
        if len(decoded) != 1:
            raise RuntimeError(f"{row['request_id']}: expected one ES contract, got {sorted(decoded)}")
        actual, data = next(iter(decoded.items()))
        start = int(pd.Timestamp(row["start_utc"]).value)
        end = int(pd.Timestamp(row["end_utc"]).value)
        for shift in (0, 500):
            grid = np.arange(start + 60 * NS + shift * 1_000_000, end - 60 * NS, NS, dtype=np.int64)
            values = esmod.values(data, grid)
            frame = pd.DataFrame({"date": row["date"], "grid_shift_ms": shift, "second_index": np.arange(len(grid)), "t_ns": grid, "contract": actual})
            for key, value in values.items():
                frame[key] = value
            for key, value in esmod.values(data, grid - NS).items():
                frame["lag1_" + key] = value
            frames.append(attach(frame, row))
        contracts.append({"sample_id": row["sample_id"], "requested": "ES.v.0", "actual": actual, "raw_path": row["path"], "raw_sha256": row["sha256"]})
    table = pd.concat(frames, ignore_index=True)
    keys = ["sample_id", "grid_shift_ms", "second_index"]
    if table.duplicated(keys).any():
        raise RuntimeError("duplicate ES panel key")
    out.parent.mkdir(parents=True, exist_ok=True)
    table.to_parquet(out, index=False)
    return {"path": str(out), "sha256": digest(out), "rows": len(table), "samples": int(table.sample_id.nunique()), "contracts": contracts}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--download-receipt", required=True, type=Path)
    ap.add_argument("--equity-feature-code", required=True, type=Path)
    ap.add_argument("--equity-base-code", required=True, type=Path)
    ap.add_argument("--es-code", required=True, type=Path)
    ap.add_argument("--equity-out", required=True, type=Path)
    ap.add_argument("--es-out", required=True, type=Path)
    ap.add_argument("--receipt", required=True, type=Path)
    ap.add_argument("--shard-index", type=int)
    ap.add_argument("--shard-count", type=int)
    args = ap.parse_args()
    receipt = json.loads(args.download_receipt.read_text())
    files = receipt.get("files", [])
    if receipt.get("status") != "COMPLETE_NATIVE_DBN_ON_SCC" or len(files) != 288:
        raise RuntimeError("complete fixed 288-file receipt required")
    equity = [r for r in files if r["dataset"] in {"XNAS.ITCH", "ARCX.PILLAR"}]
    futures = [r for r in files if r["dataset"] == "GLBX.MDP3"]
    if len(equity) != 192 or len(futures) != 96:
        raise RuntimeError("unexpected source counts")
    if (args.shard_index is None) != (args.shard_count is None):
        raise RuntimeError("shard-index and shard-count must be supplied together")
    if args.shard_index is not None:
        samples = sorted({r["sample_id"] for r in files})
        if not (0 <= args.shard_index < args.shard_count):
            raise RuntimeError("invalid shard index")
        keep = {sample for position, sample in enumerate(samples) if position % args.shard_count == args.shard_index}
        equity = [r for r in equity if r["sample_id"] in keep]
        futures = [r for r in futures if r["sample_id"] in keep]
    feature = load(args.equity_feature_code, "earnings_feature")
    base = feature.load_base(args.equity_base_code)
    esmod = load(args.es_code, "earnings_es")
    equity_result = build_equity(equity, feature, base, args.equity_out)
    es_result = build_es(futures, esmod, args.es_out)
    output = {
        "status": "COMPLETE_EARNINGS_PANELS_ON_SCC", "equity": equity_result, "es": es_result,
        "event_clock_definition": "second_index=600 is the candidate earnings minute; panel covers anchor[-10m,+16m) on 0/500ms grids",
        "shard_index": args.shard_index, "shard_count": args.shard_count,
        "raw_or_row_level_data_exported_locally": False,
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": output["status"], "equity_rows": equity_result["rows"], "es_rows": es_result["rows"]}, sort_keys=True))


if __name__ == "__main__":
    main()
