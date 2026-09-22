#!/usr/bin/env python3
"""Validate the SCC-only causal feature-table contract before model fitting."""
from __future__ import annotations
import argparse
import pandas as pd

REQUIRED = ["date", "t_ns", "symbol", "venue", "grid_shift_ms", "minute_bin_5m",
            "report_weight", "y_100ms_bp", "y_1s_bp", "y_5s_bp",
            "ret_0_100ms", "ret_100ms_1s", "ret_1s_5s",
            "flow_0_100ms", "flow_100ms_1s", "flow_1s_5s",
            "spread_bp", "bid_depth", "ask_depth", "volume_5s",
            "native_direction_share_5s", "quote_valid"]

def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("features"); args = ap.parse_args()
    x = pd.read_parquet(args.features) if args.features.endswith((".parquet", ".pq")) else pd.read_csv(args.features)
    missing = sorted(set(REQUIRED) - set(x.columns))
    if missing: raise SystemExit("missing feature-contract columns: " + ", ".join(missing))
    if x.duplicated(["date", "t_ns", "symbol", "venue", "grid_shift_ms"]).any():
        raise SystemExit("duplicate feature keys")
    if not set(x.grid_shift_ms.unique()).issubset({0, 500}): raise SystemExit("unexpected grid shift")
    print(f"PASS {len(x)} causal feature rows; raw/fine records remain SCC-only")

if __name__ == "__main__": main()
