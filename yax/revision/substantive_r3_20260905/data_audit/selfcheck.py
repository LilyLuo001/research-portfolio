#!/usr/bin/env python3
"""Fail-closed checks for the corrected-calendar data audit."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

import pandas as pd


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def run(output: pathlib.Path) -> None:
    receipt = json.loads((output / "EXECUTION_RECEIPT.json").read_text())
    calendar = pd.read_csv(output / "CALENDAR_AUDIT.csv")
    flow = pd.read_csv(output / "SAMPLE_FLOW_CORRECTED.csv")
    route = json.loads((output / "WEIGHT_AND_ROUTE_AUDIT.json").read_text())
    count = dict(zip(flow.stage, flow["count"]))
    checks = {
        "calendar_expected_115": len(calendar) == 115,
        "calendar_observed_114": int(calendar.observed_in_source.astype(bool).sum()) == 114,
        "static_113": int(calendar.retained_in_static_model.astype(bool).sum()) == 113,
        "october_2025_absent": not bool(calendar.loc[calendar.month.eq("2025-10"), "observed_in_source"].iloc[0]),
        "december_2022_observed_excluded": bool(calendar.loc[calendar.month.eq("2022-12"), "observed_in_source"].iloc[0]) and not bool(calendar.loc[calendar.month.eq("2022-12"), "retained_in_static_model"].iloc[0]),
        "support_468": receipt["support_occupations"] == 468,
        "grid_52884": count["complete_primary_grid"] == 468 * 113,
        "fitted_plus_both_zero_equals_grid": count["positive_total_fitted_cells"] + count["both_zero_grid_cells_no_likelihood_contribution"] == count["complete_primary_grid"],
        "one_sided_zeros_retained": count["one_sided_zero_cells_retained"] > 0,
        "route_conserves": route["route_conservation_pass"],
        "receipt_avoids_mutable_hashes": not {"SELF_CHECK.json", "EXECUTION_RECEIPT.json"}.intersection(receipt["output_hashes"]),
    }
    for name, digest in receipt["output_hashes"].items():
        checks[f"hash_{name}"] = sha256(output / name) == digest
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"data-audit selfcheck failed: {failed}")
    result = {"status": "PASS_DATA_AUDIT_SELF_CHECK", "checks": checks}
    (output / "SELF_CHECK.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "checks": len(checks)}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=pathlib.Path, required=True)
    run(parser.parse_args().output_dir)
