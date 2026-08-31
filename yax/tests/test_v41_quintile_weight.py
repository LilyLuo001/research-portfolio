from __future__ import annotations

import hashlib
import importlib.util
import pathlib

import numpy as np


ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "yax/analysis/postoutcome_v41_quintile_weight/run_v41_quintile_weight.py"
SPEC = importlib.util.spec_from_file_location("v41_quintile_weight_test_module", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_support_hash_is_sorted_newline_sha256() -> None:
    expected = hashlib.sha256(b"0010\n0020\n0100\n").hexdigest()
    assert MODULE.support_hash(["0100", "0010", "0020"]) == expected


def test_weighted_cuts_match_frozen_assignment() -> None:
    values = np.arange(10, dtype=float)
    weights = np.ones(10)
    cuts = MODULE.weighted_cuts(values, weights)
    expected = MODULE.FROZEN.weighted_quintiles(values, weights)
    actual = np.searchsorted(cuts, values, side="left") + 1
    assert np.array_equal(actual, expected)


def test_weighted_correlation_identity() -> None:
    values = np.arange(1, 6, dtype=float)
    weights = np.arange(1, 6, dtype=float)
    assert np.isclose(MODULE.weighted_correlation(values, values, weights), 1.0)


def test_only_declared_stages_exist() -> None:
    text = PATH.read_text()
    assert 'choices=("primary", "common_support")' in text
    for forbidden_stage in ("categorical_event", "alternative_window", "flow_analysis"):
        assert f'args.stage == "{forbidden_stage}"' not in text


def test_preperiod_classification_changes_only_ai_quintile_columns() -> None:
    text = PATH.read_text()
    assert 'regressors = prepared["regressors"].copy()' in text
    assert 'for column, quintile in enumerate((2, 3, 4, 5)):' in text
    assert 'regressors[:, column]' in text
    assert 'target = 3' in text
