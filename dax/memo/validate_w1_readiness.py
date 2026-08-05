"""Audit DAX W1 memo structure and report Gate-1 blockers.

The default command succeeds when the draft is structurally coherent and
prints the remaining human/evidence blockers. ``--require-gate-ready`` is a
fail-closed gate check and returns nonzero until every blocker is resolved.
"""

from __future__ import annotations

import argparse
import importlib.util
import pathlib
import re


HERE = pathlib.Path(__file__).resolve().parent
MEMO = HERE / "design_memo_v1.md"
CHECKLIST = HERE / "PI_DECISIONS_OPEN.md"
EVENT_VALIDATOR = HERE / "validate_event_registry.py"
DECISION_RE = re.compile(r"\[PI-DECISION (\d+)\]")
CHECKLIST_ROW_RE = re.compile(
    r"^\|\s*(\d+)\s*\|.*\|\s*(OPEN|APPROVED|REJECTED)\s*\|\s*$",
    re.MULTILINE,
)


def _load_event_validator():
    spec = importlib.util.spec_from_file_location("validate_event_registry", EVENT_VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EVENT_VALIDATOR}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def audit() -> dict[str, object]:
    memo = MEMO.read_text(encoding="utf-8")
    checklist = CHECKLIST.read_text(encoding="utf-8")
    structural_errors: list[str] = []

    memo_numbers = [int(value) for value in DECISION_RE.findall(memo)]
    expected = list(range(1, 18))
    if memo_numbers != expected:
        structural_errors.append(
            f"memo PI decisions must appear once in order 1..17; found {memo_numbers}"
        )

    checklist_rows = {
        int(number): status for number, status in CHECKLIST_ROW_RE.findall(checklist)
    }
    if sorted(checklist_rows) != expected:
        structural_errors.append(
            "PI checklist must contain exactly one response row for decisions 1..17"
        )

    event_validator = _load_event_validator()
    event_rows, event_errors = event_validator.validate()
    structural_errors.extend(f"event registry: {error}" for error in event_errors)

    open_decisions = sorted(
        number for number, status in checklist_rows.items() if status == "OPEN"
    )
    rejected_decisions = sorted(
        number for number, status in checklist_rows.items() if status == "REJECTED"
    )
    pending_event_locators = sorted(
        row["event_id"]
        for row in event_rows
        if row["verification_status"] == "pending_second_date_locator"
    )
    unchecked_items = len(re.findall(r"^- \[ \] ", checklist, flags=re.MULTILINE))
    draft_status = "DRAFT FOR PI DECISION" in memo

    blockers: list[str] = []
    if open_decisions:
        blockers.append(f"{len(open_decisions)} PI decisions remain OPEN")
    if rejected_decisions:
        blockers.append(f"{len(rejected_decisions)} PI decisions are REJECTED and need revision")
    if pending_event_locators:
        blockers.append(
            f"{len(pending_event_locators)} event rows need a second dated locator"
        )
    if unchecked_items:
        blockers.append(f"{unchecked_items} confirmation/evidence checklist items are unchecked")
    if draft_status:
        blockers.append("memo is still marked DRAFT FOR PI DECISION")

    return {
        "structural_errors": structural_errors,
        "blockers": blockers,
        "open_decisions": open_decisions,
        "rejected_decisions": rejected_decisions,
        "pending_event_locators": pending_event_locators,
        "unchecked_items": unchecked_items,
        "event_rows": len(event_rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-gate-ready",
        action="store_true",
        help="return nonzero while any W1 Gate-1 blocker remains",
    )
    args = parser.parse_args()
    report = audit()

    structural_errors = report["structural_errors"]
    if structural_errors:
        print("W1 STRUCTURE FAILED")
        for error in structural_errors:
            print(f"- {error}")
        return 1

    blockers = report["blockers"]
    print(
        "W1 STRUCTURE PASSED — "
        f"17 PI decisions; {report['event_rows']} event rows"
    )
    if blockers:
        print("GATE 1 BLOCKED (expected for this draft)")
        for blocker in blockers:
            print(f"- {blocker}")
    else:
        print("GATE 1 READY FOR OWNER SIGNATURE")

    return 2 if args.require_gate_ready and blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
