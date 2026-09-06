#!/usr/bin/env python3
"""Build machine-readable DATA-01/02/04 audits from corrected CPS cells."""
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


LABEL = "POST-OUTCOME DESCRIPTIVE AUDIT -- NOT PART OF CONFIRMATORY YAX v1.1"


def import_path(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: pathlib.Path, rows: list[dict]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def period_range(start: str, end: str) -> list[str]:
    return [str(value) for value in pd.period_range(start, end, freq="M")]


def distribution(values: np.ndarray, label: str) -> dict:
    flat = np.asarray(values, float).reshape(-1)
    positive = flat[flat > 0]
    return {
        "age_group": label,
        "grid_cells": int(flat.size),
        "zero_cells": int(np.sum(flat == 0)),
        "zero_share": float(np.mean(flat == 0)),
        "below_five_share": float(np.mean(flat < 5)),
        "p10_all": float(np.quantile(flat, .10)),
        "median_all": float(np.quantile(flat, .50)),
        "p90_all": float(np.quantile(flat, .90)),
        "p10_positive": float(np.quantile(positive, .10)),
        "median_positive": float(np.quantile(positive, .50)),
        "p90_positive": float(np.quantile(positive, .90)),
        "sum": float(flat.sum()),
    }


def run(args: argparse.Namespace) -> None:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cells_module = import_path(
        "yax_r3_data_cells",
        args.repo_root / "yax/revision/referee_20260905/run_referee_cells.py",
    )
    cells, _, build = cells_module.build_exact_age_cells(args)
    contracts = pd.read_csv(args.contracts, dtype={"occupation_code": str})
    contracts["occupation_code"] = contracts.occupation_code.str.zfill(4)
    support = sorted(contracts.loc[
        contracts.contract.eq("historical_production_full_static_weight"),
        "occupation_code",
    ].unique())
    if len(support) != 468:
        raise RuntimeError(f"primary support changed: {len(support)}")

    observed = sorted(cells.month.unique())
    static = [month for month in observed if month != "2022-12"]
    expected = period_range("2017-01", "2026-07")
    observed_set, static_set = set(observed), set(static)
    calendar_rows = []
    for month in expected:
        if month == "2025-10":
            reason = "source survey month absent; never interpolated"
        elif month == "2022-12":
            reason = "observed transition month excluded from static model"
        else:
            reason = "retained static month"
        calendar_rows.append({
            "month": month,
            "observed_in_source": month in observed_set,
            "retained_in_static_model": month in static_set,
            "reason": reason,
        })
    write_csv(args.output_dir / "CALENDAR_AUDIT.csv", calendar_rows)

    young_stock, older_stock = cells_module.panel_for_ages(
        cells, support, static, (22, 25), (26, 65), "stock"
    )
    young_re, older_re = cells_module.panel_for_ages(
        cells, support, static, (22, 25), (26, 65), "respondent_equivalent"
    )
    distributions = [
        distribution(young_re, "young_22_25"),
        distribution(older_re, "older_26_65"),
        distribution(np.concatenate([young_re.reshape(-1), older_re.reshape(-1)]),
                     "pooled_age_cells"),
    ]
    for row in distributions:
        row.update({
            "analysis_status": LABEL,
            "count_definition": (
                "fractional routed-record equivalents before 2020; exact records from 2020 onward"
            ),
            "months": len(static),
            "occupations": len(support),
        })
    write_csv(args.output_dir / "CELL_COUNT_DISTRIBUTION.csv", distributions)

    total = young_stock + older_stock
    one_sided = ((young_stock == 0) ^ (older_stock == 0))
    both_zero = total == 0
    flow_rows = [
        {"stage": "raw_rows_scanned_across_both_files", "count": build["rows_read"],
         "unit": "source rows", "note": "includes explicitly superseded 03s rows"},
        {"stage": "eligible_employed_age_18_65_positive_weight", "count": build["employed_age_18_65_records"],
         "unit": "source records", "note": "after explicit March replacement and eligibility"},
        {"stage": "fractional_routed_descendants", "count": build["routed_rows"],
         "unit": "route-expanded rows", "note": "not distinct respondents"},
        {"stage": "routed_age_level_aggregates", "count": build["routed_aggregate_rows"],
         "unit": "occupation-month-age-route-industry aggregates", "note": "before headline age pooling"},
        {"stage": "complete_primary_grid", "count": int(total.size),
         "unit": "occupation-month cells", "note": "468 occupations by 113 static months"},
        {"stage": "positive_total_fitted_cells", "count": int(np.sum(total > 0)),
         "unit": "occupation-month cells", "note": "likelihood rows"},
        {"stage": "one_sided_zero_cells_retained", "count": int(np.sum(one_sided)),
         "unit": "occupation-month cells", "note": "valid boundary outcomes"},
        {"stage": "both_zero_grid_cells_no_likelihood_contribution", "count": int(np.sum(both_zero)),
         "unit": "occupation-month cells", "note": "counted in grid; absent from fitted rows"},
    ]
    write_csv(args.output_dir / "SAMPLE_FLOW_CORRECTED.csv", flow_rows)

    universe = pd.read_csv(args.universe, dtype={"occupation_code": str})
    universe["occupation_code"] = universe.occupation_code.str.zfill(4)
    universe.to_csv(args.output_dir / "SUPPORT_AND_EXCLUSIONS.csv", index=False)
    exclusions = universe.loc[~universe.eligible.astype(bool), "exclusion_reasons"].fillna("eligible").value_counts()
    exclusion_rows = [{"exclusion_reason": reason, "occupation_count": int(count)}
                      for reason, count in exclusions.items()]
    write_csv(args.output_dir / "EXCLUSION_REASON_COUNTS.csv", exclusion_rows)

    route = json.loads(args.route_receipt.read_text(encoding="utf-8"))
    route_audit = {
        "analysis_status": LABEL,
        "route_receipt_sha256": sha256(args.route_receipt),
        "route_conservation_pass": bool(route["route_conservation_pass"]),
        "early_relative_gap": route["early_relative_gap"],
        "current_relative_gap": route["current_relative_gap"],
        "early_valid_stock_route_coverage": route["early_valid_stock_route_coverage"],
        "one_to_many_source_codes": build["one_to_many_source_codes"],
        "maximum_source_multiplicity": build["maximum_source_multiplicity"],
        "weight_application": (
            "source WTFINL enters stock once; pre-2020 bridge shares partition each source stock"
        ),
        "respondent_equivalent_definition": (
            "sum of bridge shares before 2020 and unit records from 2020 onward; not distinct respondents"
        ),
    }
    (args.output_dir / "WEIGHT_AND_ROUTE_AUDIT.json").write_text(
        json.dumps(route_audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    output_hashes = {
        path.name: sha256(path) for path in sorted(args.output_dir.iterdir())
        if path.is_file() and path.name not in {"EXECUTION_RECEIPT.json", "SELF_CHECK.json"}
    }
    receipt = {
        "analysis_status": LABEL,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=args.repo_root, text=True
        ).strip(),
        "script_sha256": sha256(pathlib.Path(__file__)),
        "input_hashes": {
            "wide_microdata": sha256(args.microdata),
            "march_repair": sha256(args.repair_microdata),
            "bridge": sha256(args.bridge),
            "contracts": sha256(args.contracts),
            "universe": sha256(args.universe),
            "route_receipt": sha256(args.route_receipt),
        },
        "calendar": {"expected": len(expected), "observed": len(observed), "static": len(static)},
        "support_occupations": len(support),
        "cell_build_receipt": build,
        "output_hashes": output_hashes,
    }
    (args.output_dir / "EXECUTION_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": "PASS_DATA_AUDIT", "static_months": len(static),
                      "support": len(support), "fitted_cells": int(np.sum(total > 0))}, indent=2))


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--repo-root", type=pathlib.Path, required=True)
    value.add_argument("--microdata", type=pathlib.Path, required=True)
    value.add_argument("--repair-microdata", type=pathlib.Path, required=True)
    value.add_argument("--bridge", type=pathlib.Path, required=True)
    value.add_argument("--contracts", type=pathlib.Path, required=True)
    value.add_argument("--universe", type=pathlib.Path, required=True)
    value.add_argument("--route-receipt", type=pathlib.Path, required=True)
    value.add_argument("--output-dir", type=pathlib.Path, required=True)
    return value


if __name__ == "__main__":
    run(parser().parse_args())
