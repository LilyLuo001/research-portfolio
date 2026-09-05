#!/usr/bin/env python3
"""Minimal internal-consistency checks for the BCC CPS bridge."""

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"

receipt = json.loads((RESULTS / "BCC_GROUPING_RECEIPT.json").read_text())
models = pd.read_csv(RESULTS / "BCC_GROUPING_ARCHITECTURE_RESULTS.csv")
paired = pd.read_csv(RESULTS / "BCC_GROUPING_PAIRED_DIFFERENCES.csv")

assert receipt["status"] == "PASS"
assert int(receipt["support_occupations"]) == 468
assert len(models) == 16
assert set(models["support_rule"]) == {"native", "literal_common"}
assert models.loc[models["support_rule"].eq("literal_common"), "support_occupations"].nunique() == 1
assert int(models.loc[models["support_rule"].eq("literal_common"), "support_occupations"].iloc[0]) == 426
assert len(paired) == 7
assert paired["common_occupation_multipliers"].all()
assert paired["bootstrap_draws"].eq(9999).all()

beta = models[(models["architecture"] == "dv_rating_beta") & (models["support_rule"] == "native")].iloc[0]
assert abs(float(beta["coefficient"]) - float(receipt["controlled_model"]["coefficient"])) < 1e-12

oecd = paired[paired["contrast"].str.endswith("oecd_ai_capability_gap_reversed")].iloc[0]
assert float(oecd["paired_ci_upper"]) < 0
assert (paired.loc[~paired.index.isin([oecd.name]), "paired_ci_lower"] <= 0).all()
assert (paired.loc[~paired.index.isin([oecd.name]), "paired_ci_upper"] >= 0).all()

print("PASS: BCC grouping bridge outputs are internally consistent")
