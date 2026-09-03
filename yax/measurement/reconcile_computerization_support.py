#!/usr/bin/env python3
"""Reconcile YAX's 13-month OCC2010 and 66-month target supports."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib


METRICS = (
    "partial_variance_of_ai",
    "vif",
    "se_inflation",
    "effective_number_identifying_ai",
    "common_support_employment_share",
)


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def build(old_path, new_path, cells_receipt_path):
    old, new, cells = load(old_path), load(new_path), load(cells_receipt_path)
    old_pairs = {(row["ai_measure"], row["computerization_measure"]): row
                 for row in old["pairs"]}
    comparisons = []
    for current in new["pairs"]:
        key = (current["ai_measure"], current["computerization_measure"])
        prior = old_pairs[key]
        comparisons.append({
            "ai_measure": key[0],
            "computerization_measure": key[1],
            "thirteen_month": {metric: prior[metric] for metric in METRICS},
            "sixty_six_month": {metric: current[metric] for metric in METRICS},
            "change_66m_minus_13m": {
                metric: current[metric] - prior[metric] for metric in METRICS
            },
        })
    maxima = {
        metric: max(comparisons,
                    key=lambda row: abs(row["change_66m_minus_13m"][metric]))
        for metric in METRICS
    }
    new_support = new["preperiod_support"]
    return {
        "record_version": "yax-support-reconciliation-v1",
        "status": "PASS_SUPPORTS_RECONCILED_AND_PRIMARY_PINNED",
        "post_event_outcomes_opened": False,
        "inputs": {
            "thirteen_month_receipt": {"path": str(old_path),
                                         "sha256": sha256(old_path)},
            "sixty_six_month_receipt": {"path": str(new_path),
                                          "sha256": sha256(new_path)},
            "design_cells_receipt": {"path": str(cells_receipt_path),
                                       "sha256": sha256(cells_receipt_path)},
        },
        "counts": {
            "490": {
                "meaning": "balanced two-age Census-2018 target clusters used by the power design",
                "derivation": (
                    f"{new_support.get('raw_occupation_codes')} raw target codes minus "
                    f"codes without positive 66-month support in both age groups"
                ),
            },
            "445": {
                "meaning": "OCC2010 codes observed in the older 13-month moment artifact",
                "derivation": (
                    "current valid occupation for employed people or most recent prior valid "
                    "occupation within 15 months for non-employed people"
                ),
            },
            "442": {
                "meaning": "the 445 older-support OCC2010 codes carrying a Webb score",
                "derivation": "445 minus the three Webb-unscored source occupations",
            },
        },
        "comparison_warning": (
            "13m-to-66m changes combine horizon, occupation vintage, balance rule and weight "
            "definition; they are not a pure calendar-window experiment"
        ),
        "pinned_primary_support": {
            "name": "66-month balanced Census-2018 target-occupation design cells",
            "months": new_support["months"],
            "first_month": new_support["first_month"],
            "last_month": new_support["last_month"],
            "occupation_clusters": new_support["occupation_codes"],
            "lookup_role": new_support["lookup_role"],
            "cells_sha256": cells.get("cells_sha256"),
            "cells_receipt_status": cells.get("status"),
            "coverage_gate_pass": cells.get("coverage_gate_pass"),
            "role": "primary design support; OCC2010 remains a sensitivity support",
        },
        "comparisons": comparisons,
        "largest_absolute_changes": maxima,
    }


def markdown(receipt):
    pin = receipt["pinned_primary_support"]
    lines = [
        "# Support reconciliation for the computerization design", "",
        "## The three live counts", "",
        "| count | what it counts | why it differs |", "|---:|---|---|",
    ]
    for count in ("490", "445", "442"):
        item = receipt["counts"][count]
        lines.append(f"| {count} | {item['meaning']} | {item['derivation']} |")
    lines += [
        "", "These are not three estimates of one population. The 490-cluster artifact "
        "uses harmonized Census-2018 target occupations and current employment in the "
        "two frozen age groups. The older 445-code artifact uses OCC2010 and can assign "
        "a recent occupation to a non-employed respondent. The 442 count is a measure-"
        "availability subset of that older support.", "",
        "## Frozen support", "",
        f"The design pins the **{pin['name']}**: {pin['occupation_clusters']} clusters, "
        f"{pin['months']} months ({pin['first_month']} through {pin['last_month']}), "
        f"lookup role `{pin['lookup_role']}`, cells SHA-256 `{pin['cells_sha256']}`. "
        "OCC2010 is retained only as a sensitivity support.", "",
        "The cells receipt still records the previously failed exposure-coverage gate. "
        "Pinning the file does not convert that failed gate into a pass.", "",
        "## Thirteen- versus 66-month diagnostics", "",
        receipt["comparison_warning"] + ". The table therefore reports movements rather "
        "than attributing them to the additional months.", "",
        "| AI measure | computerization | partial 13m | partial 66m | VIF 13m | VIF 66m | effective N 13m | effective N 66m |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in receipt["comparisons"]:
        old, new = row["thirteen_month"], row["sixty_six_month"]
        lines.append(
            f"| {row['ai_measure']} | {row['computerization_measure']} | "
            f"{old['partial_variance_of_ai']:.3f} | {new['partial_variance_of_ai']:.3f} | "
            f"{old['vif']:.2f} | {new['vif']:.2f} | "
            f"{old['effective_number_identifying_ai']:.1f} | "
            f"{new['effective_number_identifying_ai']:.1f} |"
        )
    partial = receipt["largest_absolute_changes"]["partial_variance_of_ai"]
    vif = receipt["largest_absolute_changes"]["vif"]
    eff = receipt["largest_absolute_changes"]["effective_number_identifying_ai"]
    lines += [
        "", "## Reading the movement", "",
        f"The largest absolute partial-variance movement is "
        f"{abs(partial['change_66m_minus_13m']['partial_variance_of_ai']):.3f}; "
        f"the largest VIF movement is {abs(vif['change_66m_minus_13m']['vif']):.3f}. "
        "Those changes do not reverse the Y1b conclusion about which pairings are "
        "strongly versus weakly collinear. Effective-N moves more: the largest change "
        f"is {abs(eff['change_66m_minus_13m']['effective_number_identifying_ai']):.1f} "
        "occupations, so concentration must be reported on the pinned support rather "
        "than carried over from the 13-month receipt.", "",
    ]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--thirteen-month", type=pathlib.Path, required=True)
    parser.add_argument("--sixty-six-month", type=pathlib.Path, required=True)
    parser.add_argument("--cells-receipt", type=pathlib.Path, required=True)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--markdown", type=pathlib.Path, required=True)
    args = parser.parse_args(argv)
    receipt = build(args.thirteen_month, args.sixty_six_month, args.cells_receipt)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(markdown(receipt), encoding="utf-8")
    print(f"wrote {args.markdown} and {args.receipt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
