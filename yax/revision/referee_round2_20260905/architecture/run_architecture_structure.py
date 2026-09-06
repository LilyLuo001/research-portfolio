#!/usr/bin/env python3
"""Audit dimensionality of the six original exposure implementations.

POST-OUTCOME EXPLORATORY. No labor-market outcome is read. The calculation uses
the frozen preperiod occupation employment weights and literal six-score
complete support. Principal components summarize dependence; they are not new
exposure architectures.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[4]
INPUT = ROOT / "yax/measurement/test_a/TEST_A_OCCUPATION_CHARACTERISTICS.csv"
COMPUTERIZATION = ROOT / "yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv"
FROZEN_COMMON = (
    ROOT / "yax/revision/referee_20260905/results/core/TAIL_STABILITY_OCCUPATIONS.csv"
)
OUT = Path(__file__).resolve().parent / "results"
MEASURES = [
    "aioe_admin_equal",
    "aioe_ability_direct",
    "aioe_oews2018_source_weighted",
    "dv_rating_alpha",
    "dv_rating_beta",
    "dv_rating_gamma",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    frame = pd.read_csv(INPUT, dtype={"census2018": str})
    computers = pd.read_csv(COMPUTERIZATION, dtype={"census2018": str})[
        ["census2018", "webb_pct_software"]
    ]
    frame = frame.merge(computers, on="census2018", how="left")
    frozen_codes = set(
        pd.read_csv(FROZEN_COMMON, dtype={"occupation_code": str}).occupation_code
    )
    panels = {
        "six_score_complete": frame.dropna(
            subset=["preperiod_employment_weight", *MEASURES]
        ).copy(),
        "six_score_plus_webb_model_support": frame.dropna(
            subset=["preperiod_employment_weight", "webb_pct_software", *MEASURES]
        ).copy(),
        "frozen_six_score_plus_webb_common_support": frame[
            frame.census2018.isin(frozen_codes)
        ].dropna(subset=["preperiod_employment_weight", "webb_pct_software", *MEASURES]).copy(),
    }
    rows = []
    receipts = {}
    correlations = []
    for panel_name, selected in panels.items():
        selected = selected[selected.preperiod_employment_weight > 0].copy()
        weights = selected.preperiod_employment_weight.to_numpy(float)
        weights /= weights.sum()
        raw = selected[MEASURES].to_numpy(float)
        means = np.sum(weights[:, None] * raw, axis=0)
        centered = raw - means
        sds = np.sqrt(np.sum(weights[:, None] * centered**2, axis=0))
        standardized = centered / sds
        correlation = standardized.T @ (weights[:, None] * standardized)
        correlation = (correlation + correlation.T) / 2
        eigenvalues = np.linalg.eigvalsh(correlation)[::-1]
        shares = eigenvalues / eigenvalues.sum()
        cumulative = 0.0
        for component, (eigenvalue, share) in enumerate(zip(eigenvalues, shares), 1):
            cumulative += float(share)
            rows.append({
                "support_definition": panel_name,
                "support_occupations": int(len(selected)),
                "component": component,
                "eigenvalue": float(eigenvalue),
                "variance_share": float(share),
                "cumulative_variance_share": cumulative,
            })
        for i, left in enumerate(MEASURES):
            for j, right in enumerate(MEASURES):
                correlations.append({
                    "support_definition": panel_name,
                    "left": left,
                    "right": right,
                    "weighted_correlation": float(correlation[i, j]),
                })
        receipts[panel_name] = {
            "support_occupations": int(len(selected)),
            "components_for_90_percent": int(np.searchsorted(np.cumsum(shares), .90) + 1),
            "components_for_95_percent": int(np.searchsorted(np.cumsum(shares), .95) + 1),
            "first_two_variance_share": float(shares[:2].sum()),
            "first_three_variance_share": float(shares[:3].sum()),
        }

    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT / "ARCHITECTURE_EIGEN_SPECTRUM.csv", index=False)
    pd.DataFrame(correlations).to_csv(OUT / "ARCHITECTURE_WEIGHTED_CORRELATION.csv", index=False)
    receipt = {
        "status": "PASS",
        "analysis_status": "POST-OUTCOME EXPLORATORY; TREATMENT-SIDE ONLY",
        "input": str(INPUT.relative_to(ROOT)),
        "input_sha256": sha256(INPUT),
        "computerization_input": str(COMPUTERIZATION.relative_to(ROOT)),
        "computerization_input_sha256": sha256(COMPUTERIZATION),
        "frozen_common_support_input": str(FROZEN_COMMON.relative_to(ROOT)),
        "frozen_common_support_input_sha256": sha256(FROZEN_COMMON),
        "weight": "frozen preperiod_employment_weight, normalized across complete support",
        "measures": MEASURES,
        "support_panels": receipts,
        "interpretation": (
            "The spectrum describes dependence among six implementations on literal "
            "complete support. It does not validate a latent-factor model or turn PCs "
            "into admissible exposure constructs."
        ),
    }
    (OUT / "ARCHITECTURE_STRUCTURE_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
