#!/usr/bin/env python3
"""Independently validate retained Gate 4 ACS aggregate outputs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


REPLICATES = 80
SDR_FACTOR = 4.0 / REPLICATES
NORMAL_975 = 1.959963984540054
YEARS = {2017, 2018, 2019, 2021, 2022, 2023, 2024}
MODEL_YEARS = {
    "full_2017_2019_2021_2023_2024": {2017, 2018, 2019, 2021, 2023, 2024},
    "nonreuse_2017_2021_2023_2024": {2017, 2021, 2023, 2024},
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def close(left: float, right: float, tolerance: float = 2e-11) -> bool:
    return bool(np.isclose(float(left), float(right), atol=tolerance, rtol=tolerance))


def validate(output: Path) -> dict:
    receipt = json.loads((output / "EXECUTION_RECEIPT.json").read_text(encoding="utf-8"))
    manifest = json.loads((output / "ACS_INPUT_MANIFEST.json").read_text(encoding="utf-8"))
    benchmark = pd.read_csv(output / "ACS_BENCHMARK_RESULTS.csv")
    benchmark_paired = pd.read_csv(output / "ACS_BENCHMARK_PAIRED.csv")
    panel = pd.read_csv(output / "ACS_PANEL_RESULTS.csv")
    paired = pd.read_csv(output / "ACS_PANEL_PAIRED.csv")
    reps = pd.read_csv(output / "ACS_SURVEY_REPLICATE_ESTIMATES.csv")
    support = pd.read_csv(output / "ACS_SUPPORT_INFORMATION.csv")
    tails = pd.read_csv(output / "ACS_DIRECT_TAIL_SUPPORT.csv")
    checks: dict[str, bool] = {}
    checks["receipt_status"] = receipt.get("status") == "PASS_PUBLIC_ACS_EXTENSION"
    checks["manifest_status"] = manifest.get("status") == "PASS_PUBLIC_ACS_INPUT_READ"
    checks["calendar"] = set(manifest.get("years", [])) == YEARS and 2020 not in YEARS
    checks["counts"] = (
        len(benchmark) == receipt.get("benchmark_result_count") == 18 and
        len(benchmark_paired) == receipt.get("benchmark_paired_count") == 15 and
        len(panel) == receipt.get("panel_model_count") == 16 and
        len(paired) == receipt.get("paired_result_count") == 8 and
        receipt.get("replicate_count_per_year") == REPLICATES and
        len(reps) == receipt.get("replicate_result_count") == 116 * REPLICATES)
    checks["finite_outputs"] = all(
        np.isfinite(frame.select_dtypes(include=[np.number]).to_numpy(float)).all()
        for frame in (benchmark, benchmark_paired, panel, paired, reps, support, tails))
    checks["output_hashes"] = all(
        (output / name).is_file() and sha256_file(output / name) == digest
        for name, digest in receipt.get("output_hashes", {}).items())
    checks["input_hashes"] = all(
        Path(item["zip_path"]).is_file() and
        sha256_file(Path(item["zip_path"])) == item["zip_sha256"]
        for item in manifest.get("files", []))
    checks["input_years_unique"] = (
        len(manifest.get("files", [])) == 7 and
        {item["year"] for item in manifest.get("files", [])} == YEARS)
    checks["replicate_domain"] = (
        set(pd.to_numeric(reps.replicate, errors="raise").astype(int)) ==
        set(range(1, REPLICATES + 1)) and
        set(pd.to_numeric(reps.perturbed_year, errors="raise").astype(int)).issubset(YEARS))

    benchmark_ok = True
    benchmark_reps = reps.loc[reps.result_type.eq("benchmark")]
    for row in benchmark.itertuples(index=False):
        block = benchmark_reps.loc[
            benchmark_reps.definition.eq(row.definition) &
            benchmark_reps.population.eq(row.population)]
        benchmark_ok &= len(block) == 2 * REPLICATES
        benchmark_ok &= set(block.perturbed_year.astype(int)) == {2022, 2024}
        benchmark_ok &= all(block.groupby("perturbed_year").size().eq(REPLICATES))
        variance = SDR_FACTOR * float(np.square(block.delta.to_numpy(float)).sum())
        se = np.sqrt(max(variance, 0.0))
        benchmark_ok &= close(se, row.ACS_SDR_se)
        benchmark_ok &= close(row.ACS_SDR_ci_lower,
                              row.estimate_Q5_minus_Q1_growth_factor - NORMAL_975 * se)
        benchmark_ok &= close(row.ACS_SDR_ci_upper,
                              row.estimate_Q5_minus_Q1_growth_factor + NORMAL_975 * se)
        benchmark_ok &= np.max(np.abs(
            block.full_weight_estimate.to_numpy(float) -
            row.estimate_Q5_minus_Q1_growth_factor)) <= 2e-11
        benchmark_ok &= np.max(np.abs(
            block.estimate.to_numpy(float) - block.full_weight_estimate.to_numpy(float) -
            block.delta.to_numpy(float))) <= 2e-11
    checks["benchmark_SDR_recomputed"] = bool(benchmark_ok)

    benchmark_pair_ok = True
    for row in benchmark_paired.itertuples(index=False):
        left = benchmark_reps.loc[
            benchmark_reps.definition.eq(row.left_definition) &
            benchmark_reps.population.eq(row.left_population)].sort_values(
                ["perturbed_year", "replicate"])
        right = benchmark_reps.loc[
            benchmark_reps.definition.eq(row.right_definition) &
            benchmark_reps.population.eq(row.right_population)].sort_values(
                ["perturbed_year", "replicate"])
        benchmark_pair_ok &= np.array_equal(
            left[["perturbed_year", "replicate"]].to_numpy(),
            right[["perturbed_year", "replicate"]].to_numpy())
        delta = ((left.estimate.to_numpy(float) - right.estimate.to_numpy(float)) -
                 float(row.estimate_left_minus_right))
        se = np.sqrt(SDR_FACTOR * np.square(delta).sum())
        benchmark_pair_ok &= close(se, row.ACS_paired_SDR_se)
        benchmark_pair_ok &= close(row.ACS_paired_SDR_ci_lower,
                                   row.estimate_left_minus_right - NORMAL_975 * se)
        benchmark_pair_ok &= close(row.ACS_paired_SDR_ci_upper,
                                   row.estimate_left_minus_right + NORMAL_975 * se)
    checks["benchmark_paired_covariance_recomputed"] = bool(benchmark_pair_ok)

    panel_ok = True
    panel_reps = reps.loc[reps.result_type.eq("annual_panel")]
    for row in panel.itertuples(index=False):
        block = panel_reps.loc[
            panel_reps.definition.eq(row.definition) &
            panel_reps.population.eq(row.population) &
            panel_reps.structure.eq(row.structure) &
            panel_reps.calendar_rule.eq(row.calendar_rule)]
        expected_years = MODEL_YEARS[row.calendar_rule]
        panel_ok &= len(block) == REPLICATES * len(expected_years)
        panel_ok &= set(block.perturbed_year.astype(int)) == expected_years
        panel_ok &= all(block.groupby("perturbed_year").size().eq(REPLICATES))
        variance = SDR_FACTOR * float(np.square(block.delta.to_numpy(float)).sum())
        se = np.sqrt(max(variance, 0.0))
        panel_ok &= close(se, row.ACS_block_independent_SDR_se)
        panel_ok &= close(row.ACS_block_independent_SDR_ci_lower,
                          row.coefficient - NORMAL_975 * se)
        panel_ok &= close(row.ACS_block_independent_SDR_ci_upper,
                          row.coefficient + NORMAL_975 * se)
        panel_ok &= np.max(np.abs(
            block.full_weight_estimate.to_numpy(float) - row.coefficient)) <= 2e-11
        panel_ok &= bool(row.transition_2022_excluded)
        panel_ok &= bool(row.zero_2020_standard_one_year_omitted)
    checks["panel_SDR_recomputed"] = bool(panel_ok)

    paired_ok = True
    for row in paired.itertuples(index=False):
        key = (panel_reps.definition.eq(row.definition) &
               panel_reps.population.eq(row.population) &
               panel_reps.calendar_rule.eq(row.calendar_rule))
        left = panel_reps.loc[key & panel_reps.structure.eq("pooled")].sort_values(
            ["perturbed_year", "replicate"])
        right = panel_reps.loc[key & panel_reps.structure.eq("family_year")].sort_values(
            ["perturbed_year", "replicate"])
        paired_ok &= len(left) == len(right) > 0
        paired_ok &= np.array_equal(
            left[["perturbed_year", "replicate"]].to_numpy(),
            right[["perturbed_year", "replicate"]].to_numpy())
        delta = ((left.estimate.to_numpy(float) - right.estimate.to_numpy(float)) -
                 float(row.estimate_left_minus_right))
        se = np.sqrt(SDR_FACTOR * np.square(delta).sum())
        paired_ok &= close(se, row.ACS_paired_block_independent_SDR_se)
        paired_ok &= close(row.ACS_paired_block_independent_SDR_ci_lower,
                           row.estimate_left_minus_right - NORMAL_975 * se)
        paired_ok &= close(row.ACS_paired_block_independent_SDR_ci_upper,
                           row.estimate_left_minus_right + NORMAL_975 * se)
    checks["paired_covariance_recomputed"] = bool(paired_ok)

    checks["support_grid"] = (
        len(support) == 3 * 2 * 7 * 2 * 5 and
        set(support.quintile.astype(int)) == {1, 2, 3, 4, 5} and
        set(support.year.astype(int)) == YEARS)
    checks["tail_grid"] = (
        set(tails.definition) == {
            "BCC_analogue_primary_equal", "YAX_primary_fixed",
            "BCC_analogue_broader_equal"} and
        set(tails.population) == {"all_employed", "full_time_civilian_wage_salary"})
    require(all(checks.values()), "ACS validation failed: " +
            ", ".join(name for name, passed in checks.items() if not passed))
    return {
        "status": "PASS_INDEPENDENT_ACS_OUTPUT_VALIDATION",
        "checks": checks, "check_count": len(checks),
        "receipt_id": receipt["receipt_id"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = validate(args.output_dir)
    report = args.report or args.output_dir / "VALIDATION_REPORT.json"
    report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
