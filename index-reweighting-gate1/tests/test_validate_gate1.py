from __future__ import annotations

import csv
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "validate_gate1.py"
SPEC = importlib.util.spec_from_file_location("validate_gate1", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)
PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def copy_package(parent: Path) -> Path:
    destination = parent / "package"
    shutil.copytree(
        PACKAGE_ROOT,
        destination,
        ignore=shutil.ignore_patterns(".pytest_cache", "__pycache__", "*.pyc"),
    )
    return destination


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def package_errors(root: Path) -> list[str]:
    return MODULE.validate_package(root, root / "config" / "output_contract.json")


class ValidateGate1Tests(unittest.TestCase):
    def test_missing_artifacts_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            contract = root / "contract.json"
            contract.write_text(
                json.dumps(
                    {
                        "required_files": {"x.csv": ["evidence_key", "status"]},
                        "required_documents": ["FINAL_DECISION.md"],
                        "required_directories": ["src"],
                        "allowed_assignment_grades": ["A", "B", "C", "U"],
                        "allowed_recommendations": ["REVISE"],
                    }
                ),
                encoding="utf-8",
            )
            errors = MODULE.validate_package(root, contract)
            self.assertTrue(any("missing required table" in error for error in errors))
            self.assertTrue(any("required document" in error for error in errors))

    def test_duplicate_key_and_bad_grade_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src").mkdir()
            (root / "FINAL_DECISION.md").write_text("REVISE", encoding="utf-8")
            (root / "assignment_doses_and_evidence.csv").write_text(
                "evidence_key,event_id,evidence_grade,status\n"
                "D:1,E1,Z,OPEN\n"
                "D:1,E2,A,OPEN\n",
                encoding="utf-8",
            )
            contract = root / "contract.json"
            contract.write_text(
                json.dumps(
                    {
                        "required_files": {
                            "assignment_doses_and_evidence.csv": [
                                "evidence_key",
                                "event_id",
                                "evidence_grade",
                                "status",
                            ]
                        },
                        "required_documents": ["FINAL_DECISION.md"],
                        "required_directories": ["src"],
                        "allowed_assignment_grades": ["A", "B", "C", "U"],
                        "allowed_recommendations": ["REVISE"],
                    }
                ),
                encoding="utf-8",
            )
            errors = MODULE.validate_package(root, contract)
            self.assertTrue(any("duplicate evidence_key" in error for error in errors))
            self.assertTrue(any("invalid evidence_grade" in error for error in errors))

    def test_stage_a_gap_locators_must_remain_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = copy_package(Path(temp))

            stage_a_path = root / "remaining_input_gaps_stage_a.csv"
            fields, rows = read_csv(stage_a_path)
            rows[0]["source_locator"] = "UNREDACTED_PRIVATE_LOCATOR"
            write_csv(stage_a_path, fields, rows)

            integrated_path = root / "remaining_input_gaps.csv"
            fields, rows = read_csv(integrated_path)
            next(row for row in rows if row["evidence_key"].startswith("GAPA:"))[
                "source_locator"
            ] = "UNREDACTED_PRIVATE_LOCATOR"
            write_csv(integrated_path, fields, rows)

            errors = package_errors(root)
            self.assertTrue(
                any("public Stage A gap locator not redacted" in error for error in errors)
            )
            self.assertTrue(
                any("integrated Stage A gap locator not redacted" in error for error in errors)
            )

    def test_support_anchor_date_and_eligible_set_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = copy_package(Path(temp))
            path = root / "assignment_and_fomc_support.csv"
            fields, rows = read_csv(path)
            computed_index = next(
                index for index, row in enumerate(rows) if row["meeting_id"] != "UNRESOLVED"
            )
            rows[computed_index]["anchor_date"] = "1900-01-01"
            removed = rows.pop(computed_index + 1)
            self.assertNotEqual(removed["meeting_id"], "UNRESOLVED")
            write_csv(path, fields, rows)

            errors = package_errors(root)
            self.assertTrue(any("anchor_date does not match event anchor" in error for error in errors))
            self.assertTrue(
                any("support FOMC set must equal" in error for error in errors)
            )

    def test_summary_staleness_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = copy_package(Path(temp))
            path = root / "logs" / "gate1_summary.json"
            summary = json.loads(path.read_text(encoding="utf-8"))
            summary["headline_outcome_regressions_run"] = True
            path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

            errors = package_errors(root)
            self.assertTrue(any("gate1_summary.json is stale" in error for error in errors))

    def test_raw_artifact_and_runtime_path_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = copy_package(Path(temp))
            (root / "temporary_workbook.xlsx").write_bytes(b"not a real workbook")
            (root / "logs" / "accidental_runtime.log").write_text(
                "/" + "Users/private-account/project/output.csv\n", encoding="utf-8"
            )

            errors = package_errors(root)
            self.assertTrue(any("raw/private data artifact present" in error for error in errors))
            self.assertTrue(any("possible account/runtime path" in error for error in errors))

    def test_event_rule_foreign_key_and_regime_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = copy_package(Path(temp))
            path = root / "rebalance_event_ledger.csv"
            fields, rows = read_csv(path)
            rows[0]["rule_evidence_keys"] = "RULE:DOES_NOT_EXIST"
            write_csv(path, fields, rows)

            errors = package_errors(root)
            self.assertTrue(any("unresolved rule_evidence_keys" in error for error in errors))

    def test_support_event_snapshot_and_fomc_foreign_key_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = copy_package(Path(temp))
            path = root / "assignment_and_fomc_support.csv"
            fields, rows = read_csv(path)
            computed = next(row for row in rows if row["meeting_id"] != "UNRESOLVED")
            computed["event_evidence_key"] = "EVENT:WRONG_SNAPSHOT"
            computed["fomc_evidence_key"] = "FOMC:DOES_NOT_EXIST"
            write_csv(path, fields, rows)

            errors = package_errors(root)
            self.assertTrue(any("copied event_evidence_key mismatch" in error for error in errors))
            self.assertTrue(any("unresolved FOMC evidence key" in error for error in errors))

    def test_github_credential_patterns_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = copy_package(Path(temp))
            fake_token = "github_" + "pat_" + ("A" * 30)
            (root / "logs" / "accidental_secret.log").write_text(
                fake_token + "\n", encoding="utf-8"
            )

            errors = package_errors(root)
            self.assertTrue(any("possible credential material" in error for error in errors))

if __name__ == "__main__":
    unittest.main()
