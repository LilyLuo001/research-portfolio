#!/usr/bin/env python3
"""Aggregate and document the four frozen YAX joint-power scenarios."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib


PRIMARY_BETA_C = -0.05129329438755058  # log(0.95)


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def _load(paths):
    scenarios = []
    inputs = []
    for path in paths:
        record = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        if record.get("status") != "PASS_SIMULATION_COMPLETE":
            raise ValueError(f"incomplete scenario: {path}")
        if record.get("post_outcomes_read") is not False:
            raise ValueError(f"outcome seal not preserved: {path}")
        design = record.get("design", {})
        if not (
            design.get("post_start") == "2023-01"
            and design.get("transition_excluded") == "2022-12"
            and design.get("post_end") == "2026-07"
            and "2025-10" in design.get("post_gaps", [])
        ):
            raise ValueError(f"scenario does not use the frozen v5 post window: {path}")
        scenarios.append(record)
        inputs.append({"path": str(path), "sha256": sha256(path)})
    return scenarios, inputs


def build(paths, sensitivity_paths=()):
    scenarios, inputs = _load(paths)
    expected = {
        ("dv_rating_beta", "onet_computers_importance"),
        ("dv_rating_beta", "webb_pct_software"),
        ("dv_rating_alpha", "onet_computers_importance"),
        ("dv_rating_alpha", "webb_pct_software"),
    }
    observed = {(s["ai_measure"], s["computerization_measure"]) for s in scenarios}
    if observed != expected:
        raise ValueError(f"expected four frozen scenarios; got {sorted(observed)}")
    if any(abs(s["beta_c"] - PRIMARY_BETA_C) > 1e-12 for s in scenarios):
        raise ValueError("primary aggregate requires beta_c = log(0.95)")
    sensitivity, sensitivity_inputs = _load(sensitivity_paths)
    if sensitivity:
        expected_sensitivity = {
            ("dv_rating_beta", "onet_computers_importance", 0.0),
            ("dv_rating_beta", "webb_pct_software", 0.0),
            ("dv_rating_beta", "onet_computers_importance", -0.10536051565782628),
            ("dv_rating_beta", "webb_pct_software", -0.10536051565782628),
        }
        observed_sensitivity = {
            (s["ai_measure"], s["computerization_measure"], s["beta_c"])
            for s in sensitivity
        }
        if observed_sensitivity != expected_sensitivity:
            raise ValueError("sensitivity set must be beta × two controls at 0% and 10%")
    return {
        "record_version": "yax-joint-computerization-power-aggregate-v2",
        "status": "PASS_FOUR_PRIMARY_SCENARIOS_COMPLETE",
        "post_outcomes_read": False,
        "primary_ai_measure": "dv_rating_beta",
        "robustness_ai_measure": "dv_rating_alpha",
        "primary_beta_c": PRIMARY_BETA_C,
        "beta_c_interpretation": (
            "pre-specified 5% relative young-employment decline per one "
            "weighted-SD of computerization in the synthetic post period"
        ),
        "bootstrap": {
            "primary_inference": "occupation-cluster Rademacher calibration",
            "draws_per_scenario": 999,
            "mde_interval_draws_per_scenario": 999,
            "scenario_records_carry_critical_values_and_seeds": True,
        },
        "inputs": inputs,
        "scenarios": sorted(scenarios,
                            key=lambda x: (x["ai_measure"],
                                           x["computerization_measure"])),
        "sensitivity_inputs": sensitivity_inputs,
        "beta_c_sensitivity_scenarios": sorted(
            sensitivity,
            key=lambda x: (x["beta_c"], x["computerization_measure"])),
    }


def markdown(receipt):
    lines = [
        "# Joint AI-exposure and computerization power", "",
        "This power exercise uses only the sealed 2017-01–2022-11 cells. Synthetic "
        "post months are generated from pre-period donors; no post-period outcome "
        "has been opened. The primary AI measure remains Eloundou β. Eloundou α is "
        "a frozen robustness measure, not a replacement chosen for lower collinearity.", "",
        "The v5 static synthetic post window starts January 2023, excludes December "
        "2022 as the transition month, ends July 2026, and omits the known October "
        "2025 gap.", "",
        "The computerization coefficient is fixed at `log(0.95)` per employment-"
        "weighted standard deviation. It is a design stress parameter, not an "
        "estimate from outcomes. Primary inference uses an independently calibrated "
        "occupation-cluster Rademacher critical value with 999 draws.", "",
        "| AI exposure | computerization control | clusters | partial variance | effective occupations | null size | MDE80 | 95% Monte Carlo interval |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in receipt["scenarios"]:
        null = next(item for item in row["results"]
                    if abs(item["true_log_effect"]) < 1e-12)
        support = row["identifying_support"]
        interval = row["bootstrap"]["mde_monte_carlo_interval"]
        mde = row["empirical_mde80_relative_decline"]
        mde_text = "not bracketed" if mde is None else f"{mde:.2%}"
        interval_text = ("not available" if interval["lower"] is None else
                         f"{interval['lower']:.2%}–{interval['upper']:.2%}")
        lines.append(
            f"| {row['ai_measure']} | {row['computerization_measure']} | "
            f"{row['occupation_clusters']} | "
            f"{support['weighted_partial_variance_ai_given_computerization']:.3f} | "
            f"{support['effective_occupations_identifying_beta_ai']:.1f} | "
            f"{null['rejection_probability_zero']:.3f} | {mde_text} | "
            f"{interval_text} |"
        )
    if receipt["beta_c_sensitivity_scenarios"]:
        lines += ["", "## Sensitivity to the fixed computerization effect", "",
                  "The primary 5% decline is bracketed by zero and a 10% decline. "
                  "These are transparent DGP stress values, not outcome estimates.", "",
                  "| computerization control | fixed computerization decline | MDE80 |",
                  "|---|---:|---:|"]
        for row in receipt["beta_c_sensitivity_scenarios"]:
            decline = 1.0 - math.exp(row["beta_c"])
            mde = row["empirical_mde80_relative_decline"]
            lines.append(
                f"| {row['computerization_measure']} | {decline:.0%} | "
                + ("not bracketed |" if mde is None else f"{mde:.2%} |")
            )
    lines += ["", "## Limits of the fitted-DGP exercise", "",
              "The simulation preserves the observed joint exposure distribution and "
              "pre-period occupation/month structure, but it cannot reproduce an "
              "unobserved post-2022 aggregate shock, a structural change in occupation "
              "composition, measurement error in either exposure, or misspecification "
              "of the conditional mean. Its MDE is a design diagnostic under the fitted "
              "DGP, not evidence that the eventual association is causal.", "",
              "The table reports conditional MDEs for this joint model only. It "
              "does not repeat the obsolete unconditional 3.44% figure, and no "
              "scenario is described as having ‘100% power.’", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=pathlib.Path)
    parser.add_argument("--sensitivity", nargs="*", type=pathlib.Path, default=())
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--markdown", type=pathlib.Path, required=True)
    args = parser.parse_args(argv)
    receipt = build(args.inputs, args.sensitivity)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(markdown(receipt), encoding="utf-8")
    print(f"wrote {args.output} and {args.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
