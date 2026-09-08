#!/usr/bin/env python3
"""Validate public aggregate outputs from the B03/B04 SCC benchmark run."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


EXPECTED_FILES = {
    "INDEXED_STOCK_SERIES.csv", "AGGREGATE_BENCHMARKS.csv",
    "LONG_DIFFERENCE_RESULTS.csv", "CONDITIONAL_MODEL_RESULTS.csv",
    "CONDITIONAL_PAIRED_COMPARISONS.csv", "SUPPORT_AND_POPULATION_AUDIT.csv",
    "BENCHMARK_DIFFERENCES.csv", "MODEL_INFLUENCE.csv", "MODEL_FAILURES.json",
    "FINDINGS.md",
}
POPULATIONS = {"all_employed", "full_time_civilian_wage_salary"}
ENDPOINTS = {"annual_mean_2022_to_2024", "November_2022_to_June_2026"}
CONTRASTS = {"Q5_vs_Q1", "top_two_vs_bottom_three"}
WEBB_RULES = {"no_Webb_public_benchmark", "with_Webb_YAX_extension"}
STRUCTURES = {"pooled", "family_post", "family_month"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def aggregate_from_series(series: pd.DataFrame, population: str, endpoint: str,
                          contrast: str) -> tuple[float, float, float]:
    part = series.loc[series.population.eq(population)]
    if endpoint == "annual_mean_2022_to_2024":
        start = part.loc[part.month.str.startswith("2022-")].groupby(
            "exposure_group").weighted_employment_stock.mean()
        end = part.loc[part.month.str.startswith("2024-")].groupby(
            "exposure_group").weighted_employment_stock.mean()
    else:
        start = part.loc[part.month.eq("2022-11")].set_index(
            "exposure_group").weighted_employment_stock
        end = part.loc[part.month.eq("2026-06")].set_index(
            "exposure_group").weighted_employment_stock
    if contrast == "Q5_vs_Q1_growth_factor_difference":
        high = end["Q5"] / start["Q5"]
        low = end["Q1"] / start["Q1"]
        estimate = high - low
    else:
        high = end["top_two"] / start["top_two"]
        low = end["bottom_three"] / start["bottom_three"]
        estimate = high / low - 1.0
    return float(estimate), float(high), float(low)


def validate(run_dir: Path, runner: Path, specification: Path) -> dict[str, Any]:
    receipt_path = run_dir / "EXECUTION_RECEIPT.json"
    require(receipt_path.is_file(), "execution receipt is absent")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    checks: dict[str, Any] = {}

    def check(name: str, condition: bool, detail: Any = None) -> None:
        checks[name] = {"status": "PASS" if condition else "FAIL", "detail": detail}
        require(condition, name)

    check("receipt_status", receipt.get("status") == "PASS_GATE4_PUBLIC_BENCHMARK")
    check("requirements_exact", receipt.get("requirements") == ["B03", "B04"])
    check("output_inventory", set(receipt.get("output_hashes", {})) == EXPECTED_FILES)
    for name in sorted(EXPECTED_FILES):
        path = run_dir / name
        check(f"output_exists::{name}", path.is_file())
        check(f"output_hash::{name}", sha256_file(path) == receipt["output_hashes"][name])
    check("runner_hash", sha256_file(runner) == receipt["input_hashes"]["runner"])
    check("specification_hash",
          sha256_file(specification) == receipt["input_hashes"]["specification"])
    check("calibration_reproduced",
          float(receipt["all_employed_calibration_maximum_relative_gap"]) <= 1e-10,
          receipt["all_employed_calibration_maximum_relative_gap"])
    check("calendar_counts", receipt.get("model_calendar_months") == 113 and
          receipt.get("benchmark_calendar_months") == 114 and
          receipt.get("annual_2022_month_count") == 12)
    check("transition_rules", receipt.get("December_2022_in_annual_benchmark") is True and
          receipt.get("December_2022_in_conditional_models") is False and
          receipt.get("October_2025_treated_as_collection_gap") is True)
    population_rule = receipt.get("population_rule", {})
    check("population_rule", population_rule.get("wage_salary_CLASSWKR_codes") ==
          [20, 21, 22, 23, 24, 25, 27, 28] and
          population_rule.get("armed_forces_code_excluded") == 26 and
          population_rule.get("full_time_rule") == "35 <= UHRSWORKT < 997" and
          population_rule.get("ADP_balanced_firm_or_positive_earnings_match_reproduced")
          is False)
    check("no_person_identifiers", receipt.get("person_or_household_identifiers_read") is False
          and receipt.get("protected_person_rows_written") is False)
    check("membership_not_overclaimed",
          receipt.get("grouping", {}).get("BCC_exact_membership") is False)
    check("class_codes_complete",
          receipt.get("scan_counters", {}).get("unexpected_class_codes") == [])
    check("declared_model_inventory", receipt.get("model_count") == 24 and
          receipt.get("paired_model_comparison_count") == 36 and
          receipt.get("aggregate_row_count") == 12 and
          receipt.get("long_difference_row_count") == 20 and
          receipt.get("model_failure_count") == 0)

    failures = json.loads((run_dir / "MODEL_FAILURES.json").read_text(encoding="utf-8"))
    check("no_model_failures", failures == [])
    series = pd.read_csv(run_dir / "INDEXED_STOCK_SERIES.csv",
                         float_precision="round_trip")
    check("indexed_series_rows", len(series) == 2 * 8 * 114)
    check("indexed_populations", set(series.population) == POPULATIONS)
    check("indexed_groups", set(series.exposure_group) ==
          {"Q1", "Q2", "Q3", "Q4", "Q5", "bottom_three", "top_two", "all_support"})
    check("indexed_calendar", series.month.nunique() == 114 and
          "2022-12" in set(series.month) and "2025-10" not in set(series.month))
    nov = series.loc[series.month.eq("2022-11"), "index_November_2022_equals_1"]
    check("index_normalization", np.allclose(nov, 1.0, rtol=0, atol=1e-14))

    aggregate = pd.read_csv(run_dir / "AGGREGATE_BENCHMARKS.csv",
                            float_precision="round_trip", keep_default_na=False)
    check("aggregate_rows", len(aggregate) == 12)
    max_gap = 0.0
    for population in sorted(POPULATIONS):
        for endpoint in sorted(ENDPOINTS):
            for contrast in ("Q5_vs_Q1_growth_factor_difference",
                             "top_two_vs_bottom_three_kept_pace"):
                observed = aggregate.loc[
                    aggregate.population.eq(population) & aggregate.endpoint.eq(endpoint) &
                    aggregate.contrast.eq(contrast)]
                require(len(observed) == 1, "aggregate result cell is not unique")
                estimate, high, low = aggregate_from_series(
                    series, population, endpoint, contrast)
                max_gap = max(max_gap, abs(float(observed.iloc[0].estimate) - estimate),
                              abs(float(observed.iloc[0].high_growth_factor) - high),
                              abs(float(observed.iloc[0].low_growth_factor) - low))
    check("aggregate_recomputed_from_series", max_gap <= 1e-12, max_gap)
    paired_gap = 0.0
    for endpoint in ENDPOINTS:
        for contrast in ("Q5_vs_Q1_growth_factor_difference",
                         "top_two_vs_bottom_three_kept_pace"):
            aligned = aggregate.loc[
                aggregate.population.eq("full_time_civilian_wage_salary") &
                aggregate.endpoint.eq(endpoint) & aggregate.contrast.eq(contrast)].iloc[0]
            all_workers = aggregate.loc[
                aggregate.population.eq("all_employed") & aggregate.endpoint.eq(endpoint) &
                aggregate.contrast.eq(contrast)].iloc[0]
            difference = aggregate.loc[
                aggregate.population.eq("full_time_civilian_wage_salary_minus_all_employed") &
                aggregate.endpoint.eq(endpoint) & aggregate.contrast.eq(contrast)].iloc[0]
            paired_gap = max(paired_gap, abs(float(difference.estimate) -
                                             (float(aligned.estimate) -
                                              float(all_workers.estimate))))
    check("aggregate_sample_differences_paired", paired_gap <= 1e-14, paired_gap)

    long_difference = pd.read_csv(run_dir / "LONG_DIFFERENCE_RESULTS.csv",
                                  float_precision="round_trip")
    check("long_difference_rows", len(long_difference) == 20)
    check("long_difference_populations", set(long_difference.population) == POPULATIONS)
    check("long_difference_endpoints", set(long_difference.endpoint) == ENDPOINTS)
    check("long_difference_labels", set(long_difference.coefficient_label) ==
          {"intercept_Q1", "Q2_vs_Q1", "Q3_vs_Q1", "Q4_vs_Q1", "Q5_vs_Q1"})
    check("long_difference_no_hidden_controls", set(long_difference.controls) == {"none"})

    models = pd.read_csv(run_dir / "CONDITIONAL_MODEL_RESULTS.csv",
                         float_precision="round_trip", keep_default_na=False)
    check("conditional_model_rows", len(models) == 24 and models.model_id.nunique() == 24)
    inventory = set(zip(models.population, models.contrast, models.Webb_rule, models.structure))
    expected_inventory = {(p, c, w, s) for p in POPULATIONS for c in CONTRASTS
                          for w in WEBB_RULES for s in STRUCTURES}
    check("conditional_inventory_exact", inventory == expected_inventory)
    check("conditional_common_support", models.support_hash_sha256.nunique() == 1 and
          models.support_occupations.nunique() == 1 and
          int(models.support_occupations.iloc[0]) ==
          int(receipt["conditional_common_support_occupations"]))
    no_webb = models.loc[models.Webb_rule.eq("no_Webb_public_benchmark")]
    with_webb = models.loc[models.Webb_rule.eq("with_Webb_YAX_extension")]
    check("Webb_label_separation",
          not no_webb.regressor_labels_json.str.contains("Webb").any() and
          with_webb.regressor_labels_json.str.contains("Webb").all())
    check("conditional_not_called_replication",
          set(models.bridge_status) ==
          {"separate_YAX_young_relative_extension_not_BCC_replication"})

    paired = pd.read_csv(run_dir / "CONDITIONAL_PAIRED_COMPARISONS.csv",
                         float_precision="round_trip")
    check("conditional_paired_rows", len(paired) == 36)
    check("common_draws", paired.common_draws_preserve_covariance.astype(bool).all())
    coefficients = models.set_index("model_id").coefficient.to_dict()
    max_pair_gap = max(abs(float(row.estimate_left_minus_right) -
                           (float(coefficients[row.left_model]) -
                            float(coefficients[row.right_model])))
                       for row in paired.itertuples(index=False))
    check("paired_point_identity", max_pair_gap <= 1e-14, max_pair_gap)
    binary_pairs = paired.loc[
        paired.left_model.str.contains("top_two_vs_bottom_three")]
    check("binary_has_own_paired_inference", len(binary_pairs) == 18 and
          binary_pairs.right_model.str.contains("top_two_vs_bottom_three").all())

    differences = pd.read_csv(run_dir / "BENCHMARK_DIFFERENCES.csv",
                              keep_default_na=False)
    check("differences_table", len(differences) == 7 and
          set(differences.dimension) == {"data_source_and_unit", "age",
          "employment_population", "exposure_membership", "endpoint", "controls",
          "inference"})
    influences = pd.read_csv(run_dir / "MODEL_INFLUENCE.csv",
                             float_precision="round_trip")
    check("influence_model_coverage",
          set(models.model_id).issubset(set(influences.model_id)) and
          set(long_difference.model_id).issubset(set(influences.model_id)))
    check("influence_finite", np.isfinite(influences.target_influence).all())
    findings = (run_dir / "FINDINGS.md").read_text(encoding="utf-8")
    check("findings_scope_language", "not exact BCC occupation memberships" in findings and
          "does not establish equivalence" in findings and
          "does not detect a difference" in findings)

    return {
        "schema_version": "yax-gate4-public-benchmark-validation-v1",
        "status": "PASS_GATE4_PUBLIC_BENCHMARK_VALIDATION",
        "run_dir": str(run_dir), "execution_receipt_sha256": sha256_file(receipt_path),
        "checks": checks, "check_count": len(checks),
        "maximum_aggregate_recomputation_gap": max_gap,
        "maximum_paired_point_identity_gap": max_pair_gap,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--runner", type=Path,
                        default=Path(__file__).with_name("run_public_benchmark.py"))
    parser.add_argument("--specification", type=Path,
                        default=Path(__file__).with_name("PUBLIC_BENCHMARK_SPEC.md"))
    args = parser.parse_args()
    report = validate(args.run_dir, args.runner, args.specification)
    output = args.run_dir / "VALIDATION_REPORT.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": report["check_count"]},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
