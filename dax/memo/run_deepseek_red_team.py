"""Run and validate the independent DeepSeek review of the DAX W1 packet."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import sys


HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
INPUTS = [
    HERE / "design_memo_v1.md",
    HERE / "PI_DECISIONS_OPEN.md",
    HERE / "event_registry_v1.csv",
    HERE / "event_table_shell_v1.csv",
    HERE / "red_team_remediation.md",
    # The four counter-signed amendments: a reviewer who cannot see WHY the
    # primary changed will re-litigate the discrete design instead of
    # attacking the one that replaced it.
    HERE / "PI_DECISION_D1_2026-08-18.md",
    HERE / "PI_DECISION_D3_2026-08-18.md",
    HERE / "PI_DECISION_D4_2026-08-18.md",
    HERE / "design_audit_2026-08-14.md",
    HERE / "power_calcs" / "README.md",
    HERE / "power_calcs" / "power_standard.json",
    HERE / "power_calcs" / "ipums_preperiod_extract_receipt.json",
    HERE / "power_calcs" / "synthetic" / "power_results_continuous.json",
    HERE / "power_calcs" / "synthetic" / "power_results.json",
]


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_prompt() -> str:
    packet = []
    for path in INPUTS:
        packet.append(
            f"\n===== BEGIN {path.relative_to(REPO)} =====\n"
            f"{path.read_text(encoding='utf-8')}"
            f"\n===== END {path.relative_to(REPO)} =====\n"
        )
    return """You are the independent, cross-vendor adversarial reviewer for a
pre-registration packet. You did not author any included file. Use only the
packet below: do not browse, add outside facts, invent results, or treat the
synthetic power output as empirical evidence.

This packet is version 2. The primary specification CHANGED on 2026-08-18
from a stacked event study to a continuous cumulative-dose design, and an
entrant-margin companion was added. A prior review of the SUPERSEDED design
returned CONDITIONAL_GO; that verdict does not transfer and you must not defer
to it. Review what is in front of you.

Attack, at minimum: whether the continuous design is identified once occupation
and calendar-month effects are absorbed; whether any pre-trend test is even
computable when cumulative dose is identically zero throughout the pre-period;
whether the frozen entry mix pi_go can be estimated with usable precision from
16 months of CPS entrants and whether it is a valid instrument rather than a
noisy description; whether the "entrant" sample is contaminated by CPSIDP
linkage failure rather than being true labour-market entrants; whether the D3
benchmark conflates a payroll decline with an employment-rate decline; whether
the memo's person-month unit matches the occupation-month panel the engine
actually builds; outcome-seal integrity; event provenance; multiple testing
across the primary and companion families; crosswalk measurement error; and
whether each of PI Decisions 1 through 17 is still mechanically implementable
in its amended role. Be specific and
unpleasantly rigorous. Return at least three substantive issue objects in
total; classify an issue as major only when it actually requires a change
before Gate 1, and otherwise classify it as minor. A PASS or GO review may
have zero major issues. Do not spend space on praise.

Return exactly one JSON object whose sole top-level key is W1_REVIEW. Its value
must have this schema:
{
  "verdict": "PASS" or "REVISE",
  "gate_recommendation": "BLOCK" or "CONDITIONAL_GO" or "GO",
  "major_issues": [
    {"id": "M1", "severity": "major", "location": "section/file",
     "claim": "precise problem", "why_it_matters": "design consequence",
     "required_change": "mechanical remedy"}
  ],
  "minor_issues": [same object schema, with severity "minor"],
  "decision_checks": [
    {"decision": 1, "implementable": true or false,
     "problem": "empty only if none", "required_change": "empty only if none"}
  ],
  "evidence_gap_checks": [
    {"item": "registry" or "empirical_power" or "red_team" or "pi_pdf_review",
     "satisfied": true or false, "reason": "packet-grounded reason"}
  ],
  "outcome_seal_assessment": "specific assessment",
  "required_changes_before_gate": ["ordered concrete changes"],
  "nonblocking_followups": ["concrete followups"]
}
decision_checks must contain each integer 1 through 17 exactly once.
evidence_gap_checks must contain each of the four named items exactly once.
""" + "".join(packet)


def validate_review(review: object) -> dict[str, object]:
    if not isinstance(review, dict):
        raise ValueError("W1_REVIEW must be an object")
    if review.get("verdict") not in {"PASS", "REVISE"}:
        raise ValueError("invalid verdict")
    if review.get("gate_recommendation") not in {"BLOCK", "CONDITIONAL_GO", "GO"}:
        raise ValueError("invalid gate_recommendation")
    majors = review.get("major_issues")
    minors = review.get("minor_issues")
    if not isinstance(majors, list) or not isinstance(minors, list):
        raise ValueError("red-team issue lists are malformed")
    if len(majors) + len(minors) < 3:
        raise ValueError("red-team must return at least three substantive issues")
    issue_fields = {"id", "severity", "location", "claim", "why_it_matters", "required_change"}
    for issue in majors + minors:
        if not isinstance(issue, dict) or not issue_fields <= set(issue):
            raise ValueError("issue object does not match the required schema")
    checks = review.get("decision_checks")
    if not isinstance(checks, list) or sorted(item.get("decision") for item in checks) != list(range(1, 18)):
        raise ValueError("decision_checks must contain decisions 1 through 17 exactly once")
    evidence = review.get("evidence_gap_checks")
    expected = {"registry", "empirical_power", "red_team", "pi_pdf_review"}
    if not isinstance(evidence, list) or {item.get("item") for item in evidence} != expected:
        raise ValueError("evidence_gap_checks does not contain the four required items")
    if not isinstance(review.get("outcome_seal_assessment"), str):
        raise ValueError("missing outcome_seal_assessment")
    if not isinstance(review.get("required_changes_before_gate"), list):
        raise ValueError("missing required_changes_before_gate")
    return review


def run(output: pathlib.Path) -> dict[str, object]:
    if not os.getenv("DEEPSEEK_API_KEY"):
        raise RuntimeError("DEEPSEEK_API_KEY is not set")
    sys.path.insert(0, str(REPO))
    from ops.runner.models import MODELS, dispatch, parse_answers

    prompt = build_prompt()
    ok, result = dispatch("deepseek", prompt, dry_run=False)
    if not ok:
        raise RuntimeError(f"DeepSeek request failed: {result.get('error', 'unknown error')}")
    if result.get("finish_reason") == "length":
        raise RuntimeError("DeepSeek response was truncated")
    answers = parse_answers(result.get("text", ""))
    review = validate_review(answers.get("W1_REVIEW"))
    artifact = {
        "status": "INDEPENDENT_CROSS_VENDOR_RED_TEAM",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "reviewer_vendor": "DeepSeek",
        "model": MODELS["deepseek"],
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "inputs": {
            str(path.relative_to(REPO)): sha256(path)
            for path in INPUTS
        },
        "usage": result.get("usage", {}),
        "finish_reason": result.get("finish_reason"),
        "review": review,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=HERE / "red_team_deepseek_v4_pro.json",
    )
    args = parser.parse_args()
    artifact = run(args.output)
    review = artifact["review"]
    print(json.dumps({
        "status": artifact["status"],
        "model": artifact["model"],
        "verdict": review["verdict"],
        "gate_recommendation": review["gate_recommendation"],
        "major_issues": len(review["major_issues"]),
        "output": str(args.output),
        "usage": artifact["usage"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
