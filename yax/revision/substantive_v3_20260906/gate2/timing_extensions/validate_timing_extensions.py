#!/usr/bin/env python3
"""Independently validate the public N04/T05/Y08/Y09 result package."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("yax_timing_validation_math", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} is not an object")
    return value


def close(left: float, right: float, tolerance: float = 1e-10) -> bool:
    return bool(np.isclose(float(left), float(right), rtol=1e-9, atol=tolerance))


def validate(repo: Path, results: Path) -> dict[str, Any]:
    base = repo / "yax/revision/substantive_v3_20260906"
    module = load_module(base / "gate2/timing_extensions/run_timing_extensions.py")
    spec = load_json(base / "gate2/timing_extensions/TIMING_EXTENSIONS_SPEC.json")
    module.validate_spec(spec)
    manifest = load_json(results / "RESULT_MANIFEST.json")
    receipt = load_json(results / "EXECUTION_RECEIPT.json")
    models = pd.read_csv(results / "MODEL_RESULTS.csv")
    pairs = pd.read_csv(results / "PAIRED_COMPARISONS.csv")
    covariance = pd.read_csv(results / "MODEL_COVARIANCE.csv")
    influence = pd.read_csv(results / "MODEL_INFLUENCE.csv", dtype={"occupation_code": str})
    numerical = load_json(results / "NUMERICAL_AUDITS.json")
    producer = load_json(results / "VALIDATION_REPORT.json")
    archive = np.load(
        base / "runs/gate2_support_inference_authoritative_20260908/COMMON_MULTIPLIERS.npz",
        allow_pickle=False)
    signs = np.asarray(archive["multipliers"], float)
    occupations = archive["occupation_codes"].astype(str).tolist()
    model_names = models.model_id.astype(str).tolist()
    checks: dict[str, bool] = {}

    expected_files = set(module.OUTPUTS)
    records = manifest["artifacts"]
    checks["manifest_inventory"] = set(records) == expected_files
    checks["manifest_hashes"] = all(
        sha256_file(results / name) == record["sha256"] and
        (results / name).stat().st_size == record["bytes"]
        for name, record in records.items())
    payload = dict(manifest)
    payload.pop("result_id", None)
    checks["result_id"] = manifest["result_id"] == module.content_id(
        module.RESULT_PREFIX, payload)
    checks["receipt_binding"] = (
        receipt["status"] == "PASS_TIMING_EXTENSIONS_EXECUTION" and
        receipt["spec_id"] == spec["spec_id"] and
        receipt["runner_sha256"] == sha256_file(
            base / "gate2/timing_extensions/run_timing_extensions.py") and
        receipt["result_id"] == manifest["result_id"] and
        receipt["result_manifest_sha256"] == sha256_file(results / "RESULT_MANIFEST.json")
    )
    checks["privacy"] = (receipt["protected_cells_published"] is False and
                         receipt["row_microdata_published"] is False and
                         not any("cell" in name.lower() for name in records))
    checks["model_inventory"] = (
        len(models) == 34 and len(set(model_names)) == 34 and
        set(model_names) == {row.model_id for row in module.model_definitions(
            [value for value in pd.period_range("2017-01", "2026-07", freq="M").astype(str)
             if value != "2025-10"])}
    )
    checks["requirement_counts"] = (
        int((models.requirement == "N04").sum()) == 6 and
        int((models.requirement == "T05").sum()) == 4 and
        int((models.requirement == "Y08").sum()) == 16 and
        int((models.requirement == "Y09").sum()) == 8)
    checks["calendar_contract"] = bool(
        models.transition_2022_12_excluded.all() and models.october_2025_absent.all())
    checks["influence_order"] = (
        influence.occupation_code.astype(str).str.zfill(4).tolist() == occupations and
        list(influence.columns[1:]) == model_names)
    matrix = influence[model_names].to_numpy(float)
    recomputed_covariance = matrix.T @ matrix
    published_covariance = covariance.pivot(
        index="row_model", columns="column_model", values="occupation_cluster_covariance"
    ).reindex(index=model_names, columns=model_names).to_numpy(float)
    maximum_covariance_difference = float(np.max(np.abs(
        recomputed_covariance - published_covariance)))
    checks["covariance_recomputed"] = maximum_covariance_difference <= 1e-12

    model_index = models.set_index("model_id")
    maximum_model_difference = 0.0
    for column, name in enumerate(model_names):
        row = model_index.loc[name]
        values = matrix[:, column]
        se = float(np.sqrt(values @ values))
        centered = signs @ values
        critical = module.higher_quantile(np.abs(centered / se), .95)
        estimate = float(row.coefficient)
        recomputed = (
            se, estimate - critical * se, estimate + critical * se,
            (1 + np.sum(np.abs(centered / se) >= abs(estimate / se))) / (len(centered) + 1),
            module.MDE_FACTOR * se,
        )
        published = (row.occupation_cluster_se, row.ci_lower, row.ci_upper,
                     row.bootstrap_p_value, row.mde80)
        maximum_model_difference = max(
            maximum_model_difference,
            max(abs(float(left) - float(right)) for left, right in zip(recomputed, published)))
    checks["model_inference_recomputed"] = maximum_model_difference <= 1e-10

    pair_index = pairs.set_index("pair_id")
    expected_pairs = module.pair_inventory()
    checks["pair_inventory"] = (
        len(pairs) == len(expected_pairs) and
        set(pair_index.index) == {row[0] for row in expected_pairs})
    maximum_pair_difference = 0.0
    for pair_id, _, left, right in expected_pairs:
        row = pair_index.loc[pair_id]
        delta = float(model_index.at[left, "coefficient"] - model_index.at[right, "coefficient"])
        vector = matrix[:, model_names.index(left)] - matrix[:, model_names.index(right)]
        se = float(np.sqrt(vector @ vector))
        if se <= np.finfo(float).eps:
            recomputed = (delta, se, delta, delta, 1.0, 0.0)
        else:
            centered = signs @ vector
            critical = module.higher_quantile(np.abs(centered / se), .95)
            recomputed = (
                delta, se, delta - critical * se, delta + critical * se,
                (1 + np.sum(np.abs(centered / se) >= abs(delta / se))) /
                (len(centered) + 1), module.MDE_FACTOR * se,
            )
        published = (row.coefficient_difference, row.paired_occupation_cluster_se,
                     row.ci_lower, row.ci_upper, row.bootstrap_p_value,
                     row.mde80_difference)
        maximum_pair_difference = max(
            maximum_pair_difference,
            max(abs(float(left_value) - float(right_value))
                for left_value, right_value in zip(recomputed, published)))
    checks["paired_inference_recomputed"] = maximum_pair_difference <= 1e-10

    maximum_simultaneous_difference = 0.0
    for structure in module.STRUCTURES:
        names = [f"onset_{value.replace('-', '_')}_{structure}" for value in module.ONSETS]
        indices = [model_names.index(name) for name in names]
        ses = np.sqrt(np.diag(recomputed_covariance)[indices])
        centered = signs @ matrix[:, indices]
        critical = module.higher_quantile(np.max(np.abs(centered / ses[None, :]), axis=1), .95)
        for name, se in zip(names, ses):
            row = model_index.loc[name]
            estimate = float(row.coefficient)
            maximum_simultaneous_difference = max(
                maximum_simultaneous_difference,
                abs(float(row.simultaneous_onset_critical) - critical),
                abs(float(row.simultaneous_onset_ci_lower) - (estimate - critical * se)),
                abs(float(row.simultaneous_onset_ci_upper) - (estimate + critical * se)),
            )
    checks["onset_simultaneous_recomputed"] = maximum_simultaneous_difference <= 1e-10
    checks["duplicate_definitions"] = all(
        close(model_index.at[left, "coefficient"], model_index.at[right, "coefficient"])
        for structure in module.STRUCTURES
        for left, right in (
            (f"baseline_full_{structure}", f"onset_2023_01_{structure}"),
            (f"endpoint_through_2024_{structure}", f"era_2023_2024_{structure}"),
            (f"onset_2022_12_{structure}", f"onset_2023_01_{structure}"),
        ))
    checks["numerical_certificates"] = (
        len(numerical["models"]) == 34 and
        all(row["audit"]["a1_certification"]["status"] ==
            "PASS_A1_NUMERICAL_CERTIFICATE" for row in numerical["models"]))
    checks["producer_validation"] = (
        producer["status"] == "PASS_TIMING_EXTENSIONS_VALIDATION" and
        all(producer["checks"].values()))
    checks = {key: bool(value) for key, value in checks.items()}
    return {
        "schema_version": "yax-gate2-timing-extensions-independent-validation-v1",
        "status": ("PASS_INDEPENDENT_TIMING_EXTENSIONS_VALIDATION"
                   if all(checks.values()) else "FAIL_INDEPENDENT_TIMING_EXTENSIONS_VALIDATION"),
        "checks": checks,
        "failed": [key for key, value in checks.items() if not value],
        "maximum_absolute_covariance_difference": maximum_covariance_difference,
        "maximum_absolute_model_inference_difference": maximum_model_difference,
        "maximum_absolute_paired_inference_difference": maximum_pair_difference,
        "maximum_absolute_onset_simultaneous_difference": maximum_simultaneous_difference,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.repo_root.resolve(), args.results_dir.resolve())
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "failed": result["failed"]}, sort_keys=True))
    return 0 if not result["failed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
