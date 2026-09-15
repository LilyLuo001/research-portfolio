#!/usr/bin/env python3
"""Build the maximum five-wave roster allowed by the proposed overlap rule."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
POOL = ROOT / "FULL_SUPPORTED_CANDIDATE_POOL.csv"
DETAIL = ROOT / "crsp_attached/stock_wave_candidate_roster.csv"
E007 = Path("/Users/lilyluo/research-portfolio-p1-advanced-readonly/p1/exposure/exposure_stock_wave_all.csv")
OUT = ROOT / "clean_acquisition"
CUTOFF = {
    "W002": "2020-11-16", "W013": "2021-12-01", "W016": "2022-08-26",
    "W021": "2023-02-07", "W025": "2023-06-14",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if OUT.exists():
        raise FileExistsError(f"preserve output: {OUT}")
    OUT.mkdir()
    pool = pd.read_csv(POOL)
    pool["permno"] = pool.permno.astype(int)
    detail = pd.read_csv(DETAIL)
    detail["permno"] = detail.permno.astype(int)
    e007 = pd.read_csv(E007)
    e007["permno"] = e007.permno.astype(int)
    e007["effective_date_dt"] = pd.to_datetime(e007.effective_date)
    flags = []
    for row in pool.itertuples(index=False):
        anchor = pd.Timestamp(CUTOFF[row.wave_id])
        other = e007[
            e007.permno.eq(row.permno)
            & e007.wave_id.ne(row.wave_id)
            & e007.effective_date_dt.between(
                anchor - pd.DateOffset(months=24), anchor + pd.DateOffset(months=24)
            )
        ]
        flags.append(len(other) == 0)
    pool["proposed_overlap_clean"] = flags
    pool.to_csv(OUT / "full_supported_pool_with_overlap_flag.csv", index=False)

    selected = []
    support_rows = []
    for (wave, tier), group in pool.groupby(["wave_id", "provisional_tier"]):
        clean = group[group.proposed_overlap_clean].copy()
        median = group.median_dollar_volume_candidate.median()
        clean["liquidity_stratum"] = clean.median_dollar_volume_candidate.map(
            lambda value: "LOW_LIQ" if value <= median else "HIGH_LIQ"
        )
        target = min(4, len(clean))
        pieces = []
        for stratum in ["LOW_LIQ", "HIGH_LIQ"]:
            candidates = clean[clean.liquidity_stratum.eq(stratum)].copy()
            ascending = tier.lower() == "low"
            pieces.append(
                candidates.sort_values(["exposure_ownership", "permno"], ascending=[ascending, True]).head(2)
            )
        chosen = pd.concat(pieces).drop_duplicates(["wave_id", "permno"])
        if len(chosen) < target:
            remaining = clean[~clean.permno.isin(set(chosen.permno))]
            ascending = tier.lower() == "low"
            chosen = pd.concat(
                [chosen, remaining.sort_values(["exposure_ownership", "permno"], ascending=[ascending, True]).head(target - len(chosen))]
            )
        chosen = chosen.head(target).copy()
        selected.append(chosen)
        support_rows.append({
            "wave_id": wave,
            "tier": tier.upper(),
            "full_supported": len(group),
            "proposed_overlap_clean": len(clean),
            "selected": len(chosen),
            "diagnostic_liquidity_median": median,
        })
    selected_pool = pd.concat(selected, ignore_index=True)
    roster = selected_pool.merge(detail, on=["wave_id", "permno"], how="left", validate="one_to_one")
    roster["tier"] = roster.provisional_tier.str.upper()
    roster["purpose"] = "MAXIMUM_PROPOSED_OVERLAP_CLEAN_DATA_ACQUISITION_ONLY"
    roster["final_analysis_eligibility"] = "NOT_CERTIFIED"
    roster.to_csv(OUT / "PILOT_STOCKS_CLEAN_MAX23.csv", index=False)
    pd.DataFrame(support_rows).to_csv(OUT / "clean_support_by_wave_tier.csv", index=False)

    existing = pd.read_csv(ROOT / "supported_roster/PILOT_STOCKS_40_SUPPORTED.csv")
    existing["permno"] = existing.permno.astype(int)
    existing["roster_source"] = "ORIGINAL_FIVE_WAVE_ACQUISITION_40"
    clean_detail = roster.copy()
    clean_detail["roster_source"] = "PROPOSED_OVERLAP_CLEAN_MAX23"
    common = sorted(set(existing.columns) & set(clean_detail.columns))
    union = pd.concat([existing[common], clean_detail[common]], ignore_index=True)
    union = union.sort_values(["wave_id", "permno", "roster_source"]).drop_duplicates(["wave_id", "permno"], keep="last")
    union["purpose"] = "UNION_DATA_ACQUISITION_ONLY"
    union["final_analysis_eligibility"] = "NOT_CERTIFIED"
    union.to_csv(OUT / "PILOT_STOCKS_ACQUISITION_UNION.csv", index=False)
    receipt = {
        "status": "MAXIMUM_PROPOSED_OVERLAP_CLEAN_ROSTER_BUILT",
        "clean_selected_rows": len(roster),
        "clean_selected_waves": int(roster.wave_id.nunique()),
        "union_rows": len(union),
        "union_waves": int(union.wave_id.nunique()),
        "zero_clean_waves": sorted(set(CUTOFF) - set(roster.wave_id)),
        "pool_sha256": sha(POOL),
        "detail_sha256": sha(DETAIL),
        "e007_sha256": sha(E007),
        "clean_roster_sha256": sha(OUT / "PILOT_STOCKS_CLEAN_MAX23.csv"),
        "union_roster_sha256": sha(OUT / "PILOT_STOCKS_ACQUISITION_UNION.csv"),
        "rule_status": "PROPOSED_NOT_FINAL_CONTRACT",
        "outcomes_read": False,
    }
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
