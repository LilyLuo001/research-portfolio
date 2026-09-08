#!/usr/bin/env python3
"""Run the frozen YAX timing, endpoint, era, and seasonality extensions.

The runner consumes the authenticated 468-occupation Gate 1 aggregate and
publishes coefficients, occupation influence representations, paired
comparisons, and numerical audits only. It never publishes cell stocks.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy.stats import norm


HERE = Path(__file__).resolve().parent
SPEC_PATH = HERE / "TIMING_EXTENSIONS_SPEC.json"
SCHEMA = "yax-gate2-timing-extensions-spec-v1"
SPEC_PREFIX = "yaxgate2timing_v1"
RESULT_PREFIX = "yaxresult_v1"
RECEIPT_PREFIX = "yaxreceipt_v1"
MDE_FACTOR = 1.959963984540054 + 0.8416212335729143
ONSETS = (
    "2022-11", "2022-12", "2023-01", "2023-02",
    "2023-03", "2023-04", "2023-05", "2023-06",
)
STRUCTURES = ("unconditioned", "family_month")
OUTPUTS = {
    "MODEL_RESULTS.csv", "PAIRED_COMPARISONS.csv", "MODEL_COVARIANCE.csv",
    "MODEL_INFLUENCE.csv", "NUMERICAL_AUDITS.json", "VALIDATION_REPORT.json",
    "RESULT_SUMMARY.md",
}


class TimingError(RuntimeError):
    """A frozen scientific or numerical requirement failed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise TimingError(message)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def content_id(prefix: str, value: dict[str, Any], excluded: Iterable[str] = ()) -> str:
    omitted = set(excluded)
    payload = {key: item for key, item in value.items() if key not in omitted}
    return f"{prefix}_{hashlib.sha256(canonical_bytes(payload)).hexdigest()}"


def spec_id(spec: dict[str, Any]) -> str:
    return content_id(SPEC_PREFIX, spec, ("spec_id",))


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise TimingError(f"cannot read {path.name}: {error}") from error
    require(isinstance(value, dict), f"{path.name} is not a JSON object")
    return value


def load_module(name: str, path: Path):
    module_spec = importlib.util.spec_from_file_location(name, path)
    require(module_spec is not None and module_spec.loader is not None,
            f"cannot import {path.name}")
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[name] = module
    module_spec.loader.exec_module(module)
    return module


def support_hash(codes: list[str]) -> str:
    return hashlib.sha256("".join(f"{code}\n" for code in sorted(codes)).encode()).hexdigest()


def higher_quantile(values: np.ndarray, probability: float) -> float:
    return float(np.quantile(np.asarray(values, float), probability, method="higher"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    require(bool(rows), f"refusing to write empty {path.name}")
    fields: list[str] = []
    for row in rows:
        fields.extend(key for key in row if key not in fields)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def validate_spec(spec: dict[str, Any]) -> None:
    require(spec.get("schema_version") == SCHEMA, "spec schema differs")
    require(spec.get("spec_id") == spec_id(spec), "spec identity differs")
    require(spec.get("execution", {}).get("runner_sha256") == sha256_file(Path(__file__)),
            "runner hash differs")
    contract = spec.get("scientific_contract", {})
    require(contract.get("support_occupations") == 468, "support count differs")
    require(contract.get("support_hash_sha256") ==
            "11ec58ab1004cd83d62c57785f6c0dd3ee5a8abf08b7f71a3b664e91ded8333b",
            "support identity differs")
    require(tuple(contract.get("onset_dates", [])) == ONSETS, "onset grid differs")
    require(tuple(contract.get("structures", [])) == STRUCTURES, "structures differ")
    require(contract.get("transition_month_excluded") == "2022-12",
            "transition rule differs")
    require(contract.get("missing_month") == "2025-10", "missing month differs")
    require(contract.get("target") == "Q5_x_post conditional on Q2-Q4 and Webb_z by post",
            "target differs")
    require(spec.get("inference", {}).get("draws") == 9999, "draw count differs")
    require(spec.get("inference", {}).get("cluster") == "occupation", "cluster differs")
    require(set(spec.get("outputs", {}).get("files", [])) == OUTPUTS,
            "output inventory differs")
    require(spec.get("outputs", {}).get("protected_cells_published") is False,
            "protected-output rule differs")
    require(spec.get("requirements") == {
        "N04": "coding-stable and two feasible seasonality specifications",
        "T05": "through-2024 and full-window paired comparison under both structures",
        "Y08": "complete November-2022 through June-2023 onset grid and seasonality",
        "Y09": "early-late eras and shutdown-adjacent exclusions under both structures",
    }, "requirement scope differs")


def verify_inputs(args: argparse.Namespace, spec: dict[str, Any]) -> dict[str, str]:
    observed: dict[str, str] = {}
    for label, record in spec["authenticated_inputs"].items():
        path = getattr(args, label)
        require(path.is_file() and not path.is_symlink(), f"{label} is absent or indirect")
        digest = sha256_file(path)
        require(digest == record["sha256"], f"{label} hash differs")
        observed[label] = digest
    return observed


@dataclass(frozen=True)
class ModelDefinition:
    model_id: str
    requirement: str
    category: str
    structure: str
    onset: str
    months: tuple[str, ...]
    seasonality: str = "none"


def model_definitions(observed_months: list[str]) -> list[ModelDefinition]:
    base = tuple(month for month in observed_months if month != "2022-12")
    post_2020 = tuple(month for month in base if month >= "2020-01")
    through_2024 = tuple(month for month in base if month <= "2024-12")
    late = tuple(month for month in base if month <= "2022-11" or month >= "2025-01")
    full_no_adjacent = tuple(month for month in base if month not in {"2025-09", "2025-11"})
    late_no_adjacent = tuple(month for month in late if month not in {"2025-09", "2025-11"})
    definitions: list[ModelDefinition] = []
    for structure in STRUCTURES:
        suffix = structure
        definitions.extend([
            ModelDefinition(f"baseline_full_{suffix}", "T05", "endpoint", structure,
                            "2023-01", base),
            ModelDefinition(f"endpoint_through_2024_{suffix}", "T05", "endpoint", structure,
                            "2023-01", through_2024),
            ModelDefinition(f"post_2020_{suffix}", "N04", "coding_stable", structure,
                            "2023-01", post_2020),
            ModelDefinition(f"seasonal_quintile_month_{suffix}", "N04", "seasonality",
                            structure, "2023-01", base, "quintile_month_of_year"),
            ModelDefinition(f"seasonal_occupation_month_{suffix}", "N04", "seasonality",
                            structure, "2023-01", base, "occupation_month_of_year"),
            ModelDefinition(f"era_2023_2024_{suffix}", "Y09", "era", structure,
                            "2023-01", through_2024),
            ModelDefinition(f"era_2025_2026_{suffix}", "Y09", "era", structure,
                            "2025-01", late),
            ModelDefinition(f"full_without_2025_09_11_{suffix}", "Y09", "shutdown",
                            structure, "2023-01", full_no_adjacent),
            ModelDefinition(f"late_without_2025_09_11_{suffix}", "Y09", "shutdown",
                            structure, "2025-01", late_no_adjacent),
        ])
        definitions.extend(
            ModelDefinition(f"onset_{onset.replace('-', '_')}_{suffix}", "Y08", "onset",
                            structure, onset, base)
            for onset in ONSETS
        )
    require(len(definitions) == 34, "model inventory does not contain 34 fits")
    require(len({row.model_id for row in definitions}) == 34, "model IDs are not unique")
    return definitions


def stable_occupation_data(cells: pd.DataFrame) -> pd.DataFrame:
    rows = cells.groupby("occ_code", as_index=False).agg(
        family=("family", "first"), family_count=("family", "nunique"),
        quintile=("beta_quintile", "first"), quintile_count=("beta_quintile", "nunique"),
        webb_z=("webb_z", "first"), webb_count=("webb_z", "nunique"),
    ).sort_values("occ_code", kind="mergesort")
    require((rows[["family_count", "quintile_count", "webb_count"]] == 1).all().all(),
            "occupation treatment attributes are not stable")
    return rows.reset_index(drop=True)


def make_bundle(a1, cells: pd.DataFrame, definition: ModelDefinition):
    stable = stable_occupation_data(cells)
    occupations = stable.occ_code.astype(str).tolist()
    selected = cells.loc[cells.month.isin(definition.months)].copy()
    selected = selected.sort_values(["occ_code", "month"], kind="mergesort").reset_index(drop=True)
    require(sorted(selected.month.unique()) == sorted(definition.months),
            f"{definition.model_id}: month support differs")
    require(len(selected) == len(occupations) * len(definition.months),
            f"{definition.model_id}: panel is not balanced")
    require(selected.occ_code.astype(str).tolist() ==
            np.repeat(np.asarray(occupations, object), len(definition.months)).tolist(),
            f"{definition.model_id}: row order differs")
    months = selected.month.astype(str).to_numpy(object)
    quintile = selected.beta_quintile.to_numpy(int)
    post = months >= definition.onset
    columns = [((quintile == value) & post).astype(float) for value in (2, 3, 4, 5)]
    labels = [f"Q{value}_x_post" for value in (2, 3, 4, 5)]
    columns.append(selected.webb_z.to_numpy(float) * post)
    labels.append("Webb_z_x_post")
    if definition.seasonality == "quintile_month_of_year":
        month_number = np.asarray([int(value[5:7]) for value in months])
        for value in (2, 3, 4, 5):
            for number in range(2, 13):
                columns.append(((quintile == value) & (month_number == number)).astype(float))
                labels.append(f"Q{value}_x_month_of_year_{number:02d}")
    x = np.column_stack(columns)
    first = selected.occ_code.astype(str).to_numpy(object)
    if definition.seasonality == "occupation_month_of_year":
        first = (selected.occ_code.astype(str) + "|m" +
                 selected.month.astype(str).str[5:7]).to_numpy(object)
    second = selected.month.astype(str).to_numpy(object)
    if definition.structure == "family_month":
        second = (selected.family.astype(str) + "|" +
                  selected.month.astype(str)).to_numpy(object)
    young = selected.young.to_numpy(float)
    older = selected.older.to_numpy(float)
    bundle = a1.ModelBundle(
        model_id=definition.model_id,
        frame=selected[["occ_code", "month", "family", "young", "older",
                        "beta_quintile", "webb_z"]].copy(),
        young=young, total=young + older, first_labels=first, second_labels=second,
        regressors=x, regressor_labels=labels, focal_target_label="Q5_x_post",
    )
    return bundle, occupations


def assert_registered_n04_parity(a1, cells: pd.DataFrame, bundle,
                                 definition: ModelDefinition) -> None:
    """Require exact parity with the six already reviewed A1 model builders."""
    if definition.requirement != "N04":
        return
    registered = a1.model_bundle(cells, definition.model_id)
    checks = (
        np.array_equal(bundle.frame[["occ_code", "month"]].to_numpy(object),
                       registered.frame[["occ_code", "month"]].to_numpy(object)),
        np.array_equal(bundle.young, registered.young),
        np.array_equal(bundle.total, registered.total),
        np.array_equal(bundle.first_labels, registered.first_labels),
        np.array_equal(bundle.second_labels, registered.second_labels),
        np.array_equal(bundle.regressors, registered.regressors),
        bundle.regressor_labels == registered.regressor_labels,
        bundle.focal_target_label == registered.focal_target_label,
    )
    require(all(checks), f"{definition.model_id}: registered A1 design parity failed")


def scaled_influence(fit) -> np.ndarray:
    count = fit.influence.shape[0]
    value = math.sqrt(count / (count - 1)) * np.asarray(fit.influence, float)
    require(np.allclose(value.T @ value, fit.covariance, rtol=1e-9, atol=1e-12),
            f"{fit.model_id}: influence does not reproduce covariance")
    return value


def align_target_influence(fit, target: int,
                           occupation_universe: list[str]) -> tuple[np.ndarray, list[str]]:
    active_occupations = sorted(
        fit.bundle.frame.loc[fit.active, "occ_code"].astype(str).unique().tolist())
    require(len(active_occupations) == fit.influence.shape[0],
            f"{fit.model_id}: active occupation labels do not match influence")
    require(set(active_occupations).issubset(occupation_universe),
            f"{fit.model_id}: active occupation lies outside fixed support")
    active_influence = scaled_influence(fit)[:, target]
    active_map = dict(zip(active_occupations, active_influence))
    influence = np.asarray([active_map.get(code, 0.0) for code in occupation_universe], float)
    require(np.isclose(influence @ influence, fit.covariance[target, target],
                       rtol=1e-9, atol=1e-12),
            f"{fit.model_id}: aligned influence changes covariance")
    return influence, active_occupations


def summarize_fit(fit, definition: ModelDefinition, signs: np.ndarray,
                  occupation_universe: list[str]) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    target = fit.labels.index("Q5_x_post")
    influence, active_occupations = align_target_influence(
        fit, target, occupation_universe)
    centered = signs @ influence
    estimate = float(fit.treatment[target])
    se = float(np.sqrt(fit.covariance[target, target]))
    require(se > 0 and np.isfinite(se), f"{fit.model_id}: invalid standard error")
    critical = higher_quantile(np.abs(centered / se), .95)
    row = {
        "model_id": definition.model_id, "requirement": definition.requirement,
        "category": definition.category, "structure": definition.structure,
        "onset": definition.onset, "seasonality": definition.seasonality,
        "first_month": definition.months[0], "last_month": definition.months[-1],
        "observed_months": len(definition.months),
        "month_list_sha256": hashlib.sha256(canonical_bytes(list(definition.months))).hexdigest(),
        "transition_2022_12_excluded": "2022-12" not in definition.months,
        "october_2025_absent": "2025-10" not in definition.months,
        "september_2025_included": "2025-09" in definition.months,
        "november_2025_included": "2025-11" in definition.months,
        "coefficient": estimate, "occupation_cluster_se": se,
        "ci_lower": estimate - critical * se, "ci_upper": estimate + critical * se,
        "bootstrap_p_value": float((1 + np.sum(np.abs(centered / se) >= abs(estimate / se))) /
                                   (len(centered) + 1)),
        "bootstrap_critical": critical, "mde80": MDE_FACTOR * se,
        "support_occupations": len(occupation_universe),
        "estimating_occupation_clusters": fit.influence.shape[0],
        "zero_influence_support_occupations": len(occupation_universe) - fit.influence.shape[0],
        "active_rows": int(fit.active.sum()),
        "profiled_boundary_rows": int(np.sum((fit.bundle.total > 0) & ~fit.active)),
        "a1_certificate": fit.audit["a1_certification"]["status"],
        "state_source": "fresh A1 trust path corroborated by independent zero-start reference",
    }
    return row, influence, centered


def paired_row(pair_id: str, purpose: str, left: str, right: str,
               rows: dict[str, dict[str, Any]], influences: dict[str, np.ndarray],
               signs: np.ndarray) -> dict[str, Any]:
    difference = float(rows[left]["coefficient"] - rows[right]["coefficient"])
    influence = influences[left] - influences[right]
    se = float(np.sqrt(influence @ influence))
    if se <= np.finfo(float).eps:
        critical, p_value, lower, upper, mde = 0.0, 1.0, difference, difference, 0.0
    else:
        centered = signs @ influence
        critical = higher_quantile(np.abs(centered / se), .95)
        p_value = float((1 + np.sum(np.abs(centered / se) >= abs(difference / se))) /
                        (len(centered) + 1))
        lower, upper, mde = difference - critical * se, difference + critical * se, MDE_FACTOR * se
    return {
        "pair_id": pair_id, "purpose": purpose, "left_model": left,
        "right_model": right, "coefficient_difference": difference,
        "paired_occupation_cluster_se": se, "ci_lower": lower, "ci_upper": upper,
        "bootstrap_p_value": p_value, "bootstrap_critical": critical,
        "mde80_difference": mde, "common_occupation_draws": True,
        "interpretation_if_ci_contains_zero": "design does not detect a difference; not economic equivalence",
    }


def pair_inventory() -> list[tuple[str, str, str, str]]:
    pairs: list[tuple[str, str, str, str]] = []
    for structure in STRUCTURES:
        suffix = structure
        pairs.extend([
            (f"endpoint_change_{suffix}", "through-2024 minus full window",
             f"endpoint_through_2024_{suffix}", f"baseline_full_{suffix}"),
            (f"late_minus_early_{suffix}", "2025-2026 era minus 2023-2024 era",
             f"era_2025_2026_{suffix}", f"era_2023_2024_{suffix}"),
            (f"shutdown_full_{suffix}", "drop September and November 2025 from full window",
             f"full_without_2025_09_11_{suffix}", f"baseline_full_{suffix}"),
            (f"shutdown_late_{suffix}", "drop September and November 2025 from 2025-2026 era",
             f"late_without_2025_09_11_{suffix}", f"era_2025_2026_{suffix}"),
            (f"post2020_{suffix}", "coding-stable post-2020 minus full window",
             f"post_2020_{suffix}", f"baseline_full_{suffix}"),
            (f"season_quintile_{suffix}", "quintile-by-month seasonality minus baseline",
             f"seasonal_quintile_month_{suffix}", f"baseline_full_{suffix}"),
            (f"season_occupation_{suffix}", "occupation-by-month matched-calendar seasonality minus baseline",
             f"seasonal_occupation_month_{suffix}", f"baseline_full_{suffix}"),
        ])
        for onset in ONSETS:
            label = onset.replace("-", "_")
            pairs.append((f"onset_{label}_{suffix}_minus_jan2023",
                          "onset sensitivity relative to January 2023",
                          f"onset_{label}_{suffix}", f"onset_2023_01_{suffix}"))
    for stem in (
        "baseline_full", "endpoint_through_2024", "post_2020",
        "seasonal_quintile_month", "seasonal_occupation_month", "era_2023_2024",
        "era_2025_2026", "full_without_2025_09_11", "late_without_2025_09_11",
    ) + tuple(f"onset_{value.replace('-', '_')}" for value in ONSETS):
        pairs.append((f"conditioning_{stem}", "family-month minus unconditioned",
                      f"{stem}_family_month", f"{stem}_unconditioned"))
    return pairs


def apply_onset_simultaneous(rows: dict[str, dict[str, Any]],
                             centered: dict[str, np.ndarray]) -> None:
    for structure in STRUCTURES:
        names = [f"onset_{value.replace('-', '_')}_{structure}" for value in ONSETS]
        ses = np.asarray([rows[name]["occupation_cluster_se"] for name in names])
        draws = np.column_stack([centered[name] for name in names])
        critical = higher_quantile(np.max(np.abs(draws / ses[None, :]), axis=1), .95)
        for name, se in zip(names, ses):
            estimate = rows[name]["coefficient"]
            rows[name]["simultaneous_onset_critical"] = critical
            rows[name]["simultaneous_onset_ci_lower"] = estimate - critical * se
            rows[name]["simultaneous_onset_ci_upper"] = estimate + critical * se


def run(args: argparse.Namespace) -> None:
    require(not args.output_dir.exists(), "refusing to overwrite output directory")
    spec = load_json(args.spec)
    validate_spec(spec)
    authenticated = verify_inputs(args, spec)
    support = load_module("yax_timing_support", args.support_runner)
    dynamic_core = load_module("yax_timing_dynamic_core", args.dynamic_core_runner)
    support_spec = load_json(args.support_spec)
    _, analysis, _, membership, cells, _, _, _ = support.authenticate(args, support_spec)
    a1 = support.load_a1(args.a1_runner, analysis["software"]["artifact_safety_sha256"])
    runtime = support.verify_signed_a1_runtime_contract(a1, analysis)
    occupations, signs, _ = dynamic_core.load_common_draws(args, cells, spec)
    require(len(occupations) == 468 and support_hash(occupations) ==
            spec["scientific_contract"]["support_hash_sha256"], "support moved")
    definitions = model_definitions(sorted(cells.month.astype(str).unique()))
    rows: dict[str, dict[str, Any]] = {}
    influences: dict[str, np.ndarray] = {}
    centered: dict[str, np.ndarray] = {}
    numerical: list[dict[str, Any]] = []
    for index, definition in enumerate(definitions, start=1):
        print(json.dumps({"stage": "fit", "index": index, "total": len(definitions),
                          "model_id": definition.model_id}), flush=True)
        bundle, bundle_occupations = make_bundle(a1, cells, definition)
        require(bundle_occupations == occupations, f"{definition.model_id}: support order differs")
        assert_registered_n04_parity(a1, cells, bundle, definition)
        fit = support.certified_fit(a1, bundle, analysis)
        row, influence, draws = summarize_fit(fit, definition, signs, occupations)
        rows[definition.model_id] = row
        influences[definition.model_id] = influence
        centered[definition.model_id] = draws
        numerical.append({"model_id": definition.model_id,
                          "audit": support.sanitized_numerical_evidence(fit.audit)})
    apply_onset_simultaneous(rows, centered)

    # Duplicated scientific definitions are deliberate completeness views and
    # must reproduce exactly rather than silently drift.
    duplicate_pairs = []
    for structure in STRUCTURES:
        duplicate_pairs.extend([
            (f"baseline_full_{structure}", f"onset_2023_01_{structure}"),
            (f"endpoint_through_2024_{structure}", f"era_2023_2024_{structure}"),
            (f"onset_2022_12_{structure}", f"onset_2023_01_{structure}"),
        ])
    maximum_duplicate_difference = max(
        abs(rows[left]["coefficient"] - rows[right]["coefficient"])
        for left, right in duplicate_pairs
    )
    require(maximum_duplicate_difference <= 1e-10, "duplicate scientific definitions differ")
    dynamic_checkpoint = pd.read_csv(args.dynamic_core_estimates).set_index("target")
    checkpoint_differences = {}
    for structure in STRUCTURES:
        observed = rows[f"baseline_full_{structure}"]["coefficient"]
        expected = float(dynamic_checkpoint.at[f"{structure}::S", "estimate"])
        checkpoint_differences[structure] = observed - expected
    require(max(abs(value) for value in checkpoint_differences.values()) <= 1e-8,
            "full-window checkpoint differs from authoritative dynamic core")

    pairs = [paired_row(pair_id, purpose, left, right, rows, influences, signs)
             for pair_id, purpose, left, right in pair_inventory()]
    model_names = [definition.model_id for definition in definitions]
    influence_matrix = np.column_stack([influences[name] for name in model_names])
    covariance = influence_matrix.T @ influence_matrix
    covariance_rows = [
        {"row_model": left, "column_model": right,
         "occupation_cluster_covariance": float(covariance[i, j])}
        for i, left in enumerate(model_names) for j, right in enumerate(model_names)
    ]
    influence_rows = [
        {"occupation_code": occupation,
         **{name: float(influence_matrix[index, column])
            for column, name in enumerate(model_names)}}
        for index, occupation in enumerate(occupations)
    ]
    output_rows = [rows[name] for name in model_names]
    validation = {
        "schema_version": "yax-gate2-timing-extensions-validation-v1",
        "status": "PASS_TIMING_EXTENSIONS_VALIDATION",
        "checks": {
            "model_count_34": len(output_rows) == 34,
            "all_a1_certified": all(row["a1_certificate"] == "PASS_A1_NUMERICAL_CERTIFICATE"
                                    for row in output_rows),
            "onset_models_16": sum(row["category"] == "onset" for row in output_rows) == 16,
            "n04_models_6": sum(row["requirement"] == "N04" for row in output_rows) == 6,
            "full_checkpoint_reproduced": max(abs(value) for value in checkpoint_differences.values()) <= 1e-8,
            "duplicate_views_reproduced": maximum_duplicate_difference <= 1e-10,
            "all_support_468": all(row["support_occupations"] == 468 for row in output_rows),
            "estimating_cluster_counts_valid": all(
                2 <= row["estimating_occupation_clusters"] <= 468 for row in output_rows),
            "all_transition_excluded": all(row["transition_2022_12_excluded"] for row in output_rows),
            "all_october_2025_absent": all(row["october_2025_absent"] for row in output_rows),
            "paired_inventory_complete": len(pairs) == len(pair_inventory()),
            "covariance_symmetric": bool(np.allclose(covariance, covariance.T, rtol=0, atol=1e-12)),
        },
        "full_window_checkpoint_differences": checkpoint_differences,
        "maximum_duplicate_definition_coefficient_difference": maximum_duplicate_difference,
    }
    require(all(validation["checks"].values()), "timing extension validation failed")

    args.output_dir.mkdir(parents=True)
    write_csv(args.output_dir / "MODEL_RESULTS.csv", output_rows)
    write_csv(args.output_dir / "PAIRED_COMPARISONS.csv", pairs)
    write_csv(args.output_dir / "MODEL_COVARIANCE.csv", covariance_rows)
    write_csv(args.output_dir / "MODEL_INFLUENCE.csv", influence_rows)
    write_json(args.output_dir / "NUMERICAL_AUDITS.json", {"models": numerical})
    write_json(args.output_dir / "VALIDATION_REPORT.json", validation)
    endpoint = {row["model_id"]: row["coefficient"] for row in output_rows
                if row["model_id"].startswith(("baseline_full", "endpoint_through_2024",
                                                "era_2025_2026"))}
    summary = (
        "# Timing, endpoint, era, and seasonality extensions\n\n"
        "Status: **post-outcome required revision; numerically validated**.\n\n"
        f"The run fits {len(output_rows)} frozen-support models: 16 onset models, six "
        "coding-stable/seasonality models, and endpoint, era, and shutdown-adjacent "
        "comparisons under both conditioning structures. Every fit uses the same "
        "468 occupations and passes fresh same-objective A1 certification.\n\n"
        f"Endpoint coefficients: `{json.dumps(endpoint, sort_keys=True)}`. Interpret "
        "all movements with the paired intervals in `PAIRED_COMPARISONS.csv`; a "
        "confidence interval containing zero is nondetection, not equivalence.\n"
    )
    (args.output_dir / "RESULT_SUMMARY.md").write_text(summary, encoding="utf-8")
    artifacts = {name: {"sha256": sha256_file(args.output_dir / name),
                        "bytes": (args.output_dir / name).stat().st_size}
                 for name in sorted(OUTPUTS)}
    manifest = {"schema_version": "yax-gate2-timing-extensions-manifest-v1",
                "spec_id": spec["spec_id"], "artifacts": artifacts}
    manifest["result_id"] = content_id(RESULT_PREFIX, manifest)
    write_json(args.output_dir / "RESULT_MANIFEST.json", manifest)
    receipt = {
        "schema_version": "yax-gate2-timing-extensions-receipt-v1",
        "status": "PASS_TIMING_EXTENSIONS_EXECUTION",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sge_job_id": os.environ.get("JOB_ID"),
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=args.repo_root, text=True).strip(),
        "spec_id": spec["spec_id"], "runner_sha256": sha256_file(Path(__file__)),
        "authenticated_input_hashes": authenticated, "runtime": runtime,
        "models": len(output_rows), "result_id": manifest["result_id"],
        "result_manifest_sha256": sha256_file(args.output_dir / "RESULT_MANIFEST.json"),
        "protected_cells_published": False, "row_microdata_published": False,
    }
    receipt["receipt_id"] = content_id(RECEIPT_PREFIX, receipt)
    write_json(args.output_dir / "EXECUTION_RECEIPT.json", receipt)
    print(json.dumps({"status": receipt["status"], "result_id": receipt["result_id"],
                      "models": len(output_rows)}, sort_keys=True))


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--repo-root", type=Path, required=True)
    value.add_argument("--spec", type=Path, default=SPEC_PATH)
    for name in (
        "support_spec", "support_runner", "canonical_spec", "a1_spec", "a1_runner",
        "a1_model_audit", "a1_dependency_release", "cells", "cells_receipt",
        "fixed_membership", "support_matrix", "support_edges",
        "direct_tail_membership", "support_result_manifest", "common_draw_binding",
        "common_multipliers", "dynamic_core_runner", "dynamic_core_spec",
        "dynamic_core_estimates", "dynamic_core_receipt", "output_dir",
    ):
        value.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    return value


def main() -> int:
    run(parser().parse_args())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except TimingError as error:
        print(f"BLOCKED: {error}")
        raise SystemExit(2)
