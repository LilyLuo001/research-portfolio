from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


RUN = load_module("test_yax_gate3_architecture", HERE / "run_architecture_reconciliation.py")


def test_continuous_design_has_declared_target_and_row_order():
    score = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    webb = np.array([0.5, -0.5, 0.0, 0.25, -0.25])
    months = ["2022-11", "2023-01"]
    families = np.array(["11", "11", "13", "13", "15"])
    design = RUN.build_continuous_design(score, webb, families, months, "pooled")
    assert design.regressors.shape == (10, 2)
    assert design.focal_target_index == 0
    assert design.regressor_labels[0] == "exposure_z_x_post"
    assert np.array_equal(design.regressors[:, 0], [0, -2, 0, -1, 0, 0, 0, 1, 0, 2])


def test_family_month_design_uses_family_by_calendar_effects():
    design = RUN.build_continuous_design(
        np.arange(5), np.arange(5), np.array(["11", "11", "13", "13", "15"]),
        ["2022-11", "2023-01"], "family_month")
    assert len(set(design.second_labels.tolist())) == 6


def test_public_exposure_support_counts_are_fixed():
    root = RUN.ROOT
    membership = pd.read_csv(
        root / "yax/revision/substantive_v3_20260906/runs/gate1_baseline/results/"
        "REBUILT_TREATMENT_MEMBERSHIP.csv", dtype={"occupation_code": str})
    occupations = membership.occupation_code.str.zfill(4).to_numpy()
    _, scores = RUN.load_scores(
        root / "yax/revision/substantive_v3_20260906/runs/gate1_baseline/results/"
        "REBUILT_TREATMENT_MEMBERSHIP.csv",
        root / "yax/measurement/CENSUS2018_EXPOSURE_VARIANTS.csv",
        root / "yax/revision/referee_20260905/results/external/WEBB_AI_CENSUS2018_MAP.csv",
        root / "yax/revision/referee_20260905/results/external/OECD_CENSUS2018_MAP.csv",
        occupations,
    )
    assert scores.notna().sum().to_dict() == {
        "aioe_admin_equal": 466,
        "aioe_ability_direct": 455,
        "aioe_oews2018_source_weighted": 456,
        "webb_ai": 443,
        "oecd_ai_gap_reversed": 448,
    }
    assert scores[["aioe_admin_equal", "aioe_ability_direct",
                   "aioe_oews2018_source_weighted"]].notna().all(axis=1).sum() == 444


def test_w06_public_carry_forward_is_fully_validated():
    result = RUN.validate_w06(
        RUN.ROOT / "yax/revision/substantive_r3_20260905/architecture/results")
    assert result["status"] == "PASS_W06_CURRENT_CONTRACT_CARRY_FORWARD"
    assert result["lambda_membership_rows"] == 2340
    assert result["lambda_paired_rows"] == 30
    assert result["model_failures"] == 0


def test_w06_carry_forward_accepts_repo_relative_source_path(monkeypatch):
    monkeypatch.chdir(RUN.ROOT)
    relative = Path("yax/revision/substantive_r3_20260905/architecture/results")
    result = RUN.validate_w06(relative)
    assert result["source_directory"] == relative.as_posix()


def test_spec_separates_constructs_units_and_historical_evidence():
    text = (HERE / "ARCHITECTURE_RECONCILIATION_SPEC.md").read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    assert "AIOE variants are alternative implementations of one construct" in normalized
    assert "Webb AI and OECD are different constructs" in normalized
    assert "it is not a percentage" in normalized
    assert "not current outcome evidence" in normalized
    assert "does not establish equivalence" in normalized
