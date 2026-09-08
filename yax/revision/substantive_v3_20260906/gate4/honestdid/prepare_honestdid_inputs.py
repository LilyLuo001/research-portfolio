#!/usr/bin/env python3
"""Prepare exact current-contract HonestDiD inputs from certified Gate 2 bytes."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
EXPECTED_RESULT_ID = (
    "yaxresult_v1_b039944581f0da60fb7e8368bff687858b740a7e638c190a8c934369fc10defe"
)
EXPECTED_RUN_ID = "gate2_dynamic_core_sge_7489898"
EXPECTED_RECEIPT_STATUS = "CERTIFIED_DYNAMIC_CORE_Y01_Y05_PUBLICATION"
EXPECTED_MANIFEST_SHA256 = (
    "63e268d9f25038b86e37ff503cc3438481e7e7d8a439172b65a90c44bbaaf507"
)
EXPECTED_RECEIPT_SHA256 = (
    "f3b803c514993412f41152598a722386dc8a340bb322e7054e6fc1f64f132d56"
)
EXPECTED_DYNAMIC_SPEC_SHA256 = (
    "8d530008dbccb32aa99ba26ef35128283840f700aa0cd80600ba352ac5e975eb"
)
OFFICIAL_HONESTDID_COMMIT = "6813f02ed38f0b63bdca6915604b2eac90491303"
SMOOTH_GRID = (0.0, 0.005, 0.01, 0.02, 0.03, 0.04, 0.05)
RELATIVE_GRID = (0.0, 0.5, 1.0, 1.5, 2.0)
WINDOWS = {
    "full_2017Q1_2022Q3": ("2017Q1", "2022Q3", 23),
    "recent_2021Q1_2022Q3": ("2021Q1", "2022Q3", 7),
}
STRUCTURES = ("unconditioned", "family_month")
REFERENCE = "2022Q4"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    require(bool(rows), f"refusing to write empty {path.name}")
    fields: list[str] = []
    for row in rows:
        fields.extend(field for field in row if field not in fields)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def quarter_number(label: str) -> int:
    require(len(label) == 6 and label[4] == "Q", f"invalid quarter {label}")
    year = int(label[:4])
    quarter = int(label[5])
    require(1 <= quarter <= 4, f"invalid quarter {label}")
    return 4 * year + quarter - 1


def quarters_between(start: str, end: str) -> list[str]:
    first, last = quarter_number(start), quarter_number(end)
    require(first <= last, "quarter window is reversed")
    return [f"{number // 4}Q{number % 4 + 1}" for number in range(first, last + 1)]


def smoothness_matrix(num_pre: int, num_post: int) -> np.ndarray:
    """Exact `.create_A_SD(..., postPeriodMomentsOnly=FALSE)` construction."""
    free = num_pre + num_post
    full = np.zeros((free - 1, free + 1), dtype=float)
    for row in range(free - 1):
        full[row, row:row + 3] = (1.0, -2.0, 1.0)
    positive = np.delete(full, num_pre, axis=1)
    return np.vstack((positive, -positive))


def relative_matrix(num_pre: int, num_post: int, mbar: float,
                    s: int, max_positive: bool) -> np.ndarray:
    """Exact `.create_A_RM(..., dropZero=TRUE)` construction."""
    require(-(num_pre - 1) <= s <= 0, "relative-magnitude s is outside preperiod")
    free = num_pre + num_post
    difference = np.zeros((free, free + 1), dtype=float)
    for row in range(free):
        difference[row, row:row + 2] = (-1.0, 1.0)
    selected = np.zeros(free + 1, dtype=float)
    first = num_pre + s - 1
    selected[first:first + 2] = (-1.0, 1.0)
    if not max_positive:
        selected *= -1.0
    upper = np.vstack((
        np.tile(selected, (num_pre, 1)),
        np.tile(float(mbar) * selected, (num_post, 1)),
    ))
    constrained = np.vstack((difference - upper, -difference - upper))
    constrained = constrained[np.sum(constrained * constrained, axis=1) > 1e-10]
    return np.delete(constrained, num_pre, axis=1)


def sparse_rows(matrix: np.ndarray, analysis_id: str, matrix_id: str,
                coefficient_labels: list[str], family: str,
                **parameters: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for matrix_row in range(matrix.shape[0]):
        for column in np.flatnonzero(matrix[matrix_row] != 0.0):
            rows.append({
                "analysis_id": analysis_id,
                "restriction_family": family,
                "matrix_id": matrix_id,
                **parameters,
                "matrix_row": matrix_row + 1,
                "coefficient_index": int(column) + 1,
                "coefficient_quarter": coefficient_labels[int(column)],
                "value": float(matrix[matrix_row, column]),
                "rhs": 0.0,
            })
    return rows


def authenticate_dynamic(dynamic_dir: Path, dynamic_spec: Path) -> dict[str, Any]:
    manifest_path = dynamic_dir / "RESULT_MANIFEST.json"
    receipt_path = dynamic_dir / "EXECUTION_RECEIPT.json"
    require(sha256_file(manifest_path) == EXPECTED_MANIFEST_SHA256,
            "authoritative dynamic result manifest hash differs")
    require(sha256_file(receipt_path) == EXPECTED_RECEIPT_SHA256,
            "authoritative dynamic receipt hash differs")
    require(sha256_file(dynamic_spec) == EXPECTED_DYNAMIC_SPEC_SHA256,
            "dynamic parent specification hash differs")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(manifest["result_id"] == receipt["result_id"] == EXPECTED_RESULT_ID,
            "authoritative dynamic result ID differs")
    require(manifest["run_id"] == receipt["run_id"] == EXPECTED_RUN_ID,
            "authoritative dynamic run ID differs")
    require(receipt["status"] == EXPECTED_RECEIPT_STATUS,
            "authoritative dynamic receipt is not certified")
    required = {"DYNAMIC_Q5_EVENT_STUDY.csv", "DYNAMIC_COVARIANCE.csv",
                "RECONCILIATION_ESTIMATES.csv"}
    artifact_hashes = {row["filename"]: row["sha256"] for row in manifest["artifacts"]}
    require(required.issubset(artifact_hashes), "dynamic result manifest omits a required file")
    for filename in required:
        require(sha256_file(dynamic_dir / filename) == artifact_hashes[filename],
                f"dynamic artifact hash differs for {filename}")
    return {
        "manifest": manifest,
        "receipt": receipt,
        "artifact_hashes": artifact_hashes,
        "dynamic_spec": json.loads(dynamic_spec.read_text(encoding="utf-8")),
    }


def covariance_matrix(covariance: pd.DataFrame, structure: str,
                      quarters: list[str]) -> np.ndarray:
    labels = [f"Q5_x_{quarter}" for quarter in quarters]
    selected = covariance.loc[
        covariance.structure.eq(structure)
        & covariance.row_label.isin(labels)
        & covariance.column_label.isin(labels)
    ]
    require(len(selected) == len(labels) ** 2,
            f"incomplete Q5 covariance for {structure}")
    require(not selected.duplicated(["row_label", "column_label"]).any(),
            f"duplicate Q5 covariance entries for {structure}")
    matrix = selected.pivot(index="row_label", columns="column_label", values="value")
    matrix = matrix.loc[labels, labels].to_numpy(float)
    require(np.all(np.isfinite(matrix)), "event covariance is nonfinite")
    require(np.max(np.abs(matrix - matrix.T)) <= 1e-12,
            "event covariance is asymmetric")
    eigenvalues = np.linalg.eigvalsh(matrix)
    require(eigenvalues[0] >= -1e-12 * max(1.0, eigenvalues[-1]),
            "event covariance is not positive semidefinite")
    return matrix


def prepare(dynamic_dir: Path, dynamic_spec: Path, output_dir: Path) -> None:
    require(not output_dir.exists() or not any(output_dir.iterdir()),
            "output directory must be absent or empty")
    output_dir.mkdir(parents=True, exist_ok=True)
    authenticated = authenticate_dynamic(dynamic_dir, dynamic_spec)
    spec = authenticated["dynamic_spec"]
    post_weights = spec["functionals"]["post_quarter_weights"]
    post_quarters = quarters_between("2023Q1", "2026Q3")
    require(list(post_weights) == post_quarters, "post-weight quarter order differs")
    l_vec = np.asarray([post_weights[label] for label in post_quarters], float)
    require(np.all(l_vec >= 0) and abs(float(l_vec.sum()) - 1.0) <= 1e-15,
            "post-only functional weights are invalid")

    event = pd.read_csv(dynamic_dir / "DYNAMIC_Q5_EVENT_STUDY.csv",
                        float_precision="round_trip")
    covariance = pd.read_csv(dynamic_dir / "DYNAMIC_COVARIANCE.csv",
                             float_precision="round_trip")
    reconciliation = pd.read_csv(dynamic_dir / "RECONCILIATION_ESTIMATES.csv",
                                 float_precision="round_trip")
    require(set(event.structure) == set(STRUCTURES), "event-study structures differ")
    reference_rows = event.loc[event.reference_quarter.astype(str).str.lower().eq("true")]
    require(len(reference_rows) == 2 and set(reference_rows.quarter) == {REFERENCE},
            "event-study reference rows differ")
    require(np.max(np.abs(reference_rows.estimate.to_numpy(float))) == 0,
            "reference coefficients are not exactly zero")

    analysis_rows: list[dict[str, Any]] = []
    vector_rows: list[dict[str, Any]] = []
    covariance_rows: list[dict[str, Any]] = []
    functional_rows: list[dict[str, Any]] = []
    grid_rows: list[dict[str, Any]] = []
    smooth_rows: list[dict[str, Any]] = []
    relative_rows: list[dict[str, Any]] = []
    matrix_catalog: list[dict[str, Any]] = []

    for structure in STRUCTURES:
        structure_event = event.loc[event.structure.eq(structure)].set_index("quarter")
        require(not structure_event.index.duplicated().any(), "duplicate event quarter")
        model_id = str(structure_event.model_id.iloc[0])
        expected_p = reconciliation.loc[
            reconciliation.target.eq(f"{structure}::P")].iloc[0]
        for window, (start, end, expected_pre) in WINDOWS.items():
            pre_quarters = quarters_between(start, end)
            require(len(pre_quarters) == expected_pre, "prewindow size differs")
            require(quarter_number(pre_quarters[-1]) + 1 == quarter_number(REFERENCE),
                    "prewindow is not contiguous with the reference")
            require(quarter_number(REFERENCE) + 1 == quarter_number(post_quarters[0]),
                    "postwindow is not contiguous with the reference")
            labels = pre_quarters + post_quarters
            require(set(labels).issubset(structure_event.index),
                    "event-study vector omits a requested quarter")
            beta = structure_event.loc[labels, "estimate"].to_numpy(float)
            sigma = covariance_matrix(covariance, structure, labels)
            npre, npost = len(pre_quarters), len(post_quarters)
            analysis_id = f"{structure}__{window}"
            estimate = float(l_vec @ beta[npre:])
            variance = float(l_vec @ sigma[npre:, npre:] @ l_vec)
            require(variance > 0 and math.isfinite(variance), "functional variance invalid")
            standard_error = math.sqrt(variance)
            require(abs(estimate - float(expected_p.estimate)) <= 1e-12,
                    "post functional does not reproduce Gate 2 P estimate")
            require(abs(standard_error - float(expected_p.standard_error)) <= 1e-12,
                    "post functional does not reproduce Gate 2 P standard error")

            for index, quarter in enumerate(labels):
                is_post = index >= npre
                vector_rows.append({
                    "analysis_id": analysis_id, "structure": structure,
                    "model_id": model_id, "calibration_window": window,
                    "coefficient_index": index + 1, "quarter": quarter,
                    "reference_quarter": REFERENCE,
                    "role": "post" if is_post else "pre",
                    "estimate": float(beta[index]),
                    "l_vec_post_functional_weight": (
                        float(l_vec[index - npre]) if is_post else 0.0),
                })
            for row in range(len(labels)):
                for column in range(len(labels)):
                    covariance_rows.append({
                        "analysis_id": analysis_id,
                        "row_index": row + 1, "column_index": column + 1,
                        "row_quarter": labels[row], "column_quarter": labels[column],
                        "covariance": float(sigma[row, column]),
                    })
            functional_rows.append({
                "analysis_id": analysis_id, "structure": structure,
                "calibration_window": window, "target": "dynamic_P",
                "estimate": estimate, "standard_error": standard_error,
                "normal_ci_lower": estimate - 1.959963984540054 * standard_error,
                "normal_ci_upper": estimate + 1.959963984540054 * standard_error,
                "post_weight_sum": float(l_vec.sum()),
                "minimum_post_weight": float(l_vec.min()),
                "maximum_post_weight": float(l_vec.max()),
                "gate2_P_estimate_difference": estimate - float(expected_p.estimate),
                "gate2_P_se_difference": standard_error - float(expected_p.standard_error),
            })

            full_labels = pre_quarters + [REFERENCE] + post_quarters
            coefficient_labels = pre_quarters + post_quarters
            smooth = smoothness_matrix(npre, npost)
            smooth_id = f"smoothness__{analysis_id}"
            smooth_rows.extend(sparse_rows(
                smooth, analysis_id, smooth_id, coefficient_labels, "DeltaSD"))
            matrix_catalog.append({
                "analysis_id": analysis_id, "restriction_family": "DeltaSD",
                "matrix_id": smooth_id, "Mbar": "", "s": "",
                "max_positive": "", "rows": smooth.shape[0],
                "columns": smooth.shape[1], "rhs_rule": "all entries equal M",
                "full_bias_order_including_reference": "|".join(full_labels),
                "free_coefficient_order": "|".join(coefficient_labels),
            })
            for value in SMOOTH_GRID:
                grid_rows.append({
                    "analysis_id": analysis_id, "restriction_family": "DeltaSD",
                    "parameter_name": "M", "parameter_value": value,
                    "units": "log points per quarter squared", "method": "FLCI",
                    "alpha": 0.05, "seed": 2026090529, "grid_points": "",
                })

            for mbar in RELATIVE_GRID:
                grid_rows.append({
                    "analysis_id": analysis_id, "restriction_family": "DeltaRM",
                    "parameter_name": "Mbar", "parameter_value": mbar,
                    "units": "ratio of consecutive-quarter bias changes",
                    "method": "C-LF", "alpha": 0.05, "seed": 2026090529,
                    "grid_points": 1000,
                })
                for s in range(-(npre - 1), 1):
                    for max_positive in (True, False):
                        sign = "positive" if max_positive else "negative"
                        matrix = relative_matrix(npre, npost, mbar, s, max_positive)
                        matrix_id = f"relative__{analysis_id}__Mbar_{mbar:g}__s_{s}__{sign}"
                        relative_rows.extend(sparse_rows(
                            matrix, analysis_id, matrix_id, coefficient_labels,
                            "DeltaRM", Mbar=mbar, s=s,
                            max_positive=str(max_positive).lower()))
                        matrix_catalog.append({
                            "analysis_id": analysis_id,
                            "restriction_family": "DeltaRM", "matrix_id": matrix_id,
                            "Mbar": mbar, "s": s,
                            "max_positive": str(max_positive).lower(),
                            "rows": matrix.shape[0], "columns": matrix.shape[1],
                            "rhs_rule": "all entries equal zero",
                            "full_bias_order_including_reference": "|".join(full_labels),
                            "free_coefficient_order": "|".join(coefficient_labels),
                        })

            analysis_rows.append({
                "analysis_id": analysis_id, "structure": structure,
                "model_id": model_id, "calibration_window": window,
                "pre_start": start, "pre_end": end, "pre_periods": npre,
                "reference_quarter": REFERENCE, "post_start": post_quarters[0],
                "post_end": post_quarters[-1], "post_periods": npost,
                "coefficient_count": len(labels),
                "target": "dynamic_P_equal_observed_post_month",
                "event_vector_file": "EVENT_VECTORS.csv",
                "covariance_file": "EVENT_COVARIANCES.csv",
                "smoothness_matrix_file": "SMOOTHNESS_CONSTRAINT_MATRIX.csv",
                "relative_matrix_file": "RELATIVE_CONSTRAINT_MATRICES.csv",
            })

    files_and_rows = {
        "ANALYSIS_MANIFEST.csv": analysis_rows,
        "EVENT_VECTORS.csv": vector_rows,
        "EVENT_COVARIANCES.csv": covariance_rows,
        "CONVENTIONAL_FUNCTIONALS.csv": functional_rows,
        "SENSITIVITY_GRID.csv": grid_rows,
        "CONSTRAINT_MATRIX_CATALOG.csv": matrix_catalog,
        "SMOOTHNESS_CONSTRAINT_MATRIX.csv": smooth_rows,
        "RELATIVE_CONSTRAINT_MATRICES.csv": relative_rows,
    }
    for filename, rows in files_and_rows.items():
        write_csv(output_dir / filename, rows)

    output_hashes = {name: sha256_file(output_dir / name) for name in files_and_rows}
    receipt = {
        "schema_version": "yax-gate4-honestdid-preparation-receipt-v1",
        "status": "PASS_CURRENT_CONTRACT_HONESTDID_INPUT_PREPARATION",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "official_package": {
            "name": "HonestDiD", "version": "0.2.8",
            "source_commit": OFFICIAL_HONESTDID_COMMIT,
            "paper": "Rambachan and Roth (Review of Economic Studies, 2023)",
        },
        "source": {
            "dynamic_result_id": EXPECTED_RESULT_ID,
            "dynamic_run_id": EXPECTED_RUN_ID,
            "dynamic_manifest_sha256": EXPECTED_MANIFEST_SHA256,
            "dynamic_receipt_sha256": EXPECTED_RECEIPT_SHA256,
            "dynamic_spec_sha256": EXPECTED_DYNAMIC_SPEC_SHA256,
            "consumed_artifact_hashes": {
                name: authenticated["artifact_hashes"][name]
                for name in ("DYNAMIC_Q5_EVENT_STUDY.csv", "DYNAMIC_COVARIANCE.csv",
                             "RECONCILIATION_ESTIMATES.csv")
            },
        },
        "analysis_count": len(analysis_rows),
        "structures": list(STRUCTURES),
        "calibration_windows": list(WINDOWS),
        "target": "dynamic P; equal-observed-post-month average",
        "post_only_l_vec": True,
        "all_post_weights_nonnegative": True,
        "post_weight_sum": float(l_vec.sum()),
        "static_target_not_substituted": True,
        "gapped_calendar_not_compressed": True,
        "smoothness_definition": "absolute adjacent-quarter second differences <= M",
        "relative_definition": (
            "union over every signed maximal pre consecutive-quarter change; "
            "post consecutive changes <= Mbar times that magnitude"
        ),
        "output_hashes": output_hashes,
    }
    write_json(output_dir / "PREPARATION_RECEIPT.json", receipt)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dynamic-dir", type=Path, required=True)
    parser.add_argument("--dynamic-spec", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    prepare(arguments.dynamic_dir, arguments.dynamic_spec, arguments.output_dir)
