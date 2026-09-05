#!/usr/bin/env python3
"""Fail closed when the major-revision prose diverges from round-2 outputs."""

from hashlib import sha256
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "yax" / "revision" / "referee_round2_20260905"
P = ROOT / "paper"


def close(actual, expected, tolerance=5e-5):
    if abs(float(actual) - float(expected)) > tolerance:
        raise AssertionError((actual, expected))


comp = pd.read_csv(R / "composition_influence" / "results" / "COMPOSITION_MODELS.csv")
rep = comp[comp["calendar"].eq("March_repaired_113_month")].set_index("model")
close(rep.loc["frozen_baseline", "coefficient"], -0.134554)
close(rep.loc["SOC2_x_post", "coefficient"], -0.031474)
close(rep.loc["SOC2_x_calendar_month", "coefficient"], -0.031737)

pair = pd.read_csv(R / "composition_influence" / "results" / "COMPOSITION_PAIRED_DIFFERENCES.csv")
assert (pair["ci_lower"] > 0).all(), "SOC2-minus-baseline intervals must exclude zero above"

service = pd.read_csv(R / "composition_influence" / "results" / "OCCUPATION_SERVICE_EXCLUSIONS.csv").set_index("specification")
close(service.loc["exclude_Q1_SOC35_food_preparation_and_serving", "coefficient"], -0.119589)
close(service.loc["exclude_all_SOC35_37_39_in_person_services", "coefficient"], -0.136974)

canonical = pd.read_csv(R / "precision_rotation" / "results" / "CANONICAL_PRIMARY_INTERVAL.csv").iloc[0]
close(canonical["estimate_log_points"], -0.131074)
close(canonical["ci_lower"], -0.217075)
close(canonical["ci_upper"], -0.045073)
close(canonical["normal_theory_mde80_log_points"], 0.124418)

arch = pd.read_csv(R / "precision_rotation" / "results" / "PAIRED_ARCHITECTURE_PRECISION.csv")
assert ((arch["paired_ci_lower"] <= 0) & (arch["paired_ci_upper"] >= 0)).all()

bcc = pd.read_csv(R / "bcc_bridge" / "results" / "BCC_GROUPING_ARCHITECTURE_RESULTS.csv")
bcc_beta = bcc[(bcc["architecture"].eq("dv_rating_beta")) & (bcc["support_rule"].eq("native"))].iloc[0]
close(bcc_beta["coefficient"], -0.072766)

universe = pd.read_csv(R / "bridge_uncertainty" / "results" / "UNIVERSE_RECONCILIATION.csv")
assert len(universe) == 539
assert int(universe["in_frozen_490"].sum()) == 490
assert int(universe["in_route_expanded_495"].sum()) == 495

pca = pd.read_csv(R / "architecture" / "results" / "ARCHITECTURE_EIGEN_SPECTRUM.csv")
row2 = pca[
    (pca["support_definition"].eq("frozen_six_score_plus_webb_common_support"))
    & (pca["component"].eq(2))
].iloc[0]
close(row2["cumulative_variance_share"], 0.961108, tolerance=1e-4)

mobility = json.loads((R / "mobility_major" / "results" / "HOUSEHOLD_CLUSTER_BOOTSTRAP.json").read_text())
close(mobility["realized_conflict"]["point_on_sealed_represented_support"], 0.5328185)
close(mobility["realized_conflict"]["cluster_bootstrap_se"], 0.00197945)
close(mobility["realized_minus_benchmark"]["point_on_sealed_represented_support"], 0.00959187)
close(mobility["realized_minus_benchmark"]["variance_subtracted_cluster_sampling_se"], 0.00077634)
entry = json.loads((R / "mobility_major" / "results" / "ENTRY_DESTINATION_EVIDENCE.json").read_text())
close(entry["coefficient_log_points"], -0.0887622)
assert entry["wild_score_ci"][0] < 0 < entry["wild_score_ci"][1]

included = [
    P / "main" / "preamble.tex",
    P / "main" / "abstract_working.tex",
    *[P / "main" / "sections" / f"{i:02d}_{name}.tex" for i, name in [
        (1, "introduction"), (2, "literature"), (3, "measurement"),
        (4, "data_design"), (5, "support"), (6, "stock_results"),
        (7, "reallocation"), (8, "competing_interpretations")]],
]
main_text = "\n".join(path.read_text() for path in included)
for marker in [
    "AI Exposure or Occupational Composition?",
    "-0.0315",
    "does not detect a difference",
    "not an additive decomposition",
    "food-service recovery explains",
    "0.1244",
    "96.11",
]:
    if marker not in main_text:
        raise AssertionError(f"required major-revision marker missing: {marker}")

for forbidden in [
    "provide six independent validations",
    "AI caused the",
    "the estimates are economically equivalent",
    "broad assortativity explains most",
]:
    if forbidden in main_text:
        raise AssertionError(f"forbidden overclaim in main text: {forbidden}")

out = R / "MAJOR_REVISION_AUDIT.json"
result_files = [
    p for p in R.rglob("*")
    if p.is_file() and "__pycache__" not in p.parts and p != out
]
receipt = {
    "status": "PASS",
    "checks": [
        "corrected and SOC2 coefficients",
        "paired SOC2 movement",
        "service exclusions",
        "canonical interval and MDE",
        "architecture paired intervals",
        "BCC grouping",
        "539/490/495 universe reconciliation",
        "architecture spectrum",
        "mobility support and uncertainty",
        "entry-destination interpretation",
        "required and forbidden prose",
    ],
    "result_files_sha256": {
        str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest() for p in sorted(result_files)
    },
}
out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(json.dumps({"status": "PASS", "checks": len(receipt["checks"]), "hashed_results": len(result_files)}))
