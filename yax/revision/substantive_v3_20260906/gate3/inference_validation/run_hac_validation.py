#!/usr/bin/env python3
"""Validate elapsed-calendar inclusion--exclusion HAC for current Gate 2 targets."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
AGGREGATE_CELLS_SHA256 = "5e10dabf78b1b1cbc8b6aa9f8745435224b9fe3cb078e73cd9d9e27a9c292717"
LAGS = (0, 1, 4, 12, 16)
TARGET = 3
LABELS = ("Q2_x_post", "Q3_x_post", "Q4_x_post", "Q5_x_post", "Webb_z_x_post")
Z975 = 1.959963984540054


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CORE = load_module("yax_gate3_hac_core", HERE / "inference_engine.py")
CAL = load_module("yax_gate3_hac_calibration", HERE / "build_private_calibration.py")
ENGINE = load_module(
    "yax_gate3_hac_engine",
    ROOT / "dax/memo/power_calcs/young_relative_employment_power.py",
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


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    require(bool(rows), f"refusing to write empty {path.name}")
    fields: list[str] = []
    for row in rows:
        fields.extend(key for key in row if key not in fields)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def month_number(value: str) -> int:
    year, month = (int(part) for part in value.split("-"))
    return year * 12 + month - 1


def full_calendar_positions(months: list[str]) -> tuple[list[str], np.ndarray]:
    numbers = np.asarray([month_number(value) for value in months], int)
    require(np.all(np.diff(numbers) > 0), "observed months are not increasing")
    full_numbers = np.arange(numbers[0], numbers[-1] + 1)
    full = [f"{value // 12:04d}-{value % 12 + 1:02d}" for value in full_numbers]
    lookup = {value: index for index, value in enumerate(full_numbers.tolist())}
    return full, np.asarray([lookup[value] for value in numbers], int)


def newey_west_meat(scores: np.ndarray, lag: int) -> np.ndarray:
    scores = np.asarray(scores, float)
    require(scores.ndim == 2 and lag >= 0, "invalid HAC score array or lag")
    meat = scores.T @ scores
    for distance in range(1, lag + 1):
        weight = 1.0 - distance / (lag + 1.0)
        cross = scores[distance:].T @ scores[:-distance]
        meat += weight * (cross + cross.T)
    return (meat + meat.T) / 2.0


def row_influence_cube(fit: CORE.FitArtifacts, young: np.ndarray, total: np.ndarray,
                       design: CORE.ModelDesign, engine: Any) -> np.ndarray:
    young = np.asarray(young, float).reshape(-1)
    total = np.asarray(total, float).reshape(-1)
    active = total > 0
    first, n_first = CORE._active_contiguous(design.first_labels, active)
    second, n_second = CORE._active_contiguous(design.second_labels, active)
    probability = fit.fitted_probability[active]
    residual = young[active] - total[active] * probability
    weight = np.maximum(total[active] * probability * (1 - probability), 1e-12)
    rx = engine._weighted_absorb(
        design.regressors[active], weight, first[active], second[active], n_first, n_second)
    information = rx.T @ (weight[:, None] * rx)
    bread = np.linalg.inv(information)
    row_influence = (rx * residual[:, None]) @ bread.T
    n_occ = int(design.occupation_codes.max()) + 1
    n_month = len(total) // n_occ
    cube = np.zeros((n_occ, n_month, len(LABELS)))
    row_number = np.arange(len(total), dtype=int)[active]
    np.add.at(cube, (design.occupation_codes[active], row_number % n_month), row_influence)
    rebuilt = cube.sum(axis=1) * math.sqrt(
        fit.active_occupation_count / (fit.active_occupation_count - 1.0))
    require(np.allclose(rebuilt, fit.occupation_influence, rtol=1e-8, atol=1e-11),
            "cell influence does not reproduce occupation influence")
    return cube


def covariance_components(cube: np.ndarray, months: list[str], lag: int) -> dict[str, Any]:
    n_occ, _, parameter_count = cube.shape
    full_months, positions = full_calendar_positions(months)
    full = np.zeros((n_occ, len(full_months), parameter_count))
    full[:, positions, :] = cube
    occupation_scores = full.sum(axis=1)
    aggregate_time_scores = full.sum(axis=0)
    occupation_meat = occupation_scores.T @ occupation_scores
    aggregate_hac = newey_west_meat(aggregate_time_scores, lag)
    within_occupation_hac = sum(
        (newey_west_meat(full[index], lag) for index in range(n_occ)),
        start=np.zeros((parameter_count, parameter_count)),
    )
    combined = occupation_meat + aggregate_hac - within_occupation_hac
    combined = (combined + combined.T) / 2.0
    covariance = n_occ / (n_occ - 1.0) * combined
    covariance = (covariance + covariance.T) / 2.0
    return {
        "full_months": full_months, "positions": positions,
        "occupation_meat": occupation_meat, "aggregate_hac": aggregate_hac,
        "within_occupation_hac": within_occupation_hac,
        "combined": combined, "covariance": covariance,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aggregate-cells", type=Path, required=True)
    parser.add_argument("--timing-model-results", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output_dir.exists(), "refusing to overwrite HAC output")
    require(sha256_file(args.aggregate_cells) == AGGREGATE_CELLS_SHA256,
            "aggregate-cell hash differs")
    frame = CAL.stable_aggregate(args.aggregate_cells)
    stable = frame.groupby("occ_code", as_index=False).first().sort_values("occ_code")
    months = sorted(frame.month.unique().tolist())
    young = CAL.array_from_aggregate(frame, "young").reshape(-1)
    older = CAL.array_from_aggregate(frame, "older").reshape(-1)
    total = young + older
    designs = {
        name: CORE.build_design(
            stable.beta_quintile.to_numpy(int), stable.webb_z.to_numpy(float),
            stable.family.astype(str).to_numpy(object), months, name)
        for name in ("pooled", "family_month")
    }
    fits = {name: CORE.fit_with_influence(ENGINE, young, total, design)
            for name, design in designs.items()}
    timing = pd.read_csv(args.timing_model_results).set_index("model_id")
    checkpoints = {
        "pooled": fits["pooled"].estimate -
        float(timing.at["baseline_full_unconditioned", "coefficient"]),
        "family_month": fits["family_month"].estimate -
        float(timing.at["baseline_full_family_month", "coefficient"]),
    }
    require(max(abs(value) for value in checkpoints.values()) <= 1e-6,
            "HAC fit differs from certified central checkpoint")
    cubes = {name: row_influence_cube(fits[name], young, total, designs[name], ENGINE)
             for name in designs}
    block_cube = np.concatenate([cubes["pooled"], cubes["family_month"]], axis=2)
    contrast = np.zeros(10)
    contrast[TARGET] = -1.0
    contrast[5 + TARGET] = 1.0
    summaries: list[dict[str, Any]] = []
    matrix_rows: list[dict[str, Any]] = []
    labels = [f"pooled::{label}" for label in LABELS] + [
        f"family_month::{label}" for label in LABELS]
    estimates = {
        "pooled": fits["pooled"].estimate,
        "family_month": fits["family_month"].estimate,
        "family_month_minus_pooled": fits["family_month"].estimate - fits["pooled"].estimate,
    }
    for lag in LAGS:
        component = covariance_components(block_cube, months, lag)
        covariance = component["covariance"]
        symmetry_gap = float(np.max(np.abs(covariance - covariance.T)))
        eigenvalues = np.linalg.eigvalsh(covariance)
        tolerance = max(1e-12, float(np.max(np.abs(eigenvalues))) * 1e-10)
        numerical_rank = int(np.sum(np.abs(eigenvalues) > tolerance))
        positive_rank = int(np.sum(eigenvalues > tolerance))
        negative_rank = int(np.sum(eigenvalues < -tolerance))
        omitted = sorted(set(component["full_months"]) - set(months))
        require(omitted == ["2022-12", "2025-10"],
                "elapsed-calendar placeholder inventory differs")
        for row_index, row_label in enumerate(labels):
            for column_index, column_label in enumerate(labels):
                matrix_rows.append({
                    "lag_elapsed_calendar_months": lag,
                    "row_parameter": row_label, "column_parameter": column_label,
                    "covariance": float(covariance[row_index, column_index]),
                })
        target_vectors = {
            "pooled": np.eye(10)[TARGET],
            "family_month": np.eye(10)[5 + TARGET],
            "family_month_minus_pooled": contrast,
        }
        for name, vector in target_vectors.items():
            variance = float(vector @ covariance @ vector)
            se = math.sqrt(variance) if variance >= 0 else None
            summaries.append({
                "object": name, "lag_elapsed_calendar_months": lag,
                "estimate": estimates[name],
                "corrected_inclusion_exclusion_variance": variance,
                "corrected_inclusion_exclusion_se": se,
                "normal_ci_lower": estimates[name] - Z975 * se if se is not None else None,
                "normal_ci_upper": estimates[name] + Z975 * se if se is not None else None,
                "full_calendar_months": len(component["full_months"]),
                "observed_model_months": len(months),
                "zero_placeholder_months": len(component["full_months"]) - len(months),
                "zero_placeholder_labels": ";".join(omitted),
                "maximum_symmetry_gap": symmetry_gap,
                "joint_covariance_numerical_rank": numerical_rank,
                "joint_covariance_positive_rank": positive_rank,
                "joint_covariance_negative_rank": negative_rank,
                "minimum_joint_covariance_eigenvalue": float(eigenvalues.min()),
                "maximum_joint_covariance_eigenvalue": float(eigenvalues.max()),
                "negative_joint_eigenvalues_at_scaled_tolerance": negative_rank,
                "eigenvalue_tolerance": tolerance,
                "PSD_projection_applied": False,
            })
    args.output_dir.mkdir(parents=True)
    write_csv(args.output_dir / "HAC_TARGET_SUMMARY.csv", summaries)
    write_csv(args.output_dir / "HAC_JOINT_COVARIANCE.csv", matrix_rows)
    validation = {
        "schema_version": "yax-gate3-hac-validation-v1",
        "status": "PASS_HAC_CONSTRUCTION",
        "lags": list(LAGS), "parameter_order": labels,
        "coefficient_checkpoint_differences": checkpoints,
        "calendar": {"observed_months": len(months), "full_elapsed_months": 115,
                     "gaps": ["2022-12", "2025-10"]},
        "formula": "occupation meat + aggregate elapsed-month Bartlett HAC - within-occupation elapsed-month Bartlett HAC; one occupation CRV1 factor after combination",
        "cross_model_blocks_included": True,
        "matrix_clipping_or_projection": False,
    }
    (args.output_dir / "VALIDATION.json").write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    outputs = ["HAC_TARGET_SUMMARY.csv", "HAC_JOINT_COVARIANCE.csv", "VALIDATION.json"]
    receipt = {
        "schema_version": "yax-gate3-hac-execution-receipt-v1",
        "status": "PASS_HAC_EXECUTION",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                              cwd=ROOT, text=True).strip(),
        "sge_job_id": os.environ.get("JOB_ID"),
        "aggregate_cells_sha256": AGGREGATE_CELLS_SHA256,
        "timing_model_results_sha256": sha256_file(args.timing_model_results),
        "output_hashes": {name: sha256_file(args.output_dir / name) for name in outputs},
        "privacy": "aggregate coefficient covariance and diagnostics only; no cell stock or private path",
    }
    (args.output_dir / "EXECUTION_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "lags": len(LAGS),
                      "objects": 3}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
