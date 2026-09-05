#!/usr/bin/env python3
"""Mechanical checks for the composition/influence exploratory outputs."""
from __future__ import annotations

import hashlib
import json
import pathlib

import numpy as np
import pandas as pd


HERE = pathlib.Path(__file__).resolve().parent
RESULTS = HERE / "results"
PRIMARY = -0.13107397642233506
LABEL = "POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    receipt = json.loads((RESULTS / "EXECUTION_RECEIPT.json").read_text())
    assert receipt["analysis_status"] == LABEL
    assert np.isclose(receipt["frozen_primary_reproduced"], PRIMARY, atol=1e-12, rtol=0)
    source = receipt["implementation_source"]
    assert sha256(HERE / "run_composition_influence.py") == source["script_sha256"]
    assert sha256(HERE / "ANALYSIS_SPEC.md") == source["analysis_spec_sha256"]
    for name, expected in receipt["output_hashes"].items():
        assert sha256(RESULTS / name) == expected, name

    models = pd.read_csv(RESULTS / "COMPOSITION_MODELS.csv")
    assert set(models.model) == {"frozen_baseline", "SOC2_x_post", "SOC2_x_calendar_month"}
    assert set(models.calendar) == {"frozen_108_month", "March_repaired_113_month"}
    assert len(models) == 6
    assert (models.analysis_status == LABEL).all()
    baseline = models.loc[
        models.model.eq("frozen_baseline") & models.calendar.eq("frozen_108_month")
    ].iloc[0]
    assert np.isclose(baseline.coefficient, PRIMARY, atol=1e-12, rtol=0)
    assert (models.information_matrix_rank == models.information_matrix_columns).all()
    assert (models.conditional_target_information > 0).all()
    assert json.loads((RESULTS / "COMPOSITION_MODEL_FAILURES.json").read_text()) == []
    paired = pd.read_csv(RESULTS / "COMPOSITION_PAIRED_DIFFERENCES.csv")
    assert len(paired) == 4
    assert paired.common_occupation_multipliers.all()
    assert np.isfinite(paired.coefficient_difference).all()

    support = pd.read_csv(RESULTS / "SOC2_QUINTILE_SUPPORT.csv")
    assert len(support) == 44
    assert (support.groupby("calendar").occupations.sum() == 468).all()
    assert (support.groupby("calendar").contains_Q1_and_Q5.sum() == 4).all()

    profile = json.loads((RESULTS / "QUINTILE_PROFILE_TESTS.json").read_text())
    assert profile["equality"]["null"] == "b2=b3=b4=b5"
    assert len(profile["monotonicity"]["adjacent"]) == 4
    assert profile["monotonicity"]["verdict"] in {
        "REJECT_MONOTONE_NONINCREASING_AT_5_PERCENT",
        "SIMULTANEOUS_UPPER_BOUNDS_SUPPORT_MONOTONE_NONINCREASING",
        "UNRESOLVED_NOT_REJECTED_AND_NOT_ESTABLISHED",
    }

    stable = json.loads((RESULTS / "STABLE_TAIL_RESULT.json").read_text())
    assert stable["always_Q1_occupations"] == 46
    assert stable["always_Q5_occupations"] == 18
    assert stable["selected_occupations"] == 64

    influence = pd.read_csv(RESULTS / "JOINT_DELETION_AND_ROBUST_INFLUENCE.csv")
    assert set(influence.specification) == {
        "joint_leave_top_5_frozen_LOCO",
        "joint_leave_top_10_frozen_LOCO",
        "joint_leave_top_20_frozen_LOCO",
        "trim_2.5pct_each_signed_frozen_LOCO_tail",
        "Huber_downweight_above_p95_absolute_LOCO_deviation",
    }
    assert np.isfinite(influence.coefficient).all()

    exclusions = pd.read_csv(RESULTS / "OCCUPATION_SERVICE_EXCLUSIONS.csv")
    assert len(exclusions) == 4
    assert (exclusions.quintiles_recomputed == False).all()  # noqa: E712
    assert (exclusions.analysis_status == LABEL).all()
    print("PASS_COMPOSITION_INFLUENCE_SELFCHECK")


if __name__ == "__main__":
    main()
