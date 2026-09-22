#!/usr/bin/env python3
"""Build SCC-only features for the directional-evidence continuation.

Extends the validated bidirectional feature construction by separating known-
side signed flow, unknown-side dollar volume, and no-trade intervals.  It also
records midpoint-update activity for the 0/500ms grid comparison.  Raw and
row-level feature data remain on SCC.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd


NS = 1_000_000_000
INTERVALS = (
    ("0_100ms", 100_000_000, 0),
    ("100ms_1s", NS, 100_000_000),
    ("1s_5s", 5 * NS, NS),
)


def load_base(path: Path):
    spec = importlib.util.spec_from_file_location("validated_base", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def trade_extended(data: dict, start: np.ndarray, end: np.ndarray) -> dict[str, np.ndarray]:
    left = np.searchsorted(data["trade_t"], start, side="right")
    right = np.searchsorted(data["trade_t"], end, side="right")
    n = len(start)
    signed = np.zeros(n); known_dollars = np.zeros(n); unknown_dollars = np.zeros(n)
    total_dollars = np.zeros(n); no_trade = np.zeros(n); known_share = np.full(n, np.nan)
    dollars, signs = data["trade_dollars"], data["trade_sign"]
    for i, (lo, hi) in enumerate(zip(left, right)):
        if lo == hi:
            no_trade[i] = 1.0; known_share[i] = 1.0
            continue
        d, s = dollars[lo:hi], signs[lo:hi]
        good = np.isfinite(d); known = good & np.isfinite(s); unknown = good & ~np.isfinite(s)
        total_dollars[i] = float(np.sum(d[good]))
        known_dollars[i] = float(np.sum(d[known]))
        unknown_dollars[i] = float(np.sum(d[unknown]))
        signed[i] = float(np.sum(d[known] * s[known]))
        known_share[i] = float(np.sum(known) / np.sum(good)) if np.sum(good) else np.nan
    return {
        "known_signed_flow": signed, "known_dollar_volume": known_dollars,
        "unknown_dollar_volume": unknown_dollars, "total_dollar_volume": total_dollars,
        "no_trade": no_trade, "known_direction_share": known_share,
    }


def midpoint_update_times(data: dict) -> np.ndarray:
    t, m = data["state_t"], data["mid"]
    if len(t) == 0:
        return np.asarray([], dtype=np.int64)
    last = np.r_[np.flatnonzero(t[1:] != t[:-1]), len(t) - 1]
    tt, mm = t[last], m[last]
    changed = np.zeros(len(tt), dtype=bool)
    changed[1:] = np.isfinite(mm[1:]) & np.isfinite(mm[:-1]) & (mm[1:] != mm[:-1])
    return tt[changed]


def update_diagnostics(update_t: np.ndarray, grid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    left = np.searchsorted(update_t, grid - NS, side="right")
    right = np.searchsorted(update_t, grid, side="right")
    count = (right - left).astype(float)
    pos = np.searchsorted(update_t, grid, side="right") - 1
    age = np.full(len(grid), np.nan)
    valid = pos >= 0
    age[valid] = (grid[valid] - update_t[pos[valid]]) / 1e6
    return count, age


def build_symbol(base, date: str, venue: str, symbol: str, data: dict,
                 core_start: int, core_end: int, shift_ms: int) -> pd.DataFrame:
    grid = np.arange(core_start + shift_ms * 1_000_000, core_end, NS, dtype=np.int64)
    frame = pd.DataFrame({"date": date, "t_ns": grid, "symbol": symbol,
                          "venue": venue, "grid_shift_ms": shift_ms})
    frame["second_index"] = np.arange(len(grid), dtype=int)
    frame["minute_bin_5m"] = ((grid - core_start) // (300 * NS)).astype(int)
    frame["quote_valid"] = np.isfinite(base.state_at(data, grid, "mid"))
    for name, outer, inner in INTERVALS:
        start, end = grid - outer, grid - inner
        frame[f"ret_{name}"] = base.log_return(data, start, end)
        parts = trade_extended(data, start, end)
        for key, value in parts.items():
            frame[f"{key}_{name}"] = value
    frame["spread_bp"] = base.state_at(data, grid, "spread_bp")
    frame["bid_depth"] = base.state_at(data, grid, "bid_depth")
    frame["ask_depth"] = base.state_at(data, grid, "ask_depth")
    count, age = update_diagnostics(midpoint_update_times(data), grid)
    frame["mid_update_count_1s"] = count
    frame["mid_update_age_ms"] = age
    frame["y_1s_bp"] = base.log_return(data, grid, grid + NS)
    return frame


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-code", required=True, type=Path)
    ap.add_argument("--download-receipt", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--receipt", required=True, type=Path)
    args = ap.parse_args()
    base = load_base(args.base_code)
    receipt = json.loads(args.download_receipt.read_text())
    request_by_id = {x["request_id"]: x for x in receipt["selected_variant"]["requests"]}
    frames, status = [], []
    for item in receipt["files"]:
        request = request_by_id[item["request_id"]]
        decoded = base.decode(Path(item["path"]))
        request_start = int(pd.Timestamp(request["start_utc"]).value)
        request_end = int(pd.Timestamp(request["end_utc"]).value)
        core_start, core_end = request_start + 60 * NS, request_end - 60 * NS
        for symbol in request["symbols"]:
            if symbol not in decoded:
                status.append({"request_id": item["request_id"], "symbol": symbol, "status": "NO_ROWS"})
                continue
            for shift in (0, 500):
                frames.append(build_symbol(base, request["start_utc"][:10], request["dataset"],
                                           symbol, decoded[symbol], core_start, core_end, shift))
            status.append({"request_id": item["request_id"], "symbol": symbol, "status": "BUILT"})
    table = pd.concat(frames, ignore_index=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    table.to_parquet(args.out, index=False)
    output = {
        "status": "COMPLETE_DIRECTIONAL_FEATURES_ON_SCC", "feature_path": str(args.out),
        "rows": len(table), "dates": int(table.date.nunique()), "symbols": int(table.symbol.nunique()),
        "venues": sorted(table.venue.unique().tolist()), "grid_shifts_ms": sorted(table.grid_shift_ms.unique().tolist()),
        "source_status_counts": pd.DataFrame(status).status.value_counts().to_dict(),
        "unknown_trade_handling": "known signed flow and unknown dollar volume are separate; no-trade is explicit",
        "raw_or_feature_rows_exported_locally": False,
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
