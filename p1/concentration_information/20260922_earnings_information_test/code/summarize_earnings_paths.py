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
        # Keep the anchor state as an auditable reference, but use the fixed
        # grid point one second before it as the response baseline.  Neither
        # state is back-filled from an earlier valid quote.
        anchor = index.loc[600] if 600 in index.index else None
        base = index.loc[599] if 599 in index.index else None
        for endpoint in ENDPOINTS:
            finish = index.loc[600 + endpoint] if 600 + endpoint in index.index else None
            valid = base is not None and finish is not None and bool(base.quote_valid) and bool(finish.quote_valid) and np.isfinite(base.mid) and np.isfinite(finish.mid) and base.mid > 0 and finish.mid > 0
            rows.append({
                **dict(zip(group_cols, keys)), "endpoint_seconds": endpoint,
                "response_bp": float(1e4 * (np.log(finish.mid) - np.log(base.mid))) if valid else np.nan,
                "anchor_to_endpoint_response_bp": float(1e4 * (np.log(finish.mid) - np.log(anchor.mid))) if (anchor is not None and finish is not None and bool(anchor.quote_valid) and bool(finish.quote_valid) and np.isfinite(anchor.mid) and np.isfinite(finish.mid) and anchor.mid > 0 and finish.mid > 0) else np.nan,
                "response_baseline": "FIXED_GRID_T_MINUS_1_SECOND",
                "response_baseline_relative_seconds": -1,
                "anchor_reference": "GRID_T_ZERO",
                "anchor_reference_valid": bool(anchor is not None and anchor.quote_valid and np.isfinite(anchor.mid) and anchor.mid > 0),
                "baseline_valid": bool(base is not None and base.quote_valid),
                "endpoint_valid": bool(finish is not None and finish.quote_valid),
                "baseline_spread_bp": float(base.spread_bp) if base is not None and np.isfinite(base.spread_bp) else np.nan,
                "endpoint_spread_bp": float(finish.spread_bp) if finish is not None and np.isfinite(finish.spread_bp) else np.nan,
            })
    observed = pd.DataFrame(rows)
    # Materialize all intended cells.  This separates a missing source panel
    # from an invalid quote endpoint rather than silently omitting either.
    sample_meta = data[["sample_id", "event_id", "issuer", "date", "sample_kind", "split", "anchor_et", "session", "venue"]].drop_duplicates()
    expected = []
    for row in sample_meta.itertuples(index=False):
        for symbol, instrument in (("SPY", "SPY"), (row.issuer, "ISSUER")):
            for endpoint in ENDPOINTS:
                expected.append({**row._asdict(), "symbol": symbol, "instrument": instrument, "endpoint_seconds": endpoint})
    expected = pd.DataFrame(expected)
    detail = expected.merge(observed, on=[*group_cols, "symbol", "endpoint_seconds"], how="left", indicator=True)
    detail["instrument"] = detail["instrument"].where(detail["instrument"].notna(), pd.Series(np.where(detail.symbol == "SPY", "SPY", "ISSUER"), index=detail.index))
    detail["path_status"] = np.where(detail._merge.eq("left_only"), "NO_SOURCE_PANEL", np.where(detail.response_bp.isna(), "INVALID_BASELINE_OR_ENDPOINT", "VALID_RESPONSE"))
    detail = detail.drop(columns="_merge")
    aggregate = detail.groupby(["split", "sample_kind", "session", "venue", "instrument", "endpoint_seconds"], dropna=False).response_bp.agg(n="count", median_bp="median", mean_bp="mean", median_abs_bp=lambda x: x.abs().median()).reset_index()
    def persistence_summary_for(value_col, baseline_label):
        sixty = detail[detail.endpoint_seconds == 60][["sample_id", "venue", "symbol", value_col]].rename(columns={value_col: "response_60_bp"})
        persistence = detail.merge(sixty, on=["sample_id", "venue", "symbol"], how="left")
        persistence = persistence[persistence.endpoint_seconds.isin([300, 900]) & persistence[value_col].notna() & persistence.response_60_bp.notna()].copy()
        signs_equal = np.sign(persistence[value_col]) == np.sign(persistence.response_60_bp)
        nonzero = (persistence[value_col] != 0) & (persistence.response_60_bp != 0)
        persistence["nonzero_comparable"] = nonzero
        persistence["same_direction_nonzero"] = signs_equal & nonzero
        persistence["zero_to_zero"] = (persistence[value_col] == 0) & (persistence.response_60_bp == 0)
        pgroup = ["split", "sample_kind", "session", "venue", "instrument", "endpoint_seconds"]
        ans = persistence.groupby(pgroup).agg(n_comparable=(value_col, "count"), n_nonzero_comparable=("nonzero_comparable", "sum"), same_direction_nonzero_count=("same_direction_nonzero", "sum"), zero_to_zero_count=("zero_to_zero", "sum")).reset_index()
        ans["baseline"] = baseline_label
        return ans
    persistence_summary = pd.concat([persistence_summary_for("response_bp", "FIXED_GRID_T_MINUS_1_SECOND"), persistence_summary_for("anchor_to_endpoint_response_bp", "LEGACY_ANCHOR_T_ZERO_REFERENCE")], ignore_index=True)
    persistence_summary["same_direction_nonzero_fraction"] = np.where(persistence_summary.n_nonzero_comparable > 0, persistence_summary.same_direction_nonzero_count / persistence_summary.n_nonzero_comparable, np.nan)
    coverage = detail.groupby(["split", "sample_kind", "session", "venue", "instrument", "endpoint_seconds", "path_status"], dropna=False).size().rename("rows").reset_index()
    args.out.mkdir(parents=True, exist_ok=True)
    detail.to_csv(args.out / "EVENT_PATH_DETAIL.csv", index=False)
    aggregate.to_csv(args.out / "EVENT_PATH_SUMMARY.csv", index=False)
    persistence_summary.to_csv(args.out / "PERSISTENCE_SUMMARY.csv", index=False)
    coverage.to_csv(args.out / "PATH_COVERAGE.csv", index=False)
    receipt = {"status": "COMPLETE_SAFE_EARNINGS_PATH_SUMMARY", "feature_sha256": digest(args.features), "detail_rows": len(detail), "observed_detail_rows": len(observed), "aggregate_rows": len(aggregate), "endpoints_seconds": list(ENDPOINTS), "raw_prices_exported": False, "baseline": "fixed grid t=-1 second; anchor t=0 retained as labelled reference; no backward search or interpolation"}
    (args.out / "PATH_RECEIPT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
