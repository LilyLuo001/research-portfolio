#!/usr/bin/env python3
"""Audit and, if admissible, fit Webb AI and OECD AI capability exposure.

POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1.
The admission rule is stored in EXTERNAL_ARCHITECTURE_ADMISSION_RULE.md.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import pathlib
import sys
import zipfile

import numpy as np
import pandas as pd


HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[3]
LABEL = "POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1"
SEED = 2026090504
DRAWS = 999


def import_path(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CORE = import_path("yax_revision_external_core", HERE / "run_referee_core.py")
FROZEN = CORE.FROZEN
CROSSWALK = import_path(
    "yax_revision_external_crosswalk", ROOT / "yax/measurement/reproduce_eig_crosswalk.py"
)


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
        writer.writeheader(); writer.writerows(rows)


def write_json(path: pathlib.Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_soc_maps(bls_path: pathlib.Path, census_path: pathlib.Path):
    bridge = pd.read_excel(bls_path, skiprows=8, dtype=str)
    bridge.columns = ["soc_2010", "soc_title_2010", "soc_2018", "soc_title_2018"]
    bridge = bridge.dropna(subset=["soc_2010", "soc_2018"]).copy()
    bridge["soc_2010"] = bridge.soc_2010.str.strip().str[:7]
    bridge["soc_2018"] = bridge.soc_2018.str.strip().str[:7]

    # Reuse the already-tested project mapping logic, including the Census
    # aggregate-code exceptions. Point its source locator at the authenticated
    # file supplied to this audit rather than adding a second implementation.
    prior = CROSSWALK.CENSUS
    try:
        CROSSWALK.CENSUS = census_path
        _, mapping = CROSSWALK.build_soc18_census(bridge)
    finally:
        CROSSWALK.CENSUS = prior
    mapping = mapping.rename(columns={"census_2018": "census2018"})
    mapping["census2018"] = mapping.census2018.str.zfill(4)
    return bridge, mapping[["soc_2018", "census2018"]].drop_duplicates()


def oews_weights(path: pathlib.Path) -> dict[str, float]:
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if name.endswith("national_M2021_dl.xlsx")]
        if len(members) != 1:
            raise RuntimeError("OEWS 2021 workbook not found uniquely")
        with archive.open(members[0]) as handle:
            frame = pd.read_excel(handle, dtype=str)
    frame.columns = [str(column).lower() for column in frame.columns]
    frame = frame.loc[frame.o_group.str.lower().eq("detailed")].copy()
    frame["soc_2018"] = frame.occ_code.str.strip().str[:7]
    frame["employment"] = pd.to_numeric(frame.tot_emp.str.replace(",", "", regex=False),
                                         errors="coerce")
    return frame.set_index("soc_2018").employment.to_dict()


def collapse_full_component(soc: pd.DataFrame, mapping: pd.DataFrame,
                            employment: dict[str, float], value: str):
    merged = mapping.merge(soc[["soc_2018", value]], on="soc_2018", how="left")
    rows = []
    for code, group in merged.groupby("census2018", sort=True):
        raw_weights = np.array([employment.get(item, np.nan) for item in group.soc_2018], float)
        if np.isfinite(raw_weights).all() and (raw_weights > 0).all():
            weights = raw_weights / raw_weights.sum(); basis = "OEWS_2021_employment"
        else:
            weights = np.repeat(1 / len(group), len(group)); basis = "equal_missing_OEWS"
        available = np.isfinite(group[value].to_numpy(float))
        covered = float(weights[available].sum())
        score = float(np.sum(weights * group[value].to_numpy(float))) if available.all() else np.nan
        rows.append({"census2018": code, value: score, "covered_component_weight": covered,
                     "component_count": len(group), "weight_basis": basis})
    return pd.DataFrame(rows)


def webb_soc(path: pathlib.Path, bridge: pd.DataFrame):
    frame = pd.read_csv(path, dtype={"simpleOcc": str})
    frame["soc_2010"] = frame.simpleOcc.str.strip().str[:7]
    for column in ("pct_ai", "pct_software", "pct_robot", "lswt2010"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    consistency = frame.groupby("soc_2010")[["pct_ai", "pct_software", "pct_robot"]].nunique()
    if (consistency > 1).any().any():
        raise RuntimeError("Webb scores vary across repeated years")
    unique = frame.groupby("soc_2010", as_index=False).agg(
        pct_ai=("pct_ai", "first"), pct_software=("pct_software", "first"),
        pct_robot=("pct_robot", "first"), lswt2010=("lswt2010", "mean"))
    routed = bridge[["soc_2010", "soc_2018"]].drop_duplicates().merge(
        unique, on="soc_2010", how="left")
    rows = []
    for code, group in routed.groupby("soc_2018", sort=True):
        available = group.pct_ai.notna()
        if not available.all():
            rows.append({"soc_2018": code, "webb_ai": np.nan}); continue
        weights = group.lswt2010.to_numpy(float)
        if not np.isfinite(weights).all() or not (weights > 0).all():
            weights = np.ones(len(group))
        rows.append({"soc_2018": code,
                     "webb_ai": float(np.average(group.pct_ai, weights=weights))})
    return pd.DataFrame(rows), {
        "raw_rows": len(frame), "source_soc2010": int(unique.soc_2010.nunique()),
        "source_score_consistent_over_years": True,
        "source_software_ai_correlation": float(unique[["pct_ai", "pct_software"]].corr().iloc[0, 1]),
    }


def oecd_soc(path: pathlib.Path):
    frame = pd.read_excel(path, sheet_name="Data", header=2, dtype=str)
    frame = frame.rename(columns={"OCC_Code": "raw_code",
                                  "AI Capability Gap Index_Rev. norm.": "oecd_ai_gap_reversed"})
    frame["soc_2018"] = frame.raw_code.str.strip().str[:7]
    frame["oecd_ai_gap_reversed"] = pd.to_numeric(frame.oecd_ai_gap_reversed,
                                                   errors="coerce")
    frame = frame.dropna(subset=["soc_2018", "oecd_ai_gap_reversed"])
    by_soc = frame.groupby("soc_2018", as_index=False).oecd_ai_gap_reversed.mean()
    return by_soc, {"raw_detail_rows": len(frame), "source_soc2018": len(by_soc),
                    "detail_aggregation": "equal mean within six-digit SOC 2018"}


def evaluate_and_fit(args, data, name: str, mapped: pd.DataFrame, source_meta: dict,
                     source_path: pathlib.Path, source_url: str, construct: str):
    mapped = mapped.set_index("census2018")
    base = sorted(data["occupations"])
    chars = pd.read_csv(args.characteristics, dtype={"census2018": str})
    chars.census2018 = chars.census2018.str.zfill(4)
    pre_weight = chars.set_index("census2018").preperiod_employment_weight.to_dict()
    score_column = next(column for column in mapped.columns if column not in
                        {"covered_component_weight", "component_count", "weight_basis"})
    score = mapped[score_column].to_dict()
    support = sorted(code for code in base if np.isfinite(score.get(code, np.nan)) and
                     np.isfinite(data["computers"]["webb_pct_software"].get(code, np.nan)))
    total = sum(pre_weight.get(code, 0) for code in base)
    retained = sum(pre_weight.get(code, 0) for code in support)
    coverage = retained / total
    young, older = FROZEN.panel_arrays(data["panel"], support, data["static_months"])
    weights = (young + older).sum(axis=1)
    values = np.array([score[code] for code in support], float)
    failure = ""
    try:
        groups, cuts = CORE.weighted_quintile_with_cuts(values, weights)
    except Exception as error:
        groups, cuts = None, None; failure = f"{type(error).__name__}: {error}"
    admitted = bool(coverage >= .8 and len(support) >= 300 and groups is not None)
    record = {
        "analysis_status": LABEL, "architecture": name, "source_url": source_url,
        "source_sha256": sha256(source_path), "construct": construct,
        "score_column": score_column, "support_occupations": len(support),
        "preperiod_employment_coverage": coverage, "coverage_threshold": .8,
        "full_component_rule": True, "non_title_mapping": True,
        "distinct_quintile_cuts": groups is not None, "admitted": admitted,
        "failure": failure, "source_meta": source_meta,
    }
    result = None
    if admitted:
        fit, influence, _, labels = CORE.fit_group_model(
            data["panel"], support, data["static_months"], groups,
            data["computers"]["webb_pct_software"])
        signs = np.random.default_rng(SEED).choice(np.array([-1., 1.]),
                                                   size=(DRAWS, len(support)))
        contrast = np.zeros(len(labels)); contrast[len(labels) - 2] = 1
        summary, centered = CORE.bootstrap_linear(fit, influence, contrast, signs)
        result = {**record, "quintile_cuts_json": json.dumps(cuts.tolist()), **summary}

        beta = data["exposures"]["dv_rating_beta"]["A"]
        common = [code for code in support if np.isfinite(beta.get(code, np.nan))]
        y, o = FROZEN.panel_arrays(data["panel"], common, data["static_months"])
        common_weights = (y + o).sum(axis=1)
        q_new, _ = CORE.weighted_quintile_with_cuts(
            np.array([score[code] for code in common]), common_weights)
        q_beta, _ = CORE.weighted_quintile_with_cuts(
            np.array([beta[code] for code in common]), common_weights)
        common_signs = np.random.default_rng(SEED + 1).choice(np.array([-1., 1.]),
                                                              size=(DRAWS, len(common)))
        fitted = []
        for label, q in ((name, q_new), ("dv_rating_beta", q_beta)):
            f, inf, _, labs = CORE.fit_group_model(data["panel"], common,
                                                    data["static_months"], q,
                                                    data["computers"]["webb_pct_software"])
            c = np.zeros(len(labs)); c[len(labs) - 2] = 1
            s, d = CORE.bootstrap_linear(f, inf, c, common_signs)
            fitted.append((label, s, d))
        delta = fitted[0][1]["coefficient"] - fitted[1][1]["coefficient"]
        centered_delta = fitted[0][2] - fitted[1][2]
        se = float(centered_delta.std(ddof=1)); critical = float(
            np.quantile(np.abs(centered_delta / se), .95, method="higher"))
        result.update({
            "common_beta_support_occupations": len(common),
            "common_support_external_coefficient": fitted[0][1]["coefficient"],
            "common_support_beta_coefficient": fitted[1][1]["coefficient"],
            "external_minus_beta_difference": delta,
            "external_minus_beta_paired_se": se,
            "external_minus_beta_ci_lower": delta - critical * se,
            "external_minus_beta_ci_upper": delta + critical * se,
        })
    return record, result


def run(args):
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = CORE.load_data(args)
    bridge, mapping = read_soc_maps(args.bls_crosswalk, args.census_crosswalk)
    employment = oews_weights(args.oews_2021)
    webb_raw, webb_meta = webb_soc(args.webb_file, bridge)
    oecd_raw, oecd_meta = oecd_soc(args.oecd_file)
    webb = collapse_full_component(webb_raw, mapping, employment, "webb_ai")
    oecd = collapse_full_component(oecd_raw, mapping, employment, "oecd_ai_gap_reversed")
    audits, results = [], []
    specs = [
        ("Webb_AI_patent_task", webb, webb_meta, args.webb_file,
         args.webb_url, "patent-task overlap for patents classified as AI"),
        ("OECD_AI_capability_gap_reversed", oecd, oecd_meta, args.oecd_file,
         args.oecd_url, "reversed gap between nine AI capability domains and occupational demands"),
    ]
    for spec in specs:
        audit, result = evaluate_and_fit(args, data, *spec)
        audits.append(audit)
        if result is not None:
            results.append(result)
    write_csv(args.output_dir / "EXTERNAL_ARCHITECTURE_ADMISSION.csv", audits)
    if results:
        write_csv(args.output_dir / "EXTERNAL_ARCHITECTURE_OUTCOMES.csv", results)
    write_csv(args.output_dir / "WEBB_AI_CENSUS2018_MAP.csv", webb.reset_index().to_dict("records"))
    write_csv(args.output_dir / "OECD_CENSUS2018_MAP.csv", oecd.reset_index().to_dict("records"))
    receipt = {"analysis_status": LABEL, "baseline_reproduced": data["baseline_reproduced"],
               "inputs": {"webb": sha256(args.webb_file), "oecd": sha256(args.oecd_file),
                          "bls_crosswalk": sha256(args.bls_crosswalk),
                          "census_crosswalk": sha256(args.census_crosswalk),
                          "oews_2021": sha256(args.oews_2021)},
               "admission_rule": sha256(HERE / "EXTERNAL_ARCHITECTURE_ADMISSION_RULE.md"),
               "admitted": [row["architecture"] for row in audits if row["admitted"]]}
    write_json(args.output_dir / "EXTERNAL_ARCHITECTURE_RECEIPT.json", receipt)
    print(json.dumps(receipt, indent=2))


def parser():
    value = CORE.parser()
    value.description = __doc__
    value.add_argument("--webb-file", type=pathlib.Path, required=True)
    value.add_argument("--oecd-file", type=pathlib.Path, required=True)
    value.add_argument("--bls-crosswalk", type=pathlib.Path, required=True)
    value.add_argument("--census-crosswalk", type=pathlib.Path, required=True)
    value.add_argument("--oews-2021", type=pathlib.Path, required=True)
    value.add_argument("--webb-url", default="https://github.com/openai/GPTs-are-GPTs/blob/main/data/autoScores.csv")
    value.add_argument("--oecd-url", default="https://www.oecd.org/en/publications/the-oecd-ai-exposure-measure_f3da0f0a-en.html")
    return value


if __name__ == "__main__":
    run(parser().parse_args())
