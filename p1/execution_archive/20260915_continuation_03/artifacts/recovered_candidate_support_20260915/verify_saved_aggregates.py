"""Read-only coordinator verification; no SCC, source scan, or outcomes."""
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
receipt = json.loads((root / "full_artifacts/receipt.json").read_text())
execution = json.loads((root / "EXECUTION_RECEIPT.json").read_text())
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def table(name):
    with (root / "full_artifacts" / name).open() as f:
        return list(csv.DictReader(f))
def total(rows, field):
    return sum(int(r[field]) for r in rows)
for name, expected in receipt["aggregate_hashes"].items():
    assert digest(root / "full_artifacts" / name) == expected, name
for name, field in [("run_recovered_support.py", "code_sha256"),
                    ("config.json", "config_sha256"),
                    ("source_manifest.json", "manifest_sha256")]:
    assert digest(root / name) == receipt[field], name
clock = table("candidate_clock_support_by_wave_tier.csv")
analyst = table("candidate_analyst_support_by_wave_tier.csv")
coverage = table("analyst_coverage_by_wave_tier_side_clock.csv")
keys = table("source_key_support_by_wave_tier_side.csv")
assert total(clock, "recovered_candidate_stock_wave_keys") == 99
assert total(clock, "all_clock_both_pre_post_candidate_keys") == 27
assert total(clock, "nominal_source_clock_both_pre_post_candidate_keys") == 2
assert total(analyst, "all_clock_observed_min2_both_pre_post_candidate_keys") == 19
assert total(analyst, "nominal_source_clock_observed_min2_both_pre_post_candidate_keys") == 0
assert total(coverage, "exact_analyst_event_keys") == 1151
assert total(coverage, "observed_source_min2_event_keys") == 525
assert total(coverage, "unknown_event_keys") == 626
nominal = [r for r in coverage if r["nominal_0930_1500_source_clock"] == "True"]
assert total(nominal, "exact_analyst_event_keys") == 35
assert total(nominal, "observed_source_min2_event_keys") == 1
assert total(keys, "source_path_rows") == 1151
for row in clock:
    assert 0 <= int(row["nominal_source_clock_both_pre_post_candidate_keys"]) <= int(row["all_clock_both_pre_post_candidate_keys"]) <= int(row["recovered_candidate_stock_wave_keys"])
assert execution["counts"]["distinct_source_rows"] == receipt["distinct_source_rows"] == 1124
subprocess.run([sys.executable, "-B", str(root / "test_recovered_support.py")], check=True, cwd=root)
print(json.dumps({"status": "SAVED_AGGREGATES_AND_NINE_FIXTURES_PASS", "source_row_independent_reproduction": "NOT_RUN_BY_COORDINATOR", "aggregate_files_hash_verified": len(receipt["aggregate_hashes"]), "source_clock_certified": False, "competing_conversion_eligibility": "UNKNOWN", "note": "Receipt invariants include declarative assertions; this check verifies saved aggregate arithmetic and the executable nine fixtures, not all source-level invariants."}))
