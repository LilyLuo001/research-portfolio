#!/usr/bin/env python3
"""Build public aggregate diagnostics for the frozen LinkUp L1 sample design.

The private formal-sample file contains record keys, but this script exports only
aggregate counts and weight diagnostics. It does not read job text, evaluate any
semantic fields, trim weights, cap weights, or draw a new sample.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


VERSION = "linkup_l1_design_diagnostics_v2"
CELL_KEYS = ["OCCUPATION_MAJOR", "CENSUS_REGION", "created_year"]
PRIVATE_COLUMNS = {
    "JOB_HASH",
    "SOURCE_FILE",
    "SOURCE_ROW",
    "RECORD_SOURCE_ROW",
    "stable_rank_in_cell_arm",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_dump(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def assert_close(name: str, actual: float, expected: float, atol: float = 1e-10) -> None:
    if not math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=atol):
        raise RuntimeError(f"{name}: expected {expected}, observed {actual}")


def kish_ess(weights: pd.Series) -> float:
    values = weights.astype(float).to_numpy()
    return float(values.sum() ** 2 / np.square(values).sum())


def scalar(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--cell-counts", type=Path, required=True)
    parser.add_argument("--formal-sample", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    cells = pd.read_parquet(args.cell_counts)
    sample = pd.read_parquet(args.formal_sample)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    required_cell = set(CELL_KEYS) | {
        "frame_count_a",
        "frame_count_b",
        "sample_count_b",
        "inclusion_probability_a",
        "inclusion_probability_b",
        "W_h",
    }
    required_sample = set(CELL_KEYS) | {
        "JOB_HASH",
        "arm",
        "frame_count_a",
        "frame_count_b",
        "selected_cell_arm_n",
        "inclusion_probability",
        "design_weight",
        "W_h",
    }
    if missing := required_cell - set(cells.columns):
        raise RuntimeError(f"cell-count input missing columns: {sorted(missing)}")
    if missing := required_sample - set(sample.columns):
        raise RuntimeError(f"formal-sample input missing columns: {sorted(missing)}")
    if cells[CELL_KEYS].duplicated().any():
        raise RuntimeError("cell-count input has duplicate common-support cells")
    if sample["JOB_HASH"].duplicated().any():
        raise RuntimeError("formal-sample input has duplicate private keys")
    if set(sample["arm"].unique()) != {"A", "B"}:
        raise RuntimeError("formal-sample arms differ from A/B")

    expected_main = int(contract["frozen_sampling"]["main_max"])
    if len(sample) != expected_main:
        raise RuntimeError(f"formal sample does not reproduce main_max={expected_main}")

    expected_b = np.minimum(cells["frame_count_b"], 3 * cells["frame_count_a"])
    if not np.array_equal(cells["sample_count_b"].to_numpy(), expected_b.to_numpy()):
        raise RuntimeError("sample_count_b differs from min(frame_count_b, 3*frame_count_a)")
    assert_close("inclusion_probability_a", cells["inclusion_probability_a"].min(), 1.0)
    assert_close("inclusion_probability_a", cells["inclusion_probability_a"].max(), 1.0)
    expected_probability_b = cells["sample_count_b"] / cells["frame_count_b"]
    max_probability_error = float(
        np.abs(cells["inclusion_probability_b"] - expected_probability_b).max()
    )
    assert_close("maximum B inclusion-probability definition error", max_probability_error, 0.0)

    pooled_frame_total = int((cells["frame_count_a"] + cells["frame_count_b"]).sum())
    expected_wh = (cells["frame_count_a"] + cells["frame_count_b"]) / pooled_frame_total
    max_wh_definition_error = float(np.abs(cells["W_h"] - expected_wh).max())
    assert_close("maximum W_h definition error", max_wh_definition_error, 0.0)
    assert_close("sum of W_h", cells["W_h"].sum(), 1.0)

    sample_counts = (
        sample.groupby(CELL_KEYS + ["arm"], observed=True)
        .size()
        .unstack("arm", fill_value=0)
        .reset_index()
    )
    cell_check = cells.merge(sample_counts, on=CELL_KEYS, how="left", validate="one_to_one")
    if not np.array_equal(cell_check["A"].to_numpy(), cell_check["frame_count_a"].to_numpy()):
        raise RuntimeError("sampled arm-A counts do not equal frame_count_a in every cell")
    if not np.array_equal(cell_check["B"].to_numpy(), cell_check["sample_count_b"].to_numpy()):
        raise RuntimeError("sampled arm-B counts do not equal sample_count_b in every cell")

    expected_sample_probability = np.where(
        sample["arm"].eq("A"),
        1.0,
        sample["selected_cell_arm_n"] / sample["frame_count_b"],
    )
    max_sample_probability_error = float(
        np.abs(sample["inclusion_probability"] - expected_sample_probability).max()
    )
    assert_close("sample inclusion-probability definition error", max_sample_probability_error, 0.0)
    max_ipw_definition_error = float(
        np.abs(sample["design_weight"] - 1.0 / sample["inclusion_probability"]).max()
    )
    assert_close("sample IPW definition error", max_ipw_definition_error, 0.0, atol=1e-9)

    reconstruction = (
        sample.groupby(CELL_KEYS + ["arm"], observed=True)["design_weight"]
        .sum()
        .unstack("arm")
        .reset_index()
        .merge(cells[CELL_KEYS + ["frame_count_a", "frame_count_b"]], on=CELL_KEYS)
    )
    reconstruction["error_a"] = reconstruction["A"] - reconstruction["frame_count_a"]
    reconstruction["error_b"] = reconstruction["B"] - reconstruction["frame_count_b"]
    max_cell_reconstruction_error = float(
        reconstruction[["error_a", "error_b"]].abs().to_numpy().max()
    )
    assert_close(
        "maximum IPW cell reconstruction error",
        max_cell_reconstruction_error,
        0.0,
        atol=1e-7,
    )

    # This is the comparison weight implied by the frozen estimand: each arm receives
    # the same original pooled frame mass W_h in each common-support cell.
    sample["standardized_comparison_weight"] = sample["W_h"] / sample["selected_cell_arm_n"]
    standardized_cell_mass = (
        sample.groupby(CELL_KEYS + ["arm"], observed=True)["standardized_comparison_weight"]
        .sum()
        .unstack("arm")
        .reset_index()
        .merge(cells[CELL_KEYS + ["W_h"]], on=CELL_KEYS)
    )
    standardized_cell_mass["error_a"] = standardized_cell_mass["A"] - standardized_cell_mass["W_h"]
    standardized_cell_mass["error_b"] = standardized_cell_mass["B"] - standardized_cell_mass["W_h"]
    max_standardized_cell_error = float(
        standardized_cell_mass[["error_a", "error_b"]].abs().to_numpy().max()
    )
    assert_close(
        "maximum standardized cell-mass error",
        max_standardized_cell_error,
        0.0,
        atol=1e-12,
    )

    frame_totals = {
        "A": int(cells["frame_count_a"].sum()),
        "B": int(cells["frame_count_b"].sum()),
    }
    selected_totals = sample.groupby("arm", observed=True).size().astype(int).to_dict()
    arm_diagnostics: dict[str, Any] = {}
    for arm in ("A", "B"):
        group = sample.loc[sample["arm"].eq(arm)]
        ipw = group["design_weight"].astype(float)
        standardized = group["standardized_comparison_weight"].astype(float)
        arm_diagnostics[arm] = {
            "selected_n": int(len(group)),
            "selected_share_of_formal_sample": float(len(group) / len(sample)),
            "frame_total_reconstructed_by_ipw": float(ipw.sum()),
            "frame_share": float(frame_totals[arm] / sum(frame_totals.values())),
            "inclusion_probability_min": float(group["inclusion_probability"].min()),
            "inclusion_probability_max": float(group["inclusion_probability"].max()),
            "ipw_min": float(ipw.min()),
            "ipw_max": float(ipw.max()),
            "ipw_kish_ess_descriptive": kish_ess(ipw),
            "ipw_kish_ess_fraction_of_selected_n": float(kish_ess(ipw) / len(group)),
            "standardized_weight_sum": float(standardized.sum()),
            "standardized_weight_min": float(standardized.min()),
            "standardized_weight_max": float(standardized.max()),
            "standardized_weight_kish_ess_descriptive": kish_ess(standardized),
            "standardized_weight_kish_ess_fraction_of_selected_n": float(
                kish_ess(standardized) / len(group)
            ),
        }

    wh_sorted = cells["W_h"].sort_values(ascending=False).reset_index(drop=True)
    support = {
        "common_support_cell_count": int(len(cells)),
        "occupation_major_category_count": int(cells["OCCUPATION_MAJOR"].nunique()),
        "census_region_category_count": int(cells["CENSUS_REGION"].nunique()),
        "created_year_category_count": int(cells["created_year"].nunique()),
        "created_year_min": int(cells["created_year"].min()),
        "created_year_max": int(cells["created_year"].max()),
        "pooled_frame_top_cell_share": float(wh_sorted.iloc[0]),
        "pooled_frame_top_5_cell_share": float(wh_sorted.iloc[:5].sum()),
        "pooled_frame_top_10_cell_share": float(wh_sorted.iloc[:10].sum()),
        "pooled_frame_cell_hhi": float(np.square(cells["W_h"]).sum()),
        "pooled_frame_effective_cell_count": float(1.0 / np.square(cells["W_h"]).sum()),
        "cells_with_sample_b_equal_3_times_a": int(
            (cells["sample_count_b"] == 3 * cells["frame_count_a"]).sum()
        ),
    }

    dimension_specs = [
        ("occupation_major", "OCCUPATION_MAJOR"),
        ("census_region", "CENSUS_REGION"),
        ("created_year", "created_year"),
    ]
    distributions: dict[str, list[dict[str, Any]]] = {}
    for public_name, column in dimension_specs:
        grouped = (
            cells.groupby(column, observed=True, dropna=False)
            .agg(
                common_support_cells=("W_h", "size"),
                frame_a=("frame_count_a", "sum"),
                frame_b=("frame_count_b", "sum"),
                selected_b=("sample_count_b", "sum"),
                pooled_frame_share=("W_h", "sum"),
            )
            .reset_index()
            .sort_values(column)
        )
        grouped["selected_a"] = grouped["frame_a"]
        grouped["selected_total"] = grouped["selected_a"] + grouped["selected_b"]
        grouped["frame_total"] = grouped["frame_a"] + grouped["frame_b"]
        distributions[public_name] = [
            {key: scalar(value) for key, value in row.items()}
            for row in grouped.to_dict(orient="records")
        ]

    validations = {
        "formal_sample_n_equals_contract_main_max": len(sample) == expected_main,
        "cell_keys_unique": True,
        "formal_private_keys_unique": True,
        "sample_count_b_rule_holds_all_cells": True,
        "sampled_cell_arm_counts_match_design": True,
        "max_inclusion_probability_definition_error": max(
            max_probability_error, max_sample_probability_error
        ),
        "max_ipw_definition_error": max_ipw_definition_error,
        "max_ipw_cell_reconstruction_error": max_cell_reconstruction_error,
        "max_W_h_definition_error": max_wh_definition_error,
        "W_h_sum": float(cells["W_h"].sum()),
        "max_standardized_cell_mass_error": max_standardized_cell_error,
    }

    interpretation = [
        (
            "The frozen formal sample contains 10,075 arm-A and 30,225 arm-B records. "
            "Those counts are deliberately balanced at 1:3 within every one of the 69 "
            "common-support cells; the unweighted 25%/75% arm split is therefore a design "
            "composition and does not represent the pooled frame, where arm A is under 1%."
        ),
        (
            "Arm-B inclusion probabilities range from about 0.24% to 19.46%, producing IPWs "
            "from about 5.14 to 421.59. The IPWs exactly reconstruct the arm-specific frame "
            "counts within numerical tolerance, but their concentration means that simple "
            "unweighted summaries do not recover frame composition. No trimming, capping, or "
            "resampling is applied because that would change the frozen design and estimand."
        ),
        (
            "The comparison weights serve a different purpose from IPW: they give both arms "
            "the same original pooled-frame cell distribution, with each arm summing to one. "
            "Their descriptive Kish ESS is much lower than the selected count, especially for "
            "arm A, showing concentration in the standardized comparison. These ESS values are "
            "weight-concentration summaries only; they are not statistical power and do not "
            "account for employer, occupation, or other dependence."
        ),
        (
            "Composition is concentrated within the supported frame: the largest cell has about "
            "4.52% of pooled cell mass, the ten largest have about 34.26%, and the effective cell "
            "count is about 43.1 out of 69. The three largest occupation-major categories account "
            "for about 80.73% of pooled supported-frame mass. Comparisons therefore describe the "
            "frozen supported cells and should not be generalized to occupations, years, or "
            "regions outside that support."
        ),
    ]

    diagnostics = {
        "version": VERSION,
        "source_contract_version": contract.get("version"),
        "scope": {
            "analysis": "frozen_sample_design_and_weight_concentration_only",
            "semantic_analysis_performed": False,
            "new_sample_drawn": False,
            "weights_trimmed_or_capped": False,
            "record_level_output_written": False,
        },
        "definitions": {
            "ipw": "inverse inclusion probability; reconstructs arm-specific frame counts",
            "original_pooled_cell_standardized_weight": (
                "W_h divided by selected cell-arm n; each arm sums to one and each original "
                "common-support cell contributes the same pooled-frame mass W_h in both arms"
            ),
            "kish_ess": (
                "descriptive weight-concentration diagnostic (sum(w)^2/sum(w^2)); not an "
                "inferential effective sample size, clustering adjustment, or power calculation"
            ),
        },
        "frame_and_sample": {
            "formal_sample_total": int(len(sample)),
            "pooled_supported_frame_total": int(sum(frame_totals.values())),
            "arms": arm_diagnostics,
        },
        "common_support": support,
        "distributions": distributions,
        "validation": validations,
        "interpretation": interpretation,
        "limitations": [
            "Diagnostics apply only to the frozen old-C1 common-support candidate frame.",
            "No outcome, text, evaluation flag, employer identifier, or semantic label was analyzed.",
            "Kish ESS does not account for correlated records or identify inferential power.",
        ],
    }

    json_path = args.output_dir / "design_diagnostics.json"
    csv_path = args.output_dir / "design_diagnostics.csv"
    interpretation_path = args.output_dir / "INTERPRETATION.md"
    json_dump(json_path, diagnostics)

    rows: list[dict[str, Any]] = []

    def add_row(
        section: str,
        metric: str,
        value: Any,
        unit: str,
        arm: str = "",
        dimension: str = "",
        category: Any = "",
        denominator: str = "",
        note: str = "",
    ) -> None:
        rows.append(
            {
                "section": section,
                "dimension": dimension,
                "category": category,
                "arm": arm,
                "metric": metric,
                "value": value,
                "unit": unit,
                "denominator": denominator,
                "note": note,
            }
        )

    add_row("frame_and_sample", "formal_sample_total", len(sample), "records")
    add_row(
        "frame_and_sample",
        "pooled_supported_frame_total",
        sum(frame_totals.values()),
        "records",
    )
    for arm, values in arm_diagnostics.items():
        units = {
            "selected_n": "records",
            "selected_share_of_formal_sample": "share",
            "frame_total_reconstructed_by_ipw": "records",
            "frame_share": "share",
            "inclusion_probability_min": "probability",
            "inclusion_probability_max": "probability",
            "ipw_min": "weight",
            "ipw_max": "weight",
            "ipw_kish_ess_descriptive": "records_equivalent",
            "ipw_kish_ess_fraction_of_selected_n": "share",
            "standardized_weight_sum": "normalized_weight",
            "standardized_weight_min": "normalized_weight",
            "standardized_weight_max": "normalized_weight",
            "standardized_weight_kish_ess_descriptive": "records_equivalent",
            "standardized_weight_kish_ess_fraction_of_selected_n": "share",
        }
        for metric, value in values.items():
            note = ""
            if "kish_ess" in metric:
                note = "Descriptive weight concentration only; not inferential power."
            add_row("arm_weight_diagnostics", metric, value, units[metric], arm=arm, note=note)
    for metric, value in support.items():
        unit = "count"
        if metric.endswith("share") or metric.endswith("hhi"):
            unit = "share"
        elif metric == "pooled_frame_effective_cell_count":
            unit = "cells_equivalent"
        elif metric.startswith("created_year_"):
            unit = "year"
        add_row("common_support", metric, value, unit)
    for dimension, records in distributions.items():
        category_key = {
            "occupation_major": "OCCUPATION_MAJOR",
            "census_region": "CENSUS_REGION",
            "created_year": "created_year",
        }[dimension]
        for record in records:
            category = record[category_key]
            for metric, value in record.items():
                if metric == category_key:
                    continue
                unit = "share" if metric == "pooled_frame_share" else (
                    "cells" if metric == "common_support_cells" else "records"
                )
                add_row(
                    "distribution",
                    metric,
                    value,
                    unit,
                    dimension=dimension,
                    category=category,
                    denominator=(
                        "pooled supported frame" if metric == "pooled_frame_share" else ""
                    ),
                )
    for metric, value in validations.items():
        add_row("validation", metric, value, "boolean" if isinstance(value, bool) else "absolute")

    if any(PRIVATE_COLUMNS.intersection(row.keys()) for row in rows):
        raise RuntimeError("private columns reached aggregate CSV construction")
    pd.DataFrame(rows).to_csv(csv_path, index=False, quoting=csv.QUOTE_MINIMAL)

    interpretation_path.write_text(
        "# LinkUp L1 design diagnostics\n\n"
        + "\n\n".join(interpretation)
        + "\n\n"
        + "The CSV and JSON contain only aggregate structural diagnostics. They contain no "
        + "record keys, source-row identifiers, employer identifiers, job text, outcomes, or "
        + "record-level weights.\n",
        encoding="utf-8",
    )

    input_files = [args.contract, args.cell_counts, args.formal_sample]
    output_files = [json_path, csv_path, interpretation_path]
    execution_receipt = {
        "version": VERSION,
        "status": "complete",
        "inputs": {
            path.name: {"sha256": sha256(path), "bytes": path.stat().st_size}
            for path in input_files
        },
        "outputs": {
            path.name: {"sha256": sha256(path), "bytes": path.stat().st_size}
            for path in output_files
        },
        "script": {
            Path(__file__).name: {
                "sha256": sha256(Path(__file__)),
                "bytes": Path(__file__).stat().st_size,
            }
        },
        "validation": validations,
    }
    receipt_path = args.output_dir / "EXECUTION_RECEIPT.json"
    json_dump(receipt_path, execution_receipt)

    sha_rows = []
    for role, paths in (
        ("input", input_files),
        ("output", output_files + [receipt_path]),
        ("script", [Path(__file__)]),
    ):
        for path in paths:
            sha_rows.append(
                {
                    "role": role,
                    "filename": path.name,
                    "sha256": sha256(path),
                    "bytes": path.stat().st_size,
                }
            )
    pd.DataFrame(sha_rows).to_csv(
        args.output_dir / "SHA256_RECEIPT.csv", index=False, quoting=csv.QUOTE_MINIMAL
    )


if __name__ == "__main__":
    main()
