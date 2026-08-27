#!/usr/bin/env python3
"""Check whether a planned capture is exposed to the open CONFLICT-B pricing defect.

`feasibility_note.md` §2 records an unresolved defect in the vendor pricing
page: for the gpt-5.4 / 5.5 / 5.6 families it carries two tables at exactly 2x
each other (gpt-5.4 at $2.50/$15 OR $1.25/$7.50). Neither is filed as the
price. The standing rule is to plan at the HIGHER value of each pair, so the
defect inflates a budget rather than understating it -- but a cost figure built
on a conflicted rate is still a figure nobody can reconcile to a source, and
the v3 packet names resolving it as part of the no-inference preflight that
should precede budget signature.

The practical question is narrower than resolving it, and answerable now: does
any given capture scenario actually touch a conflicted family? The five
snapshots retiring 2026-10-23 are gpt-4 and o1 vintages, whose rates carry no
conflict. If a scenario spends only on those, its dollar figure is exact and
CONFLICT-B is irrelevant to the decision to authorize it.

This resolves nothing about the pricing page. It scopes the defect to the
scenarios it can actually reach, so a preservation run is not held behind a
conflict that does not apply to it -- and so the reverse case, a scenario that
IS exposed, cannot be authorized on a figure that looks equally solid.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
RECEIPT = HERE / "minimal_preservation_receipt.json"
FEASIBILITY = REPO / "dax" / "memo" / "feasibility_note.md"

# Families the note names as carrying two tables at 2x. Matched as model-id
# prefixes; the note's wording is "gpt-5.4/5.5/5.6 families".
CONFLICTED_PREFIXES = ("gpt-5.4", "gpt-5.5", "gpt-5.6")
CONFLICT_ID = "CONFLICT-B"


class PreflightError(RuntimeError):
    """Raised when the conflict's scope cannot be established from sources."""


def conflict_is_open(note_text):
    """Read the note rather than trusting this file's docstring.

    If someone resolves CONFLICT-B and updates the note, this preflight must
    stop reporting exposure -- otherwise it becomes a permanent false alarm
    that people learn to click through.
    """
    if CONFLICT_ID not in note_text:
        raise PreflightError(
            f"{FEASIBILITY.name} no longer mentions {CONFLICT_ID}. Either it "
            f"was resolved and this preflight is obsolete, or the note was "
            f"restructured. Re-scope by hand rather than assuming.")
    open_line = re.search(
        rf"Open at signature time:\s*\*\*{CONFLICT_ID}\*\*", note_text)
    return open_line is not None


def exposure(model_ids):
    """Split model ids into those a conflicted rate would price and those it would not."""
    exposed, clean = [], []
    for mid in model_ids:
        (exposed if mid.startswith(CONFLICTED_PREFIXES) else clean).append(mid)
    return {"exposed": sorted(exposed), "unexposed": sorted(clean)}


def build():
    note = FEASIBILITY.read_text(encoding="utf-8")
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))

    retiring = receipt["rows_retiring_2026_10_23"]
    later = receipt["rows_retiring_later_or_unannounced"]

    retiring_exp = exposure(retiring)
    full_plan_exp = exposure(retiring + later)

    scenarios = {}
    for name, block in receipt["scenarios"].items():
        # Every named scenario in this receipt captures against the retiring
        # rows only; the full plan is carried separately for contrast.
        scenarios[name] = {
            "usd": block["usd"],
            "model_ids": retiring,
            "exposed_model_ids": retiring_exp["exposed"],
            "conflict_affects_this_figure": bool(retiring_exp["exposed"]),
        }
    scenarios["full_plan_for_contrast"] = {
        "usd": receipt["full_plan_for_contrast"]["usd"],
        "model_ids": retiring + later,
        "exposed_model_ids": full_plan_exp["exposed"],
        "conflict_affects_this_figure": bool(full_plan_exp["exposed"]),
    }

    return {
        "record_version": "dax-w4-price-conflict-preflight-v1",
        "conflict": CONFLICT_ID,
        "conflict_open": conflict_is_open(note),
        "conflict_description": (
            "vendor pricing page carries two tables at exactly 2x for the "
            "gpt-5.4/5.5/5.6 families; neither filed as the price; planning "
            "uses the higher value of each pair"),
        "conflicted_family_prefixes": list(CONFLICTED_PREFIXES),
        "sources": {
            "feasibility_note": str(FEASIBILITY.relative_to(REPO)),
            "preservation_receipt": str(RECEIPT.relative_to(REPO)),
        },
        "scenarios": scenarios,
        "resolves_the_conflict": False,
        "what_this_establishes": (
            "which capture scenarios the open pricing conflict can reach. It "
            "does not resolve the conflict, and a scenario reported as "
            "unaffected still depends on its own rates being correct."),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=pathlib.Path,
                    default=HERE / "price_conflict_preflight_receipt.json")
    ap.add_argument("--scenario",
                    help="exit nonzero if THIS scenario is exposed to the conflict")
    args = ap.parse_args(argv)

    try:
        rec = build()
    except PreflightError as exc:
        print(f"NEED_HUMAN: {exc}", file=sys.stderr)
        return 2

    args.output.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    print(f"{CONFLICT_ID} open: {rec['conflict_open']}")
    for name, block in sorted(rec["scenarios"].items()):
        mark = "EXPOSED" if block["conflict_affects_this_figure"] else "clean  "
        print(f"  {mark}  ${block['usd']:>8.2f}  {name}")

    if args.scenario:
        block = rec["scenarios"].get(args.scenario)
        if block is None:
            print(f"NEED_HUMAN: no scenario named {args.scenario!r}", file=sys.stderr)
            return 2
        return 1 if block["conflict_affects_this_figure"] else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
