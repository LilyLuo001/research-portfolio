from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pandas as pd


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
PRIOR = REPO / "yax/revision/substantive_r3_20260905/heterogeneity/results"
MEMBERSHIP = REPO / (
    "yax/revision/substantive_v3_20260906/runs/gate1_baseline/results/"
    "REBUILT_TREATMENT_MEMBERSHIP.csv"
)
RUNNER = HERE / "validate_industry_carryforward.py"


def test_real_public_carryforward_reconstructs(tmp_path: Path) -> None:
    completed = subprocess.run([
        sys.executable, str(RUNNER), "--prior-results", str(PRIOR),
        "--current-membership", str(MEMBERSHIP), "--output-dir", str(tmp_path),
    ], check=False, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    report = json.loads((tmp_path / "VALIDATION_REPORT.json").read_text())
    assert report["status"] == "PASS_GATE3_INDUSTRY_CARRYFORWARD"
    assert report["models"] == report["paired_comparisons"] == 3
    assert report["maximum_recomputed_gap"] <= 2e-12
    pairs = pd.read_csv(tmp_path / "INDUSTRY_CURRENT_CONTRACT_PAIRED.csv")
    movement = pairs.loc[
        pairs.contrast.eq("industry_conditioned_minus_industry_cell")
    ].iloc[0]
    assert abs(float(movement.coefficient_difference) - 0.0389103763) < 5e-10


def test_membership_byte_change_fails_closed(tmp_path: Path) -> None:
    altered = tmp_path / "membership.csv"
    altered.write_bytes(MEMBERSHIP.read_bytes() + b"\n")
    completed = subprocess.run([
        sys.executable, str(RUNNER), "--prior-results", str(PRIOR),
        "--current-membership", str(altered),
        "--output-dir", str(tmp_path / "out"),
    ], check=False, capture_output=True, text=True)
    assert completed.returncode != 0
    assert "canonical 468-occupation file" in completed.stderr
