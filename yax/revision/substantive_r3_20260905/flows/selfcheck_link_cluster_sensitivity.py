#!/usr/bin/env python3
"""Fail-closed verifier for aggregate flow link-cluster sensitivities."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

import numpy as np
import pandas as pd


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True, type=pathlib.Path)
    args = parser.parse_args()
    root = args.results
    checks: list[dict] = []

    def require(condition: bool, description: str) -> None:
        checks.append({"description": description, "passed": bool(condition)})
        if not condition:
            raise AssertionError(description)

    result = pd.read_csv(root / "PERSON_HOUSEHOLD_CLUSTER_SENSITIVITY.csv")
    conservation = pd.read_csv(root / "EVENT_SCORE_CONSERVATION.csv")
    receipt = json.loads((root / "EXECUTION_RECEIPT.json").read_text(encoding="utf-8"))
    require(len(result) == 10, "all ten official core-flow models are present")
    require(result.model_id.nunique() == 10, "core-flow model identifiers are unique")
    require(
        set(result.model_id.str.split("__").str[0]) == {"adjacent_month", "twelve_month"},
        "both declared horizons are present",
    )
    require(
        np.isfinite(
            result[
                [
                    "coefficient",
                    "primary_occupation_cluster_se",
                    "person_cluster_se",
                    "household_cluster_se",
                    "person_normal_mde80",
                    "household_normal_mde80",
                ]
            ].to_numpy()
        ).all(),
        "coefficients and cluster precision statistics are finite",
    )
    require(
        (result[["person_score_clusters", "household_score_clusters"]].to_numpy() > 1).all(),
        "every model has multiple person and household score clusters",
    )
    require(len(conservation) == 10, "all ten models have conservation diagnostics")
    require(
        conservation.coefficient_reproduction_error.abs().max() < 1e-10,
        "all coefficients reproduce stored official results",
    )
    require(
        conservation.event_weight_conservation_error.abs().max() < 1e-5,
        "modeled event weights reproduce cell event totals",
    )
    require(
        conservation.max_raw_occupation_influence_error.max() < 1e-8,
        "event influences reproduce raw occupation influences",
    )
    require(
        conservation.max_saved_occupation_influence_error.max() < 1e-8,
        "event influences reproduce saved finite-corrected occupation influences",
    )
    forbidden = {"CPSID", "CPSIDP", "CPSIDV", "SERIAL", "PERNUM", "event_id"}
    for path in root.glob("*.csv"):
        headers = set(pd.read_csv(path, nrows=0).columns)
        require(not (headers & forbidden), f"{path.name} contains no restricted identifier column")
    require(receipt["no_restricted_identifier_or_event_record_written"], "receipt records aggregate-only outputs")
    require(receipt["not_full_CPS_design_inference"], "receipt rejects a full design-based interpretation")
    require(
        receipt["not_combined_with_occupation_cluster_variance"],
        "receipt keeps sampling and occupation-shock sensitivities separate",
    )
    for filename, expected in receipt["output_hashes"].items():
        require(sha256(root / filename) == expected, f"{filename} hash matches execution receipt")
    output = {"status": "PASS", "checks": checks}
    (root / "SELF_CHECK.json").write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": "PASS", "checks": len(checks)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

