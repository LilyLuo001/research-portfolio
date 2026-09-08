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

    def test_nonbinding_and_other_intervention_are_not_assignment_unknown(self) -> None:
        events = [
            {
                "event_id": "NONBINDING",
                "binding_status": "confirmed_nonbinding",
                "assignment_evidence_grade": "U",
            },
            {
                "event_id": "OTHER",
                "binding_status": "confirmed_other_intervention",
                "assignment_evidence_grade": "B",
            },
        ]
        rows = {row["event_id"]: row for row in MODULE.build_comparison_rows(events, [])}
        self.assertEqual(rows["NONBINDING"]["status"], "CONFIRMED_NONBINDING_CONTEXT")
        self.assertEqual(
            rows["OTHER"]["status"],
            "OTHER_INTERVENTION_CONTEXT_NOT_CANDIDATE_TREATMENT",
        )

    def test_stage_a_gap_blockers_are_explicit_booleans(self) -> None:
        rows = MODULE.build_gap_rows(
            [],
            [],
            [],
            [
                {
                    "evidence_key": "GAPA:provider_issuer_float_mapping",
                    "gap_id": "provider_issuer_float_mapping",
                    "status": "MISSING_LOCAL_INPUT",
                },
                {
                    "evidence_key": "GAPA:holdings_snapshot_gaps",
                    "gap_id": "holdings_snapshot_gaps",
                    "status": "OBSERVED_COVERAGE_GAPS",
                },
            ],
        )
        imported = {row["gap_id"]: row for row in rows if row["stage"] == "A"}
        self.assertEqual(
            imported["STAGE_A_provider_issuer_float_mapping"][
                "blocks_gate1_assignment"
            ],
            "yes",
        )
        self.assertEqual(
            imported["STAGE_A_holdings_snapshot_gaps"]["blocks_future_measurement"],
            "no",
        )
        for row in imported.values():
            self.assertIn(row["blocks_gate1_assignment"], {"yes", "no"})
            self.assertIn(row["blocks_future_measurement"], {"yes", "no"})

    def test_unadjudicated_stage_a_gap_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "no explicit blocker adjudication"):
            MODULE.build_gap_rows(
                [],
                [],
                [],
                [{"gap_id": "new_unreviewed_gap", "status": "OPEN"}],
            )


if __name__ == "__main__":
    unittest.main()
