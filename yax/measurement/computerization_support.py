#!/usr/bin/env python3
"""Outcome-blind AI-versus-computerization support diagnostics.

The statistic that answers the design question is the employment-weighted
variance of AI exposure left after projecting it on a real computerization
measure.  This script reports that partial variance, its equivalent VIF and
standard-error inflation, and where the residual variance comes from.  It does
not estimate employment outcomes and contains no MDE calculation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import pathlib
from collections import defaultdict


AI_MEASURES = (
    "aioe_admin_equal",
    "aioe_ability_direct",
    "aioe_oews2018_source_weighted",
    "dv_rating_alpha",
    "dv_rating_beta",
    "dv_rating_gamma",
)
COMPUTERIZATION_MEASURES = (
    "webb_pct_software",
    "onet_computers_importance",
    "onet_computers_level",
    "rti_autor_dorn",
    "frey_osborne_probability",
)
LOOKUP_ROLE = "occ2010_sensitivity_all_years"
POST_START = "2022-12-01"


def sha256(path):
    digest = hashlib.sha256()
    with pathlib.Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rows(path):
    with pathlib.Path(path).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def number(value):
    text = "" if value is None else str(value).strip()
    return None if not text else float(text)


def preperiod_mass(path):
    mass = defaultdict(float)
    months = set()
    excluded_months = set()
    # Select only the three non-outcome columns by index.  The artifact also
    # carries employment-rate and hours fields; those columns are never
    # converted or accessed here, and rows at/after POST_START are rejected
    # before their survey weight enters the support distribution.
    with pathlib.Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        indices = {name: header.index(name) for name in ("cps_occ", "month", "weight_sum")}
        for raw in reader:
            month = raw[indices["month"]]
            if month >= POST_START:
                excluded_months.add(month)
                continue
            mass[raw[indices["cps_occ"]].zfill(4)] += float(raw[indices["weight_sum"]])
            months.add(month)
    return dict(mass), sorted(months), sorted(excluded_months)


def design_preperiod_mass(path, lookup_role):
    """Employment support for the frozen 66-month target-occupation panel.

    The input contract is already aggregated and pre-period-only.  We still
    reject rows at or after the event before reading their employment count.
    The two-age grouped-binomial estimator retains only occupations with
    positive total support in both age groups; this reproduces its 490-cluster
    support from the 492 codes present in the raw cell artifact.
    """
    by_age = defaultdict(lambda: defaultdict(float))
    months = set()
    excluded_months = set()
    with pathlib.Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"month", "lookup_role", "occ_code", "age_group",
                    "employment_headcount"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"design support missing fields {sorted(missing)}")
        for row in reader:
            month = row["month"] + ("-01" if len(row["month"]) == 7 else "")
            if month >= POST_START:
                excluded_months.add(month)
                continue
            if row["lookup_role"] != lookup_role:
                continue
            age = row["age_group"]
            if age not in {"young_22_25", "older_26_65"}:
                raise ValueError(f"unexpected age group {age!r}")
            by_age[row["occ_code"].zfill(4)][age] += float(row["employment_headcount"])
            months.add(month)
    raw_codes = len(by_age)
    mass = {
        code: values["young_22_25"] + values["older_26_65"]
        for code, values in by_age.items()
        if values["young_22_25"] > 0 and values["older_26_65"] > 0
    }
    return mass, sorted(months), sorted(excluded_months), {
        "raw_occupation_codes": raw_codes,
        "balanced_two_age_occupation_codes": len(mass),
        "balance_rule": "positive 66-month employment support in both age groups",
    }


def weighted_projection(x, c, w):
    total = sum(w)
    mean_x = sum(wi * xi for xi, wi in zip(x, w)) / total
    mean_c = sum(wi * ci for ci, wi in zip(c, w)) / total
    sxx = sum(wi * (xi - mean_x) ** 2 for xi, wi in zip(x, w))
    scc = sum(wi * (ci - mean_c) ** 2 for ci, wi in zip(c, w))
    sxc = sum(wi * (xi - mean_x) * (ci - mean_c)
              for xi, ci, wi in zip(x, c, w))
    if sxx <= 0 or scc <= 0:
        raise ValueError("zero weighted variance in support diagnostic")
    slope = sxc / scc
    intercept = mean_x - slope * mean_c
    residual = [xi - intercept - slope * ci for xi, ci in zip(x, c)]
    residual_ss = sum(wi * ri * ri for ri, wi in zip(residual, w))
    partial = residual_ss / sxx
    r = sxc / math.sqrt(sxx * scc)
    vif = 1.0 / partial
    return {
        "correlation": r,
        "r_squared": 1.0 - partial,
        "partial_variance_of_ai": partial,
        "vif": vif,
        "se_inflation": math.sqrt(vif),
        "residual": residual,
        "contribution": [wi * ri * ri for ri, wi in zip(residual, w)],
        "residual_sd": math.sqrt(residual_ss / total),
    }


def analyse_pair(ai_name, comp_name, ai, comp, mass, total_mass, top_k=15):
    codes = sorted(set(ai) & set(comp) & set(mass))
    x, c, w = ([ai[code] for code in codes], [comp[code][comp_name] for code in codes],
               [mass[code] for code in codes])
    fit = weighted_projection(x, c, w)
    contributions = fit.pop("contribution")
    residuals = fit.pop("residual")
    contribution_total = sum(contributions)
    effective_n = ((contribution_total ** 2 / sum(value ** 2 for value in contributions))
                   if contribution_total else None)

    by_group = defaultdict(float)
    for code, value in zip(codes, contributions):
        by_group[comp[code].get("soc_major_group") or "unknown"] += value
    group_shares = [
        {"soc_major_group": group, "residual_variance_share": value / contribution_total,
         "n_occupations": sum((comp[code].get("soc_major_group") or "unknown") == group
                              for code in codes)}
        for group, value in sorted(by_group.items(), key=lambda item: -item[1])
    ]

    def named(indices):
        result = []
        for i in indices:
            code = codes[i]
            result.append({
                "cps_occ2010": code,
                "occupation": comp[code].get("occupation") or f"CPS OCC2010 {code}",
                "soc_major_group": comp[code].get("soc_major_group") or "unknown",
                "preperiod_employment_weight": w[i],
                "ai_exposure": x[i], "computerization": c[i],
                "ai_residual": residuals[i],
                "ai_residual_sd_units": (residuals[i] / fit["residual_sd"]
                                         if fit["residual_sd"] else None),
                "residual_variance_share": contributions[i] / contribution_total,
            })
        return result

    largest_contribution = sorted(range(len(codes)), key=lambda i: -contributions[i])[:top_k]
    positive = sorted(range(len(codes)), key=lambda i: -residuals[i])[:top_k]
    negative = sorted(range(len(codes)), key=lambda i: residuals[i])[:top_k]
    return {
        "ai_measure": ai_name,
        "computerization_measure": comp_name,
        "n_occupations": len(codes),
        "common_support_employment_weight": sum(w),
        "common_support_employment_share": sum(w) / total_mass,
        **fit,
        "effective_number_identifying_ai": effective_n,
        "residual_variation_by_soc_major_group": group_shares,
        "named_divergence_occupations": {
            "largest_residual_variance_contributors": named(largest_contribution),
            "largest_positive_ai_residuals": named(positive),
            "largest_negative_ai_residuals": named(negative),
        },
    }


def webb_missing(webb_path, dorn_crosswalk_path, mass, total_mass):
    source = rows(webb_path)
    missing = {int(row["occ1990dd"]): row for row in source
               if number(row.get("pct_software")) is None}
    routes = defaultdict(list)
    for row in rows(dorn_crosswalk_path):
        routes[int(float(row["occ1990dd"]))].append(str(int(float(row["occ"]))).zfill(4))
    result = []
    for code, row in sorted(missing.items()):
        cps_codes = sorted(routes.get(code, []))
        weight = sum(mass.get(cps, 0.0) for cps in cps_codes)
        result.append({
            "occ1990dd": code, "occupation": row["occ1990dd_title"],
            "cps_occ2010_codes": cps_codes,
            "preperiod_employment_weight": weight,
            "preperiod_employment_share": weight / total_mass,
            "route_status": "mapped" if cps_codes else "absent_from_direct_dorn_crosswalk",
        })
    return result


def build(args):
    if args.support_kind == "design_cells":
        mass, months, excluded_months, support_extra = design_preperiod_mass(
            args.preperiod_cells, args.lookup_role)
        preperiod_outcomes_read = True
    else:
        mass, months, excluded_months = preperiod_mass(args.preperiod_cells)
        support_extra = {}
        preperiod_outcomes_read = False
    support_rule = (
        "month < 2022-12-01; raw target codes retained only with positive "
        "66-month support in both frozen age groups"
        if args.support_kind == "design_cells"
        else "month < 2022-12-01; only cps_occ/month/weight_sum accessed"
    )
    correction = (
        {
            "supersedes_13_month_diagnostic": True,
            "reason": "freeze uses the 66-month target-occupation design support",
        }
        if args.support_kind == "design_cells"
        else {
            "discarded_initial_support_run": True,
            "reason": (
                "the private file labelled preperiod also contained 2022-12 "
                "through 2023-02 rows; the discarded run used their occupation "
                "weights but did not access an outcome field"
            ),
            "resolution": (
                "the output was overwritten before commit; this receipt rejects "
                "month >= 2022-12-01 before any survey weight enters the support"
            ),
        }
    )
    total_mass = sum(mass.values())
    ai_rows = [row for row in rows(args.ai_lookup)
               if row["lookup_role"] == args.lookup_role]
    ai = {
        name: {row["occ_code"].zfill(4): number(row[name]) for row in ai_rows
               if number(row.get(name)) is not None}
        for name in AI_MEASURES
    }
    comp_rows = rows(args.computerization)
    comp = {}
    for row in comp_rows:
        code = row[args.computerization_code_field].zfill(4)
        comp[code] = {**row, **{name: number(row.get(name))
                               for name in COMPUTERIZATION_MEASURES}}
    pairs = []
    for ai_name in AI_MEASURES:
        for comp_name in COMPUTERIZATION_MEASURES:
            comp_available = {code: row for code, row in comp.items()
                              if row[comp_name] is not None}
            pairs.append(analyse_pair(ai_name, comp_name, ai[ai_name], comp_available,
                                      mass, total_mass))
    missing = (webb_missing(args.webb, args.dorn_crosswalk_csv, mass, total_mass)
               if args.computerization_code_field == "cps_occ2010" else [])
    receipt = {
        "record_version": "yax-computerization-support-v2",
        "status": "PASS_REAL_COMPUTERIZATION_MEASURES",
        "question": "How much AI-exposure variance remains after conditioning on prior computerization?",
        "identification_statistic": "employment-weighted partial variance of AI, 1-R_squared",
        "scope": "outcome-blind preperiod occupation support; no post-period outcome opened",
        "post_event_outcomes_opened": False,
        "preperiod_outcomes_read": preperiod_outcomes_read,
        "execution_correction": correction,
        "inputs": {
            "ai_lookup": {"path": str(args.ai_lookup), "sha256": sha256(args.ai_lookup)},
            "computerization": {"path": str(args.computerization),
                                "sha256": sha256(args.computerization)},
            "preperiod_cells": {"path": str(args.preperiod_cells),
                                "sha256": sha256(args.preperiod_cells)},
            "webb": {"path": str(args.webb), "sha256": sha256(args.webb)},
            "dorn_crosswalk_csv": {"path": str(args.dorn_crosswalk_csv),
                                   "sha256": sha256(args.dorn_crosswalk_csv)},
        },
        "preperiod_support": {
            "months": len(months), "first_month": months[0] if months else None,
            "last_month": months[-1] if months else None,
            "post_start": POST_START,
            "excluded_post_months": excluded_months,
            "support_rule": support_rule,
            "occupation_codes": len(mass), "employment_weight": total_mass,
            "lookup_role": args.lookup_role,
            "computerization_code_field": args.computerization_code_field,
            **support_extra,
        },
        "ai_measures": list(AI_MEASURES),
        "computerization_measures": list(COMPUTERIZATION_MEASURES),
        "webb_unscored_occupations": missing,
        "webb_unscored_combined_preperiod_employment_weight": sum(
            row["preperiod_employment_weight"] for row in missing),
        "webb_unscored_combined_preperiod_employment_share": sum(
            row["preperiod_employment_weight"] for row in missing) / total_mass,
        "pairs": pairs,
    }
    args.output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main(argv=None):
    here = pathlib.Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ai-lookup", type=pathlib.Path,
                        default=here / "CPS_OCCUPATION_EXPOSURE_LOOKUP.csv")
    parser.add_argument("--computerization", type=pathlib.Path,
                        default=here / "COMPUTERIZATION_MEASURES.csv")
    parser.add_argument("--preperiod-cells", type=pathlib.Path, required=True)
    parser.add_argument("--webb", type=pathlib.Path, required=True)
    parser.add_argument("--dorn-crosswalk-csv", type=pathlib.Path, required=True)
    parser.add_argument("--support-kind", choices=("legacy_weight_cells", "design_cells"),
                        default="legacy_weight_cells")
    parser.add_argument("--lookup-role", default=LOOKUP_ROLE)
    parser.add_argument("--computerization-code-field", default="cps_occ2010")
    parser.add_argument("--output", type=pathlib.Path,
                        default=here / "computerization_support_receipt.json")
    args = parser.parse_args(argv)
    for path in (args.ai_lookup, args.computerization, args.preperiod_cells,
                 args.webb, args.dorn_crosswalk_csv):
        if not path.is_file():
            print(f"NEED_HUMAN: missing input {path}")
            return 2
    receipt = build(args)
    print(f"wrote {args.output}; {len(receipt['pairs'])} AI x computerization pairs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
