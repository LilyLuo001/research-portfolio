#!/usr/bin/env python3
"""Small invariant checks for the resilience demo's core definitions."""
import numpy as np
import pandas as pd

from run_fomc_measurement_demo import safe_corr


def test_safe_corr_direction():
    x = pd.Series(np.arange(20, dtype=float))
    assert abs(safe_corr(x, x) - 1.0) < 1e-12


def test_divergence_and_recovery_definition():
    spy = pd.Series([1.0, 2.0, 2.5]).cumsum()
    es = pd.Series([1.0, 1.0, 1.0]).cumsum()
    d = spy - 1.5 * es
    assert np.allclose(d.to_numpy(), [-0.5, 0.0, 1.0])
    assert float(abs(d.iloc[-1]) / abs(d).max()) == 1.0
