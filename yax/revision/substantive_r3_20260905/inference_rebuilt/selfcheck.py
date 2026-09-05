#!/usr/bin/env python3
"""Mechanical self-check for the rebuilt-treatment inference addendum."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

import numpy as np
import pandas as pd


EXPECTED_SUPPORT_HASH = "11ec58ab1004cd83d62c57785f6c0dd3ee5a8abf08b7f71a3b664e91ded8333b"
EXPECTED_POOLED = -0.13210945079219033
EXPECTED_CONDITIONED = -0.021674952018245923


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=pathlib.Path, required=True)
    args = parser.parse_args()
    results = args.results_dir
    receipt = json.loads((results / "EXECUTION_RECEIPT.json").read_text(encoding="utf-8"))
    checks = {}

    checks["output_hashes"] = all(
        sha256(results / name) == expected
        for name, expected in receipt["output_hashes"].items()
    )
    checks["support"] = (
        receipt["support_occupations"] == 468 and
        receipt["support_hash_sha256"] == EXPECTED_SUPPORT_HASH
    )
    checks["calendar"] = (
        receipt["observed_model_months"] == 113 and
        receipt["full_elapsed_calendar_months"] == 115 and
        receipt["zero_placeholder_months"] == ["2022-12", "2025-10"]
    )
    receipt_text = (results / "EXECUTION_RECEIPT.json").read_text(encoding="utf-8")
    checks["no_private_absolute_paths"] = (
        "/projectnb/" not in receipt_text and "/project/econdept/" not in receipt_text
    )
    checks["no_failures"] = json.loads(
        (results / "MODEL_FAILURES.json").read_text(encoding="utf-8")
    ) == []

    models = pd.read_csv(results / "MODEL_SUMMARIES.csv")
    checks["model_rows"] = (
        len(models) == 3 and
        set(models.object) == {"pooled", "conditioned", "paired_movement"}
    )
    lookup = models.set_index("object")
    checks["coefficient_checkpoints"] = (
        np.isclose(lookup.loc["pooled", "estimate"], EXPECTED_POOLED, atol=1e-9, rtol=0) and
        np.isclose(lookup.loc["conditioned", "estimate"], EXPECTED_CONDITIONED, atol=1e-9, rtol=0) and
        np.isclose(
            lookup.loc["paired_movement", "estimate"],
            EXPECTED_CONDITIONED - EXPECTED_POOLED,
            atol=1e-12, rtol=0,
        ) and
        (models.occupation_cluster_se > 0).all() and
        (models.normal_theory_MDE80 > 0).all()
    )

    influence = pd.read_csv(results / "OCCUPATION_INFLUENCE.csv", dtype={"occupation_code": str})
    checks["occupation_influence"] = (
        len(influence) == 468 and influence.occupation_code.nunique() == 468 and
        np.allclose(
            influence.paired_movement_Q5_target_influence_CRV1_scaled,
            influence.conditioned_Q5_target_influence_CRV1_scaled -
            influence.pooled_Q5_target_influence_CRV1_scaled,
            atol=1e-13, rtol=0,
        )
    )

    scores = pd.read_csv(results / "SOC2_FAMILY_SCORE_CONTRIBUTIONS.csv", dtype={"SOC2": str})
    pivot = scores.pivot(index="SOC2", columns="object", values="nuisance_adjusted_target_score")
    checks["family_scores"] = (
        len(scores) == 66 and pivot.shape == (22, 3) and
        np.allclose(
            pivot.paired_movement,
            pivot.conditioned - pivot.pooled,
            atol=1e-13, rtol=0,
        )
    )

    wild = pd.read_csv(results / "SOC2_WILD_SENSITIVITY.csv")
    checks["wild_sensitivity"] = (
        len(wild) == 6 and
        set(wild.wild_weight_distribution) == {"Rademacher", "Webb_six_point"} and
        (wild.SOC2_clusters == 22).all() and
        (wild.wild_score_draws == 99999).all() and
        (wild.wild_score_seed == 2026090561).all() and
        wild.common_family_draws_across_all_objects.all() and
        (wild.SOC2_CRV1_se > 0).all() and
        (wild.normal_theory_MDE80_SOC2_CRV1 > 0).all()
    )

    hac = pd.read_csv(results / "CORRECTED_TIME_HAC_RESULTS.csv")
    checks["hac_rows"] = (
        len(hac) == 15 and
        set(hac.lag_elapsed_calendar_months) == {0, 1, 4, 12, 16} and
        set(hac.object) == {"pooled", "conditioned", "paired_movement"} and
        (hac.full_calendar_months == 115).all() and
        (hac.observed_model_months == 113).all() and
        (hac.zero_placeholder_months == 2).all() and
        (~hac.PSD_projection_applied).all() and
        hac.target_scalar_variance_nonnegative.all()
    )
    checks["occupation_se_conservation"] = all(
        np.isclose(
            row.occupation_cluster_se,
            lookup.loc[row.object, "occupation_cluster_se"],
            atol=1e-10, rtol=1e-9,
        ) for row in hac.itertuples()
    )

    matrices = pd.read_csv(results / "TIME_HAC_COVARIANCE_MATRICES.csv")
    checks["covariance_matrix_rows"] = len(matrices) == 3 * 5 * 5 * 5
    eigen_checks = []
    for (name, lag), group in matrices.groupby(["object", "lag_elapsed_calendar_months"]):
        frame = group.pivot(
            index="row_parameter", columns="column_parameter",
            values="corrected_inclusion_exclusion_covariance",
        )
        labels = sorted(frame.index)
        matrix = frame.loc[labels, labels].to_numpy(float)
        symmetric = np.allclose(matrix, matrix.T, atol=1e-12, rtol=1e-10)
        minimum = float(np.linalg.eigvalsh((matrix + matrix.T) / 2).min())
        summary = hac.loc[(hac.object == name) & (hac.lag_elapsed_calendar_months == lag)].iloc[0]
        eigen_checks.append(
            symmetric and np.isclose(minimum, summary.minimum_covariance_eigenvalue,
                                     atol=1e-10, rtol=1e-8)
        )
    checks["covariance_eigenvalues"] = all(eigen_checks) and len(eigen_checks) == 15
    checks["no_PSD_projection"] = (
        receipt["PSD_projection_applied"] is False and
        (~matrices.PSD_projection_applied).all()
    )

    passed = all(bool(value) for value in checks.values())
    record = {
        "status": "PASS_REBUILT_INFERENCE_SELFCHECK" if passed else "FAIL_REBUILT_INFERENCE_SELFCHECK",
        "checks": {key: bool(value) for key, value in checks.items()},
        "result_hashes": {
            path.name: sha256(path) for path in sorted(results.iterdir())
            if path.is_file() and path.name != "SELF_CHECK.json"
        },
    }
    (results / "SELF_CHECK.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not passed:
        raise RuntimeError(record)
    print(json.dumps(record, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
