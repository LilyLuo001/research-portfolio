#!/usr/bin/env python3
"""Derive a transparent linear pretrend functional from public aggregate results.

The script reads only the stored rebuilt quarterly coefficient vector and its
occupation-cluster covariance.  It does not access CPS microdata.  The target
is the OLS slope, in log points per calendar year, through the 23 estimated
preperiod Q5 coefficients.  This low-dimensional functional complements rather
than replaces the unrestricted joint preperiod test.
"""
from __future__ import annotations

import csv
import pathlib

import numpy as np
import pandas as pd


ROOT = pathlib.Path(__file__).resolve().parents[2]
RESULTS = ROOT / "yax/revision/substantive_r3_20260905/dynamics/results"
OUTPUT = RESULTS / "PRETREND_LINEAR_DRIFT_PRECISION.csv"
CONTRACT = "rebuilt_corrected_preperiod_weight"
Z_975 = 1.959963984540054
Z_80 = 0.8416212335729143


def main() -> None:
    profile = pd.read_csv(RESULTS / "DYNAMIC_TARGET_PROFILE.csv")
    rows = []
    for structure in ("unconditioned", "SOC2_x_calendar_month"):
        subset = profile.loc[
            profile["treatment_contract"].eq(CONTRACT)
            & profile["structure"].eq(structure)
            & profile["quintile"].eq(5)
            & profile["event_bin"].lt("2022Q4")
        ].sort_values("event_bin")
        if len(subset) != 23:
            raise RuntimeError(f"expected 23 Q5 preperiod coefficients for {structure}")
        labels = [f"Q5_x_{value}" for value in subset["event_bin"]]
        covariance_long = pd.read_csv(
            RESULTS / f"TARGET_COVARIANCE_{CONTRACT}_{structure}.csv"
        )
        covariance = covariance_long.pivot(
            index="row_target", columns="column_target",
            values="occupation_cluster_covariance",
        ).reindex(index=labels, columns=labels).to_numpy(float)
        if not np.isfinite(covariance).all() or not np.allclose(covariance, covariance.T):
            raise RuntimeError(f"invalid covariance for {structure}")
        time_years = np.arange(len(labels), dtype=float) / 4.0
        weights = (time_years - time_years.mean()) / np.sum(
            (time_years - time_years.mean()) ** 2
        )
        estimate = float(weights @ subset["coefficient"].to_numpy(float))
        standard_error = float(np.sqrt(weights @ covariance @ weights))
        rows.append({
            "analysis_status": "POST-OUTCOME EXPLORATORY",
            "treatment_contract": CONTRACT,
            "structure": structure,
            "target": "OLS linear slope through 23 estimated preperiod Q5 coefficients",
            "units": "log points per calendar year",
            "preperiod_quarters": len(labels),
            "first_quarter": subset["event_bin"].iloc[0],
            "last_quarter": subset["event_bin"].iloc[-1],
            "coefficient": estimate,
            "occupation_cluster_se": standard_error,
            "normal_ci_lower": estimate - Z_975 * standard_error,
            "normal_ci_upper": estimate + Z_975 * standard_error,
            "normal_theory_MDE80": (Z_975 + Z_80) * standard_error,
            "weight_definition": "centered quarterly time divided by centered sum of squares; multiplied by four through year units",
            "interpretation": "precision diagnostic for one linear functional; does not replace unrestricted joint pretrend test",
        })
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(rows[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    print(OUTPUT)


if __name__ == "__main__":
    main()
