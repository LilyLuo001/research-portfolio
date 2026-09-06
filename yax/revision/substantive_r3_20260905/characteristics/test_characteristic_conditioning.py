"""Regression tests for the rebuilt-treatment characteristic rerun."""
from __future__ import annotations

import hashlib
import json
import pathlib

import numpy as np
import pandas as pd


HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RESULTS = HERE / "results"
SUPPORT_HASH = "11ec58ab1004cd83d62c57785f6c0dd3ee5a8abf08b7f71a3b664e91ded8333b"
MEMBERSHIP_HASH = "c76eb85956e4a413e130bab53fe8c50616cf6d7a02c81c266ec369879dd56bc1"
NORMALIZATION_HASH = "e756d597c12fc2b61ddf62e536b50d3edab32375980e7cea70e5de42fca57557"


def file_hash(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_rebuilt_contract_and_native_checkpoint() -> None:
    receipt = json.loads((RESULTS / "EXECUTION_RECEIPT.json").read_text(encoding="utf-8"))
    assert receipt["treatment_contract"] == "rebuilt_corrected_preperiod_weight"
    assert receipt["no_postperiod_stock_used_for_treatment"] is True
    assert receipt["rebuilt_treatment_support_hash_sha256"] == SUPPORT_HASH
    assert receipt["rebuilt_treatment_input_hashes"] == {
        "membership": MEMBERSHIP_HASH,
        "normalization": NORMALIZATION_HASH,
    }
    for name, expected in receipt["output_hashes"].items():
        assert file_hash(RESULTS / name) == expected

    models = pd.read_csv(RESULTS / "CHARACTERISTIC_MODEL_RESULTS.csv")
    native = models.loc[models.specification.eq("native_corrected_baseline")].iloc[0]
    assert int(native.support_occupations) == 468
    assert native.support_hash_sha256 == SUPPORT_HASH
    assert np.isclose(native.coefficient, -0.13210945079219033, atol=1e-10, rtol=0)
    assert models.analysis_status.str.startswith("POST-OUTCOME EXPLORATORY").all()


def test_registered_grid_and_paired_supports_are_preserved() -> None:
    models = pd.read_csv(RESULTS / "CHARACTERISTIC_MODEL_RESULTS.csv")
    pairs = pd.read_csv(RESULTS / "CHARACTERISTIC_PAIRED_DIFFERENCES.csv")
    support_map = pd.read_csv(RESULTS / "SUPPORT_SPECIFIC_MODEL_MAP.csv")
    expected_registered = {
        "native_corrected_baseline", "common_support_baseline",
        "one_at_a_time_computer_use", "one_at_a_time_remotability",
        "one_at_a_time_wage", "one_at_a_time_education",
        "one_at_a_time_routine", "one_at_a_time_manual",
        "one_at_a_time_pandemic_total", "one_at_a_time_pandemic_young_relative",
        "one_at_a_time_SOC2_post", "cumulative_computer",
        "cumulative_computer_remote", "cumulative_human_task_block",
        "cumulative_plus_pandemic", "cumulative_plus_pandemic_SOC2",
        "parsimonious_combined_SOC2",
    }
    assert expected_registered.issubset(set(models.specification))
    assert len(models) == 35
    assert len(pairs) == 24
    assert pairs.common_occupation_multipliers.all()
    assert json.loads((RESULTS / "MODEL_FAILURES.json").read_text(encoding="utf-8")) == []
    information = pd.read_csv(RESULTS / "CHARACTERISTIC_INFORMATION_BY_OCCUPATION.csv")
    assert "rebuilt_beta_quintile" in information.columns
    assert "frozen_beta_quintile" not in information.columns

    indexed = models.set_index("specification")
    for row in support_map.itertuples(index=False):
        baseline = indexed.loc[row.baseline_specification]
        augmented = indexed.loc[row.augmented_specification]
        assert baseline.support_hash_sha256 == augmented.support_hash_sha256
        assert int(baseline.support_occupations) == int(augmented.support_occupations)
        contrast = f"{row.augmented_specification}_minus_{row.baseline_specification}"
        pair = pairs.loc[pairs.contrast.eq(contrast)].iloc[0]
        assert pair.support_hash_sha256 == baseline.support_hash_sha256


def test_active_characteristic_reporting_names_rebuilt_contract() -> None:
    appendix = (ROOT / "paper/appendix/sections/r3_D_characteristics.tex").read_text(
        encoding="utf-8"
    )
    table = (ROOT / "paper/tables/r3_appendix_characteristic_estimates.tex").read_text(
        encoding="utf-8"
    )
    active = appendix + "\n" + table
    assert "canonical corrected-preperiod membership" in active
    assert "canonical rebuilt corrected-preperiod beta groups" in active
    assert "fixed historical beta groups" not in active


def test_treatment_change_preserved_registered_grid() -> None:
    audit = json.loads(
        (HERE / "TREATMENT_CONTRACT_CHANGE_AUDIT.json").read_text(encoding="utf-8")
    )
    assert audit["status"] == "PASS_REBUILT_TREATMENT_CHARACTERISTIC_AUDIT"
    assert audit["historical_to_rebuilt_quintile_memberships_changed"] == 9
    assert audit["registered_model_identifiers_unchanged"] is True
    assert audit["registered_pair_identifiers_unchanged"] is True
    assert audit["support_counts_unchanged_for_every_model"] is True
    assert audit["support_hashes_unchanged_for_every_model"] is True
    assert audit["model_failures_unchanged_and_empty"] is True
