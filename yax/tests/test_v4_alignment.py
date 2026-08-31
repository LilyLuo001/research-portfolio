from __future__ import annotations

import hashlib
import importlib.util
import pathlib

import numpy as np


ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "yax" / "analysis" / "postoutcome_v4_supplementary" / "run_v4_alignment.py"
SPEC = importlib.util.spec_from_file_location("v4_alignment_test_module", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_support_hash_is_sorted_newline_sha256() -> None:
    expected = hashlib.sha256(b"0010\n0020\n0100\n").hexdigest()
    assert MODULE.support_hash(["0100", "0010", "0020"]) == expected


def test_finite_support_is_sorted_intersection() -> None:
    base = ["30", "10", "20", "40"]
    exposure = {"10": 1.0, "20": np.nan, "30": 2.0, "40": 3.0}
    webb = {"10": 0.0, "20": 1.0, "30": 1.0, "40": np.nan}
    assert MODULE.finite_support(base, exposure, webb) == ["10", "30"]


def test_authorized_stages_only() -> None:
    text = PATH.read_text()
    assert 'choices=("support_and_common", "categorical_event")' in text
    for forbidden in ("alternative_reference", "alternative_window", "remote_interaction"):
        assert forbidden not in text


def test_categorical_event_includes_q2_through_q5_and_dynamic_webb() -> None:
    text = PATH.read_text()
    assert "for quintile in (2, 3, 4, 5):" in text
    assert 'labels.append(f"Webb_z_x_{month}")' in text
    assert "q5_indices" in text
