#!/usr/bin/env python3
"""Run the fixed public RPS detailed-occupation adoption diagnostic."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
RPS_SHA256 = "2212465781179782c6f69750af21b00bd545edc21581d9577fbf7affc1bf0c43"
PRIMARY_SHA256 = "c76eb85956e4a413e130bab53fe8c50616cf6d7a02c81c266ec369879dd56bc1"
BROADER_SHA256 = "2fe1967db31dea51e007861867e01bd6fa872828a9d589bc0490212e534220fc"
SHEET = "2018 Census Occupation Code"
EXPECTED_HEADER = (
    "census_occupation_code", "census_occupation_name",
    "adoption_rate", "number_observations",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def git_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _xlsx_rows(path: Path, sheet_name: str) -> list[list[object]]:
    """Read a small value-only XLSX sheet with standard-library XML."""
    main_ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    doc_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    pkg_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rid = None
        for sheet in workbook.findall(f".//{{{main_ns}}}sheet"):
            if sheet.attrib.get("name") == sheet_name:
                rid = sheet.attrib[f"{{{doc_ns}}}id"]
                break
        require(rid is not None, f"missing workbook sheet {sheet_name}")
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {
            node.attrib["Id"]: node.attrib["Target"]
            for node in relationships.findall(f"{{{pkg_ns}}}Relationship")
        }
        require(rid in targets, "workbook sheet relationship is missing")
        target = targets[rid]
        sheet_path = target.lstrip("/")
        if not sheet_path.startswith("xl/"):
            sheet_path = "xl/" + sheet_path
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in strings.findall(f"{{{main_ns}}}si"):
                shared.append("".join(
                    node.text or "" for node in item.iter(f"{{{main_ns}}}t")))
        sheet_xml = ET.fromstring(archive.read(sheet_path))
        output: list[list[object]] = []
        for row in sheet_xml.findall(f".//{{{main_ns}}}row"):
            values: dict[int, object] = {}
            for cell in row.findall(f"{{{main_ns}}}c"):
                reference = cell.attrib.get("r", "A1")
                letters = "".join(ch for ch in reference if ch.isalpha())
                column = 0
                for letter in letters:
                    column = column * 26 + ord(letter.upper()) - ord("A") + 1
                column -= 1
                value_node = cell.find(f"{{{main_ns}}}v")
                kind = cell.attrib.get("t")
                if kind == "inlineStr":
                    inline = cell.find(f"{{{main_ns}}}is")
                    value: object = "" if inline is None else "".join(
                        node.text or "" for node in inline.iter(f"{{{main_ns}}}t"))
                elif value_node is None:
                    value = ""
                elif kind == "s":
                    value = shared[int(value_node.text or "0")]
                elif kind in {"str", "e"}:
                    value = value_node.text or ""
                else:
                    text = value_node.text or ""
                    try:
                        value = float(text)
                    except ValueError:
                        value = text
                values[column] = value
            width = max(values, default=-1) + 1
            output.append([values.get(column, "") for column in range(width)])
    return output


def load_rps(path: Path) -> pd.DataFrame:
    rows = _xlsx_rows(path, SHEET)
    require(bool(rows) and tuple(rows[0]) == EXPECTED_HEADER,
            "RPS detailed-occupation header differs")
    padded = [row + [""] * (len(EXPECTED_HEADER) - len(row)) for row in rows[1:]]
    frame = pd.DataFrame(
        [row[:len(EXPECTED_HEADER)] for row in padded], columns=EXPECTED_HEADER)
    frame["occ_code"] = frame.census_occupation_code.map(
        lambda value: str(int(float(value))).zfill(4) if str(value).strip() else "")
    frame["adoption_rate"] = pd.to_numeric(frame.adoption_rate, errors="coerce")
    frame["number_observations"] = pd.to_numeric(
        frame.number_observations, errors="coerce")
    require(frame.occ_code.ne("").all() and not frame.occ_code.duplicated().any(),
            "RPS detailed occupation codes are empty or duplicated")
    observed = frame.adoption_rate.notna()
    require(frame.loc[observed, "adoption_rate"].between(0, 1).all(),
            "RPS adoption rate lies outside [0,1]")
    require((frame.loc[observed, "number_observations"] >= 20).all(),
            "RPS nonsuppressed cell has fewer than 20 observations")
    return frame[[
        "occ_code", "census_occupation_name", "adoption_rate",
        "number_observations",
    ]].copy()


def _boolean(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().map({"true": True, "false": False})


def load_yax(primary_path: Path, broader_path: Path) -> pd.DataFrame:
    primary = pd.read_csv(primary_path, dtype={"occupation_code": str},
                          float_precision="round_trip")
    broader = pd.read_csv(broader_path, dtype={"occupation_code": str},
                          float_precision="round_trip")
    require(len(primary) == 468 and not primary.occupation_code.duplicated().any(),
            "frozen primary membership differs")
    primary["occ_code"] = primary.occupation_code.str.zfill(4)
    broader["occ_code"] = broader.occupation_code.str.zfill(4)
    broader["in_primary_468"] = _boolean(broader.in_primary_468)
    support = broader.loc[broader.in_primary_468, [
        "occ_code", "family", "rule_A_beta", "primary_quintile_if_present",
    ]].copy()
    require(len(support) == 468 and not support.occ_code.duplicated().any(),
            "broader file does not uniquely cover the frozen primary support")
    merged = primary.merge(support, on="occ_code", how="left", validate="one_to_one")
    require(merged.family.notna().all(), "SOC family is missing on primary support")
    require(np.max(np.abs(
        merged.rule_A_beta_x.to_numpy(float) -
        merged.rule_A_beta_y.to_numpy(float))) <= 1e-12,
        "frozen exposure values differ across membership files")
    require(np.array_equal(
        merged.beta_quintile.to_numpy(int),
        merged.primary_quintile_if_present.to_numpy(int)),
        "frozen quintiles differ across membership files")
    return merged.rename(columns={
        "occupation_name": "yax_occupation_name",
        "rule_A_beta_x": "rule_A_beta",
        "beta_quintile": "beta_quintile",
    })[[
        "occ_code", "yax_occupation_name", "family", "rule_A_beta",
        "beta_quintile", "preperiod_weight",
    ]].copy()


def weighted_moments(x: np.ndarray, y: np.ndarray,
                     weight: np.ndarray) -> dict[str, float]:
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    weight = np.asarray(weight, float)
    require(x.shape == y.shape == weight.shape and np.all(weight > 0),
            "weighted-moment inputs differ")
    total = float(weight.sum())
    x_mean = float(weight @ x / total)
    y_mean = float(weight @ y / total)
    xc, yc = x - x_mean, y - y_mean
    xx = float(weight @ np.square(xc))
    yy = float(weight @ np.square(yc))
    xy = float(weight @ (xc * yc))
    require(xx > 0 and yy > 0, "weighted moments are degenerate")
    return {
        "pearson_correlation": xy / np.sqrt(xx * yy),
        "ols_slope_adoption_on_beta": xy / xx,
        "beta_mean": x_mean,
        "adoption_mean": y_mean,
    }


def family_moments(frame: pd.DataFrame, weight: np.ndarray) -> dict[str, float]:
    work = frame[["family", "rule_A_beta", "adoption_rate"]].copy()
    work["weight"] = np.asarray(weight, float)
    totals = work.groupby("family", observed=True).weight.transform("sum")
    xbar = (work.weight * work.rule_A_beta).groupby(
        work.family, observed=True).transform("sum") / totals
    ybar = (work.weight * work.adoption_rate).groupby(
        work.family, observed=True).transform("sum") / totals
    xr = work.rule_A_beta.to_numpy(float) - xbar.to_numpy(float)
    yr = work.adoption_rate.to_numpy(float) - ybar.to_numpy(float)
    w = work.weight.to_numpy(float)
    x = work.rule_A_beta.to_numpy(float)
    overall = float(w @ x / w.sum())
    total_ss = float(w @ np.square(x - overall))
    within_ss = float(w @ np.square(xr))
    require(total_ss > 0 and within_ss > 0, "within-family exposure is degenerate")
    counts = work.groupby("family", observed=True).size()
    return {
        "within_family_exposure_ss_share": within_ss / total_ss,
        "within_family_slope_adoption_on_beta": float(w @ (xr * yr) / within_ss),
        "matched_families": float(counts.size),
        "families_with_at_least_two_occupations": float((counts >= 2).sum()),
    }


def compute(primary: pd.DataFrame, rps: pd.DataFrame
            ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    coverage = primary.merge(rps, on="occ_code", how="left", validate="one_to_one")
    coverage["matched_nonsuppressed"] = (
        coverage.adoption_rate.notna() &
        coverage.number_observations.notna() &
        coverage.number_observations.gt(0))
    coverage["coverage_status"] = np.where(
        coverage.matched_nonsuppressed, "matched_nonsuppressed",
        np.where(coverage.census_occupation_name.notna(),
                 "rps_suppressed_or_missing_rate", "rps_code_absent"))
    matched = coverage.loc[coverage.matched_nonsuppressed].copy()
    require(set(matched.beta_quintile.astype(int)) == {1, 2, 3, 4, 5},
            "matched RPS support loses a frozen quintile")
    counts = matched.groupby("family", observed=True).size()
    require(int((counts >= 2).sum()) >= 10,
            "fewer than ten SOC families have two matched occupations")
    summary_rows: list[dict[str, object]] = []
    for weighting, weight in (
            ("equal_occupation", np.ones(len(matched))),
            ("reported_observation_count_sensitivity",
             matched.number_observations.to_numpy(float))):
        moments = weighted_moments(
            matched.rule_A_beta.to_numpy(float),
            matched.adoption_rate.to_numpy(float), weight)
        families = family_moments(matched, weight)
        for metric, estimate in {**moments, **families}.items():
            summary_rows.append({
                "weighting": weighting, "metric": metric,
                "estimate": estimate,
            })
    ranks_x = matched.rule_A_beta.rank(method="average").to_numpy(float)
    ranks_y = matched.adoption_rate.rank(method="average").to_numpy(float)
    spearman = weighted_moments(ranks_x, ranks_y, np.ones(len(matched)))[
        "pearson_correlation"]
    summary_rows.append({
        "weighting": "equal_occupation", "metric": "spearman_rank_correlation",
        "estimate": spearman,
    })
    quintile_rows: list[dict[str, object]] = []
    for weighting, weight in (
            ("equal_occupation", np.ones(len(matched))),
            ("reported_observation_count_sensitivity",
             matched.number_observations.to_numpy(float))):
        work = matched[["beta_quintile", "adoption_rate"]].copy()
        work["weight"] = weight
        values: dict[int, float] = {}
        for quintile, group in work.groupby("beta_quintile", observed=True):
            value = float(group.weight @ group.adoption_rate / group.weight.sum())
            values[int(quintile)] = value
            quintile_rows.append({
                "weighting": weighting, "beta_quintile": int(quintile),
                "matched_occupations": len(group), "mean_adoption_rate": value,
            })
        summary_rows.append({
            "weighting": weighting, "metric": "Q5_minus_Q1_mean_adoption_rate",
            "estimate": values[5] - values[1],
        })
    unmatched_rps = rps.loc[~rps.occ_code.isin(set(primary.occ_code))].copy()
    return (pd.DataFrame(summary_rows), pd.DataFrame(quintile_rows),
            coverage, unmatched_rps)


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    frame.to_csv(path, index=False, lineterminator="\n", float_format="%.15g")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rps", type=Path, default=HERE / "inputs" /
                        "rps_adoption_rates_by_occupation_20260806.xlsx")
    parser.add_argument("--primary", type=Path, default=ROOT / "yax/revision/"
                        "substantive_v3_20260906/runs/gate1_baseline/results/"
                        "REBUILT_TREATMENT_MEMBERSHIP.csv")
    parser.add_argument("--broader", type=Path, default=ROOT / "yax/revision/"
                        "substantive_v3_20260906/runs/"
                        "gate2_broader_support_authoritative_20260908/"
                        "BROADER_SUPPORT_MEMBERSHIP.csv")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    expected = {
        args.rps: RPS_SHA256, args.primary: PRIMARY_SHA256,
        args.broader: BROADER_SHA256,
    }
    for path, expected_hash in expected.items():
        require(path.is_file() and digest(path) == expected_hash,
                f"authenticated input differs: {path}")
    primary = load_yax(args.primary, args.broader)
    rps = load_rps(args.rps)
    summary, quintiles, coverage, unmatched = compute(primary, rps)
    args.output.mkdir(parents=True, exist_ok=False)
    paths = {
        "summary": args.output / "ADOPTION_SUMMARY.csv",
        "quintiles": args.output / "ADOPTION_QUINTILES.csv",
        "coverage": args.output / "ADOPTION_COVERAGE.csv",
        "unmatched_rps": args.output / "RPS_UNMATCHED_CODES.csv",
    }
    write_csv(paths["summary"], summary)
    write_csv(paths["quintiles"], quintiles)
    write_csv(paths["coverage"], coverage)
    write_csv(paths["unmatched_rps"], unmatched)
    matched = coverage.loc[coverage.matched_nonsuppressed]
    receipt = {
        "schema": "yax.rps_adoption_extension.v1",
        "status": "PASS_FOCUSED_DESCRIPTIVE_ADOPTION_EXTENSION",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "input_sha256": {path.name: digest(path) for path in expected},
        "output_sha256": {key: digest(path) for key, path in paths.items()},
        "rps_rows": len(rps),
        "frozen_yax_occupations": len(primary),
        "matched_nonsuppressed_occupations": len(matched),
        "matched_quintiles": sorted(matched.beta_quintile.astype(int).unique().tolist()),
        "matched_families": int(matched.family.nunique()),
        "families_with_at_least_two_occupations": int(
            (matched.groupby("family", observed=True).size() >= 2).sum()),
        "suppressed_or_missing_rate": int(
            coverage.coverage_status.eq("rps_suppressed_or_missing_rate").sum()),
        "rps_code_absent": int(coverage.coverage_status.eq("rps_code_absent").sum()),
        "inference": "none_detailed_cell_sampling_uncertainty_unavailable",
        "timing": "pooled_future_post_outcome_occupation_classification",
        "causal_interpretation_permitted": False,
    }
    receipt_path = args.output / "ADOPTION_RUN_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": receipt["status"],
        "matched": receipt["matched_nonsuppressed_occupations"],
        "output": str(args.output.resolve()),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
