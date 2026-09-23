#!/usr/bin/env python3
"""Create safe event-level and aggregate quote-response paths from SCC panels."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ENDPOINTS = (1, 5, 10, 30, 60, 300, 900)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    files = sorted(path.glob("*.parquet")) if path.is_dir() else [path]
    for file in files:
        h.update(file.name.encode())
        h.update(file.read_bytes())
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    columns = ["sample_id", "event_id", "issuer", "date", "sample_kind", "split", "anchor_et", "session", "venue", "symbol", "grid_shift_ms", "second_index", "mid", "spread_bp", "quote_valid"]
    # session is reconstructed below when older feature artifacts omit it.
    try:
        data = pd.read_parquet(args.features, columns=columns)
    except Exception:
        columns.remove("session")
        data = pd.read_parquet(args.features, columns=columns)
        data["session"] = np.where(data.anchor_et < "09:30:00", "PREMARKET", np.where(data.anchor_et < "16:00:00", "RTH", "AFTER_HOURS"))
    data = data[data.grid_shift_ms == 0].copy()
    data = data[(data.symbol == "SPY") | (data.symbol == data.issuer)].copy()
    rows = []
    group_cols = ["sample_id", "event_id", "issuer", "date", "sample_kind", "split", "anchor_et", "session", "venue", "symbol"]
    for keys, group in data.groupby(group_cols, sort=False):
        index = group.set_index("second_index")
        base = index.loc[600] if 600 in index.index else None
        for endpoint in ENDPOINTS:
            finish = index.loc[600 + endpoint] if 600 + endpoint in index.index else None
            valid = base is not None and finish is not None and bool(base.quote_valid) and bool(finish.quote_valid) and np.isfinite(base.mid) and np.isfinite(finish.mid) and base.mid > 0 and finish.mid > 0
            rows.append({
                **dict(zip(group_cols, keys)), "endpoint_seconds": endpoint,
                "response_bp": float(1e4 * (np.log(finish.mid) - np.log(base.mid))) if valid else np.nan,
                "baseline_valid": bool(base is not None and base.quote_valid),
                "endpoint_valid": bool(finish is not None and finish.quote_valid),
                "baseline_spread_bp": float(base.spread_bp) if base is not None and np.isfinite(base.spread_bp) else np.nan,
                "endpoint_spread_bp": float(finish.spread_bp) if finish is not None and np.isfinite(finish.spread_bp) else np.nan,
            })
    detail = pd.DataFrame(rows)
    detail["instrument"] = np.where(detail.symbol == "SPY", "SPY", "ISSUER")
    aggregate = detail.groupby(["split", "sample_kind", "session", "venue", "instrument", "endpoint_seconds"], dropna=False).response_bp.agg(n="count", median_bp="median", mean_bp="mean", median_abs_bp=lambda x: x.abs().median()).reset_index()
    sixty = detail[detail.endpoint_seconds == 60][["sample_id", "venue", "symbol", "response_bp"]].rename(columns={"response_bp": "response_60_bp"})
    persistence = detail.merge(sixty, on=["sample_id", "venue", "symbol"], how="left")
    persistence = persistence[persistence.endpoint_seconds.isin([300, 900]) & persistence.response_bp.notna() & persistence.response_60_bp.notna()].copy()
    persistence["same_direction_as_60s"] = np.sign(persistence.response_bp) == np.sign(persistence.response_60_bp)
    persistence_summary = persistence.groupby(["split", "sample_kind", "session", "venue", "instrument", "endpoint_seconds"]).same_direction_as_60s.agg(n="count", same_direction_fraction="mean").reset_index()
    args.out.mkdir(parents=True, exist_ok=True)
    detail.to_csv(args.out / "EVENT_PATH_DETAIL.csv", index=False)
    aggregate.to_csv(args.out / "EVENT_PATH_SUMMARY.csv", index=False)
    persistence_summary.to_csv(args.out / "PERSISTENCE_SUMMARY.csv", index=False)
    receipt = {"status": "COMPLETE_SAFE_EARNINGS_PATH_SUMMARY", "feature_sha256": digest(args.features), "detail_rows": len(detail), "aggregate_rows": len(aggregate), "endpoints_seconds": list(ENDPOINTS), "raw_prices_exported": False, "baseline": "exact candidate-clock grid center; no backward search or interpolation"}
    (args.out / "PATH_RECEIPT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
