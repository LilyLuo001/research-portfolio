#!/usr/bin/env python3
"""Recompute and validate current-contract official HonestDiD outputs."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent


def load_preparer():
    spec = importlib.util.spec_from_file_location(
        "yax_current_honestdid_preparer", HERE / "prepare_honestdid_inputs.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import HonestDiD preparer")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PREP = load_preparer()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    require(bool(rows), f"refusing to write empty {path.name}")
    fields: list[str] = []
    for row in rows:
        fields.extend(field for field in row if field not in fields)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sparse_matrix(frame: pd.DataFrame, matrix_id: str,
                  rows: int, columns: int) -> np.ndarray:
    selected = frame.loc[frame.matrix_id.eq(matrix_id)]
    require(len(selected) > 0, f"empty sparse matrix {matrix_id}")
    require(not selected.duplicated(["matrix_row", "coefficient_index"]).any(),
            f"duplicate sparse cell in {matrix_id}")
    matrix = np.zeros((rows, columns), dtype=float)
    row = selected.matrix_row.to_numpy(int) - 1
    column = selected.coefficient_index.to_numpy(int) - 1
    require(np.all((0 <= row) & (row < rows) & (0 <= column) & (column < columns)),
            f"sparse index out of bounds in {matrix_id}")
    matrix[row, column] = selected.value.to_numpy(float)
    return matrix


def reconstruct_smooth(num_pre: int, num_post: int) -> np.ndarray:
    """Independent signed second-difference construction with inserted reference."""
    full_columns = num_pre + 1 + num_post
    rows = []
    for start in range(full_columns - 2):
        row = np.zeros(full_columns)
        row[start], row[start + 1], row[start + 2] = 1.0, -2.0, 1.0
        rows.append(np.delete(row, num_pre))
    positive = np.asarray(rows)
    return np.concatenate([positive, -positive], axis=0)


def reconstruct_relative(num_pre: int, num_post: int, mbar: float,
                         s: int, max_positive: bool) -> np.ndarray:
    """Independent signed first-difference restriction construction."""
    full_columns = num_pre + 1 + num_post
    selected = np.zeros(full_columns)
    left = num_pre + s - 1
    selected[left:left + 2] = (-1.0, 1.0)
    if not max_positive:
        selected = -selected
    rows = []
    for direction in (1.0, -1.0):
        for transition in range(full_columns - 1):
            first_difference = np.zeros(full_columns)
            first_difference[transition:transition + 2] = (-direction, direction)
            scale = 1.0 if transition < num_pre else float(mbar)
            row = first_difference - scale * selected
            if float(row @ row) > 1e-10:
                rows.append(np.delete(row, num_pre))
    return np.asarray(rows)


def validate(output_dir: Path) -> dict[str, Any]:
    preparation = json.loads((output_dir / "PREPARATION_RECEIPT.json").read_text())
    require(preparation["status"] ==
            "PASS_CURRENT_CONTRACT_HONESTDID_INPUT_PREPARATION",
            "input preparation did not pass")
    for filename, expected in preparation["output_hashes"].items():
        require(sha256_file(output_dir / filename) == expected,
                f"prepared input hash differs for {filename}")
    official = json.loads((output_dir / "OFFICIAL_EXECUTION_RECEIPT.json").read_text())
    require(official["status"] ==
            "PASS_OFFICIAL_CURRENT_CONTRACT_HONESTDID_EXECUTION",
            "official execution did not pass")
    require(official["official_package"]["source_commit"] ==
            PREP.OFFICIAL_HONESTDID_COMMIT,
            "official HonestDiD source commit differs")
    require(bool(official["matrix_parity"]["all_pass"]),
            "R-stage official constraint parity did not pass")
    for filename, expected in official["output_hashes"].items():
        require(sha256_file(output_dir / filename) == expected,
                f"official output hash differs for {filename}")

    manifest = pd.read_csv(output_dir / "ANALYSIS_MANIFEST.csv")
    vectors = pd.read_csv(output_dir / "EVENT_VECTORS.csv",
                          float_precision="round_trip")
    covariance = pd.read_csv(output_dir / "EVENT_COVARIANCES.csv",
                             float_precision="round_trip")
    functionals = pd.read_csv(output_dir / "CONVENTIONAL_FUNCTIONALS.csv",
                              float_precision="round_trip")
    grid = pd.read_csv(output_dir / "SENSITIVITY_GRID.csv")
    catalog = pd.read_csv(output_dir / "CONSTRAINT_MATRIX_CATALOG.csv",
                          keep_default_na=False)
    smooth_sparse = pd.read_csv(output_dir / "SMOOTHNESS_CONSTRAINT_MATRIX.csv",
                                float_precision="round_trip")
    relative_sparse = pd.read_csv(output_dir / "RELATIVE_CONSTRAINT_MATRICES.csv",
                                  float_precision="round_trip")
    original = pd.read_csv(output_dir / "OFFICIAL_ORIGINAL_RESULTS.csv",
                           float_precision="round_trip")
    smooth = pd.read_csv(output_dir / "OFFICIAL_SMOOTHNESS_RESULTS.csv",
                         float_precision="round_trip")
    relative = pd.read_csv(output_dir / "OFFICIAL_RELATIVE_MAGNITUDE_RESULTS.csv",
                           float_precision="round_trip")
    execution = pd.read_csv(output_dir / "OFFICIAL_EXECUTION_LOG.csv")
    parity = pd.read_csv(output_dir / "OFFICIAL_MATRIX_PARITY.csv")

    require(len(manifest) == 4 and manifest.analysis_id.nunique() == 4,
            "analysis inventory differs")
    require(set(manifest.structure) == set(PREP.STRUCTURES), "structure inventory differs")
    require(set(manifest.calibration_window) == set(PREP.WINDOWS),
            "calibration-window inventory differs")
    require(len(original) == 4 and len(smooth) == 4 * len(PREP.SMOOTH_GRID)
            and len(relative) == 4 * len(PREP.RELATIVE_GRID),
            "official result-grid inventory differs")
    require(len(execution) == 12 and set(execution.call_status) ==
            {"RETURNED_FINITE_OFFICIAL_RESULT"}, "official execution log differs")
    require(len(parity) == 8 and set(parity.status) == {"PASS_OFFICIAL_MATRIX_PARITY"},
            "official matrix-parity inventory differs")
    require(float(parity.maximum_absolute_difference.max()) <= 1e-12,
            "official matrix-parity tolerance exceeded")

    summary: list[dict[str, Any]] = []
    maximum_covariance_asymmetry = 0.0
    minimum_covariance_eigenvalue = math.inf
    maximum_matrix_difference = 0.0
    for info in manifest.itertuples(index=False):
        analysis_id = info.analysis_id
        vector = vectors.loc[vectors.analysis_id.eq(analysis_id)].sort_values(
            "coefficient_index")
        require(len(vector) == info.coefficient_count,
                f"event-vector inventory differs for {analysis_id}")
        require(vector.quarter.tolist() ==
                PREP.quarters_between(info.pre_start, info.pre_end) +
                PREP.quarters_between(info.post_start, info.post_end),
                f"calendar is gapped or reordered for {analysis_id}")
        require(vector.role.tolist() == ["pre"] * info.pre_periods +
                ["post"] * info.post_periods, f"event roles differ for {analysis_id}")
        require(PREP.quarter_number(info.pre_end) + 1 ==
                PREP.quarter_number(info.reference_quarter),
                f"prewindow is not contiguous with reference for {analysis_id}")
        require(PREP.quarter_number(info.reference_quarter) + 1 ==
                PREP.quarter_number(info.post_start),
                f"postwindow is not contiguous with reference for {analysis_id}")
        cov = covariance.loc[covariance.analysis_id.eq(analysis_id)]
        require(len(cov) == info.coefficient_count ** 2,
                f"covariance inventory differs for {analysis_id}")
        matrix = np.full((info.coefficient_count, info.coefficient_count), np.nan)
        matrix[cov.row_index.to_numpy(int) - 1,
               cov.column_index.to_numpy(int) - 1] = cov.covariance.to_numpy(float)
        asymmetry = float(np.max(np.abs(matrix - matrix.T)))
        eigenvalue = float(np.linalg.eigvalsh(matrix)[0])
        maximum_covariance_asymmetry = max(maximum_covariance_asymmetry, asymmetry)
        minimum_covariance_eigenvalue = min(minimum_covariance_eigenvalue, eigenvalue)
        require(asymmetry <= 1e-12 and eigenvalue >= -1e-12,
                f"covariance invalid for {analysis_id}")
        l_vec = vector.l_vec_post_functional_weight.iloc[info.pre_periods:].to_numpy(float)
        require(np.all(l_vec >= 0) and abs(float(l_vec.sum()) - 1) <= 1e-12,
                f"post l_vec invalid for {analysis_id}")
        require(np.max(np.abs(vector.l_vec_post_functional_weight.iloc[
            :info.pre_periods].to_numpy(float))) == 0,
            f"pre weight was passed to l_vec for {analysis_id}")
        beta = vector.estimate.to_numpy(float)
        estimate = float(l_vec @ beta[info.pre_periods:])
        se = math.sqrt(float(l_vec @ matrix[info.pre_periods:, info.pre_periods:] @ l_vec))
        stored = functionals.loc[functionals.analysis_id.eq(analysis_id)].iloc[0]
        require(abs(estimate - stored.estimate) <= 1e-12 and
                abs(se - stored.standard_error) <= 1e-12,
                f"conventional functional does not reproduce for {analysis_id}")
        official_original = original.loc[original.analysis_id.eq(analysis_id)].iloc[0]
        expected_lower = estimate - 1.959963984540054 * se
        expected_upper = estimate + 1.959963984540054 * se
        require(abs(official_original.lb - expected_lower) <= 1e-10 and
                abs(official_original.ub - expected_upper) <= 1e-10,
                f"official conventional interval differs for {analysis_id}")

        smooth_values = smooth.loc[smooth.analysis_id.eq(analysis_id)]
        relative_values = relative.loc[relative.analysis_id.eq(analysis_id)]
        require(np.allclose(sorted(smooth_values.M.to_numpy(float)), PREP.SMOOTH_GRID,
                            atol=0, rtol=0), f"smoothness grid differs for {analysis_id}")
        relative_parameter = "Mbar" if "Mbar" in relative_values else "M"
        require(np.allclose(sorted(relative_values[relative_parameter].to_numpy(float)),
                            PREP.RELATIVE_GRID, atol=0, rtol=0),
                f"relative grid differs for {analysis_id}")

        smooth_info = catalog.loc[(catalog.analysis_id == analysis_id) &
                                  (catalog.restriction_family == "DeltaSD")].iloc[0]
        prepared_smooth = sparse_matrix(
            smooth_sparse, smooth_info.matrix_id, int(smooth_info.rows),
            int(smooth_info.columns))
        smooth_difference = float(np.max(np.abs(
            prepared_smooth - reconstruct_smooth(info.pre_periods, info.post_periods))))
        maximum_matrix_difference = max(maximum_matrix_difference, smooth_difference)
        require(smooth_difference <= 1e-12,
                f"smoothness matrix reconstruction differs for {analysis_id}")
        relative_info = catalog.loc[(catalog.analysis_id == analysis_id) &
                                    (catalog.restriction_family == "DeltaRM")]
        require(len(relative_info) == len(PREP.RELATIVE_GRID) * info.pre_periods * 2,
                f"relative matrix inventory differs for {analysis_id}")
        for matrix_info in relative_info.itertuples(index=False):
            prepared_relative = sparse_matrix(
                relative_sparse, matrix_info.matrix_id, int(matrix_info.rows),
                int(matrix_info.columns))
            expected_relative = reconstruct_relative(
                info.pre_periods, info.post_periods, float(matrix_info.Mbar),
                int(matrix_info.s), str(matrix_info.max_positive).lower() == "true")
            difference = float(np.max(np.abs(prepared_relative - expected_relative)))
            maximum_matrix_difference = max(maximum_matrix_difference, difference)
            require(difference <= 1e-12,
                    f"relative matrix reconstruction differs for {matrix_info.matrix_id}")

        conventional_includes_zero = bool(official_original.lb <= 0 <= official_original.ub)
        smooth_crossings = smooth_values.loc[(smooth_values.lb <= 0) & (smooth_values.ub >= 0)]
        relative_crossings = relative_values.loc[
            (relative_values.lb <= 0) & (relative_values.ub >= 0)]
        summary.append({
            "analysis_id": analysis_id, "structure": info.structure,
            "calibration_window": info.calibration_window,
            "target": "dynamic_P_equal_observed_post_month",
            "estimate": estimate, "standard_error": se,
            "conventional_ci_lower": float(official_original.lb),
            "conventional_ci_upper": float(official_original.ub),
            "conventional_interval_includes_zero": conventional_includes_zero,
            "positive_zero_exclusion_breakdown_defined": not conventional_includes_zero,
            "first_declared_smoothness_grid_point_including_zero": (
                float(smooth_crossings.M.min()) if len(smooth_crossings) else ""),
            "first_declared_relative_grid_point_including_zero": (
                float(relative_crossings[relative_parameter].min())
                if len(relative_crossings) else ""),
            "breakdown_interpretation": (
                "zero: conventional interval already includes zero for dynamic P"
                if conventional_includes_zero else
                "coarse first declared-grid crossing; not interpolated threshold"),
        })

    require(set(grid.loc[grid.restriction_family.eq("DeltaSD"), "method"]) == {"FLCI"},
            "smoothness method differs")
    require(set(grid.loc[grid.restriction_family.eq("DeltaRM"), "method"]) == {"C-LF"},
            "relative-magnitude method differs")
    require(set(grid.loc[grid.restriction_family.eq("DeltaRM"), "grid_points"]) == {1000.0},
            "relative test-inversion grid differs")
    write_csv(output_dir / "HONESTDID_SUMMARY.csv", summary)
    findings = [
        "# Current-contract HonestDiD findings\n",
        "These results apply only to the dynamic `P` functional: the equal-observed-post-month average of quarterly Q5-versus-Q1 coefficients relative to 2022Q4. They are not intervals for the nonlinear static coefficient.\n",
        "## Results\n",
    ]
    for row in summary:
        findings.append(
            f"- `{row['structure']}`, `{row['calibration_window']}`: "
            f"estimate {row['estimate']:.6f}, conventional 95% interval "
            f"[{row['conventional_ci_lower']:.6f}, {row['conventional_ci_upper']:.6f}]. "
            f"{row['breakdown_interpretation']}.\n")
    findings.extend([
        "\n## Interpretation limits\n",
        "The full and recent windows are both reported. The recent calibration uses consecutive 2021Q1--2022Q3 quarters; no pandemic quarter was deleted from inside a retained sequence and no calendar gap was compressed. Smoothness constrains adjacent-quarter second differences, while relative magnitude constrains consecutive-quarter changes and unions over all signed maximal pre changes.\n",
        "The official high-level package functions returned finite intervals, but do not expose every underlying optimizer status. The retained execution log therefore records returned results and warnings without claiming an unavailable per-optimization certificate.\n",
    ])
    (output_dir / "FINDINGS.md").write_text("\n".join(findings), encoding="utf-8")

    report = {
        "schema_version": "yax-gate4-honestdid-validation-v1",
        "status": "PASS_RECOMPUTED_CURRENT_CONTRACT_HONESTDID",
        "validated_utc": datetime.now(timezone.utc).isoformat(),
        "analysis_count": len(summary),
        "official_result_rows": {
            "original": len(original), "smoothness": len(smooth),
            "relative_magnitude": len(relative),
        },
        "checks": {
            "authoritative_dynamic_inputs_authenticated": True,
            "post_only_nonnegative_l_vec": True,
            "dynamic_P_reproduced": True,
            "full_covariance_used": True,
            "both_structures_present": True,
            "full_and_contiguous_recent_windows_present": True,
            "no_calendar_gap_compressed": True,
            "smoothness_second_difference_definition_recomputed": True,
            "relative_consecutive_change_definition_recomputed": True,
            "official_package_matrix_parity_passed": True,
            "official_result_grids_complete": True,
            "static_target_not_substituted": True,
        },
        "diagnostics": {
            "maximum_covariance_asymmetry": maximum_covariance_asymmetry,
            "minimum_covariance_eigenvalue": minimum_covariance_eigenvalue,
            "maximum_independent_matrix_reconstruction_difference":
                maximum_matrix_difference,
        },
        "output_hashes": {
            filename: sha256_file(output_dir / filename)
            for filename in ("HONESTDID_SUMMARY.csv", "FINDINGS.md")
        },
    }
    write_json(output_dir / "VALIDATION_REPORT.json", report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    print(json.dumps(validate(arguments.output_dir), indent=2, sort_keys=True))

