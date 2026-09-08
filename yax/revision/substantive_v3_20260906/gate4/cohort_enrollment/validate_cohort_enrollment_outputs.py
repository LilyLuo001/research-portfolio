#!/usr/bin/env python3
"""Public, numerical validation of D05--D07 cohort/enrollment outputs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED = {
    "MODEL_RESULTS.csv", "PAIRED_COMPARISONS.csv", "MODEL_INFLUENCE.csv",
    "SUPPORT_MEMBERSHIP.csv", "AGE_STANDARDIZATION_WEIGHTS.csv",
    "SCHLCOLL_CODE_AUDIT.csv", "EMPLOYED_YOUNG_COMPOSITION.csv",
    "NATIONAL_YOUNG_POPULATION_COMPOSITION.csv", "MODEL_FAILURES.json",
    "EXECUTION_RECEIPT.json",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def expected_models() -> set[str]:
    result: set[str] = set()
    for structure in ("pooled", "family_month"):
        result.add(f"d05_22_25_vs_26_65_{structure}")
        result.add(f"d05_22_25_vs_26_65_fixed_age_{structure}")
        for band in ("26_30", "31_40", "41_50", "51_65"):
            result.add(f"d05_22_25_vs_{band}_{structure}")
        result.update({
            f"d06_unrestricted_young_vs_all_older_{structure}",
            f"d06_nonenrolled_young_vs_all_older_{structure}",
            f"d06_unrestricted_22_25_vs_26_54_{structure}",
            f"d06_nonenrolled_22_25_vs_nonenrolled_26_54_{structure}",
        })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    out = args.output_dir
    require(out.is_dir(), "output directory is absent")
    require(REQUIRED.issubset({path.name for path in out.iterdir()}),
            "required cohort/enrollment output is absent")
    receipt = json.loads((out / "EXECUTION_RECEIPT.json").read_text())
    require(receipt.get("status") == "PASS_GATE4_COHORT_ENROLLMENT",
            "run receipt does not pass")
    for name, expected in receipt["output_hashes"].items():
        require(sha256_file(out / name) == expected, f"output hash differs: {name}")
    require(receipt["canonical_rebuild_maximum_relative_gap"] <= 1e-10,
            "canonical cell reproduction failed")
    require(receipt["fixed_age_population_identity_maximum_relative_gap"] <= 1e-12,
            "age-standardization identity failed")
    require(receipt["nonworker_occupational_exposure_assignment_count"] == 0,
            "national population received occupation exposure")
    require(receipt["older_groups_are_untreated"] is False,
            "older comparator was mislabeled untreated")
    require(receipt["SCHLCOLL_invalid_codes_never_classified_nonenrolled"] is True,
            "invalid enrollment codes entered nonenrollment")
    require(receipt["model_count"] == 20 and receipt["paired_comparison_count"] == 14,
            "declared model/pair inventory differs")
    require(receipt["model_failure_count"] == 0 and
            json.loads((out / "MODEL_FAILURES.json").read_text()) == [],
            "a model failed")

    models = pd.read_csv(out / "MODEL_RESULTS.csv", float_precision="round_trip")
    pairs = pd.read_csv(out / "PAIRED_COMPARISONS.csv", float_precision="round_trip")
    influence = pd.read_csv(out / "MODEL_INFLUENCE.csv", dtype={"cluster_id": str},
                            float_precision="round_trip")
    require(set(models.model_id) == expected_models() and models.model_id.is_unique,
            "model inventory differs")
    require(len(pairs) == 14 and pairs.comparison.is_unique,
            "paired-comparison inventory differs")
    require((models.support_occupations > 4).all(), "model support is empty")
    for prefix, count in (("d05_", receipt["support_counts"]["D05"]),
                          ("d06_unrestricted_young", receipt["support_counts"]["D06_young_restriction"]),
                          ("d06_nonenrolled_young", receipt["support_counts"]["D06_young_restriction"]),
                          ("d06_unrestricted_22", receipt["support_counts"]["D06_common_enrollment_universe"]),
                          ("d06_nonenrolled_22", receipt["support_counts"]["D06_common_enrollment_universe"])):
        selected = models.loc[models.model_id.str.startswith(prefix)]
        require(not selected.empty and (selected.support_occupations == count).all(),
                f"{prefix} support count differs")
    require((models.occupation_ci_lower <= models.coefficient_Q5_x_post).all() and
            (models.coefficient_Q5_x_post <= models.occupation_ci_upper).all(),
            "occupation interval ordering failed")
    require((models.family_ci_lower <= models.coefficient_Q5_x_post).all() and
            (models.coefficient_Q5_x_post <= models.family_ci_upper).all(),
            "family interval ordering failed")

    for model in models.itertuples(index=False):
        for cluster, se_field in (("occupation", "occupation_se"), ("family", "family_se")):
            values = influence.loc[
                (influence.model_id == model.model_id) &
                (influence.cluster_type == cluster), "influence_Q5_x_post"].to_numpy(float)
            require(len(values) > 1 and
                    abs(float(np.sqrt(values @ values)) - getattr(model, se_field)) <= 1e-11,
                    f"model {cluster} SE does not reproduce: {model.model_id}")

    model_lookup = models.set_index("model_id")
    for row in pairs.itertuples(index=False):
        observed = (model_lookup.at[row.left_model, "coefficient_Q5_x_post"] -
                    model_lookup.at[row.right_model, "coefficient_Q5_x_post"])
        require(abs(observed - row.estimate_left_minus_right) <= 1e-12,
                f"paired estimate identity failed: {row.comparison}")
        require(bool(row.common_draws_preserve_covariance),
                "paired row does not preserve covariance")
        for cluster, se_field in (("occupation", "occupation_se"), ("family", "family_se")):
            left = influence.loc[(influence.model_id == row.left_model) &
                                 (influence.cluster_type == cluster)].set_index("cluster_id")
            right = influence.loc[(influence.model_id == row.right_model) &
                                  (influence.cluster_type == cluster)].set_index("cluster_id")
            aligned = left.join(right, lsuffix="_left", rsuffix="_right", how="outer").fillna(0)
            values = (aligned.influence_Q5_x_post_left - aligned.influence_Q5_x_post_right)
            require(abs(float(np.sqrt(np.square(values).sum())) - getattr(row, se_field)) <= 1e-11,
                    f"paired {cluster} SE does not reproduce: {row.comparison}")

    support = pd.read_csv(out / "SUPPORT_MEMBERSHIP.csv", dtype={"occupation_code": str})
    require(len(support) == 468 and support.occupation_code.nunique() == 468,
            "support membership is not the current 468 occupations")
    for column, key in (("d05_common_support", "D05"),
                        ("d06_young_restriction_support", "D06_young_restriction"),
                        ("d06_common_enrollment_universe_support", "D06_common_enrollment_universe")):
        require(int(support[column].sum()) == receipt["support_counts"][key],
                f"support table count differs: {column}")

    standard = pd.read_csv(out / "AGE_STANDARDIZATION_WEIGHTS.csv")
    require(set(standard.exact_age) == set(range(26, 66)) and len(standard) == 40,
            "age-standardization inventory differs")
    require(abs(standard.preperiod_reference_population_share.sum() - 1) <= 1e-12,
            "reference exact-age shares do not sum to one")
    require((standard.minimum_month_factor > 0).all(), "age factor is nonpositive")

    audit = pd.read_csv(out / "SCHLCOLL_CODE_AUDIT.csv")
    require(set(audit.age_bucket) == {"16_21", "22_25", "26_54", "55_65"},
            "enrollment code audit age inventory differs")
    require(set(audit.source) == {"wide", "march_repair"},
            "enrollment code audit source inventory differs")
    require((audit.person_rows > 0).all() and (audit.weighted_persons > 0).all(),
            "enrollment code audit contains empty rows")

    national = pd.read_csv(out / "NATIONAL_YOUNG_POPULATION_COMPOSITION.csv")
    employed = pd.read_csv(out / "EMPLOYED_YOUNG_COMPOSITION.csv")
    require("beta_quintile" not in national.columns and "occupation_code" not in national.columns,
            "national population profile contains occupational exposure")
    require("beta_quintile" in employed.columns,
            "employed on-support composition lacks quintiles")
    for frame in (national, employed):
        for column in [name for name in frame if name.endswith("_share") or name == "employment_rate"]:
            finite = frame[column].dropna()
            require(((finite >= 0) & (finite <= 1)).all(),
                    f"composition share is out of bounds: {column}")

    for path in out.iterdir():
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="ignore")
            require("/projectnb/" not in text and "/usr3/" not in text,
                    f"protected absolute path leaked: {path.name}")
    report = {
        "schema_version": "yax-gate4-cohort-enrollment-validation-v1",
        "status": "PASS_RECOMPUTED_COHORT_ENROLLMENT_VALIDATION",
        "models": len(models), "pairs": len(pairs),
        "support_counts": receipt["support_counts"],
        "canonical_rebuild_maximum_relative_gap":
            receipt["canonical_rebuild_maximum_relative_gap"],
        "fixed_age_population_identity_maximum_relative_gap":
            receipt["fixed_age_population_identity_maximum_relative_gap"],
    }
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
