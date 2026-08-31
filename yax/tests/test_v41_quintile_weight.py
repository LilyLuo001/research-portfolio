from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import re

import numpy as np
import pandas as pd


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


def test_stored_primary_sensitivity_is_w1() -> None:
    out = PATH.parent
    receipt = json.loads((out / "YAX_V41_QUINTILE_WEIGHT_IMPLEMENTATION_RECEIPT.json").read_text())
    assert receipt["design_verdict"] == "Verdict 3 — Freeze ambiguity"
    assert receipt["implementation_commit"] == "3445a23df7302a2e1deb5d83d6f47b0e63fef7d9"
    assert receipt["support_occupations"] == 468
    assert receipt["full_static_weight_window"]["included_months"] == 108
    assert receipt["preperiod_weight_window"]["included_months"] == 66
    assert receipt["full_static_weight_window"]["december_2022_excluded"] is True
    assert receipt["full_static_weight_window"]["october_2025_absent"] is True
    metrics = receipt["classification_metrics"]
    assert metrics["occupations_changing_quintile"] == 9
    assert np.isclose(metrics["q5_jaccard"], 1.0)
    assert np.isclose(metrics["q1_jaccard"], 0.9699248120300752)
    assert np.isclose(receipt["preperiod_weight_result"]["coefficient"], -0.12850712230916214)
    assert np.isclose(receipt["delta_preweight_minus_fullweight"], 0.0025668541131729228)


def test_stored_common_support_extension_preserves_signs() -> None:
    path = PATH.parent / "YAX_V41_SIX_MEASURE_COMMON_SUPPORT_WEIGHTING_COMPARISON.csv"
    results = pd.read_csv(path)
    assert len(results) == 6
    assert results["support_occupations"].eq(444).all()
    assert results["support_hash_sha256"].nunique() == 1
    assert results["preperiod_sign_negative"].all()
    assert results["preperiod_weight_ci_upper"].lt(0).sum() == 5
    assert results["delta_preweight_minus_fullweight"].abs().max() < 0.0064


def test_v41_manuscripts_differ_only_by_provenance() -> None:
    manuscript = ROOT / "yax/manuscript/v4_1"
    clean = (manuscript / "YAX_MANUSCRIPT_v4_1_CLEAN.md").read_text()
    auditable = (manuscript / "YAX_MANUSCRIPT_v4_1_AUDITABLE.md").read_text()
    stripped = re.sub(r"[ \t]*<!--\s*prov:[^>]+-->", "", auditable)
    assert clean == stripped
    assert "The design freeze specified employment-weighted quintiles but did not state" in clean
    assert "Its Q5–Q1 coefficient is -0.1285" in clean


def test_scope_has_no_new_event_or_flow_outputs() -> None:
    names = [path.name.lower() for path in PATH.parent.iterdir() if path.is_file()]
    assert not any("event_study" in name for name in names)
    assert not any("flow" in name for name in names)
