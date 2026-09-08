#!/usr/bin/env python3
"""Independently validate the public I10 HAC matrices and target summaries."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


Z975 = 1.959963984540054
TARGET = 3


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def close(left: float, right: float, tolerance: float = 1e-12) -> None:
    require(math.isclose(float(left), float(right), rel_tol=tolerance, abs_tol=tolerance),
            f"numerical mismatch: {left} versus {right}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    receipt = json.loads((args.run_dir / "EXECUTION_RECEIPT.json").read_text())
    validation = json.loads((args.run_dir / "VALIDATION.json").read_text())
    require(receipt["status"] == "PASS_HAC_EXECUTION", "HAC receipt does not pass")
    require(validation["status"] == "PASS_HAC_CONSTRUCTION", "HAC validation does not pass")
    for name, expected in receipt["output_hashes"].items():
        require(sha256_file(args.run_dir / name) == expected, f"{name} hash differs")

    labels = validation["parameter_order"]
    require(len(labels) == 10 and len(set(labels)) == 10, "parameter order differs")
    covariance = pd.read_csv(args.run_dir / "HAC_JOINT_COVARIANCE.csv")
    summary = pd.read_csv(args.run_dir / "HAC_TARGET_SUMMARY.csv")
    lags = sorted(covariance.lag_elapsed_calendar_months.unique().tolist())
    require(lags == [0, 1, 4, 12, 16], "HAC lag inventory differs")
    targets = {
        "pooled": np.eye(10)[TARGET],
        "family_month": np.eye(10)[5 + TARGET],
        "family_month_minus_pooled": np.eye(10)[5 + TARGET] - np.eye(10)[TARGET],
    }
    maximum_gap = 0.0
    spectra = {}
    for lag in lags:
        local = covariance.loc[covariance.lag_elapsed_calendar_months.eq(lag)]
        require(len(local) == 100, f"lag {lag} covariance inventory differs")
        matrix = local.pivot(index="row_parameter", columns="column_parameter",
                             values="covariance").loc[labels, labels].to_numpy(float)
        symmetry = float(np.max(np.abs(matrix - matrix.T)))
        require(symmetry <= 1e-14, f"lag {lag} covariance is asymmetric")
        eigenvalues = np.linalg.eigvalsh(matrix)
        tolerance = max(1e-12, float(np.max(np.abs(eigenvalues))) * 1e-10)
        spectra[str(lag)] = {
            "rank": int(np.sum(np.abs(eigenvalues) > tolerance)),
            "positive_rank": int(np.sum(eigenvalues > tolerance)),
            "negative_rank": int(np.sum(eigenvalues < -tolerance)),
            "minimum_eigenvalue": float(eigenvalues.min()),
            "maximum_eigenvalue": float(eigenvalues.max()),
            "maximum_symmetry_gap": symmetry,
        }
        for name, vector in targets.items():
            row = summary.loc[
                summary.object.eq(name) & summary.lag_elapsed_calendar_months.eq(lag)]
            require(len(row) == 1, f"{name}/lag {lag} summary inventory differs")
            row = row.iloc[0]
            variance = float(vector @ matrix @ vector)
            close(variance, row.corrected_inclusion_exclusion_variance)
            require(variance >= 0, f"{name}/lag {lag} variance is negative")
            se = math.sqrt(variance)
            close(se, row.corrected_inclusion_exclusion_se)
            close(row.estimate - Z975 * se, row.normal_ci_lower)
            close(row.estimate + Z975 * se, row.normal_ci_upper)
            close(spectra[str(lag)]["minimum_eigenvalue"],
                  row.minimum_joint_covariance_eigenvalue)
            require(spectra[str(lag)]["rank"] == row.joint_covariance_numerical_rank,
                    "reported HAC rank differs")
            require(spectra[str(lag)]["negative_rank"] ==
                    row.joint_covariance_negative_rank,
                    "reported HAC negative rank differs")
            maximum_gap = max(maximum_gap,
                              abs(variance - row.corrected_inclusion_exclusion_variance))
    result = {
        "schema_version": "yax-gate3-hac-independent-validation-v1",
        "status": "PASS_HAC_PUBLIC_OUTPUT_VALIDATION",
        "lags": lags, "targets": list(targets),
        "maximum_recomputed_variance_difference": maximum_gap,
        "spectra": spectra,
        "input_hashes": {
            name: sha256_file(args.run_dir / name)
            for name in ("EXECUTION_RECEIPT.json", "VALIDATION.json",
                         "HAC_JOINT_COVARIANCE.csv", "HAC_TARGET_SUMMARY.csv")
        },
    }
    path = args.run_dir / "INDEPENDENT_VALIDATION.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "lags": len(lags)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
