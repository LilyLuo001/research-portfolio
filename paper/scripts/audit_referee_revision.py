#!/usr/bin/env python3
"""Fail closed when revised prose no longer matches decisive machine results."""

from hashlib import sha256
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "yax" / "revision" / "referee_20260905" / "results"
P = ROOT / "paper"


def close(x, y, tol=5e-5):
    if abs(float(x) - y) > tol:
        raise AssertionError((x, y))


place = pd.read_csv(R / "core" / "PLACEBO_BENCHMARK.csv").set_index("architecture")
close(place.loc["beta_ai", "coefficient"], -0.114154)
ref = pd.read_csv(R / "core" / "REFERENCE_CONTRASTS.csv").set_index("contrast")
close(ref.loc["Q5_minus_Q2", "coefficient"], -0.045605)
close(ref.loc["Q5_minus_Q4", "coefficient"], -0.034046)
age = pd.read_csv(R / "balanced_cells" / "AGE_COMPARISON_RESULTS.csv").set_index("comparison")
close(age.loc["22_25_vs_26_35", "coefficient"], -0.130732)
time = pd.read_csv(R / "balanced_cells" / "TIME_HETEROGENEITY_RESULTS.csv").set_index("period")
close(time.loc["2025_2026_minus_2024", "coefficient"], -0.084590)
fg = pd.read_csv(R / "core" / "FG_LEAVE_ONE_OUT_RESULTS.csv")
close(fg[(fg.specification == "omit_dv_rating_alpha") & (fg.term == "G")].iloc[0].coefficient, 0.034242)
external = pd.read_csv(R / "external" / "EXTERNAL_ARCHITECTURE_OUTCOMES.csv").set_index("architecture")
close(external.loc["Webb_AI_patent_task", "coefficient"], -0.064926)
close(external.loc["OECD_AI_capability_gap_reversed", "coefficient"], -0.010956)
remote = pd.read_csv(R / "core" / "CATEGORICAL_REMOTE_RESULTS.csv").set_index("exposure_measure")
close(remote.loc["dv_rating_beta", "ai_coefficient"], -0.107664)
close(remote.loc["dv_rating_beta", "remote_coefficient"], 0.006480)
mob = pd.read_csv(R / "mobility" / "MOBILITY_THRESHOLD_RESULTS.csv")
row = mob[(mob.architecture_set == "all_six") & (mob.scale == "standardized_score") & (mob["sample"] == "all_switches") & (mob.threshold == .5)].iloc[0]
close(row.substantial_opposition_share_all_switches, 0.139987)

main_text = "\n".join(p.read_text() for p in sorted((P / "main").rglob("*.tex")))
required = [
    "Constructed Exposure Measures and Statement-Specific Robustness",
    "AI specificity is not established",
    "Q5--Q2",
    "2025--26",
    "post-outcome exploratory",
]
for marker in required:
    if marker not in main_text:
        raise AssertionError(f"required main-text marker missing: {marker}")

receipt = {
    "status": "PASS",
    "checks": [
        "placebo primary", "Q5-Q2 and Q5-Q4", "nearest age comparison",
        "post-2025 contrast", "no-alpha G refit", "external architectures",
        "categorical remote coefficients", "0.5-SD mobility opposition",
        "required framing and chronology language",
    ],
    "result_files_sha256": {
        str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest()
        for p in sorted(R.rglob("*")) if p.is_file()
    },
}
out = ROOT / "yax" / "revision" / "referee_20260905" / "FINAL_NUMERIC_AUDIT.json"
out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(json.dumps({"status": "PASS", "checks": len(receipt["checks"]), "hashed_results": len(receipt["result_files_sha256"])}))
