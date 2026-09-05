#!/usr/bin/env python3
"""Fail-closed numerical and disclosure audit for the substantive R3 package.

The script reads only versioned aggregate results.  It does not access CPS
microdata.  Rounded manuscript tokens are checked against a single declared
source row, while model-specific alternative inference procedures remain
separately labelled in the appendix.
"""

from __future__ import annotations

import csv
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
R3 = ROOT / "yax" / "revision" / "substantive_r3_20260905"
PAPER = ROOT / "paper"
OUT_JSON = R3 / "SUBSTANTIVE_REVISION_AUDIT.json"
OUT_CSV = R3 / "NUMERICAL_CONSISTENCY_AUDIT.csv"


def close(actual: object, expected: float, tol: float = 5e-6) -> None:
    if abs(float(actual) - expected) > tol:
        raise AssertionError(f"expected {expected}, found {actual}")


def one(df: pd.DataFrame, **selector: object) -> pd.Series:
    mask = pd.Series(True, index=df.index)
    for key, value in selector.items():
        mask &= df[key].eq(value)
    rows = df.loc[mask]
    if len(rows) != 1:
        raise AssertionError(f"selector {selector!r} returned {len(rows)} rows")
    return rows.iloc[0]


numeric_checks: list[dict[str, str]] = []


def record(
    claim_id: str,
    source: str,
    selector: str,
    field: str,
    actual: object,
    expected: float,
    manuscript_token: str,
    tol: float = 5e-6,
) -> None:
    close(actual, expected, tol)
    numeric_checks.append(
        {
            "claim_id": claim_id,
            "source": source,
            "selector": selector,
            "field": field,
            "source_value": f"{float(actual):.12g}",
            "expected_value": f"{expected:.12g}",
            "manuscript_token": manuscript_token,
            "status": "PASS",
        }
    )


# Canonical rebuilt static result and paired broad-family comparison.
rel = "rebuilt_baseline/results/BASELINE_DECOMPOSITION.csv"
base = pd.read_csv(R3 / rel)
row = one(base, row_id="corrected_113_recomputed_preperiod_treatment")
for field, expected, token in [
    ("coefficient", -0.132109450792, "-0.1321"),
    ("analytic_cluster_se", 0.0451739, "0.0452"),
    ("ci_lower", -0.220565, "-0.2206"),
    ("ci_upper", -0.043654, "-0.0437"),
]:
    record("BASE03", rel, "row_id=corrected_113_recomputed_preperiod_treatment", field, row[field], expected, token, 8e-6)
assert int(row["occupations"]) == 468 and int(row["months"]) == 113

rel = "dynamics/results/STATIC_STRUCTURE_PAIRING.csv"
pair = pd.read_csv(R3 / rel)
row = one(pair, treatment_contract="rebuilt_corrected_preperiod_weight")
for field, expected, token in [
    ("conditioned_coefficient", -0.0216749520182, "-0.0217"),
    ("conditioned_ci_lower", -0.1606508, "-0.1607"),
    ("conditioned_ci_upper", 0.1173009, "0.1173"),
    ("conditioned_minus_unconditioned", 0.110434498774, "0.1104"),
    ("paired_ci_lower", 0.0106982, "0.0107"),
    ("paired_ci_upper", 0.2101708, "0.2102"),
    ("paired_normal_theory_MDE80", 0.1453866, "0.1454"),
]:
    record("STRUCTURE", rel, "treatment_contract=rebuilt_corrected_preperiod_weight", field, row[field], expected, token, 8e-6)

# Dynamic pretrends, post functional, and official HonestDiD provenance.
rel = "dynamics/results/PRETREND_TESTS.csv"
pre = pd.read_csv(R3 / rel)
for structure, expected, token in [
    ("unconditioned", 0.0149, "0.0149"),
    ("SOC2_x_calendar_month", 0.0053, "0.0053"),
]:
    row = one(
        pre,
        treatment_contract="rebuilt_corrected_preperiod_weight",
        structure=structure,
        test="all_pre_Q5_coefficients_jointly_zero",
    )
    record(f"PRE-{structure}", rel, f"rebuilt/{structure}/joint", "wild_score_p_value", row["wild_score_p_value"], expected, token)
    assert int(row["restrictions"]) == 23

rel = "dynamics/results/STATIC_DYNAMIC_MAPPING.csv"
dyn = pd.read_csv(R3 / rel)
for structure, coefficient, lo, hi, tokens in [
    ("unconditioned", -0.119889, -0.261836, 0.022058, ("-0.1199", "-0.2618", "0.0221")),
    ("SOC2_x_calendar_month", -0.207434, -0.421567, 0.006700, ("-0.2074", "-0.4216", "0.0067")),
]:
    row = one(dyn, treatment_contract="rebuilt_corrected_preperiod_weight", structure=structure)
    for field, expected, token in zip(
        ("dynamic_functional_coefficient", "dynamic_functional_ci_lower", "dynamic_functional_ci_upper"),
        (coefficient, lo, hi),
        tokens,
    ):
        record(f"DYN-{structure}", rel, f"rebuilt/{structure}", field, row[field], expected, token, 8e-6)

honest = pd.read_csv(R3 / "dynamics/results/HONESTDID_EXECUTION_RECEIPT.csv")
assert len(honest) == 4
assert set(honest["package"]) == {"HonestDiD"}
assert set(honest["package_version"].astype(str)) == {"0.2.8"}
assert set(honest["official_source_commit"]) == {"6813f02ed38f0b63bdca6915604b2eac90491303"}
assert honest["conventional_interval_includes_zero"].astype(bool).all()

# Characteristic, industry, education, flow, BCC, and architecture checkpoints.
rel = "architecture/results/CHARACTERISTIC_CONDITIONING_RESULTS.csv"
characteristics = pd.read_csv(R3 / rel)
for model, expected, token in [
    ("beta_plus_Webb", -0.107041, "-0.1070"),
    ("beta_plus_Webb_plus_computer", -0.212433, "-0.2124"),
    ("beta_plus_Webb_plus_remote", -0.115544, "-0.1155"),
]:
    row = one(characteristics, model=model)
    record(f"CHAR-{model}", rel, f"model={model}", "coefficient", row["coefficient"], expected, token, 8e-6)
    assert int(row["support_occupations"]) == 408

rel = "architecture/results/LAMBDA_GRID_RESULTS.csv"
lam = pd.read_csv(R3 / rel)
expected_lambda = {0.0: -0.102791, 0.25: -0.100732, 0.5: -0.132109, 0.75: -0.142765, 1.0: -0.155621}
for value, expected in expected_lambda.items():
    row = one(lam, lambda_=value) if "lambda_" in lam.columns else one(lam, **{"lambda": value})
    record(f"LAMBDA-{value:.2f}", rel, f"lambda={value:.2f}", "categorical_coefficient", row["categorical_coefficient"], expected, f"{expected:.4f}", 8e-6)

rel = "inference_rebuilt/results/SOC2_WILD_SENSITIVITY.csv"
few = pd.read_csv(R3 / rel)
row = one(few, object="paired_movement", wild_weight_distribution="Webb_six_point")
record("INF-SOC2-PAIR", rel, "paired_movement/Webb", "wild_score_ci_lower", row["wild_score_ci_lower"], 0.005876, "0.0059", 8e-6)
record("INF-SOC2-PAIR", rel, "paired_movement/Webb", "wild_score_ci_upper", row["wild_score_ci_upper"], 0.214993, "0.2150", 8e-6)
assert int(row["SOC2_clusters"]) == 22 and int(row["wild_score_draws"]) == 99999

rel = "heterogeneity/results/HETEROGENEITY_MODEL_RESULTS.csv"
hetero = pd.read_csv(R3 / rel)
assert len(hetero) >= 8 and hetero["coefficient"].notna().all()
rel_pair = "heterogeneity/results/HETEROGENEITY_PAIRED_DIFFERENCES.csv"
hetero_pair = pd.read_csv(R3 / rel_pair)
assert len(hetero_pair) >= 5

rel = "flows/results/FLOW_AND_WORKER_OUTCOME_RESULTS.csv"
flows = pd.read_csv(R3 / rel)
for model, expected, token in [
    ("adjacent_month__employment_exit__official", 0.132475442283, "0.132"),
    ("adjacent_month__occupational_outflow__official", 0.002546, "0.003"),
    ("adjacent_month__entry_destination__official", -0.070399, "-0.070"),
    ("twelve_month__employment_exit__official", 0.122722, "0.123"),
    ("twelve_month__occupational_outflow__official", -0.017841, "-0.018"),
    ("twelve_month__entry_destination__official", -0.051945, "-0.052"),
]:
    row = one(flows, model_id=model)
    record(f"FLOW-{model}", rel, f"model_id={model}", "coefficient", row["coefficient"], expected, token, 8e-6)
    assert float(row["wild_score_ci_lower"]) < 0 < float(row["wild_score_ci_upper"])

rel = "bcc_bridge/results/STATIC_MODEL_RESULTS.csv"
bcc = pd.read_csv(R3 / rel)
row = one(
    bcc,
    grouping_name="public_dashboard_equal_occupation_approximation",
    conditioning_structure="occupation_plus_calendar_month_FE",
)
record("BCC-STOCK", rel, "equal_occupation_approximation/unconditioned", "coefficient", row["coefficient"], -0.072037, "-0.0720", 8e-6)

# The family-harmonization output is mandatory: all support and tables must use
# the rebuilt treatment contract, not the historical family run.
family_dir = R3 / "dynamics" / "rebuilt_family_harmonization" / "results"
for name in [
    "REBUILT_Q1_Q5_AGGREGATE_PATHS.csv",
    "FAMILY_QUINTILE_SUPPORT.csv",
    "PROFILE_COEFFICIENTS.csv",
    "DIRECT_TAIL_MODELS.csv",
    "CONTINUOUS_WITHIN_FAMILY_MODELS.csv",
    "REBUILT_SELF_CHECK.json",
]:
    if not (family_dir / name).is_file():
        raise AssertionError(f"mandatory rebuilt-family output missing: {name}")
family_self = json.loads((family_dir / "REBUILT_SELF_CHECK.json").read_text())
assert "PASS" in str(family_self.get("status", ""))

rel = "dynamics/rebuilt_family_harmonization/results/DIRECT_TAIL_MODELS.csv"
direct = pd.read_csv(R3 / rel)
row = one(direct, model_id="direct_SOC2_x_calendar_month")
for field, expected, token in [
    ("coefficient", 0.149364, "0.1494"),
    ("pointwise_ci_lower", -0.169434, "-0.1694"),
    ("pointwise_ci_upper", 0.468161, "0.4682"),
    ("preperiod_stock_share_of_full_support", 0.050294, "5.03"),
]:
    record("FAM-DIRECT", rel, "model_id=direct_SOC2_x_calendar_month", field, row[field], expected, token, 8e-6)
assert int(row["support_occupations"]) == 29

rel = "dynamics/rebuilt_family_harmonization/results/CONTINUOUS_WITHIN_FAMILY_MODELS.csv"
continuous = pd.read_csv(R3 / rel)
row = one(continuous, model_id="continuous_SOC2_x_calendar_month")
for field, expected, token in [
    ("scale_raw_beta_units_per_one_z", 0.108385, "0.1084"),
    ("coefficient", -0.002465, "-0.0025"),
    ("pointwise_ci_lower", -0.023989, "-0.0240"),
    ("pointwise_ci_upper", 0.019059, "0.0191"),
]:
    record("FAM-CONTINUOUS", rel, "model_id=continuous_SOC2_x_calendar_month", field, row[field], expected, token, 8e-6)

# Every core module must carry a passing self-check.
core_selfchecks = [
    "rebuilt_baseline/results/SELF_CHECK.json",
    "data_audit/results/SELF_CHECK.json",
    "heterogeneity/results/SELF_CHECK.json",
    "inference_rebuilt/results/SELF_CHECK.json",
    "dynamics/results/SELF_CHECK.json",
    "bcc_bridge/results/SELF_CHECK.json",
    "flows/results/SELF_CHECK.json",
    "flows/results_household/SELF_CHECK.json",
    "architecture/results/SELF_CHECK.json",
]
for relpath in core_selfchecks:
    payload = json.loads((R3 / relpath).read_text())
    if "PASS" not in str(payload.get("status", "")):
        raise AssertionError(f"nonpassing self-check: {relpath}")

# Scientific sources and response documents must agree on canonical rounded
# values and must preserve the interpretation boundaries.
main_paths = [
    PAPER / "main" / "abstract_restat.tex",
    PAPER / "main" / "abstract_working.tex",
    *sorted((PAPER / "main" / "sections").glob("*.tex")),
    *sorted((PAPER / "tables").glob("r3_*.tex")),
]
appendix_paths = [PAPER / "appendix" / "appendix.tex", *sorted((PAPER / "appendix" / "sections").glob("r3_*.tex"))]
response_paths = [PAPER / "revision" / "referee_response.tex", PAPER / "revision" / "revision_diagnosis.tex"]
main_text = "\n".join(path.read_text() for path in main_paths)
appendix_text = "\n".join(path.read_text() for path in appendix_paths)
response_text = "\n".join(path.read_text() for path in response_paths)
all_text = "\n".join((main_text, appendix_text, response_text))


def prose_words(text: str) -> int:
    text = re.sub(r"%.*", " ", text)
    text = re.sub(
        r"\\(?:cite\w*|ref|eqref|label|input|includegraphics|bibliography|bibliographystyle)(?:\[[^]]*\])?\{[^}]*\}",
        " ",
        text,
    )
    text = re.sub(r"\\[A-Za-z@]+\*?(?:\[[^]]*\])?", " ", text)
    text = re.sub(r"[{}$&_^~\\]", " ", text)
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'’-]*", text))


included_main = [PAPER / "main" / "abstract_working.tex", *sorted((PAPER / "main" / "sections").glob("0[1-8]_*.tex"))]
current_main_words = prose_words("\n".join(path.read_text() for path in included_main))
baseline_sources = []
for path in included_main:
    relpath = path.relative_to(ROOT)
    baseline_sources.append(subprocess.check_output(["git", "show", f"6b8d85e:{relpath}"], text=True))
baseline_main_words = prose_words("\n".join(baseline_sources))
main_reduction_share = 1 - current_main_words / baseline_main_words
if not 0.33 <= main_reduction_share <= 0.42:
    raise AssertionError(
        f"main-text contraction outside requested range: {main_reduction_share:.3%} "
        f"({baseline_main_words} to {current_main_words} words)"
    )

for token in [
    "-0.1321", "-0.2206", "-0.0437", "-0.0217", "-0.1607", "0.1173",
    "0.1104", "0.0107", "0.2102", "0.1454", "3.33", "97.7",
]:
    if token not in all_text:
        raise AssertionError(f"required rounded manuscript token absent: {token}")

for required in [
    "not a causal decomposition",
    "economic equivalence",
    "does not identify",
    "[AUTHOR TO COMPLETE]",
]:
    if required.lower() not in all_text.lower():
        raise AssertionError(f"required interpretive boundary absent: {required}")

for forbidden in [
    "AI caused the decline",
    "composition explains most",
    "demonstrates economic equivalence",
    "replicates the ADP",
]:
    if forbidden.lower() in all_text.lower():
        raise AssertionError(f"forbidden overclaim found: {forbidden}")

appendix_driver = (PAPER / "appendix" / "appendix.tex").read_text()
for retired_input in ["appendix_H_mobility", "appendix_I_FG_AE"]:
    if retired_input in appendix_driver:
        raise AssertionError(f"retired scientific-appendix input remains active: {retired_input}")

# No unfinished response/registry statuses may survive production, except
# explicitly documented external blockers.
spec = pd.read_csv(R3 / "SPECIFICATION_REGISTRY.csv", keep_default_na=False)
unfinished = spec[spec["status"].isin(["planned", "pending_audit", "blocked_on_results", "in_progress"])]
if len(unfinished):
    raise AssertionError("unfinished specification rows: " + ",".join(unfinished["spec_id"]))
matrix = pd.read_csv(R3 / "responses" / "COMMENT_RESPONSE_MATRIX.csv", keep_default_na=False)
unfinished_matrix = matrix[matrix["status"].str.contains("pending|in_progress|writing", case=False, regex=True)]
if len(unfinished_matrix):
    raise AssertionError("unfinished response rows: " + ",".join(unfinished_matrix["report"] + ":" + unfinished_matrix["comment_id"]))

for required_file in [
    PAPER / "figures" / "r3_figure1_q1_q5_paths.pdf",
    PAPER / "figures" / "r3_figure2_dynamics.pdf",
    PAPER / "tables" / "r3_appendix_family_support.tex",
    PAPER / "tables" / "r3_appendix_profile.tex",
    R3 / "UNRESOLVED_ITEMS.md",
    R3 / "REPRODUCIBILITY.md",
    R3 / "ENVIRONMENT_LOCK.txt",
]:
    if not required_file.is_file() or required_file.stat().st_size == 0:
        raise AssertionError(f"required final artifact missing or empty: {required_file.relative_to(ROOT)}")

with OUT_CSV.open("w", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(numeric_checks[0]))
    writer.writeheader()
    writer.writerows(numeric_checks)

result_files = [
    path
    for path in R3.rglob("*")
    if path.is_file()
    and "__pycache__" not in path.parts
    and path not in {OUT_JSON, OUT_CSV}
    and path.name not in {".DS_Store"}
]
receipt = {
    "status": "PASS_SUBSTANTIVE_R3_AUDIT",
    "numeric_checks": len(numeric_checks),
    "main_text_word_audit": {
        "baseline_commit": "6b8d85e",
        "baseline_words": baseline_main_words,
        "revised_words": current_main_words,
        "reduction_share": main_reduction_share,
        "method": "deterministic TeX-control-stripped source token count; included abstract and sections 01--08",
    },
    "core_selfchecks": core_selfchecks,
    "manuscript_sources_checked": [str(p.relative_to(ROOT)) for p in main_paths + appendix_paths + response_paths],
    "result_files_sha256": {
        str(path.relative_to(ROOT)): sha256(path.read_bytes()).hexdigest()
        for path in sorted(result_files)
    },
}
OUT_JSON.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(json.dumps({"status": receipt["status"], "numeric_checks": len(numeric_checks), "hashed_files": len(result_files)}))
