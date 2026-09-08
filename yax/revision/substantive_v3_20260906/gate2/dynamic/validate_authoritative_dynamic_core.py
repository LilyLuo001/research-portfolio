#!/usr/bin/env python3
"""Independently recompute the public Gate 2 dynamic-core result artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd
from scipy.stats import chi2, norm


CORE_OUTPUTS = {
    "MODEL_CATALOG.json", "RECONCILIATION_ESTIMATES.csv",
    "RECONCILIATION_COVARIANCE.csv", "DYNAMIC_COEFFICIENTS.csv",
    "DYNAMIC_COVARIANCE.csv", "DYNAMIC_INFLUENCE.csv",
    "DYNAMIC_Q5_EVENT_STUDY.csv", "DYNAMIC_Q5_CENTERED_DRAWS.npz",
    "PRETREND_TESTS.csv", "PRETREND_DIAGNOSTICS.csv",
    "REPARAMETERIZATION_AUDIT.json", "NESTING_PROJECTION_AUDIT.json",
    "NUMERICAL_MODEL_AUDITS.json", "VALIDATION_REPORT.json",
}
STRUCTURES = {
    "unconditioned": ("pooled", "dynamics_unconditioned"),
    "family_month": ("family_month", "dynamics_family_month"),
}
REFERENCE = "2022Q4"


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def content_id(prefix: str, value: dict[str, Any], excluded: Sequence[str]) -> str:
    payload = {key: item for key, item in value.items() if key not in set(excluded)}
    return f"{prefix}_{hashlib.sha256(canonical_bytes(payload)).hexdigest()}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path.name} is not a JSON object")
    return value


def maximum_difference(left: np.ndarray, right: np.ndarray) -> float:
    require(left.shape == right.shape, "comparison shapes differ")
    return float(np.max(np.abs(left - right), initial=0.0))


def verify_manifest(run_dir: Path, spec: dict[str, Any]) -> dict[str, Any]:
    observed = {path.name for path in run_dir.iterdir() if path.is_file()}
    expected = CORE_OUTPUTS | {"RESULT_MANIFEST.json", "EXECUTION_RECEIPT.json"}
    require(observed == expected, "result file inventory differs")
    manifest = load_json(run_dir / "RESULT_MANIFEST.json")
    receipt = load_json(run_dir / "EXECUTION_RECEIPT.json")
    require(manifest.get("spec_id") == spec["spec_id"], "manifest spec differs")
    require(receipt.get("spec_id") == spec["spec_id"], "receipt spec differs")
    require(receipt.get("result_id") == manifest.get("result_id"),
            "receipt and manifest result identities differ")
    records = manifest.get("artifacts", [])
    require({row.get("filename") for row in records} == CORE_OUTPUTS,
            "manifest artifact inventory differs")
    for row in records:
        path = run_dir / row["filename"]
        require(row.get("sha256") == sha256_file(path),
                f"artifact hash differs: {path.name}")
        require(row.get("byte_count") == path.stat().st_size,
                f"artifact byte count differs: {path.name}")
        require(row.get("result_id") == content_id(
            "yaxartifact_v1", row, ("result_id",)),
            f"artifact content identity differs: {path.name}")
    require(manifest.get("result_id") == content_id(
        "yaxresult_v1", manifest, ("result_id",)), "manifest result ID differs")
    manifest_record = receipt.get("result_manifest", {})
    require(manifest_record.get("sha256") == sha256_file(run_dir / "RESULT_MANIFEST.json"),
            "receipt manifest hash differs")
    require(receipt.get("receipt_id") == content_id(
        "yaxreceipt_v1", receipt, ("receipt_id",)), "receipt ID differs")
    require(receipt.get("protected_objects_published") is False,
            "receipt does not prohibit protected publication")
    return {
        "result_id": manifest["result_id"], "receipt_id": receipt["receipt_id"],
        "artifact_count": len(records),
    }


def calendar_weights(parent_spec: dict[str, Any]) -> tuple[list[str], dict[str, float], dict[str, float]]:
    calendar = parent_spec["calendar"]
    months = pd.period_range(*calendar["observed_window"], freq="M").astype(str).tolist()
    months = [month for month in months if month not in calendar["missing_months"]]
    fit = [month for month in months if month != calendar["transition_month"]]
    pre = [month for month in fit if month <= calendar["preperiod"][1]]
    post = [month for month in fit if month >= calendar["postperiod"][0]]

    def quarter(month: str) -> str:
        return f"{month[:4]}Q{(int(month[5:7]) - 1) // 3 + 1}"

    quarters = sorted({quarter(month) for month in fit})
    pre_weights = {period: sum(quarter(month) == period for month in pre) / len(pre)
                   for period in quarters}
    post_weights = {period: sum(quarter(month) == period for month in post) / len(post)
                    for period in quarters}
    return quarters, pre_weights, post_weights


def static_objects(support_dir: Path) -> dict[str, tuple[float, list[str], np.ndarray]]:
    estimates = pd.read_csv(support_dir / "PROFILE_ESTIMATES.csv")
    influence = pd.read_csv(
        support_dir / "OCCUPATION_INFLUENCE.csv",
        dtype={"occupation_code": str},
    )
    output = {}
    for model_id in ("pooled", "family_month"):
        estimate_row = estimates.loc[
            estimates.model_id.eq(model_id) & estimates.target.eq("Q5_x_post")
        ]
        require(len(estimate_row) == 1, f"static Q5 estimate missing: {model_id}")
        rows = influence.loc[
            influence.model_id.eq(model_id) & influence.target.eq("Q5_x_post")
        ].sort_values("occupation_code", kind="mergesort")
        require(len(rows) == 468, f"static Q5 influence count differs: {model_id}")
        codes = rows.occupation_code.tolist()
        scaled = math.sqrt(len(rows) / (len(rows) - 1)) * rows.raw_influence.to_numpy(float)
        output[model_id] = (float(estimate_row.iloc[0].estimate), codes, scaled)
    return output


def dynamic_objects(run_dir: Path) -> dict[str, dict[str, Any]]:
    coefficients = pd.read_csv(run_dir / "DYNAMIC_COEFFICIENTS.csv")
    influence = pd.read_csv(
        run_dir / "DYNAMIC_INFLUENCE.csv", dtype={"occupation_code": str},
    )
    output: dict[str, dict[str, Any]] = {}
    for structure, (_, model_id) in STRUCTURES.items():
        beta_rows = coefficients.loc[
            coefficients.structure.eq(structure) & coefficients.model_id.eq(model_id)
        ]
        require(len(beta_rows) == 190, f"dynamic coefficient count differs: {structure}")
        labels = beta_rows.coefficient_label.tolist()
        require(len(labels) == len(set(labels)), f"dynamic labels duplicate: {structure}")
        beta = beta_rows.estimate.to_numpy(float)
        subset = influence.loc[
            influence.structure.eq(structure) & influence.model_id.eq(model_id)
        ]
        pivot = subset.pivot(index="occupation_code", columns="coefficient_label",
                            values="scaled_influence").sort_index()
        require(pivot.shape == (468, 190), f"dynamic influence dimensions differ: {structure}")
        require(set(pivot.columns) == set(labels), f"dynamic influence labels differ: {structure}")
        output[structure] = {
            "model_id": model_id, "labels": labels, "beta": beta,
            "codes": pivot.index.tolist(), "influence": pivot[labels].to_numpy(float),
        }
    return output


def target(beta: np.ndarray, influence: np.ndarray, weights: np.ndarray) -> tuple[float, np.ndarray]:
    return float(weights @ beta), influence @ weights


def add(left: tuple[float, np.ndarray], right: tuple[float, np.ndarray], sign: float = 1.0):
    return left[0] + sign * right[0], left[1] + sign * right[1]


def reconstruct_reconciliation(
    static: dict[str, tuple[float, list[str], np.ndarray]],
    dynamic: dict[str, dict[str, Any]],
    parent_spec: dict[str, Any],
) -> dict[str, tuple[float, np.ndarray]]:
    _, pre, post = calendar_weights(parent_spec)
    objects: dict[str, tuple[float, np.ndarray]] = {}
    for structure, (static_id, _) in STRUCTURES.items():
        dynamic_row = dynamic[structure]
        static_estimate, static_codes, static_influence = static[static_id]
        require(static_codes == dynamic_row["codes"],
                f"static/dynamic occupation order differs: {structure}")
        labels = dynamic_row["labels"]
        post_vector = np.array([
            post.get(label.rsplit("_", 1)[1], 0.0) if label.startswith("Q5_x_") else 0.0
            for label in labels
        ])
        difference_vector = np.array([
            post.get(label.rsplit("_", 1)[1], 0.0)
            - pre.get(label.rsplit("_", 1)[1], 0.0)
            if label.startswith("Q5_x_") else 0.0
            for label in labels
        ])
        s = (static_estimate, static_influence)
        p = target(dynamic_row["beta"], dynamic_row["influence"], post_vector)
        d = target(dynamic_row["beta"], dynamic_row["influence"], difference_vector)
        objects[f"{structure}::S"] = s
        objects[f"{structure}::P"] = p
        objects[f"{structure}::D"] = d
        objects[f"{structure}::P_minus_S"] = add(p, s, -1)
        objects[f"{structure}::D_minus_S"] = add(d, s, -1)
        objects[f"{structure}::P_minus_D"] = add(p, d, -1)
    for name in ("S", "P", "D", "P_minus_S", "D_minus_S", "P_minus_D"):
        objects[f"conditioning_family_month_minus_unconditioned::{name}"] = add(
            objects[f"family_month::{name}"], objects[f"unconditioned::{name}"], -1
        )
    return objects


def verify_reconciliation(run_dir: Path, objects: dict[str, tuple[float, np.ndarray]]) -> dict[str, float]:
    estimates = pd.read_csv(run_dir / "RECONCILIATION_ESTIMATES.csv").set_index("target")
    labels = list(objects)
    require(estimates.index.tolist() == labels, "reconciliation target order differs")
    observed_estimate = estimates.loc[labels, "estimate"].to_numpy(float)
    observed_se = estimates.loc[labels, "standard_error"].to_numpy(float)
    expected_estimate = np.array([objects[label][0] for label in labels])
    matrix = np.vstack([objects[label][1] for label in labels])
    expected_covariance = matrix @ matrix.T
    expected_se = np.sqrt(np.diag(expected_covariance))
    covariance_rows = pd.read_csv(run_dir / "RECONCILIATION_COVARIANCE.csv")
    observed_covariance = covariance_rows.pivot(
        index="row_target", columns="column_target", values="value"
    ).loc[labels, labels].to_numpy(float)
    differences = {
        "estimate": maximum_difference(observed_estimate, expected_estimate),
        "standard_error": maximum_difference(observed_se, expected_se),
        "covariance": maximum_difference(observed_covariance, expected_covariance),
    }
    require(max(differences.values()) <= 2e-12,
            "reconciliation estimate or covariance did not reproduce")
    return differences


def simultaneous(beta: np.ndarray, influence: np.ndarray, xi: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
    se = np.sqrt(np.diag(influence.T @ influence))
    maxima = np.max(np.abs((xi @ influence) / se[None, :]), axis=1)
    index = int(math.ceil((len(maxima) - 1) * .95))
    critical = float(np.sort(maxima)[index])
    return critical, beta - critical * se, beta + critical * se


def wald(beta: np.ndarray, influence: np.ndarray, restrictions: np.ndarray,
         xi: np.ndarray, eigen_tolerance: float, range_tolerance: float) -> dict[str, float]:
    target_value = restrictions @ beta
    covariance = restrictions @ (influence.T @ influence) @ restrictions.T
    covariance = .5 * (covariance + covariance.T)
    values, vectors = np.linalg.eigh(covariance)
    cutoff = eigen_tolerance * float(np.max(np.abs(values)))
    keep = values > cutoff
    null = vectors[:, ~keep] @ (vectors[:, ~keep].T @ target_value)
    scale = max(float(np.linalg.norm(target_value)), math.sqrt(max(0.0, values[-1])),
                np.finfo(float).tiny)
    require(float(np.linalg.norm(null)) / scale <= range_tolerance,
            "recomputed target is outside covariance range")
    statistic = float(np.sum(np.square(vectors[:, keep].T @ target_value) / values[keep]))
    bootstrap = np.sum(np.square((xi @ influence @ restrictions.T) @ vectors[:, keep])
                       / values[keep], axis=1)
    rank = int(np.sum(keep))
    return {
        "statistic": statistic, "rank": rank,
        "p_chi2": float(chi2.sf(statistic, rank)),
        "p_multiplier": float((1 + np.sum(bootstrap >= statistic)) / (len(xi) + 1)),
    }


def restriction(labels: list[str], selected: list[str], within: bool) -> np.ndarray:
    positions = {label: index for index, label in enumerate(labels)}
    if not within:
        result = np.zeros((len(selected), len(labels)))
        for row, label in enumerate(selected):
            result[row, positions[label]] = 1.0
        return result
    result = np.zeros((len(selected) - 1, len(labels)))
    for row, label in enumerate(selected[1:]):
        result[row, positions[label]] = 1.0
        result[row, positions[selected[0]]] = -1.0
    return result


def verify_event_and_pretrend(
    run_dir: Path, dynamic: dict[str, dict[str, Any]], parent_spec: dict[str, Any],
    xi: np.ndarray,
) -> dict[str, float]:
    event = pd.read_csv(run_dir / "DYNAMIC_Q5_EVENT_STUDY.csv")
    tests = pd.read_csv(run_dir / "PRETREND_TESTS.csv")
    diagnostic = pd.read_csv(run_dir / "PRETREND_DIAGNOSTICS.csv")
    quarters, _, _ = calendar_weights(parent_spec)
    free = [period for period in quarters if period != REFERENCE]
    pre = [period for period in quarters if period < REFERENCE]
    maxima = {"event": 0.0, "pretrend": 0.0, "diagnostic": 0.0}
    for structure, row in dynamic.items():
        positions = {label: index for index, label in enumerate(row["labels"])}
        selected = [positions[f"Q5_x_{period}"] for period in free]
        beta = row["beta"][selected]
        influence = row["influence"][:, selected]
        covariance = influence.T @ influence
        se = np.sqrt(np.diag(covariance))
        full_critical, full_lower, full_upper = simultaneous(beta, influence, xi)
        pre_positions = [free.index(period) for period in pre]
        pre_beta = beta[pre_positions]
        pre_influence = influence[:, pre_positions]
        pre_critical, pre_lower, pre_upper = simultaneous(pre_beta, pre_influence, xi)
        observed = event.loc[event.structure.eq(structure)].set_index("quarter").loc[quarters]
        for period in quarters:
            if period == REFERENCE:
                expected = np.zeros(7)
            else:
                index = free.index(period)
                point = float(norm.ppf(.975)) * se[index]
                if period in pre:
                    pre_index = pre.index(period)
                    pre_values = (pre_lower[pre_index], pre_upper[pre_index])
                else:
                    pre_values = (np.nan, np.nan)
                expected = np.array([
                    beta[index], se[index], beta[index] - point, beta[index] + point,
                    full_lower[index], full_upper[index], *pre_values,
                ])
                observed_values = observed.loc[period, [
                    "estimate", "standard_error", "pointwise_lower", "pointwise_upper",
                    "simultaneous_full_lower", "simultaneous_full_upper",
                    "simultaneous_pre_lower", "simultaneous_pre_upper",
                ]].to_numpy(float)
                finite = np.isfinite(expected)
                maxima["event"] = max(
                    maxima["event"], maximum_difference(observed_values[finite], expected[finite])
                )
                continue
            observed_values = observed.loc[period, [
                "estimate", "standard_error", "pointwise_lower", "pointwise_upper",
                "simultaneous_full_lower", "simultaneous_full_upper",
                "simultaneous_pre_lower",
            ]].to_numpy(float)
            maxima["event"] = max(maxima["event"], maximum_difference(observed_values, expected))
        require(maximum_difference(
            observed.simultaneous_full_critical.to_numpy(float),
            np.repeat(full_critical, len(observed)),
        ) <= 2e-12, "full simultaneous critical differs")
        require(maximum_difference(
            observed.simultaneous_pre_critical.to_numpy(float),
            np.repeat(pre_critical, len(observed)),
        ) <= 2e-12, "pre simultaneous critical differs")

        tolerances = parent_spec["tolerances"]
        windows = parent_spec["pretrend"]["windows"]
        for window, definition in windows.items():
            selected_quarters = [period for period in pre
                                 if definition["span"][0] <= period <= definition["span"][1]
                                 and period not in definition["excluded_quarters"]]
            for null, within in (("equality_to_original_2022Q4_reference", False),
                                 ("equality_within_selected_block", True)):
                matrix = restriction(pre, selected_quarters, within)
                expected = wald(
                    pre_beta, pre_influence, matrix, xi,
                    tolerances["conditioning_rank_relative"],
                    tolerances["target_range_relative"],
                )
                observed_test = tests.loc[
                    tests.structure.eq(structure) & tests.window.eq(window)
                    & tests["null"].eq(null)
                ]
                require(len(observed_test) == 1, "pretrend test row is missing")
                observed_test = observed_test.iloc[0]
                differences = np.abs(np.array([
                    observed_test.wald_statistic - expected["statistic"],
                    observed_test.p_value_chi2 - expected["p_chi2"],
                    observed_test.p_value_multiplier - expected["p_multiplier"],
                ]))
                maxima["pretrend"] = max(maxima["pretrend"], float(differences.max()))
                require(int(observed_test.degrees_of_freedom) == expected["rank"],
                        "pretrend degrees of freedom differ")

        for null, within in (("full_preperiod_equality_to_reference", False),
                             ("full_preperiod_equality_within_block", True)):
            full = wald(pre_beta, pre_influence, restriction(pre, pre, within), xi,
                        tolerances["conditioning_rank_relative"],
                        tolerances["target_range_relative"])
            for omitted in pre:
                remaining = [period for period in pre if period != omitted]
                expected = wald(pre_beta, pre_influence, restriction(pre, remaining, within), xi,
                                tolerances["conditioning_rank_relative"],
                                tolerances["target_range_relative"])
                observed_row = diagnostic.loc[
                    diagnostic.structure.eq(structure)
                    & diagnostic.diagnostic.eq("leave_one_quarter_out")
                    & diagnostic.contrast.eq(null)
                    & diagnostic.omitted_quarter.eq(omitted)
                ]
                require(len(observed_row) == 1, "leave-one-quarter row is missing")
                observed_row = observed_row.iloc[0]
                values = np.array([
                    observed_row.wald_statistic - expected["statistic"],
                    observed_row.p_value_multiplier - expected["p_multiplier"],
                    observed_row.full_wald_statistic - full["statistic"],
                    observed_row.wald_change_not_additive_contribution
                    - (expected["statistic"] - full["statistic"]),
                ])
                maxima["diagnostic"] = max(maxima["diagnostic"],
                                             float(np.max(np.abs(values))))

        times = np.arange(len(pre), dtype=float)
        centered = times - times.mean()
        contrasts = {
            "persistent_level": np.repeat(1 / len(pre), len(pre)),
            "equal_elapsed_quarter_linear_drift": centered / float(centered @ centered),
        }
        for quarter in (2, 3, 4):
            q1 = np.array([period.endswith("Q1") for period in pre], float)
            target_q = np.array([period.endswith(f"Q{quarter}") for period in pre], float)
            contrasts[f"Q{quarter}_minus_Q1_mean"] = target_q / target_q.sum() - q1 / q1.sum()
        for name, contrast in contrasts.items():
            estimate = float(contrast @ pre_beta)
            influence_value = pre_influence @ contrast
            standard_error = float(np.linalg.norm(influence_value))
            z = estimate / standard_error
            multiplier_p = float((1 + np.sum(np.abs(xi @ influence_value / standard_error)
                                             >= abs(z))) / (len(xi) + 1))
            observed_row = diagnostic.loc[
                diagnostic.structure.eq(structure)
                & diagnostic.diagnostic.eq("linear_contrast")
                & diagnostic.contrast.eq(name)
            ]
            require(len(observed_row) == 1, "linear pretrend diagnostic is missing")
            observed_row = observed_row.iloc[0]
            values = np.array([
                observed_row.estimate - estimate,
                observed_row.standard_error - standard_error,
                observed_row.z - z,
                observed_row.p_value_normal - float(2 * norm.sf(abs(z))),
                observed_row.p_value_multiplier - multiplier_p,
            ])
            maxima["diagnostic"] = max(maxima["diagnostic"],
                                         float(np.max(np.abs(values))))
    require(max(maxima.values()) <= 3e-11,
            "event-study or pretrend inference did not reproduce")
    return maxima


def verify_certificates(run_dir: Path, spec: dict[str, Any]) -> dict[str, Any]:
    catalog = load_json(run_dir / "MODEL_CATALOG.json")
    require([row.get("model_id") for row in catalog.get("models", [])] ==
            spec["models"]["core_model_ids"], "model catalog differs")
    require(all(row.get("a1_certificate") == "PASS_A1_NUMERICAL_CERTIFICATE"
                for row in catalog["models"]), "fresh numerical certificate failed")
    validation = load_json(run_dir / "VALIDATION_REPORT.json")
    require(validation.get("status") == "PASS_RECOMPUTED_DYNAMIC_CORE_VALIDATION",
            "producer validation did not pass")
    require(all(validation.get("checks", {}).values()), "producer validation has a failed check")
    reparameterization = load_json(run_dir / "REPARAMETERIZATION_AUDIT.json")
    require(reparameterization.get("status", "").startswith("PASS_"),
            "reference reparameterization did not pass")
    reparam_maximum = max(reparameterization["maximum_relative_differences"][key]
                          for key in ("target", "covariance", "influence"))
    require(reparam_maximum <= spec["reparameterization"]["relative_tolerance"],
            "reparameterization tolerance failed")
    nesting = load_json(run_dir / "NESTING_PROJECTION_AUDIT.json")
    require(nesting.get("status", "").startswith("PASS_"), "nesting audit did not pass")
    for row in nesting["structures"].values():
        require(row["nesting"]["maximum_absolute_residual"] == 0,
                "exact nesting residual is nonzero")
        require(row["score_and_projection"][
            "maximum_absolute_static_target_projection_difference"
        ] <= spec["nesting"]["target_absolute_tolerance"],
            "pseudo-stock target projection differs")
    return {"reparameterization_maximum_relative_difference": reparam_maximum}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--support-run-dir", type=Path, required=True)
    parser.add_argument("--core-spec", type=Path, required=True)
    parser.add_argument("--parent-spec", type=Path, required=True)
    parser.add_argument("--common-multipliers", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)

    spec = load_json(args.core_spec)
    parent_spec = load_json(args.parent_spec)
    manifest = verify_manifest(args.run_dir, spec)
    static = static_objects(args.support_run_dir)
    dynamic = dynamic_objects(args.run_dir)
    archive = np.load(args.common_multipliers, allow_pickle=False)
    xi = np.asarray(archive["multipliers"], float)
    require(xi.shape == (9999, 468), "common multiplier dimensions differ")
    objects = reconstruct_reconciliation(static, dynamic, parent_spec)
    reconciliation = verify_reconciliation(args.run_dir, objects)
    inference = verify_event_and_pretrend(args.run_dir, dynamic, parent_spec, xi)
    certificates = verify_certificates(args.run_dir, spec)
    report = {
        "schema_version": "yax-gate2-dynamic-core-independent-validation-v1",
        "status": "PASS_INDEPENDENT_DYNAMIC_CORE_RECOMPUTATION",
        "result": manifest,
        "checks": {
            "manifest_receipt_and_all_artifact_hashes": "PASS",
            "all_18_reconciliation_estimates_and_covariance": "PASS",
            "all_event_pointwise_and_simultaneous_intervals": "PASS",
            "all_16_pretrend_tests": "PASS",
            "all_leave_one_quarter_and_level_drift_seasonal_diagnostics": "PASS",
            "numerical_reparameterization_and_nesting_certificates": "PASS",
        },
        "maximum_absolute_recomputation_differences": {
            **{f"reconciliation_{key}": value for key, value in reconciliation.items()},
            **inference,
        },
        **certificates,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_bytes(canonical_bytes(report) + b"\n")
    print(json.dumps({"status": report["status"], "result_id": manifest["result_id"]},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationError as error:
        print(f"FAILED: {error}")
        raise SystemExit(2)
