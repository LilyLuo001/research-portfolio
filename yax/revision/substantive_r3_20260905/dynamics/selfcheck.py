#!/usr/bin/env python3
"""Validate the complete R3 dynamics artifact set."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

import numpy as np
import pandas as pd


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_bool(value) -> bool:
    """Parse R/Pandas CSV booleans without treating nonempty strings as true."""
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"true", "t", "1"}:
        return True
    if normalized in {"false", "f", "0"}:
        return False
    raise RuntimeError("unrecognized Boolean value: {!r}".format(value))


def validate_honestdid(output: pathlib.Path) -> dict:
    receipt_path = output / "HONESTDID_EXECUTION_RECEIPT.csv"
    if not receipt_path.is_file():
        raise RuntimeError("official HonestDiD execution receipt is missing")
    applicability = pd.read_csv(output / "RAMBACHAN_ROTH_APPLICABILITY.csv")
    ready = applicability.loc[
        applicability.execution_status.eq("READY_FOR_OFFICIAL_HONESTDID")
    ]
    receipt = pd.read_csv(receipt_path, keep_default_na=False)
    if len(receipt) != len(ready) or len(receipt) == 0:
        raise RuntimeError("HonestDiD receipt does not cover every validated event vector")
    pinned_sha = "6813f02ed38f0b63bdca6915604b2eac90491303"
    pinned_cvxr_sha = "2fe1dac4d0c903c4a29515bef19c5d3824d09656"
    expected_smooth = "0|0.005|0.01|0.02|0.03|0.04|0.05"
    expected_relative = "0|0.5|1|1.5|2"
    if set(receipt.official_source_commit.astype(str)) != {pinned_sha}:
        raise RuntimeError("HonestDiD official source commit changed")
    if set(receipt.installed_remote_sha.astype(str)) != {pinned_sha}:
        raise RuntimeError("installed HonestDiD source does not match the pinned commit")
    if set(receipt.package_version.astype(str)) != {"0.2.8"}:
        raise RuntimeError("unexpected HonestDiD package version")
    if set(receipt.cvxr_version.astype(str)) != {"1.8.2"}:
        raise RuntimeError("unexpected CVXR package version")
    if set(receipt.cvxr_official_source_commit.astype(str)) != {pinned_cvxr_sha}:
        raise RuntimeError("CVXR official source commit changed")
    if set(receipt.cvxr_installed_remote_sha.astype(str)) != {pinned_cvxr_sha}:
        raise RuntimeError("installed CVXR source does not match the pinned commit")
    if not all(parse_bool(value) for value in receipt.cvxr_status_export_verified):
        raise RuntimeError("pinned CVXR status API was not verified")
    if set(receipt.highs_version.astype(str)) != {"1.12.0-3"}:
        raise RuntimeError("unexpected highs dependency version")
    if set(receipt.highs_source.astype(str)) != {"CRAN archive release 1.12.0-3"}:
        raise RuntimeError("unexpected highs dependency source")
    if set(receipt.osqp_version.astype(str)) != {"1.0.0"}:
        raise RuntimeError("unexpected osqp dependency version")
    if set(receipt.osqp_source.astype(str)) != {"CRAN release 1.0.0"}:
        raise RuntimeError("unexpected osqp dependency source")
    if set(receipt.smoothness_grid_log_points_per_quarter.astype(str)) != {expected_smooth}:
        raise RuntimeError("HonestDiD smoothness grid changed")
    if set(receipt.relative_magnitude_grid.astype(str)) != {expected_relative}:
        raise RuntimeError("HonestDiD relative-magnitude grid changed")

    checked_outputs = []
    for row in receipt.itertuples(index=False):
        suffix = "{}_{}".format(row.treatment_contract, row.structure)
        vector_path = output / "HONESTDID_EVENT_VECTOR_{}.csv".format(suffix)
        covariance_path = output / "HONESTDID_COVARIANCE_{}.csv".format(suffix)
        original_path = output / "HONESTDID_ORIGINAL_{}.csv".format(suffix)
        smooth_path = output / "HONESTDID_SMOOTHNESS_{}.csv".format(suffix)
        relative_path = output / "HONESTDID_RELATIVE_MAGNITUDE_{}.csv".format(suffix)
        for path in (vector_path, covariance_path, original_path, smooth_path, relative_path):
            if not path.is_file():
                raise RuntimeError("missing HonestDiD artifact: {}".format(path.name))
        expected_hashes = {
            vector_path: row.event_vector_sha256,
            covariance_path: row.event_covariance_sha256,
            original_path: row.original_result_sha256,
            smooth_path: row.smoothness_result_sha256,
            relative_path: row.relative_magnitude_result_sha256,
        }
        for path, expected in expected_hashes.items():
            if sha256(path) != str(expected):
                raise RuntimeError("HonestDiD hash mismatch for {}".format(path.name))
        if int(row.event_coefficients) != 38 or int(row.pre_coefficients) != 23:
            raise RuntimeError("HonestDiD event-vector dimensions changed")
        if int(row.post_coefficients) != 15 or row.reference_bin != "2022Q4":
            raise RuntimeError("HonestDiD post/reference dimensions changed")
        if not np.isclose(float(row.l_vec_sum), 1.0, atol=1e-12, rtol=0):
            raise RuntimeError("HonestDiD post functional no longer sums to one")
        if parse_bool(row.positive_zero_exclusion_breakdown_defined) == parse_bool(
            row.conventional_interval_includes_zero
        ):
            raise RuntimeError("HonestDiD breakdown status contradicts conventional interval")
        for path in (original_path, smooth_path, relative_path):
            frame = pd.read_csv(path)
            if not {"lb", "ub"}.issubset(frame.columns):
                raise RuntimeError("HonestDiD interval columns missing in {}".format(path.name))
            if frame[["lb", "ub"]].isna().all(axis=None):
                raise RuntimeError("HonestDiD produced no finite interval in {}".format(path.name))
        checked_outputs.extend((original_path.name, smooth_path.name, relative_path.name))
    return {
        "status": "PASS_OFFICIAL_HONESTDID_SELFCHECK",
        "models": int(len(receipt)),
        "official_source_commit": pinned_sha,
        "cvxr_official_source_commit": pinned_cvxr_sha,
        "result_files": sorted(checked_outputs),
        "receipt_sha256": sha256(receipt_path),
    }


def validate_structure_pair(output: pathlib.Path) -> dict:
    table_path = output / "STATIC_STRUCTURE_PAIRING.csv"
    receipt_path = output / "STATIC_STRUCTURE_PAIRING_RECEIPT.json"
    if not table_path.is_file() or not receipt_path.is_file():
        raise RuntimeError("paired cross-structure artifacts are missing")
    table = pd.read_csv(table_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    contracts = {
        "historical_production_full_static_weight",
        "rebuilt_corrected_preperiod_weight",
    }
    if len(table) != 2 or set(table.treatment_contract) != contracts:
        raise RuntimeError("paired cross-structure table does not cover both contracts")
    if not table.common_occupation_Rademacher_draws.map(parse_bool).all():
        raise RuntimeError("cross-structure pairing does not use common draws")
    if not table.support_occupations.astype(int).eq(468).all():
        raise RuntimeError("cross-structure support changed")
    mapping = pd.read_csv(output / "STATIC_DYNAMIC_MAPPING.csv")
    for row in table.itertuples(index=False):
        item = mapping.loc[mapping.treatment_contract.eq(row.treatment_contract)]
        unconditioned = item.loc[item.structure.eq("unconditioned")]
        conditioned = item.loc[item.structure.eq("SOC2_x_calendar_month")]
        if len(unconditioned) != 1 or len(conditioned) != 1:
            raise RuntimeError("static mapping counterpart is missing")
        if not np.isclose(
            row.unconditioned_coefficient, unconditioned.static_coefficient.iloc[0],
            atol=1e-12, rtol=0,
        ) or not np.isclose(
            row.conditioned_coefficient, conditioned.static_coefficient.iloc[0],
            atol=1e-12, rtol=0,
        ):
            raise RuntimeError("paired coefficient differs from static mapping model")
        expected_difference = row.conditioned_coefficient - row.unconditioned_coefficient
        if not np.isclose(row.conditioned_minus_unconditioned, expected_difference,
                          atol=1e-14, rtol=0):
            raise RuntimeError("cross-structure paired difference arithmetic failed")
        influence_path = output / row.influence_file
        covariance_path = output / row.covariance_file
        influence = pd.read_csv(influence_path)
        covariance_long = pd.read_csv(covariance_path)
        if len(influence) != 468 or influence.occupation_code.duplicated().any():
            raise RuntimeError("cross-structure influence support is invalid")
        values = influence[[
            "unconditioned_influence", "SOC2_x_calendar_month_influence",
        ]].to_numpy(float)
        stored = covariance_long.pivot(
            index="row_structure", columns="column_structure",
            values="occupation_cluster_covariance",
        ).reindex(
            index=["unconditioned", "SOC2_x_calendar_month"],
            columns=["unconditioned", "SOC2_x_calendar_month"],
        ).to_numpy(float)
        if not np.allclose(values.T @ values, stored, atol=1e-12, rtol=1e-10):
            raise RuntimeError("cross-structure stored covariance is not reproduced")
        delta = values[:, 1] - values[:, 0]
        if not np.isclose(np.sqrt(delta @ delta), row.paired_occupation_cluster_se,
                          atol=1e-12, rtol=1e-10):
            raise RuntimeError("paired SE is not reproduced by stored influence")
    for name, digest in receipt["output_hashes"].items():
        if sha256(output / name) != digest:
            raise RuntimeError("cross-structure output hash mismatch for {}".format(name))
    return {
        "status": "PASS_STATIC_STRUCTURE_PAIRING_SELFCHECK",
        "rows": int(len(table)),
        "receipt_sha256": sha256(receipt_path),
    }


def run(output: pathlib.Path, require_honestdid: bool = False,
        require_structure_pair: bool = False) -> None:
    required = (
        "DYNAMIC_TARGET_PROFILE.csv", "DYNAMIC_Q5_Q1_PROFILE.csv",
        "PRETREND_TESTS.csv", "STATIC_DYNAMIC_MAPPING.csv",
        "ONSET_DATE_SENSITIVITY.csv", "ENDPOINT_SENSITIVITY.csv",
        "SEASONALITY_SENSITIVITY.csv", "RAMBACHAN_ROTH_APPLICABILITY.csv",
        "MARCH_REPAIR_POLICY_RECEIPT.json", "MODEL_FAILURES.json",
        "EXECUTION_RECEIPT.json",
    )
    missing = [name for name in required if not (output / name).is_file()]
    if missing:
        raise RuntimeError("missing outputs: {}".format(missing))
    receipt = json.loads((output / "EXECUTION_RECEIPT.json").read_text(encoding="utf-8"))
    repair = json.loads((output / "MARCH_REPAIR_POLICY_RECEIPT.json").read_text(encoding="utf-8"))
    if repair["status"] != "PASS_APPEND_EQUIVALENT_TO_REPLACE_ON_ANALYSIS_ELIGIBLE_STOCK":
        raise RuntimeError("March repair policy preflight did not pass")
    if repair["source_audits"]["wide_ASEC"]["analysis_eligible_positive_weight_rows"] != 0:
        raise RuntimeError("wide ASEC unexpectedly contributes eligible March stock")
    if any(value != 0 for value in repair["eligible_CPSIDP_overlap_by_month"].values()):
        raise RuntimeError("eligible March identifiers overlap across sources")
    if receipt["calendar"]["corrected_months"] != 113:
        raise RuntimeError("corrected calendar count changed")
    if not receipt["calendar"]["transition_excluded"]:
        raise RuntimeError("transition month was not excluded")
    if receipt["calendar"]["reference_bin"] != "2022Q4":
        raise RuntimeError("reference bin changed")
    if receipt["calendar"]["reference_observed_months"] != ["2022-10", "2022-11"]:
        raise RuntimeError("reference bin does not contain exactly October-November 2022")

    profile = pd.read_csv(output / "DYNAMIC_TARGET_PROFILE.csv")
    q5 = pd.read_csv(output / "DYNAMIC_Q5_Q1_PROFILE.csv")
    structures = {"unconditioned", "SOC2_x_calendar_month"}
    for contract in profile.treatment_contract.unique():
        subset = profile.loc[profile.treatment_contract.eq(contract)]
        if set(subset.structure) != structures:
            raise RuntimeError("missing dynamic structure for {}".format(contract))
        for structure in structures:
            item = subset.loc[subset.structure.eq(structure)]
            if set(item.quintile.astype(int)) != {2, 3, 4, 5}:
                raise RuntimeError("dynamic profile is not fully interacted")
            if "2022Q4" in set(item.event_bin):
                raise RuntimeError("reference bin was estimated rather than omitted")
    if not np.all(q5.quintile.astype(int).eq(5)):
        raise RuntimeError("Q5 profile contains non-Q5 rows")

    mapping = pd.read_csv(output / "STATIC_DYNAMIC_MAPPING.csv")
    if not mapping.mapping_rule.str.contains("equality is not assumed").all():
        raise RuntimeError("static-dynamic mapping overclaims equality")
    historical = mapping.loc[
        mapping.treatment_contract.eq("historical_production_full_static_weight") &
        mapping.structure.eq("unconditioned")
    ]
    if len(historical) != 1 or not np.isclose(
        historical.static_coefficient.iloc[0], -0.1345539535732939, atol=1e-8, rtol=0,
    ):
        raise RuntimeError("static corrected baseline did not reproduce")

    onset = pd.read_csv(output / "ONSET_DATE_SENSITIVITY.csv")
    expected_onsets = {
        "2022-11", "2022-12", "2023-01", "2023-02",
        "2023-03", "2023-04", "2023-05", "2023-06",
    }
    for contract in onset.treatment_contract.unique():
        for structure in structures:
            subset = onset.loc[
                onset.treatment_contract.eq(contract) & onset.structure.eq(structure)
            ]
            if set(subset.onset) != expected_onsets:
                raise RuntimeError("onset grid incomplete")
            reference = subset.loc[subset.onset.eq("2023-01")]
            if len(reference) != 1 or reference.status.iloc[0] != "PASS":
                raise RuntimeError("January-2023 onset reference failed")
    endpoint = pd.read_csv(output / "ENDPOINT_SENSITIVITY.csv")
    expected_endpoints = {
        "through_2025_09", "through_2025_12_actual_gap",
        "full_excluding_September_and_November_2025",
        "full_through_2026_07_excluding_late_2025", "full_through_2026_07",
        "post_2020_coding_stable_through_2026_07",
    }
    for contract in endpoint.treatment_contract.unique():
        for structure in structures:
            subset = endpoint.loc[
                endpoint.treatment_contract.eq(contract) & endpoint.structure.eq(structure)
            ]
            if set(subset.variant) != expected_endpoints:
                raise RuntimeError("endpoint grid incomplete")
            reference = subset.loc[subset.variant.eq("full_through_2026_07")]
            if len(reference) != 1 or reference.status.iloc[0] != "PASS":
                raise RuntimeError("full-window endpoint reference failed")
    allowed_status = {"PASS", "FAILED_REPORTED_NOT_SUBSTITUTED"}
    if not set(onset.status).issubset(allowed_status) or not set(endpoint.status).issubset(allowed_status):
        raise RuntimeError("grid contains an unrecognized execution status")

    seasonal = pd.read_csv(output / "SEASONALITY_SENSITIVITY.csv")
    lower = seasonal.loc[seasonal.specification.str.startswith("quintile_by_month_of_year")]
    for contract in profile.treatment_contract.unique():
        for structure in structures:
            item = lower.loc[
                lower.treatment_contract.eq(contract) & lower.structure.eq(structure)
            ]
            if len(item) != 1 or item.status.iloc[0] != "PASS":
                raise RuntimeError("lower-dimensional seasonality model did not pass")

    rr = pd.read_csv(output / "RAMBACHAN_ROTH_APPLICABILITY.csv")
    if not rr.reference_bin_omitted.astype(bool).all():
        raise RuntimeError("HonestDiD input did not omit its reference")
    if not np.allclose(rr.weights_sum, 1.0, atol=1e-12, rtol=0):
        raise RuntimeError("HonestDiD functional weights do not sum to one")

    for model in receipt["model_receipts"]:
        cov = pd.read_csv(output / model["covariance_file"])
        labels = sorted(set(cov.row_target))
        matrix = cov.pivot(index="row_target", columns="column_target", values="occupation_cluster_covariance")
        matrix = matrix.reindex(index=labels, columns=labels).to_numpy(float)
        if not np.allclose(matrix, matrix.T, atol=1e-12, rtol=1e-10):
            raise RuntimeError("stored covariance is asymmetric")
        if np.linalg.eigvalsh((matrix + matrix.T) / 2).min() < -1e-9:
            raise RuntimeError("stored covariance is materially indefinite")
        if model["target_covariance_rank"] != int(np.linalg.matrix_rank(matrix)):
            raise RuntimeError("stored covariance rank differs from receipt")
        if not (output / model["influence_file"]).is_file():
            raise RuntimeError("missing stored influence representation")

    for name, digest in receipt["output_hashes"].items():
        if sha256(output / name) != digest:
            raise RuntimeError("output hash mismatch for {}".format(name))
    result = {
        "status": "PASS_R3_DYNAMICS_SELFCHECK",
        "contracts": sorted(profile.treatment_contract.unique().tolist()),
        "dynamic_profile_rows": int(len(profile)),
        "q5_profile_rows": int(len(q5)),
        "onset_rows": int(len(onset)),
        "endpoint_rows": int(len(endpoint)),
        "receipt_sha256": sha256(output / "EXECUTION_RECEIPT.json"),
    }
    if require_honestdid:
        result["honestdid"] = validate_honestdid(output)
    if require_structure_pair:
        result["structure_pair"] = validate_structure_pair(output)
    (output / "SELF_CHECK.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))


def parser():
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--output-dir", type=pathlib.Path, required=True)
    value.add_argument(
        "--require-honestdid", action="store_true",
        help="also require and validate official pinned HonestDiD outputs",
    )
    value.add_argument(
        "--require-structure-pair", action="store_true",
        help="also require and validate the paired static cross-structure result",
    )
    return value


if __name__ == "__main__":
    arguments = parser().parse_args()
    run(
        arguments.output_dir,
        require_honestdid=arguments.require_honestdid,
        require_structure_pair=arguments.require_structure_pair,
    )
