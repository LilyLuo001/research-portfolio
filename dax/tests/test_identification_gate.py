import importlib.util
import pathlib

import numpy as np
import pandas as pd
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "memo" / "power_calcs" / "run_identification_gate.py"
SPEC = importlib.util.spec_from_file_location("identification_gate", PATH)
assert SPEC and SPEC.loader
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


def test_rank_one_dose_profile_fails_dynamic_gate():
    matrix = np.outer([1.0, 2.0, 4.0], [0.0, 1.0, 2.0, 3.0])
    result = GATE.matrix_diagnostics(matrix)
    assert result["effective_rank"] == 1
    assert result["leading_singular_share"] == pytest.approx(1.0)


def test_two_independent_profiles_clear_rank_threshold():
    matrix = np.array([
        [1.0, 0.0, 1.0, 0.0],
        [0.0, 1.0, 0.0, 1.0],
        [1.0, 1.0, 0.0, 0.0],
    ])
    result = GATE.matrix_diagnostics(matrix)
    assert result["effective_rank"] >= 2
    assert result["leading_singular_share"] < 0.95


def test_gate_rejects_any_outcome_column_before_unsealing():
    frame = pd.DataFrame({
        "cps_occ": ["1", "1", "2", "2"],
        "month": ["2023-01", "2023-02", "2023-01", "2023-02"],
        "dax": [0.0, 0.1, 0.0, 0.2],
        "industry": ["A", "A", "B", "B"],
        "static_decile": [1, 1, 2, 2],
        "weight": [1.0] * 4,
        "employment_rate": [0.8] * 4,
    })
    with pytest.raises(ValueError, match="outcome-like columns forbidden"):
        GATE.evaluate(frame)
