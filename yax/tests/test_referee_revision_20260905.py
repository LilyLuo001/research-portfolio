"""Regression tests for the post-outcome referee-revision helpers."""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import numpy as np
import pytest


ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "yax/revision/referee_20260905/run_referee_core.py"
SPEC = importlib.util.spec_from_file_location("yax_test_referee_revision", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_support_hash_is_order_invariant():
    assert MODULE.support_hash(["0010", "0020"]) == MODULE.support_hash(["0020", "0010"])


def test_weighted_scale_and_correlation():
    values = np.array([1.0, 2.0, 4.0])
    weights = np.array([1.0, 2.0, 1.0])
    assert MODULE.weighted_mean(values, weights) == pytest.approx(2.25)
    assert MODULE.weighted_sd(values, weights) > 0
    assert MODULE.weighted_corr(values, values, weights) == pytest.approx(1.0)


def test_quintiles_preserve_ties_and_reject_collapsed_cuts():
    values = np.arange(1.0, 11.0)
    weights = np.ones(10)
    groups, cuts = MODULE.weighted_quintile_with_cuts(values, weights)
    assert cuts.tolist() == [2.0, 4.0, 6.0, 8.0]
    assert groups.tolist() == [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]
    with pytest.raises(ValueError, match="collapsed"):
        MODULE.weighted_quintile_with_cuts(np.zeros(10), weights)


def test_common_support_hash_is_the_sealed_literal_support_hash():
    assert len(MODULE.COMMON_SUPPORT_HASH) == 64
    assert MODULE.DRAWS == 999
    assert MODULE.PERMUTATION_SEED == 2026090502
