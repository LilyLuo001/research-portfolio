#!/usr/bin/env python3
"""Invoke the validated directional feature builder for the frozen 2024 data.

This wrapper enforces the 24-date/two-equity-venue/one-shared-ES input design,
then leaves native DBN and the row-level parquet on SCC.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--download-receipt", required=True, type=Path)
    ap.add_argument("--validated-builder", required=True, type=Path)
    ap.add_argument("--base-code", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--receipt", required=True, type=Path)
    args = ap.parse_args()
    download = json.loads(args.download_receipt.read_text())
    requests = download.get("selected_variant", {}).get("requests", [])
    if download.get("status") != "COMPLETE_NATIVE_DBN_ON_SCC" or len(requests) != 72:
        raise RuntimeError("complete 72-request external download receipt required")
    if {r["dataset"] for r in requests} != {"XNAS.ITCH", "ARCX.PILLAR", "GLBX.MDP3"}:
        raise RuntimeError("wrong external datasets")
    # The validated builder consumes only the two equity venue requests.  ES is
    # built by the frozen ES feature builder and joined later by model code.
    equity = []
    for source in requests:
        if source["dataset"] not in {"XNAS.ITCH", "ARCX.PILLAR"}:
            continue
        # The machine manifest stores its compact symbol field as a semicolon
        # string.  The validated builder expects an iterable of full symbols;
        # passing the string would iterate characters and silently lose rows.
        item = dict(source)
        item["symbols"] = list(source.get("resolved_symbols") or source["symbols"].split(";"))
        equity.append(item)
    files = [r for r in download["files"] if r["dataset"] in {"XNAS.ITCH", "ARCX.PILLAR"}]
    staged = args.receipt.parent / "_EQUITY_DOWNLOAD_RECEIPT.json"
    staged.write_text(json.dumps({"status": "COMPLETE_NATIVE_DBN_ON_SCC", "selected_variant": {"requests": equity}, "files": files}) + "\n")
    subprocess.run([sys.executable, str(args.validated_builder), "--base-code", str(args.base_code),
                    "--download-receipt", str(staged), "--out", str(args.out),
                    "--receipt", str(args.receipt)], check=True)
    data = pd.read_parquet(args.out, columns=["date", "venue", "grid_shift_ms", "symbol"])
    if (set(data.date.astype(str).unique()) != {r["date"] for r in equity}
            or set(data.venue.unique()) != {"XNAS.ITCH", "ARCX.PILLAR"}
            or set(data.grid_shift_ms.unique()) != {0, 500}
            or len(set(data.symbol.unique())) != 24
            or "BF" in set(data.symbol.unique())):
        raise RuntimeError("unexpected external equity feature panel identity")
    receipt = json.loads(args.receipt.read_text()); receipt.update({"wrapper_status": "COMPLETE_EXTERNAL_EQUITY_FEATURES_ON_SCC",
        "external_dates": 24, "equity_request_count": 48, "external_symbols": 24,
        "stocks": 23, "excluded_unobserved_roster_symbol": "BF", "native_rows_stay_on_scc": True})
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
