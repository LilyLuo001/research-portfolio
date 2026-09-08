#!/usr/bin/env python3
"""Recompute the public Gate 3 mapping-sensitivity evidence."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
DRAWS = 9_999
SEED = 202609086401
EXPECTED_POOLED = -0.13210945079219025
EXPECTED_FAMILY = -0.021674952018246537


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CORE = load_module("yax_mapping_validation_core", HERE.parent / "inference_validation" /
                   "inference_engine.py")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def maximum_gap(left: dict[str, float], right: dict[str, float]) -> float:
    return max(abs(float(left[key]) - float(right[key])) for key in left)


def read_influence(path: Path) -> tuple[pd.DataFrame, list[str], list[str]]:
    frame = pd.read_csv(path, dtype={"cluster_id": str}, float_precision="round_trip")
    required = {"model_id", "cluster_type", "cluster_id", "influence_Q5_x_post"}
    require(set(frame.columns) == required, "influence schema differs")
    baseline = "symmetric_K_1_fixed_labels_pooled"
    occupations = frame.loc[(frame.model_id == baseline) &
                            (frame.cluster_type == "occupation"), "cluster_id"].tolist()
    families = frame.loc[(frame.model_id == baseline) &
                         (frame.cluster_type == "family"), "cluster_id"].tolist()
    require(len(occupations) == 468 and len(families) == 22,
            "baseline influence cluster inventory differs")
    return frame, occupations, families


def vector(frame: pd.DataFrame, model: str, cluster_type: str,
           levels: list[str]) -> np.ndarray:
    rows = frame.loc[(frame.model_id == model) & (frame.cluster_type == cluster_type)].copy()
    require(len(rows) == len(levels) and not rows.cluster_id.duplicated().any(),
            f"{model} {cluster_type} influence inventory differs")
    rows = rows.set_index("cluster_id").reindex(levels)
    require(not rows.influence_Q5_x_post.isna().any(),
            f"{model} {cluster_type} influence levels differ")
    return rows.influence_Q5_x_post.to_numpy(float)


def validate(output_dir: Path) -> dict[str, Any]:
    receipt = json.loads((output_dir / "EXECUTION_RECEIPT.json").read_text(encoding="utf-8"))
    require(receipt.get("status") == "PASS_GATE3_MAPPING_SENSITIVITY",
            "mapping execution receipt does not pass")
    for name, expected in receipt["output_hashes"].items():
        require(sha256_file(output_dir / name) == expected, f"{name} hash differs")
    models = pd.read_csv(output_dir / "MODEL_RESULTS.csv", float_precision="round_trip")
    pairs = pd.read_csv(output_dir / "PAIRED_MOVEMENTS.csv", float_precision="round_trip")
    influence, occupations, families = read_influence(output_dir / "MODEL_INFLUENCE.csv")
    require(len(models) == 65 and models.model_id.nunique() == 65,
            "model inventory differs")
    require(len(pairs) == 32 and pairs.comparison.nunique() == 32,
            "paired-comparison inventory differs")
    require(len(influence) == 65 * (468 + 22), "influence row count differs")
    multipliers_raw = CORE.draw_multiplier_matrices(DRAWS, 468, 22, SEED)
    multipliers = {"occupation": multipliers_raw["occupation_rademacher"],
                   "family": multipliers_raw["family_rademacher"]}

    model_gap = 0.0
    model_vectors: dict[tuple[str, str], np.ndarray] = {}
    for _, row in models.iterrows():
        for cluster_type, prefix in (("occupation", "occupation"), ("family", "family")):
            levels = occupations if cluster_type == "occupation" else families
            value = vector(influence, row.model_id, cluster_type, levels)
            model_vectors[(row.model_id, cluster_type)] = value
            recomputed = CORE.multiplier_interval(
                float(row.coefficient_Q5_x_post), value, multipliers[cluster_type])
            stored = {"se": row[f"{prefix}_se"], "lower": row[f"{prefix}_ci_lower"],
                      "upper": row[f"{prefix}_ci_upper"],
                      "p_value": row[f"{prefix}_multiplier_p"]}
            model_gap = max(model_gap, maximum_gap(stored, recomputed))
    require(model_gap <= 5e-13, f"model inference reconstruction gap {model_gap}")

    pair_gap = 0.0
    for _, row in pairs.iterrows():
        left = models.set_index("model_id").loc[row.left_model]
        right = models.set_index("model_id").loc[row.right_model]
        estimate = float(left.coefficient_Q5_x_post - right.coefficient_Q5_x_post)
        require(abs(estimate - float(row.estimate_left_minus_right)) <= 5e-15,
                f"{row.comparison} paired estimate differs")
        for cluster_type, prefix in (("occupation", "occupation"), ("family", "family")):
            value = (model_vectors[(row.left_model, cluster_type)] -
                     model_vectors[(row.right_model, cluster_type)])
            recomputed = CORE.multiplier_interval(estimate, value, multipliers[cluster_type])
            stored = {"se": row[f"{prefix}_se"], "lower": row[f"{prefix}_ci_lower"],
                      "upper": row[f"{prefix}_ci_upper"],
                      "p_value": row[f"{prefix}_multiplier_p"]}
            pair_gap = max(pair_gap, maximum_gap(stored, recomputed))
    require(pair_gap <= 5e-13, f"paired inference reconstruction gap {pair_gap}")

    indexed = models.set_index("model_id")
    identities = {
        "fixed_pooled": abs(indexed.at["symmetric_K_1_fixed_labels_pooled",
                                        "coefficient_Q5_x_post"] - EXPECTED_POOLED),
        "rebuilt_pooled": abs(indexed.at["symmetric_K_1_rebuilt_treatment_pooled",
                                          "coefficient_Q5_x_post"] - EXPECTED_POOLED),
        "fixed_family": abs(indexed.at["symmetric_K_1_fixed_labels_family_month",
                                        "coefficient_Q5_x_post"] - EXPECTED_FAMILY),
        "rebuilt_family": abs(indexed.at["symmetric_K_1_rebuilt_treatment_family_month",
                                          "coefficient_Q5_x_post"] - EXPECTED_FAMILY),
    }
    require(max(identities.values()) <= 1e-8, "a no-tilt coefficient identity differs")
    require(receipt["canonical_identity"]["cell_maximum_relative_gap"] <= 1e-10,
            "no-tilt cell identity fails")
    require(receipt["canonical_identity"]["official_rebuilt_labels_exact"],
            "no-tilt label identity fails")

    symmetric = models.loc[models.block.eq("W02_symmetric_odds_tilt")]
    adverse = pd.read_csv(output_dir / "ADVERSE_GRID.csv", float_precision="round_trip")
    mass = pd.read_csv(output_dir / "MASS_CONSERVATION.csv", float_precision="round_trip")
    members = pd.read_csv(output_dir / "SYMMETRIC_TILT_MEMBERSHIP.csv",
                          dtype={"occupation_code": str}, float_precision="round_trip")
    require(len(symmetric) == 28 and len(adverse) == 25 and len(mass) == 7,
            "tilt grid inventory differs")
    require(len(members) == 7 * 468, "tilt membership inventory differs")
    require(max(mass.maximum_relative_source_age_month_gap.max(),
                adverse.maximum_relative_source_age_month_gap.max()) <= 1e-11,
            "a route grid point changes source-age-month mass")
    require(bool(models.loc[models.block.eq("W03_joint_adverse_grid"),
                            "jointly_feasible_source_age_month_allocation"].all()),
            "an adverse model is not marked feasible")
    envelope = json.loads((output_dir / "ADVERSE_ENVELOPE.json").read_text(encoding="utf-8"))
    require(envelope["status"] == "EXPLORED_FEASIBLE_GRID_NOT_A_SHARP_OR_GLOBAL_BOUND",
            "adverse grid is mislabeled")
    require(abs(envelope["minimum"]["coefficient_Q5_x_post"] -
                adverse.coefficient_Q5_x_post.min()) <= 5e-15,
            "adverse minimum differs")
    require(abs(envelope["maximum"]["coefficient_Q5_x_post"] -
                adverse.coefficient_Q5_x_post.max()) <= 5e-15,
            "adverse maximum differs")

    service = pd.read_csv(output_dir / "SERVICE_AND_DELETION_MEMBERS.csv",
                          dtype={"excluded_codes": str})
    diagnostic = pd.read_csv(output_dir / "BASELINE_INFLUENCE_DIAGNOSTICS.csv",
                             dtype={"occupation_code": str}, float_precision="round_trip")
    require(len(service) == 8 and len(diagnostic) == 468,
            "service or influence diagnostic inventory differs")
    base_value = model_vectors[("symmetric_K_1_fixed_labels_pooled", "occupation")]
    shares = np.square(base_value) / np.square(base_value).sum()
    require(float(np.max(np.abs(np.sort(shares)[::-1] -
                                diagnostic.squared_influence_share.to_numpy(float)))) <= 5e-15,
            "baseline influence shares differ")

    carry = pd.read_csv(output_dir / "CARRY_FORWARD_RESULTS.csv", float_precision="round_trip")
    require(len(carry) == 3, "carry-forward row inventory differs")
    for _, row in carry.iterrows():
        path = ROOT / row.source_path
        require(path.is_file() and sha256_file(path) == row.source_sha256,
                f"carry-forward source moved: {row.model_id}")
    disposition = json.loads((output_dir / "CODING_ERROR_DISPOSITION.json").read_text(
        encoding="utf-8"))
    require(disposition["status"] == "NOT_EXECUTED_NO_VALIDATED_ERROR_MATRIX" and
            not disposition["arbitrary_symmetric_error_rate_fabricated"],
            "coding-error disposition differs")
    failures = json.loads((output_dir / "MODEL_FAILURES.json").read_text(encoding="utf-8"))
    require(failures == [], "retained model failures are nonempty")
    report = {
        "schema_version": "yax-gate3-mapping-public-validation-v1",
        "status": "PASS_GATE3_MAPPING_PUBLIC_VALIDATION",
        "model_count": len(models), "paired_comparisons": len(pairs),
        "model_inference_maximum_absolute_gap": model_gap,
        "paired_inference_maximum_absolute_gap": pair_gap,
        "no_tilt_coefficient_absolute_gaps": identities,
        "cell_maximum_relative_gap": receipt["canonical_identity"]["cell_maximum_relative_gap"],
        "maximum_source_age_month_mass_relative_gap": float(max(
            mass.maximum_relative_source_age_month_gap.max(),
            adverse.maximum_relative_source_age_month_gap.max())),
        "adverse_grid_points": len(adverse),
        "adverse_grid_minimum_coefficient": float(adverse.coefficient_Q5_x_post.min()),
        "adverse_grid_maximum_coefficient": float(adverse.coefficient_Q5_x_post.max()),
        "output_hashes_verified": len(receipt["output_hashes"]),
        "carry_forward_hashes_verified": len(carry),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--write-report", type=Path)
    args = parser.parse_args()
    report = validate(args.output_dir)
    if args.write_report:
        args.write_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                                    encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
