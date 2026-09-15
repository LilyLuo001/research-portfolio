#!/usr/bin/env python3
"""Attach observed U.S. sessions and corporate-action metadata to 480 events.

Reads no prices or returns.  Distribution amounts remain in the SCC-only raw
subset; the exportable table contains only counts and boolean/factor-change
flags used to protect later endpoint construction.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq


ROOT = Path("/projectnb/econdept/qluo/P1_Refraction_WRDS/missing_data_round_20260914")
RAW = Path("/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared/raw")
EVENTS = Path(os.environ.get("P1_EVENT_MANIFEST", ROOT / "supported_earnings_inputs/selected_event_metadata.csv"))
OUT = Path(os.environ.get("P1_EVENT_CALENDAR_OUTPUT", ROOT / "event_calendar_actions"))
EXPECTED_EVENTS_SHA256 = os.environ.get(
    "P1_EVENT_MANIFEST_SHA256",
    "d2f113fe770ed9efb959652f0b4aef99442138056d3a08311771e1cc408bab52",
)
EXPECTED_EVENT_ROWS = int(os.environ.get("P1_EVENT_ROWS", "480"))
SPY_PERMNO = 84398


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    if sha256(EVENTS) != EXPECTED_EVENTS_SHA256:
        raise ValueError("event manifest hash mismatch")
    if OUT.exists():
        raise FileExistsError(f"preserve existing output: {OUT}")
    OUT.mkdir(parents=True)
    events = pd.read_csv(EVENTS)
    events["announcement_date"] = pd.to_datetime(events.announcement_date)
    permnos = set(events.permno.astype(int)) | {SPY_PERMNO}

    daily_parts = []
    daily_inputs = []
    for year in range(2019, 2025):
        path = RAW / "rescue" / f"crsp_dsf_allcols_{year}.parquet"
        columns = ["permno", "date", "cfacpr", "cfacshr"]
        missing = [c for c in columns if c not in pq.read_schema(path).names]
        if missing:
            raise ValueError(f"missing daily columns {path}: {missing}")
        frame = pd.read_parquet(path, columns=columns)
        frame = frame[frame.permno.isin(permnos)].copy()
        daily_parts.append(frame)
        daily_inputs.append({"path": str(path), "sha256": sha256(path), "selected_rows": len(frame)})
    daily = pd.concat(daily_parts, ignore_index=True)
    daily["date"] = pd.to_datetime(daily.date)
    daily = daily.sort_values(["permno", "date"]).drop_duplicates(["permno", "date"])
    sessions = sorted(daily.loc[daily.permno.eq(SPY_PERMNO), "date"].unique())
    if len(sessions) < 1400:
        raise ValueError("SPY observed-session calendar unexpectedly short")
    session_index = {pd.Timestamp(d): i for i, d in enumerate(sessions)}
    pd.DataFrame({"session_date": sessions, "calendar_basis": "CRSP_SPY_OBSERVED_SESSION"}).to_csv(
        OUT / "trading_calendar.csv", index=False
    )

    def first_on_or_after(day: pd.Timestamp) -> pd.Timestamp:
        for value in sessions:
            value = pd.Timestamp(value)
            if value >= day:
                return value
        raise ValueError(f"calendar ends before {day}")

    calendar_rows = []
    for row in events.itertuples(index=False):
        day = pd.Timestamp(row.announcement_date)
        reaction = first_on_or_after(day)
        idx = session_index[reaction]
        if idx < 1 or idx + 2 >= len(sessions):
            raise ValueError(f"calendar boundary for {row.association_id}")
        calendar_rows.append({
            "association_id": row.association_id,
            "wave_id": row.wave_id,
            "permno": int(row.permno),
            "date_valid_raw_symbol": row.date_valid_raw_symbol,
            "sample_period": row.sample_period,
            "announcement_date": day.strftime("%Y-%m-%d"),
            "announcement_date_is_observed_session": day in session_index,
            "previous_session": pd.Timestamp(sessions[idx - 1]).strftime("%Y-%m-%d"),
            "reaction_session": reaction.strftime("%Y-%m-%d"),
            "next_session": pd.Timestamp(sessions[idx + 1]).strftime("%Y-%m-%d"),
            "second_next_session": pd.Timestamp(sessions[idx + 2]).strftime("%Y-%m-%d"),
            "calendar_basis": "CRSP_SPY_OBSERVED_SESSION",
        })
    calendar = pd.DataFrame(calendar_rows)

    dist_path = RAW / "crsp_dsedist.parquet"
    dist_columns = [
        "permno", "distcd", "divamt", "facpr", "facshr", "dclrdt", "exdt",
        "rcrddt", "paydt", "acperm", "accomp", "cusip",
    ]
    missing = [c for c in dist_columns if c not in pq.read_schema(dist_path).names]
    if missing:
        raise ValueError(f"missing distribution columns: {missing}")
    distributions = pq.read_table(
        dist_path,
        columns=dist_columns,
        filters=[("permno", "in", sorted(set(events.permno.astype(int))))],
    ).to_pandas()
    distributions = distributions[distributions.permno.isin(set(events.permno.astype(int)))].copy()
    for col in ["dclrdt", "exdt", "rcrddt", "paydt"]:
        distributions[col] = pd.to_datetime(distributions[col])

    action_rows = []
    for row in calendar.itertuples(index=False):
        lo = pd.Timestamp(row.previous_session)
        hi = pd.Timestamp(row.second_next_session)
        stock_daily = daily[(daily.permno.eq(row.permno)) & daily.date.between(lo, hi)].copy()
        stock_dist = distributions[
            distributions.permno.eq(row.permno) & distributions.exdt.between(lo, hi)
        ].copy()
        action_rows.append({
            "association_id": row.association_id,
            "daily_factor_rows": len(stock_daily),
            "cfacpr_unique": stock_daily.cfacpr.nunique(dropna=True),
            "cfacshr_unique": stock_daily.cfacshr.nunique(dropna=True),
            "price_factor_change_flag": stock_daily.cfacpr.nunique(dropna=True) > 1,
            "share_factor_change_flag": stock_daily.cfacshr.nunique(dropna=True) > 1,
            "distribution_event_count": len(stock_dist),
            "distribution_flag": len(stock_dist) > 0,
        })
    actions = pd.DataFrame(action_rows)
    export = calendar.merge(actions, on="association_id", validate="one_to_one")
    export.to_csv(OUT / "event_calendar_and_action_flags.csv", index=False)
    # Values needed for later adjustments stay only on SCC.
    distributions.to_parquet(OUT / "licensed_distribution_rows_selected_permnos.parquet", index=False)
    daily.to_parquet(OUT / "daily_factor_rows_selected_permnos.parquet", index=False)

    if len(export) != EXPECTED_EVENT_ROWS:
        raise ValueError(f"expected {EXPECTED_EVENT_ROWS} event rows")
    receipt = {
        "status": "EVENT_CALENDAR_AND_ACTION_INPUTS_ACQUIRED",
        "event_manifest_sha256": sha256(EVENTS),
        "event_rows": len(export),
        "non_session_announcement_dates": int((~export.announcement_date_is_observed_session).sum()),
        "distribution_flagged_associations": int(export.distribution_flag.sum()),
        "price_factor_change_associations": int(export.price_factor_change_flag.sum()),
        "share_factor_change_associations": int(export.share_factor_change_flag.sum()),
        "calendar_sha256": sha256(OUT / "trading_calendar.csv"),
        "export_sha256": sha256(OUT / "event_calendar_and_action_flags.csv"),
        "licensed_distribution_subset_sha256": sha256(OUT / "licensed_distribution_rows_selected_permnos.parquet"),
        "daily_factor_subset_sha256": sha256(OUT / "daily_factor_rows_selected_permnos.parquet"),
        "daily_inputs": daily_inputs,
        "distribution_input": {"path": str(dist_path), "sha256": sha256(dist_path)},
        "price_or_return_values_read": False,
        "licensed_distribution_values_exported": False,
    }
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
