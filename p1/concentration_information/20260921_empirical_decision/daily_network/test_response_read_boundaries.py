#!/usr/bin/env python3
"""Static audit that every return-bearing parquet read has an H1 predicate."""
from pathlib import Path

text=(Path(__file__).parent/"run_daily_network.py").read_text()
assert 'filters = [("date", "==", "2022-12-30")] if key == "dsf2022" else [("date", ">=", "2023-01-01"), ("date", "<=", "2023-06-30")]' in text
assert 'filters=[("dlstdt", ">=", "2023-01-01"), ("dlstdt", "<=", "2023-06-30")]' in text
print("response-bearing source-read predicates: PASS")
