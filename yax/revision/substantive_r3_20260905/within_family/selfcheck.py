#!/usr/bin/env python3
"""Fail-closed self-check for the R3 within-family output bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

import numpy as np
import pandas as pd


EXPECTED = -0.1345539535732939
REQUIRED = (
    "FAMILY_QUINTILE_SUPPORT.csv",
    "PROFILE_COEFFICIENTS.csv",
    "PROFILE_JOINT_TESTS.csv",
    "PAIRED_PROFILE_CHANGES.csv",
    "DIRECT_TAIL_SUPPORT.csv",
    "DIRECT_TAIL_MODELS.csv",
    "CONTINUOUS_WITHIN_FAMILY_MODELS.csv",
    "LEAVE_ONE_FAMILY_OUT.csv",
    "MODEL_FAILURES.csv",
    "INFORMATION_DIAGNOSTICS.csv",
    "OCCUPATION_INFORMATION.csv",
    "FAMILY_INFORMATION.csv",
    "FAMILY_TAIL_TRAJECTORIES.csv",
    "FAMILY_TRAJECTORY_SELECTION.csv",
    "CENTERED_BOOTSTRAP_DRAWS.npz",
    "EXECUTION_RECEIPT.json",
    "FINDINGS.md",
)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check(output: pathlib.Path):
    checks = []

    def require(condition, label):
        checks.append({"check": label, "pass": bool(condition)})
        if not condition:
            raise RuntimeError("self-check failed: {}".format(label))

    for name in REQUIRED:
        require((output / name).is_file(), "required output exists: {}".format(name))
    receipt = json.loads((output / "EXECUTION_RECEIPT.json").read_text(encoding="utf-8"))
    require(abs(receipt["corrected_baseline_reproduced"] - EXPECTED) <= 1e-10,
            "corrected baseline reproduced")
    require(receipt["historical_support_occupations"] == 468,
            "historical support has 468 occupations")
    require(receipt["bootstrap"]["draws"] == 9999,
            "canonical workstream uses 9999 draws")
    require(receipt["bootstrap"]["common_occupation_Rademacher_multipliers"],
            "common occupation signs declared")
    require(not receipt["raw_microdata_written"], "no raw microdata written")
    for name, expected_hash in receipt["output_hashes"].items():
        require(sha256(output / name) == expected_hash,
                "receipt hash matches: {}".format(name))

    profile = pd.read_csv(output / "PROFILE_COEFFICIENTS.csv")
    require(set(profile.model_id) == {
        "profile_baseline", "profile_SOC2_x_post", "profile_SOC2_x_calendar_month"
    }, "three profile models present")
    require(profile.groupby("model_id").target.nunique().eq(4).all(),
            "each profile has Q2-Q5")
    require(np.isfinite(profile[
        ["coefficient", "occupation_cluster_se", "simultaneous_ci_lower",
         "simultaneous_ci_upper"]
    ].to_numpy(float)).all(), "profile estimates and simultaneous intervals finite")

    tests = pd.read_csv(output / "PROFILE_JOINT_TESTS.csv")
    require(tests.groupby("model_id").test.nunique().eq(3).all(),
            "each profile has joint zero/equality/monotonicity tests")
    require((tests.loc[tests.test.eq("Q2_Q3_Q4_Q5_jointly_zero"), "restrictions"] == 4).all(),
            "joint-zero tests have four restrictions")

    support = pd.read_csv(output / "FAMILY_QUINTILE_SUPPORT.csv", dtype={"SOC2": str})
    require(len(support) == 22, "22 SOC2 families in support exhibit")
    direct_families = sorted(support.loc[support.contains_Q1_and_Q5, "SOC2"].str.zfill(2))
    require(direct_families == ["27", "29", "31", "41"],
            "direct-tail family set is 27/29/31/41")
    direct = pd.read_csv(output / "DIRECT_TAIL_MODELS.csv")
    require(len(direct) == 3 and direct.support_occupations.nunique() == 1,
            "three direct-tail models share one changed population")
    require((direct.preperiod_stock_share_of_full_support > 0).all()
            and (direct.preperiod_stock_share_of_full_support < 1).all(),
            "direct-tail stock share explicitly lies inside full population")

    continuous = pd.read_csv(output / "CONTINUOUS_WITHIN_FAMILY_MODELS.csv")
    require(len(continuous) == 3 and continuous.common_slope_across_SOC2_families.all(),
            "three continuous common-slope models present")
    require((continuous.scale_raw_beta_units_per_one_z > 0).all(),
            "continuous scale is positive and disclosed")

    lofo = pd.read_csv(output / "LEAVE_ONE_FAMILY_OUT.csv", dtype={"omitted_SOC2": str})
    require(lofo.parent_model.nunique() == 4, "four primary models receive LOFO")
    require(lofo.omitted_SOC2.str.zfill(2).nunique() == 22,
            "all 22 families omitted in LOFO")
    require(lofo.loc[lofo.parent_model.str.startswith("profile_")].groupby(
        ["parent_model", "omitted_SOC2"]
    ).target.nunique().eq(4).all(), "profile LOFO retains all four targets")

    info = pd.read_csv(output / "INFORMATION_DIAGNOSTICS.csv")
    require((info.nuisance_adjusted_fisher_information > 0).all(),
            "all fitted-information values positive")
    require((info.effective_occupation_information_count > 0).all(),
            "all effective occupation counts positive")
    require(((info.top_five_occupation_information_share > 0)
             & (info.top_five_occupation_information_share <= 1)).all(),
            "top-five shares valid")
    require((info.normal_theory_MDE80 > 0).all(), "conditional MDEs positive")

    selected = pd.read_csv(output / "FAMILY_TRAJECTORY_SELECTION.csv", dtype={"SOC2": str})
    require(sorted(selected.SOC2.str.zfill(2)) == ["27", "29", "31", "41"],
            "trajectory families equal information-ranked direct-tail families")
    require((~selected.selected_by_coefficient_sign).all(),
            "trajectory selection is not coefficient-sign based")
    paths = pd.read_csv(output / "FAMILY_TAIL_TRAJECTORIES.csv", dtype={"SOC2": str})
    require(paths.month.nunique() == 113, "trajectory calendar has 113 months")
    require(set(paths["tail"]) == {"Q1", "Q5"}, "young/older paths cover both tails")
    require(paths.groupby(["SOC2", "tail"]).month.nunique().eq(113).all(),
            "each selected family-tail has a full path")

    arrays = np.load(output / "CENTERED_BOOTSTRAP_DRAWS.npz")
    require(tuple(arrays["common_signs_shape"].tolist()) == (9999, 468),
            "stored common sign shape has expected dimensions")
    unpacked = np.unpackbits(arrays["common_signs_packbits"], axis=1)[:, :468]
    require(unpacked.shape == (9999, 468),
            "bit-packed common sign matrix reconstructs exactly")
    require(set(np.unique(unpacked)) == {0, 1},
            "stored common signs are binary Rademacher representation")
    require("profile_baseline__Q5_x_post" in arrays.files
            and "direct_SOC2_x_calendar_month__Q5_x_post" in arrays.files
            and "continuous_SOC2_x_calendar_month__within_beta" in arrays.files,
            "main-model centered shifts are stored")

    result = {
        "status": "PASS_R3_WITHIN_FAMILY_SELF_CHECK",
        "checks": checks,
        "checks_passed": len(checks),
    }
    (output / "SELF_CHECK.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=pathlib.Path, required=True)
    check(parser.parse_args().output_dir)


if __name__ == "__main__":
    main()
