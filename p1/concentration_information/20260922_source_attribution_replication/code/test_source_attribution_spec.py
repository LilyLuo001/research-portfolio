#!/usr/bin/env python3
"""Small regression tests for source-block membership and frozen preprocessing."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("source_models", HERE / "run_source_attribution_cell.py")
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_blocks() -> None:
    base = SimpleNamespace(QUOTE=["q1", "q2"], TRADE=["c1", "c2"])
    names = ["minute_bin_5m", *[f"minute_{k}" for k in range(1, 6)]]
    names += [f"stock__{x}" for x in base.QUOTE + base.TRADE]
    names += [f"spy__{x}" for x in base.QUOTE + base.TRADE]
    names += [f"rest__{x}" for x in base.QUOTE + base.TRADE]
    names += [f"rest__coverage_{x}" for x in base.QUOTE + base.TRADE]
    names += [f"es__{x}" for x in base.QUOTE]
    blocks = module.block_columns(base, pd.DataFrame(columns=names))
    assert "minute_bin_5m" not in blocks["B"]
    assert blocks["A0"] == blocks["B"]
    assert blocks["A2"] == blocks["B"] + blocks["C"]
    assert blocks["A5"] == blocks["B"] + blocks["C"] + blocks["Q"] + blocks["P"]
    assert not set(blocks["C"]) & set(blocks["P"])


def test_training_imputation_is_frozen() -> None:
    raw = np.asarray([[1.0, np.nan], [3.0, 5.0], [100.0, 100.0]])
    train = np.asarray([True, True, False]); valid = np.asarray([False, False, True])
    x, median, mean, scale = module.training_arrays(raw, train, valid)
    assert np.allclose(median, [2.0, 5.0])
    external = module.prepared(np.asarray([[np.nan, 999.0]]), median)
    assert external[0, 0] == 2.0 and external[0, 2] == 1.0
    assert mean.shape == scale.shape == (4,)


if __name__ == "__main__":
    test_blocks(); test_training_imputation_is_frozen(); print("PASS")
