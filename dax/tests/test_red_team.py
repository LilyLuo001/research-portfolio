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


def test_fresh_reruns_remain_blocking_and_adjudication_does_not_self_clear():
    import json

    memo_dir = pathlib.Path(__file__).resolve().parents[1] / "memo"
    reruns = sorted(memo_dir.glob("red_team_deepseek_v4_pro_rerun_20260818_round*.json"))
    assert len(reruns) == 3
    for path in reruns:
        review = json.loads(path.read_text(encoding="utf-8"))["review"]
        assert review["verdict"] == "REVISE"
        assert review["gate_recommendation"] == "BLOCK"
    adjudication = (memo_dir / "red_team_rerun_adjudication_20260818.md").read_text()
    assert "**BLOCK.**" in adjudication
    assert "does not self-certify" in adjudication


def test_red_team_packet_covers_the_v3_design():
    """A reviewer who cannot see what changed after 2026-08-18 reviews a ghost.

    Four things moved the primary specification or its evidence base after the
    v2 packet was assembled. Omitting any of them repeats the exact failure
    that retired the previous CONDITIONAL_GO -- a careful review of a design
    that no longer exists.
    """
    import pathlib

    source = (pathlib.Path(__file__).resolve().parents[1]
              / "memo" / "run_deepseek_red_team.py").read_text(encoding="utf-8")
    for required in ("W3_RECONCILIATION_2026-08-23.md",
                     "W2_DECISION_task_weight_2026-08-24.md",
                     "PI_AUTHORIZATION_2026-08-24.md",
                     "dwa_coverage_bound_receipt.json",
                     "gate_dependency_status.json"):
        assert required in source, f"v3 packet is missing {required}"


def test_the_prompt_forbids_reading_the_synthetic_pass_as_power():
    """The freeze made this trap sharper, not softer.

    Before 2026-08-24 the synthetic smoke test reported adequately_powered:
    null, which invited no misreading. It now reports true, and a reviewer
    skimming the packet could take that as evidence the design is powered. The
    prompt must say plainly that it is not.
    """
    import pathlib

    source = (pathlib.Path(__file__).resolve().parents[1]
              / "memo" / "run_deepseek_red_team.py").read_text(encoding="utf-8")
    assert "NOT EVIDENCE THAT THE DESIGN IS POWERED" in source
    assert "NOT_EVIDENCE_SYNTHETIC_SMOKE_TEST" in source


def test_the_prompt_names_the_unbuilt_primary_mapping():
    """The reviewer must be told the primary mapping does not exist yet."""
    import pathlib

    source = (pathlib.Path(__file__).resolve().parents[1]
              / "memo" / "run_deepseek_red_team.py").read_text(encoding="utf-8")
    assert "DOES NOT EXIST YET" in source
    assert "13 PASS of 120" in source


def test_every_packet_input_exists_and_is_readable():
    """build_prompt() reads all of them; a missing file fails only at run time.

    That run time is a paid cross-vendor call, so the failure must surface
    here instead.
    """
    for path in RED_TEAM.INPUTS:
        assert path.is_file(), f"packet input missing: {path}"
        assert path.read_text(encoding="utf-8").strip(), f"packet input empty: {path}"
