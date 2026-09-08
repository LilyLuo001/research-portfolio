from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "build_design_audit.py"
SPEC = importlib.util.spec_from_file_location("build_design_audit", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class BuildDesignAuditTests(unittest.TestCase):
    def test_incomplete_grade_b_vector_never_gets_information_n(self) -> None:
        events = [
            {
                "event_id": "SS_TECH_2024Q1_REGULAR",
                "event_group_id": "G1",
                "index_family": "Select Sector",
                "event_type": "regular",
                "evidence_grade": "B",
            }
        ]
        doses = [
            {
                "event_id": "SS_TECH_2024Q1_REGULAR",
                "evidence_grade": "B",
                "vector_complete": "no",
                "rebalance_change_weight_pct": "-2.0",
            }
        ]
        row = MODULE.build_comparison_rows(events, doses)[0]
        self.assertEqual(row["dose_information_n"], "")
        self.assertEqual(row["status"], "EVENT_DOCUMENTED_DOSE_INCOMPLETE")

    def test_information_n_only_for_complete_grade_a_vector(self) -> None:
        events = [{"event_id": "E1", "evidence_grade": "A"}]
        doses = [
            {
                "event_id": "E1",
                "evidence_grade": "A",
                "vector_complete": "yes",
                "rebalance_change_weight_pct": "1",
            },
            {
                "event_id": "E1",
                "evidence_grade": "A",
                "vector_complete": "yes",
                "rebalance_change_weight_pct": "-1",
            },
        ]
        row = MODULE.build_comparison_rows(events, doses)[0]
        self.assertEqual(row["dose_information_n"], "2")
        self.assertEqual(row["status"], "ELIGIBLE_EXACT_DOSE_SUPPORT_AUDIT")


if __name__ == "__main__":
    unittest.main()
