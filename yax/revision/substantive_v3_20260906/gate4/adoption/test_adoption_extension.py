from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("yax_adoption_runner", HERE /
                                              "run_adoption_extension.py")
assert spec is not None and spec.loader is not None
MOD = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = MOD
spec.loader.exec_module(MOD)


def inputs():
    return (
        HERE / "inputs/rps_adoption_rates_by_occupation_20260806.xlsx",
        MOD.ROOT / "yax/revision/substantive_v3_20260906/runs/"
        "gate1_baseline/results/REBUILT_TREATMENT_MEMBERSHIP.csv",
        MOD.ROOT / "yax/revision/substantive_v3_20260906/runs/"
        "gate2_broader_support_authoritative_20260908/BROADER_SUPPORT_MEMBERSHIP.csv",
    )


def test_authenticated_workbook_schema_and_suppression():
    rps_path, _, _ = inputs()
    assert MOD.digest(rps_path) == MOD.RPS_SHA256
    frame = MOD.load_rps(rps_path)
    assert len(frame) == 505
    assert not frame.occ_code.duplicated().any()
    observed = frame.adoption_rate.notna()
    assert frame.loc[observed, "adoption_rate"].between(0, 1).all()
    assert (frame.loc[observed, "number_observations"] >= 20).all()


def test_weighted_moments_match_direct_least_squares():
    x = np.asarray([0.1, 0.2, 0.7, 0.9])
    y = np.asarray([0.2, 0.4, 0.5, 0.8])
    w = np.asarray([1.0, 2.0, 3.0, 4.0])
    result = MOD.weighted_moments(x, y, w)
    matrix = np.column_stack([np.ones(len(x)), x])
    reference = np.linalg.solve(matrix.T @ (w[:, None] * matrix), matrix.T @ (w * y))
    assert result["ols_slope_adoption_on_beta"] == pytest.approx(reference[1])


def test_fixed_merge_and_computation_preserve_declared_boundary():
    rps_path, primary_path, broader_path = inputs()
    primary = MOD.load_yax(primary_path, broader_path)
    summary, quintiles, coverage, _ = MOD.compute(primary, MOD.load_rps(rps_path))
    assert len(primary) == len(coverage) == 468
    assert coverage.matched_nonsuppressed.sum() == 121
    assert set(quintiles.beta_quintile) == {1, 2, 3, 4, 5}
    assert set(summary.weighting) == {
        "equal_occupation", "reported_observation_count_sensitivity",
    }
    assert not any(token in column.lower() for column in summary.columns
                   for token in ("standard_error", "p_value", "ci_lower", "ci_upper"))
