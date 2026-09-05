#!/usr/bin/env python3
"""Mechanical validation for R3 characteristic-conditioning outputs."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

import numpy as np
import pandas as pd


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=pathlib.Path, required=True)
    args = parser.parse_args()
    results = args.results_dir
    receipt = json.loads((results / "EXECUTION_RECEIPT.json").read_text())
    for name, expected in receipt["output_hashes"].items():
        assert sha256(results / name) == expected, name
    models = pd.read_csv(results / "CHARACTERISTIC_MODEL_RESULTS.csv")
    assert models.specification.is_unique
    assert {"native_corrected_baseline", "common_support_baseline"}.issubset(set(models.specification))
    native = models.loc[models.specification.eq("native_corrected_baseline")].iloc[0]
    assert np.isclose(native.coefficient, -0.1345539535732939, atol=1e-10, rtol=0)
    assert (models.information_matrix_rank == models.information_matrix_columns).all()
    assert (models.conditional_target_information > 0).all()
    assert (models.information_retention_conditional_over_raw > 0).all()
    assert (models.information_retention_conditional_over_raw <= 1.0000001).all()
    paired = pd.read_csv(results / "CHARACTERISTIC_PAIRED_DIFFERENCES.csv")
    assert paired.common_occupation_multipliers.all()
    assert np.isfinite(paired.paired_se).all()
    support = pd.read_csv(results / "CHARACTERISTIC_SUPPORT_BY_QUINTILE.csv")
    assert set(support.quintile) == {1, 2, 3, 4, 5}
    assert json.loads((results / "MODEL_FAILURES.json").read_text()) == receipt["model_failures"]
    print("PASS_R3_CHARACTERISTIC_CONDITIONING_SELFCHECK")


if __name__ == "__main__":
    main()

