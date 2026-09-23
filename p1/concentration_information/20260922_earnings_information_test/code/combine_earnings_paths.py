#!/usr/bin/env python3
"""Combine disjoint safe path shards and recompute aggregate support."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    files = sorted(args.parts.glob("part_*/EVENT_PATH_DETAIL.csv"))
    if len(files) != 12:
        raise RuntimeError(f"expected 12 path shards, found {len(files)}")
    detail = pd.concat([pd.read_csv(path) for path in files], ignore_index=True)
    if detail.sample_id.nunique() != 96:
        raise RuntimeError("expected 96 logical event/control windows")
    # Shards already contain the fixed t=-1 baseline response and, after the
    # correction, a labelled t=0 reference sensitivity.  Never turn 0→0 into
    # same-direction persistence.
    aggregate = detail.groupby(["split", "sample_kind", "session", "venue", "instrument", "endpoint_seconds"], dropna=False).response_bp.agg(n="count", median_bp="median", mean_bp="mean", median_abs_bp=lambda x: x.abs().median()).reset_index()
    def persist(value, label):
        sixty=detail[detail.endpoint_seconds==60][["sample_id","venue","symbol",value]].rename(columns={value:"at60"})
        x=detail.merge(sixty,on=["sample_id","venue","symbol"],how="left")
        x=x[x.endpoint_seconds.isin([300,900])&x[value].notna()&x.at60.notna()].copy()
        x["nonzero_comparable"]=(x[value]!=0)&(x.at60!=0); x["same_direction_nonzero"]=(np.sign(x[value])==np.sign(x.at60))&x.nonzero_comparable; x["zero_to_zero"]=(x[value]==0)&(x.at60==0)
        g=["split","sample_kind","session","venue","instrument","endpoint_seconds"]
        z=x.groupby(g).agg(n_comparable=(value,"count"),n_nonzero_comparable=("nonzero_comparable","sum"),same_direction_nonzero_count=("same_direction_nonzero","sum"),zero_to_zero_count=("zero_to_zero","sum")).reset_index(); z["baseline"]=label; z["same_direction_nonzero_fraction"]=np.where(z.n_nonzero_comparable>0,z.same_direction_nonzero_count/z.n_nonzero_comparable,np.nan); return z
    summaries=[persist("response_bp","FIXED_GRID_T_MINUS_1_SECOND")]
    if "anchor_to_endpoint_response_bp" in detail: summaries.append(persist("anchor_to_endpoint_response_bp","LEGACY_ANCHOR_T_ZERO_REFERENCE"))
    persistence_summary=pd.concat(summaries,ignore_index=True)
    if "path_status" not in detail:
        detail["path_status"]=np.where(detail.response_bp.notna(),"VALID_RESPONSE","INVALID_BASELINE_OR_ENDPOINT")
    coverage=detail.groupby(["split","sample_kind","session","venue","instrument","endpoint_seconds","path_status"],dropna=False).size().rename("rows").reset_index()
    args.out.mkdir(parents=True, exist_ok=True)
    detail.to_csv(args.out / "EVENT_PATH_DETAIL.csv", index=False)
    aggregate.to_csv(args.out / "EVENT_PATH_SUMMARY.csv", index=False)
    persistence_summary.to_csv(args.out / "PERSISTENCE_SUMMARY.csv", index=False)
    coverage.to_csv(args.out / "PATH_COVERAGE.csv",index=False)
    receipt = {"status": "COMPLETE_COMBINED_SAFE_EARNINGS_PATHS", "part_count": len(files), "samples": int(detail.sample_id.nunique()), "events": int(detail.event_id.nunique()), "detail_rows": len(detail), "raw_prices_exported": False, "baseline":"fixed t=-1 second with labelled anchor-t=0 sensitivity when shard fields are present"}
    (args.out / "PATH_RECEIPT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
