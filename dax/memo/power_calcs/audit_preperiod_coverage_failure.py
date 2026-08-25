"""Annotate a failed pre-period exposure-coverage receipt with official titles."""

from __future__ import annotations

import argparse
import json
import pathlib

import pandas as pd


CURRENT_ROLE = "raw_occ_main_2020_plus"


def code4(value) -> str:
    if pd.isna(value):
        return ""
    try:
        return f"{int(float(value)):04d}"
    except (TypeError, ValueError):
        return str(value).strip().zfill(4)


def title_maps(workbook: pathlib.Path) -> tuple[dict[str, str], dict[str, str]]:
    current = pd.read_excel(
        workbook, sheet_name="Summary of 2018 Changes", header=2
    )
    current_titles = {
        code4(code): str(title).strip()
        for code, title in zip(
            current["2018 Census Code"], current["2018 Census Title "]
        )
        if code4(code)
    }
    crosswalk = pd.read_excel(
        workbook, sheet_name="2010 to 2018 Crosswalk ", header=3
    )
    source_titles = {
        code4(code): str(title).strip()
        for code, title in zip(
            crosswalk["2010 Census Code"], crosswalk["2010 Census Title \n"]
        )
        if code4(code)
    }
    return source_titles, current_titles


def build(receipt: dict, lookup: pd.DataFrame, workbook: pathlib.Path):
    source_titles, current_titles = title_maps(workbook)
    current = lookup.loc[lookup["lookup_role"] == CURRENT_ROLE].copy()
    current["occ_code"] = current["occ_code"].map(code4)
    current = current.set_index("occ_code")
    total_weight = receipt["excluded_total_weight"] / (
        1.0 - receipt["covered_route_mass_fraction"]
    )

    target_rows = []
    for row in receipt["largest_nonfull_exposure_target_codes"]:
        code = code4(row["occ_code"])
        info = current.loc[code] if code in current.index else None
        covered = (
            float(info["dv_rating_beta_covered_route_mass"])
            if info is not None
            and pd.notna(info["dv_rating_beta_covered_route_mass"])
            else 0.0
        )
        target_rows.append({
            "occupation_vintage": "Census 2018",
            "occ_code": code,
            "title": current_titles.get(code, "UNRESOLVED TITLE"),
            "excluded_weight": float(row["weight"]),
            "share_of_eligible_weight": float(row["weight"]) / total_weight,
            "share_of_excluded_exposure_weight": (
                float(row["weight"])
                / receipt["excluded_nonfull_exposure_weight"]
            ),
            "beta_covered_route_mass": covered,
            "beta_partial_weighted_sum": (
                float(info["dv_rating_beta_partial_weighted_sum"])
                if info is not None
                and pd.notna(info["dv_rating_beta_partial_weighted_sum"])
                else None
            ),
            "reason": (
                "zero target exposure coverage" if covered == 0
                else "partial target exposure coverage; fail-closed score"
            ),
        })

    source_rows = []
    for row in receipt["largest_missing_bridge_source_codes"]:
        code = code4(row["occ_code"])
        source_rows.append({
            "occupation_vintage": "Census 2010",
            "occ_code": code,
            "title": source_titles.get(code, "UNRESOLVED TITLE"),
            "excluded_weight": float(row["weight"]),
            "share_of_eligible_weight": float(row["weight"]) / total_weight,
            "reason": "no official conversion-rate route in frozen bridge",
        })
    return pd.DataFrame(target_rows), pd.DataFrame(source_rows), total_weight


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--lookup", type=pathlib.Path, required=True)
    parser.add_argument("--census-workbook", type=pathlib.Path, required=True)
    parser.add_argument("--output-prefix", type=pathlib.Path, required=True)
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    if receipt.get("status") != "FAIL_PRIMARY_EXPOSURE_COVERAGE":
        raise ValueError("audit requires a failed primary-coverage receipt")
    lookup = pd.read_csv(args.lookup, dtype={"occ_code": str})
    target, source, total_weight = build(receipt, lookup, args.census_workbook)
    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    target_path = args.output_prefix.with_name(args.output_prefix.name + "_target.csv")
    source_path = args.output_prefix.with_name(args.output_prefix.name + "_source.csv")
    summary_path = args.output_prefix.with_name(args.output_prefix.name + "_summary.json")
    target.to_csv(target_path, index=False)
    source.to_csv(source_path, index=False)
    summary = {
        "status": receipt["status"],
        "post_outcomes_read": receipt["post_outcomes_read"],
        "eligible_weight": total_weight,
        "covered_weight_fraction": receipt["covered_route_mass_fraction"],
        "threshold": receipt["minimum_coverage_threshold"],
        "gap_to_threshold_percentage_points": 100 * (
            receipt["minimum_coverage_threshold"]
            - receipt["covered_route_mass_fraction"]
        ),
        "excluded_nonfull_exposure_weight": receipt[
            "excluded_nonfull_exposure_weight"
        ],
        "missing_bridge_weight": receipt["missing_bridge_weight"],
        "top_target_codes_share_of_excluded_exposure_weight": float(
            target["excluded_weight"].sum()
            / receipt["excluded_nonfull_exposure_weight"]
        ),
        "target_rows": len(target),
        "source_rows": len(source),
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
