#!/usr/bin/env python3
"""Static seal checks; does not read response data."""
from pathlib import Path

text = (Path(__file__).parent / "build_replication_response.py").read_text()
assert 'filters=[("date", "in", required_iso), ("permco", "in", receiver_list)]' in text
assert 'filters=[("dlstdt", "in", required_iso), ("permno", "in", selected_permnos)]' in text
assert 'columns=["permno", "permco", "date", "prc", "shrout"]' in text
assert 'verify_opening_gate(stage, bound)' in text
assert text.index('verify_opening_gate(stage, bound)') < text.index('columns=["permno", "permco", "date", "ret"]')
print("response source predicates and pre-read opening guard: PASS")
