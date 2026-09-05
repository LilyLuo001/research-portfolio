#!/usr/bin/env python3
"""Audit the January-2025 CPS population-control break in the YAX stock design.

POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1.

The program does not manufacture counterfactual person weights.  It compares
the official-weight design with respondent-equivalent cells, reports a
pre-January-2025 endpoint, and estimates early/late post-period coefficients
in one joint model using the repaired 113-month calendar.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd


HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
LABEL = "POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1"
DRAWS = 9999
SEED = 2026090521
Z975 = 1.959963984540054
Z80 = 0.8416212335729143


def import_path(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CORE = import_path("yax_r2_pc_core", ROOT / "yax/revision/referee_20260905/run_referee_core.py")
CELLS = import_path("yax_r2_pc_cells", ROOT / "yax/revision/referee_20260905/run_referee_cells.py")
FROZEN = CORE.FROZEN


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: pathlib.Path, rows: list[dict]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty output {path}")
    fields: list[str] = []
    for row in rows:
        fields.extend(key for key in row if key not in fields)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: pathlib.Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def summarize(fit, influence: np.ndarray, contrast: np.ndarray,
              signs: np.ndarray, label: str) -> tuple[dict, np.ndarray]:
    estimate = float(contrast @ fit.beta)
    vector = influence @ contrast
    centered = signs @ vector
    se = float(np.sqrt(np.sum(np.square(vector))))
    try:
        critical = float(np.quantile(np.abs(centered / se), .95, method="higher"))
    except TypeError:
        critical = float(np.quantile(np.abs(centered / se), .95, interpolation="higher"))
    return ({
        "analysis_status": LABEL,
        "specification": label,
        "coefficient": estimate,
        "occupation_cluster_se": se,
        "ci_lower": estimate - critical * se,
        "ci_upper": estimate + critical * se,
        "wild_score_p_value": float(
            (1 + np.sum(np.abs(centered / se) >= abs(estimate / se))) / (len(centered) + 1)
        ),
        "wild_score_critical": critical,
        "normal_theory_mde80": (Z975 + Z80) * se,
        "bootstrap_draws": len(centered),
    }, centered)


def arrays(cells: pd.DataFrame, setup: dict, months: list[str], value: str):
    support = setup["support"]
    young, older = CELLS.panel_for_ages(
        cells, support, months, (22, 25), (26, 65), value=value
    )
    valid = ((young + older).sum(axis=1) > 0)
    if not np.all(valid):
        raise RuntimeError(f"{value} loses {int((~valid).sum())} frozen-support occupations")
    return young, older


def static_fit(cells: pd.DataFrame, setup: dict, months: list[str], value: str,
               signs: np.ndarray, label: str) -> dict:
    young, older = arrays(cells, setup, months, value)
    fit, influence, labels, _ = CELLS.fit_q_model(
        young, older, setup["quintiles"], setup["webb_z"], months
    )
    target = labels.index("Q5_x_post_2023_2026")
    contrast = np.zeros(len(fit.beta)); contrast[target] = 1.0
    result, _ = summarize(fit, influence, contrast, signs, label)
    result.update({
        "cell_value": value,
        "months": len(months),
        "first_month": months[0],
        "last_month": months[-1],
        "support_occupations": len(setup["support"]),
        "quintiles_and_webb_scale": "frozen primary classification and scaling",
    })
    return result


def era_fit(cells: pd.DataFrame, setup: dict, months: list[str], value: str,
            signs: np.ndarray) -> list[dict]:
    young, older = arrays(cells, setup, months, value)
    periods = [
        ("post_2023_2024", np.array(["2023-01" <= month <= "2024-12" for month in months])),
        ("post_2025_2026", np.array([month >= "2025-01" for month in months])),
    ]
    fit, influence, labels, _ = CELLS.fit_q_model(
        young, older, setup["quintiles"], setup["webb_z"], months,
        period_masks=periods,
    )
    rows, centered = [], {}
    for period, _ in periods:
        target = labels.index(f"Q5_x_{period}")
        contrast = np.zeros(len(fit.beta)); contrast[target] = 1.0
        row, draws = summarize(fit, influence, contrast, signs, f"{value}_{period}")
        row.update({
            "cell_value": value,
            "period": period,
            "months_full_model": len(months),
            "support_occupations": len(setup["support"]),
        })
        rows.append(row)
        centered[period] = (row, draws, contrast)
    left, right = "post_2025_2026", "post_2023_2024"
    contrast = centered[left][2] - centered[right][2]
    row, _ = summarize(
        fit, influence, contrast, signs,
        f"{value}_{left}_minus_{right}",
    )
    row.update({
        "cell_value": value,
        "period": f"{left}_minus_{right}",
        "months_full_model": len(months),
        "support_occupations": len(setup["support"]),
        "paired_common_draws": True,
    })
    rows.append(row)
    return rows


def raw_monthly_contrasts(cells: pd.DataFrame, setup: dict,
                          months: list[str]) -> list[dict]:
    rows = []
    for value in ("stock", "respondent_equivalent"):
        young, older = arrays(cells, setup, months, value)
        q1, q5 = setup["quintiles"] == 1, setup["quintiles"] == 5
        for index, month in enumerate(months):
            quantities = [
                young[q5, index].sum(), older[q5, index].sum(),
                young[q1, index].sum(), older[q1, index].sum(),
            ]
            if min(quantities) <= 0:
                raw = float("nan")
            else:
                raw = math.log(quantities[0] / quantities[1]) - math.log(quantities[2] / quantities[3])
            rows.append({
                "analysis_status": LABEL,
                "month": month,
                "cell_value": value,
                "raw_log_young_older_Q5_minus_Q1": raw,
                "Q5_young": quantities[0], "Q5_older": quantities[1],
                "Q1_young": quantities[2], "Q1_older": quantities[3],
                "warning": "raw monthly ratio; no fixed effects, Webb adjustment, or seasonal adjustment",
            })
    return rows


def run(args: argparse.Namespace) -> None:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cells, _, build = CELLS.build_exact_age_cells(args)
    setup = CELLS.primary_setup(args, cells)
    corrected = [month for month in setup["observed_months"] if month != "2022-12"]
    through_2024 = [month for month in corrected if month <= "2024-12"]
    frozen = setup["frozen_static"]
    signs = np.random.default_rng(SEED).choice(
        np.array([-1.0, 1.0]), size=(DRAWS, len(setup["support"]))
    )

    static_rows = [
        static_fit(cells, setup, frozen, "stock", signs, "frozen_108_month_chronology_benchmark"),
        static_fit(cells, setup, corrected, "stock", signs, "repaired_113_month_substantive_baseline"),
        static_fit(cells, setup, through_2024, "stock", signs, "official_weights_endpoint_December_2024"),
        static_fit(cells, setup, corrected, "respondent_equivalent", signs,
                   "repaired_113_month_unweighted_respondent_equivalent"),
        static_fit(cells, setup, through_2024, "respondent_equivalent", signs,
                   "unweighted_endpoint_December_2024"),
    ]
    era_rows = era_fit(cells, setup, corrected, "stock", signs)
    era_rows.extend(era_fit(cells, setup, corrected, "respondent_equivalent", signs))
    monthly_rows = raw_monthly_contrasts(cells, setup, corrected)
    write_csv(args.output_dir / "POPULATION_CONTROL_STATIC_SENSITIVITIES.csv", static_rows)
    write_csv(args.output_dir / "POPULATION_CONTROL_ERA_COMPARISON.csv", era_rows)
    write_csv(args.output_dir / "RAW_MONTHLY_WEIGHTED_UNWEIGHTED_CONTRASTS.csv", monthly_rows)

    by_key = {(row["cell_value"], row["month"]): row for row in monthly_rows}
    discontinuities = []
    for value in ("stock", "respondent_equivalent"):
        december = by_key[(value, "2024-12")]["raw_log_young_older_Q5_minus_Q1"]
        january = by_key[(value, "2025-01")]["raw_log_young_older_Q5_minus_Q1"]
        discontinuities.append({
            "cell_value": value,
            "December_2024_raw_contrast": december,
            "January_2025_raw_contrast": january,
            "January_minus_December": january - december,
        })
    write_csv(args.output_dir / "JANUARY_2025_RAW_DISCONTINUITY.csv", discontinuities)

    receipt = {
        "record": "YAX January-2025 CPS population-control audit",
        "analysis_status": LABEL,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "support_occupations": len(setup["support"]),
        "bootstrap_seed": SEED,
        "bootstrap_draws": DRAWS,
        "raw_build_aggregate": {key: value for key, value in build.items() if key != "microdata_files"},
        "input_hashes": {
            "microdata": sha256(args.microdata),
            "repair_microdata": sha256(args.repair_microdata),
            "preperiod_cells": sha256(args.preperiod_cells),
            "lookup": sha256(args.lookup),
            "computerization": sha256(args.computerization),
            "bridge": sha256(args.bridge),
            "rule_b_values": sha256(args.rule_b_values),
        },
        "counterfactual_weight_series_constructed": False,
        "reason": (
            "The official BLS experimental January-2025 adjustment is an aggregate ratio series, "
            "not an age-by-occupation micro-weight bridge. Applying it to YAX cells would fabricate "
            "unpublished demographic and occupational allocation assumptions."
        ),
        "official_sources": [
            "https://www.bls.gov/cps/methods/population-controls/population-control-adjustments-2025.pdf",
            "https://www.bls.gov/cps/methods/population-controls/experimental-series-accounting-for-January-2025-population-control-effects.htm",
            "https://cps.ipums.org/cps-action/variables/170703",
        ],
        "protected_artifacts_modified": False,
    }
    write_json(args.output_dir / "POPULATION_CONTROL_AUDIT_RECEIPT.json", receipt)
    outputs = sorted(path for path in args.output_dir.iterdir() if path.is_file())
    write_json(args.output_dir / "OUTPUT_MANIFEST.json", {
        "output_hashes": {path.name: sha256(path) for path in outputs},
    })
    print(json.dumps({"status": "PASS_POPULATION_CONTROL_AUDIT", "rows": {
        "static": len(static_rows), "era": len(era_rows), "monthly": len(monthly_rows)
    }}, indent=2))


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--microdata", type=pathlib.Path, required=True)
    value.add_argument("--repair-microdata", type=pathlib.Path, required=True)
    value.add_argument("--preperiod-cells", type=pathlib.Path, required=True)
    value.add_argument("--lookup", type=pathlib.Path,
                       default=ROOT / "yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv")
    value.add_argument("--computerization", type=pathlib.Path,
                       default=ROOT / "yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv")
    value.add_argument("--computerization-2010", type=pathlib.Path,
                       default=ROOT / "yax/measurement/COMPUTERIZATION_MEASURES.csv")
    value.add_argument("--rule-b-values", type=pathlib.Path,
                       default=ROOT / "yax/measurement/RULE_B_VALUES_CENSUS2018.csv")
    value.add_argument("--bridge", type=pathlib.Path,
                       default=ROOT / "yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv")
    value.add_argument("--first-access-receipt", type=pathlib.Path,
                       default=ROOT / "yax/analysis/FIRST_OUTCOME_ACCESS_RECEIPT.json")
    value.add_argument("--output-dir", type=pathlib.Path, default=HERE / "results")
    return value


if __name__ == "__main__":
    run(parser().parse_args())
