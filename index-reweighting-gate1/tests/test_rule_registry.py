from __future__ import annotations

import csv
import importlib.util
import math
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "build_rule_registry.py"
SPEC = importlib.util.spec_from_file_location("build_rule_registry", MODULE_PATH)
assert SPEC and SPEC.loader
registry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(registry)


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


class RuleRegistryBuilderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory()
        cls.output = Path(cls.temp.name)
        registry.write_csv(cls.output / "source_and_rule_registry.csv", registry.SOURCE_HEADERS, registry.build_source_registry())
        registry.write_csv(cls.output / "rebalance_event_ledger.csv", registry.EVENT_HEADERS, registry.build_event_ledger())
        registry.write_csv(cls.output / "assignment_doses_and_evidence.csv", registry.DOSE_HEADERS, registry.build_assignment_doses())
        cls.source_headers, cls.sources = read_csv(cls.output / "source_and_rule_registry.csv")
        cls.event_headers, cls.events = read_csv(cls.output / "rebalance_event_ledger.csv")
        cls.dose_headers, cls.doses = read_csv(cls.output / "assignment_doses_and_evidence.csv")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def test_exact_headers_and_lf_newlines(self) -> None:
        self.assertEqual(self.source_headers, registry.SOURCE_HEADERS)
        self.assertEqual(self.event_headers, registry.EVENT_HEADERS)
        self.assertEqual(self.dose_headers, registry.DOSE_HEADERS)
        for filename in (
            "source_and_rule_registry.csv",
            "rebalance_event_ledger.csv",
            "assignment_doses_and_evidence.csv",
        ):
            payload = (self.output / filename).read_bytes()
            self.assertNotIn(b"\r", payload)
            self.assertTrue(payload.endswith(b"\n"))

    def test_stable_unique_evidence_keys(self) -> None:
        for rows, prefix in ((self.sources, "RULE:"), (self.events, "EVENT:"), (self.doses, "DOSE:")):
            keys = [row["evidence_key"] for row in rows]
            self.assertTrue(all(key.startswith(prefix) for key in keys))
            self.assertEqual(len(keys), len(set(keys)))
        for row in self.sources:
            self.assertEqual(row["evidence_key"], f"RULE:{row['rule_id']}")
        for row in self.events:
            self.assertEqual(row["evidence_key"], f"EVENT:{row['event_id']}")
        for row in self.doses:
            self.assertEqual(row["evidence_key"], f"DOSE:{row['event_id']}:{row['security_or_all']}")

    def test_public_source_lineage_and_retrieval_date(self) -> None:
        permitted = (
            "https://www.spglobal.com/",
            "https://indexes.nasdaq",
            "https://www.nasdaq.com/",
            "https://ir.nasdaq.com/",
            "https://www.sec.gov/",
        )
        source_ids = {row["source_id"] for row in self.sources}
        for rows in (self.sources, self.events, self.doses):
            for row in rows:
                self.assertEqual(row["retrieval_date"], "2026-09-08")
                self.assertTrue(row["source_url"].startswith(permitted), row["source_url"])
        for row in self.sources:
            self.assertIn(row["rule_source_grade"], {"A", "B", "C", "U"})
            self.assertIn("never assignment", row["grade_dimension"])
        for row in self.events:
            self.assertIn(row["classification_evidence_grade"], {"A", "B", "C", "U"})
            self.assertIn(row["assignment_evidence_grade"], {"A", "B", "C", "U"})
        for row in self.doses:
            self.assertIn(row["evidence_grade"], {"A", "B", "C", "U"})
            self.assertEqual(row["grade_dimension"], "assignment evidence")
        for row in self.events:
            self.assertIn(row["source_id"], source_ids)
        for row in self.doses:
            self.assertIn(row["source_id"], source_ids)
            for field in ("uncapped_source_id", "assignment_source_id", "etf_holdings_source_id", "creation_basket_source_id"):
                if row[field]:
                    self.assertIn(row[field], source_ids)

    def test_complete_bounded_calendar_and_pilot_ids(self) -> None:
        # 34 quarters x 11 sectors x (regular + secondary), 34 NDX routine
        # quarters, one S&P common transition, one NDX special, and one
        # separately documented constituent-replacement interference event.
        self.assertEqual(len(self.events), 785)
        event_ids = {row["event_id"] for row in self.events}
        pilots = {
            "SS_TECH_2024Q1_REGULAR",
            "SS_TECH_2024Q2_REGULAR",
            "SS_ALL_2024Q3_RULE_TRANSITION",
            "NDX_2023_07_SPECIAL",
            "NDX_2023_07_17_TTD_ATVI_REPLACEMENT",
        }
        self.assertTrue(pilots.issubset(event_ids))
        self.assertTrue({row["event_id"] for row in self.doses}.issubset(event_ids))

    def test_exact_pilot_stage_dates(self) -> None:
        by_id = {row["event_id"]: row for row in self.events}
        expected = {
            "SS_TECH_2024Q1_REGULAR": ("2024-03-08", "", "", "2024-03-15", "2024-03-18"),
            "SS_TECH_2024Q2_REGULAR": ("2024-06-14", "", "", "2024-06-21", "2024-06-24"),
            "SS_ALL_2024Q3_RULE_TRANSITION": ("2024-09-13", "2024-09-03", "2024-09-13", "2024-09-20", "2024-09-23"),
            "NDX_2023_07_SPECIAL": ("2023-07-03", "2023-07-07", "2023-07-14", "2023-07-21", "2023-07-24"),
        }
        fields = (
            "input_reference_date",
            "earliest_public_announcement_date",
            "pro_forma_available_date",
            "implementation_close_date",
            "effective_open_date",
        )
        for event_id, values in expected.items():
            self.assertEqual(tuple(by_id[event_id][field] for field in fields), values)

    def test_transition_is_one_common_policy_event(self) -> None:
        transition_rows = [row for row in self.events if row["event_type"] == "methodology_change"]
        self.assertEqual([row["event_id"] for row in transition_rows], ["SS_ALL_2024Q3_RULE_TRANSITION"])
        q3_regular = [row for row in self.events if row["event_id"].startswith("SS_") and row["event_id"].endswith("2024Q3_REGULAR")]
        self.assertEqual(len(q3_regular), 11)
        self.assertEqual({row["event_group_id"] for row in q3_regular}, {"SS_2024Q3_COMMON_RULE_TRANSITION"})
        transition_doses = [row for row in self.doses if row["event_id"] == "SS_ALL_2024Q3_RULE_TRANSITION"]
        self.assertEqual(len(transition_doses), 1)
        self.assertEqual(transition_doses[0]["security_or_all"], "ALL")

    def test_sector_reorganization_is_not_backcast(self) -> None:
        by_id = {row["event_id"]: row for row in self.events}
        for quarter in (1, 2):
            for suffix in ("REGULAR", "SECONDARY_CHECK"):
                row = by_id[f"SS_COMMS_2018Q{quarter}_{suffix}"]
                self.assertEqual(row["binding_status"], "outside_applicable_regime")
                self.assertEqual(row["status"], "OUTSIDE_APPLICABLE_REGIME")
        self.assertNotEqual(by_id["SS_COMMS_2018Q3_REGULAR"]["binding_status"], "outside_applicable_regime")

    def test_secondary_checks_are_separate_and_conservative(self) -> None:
        by_id = {row["event_id"]: row for row in self.events}
        # Rounded displays that clearly cross a threshold.
        self.assertEqual(by_id["SS_TECH_2020Q4_SECONDARY_CHECK"]["binding_status"], "confirmed_binding")
        self.assertEqual(by_id["SS_MATERIAL_2024Q2_SECONDARY_CHECK"]["binding_status"], "confirmed_binding")
        # Rounded boundary display remains unknown.
        self.assertEqual(by_id["SS_TECH_2020Q3_SECONDARY_CHECK"]["binding_status"], "uncertain")
        self.assertEqual(by_id["SS_CONS_DISC_2021Q2_SECONDARY_CHECK"]["binding_status"], "uncertain")
        # S2 explicitly says omitted sectors did not trigger over its appendix window.
        self.assertEqual(by_id["SS_FINANCIAL_2022Q2_SECONDARY_CHECK"]["binding_status"], "confirmed_nonbinding")
        # A nonbinding check has no fabricated implementation or adjustment date.
        row = by_id["SS_FINANCIAL_2022Q2_SECONDARY_CHECK"]
        self.assertEqual(row["implementation_close_date"], "")
        self.assertEqual(row["secondary_adjustment_date"], "")

    def test_four_portfolio_objects_remain_distinct(self) -> None:
        for row in self.doses:
            self.assertEqual(row["etf_holding_weight_pct"], "")
            self.assertEqual(row["creation_basket_weight_pct"], "")
            self.assertEqual(row["etf_holdings_status"], "not_observed_not_substituted")
            self.assertEqual(row["creation_basket_status"], "not_observed_not_substituted")
            self.assertEqual(row["vector_complete"], "false")
            self.assertEqual(row["rebalance_change_weight_pct"], "")

    def test_selected_weight_arithmetic_and_precision(self) -> None:
        selected = [row for row in self.doses if row["security_or_all"] != "ALL"]
        self.assertEqual(len(selected), 30)
        for row in selected:
            self.assertEqual(row["evidence_grade"], "B")
            self.assertEqual(row["numeric_precision_pct"], "0.1")
            uncapped = float(row["uncapped_reference_weight_pct"])
            assigned = float(row["rule_assigned_weight_pct"])
            distortion = float(row["cap_distortion_pct"])
            self.assertTrue(math.isclose(distortion, assigned - uncapped, abs_tol=1e-9))
        nvda_march = next(row for row in selected if row["event_id"] == "SS_TECH_2024Q1_REGULAR" and row["ticker"] == "NVDA")
        apple_june = next(row for row in selected if row["event_id"] == "SS_TECH_2024Q2_REGULAR" and row["ticker"] == "AAPL")
        self.assertEqual((nvda_march["uncapped_reference_weight_pct"], nvda_march["rule_assigned_weight_pct"], nvda_march["cap_distortion_pct"]), ("16.8", "4.5", "-12.3"))
        self.assertEqual((apple_june["uncapped_reference_weight_pct"], apple_june["rule_assigned_weight_pct"], apple_june["cap_distortion_pct"]), ("20.4", "4.5", "-15.9"))

    def test_no_false_grade_a_assignment_or_silent_renormalization(self) -> None:
        self.assertFalse(any(row["evidence_grade"] == "A" for row in self.doses))
        for event_id in ("SS_TECH_2024Q1_REGULAR", "SS_TECH_2024Q2_REGULAR"):
            rows = [row for row in self.doses if row["event_id"] == event_id]
            all_row = next(row for row in rows if row["security_or_all"] == "ALL")
            self.assertIn("never renormalized", all_row["limitations"])
            self.assertEqual(all_row["dose_status"], "FULL_VECTOR_NOT_PUBLICLY_RECOVERED")

    def test_ndx_turnover_is_approximate_event_level_only(self) -> None:
        row = next(row for row in self.doses if row["event_id"] == "NDX_2023_07_SPECIAL")
        self.assertEqual(row["security_or_all"], "ALL")
        self.assertEqual(row["reported_one_way_turnover_pct"], "12")
        self.assertEqual(row["numeric_precision_pct"], "")
        self.assertIn("approximately", row["limitations"])
        self.assertEqual(row["evidence_grade"], "B")

    def test_nasdaq_publishers_are_not_inherited_from_sp_default(self) -> None:
        for row in self.sources:
            if row["index_family"].startswith("Nasdaq"):
                self.assertNotEqual(row["publisher"], "S&P Dow Jones Indices LLC")

    def test_all_claimed_implementation_closes_are_market_days(self) -> None:
        for row in self.events:
            if row["implementation_close_date"]:
                self.assertTrue(
                    registry.is_market_day(
                        registry.date.fromisoformat(row["implementation_close_date"])
                    ),
                    row["event_id"],
                )
        by_id = {row["event_id"]: row for row in self.events}
        self.assertEqual(by_id["NDX_2026Q2_REGULAR"]["implementation_close_date"], "2026-06-18")
        self.assertEqual(by_id["SS_TECH_2026Q2_REGULAR"]["implementation_close_date"], "2026-06-18")
        self.assertEqual(by_id["NDX_2026Q1_REGULAR"]["next_intervention_date"], "2026-06-18")

    def test_historical_ndx_rule_level_is_not_backcast(self) -> None:
        by_id = {row["event_id"]: row for row in self.events}
        for year in (2018, 2019):
            for quarter in (1, 2, 3, 4):
                self.assertEqual(
                    by_id[f"NDX_{year}Q{quarter}_REGULAR"]["regime_id"],
                    "NDX_SECURITY_LEVEL_SCREEN_2018_2020Q1",
                )
        self.assertEqual(
            by_id["NDX_2020Q1_REGULAR"]["regime_id"],
            "NDX_SECURITY_LEVEL_SCREEN_2018_2020Q1",
        )
        self.assertEqual(
            by_id["NDX_2020Q2_REGULAR"]["regime_id"],
            "NDX_RULE_LEVEL_TRANSITION_UNRESOLVED_2020Q2",
        )
        self.assertEqual(
            by_id["NDX_2020Q3_REGULAR"]["regime_id"],
            "NDX_ISSUER_LEVEL_2020Q3_20240623",
        )
        for row in self.events:
            if row["event_id"].startswith("NDX_") and row["event_id"].endswith("_REGULAR"):
                if row["effective_open_date"] < "2026-05-01":
                    self.assertEqual(row["earliest_public_announcement_date"], "")

    def test_event_rule_foreign_keys_and_regimes_resolve(self) -> None:
        by_key = {row["evidence_key"]: row for row in self.sources}
        for event in self.events:
            keys = event["rule_evidence_keys"].split("|")
            self.assertTrue(keys, event["event_id"])
            self.assertTrue(all(key in by_key for key in keys), event["event_id"])
            self.assertTrue(
                any(by_key[key]["regime_id"] == event["regime_id"] for key in keys),
                event["event_id"],
            )

    def test_nonbinding_classification_grade_is_not_assignment_grade_b(self) -> None:
        for row in self.events:
            if row["binding_status"] == "confirmed_nonbinding":
                self.assertEqual(row["classification_evidence_grade"], "B")
                self.assertEqual(row["assignment_evidence_grade"], "U")

    def test_july_2023_replacement_is_separate_linked_interference(self) -> None:
        by_id = {row["event_id"]: row for row in self.events}
        replacement = by_id["NDX_2023_07_17_TTD_ATVI_REPLACEMENT"]
        special = by_id["NDX_2023_07_SPECIAL"]
        self.assertEqual(replacement["earliest_public_announcement_date"], "2023-07-12")
        self.assertEqual(replacement["implementation_close_date"], "2023-07-14")
        self.assertEqual(replacement["effective_open_date"], "2023-07-17")
        self.assertEqual(replacement["binding_status"], "confirmed_other_intervention")
        self.assertEqual(replacement["interference_event_ids"], special["event_id"])
        self.assertEqual(special["interference_event_ids"], replacement["event_id"])
        self.assertEqual(
            by_id["NDX_2023Q2_REGULAR"]["next_intervention_date"],
            "2023-07-17",
        )


if __name__ == "__main__":
    unittest.main()
