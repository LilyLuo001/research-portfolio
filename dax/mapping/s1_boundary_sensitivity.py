#!/usr/bin/env python3
"""How much of the S1 headline is a judgment, and how much is a boundary?

S1 is single-annotator against a protocol requiring independent domain
reviewers, so the obvious cross-check is a second annotator. That check is
necessary and is not this one: it needs the private task text and a second
vendor family, and it can only ever test whether the annotator classified
individual tasks correctly.

This tests something a second annotator cannot. Two choices sit downstream of
every per-task judgment, neither of them signed, and both move the headline:

1. **Weighting.** The receipt already carries three: unweighted counts,
   equal-family, and task-mass within the pilot. They disagree.
2. **Where the evaluable boundary is drawn.** The v3 packet's own taxonomy
   puts `executable_with_construct_valid_simulated_inputs` in a conditional
   class -- "Evaluable only after construct-validity review; report
   separately" -- so whether it counts is a decision, not an observation.
   `executable_with_supplied_files_data` is conditional too: "Evaluable if
   input validity passes."

The identified share `B_o` is what the missing-mass multiplier multiplies. If
`B` moves by more across an unsigned boundary than two annotators would ever
disagree, then the annotator count is not the binding uncertainty, and fixing
it first would be treating the smaller problem.

Two perfectly agreeing annotators leave this entirely open, which is why it is
worth computing before spending anything on the second one.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
RESULT = HERE / "s1_construct_validity_result_receipt_20260823.json"

# Ordered from the narrowest defensible reading to the widest. Each step adds
# exactly one class, and each added class is one the v3 taxonomy marks
# conditional rather than plainly evaluable.
BOUNDARIES = {
    "strict": {
        "classes": ["directly_executable_digital"],
        "reading": "only tasks whose inputs and deliverable are natively "
                   "digital and available in the frozen harness",
    },
    "medium": {
        "classes": ["directly_executable_digital",
                    "executable_with_supplied_files_data"],
        "reading": "adds tasks needing supplied files or data, which the v3 "
                   "taxonomy admits only 'if input validity passes'",
    },
    "broad": {
        "classes": ["directly_executable_digital",
                    "executable_with_supplied_files_data",
                    "executable_with_construct_valid_simulated_inputs"],
        "reading": "adds simulated-input tasks, which the v3 taxonomy admits "
                   "only after construct-validity review and requires to be "
                   "reported separately",
    },
}


class SensitivityError(RuntimeError):
    """Raised when the receipt cannot support the computation."""


def load_result(path=RESULT):
    return json.loads(path.read_text(encoding="utf-8"))


def headline_weightings(result):
    """The three NON_EVALUABLE shares the receipt already carries."""
    counts = result["construct_status_counts"]
    n = sum(counts.values())
    return {
        "unweighted_count": {
            "value": counts["NON_EVALUABLE"] / n,
            "numerator": counts["NON_EVALUABLE"], "denominator": n,
        },
        "equal_family_weighted": {
            "value": result["equal_family_weighted_construct_status_shares"]["NON_EVALUABLE"],
        },
        "task_mass_weighted_within_pilot": {
            "value": result["task_mass_weighted_construct_status_shares_within_pilot"]["NON_EVALUABLE"],
        },
    }


def evaluable_mass(result, boundary_key):
    """Identified mass share B under one boundary. Sums published class shares."""
    shares = result["task_mass_weighted_evaluable_class_shares_within_pilot"]
    spec = BOUNDARIES[boundary_key]
    missing = [c for c in spec["classes"] if c not in shares]
    if missing:
        raise SensitivityError(
            f"boundary {boundary_key!r} names classes absent from the receipt: "
            f"{missing}. The taxonomy changed and these boundaries must be "
            f"re-drawn by hand rather than silently skipping a class.")
    return sum(shares[c] for c in spec["classes"])


def kappa_multiplier(B, kappa):
    """[B + kappa(1-B)] -- the missing-mass multiplier B feeds."""
    return B + kappa * (1.0 - B)


def build(result=None, kappas=(0.0, 0.25, 0.5, 0.75, 1.0)):
    result = result or load_result()
    shares = result["task_mass_weighted_evaluable_class_shares_within_pilot"]

    boundaries = {}
    for key, spec in BOUNDARIES.items():
        B = evaluable_mass(result, key)
        boundaries[key] = {
            "classes_counted_evaluable": spec["classes"],
            "reading": spec["reading"],
            "identified_mass_share_B": B,
            "unidentified_mass_share": 1.0 - B,
            "kappa_multiplier": {str(k): kappa_multiplier(B, k) for k in kappas},
        }

    values = [b["identified_mass_share_B"] for b in boundaries.values()]
    spread = max(values) - min(values)
    ratio = (max(values) / min(values)) if min(values) > 0 else None

    weightings = headline_weightings(result)
    w_values = [w["value"] for w in weightings.values()]

    return {
        "record_version": "dax-s1-boundary-sensitivity-v1",
        "what_this_is": (
            "Sensitivity of the S1 headline to two unsigned choices that sit "
            "downstream of every per-task judgment: the weighting, and where "
            "the evaluable boundary is drawn. It is not a second annotation "
            "and does not substitute for one."),
        "s1_qualifier": (
            "S1 is single-annotator with formal_s1_gate_result UNRESOLVED and "
            "audit_limit PRELIMINARY_SINGLE_CODEX_NOT_INDEPENDENT_DOMAIN_"
            "EXPERT_VALIDATION. Every number below inherits that limit; these "
            "are diagnostics and carry no claim."),
        "source_receipt": str(RESULT.relative_to(HERE.parents[1])),
        "non_evaluable_headline_by_weighting": weightings,
        "headline_spread_across_weightings": max(w_values) - min(w_values),
        "boundaries": boundaries,
        "identified_share_spread": spread,
        "identified_share_ratio_widest_to_narrowest": ratio,
        "directly_executable_digital_mass": shares["directly_executable_digital"],
        "why_this_ranks_above_the_annotator_count": (
            "Two annotators in perfect agreement leave both choices open. The "
            "boundary is definitional, not a judgment about any task, and it "
            "moves the identified share by more than a disagreement between "
            "careful annotators plausibly would."),
        "the_degenerate_case": (
            "Under the strict boundary the identified mass is exactly zero, "
            "because S1 found no directly-executable-digital task at all. At "
            "B = 0 the multiplier collapses to kappa: the index would carry no "
            "information from data and would be the missing-mass assumption "
            "alone. That is not a bound anyone can publish, and it is reached "
            "by a defensible reading of the project's own taxonomy."),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=pathlib.Path,
                    default=HERE / "s1_boundary_sensitivity_receipt.json")
    args = ap.parse_args(argv)
    try:
        rec = build()
    except SensitivityError as exc:
        print(f"NEED_HUMAN: {exc}", file=sys.stderr)
        return 2
    args.output.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")

    print(f"wrote {args.output}\n")
    print("NON_EVALUABLE headline, by weighting:")
    for name, block in rec["non_evaluable_headline_by_weighting"].items():
        print(f"  {name:<34} {block['value']:.4f}")
    print(f"  spread {rec['headline_spread_across_weightings']:.4f}\n")
    print("Identified mass share B, by evaluable boundary:")
    for name, block in rec["boundaries"].items():
        print(f"  {name:<8} B = {block['identified_mass_share_B']:.4f}   "
              f"kappa=0 multiplier {block['kappa_multiplier']['0.0']:.4f}")
    ratio = rec["identified_share_ratio_widest_to_narrowest"]
    print(f"  spread {rec['identified_share_spread']:.4f}, "
          f"ratio {'undefined (narrowest is zero)' if ratio is None else f'{ratio:.2f}x'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
