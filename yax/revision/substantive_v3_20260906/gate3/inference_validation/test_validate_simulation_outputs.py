import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "yax_gate3_validate_simulation_outputs", HERE / "validate_simulation_outputs.py")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


def test_summary_recomputation_uses_each_procedures_declared_studentizer():
    rows = []
    for replicate in range(1, 201):
        base = (replicate - 100.5) / 1000
        for target, estimate in (
            ("pooled", base),
            ("family_month", 2 * base),
            ("family_month_minus_pooled", base),
        ):
            row = {
                "scenario": "empirical_null", "replicate": replicate,
                "target": target, "pseudo_truth": 0.0, "estimate": estimate,
                "occupation_se": .1, "family_se": .2,
                "pooled_separated_fraction": 0.0,
                "family_month_separated_fraction": 0.0,
            }
            for procedure, half_width in (
                ("occupation_rademacher", .15), ("occupation_webb", .16),
                ("family_rademacher", .30), ("family_webb", .31),
            ):
                row[f"{procedure}_lower"] = estimate - half_width
                row[f"{procedure}_upper"] = estimate + half_width
                row[f"{procedure}_critical"] = half_width / (
                    .1 if procedure.startswith("occupation_") else .2)
            rows.append(row)
    summary, stopping = VALIDATOR.expected_summary(pd.DataFrame(rows), 200, 0)
    pooled = summary.loc[summary.target.eq("pooled")].set_index("procedure")
    assert pooled.loc["occupation_webb", "mean_reported_se"] == .1
    assert pooled.loc["family_webb", "mean_reported_se"] == .2
    assert pooled.loc["crossfit_full_refit_oracle", "mean_reported_se"] == .1
    assert len(summary) == 15
    assert stopping["maximum_relevant_binomial_mcse"] >= 0


def test_empirical_sd_relative_error_uses_observed_fourth_moment():
    values = np.asarray([-2.0, -1.0, 0.0, 1.0, 2.0])
    centered = values - values.mean()
    expected = np.sqrt(
        max(0.0, np.mean(centered ** 4) / np.mean(centered ** 2) ** 2 - 1.0)
        / (4.0 * len(values)))
    assert VALIDATOR.empirical_sd_relative_mc_error(values) == expected
