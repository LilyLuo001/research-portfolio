from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "validate_gate1.py"
SPEC = importlib.util.spec_from_file_location("validate_gate1", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


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


if __name__ == "__main__":
    unittest.main()
