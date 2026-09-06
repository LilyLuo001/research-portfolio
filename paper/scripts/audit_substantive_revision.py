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

rel = "dynamics/results/PRETREND_LINEAR_DRIFT_PRECISION.csv"
drift = pd.read_csv(R3 / rel)
drift_expected = {
    "unconditioned": (-0.0078308890094571, 0.0118658146925721, -0.0310874584541248, 0.0154256804352105, 0.0332430910435779),
    "SOC2_x_calendar_month": (0.0040598881979825, 0.0292488069338206, -0.0532667199830712, 0.0613864963790363, 0.0819430251532318),
}
for structure, expected_values in drift_expected.items():
    row = one(
        drift,
        treatment_contract="rebuilt_corrected_preperiod_weight",
        structure=structure,
    )
    if (
        row["target"] != "OLS linear slope through 23 estimated preperiod Q5 coefficients"
        or row["units"] != "log points per calendar year"
        or int(row["preperiod_quarters"]) != 23
        or row["first_quarter"] != "2017Q1"
        or row["last_quarter"] != "2022Q3"
    ):
        raise AssertionError(f"pretrend-drift contract changed for {structure}")
    for field, expected, token in zip(
        ("coefficient", "occupation_cluster_se", "normal_ci_lower", "normal_ci_upper", "normal_theory_MDE80"),
        expected_values,
        tuple(f"{value:.4f}" for value in expected_values),
    ):
        record(f"PRE-DRIFT-{structure}", rel, f"rebuilt/{structure}/linear_drift", field, row[field], expected, token, 8e-6)

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

rel = "dynamics/results/ENDPOINT_SENSITIVITY.csv"
endpoints = pd.read_csv(R3 / rel)
for structure, values, tokens in [
    (
        "unconditioned",
        (-0.1110386746699298, -0.2007657531618162, -0.0213115961780434, 0.0210707761222604, -0.0073127415348206, 0.0494542937793416, 0.0407110507801537),
        ("-0.1110", "-0.2008", "-0.0213", "0.0211", "-0.0073", "0.0495", "0.0407"),
    ),
    (
        "SOC2_x_calendar_month",
        (-0.0119961199735932, -0.1656653949418117, 0.1416731549946253, 0.0096788320446526, -0.052551897200756, 0.0719095612900614, 0.0897229417868637),
        ("-0.0120", "-0.1657", "0.1417", "0.0097", "-0.0526", "0.0719", "0.0897"),
    ),
]:
    row = one(
        endpoints,
        treatment_contract="rebuilt_corrected_preperiod_weight",
        structure=structure,
        grid="endpoint",
        variant="through_2024_12",
    )
    if row["status"] != "PASS" or int(row["months"]) != 95:
        raise AssertionError(f"December-2024 endpoint contract changed for {structure}")
    if not bool(row["common_occupation_multipliers_for_pair"]):
        raise AssertionError(f"December-2024 endpoint lacks common paired draws: {structure}")
    for field, expected, token in zip(
        (
            "coefficient",
            "ci_lower",
            "ci_upper",
            "difference_vs_reference",
            "paired_ci_lower_vs_reference",
            "paired_ci_upper_vs_reference",
            "paired_MDE80_vs_reference",
        ),
        values,
        tokens,
    ):
        record(
            f"DYN-ENDPOINT-2024-{structure}",
            rel,
            f"rebuilt/{structure}/through_2024_12",
            field,
            row[field],
            expected,
            token,
            8e-6,
        )

rel = "yax/revision/referee_round2_20260905/population_controls/results/POPULATION_CONTROL_ERA_COMPARISON.csv"
eras = pd.read_csv(ROOT / rel)
for specification, coefficient, lo, hi, tokens in [
    ("stock_post_2023_2024", -0.1107701585072698, -0.1974571827064755, -0.024083134308064, ("-0.1108", "-0.1975", "-0.0241")),
    ("stock_post_2025_2026", -0.1663857322550958, -0.2704362725725546, -0.0623351919376369, ("-0.1664", "-0.2704", "-0.0623")),
    ("stock_post_2025_2026_minus_post_2023_2024", -0.055615573747826, -0.1228370367736053, 0.0116058892779533, ("-0.0556", "-0.1228", "0.0116")),
    ("respondent_equivalent_post_2025_2026_minus_post_2023_2024", -0.0800404159832483, -0.1389944380565433, -0.0210863939099532, ("-0.0800", "-0.1390", "-0.0211")),
]:
    row = one(eras, specification=specification)
    for field, expected, token in zip(
        ("coefficient", "ci_lower", "ci_upper"),
        (coefficient, lo, hi),
        tokens,
    ):
        record(f"ERA-{specification}", rel, f"specification={specification}", field, row[field], expected, token, 8e-6)
    assert int(row["months_full_model"]) == 113 and int(row["support_occupations"]) == 468
    if "minus" in specification and not bool(row["paired_common_draws"]):
        raise AssertionError(f"era comparison lacks common draws: {specification}")

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

rel = "architecture/results/CHARACTERISTIC_CONDITIONING_PAIRED.csv"
characteristic_pairs = pd.read_csv(R3 / rel)
for left, estimate, lo, hi, tokens in [
    (
        "beta_plus_Webb_plus_computer",
        -0.1053919349221173,
        -0.183452153282273,
        -0.0273317165619616,
        ("-0.1054", "-0.1835", "-0.0273"),
    ),
    (
        "beta_plus_Webb_plus_remote",
        -0.0085027372907299,
        -0.0437004197074322,
        0.0266949451259724,
        ("-0.0085", "-0.0437", "0.0267"),
    ),
]:
    row = one(characteristic_pairs, left=left, right="beta_plus_Webb")
    for field, expected, token in zip(
        ("coefficient_difference", "ci_lower", "ci_upper"),
        (estimate, lo, hi),
        tokens,
    ):
        record(f"CHAR-PAIR-{left}", rel, f"{left}_minus_beta_plus_Webb", field, row[field], expected, token, 8e-6)
    if not bool(row["common_multiplier_draws"]):
        raise AssertionError(f"characteristic comparison lacks common draws: {left}")

# The expanded characteristic grid must use the same corrected-preperiod
# treatment contract as the active paper, rather than the historical
# full-static-panel assignment inherited by the first exploratory run.
expanded_rel = "characteristics/results/CHARACTERISTIC_MODEL_RESULTS.csv"
expanded = pd.read_csv(R3 / expanded_rel)
for model, estimate, lo, hi, tokens in [
    (
        "native_corrected_baseline",
        -0.1321094507921903,
        -0.2207464082642757,
        -0.0434724933201050,
        ("-0.132", "-0.221", "-0.043"),
    ),
    (
        "support_specific_computer_use_augmented",
        -0.1966022206064111,
        -0.3163856810931094,
        -0.0768187601197128,
        ("-0.197", "-0.316", "-0.077"),
    ),
    (
        "support_specific_SOC2_post_augmented",
        -0.0215989846315222,
        -0.1621117977612676,
        0.1189138284982231,
        ("-0.022", "-0.162", "0.119"),
    ),
]:
    row = one(expanded, specification=model)
    for field, expected, token in zip(
        ("coefficient", "ci_lower", "ci_upper"), (estimate, lo, hi), tokens
    ):
        record(
            f"CHAR-EXPANDED-{model}", expanded_rel, f"specification={model}",
            field, row[field], expected, token, 8e-6,
        )

expanded_pair_rel = "characteristics/results/CHARACTERISTIC_PAIRED_DIFFERENCES.csv"
expanded_pairs = pd.read_csv(R3 / expanded_pair_rel)
for contrast, estimate, lo, hi, tokens in [
    (
        "support_specific_computer_use_augmented_minus_support_specific_computer_use_baseline",
        -0.1008550338521072,
        -0.1764736471528550,
        -0.0252364205513593,
        ("-0.101", "-0.176", "-0.025"),
    ),
    (
        "support_specific_SOC2_post_augmented_minus_support_specific_SOC2_post_baseline",
        0.1105104661606681,
        0.0079977958698979,
        0.2130231364514383,
        ("0.111", "0.008", "0.213"),
    ),
]:
    row = one(expanded_pairs, contrast=contrast)
    for field, expected, token in zip(
        ("coefficient_difference", "paired_ci_lower", "paired_ci_upper"),
        (estimate, lo, hi), tokens,
    ):
        record(
            f"CHAR-EXPANDED-PAIR-{contrast}", expanded_pair_rel, contrast,
            field, row[field], expected, token, 8e-6,
        )
    if not bool(row["common_occupation_multipliers"]):
        raise AssertionError(f"expanded characteristic pair lacks common draws: {contrast}")

expanded_receipt = json.loads(
    (R3 / "characteristics/results/EXECUTION_RECEIPT.json").read_text(encoding="utf-8")
)
if expanded_receipt.get("treatment_contract") != "rebuilt_corrected_preperiod_weight":
    raise AssertionError("expanded characteristic grid does not use rebuilt treatment")
if expanded_receipt.get("no_postperiod_stock_used_for_treatment") is not True:
    raise AssertionError("expanded characteristic treatment admits postperiod stock")
if expanded_receipt.get("rebuilt_treatment_input_hashes") != {
    "membership": "c76eb85956e4a413e130bab53fe8c50616cf6d7a02c81c266ec369879dd56bc1",
    "normalization": "e756d597c12fc2b61ddf62e536b50d3edab32375980e7cea70e5de42fca57557",
}:
    raise AssertionError("expanded characteristic treatment hashes changed")

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

rel = "inference_rebuilt/results/CORRECTED_TIME_HAC_RESULTS.csv"
hac = pd.read_csv(R3 / rel)
for object_name, expected_se, lo, hi, mde, tokens in [
    ("pooled", 0.0444909550014034, -0.2193101202327332, -0.0449087813516475, 0.124645201871661, ("0.0445", "-0.2193", "-0.0449", "0.1246")),
    ("conditioned", 0.055220779170484, -0.1299056903906346, 0.086555786354142, 0.1547057186567086, ("0.0552", "-0.1299", "0.0866", "0.1547")),
    ("paired_movement", 0.0450047234250753, 0.0222268617266102, 0.198642135821278, 0.1260845678929536, ("0.0450", "0.0222", "0.1986", "0.1261")),
]:
    row = one(hac, object=object_name, lag_elapsed_calendar_months=16)
    for field, expected, token in zip(
        (
            "corrected_inclusion_exclusion_target_se",
            "normal_ci_lower",
            "normal_ci_upper",
            "normal_theory_MDE80",
        ),
        (expected_se, lo, hi, mde),
        tokens,
    ):
        record(f"INF-HAC16-{object_name}", rel, f"object={object_name}/lag=16", field, row[field], expected, token, 8e-6)
if len(hac) != 15:
    raise AssertionError(f"expected 15 rebuilt HAC rows, found {len(hac)}")
if set(hac["joint_covariance_status"]) != {"FULL_COVARIANCE_PSD"}:
    raise AssertionError("rebuilt HAC output contains an indefinite joint covariance matrix")
if (hac["negative_covariance_eigenvalues_at_scaled_tolerance"].astype(int) != 0).any():
    raise AssertionError("rebuilt HAC output reports a negative covariance eigenvalue")
if hac["PSD_projection_applied"].astype(bool).any():
    raise AssertionError("rebuilt HAC output unexpectedly applies a PSD projection")

rel = "heterogeneity/results/HETEROGENEITY_MODEL_RESULTS.csv"
hetero = pd.read_csv(R3 / rel)
assert len(hetero) >= 8 and hetero["coefficient"].notna().all()
rel_pair = "heterogeneity/results/HETEROGENEITY_PAIRED_DIFFERENCES.csv"
hetero_pair = pd.read_csv(R3 / rel_pair)
assert len(hetero_pair) >= 5

rel = "flows/results/FLOW_AND_WORKER_OUTCOME_RESULTS.csv"
flows = pd.read_csv(R3 / rel)
for model, expected, token, mde80, mde_token in [
    ("adjacent_month__employment_exit__official", 0.132475442283, "0.132", 0.2544258177, "0.254"),
    ("adjacent_month__occupational_outflow__official", 0.002546, "0.003", 0.1737868509, "0.174"),
    ("adjacent_month__entry_destination__official", -0.070399, "-0.070", 0.2596207256, "0.260"),
    ("twelve_month__employment_exit__official", 0.122722, "0.123", 0.3357876277, "0.336"),
    ("twelve_month__occupational_outflow__official", -0.017841, "-0.018", 0.1147284060, "0.115"),
    ("twelve_month__entry_destination__official", -0.051945, "-0.052", 0.2819424875, "0.282"),
]:
    row = one(flows, model_id=model)
    record(f"FLOW-{model}", rel, f"model_id={model}", "coefficient", row["coefficient"], expected, token, 8e-6)
    record(
        f"FLOW-MDE-{model}",
        rel,
        f"model_id={model}",
        "normal_theory_MDE80",
        row["normal_theory_MDE80"],
        mde80,
        mde_token,
        8e-6,
    )
    assert float(row["wild_score_ci_lower"]) < 0 < float(row["wild_score_ci_upper"])

risk_count_rel = "flows/results/FLOW_RISK_EVENT_COUNTS.csv"
risk_counts = pd.read_csv(R3 / risk_count_rel)
for model, expected, lo, hi, events, tokens in [
    ("adjacent_month__unemployment_entry__official", 0.054644, -0.271847, 0.381135, 32488, ("0.055", "-0.272", "0.381")),
    ("adjacent_month__labor_force_exit__official", 0.134549, -0.063874, 0.332972, 74480, ("0.135", "-0.064", "0.333")),
    ("twelve_month__unemployment_entry__official", 0.245926, -0.295237, 0.787088, 27330, ("0.246", "-0.295", "0.787")),
    ("twelve_month__labor_force_exit__official", 0.078016, -0.180866, 0.336898, 78773, ("0.078", "-0.181", "0.337")),
]:
    row = one(flows, model_id=model)
    for field, expected_value, token in zip(
        ("coefficient", "wild_score_ci_lower", "wild_score_ci_upper"),
        (expected, lo, hi),
        tokens,
    ):
        record(f"FLOW-COMP-{model}", rel, f"model_id={model}", field, row[field], expected_value, token, 8e-6)
    if int(row["event_contributing_occupations"]) <= 0:
        raise AssertionError(f"exit component has no event-contributing occupations: {model}")
    horizon, margin, weighting = model.split("__")
    count_row = one(risk_counts, horizon=horizon, margin=margin, weighting=weighting)
    record(
        f"FLOW-COMP-COUNT-{model}",
        risk_count_rel,
        f"horizon={horizon}/margin={margin}/weighting={weighting}",
        "event_raw_records",
        count_row["event_raw_records"],
        events,
        f"{events:,}",
        0.1,
    )

rel = "bcc_bridge/results/STATIC_MODEL_RESULTS.csv"
bcc = pd.read_csv(R3 / rel)
for structure, coefficient, lo, hi, tokens in [
    ("occupation_plus_calendar_month_FE", -0.072036954878501, -0.121849025769711, -0.022224883987291, ("-0.0720", "-0.1218", "-0.0222")),
    ("SOC2_x_post", -0.0147571956503785, -0.0796273050254381, 0.0501129137246809, ("-0.0148", "-0.0796", "0.0501")),
    ("SOC2_x_calendar_month", -0.0167729542707889, -0.0809855189534624, 0.0474396104118846, ("-0.0168", "-0.0810", "0.0474")),
]:
    row = one(
        bcc,
        grouping_name="public_dashboard_equal_occupation_approximation",
        conditioning_structure=structure,
    )
    for field, expected, token in zip(("coefficient", "ci_lower", "ci_upper"), (coefficient, lo, hi), tokens):
        record(f"BCC-{structure}", rel, f"equal_occupation_approximation/{structure}", field, row[field], expected, token, 8e-6)
    assert int(row["support_occupations"]) == 468

rel = "architecture/results/PRIMITIVE_ILLUSTRATIVE_CONTRASTS.csv"
primitive = pd.read_csv(R3 / rel)
for contrast, estimate, lo, hi, mde, tokens in [
    ("one_weighted_SD_D_holding_S_fixed", -0.0309234935212155, -0.0579822228974912, -0.0038647641449398, 0.0389299381248802, ("-0.0309", "-0.0580", "-0.0039", "0.0389")),
    ("one_weighted_SD_S_holding_D_fixed", -0.027926694422027, -0.0541845073631273, -0.0016688814809266, 0.0381126984177959, ("-0.0279", "-0.0542", "-0.0017", "0.0381")),
    ("one_weighted_SD_each_D_and_S", -0.0588501879432425, -0.0980577214576963, -0.0196426544287887, 0.0561438118545034, ("-0.0589", "-0.0981", "-0.0196", "0.0561")),
]:
    row = one(primitive, contrast=contrast)
    for field, expected, token in zip(
        ("raw_unit_estimate", "ci_lower", "ci_upper", "mde80"),
        (estimate, lo, hi, mde),
        tokens,
    ):
        record(f"ARCH-PRIMITIVE-{contrast}", rel, f"contrast={contrast}", field, row[field], expected, token, 8e-6)
    if not bool(row["common_multiplier_draws"]):
        raise AssertionError(f"primitive comparison lacks common draws: {contrast}")

# The family-harmonization output is mandatory: all support and tables must use
# the rebuilt treatment contract, not the historical family run.
family_dir = R3 / "dynamics" / "rebuilt_family_harmonization" / "results"
for name in [
    "REBUILT_Q1_Q5_AGGREGATE_PATHS.csv",
    "FAMILY_QUINTILE_SUPPORT.csv",
    "PROFILE_COEFFICIENTS.csv",
    "DIRECT_TAIL_MODELS.csv",
    "CONTINUOUS_WITHIN_FAMILY_MODELS.csv",
    "INFORMATION_DIAGNOSTICS.csv",
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

# Information and precision for the rebuilt family-support targets.  Absolute
# information is only compared within a target scale; relative information
# uses the corresponding pooled parent on the same target and population.
rel = "dynamics/rebuilt_family_harmonization/results/INFORMATION_DIAGNOSTICS.csv"
family_information = pd.read_csv(R3 / rel)
family_information_expected = {
    ("profile_baseline", "Q5_x_post"): (468, 26289231.23526308, 0.3783350210977821, 1.0, 43.24179410130085, 0.2449930555702378, 0.1265585171164715),
    ("profile_SOC2_x_calendar_month", "Q5_x_post"): (468, 7803023.092359761, 0.1124065972072296, 0.2968144265052973, 53.27437226583803, 0.2182183804522474, 0.1998162924289003),
    ("direct_SOC2_x_calendar_month", "Q5_x_post"): (29, 668942.8323098304, 0.0804079360858607, 0.3081671840526238, 6.232465172118025, 0.7775822736612467, 0.4575861111905094),
    ("continuous_SOC2_x_calendar_month", "within_SOC2_beta_z_x_post"): (468, 261278380.1101386, 0.5834547457637788, 0.9646781780209124, 48.02440426722479, 0.2489063330444246, 0.0313318972957119),
}
for (model_id, target), expected_values in family_information_expected.items():
    row = one(family_information, model_id=model_id, target=target)
    support, info, retained, relative, effective, top_five, mde80 = expected_values
    if int(row["support_occupations"]) != support:
        raise AssertionError(f"family-information support changed for {model_id}")
    for field, expected, token in zip(
        (
            "nuisance_adjusted_fisher_information",
            "information_retained_vs_raw",
            "information_relative_to_parent_baseline",
            "effective_occupation_information_count",
            "top_five_occupation_information_share",
            "normal_theory_MDE80",
        ),
        (info, retained, relative, effective, top_five, mde80),
        (
            f"{info / 1e6:.3f}",
            f"{retained:.3f}",
            f"{relative:.3f}",
            f"{effective:.1f}",
            f"{top_five:.3f}",
            f"{mde80:.4f}",
        ),
    ):
        record(
            f"FAM-INFO-{model_id}",
            rel,
            f"model_id={model_id}/target={target}",
            field,
            row[field],
            expected,
            token,
            8e-6,
        )

# The mapping-only count is distinct from the 468-occupation analysis support.
mapping_receipt = json.loads((ROOT / "yax" / "measurement" / "CPS_OCCUPATION_EXPOSURE_LOOKUP_RECEIPT.json").read_text())
mapping_coverage = mapping_receipt["coverage"]["raw_occ_main_2017_2019"]
if int(mapping_coverage["codes"]) != 503:
    raise AssertionError("pre-2020 mapping-source count changed")
aioe_admin_full = mapping_coverage["variants"]["aioe_admin_equal"]["full_coverage_codes"]
record(
    "MAP-AIOE-480",
    "yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP_RECEIPT.json",
    "coverage/raw_occ_main_2017_2019/variants/aioe_admin_equal",
    "full_coverage_codes",
    aioe_admin_full,
    480,
    "480",
    0.1,
)

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
active_main_text = "\n".join(path.read_text() for path in included_main)
current_main_words = prose_words(active_main_text)
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

if "post-outcome exploratory" not in active_main_text.lower():
    raise AssertionError("active manuscript does not disclose the post-outcome exploratory status")

profile_table_text = (PAPER / "tables" / "r3_appendix_profile.tex").read_text()
normalized_profile = re.sub(r"[\s$]", "", profile_table_text)
for required_interval in [
    "[-0.2206,-0.0437]",
    "[-0.1607,0.1173]",
    "0.1104[0.0107,0.2102]",
]:
    if required_interval not in normalized_profile:
        raise AssertionError(f"canonical Q5 profile interval absent: {required_interval}")

normalized_intervals = re.sub(r"[\s$]", "", all_text)
for stale_interval in [
    "[-0.2203,-0.0439]",
    "[-0.1595,0.1162]",
    "[0.0085,0.2124]",
]:
    if stale_interval in normalized_intervals:
        raise AssertionError(f"stale seed-dependent Q5 interval survives: {stale_interval}")

family_information_table = (PAPER / "tables" / "r3_appendix_family_information_precision.tex").read_text()
for required_row in [
    "Q5--Q1, pooled & 468 & 26.289 & 0.378 & 1.000 & 43.2 & 0.245 & 0.1266",
    "Q5--Q1, SOC2 $\\times$ month & 468 & 7.803 & 0.112 & 0.297 & 53.3 & 0.218 & 0.1998",
    "Direct-tail Q5--Q1, SOC2 $\\times$ month & 29 & 0.669 & 0.080 & 0.308 & 6.2 & 0.778 & 0.4576",
    "Continuous within-SOC2 slope, SOC2 $\\times$ month & 468 & 261.278 & 0.583 & 0.965 & 48.0 & 0.249 & 0.0313",
]:
    if required_row not in family_information_table:
        raise AssertionError(f"family-information table row absent: {required_row}")
for required_boundary in [
    "not comparable across all rows",
    "neither replaces the nominal occupation-cluster count nor measures first-stage CPS sampling precision",
    "normal-theory precision diagnostic, not a rejection result",
]:
    if required_boundary not in family_information_table:
        raise AssertionError(f"family-information interpretation boundary absent: {required_boundary}")

flow_table = (PAPER / "tables" / "r3_table5_flows.tex").read_text()
for required_row in [
    "Adjacent employment exit & 3,346,227 & $0.132$ & $[-0.042,0.307]$ & 0.254",
    "Adjacent reported-occupation change & 3,207,598 & $0.003$ & $[-0.118,0.123]$ & 0.174",
    "Adjacent entry-destination allocation & 96,981 & $-0.070$ & $[-0.250,0.110]$ & 0.260",
    "Twelve-month employment exit & 1,399,376 & $0.123$ & $[-0.111,0.357]$ & 0.336",
    "Twelve-month reported-occupation endpoint change & 1,110,024 & $-0.018$ & $[-0.097,0.061]$ & 0.115",
    "Twelve-month entry-destination allocation & 82,573 & $-0.052$ & $[-0.251,0.147]$ & 0.282",
]:
    if required_row not in flow_table:
        raise AssertionError(f"flow precision row absent: {required_row}")
if "normal-theory precision diagnostic, not the wild-score rejection threshold" not in flow_table:
    raise AssertionError("flow MDE interpretation boundary absent")

mapping_appendix = (PAPER / "appendix" / "sections" / "r3_B_mapping.tex").read_text()
for required_mapping_token in ["480 of the 503", "not the regression sample", "468-occupation primary analysis support"]:
    if required_mapping_token not in mapping_appendix:
        raise AssertionError(f"mapping/support count distinction absent: {required_mapping_token}")

core_table = (PAPER / "tables" / "r3_table2_occupation.tex").read_text()
if "SOC2 $\\times$ young $\\times$ month & $-0.0217$ & $[-0.1607,0.1173]$ & $0.1104$ & 0.1998" not in core_table:
    raise AssertionError("family-conditioned MDE80 is not source-consistent in Main Table 2")

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
    "uses Eloundou et al.'s published notation $\\alpha$, $\\beta$, and $\\zeta$",
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

# Evidence locators must be clickable/auditable rather than informal labels.
# Semicolons delimit locators; repo paths must exist, while non-filesystem
# provenance must declare its type explicitly.
for _, response_row in matrix.iterrows():
    locators = [item.strip() for item in response_row["evidence_location"].split(";") if item.strip()]
    if not locators:
        raise AssertionError(
            f"empty evidence locator: {response_row['report']}:{response_row['comment_id']}"
        )
    for locator in locators:
        if locator.startswith("git-tag:"):
            tag = locator.removeprefix("git-tag:")
            if not tag:
                raise AssertionError("empty git-tag evidence locator")
            tag_check = subprocess.run(
                ["git", "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}"],
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if tag_check.returncode != 0:
                raise AssertionError(f"evidence git tag does not exist: {tag}")
            continue
        if locator.startswith("external:"):
            if not locator.removeprefix("external:").strip():
                raise AssertionError("empty external evidence locator")
            continue
        relative = Path(locator)
        if relative.is_absolute() or ".." in relative.parts:
            raise AssertionError(f"evidence locator is not repo relative: {locator}")
        if not (ROOT / relative).exists():
            raise AssertionError(
                f"evidence locator does not exist: {response_row['report']}:"
                f"{response_row['comment_id']}:{locator}"
            )

gamma_row = one(matrix, report="R1", comment_id="S11")
if "alpha, beta, and zeta" in gamma_row["response_or_limitation"]:
    raise AssertionError("stale alpha/beta/zeta reporting claim remains in response matrix")
for required_gamma_token in ["D=E1", "S=E2", "dv_rating_gamma", "published zeta"]:
    if required_gamma_token not in gamma_row["response_or_limitation"]:
        raise AssertionError(f"Eloundou notation response lacks: {required_gamma_token}")

for report, comment_id in [("R1", "M5"), ("R1", "M9"), ("R2", "M4")]:
    endpoint_response = one(matrix, report=report, comment_id=comment_id)
    if "dynamics/results/ENDPOINT_SENSITIVITY.csv" not in endpoint_response["evidence_location"]:
        raise AssertionError(f"December-2024 endpoint source absent from {report}:{comment_id}")
    for required_endpoint_token in ["post-outcome exploratory", "-0.1110", "-0.0120"]:
        if required_endpoint_token not in endpoint_response["response_or_limitation"]:
            raise AssertionError(
                f"December-2024 endpoint reporting absent from {report}:{comment_id}:"
                f"{required_endpoint_token}"
            )
for required_response_token in [
    "December-2024 pooled coefficient is $-0.1110$",
    "endpoint-minus-full-window difference is 0.0211 ($[-0.0073,0.0495]$)",
    "family-conditioned coefficient is $-0.0120$ ($[-0.1657,0.1417]$)",
    "paired difference 0.0097 ($[-0.0526,0.0719]$)",
]:
    if required_response_token not in response_text:
        raise AssertionError(f"referee response omits December-2024 endpoint detail: {required_response_token}")

ledger = pd.read_csv(R3 / "RESULTS_LEDGER.csv", keep_default_na=False)
row = one(ledger, spec_id="INF-04")
if (
    row["status"] != "complete"
    or row["output_path"] != "yax/revision/substantive_r3_20260905/inference_rebuilt/results/CORRECTED_TIME_HAC_RESULTS.csv"
    or "0 of 15 are indefinite" not in row["notes"]
):
    raise AssertionError("INF-04 ledger row does not describe the rebuilt PSD HAC result")
for field, expected in [
    ("estimate", -0.1321094508),
    ("se", 0.044491),
    ("ci_low", -0.219310),
    ("ci_high", -0.044909),
    ("mde80", 0.124645),
]:
    close(row[field], expected, 8e-6)

row = one(ledger, spec_id="FAM-01-REBUILT")
if row["output_path"] != "dynamics/results/STATIC_STRUCTURE_PAIRING.csv":
    raise AssertionError("FAM-01-REBUILT ledger row does not cite the canonical single-target source")
for field, expected in [
    ("estimate", -0.021675),
    ("ci_low", -0.160651),
    ("ci_high", 0.117301),
]:
    close(row[field], expected, 8e-6)

for required_file in [
    PAPER / "figures" / "r3_figure1_q1_q5_paths.pdf",
    PAPER / "figures" / "r3_figure2_dynamics.pdf",
    PAPER / "figures" / "r3_figure3_family_paths.pdf",
    PAPER / "tables" / "r3_appendix_family_support.tex",
    PAPER / "tables" / "r3_appendix_family_information_precision.tex",
    PAPER / "tables" / "r3_appendix_profile.tex",
    PAPER / "tables" / "r3_appendix_lofo.tex",
    PAPER / "tables" / "r3_appendix_characteristic_estimates.tex",
    PAPER / "tables" / "r3_appendix_characteristic_information.tex",
    PAPER / "tables" / "r3_appendix_population_eras.tex",
    PAPER / "tables" / "r3_appendix_bcc_bridge.tex",
    PAPER / "tables" / "r3_appendix_primitive_ds.tex",
    PAPER / "tables" / "r3_appendix_architecture_pairs.tex",
    PAPER / "tables" / "r3_appendix_webb_support.tex",
    PAPER / "tables" / "r3_appendix_exit_components.tex",
    PAPER / "tables" / "r3_appendix_endpoint_sensitivity.tex",
    R3 / "PATH_REDACTION_RECEIPT.md",
    R3 / "characteristics" / "ANALYSIS_SPEC_AMENDMENT_2_REBUILT_TREATMENT.md",
    R3 / "characteristics" / "SCC_EXECUTION_RECEIPT.md",
    R3 / "characteristics" / "TREATMENT_CONTRACT_CHANGE_AUDIT.json",
    R3 / "characteristics" / "test_characteristic_conditioning.py",
    R3 / "UNRESOLVED_ITEMS.md",
    R3 / "REPRODUCIBILITY.md",
    R3 / "ENVIRONMENT_LOCK.txt",
]:
    if not required_file.is_file() or required_file.stat().st_size == 0:
        raise AssertionError(f"required final artifact missing or empty: {required_file.relative_to(ROOT)}")

for active_appendix_token in [
    "r3_figure3_family_paths.pdf",
    "r3_appendix_lofo.tex",
    "r3_appendix_family_information_precision.tex",
    "r3_appendix_characteristic_estimates.tex",
    "r3_appendix_characteristic_information.tex",
    "r3_appendix_population_eras.tex",
    "r3_appendix_bcc_bridge.tex",
    "r3_appendix_primitive_ds.tex",
    "r3_appendix_architecture_pairs.tex",
    "r3_appendix_webb_support.tex",
    "r3_appendix_exit_components.tex",
    "r3_appendix_endpoint_sensitivity.tex",
]:
    if active_appendix_token not in appendix_text:
        raise AssertionError(f"required artifact is not active in the appendix: {active_appendix_token}")

public_roots = ["paper", str(R3.relative_to(ROOT))]
public_paths = subprocess.check_output(
    ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", *public_roots],
    cwd=ROOT,
    text=True,
).splitlines()
forbidden_absolute_prefixes = tuple(
    prefix.encode()
    for prefix in [
        "/" + "projectnb/",
        "/" + "project/econdept/",
        "/" + "usr3/",
        "/" + "Users/",
    ]
)
path_leaks: list[str] = []
for relpath in public_paths:
    path = ROOT / relpath
    if not path.is_file():
        continue
    payload = path.read_bytes()
    if any(prefix in payload for prefix in forbidden_absolute_prefixes):
        path_leaks.append(relpath)
if path_leaks:
    raise AssertionError("private absolute path prefix survives in public package: " + ",".join(path_leaks))

with OUT_CSV.open("w", newline="") as handle:
    writer = csv.DictWriter(
        handle, fieldnames=list(numeric_checks[0]), lineterminator="\n"
    )
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
    "path_redaction_files_checked": len(public_paths),
    "manuscript_sources_checked": [str(p.relative_to(ROOT)) for p in main_paths + appendix_paths + response_paths],
    "result_files_sha256": {
        str(path.relative_to(ROOT)): sha256(path.read_bytes()).hexdigest()
        for path in sorted(result_files)
    },
}
OUT_JSON.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(json.dumps({"status": receipt["status"], "numeric_checks": len(numeric_checks), "hashed_files": len(result_files)}))
