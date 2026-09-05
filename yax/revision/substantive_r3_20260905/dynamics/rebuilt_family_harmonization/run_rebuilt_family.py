#!/usr/bin/env python3
"""Rerun registered FAM-01--FAM-06 under the rebuilt treatment contract."""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import pathlib
import sys

import numpy as np
import pandas as pd


HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[5]
CONTRACT = "rebuilt_corrected_preperiod_weight"
EXPECTED_BASELINE = -0.1321094507921903
EXPECTED_MEMBERSHIP_HASH = "c76eb85956e4a413e130bab53fe8c50616cf6d7a02c81c266ec369879dd56bc1"


def import_path(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import {}".format(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


WF = import_path(
    "yax_rebuilt_family_harmonization_source",
    ROOT / "yax/revision/substantive_r3_20260905/within_family/run_within_family.py",
)


def read_membership(path: pathlib.Path) -> pd.DataFrame:
    if WF.sha256(path) != EXPECTED_MEMBERSHIP_HASH:
        raise RuntimeError("rebuilt membership hash changed")
    frame = pd.read_csv(path, dtype={"occupation_code": str})
    required = {
        "occupation_code", "preperiod_weight", "rule_A_beta", "beta_quintile",
        "webb_pct_software", "webb_z",
    }
    if not required.issubset(frame.columns):
        raise RuntimeError("rebuilt membership lacks required fields")
    frame["occupation_code"] = frame.occupation_code.str.zfill(4)
    if len(frame) != 468 or frame.occupation_code.duplicated().any():
        raise RuntimeError("rebuilt membership is not the expected 468-code support")
    if set(frame.beta_quintile.astype(int)) != {1, 2, 3, 4, 5}:
        raise RuntimeError("rebuilt membership lacks five quintiles")
    return frame


def aggregate_tail_paths(cells, membership: pd.DataFrame):
    support = membership.occupation_code.tolist()
    months = [month for month in sorted(cells.month.unique()) if month != "2022-12"]
    if len(months) != 113 or "2025-10" in months:
        raise RuntimeError("rebuilt tail path calendar is not the corrected 113 months")
    young, older = WF.CELLS.panel_for_ages(cells, support, months, (22, 25), (26, 65))
    quintiles = membership.beta_quintile.astype(int).to_numpy()
    pre = np.array([month <= "2022-11" for month in months])
    rows = []
    for quintile in (1, 5):
        keep = quintiles == quintile
        young_stock = young[keep].sum(axis=0)
        older_stock = older[keep].sum(axis=0)
        young_pre_mean = float(young_stock[pre].mean())
        older_pre_mean = float(older_stock[pre].mean())
        for index, month in enumerate(months):
            y_value = float(young_stock[index])
            o_value = float(older_stock[index])
            if y_value <= 0 or o_value <= 0:
                raise RuntimeError("nonpositive aggregate tail stock in {} Q{}".format(
                    month, quintile,
                ))
            rows.append({
                "treatment_contract": CONTRACT,
                "month": month,
                "tail": "Q{}".format(quintile),
                "support_occupations": int(keep.sum()),
                "young_age_group": "22-25",
                "older_age_group": "26-65",
                "young_weighted_employment_stock": y_value,
                "older_weighted_employment_stock": o_value,
                "young_to_older_stock_ratio": y_value / o_value,
                "log_young_to_older_stock_ratio": math.log(y_value / o_value),
                "young_preperiod_mean_index_100": 100.0 * y_value / young_pre_mean,
                "older_preperiod_mean_index_100": 100.0 * o_value / older_pre_mean,
                "public_aggregate_only": True,
                "interval_note": (
                    "descriptive survey-weighted aggregate path; no person or "
                    "occupation-month cell and no design-based interval"
                ),
            })
    return rows


def run(args) -> None:
    membership = read_membership(args.rebuilt_membership)
    member_index = membership.set_index("occupation_code", drop=False)
    captured = {}

    original_load_data = WF.CORE.load_data
    original_primary_setup = WF.COMP.primary_setup
    original_build_cells = WF.CELLS.build_exact_age_cells
    original_write_csv = WF.write_csv
    original_write_json = WF.write_json
    original_build_findings = WF.build_findings

    def patched_load_data(load_args):
        data = original_load_data(load_args)
        data["exposures"]["dv_rating_beta"]["A"] = {
            code: float(value) for code, value in
            zip(membership.occupation_code, membership.rule_A_beta)
        }
        data["computers"]["webb_pct_software"] = {
            code: float(value) for code, value in
            zip(membership.occupation_code, membership.webb_pct_software)
        }
        return data

    def patched_primary_setup(data, setup_args):
        prepared, _, majors, extra = original_primary_setup(data, setup_args)
        support = list(prepared["occupations"])
        if set(support) != set(membership.occupation_code) or len(support) != 468:
            raise RuntimeError("rebuilt and original common support differ")
        ordered = member_index.reindex(support)
        if ordered.isna().any(axis=None):
            raise RuntimeError("rebuilt membership failed support alignment")
        prepared = dict(prepared)
        prepared["weights"] = ordered.preperiod_weight.to_numpy(float)
        return prepared, ordered.beta_quintile.to_numpy(int), majors, extra

    def patched_build_cells(build_args):
        result = original_build_cells(build_args)
        captured["cells"] = result[0]
        return result

    def patched_write_csv(path, rows):
        labeled = []
        for row in rows:
            item = dict(row)
            item["treatment_contract"] = CONTRACT
            labeled.append(item)
        original_write_csv(path, labeled)

    def patched_build_findings(path, *values, **keywords):
        original_build_findings(path, *values, **keywords)
        original = path.read_text(encoding="utf-8")
        prefix = (
            "# Rebuilt-treatment contract harmonization\n\n"
            "All estimates below use `rebuilt_corrected_preperiod_weight`; "
            "historical-only FAM rows are excluded from revised main-text "
            "synthesis. Models, supports, seeds, and rules otherwise match the "
            "registered FAM-01--FAM-06 implementation.\n\n"
        )
        path.write_text(prefix + original, encoding="utf-8")

    def patched_write_json(path, value):
        if path.name == "EXECUTION_RECEIPT.json":
            if "cells" not in captured:
                raise RuntimeError("corrected cells were not captured for tail aggregation")
            tail_name = "REBUILT_Q1_Q5_AGGREGATE_PATHS.csv"
            patched_write_csv(
                path.parent / tail_name,
                aggregate_tail_paths(captured["cells"], membership),
            )
            value = dict(value)
            value["record"] = "YAX R3 FAM-01--FAM-06 rebuilt-treatment harmonization"
            value["treatment_contract"] = CONTRACT
            value["contract_harmonization_status"] = (
                "post-outcome rerun of identical registered models; no new specification"
            )
            value["historical_assignments_permitted_in_revised_main_text"] = False
            value["common_support_occupations"] = value.pop(
                "historical_support_occupations"
            )
            value["common_support_hash"] = value.pop("historical_support_hash")
            value["input_hashes"] = dict(value["input_hashes"])
            value["input_hashes"]["rebuilt_treatment_membership"] = WF.sha256(
                args.rebuilt_membership
            )
            value["aggregate_tail_path"] = {
                "file": tail_name,
                "rows": 226,
                "rule": (
                    "sum corrected monthly survey-weighted employment over all "
                    "rebuilt Q1 or Q5 occupations, separately for ages 22-25 and 26-65"
                ),
                "contains_person_or_occupation_month_cells": False,
            }
            value["implementation"] = dict(value["implementation"])
            value["implementation"]["source_historical_script"] = value["implementation"][
                "script"
            ]
            value["implementation"]["harmonization_wrapper"] = str(
                pathlib.Path(__file__).resolve().relative_to(ROOT)
            )
            value["implementation"]["harmonization_wrapper_sha256"] = WF.sha256(
                pathlib.Path(__file__).resolve()
            )
            value["implementation"]["harmonization_spec"] = str(
                (HERE / "ANALYSIS_SPEC_BEFORE_RESULTS.md").relative_to(ROOT)
            )
            value["implementation"]["harmonization_spec_sha256"] = WF.sha256(
                HERE / "ANALYSIS_SPEC_BEFORE_RESULTS.md"
            )
            value["output_hashes"] = dict(value["output_hashes"])
            value["output_hashes"][tail_name] = WF.sha256(path.parent / tail_name)
        original_write_json(path, value)

    WF.CORE.load_data = patched_load_data
    WF.COMP.primary_setup = patched_primary_setup
    WF.CELLS.build_exact_age_cells = patched_build_cells
    WF.write_csv = patched_write_csv
    WF.write_json = patched_write_json
    WF.build_findings = patched_build_findings
    WF.EXPECTED_CORRECTED = EXPECTED_BASELINE
    WF.run(args)
    print(json.dumps({
        "status": "PASS_REBUILT_FAMILY_CONTRACT_HARMONIZATION",
        "treatment_contract": CONTRACT,
        "membership_sha256": WF.sha256(args.rebuilt_membership),
        "output_dir": str(args.output_dir),
    }, indent=2, sort_keys=True))


def parser():
    value = WF.parser()
    value.description = __doc__
    value.add_argument("--rebuilt-membership", type=pathlib.Path, required=True)
    return value


if __name__ == "__main__":
    run(parser().parse_args())
