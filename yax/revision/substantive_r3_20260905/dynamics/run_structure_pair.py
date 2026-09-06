#!/usr/bin/env python3
"""Pair the declared unconditioned and SOC2-by-month static estimates.

POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1. The two
already-declared static mapping models are fit on identical treatment support.
Their joint occupation influence representation makes the cross-structure
difference a paired comparison rather than a comparison of significance.
"""
from __future__ import annotations

import argparse
import json
import pathlib
from datetime import datetime, timezone

import numpy as np

import run_dynamics as DYN


def run(args) -> None:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    repair_receipt = DYN.march_repair_preflight(args)
    cells, _, cell_receipt = DYN.CELLS.build_exact_age_cells(args)
    historical = DYN.setup_historical(args, cells)
    rebuilt = DYN.setup_rebuilt(args.rebuilt_membership, historical, cells)
    if rebuilt is None:
        raise RuntimeError("rebuilt membership is required for paired synthesis")
    rows, artifact_names = [], []
    for contract_index, contract in enumerate((historical, rebuilt)):
        signs = np.random.default_rng(DYN.SEED + contract_index).choice(
            np.array([-1.0, 1.0]), size=(DYN.DRAWS, len(contract["support"])),
        )
        unconditioned = DYN.fit_static(contract, cells, "unconditioned")
        conditioned = DYN.fit_static(contract, cells, "SOC2_x_calendar_month")
        left_target = unconditioned["target"]
        right_target = conditioned["target"]
        left_estimate = float(unconditioned["fit"].beta[left_target])
        right_estimate = float(conditioned["fit"].beta[right_target])
        left_influence = unconditioned["influence"][:, left_target]
        right_influence = conditioned["influence"][:, right_target]
        difference = right_estimate - left_estimate
        difference_influence = right_influence - left_influence
        left_summary, _ = DYN.bootstrap_scalar(left_estimate, left_influence, signs)
        right_summary, _ = DYN.bootstrap_scalar(right_estimate, right_influence, signs)
        paired_summary, _ = DYN.bootstrap_scalar(difference, difference_influence, signs)
        covariance = np.array([
            [left_influence @ left_influence, left_influence @ right_influence],
            [right_influence @ left_influence, right_influence @ right_influence],
        ])
        suffix = contract["treatment_contract"]
        influence_name = "STATIC_STRUCTURE_PAIR_INFLUENCE_{}.csv".format(suffix)
        covariance_name = "STATIC_STRUCTURE_PAIR_COVARIANCE_{}.csv".format(suffix)
        influence_rows = []
        for index, occupation in enumerate(contract["support"]):
            influence_rows.append({
                "treatment_contract": suffix,
                "occupation_code": occupation,
                "occupation_name": contract["names"].get(occupation, occupation),
                "SOC2": contract["majors"][index],
                "unconditioned_influence": float(left_influence[index]),
                "SOC2_x_calendar_month_influence": float(right_influence[index]),
                "conditioned_minus_unconditioned_influence": float(
                    difference_influence[index]
                ),
            })
        DYN.write_csv(args.output_dir / influence_name, influence_rows)
        labels = ("unconditioned", "SOC2_x_calendar_month")
        covariance_rows = []
        for i, left in enumerate(labels):
            for j, right in enumerate(labels):
                covariance_rows.append({
                    "treatment_contract": suffix,
                    "row_structure": left,
                    "column_structure": right,
                    "occupation_cluster_covariance": float(covariance[i, j]),
                })
        DYN.write_csv(args.output_dir / covariance_name, covariance_rows)
        artifact_names.extend((influence_name, covariance_name))
        rows.append({
            "analysis_status": DYN.LABEL,
            "treatment_contract": suffix,
            "support_occupations": len(contract["support"]),
            "support_hash_sha256": DYN.support_hash(contract["support"]),
            "from_structure": "unconditioned",
            "to_structure": "SOC2_x_calendar_month",
            "unconditioned_coefficient": left_estimate,
            "unconditioned_occupation_cluster_se": left_summary["occupation_cluster_se"],
            "unconditioned_ci_lower": left_summary["ci_lower"],
            "unconditioned_ci_upper": left_summary["ci_upper"],
            "conditioned_coefficient": right_estimate,
            "conditioned_occupation_cluster_se": right_summary["occupation_cluster_se"],
            "conditioned_ci_lower": right_summary["ci_lower"],
            "conditioned_ci_upper": right_summary["ci_upper"],
            "conditioned_minus_unconditioned": difference,
            "paired_occupation_cluster_se": paired_summary["occupation_cluster_se"],
            "paired_bootstrap_se": paired_summary["bootstrap_se"],
            "paired_ci_lower": paired_summary["ci_lower"],
            "paired_ci_upper": paired_summary["ci_upper"],
            "paired_wild_score_p_value": paired_summary["wild_score_p_value"],
            "paired_normal_theory_MDE80": paired_summary["normal_theory_MDE80"],
            "common_occupation_Rademacher_draws": True,
            "bootstrap_draws": DYN.DRAWS,
            "seed": DYN.SEED + contract_index,
            "cross_structure_covariance": float(covariance[0, 1]),
            "difference_interpretation": (
                "change in conditioning estimand; not an additive causal decomposition; "
                "CI including zero means no detected difference, not equivalence"
            ),
            "influence_file": influence_name,
            "covariance_file": covariance_name,
        })
    table_name = "STATIC_STRUCTURE_PAIRING.csv"
    DYN.write_csv(args.output_dir / table_name, rows)
    artifact_names.append(table_name)
    receipt = {
        "record": "YAX R3 paired unconditioned-to-SOC2 static movement",
        "analysis_status": DYN.LABEL,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "script_sha256": DYN.sha256(pathlib.Path(__file__)),
        "wide_microdata_sha256": DYN.sha256(args.microdata),
        "march_repair_sha256": DYN.sha256(args.repair_microdata),
        "rebuilt_membership_sha256": DYN.sha256(args.rebuilt_membership),
        "march_repair_status": repair_receipt["status"],
        "cell_build_receipt": cell_receipt,
        "common_draws_and_cluster_covariance": True,
        "rows": rows,
        "output_hashes": {
            name: DYN.sha256(args.output_dir / name) for name in sorted(artifact_names)
        },
    }
    DYN.write_json(args.output_dir / "STATIC_STRUCTURE_PAIRING_RECEIPT.json", receipt)
    print(json.dumps({
        "status": "PASS_STATIC_STRUCTURE_PAIRING",
        "rows": len(rows),
        "rebuilt_difference": rows[1]["conditioned_minus_unconditioned"],
        "rebuilt_paired_se": rows[1]["paired_occupation_cluster_se"],
        "rebuilt_paired_ci": [rows[1]["paired_ci_lower"], rows[1]["paired_ci_upper"]],
        "rebuilt_MDE80": rows[1]["paired_normal_theory_MDE80"],
    }, indent=2, sort_keys=True))


def parser():
    value = DYN.parser()
    value.description = __doc__
    return value


if __name__ == "__main__":
    run(parser().parse_args())
