#!/usr/bin/env python3
"""Mechanical validation for R3 dependence outputs."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

import numpy as np
import pandas as pd


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=pathlib.Path, required=True)
    args = parser.parse_args()
    receipt = json.loads((args.results_dir / "EXECUTION_RECEIPT.json").read_text())
    for name, expected in receipt["output_hashes"].items():
        assert sha256(args.results_dir / name) == expected, name
    rows = pd.read_csv(args.results_dir / "CORRECTED_TIME_HAC_RESULTS.csv")
    assert len(rows) == 15
    assert set(rows.lag_elapsed_calendar_months) == {0, 1, 4, 12, 16}
    assert (rows.full_calendar_months == 115).all()
    assert (rows.observed_model_months == 113).all()
    assert (rows.zero_placeholder_months == 2).all()
    assert (~rows.PSD_projection_applied).all()
    base = rows.loc[(rows.object == "corrected_baseline") & (rows.lag_elapsed_calendar_months == 0)].iloc[0]
    conditional = rows.loc[(rows.object == "SOC2_post_conditioned") & (rows.lag_elapsed_calendar_months == 0)].iloc[0]
    assert np.isclose(base.estimate, -0.1345539535732939, atol=1e-10, rtol=0)
    assert np.isclose(conditional.estimate, -0.0314737789148527, atol=1e-10, rtol=0)
    conservation = pd.read_csv(args.results_dir / "SCORE_CONSERVATION_AUDIT.csv")
    finite = conservation.loc[conservation.engine_reported_occupation_cluster_se.notna()]
    assert (finite.absolute_se_difference < 1e-8).all()
    few = pd.read_csv(args.results_dir / "SOC2_FEW_CLUSTER_RESULTS.csv")
    assert len(few) == 6
    assert set(few.wild_weight_distribution) == {"Rademacher", "Webb_six_point"}
    assert few.common_cluster_draws_across_objects.all()
    print("PASS_R3_DEPENDENCE_SELFCHECK")


if __name__ == "__main__":
    main()
