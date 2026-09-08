#!/usr/bin/env python3
"""Run one linked-household batch with corrected shortfalls regenerated."""
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
import pandas as pd


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
HOUSEHOLD_SEED = 202609083000
BRIDGE_SHA256 = "0bd2f63c72e24bed2cc1cb414395c3cbddf7c00011e47ec1c1de6ae534fd1dcc"
MODES = (
    "fixed_shortfalls_fixed_labels",
    "regenerated_shortfalls_fixed_labels",
    "regenerated_shortfalls_and_labels",
)
CONTROLS = ("total", "young_relative")
TARGETS = ("pooled", "family_month", "family_month_minus_pooled")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CORE = load_module("yax_shortfall_core", HERE.parent / "inference_validation" / "inference_engine.py")
HH = load_module("yax_shortfall_household", HERE.parent / "inference_validation" / "run_household_refit_batch.py")
SHORT = load_module("yax_shortfall_construction", HERE / "shortfall_engine.py")
ENGINE = load_module(
    "yax_shortfall_engine", ROOT / "dax/memo/power_calcs/young_relative_employment_power.py")


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


def fit_collection(young_matrix: np.ndarray, older_matrix: np.ndarray,
                   arrays: dict[str, np.ndarray], support: np.ndarray,
                   quintiles: np.ndarray, webb_z: np.ndarray,
                   controls_z: dict[str, np.ndarray]) -> dict[str, dict[str, Any]]:
    months = arrays["months"].tolist()
    families = arrays["families"][support]
    q = quintiles[support]
    webb = webb_z[support]
    young = SHORT.subset_cells(young_matrix, support)
    older = SHORT.subset_cells(older_matrix, support)
    result: dict[str, dict[str, Any]] = {}
    for control in ("baseline", *CONTROLS):
        fits = {}
        for structure in ("pooled", "family_month"):
            design = CORE.build_design(q, webb, families, months, structure)
            if control != "baseline":
                design = SHORT.augment_design(
                    CORE, design, controls_z[control][support], months, control)
            fits[structure] = CORE.fit_with_influence(
                ENGINE, young, young + older, design)
        records: dict[str, Any] = {}
        for structure, fit in fits.items():
            record = {
                "q5": float(fit.beta[CORE.TARGET_INDEX]),
                "q5_occupation_se": float(np.sqrt(
                    fit.occupation_influence[:, CORE.TARGET_INDEX]
                    @ fit.occupation_influence[:, CORE.TARGET_INDEX])),
                "q5_family_se": float(np.sqrt(
                    fit.family_influence[:, CORE.TARGET_INDEX]
                    @ fit.family_influence[:, CORE.TARGET_INDEX])),
                "iterations": fit.iterations,
                "separated_observations": fit.separated_observation_count,
            }
            if control != "baseline":
                index = len(design.regressor_labels) - 1
                short_occ = fit.occupation_influence[:, index]
                short_fam = fit.family_influence[:, index]
                q_occ = fit.occupation_influence[:, CORE.TARGET_INDEX]
                q_fam = fit.family_influence[:, CORE.TARGET_INDEX]
                record.update({
                    "shortfall_z": float(fit.beta[index]),
                    "shortfall_occupation_se": float(np.sqrt(short_occ @ short_occ)),
                    "shortfall_family_se": float(np.sqrt(short_fam @ short_fam)),
                    "q5_shortfall_occupation_covariance": float(q_occ @ short_occ),
                    "q5_shortfall_family_covariance": float(q_fam @ short_fam),
                })
            records[structure] = record
        paired = {
            "q5": records["family_month"]["q5"] - records["pooled"]["q5"],
            "iterations": max(records["pooled"]["iterations"],
                              records["family_month"]["iterations"]),
            "separated_observations": max(records["pooled"]["separated_observations"],
                                           records["family_month"]["separated_observations"]),
        }
        if control != "baseline":
            paired["shortfall_z"] = (records["family_month"]["shortfall_z"] -
                                      records["pooled"]["shortfall_z"])
        records["family_month_minus_pooled"] = paired
        result[control] = records
    return result


def construction(young_matrix: np.ndarray, older_matrix: np.ndarray,
                 months: list[str], structural_support: np.ndarray,
                 fixed_support: np.ndarray | None = None) -> tuple[dict[str, np.ndarray],
                                                                   np.ndarray, dict[str, Any]]:
    raw = SHORT.corrected_shortfalls(young_matrix, older_matrix, months)
    support = structural_support & raw["finite_support"]
    if fixed_support is not None:
        require(np.array_equal(support, fixed_support),
                "positive household multipliers changed shortfall support")
    z = {}
    scaling = {}
    for control in CONTROLS:
        z[control], scaling[control] = SHORT.weighted_standardize(
            raw[control], raw["pre_weight"], support)
    diagnostics = {
        "support_occupations": int(support.sum()),
        "support_preperiod_weight": float(raw["pre_weight"][support].sum()),
        "total_negative_predictions_before_bound": int(
            raw["total_negative_predictions_before_bound"][support].sum()),
        "share_out_of_bounds_predictions_before_bound": int(
            raw["share_out_of_bounds_predictions_before_bound"][support].sum()),
        "scaling": scaling,
    }
    return z, support, diagnostics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-calibration", type=Path, required=True)
    parser.add_argument("--calibration-receipt", type=Path, required=True)
    parser.add_argument("--bridge", type=Path, required=True)
    parser.add_argument("--start-draw", type=int, required=True)
    parser.add_argument("--draw-count", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    require(args.start_draw >= 1 and 1 <= args.draw_count <= 400,
            "invalid shortfall household batch")
    require(not args.output_dir.exists(), "refusing to overwrite batch output")
    receipt = json.loads(args.calibration_receipt.read_text(encoding="utf-8"))
    require(receipt.get("status") == "PASS_PRIVATE_CALIBRATION_BUILD",
            "calibration receipt does not pass")
    require(receipt.get("private_npz_sha256") == sha256_file(args.private_calibration),
            "private calibration hash differs")
    require(sha256_file(args.bridge) == BRIDGE_SHA256, "occupation bridge hash differs")
    bridge = pd.read_csv(args.bridge, dtype=str)
    with np.load(args.private_calibration, allow_pickle=False) as loaded:
        arrays = {name: loaded[name] for name in loaded.files}
    n_occ, n_month = len(arrays["occupations"]), len(arrays["months"])
    structural_support = SHORT.one_to_one_mask(arrays["occupations"], bridge)
    household_count = int(arrays["household_count"][0])
    require(household_count == receipt["route_counts"]["analysis_contributing_CPSID_units"],
            "household count differs")
    observed_young, observed_older = HH.cells_from_multiplier(
        arrays, np.ones(household_count))
    observed_young = observed_young.reshape(n_occ, n_month)
    observed_older = observed_older.reshape(n_occ, n_month)
    fixed_z, fixed_support, observed_construction = construction(
        observed_young, observed_older, arrays["months"].tolist(), structural_support)
    require(int(fixed_support.sum()) >= 250, "corrected shortfall support is too small")
    fixed_observed = fit_collection(
        observed_young, observed_older, arrays, fixed_support,
        arrays["quintiles"], arrays["webb_z"], fixed_z)
    observed_rows = []
    for control, records in fixed_observed.items():
        for target, values in records.items():
            observed_rows.append({"control": control, "target": target, **values})

    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    last_draw = args.start_draw + args.draw_count - 1
    pre = np.asarray([value <= "2022-11" for value in arrays["months"].tolist()])
    for draw in range(args.start_draw, last_draw + 1):
        if draw == args.start_draw or draw % 10 == 0:
            print(json.dumps({"stage": "shortfall_refit", "draw": draw,
                              "last_draw": last_draw}), flush=True)
        rng = np.random.default_rng(HOUSEHOLD_SEED + draw)
        multiplier = rng.exponential(scale=1.0, size=household_count)
        young, older = HH.cells_from_multiplier(arrays, multiplier)
        young_matrix = young.reshape(n_occ, n_month)
        older_matrix = older.reshape(n_occ, n_month)
        try:
            regenerated_z, support, diagnostics = construction(
                young_matrix, older_matrix, arrays["months"].tolist(),
                structural_support, fixed_support)
            construction_weight = (young_matrix + older_matrix)[:, pre].sum(axis=1)
            regenerated_q, regenerated_webb, label_diagnostics = HH.weighted_labels(
                arrays["exposure_beta"], arrays["webb_z"], construction_weight)
            label_diagnostics["occupations_reclassified"] = int(np.sum(
                regenerated_q != arrays["quintiles"]))
        except Exception as error:
            failures.append({"draw": draw, "mode": "all", "stage": "construction",
                             "error": repr(error)})
            continue
        mode_inputs = {
            "fixed_shortfalls_fixed_labels": (
                arrays["quintiles"], arrays["webb_z"], fixed_z),
            "regenerated_shortfalls_fixed_labels": (
                arrays["quintiles"], arrays["webb_z"], regenerated_z),
            "regenerated_shortfalls_and_labels": (
                regenerated_q, regenerated_webb, regenerated_z),
        }
        for mode, (q, webb, controls_z) in mode_inputs.items():
            try:
                fitted = fit_collection(
                    young_matrix, older_matrix, arrays, support, q, webb, controls_z)
            except Exception as error:
                failures.append({"draw": draw, "mode": mode, "stage": "joint_refits",
                                 "error": repr(error)})
                continue
            for control in CONTROLS:
                scale = (observed_construction["scaling"][control]
                         if mode == "fixed_shortfalls_fixed_labels"
                         else diagnostics["scaling"][control])
                for target in TARGETS:
                    fit = fitted[control][target]
                    base = fitted["baseline"][target]
                    observed_fit = fixed_observed[control][target]
                    observed_base = fixed_observed["baseline"][target]
                    record = {
                        "draw": draw, "mode": mode, "control": control,
                        "target": target,
                        "observed_q5": observed_fit["q5"],
                        "bootstrap_q5": fit["q5"],
                        "q5_shift": fit["q5"] - observed_fit["q5"],
                        "observed_baseline_q5": observed_base["q5"],
                        "bootstrap_baseline_q5": base["q5"],
                        "observed_conditioning_movement": (
                            observed_fit["q5"] - observed_base["q5"]),
                        "bootstrap_conditioning_movement": fit["q5"] - base["q5"],
                        "conditioning_movement_shift": (
                            (fit["q5"] - base["q5"]) -
                            (observed_fit["q5"] - observed_base["q5"])),
                        "observed_shortfall_z_coefficient": observed_fit["shortfall_z"],
                        "bootstrap_shortfall_z_coefficient": fit["shortfall_z"],
                        "shortfall_z_coefficient_shift": (
                            fit["shortfall_z"] - observed_fit["shortfall_z"]),
                        "observed_shortfall_raw_coefficient": (
                            observed_fit["shortfall_z"] /
                            observed_construction["scaling"][control]["weighted_sd"]),
                        "bootstrap_shortfall_raw_coefficient": (
                            fit["shortfall_z"] / scale["weighted_sd"]),
                        "support_occupations": int(support.sum()),
                        "occupations_reclassified": label_diagnostics[
                            "occupations_reclassified"],
                        "shortfall_weighted_mean": scale["weighted_mean"],
                        "shortfall_weighted_sd": scale["weighted_sd"],
                        "fit_iterations": fit["iterations"],
                        "baseline_iterations": base["iterations"],
                    }
                    record["shortfall_raw_coefficient_shift"] = (
                        record["bootstrap_shortfall_raw_coefficient"] -
                        record["observed_shortfall_raw_coefficient"])
                    rows.append(record)

    args.output_dir.mkdir(parents=True)
    write_csv(args.output_dir / "SHORTFALL_REFIT_DRAWS.csv", rows)
    write_csv(args.output_dir / "OBSERVED_CORRECTED_SHORTFALL_MODELS.csv", observed_rows)
    (args.output_dir / "OBSERVED_CONSTRUCTION.json").write_text(
        json.dumps(observed_construction, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "MODEL_FAILURES.json").write_text(
        json.dumps(failures, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    outputs = ["SHORTFALL_REFIT_DRAWS.csv", "OBSERVED_CORRECTED_SHORTFALL_MODELS.csv",
               "OBSERVED_CONSTRUCTION.json", "MODEL_FAILURES.json"]
    batch_receipt = {
        "schema_version": "yax-gate3-shortfall-refit-batch-v1",
        "status": "PASS_SHORTFALL_REFIT_BATCH" if not failures else "SHORTFALL_REFIT_FAILURES_RETAINED",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                              cwd=ROOT, text=True).strip(),
        "sge_job_id": os.environ.get("JOB_ID"),
        "private_calibration_sha256": receipt["private_npz_sha256"],
        "calibration_receipt_sha256": sha256_file(args.calibration_receipt),
        "bridge_sha256": sha256_file(args.bridge),
        "start_draw": args.start_draw, "last_draw": last_draw,
        "requested_draws": args.draw_count, "successful_rows": len(rows),
        "failure_records": len(failures), "support_occupations": int(fixed_support.sum()),
        "output_hashes": {name: sha256_file(args.output_dir / name) for name in outputs},
        "sampling_unit": "positive CPSID multiplier common across months, co-residents, and route descendants",
        "privacy": "outputs contain coefficients and aggregate diagnostics only; protected cells and household codes remain on SCC",
    }
    (args.output_dir / "EXECUTION_RECEIPT.json").write_text(
        json.dumps(batch_receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": batch_receipt["status"], "start": args.start_draw,
                      "last": last_draw, "failures": len(failures)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
