import importlib.util
import pathlib

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "memo" / "run_deepseek_red_team.py"
SPEC = importlib.util.spec_from_file_location("run_deepseek_red_team", MODULE_PATH)
assert SPEC and SPEC.loader
RED_TEAM = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RED_TEAM)


def valid_review():
    issue = {
        "id": "M1", "severity": "major", "location": "memo",
        "claim": "problem", "why_it_matters": "consequence",
        "required_change": "remedy",
    }
    return {
        "verdict": "REVISE",
        "gate_recommendation": "BLOCK",
        "major_issues": [issue],
        "minor_issues": [
            {**issue, "id": "m1", "severity": "minor"},
            {**issue, "id": "m2", "severity": "minor"},
        ],
        "decision_checks": [
            {"decision": number, "implementable": True, "problem": "", "required_change": ""}
            for number in range(1, 18)
        ],
        "evidence_gap_checks": [
            {"item": item, "satisfied": False, "reason": "pending"}
            for item in ("registry", "empirical_power", "red_team", "pi_pdf_review")
        ],
        "outcome_seal_assessment": "sealed",
        "required_changes_before_gate": ["change"],
        "nonblocking_followups": [],
    }


def test_validate_review_accepts_complete_contract():
    assert RED_TEAM.validate_review(valid_review())["verdict"] == "REVISE"


def test_validate_review_rejects_missing_decision():
    review = valid_review()
    review["decision_checks"].pop()
    with pytest.raises(ValueError, match="1 through 17"):
        RED_TEAM.validate_review(review)
