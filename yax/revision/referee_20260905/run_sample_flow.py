#!/usr/bin/env python3
"""Reconcile the 463/468/465/444 YAX universes from the corrected raw calendar.

POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1.  The output
contains aggregates only.  Raw IPUMS records remain in the private SCC path.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd


HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[3]
LABEL = "POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1"
MEASURES = (
    "aioe_admin_equal", "aioe_ability_direct", "aioe_oews2018_source_weighted",
    "dv_rating_alpha", "dv_rating_beta", "dv_rating_gamma",
)


def import_path(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CELLS = import_path("yax_revision_sample_cells", HERE / "run_referee_cells.py")
P3 = import_path("yax_revision_sample_p3", ROOT / "yax/analysis/postoutcome_phase3_final/run_phase3.py")


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: pathlib.Path, rows: list[dict]) -> None:
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def summarize(cells: pd.DataFrame, support: list[str], months: list[str],
              base_arrays: dict[str, tuple[np.ndarray, np.ndarray]], definition: str) -> dict:
    stock_y, stock_o = CELLS.panel_for_ages(cells, support, months, (22, 25), (26, 65))
    resp_y, resp_o = CELLS.panel_for_ages(
        cells, support, months, (22, 25), (26, 65), "respondent_equivalent"
    )
    pre = np.array([month < "2023-01" for month in months])
    post = ~pre
    row = {
        "analysis_status": LABEL,
        "universe": definition,
        "occupations": len(support),
        "months": len(months),
        "potential_occupation_month_cells": len(support) * len(months),
        "nonempty_occupation_month_cells": int(np.sum((stock_y + stock_o) > 0)),
        "zero_young_cells": int(np.sum(stock_y == 0)),
        "zero_older_cells": int(np.sum(stock_o == 0)),
        "empty_both_cells": int(np.sum((stock_y + stock_o) == 0)),
        "respondent_equivalent_young": float(resp_y.sum()),
        "respondent_equivalent_older": float(resp_o.sum()),
        "weighted_young_stock": float(stock_y.sum()),
        "weighted_older_stock": float(stock_o.sum()),
    }
    for period, mask in (("pre", pre), ("post", post)):
        for age, array in (("young", stock_y), ("older", stock_o)):
            numerator = float(array[:, mask].sum())
            denominator = float(base_arrays[period][0 if age == "young" else 1].sum())
            row[f"{period}_{age}_weighted_stock"] = numerator
            row[f"{period}_{age}_employment_coverage"] = numerator / denominator
    return row


def run(args: argparse.Namespace) -> None:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cells, _, build = CELLS.build_exact_age_cells(args)
    setup = CELLS.primary_setup(args, cells)
    months = setup["frozen_static"]
    pre = np.array([month < "2023-01" for month in months])
    post = ~pre

    pre_frame = setup["frozen_pre"]
    base = sorted(set(pre_frame.index.get_level_values("occ_code")))
    base_y, base_o = CELLS.panel_for_ages(cells, base, months, (22, 25), (26, 65))
    base_arrays = {
        "pre": (base_y[:, pre], base_o[:, pre]),
        "post": (base_y[:, post], base_o[:, post]),
    }
    exposure = setup["exposures"]
    computers = setup["computers"]
    primary = setup["support"]
    onet = sorted(
        code for code in base
        if np.isfinite(exposure["dv_rating_beta"]["A"].get(code, np.nan))
        and np.isfinite(computers["onet_computers_importance"].get(code, np.nan))
    )
    common = sorted(
        code for code in base
        if np.isfinite(computers["webb_pct_software"].get(code, np.nan))
        and all(np.isfinite(exposure[m]["A"].get(code, np.nan)) for m in MEASURES)
    )
    reference, _ = P3.load_reference_components(args.characteristics)
    treatment_reference = sorted(reference.census2018.astype(str).str.zfill(4).unique())
    if (len(treatment_reference), len(primary), len(onet), len(common)) != (463, 468, 465, 444):
        raise RuntimeError(
            "named universe counts changed: "
            f"{len(treatment_reference)}, {len(primary)}, {len(onet)}, {len(common)}"
        )

    definitions = [
        (treatment_reference, "treatment_side_complete_characteristics_reference_463"),
        (primary, "primary_beta_plus_Webb_468"),
        (onet, "beta_plus_ONET_computer_importance_465"),
        (common, "literal_six_AI_measures_plus_Webb_444"),
    ]
    rows = []
    for support, name in definitions:
        row = summarize(cells, support, months, base_arrays, name)
        row["base_candidate_occupations"] = len(base)
        row["occupation_exclusions_from_base"] = len(set(base) - set(support))
        row["support_definition"] = {
            definitions[0][1]: "complete six-score and occupational-characteristic treatment-side reference",
            definitions[1][1]: "strict beta exposure and finite Webb software score",
            definitions[2][1]: "strict beta exposure and finite O*NET computer-use importance",
            definitions[3][1]: "finite strict scores for all six selected implementations and Webb software",
        }[name]
        rows.append(row)
    write_csv(args.output_dir / "UNIFIED_SAMPLE_FLOW.csv", rows)
    receipt = {
        "analysis_status": LABEL,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "universe_counts_verified": [463, 468, 465, 444],
        "months": months,
        "base_candidate_occupations": len(base),
        "raw_build": build,
        "input_hashes": {
            "microdata": sha256(args.microdata),
            "repair_microdata": sha256(args.repair_microdata),
            "preperiod_cells": sha256(args.preperiod_cells),
            "lookup": sha256(args.lookup),
            "computerization": sha256(args.computerization),
            "bridge": sha256(args.bridge),
        },
        "output_sha256": sha256(args.output_dir / "UNIFIED_SAMPLE_FLOW.csv"),
        "record_count_note": (
            "Pre-2020 one-to-many routes make unweighted_n a respondent-equivalent count after routing; "
            "the source-record audit remains in the corrected-calendar receipt."
        ),
    }
    (args.output_dir / "UNIFIED_SAMPLE_FLOW_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": "PASS_SAMPLE_FLOW", "counts": [len(x[0]) for x in definitions]}, indent=2))


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--microdata", type=pathlib.Path, required=True)
    value.add_argument("--repair-microdata", type=pathlib.Path, required=True)
    value.add_argument("--preperiod-cells", type=pathlib.Path, required=True)
    value.add_argument("--lookup", type=pathlib.Path, default=ROOT / "yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv")
    value.add_argument("--computerization", type=pathlib.Path, default=ROOT / "yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv")
    value.add_argument("--computerization-2010", type=pathlib.Path, default=ROOT / "yax/measurement/COMPUTERIZATION_MEASURES.csv")
    value.add_argument("--rule-b-values", type=pathlib.Path, default=ROOT / "yax/measurement/RULE_B_VALUES_CENSUS2018.csv")
    value.add_argument("--bridge", type=pathlib.Path, default=ROOT / "yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv")
    value.add_argument("--first-access-receipt", type=pathlib.Path, default=ROOT / "yax/analysis/FIRST_OUTCOME_ACCESS_RECEIPT.json")
    value.add_argument("--characteristics", type=pathlib.Path, default=ROOT / "yax/measurement/test_a/TEST_A_OCCUPATION_CHARACTERISTICS.csv")
    value.add_argument("--output-dir", type=pathlib.Path, required=True)
    return value


if __name__ == "__main__":
    run(parser().parse_args())
