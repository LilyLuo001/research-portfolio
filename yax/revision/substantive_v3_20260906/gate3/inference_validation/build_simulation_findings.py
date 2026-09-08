#!/usr/bin/env python3
"""Assemble the independently validated Gate 3 simulation result tables."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


SCENARIOS = (
    "empirical_null", "empirical_local", "empirical_observed",
    "adverse_null", "adverse_local", "adverse_observed",
    "sparsity_equalized_null", "family_variance_zero_null",
    "serial_independent_null", "influence_equalized_null",
    "occupation_ar1_null",
)
PROCEDURES = (
    "occupation_rademacher", "occupation_webb",
    "family_rademacher", "family_webb", "crossfit_full_refit_oracle",
)
TARGETS = ("pooled", "family_month", "family_month_minus_pooled")
CORE_SCENARIOS = ("empirical_observed", "empirical_null", "adverse_null")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output_dir.exists(), "refusing to overwrite simulation findings")
    validation_path = args.run_root / "INDEPENDENT_VALIDATION.json"
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    require(validation.get("status") == "PASS_INDEPENDENT_PUBLIC_SIMULATION_VALIDATION",
            "simulation public validation does not pass")
    frames = []
    source_hashes = {}
    for scenario in SCENARIOS:
        path = args.run_root / scenario / "SIMULATION_SUMMARY.csv"
        receipt_path = args.run_root / scenario / "EXECUTION_RECEIPT.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        require(receipt.get("status") == "PASS_SIMULATION_SCENARIO_RESOLVED",
                f"{scenario} is not numerically resolved")
        require(receipt["output_hashes"][path.name] == sha256_file(path),
                f"{scenario} summary hash differs")
        frame = pd.read_csv(path)
        require(set(frame.scenario) == {scenario}, f"{scenario} label differs")
        require(set(frame.procedure) == set(PROCEDURES), f"{scenario} procedures differ")
        require(set(frame.target) == set(TARGETS), f"{scenario} targets differ")
        require(len(frame) == len(PROCEDURES) * len(TARGETS),
                f"{scenario} summary inventory differs")
        frames.append(frame)
        source_hashes[f"{scenario}/SIMULATION_SUMMARY.csv"] = sha256_file(path)
        source_hashes[f"{scenario}/EXECUTION_RECEIPT.json"] = sha256_file(receipt_path)
    combined = pd.concat(frames, ignore_index=True)
    require(len(combined) == len(SCENARIOS) * len(PROCEDURES) * len(TARGETS),
            "combined simulation inventory differs")
    require(not combined.duplicated(["scenario", "target", "procedure"]).any(),
            "combined simulation rows overlap")
    columns = [
        "scenario", "target", "procedure", "structural_theta", "pseudo_truth",
        "attempted_replications", "successful_joint_refits", "failed_joint_refits",
        "bias", "empirical_sd", "mean_reported_se", "mean_interval_length",
        "coverage", "coverage_mcse", "zero_rejection", "zero_rejection_is_size",
        "zero_rejection_mcse", "mean_or_crossfit_critical",
        "empirical_sd_relative_mc_error",
    ]
    compact = combined.loc[combined.scenario.isin(CORE_SCENARIOS), columns].copy()
    ablations = combined.loc[
        combined.scenario.str.endswith("_null")
        & combined.procedure.isin(["occupation_rademacher", "family_rademacher",
                                   "crossfit_full_refit_oracle"]),
        columns,
    ].copy()
    args.output_dir.mkdir(parents=True)
    paths = {
        "ALL_SIMULATION_SUMMARY.csv": combined[columns].copy(),
        "CORE_SIMULATION_COMPARISON.csv": compact,
        "NULL_AND_ABLATION_COMPARISON.csv": ablations,
    }
    for name, frame in paths.items():
        frame.to_csv(args.output_dir / name, index=False, lineterminator="\n")
    receipt = {
        "schema_version": "yax-gate3-simulation-findings-v1",
        "status": "PASS_SIMULATION_FINDINGS_ASSEMBLY",
        "scenario_count": len(SCENARIOS),
        "procedure_count": len(PROCEDURES),
        "target_count": len(TARGETS),
        "all_summary_rows": len(combined),
        "independent_validation_sha256": sha256_file(validation_path),
        "source_hashes": source_hashes,
        "output_hashes": {
            name: sha256_file(args.output_dir / name) for name in paths
        },
    }
    (args.output_dir / "ASSEMBLY_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"],
                      "rows": receipt["all_summary_rows"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
