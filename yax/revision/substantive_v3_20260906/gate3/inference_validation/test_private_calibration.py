from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "yax_gate3_private_calibration", HERE / "build_private_calibration.py")
CAL = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = CAL
spec.loader.exec_module(CAL)


def aggregate_frame() -> pd.DataFrame:
    months = [f"2017-{month:02d}" for month in range(1, 13)]
    rows = []
    for index in range(468):
        for month in months:
            rows.append({
                "occ_code": f"{index:04d}", "month": month,
                "family": f"{index % 22:02d}", "young": 10.0,
                "older": 90.0, "beta_quintile": index % 5 + 1,
                "webb_z": index / 468,
            })
    return pd.DataFrame(rows)


def test_effective_count_summary_does_not_serialize_cells():
    result = CAL.summarize_effective_counts(np.asarray([0, 1, 3, 10, 100], float))
    assert result["positive_cells"] == 4
    assert result["minimum"] == 1
    assert "values" not in result


def test_stable_aggregate_rejects_wrong_hash_independent_schema(tmp_path):
    frame = aggregate_frame()
    path = tmp_path / "cells.csv"
    frame.to_csv(path, index=False)
    with pytest.raises(RuntimeError, match="analysis calendar differs"):
        CAL.stable_aggregate(path)


def test_calibrated_family_path_is_family_and_month_residualized():
    q = np.repeat(np.arange(1, 6), 2)
    families = np.asarray(["A"] * 5 + ["B"] * 5, object)
    months = ["2022-10", "2022-11", "2023-01", "2023-02"]
    design = CAL.CORE.build_design(q, np.linspace(-1, 1, 10), families, months, "pooled")
    total = np.full(40, 100.0)
    probability = np.full(40, .2)
    residual = np.tile(np.asarray([-2.0, 1.0, 3.0, -2.0]), 10)
    fit = CAL.CORE.FitArtifacts(
        structure="pooled", beta=np.zeros(5), fitted_probability=probability,
        residual=residual, occupation_influence=np.zeros((10, 5)),
        family_influence=np.zeros((2, 5)), active_occupation_count=10,
        active_family_count=2, separated_observation_count=0,
        separated_first_group_count=0, separated_second_group_count=0,
        iterations=1, maximum_normalized_score=0.0,
    )
    shock, weight = CAL.calibrated_family_path(fit, total, design, 2, 4)
    assert shock.shape == weight.shape == (2, 4)
    assert np.max(np.abs(np.average(shock, axis=0, weights=weight))) < 1e-10
    assert np.max(np.abs(np.average(shock, axis=1, weights=weight))) < 1e-10
