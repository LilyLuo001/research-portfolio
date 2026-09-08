#!/usr/bin/env python3
"""Validate public two-fold household shortfall diagnostic outputs."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import pandas as pd


SAMPLES = (
    "full_in_sample_same_support",
    "construct_fold0_estimate_fold1",
    "construct_fold1_estimate_fold0",
    "equal_weight_crossfit_average",
)
CONTROLS = ("total", "young_relative")
TARGETS = ("pooled", "family_month", "family_month_minus_pooled")
QUANTITIES = (
    "baseline_q5", "augmented_q5", "conditioning_movement",
    "shortfall_z_coefficient", "shortfall_raw_coefficient",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def close(left: float, right: float, tolerance: float = 2e-12) -> None:
    require(math.isclose(float(left), float(right), rel_tol=tolerance, abs_tol=tolerance),
            f"numerical mismatch: {left} versus {right}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    receipt_path = args.run_dir / "EXECUTION_RECEIPT.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(receipt.get("status") == "PASS_SHORTFALL_HOUSEHOLD_SPLIT_DIAGNOSTIC",
            "shortfall split receipt does not pass")
    for name, expected in receipt["output_hashes"].items():
        require(sha256_file(args.run_dir / name) == expected,
                f"cross-fit {name} hash differs")
    construction = json.loads(
        (args.run_dir / "SHORTFALL_CROSSFIT_CONSTRUCTION.json").read_text(encoding="utf-8"))
    require(construction["households"] == sum(construction["fold_households"]),
            "household split count differs")
    require(abs(construction["fold_households"][0]
                - construction["fold_households"][1]) <= 1,
            "household split is not count balanced")
    close(sum(construction["fold_preperiod_weights"]),
          construction["full_preperiod_weight"], tolerance=1e-10)
    frame = pd.read_csv(args.run_dir / "SHORTFALL_CROSSFIT_RESULTS.csv")
    require(len(frame) == len(SAMPLES) * len(CONTROLS) * len(TARGETS),
            "cross-fit result inventory differs")
    require(not frame.duplicated(["sample", "control", "target"]).any(),
            "cross-fit result rows overlap")
    require(set(frame["sample"]) == set(SAMPLES)
            and set(frame.control) == set(CONTROLS)
            and set(frame.target) == set(TARGETS),
            "cross-fit labels differ")
    maximum_identity_gap = 0.0
    for row in frame.itertuples(index=False):
        expected = row.augmented_q5 - row.baseline_q5
        maximum_identity_gap = max(maximum_identity_gap,
                                   abs(row.conditioning_movement - expected))
        close(row.conditioning_movement, expected)
    for (sample, control), local in frame.groupby(["sample", "control"]):
        indexed = local.set_index("target")
        for quantity in QUANTITIES:
            expected = indexed.at["family_month", quantity] - indexed.at["pooled", quantity]
            maximum_identity_gap = max(
                maximum_identity_gap,
                abs(indexed.at["family_month_minus_pooled", quantity] - expected),
            )
            close(indexed.at["family_month_minus_pooled", quantity], expected)
    indexed = frame.set_index(["sample", "control", "target"])
    for control in CONTROLS:
        for target in TARGETS:
            for quantity in QUANTITIES:
                left = indexed.at[("construct_fold0_estimate_fold1", control, target), quantity]
                right = indexed.at[("construct_fold1_estimate_fold0", control, target), quantity]
                expected = .5 * (left + right)
                actual = indexed.at[("equal_weight_crossfit_average", control, target), quantity]
                maximum_identity_gap = max(maximum_identity_gap, abs(actual - expected))
                close(actual, expected)
            full = indexed.at[("full_in_sample_same_support", control, target),
                              "conditioning_movement"]
            average = indexed.at[("equal_weight_crossfit_average", control, target),
                                 "conditioning_movement"]
            close(indexed.at[("equal_weight_crossfit_average", control, target),
                             "conditioning_movement_minus_full_in_sample"],
                  average - full)
    result = {
        "schema_version": "yax-gate3-shortfall-crossfit-independent-validation-v1",
        "status": "PASS_SHORTFALL_CROSSFIT_PUBLIC_OUTPUT_VALIDATION",
        "result_rows": len(frame),
        "support_occupations": receipt["support_occupations"],
        "maximum_recomputed_identity_gap": maximum_identity_gap,
        "receipt_sha256": sha256_file(receipt_path),
        "result_sha256": sha256_file(args.run_dir / "SHORTFALL_CROSSFIT_RESULTS.csv"),
        "construction_sha256": sha256_file(
            args.run_dir / "SHORTFALL_CROSSFIT_CONSTRUCTION.json"),
    }
    output = args.run_dir / "INDEPENDENT_VALIDATION.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    print(json.dumps({"status": result["status"],
                      "result_rows": len(frame)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
