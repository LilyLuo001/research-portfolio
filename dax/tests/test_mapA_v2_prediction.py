import json
import pathlib
import sys

import numpy as np
import pytest


pytest.importorskip("sklearn")
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mapping"))

from mapA_v2_prediction import (  # noqa: E402
    C_GRID,
    FEATURE_NAMES,
    RetrievalPair,
    build_feature_rows,
    fit_platt_calibrator,
    select_and_fit_development_model,
    select_calibration_cutoff,
)


def test_spec_file_and_code_freeze_match():
    spec = json.loads((ROOT / "mapping" / "mapA_v2_prediction_spec_20260821.json").read_text())
    assert tuple(spec["feature_names_in_order"]) == FEATURE_NAMES
    assert tuple(spec["development_selection"]["C_grid"]) == C_GRID
    assert spec["cutoff"]["constraints"] == {"FPR_max": 0.05, "PPV_min": 0.95}
    assert spec["cutoff"]["no_feasible_cutoff"] == "MAPPING_A_V2_CALIBRATION_FAIL"


def test_feature_vector_is_exact_and_ties_break_by_id():
    rows = [
        RetrievalPair("o1", f"g{index:03d}", 1.0 - index / 220, float(index % 7))
        for index in range(220)
    ]
    matrix, order = build_feature_rows(rows, [("o1", "g000"), ("o1", "g219")])
    assert order == [("o1", "g000"), ("o1", "g219")]
    assert matrix.shape == (2, len(FEATURE_NAMES))
    assert matrix[0, 0] == 1.0
    assert matrix[0, 1] == 0.0
    assert matrix[1, 1] == 1.0
    assert np.isfinite(matrix).all()


def test_feature_builder_fails_closed_on_missing_pair_and_nonfinite():
    short = [RetrievalPair("o1", f"g{index}", 0.5, 0.0) for index in range(219)]
    with pytest.raises(ValueError, match="incomplete"):
        build_feature_rows(short, [("o1", "g0")])
    bad = [RetrievalPair("o1", f"g{index}", 0.5, 0.0) for index in range(220)]
    bad[0] = RetrievalPair("o1", "g0", float("nan"), 0.0)
    with pytest.raises(ValueError, match="finite"):
        build_feature_rows(bad, [("o1", "g0")])


def test_cutoff_rule_maximizes_recall_then_uses_frozen_ties():
    probabilities = [0.99, 0.98, 0.97, 0.96, 0.2, 0.1]
    labels = ["D", "D", "D", "D", "N", "U"]
    result = select_calibration_cutoff(probabilities, labels)
    assert result.cutoff == 0.96
    assert result.ppv == 1.0
    assert result.false_positive_rate == 0.0
    assert result.recall == 1.0


def test_cutoff_rule_fails_instead_of_weakening_constraints():
    with pytest.raises(RuntimeError, match="MAPPING_A_V2_CALIBRATION_FAIL"):
        select_calibration_cutoff([0.9, 0.8, 0.7, 0.6], ["N", "D", "N", "D"])


def test_development_selection_and_platt_fit_are_deterministic():
    generator = np.random.default_rng(20260821)
    x = generator.normal(size=(120, len(FEATURE_NAMES)))
    y = ["D" if value > 0 else "N" for value in x[:, 0] + 0.25 * x[:, 1]]
    scaler_1, model_1, receipt_1 = select_and_fit_development_model(x, y)
    scaler_2, model_2, receipt_2 = select_and_fit_development_model(x, y)
    assert receipt_1 == receipt_2
    assert np.array_equal(scaler_1.mean_, scaler_2.mean_)
    assert np.array_equal(model_1.coef_, model_2.coef_)
    calibrator = fit_platt_calibrator(scaler_1, model_1, x[:50], y[:50])
    assert calibrator.coef_.shape == (1, 1)
