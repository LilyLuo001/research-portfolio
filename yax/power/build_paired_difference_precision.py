#!/usr/bin/env python3
"""Build the amended outcome-blind Test C precision receipt.

This is a lossless metadata wrapper around the original paired-equivalence
artifact.  The original file and its failed SESOI instantiation remain
unchanged.  No protected outcome is read and no numerical SESOI is supplied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import statistics


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def build(source_path):
    source_path = pathlib.Path(source_path)
    source = json.loads(source_path.read_text(encoding="utf-8"))
    draws = source.get("paired_delta_distribution")
    if not isinstance(draws, list) or len(draws) < 999:
        raise ValueError("source must store at least 999 paired Delta draws")
    if not all(isinstance(x, (int, float)) and math.isfinite(x) for x in draws):
        raise ValueError("paired Delta draws must be finite")
    if source.get("post_outcomes_read") is not False:
        raise ValueError("protected post-period outcomes were read")
    if source.get("paired_failures") != 0:
        raise ValueError("paired source contains failed draws")
    if source.get("paired_draws") != len(draws):
        raise ValueError("stored distribution length does not match paired_draws")
    stored_se = source.get("paired_delta_se")
    computed_se = statistics.stdev(draws)
    if not math.isclose(stored_se, computed_se, rel_tol=1e-12, abs_tol=1e-12):
        raise ValueError("stored SE(Delta) does not match paired distribution")
    benchmark = source.get("benchmark", {})
    if benchmark.get("status") != "BLOCKED_NO_COMMON_SCALE_BENCHMARK":
        raise ValueError("source does not preserve the failed benchmark audit")

    return {
        "record_version": "yax-paired-difference-precision-v2",
        "status": "PASS_PAIRED_DIFFERENCE_PRECISION",
        "amendment": "yax/FREEZE_AMENDMENT_2026-08-29_PAIRED_PRECISION.md",
        "post_outcomes_read": False,
        "synthetic_post_constructed_only_from_preperiod_donors": True,
        "delta_definition": source["comparison_scope"]["delta_definition"],
        "comparison_scope": source["comparison_scope"],
        "design": source["design"],
        "inputs": source["inputs"],
        "paired_distribution_source": {
            "path": "yax/power/PAIRED_EQUIVALENCE_PRECISION_v1.json",
            "sha256": sha256(source_path),
            "field": "paired_delta_distribution",
            "stored_draws": len(draws),
            "note": "Original blocked SESOI artifact is preserved unchanged."
        },
        "common_bootstrap_draws": {
            "same_draw_applied_to_both_exposure_definitions": True,
            "covariance_preserved": True,
            "paired_covariance": source[
                "paired_covariance_beta_primary_beta_contrast"
            ],
            "draws": source["paired_draws"],
            "failures": source["paired_failures"],
            "attempts": source["paired_attempts"]
        },
        "paired_delta_se": stored_se,
        "paired_confidence_interval": {
            "confidence_level": 0.95,
            "method": "percentile-t paired occupation-cluster bootstrap",
            "construction": (
                "[delta_hat - q_0.975(t_star)*se_hat_delta, "
                "delta_hat - q_0.025(t_star)*se_hat_delta]"
            ),
            "bootstrap_draws_minimum": 999,
            "same_occupation_cluster_weights_for_both_exposures": True,
            "computed_after_outcomes_open": False,
            "note": (
                "The construction is frozen now; t_star and the numerical "
                "interval are formed only after protected estimates are opened."
            )
        },
        "mde_delta_80": {
            "power_target": 0.80,
            "log_points": source["mde_delta_80_log_points"],
            "relative_magnitude": source["mde_delta_80_relative_magnitude"],
            "outcome_blind_95_critical_halfwidth_log_points": source[
                "paired_95_critical_halfwidth_log_points"
            ]
        },
        "retired_equivalence_requirements": {
            "numerical_sesoi": "RETIRED_NO_VERIFIED_MATCHING_BENCHMARK",
            "equivalence_interval": "RETIRED",
            "equivalence_power": "RETIRED",
            "arbitrary_replacement_threshold_prohibited": True
        },
        "failed_sesoi_instantiation_preserved": {
            "benchmark_status": benchmark["status"],
            "required_match_dimensions": benchmark["required_match_dimensions"],
            "rejected_shortcuts": benchmark["rejected_shortcuts"],
            "alignment_audit": "yax/literature/BENCHMARK_ALIGNMENT_2026-08-28.md",
            "alignment_receipt": (
                "yax/literature/BENCHMARK_ALIGNMENT_RECEIPT_2026-08-28.json"
            )
        },
        "binding_interpretation": {
            "ci_excludes_zero": (
                "Estimates are statistically distinguishable across the frozen "
                "exposure definitions; report the magnitude directly."
            ),
            "ci_includes_zero": "The design does not detect a difference.",
            "economic_equivalence_claim_permitted": False,
            "ex_ante_precision_statement": (
                "The frozen paired design had 80% power to detect coefficient "
                "differences of approximately 3.27 percentage points."
            )
        }
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)
    result = build(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
