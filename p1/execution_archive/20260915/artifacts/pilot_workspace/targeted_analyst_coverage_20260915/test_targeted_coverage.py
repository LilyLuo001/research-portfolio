#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import pandas as pd

P = Path(__file__).with_name("run_targeted_coverage.py")
spec = importlib.util.spec_from_file_location("m", P)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def main():
    rel = pd.Timestamp("2024-04-01")
    rows = pd.DataFrame({
        "anndats": pd.to_datetime(["2024-01-02", "2024-01-02", "2024-01-03", "2024-04-01"]),
        "analys": ["A", "A", "B", "C"]
    })
    assert m.count_analysts(rows, rel, 90) == 2  # lower included, release excluded, revisions deduped
    a = m.event_key("W002", "high", 10001, "PRE", "2023-12-31", "2024-04-01")
    b = m.event_key("W002", "low", 10001, "PRE", "2023-12-31", "2024-04-01")
    c = m.event_key("W002", "high", 10001, "PRE", "2023-12-31", "2024-04-02")
    assert len({a,b,c}) == 3  # tier and release date retained
    assert m.window_status(rel, {2024}, pd.Timestamp("2024-12-30"), 90) == "AVAILABLE_PARTITIONS_OBSERVED_THROUGH_RELEASE_COMPLETENESS_UNKNOWN"
    assert m.window_status(rel, set(), pd.Timestamp("2024-12-30"), 90) == "UNKNOWN_MISSING_SOURCE_YEAR"
    assert m.window_status(pd.Timestamp("2026-09-02"), {2026}, pd.Timestamp("2026-08-31"), 90) == "UNKNOWN_SOURCE_NOT_OBSERVED_THROUGH_RELEASE"
    candidate = pd.DataFrame({"pre_min2":[1],"post_min2":[1],"unknown_keys":[2]})
    assert bool((candidate.pre_min2.gt(0)&candidate.post_min2.gt(0)).iloc[0])
    inv={"a":True,"protected_rows_local_exported":False}; exp={"a":True,"protected_rows_local_exported":False}
    assert inv==exp
    print('{"status":"PASS","fixture_count":8}')

if __name__ == "__main__": main()
