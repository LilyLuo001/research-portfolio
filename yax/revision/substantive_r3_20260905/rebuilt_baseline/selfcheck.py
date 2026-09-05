#!/usr/bin/env python3
"""Fail-closed self-check for BASE-03 generated artifacts."""
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


def boolean_series(values: pd.Series) -> pd.Series:
    return values.astype(str).str.strip().str.lower().map({"true": True, "false": False})


def run(output: pathlib.Path) -> None:
    required = [
        "CALENDAR_RECEIPT.json", "ROUTE_CONSERVATION_RECEIPT.json", "PREFIT_GATE.json",
        "REBUILT_ELIGIBLE_UNIVERSE.csv", "REBUILT_TREATMENT_MEMBERSHIP.csv",
        "REBUILT_QUINTILE_SUPPORT.csv", "REBUILT_NORMALIZATION_AND_CUTS.json",
        "NATIVE_TREATMENT_CONTRACTS.csv", "TREATMENT_CONTRACT_SUMMARY.csv",
        "BASELINE_DECOMPOSITION.csv",
        "PAIRED_COMPARISONS.csv", "PAIRED_CENTERED_DRAWS.csv",
        "SUPPORT_CHANGING_COMPARISONS.csv", "COMMON_SUPPORT_RECLASSIFICATION.csv",
        "MODEL_FAILURES.json", "EXECUTION_RECEIPT.json",
    ]
    missing = [name for name in required if not (output / name).is_file()]
    if missing:
        raise RuntimeError(f"missing BASE-03 outputs: {missing}")
    calendar = json.loads((output / "CALENDAR_RECEIPT.json").read_text())
    prefit = json.loads((output / "PREFIT_GATE.json").read_text())
    route = json.loads((output / "ROUTE_CONSERVATION_RECEIPT.json").read_text())
    norm = json.loads((output / "REBUILT_NORMALIZATION_AND_CUTS.json").read_text())
    models = pd.read_csv(output / "BASELINE_DECOMPOSITION.csv")
    members = pd.read_csv(output / "REBUILT_TREATMENT_MEMBERSHIP.csv", dtype={"occupation_code": str})
    universe = pd.read_csv(output / "REBUILT_ELIGIBLE_UNIVERSE.csv", dtype={"occupation_code": str})
    pairs = pd.read_csv(output / "PAIRED_COMPARISONS.csv")
    support_change = pd.read_csv(output / "SUPPORT_CHANGING_COMPARISONS.csv")
    contracts = pd.read_csv(output / "TREATMENT_CONTRACT_SUMMARY.csv")
    checks = {
        "calendar_71": calendar["preperiod_month_count"] == 71,
        "calendar_starts_2017_01": calendar["preperiod_months"][0] == "2017-01",
        "calendar_ends_2022_11": calendar["preperiod_months"][-1] == "2022-11",
        "static_113": calendar["corrected_static_month_count"] == 113,
        "december_transition_excluded": calendar["december_2022_excluded_static"],
        "october_2025_missing_not_interpolated": calendar["october_2025_missing"] and not calendar["october_2025_interpolated"],
        "all_march_basic_restored": len(calendar["restored_march_basic_months"]) == 5,
        "route_conservation": route["route_conservation_pass"],
        "prefit_before_historical_read": prefit["status"] == "PASS_PREFIT_REBUILT_CONTRACT" and not prefit["historical_sealed_support_read"],
        "no_post_stock": prefit["no_postperiod_stock_used"] and norm["postperiod_stock_used"] == 0,
        "rule_A_and_webb": prefit["rule_A_beta_required"] and prefit["finite_webb_required"],
        "both_age_stocks_positive": bool((universe.loc[boolean_series(universe.eligible), ["young_preperiod_stock", "older_preperiod_stock"]] > 0).all().all()),
        "finite_member_values": bool(np.isfinite(members[["preperiod_weight", "rule_A_beta", "webb_pct_software", "webb_z"]].to_numpy()).all()),
        "all_five_quintiles": sorted(members.beta_quintile.unique().tolist()) == [1, 2, 3, 4, 5],
        "historical_reproduced": bool(np.isclose(models.loc[models.row_id.eq("historical_108_historical_treatment"), "coefficient"].iloc[0], -0.13107397642233506, atol=1e-8)),
        "calendar_corrected_reproduced": bool(np.isclose(models.loc[models.row_id.eq("corrected_113_historical_treatment"), "coefficient"].iloc[0], -0.1345539535732939, atol=1e-8)),
        "rebuilt_row_present": int(models.row_id.eq("corrected_113_recomputed_preperiod_treatment").sum()) == 1,
        "historical_contract_discloses_post_stock": bool(boolean_series(contracts.loc[contracts.contract.eq("historical_production_full_static_weight"), "postperiod_stock_used"]).iloc[0]),
        "rebuilt_contract_excludes_post_stock": not bool(boolean_series(contracts.loc[contracts.contract.eq("rebuilt_corrected_preperiod_weight"), "postperiod_stock_used"]).iloc[0]),
        "paired_rows_exact_support": bool(boolean_series(pairs.common_support_only).all()),
        "support_change_not_mislabeled_paired": bool((~boolean_series(support_change.support_changed) | ~boolean_series(support_change.paired_inference_valid)).all()),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"BASE-03 self-check failed: {failed}")
    receipt = json.loads((output / "EXECUTION_RECEIPT.json").read_text())
    expected_hashes = receipt["output_hashes"]
    circular_hashes = sorted(
        {"EXECUTION_RECEIPT.json", "SELF_CHECK.json"}.intersection(expected_hashes)
    )
    if circular_hashes:
        raise RuntimeError(
            "BASE-03 receipt hashes mutable/self-referential outputs: "
            f"{circular_hashes}"
        )
    hash_failures = {name: [sha256(output / name), expected]
                     for name, expected in expected_hashes.items()
                     if sha256(output / name) != expected}
    if hash_failures:
        raise RuntimeError(f"BASE-03 hash self-check failed: {hash_failures}")
    result = {
        "status": "PASS_BASE_03_SELF_CHECK", "checks": checks,
        "verified_output_hashes": expected_hashes,
    }
    (output / "SELF_CHECK.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "checks": len(checks)}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=pathlib.Path, required=True)
    run(parser.parse_args().output_dir)
