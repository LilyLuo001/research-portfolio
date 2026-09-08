#!/usr/bin/env python3
"""Run the current-contract D05--D07 age and enrollment comparisons on SCC."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
DRAWS = 9_999
SEED = 202609089101
MARCH_REPAIRS = {f"{year}-03" for year in range(2017, 2022)}
OLDER_BANDS = {
    "26_30": (26, 30),
    "31_40": (31, 40),
    "41_50": (41, 50),
    "51_65": (51, 65),
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


MAP = load_module("yax_cohort_mapping_helpers",
                  HERE.parents[1] / "gate3" / "mapping" / "run_mapping_sensitivity.py")
CORE = MAP.CORE


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    require(bool(rows), f"refusing to write empty {path.name}")
    fields: list[str] = []
    for row in rows:
        fields.extend(field for field in row if field not in fields)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def month_string(frame: pd.DataFrame) -> pd.Series:
    return (pd.to_numeric(frame.YEAR, errors="raise").astype(int).astype(str) + "-" +
            pd.to_numeric(frame.MONTH, errors="raise").astype(int).astype(str).str.zfill(2))


def education_group(code: pd.Series) -> pd.Series:
    value = pd.to_numeric(code, errors="coerce")
    return pd.Series(np.select(
        [value.eq(111) | value.between(120, 125), value.between(2, 110)],
        ["BA_plus", "non_BA"], default="invalid"), index=code.index)


def school_group(code: pd.Series) -> pd.Series:
    value = pd.to_numeric(code, errors="coerce")
    return pd.Series(np.select(
        [value.isin([1, 2, 3, 4]), value.eq(5)],
        ["enrolled", "not_enrolled"], default="invalid"), index=code.index)


def employment_group(code: pd.Series) -> pd.Series:
    value = pd.to_numeric(code, errors="coerce")
    return pd.Series(np.select(
        [value.isin([10, 12]), value.isin([20, 21, 22]),
         value.isin([30, 31, 32, 34, 36])],
        ["employed", "unemployed", "not_in_labor_force"], default="other"),
        index=code.index)


def age_bucket(age: pd.Series) -> pd.Series:
    value = pd.to_numeric(age, errors="coerce")
    return pd.Series(np.select(
        [value.between(16, 21), value.between(22, 25),
         value.between(26, 54), value.between(55, 65)],
        ["16_21", "22_25", "26_54", "55_65"], default="outside_audit"),
        index=age.index)


def scan_sources(wide: Path, repair: Path, bridge_path: Path,
                 support: set[str], months: list[str]) -> tuple[pd.DataFrame, pd.DataFrame,
                                                                pd.DataFrame, dict[str, Any]]:
    """Return routed employed cells, national person aggregates, and code audit."""
    bridge = pd.read_csv(bridge_path, dtype={"census_2010": str, "census_2018": str},
                         float_precision="round_trip")
    bridge["census_2010"] = bridge.census_2010.str.zfill(4)
    bridge["census_2018"] = bridge.census_2018.str.zfill(4)
    bridge["bridge_weight"] = pd.to_numeric(bridge.bridge_weight, errors="raise")
    bridge = bridge.loc[bridge.census_2018.isin(support)].copy()
    routed_parts: list[pd.DataFrame] = []
    population_parts: list[pd.DataFrame] = []
    audit_parts: list[pd.DataFrame] = []
    counters = {"raw_rows": 0, "wide_march_rows_removed": 0,
                "positive_weight_person_rows": 0, "employed_source_rows": 0,
                "routed_descendant_rows": 0, "fractional_descendant_rows": 0}
    usecols = ["YEAR", "MONTH", "AGE", "EMPSTAT", "OCC", "EDUC", "SCHLCOLL", "WTFINL"]
    for source, path in (("wide", wide), ("march_repair", repair)):
        for chunk in pd.read_csv(path, usecols=usecols, chunksize=400_000):
            counters["raw_rows"] += len(chunk)
            chunk["month"] = month_string(chunk)
            if source == "wide":
                replaced = chunk.month.isin(MARCH_REPAIRS)
                counters["wide_march_rows_removed"] += int(replaced.sum())
                chunk = chunk.loc[~replaced].copy()
            else:
                require(set(chunk.month.unique()).issubset(MARCH_REPAIRS),
                        "March repair contains a non-repair month")
            chunk = chunk.loc[chunk.month.isin(months)].copy()
            if chunk.empty:
                continue
            age = pd.to_numeric(chunk.AGE, errors="coerce")
            weight = pd.to_numeric(chunk.WTFINL, errors="coerce")
            person = age.between(16, 65) & np.isfinite(weight) & weight.gt(0)
            people = chunk.loc[person].copy()
            if people.empty:
                continue
            people["age"] = age.loc[people.index].astype(int)
            people["weight"] = weight.loc[people.index].astype(float)
            people["year"] = pd.to_numeric(people.YEAR, errors="raise").astype(int)
            people["education_group"] = education_group(people.EDUC)
            people["school_group"] = school_group(people.SCHLCOLL)
            people["employment_group"] = employment_group(people.EMPSTAT)
            people["age_bucket"] = age_bucket(people.age)
            people["school_code"] = pd.to_numeric(
                people.SCHLCOLL, errors="coerce").fillna(-999).astype(int)
            counters["positive_weight_person_rows"] += len(people)

            pop = people.loc[people.age.between(22, 65)].groupby(
                ["month", "year", "age", "education_group", "school_group",
                 "employment_group"], as_index=False, observed=True).agg(
                    person_rows=("weight", "size"), weighted_persons=("weight", "sum"))
            population_parts.append(pop)
            audited = people.groupby(
                ["month", "age_bucket", "school_code"], as_index=False,
                observed=True).agg(person_rows=("weight", "size"),
                                   weighted_persons=("weight", "sum"))
            audited["source"] = source
            audit_parts.append(audited)

            employed = people.loc[
                people.age.between(22, 65) & people.employment_group.eq("employed")].copy()
            occ = pd.to_numeric(employed.OCC, errors="coerce")
            employed = employed.loc[
                occ.notna() & occ.between(0, 9999) & occ.mod(1).eq(0)].copy()
            if employed.empty:
                continue
            employed["source_occ"] = occ.loc[employed.index].astype(int).map(
                lambda value: f"{value:04d}")
            counters["employed_source_rows"] += len(employed)
            early = employed.loc[employed.year.le(2019)].merge(
                bridge, left_on="source_occ", right_on="census_2010", how="inner",
                validate="many_to_many")
            early["occ_code"] = early.census_2018
            early["route_weight"] = early.bridge_weight
            current = employed.loc[
                employed.year.ge(2020) & employed.source_occ.isin(support)].copy()
            current["occ_code"] = current.source_occ
            current["route_weight"] = 1.0
            routed = pd.concat([early, current], ignore_index=True, sort=False)
            if routed.empty:
                continue
            routed["stock"] = routed.weight * routed.route_weight
            routed["respondent_equivalent"] = routed.route_weight
            counters["routed_descendant_rows"] += len(routed)
            counters["fractional_descendant_rows"] += int(
                np.sum(~np.isclose(routed.route_weight.to_numpy(float), 1.0)))
            routed_parts.append(routed.groupby(
                ["occ_code", "month", "year", "age", "education_group", "school_group"],
                as_index=False, observed=True)[["stock", "respondent_equivalent"]].sum())

    require(bool(routed_parts) and bool(population_parts) and bool(audit_parts),
            "microdata scan produced an empty output")
    routed = pd.concat(routed_parts, ignore_index=True).groupby(
        ["occ_code", "month", "year", "age", "education_group", "school_group"],
        as_index=False, observed=True)[["stock", "respondent_equivalent"]].sum()
    population = pd.concat(population_parts, ignore_index=True).groupby(
        ["month", "year", "age", "education_group", "school_group", "employment_group"],
        as_index=False, observed=True)[["person_rows", "weighted_persons"]].sum()
    audit = pd.concat(audit_parts, ignore_index=True).groupby(
        ["source", "month", "age_bucket", "school_code"], as_index=False,
        observed=True)[["person_rows", "weighted_persons"]].sum()
    return routed, population, audit, counters


def stock_matrix(routed: pd.DataFrame, occupations: np.ndarray, months: list[str],
                 mask: pd.Series, value: str = "stock") -> np.ndarray:
    part = routed.loc[mask].groupby(["occ_code", "month"], as_index=False,
                                    observed=True)[value].sum()
    index = pd.MultiIndex.from_product([occupations.tolist(), months],
                                       names=["occ_code", "month"])
    return (part.set_index(["occ_code", "month"])[value].reindex(index, fill_value=0.0)
            .to_numpy(float).reshape(len(occupations), len(months)))


def fixed_age_standardization(population: pd.DataFrame, routed: pd.DataFrame,
                              months: list[str]) -> tuple[np.ndarray, list[dict[str, Any]], float]:
    ages = list(range(26, 66))
    counts = population.groupby(["age", "month"], observed=True).weighted_persons.sum().unstack()
    counts = counts.reindex(index=ages, columns=months, fill_value=0.0).to_numpy(float)
    require(np.all(np.isfinite(counts)) and np.all(counts > 0),
            "an exact-age national population denominator is nonpositive")
    pre = np.asarray([month <= "2022-11" for month in months], bool)
    pi = counts[:, pre].sum(axis=1)
    pi /= pi.sum()
    month_total = counts.sum(axis=0)
    factor = month_total[None, :] * pi[:, None] / counts
    gap = float(np.max(np.abs((counts * factor).sum(axis=0) - month_total) /
                             np.maximum(month_total, 1.0)))
    require(gap <= 1e-12, "fixed-age standardization does not preserve population totals")
    factor_frame = pd.DataFrame(factor, index=ages, columns=months)
    older = routed.loc[routed.age.between(26, 65)].copy()
    older["standardization_factor"] = [
        factor_frame.at[int(age), month] for age, month in zip(older.age, older.month)]
    older["standardized_stock"] = older.stock * older.standardization_factor
    rows = [{
        "exact_age": age,
        "preperiod_reference_population_share": float(pi[index]),
        "minimum_month_factor": float(factor[index].min()),
        "maximum_month_factor": float(factor[index].max()),
        "mean_month_factor": float(factor[index].mean()),
        "preperiod_weighted_population": float(counts[index, pre].sum()),
    } for index, age in enumerate(ages)]
    return older, rows, gap


def prepositive(*arrays: np.ndarray, pre: np.ndarray) -> np.ndarray:
    keep = np.ones(arrays[0].shape[0], bool)
    for value in arrays:
        require(value.shape == arrays[0].shape, "support arrays differ")
        keep &= value[:, pre].sum(axis=1) > 0
    return keep


def composition_rows(frame: pd.DataFrame, keys: list[str], weight: str,
                     national: bool) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, group in frame.groupby(keys, observed=True):
        if not isinstance(key, tuple):
            key = (key,)
        row = dict(zip(keys, key))
        weights = group[weight].to_numpy(float)
        total = float(weights.sum())
        require(total > 0, "composition group has nonpositive weight")
        row.update({
            "weighted_population_or_stock": total,
            "weighted_mean_age": float(np.average(group.age, weights=weights)),
            "weighted_mean_birth_year_proxy": float(np.average(group.year - group.age,
                                                                  weights=weights)),
            "BA_plus_share": float(weights[group.education_group.eq("BA_plus")].sum() / total),
            "education_valid_share": float(weights[group.education_group.ne("invalid")].sum() / total),
            "enrollment_valid_share": float(weights[group.school_group.ne("invalid")].sum() / total),
        })
        valid_school = group.school_group.ne("invalid").to_numpy()
        row["enrolled_share_among_valid"] = float(
            weights[group.school_group.eq("enrolled")].sum() / weights[valid_school].sum()
        ) if weights[valid_school].sum() > 0 else math.nan
        for age in range(22, 26):
            row[f"age_{age}_share"] = float(weights[group.age.eq(age)].sum() / total)
        if national:
            row["employment_rate"] = float(
                weights[group.employment_group.eq("employed")].sum() / total)
            row["unemployment_population_share"] = float(
                weights[group.employment_group.eq("unemployed")].sum() / total)
        rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--microdata", type=Path, required=True)
    parser.add_argument("--repair-microdata", type=Path, required=True)
    parser.add_argument("--bridge", type=Path, required=True)
    parser.add_argument("--membership", type=Path, required=True)
    parser.add_argument("--private-calibration", type=Path, required=True)
    parser.add_argument("--calibration-receipt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output_dir.exists(), "refusing to overwrite cohort/enrollment output")
    require(sha256_file(args.membership) == MAP.MEMBERSHIP_SHA256, "membership hash differs")
    require(sha256_file(args.bridge) == MAP.BRIDGE_SHA256, "bridge hash differs")
    receipt = json.loads(args.calibration_receipt.read_text(encoding="utf-8"))
    require(receipt.get("status") == "PASS_PRIVATE_CALIBRATION_BUILD",
            "private calibration receipt does not pass")
    require(sha256_file(args.private_calibration) == receipt.get("private_npz_sha256"),
            "private calibration hash differs")
    require(sha256_file(args.microdata) == receipt["input_hashes"]["wide_microdata"],
            "wide microdata hash differs")
    require(sha256_file(args.repair_microdata) == receipt["input_hashes"]["march_repair"],
            "March repair hash differs")

    with np.load(args.private_calibration, allow_pickle=False) as loaded:
        arrays = {name: loaded[name] for name in loaded.files}
    occupations = arrays["occupations"].astype(str)
    families = arrays["families"].astype(str)
    months = arrays["months"].astype(str).tolist()
    require(len(occupations) == 468 and len(months) == 113,
            "protected current-contract dimensions differ")
    membership = pd.read_csv(args.membership, dtype={"occupation_code": str},
                             float_precision="round_trip")
    membership["occupation_code"] = membership.occupation_code.str.zfill(4)
    membership = membership.set_index("occupation_code").reindex(occupations)
    require(not membership.isna().any().any(), "membership does not align")
    quintiles = membership.beta_quintile.to_numpy(int)
    webb_z = membership.webb_z.to_numpy(float)
    require(np.array_equal(quintiles, arrays["quintiles"]), "quintiles differ")
    require(np.allclose(webb_z, arrays["webb_z"], rtol=0, atol=1e-12),
            "Webb normalization differs")

    routed, population, school_audit, counters = scan_sources(
        args.microdata, args.repair_microdata, args.bridge,
        set(occupations.tolist()), months)
    young = stock_matrix(routed, occupations, months, routed.age.between(22, 25))
    older_full = stock_matrix(routed, occupations, months, routed.age.between(26, 65))
    n_cell = len(occupations) * len(months)
    protected = np.bincount(arrays["cellage"], weights=arrays["route_stock"],
                            minlength=2 * n_cell)
    protected_young = protected[:n_cell].reshape(len(occupations), len(months))
    protected_older = protected[n_cell:].reshape(len(occupations), len(months))
    rebuild_gap = float(max(
        np.max(np.abs(young - protected_young) / np.maximum(protected_young, 1.0)),
        np.max(np.abs(older_full - protected_older) / np.maximum(protected_older, 1.0))))
    require(rebuild_gap <= 1e-10, "current young/older cells do not reproduce calibration")

    older_standardized_frame, standardization_rows, standardization_gap = (
        fixed_age_standardization(population, routed, months))
    older_standardized = stock_matrix(
        older_standardized_frame, occupations, months,
        pd.Series(True, index=older_standardized_frame.index), "standardized_stock")
    band_arrays = {name: stock_matrix(
        routed, occupations, months, routed.age.between(low, high))
        for name, (low, high) in OLDER_BANDS.items()}
    young_non = stock_matrix(
        routed, occupations, months,
        routed.age.between(22, 25) & routed.school_group.eq("not_enrolled"))
    older_26_54 = stock_matrix(routed, occupations, months, routed.age.between(26, 54))
    older_26_54_non = stock_matrix(
        routed, occupations, months,
        routed.age.between(26, 54) & routed.school_group.eq("not_enrolled"))
    pre = np.asarray([month <= "2022-11" for month in months], bool)
    d05_keep = prepositive(young, older_full, older_standardized,
                           *band_arrays.values(), pre=pre)
    d06_all_keep = prepositive(young, young_non, older_full, pre=pre)
    d06_common_keep = prepositive(young, young_non, older_26_54,
                                  older_26_54_non, pre=pre)
    for label, keep in (("D05", d05_keep), ("D06_all_older", d06_all_keep),
                        ("D06_common_universe", d06_common_keep)):
        require(keep.sum() > 4 and set(quintiles[keep]) == {1, 2, 3, 4, 5},
                f"{label} support loses a quintile")

    global_families = sorted(set(families.tolist()))
    draws = CORE.draw_multiplier_matrices(DRAWS, len(occupations), len(global_families), SEED)
    multipliers = {"occupation": draws["occupation_rademacher"],
                   "family": draws["family_rademacher"]}
    models: dict[str, dict[str, Any]] = {}
    model_rows: list[dict[str, Any]] = []
    pair_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    def add(model_id: str, structure: str, numerator: np.ndarray,
            denominator: np.ndarray, keep: np.ndarray, block: str,
            definition: str) -> dict[str, Any]:
        try:
            result = MAP.fit_model(
                model_id, structure, numerator, denominator, keep, quintiles,
                webb_z, families, occupations, months, multipliers,
                {"requirement_block": block, "numerator_population": "ages_22_25",
                 "denominator_definition": definition,
                 "older_is_untreated": False, "fixed_current_labels": True})
        except Exception as error:
            failures.append({"model_id": model_id, "error": repr(error)})
            args.output_dir.mkdir(parents=True, exist_ok=True)
            write_json(args.output_dir / "MODEL_FAILURES.json", failures)
            raise
        models[model_id] = result
        model_rows.append(result["row"])
        return result

    for structure in ("pooled", "family_month"):
        base = add(f"d05_22_25_vs_26_65_{structure}", structure, young,
                   older_full, d05_keep, "D05", "ages_26_65_observed")
        for name, denominator in band_arrays.items():
            other = add(f"d05_22_25_vs_{name}_{structure}", structure, young,
                        denominator, d05_keep, "D05", f"ages_{name}")
            pair_rows.append(MAP.paired_row(
                f"d05_{name}_minus_26_65_{structure}", other, base, multipliers))
        standardized = add(f"d05_22_25_vs_26_65_fixed_age_{structure}", structure,
                           young, older_standardized, d05_keep, "D05",
                           "ages_26_65_fixed_preperiod_exact_age_composition")
        pair_rows.append(MAP.paired_row(
            f"d05_fixed_age_minus_observed_age_{structure}", standardized, base,
            multipliers))

        unrestricted_all = add(
            f"d06_unrestricted_young_vs_all_older_{structure}", structure,
            young, older_full, d06_all_keep, "D06",
            "all_employed_ages_26_65")
        restricted_young = add(
            f"d06_nonenrolled_young_vs_all_older_{structure}", structure,
            young_non, older_full, d06_all_keep, "D06",
            "all_employed_ages_26_65; numerator restricted to SCHLCOLL=5")
        pair_rows.append(MAP.paired_row(
            f"d06_nonenrolled_young_minus_unrestricted_young_{structure}",
            restricted_young, unrestricted_all, multipliers))

        unrestricted_common = add(
            f"d06_unrestricted_22_25_vs_26_54_{structure}", structure,
            young, older_26_54, d06_common_keep, "D06",
            "all_employed_ages_26_54_within_enrollment_question_age_universe")
        nonenrolled_common = add(
            f"d06_nonenrolled_22_25_vs_nonenrolled_26_54_{structure}", structure,
            young_non, older_26_54_non, d06_common_keep, "D06",
            "SCHLCOLL=5_for_both_ages_22_25_and_26_54")
        pair_rows.append(MAP.paired_row(
            f"d06_common_universe_nonenrolled_minus_unrestricted_{structure}",
            nonenrolled_common, unrestricted_common, multipliers))

    support_rows = []
    for index, code in enumerate(occupations):
        row: dict[str, Any] = {
            "occupation_code": code,
            "occupation_name": membership.occupation_name.iloc[index],
            "beta_quintile": int(quintiles[index]),
            "d05_common_support": bool(d05_keep[index]),
            "d06_young_restriction_support": bool(d06_all_keep[index]),
            "d06_common_enrollment_universe_support": bool(d06_common_keep[index]),
            "pre_young_22_25_stock": float(young[index, pre].sum()),
            "pre_older_26_65_stock": float(older_full[index, pre].sum()),
            "pre_nonenrolled_young_stock": float(young_non[index, pre].sum()),
            "pre_older_26_54_stock": float(older_26_54[index, pre].sum()),
            "pre_nonenrolled_older_26_54_stock": float(older_26_54_non[index, pre].sum()),
        }
        row.update({f"pre_older_{name}_stock": float(value[index, pre].sum())
                    for name, value in band_arrays.items()})
        support_rows.append(row)

    influence_rows: list[dict[str, Any]] = []
    for model in models.values():
        influence_rows.extend(MAP.influence_rows(model, occupations, global_families))

    routed_young = routed.loc[routed.age.between(22, 25)].copy()
    routed_young["beta_quintile"] = routed_young.occ_code.map(
        membership.beta_quintile.to_dict()).astype(int)
    routed_young["period"] = np.where(routed_young.month.le("2022-11"), "pre", "post")
    employed_composition = composition_rows(
        routed_young, ["year", "beta_quintile"], "stock", national=False)
    employed_composition += composition_rows(
        routed_young, ["period", "beta_quintile"], "stock", national=False)
    national_young = population.loc[population.age.between(22, 25)].copy()
    national_young["period"] = np.where(national_young.month.le("2022-11"), "pre", "post")
    national_composition = composition_rows(
        national_young, ["year"], "weighted_persons", national=True)
    national_composition += composition_rows(
        national_young, ["period"], "weighted_persons", national=True)

    audit_rows = school_audit.to_dict("records")
    valid_55_65 = school_audit.loc[
        school_audit.age_bucket.eq("55_65") & school_audit.school_code.isin([1, 2, 3, 4, 5])]
    args.output_dir.mkdir(parents=True)
    output_rows = {
        "MODEL_RESULTS.csv": model_rows,
        "PAIRED_COMPARISONS.csv": pair_rows,
        "MODEL_INFLUENCE.csv": influence_rows,
        "SUPPORT_MEMBERSHIP.csv": support_rows,
        "AGE_STANDARDIZATION_WEIGHTS.csv": standardization_rows,
        "SCHLCOLL_CODE_AUDIT.csv": audit_rows,
        "EMPLOYED_YOUNG_COMPOSITION.csv": employed_composition,
        "NATIONAL_YOUNG_POPULATION_COMPOSITION.csv": national_composition,
    }
    for name, rows in output_rows.items():
        write_csv(args.output_dir / name, rows)
    write_json(args.output_dir / "MODEL_FAILURES.json", failures)
    output_names = [*output_rows, "MODEL_FAILURES.json"]
    run_receipt = {
        "schema_version": "yax-gate4-cohort-enrollment-v1",
        "status": "PASS_GATE4_COHORT_ENROLLMENT",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                              text=True).strip(),
        "sge_job_id": os.environ.get("JOB_ID"),
        "input_hashes": {
            "wide_microdata": sha256_file(args.microdata),
            "march_repair": sha256_file(args.repair_microdata),
            "bridge": sha256_file(args.bridge),
            "membership": sha256_file(args.membership),
            "private_calibration": sha256_file(args.private_calibration),
            "calibration_receipt": sha256_file(args.calibration_receipt),
            "specification": sha256_file(HERE / "COHORT_ENROLLMENT_SPEC.md"),
            "runner": sha256_file(Path(__file__)),
        },
        "canonical_rebuild_maximum_relative_gap": rebuild_gap,
        "fixed_age_population_identity_maximum_relative_gap": standardization_gap,
        "SCHLCOLL_valid_code_weight_ages_55_65": float(valid_55_65.weighted_persons.sum()),
        "SCHLCOLL_invalid_codes_never_classified_nonenrolled": True,
        "nonworker_occupational_exposure_assignment_count": 0,
        "older_groups_are_untreated": False,
        "support_counts": {
            "D05": int(d05_keep.sum()),
            "D06_young_restriction": int(d06_all_keep.sum()),
            "D06_common_enrollment_universe": int(d06_common_keep.sum()),
        },
        "model_count": len(model_rows), "paired_comparison_count": len(pair_rows),
        "model_failure_count": len(failures), "draws": DRAWS, "seed": SEED,
        "common_draws_preserve_covariance": True,
        "scan_counters": counters,
        "protected_person_or_household_rows_written": False,
        "output_hashes": {name: sha256_file(args.output_dir / name)
                          for name in output_names},
    }
    write_json(args.output_dir / "EXECUTION_RECEIPT.json", run_receipt)
    print(json.dumps({"status": run_receipt["status"], "models": len(model_rows),
                      "pairs": len(pair_rows)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
