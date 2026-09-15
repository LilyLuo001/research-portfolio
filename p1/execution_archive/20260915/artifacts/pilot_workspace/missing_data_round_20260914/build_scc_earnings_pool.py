#!/usr/bin/env python3
"""Build an outcomes-free 8-PRE/4-POST earnings metadata pool on SCC."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
ARCHIVE = Path("/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared")
TIERS = HERE / "PREANNOUNCEMENT_EXPOSURE_PROVISIONAL_TIERS.csv"
PACKAGES = HERE / "PACKAGE_INPUTS.csv"
LINK = ARCHIVE / "raw" / "crsp_ibes_link_full.parquet"
CALENDAR = ARCHIVE / "raw" / "maximal" / "crsp_metaexchangecalendar_full.parquet"
IBES_META = Path("/projectnb/econdept/qluo/P1_Refraction_WRDS/p1_roster_earnings_20260913/ibes_metadata_projection_v2/ibes_announcement_metadata.csv")

LISTING_DATES = {
    "W002": "2021-06-14",
    "W013": "2022-10-31",
    "W016": "2023-03-13",
    "W021": "2023-07-31",
    "W025": "2023-11-20",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def norm8(x) -> str:
    if pd.isna(x):
        return ""
    return str(x).strip().upper()[:8]


def post_thresholds() -> dict[str, str]:
    cal = pd.read_parquet(CALENDAR, columns=["caldt", "tradingflg"])
    cal["caldt"] = pd.to_datetime(cal.caldt)
    sessions = sorted(cal.loc[cal.tradingflg.eq("Y"), "caldt"].drop_duplicates())
    out = {}
    for wave, listing in LISTING_DATES.items():
        later = [x for x in sessions if x > pd.Timestamp(listing)]
        if len(later) < 20:
            raise ValueError(f"calendar lacks 20 sessions after {listing}")
        out[wave] = later[19].strftime("%Y-%m-%d")
    return out


def main():
    tiers = pd.read_csv(TIERS)
    tiers = tiers[tiers.provisional_tier.isin(["low", "high"])].copy()
    tiers["permno"] = tiers.permno.astype(int)
    wanted = set(tiers.permno)
    link = pd.read_parquet(LINK, columns=["permno", "ncusip", "sdate", "edate", "score"])
    link = link[link.permno.isin(wanted)].copy()
    link["permno"] = link.permno.astype(int)
    link["cusip"] = link.ncusip.map(norm8)
    link["sdate"] = pd.to_datetime(link.sdate, errors="coerce")
    link["edate"] = pd.to_datetime(link.edate, errors="coerce").fillna(pd.Timestamp("2099-12-31"))
    meta = pd.read_csv(IBES_META, dtype=str)
    forbidden = {"value", "actual", "forecast", "ret", "return", "car", "sue"}
    if forbidden.intersection({c.lower() for c in meta.columns}):
        raise ValueError("outcome/value column unexpectedly present")
    meta = meta[meta.pdicity.eq("QTR")].copy()
    meta["cusip"] = meta.cusip.map(norm8)
    meta["anndats_dt"] = pd.to_datetime(meta.anndats, errors="coerce")
    merged = tiers.merge(link, on="permno", how="left", validate="many_to_many", suffixes=("", "_link"))
    merged = merged.merge(meta, on="cusip", how="left", validate="many_to_many", suffixes=("", "_ibes"))
    merged = merged[(merged.sdate <= merged.anndats_dt) & (merged.anndats_dt <= merged.edate)].copy()
    thresholds = post_thresholds()
    merged["post_20_session_threshold"] = merged.wave_id.map(thresholds)
    merged["event_side"] = np.where(
        merged.anndats_dt < pd.to_datetime(merged.announcement_cutoff),
        "PRE",
        np.where(merged.anndats_dt >= pd.to_datetime(merged.post_20_session_threshold), "POST", "TRANSITION_OR_BUFFER"),
    )
    # Collapse only exact duplicate link paths; retain one row per stock-wave/accounting period.
    merged = merged.sort_values(["wave_id", "permno", "pends", "anndats_dt", "anntims", "score"])
    dup = merged.groupby(["wave_id", "permno", "pends"], dropna=False).size().rename("period_candidate_rows").reset_index()
    merged = merged.merge(dup, on=["wave_id", "permno", "pends"], how="left", validate="many_to_one")
    unique = merged.drop_duplicates(["wave_id", "permno", "pends"], keep="first").copy()
    selected = []
    for (wave, permno), g in unique.groupby(["wave_id", "permno"], sort=True):
        pre = g[g.event_side.eq("PRE")].sort_values(["anndats_dt", "anntims"]).tail(8).copy()
        post = g[g.event_side.eq("POST")].sort_values(["anndats_dt", "anntims"]).head(4).copy()
        pre["within_side_order"] = range(1, len(pre) + 1)
        post["within_side_order"] = range(1, len(post) + 1)
        selected.extend([pre, post])
    pool = pd.concat(selected, ignore_index=True) if selected else pd.DataFrame()
    keep = [
        "wave_id", "role", "permno", "crsp_ticker", "issuer_name_crsp", "siccd",
        "provisional_tier", "tier_rule_status", "exposure_ownership", "q1", "q2",
        "median_dollar_volume_candidate", "liquidity_rule_status", "announcement_cutoff",
        "post_20_session_threshold", "event_side", "within_side_order", "cusip", "score",
        "ticker", "pends", "pdicity", "anndats", "anntims", "actdats", "acttims",
        "source_partition", "period_candidate_rows",
    ]
    pool = pool[keep].sort_values(["wave_id", "permno", "event_side", "within_side_order"])
    pool["economic_event_status"] = "METADATA_CANDIDATE_NOT_PUBLIC_CLOCK_CERTIFIED"
    pool.to_csv(HERE / "EARNINGS_METADATA_POOL_8PRE_4POST.csv", index=False)
    counts = pool.groupby(["wave_id", "permno", "provisional_tier", "event_side"]).size().unstack(fill_value=0).reset_index()
    for c in ["PRE", "POST"]:
        if c not in counts:
            counts[c] = 0
    counts["has_8pre_4post"] = counts.PRE.ge(8) & counts.POST.ge(4)
    counts = counts.merge(
        tiers[["wave_id", "permno", "crsp_ticker", "exposure_ownership", "median_dollar_volume_candidate", "liquidity_observations"]],
        on=["wave_id", "permno"], how="left", validate="one_to_one"
    )
    counts.to_csv(HERE / "EARNINGS_METADATA_ELIGIBILITY.csv", index=False)
    summary = counts.groupby(["wave_id", "provisional_tier"]).agg(
        tail_candidates=("permno", "size"),
        candidates_with_8pre_4post=("has_8pre_4post", "sum"),
    ).reset_index()
    summary.to_csv(HERE / "EARNINGS_METADATA_WAVE_TIER_SUMMARY.csv", index=False)
    receipt = {
        "status": "OUTCOMES_FREE_EARNINGS_METADATA_POOL_COMPLETE",
        "raw_financial_values_read": False,
        "post_quote_outcomes_read": False,
        "source_record_unit": "IBES QTR metadata record",
        "economic_event_certified": False,
        "tail_stock_wave_candidates": len(counts),
        "candidate_rows_selected_max_8pre_4post": len(pool),
        "candidates_with_8pre_4post": int(counts.has_8pre_4post.sum()),
        "post_thresholds": thresholds,
        "input_hashes": {"tiers": sha256(TIERS), "packages": sha256(PACKAGES), "link": sha256(LINK), "calendar": sha256(CALENDAR), "ibes_metadata": sha256(IBES_META)},
        "output_hashes": {},
    }
    for name in ["EARNINGS_METADATA_POOL_8PRE_4POST.csv", "EARNINGS_METADATA_ELIGIBILITY.csv", "EARNINGS_METADATA_WAVE_TIER_SUMMARY.csv"]:
        receipt["output_hashes"][name] = sha256(HERE / name)
    (HERE / "SCC_EARNINGS_POOL_RECEIPT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(summary.to_string(index=False))
    print(json.dumps({k: receipt[k] for k in ["status", "tail_stock_wave_candidates", "candidate_rows_selected_max_8pre_4post", "candidates_with_8pre_4post", "post_thresholds"]}, indent=2))


if __name__ == "__main__":
    main()
