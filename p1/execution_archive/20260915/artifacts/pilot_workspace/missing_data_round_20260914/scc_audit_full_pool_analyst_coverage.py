#!/usr/bin/env python3
"""Measure >=2-analyst forecast support for the full 8PRE+4POST pool on SCC."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq


ROOT = Path("/projectnb/econdept/qluo/P1_Refraction_WRDS/missing_data_round_20260914")
RAW = Path("/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared/raw")
POOL = ROOT / "EARNINGS_METADATA_POOL_8PRE_4POST.csv"
OUT = ROOT / "full_pool_analyst_coverage"
EXPECTED_POOL_SHA256 = "f33bc3532b127554531380e80635c961a5a251ada51ca287b412c144ba0a6b3f"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    if sha256(POOL) != EXPECTED_POOL_SHA256:
        raise ValueError("earnings pool hash mismatch")
    if OUT.exists():
        raise FileExistsError(f"preserve output: {OUT}")
    OUT.mkdir(parents=True)
    pool = pd.read_csv(POOL)
    pool["cusip"] = pool.cusip.astype("string").str.strip().str.upper()
    pool["pends_dt"] = pd.to_datetime(pool.pends)
    pool["release_dt"] = pd.to_datetime(pool.anndats)
    pool["event_key"] = pool.apply(
        lambda r: f"{r.wave_id}_{int(r.permno)}_{r.event_side}_{r.pends.replace('-', '')}", axis=1
    )
    selected_cusips = set(pool.cusip.dropna())
    selected_periods = set(pool.pends_dt.dropna())
    key_table = pool[["event_key", "cusip", "pends_dt", "release_dt"]].drop_duplicates()

    counts = []
    input_receipts = []
    for year in range(2018, 2025):
        path = RAW / f"ibes_detu_eps_{year}.parquet"
        if not path.exists():
            continue
        columns = ["cusip", "fpedats", "analys", "anndats"]
        pf = pq.ParquetFile(path)
        if any(c not in pf.schema.names for c in columns):
            raise ValueError(f"missing columns in {path}")
        selected_rows = 0
        for batch in pf.iter_batches(batch_size=400_000, columns=columns):
            frame = batch.to_pandas()
            frame["cusip"] = frame.cusip.astype("string").str.strip().str.upper()
            frame["fpedats"] = pd.to_datetime(frame.fpedats)
            frame = frame[frame.cusip.isin(selected_cusips) & frame.fpedats.isin(selected_periods)].copy()
            if frame.empty:
                continue
            frame["forecast_date"] = pd.to_datetime(frame.anndats)
            joined = frame.merge(
                key_table,
                left_on=["cusip", "fpedats"],
                right_on=["cusip", "pends_dt"],
                how="inner",
            )
            joined = joined[
                (joined.forecast_date < joined.release_dt)
                & (joined.forecast_date >= joined.release_dt - pd.Timedelta(days=90))
            ].copy()
            if not joined.empty:
                counts.append(joined[["event_key", "analys"]])
                selected_rows += len(joined)
        input_receipts.append({"path": str(path), "sha256": sha256(path), "matched_rows": selected_rows})
    detail = pd.concat(counts, ignore_index=True) if counts else pd.DataFrame(columns=["event_key", "analys"])
    analyst_counts = detail.groupby("event_key").analys.nunique().rename("analyst_count_90d")
    events = pool.merge(analyst_counts, on="event_key", how="left")
    events["analyst_count_90d"] = events.analyst_count_90d.fillna(0).astype(int)
    events["analyst_min2"] = events.analyst_count_90d.ge(2)
    event_export = events[
        ["event_key", "wave_id", "permno", "provisional_tier", "event_side", "pends", "anndats", "analyst_count_90d", "analyst_min2"]
    ].drop_duplicates("event_key")
    event_export.to_csv(OUT / "event_analyst_coverage.csv", index=False)
    candidate = event_export.groupby(["wave_id", "permno", "provisional_tier"]).agg(
        selected_events=("event_key", "size"),
        events_with_min2=("analyst_min2", "sum"),
        minimum_analyst_count=("analyst_count_90d", "min"),
    ).reset_index()
    candidate["all_12_events_min2"] = candidate.selected_events.eq(12) & candidate.events_with_min2.eq(12)
    candidate.to_csv(OUT / "candidate_analyst_coverage.csv", index=False)
    summary = candidate.groupby(["wave_id", "provisional_tier"]).agg(
        full_8pre4post_candidates=("permno", "size"),
        all_12_events_min2=("all_12_events_min2", "sum"),
    ).reset_index()
    summary.to_csv(OUT / "analyst_coverage_summary.csv", index=False)
    receipt = {
        "status": "FULL_POOL_ANALYST_COVERAGE_COMPLETE",
        "pool_sha256": sha256(POOL),
        "pool_rows": len(pool),
        "unique_events": int(event_export.event_key.nunique()),
        "candidate_rows": len(candidate),
        "candidates_all_12_events_min2": int(candidate.all_12_events_min2.sum()),
        "event_coverage_sha256": sha256(OUT / "event_analyst_coverage.csv"),
        "candidate_coverage_sha256": sha256(OUT / "candidate_analyst_coverage.csv"),
        "summary_sha256": sha256(OUT / "analyst_coverage_summary.csv"),
        "forecast_inputs": input_receipts,
        "forecast_values_read": False,
        "price_return_quote_values_read": False,
    }
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
