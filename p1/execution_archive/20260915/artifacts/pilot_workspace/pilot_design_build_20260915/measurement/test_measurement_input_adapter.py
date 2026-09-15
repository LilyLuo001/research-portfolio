import unittest
import csv
import subprocess
import sys
import tempfile
from pathlib import Path

from measurement_input_adapter import classify


class ClockSessionClassifierTests(unittest.TestCase):
    CALENDAR = {("XNYS", "2024-05-01"): {"calendar_id": "XNYS", "session_date": "2024-05-01", "calendar_timezone": "America/New_York", "open_local": "09:30:00", "close_local": "16:00:00"}}

    def row(self, **override):
        value = {"association_id": "synthetic", "source_id": "fixture", "source_timezone": "America/New_York", "interval_lower": "2024-05-01T10:00:00", "interval_upper": "2024-05-01T10:00:30", "calendar_id": "XNYS"}
        value.update(override); return value

    def test_definitive_rth60_needs_all_provenance(self):
        self.assertEqual(classify(self.row(), self.CALENDAR)["classification"], "DEFINITIVE_RTH_60_ELIGIBLE")

    def test_missing_timezone_is_unknown_not_et(self):
        self.assertEqual(classify(self.row(source_timezone=""), self.CALENDAR)["classification"], "UNKNOWN")

    def test_missing_source_id_is_unknown(self):
        self.assertEqual(classify(self.row(source_id=""), self.CALENDAR)["classification"], "UNKNOWN")

    def test_crossing_cutoff_is_unknown(self):
        actual = classify(self.row(interval_lower="2024-05-01T14:59:50", interval_upper="2024-05-01T15:00:10"), self.CALENDAR)
        self.assertEqual(actual["classification"], "UNKNOWN")

    def test_cutoff_equality_is_eligible(self):
        actual = classify(self.row(interval_lower="2024-05-01T14:59:00", interval_upper="2024-05-01T15:00:00"), self.CALENDAR)
        self.assertEqual(actual["classification"], "DEFINITIVE_RTH_60_ELIGIBLE")

    def test_crossing_open_is_unknown(self):
        actual = classify(self.row(interval_lower="2024-05-01T09:29:59", interval_upper="2024-05-01T09:30:01"), self.CALENDAR)
        self.assertEqual(actual["classification"], "UNKNOWN")

    def test_utc_source_converts_to_calendar_timezone(self):
        actual = classify(self.row(source_timezone="UTC", interval_lower="2024-05-01T14:00:00+00:00", interval_upper="2024-05-01T14:00:30+00:00"), self.CALENDAR)
        self.assertEqual(actual["classification"], "DEFINITIVE_RTH_60_ELIGIBLE")

    def test_after_cutoff_is_definitive_noneligible(self):
        actual = classify(self.row(interval_lower="2024-05-01T15:05:00", interval_upper="2024-05-01T15:10:00"), self.CALENDAR)
        self.assertEqual(actual["classification"], "DEFINITIVE_RTH_BUT_NOT_RTH_60")

    def test_outside_session_is_definitive_nonrth(self):
        actual = classify(self.row(interval_lower="2024-05-01T16:00:00", interval_upper="2024-05-01T16:00:10"), self.CALENDAR)
        self.assertEqual(actual["classification"], "DEFINITIVE_NON_RTH")

    def test_crossing_close_is_unknown(self):
        actual = classify(self.row(interval_lower="2024-05-01T15:59:59", interval_upper="2024-05-01T16:00:01"), self.CALENDAR)
        self.assertEqual(actual["classification"], "UNKNOWN")

    def test_missing_calendar_is_unknown(self):
        self.assertEqual(classify(self.row(calendar_id="NOPE"), self.CALENDAR)["classification"], "UNKNOWN")

    def test_multiple_dates_are_not_definitive_afterclose(self):
        result = classify(self.row(interval_lower='2024-05-01T17:00:00', interval_upper='2024-05-02T11:00:00'), self.CALENDAR)
        self.assertEqual(result['classification'], 'UNKNOWN')

    def test_conflicting_calendar_zones_are_unknown(self):
        second = dict(next(iter(self.CALENDAR.values())), session_date='2024-05-02', calendar_timezone='UTC')
        calendar = dict(self.CALENDAR)
        calendar[('XNYS','2024-05-02')] = second
        self.assertEqual(classify(self.row(), calendar)['classification'], 'UNKNOWN')

    def test_ambiguous_dst_naive_time_is_unknown(self):
        self.assertEqual(classify(self.row(interval_lower='2024-11-03T01:30:00', interval_upper='2024-11-03T01:31:00'), self.CALENDAR)['classification'], 'UNKNOWN')

    def test_nonexistent_dst_naive_time_is_unknown(self):
        self.assertEqual(classify(self.row(interval_lower='2024-03-10T02:30:00', interval_upper='2024-03-10T02:31:00'), self.CALENDAR)['classification'], 'UNKNOWN')

    def test_missing_interval_and_duplicate_calendar_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def put(name, fields, rows):
                with (root / name).open("w", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
            event = {"association_id":"one", "wave_id":"w", "permno":"1", "sample_period":"PRE", "announcement_date":"2024-05-01", "announcement_times_all":"10:00", "mapping_status":"x", "date_valid_raw_symbol":"X", "date_valid_ncusip":"Y", "pends":"", "tier":"", "liquidity_stratum":"", "analyst_count_90d":"", "sue_analyst_min2_coverage":""}
            put("events.csv", list(event), [event])
            put("gaps.csv", ["association_id","sample_period","symbol_role","leg","job_id","symbol","file_status","mapping_status"], [])
            put("intervals.csv", ["association_id","source_id","source_timezone","interval_lower","interval_upper","calendar_id"], [])
            cal = {"calendar_id":"XNYS","session_date":"2024-05-01","calendar_timezone":"America/New_York","open_local":"09:30:00","close_local":"16:00:00"}
            put("calendar.csv", list(cal), [cal])
            command = [sys.executable, "measurement_input_adapter.py", "--events", str(root/"events.csv"), "--mapping-gaps", str(root/"gaps.csv"), "--intervals", str(root/"intervals.csv"), "--calendar", str(root/"calendar.csv"), "--outdir", str(root/"out")]
            subprocess.run(command, check=True, cwd=Path(__file__).parent)
            with (root/"out"/"clock_session_census.csv").open() as f: self.assertEqual(next(csv.DictReader(f))["reason"], "MISSING_INTERVAL_PROJECTION")
            put("calendar.csv", list(cal), [cal, cal])
            self.assertNotEqual(subprocess.run(command, cwd=Path(__file__).parent, capture_output=True).returncode, 0)


if __name__ == "__main__":
    unittest.main()
