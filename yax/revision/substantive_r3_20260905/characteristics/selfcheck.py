#!/usr/bin/env python3
"""Mechanical validation for R3 characteristic-conditioning outputs."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

import numpy as np
import pandas as pd


EXPECTED_SUPPORT_HASH = "11ec58ab1004cd83d62c57785f6c0dd3ee5a8abf08b7f71a3b664e91ded8333b"
EXPECTED_MEMBERSHIP_HASH = "c76eb85956e4a413e130bab53fe8c50616cf6d7a02c81c266ec369879dd56bc1"
EXPECTED_NORMALIZATION_HASH = "e756d597c12fc2b61ddf62e536b50d3edab32375980e7cea70e5de42fca57557"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=pathlib.Path, required=True)
    args = parser.parse_args()
    results = args.results_dir
    receipt = json.loads((results / "EXECUTION_RECEIPT.json").read_text())
    assert receipt["analysis_status"].startswith("POST-OUTCOME EXPLORATORY")
    assert receipt["treatment_contract"] == "rebuilt_corrected_preperiod_weight"
    assert receipt["rebuilt_treatment_support_hash_sha256"] == EXPECTED_SUPPORT_HASH
    assert receipt["rebuilt_treatment_input_hashes"] == {
        "membership": EXPECTED_MEMBERSHIP_HASH,
        "normalization": EXPECTED_NORMALIZATION_HASH,
    }
    assert receipt["no_postperiod_stock_used_for_treatment"] is True
    for name, expected in receipt["output_hashes"].items():
        assert sha256(results / name) == expected, name
    models = pd.read_csv(results / "CHARACTERISTIC_MODEL_RESULTS.csv")
    assert models.specification.is_unique
    assert {"native_corrected_baseline", "common_support_baseline"}.issubset(set(models.specification))
    assert "support_specific_computer_use_augmented" in set(models.specification)
    assert "support_specific_SOC2_post_augmented" in set(models.specification)
    native = models.loc[models.specification.eq("native_corrected_baseline")].iloc[0]
    assert np.isclose(native.coefficient, -0.13210945079219033, atol=1e-10, rtol=0)
    assert native.support_hash_sha256 == EXPECTED_SUPPORT_HASH
    assert models.analysis_status.str.startswith("POST-OUTCOME EXPLORATORY").all()
    assert (models.information_matrix_rank == models.information_matrix_columns).all()
    assert (models.conditional_target_information > 0).all()
    assert (models.information_retention_conditional_over_raw > 0).all()
    assert (models.information_retention_conditional_over_raw <= 1.0000001).all()
    paired = pd.read_csv(results / "CHARACTERISTIC_PAIRED_DIFFERENCES.csv")
    assert paired.common_occupation_multipliers.all()
    assert np.isfinite(paired.paired_se).all()
    support = pd.read_csv(results / "CHARACTERISTIC_SUPPORT_BY_QUINTILE.csv")
    assert set(support.quintile) == {1, 2, 3, 4, 5}
    coefficients = pd.read_csv(results / "ALL_MODEL_COEFFICIENTS.csv")
    assert set(coefficients.specification) == set(models.specification)
    assert coefficients.groupby("specification").is_Q5_target.sum().eq(1).all()
    information = pd.read_csv(results / "CHARACTERISTIC_INFORMATION_BY_OCCUPATION.csv")
    assert "rebuilt_beta_quintile" in information.columns
    assert "frozen_beta_quintile" not in information.columns
    support_map = pd.read_csv(results / "SUPPORT_SPECIFIC_MODEL_MAP.csv")
    assert len(support_map) == 9
    assert (support_map.support_occupations <= 468).all()
    full_support = support.loc[support.support.eq("primary_native")]
    assert int(full_support.occupations.sum()) == 468
    assert set(full_support.quintile) == {1, 2, 3, 4, 5}
    assert json.loads((results / "MODEL_FAILURES.json").read_text()) == receipt["model_failures"]
    print("PASS_R3_CHARACTERISTIC_CONDITIONING_SELFCHECK")


if __name__ == "__main__":
    main()
