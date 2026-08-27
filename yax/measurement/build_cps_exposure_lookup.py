#!/usr/bin/env python3
"""Build a measurement-only Census occupation exposure lookup for CPS.

The main lookup uses raw CPS OCC: Census 2010 codes in 2017--2019 are
bridged with the Census Bureau's official conversion rates, while Census 2018
codes in 2020 onward are matched directly. Harmonized IPUMS OCC2010 is emitted
as a separately labelled sensitivity and must not replace observed post-2020
raw OCC. No CPS microdata are read by this builder.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "dax/w2/crosswalk"))
from build_occ2010_crosswalk import (  # noqa: E402
    add_ipums_single_source_fallbacks,
    census_routes,
    read_census_crosswalk,
    read_ipums_occ2010_crosswalk,
    read_total_conversion_rates,
)


VARIANTS = (
    "aioe_admin_equal",
    "aioe_ability_direct",
    "aioe_oews2018_source_weighted",
    "dv_rating_alpha",
    "dv_rating_beta",
    "dv_rating_gamma",
    "dingel_neiman_telework",
)

AI_EXPOSURE_VARIANTS = VARIANTS[:-1]
REMOTE_WORK_MEASURE = VARIANTS[-1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def route_entropy(weights: list[float]) -> float:
    return -sum(weight * math.log(weight) for weight in weights if weight > 0)


def ambiguity_status(weights: list[float]) -> str:
    if len(weights) == 1:
        return "one_to_one"
    if max(weights) >= 0.90:
        return "one_to_many_dominant_route"
    return "one_to_many_diffuse"


def aggregate_routes(
    old_code: str,
    routes: list[tuple[str, str, float]],
    exposure_by_target: dict[str, dict[str, float]],
    route_source: str,
) -> dict[str, object]:
    weights = [weight for _, _, weight in routes]
    row: dict[str, object] = {
        "occ_code": old_code,
        "n_routes": len(routes),
        "max_route_weight": max(weights),
        "route_entropy": route_entropy(weights),
        "ambiguity_status": ambiguity_status(weights),
        "bridge_source": route_source,
    }
    for variant in VARIANTS:
        covered_mass = 0.0
        partial_sum = 0.0
        for target, _, weight in routes:
            target_row = exposure_by_target.get(target, {})
            value = target_row.get(variant)
            target_coverage = target_row.get(
                f"{variant}_target_soc_covered_weight"
            )
            target_partial = target_row.get(
                f"{variant}_target_soc_partial_weighted_sum"
            )
            if target_coverage is None or pd.isna(target_coverage):
                target_coverage = (
                    1.0 if value is not None and not pd.isna(value) else 0.0
                )
            if target_partial is None or pd.isna(target_partial):
                target_partial = (
                    float(value)
                    if value is not None and not pd.isna(value)
                    else None
                )
            covered_mass += weight * float(target_coverage)
            if target_partial is not None:
                partial_sum += weight * float(target_partial)
        row[f"{variant}_covered_route_mass"] = covered_mass
        row[f"{variant}_partial_weighted_sum"] = (
            partial_sum if covered_mass > 0 else None
        )
        # Fail closed: never renormalize the observed children around a gap.
        row[variant] = partial_sum if abs(covered_mass - 1.0) <= 1e-9 else None
    return row


def build_tables(
    variants: pd.DataFrame,
    rates_path: Path,
    census_path: Path,
    ipums_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    required = {"census_2018", *VARIANTS}
    missing = required - set(variants.columns)
    if missing:
        raise ValueError(f"exposure variants missing columns {sorted(missing)}")
    variants = variants.copy()
    variants["census_2018"] = variants.census_2018.astype(str).str.zfill(4)
    if variants.census_2018.duplicated().any():
        raise ValueError("duplicate Census 2018 exposure codes")
    exposure_by_target = variants.set_index("census_2018").to_dict("index")

    rates = read_total_conversion_rates(rates_path)
    census_crosswalk = read_census_crosswalk(census_path)
    routes = census_routes(census_crosswalk, rates)
    official_codes = set(routes)
    ipums = read_ipums_occ2010_crosswalk(ipums_path)
    fallback_codes = add_ipums_single_source_fallbacks(
        routes, ipums, census_crosswalk[1]
    )
    rate_codes = {old for old, _ in rates}

    bridge_rows = []
    old_lookup_rows = []
    for old_code, old_routes in sorted(routes.items()):
        if old_code in fallback_codes:
            source = "ipums_unambiguous_fallback"
        elif old_code in rate_codes:
            source = "census_official_conversion_rate"
        elif old_code in official_codes:
            source = "census_official_one_to_one"
        else:  # Defensive; every route must have named provenance.
            raise AssertionError(f"unnamed route provenance for {old_code}")
        summary = aggregate_routes(old_code, old_routes, exposure_by_target, source)
        old_lookup_rows.append(summary)
        status = summary["ambiguity_status"]
        for target, soc_pattern, weight in old_routes:
            detail = {
                "census_2010": old_code,
                "census_2018": target,
                "soc_2018_pattern": soc_pattern,
                "bridge_weight": weight,
                "bridge_source": source,
                "n_routes": len(old_routes),
                "max_route_weight": summary["max_route_weight"],
                "route_entropy": summary["route_entropy"],
                "ambiguity_status": status,
            }
            detail.update(exposure_by_target.get(target, {}))
            bridge_rows.append(detail)

    old_lookup = pd.DataFrame(old_lookup_rows)
    main_old = old_lookup.assign(
        lookup_role="raw_occ_main_2017_2019", occ_vintage="census_2010"
    )
    sensitivity = old_lookup.assign(
        lookup_role="occ2010_sensitivity_all_years",
        occ_vintage="ipums_occ2010_harmonized",
    )

    direct_rows = []
    # Emit the full official Census-2018 code universe, including explicit
    # zero-coverage rows. Otherwise a later merge could silently discard an
    # occupation absent from every exposure construction.
    direct_codes = sorted(set(census_crosswalk[1]) | set(exposure_by_target))
    for code in direct_codes:
        out = aggregate_routes(
            code,
            [(code, census_crosswalk[1].get(code, ""), 1.0)],
            exposure_by_target,
            "none_direct_census_2018",
        )
        out.update({
            "ambiguity_status": "direct_observed_code",
            "lookup_role": "raw_occ_main_2020_plus",
            "occ_vintage": "census_2018",
        })
        direct_rows.append(out)

    lookup = pd.concat(
        [main_old, pd.DataFrame(direct_rows), sensitivity], ignore_index=True
    )
    leading = [
        "lookup_role",
        "occ_vintage",
        "occ_code",
        "bridge_source",
        "n_routes",
        "max_route_weight",
        "route_entropy",
        "ambiguity_status",
    ]
    lookup = lookup[leading + [
        column for variant in VARIANTS for column in (
            variant,
            f"{variant}_covered_route_mass",
            f"{variant}_partial_weighted_sum",
        )
    ]].sort_values(["lookup_role", "occ_code"])
    bridge = pd.DataFrame(bridge_rows).sort_values(
        ["census_2010", "census_2018"]
    )
    return bridge, lookup


def coverage_summary(lookup: pd.DataFrame) -> dict[str, object]:
    result: dict[str, object] = {}
    for role, group in lookup.groupby("lookup_role", sort=True):
        result[role] = {
            "codes": int(len(group)),
            "ambiguity_status": {
                key: int(value)
                for key, value in group.ambiguity_status.value_counts().items()
            },
            "variants": {
                variant: {
                    "full_coverage_codes": int(group[variant].notna().sum()),
                    "partial_or_full_coverage_codes": int(
                        group[f"{variant}_covered_route_mass"].gt(0).sum()
                    ),
                    "zero_coverage_codes": int(
                        group[f"{variant}_covered_route_mass"].eq(0).sum()
                    ),
                }
                for variant in VARIANTS
            },
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variants", type=Path, required=True)
    parser.add_argument("--rates", type=Path, required=True)
    parser.add_argument("--census-crosswalk", type=Path, required=True)
    parser.add_argument("--ipums-crosswalk", type=Path, required=True)
    parser.add_argument("--bridge-output", type=Path, required=True)
    parser.add_argument("--lookup-output", type=Path, required=True)
    parser.add_argument("--receipt-output", type=Path, required=True)
    args = parser.parse_args()

    variants = pd.read_csv(args.variants, dtype={"census_2018": str})
    bridge, lookup = build_tables(
        variants, args.rates, args.census_crosswalk, args.ipums_crosswalk
    )
    bridge.to_csv(args.bridge_output, index=False, float_format="%.12g")
    lookup.to_csv(args.lookup_output, index=False, float_format="%.12g")
    receipt = {
        "record_version": "dax-cps-occupation-exposure-lookup-v1",
        "status": "PASS",
        "gate": "vintage_aware_cps_occupation_exposure_lookup",
        "outcome_fields_read": False,
        "scope": "measurement only; no CPS microdata or outcomes read",
        "design": {
            "main_2017_2019": "raw OCC on Census 2010 basis, official conversion-rate bridge",
            "main_2020_plus": "raw OCC on Census 2018 basis, direct match",
            "sensitivity": "harmonized OCC2010 only; never substitutes for observed post-2020 raw OCC",
            "missing_child_rule": "fail closed; partial sums reported, no renormalization around missing target exposure",
            "exposure_variants": list(VARIANTS),
            "primary_exposure": "dv_rating_beta",
            "remote_work_control": REMOTE_WORK_MEASURE,
            "eloundou_notation": {
                "source_column": "dv_rating_gamma",
                "paper_symbol": "zeta",
                "definition": "E1 + E2",
                "rule": "preserve source column name; do not duplicate as a numerical alias",
            },
        },
        "inputs": {
            str(path): sha256(path)
            for path in (
                args.variants,
                args.rates,
                args.census_crosswalk,
                args.ipums_crosswalk,
            )
        },
        "outputs": {
            str(args.bridge_output): {
                "sha256": sha256(args.bridge_output),
                "rows": int(len(bridge)),
            },
            str(args.lookup_output): {
                "sha256": sha256(args.lookup_output),
                "rows": int(len(lookup)),
            },
        },
        "coverage": coverage_summary(lookup),
    }
    args.receipt_output.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
