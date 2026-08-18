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


def test_selfreview_can_never_count_as_the_independent_pass():
    """A self-review must be structurally incapable of clearing Gate 1.

    The failure mode this guards against is a future session finding a
    review-shaped document in dax/memo/ and treating it as the meta-rule 2
    evidence item.
    """
    import pathlib

    memo_dir = pathlib.Path(__file__).resolve().parents[1] / "memo"
    review = (memo_dir / "red_team_selfreview_2026-08-18.md").read_text(encoding="utf-8")
    assert "SATISFIES_META_RULE_2: NO" in review
    assert "COUNTS_AS_GATE1_RED_TEAM_EVIDENCE: NO" in review
    for verdict in ("CONDITIONAL_GO", "GO", "PASS"):
        assert f"VERDICT: {verdict}" not in review, \
            "a self-review must not issue a gate verdict"

    checklist = (memo_dir / "PI_DECISIONS_OPEN.md").read_text(encoding="utf-8")
    line = next(l for l in checklist.splitlines() if "cross-vendor red-team" in l)
    assert line.strip().startswith("- [ ]"), \
        "the independent red-team item must remain unchecked"


def test_red_team_packet_covers_the_v2_design():
    """The paid pass must see WHY the primary changed, or it reviews the wrong design."""
    import pathlib

    source = (pathlib.Path(__file__).resolve().parents[1]
              / "memo" / "run_deepseek_red_team.py").read_text(encoding="utf-8")
    for required in ("PI_DECISION_D1_2026-08-18.md",
                     "PI_DECISION_D3_2026-08-18.md",
                     "PI_DECISION_D4_2026-08-18.md",
                     "power_results_continuous.json",
                     "power_standard.json"):
        assert required in source, f"v2 packet is missing {required}"
    assert "does not transfer" in source, \
        "the prompt must tell the reviewer not to defer to the superseded verdict"
