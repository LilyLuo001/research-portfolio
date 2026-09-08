#!/usr/bin/env python3
"""Independently validate the retained Gate 2 support-inference publication."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy.stats import chi2, norm


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[4]
V3 = REPO_ROOT / "yax/revision/substantive_v3_20260906"
DEFAULT_RUN = V3 / "runs/gate2_support_inference_authoritative_20260908"
EXPECTED_MODELS = {
    "pooled",
    "family_month",
    "family_heterogeneous_supported",
    "direct_tail_four_family",
    "continuous_raw_beta_family_month",
}
EXPECTED_REQUIREMENTS = {"S03", "S04", "S06", "S07"}
EXPECTED_VALIDATION_CHECK_COUNT = 26


class SupportResultValidationError(RuntimeError):
    """The retained support-inference result failed an independent check."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SupportResultValidationError(message)


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"{path.name} is not a JSON object")
    return value


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _content_id(prefix: str, value: dict[str, Any], excluded: Iterable[str]) -> str:
    omitted = set(excluded)
    payload = {key: item for key, item in value.items() if key not in omitted}
    return f"{prefix}_{hashlib.sha256(_canonical_bytes(payload)).hexdigest()}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _long_matrix(frame: pd.DataFrame, kind: str, labels: list[str]) -> np.ndarray:
    selected = frame.loc[frame["matrix_kind"].eq(kind)]
    _require(len(selected) == len(labels) ** 2, f"{kind} covariance row count differs")
    pivot = selected.pivot(index="row_target", columns="column_target", values="value")
    _require(set(pivot.index) == set(labels), f"{kind} covariance row labels differ")
    _require(set(pivot.columns) == set(labels), f"{kind} covariance column labels differ")
    return pivot.loc[labels, labels].to_numpy(float)


def _maximum(values: list[float]) -> float:
    return float(max(values, default=0.0))


def validate(run_dir: Path = DEFAULT_RUN) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    _require(run_dir.is_dir(), "authoritative Gate 2 run directory is absent")
    entries = list(run_dir.iterdir())
    _require(
        all(path.is_file() and not path.is_symlink() for path in entries),
        "run directory contains a non-regular entry",
    )

    manifest = _load_json(run_dir / "RESULT_MANIFEST.json")
    receipt = _load_json(run_dir / "EXECUTION_RECEIPT.json")
    validation = _load_json(run_dir / "VALIDATION_REPORT.json")
    catalog = _load_json(run_dir / "MODEL_CATALOG.json")

    records = manifest.get("artifacts")
    _require(isinstance(records, list) and len(records) == 40, "manifest must contain 40 artifacts")
    filenames = [record.get("filename") for record in records]
    _require(len(filenames) == len(set(filenames)), "manifest contains duplicate filenames")
    expected_inventory = set(filenames) | {"RESULT_MANIFEST.json", "EXECUTION_RECEIPT.json"}
    _require({path.name for path in entries} == expected_inventory, "run inventory differs from manifest")

    artifact_identity_checks = 0
    for record in records:
        path = run_dir / str(record["filename"])
        _require(path.stat().st_size == record.get("byte_count"), f"byte count differs: {path.name}")
        _require(_sha256(path) == record.get("sha256"), f"SHA-256 differs: {path.name}")
        _require(
            record.get("result_id") == _content_id("yaxartifact_v1", record, ("result_id",)),
            f"artifact content ID differs: {path.name}",
        )
        artifact_identity_checks += 1

    expected_result_id = _content_id("yaxresult_v1", manifest, ("result_id",))
    _require(manifest.get("result_id") == expected_result_id, "manifest result ID differs")
    _require(receipt.get("result_id") == expected_result_id, "receipt result ID differs")
    _require(receipt.get("artifact_count") == len(records), "receipt artifact count differs")
    _require(receipt.get("scientific_result_claims") is True, "receipt is not a result publication")
    _require(
        receipt.get("status") == "CERTIFIED_ARTIFACT_PUBLICATION_WITH_EXPECTED_STRUCTURAL_RANK_BLOCK",
        "receipt status differs",
    )
    manifest_record = receipt.get("result_manifest", {})
    manifest_path = run_dir / "RESULT_MANIFEST.json"
    _require(manifest_record.get("sha256") == _sha256(manifest_path), "receipt manifest hash differs")
    _require(manifest_record.get("byte_count") == manifest_path.stat().st_size, "manifest byte count differs")
    _require(
        manifest_record.get("result_id")
        == _content_id("yaxartifact_v1", manifest_record, ("result_id",)),
        "manifest artifact content ID differs",
    )
    expected_receipt_id = _content_id("yaxreceipt_v1", receipt, ("receipt_id",))
    _require(receipt.get("receipt_id") == expected_receipt_id, "receipt content ID differs")

    checks = validation.get("checks", {})
    _require(validation.get("status") == "PASS_RECOMPUTED_VALIDATION", "validation did not pass")
    _require(validation.get("failed_checks") == [], "validation has failed checks")
    _require(len(checks) == EXPECTED_VALIDATION_CHECK_COUNT, "validation check count differs")
    _require(all(item.get("pass") is True for item in checks.values()), "a validation check did not pass")
    scope = validation.get("requirement_scope", {})
    _require(EXPECTED_REQUIREMENTS <= set(scope), "required Gate 2 result scope is incomplete")
    _require(scope.get("S05") == "UNRESOLVED_OUT_OF_SCOPE", "S05 was incorrectly claimed")

    models = catalog.get("models", [])
    _require({model.get("model_id") for model in models} == EXPECTED_MODELS, "model inventory differs")
    _require(
        all(model.get("a1_certificate", {}).get("status") == "PASS_A1_NUMERICAL_CERTIFICATE"
            for model in models),
        "not all required models have passing A1 certificates",
    )

    profile = pd.read_csv(run_dir / "PROFILE_ESTIMATES.csv")
    intervals = pd.read_csv(run_dir / "PROFILE_INTERVALS.csv")
    covariance_rows = pd.read_csv(run_dir / "PROFILE_COVARIANCE.csv")
    joint = _load_json(run_dir / "PROFILE_JOINT_TESTS.json")
    draws = np.load(run_dir / "CENTERED_TARGET_DRAWS.npz", allow_pickle=False)
    labels = [f"Q{q}_x_post" for q in range(2, 6)]
    delta_labels = [f"delta_Q{q}" for q in range(2, 6)]
    model_labels = {"pooled": labels, "family_month": labels,
                    "family_month_minus_pooled": delta_labels}
    draw_keys = {"pooled": "pooled_Q2_Q5", "family_month": "family_month_Q2_Q5",
                 "family_month_minus_pooled": "paired_Q2_Q5"}
    covariance_kinds = {"pooled": "pooled", "family_month": "family_month",
                        "family_month_minus_pooled": "family_month_minus_pooled"}

    pooled = profile.loc[profile["model_id"].eq("pooled")].set_index("target").loc[labels]
    family = profile.loc[profile["model_id"].eq("family_month")].set_index("target").loc[labels]
    paired = profile.loc[profile["model_id"].eq("family_month_minus_pooled")].set_index("target").loc[delta_labels]
    paired_identity = np.max(np.abs(
        paired["estimate"].to_numpy(float)
        - (family["estimate"].to_numpy(float) - pooled["estimate"].to_numpy(float))
    ))
    draw_identity = np.max(np.abs(
        draws["paired_Q2_Q5"] - (draws["family_month_Q2_Q5"] - draws["pooled_Q2_Q5"])
    ))

    se_residuals: list[float] = []
    pointwise_residuals: list[float] = []
    simultaneous_residuals: list[float] = []
    joint_statistic_residuals: list[float] = []
    joint_p_residuals: list[float] = []
    multiplier_p_residuals: list[float] = []
    critical_residuals: list[float] = []
    z975 = float(norm.ppf(0.975))
    for model_id, target_labels in model_labels.items():
        estimates = (
            profile.loc[profile["model_id"].eq(model_id)]
            .set_index("target").loc[target_labels, "estimate"].to_numpy(float)
        )
        covariance = _long_matrix(covariance_rows, covariance_kinds[model_id], target_labels)
        standard_errors = np.sqrt(np.diag(covariance))
        published = profile.loc[profile["model_id"].eq(model_id)].set_index("target").loc[target_labels]
        se_residuals.append(float(np.max(np.abs(standard_errors - published["standard_error"]))))
        published_intervals = intervals.loc[intervals["model_id"].eq(model_id)].set_index("target").loc[target_labels]
        pointwise_residuals.extend([
            float(np.max(np.abs(estimates - z975 * standard_errors - published_intervals["pointwise_lower"]))),
            float(np.max(np.abs(estimates + z975 * standard_errors - published_intervals["pointwise_upper"]))),
        ])
        centered_draws = draws[draw_keys[model_id]]
        critical = float(np.quantile(
            np.max(np.abs(centered_draws / standard_errors), axis=1), 0.95, method="higher"
        ))
        critical_residuals.append(abs(critical - float(published_intervals["simultaneous_critical_value"].iloc[0])))
        simultaneous_residuals.extend([
            float(np.max(np.abs(estimates - critical * standard_errors - published_intervals["simultaneous_lower"]))),
            float(np.max(np.abs(estimates + critical * standard_errors - published_intervals["simultaneous_upper"]))),
        ])
        joint_key = "paired_movement" if model_id == "family_month_minus_pooled" else model_id
        published_joint = joint[joint_key]
        statistic = float(estimates @ np.linalg.solve(covariance, estimates))
        p_chi2 = float(chi2.sf(statistic, len(estimates)))
        inverse = np.linalg.inv(covariance)
        bootstrap = np.einsum("bi,ij,bj->b", centered_draws, inverse, centered_draws)
        p_multiplier = float((1 + np.sum(bootstrap >= statistic)) / (len(bootstrap) + 1))
        joint_statistic_residuals.append(abs(statistic - float(published_joint["chi2"])))
        joint_p_residuals.append(abs(p_chi2 - float(published_joint["p_value_chi2"])))
        multiplier_p_residuals.append(abs(p_multiplier - float(published_joint["p_value_multiplier"])))

    def covariance_se_check(estimate_file: str, covariance_file: str, kind: str,
                            label_column: str) -> float:
        estimates = pd.read_csv(run_dir / estimate_file)
        labels_local = estimates[label_column].astype(str).tolist()
        covariance = _long_matrix(pd.read_csv(run_dir / covariance_file), kind, labels_local)
        return float(np.max(np.abs(
            estimates["standard_error"].to_numpy(float) - np.sqrt(np.diag(covariance))
        )))

    edge_se_residual = covariance_se_check(
        "SUPPORTED_PAIRWISE_CONTRASTS.csv", "SUPPORTED_EDGE_COVARIANCE.csv",
        "supported_edges", "functional_label",
    )
    pair_se_residual = covariance_se_check(
        "PAIRWISE_AGGREGATES.csv", "PAIRWISE_AGGREGATE_COVARIANCE.csv",
        "pairwise_aggregates", "functional_label",
    )
    direct = pd.read_csv(run_dir / "DIRECT_TAIL_ESTIMATES.csv")
    direct_labels = [
        f"family_{str(value).zfill(2)}:Q5_vs_Q1" if value != "PRE_STOCK_AGGREGATE"
        else "fixed_pre_stock_aggregate"
        for value in direct["family"].astype(str)
    ]
    direct_covariance = _long_matrix(
        pd.read_csv(run_dir / "DIRECT_TAIL_COVARIANCE.csv"),
        "direct_tail_functionals", direct_labels,
    )
    direct_se_residual = float(np.max(np.abs(
        direct["standard_error"].to_numpy(float) - np.sqrt(np.diag(direct_covariance))
    )))

    failures = _load_json(run_dir / "MODEL_FAILURES.json")
    block = failures.get("blocked_components", [{}])[0]
    _require(failures.get("numerical_fit_status") == "ALL_REQUIRED_A1_CERTIFICATES_PASS",
             "numerical fit status differs")
    _require(block.get("disposition") == "EXPECTED_STRUCTURAL_RANK_BLOCK",
             "expected supported-edge rank block is absent")
    _require(block.get("chi2_or_p_value_emitted") is False,
             "rank-deficient edge test incorrectly emitted inference")

    tolerances = {
        "identity": 1e-14,
        "published_numeric_reconstruction": 1e-12,
    }
    numeric_checks = {
        "paired_point_estimate_identity_max_abs": float(paired_identity),
        "paired_common_draw_identity_max_abs": float(draw_identity),
        "profile_standard_error_max_abs": _maximum(se_residuals),
        "profile_pointwise_interval_max_abs": _maximum(pointwise_residuals),
        "profile_simultaneous_interval_max_abs": _maximum(simultaneous_residuals),
        "profile_simultaneous_critical_value_max_abs": _maximum(critical_residuals),
        "profile_joint_statistic_max_abs": _maximum(joint_statistic_residuals),
        "profile_joint_chi2_p_value_max_abs": _maximum(joint_p_residuals),
        "profile_joint_multiplier_p_value_max_abs": _maximum(multiplier_p_residuals),
        "supported_edge_standard_error_max_abs": edge_se_residual,
        "pairwise_aggregate_standard_error_max_abs": pair_se_residual,
        "direct_tail_standard_error_max_abs": direct_se_residual,
    }
    _require(numeric_checks["paired_point_estimate_identity_max_abs"] <= tolerances["identity"],
             "paired point-estimate identity failed")
    _require(numeric_checks["paired_common_draw_identity_max_abs"] <= tolerances["identity"],
             "paired common-draw identity failed")
    for key, value in numeric_checks.items():
        if key not in {"paired_point_estimate_identity_max_abs", "paired_common_draw_identity_max_abs"}:
            _require(value <= tolerances["published_numeric_reconstruction"],
                     f"published numeric reconstruction failed: {key}")

    return {
        "schema_version": "yax-gate2-support-inference-postrun-validation-v1",
        "status": "PASS_AUTHORITATIVE_RESULT_AND_PUBLIC_NUMERIC_RECONSTRUCTION_NOT_PRESENTATION",
        "run_directory": str(run_dir.relative_to(V3)),
        "result_id": expected_result_id,
        "receipt_id": expected_receipt_id,
        "inventory": {
            "total_files": len(entries),
            "manifest_artifacts": len(records),
            "artifact_hash_and_id_checks": artifact_identity_checks,
        },
        "producer_validation": {
            "status": validation["status"],
            "passing_check_count": len(checks),
            "failed_checks": validation["failed_checks"],
        },
        "model_certificates": {
            "model_count": len(models),
            "models": sorted(EXPECTED_MODELS),
            "status": "ALL_REQUIRED_A1_CERTIFICATES_PASS",
        },
        "numeric_reconstruction": numeric_checks,
        "tolerances": tolerances,
        "expected_structural_rank_block": {
            "restriction_count": block["restriction_count"],
            "covariance_rank": block["covariance_rank"],
            "chi2_or_p_value_emitted": block["chi2_or_p_value_emitted"],
            "status": block["disposition"],
        },
        "scope": {
            "run_evidence_present": sorted(EXPECTED_REQUIREMENTS),
            "S05": "UNRESOLVED_OUT_OF_SCOPE",
            "presentation_validation": "NOT_YET_PERFORMED",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN)
    args = parser.parse_args()
    print(json.dumps(validate(args.run_dir), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
