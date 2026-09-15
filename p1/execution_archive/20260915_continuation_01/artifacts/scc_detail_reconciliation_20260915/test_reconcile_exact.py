"""Execute the saved script against synthetic in-memory I/O, never SCC data."""
import contextlib
import io
import json
from pathlib import Path
import runpy
import sys
import types
import unittest
from unittest.mock import patch
import pandas as pd

SCRIPT = Path(__file__).with_name("reconcile_exact.py")
RELEASES = ["2020-02-14", "2020-05-14", "2020-08-14", "2020-11-14"]
PERIODS = ["2019-12-31", "2020-03-31", "2020-06-30", "2020-09-30"]

def execute_synthetic(specs, ambiguous=False):
    targets = pd.DataFrame([
        dict(wave_id="W002", provisional_tier="high", permno="1", candidate_id="SYNTHETIC",
             event_side="PRE" if i < 3 else "POST", pends=period, anndats=release,
             cusip="TEST0001", overlap_status="PROPOSED_CLEAN_TRUE",
             source_permno_mapping_status="UNIQUE_VALID_PERMNO", nominal_0930_1500_source_clock="True")
        for i, (period, release) in enumerate(zip(PERIODS, RELEASES))])
    if ambiguous:
        extra = targets.iloc[[0]].copy(); extra["cusip"] = "TEST0002"
        targets = pd.concat([targets, extra], ignore_index=True)
    rows = []
    for period, release in zip(PERIODS, RELEASES):
        for analyst, offset, wrong_period in specs:
            rows.append(dict(cusip="TEST0001", fpedats=pd.Timestamp(period) + pd.Timedelta(days=int(wrong_period)),
                             analys=analyst, anndats=pd.Timestamp(release) + pd.Timedelta(days=offset)))
    forecasts = pd.DataFrame(rows, columns=["cusip", "fpedats", "analys", "anndats"])
    def read_table(path, columns):
        assert columns == ["cusip", "fpedats", "analys", "anndats"]
        year = int(Path(path).stem.split("_")[-1])
        selected = forecasts[pd.to_datetime(forecasts.anndats).dt.year.eq(year)].copy()
        return types.SimpleNamespace(to_pandas=lambda: selected)
    output = io.StringIO()
    fake_arrow = types.ModuleType("pyarrow"); fake_arrow.__version__ = "0.0.0"
    fake_parquet = types.ModuleType("pyarrow.parquet"); fake_parquet.read_table = read_table
    fake_arrow.parquet = fake_parquet
    with patch("pandas.read_csv", return_value=targets), patch.dict(sys.modules, {"pyarrow": fake_arrow, "pyarrow.parquet": fake_parquet}), contextlib.redirect_stdout(output):
        runpy.run_path(str(SCRIPT))
    return json.loads(output.getvalue())

class ReconciliationTests(unittest.TestCase):
    def assert_counts(self, specs, expected):
        result = execute_synthetic(specs)
        for family in ("core", "rescue"):
            self.assertEqual(result["sources"][family]["distinct_analyst_histogram"], {str(expected): 4})

    def test_minus90_inclusive(self): self.assert_counts([(1, -90, False)], 1)
    def test_release_exclusive(self): self.assert_counts([(1, 0, False)], 0)
    def test_before_window_excluded(self): self.assert_counts([(1, -91, False)], 0)
    def test_duplicate_analyst_not_new_information(self): self.assert_counts([(1, -90, False), (1, -1, False)], 1)
    def test_null_analyst_ignored(self): self.assert_counts([(None, -1, False)], 0)
    def test_period_mismatch_excluded(self): self.assert_counts([(1, -1, True)], 0)
    def test_ambiguous_cusip_rejected(self):
        with self.assertRaises(AssertionError): execute_synthetic([(1, -1, False)], ambiguous=True)

if __name__ == "__main__": unittest.main()
