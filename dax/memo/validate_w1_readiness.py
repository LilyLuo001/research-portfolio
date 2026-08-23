"""Audit DAX W1 memo structure and report Gate-1 blockers.

The default command succeeds when the draft is structurally coherent and
prints the remaining human/evidence blockers. ``--require-gate-ready`` is a
fail-closed gate check and returns nonzero until every blocker is resolved.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import pathlib
import re


HERE = pathlib.Path(__file__).resolve().parent
MEMO = HERE / "design_memo_v1.md"
CHECKLIST = HERE / "PI_DECISIONS_OPEN.md"
EVENT_VALIDATOR = HERE / "validate_event_registry.py"
EVENT_TABLE_SHELL = HERE / "event_table_shell_v1.csv"
POWER_STANDARD = HERE / "power_calcs" / "power_standard.json"
ENTRANT_AUDIT = HERE.parent / "data_raw" / "entrant_companion_audit_receipt.json"
IDENTIFICATION_GATE = HERE.parent / "data_raw" / "identification_gate_receipt.json"
PERSON_POWER = HERE.parent / "data_raw" / "person_level_power_receipt.json"
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
    if "Entrant-margin companion (registered secondary" in memo:
        structural_errors.append(
            "memo still describes the failed entrant companion as registered secondary"
        )
    if "demoted to exploratory" not in memo:
        structural_errors.append("memo does not record the entrant-companion demotion")

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

    # Restructured 2026-08-19 for the D1 continuous primary, per the red team's
    # required change ("remove or mark as superseded the discrete-design columns
    # and add continuous-dose columns"). Under the continuous design every event
    # contributes to the dose path, so the shell describes CONTRIBUTION rather
    # than selection. The stack's window columns survive under a `secondary_`
    # prefix because the stacked corroboration still uses them.
    shell_fields = {
        "event_id", "api_effective_date", "registry_status",
        "source_verification",
        "n_occupations", "n_treated_ge_0_01", "wage_bill_crossing_mass",
        "dose_p25", "dose_p50", "dose_p75", "dose_p90",
        # continuous primary
        "dax_level_after_event_p50", "delta_dax_share_of_total_path",
        "residualized_variance_share", "narrated_under_decision_1",
        "leave_one_event_out_beta_shift",
        # secondary stacked corroboration only
        "secondary_inclusion_rule", "secondary_window_rule",
        "secondary_window_start", "secondary_window_end",
        "secondary_pre_months", "secondary_post_months",
        "secondary_max_effective_weight_share",
        "w5_fill_status",
    }
    try:
        with EVENT_TABLE_SHELL.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            missing = shell_fields - set(reader.fieldnames or [])
            shell_rows = list(reader)
        if missing:
            structural_errors.append(
                f"event table shell is missing fields {sorted(missing)}"
            )
        registry_by_id = {row["event_id"]: row for row in event_rows}
        shell_by_id = {row["event_id"]: row for row in shell_rows}
        if len(shell_rows) != len(shell_by_id):
            structural_errors.append("event table shell contains duplicate event IDs")
        if set(shell_by_id) != set(registry_by_id):
            structural_errors.append("event table shell IDs do not match the registry")
        for event_id in set(shell_by_id) & set(registry_by_id):
            shell_row = shell_by_id[event_id]
            registry_row = registry_by_id[event_id]
            locked_pairs = {
                "api_effective_date": "api_effective_date",
                "registry_status": "analysis_status",
                "source_verification": "verification_status",
            }
            for shell_field, registry_field in locked_pairs.items():
                if shell_row[shell_field] != registry_row[registry_field]:
                    structural_errors.append(
                        f"event table shell {event_id} {shell_field} diverges from registry"
                    )
            if not shell_row.get("w5_fill_status"):
                structural_errors.append(
                    f"event table shell {event_id} lacks a W5 fill status"
                )
    except FileNotFoundError:
        structural_errors.append("event table shell is missing")

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

    power_standard = json.loads(POWER_STANDARD.read_text(encoding="utf-8"))
    benchmark = power_standard["benchmark"]
    if (power_standard["status"] != "FROZEN"
            or benchmark.get("locator_status") != "VERIFIED"):
        blockers.append("power benchmark is not frozen from a verified dated locator")

    if not ENTRANT_AUDIT.is_file():
        blockers.append("entrant-companion audit receipt is missing")
    else:
        entrant = json.loads(ENTRANT_AUDIT.read_text(encoding="utf-8"))
        if entrant.get("status") != "ENTRANT_COMPANION_GATE_READY":
            blockers.append("entrant companion is demoted to exploratory")

    if not IDENTIFICATION_GATE.is_file():
        blockers.append("real-dose residualized identification gate has not run")
    else:
        identification = json.loads(IDENTIFICATION_GATE.read_text(encoding="utf-8"))
        if identification.get("status") != "PASS_DYNAMIC_IDENTIFICATION":
            blockers.append("real-dose residualized identification gate failed")

    if not PERSON_POWER.is_file():
        blockers.append("person-level empirical power receipt is missing")
    else:
        person_power = json.loads(PERSON_POWER.read_text(encoding="utf-8"))
        if person_power.get("status") != "PASS_PERSON_LEVEL_POWER":
            blockers.append("person-level empirical power gate did not pass")

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
