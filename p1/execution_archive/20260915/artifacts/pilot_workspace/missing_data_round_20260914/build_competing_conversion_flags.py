#!/usr/bin/env python3
"""Attach proposed +/-24-month competing-conversion flags to acquisition roster."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
ROSTER = ROOT / "supported_roster/PILOT_STOCKS_40_SUPPORTED.csv"
E007 = Path("/Users/lilyluo/research-portfolio-p1-advanced-readonly/p1/exposure/exposure_stock_wave_all.csv")
OUT = ROOT / "competing_conversion"
EXPECTED_ROSTER = "eeb3ab2f522fc611dc614aceed79b95c2e9ccb772fec11f6fa1db5d6c29323be"
EXPECTED_E007 = "905b7faa844a3a415f5b6c42d0e8de4c1fa28060efe16370182ef86df20b7320"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if sha(ROSTER) != EXPECTED_ROSTER or sha(E007) != EXPECTED_E007:
        raise ValueError("input hash mismatch")
    if OUT.exists():
        raise FileExistsError(f"preserve output: {OUT}")
    OUT.mkdir()
    roster = pd.read_csv(ROSTER)
    roster["permno"] = roster.permno.astype(int)
    roster["announcement_cutoff_dt"] = pd.to_datetime(roster.announcement_cutoff)
    e007 = pd.read_csv(E007)
    e007["permno"] = e007.permno.astype(int)
    e007["effective_date_dt"] = pd.to_datetime(e007.effective_date)
    rows = []
    for row in roster.itertuples(index=False):
        lo = row.announcement_cutoff_dt - pd.DateOffset(months=24)
        hi = row.announcement_cutoff_dt + pd.DateOffset(months=24)
        other = e007[
            e007.permno.eq(row.permno)
            & e007.wave_id.ne(row.wave_id)
            & e007.effective_date_dt.between(lo, hi)
        ].copy()
        rows.append({
            "permno": row.permno,
            "wave_id": row.wave_id,
            "historical_ticker": row.historical_ticker,
            "announcement_cutoff": row.announcement_cutoff,
            "overlap_window_start": lo.strftime("%Y-%m-%d"),
            "overlap_window_end": hi.strftime("%Y-%m-%d"),
            "other_conversion_count": len(other),
            "other_wave_ids": ";".join(sorted(set(other.wave_id))),
            "other_effective_dates": ";".join(sorted(set(other.effective_date))),
            "proposed_competing_conversion_exclusion": len(other) > 0,
            "rule_status": "PROPOSED_NOT_FINAL_CONTRACT",
        })
    flags = pd.DataFrame(rows)
    flags.to_csv(OUT / "supported_roster_overlap_flags.csv", index=False)
    summary = flags.groupby("wave_id").agg(
        roster_rows=("permno", "size"),
        flagged=("proposed_competing_conversion_exclusion", "sum"),
    ).reset_index()
    summary["clean"] = summary.roster_rows - summary.flagged
    summary.to_csv(OUT / "overlap_summary_by_wave.csv", index=False)
    receipt = {
        "status": "PROPOSED_COMPETING_CONVERSION_FLAGS_BUILT",
        "roster_rows": len(flags),
        "flagged": int(flags.proposed_competing_conversion_exclusion.sum()),
        "clean": int((~flags.proposed_competing_conversion_exclusion).sum()),
        "roster_sha256": sha(ROSTER),
        "e007_sha256": sha(E007),
        "flags_sha256": sha(OUT / "supported_roster_overlap_flags.csv"),
        "summary_sha256": sha(OUT / "overlap_summary_by_wave.csv"),
        "rule_status": "PROPOSED_NOT_FINAL_CONTRACT",
        "outcomes_read": False,
    }
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
