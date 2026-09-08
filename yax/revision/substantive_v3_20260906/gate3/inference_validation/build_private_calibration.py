#!/usr/bin/env python3
"""Build a protected Gate 3 calibration object and a sanitized receipt.

The NPZ contains aggregate cells, effective-count ingredients, calibrated
shock paths, and encoded household routes.  It remains on SCC.  The public
receipt contains hashes and aggregate diagnostics only.
"""
from __future__ import annotations

import argparse
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
WIDE_SHA256 = "3fe42477e6f2ce401e85123f0e278e758595c1c4071a8743f243a92752db38c9"
REPAIR_SHA256 = "a4ae2ef06d66a0d47359ccceffff9a15843ac501a9f25f9a05aa8fdca9c4f911"
BRIDGE_SHA256 = "0bd2f63c72e24bed2cc1cb414395c3cbddf7c00011e47ec1c1de6ae534fd1dcc"
COMPUTERIZATION_SHA256 = "352cb40834ec83225f747d316eb3e03fce1d1c5c65d80720c558177f85801fdd"
TREATMENT_CONTRACT_SHA256 = "95db83635da57b58db98217c96bf85c40aa0249146031db23cfa1221d11804b6"
MARCH_RECEIPT_SHA256 = "b2e1810c1f154f8efd290ccc65a155a6553642fb03d76fd818d7348e98bb3b8a"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CORE = load_module("yax_gate3_calibration_core", HERE / "inference_engine.py")
OLD = load_module(
    "yax_gate3_historical_survey_runner",
    ROOT / "yax/revision/substantive_r3_20260905/survey_sim/run_inf03_inf05.py",
)
ENGINE = OLD.ENGINE


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def verify_file(path: Path, expected: str, label: str) -> str:
    require(path.is_file() and not path.is_symlink(), f"{label} is absent or indirect")
    observed = sha256_file(path)
    require(observed == expected, f"{label} hash differs")
    return observed


def stable_aggregate(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype={"occ_code": str}, float_precision="round_trip")
    required = {"occ_code", "month", "family", "young", "older",
                "beta_quintile", "webb_z"}
    require(set(frame) == required, "aggregate-cell schema differs")
    frame["occ_code"] = frame.occ_code.str.zfill(4)
    frame = frame.loc[frame.month.ne("2022-12")].copy()
    frame = frame.sort_values(["occ_code", "month"], kind="mergesort").reset_index(drop=True)
    stable = frame.groupby("occ_code", as_index=False).agg(
        family=("family", "first"), family_n=("family", "nunique"),
        quintile=("beta_quintile", "first"), quintile_n=("beta_quintile", "nunique"),
        webb_z=("webb_z", "first"), webb_n=("webb_z", "nunique"),
    )
    require(len(stable) == 468, "aggregate support is not 468 occupations")
    require((stable[["family_n", "quintile_n", "webb_n"]] == 1).all().all(),
            "aggregate treatment attributes move over time")
    months = sorted(frame.month.astype(str).unique().tolist())
    require(len(months) == 113 and "2022-12" not in months and "2025-10" not in months,
            "aggregate analysis calendar differs")
    require(len(frame) == 468 * 113, "aggregate panel is not balanced")
    return frame


def array_from_aggregate(frame: pd.DataFrame, field: str) -> np.ndarray:
    occupations = sorted(frame.occ_code.unique().tolist())
    months = sorted(frame.month.unique().tolist())
    pivot = frame.pivot(index="occ_code", columns="month", values=field)
    return pivot.reindex(index=occupations, columns=months).to_numpy(float)


def calibrated_family_path(pooled: CORE.FitArtifacts, total: np.ndarray,
                           design: CORE.ModelDesign, family_count: int,
                           month_count: int) -> tuple[np.ndarray, np.ndarray]:
    active = total > 0
    probability = pooled.fitted_probability[active]
    residual = pooled.residual[active]
    information = total[active] * probability * (1.0 - probability)
    code = design.family_codes[active] * month_count + (
        np.arange(len(total), dtype=int)[active] % month_count)
    numerator = np.bincount(code, weights=residual,
                            minlength=family_count * month_count)
    denominator = np.bincount(code, weights=information,
                              minlength=family_count * month_count)
    raw = np.divide(numerator, denominator, out=np.zeros_like(numerator),
                    where=denominator > 0)
    family = np.repeat(np.arange(family_count), month_count)
    month = np.tile(np.arange(month_count), family_count)
    positive = denominator > 0
    require(np.all(positive), "a family-month calibration cell has no information")
    residualized = ENGINE._weighted_absorb(
        raw[:, None], denominator, family, month, family_count, month_count,
    )[:, 0].reshape(family_count, month_count)
    return residualized, denominator.reshape(family_count, month_count)


def summarize_effective_counts(value: np.ndarray) -> dict[str, Any]:
    positive = np.asarray(value, float)[np.asarray(value, float) > 0]
    return {
        "positive_cells": int(len(positive)),
        "minimum": float(positive.min()),
        "p01": float(np.quantile(positive, .01)),
        "p05": float(np.quantile(positive, .05)),
        "median": float(np.median(positive)),
        "p95": float(np.quantile(positive, .95)),
        "below_5": int(np.sum(positive < 5)),
        "below_10": int(np.sum(positive < 10)),
        "below_20": int(np.sum(positive < 20)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aggregate-cells", type=Path, required=True)
    parser.add_argument("--microdata", type=Path, required=True)
    parser.add_argument("--repair-microdata", type=Path, required=True)
    parser.add_argument("--bridge", type=Path, required=True)
    parser.add_argument("--computerization", type=Path, required=True)
    parser.add_argument("--treatment-contract", type=Path, required=True)
    parser.add_argument("--march-audit-receipt", type=Path, required=True)
    parser.add_argument("--timing-model-results", type=Path, required=True)
    parser.add_argument("--output-npz", type=Path, required=True)
    parser.add_argument("--output-receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output_npz.exists() and not args.output_receipt.exists(),
            "refusing to overwrite calibration output")

    expected = {
        "aggregate_cells": (args.aggregate_cells, AGGREGATE_CELLS_SHA256),
        "wide_microdata": (args.microdata, WIDE_SHA256),
        "march_repair": (args.repair_microdata, REPAIR_SHA256),
        "bridge": (args.bridge, BRIDGE_SHA256),
        "computerization": (args.computerization, COMPUTERIZATION_SHA256),
        "treatment_contract": (args.treatment_contract, TREATMENT_CONTRACT_SHA256),
        "march_audit_receipt": (args.march_audit_receipt, MARCH_RECEIPT_SHA256),
    }
    hashes = {label: verify_file(path, digest, label)
              for label, (path, digest) in expected.items()}

    aggregate = stable_aggregate(args.aggregate_cells)
    contract = OLD.load_contract(args.treatment_contract, args.computerization)
    routes = OLD.build_route_contributions(args, contract)
    months = routes["months"]
    occupations = contract["support"]
    require(months == sorted(aggregate.month.unique().tolist()), "route months differ")
    require(occupations == sorted(aggregate.occ_code.unique().tolist()), "route support differs")
    young = routes["young"]
    older = routes["older"]
    aggregate_young = array_from_aggregate(aggregate, "young")
    aggregate_older = array_from_aggregate(aggregate, "older")
    absolute_gap = float(max(np.max(np.abs(young - aggregate_young)),
                             np.max(np.abs(older - aggregate_older))))
    relative_gap = float(max(
        np.max(np.abs(young - aggregate_young) / np.maximum(aggregate_young, 1.0)),
        np.max(np.abs(older - aggregate_older) / np.maximum(aggregate_older, 1.0)),
    ))
    require(relative_gap <= 1e-10, "microdata route rebuild differs from Gate 2 cells")

    total_matrix = young + older
    total = total_matrix.reshape(-1)
    sum_square = (routes["w2_young"] + routes["w2_older"]).reshape(-1)
    effective = np.divide(np.square(total), sum_square, out=np.zeros_like(total),
                          where=sum_square > 0)
    effective_integer = np.where(total > 0,
                                 np.maximum(1, np.rint(effective).astype(np.int64)), 0)
    require(np.array_equal(effective_integer > 0, total > 0),
            "effective-count support differs")

    stable = aggregate.groupby("occ_code", as_index=False).first().sort_values("occ_code")
    quintiles = stable.beta_quintile.to_numpy(int)
    webb_z = stable.webb_z.to_numpy(float)
    families = stable.family.astype(str).to_numpy(object)
    pooled_design = CORE.build_design(quintiles, webb_z, families, months, "pooled")
    family_design = CORE.build_design(quintiles, webb_z, families, months, "family_month")
    pooled = CORE.fit_with_influence(ENGINE, young.reshape(-1), total, pooled_design)
    family_month = CORE.fit_with_influence(ENGINE, young.reshape(-1), total, family_design)
    paired = CORE.paired_target(family_month, pooled)

    timing = pd.read_csv(args.timing_model_results).set_index("model_id")
    expected_pooled = float(timing.at["baseline_full_unconditioned", "coefficient"])
    expected_family = float(timing.at["baseline_full_family_month", "coefficient"])
    checkpoint = {
        "pooled_difference": pooled.estimate - expected_pooled,
        "family_month_difference": family_month.estimate - expected_family,
    }
    require(max(abs(value) for value in checkpoint.values()) <= 1e-6,
            "fast calibration fit differs from certified Gate 2 checkpoint")

    family_count = len(set(families.tolist()))
    family_path, family_information = calibrated_family_path(
        pooled, total, pooled_design, family_count, len(months))
    ar1 = CORE.estimate_ar1(family_path, family_information, months)
    weighted_rms = float(np.sqrt(np.average(
        np.square(family_path.reshape(-1)), weights=family_information.reshape(-1))))

    pre = np.asarray([value <= "2022-11" for value in months], bool)
    rebuilt_weight = total_matrix[:, pre].sum(axis=1)
    construction_gap = float(np.max(np.abs(rebuilt_weight - contract["construction_weight"])))
    construction_relative_gap = float(np.max(
        np.abs(rebuilt_weight - contract["construction_weight"]) /
        np.maximum(contract["construction_weight"], 1.0)))
    require(construction_relative_gap <= 1e-10, "construction weights differ")

    pooled_eta = np.log(np.clip(pooled.fitted_probability, 1e-10, 1 - 1e-10) /
                        np.clip(1 - pooled.fitted_probability, 1e-10, 1))
    family_eta = np.log(
        np.clip(family_month.fitted_probability, 1e-10, 1 - 1e-10) /
        np.clip(1 - family_month.fitted_probability, 1e-10, 1)
    )
    target_column = pooled_design.regressors[:, CORE.TARGET_INDEX]
    pooled_nuisance_eta = pooled_eta - target_column * pooled.estimate
    family_nuisance_eta = family_eta - target_column * family_month.estimate

    args.output_npz.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output_npz,
        months=np.asarray(months, dtype="U7"),
        occupations=np.asarray(occupations, dtype="U4"),
        families=np.asarray(families, dtype="U8"),
        quintiles=quintiles, webb_z=webb_z,
        exposure_beta=contract["beta"], construction_weight=contract["construction_weight"],
        total=total, effective_count=effective, effective_integer=effective_integer,
        pooled_nuisance_eta=pooled_nuisance_eta,
        family_nuisance_eta=family_nuisance_eta,
        family_shock_path=family_path, family_information=family_information,
        household_code=routes["household_code"], cellage=routes["cellage"],
        route_stock=routes["stock"], route_respondent=routes["respondent"],
        household_count=np.asarray([routes["household_count"]], dtype=np.int64),
    )
    private_hash = sha256_file(args.output_npz)
    receipt = {
        "schema_version": "yax-gate3-private-calibration-receipt-v1",
        "status": "PASS_PRIVATE_CALIBRATION_BUILD",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                              cwd=ROOT, text=True).strip(),
        "sge_job_id": os.environ.get("JOB_ID"),
        "input_hashes": hashes,
        "private_npz_sha256": private_hash,
        "private_npz_bytes": args.output_npz.stat().st_size,
        "support_occupations": len(occupations), "analysis_months": len(months),
        "SOC2_families": family_count,
        "aggregate_rebuild": {"maximum_absolute_gap": absolute_gap,
                              "maximum_relative_gap": relative_gap},
        "construction_weight_rebuild": {
            "maximum_absolute_gap": construction_gap,
            "maximum_relative_gap": construction_relative_gap,
        },
        "observed_models": {
            "pooled": {"coefficient": pooled.estimate, "occupation_se": pooled.occupation_se,
                       "family_se": pooled.family_se, "iterations": pooled.iterations},
            "family_month": {"coefficient": family_month.estimate,
                             "occupation_se": family_month.occupation_se,
                             "family_se": family_month.family_se,
                             "iterations": family_month.iterations},
            "family_month_minus_pooled": {
                "coefficient": paired["estimate"],
                "occupation_se": paired["occupation_se"],
                "family_se": paired["family_se"],
            },
            "certified_checkpoint_differences": checkpoint,
        },
        "effective_count_diagnostics": summarize_effective_counts(effective),
        "family_shock_calibration": {
            **ar1, "weighted_RMS_logit_shock": weighted_rms,
            "estimator": "weighted pooled AR(1) on consecutive observed family-month residual-score/information shocks",
            "uncertainty": "leave-one-SOC2-family range",
        },
        "route_counts": routes["counters"],
        "privacy": "NPZ remains protected on SCC; receipt contains no row, identifier value, cell stock, or private path",
    }
    args.output_receipt.parent.mkdir(parents=True, exist_ok=True)
    args.output_receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                                   encoding="utf-8")
    print(json.dumps({"status": receipt["status"],
                      "support_occupations": len(occupations),
                      "analysis_months": len(months)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
