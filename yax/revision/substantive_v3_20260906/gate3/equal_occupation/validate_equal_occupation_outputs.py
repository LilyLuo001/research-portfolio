#!/usr/bin/env python3
"""Recompute public equal-occupation companion identities and inference."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


RUN = load_module("yax_equal_occupation_output_runner", HERE / "run_equal_occupation.py")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate(results: Path) -> dict:
    names = ["MODEL_RESULTS.csv", "PAIRED_COMPARISONS.csv", "OBJECTIVE_WEIGHTS.csv",
             "MODEL_INFLUENCE.csv", "MODEL_FAILURES.json", "EXECUTION_RECEIPT.json"]
    for name in names:
        require((results / name).is_file(), f"missing output {name}")
    receipt = json.loads((results / "EXECUTION_RECEIPT.json").read_text())
    require(receipt.get("status") == "PASS_GATE3_EQUAL_OCCUPATION",
            "execution receipt does not pass")
    for name, expected in receipt["output_hashes"].items():
        require(RUN.sha256_file(results / name) == expected, f"output hash differs: {name}")
    models = pd.read_csv(results / "MODEL_RESULTS.csv", float_precision="round_trip")
    pairs = pd.read_csv(results / "PAIRED_COMPARISONS.csv", float_precision="round_trip")
    weights = pd.read_csv(results / "OBJECTIVE_WEIGHTS.csv",
                          dtype={"occupation_code": str}, float_precision="round_trip")
    influence = pd.read_csv(results / "MODEL_INFLUENCE.csv",
                            dtype={"cluster_id": str}, float_precision="round_trip")
    failures = json.loads((results / "MODEL_FAILURES.json").read_text())
    require(len(models) == 4 and models.model_id.nunique() == 4, "model inventory differs")
    require(len(pairs) == 2 and pairs.comparison_id.nunique() == 2,
            "paired inventory differs")
    require(len(weights) == 468 and weights.occupation_code.nunique() == 468,
            "objective-weight inventory differs")
    require(len(influence) == 4 * (468 + 22), "influence inventory differs")
    require(failures == [], "model failures are nonempty")
    require(np.max(np.abs(weights.equal_objective_weight_sum - 1.0)) <= 1e-12,
            "occupation objective weights do not sum to one")
    require(weights.WTFINL_retained_in_within_cell_share.astype(bool).all(),
            "WTFINL role differs")
    require(receipt.get("WTFINL_removed") is False, "receipt says WTFINL was removed")
    lookup = models.set_index("model_id")
    require(abs(float(lookup.loc["employment_stock_weighted_pooled",
                                 "coefficient_Q5_x_post"]) - RUN.EXPECTED_POOLED) <= 1e-8,
            "pooled baseline differs")
    require(abs(float(lookup.loc["employment_stock_weighted_family_month",
                                 "coefficient_Q5_x_post"]) - RUN.EXPECTED_FAMILY) <= 1e-8,
            "family baseline differs")
    require(models.maximum_normalized_score.max() <= 1e-7, "score certificate fails")

    occ_ids = sorted(influence.loc[influence.cluster_type.eq("occupation"),
                                   "cluster_id"].unique().tolist())
    fam_ids = sorted(influence.loc[influence.cluster_type.eq("family"),
                                   "cluster_id"].unique().tolist())
    require(len(occ_ids) == 468 and len(fam_ids) == 22, "cluster inventory differs")
    draws = RUN.CORE.draw_multiplier_matrices(RUN.DRAWS, 468, 22, RUN.SEED)
    multipliers = {"occupation": draws["occupation_rademacher"],
                   "family": draws["family_rademacher"]}
    vectors: dict[str, dict[str, np.ndarray]] = {}
    model_gap = 0.0
    for model_id, row in lookup.iterrows():
        block = influence.loc[influence.model_id.eq(model_id)]
        oi = (block.loc[block.cluster_type.eq("occupation")].set_index("cluster_id")
              .reindex(occ_ids).target_influence.to_numpy(float))
        fi = (block.loc[block.cluster_type.eq("family")].set_index("cluster_id")
              .reindex(fam_ids).target_influence.to_numpy(float))
        vectors[model_id] = {"occupation": oi, "family": fi}
        for cluster, vector in (("occupation", oi), ("family", fi)):
            rebuilt = RUN.CORE.multiplier_interval(
                float(row.coefficient_Q5_x_post), vector, multipliers[cluster])
            for field, key in (("se", f"{cluster}_se"),
                               ("lower", f"{cluster}_ci_lower"),
                               ("upper", f"{cluster}_ci_upper"),
                               ("p_value", f"{cluster}_multiplier_p")):
                gap = abs(float(rebuilt[field]) - float(row[key]))
                model_gap = max(model_gap, gap)
                require(gap <= 1e-12, f"model inference differs: {model_id} {key}")
    pair_gap = 0.0
    for _, row in pairs.iterrows():
        estimate = (float(lookup.loc[row.left_model, "coefficient_Q5_x_post"]) -
                    float(lookup.loc[row.right_model, "coefficient_Q5_x_post"]))
        require(abs(estimate - float(row.estimate_left_minus_right)) <= 1e-12,
                f"paired estimate differs: {row.comparison_id}")
        for cluster in ("occupation", "family"):
            vector = vectors[row.left_model][cluster] - vectors[row.right_model][cluster]
            rebuilt = RUN.CORE.multiplier_interval(estimate, vector, multipliers[cluster])
            for field, key in (("se", f"{cluster}_se"),
                               ("lower", f"{cluster}_ci_lower"),
                               ("upper", f"{cluster}_ci_upper"),
                               ("p_value", f"{cluster}_multiplier_p")):
                gap = abs(float(rebuilt[field]) - float(row[key]))
                pair_gap = max(pair_gap, gap)
                require(gap <= 1e-12, f"paired inference differs: {row.comparison_id} {key}")
    require(pairs.common_draws_preserve_covariance.astype(bool).all(),
            "paired inference lacks common draws")
    return {
        "schema_version": "yax-gate3-equal-occupation-validation-v1",
        "status": "PASS_RECOMPUTED_VALIDATION",
        "models": len(models), "paired_comparisons": len(pairs),
        "objective_weight_rows": len(weights), "influence_rows": len(influence),
        "maximum_model_inference_absolute_gap": model_gap,
        "maximum_paired_inference_absolute_gap": pair_gap,
        "model_failures": len(failures), "WTFINL_removed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = validate(args.results)
    RUN.write_json(args.output, report)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
