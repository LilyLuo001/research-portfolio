#!/usr/bin/env python3
import pandas as pd
from build_wave_gap_resolution import classify

def row(common, unmatched=0, ambiguous=0, mapping_rows=None, unknown=0, outside=None):
    if mapping_rows is None: mapping_rows = common
    if outside is None: outside = common - unmatched - ambiguous
    return pd.Series({"common_equity_candidates": common, "mapping_rows": mapping_rows,
        "unrecognized_mapping_status_rows": unknown, "unmatched_rows": unmatched,
        "ambiguous_rows": ambiguous, "non_common_rows": outside,
        "non_us_rows": 0, "non_us_non_crsp_rows": 0})

assert classify(row(0))[0].startswith("INTENTIONAL_NO_NPORT")
assert classify(row(5, unmatched=1))[0] == "UNKNOWN_IDENTIFIER_LINK_GAP"
assert classify(row(5, ambiguous=1))[0] == "UNKNOWN_IDENTIFIER_LINK_GAP"
assert classify(row(5))[0].startswith("INTENTIONAL_CANDIDATES_OUTSIDE")
assert classify(row(5, mapping_rows=0))[0] == "UNKNOWN_MAPPING_AUDIT_ROW_COVERAGE_GAP"
assert classify(row(5, unknown=1))[0] == "UNKNOWN_UNRECOGNIZED_MAPPING_STATUS"
print("6 fixtures PASS")
