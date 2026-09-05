#!/usr/bin/env python3
"""Fail-closed checks for rebuilt-treatment family harmonization outputs."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

import numpy as np
import pandas as pd


EXPECTED = -0.1321094507921903
CONTRACT = "rebuilt_corrected_preperiod_weight"
REQUIRED = (
    "FAMILY_QUINTILE_SUPPORT.csv", "PROFILE_COEFFICIENTS.csv",
    "PROFILE_JOINT_TESTS.csv", "PAIRED_PROFILE_CHANGES.csv",
    "DIRECT_TAIL_SUPPORT.csv", "DIRECT_TAIL_MODELS.csv",
    "CONTINUOUS_WITHIN_FAMILY_MODELS.csv", "LEAVE_ONE_FAMILY_OUT.csv",
    "INFORMATION_DIAGNOSTICS.csv", "OCCUPATION_INFORMATION.csv",
    "FAMILY_INFORMATION.csv", "FAMILY_TAIL_TRAJECTORIES.csv",
    "FAMILY_TRAJECTORY_SELECTION.csv", "REBUILT_Q1_Q5_AGGREGATE_PATHS.csv",
    "CENTERED_BOOTSTRAP_DRAWS.npz", "EXECUTION_RECEIPT.json", "FINDINGS.md",
)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check(output: pathlib.Path) -> None:
    checks = []

    def require(condition, label):
        checks.append({"check": label, "pass": bool(condition)})
        if not condition:
            raise RuntimeError("self-check failed: {}".format(label))

    for name in REQUIRED:
        require((output / name).is_file(), "required output exists: {}".format(name))

    receipt = json.loads((output / "EXECUTION_RECEIPT.json").read_text())
    require(receipt["treatment_contract"] == CONTRACT, "rebuilt contract label")
    require(abs(float(receipt["corrected_baseline_reproduced"]) - EXPECTED) <= 1e-10,
            "rebuilt baseline reproduced")
    require(int(receipt["common_support_occupations"]) == 468, "468 occupations")
    require(int(receipt["bootstrap"]["draws"]) == 9999, "9999 common draws")
    require(not receipt["raw_microdata_written"], "no raw microdata output")
    for name, expected in receipt["output_hashes"].items():
        require(sha256(output / name) == expected, "receipt hash: {}".format(name))

    profile = pd.read_csv(output / "PROFILE_COEFFICIENTS.csv")
    require(set(profile["treatment_contract"]) == {CONTRACT}, "profile contract")
    baseline = profile.loc[(profile.model_id == "profile_baseline") &
                           (profile.target == "Q5_x_post"), "coefficient"]
    require(len(baseline) == 1 and abs(float(baseline.iloc[0]) - EXPECTED) <= 1e-10,
            "profile baseline target")

    support = pd.read_csv(output / "FAMILY_QUINTILE_SUPPORT.csv", dtype={"SOC2": str})
    require(len(support) == 22, "22 broad families")
    direct = sorted(support.loc[support.contains_Q1_and_Q5, "SOC2"].str.zfill(2))
    require(len(direct) > 0, "at least one direct-tail family")

    paths = pd.read_csv(output / "REBUILT_Q1_Q5_AGGREGATE_PATHS.csv")
    require(len(paths) == 226 and paths.month.nunique() == 113, "226 aggregate tail rows")
    require(set(paths["tail"]) == {"Q1", "Q5"}, "both aggregate tails")
    require(set(paths["treatment_contract"]) == {CONTRACT}, "aggregate path contract")
    require("2025-10" not in set(paths.month), "October 2025 absent")
    require("2022-12" not in set(paths.month), "December 2022 excluded")

    arrays = np.load(output / "CENTERED_BOOTSTRAP_DRAWS.npz")
    require(tuple(arrays["common_signs_shape"].tolist()) == (9999, 468),
            "common draw dimensions")

    result = {"status": "PASS_REBUILT_FAMILY_SELFCHECK",
              "checks_passed": len(checks), "checks": checks}
    (output / "REBUILT_SELF_CHECK.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=pathlib.Path, required=True)
    check(parser.parse_args().output_dir)

