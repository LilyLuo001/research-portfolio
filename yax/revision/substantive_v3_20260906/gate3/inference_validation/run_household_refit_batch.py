#!/usr/bin/env python3
"""Run a deterministic batch of linked-household Gate 3 full refits."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
HOUSEHOLD_SEED = 202609083000
MODES = ("fixed_labels", "regenerated_preperiod_labels")
TARGETS = ("pooled", "family_month", "family_month_minus_pooled")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CORE = load_module("yax_gate3_household_core", HERE / "inference_engine.py")
ENGINE = load_module(
    "yax_gate3_household_engine",
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


def weighted_labels(exposure: np.ndarray, webb: np.ndarray,
                    weights: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    exposure = np.asarray(exposure, float)
    webb = np.asarray(webb, float)
    weights = np.asarray(weights, float)
    require(exposure.shape == webb.shape == weights.shape and np.all(weights > 0),
            "regenerated label inputs differ")
    order = np.argsort(exposure, kind="mergesort")
    cumulative = np.cumsum(weights[order])
    cuts = np.asarray([
        exposure[order[min(np.searchsorted(cumulative, share * cumulative[-1], side="left"),
                           len(exposure) - 1)]]
        for share in (.2, .4, .6, .8)
    ])
    require(np.all(np.diff(cuts) > 0), "regenerated quintile cuts collapse")
    quintiles = np.searchsorted(cuts, exposure, side="left") + 1
    webb_mean = float(np.average(webb, weights=weights))
    webb_sd = float(np.sqrt(np.average(np.square(webb - webb_mean), weights=weights)))
    require(np.isfinite(webb_sd) and webb_sd > 0, "regenerated Webb scale collapses")
    return quintiles.astype(int), (webb - webb_mean) / webb_sd, {
        "q1_cut": float(cuts[0]), "q2_cut": float(cuts[1]),
        "q3_cut": float(cuts[2]), "q4_cut": float(cuts[3]),
        "webb_mean": webb_mean, "webb_sd": webb_sd,
    }


def cells_from_multiplier(arrays: dict[str, np.ndarray], multiplier: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n_cell = len(arrays["total"])
    route_weight = arrays["route_stock"] * multiplier[arrays["household_code"]]
    rebuilt = np.bincount(arrays["cellage"], weights=route_weight, minlength=2 * n_cell)
    return rebuilt[:n_cell], rebuilt[n_cell:]


def fit_targets(young: np.ndarray, older: np.ndarray,
                arrays: dict[str, np.ndarray], quintiles: np.ndarray,
                webb_z: np.ndarray) -> dict[str, Any]:
    designs = {
        structure: CORE.build_design(
            quintiles, webb_z, arrays["families"], arrays["months"].tolist(), structure)
        for structure in ("pooled", "family_month")
    }
    fits = {
        structure: CORE.fit_with_influence(ENGINE, young, young + older, design)
        for structure, design in designs.items()
    }
    pair = CORE.paired_target(fits["family_month"], fits["pooled"])
    return {
        "pooled": fits["pooled"].estimate,
        "family_month": fits["family_month"].estimate,
        "family_month_minus_pooled": pair["estimate"],
        "pooled_iterations": fits["pooled"].iterations,
        "family_month_iterations": fits["family_month"].iterations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-calibration", type=Path, required=True)
    parser.add_argument("--calibration-receipt", type=Path, required=True)
    parser.add_argument("--start-draw", type=int, required=True)
    parser.add_argument("--draw-count", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    require(args.start_draw >= 1 and 1 <= args.draw_count <= 400,
            "invalid household draw batch")
    require(not args.output_dir.exists(), "refusing to overwrite batch output")
    receipt = json.loads(args.calibration_receipt.read_text(encoding="utf-8"))
    require(receipt.get("status") == "PASS_PRIVATE_CALIBRATION_BUILD",
            "calibration receipt does not pass")
    require(receipt.get("private_npz_sha256") == sha256_file(args.private_calibration),
            "private calibration hash differs")
    with np.load(args.private_calibration, allow_pickle=False) as loaded:
        arrays = {name: loaded[name] for name in loaded.files}
    household_count = int(arrays["household_count"][0])
    require(household_count == receipt["route_counts"]["analysis_contributing_CPSID_units"],
            "household unit count differs")
    require(len(arrays["household_code"]) == len(arrays["route_stock"]) == len(arrays["cellage"]),
            "household route arrays differ")
    observed_young, observed_older = cells_from_multiplier(arrays, np.ones(household_count))
    fixed_observed = fit_targets(
        observed_young, observed_older, arrays, arrays["quintiles"], arrays["webb_z"])
    require(abs(fixed_observed["pooled"] -
                receipt["observed_models"]["pooled"]["coefficient"]) <= 1e-8,
            "household route pooled checkpoint differs")
    require(abs(fixed_observed["family_month"] -
                receipt["observed_models"]["family_month"]["coefficient"]) <= 1e-8,
            "household route family-month checkpoint differs")
    pre = np.asarray([value <= "2022-11" for value in arrays["months"].tolist()], bool)
    observed_construction_weight = (observed_young + observed_older).reshape(
        len(arrays["occupations"]), len(arrays["months"]))[:, pre].sum(axis=1)
    rebuilt_q, rebuilt_webb, _ = weighted_labels(
        arrays["exposure_beta"], arrays["webb_z"], observed_construction_weight)
    require(np.array_equal(rebuilt_q, arrays["quintiles"]),
            "observed regenerated quintiles differ from fixed contract")
    require(np.allclose(rebuilt_webb, arrays["webb_z"], rtol=0, atol=1e-12),
            "observed regenerated Webb normalization differs from fixed contract")

    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    last_draw = args.start_draw + args.draw_count - 1
    for draw in range(args.start_draw, last_draw + 1):
        print(json.dumps({"stage": "household_refit", "draw": draw,
                          "last_draw": last_draw}), flush=True)
        rng = np.random.default_rng(HOUSEHOLD_SEED + draw)
        multiplier = rng.exponential(scale=1.0, size=household_count)
        young, older = cells_from_multiplier(arrays, multiplier)
        construction_weight = (young + older).reshape(len(arrays["occupations"]),
                                                       len(arrays["months"]))[:, pre].sum(axis=1)
        for mode in MODES:
            diagnostics = {"occupations_reclassified": 0}
            if mode == "fixed_labels":
                quintiles, webb_z = arrays["quintiles"], arrays["webb_z"]
            else:
                try:
                    quintiles, webb_z, diagnostics = weighted_labels(
                        arrays["exposure_beta"],
                        # Recover the raw Webb values from the fixed z-score only
                        # up to an affine transform; restandardization is invariant
                        # to that transform and therefore exact for the design.
                        arrays["webb_z"], construction_weight)
                    diagnostics["occupations_reclassified"] = int(
                        np.sum(quintiles != arrays["quintiles"]))
                except Exception as error:
                    failures.append({"draw": draw, "mode": mode,
                                     "stage": "regenerate_labels", "error": repr(error)})
                    continue
            try:
                fitted = fit_targets(young, older, arrays, quintiles, webb_z)
            except Exception as error:
                failures.append({"draw": draw, "mode": mode,
                                 "stage": "joint_full_refit", "error": repr(error)})
                continue
            for target in TARGETS:
                rows.append({
                    "draw": draw, "classification_mode": mode, "target": target,
                    "observed_coefficient": fixed_observed[target],
                    "bootstrap_coefficient": fitted[target],
                    "bootstrap_shift": fitted[target] - fixed_observed[target],
                    "pooled_iterations": fitted["pooled_iterations"],
                    "family_month_iterations": fitted["family_month_iterations"],
                    "occupations_reclassified": diagnostics["occupations_reclassified"],
                    "minimum_household_multiplier": float(multiplier.min()),
                    "maximum_household_multiplier": float(multiplier.max()),
                    "mean_household_multiplier": float(multiplier.mean()),
                })

    args.output_dir.mkdir(parents=True)
    write_csv(args.output_dir / "HOUSEHOLD_REFIT_DRAWS.csv", rows)
    (args.output_dir / "MODEL_FAILURES.json").write_text(
        json.dumps(failures, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    outputs = ["HOUSEHOLD_REFIT_DRAWS.csv", "MODEL_FAILURES.json"]
    batch_receipt = {
        "schema_version": "yax-gate3-household-refit-batch-v1",
        "status": "PASS_HOUSEHOLD_REFIT_BATCH",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                              cwd=ROOT, text=True).strip(),
        "sge_job_id": os.environ.get("JOB_ID"),
        "private_calibration_sha256": receipt["private_npz_sha256"],
        "calibration_receipt_sha256": sha256_file(args.calibration_receipt),
        "start_draw": args.start_draw, "last_draw": last_draw,
        "requested_draws": args.draw_count,
        "successful_mode_target_rows": len(rows), "failure_records": len(failures),
        "fixed_observed_targets": {target: fixed_observed[target] for target in TARGETS},
        "output_hashes": {name: sha256_file(args.output_dir / name) for name in outputs},
        "sampling_unit": "positive CPSID with one mean-one Exponential multiplier across all months and route descendants",
        "design_based_CPS_inference": False,
        "privacy": "outputs contain coefficients and aggregate diagnostics only; no cell, route, household code, microdata row, or private path",
    }
    (args.output_dir / "EXECUTION_RECEIPT.json").write_text(
        json.dumps(batch_receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": batch_receipt["status"], "start": args.start_draw,
                      "last": last_draw, "failures": len(failures)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
