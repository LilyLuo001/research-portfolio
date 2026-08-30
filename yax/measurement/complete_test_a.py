#!/usr/bin/env python3
"""Complete the frozen, outcome-free YAX Test A construct diagnostics.

The v1.1 design incorporated RESEARCH_PLAN_v5, which required every frozen AI
exposure definition to be related to cognitive, manual/physical, routine,
education, wage, telework, STEM, and computer-use characteristics.  The first
confirmatory archive contained only a subset.  This script fills that frozen
measurement requirement without reading any protected post-period outcome.

O*NET release 26.1 is used because it is the November-2021 release already
pinned by the task-weight build.  The script refuses any employment-weight file
containing a month after 2022-11.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import zipfile
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd


AI_MEASURES = (
    "aioe_admin_equal",
    "aioe_ability_direct",
    "aioe_oews2018_source_weighted",
    "dv_rating_alpha",
    "dv_rating_beta",
    "dv_rating_gamma",
)
CHARACTERISTICS = (
    "cognitive_ability_importance",
    "manual_physical_ability_importance",
    "rti_autor_dorn",
    "required_education_category_index",
    "log_mean_annual_wage",
    "dingel_neiman_telework",
    "stem_major_group_share",
    "onet_computers_importance",
)
STEM_MAJOR_GROUPS = {"15", "17", "19"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    return float(np.average(values, weights=weights))


def weighted_corr(x: np.ndarray, y: np.ndarray, w: np.ndarray) -> float:
    mx, my = weighted_mean(x, w), weighted_mean(y, w)
    vx = weighted_mean((x - mx) ** 2, w)
    vy = weighted_mean((y - my) ** 2, w)
    if vx <= 0 or vy <= 0:
        return float("nan")
    return float(weighted_mean((x - mx) * (y - my), w) / math.sqrt(vx * vy))


def weighted_standardize(values: np.ndarray, weights: np.ndarray) -> np.ndarray:
    mean = weighted_mean(values, weights)
    sd = math.sqrt(weighted_mean((values - mean) ** 2, weights))
    if not np.isfinite(sd) or sd <= 0:
        raise ValueError("cannot standardize zero-variance column")
    return (values - mean) / sd


def match_soc_pattern(pattern: str, available: set[str]) -> list[str]:
    if pattern in available:
        return [pattern]
    if "X" in pattern:
        expression = "^" + re.escape(pattern).replace("X", r"\d") + "$"
    elif re.fullmatch(r"\d{2}-0000", pattern):
        expression = "^" + re.escape(pattern[:3]) + r"\d{4}$"
    elif re.fullmatch(r"\d{2}-\d{2}00", pattern):
        expression = "^" + re.escape(pattern[:-2]) + r"\d{2}$"
    elif re.fullmatch(r"\d{2}-\d{3}0", pattern):
        expression = "^" + re.escape(pattern[:-1]) + r"\d$"
    else:
        return []
    return sorted(code for code in available if re.fullmatch(expression, code))


def read_zip_table(archive: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    member = f"db_26_1_text/{name}"
    with archive.open(member) as raw:
        return list(csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig"), delimiter="\t"))


def collapse_onet_details(values: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[tuple[str, dict[str, float]]]] = defaultdict(list)
    for onet_soc, row in values.items():
        grouped[onet_soc[:7]].append((onet_soc, row))
    result = {}
    for base, candidates in grouped.items():
        base_rows = [row for code, row in candidates if code.endswith(".00")]
        chosen = base_rows if base_rows else [row for _, row in candidates]
        fields = sorted(set().union(*(row.keys() for row in chosen)))
        result[base] = {
            field: float(np.mean([row[field] for row in chosen if field in row]))
            for field in fields
            if all(field in row for row in chosen)
        }
    return result


def parse_onet_constructs(path: Path) -> dict[str, dict[str, float]]:
    with zipfile.ZipFile(path) as archive:
        abilities = read_zip_table(archive, "Abilities.txt")
        education = read_zip_table(archive, "Education, Training, and Experience.txt")

    by_onet: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in abilities:
        if row["Scale ID"] != "IM":
            continue
        element = row["Element ID"]
        if element.startswith("1.A.1."):
            by_onet[row["O*NET-SOC Code"]]["cognitive_ability_importance"].append(float(row["Data Value"]))
        elif element.startswith("1.A.2.") or element.startswith("1.A.3."):
            by_onet[row["O*NET-SOC Code"]]["manual_physical_ability_importance"].append(float(row["Data Value"]))

    education_by_onet: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for row in education:
        if row["Element ID"] == "2.D.1" and row["Scale ID"] == "RL" and row["Category"]:
            education_by_onet[row["O*NET-SOC Code"]].append(
                (float(row["Category"]), float(row["Data Value"]))
            )

    full = {}
    for onet_soc in sorted(set(by_onet) | set(education_by_onet)):
        row = {}
        for field, values in by_onet.get(onet_soc, {}).items():
            if values:
                row[field] = float(np.mean(values))
        categories = education_by_onet.get(onet_soc, [])
        total = sum(percent for _, percent in categories)
        if categories and total > 0:
            row["required_education_category_index"] = sum(
                category * percent for category, percent in categories
            ) / total
        full[onet_soc] = row
    return collapse_onet_details(full)


def build_soc_characteristics(args: argparse.Namespace) -> pd.DataFrame:
    bridge = pd.read_csv(args.bridge, dtype=str)
    patterns = bridge.groupby("census_2018")["soc_2018_pattern"].agg(lambda s: sorted(set(s.dropna())))
    conflicts = {code: vals for code, vals in patterns.items() if len(vals) != 1}
    if conflicts:
        raise ValueError(f"conflicting Census-to-SOC patterns: {list(conflicts)[:5]}")
    patterns = {str(code).zfill(4): vals[0] for code, vals in patterns.items()}

    oews = pd.read_parquet(args.oews).copy()
    oews["occ_code"] = oews["occ_code"].astype(str)
    oews = oews[(oews["tot_emp"] > 0) & oews["occ_code"].str.fullmatch(r"\d{2}-\d{4}")]
    oews_by_code = oews.set_index("occ_code")
    oews_codes = set(oews_by_code.index)
    onet = parse_onet_constructs(args.onet_archive)
    onet_codes = set(onet)

    rows = []
    for census_code, pattern in sorted(patterns.items()):
        out = {"census2018": census_code, "soc_2018_pattern": pattern}
        wage_hits = match_soc_pattern(pattern, oews_codes)
        if wage_hits:
            weights = np.array([float(oews_by_code.loc[code, "tot_emp"]) for code in wage_hits])
            wages = np.array([float(oews_by_code.loc[code, "a_mean"]) for code in wage_hits])
            valid = np.isfinite(wages) & (wages > 0)
            if valid.any():
                out["log_mean_annual_wage"] = math.log(weighted_mean(wages[valid], weights[valid]))
            out["stem_major_group_share"] = weighted_mean(
                np.array([1.0 if code[:2] in STEM_MAJOR_GROUPS else 0.0 for code in wage_hits]),
                weights,
            )
            out["oews_component_count"] = len(wage_hits)

        onet_hits = match_soc_pattern(pattern, onet_codes)
        out["onet_component_count"] = len(onet_hits)
        if onet_hits:
            if all(code in oews_codes for code in onet_hits):
                onet_weights = np.array([float(oews_by_code.loc[code, "tot_emp"]) for code in onet_hits])
                out["onet_weight_basis"] = "oews_2021_employment"
            else:
                onet_weights = np.ones(len(onet_hits))
                out["onet_weight_basis"] = "equal_missing_oews_component"
            for field in (
                "cognitive_ability_importance",
                "manual_physical_ability_importance",
                "required_education_category_index",
            ):
                values = [onet[code].get(field) for code in onet_hits]
                if all(value is not None and np.isfinite(value) for value in values):
                    out[field] = weighted_mean(np.array(values, float), onet_weights)
        rows.append(out)
    return pd.DataFrame(rows)


def load_analysis_frame(args: argparse.Namespace) -> tuple[pd.DataFrame, dict]:
    cells = pd.read_csv(args.preperiod_cells, dtype={"occ_code": str, "month": str})
    if cells["month"].max() > "2022-11":
        raise RuntimeError("protected post-period outcome detected in Test A weights")
    if set(cells["lookup_role"]) != {"raw_occ_main_2020_plus"}:
        raise RuntimeError("unexpected lookup role in frozen pre-period cells")
    weights = cells.groupby("occ_code", as_index=False)["employment_headcount"].sum()
    weights["occ_code"] = weights["occ_code"].str.zfill(4)
    weights = weights.rename(columns={"occ_code": "census2018", "employment_headcount": "preperiod_employment_weight"})

    lookup = pd.read_csv(args.lookup, dtype={"occ_code": str})
    lookup = lookup[lookup["lookup_role"] == "raw_occ_main_2020_plus"].copy()
    lookup["census2018"] = lookup["occ_code"].str.zfill(4)
    keep = ["census2018", "dingel_neiman_telework", "dingel_neiman_telework_covered_route_mass"]
    for measure in AI_MEASURES:
        keep.extend([measure, measure + "_covered_route_mass"])
    lookup = lookup[keep].drop_duplicates("census2018")
    for measure in (*AI_MEASURES, "dingel_neiman_telework"):
        coverage = lookup[measure + "_covered_route_mass"]
        lookup.loc[coverage < 1 - 1e-9, measure] = np.nan

    comp = pd.read_csv(args.computerization, dtype={"census2018": str})
    comp["census2018"] = comp["census2018"].str.zfill(4)
    comp = comp[["census2018", "occupation", "soc_major_group", "rti_autor_dorn", "onet_computers_importance"]]
    soc = build_soc_characteristics(args)
    frame = weights.merge(lookup, on="census2018", how="left").merge(comp, on="census2018", how="left").merge(soc, on="census2018", how="left")
    frame = frame[frame["preperiod_employment_weight"] > 0].copy()
    meta = {
        "preperiod_first_month": cells["month"].min(),
        "preperiod_last_month": cells["month"].max(),
        "preperiod_cell_rows": len(cells),
        "weighted_occupation_rows": len(frame),
    }
    return frame, meta


def weighted_quintiles(values: np.ndarray, weights: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    cumulative = np.cumsum(weights[order])
    cuts = np.array([
        values[order[min(np.searchsorted(cumulative, share * cumulative[-1], side="left"), len(values) - 1)]]
        for share in (0.2, 0.4, 0.6, 0.8)
    ])
    if np.any(cuts[:-1] >= cuts[1:]):
        raise ValueError("employment-weighted quintile cuts are not distinct")
    return np.searchsorted(cuts, values, side="left") + 1


def analyze(frame: pd.DataFrame) -> dict:
    relation_rows = []
    ranking_rows = []
    total_weight = float(frame["preperiod_employment_weight"].sum())
    for measure in AI_MEASURES:
        for characteristic in CHARACTERISTICS:
            sample = frame[[measure, characteristic, "preperiod_employment_weight"]].dropna()
            x = sample[measure].to_numpy(float)
            y = sample[characteristic].to_numpy(float)
            w = sample["preperiod_employment_weight"].to_numpy(float)
            relation_rows.append({
                "ai_measure": measure,
                "characteristic": characteristic,
                "occupations": len(sample),
                "employment_weight_share": float(w.sum() / total_weight),
                "weighted_pearson": weighted_corr(x, y, w),
                "weighted_spearman": weighted_corr(
                    pd.Series(x).rank(method="average").to_numpy(),
                    pd.Series(y).rank(method="average").to_numpy(),
                    w,
                ),
            })
        ranked = frame[["census2018", "occupation", measure, "preperiod_employment_weight"]].dropna().sort_values(measure)
        for tail, subset in (("bottom", ranked.head(10)), ("top", ranked.tail(10).sort_values(measure, ascending=False))):
            for rank, (_, row) in enumerate(subset.iterrows(), 1):
                ranking_rows.append({
                    "ai_measure": measure,
                    "tail": tail,
                    "rank_within_tail": rank,
                    "census2018": row["census2018"],
                    "occupation": row["occupation"],
                    "exposure": float(row[measure]),
                })

    common_columns = [*AI_MEASURES, *CHARACTERISTICS, "preperiod_employment_weight"]
    common = frame[["census2018", "occupation", *common_columns]].dropna().copy()
    weights = common["preperiod_employment_weight"].to_numpy(float)
    x_chars = np.column_stack([
        weighted_standardize(common[field].to_numpy(float), weights)
        for field in CHARACTERISTICS
    ])
    design = np.column_stack([np.ones(len(common)), x_chars])
    root_w = np.sqrt(weights / weights.mean())
    residuals = {}
    residual_rows = []
    for measure in AI_MEASURES:
        y = weighted_standardize(common[measure].to_numpy(float), weights)
        beta, *_ = np.linalg.lstsq(design * root_w[:, None], y * root_w, rcond=None)
        residual = y - design @ beta
        residuals[measure] = residual
        residual_variance = weights * residual ** 2
        shares = residual_variance / residual_variance.sum()
        effective = float(1.0 / np.square(shares).sum())
        order = np.argsort(shares)[::-1]
        top = []
        for index in order[:10]:
            top.append({
                "census2018": common.iloc[index]["census2018"],
                "occupation": common.iloc[index]["occupation"],
                "residual_variance_share": float(shares[index]),
            })
        residual_rows.append({
            "ai_measure": measure,
            "occupations": len(common),
            "weighted_r_squared_on_all_characteristics": float(1 - weighted_mean(residual ** 2, weights)),
            "residual_sd": float(math.sqrt(weighted_mean(residual ** 2, weights))),
            "effective_identifying_occupations": effective,
            "top_five_residual_variance_share": float(shares[order[:5]].sum()),
            "top_ten_contributors": top,
        })

    residual_correlation_rows = []
    overlap_rows = []
    quintiles = {
        measure: weighted_quintiles(common[measure].to_numpy(float), weights)
        for measure in AI_MEASURES
    }
    for left, right in combinations(AI_MEASURES, 2):
        residual_correlation_rows.append({
            "measure_left": left,
            "measure_right": right,
            "weighted_residual_correlation": weighted_corr(residuals[left], residuals[right], weights),
            "occupations": len(common),
        })
        left_q, right_q = quintiles[left], quintiles[right]
        for tail, code in (("Q1", 1), ("Q5", 5)):
            a = set(common.loc[left_q == code, "census2018"])
            b = set(common.loc[right_q == code, "census2018"])
            overlap_rows.append({
                "measure_left": left,
                "measure_right": right,
                "tail": tail,
                "left_occupations": len(a),
                "right_occupations": len(b),
                "intersection": len(a & b),
                "jaccard": len(a & b) / len(a | b) if a | b else float("nan"),
            })
    return {
        "relations": relation_rows,
        "rankings": ranking_rows,
        "common_support_occupations": len(common),
        "residual_diagnostics": residual_rows,
        "residual_correlations": residual_correlation_rows,
        "rank_overlap": overlap_rows,
    }


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, results: dict, meta: dict) -> None:
    relations = pd.DataFrame(results["relations"])
    lines = [
        "# Frozen Test A construct diagnostics",
        "",
        "This closes the outcome-free Test A matrix incorporated by `DESIGN_FREEZE_v2.md` through `RESEARCH_PLAN_v5.md`. No protected post-period outcome is read.",
        "",
        f"Common complete support for the joint residual audit: **{results['common_support_occupations']} occupations**.",
        "",
        "## Employment-weighted Pearson correlations",
        "",
        "| AI measure | " + " | ".join(CHARACTERISTICS) + " |",
        "|---|" + "|".join(["---:"] * len(CHARACTERISTICS)) + "|",
    ]
    for measure in AI_MEASURES:
        subset = relations[relations.ai_measure == measure].set_index("characteristic")
        values = [f"{subset.loc[c, 'weighted_pearson']:.3f}" for c in CHARACTERISTICS]
        lines.append("| " + measure + " | " + " | ".join(values) + " |")
    lines.extend(["", "## Joint characteristic residual audit", "", "| AI measure | R² on characteristics | residual SD | effective occupations | top-five share | five largest contributors |", "|---|---:|---:|---:|---:|---|"])
    for row in results["residual_diagnostics"]:
        contributors = "; ".join(
            f"{item['occupation']} ({100*item['residual_variance_share']:.1f}%)"
            for item in row["top_ten_contributors"][:5]
        )
        lines.append(
            f"| {row['ai_measure']} | {row['weighted_r_squared_on_all_characteristics']:.3f} | "
            f"{row['residual_sd']:.3f} | {row['effective_identifying_occupations']:.1f} | "
            f"{row['top_five_residual_variance_share']:.3f} | {contributors} |"
        )
    lines.extend([
        "",
        "## Definitions and scope",
        "",
        "- Cognitive intensity is the mean O*NET Importance rating across the official `1.A.1` Cognitive Abilities branch.",
        "- Manual/physical intensity is the mean Importance rating across `1.A.2` Psychomotor and `1.A.3` Physical Abilities.",
        "- Education is the percentage-weighted mean category of O*NET `2.D.1` Required Level of Education; it is an ordered-category index, not years of schooling.",
        "- Wage is log OEWS-2021 mean annual wage, collapsed with OEWS employment weights.",
        "- STEM share is the OEWS-employment share of SOC major groups 15, 17 and 19 within each Census-2018 occupation mapping.",
        "- RTI, teleworkability and O*NET computer-use importance are the already frozen YAX measures.",
        "- Joint residual diagnostics use common complete support and frozen 2017-01–2022-11 employment-stock weights. They are measurement diagnostics, not post-outcome employment estimates.",
        "",
        "Full pairwise sample sizes, weighted Spearman correlations, raw rankings, rank overlap, residual correlations, and named contributors are in the machine-readable files and receipt.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--onet-archive", type=Path, required=True)
    parser.add_argument("--preperiod-cells", type=Path, required=True)
    parser.add_argument("--lookup", type=Path, default=Path("yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv"))
    parser.add_argument("--computerization", type=Path, default=Path("yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv"))
    parser.add_argument("--bridge", type=Path, default=Path("yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv"))
    parser.add_argument("--oews", type=Path, default=Path("dax/data_built/oews_wages.parquet"))
    parser.add_argument("--output-dir", type=Path, default=Path("yax/measurement/test_a"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    frame, meta = load_analysis_frame(args)
    results = analyze(frame)
    characteristics_path = args.output_dir / "TEST_A_OCCUPATION_CHARACTERISTICS.csv"
    relation_path = args.output_dir / "TEST_A_CHARACTERISTIC_MATRIX.csv"
    residual_path = args.output_dir / "TEST_A_RESIDUAL_DIAGNOSTICS.csv"
    residual_corr_path = args.output_dir / "TEST_A_RESIDUAL_CORRELATIONS.csv"
    overlap_path = args.output_dir / "TEST_A_RANK_OVERLAP.csv"
    ranking_path = args.output_dir / "TEST_A_RANKINGS.csv"
    markdown_path = args.output_dir / "TEST_A_RESULTS.md"

    frame[["census2018", "occupation", "preperiod_employment_weight", *AI_MEASURES, *CHARACTERISTICS]].to_csv(characteristics_path, index=False)
    write_csv(relation_path, results["relations"], ["ai_measure", "characteristic", "occupations", "employment_weight_share", "weighted_pearson", "weighted_spearman"])
    residual_flat = []
    for row in results["residual_diagnostics"]:
        flat = {key: value for key, value in row.items() if key != "top_ten_contributors"}
        flat["top_ten_contributors_json"] = json.dumps(row["top_ten_contributors"], separators=(",", ":"))
        residual_flat.append(flat)
    write_csv(residual_path, residual_flat, ["ai_measure", "occupations", "weighted_r_squared_on_all_characteristics", "residual_sd", "effective_identifying_occupations", "top_five_residual_variance_share", "top_ten_contributors_json"])
    write_csv(residual_corr_path, results["residual_correlations"], ["measure_left", "measure_right", "weighted_residual_correlation", "occupations"])
    write_csv(overlap_path, results["rank_overlap"], ["measure_left", "measure_right", "tail", "left_occupations", "right_occupations", "intersection", "jaccard"])
    write_csv(ranking_path, results["rankings"], ["ai_measure", "tail", "rank_within_tail", "census2018", "occupation", "exposure"])
    write_markdown(markdown_path, results, meta)

    outputs = [characteristics_path, relation_path, residual_path, residual_corr_path, overlap_path, ranking_path, markdown_path]
    receipt = {
        "record_version": "yax-frozen-test-a-completion-v1",
        "status": "PASS_COMPLETE_FROZEN_TEST_A",
        "scope": "pre-specified measurement diagnostics only; no protected post-period outcome read",
        "post_period_outcomes_read": False,
        "design_authority": ["yax/DESIGN_FREEZE_v2.md:5-7", "yax/RESEARCH_PLAN_v5.md:131-183", "yax/RESEARCH_PLAN_v5.md:580-605"],
        "ai_measures": list(AI_MEASURES),
        "characteristics": list(CHARACTERISTICS),
        "definitions": {
            "cognitive_ability_importance": "mean O*NET IM across official 1.A.1 Cognitive Abilities",
            "manual_physical_ability_importance": "mean O*NET IM across official 1.A.2 Psychomotor and 1.A.3 Physical Abilities",
            "required_education_category_index": "percentage-weighted mean O*NET 2.D.1 RL category; ordered category, not years",
            "stem_major_group_share": "OEWS-employment share in SOC major groups 15, 17, 19",
            "residualization": "weighted OLS of each standardized AI measure on all eight standardized characteristics plus intercept, common complete support",
            "rank_overlap": "Jaccard overlap of frozen employment-weighted Q1 and Q5 sets on common complete support; ties not split",
        },
        "sources": {
            "onet_26_1": {"path": str(args.onet_archive), "sha256": sha256(args.onet_archive), "url": "https://www.onetcenter.org/dl_files/database/db_26_1_text.zip", "release": "November 2021"},
            "preperiod_cells": {"path": str(args.preperiod_cells), "sha256": sha256(args.preperiod_cells)},
            "lookup": {"path": str(args.lookup), "sha256": sha256(args.lookup)},
            "computerization": {"path": str(args.computerization), "sha256": sha256(args.computerization)},
            "bridge": {"path": str(args.bridge), "sha256": sha256(args.bridge)},
            "oews": {"path": str(args.oews), "sha256": sha256(args.oews)},
        },
        "preperiod": meta,
        "common_complete_support_occupations": results["common_support_occupations"],
        "residual_diagnostics": results["residual_diagnostics"],
        "residual_correlations": results["residual_correlations"],
        "rank_overlap": results["rank_overlap"],
        "outputs": {str(path): sha256(path) for path in outputs},
    }
    receipt_path = args.output_dir / "TEST_A_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "common_support": results["common_support_occupations"], "receipt": str(receipt_path)}, indent=2))


if __name__ == "__main__":
    main()
