#!/usr/bin/env python3
"""Independently validate the public S05 broader-support result package."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from typing import Any

import numpy as np
import pandas as pd


HERE = pathlib.Path(__file__).resolve().parent
SPEC_PATH = HERE / "BROADER_SUPPORT_SPEC.json"
PRIMARY_HASH = "11ec58ab1004cd83d62c57785f6c0dd3ee5a8abf08b7f71a3b664e91ded8333b"


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def content_id(prefix: str, value: Any) -> str:
    return f"{prefix}_{hashlib.sha256(canonical_bytes(value)).hexdigest()}"


def support_hash(codes: list[str]) -> str:
    return hashlib.sha256("".join(f"{code}\n" for code in sorted(codes)).encode()).hexdigest()


def reconstructed_groups(values: np.ndarray, cuts: np.ndarray) -> np.ndarray:
    return (np.searchsorted(np.asarray(cuts, float), np.asarray(values, float), side="left") + 1).astype(int)


def boolean_series(values: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(values):
        return values.astype(bool)
    normalized = values.astype(str).str.strip().str.lower()
    if not normalized.isin(["true", "false"]).all():
        raise ValueError("boolean output column contains a non-boolean token")
    return normalized.eq("true")


def validate(repo: pathlib.Path, results: pathlib.Path) -> dict[str, Any]:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    receipt = json.loads((results / "EXECUTION_RECEIPT.json").read_text(encoding="utf-8"))
    manifest = json.loads((results / "RESULT_MANIFEST.json").read_text(encoding="utf-8"))
    validation = json.loads((results / "VALIDATION_REPORT.json").read_text(encoding="utf-8"))
    decomposition = json.loads((results / "SUPPORT_CHANGE_DECOMPOSITION.json").read_text(encoding="utf-8"))
    numerical = json.loads((results / "NUMERICAL_AUDITS.json").read_text(encoding="utf-8"))
    models = pd.read_csv(results / "MODEL_RESULTS.csv")
    pairs = pd.read_csv(results / "SAME_SUPPORT_PAIRED_COMPARISONS.csv")
    members = pd.read_csv(results / "BROADER_SUPPORT_MEMBERSHIP.csv", dtype={"occupation_code": str, "family": str})
    tails = pd.read_csv(results / "DIRECT_TAIL_BY_FAMILY.csv", dtype={"family": str})
    tail_summary = pd.read_csv(results / "DIRECT_TAIL_SUMMARY.csv")

    checks: dict[str, bool] = {}
    checks["runner_spec_hash"] = receipt["spec_sha256"] == sha256(SPEC_PATH)
    checks["runner_hash"] = receipt["runner_sha256"] == sha256(HERE / "run_broader_support.py")
    checks["result_id"] = manifest["result_id"] == content_id(
        "yaxresult_v1", {key: value for key, value in manifest.items() if key != "result_id"}
    )
    receipt_payload = {key: value for key, value in receipt.items() if key != "receipt_id"}
    checks["receipt_id"] = receipt["receipt_id"] == content_id("yaxreceipt_v1", receipt_payload)
    checks["manifest_hash"] = receipt["result_manifest_sha256"] == sha256(results / "RESULT_MANIFEST.json")
    for name, record in manifest["artifacts"].items():
        path = results / name
        checks[f"artifact::{name}"] = path.is_file() and sha256(path) == record["sha256"] and path.stat().st_size == record["bytes"]

    required_models = [row["model_id"] for row in spec["scientific_contract"]["models_in_fixed_order"]]
    checks["model_order"] = models.model_id.tolist() == required_models
    model_map = models.set_index("model_id")
    checks["primary_count"] = int(model_map.at["primary_with_webb", "support_occupations"]) == 468
    checks["primary_support_hash"] = model_map.at["primary_with_webb", "support_hash_sha256"] == PRIMARY_HASH
    checks["broader_counts_equal"] = int(model_map.at["broader_fixed_primary_cuts_without_webb", "support_occupations"]) == int(model_map.at["broader_recomputed_cuts_without_webb", "support_occupations"])

    members["occupation_code"] = members.occupation_code.str.zfill(4)
    broad_codes = members.occupation_code.tolist()
    in_primary = boolean_series(members.in_primary_468)
    primary_codes = members.loc[in_primary, "occupation_code"].tolist()
    checks["membership_broader_hash"] = support_hash(broad_codes) == receipt["broader_support_hash_sha256"]
    checks["membership_primary_hash"] = support_hash(primary_codes) == PRIMARY_HASH
    primary_cuts = np.asarray(spec["scientific_contract"]["primary_support"]["raw_beta_cuts"], float)
    fixed = reconstructed_groups(members.rule_A_beta.to_numpy(float), primary_cuts)
    checks["fixed_cut_labels"] = np.array_equal(fixed, members.broader_fixed_primary_cuts_quintile.to_numpy(int))

    weights = members.preperiod_stock.to_numpy(float)
    values = members.rule_A_beta.to_numpy(float)
    order = np.argsort(values, kind="mergesort")
    cumulative = np.cumsum(weights[order])
    broad_cuts = np.asarray([
        values[order[min(np.searchsorted(cumulative, share * cumulative[-1], side="left"), len(values) - 1)]]
        for share in (0.2, 0.4, 0.6, 0.8)
    ])
    recomputed = reconstructed_groups(values, broad_cuts)
    checks["recomputed_cut_labels"] = np.array_equal(recomputed, members.broader_recomputed_cuts_quintile.to_numpy(int))
    checks["reclassification_count"] = int(np.sum(fixed != recomputed)) == int(decomposition["reclassified_occupations"])
    checks["added_count"] = len(broad_codes) - len(primary_codes) == int(decomposition["additional_occupations"])
    added = ~in_primary.to_numpy()
    checks["added_stock_share"] = np.isclose(weights[added].sum() / weights.sum(), decomposition["additional_preperiod_stock_share_of_broader"], rtol=0, atol=1e-13)

    coefficient = model_map.coefficient.to_dict()
    checks["fixed_cut_support_movement"] = np.isclose(
        coefficient["broader_fixed_primary_cuts_without_webb"] - coefficient["primary_without_webb"],
        decomposition["fixed_cut_support_expansion_coefficient_change"], rtol=0, atol=1e-14,
    )
    checks["reclassification_movement"] = np.isclose(
        coefficient["broader_recomputed_cuts_without_webb"] - coefficient["broader_fixed_primary_cuts_without_webb"],
        decomposition["recomputed_cut_reclassification_coefficient_change"], rtol=0, atol=1e-14,
    )
    pair_map = {(row.left, row.right): row for row in pairs.itertuples(index=False)}
    expected_pairs = [
        ("primary_without_webb", "primary_with_webb"),
        ("broader_recomputed_cuts_without_webb", "broader_fixed_primary_cuts_without_webb"),
    ]
    checks["paired_set"] = set(pair_map) == set(expected_pairs)
    for left, right in expected_pairs:
        row = pair_map[(left, right)]
        checks[f"pair_point::{left}"] = np.isclose(row.coefficient_difference, coefficient[left] - coefficient[right], rtol=0, atol=1e-14)
        checks[f"pair_interval::{left}"] = np.isclose(row.ci_lower, row.coefficient_difference - row.bootstrap_critical * row.paired_bootstrap_se, rtol=0, atol=1e-13) and np.isclose(row.ci_upper, row.coefficient_difference + row.bootstrap_critical * row.paired_bootstrap_se, rtol=0, atol=1e-13)
        checks[f"pair_common_draws::{left}"] = str(row.common_multiplier_draws).strip().lower() == "true"
    checks["support_change_descriptive"] = decomposition["support_change_is_descriptive_not_paired_inference"] is True

    scheme_map = {
        "primary_fixed": in_primary.to_numpy(),
        "broader_fixed_primary_cuts": np.ones(len(members), dtype=bool),
        "broader_recomputed_cuts": np.ones(len(members), dtype=bool),
    }
    group_map = {
        "primary_fixed": members.primary_quintile_if_present,
        "broader_fixed_primary_cuts": members.broader_fixed_primary_cuts_quintile,
        "broader_recomputed_cuts": members.broader_recomputed_cuts_quintile,
    }
    tail_map = tail_summary.set_index("scheme")
    for scheme, mask in scheme_map.items():
        frame = members.loc[mask].copy()
        frame["q"] = pd.to_numeric(group_map[scheme].loc[mask], errors="raise").astype(int).to_numpy()
        spanning = 0
        for _, family in frame.groupby("family", sort=True):
            spanning += int(bool((family.q == 1).any() and (family.q == 5).any()))
        checks[f"direct_tail::{scheme}"] = spanning == int(tail_map.at[scheme, "direct_tail_spanning_families"])
        retained = tails.loc[tails.scheme.eq(scheme)]
        checks[f"direct_tail_rows::{scheme}"] = int(boolean_series(retained.direct_q5_q1_supported).sum()) == spanning

    thresholds = spec["numerical_validation"]["thresholds"]
    checks["four_numerical_audits"] = len(numerical["models"]) == 4 and numerical["all_pass"] is True
    for row in numerical["models"]:
        checks[f"numerical_status::{row['model_id']}"] = row["status"] == "PASS_SAME_OBJECTIVE_NUMERICAL_CERTIFICATION"
        checks[f"numerical_candidate_reference::{row['model_id']}"] = row["scientific_engine_reference_maximum_absolute_difference"] <= thresholds["full_treatment_vector_maximum_absolute_difference"]
        checks[f"numerical_trust_reference::{row['model_id']}"] = row["trust_reference_treatment_maximum_absolute_difference"] <= thresholds["full_treatment_vector_maximum_absolute_difference"]
        checks[f"numerical_probability::{row['model_id']}"] = row["trust_reference_fitted_probability_maximum_absolute_difference"] <= thresholds["fitted_probability_maximum_absolute_difference"]
        checks[f"numerical_objective::{row['model_id']}"] = row["trust_reference_objective_difference_per_total"] <= thresholds["objective_per_total_difference"]

    checks["producer_validation"] = validation["status"] == "PASS_S05_BROADER_SUPPORT_VALIDATION" and all(validation["checks"].values())
    checks["privacy"] = receipt["protected_cells_published"] is False and receipt["row_microdata_published"] is False
    passed = all(checks.values())
    return {
        "schema_version": "yax-gate2-broader-support-independent-validation-v1",
        "status": "PASS_INDEPENDENT_S05_VALIDATION" if passed else "BLOCKED_INDEPENDENT_S05_VALIDATION",
        "result_id": receipt["result_id"],
        "checks": checks,
        "maximum_historical_checkpoint_gap": max(abs(float(value)) for value in decomposition["historical_checkpoint_coefficient_gaps"].values()),
        "broad_raw_cuts_recomputed": broad_cuts.tolist(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=pathlib.Path, required=True)
    parser.add_argument("--results-dir", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    report = validate(args.repo_root.resolve(), args.results_dir.resolve())
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": len(report["checks"]), "failed": [key for key, value in report["checks"].items() if not value]}, indent=2, sort_keys=True))
    if not report["status"].startswith("PASS_"):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
