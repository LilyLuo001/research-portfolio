#!/usr/bin/env python3
"""Combine household-refit batches and quantify interval endpoint MC error."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


MODES = ("fixed_labels", "regenerated_preperiod_labels")
TARGETS = ("pooled", "family_month", "family_month_minus_pooled")
ENDPOINT_BOOTSTRAP_DRAWS = 1999
ENDPOINT_SEED = 202609084000
ENDPOINT_MCSE_TARGET = 0.01


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    require(bool(rows), f"refusing to write empty {path.name}")
    fields: list[str] = []
    for row in rows:
        fields.extend(key for key in row if key not in fields)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def endpoint_monte_carlo_error(shifts: np.ndarray, seed: int) -> dict[str, float]:
    shifts = np.asarray(shifts, float)
    require(len(shifts) >= 199, "too few household draws for endpoint audit")
    rng = np.random.default_rng(seed)
    quantiles = np.empty((ENDPOINT_BOOTSTRAP_DRAWS, 2))
    for index in range(ENDPOINT_BOOTSTRAP_DRAWS):
        sample = shifts[rng.integers(0, len(shifts), size=len(shifts))]
        quantiles[index] = np.quantile(sample, [.025, .975])
    return {
        "shift_q025_mcse": float(np.std(quantiles[:, 0], ddof=1)),
        "shift_q975_mcse": float(np.std(quantiles[:, 1], ddof=1)),
        "bootstrap_of_bootstrap_draws": ENDPOINT_BOOTSTRAP_DRAWS,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-root", type=Path, required=True)
    parser.add_argument("--through-draw", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output_dir.exists(), "refusing to overwrite household summary")
    receipt_paths = sorted(args.batch_root.glob("*/EXECUTION_RECEIPT.json"))
    require(bool(receipt_paths), "no household batch receipts found")
    frames = []
    receipt_hashes = {}
    inventory: list[tuple[int, int]] = []
    for path in receipt_paths:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        require(receipt.get("status") == "PASS_HOUSEHOLD_REFIT_BATCH",
                "household batch does not pass")
        draws_path = path.parent / "HOUSEHOLD_REFIT_DRAWS.csv"
        require(receipt["output_hashes"]["HOUSEHOLD_REFIT_DRAWS.csv"] == sha256_file(draws_path),
                "household batch draw hash differs")
        frame = pd.read_csv(draws_path)
        frame = frame.loc[frame.draw.le(args.through_draw)].copy()
        if not frame.empty:
            frames.append(frame)
        inventory.append((int(receipt["start_draw"]), int(receipt["last_draw"])))
        receipt_hashes[path.parent.name] = sha256_file(path)
    combined = pd.concat(frames, ignore_index=True)
    require(not combined.duplicated(["draw", "classification_mode", "target"]).any(),
            "household batch draws overlap")
    expected_draws = set(range(1, args.through_draw + 1))
    observed_draws = set(combined.draw.astype(int).unique().tolist())
    missing_draws = sorted(expected_draws - observed_draws)
    summaries: list[dict[str, Any]] = []
    endpoint_errors = []
    for mode_index, mode in enumerate(MODES):
        for target_index, target in enumerate(TARGETS):
            local = combined.loc[
                combined.classification_mode.eq(mode) & combined.target.eq(target)
            ].sort_values("draw")
            shifts = local.bootstrap_shift.to_numpy(float)
            require(len(shifts) >= 199, f"too few successful draws for {mode}/{target}")
            observed = float(local.observed_coefficient.iloc[0])
            require(np.allclose(local.observed_coefficient, observed, rtol=0, atol=1e-12),
                    "observed household target moves across batches")
            q025, q975 = np.quantile(shifts, [.025, .975])
            endpoint = endpoint_monte_carlo_error(
                shifts, ENDPOINT_SEED + mode_index * 10 + target_index)
            endpoint_errors.extend([endpoint["shift_q025_mcse"], endpoint["shift_q975_mcse"]])
            summaries.append({
                "classification_mode": mode, "target": target,
                "observed_coefficient": observed,
                "requested_draws": args.through_draw,
                "successful_full_refits": len(shifts),
                "failed_or_missing_draws": args.through_draw - len(shifts),
                "sampling_sensitivity_se": float(np.std(shifts, ddof=1)),
                "mean_full_refit_shift": float(np.mean(shifts)),
                "basic_ci_lower": float(observed - q975),
                "basic_ci_upper": float(observed - q025),
                **endpoint,
                "endpoint_mcse_target": ENDPOINT_MCSE_TARGET,
                "endpoint_mcse_pass": max(endpoint["shift_q025_mcse"],
                                           endpoint["shift_q975_mcse"]) <= ENDPOINT_MCSE_TARGET,
                "design_based_CPS_interval": False,
                "mechanically_combined_with_cluster_variance": False,
            })
    stopping = {
        "through_draw": args.through_draw,
        "maximum_interval_endpoint_mcse": max(endpoint_errors),
        "endpoint_mcse_target": ENDPOINT_MCSE_TARGET,
        "passes": max(endpoint_errors) <= ENDPOINT_MCSE_TARGET,
        "cap_reached": args.through_draw >= 1999,
        "missing_any_mode_draws": missing_draws,
    }
    args.output_dir.mkdir(parents=True)
    write_csv(args.output_dir / "HOUSEHOLD_REFIT_SUMMARY.csv", summaries)
    (args.output_dir / "HOUSEHOLD_STOPPING.json").write_text(
        json.dumps(stopping, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt = {
        "schema_version": "yax-gate3-household-refit-summary-v1",
        "status": ("PASS_HOUSEHOLD_ENDPOINT_PRECISION" if stopping["passes"]
                   else "HOUSEHOLD_ENDPOINT_PRECISION_UNRESOLVED"),
        "through_draw": args.through_draw, "batch_ranges": inventory,
        "batch_receipt_hashes": receipt_hashes,
        "stopping": stopping,
        "interpretation": "linked-household released-weight sensitivity, not CPS design-based inference",
    }
    (args.output_dir / "SUMMARY_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"],
                      "through_draw": args.through_draw,
                      "maximum_endpoint_mcse": max(endpoint_errors)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
