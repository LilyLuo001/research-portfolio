#!/usr/bin/env python3
"""Fail-closed self-check for the R3 public BCC-grouping bridge."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

import numpy as np
import pandas as pd


GROUPINGS = {
    "historical_YAX_employment_weighted_approximation",
    "public_dashboard_equal_occupation_approximation",
}
STRUCTURES = {
    "occupation_plus_calendar_month_FE",
    "SOC2_x_post",
    "SOC2_x_calendar_month",
}
DYNAMIC_STRUCTURES = {
    "occupation_plus_calendar_month_FE",
    "SOC2_x_calendar_month",
}


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check(condition, name, checks):
    passed = bool(condition)
    checks.append({"check": name, "passed": passed})
    if not passed:
        raise AssertionError(name)


def run(output_dir: pathlib.Path):
    checks = []
    required = {
        "BRIDGE_MEMBERSHIP.csv", "BRIDGE_GROUP_SUMMARY.csv",
        "BRIDGE_MEMBERSHIP_CONCORDANCE.json", "STATIC_MODEL_RESULTS.csv",
        "STATIC_PAIRED_DIFFERENCES.csv", "STATIC_INFORMATION_BY_OCCUPATION.csv",
        "STATIC_GROWTH_ENDPOINTS.csv", "DYNAMIC_PATHS.csv",
        "DYNAMIC_JOINT_TESTS.csv", "DYNAMIC_PAIRED_GROUPING_DIFFERENCES.csv",
        "DYNAMIC_TARGET_COVARIANCE.csv", "DYNAMIC_TARGET_INFLUENCE.csv",
        "MODEL_FAILURES.json", "FINDINGS.md", "EXECUTION_RECEIPT.json",
    }
    check(required.issubset({path.name for path in output_dir.iterdir()}),
          "all required output files exist", checks)

    membership = pd.read_csv(output_dir / "BRIDGE_MEMBERSHIP.csv",
                             dtype={"occupation_code": str})
    membership["occupation_code"] = membership.occupation_code.str.zfill(4)
    check(len(membership) == 468 and membership.occupation_code.nunique() == 468,
          "membership has one row for each of 468 common occupations", checks)
    check(set(membership.historical_YAX_quintile.unique()).issubset({1, 2, 3, 4, 5}),
          "historical quintiles valid", checks)
    check(set(membership.equal_occupation_quintile.unique()).issubset({1, 2, 3, 4, 5}),
          "equal-occupation quintiles valid", checks)
    check(membership.historical_YAX_quintile.nunique() == 5 and
          membership.equal_occupation_quintile.nunique() == 5,
          "both grouping rules populate all five quintiles", checks)

    summary = pd.read_csv(output_dir / "BRIDGE_GROUP_SUMMARY.csv")
    check(len(summary) == 2 and set(summary.grouping_name) == GROUPINGS,
          "two explicitly labeled grouping constructions", checks)
    check(np.all(summary.support_occupations == 468),
          "grouping constructions use common support", checks)
    check(np.all((summary.high_occupation_count > 0) &
                 (summary.high_occupation_count < summary.support_occupations)),
          "both binary grouping cells are populated", checks)
    check(summary.support_hash_sha256.nunique() == 1,
          "groupings share identical ordered support", checks)

    concordance = json.loads(
        (output_dir / "BRIDGE_MEMBERSHIP_CONCORDANCE.json").read_text()
    )
    check(concordance["external_BCC_membership_concordance"] == "UNVERIFIED",
          "external BCC membership is not claimed verified", checks)
    check(concordance["switched_binary_group_occupations"] ==
          int((~membership.same_binary_group.astype(bool)).sum()),
          "binary membership-switch count reconciles", checks)

    static = pd.read_csv(output_dir / "STATIC_MODEL_RESULTS.csv")
    check(len(static) == 6, "six static models completed", checks)
    check(set(static.grouping_name) == GROUPINGS and
          set(static.conditioning_structure) == STRUCTURES,
          "static grouping-by-conditioning grid complete", checks)
    check(np.all(static.support_occupations == 468) and
          static.support_hash_sha256.nunique() == 1,
          "static models use one common support", checks)
    check(np.all(np.isfinite(static[["coefficient", "occupation_cluster_se",
                                     "ci_lower", "ci_upper"]].to_numpy(float))),
          "static coefficients and intervals finite", checks)
    check(np.all(static.ci_lower <= static.coefficient) and
          np.all(static.coefficient <= static.ci_upper),
          "static estimates lie inside intervals", checks)
    check(np.all(static.bootstrap_draws == 9999),
          "static results use 9999 draws", checks)

    paired = pd.read_csv(output_dir / "STATIC_PAIRED_DIFFERENCES.csv")
    check(len(paired) == 7, "three grouping-rule and four conditioning pairs completed", checks)
    check(int((paired.contrast_type == "grouping_rule").sum()) == 3 and
          int((paired.contrast_type == "conditioning_change").sum()) == 4,
          "static paired contrast types complete", checks)
    check(np.all(paired.common_occupation_multipliers.astype(bool)),
          "static paired inference preserves common multipliers", checks)

    information = pd.read_csv(output_dir / "STATIC_INFORMATION_BY_OCCUPATION.csv",
                              dtype={"occupation_code": str})
    check(len(information) == 6 * 468,
          "occupation information has one row per static model and occupation", checks)
    for key, frame in information.groupby(["grouping_name", "conditioning_structure"]):
        share = frame.conditional_target_information_share.sum()
        check(np.isclose(share, 1.0, atol=1e-8),
              "information shares sum to one for {}".format(key), checks)

    growth = pd.read_csv(output_dir / "STATIC_GROWTH_ENDPOINTS.csv")
    check(len(growth) == 4 and set(growth.grouping_name) == GROUPINGS and
          set(growth.age_group) == {"young_22_25", "older_26_65"},
          "November-2022 to June-2026 endpoint table complete", checks)

    failures = json.loads((output_dir / "MODEL_FAILURES.json").read_text())
    check(len(failures) == 0, "no retained static or dynamic model failures", checks)

    dynamic = pd.read_csv(output_dir / "DYNAMIC_PATHS.csv")
    dynamic_models = dynamic.groupby(["grouping_name", "conditioning_structure"]).size()
    check(len(dynamic_models) == 4 and
          set(dynamic.grouping_name) == GROUPINGS and
          set(dynamic.conditioning_structure) == DYNAMIC_STRUCTURES,
          "four dynamic models completed", checks)
    check(dynamic_models.nunique() == 1 and dynamic_models.iloc[0] >= 35,
          "dynamic models have a common complete quarterly path", checks)
    check(np.all(dynamic.reference_bin == "2022Q4") and
          not np.any(dynamic.event_bin == "2022Q4"),
          "2022Q4 is the omitted dynamic reference", checks)
    check(np.all(dynamic.simultaneous_path_ci_lower <= dynamic.coefficient) and
          np.all(dynamic.coefficient <= dynamic.simultaneous_path_ci_upper),
          "dynamic estimates lie inside simultaneous intervals", checks)

    joint = pd.read_csv(output_dir / "DYNAMIC_JOINT_TESTS.csv")
    check(len(joint) == 8 and
          set(joint.test) == {"all_pre_reference_dynamic_coefficients_zero",
                              "all_post_2022_dynamic_coefficients_zero"},
          "preperiod and postperiod joint tests complete", checks)

    dynamic_pair = pd.read_csv(
        output_dir / "DYNAMIC_PAIRED_GROUPING_DIFFERENCES.csv"
    )
    check(set(dynamic_pair.conditioning_structure) == DYNAMIC_STRUCTURES and
          len(dynamic_pair) == 2 * dynamic_models.iloc[0],
          "paired grouping-rule dynamics complete", checks)
    check(np.all(dynamic_pair.common_support_and_multipliers.astype(bool)),
          "dynamic paired inference preserves common support and multipliers", checks)

    covariance = pd.read_csv(output_dir / "DYNAMIC_TARGET_COVARIANCE.csv")
    path_count = int(dynamic_models.iloc[0])
    check(len(covariance) == 4 * path_count * path_count,
          "complete target covariance stored for every dynamic model", checks)
    influence = pd.read_csv(output_dir / "DYNAMIC_TARGET_INFLUENCE.csv",
                            dtype={"occupation_code": str})
    check(len(influence) == 4 * 468,
          "occupation influence rows stored for every dynamic model", checks)

    receipt = json.loads((output_dir / "EXECUTION_RECEIPT.json").read_text())
    check(receipt["bcc_version"] == "2026-08-12",
          "August 12 2026 BCC version recorded", checks)
    check(receipt["calendar"] == {
        "first_month": "2017-01", "last_month": "2026-07", "months": 113,
        "transition_month_excluded": True, "october_2025_present": False,
    }, "corrected calendar contract recorded", checks)
    check(receipt["static_models_completed"] == 6 and
          receipt["dynamic_models_completed"] == 4,
          "receipt model counts complete", checks)
    check(receipt["failures"] == [], "receipt retains no hidden failures", checks)
    for filename, expected in receipt["output_hashes"].items():
        check(sha256(output_dir / filename) == expected,
              "receipt hash matches {}".format(filename), checks)

    result_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in output_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".csv", ".json", ".md"}
    ).lower()
    check("bcc-exact" not in result_text and "bcc_exact" not in result_text,
          "outputs do not claim exact BCC membership", checks)
    check("approximate_public_grouping_bridge_not_replication" in result_text,
          "bridge limitation is machine-readable", checks)

    result = {"status": "PASS", "checks": len(checks), "details": checks}
    (output_dir / "SELF_CHECK.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))


def parser():
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--output-dir", type=pathlib.Path, required=True)
    return value


if __name__ == "__main__":
    run(parser().parse_args().output_dir)
