#!/usr/bin/env python3
import json
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"

static = pd.read_csv(RESULTS / "POPULATION_CONTROL_STATIC_SENSITIVITIES.csv")
era = pd.read_csv(RESULTS / "POPULATION_CONTROL_ERA_COMPARISON.csv")
january = pd.read_csv(RESULTS / "JANUARY_2025_RAW_DISCONTINUITY.csv")
receipt = json.loads((RESULTS / "POPULATION_CONTROL_AUDIT_RECEIPT.json").read_text())

assert len(static) == 5
assert len(era) == 6
assert len(january) == 2
assert receipt["counterfactual_weight_series_constructed"] is False
assert receipt["protected_artifacts_modified"] is False

frozen = static.loc[static.specification.eq("frozen_108_month_chronology_benchmark")].iloc[0]
repaired = static.loc[static.specification.eq("repaired_113_month_substantive_baseline")].iloc[0]
unweighted = static.loc[
    static.specification.eq("repaired_113_month_unweighted_respondent_equivalent")
].iloc[0]
assert np.isclose(frozen.coefficient, -0.13107397642233506, atol=1e-10)
assert np.isclose(repaired.coefficient, -0.1345539535732939, atol=1e-10)
assert abs(repaired.coefficient - unweighted.coefficient) < .001
assert repaired.months == 113 and frozen.months == 108

weighted_delta = era.loc[
    era.specification.eq("stock_post_2025_2026_minus_post_2023_2024")
].iloc[0]
unweighted_delta = era.loc[
    era.specification.eq(
        "respondent_equivalent_post_2025_2026_minus_post_2023_2024"
    )
].iloc[0]
assert weighted_delta.ci_lower < 0 < weighted_delta.ci_upper
assert unweighted_delta.ci_upper < 0

weighted_jump = january.loc[january.cell_value.eq("stock")].iloc[0]
assert weighted_jump.January_minus_December > 0

print("PASS_POPULATION_CONTROL_SELFCHECK")
