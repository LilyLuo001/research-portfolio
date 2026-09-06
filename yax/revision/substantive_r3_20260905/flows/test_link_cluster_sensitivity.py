#!/usr/bin/env python3
"""Small deterministic tests for the flow score-cluster amendment."""
from __future__ import annotations

import math
import pathlib
import sys

import numpy as np
import pandas as pd


HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_link_cluster_sensitivity import cluster_summary  # noqa: E402


def test_cluster_summary() -> None:
    influence = pd.Series([1.0, -0.5, 0.25, -0.75])
    clusters = pd.Series([10, 10, 20, 30])
    grouped = np.array([0.5, 0.25, -0.75])
    expected = float(np.sqrt(np.sum(grouped**2)) * math.sqrt(3 / 2))
    actual = cluster_summary(influence, clusters)
    assert actual["clusters"] == 3
    assert abs(actual["se"] - expected) < 1e-14


def test_single_cluster_is_finite() -> None:
    actual = cluster_summary(pd.Series([0.2, -0.1]), pd.Series([1, 1]))
    assert actual["clusters"] == 1
    assert np.isfinite(actual["se"])


if __name__ == "__main__":
    test_cluster_summary()
    test_single_cluster_is_finite()
    print("2 flow link-cluster tests passed")

