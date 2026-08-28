#!/usr/bin/env python3
"""Re-derive which Gate-1 power dependencies are still outstanding.

Two receipts under ``dax/data_raw/`` record runs that happened before the D3
power standard was frozen on 2026-08-24:

  * ``person_level_power_receipt.json``  (generated 2026-08-20)
  * ``person_level_power_engine_validation_receipt.json`` (2026-08-18, on SCC)

Both name the unresolved power benchmark among their blockers, and the second
gives ``benchmark is null/unresolved`` as its reason for exiting nonzero. That
was true when they were written and is not true now: ``power_standard.json``
is FROZEN with ``locator_status: VERIFIED`` at a relative decline of 0.13.

Those receipts are records of runs and are deliberately NOT rewritten here --
editing a receipt to match today's state destroys the thing a receipt is for.
Instead this emits a separate, derived record of which named dependency is
still outstanding, read live from the standard rather than asserted. The point
is narrow and practical: a seat reading the 2026-08-20 receipt would conclude
the benchmark still needs resolving and would go redo work that is finished.

What this does NOT do is advance any gate. The person-level power gate and the
identification gate both still fail, for the same single reason they always
had -- there is no real W5 dose panel -- and that reason is untouched by the
freeze. This narrows a two-item blocker to a one-item blocker; it does not
clear it, and ``validate_w1_readiness.py`` still reports both gates as blocked.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import datetime, timezone

HERE = pathlib.Path(__file__).resolve().parent
STANDARD = HERE / "power_standard.json"
DATA_RAW = HERE.parent.parent / "data_raw"
PERSON_POWER = DATA_RAW / "person_level_power_receipt.json"
ENGINE_VALIDATION = DATA_RAW / "person_level_power_engine_validation_receipt.json"

# The exact dependency strings the 2026-08-20 receipt lists. Matched literally:
# if that receipt is ever reworded, this must fail loudly rather than silently
# resolve a dependency that no longer says what we think it says.
BENCHMARK_DEPENDENCY = "verified exact locator for the PI-selected power benchmark"
DOSE_DEPENDENCY = "real frozen W5 balanced occupation-month dose panel"


class StatusError(RuntimeError):
    """Raised when the inputs do not support deriving a status."""


def benchmark_is_resolved(standard):
    """True only if the standard is frozen AND its locator is verified.

    Both conditions matter and neither implies the other: a standard can be
    frozen against a benchmark whose locator was never verified, which is
    precisely the failure D3 exists to prevent.
    """
    frozen = standard.get("status") == "FROZEN"
    bench = standard.get("benchmark", {})
    verified = bench.get("locator_status") == "VERIFIED"
    resolved = bench.get("version_status") == "RESOLVED"
    value = bench.get("relative_decline")
    ceilings = standard.get("standard", {})
    have_ceilings = (ceilings.get("employment_mde_ceiling") is not None
                     and ceilings.get("hours_mde_ceiling") is not None)
    return {
        "satisfied": bool(frozen and verified and resolved
                          and value is not None and have_ceilings),
        "standard_status": standard.get("status"),
        "locator_status": bench.get("locator_status"),
        "version_status": bench.get("version_status"),
        "relative_decline": value,
        "employment_mde_ceiling": ceilings.get("employment_mde_ceiling"),
        "hours_mde_ceiling": ceilings.get("hours_mde_ceiling"),
        "frozen_at_utc": standard.get("frozen_at_utc"),
    }


def dose_panel_present(receipt):
    """The dose panel is present only if the receipt says so. Never inferred."""
    return {
        "satisfied": bool(receipt.get("w5_dose_panel_present")),
        "panel_name": receipt.get("w5_dose_panel_name"),
        "published_receipt_status":
            receipt.get("w5_handoff_check", {}).get("published_receipt_status"),
        "reason": receipt.get("w5_handoff_check", {}).get("reason"),
    }


def build():
    standard = json.loads(STANDARD.read_text(encoding="utf-8"))
    person = json.loads(PERSON_POWER.read_text(encoding="utf-8"))

    declared = list(person.get("pending_dependencies", []))
    for expected in (BENCHMARK_DEPENDENCY, DOSE_DEPENDENCY):
        if expected not in declared:
            raise StatusError(
                f"{PERSON_POWER.name} no longer lists the dependency "
                f"{expected!r}. This script resolves that receipt's dependency "
                f"strings literally; reword one and the mapping must be "
                f"re-checked by hand rather than guessed at.")

    bench = benchmark_is_resolved(standard)
    dose = dose_panel_present(person)

    still_pending = []
    if not bench["satisfied"]:
        still_pending.append(BENCHMARK_DEPENDENCY)
    if not dose["satisfied"]:
        still_pending.append(DOSE_DEPENDENCY)

    engine = json.loads(ENGINE_VALIDATION.read_text(encoding="utf-8"))

    return {
        "record_version": "dax-gate-dependency-status-v1",
        "what_this_is": (
            "A derived view of which dependencies named by the Gate-1 power "
            "receipts are still outstanding, read live from power_standard.json "
            "rather than asserted. It is not itself a run receipt and it "
            "advances no gate."),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "power_standard": str(STANDARD.relative_to(HERE.parent.parent.parent)),
            "person_level_power_receipt":
                str(PERSON_POWER.relative_to(HERE.parent.parent.parent)),
            "engine_validation_receipt":
                str(ENGINE_VALIDATION.relative_to(HERE.parent.parent.parent)),
        },
        "dependencies_declared_by_receipt": declared,
        "dependencies_still_pending": still_pending,
        "benchmark_dependency": dict(bench, dependency=BENCHMARK_DEPENDENCY),
        "dose_panel_dependency": dict(dose, dependency=DOSE_DEPENDENCY),
        "receipts_deliberately_not_rewritten": {
            "person_level_power_receipt": {
                "generated_at_utc": person.get("generated_at_utc"),
                "states_benchmark_version_status":
                    person.get("benchmark_version_status"),
                "states_benchmark_value": person.get("benchmark_value"),
                "stale_because": (
                    "written before the 2026-08-24 freeze; its benchmark fields "
                    "record the state of the world on 2026-08-20 and are "
                    "correct as history"),
            },
            "engine_validation_receipt": {
                "validated_at_utc": engine.get("validated_at_utc"),
                "states_reason_for_nonzero_exit":
                    engine.get("reason_for_nonzero_exit"),
                "adequately_powered": engine.get("adequately_powered"),
                "stale_because": (
                    "its nonzero exit was attributed to a null benchmark AND a "
                    "synthetic dose. The benchmark half no longer applies; the "
                    "synthetic-dose half still does, so the exit code would not "
                    "change. Re-running it on the SCC against the frozen "
                    "standard would replace two null verdicts with real ones "
                    "and is the only way to confirm that end to end."),
            },
        },
        "gates_advanced": [],
        "gate_1_effect": (
            "None. Both the person-level power gate and the identification gate "
            "still fail, for the single reason that no real W5 dose panel "
            "exists. That reason is untouched by the freeze and cannot be "
            "cleared before W3 mapping and W4 measurements land."),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=pathlib.Path,
                    default=DATA_RAW / "gate_dependency_status.json")
    ap.add_argument("--check", action="store_true",
                    help="exit nonzero if any declared dependency is still pending")
    args = ap.parse_args(argv)

    try:
        record = build()
    except StatusError as exc:
        print(f"NEED_HUMAN: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    pending = record["dependencies_still_pending"]
    resolved = [d for d in record["dependencies_declared_by_receipt"]
                if d not in pending]
    print(f"wrote {args.output}")
    print(f"resolved: {len(resolved)} of "
          f"{len(record['dependencies_declared_by_receipt'])}")
    for d in resolved:
        print(f"  [x] {d}")
    for d in pending:
        print(f"  [ ] {d}")
    return 1 if (args.check and pending) else 0


if __name__ == "__main__":
    raise SystemExit(main())
