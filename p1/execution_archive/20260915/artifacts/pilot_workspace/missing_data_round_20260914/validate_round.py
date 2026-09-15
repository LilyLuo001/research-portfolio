#!/usr/bin/env python3
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def csv_rows(name):
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))

def sha256(name):
    digest = hashlib.sha256()
    with (ROOT / name).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

packages = csv_rows("PACKAGE_INPUTS.csv")
assert {row["wave_id"] for row in packages if row["include_in_equity_package"] == "True"} == {"W002", "W013", "W016", "W021", "W025"}
assert [row for row in packages if row["pre_series_id"] == "S000003492" and row["include_in_equity_package"] == "False"]

selected = csv_rows("SELECTED_PREANNOUNCEMENT_FILINGS.csv")
cutoff = {row["wave_id"]: row["announcement_cutoff"] for row in packages}
assert len({(row["wave_id"], row["pre_series_id"]) for row in selected}) == 12
assert all(row["report_date"] < cutoff[row["wave_id"]] for row in selected)
assert not any(row["pre_series_id"] == "S000003492" for row in selected)

tiers = csv_rows("PREANNOUNCEMENT_EXPOSURE_PROVISIONAL_TIERS.csv")
assert len(tiers) == 4191
assert len({(row["wave_id"], row["permno"]) for row in tiers}) == 4191
assert all(row["primary_ready"] == "True" for row in tiers)
assert all(float(row["exposure_ownership"]) > 0 for row in tiers)

eligibility = csv_rows("EARNINGS_METADATA_ELIGIBILITY.csv")
full = [row for row in eligibility if row["has_8pre_4post"] == "True"]
assert len(full) == 2088
supported = csv_rows("FULL_SUPPORTED_CANDIDATE_POOL.csv")
assert len(supported) == 2088
assert {(row["wave_id"], row["permno"]) for row in supported} == {(row["wave_id"], row["permno"]) for row in full}

summary = csv_rows("EARNINGS_METADATA_WAVE_TIER_SUMMARY.csv")
expected = {
    ("W002", "high"): (775, 595), ("W002", "low"): (762, 559),
    ("W013", "high"): (32, 30), ("W013", "low"): (33, 33),
    ("W016", "high"): (172, 146), ("W016", "low"): (167, 134),
    ("W021", "high"): (13, 13), ("W021", "low"): (13, 13),
    ("W025", "high"): (315, 285), ("W025", "low"): (310, 280),
}
actual = {(row["wave_id"], row["provisional_tier"]): (int(row["tail_candidates"]), int(row["candidates_with_8pre_4post"])) for row in summary}
assert actual == expected

pool_receipt = json.loads((ROOT / "SCC_EARNINGS_POOL_RECEIPT.json").read_text())
assert pool_receipt["candidate_rows_selected_max_8pre_4post"] == 29729
assert pool_receipt["candidates_with_8pre_4post"] == 2088
assert pool_receipt["raw_financial_values_read"] is False
assert pool_receipt["post_quote_outcomes_read"] is False

pool_name = "EARNINGS_METADATA_POOL_8PRE_4POST.csv"
assert sha256(pool_name) == pool_receipt["output_hashes"][pool_name]
pool = csv_rows(pool_name)
assert len(pool) == 29729
assert not ({"actual", "forecast", "surprise", "return", "bid", "ask"} & {column.lower() for column in pool[0]})
assert max(sum(1 for row in pool if row["wave_id"] == wave and row["permno"] == permno and row["event_side"] == side)
           for wave, permno, side in {(row["wave_id"], row["permno"], row["event_side"]) for row in pool}) <= 8
assert max(int(row["within_side_order"]) for row in pool if row["event_side"] == "POST") <= 4

result = {
    "status": "PASS",
    "selected_equity_series": 12,
    "exposure_rows": len(tiers),
    "earnings_metadata_rows": len(pool),
    "full_8pre_4post_candidates": len(full),
    "w021_bond_included": False,
    "raw_financial_values_read": False,
    "post_quote_outcomes_read": False,
    "verified_hashes": {
        pool_name: sha256(pool_name),
        "EARNINGS_METADATA_ELIGIBILITY.csv": sha256("EARNINGS_METADATA_ELIGIBILITY.csv"),
        "FULL_SUPPORTED_CANDIDATE_POOL.csv": sha256("FULL_SUPPORTED_CANDIDATE_POOL.csv"),
        "EARNINGS_METADATA_WAVE_TIER_SUMMARY.csv": sha256("EARNINGS_METADATA_WAVE_TIER_SUMMARY.csv"),
    },
}
(ROOT / "VALIDATION_RECEIPT.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(json.dumps(result, indent=2, sort_keys=True))
