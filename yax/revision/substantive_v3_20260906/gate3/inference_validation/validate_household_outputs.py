#!/usr/bin/env python3
"""Independently validate public linked-household refit batches and summary."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


MODES = ("fixed_labels", "regenerated_preperiod_labels")
TARGETS = ("pooled", "family_month", "family_month_minus_pooled")
ENDPOINT_DRAWS = 1999
ENDPOINT_SEED = 202609084000


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def endpoint_error(shifts: np.ndarray, seed: int) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    quantiles = np.empty((ENDPOINT_DRAWS, 2))
    for index in range(ENDPOINT_DRAWS):
        sample = shifts[rng.integers(0, len(shifts), size=len(shifts))]
        quantiles[index] = np.quantile(sample, [.025, .975])
    return tuple(np.std(quantiles, axis=0, ddof=1).tolist())


def close(left: float, right: float, tolerance: float = 1e-12) -> None:
    require(math.isclose(float(left), float(right), rel_tol=tolerance, abs_tol=tolerance),
            f"numerical mismatch: {left} versus {right}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    frames = []
    ranges = []
    batch_hashes = {}
    for directory in sorted(args.run_dir.glob("batch_*")):
        receipt_path = directory / "EXECUTION_RECEIPT.json"
        if not receipt_path.exists():
            continue
        receipt = json.loads(receipt_path.read_text())
        require(receipt["status"] == "PASS_HOUSEHOLD_REFIT_BATCH",
                f"{directory.name} receipt does not pass")
        for name, expected in receipt["output_hashes"].items():
            require(sha256_file(directory / name) == expected,
                    f"{directory.name}/{name} hash differs")
        failures = json.loads((directory / "MODEL_FAILURES.json").read_text())
        require(failures == [] and receipt["failure_records"] == 0,
                f"{directory.name} contains refit failures")
        frame = pd.read_csv(directory / "HOUSEHOLD_REFIT_DRAWS.csv")
        require(len(frame) == receipt["requested_draws"] * len(MODES) * len(TARGETS),
                f"{directory.name} row inventory differs")
        frames.append(frame)
        ranges.append((receipt["start_draw"], receipt["last_draw"]))
        batch_hashes[directory.name] = sha256_file(receipt_path)
    combined = pd.concat(frames, ignore_index=True)
    require(not combined.duplicated(["draw", "classification_mode", "target"]).any(),
            "household draws overlap")
    require(set(combined.draw.astype(int)) == set(range(1, 400)),
            "household draw inventory differs")
    summary_dir = args.run_dir / "summary_0399"
    summary = pd.read_csv(summary_dir / "HOUSEHOLD_REFIT_SUMMARY.csv")
    stopping = json.loads((summary_dir / "HOUSEHOLD_STOPPING.json").read_text())
    receipt = json.loads((summary_dir / "SUMMARY_RECEIPT.json").read_text())
    require(receipt["status"] == "PASS_HOUSEHOLD_ENDPOINT_PRECISION",
            "household summary receipt does not pass")
    maximum_endpoint_error = 0.0
    maximum_summary_gap = 0.0
    for mode_index, mode in enumerate(MODES):
        for target_index, target in enumerate(TARGETS):
            local = combined.loc[
                combined.classification_mode.eq(mode) & combined.target.eq(target)
            ].sort_values("draw")
            require(len(local) == 399, f"{mode}/{target} draw inventory differs")
            row = summary.loc[
                summary.classification_mode.eq(mode) & summary.target.eq(target)]
            require(len(row) == 1, f"{mode}/{target} summary inventory differs")
            row = row.iloc[0]
            shifts = local.bootstrap_shift.to_numpy(float)
            observed = float(local.observed_coefficient.iloc[0])
            require(np.allclose(local.observed_coefficient, observed, rtol=0, atol=1e-12),
                    "observed coefficient changes across draws")
            q025, q975 = np.quantile(shifts, [.025, .975])
            values = {
                "observed_coefficient": observed,
                "sampling_sensitivity_se": float(np.std(shifts, ddof=1)),
                "mean_full_refit_shift": float(np.mean(shifts)),
                "basic_ci_lower": float(observed - q975),
                "basic_ci_upper": float(observed - q025),
            }
            for name, value in values.items():
                gap = abs(float(row[name]) - value)
                maximum_summary_gap = max(maximum_summary_gap, gap)
                close(row[name], value)
            lower_mcse, upper_mcse = endpoint_error(
                shifts, ENDPOINT_SEED + mode_index * 10 + target_index)
            close(row.shift_q025_mcse, lower_mcse)
            close(row.shift_q975_mcse, upper_mcse)
            maximum_endpoint_error = max(maximum_endpoint_error,
                                         lower_mcse, upper_mcse)
    close(stopping["maximum_interval_endpoint_mcse"], maximum_endpoint_error)
    require(maximum_endpoint_error <= stopping["endpoint_mcse_target"],
            "household endpoint precision does not pass")
    result = {
        "schema_version": "yax-gate3-household-independent-validation-v1",
        "status": "PASS_HOUSEHOLD_PUBLIC_OUTPUT_VALIDATION",
        "draws": 399, "modes": list(MODES), "targets": list(TARGETS),
        "batch_ranges": ranges, "batch_receipt_hashes": batch_hashes,
        "maximum_recomputed_summary_difference": maximum_summary_gap,
        "maximum_recomputed_endpoint_mcse": maximum_endpoint_error,
        "summary_hashes": {
            name: sha256_file(summary_dir / name)
            for name in ("HOUSEHOLD_REFIT_SUMMARY.csv", "HOUSEHOLD_STOPPING.json",
                         "SUMMARY_RECEIPT.json")
        },
    }
    path = summary_dir / "INDEPENDENT_VALIDATION.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "draws": 399}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
