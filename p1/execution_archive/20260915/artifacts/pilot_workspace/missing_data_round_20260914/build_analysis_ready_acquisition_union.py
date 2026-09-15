#!/usr/bin/env python3
"""Add all scarce clean+12-event-min2 candidates needed for later adjudication."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "analysis_ready_acquisition"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if OUT.exists():
        raise FileExistsError(f"preserve output: {OUT}")
    OUT.mkdir()
    pool_path = ROOT / "clean_acquisition/full_supported_pool_with_overlap_flag.csv"
    analyst_path = ROOT / "full_pool_analyst_coverage/candidate_analyst_coverage.csv"
    detail_path = ROOT / "crsp_attached/stock_wave_candidate_roster.csv"
    union_path = ROOT / "clean_acquisition/PILOT_STOCKS_ACQUISITION_UNION.csv"
    pool = pd.read_csv(pool_path)
    analyst = pd.read_csv(analyst_path)
    detail = pd.read_csv(detail_path)
    union = pd.read_csv(union_path)
    for frame in [pool, analyst, detail, union]:
        frame["permno"] = frame.permno.astype(int)
    candidates = pool.merge(
        analyst[["wave_id", "permno", "provisional_tier", "all_12_events_min2"]],
        on=["wave_id", "permno", "provisional_tier"],
        validate="one_to_one",
    )
    candidates["clean_and_analyst12"] = candidates.proposed_overlap_clean & candidates.all_12_events_min2
    candidates.to_csv(OUT / "full_support_overlap_analyst_intersection.csv", index=False)
    picked = []
    counts = []
    for (wave, tier), group in candidates.groupby(["wave_id", "provisional_tier"]):
        eligible = group[group.clean_and_analyst12].copy()
        median = group.median_dollar_volume_candidate.median()
        eligible["liquidity_stratum"] = eligible.median_dollar_volume_candidate.map(
            lambda value: "LOW_LIQ" if value <= median else "HIGH_LIQ"
        )
        target = min(4, len(eligible))
        pieces = []
        for stratum in ["LOW_LIQ", "HIGH_LIQ"]:
            frame = eligible[eligible.liquidity_stratum.eq(stratum)]
            ascending = tier.lower() == "low"
            pieces.append(frame.sort_values(["exposure_ownership", "permno"], ascending=[ascending, True]).head(2))
        chosen = pd.concat(pieces).drop_duplicates(["wave_id", "permno"])
        if len(chosen) < target:
            remaining = eligible[~eligible.permno.isin(set(chosen.permno))]
            ascending = tier.lower() == "low"
            chosen = pd.concat(
                [chosen, remaining.sort_values(["exposure_ownership", "permno"], ascending=[ascending, True]).head(target - len(chosen))]
            )
        picked.append(chosen.head(target))
        counts.append({
            "wave_id": wave,
            "tier": tier.upper(),
            "full_supported": len(group),
            "clean_and_all12_min2": len(eligible),
            "selected_for_acquisition": min(target, len(chosen)),
        })
    picked = pd.concat(picked, ignore_index=True)
    picked_detail = picked.merge(detail, on=["wave_id", "permno"], validate="one_to_one")
    picked_detail["tier"] = picked_detail.provisional_tier.str.upper()
    picked_detail["roster_source"] = "CLEAN_AND_ALL12_MIN2_MAX15"
    picked_detail["purpose"] = "ANALYSIS_SUPPORT_DATA_ACQUISITION_ONLY"
    picked_detail["final_analysis_eligibility"] = "NOT_CERTIFIED"
    picked_detail.to_csv(OUT / "PILOT_STOCKS_CLEAN_ANALYST_MAX15.csv", index=False)
    pd.DataFrame(counts).to_csv(OUT / "intersection_support_by_wave_tier.csv", index=False)

    union["roster_source"] = union.roster_source.fillna("PRIOR_ACQUISITION_UNION")
    common = sorted(set(union.columns) & set(picked_detail.columns))
    combined = pd.concat([union[common], picked_detail[common]], ignore_index=True)
    combined = combined.sort_values(["wave_id", "permno", "roster_source"]).drop_duplicates(["wave_id", "permno"], keep="last")
    combined["purpose"] = "FINAL_DATA_ACQUISITION_UNION_ONLY"
    combined["final_analysis_eligibility"] = "NOT_CERTIFIED"
    combined.to_csv(OUT / "PILOT_STOCKS_ACQUISITION_UNION_V2.csv", index=False)
    receipt = {
        "status": "ANALYSIS_SUPPORT_ACQUISITION_UNION_BUILT",
        "clean_all12_min2_selected_rows": len(picked_detail),
        "clean_all12_min2_selected_waves": int(picked_detail.wave_id.nunique()),
        "union_v2_rows": len(combined),
        "union_v2_waves": int(combined.wave_id.nunique()),
        "zero_clean_all12_min2_waves": sorted(set(pool.wave_id) - set(picked_detail.wave_id)),
        "input_hashes": {
            "pool": sha(pool_path), "analyst": sha(analyst_path),
            "detail": sha(detail_path), "prior_union": sha(union_path),
        },
        "selected_sha256": sha(OUT / "PILOT_STOCKS_CLEAN_ANALYST_MAX15.csv"),
        "union_v2_sha256": sha(OUT / "PILOT_STOCKS_ACQUISITION_UNION_V2.csv"),
        "rule_status": "PROPOSED_NOT_FINAL_CONTRACT",
        "outcomes_read": False,
    }
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
