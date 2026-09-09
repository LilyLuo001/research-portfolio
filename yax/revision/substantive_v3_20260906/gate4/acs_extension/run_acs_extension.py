#!/usr/bin/env python3
"""Run the public one-year ACS benchmark and annual YAX extension."""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterable
import zipfile

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
YEARS = (2017, 2018, 2019, 2021, 2022, 2023, 2024)
MODEL_YEARS = (2017, 2018, 2019, 2021, 2023, 2024)
NONREUSE_MODEL_YEARS = (2017, 2021, 2023, 2024)
REPLICATES = 80
SDR_FACTOR = 4.0 / REPLICATES
NORMAL_975 = 1.959963984540054
DRAWS = 9_999
SEED = 202609081417
WEIGHT_COLUMNS = ("PWGTP",) + tuple(f"PWGTP{i}" for i in range(1, 81))
BASE_INPUT_COLUMNS = ("AGEP", "ESR", "OCCP", "COW", "WKHP")
BENCHMARK_POPULATIONS = (
    "all_employed",
    "civilian_employed",
    "civilian_no_unpaid_family",
    "civilian_wage_salary",
    "full_time_civilian_wage_salary",
    "all_employed_household_only",
)
PANEL_POPULATIONS = ("all_employed", "full_time_civilian_wage_salary")
PANEL_DEFINITIONS = ("YAX_primary_fixed", "BCC_analogue_broader_equal")
STRUCTURES = ("pooled", "family_year")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


PUBLIC = load_module(
    "yax_acs_public_helpers", HERE.parent / "public_benchmark" / "run_public_benchmark.py")
CORE = PUBLIC.CORE
ENGINE = PUBLIC.ENGINE


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    require(bool(rows), f"refusing to write empty {path.name}")
    fields: list[str] = []
    for row in rows:
        fields.extend(key for key in row if key not in fields)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def git_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def prepare_bridge(path: Path, broader_support: set[str]) -> pd.DataFrame:
    bridge = pd.read_csv(path, dtype={"census_2010": str, "census_2018": str},
                         float_precision="round_trip")
    required = {"census_2010", "census_2018", "bridge_weight"}
    require(required.issubset(bridge.columns), "occupation bridge schema differs")
    bridge = bridge[list(required)].copy()
    bridge["census_2010"] = bridge.census_2010.str.zfill(4)
    bridge["census_2018"] = bridge.census_2018.str.zfill(4)
    bridge["bridge_weight"] = pd.to_numeric(bridge.bridge_weight, errors="raise")
    require(not bridge[["census_2010", "census_2018"]].duplicated().any(),
            "occupation bridge has duplicate routes")
    sums = bridge.groupby("census_2010", observed=True).bridge_weight.sum().to_numpy(float)
    require(len(sums) > 0 and np.max(np.abs(sums - 1.0)) <= 5e-7,
            "occupation bridge does not conserve source mass")
    return bridge.loc[bridge.census_2018.isin(broader_support)].copy()


def population_masks(frame: pd.DataFrame) -> dict[str, pd.Series]:
    esr = pd.to_numeric(frame.ESR, errors="coerce")
    cow = pd.to_numeric(frame.COW, errors="coerce")
    hours = pd.to_numeric(frame.WKHP, errors="coerce")
    type_hu_gq = pd.to_numeric(frame.TYPEHUGQ, errors="coerce")
    all_employed = esr.isin([1, 2, 4, 5])
    civilian = esr.isin([1, 2])
    no_unpaid = civilian & cow.notna() & cow.ne(8)
    wage_salary = no_unpaid & cow.isin([1, 2, 3, 4, 5])
    full_time = wage_salary & hours.between(35, 99)
    return {
        "all_employed": all_employed,
        "civilian_employed": civilian,
        "civilian_no_unpaid_family": no_unpaid,
        "civilian_wage_salary": wage_salary,
        "full_time_civilian_wage_salary": full_time,
        "all_employed_household_only": all_employed & type_hu_gq.eq(1),
    }


def valid_occ(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.strip()
    numeric = pd.to_numeric(text, errors="coerce")
    valid = numeric.notna() & numeric.between(0, 9999) & numeric.mod(1).eq(0)
    out = pd.Series(pd.NA, index=series.index, dtype="string")
    out.loc[valid] = numeric.loc[valid].astype(int).map(lambda value: f"{value:04d}")
    return out


def zip_person_members(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist()
                 if Path(name).name.lower().startswith("psam_p") and name.lower().endswith(".csv")]
    require(bool(names), f"{path.name} contains no person CSV")
    return sorted(names)


def aggregate_year(year: int, path: Path, bridge: pd.DataFrame,
                   broader_support: set[str]) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Aggregate full and replicate person weights without retaining identifiers."""
    before = sha256_file(path)
    members = zip_person_members(path)
    parts: list[pd.DataFrame] = []
    counters: dict[str, Any] = {
        "year": year, "zip_path": str(path.resolve()), "zip_sha256": before,
        "source_url":
            f"https://www2.census.gov/programs-surveys/acs/data/pums/{year}/1-Year/csv_pus.zip",
        "zip_bytes": path.stat().st_size, "person_members": [], "raw_rows": 0,
        "age_22_65_rows": 0, "employed_positive_weight_rows": 0,
        "valid_occupation_rows": 0, "routed_descendant_rows": 0,
        "fractional_descendant_rows": 0,
        "source_rows_with_supported_route": 0,
        "source_rows_with_full_supported_route": 0,
        "source_rows_with_partial_supported_route": 0,
        "records_with_negative_replicate_weight": 0,
        "negative_replicate_weight_entries": 0,
        "valid_occupation_full_weight_stock": 0.0,
        "routed_supported_full_weight_stock": 0.0,
    }
    with zipfile.ZipFile(path) as archive:
        for member in members:
            info = archive.getinfo(member)
            counters["person_members"].append({
                "name": member, "zip_crc32_hex": f"{info.CRC:08x}",
                "uncompressed_bytes": info.file_size,
            })
            with archive.open(member) as stream:
                relationship_field = "RELP" if year <= 2018 else "RELSHIPP"
                input_columns = BASE_INPUT_COLUMNS + (relationship_field,) + WEIGHT_COLUMNS
                reader = pd.read_csv(stream, usecols=list(input_columns), chunksize=200_000,
                                     dtype={"OCCP": str}, low_memory=False)
                for chunk in reader:
                    relationship = pd.to_numeric(chunk[relationship_field], errors="coerce")
                    require(relationship.notna().all(),
                            f"{year} has missing or invalid {relationship_field}")
                    institutional_code, noninstitutional_code = (
                        (16, 17) if relationship_field == "RELP" else (37, 38))
                    chunk["TYPEHUGQ"] = np.select(
                        [relationship.eq(institutional_code),
                         relationship.eq(noninstitutional_code)],
                        [2, 3], default=1)
                    counters["raw_rows"] += len(chunk)
                    age = pd.to_numeric(chunk.AGEP, errors="coerce")
                    age_keep = age.between(22, 65)
                    counters["age_22_65_rows"] += int(age_keep.sum())
                    chunk = chunk.loc[age_keep].copy()
                    if chunk.empty:
                        continue
                    weights = chunk.loc[:, WEIGHT_COLUMNS].apply(pd.to_numeric, errors="coerce")
                    masks = population_masks(chunk)
                    keep = masks["all_employed"] & weights.PWGTP.gt(0) & np.isfinite(weights.PWGTP)
                    counters["employed_positive_weight_rows"] += int(keep.sum())
                    chunk = chunk.loc[keep].copy()
                    weights = weights.loc[keep].copy()
                    masks = {name: mask.loc[keep] for name, mask in masks.items()}
                    if chunk.empty:
                        continue
                    weight_values = weights.to_numpy(float)
                    require(np.isfinite(weight_values).all() and
                            (weight_values[:, 0] > 0).all(),
                            f"{year} has invalid full or replicate person weights")
                    negative_replicates = weight_values[:, 1:] < 0
                    counters["records_with_negative_replicate_weight"] += int(
                        negative_replicates.any(axis=1).sum())
                    counters["negative_replicate_weight_entries"] += int(
                        negative_replicates.sum())
                    chunk["source_occ"] = valid_occ(chunk.OCCP)
                    occ_keep = chunk.source_occ.notna()
                    counters["valid_occupation_rows"] += int(occ_keep.sum())
                    chunk = chunk.loc[occ_keep].copy()
                    weights = weights.loc[occ_keep].copy()
                    masks = {name: mask.loc[occ_keep] for name, mask in masks.items()}
                    counters["valid_occupation_full_weight_stock"] += float(weights.PWGTP.sum())
                    chunk["age_group"] = np.where(
                        pd.to_numeric(chunk.AGEP, errors="raise").le(25), "young", "older")
                    chunk["source_row"] = np.arange(len(chunk), dtype=np.int64)
                    route_base = chunk[["source_row", "source_occ", "age_group"]].copy()
                    if year == 2017:
                        routed = route_base.merge(
                            bridge, left_on="source_occ", right_on="census_2010",
                            how="inner", validate="many_to_many")
                        routed["occ_code"] = routed.census_2018
                    else:
                        routed = route_base.loc[route_base.source_occ.isin(broader_support)].copy()
                        routed["occ_code"] = routed.source_occ
                        routed["bridge_weight"] = 1.0
                    if routed.empty:
                        continue
                    counters["routed_descendant_rows"] += len(routed)
                    counters["fractional_descendant_rows"] += int(
                        (~np.isclose(routed.bridge_weight.to_numpy(float), 1.0)).sum())
                    routed_mass = routed.groupby("source_row", observed=True).bridge_weight.sum()
                    counters["source_rows_with_supported_route"] += len(routed_mass)
                    counters["source_rows_with_full_supported_route"] += int(
                        np.isclose(routed_mass.to_numpy(float), 1.0, rtol=0.0, atol=5e-7).sum())
                    counters["source_rows_with_partial_supported_route"] += int(
                        ((routed_mass.to_numpy(float) > 0.0) &
                         (~np.isclose(routed_mass.to_numpy(float), 1.0,
                                     rtol=0.0, atol=5e-7))).sum())
                    route_index = routed.source_row.to_numpy(int)
                    route_weight = routed.bridge_weight.to_numpy(float)
                    source_weights = weights.reset_index(drop=True).to_numpy(float)
                    routed_weights = source_weights[route_index] * route_weight[:, None]
                    counters["routed_supported_full_weight_stock"] += float(
                        routed_weights[:, 0].sum())
                    for population in BENCHMARK_POPULATIONS:
                        source_mask = masks[population].reset_index(drop=True).to_numpy(bool)
                        selected = source_mask[route_index]
                        if not selected.any():
                            continue
                        block = routed.loc[selected, ["occ_code", "age_group"]].copy()
                        block.loc[:, WEIGHT_COLUMNS] = routed_weights[selected]
                        block["respondent_equivalent"] = route_weight[selected]
                        grouped = block.groupby(
                            ["occ_code", "age_group"], as_index=False, observed=True
                        )[list(WEIGHT_COLUMNS) + ["respondent_equivalent"]].sum()
                        grouped["year"] = year
                        grouped["population"] = population
                        parts.append(grouped)
    after = sha256_file(path)
    require(before == after, f"{path.name} changed during read")
    require(bool(parts), f"{year} produced no aggregate cells")
    cells = pd.concat(parts, ignore_index=True).groupby(
        ["year", "population", "occ_code", "age_group"], as_index=False,
        observed=True)[list(WEIGHT_COLUMNS) + ["respondent_equivalent"]].sum()
    require(set(cells.population.unique()) == set(BENCHMARK_POPULATIONS),
            f"{year} loses a declared population")
    return cells, counters


def load_memberships(primary_path: Path, broader_path: Path
                     ) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    primary = pd.read_csv(primary_path, dtype={"occupation_code": str},
                          float_precision="round_trip")
    broader = pd.read_csv(broader_path, dtype={"occupation_code": str},
                          float_precision="round_trip")
    primary["occupation_code"] = primary.occupation_code.str.zfill(4)
    broader["occupation_code"] = broader.occupation_code.str.zfill(4)
    require(len(primary) == 468 and primary.occupation_code.is_unique,
            "primary membership dimensions differ")
    require(len(broader) == 490 and broader.occupation_code.is_unique,
            "broader membership dimensions differ")
    require(set(primary.occupation_code).issubset(set(broader.occupation_code)),
            "primary support is not nested in broader support")
    aligned = broader.set_index("occupation_code").loc[primary.occupation_code]
    require(np.max(np.abs(aligned.rule_A_beta.to_numpy(float) -
                                  primary.rule_A_beta.to_numpy(float))) <= 1e-12,
            "raw beta differs between membership files")
    eq_primary, cuts_primary = PUBLIC.equal_occupation_quintiles(
        primary.rule_A_beta.to_numpy(float))
    eq_broader, cuts_broader = PUBLIC.equal_occupation_quintiles(
        broader.rule_A_beta.to_numpy(float))
    definitions: dict[str, pd.DataFrame] = {}
    base = primary[["occupation_code", "rule_A_beta"]].rename(
        columns={"occupation_code": "occ_code"}).copy()
    base["family"] = aligned.family.to_numpy(str)
    base["quintile"] = eq_primary
    definitions["BCC_analogue_primary_equal"] = base.copy()
    fixed = base.copy()
    fixed["quintile"] = primary.beta_quintile.to_numpy(int)
    definitions["YAX_primary_fixed"] = fixed
    broad = broader[["occupation_code", "family", "rule_A_beta"]].rename(
        columns={"occupation_code": "occ_code"}).copy()
    broad["quintile"] = eq_broader
    definitions["BCC_analogue_broader_equal"] = broad
    audit = {
        "definition_counts": {name: len(value) for name, value in definitions.items()},
        "equal_primary_cuts": cuts_primary.tolist(),
        "equal_broader_cuts": cuts_broader.tolist(),
        "primary_frozen_cuts": sorted(primary.groupby("beta_quintile").rule_A_beta.max().tolist())[:4],
        "assignments_fixed_under_replicate_weights": True,
    }
    return definitions, audit


def subset_cells(cells: pd.DataFrame, definition: pd.DataFrame,
                 population: str) -> pd.DataFrame:
    block = cells.loc[cells.population.eq(population)].merge(
        definition, on="occ_code", how="inner", validate="many_to_one")
    require(not block.empty, f"empty cells for {population}")
    return block


def stock(block: pd.DataFrame, year: int, age_group: str,
          quintile: int, weight: str) -> float:
    part = block.loc[
        block.year.eq(year) & block.age_group.eq(age_group) & block.quintile.eq(quintile),
        weight]
    return float(part.sum())


def benchmark_statistic(block: pd.DataFrame, weight_2022: str,
                        weight_2024: str) -> tuple[float, float, float]:
    q1_22 = stock(block, 2022, "young", 1, weight_2022)
    q5_22 = stock(block, 2022, "young", 5, weight_2022)
    q1_24 = stock(block, 2024, "young", 1, weight_2024)
    q5_24 = stock(block, 2024, "young", 5, weight_2024)
    require(min(q1_22, q5_22, q1_24, q5_24) > 0,
            "benchmark endpoint stock is nonpositive")
    g1, g5 = q1_24 / q1_22, q5_24 / q5_22
    return g5 - g1, g1, g5


def sdr_variance(deltas: Iterable[float]) -> float:
    values = np.asarray(list(deltas), float)
    require(values.ndim == 1 and len(values) % REPLICATES == 0 and
            np.isfinite(values).all(), "invalid SDR delta vector")
    return float(SDR_FACTOR * np.square(values).sum())


def benchmark_results(cells: pd.DataFrame, definitions: dict[str, pd.DataFrame]
                     ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    replicate_rows: list[dict[str, Any]] = []
    for definition_name, definition in definitions.items():
        for population in BENCHMARK_POPULATIONS:
            block = subset_cells(cells, definition, population)
            estimate, g1, g5 = benchmark_statistic(block, "PWGTP", "PWGTP")
            deltas: list[float] = []
            for year in (2022, 2024):
                for replicate in range(1, REPLICATES + 1):
                    weight = f"PWGTP{replicate}"
                    value, _, _ = benchmark_statistic(
                        block, weight if year == 2022 else "PWGTP",
                        weight if year == 2024 else "PWGTP")
                    delta = value - estimate
                    deltas.append(delta)
                    replicate_rows.append({
                        "result_type": "benchmark", "definition": definition_name,
                        "population": population, "structure": "",
                        "calendar_rule": "2022_to_2024", "perturbed_year": year,
                        "replicate": replicate, "estimate": value,
                        "full_weight_estimate": estimate, "delta": delta,
                    })
            variance = sdr_variance(deltas)
            se = math.sqrt(max(variance, 0.0))
            unweighted, ug1, ug5 = benchmark_statistic(
                block.rename(columns={"respondent_equivalent": "_respondent"}),
                "_respondent", "_respondent")
            rows.append({
                "definition": definition_name, "population": population,
                "estimate_Q5_minus_Q1_growth_factor": estimate,
                "Q1_growth_factor": g1, "Q5_growth_factor": g5,
                "ACS_SDR_se": se,
                "ACS_SDR_ci_lower": estimate - NORMAL_975 * se,
                "ACS_SDR_ci_upper": estimate + NORMAL_975 * se,
                "unweighted_respondent_count_analogue": unweighted,
                "unweighted_Q1_growth_factor": ug1,
                "unweighted_Q5_growth_factor": ug5,
                "replicate_estimates": 2 * REPLICATES,
                "replicate_construction": "one_endpoint_year_perturbed_at_a_time",
                "SDR_factor": SDR_FACTOR,
                "BCC_exact_membership": False,
            })
    return rows, replicate_rows


def benchmark_paired_results(results: list[dict[str, Any]],
                             replicate_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary = pd.DataFrame(results)
    reps = pd.DataFrame(replicate_rows)
    comparisons: list[tuple[str, tuple[str, str], tuple[str, str]]] = []
    for definition in summary.definition.unique():
        comparisons.append((
            "all_employed_minus_full_time_civilian_wage_salary",
            (definition, "all_employed"),
            (definition, "full_time_civilian_wage_salary")))
    for population in summary.population.unique():
        comparisons.extend([
            ("broader_equal_minus_primary_equal",
             ("BCC_analogue_broader_equal", population),
             ("BCC_analogue_primary_equal", population)),
            ("primary_equal_minus_YAX_fixed",
             ("BCC_analogue_primary_equal", population),
             ("YAX_primary_fixed", population)),
        ])
    rows: list[dict[str, Any]] = []
    for label, left_key, right_key in comparisons:
        left_summary = summary.loc[
            summary.definition.eq(left_key[0]) & summary.population.eq(left_key[1])]
        right_summary = summary.loc[
            summary.definition.eq(right_key[0]) & summary.population.eq(right_key[1])]
        require(len(left_summary) == len(right_summary) == 1,
                "benchmark paired summary is not unique")
        left = reps.loc[
            reps.definition.eq(left_key[0]) & reps.population.eq(left_key[1])].sort_values(
                ["perturbed_year", "replicate"])
        right = reps.loc[
            reps.definition.eq(right_key[0]) & reps.population.eq(right_key[1])].sort_values(
                ["perturbed_year", "replicate"])
        require(np.array_equal(left[["perturbed_year", "replicate"]].to_numpy(),
                               right[["perturbed_year", "replicate"]].to_numpy()),
                "benchmark paired replicate keys differ")
        full = (float(left_summary.iloc[0].estimate_Q5_minus_Q1_growth_factor) -
                float(right_summary.iloc[0].estimate_Q5_minus_Q1_growth_factor))
        deltas = ((left.estimate.to_numpy(float) - right.estimate.to_numpy(float)) - full)
        se = math.sqrt(max(sdr_variance(deltas), 0.0))
        rows.append({
            "comparison": label,
            "left_definition": left_key[0], "left_population": left_key[1],
            "right_definition": right_key[0], "right_population": right_key[1],
            "estimate_left_minus_right": full, "ACS_paired_SDR_se": se,
            "ACS_paired_SDR_ci_lower": full - NORMAL_975 * se,
            "ACS_paired_SDR_ci_upper": full + NORMAL_975 * se,
            "common_year_replicate_perturbations_preserve_covariance": True,
            "interpretation_if_CI_contains_zero":
                "design_does_not_detect_a_difference_not_equivalence",
        })
    return rows


def cell_matrix(block: pd.DataFrame, occupations: np.ndarray, years: tuple[int, ...],
                age_group: str, weight: str) -> np.ndarray:
    part = block.loc[block.age_group.eq(age_group)].groupby(
        ["occ_code", "year"], observed=True)[weight].sum()
    index = pd.MultiIndex.from_product([occupations.tolist(), list(years)],
                                       names=["occ_code", "year"])
    return part.reindex(index, fill_value=0.0).to_numpy(float).reshape(
        len(occupations), len(years))


def cell_weight_cube(block: pd.DataFrame, occupations: np.ndarray,
                     age_group: str) -> np.ndarray:
    """Return occupation x full-year-calendar x full/replicate-weight stock."""
    part = block.loc[block.age_group.eq(age_group)].groupby(
        ["occ_code", "year"], observed=True)[list(WEIGHT_COLUMNS)].sum()
    index = pd.MultiIndex.from_product([occupations.tolist(), list(YEARS)],
                                       names=["occ_code", "year"])
    values = part.reindex(index, fill_value=0.0).to_numpy(float)
    return values.reshape(len(occupations), len(YEARS), len(WEIGHT_COLUMNS))


def annual_design(quintiles: np.ndarray, families: np.ndarray,
                  years: tuple[int, ...], structure: str):
    n_occ, n_year = len(quintiles), len(years)
    post = np.asarray([year >= 2023 for year in years], bool)
    q = np.repeat(quintiles, n_year)
    row_post = np.tile(post, n_occ)
    columns = [((q == value) & row_post).astype(float) for value in range(2, 6)]
    labels = tuple(f"Q{value}_x_post" for value in range(2, 6))
    occ_codes = np.repeat(np.arange(n_occ), n_year)
    levels = {value: index for index, value in enumerate(sorted(set(families.tolist())))}
    family_codes = np.repeat(np.asarray([levels[value] for value in families], int), n_year)
    first = occ_codes.astype(object)
    if structure == "pooled":
        second = np.tile(np.arange(n_year), n_occ).astype(object)
    elif structure == "family_year":
        second = (family_codes * n_year + np.tile(np.arange(n_year), n_occ)).astype(object)
    else:
        raise ValueError(f"unknown annual structure {structure}")
    return CORE.ModelDesign(
        structure=structure, regressors=np.column_stack(columns), first_labels=first,
        second_labels=second, occupation_codes=occ_codes, family_codes=family_codes,
        regressor_labels=labels, focal_target_index=3)


@dataclass(frozen=True)
class SignedReplicateFit:
    """Root of the grouped-logit score under signed ACS replicate weights."""

    beta: np.ndarray
    iterations: int
    maximum_normalized_score: float
    minimum_first_effect_information: float
    minimum_second_effect_information: float
    minimum_treatment_information_eigenvalue: float
    negative_young_cell_count: int
    negative_older_cell_count: int
    nonpositive_total_cell_count: int
    inactive_first_effect_count: int
    inactive_second_effect_count: int


def _contiguous_codes(labels: np.ndarray) -> tuple[np.ndarray, int]:
    values = np.asarray(labels, object)
    levels = sorted(set(values.tolist()))
    require(bool(levels), "empty fixed-effect dimension")
    lookup = {value: index for index, value in enumerate(levels)}
    return np.asarray([lookup[value] for value in values], int), len(levels)


def _effect_components(first: np.ndarray, second: np.ndarray,
                       n_first: int, n_second: int,
                       active: np.ndarray | None = None,
                       ) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Return connected components of the two-way fixed-effect graph."""
    if active is None:
        active = np.ones(len(first), bool)
    active = np.asarray(active, bool)
    require(active.shape == first.shape and bool(active.any()),
            "fixed-effect component mask is invalid")
    parent = np.arange(n_first + n_second, dtype=int)

    def find(value: int) -> int:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = int(parent[value])
        return value

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for left, right in zip(first[active], second[active]):
        union(int(left), n_first + int(right))
    first_groups: dict[int, list[int]] = {}
    second_groups: dict[int, list[int]] = {}
    for value in sorted(set(first[active].tolist())):
        first_groups.setdefault(find(value), []).append(value)
    for value in sorted(set(second[active].tolist())):
        second_groups.setdefault(find(n_first + value), []).append(value)
    roots = sorted(first_groups)
    require(set(roots) == set(second_groups), "fixed-effect graph has an empty side")
    return ([np.asarray(first_groups[root], int) for root in roots],
            [np.asarray(second_groups[root], int) for root in roots])


def _anchor_effects(first_effect: np.ndarray, second_effect: np.ndarray,
                    first_components: list[np.ndarray],
                    second_components: list[np.ndarray]) -> None:
    """Anchor one second effect within every connected FE component."""
    for first_group, second_group in zip(first_components, second_components):
        shift = float(second_effect[int(second_group.min())])
        first_effect[first_group] += shift
        second_effect[second_group] -= shift


def _initial_effects(linear_nuisance: np.ndarray, first: np.ndarray,
                     second: np.ndarray, n_first: int, n_second: int,
                     first_components: list[np.ndarray],
                     second_components: list[np.ndarray],
                     active: np.ndarray | None = None,
                     ) -> tuple[np.ndarray, np.ndarray]:
    """Recover additive nuisance effects from a certified full-weight fit."""
    if active is None:
        active = np.ones(len(first), bool)
    active = np.asarray(active, bool)
    require(active.shape == first.shape and bool(active.any()),
            "full-weight active-cell mask is invalid")
    first_effect = np.zeros(n_first, float)
    second_effect = np.zeros(n_second, float)
    first_active = first[active]
    second_active = second[active]
    nuisance_active = linear_nuisance[active]
    first_count = np.bincount(first_active, minlength=n_first).astype(float)
    second_count = np.bincount(second_active, minlength=n_second).astype(float)
    first_observed = first_count > 0
    second_observed = second_count > 0
    for _ in range(1000):
        prior_first = first_effect.copy()
        prior_second = second_effect.copy()
        first_numerator = np.bincount(
            first_active, weights=nuisance_active - second_effect[second_active],
            minlength=n_first)
        first_effect = np.divide(
            first_numerator, first_count, out=np.zeros(n_first, float),
            where=first_observed)
        second_numerator = np.bincount(
            second_active, weights=nuisance_active - first_effect[first_active],
            minlength=n_second)
        second_effect = np.divide(
            second_numerator, second_count, out=np.zeros(n_second, float),
            where=second_observed)
        _anchor_effects(first_effect, second_effect,
                        first_components, second_components)
        movement = max(float(np.max(np.abs(first_effect - prior_first))),
                       float(np.max(np.abs(second_effect - prior_second))))
        if movement <= 1e-12:
            break
    reconstruction = first_effect[first] + second_effect[second]
    require(float(np.max(np.abs(
        reconstruction[active] - linear_nuisance[active]))) <= 1e-7,
            "full-weight nuisance effects cannot be reconstructed")
    return first_effect, second_effect


def _signed_weighted_absorb(matrix: np.ndarray, weight: np.ndarray,
                            first: np.ndarray, second: np.ndarray,
                            n_first: int, n_second: int,
                            tolerance: float = 1e-11,
                            max_iterations: int = 1000) -> np.ndarray:
    """Residualize against two FE dimensions under locally signed curvature."""
    result = np.asarray(matrix, float).copy()
    first_weight = np.bincount(first, weights=weight, minlength=n_first)
    second_weight = np.bincount(second, weights=weight, minlength=n_second)
    scale = max(1.0, float(np.max(np.abs(weight))))
    threshold = 1e-12 * scale
    first_absolute = np.bincount(first, weights=np.abs(weight), minlength=n_first)
    second_absolute = np.bincount(second, weights=np.abs(weight), minlength=n_second)
    first_active = np.abs(first_weight) > threshold
    second_active = np.abs(second_weight) > threshold
    require(np.all((first_absolute <= threshold) | first_active) and
            np.all((second_absolute <= threshold) | second_active),
            "signed replicate fixed-effect curvature cancels within an active level")
    for _ in range(max_iterations):
        largest = 0.0
        for group, denominator, active_level, count in (
                (first, first_weight, first_active, n_first),
                (second, second_weight, second_active, n_second)):
            for column in range(result.shape[1]):
                numerator = np.bincount(
                    group, weights=weight * result[:, column], minlength=count)
                require(np.all(np.abs(numerator[~active_level]) <= threshold),
                        "zero-curvature fixed effect has a nonzero projection score")
                adjustment = np.divide(
                    numerator, denominator, out=np.zeros(count, float),
                    where=active_level)
                result[:, column] -= adjustment[group]
                if bool(active_level.any()):
                    largest = max(
                        largest, float(np.max(np.abs(adjustment[active_level]))))
        if largest <= tolerance:
            return result
    raise RuntimeError("signed replicate fixed-effect absorption did not converge")


def fit_annual_signed_replicate(young: np.ndarray, older: np.ndarray,
                                quintiles: np.ndarray, families: np.ndarray,
                                years: tuple[int, ...], structure: str,
                                full_fit: Any, full_total: np.ndarray,
                                tolerance: float = 1e-9,
                                max_iterations: int = 5000
                                ) -> SignedReplicateFit:
    """Solve the unchanged grouped-logit score with signed SDR weights.

    ACS replicate weights are used only for variance estimation and may be
    negative.  Their aggregated young/older cells therefore need not be valid
    binomial counts, but the weighted score remains well-defined.  This solver
    starts at the certified full-weight solution, retains every fixed row, and
    Newton-solves that score without clipping, deleting or renormalizing a
    released replicate weight.
    """
    design = annual_design(quintiles, families, years, structure)
    young = np.asarray(young, float).reshape(-1)
    older = np.asarray(older, float).reshape(-1)
    total = young + older
    x = np.asarray(design.regressors, float)
    require(len(young) == len(older) == len(x) and
            np.all(np.isfinite(young)) and np.all(np.isfinite(older)),
            "signed replicate outcome/design rows differ or are nonfinite")
    require(float(total.sum()) > 0.0, "signed replicate total stock is nonpositive")
    first, n_first = _contiguous_codes(design.first_labels)
    second, n_second = _contiguous_codes(design.second_labels)
    beta = np.asarray(full_fit.beta, float).copy()
    full_probability = np.asarray(full_fit.fitted_probability, float).reshape(-1)
    full_total = np.asarray(full_total, float).reshape(-1)
    require(beta.shape == (x.shape[1],) and
            full_probability.shape == young.shape == full_total.shape and
            np.all(np.isfinite(full_total)) and np.all(full_total >= 0),
            "full-weight initializer differs from replicate design")
    full_active = full_total > 0
    require(bool(full_active.any()), "full-weight initializer has no active cells")
    initial_first_components, initial_second_components = _effect_components(
        first, second, n_first, n_second, full_active)
    replicate_scale = max(1.0, float(np.max(np.abs(total))))
    replicate_active = np.abs(total) > 1e-12 * replicate_scale
    require(bool(replicate_active.any()), "signed replicate has no active cells")
    first_components, second_components = _effect_components(
        first, second, n_first, n_second, replicate_active)
    eta = np.log(np.clip(full_probability, 1e-12, 1.0 - 1e-12) /
                 np.clip(1.0 - full_probability, 1e-12, 1.0))
    first_effect, second_effect = _initial_effects(
        eta - x @ beta, first, second, n_first, n_second,
        initial_first_components, initial_second_components, full_active)
    converged = False
    maximum_normalized_score = math.inf
    min_first_information = math.nan
    min_second_information = math.nan
    min_treatment_eigenvalue = math.nan
    scale = max(1.0, float(total.sum()))
    for iteration in range(1, max_iterations + 1):
        largest_step = 0.0
        for _ in range(2):
            eta = first_effect[first] + second_effect[second] + x @ beta
            probability = ENGINE._sigmoid(eta)
            residual = young - total * probability
            weight = total * probability * (1.0 - probability)
            first_score = np.bincount(first, weights=residual, minlength=n_first)
            first_information = np.bincount(first, weights=weight, minlength=n_first)
            first_absolute = np.bincount(
                first, weights=np.abs(weight), minlength=n_first)
            first_active = np.abs(first_information) > 1e-10
            require(np.all((first_absolute <= 1e-10) | first_active),
                    "signed replicate occupation curvature cancels within an active level")
            require(np.all(np.abs(first_score[~first_active]) <= 1e-8 * scale),
                    "zero-curvature occupation effect has a nonzero score")
            step = np.zeros(n_first, float)
            step[first_active] = np.clip(
                first_score[first_active] / first_information[first_active], -1.0, 1.0)
            first_effect += step
            largest_step = max(
                largest_step, float(np.max(np.abs(step[first_active]))))

            eta = first_effect[first] + second_effect[second] + x @ beta
            probability = ENGINE._sigmoid(eta)
            residual = young - total * probability
            weight = total * probability * (1.0 - probability)
            second_score = np.bincount(second, weights=residual, minlength=n_second)
            second_information = np.bincount(second, weights=weight, minlength=n_second)
            second_absolute = np.bincount(
                second, weights=np.abs(weight), minlength=n_second)
            second_active = np.abs(second_information) > 1e-10
            require(np.all((second_absolute <= 1e-10) | second_active),
                    "signed replicate calendar curvature cancels within an active level")
            require(np.all(np.abs(second_score[~second_active]) <= 1e-8 * scale),
                    "zero-curvature calendar effect has a nonzero score")
            step = np.zeros(n_second, float)
            step[second_active] = np.clip(
                second_score[second_active] / second_information[second_active], -1.0, 1.0)
            second_effect += step
            largest_step = max(
                largest_step, float(np.max(np.abs(step[second_active]))))
            _anchor_effects(first_effect, second_effect,
                            first_components, second_components)

        eta = first_effect[first] + second_effect[second] + x @ beta
        probability = ENGINE._sigmoid(eta)
        residual = young - total * probability
        weight = total * probability * (1.0 - probability)
        residualized = _signed_weighted_absorb(
            x, weight, first, second, n_first, n_second)
        information = residualized.T @ (weight[:, None] * residualized)
        information = (information + information.T) / 2.0
        eigenvalues = np.linalg.eigvalsh(information)
        require(float(eigenvalues.min()) > 1e-10,
                "signed replicate treatment curvature is not positive definite")
        score = residualized.T @ residual
        try:
            step = np.linalg.solve(information, score)
        except np.linalg.LinAlgError as error:
            raise RuntimeError("signed replicate treatment curvature is singular") from error
        step = np.clip(step, -1.0, 1.0)
        beta += step
        largest_step = max(largest_step, float(np.max(np.abs(step))))

        eta = first_effect[first] + second_effect[second] + x @ beta
        probability = ENGINE._sigmoid(eta)
        residual = young - total * probability
        weight = total * probability * (1.0 - probability)
        first_score = np.bincount(first, weights=residual, minlength=n_first)
        second_score = np.bincount(second, weights=residual, minlength=n_second)
        raw_treatment_score = x.T @ residual
        maximum_normalized_score = max(
            float(np.max(np.abs(first_score))),
            float(np.max(np.abs(second_score))),
            float(np.max(np.abs(raw_treatment_score))),
        ) / scale
        final_first_information = np.bincount(
            first, weights=weight, minlength=n_first)
        final_second_information = np.bincount(
            second, weights=weight, minlength=n_second)
        final_first_active = np.abs(final_first_information) > 1e-10
        final_second_active = np.abs(final_second_information) > 1e-10
        require(bool(final_first_active.any()) and bool(final_second_active.any()),
                "signed replicate loses an entire fixed-effect dimension")
        min_first_information = float(np.min(
            final_first_information[final_first_active]))
        min_second_information = float(np.min(
            final_second_information[final_second_active]))
        min_treatment_eigenvalue = float(eigenvalues.min())
        if largest_step <= tolerance and maximum_normalized_score <= tolerance:
            converged = True
            break
    require(converged, f"{structure} signed replicate score did not converge")
    require(maximum_normalized_score <= 1e-8,
            f"{structure} signed replicate score certificate failed")
    require(min_first_information > 0.0 and min_second_information > 0.0,
            f"{structure} signed replicate fixed-effect curvature is not locally concave")
    return SignedReplicateFit(
        beta=beta, iterations=iteration,
        maximum_normalized_score=maximum_normalized_score,
        minimum_first_effect_information=min_first_information,
        minimum_second_effect_information=min_second_information,
        minimum_treatment_information_eigenvalue=min_treatment_eigenvalue,
        negative_young_cell_count=int((young < 0).sum()),
        negative_older_cell_count=int((older < 0).sum()),
        nonpositive_total_cell_count=int((total <= 0).sum()),
        inactive_first_effect_count=int((~final_first_active).sum()),
        inactive_second_effect_count=int((~final_second_active).sum()),
    )


def fit_annual(young: np.ndarray, older: np.ndarray, quintiles: np.ndarray,
               families: np.ndarray, years: tuple[int, ...], structure: str):
    design = annual_design(quintiles, families, years, structure)
    fit = CORE.fit_with_influence(
        ENGINE, young.reshape(-1), (young + older).reshape(-1), design)
    require(fit.separated_observation_count == 0 and
            fit.active_occupation_count == len(quintiles) and
            fit.active_family_count == len(set(families.tolist())),
            f"{structure} silently changed the fixed annual estimating rows")
    return fit


def fixed_model_support(young: np.ndarray, older: np.ndarray,
                        years: tuple[int, ...]) -> np.ndarray:
    pre = np.asarray([year < 2022 for year in years], bool)
    require(pre.any() and (~pre).any(), "model calendar lacks pre or post years")
    return ((young[:, pre].sum(axis=1) > 0) &
            (older[:, pre].sum(axis=1) > 0) &
            ((young + older).sum(axis=1) > 0))


def multiplier_fields(estimate: float, influence: np.ndarray,
                      signs: np.ndarray, prefix: str) -> dict[str, float]:
    value = CORE.multiplier_interval(estimate, influence, signs)
    return {
        f"{prefix}_se": value["se"], f"{prefix}_ci_lower": value["lower"],
        f"{prefix}_ci_upper": value["upper"], f"{prefix}_p": value["p_value"],
    }


def panel_results(cells: pd.DataFrame, definitions: dict[str, pd.DataFrame]
                 ) -> tuple[list[dict[str, Any]], list[dict[str, Any]],
                            list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    replicate_rows: list[dict[str, Any]] = []
    fitted: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    rng = np.random.default_rng(SEED)
    for definition_name in PANEL_DEFINITIONS:
        definition = definitions[definition_name].sort_values("occ_code").reset_index(drop=True)
        occupations_all = definition.occ_code.to_numpy(str)
        q_all = definition.quintile.to_numpy(int)
        families_all = definition.family.to_numpy(str)
        for population in PANEL_POPULATIONS:
            block = subset_cells(cells, definition, population)
            young_cube = cell_weight_cube(block, occupations_all, "young")
            older_cube = cell_weight_cube(block, occupations_all, "older")
            year_location = {year: index for index, year in enumerate(YEARS)}
            for calendar_rule, years in (
                    ("full_2017_2019_2021_2023_2024", MODEL_YEARS),
                    ("nonreuse_2017_2021_2023_2024", NONREUSE_MODEL_YEARS)):
                locations = [year_location[year] for year in years]
                young_full = young_cube[:, locations, 0]
                older_full = older_cube[:, locations, 0]
                keep = fixed_model_support(young_full, older_full, years)
                require(keep.sum() > 20 and set(q_all[keep]) == {1, 2, 3, 4, 5},
                        f"annual support invalid for {definition_name}/{population}/{calendar_rule}")
                occupations = occupations_all[keep]
                q = q_all[keep]
                families = families_all[keep]
                young = young_full[keep]
                older = older_full[keep]
                occ_signs = rng.choice([-1.0, 1.0], size=(DRAWS, len(occupations)))
                family_levels = sorted(set(families.tolist()))
                family_signs = rng.choice(
                    CORE.WEBB_SUPPORT, size=(DRAWS, len(family_levels)))
                for structure in STRUCTURES:
                    fit = fit_annual(young, older, q, families, years, structure)
                    estimate = float(fit.beta[3])
                    print(
                        "ACS_PANEL_FULL_FIT "
                        f"{definition_name}/{population}/{calendar_rule}/{structure} "
                        f"support={len(occupations)}",
                        flush=True,
                    )
                    occ_if = fit.occupation_influence[:, 3]
                    family_if = fit.family_influence[:, 3]
                    model_id = "__".join((definition_name, population, calendar_rule, structure))
                    deltas: list[float] = []
                    rep_values: dict[tuple[int, int], float] = {}
                    for year_index, year in enumerate(years):
                        for replicate in range(1, REPLICATES + 1):
                            weight = f"PWGTP{replicate}"
                            young_rep = young.copy()
                            older_rep = older.copy()
                            young_rep[:, year_index] = young_cube[
                                keep, year_location[year], replicate]
                            older_rep[:, year_index] = older_cube[
                                keep, year_location[year], replicate]
                            replicate_fit = fit_annual_signed_replicate(
                                young_rep, older_rep, q, families, years, structure, fit,
                                young_full[keep] + older_full[keep])
                            value = float(replicate_fit.beta[3])
                            delta = value - estimate
                            deltas.append(delta)
                            rep_values[(year, replicate)] = value
                            replicate_rows.append({
                                "result_type": "annual_panel", "definition": definition_name,
                                "population": population, "structure": structure,
                                "calendar_rule": calendar_rule, "perturbed_year": year,
                                "replicate": replicate, "estimate": value,
                                "full_weight_estimate": estimate, "delta": delta,
                                "replicate_estimator":
                                    "same_grouped_logit_score_signed_SDR_weights",
                                "replicate_iterations": replicate_fit.iterations,
                                "replicate_maximum_normalized_score":
                                    replicate_fit.maximum_normalized_score,
                                "replicate_minimum_first_effect_information":
                                    replicate_fit.minimum_first_effect_information,
                                "replicate_minimum_second_effect_information":
                                    replicate_fit.minimum_second_effect_information,
                                "replicate_minimum_treatment_information_eigenvalue":
                                    replicate_fit.minimum_treatment_information_eigenvalue,
                                "replicate_negative_young_cells":
                                    replicate_fit.negative_young_cell_count,
                                "replicate_negative_older_cells":
                                    replicate_fit.negative_older_cell_count,
                                "replicate_nonpositive_total_cells":
                                    replicate_fit.nonpositive_total_cell_count,
                                "replicate_inactive_first_effects":
                                    replicate_fit.inactive_first_effect_count,
                                "replicate_inactive_second_effects":
                                    replicate_fit.inactive_second_effect_count,
                            })
                        print(
                            "ACS_PANEL_REPLICATES "
                            f"{definition_name}/{population}/{calendar_rule}/{structure} "
                            f"year={year} complete={REPLICATES}",
                            flush=True,
                        )
                    survey_se = math.sqrt(max(sdr_variance(deltas), 0.0))
                    row = {
                        "model_id": model_id, "definition": definition_name,
                        "population": population, "calendar_rule": calendar_rule,
                        "years_json": json.dumps(years), "structure": structure,
                        "coefficient_label": "Q5_x_post", "coefficient": estimate,
                        "ACS_block_independent_SDR_se": survey_se,
                        "ACS_block_independent_SDR_ci_lower": estimate - NORMAL_975 * survey_se,
                        "ACS_block_independent_SDR_ci_upper": estimate + NORMAL_975 * survey_se,
                        "replicate_refits": len(years) * REPLICATES,
                        "support_occupations": len(occupations),
                        "support_sha256": hashlib.sha256(
                            "".join(f"{x}\n" for x in occupations).encode()).hexdigest(),
                        "transition_2022_excluded": True,
                        "zero_2020_standard_one_year_omitted": True,
                        "cross_year_design_status":
                            "block_independent_approximation_not_exact_multiyear_design_inference",
                        "occupation_multiplier_distribution": "rademacher_two_point",
                        "family_multiplier_distribution": "webb_six_point",
                        "iterations": fit.iterations,
                        "maximum_normalized_score": fit.maximum_normalized_score,
                        **multiplier_fields(estimate, occ_if, occ_signs, "occupation_multiplier"),
                        **multiplier_fields(estimate, family_if, family_signs, "family_multiplier"),
                    }
                    rows.append(row)
                    fitted[(definition_name, population, calendar_rule, structure)] = {
                        "row": row, "occ_if": occ_if, "family_if": family_if,
                        "occ_signs": occ_signs, "family_signs": family_signs,
                        "rep_values": rep_values, "years": years,
                    }
    paired_rows: list[dict[str, Any]] = []
    for definition_name in PANEL_DEFINITIONS:
        for population in PANEL_POPULATIONS:
            for calendar_rule in ("full_2017_2019_2021_2023_2024",
                                  "nonreuse_2017_2021_2023_2024"):
                left = fitted[(definition_name, population, calendar_rule, "pooled")]
                right = fitted[(definition_name, population, calendar_rule, "family_year")]
                estimate = left["row"]["coefficient"] - right["row"]["coefficient"]
                survey_deltas = []
                for key in sorted(left["rep_values"]):
                    survey_deltas.append(
                        (left["rep_values"][key] - right["rep_values"][key]) - estimate)
                survey_se = math.sqrt(max(sdr_variance(survey_deltas), 0.0))
                paired_rows.append({
                    "definition": definition_name, "population": population,
                    "calendar_rule": calendar_rule,
                    "comparison": "pooled_minus_family_year",
                    "estimate_left_minus_right": estimate,
                    "ACS_paired_block_independent_SDR_se": survey_se,
                    "ACS_paired_block_independent_SDR_ci_lower": estimate - NORMAL_975 * survey_se,
                    "ACS_paired_block_independent_SDR_ci_upper": estimate + NORMAL_975 * survey_se,
                    **multiplier_fields(
                        estimate, left["occ_if"] - right["occ_if"],
                        left["occ_signs"], "occupation_paired_multiplier"),
                    **multiplier_fields(
                        estimate, left["family_if"] - right["family_if"],
                        left["family_signs"], "family_paired_multiplier"),
                    "common_replicate_perturbations_preserve_covariance": True,
                    "interpretation_if_CI_contains_zero":
                        "design_does_not_detect_a_difference_not_equivalence",
                })
    return rows, paired_rows, replicate_rows


def support_information(cells: pd.DataFrame, definitions: dict[str, pd.DataFrame]
                       ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    tails: list[dict[str, Any]] = []
    for definition_name, definition in definitions.items():
        for population in PANEL_POPULATIONS:
            block = subset_cells(cells, definition, population)
            for year in YEARS:
                for age_group in ("young", "older"):
                    for quintile in range(1, 6):
                        part = block.loc[
                            block.year.eq(year) & block.age_group.eq(age_group) &
                            block.quintile.eq(quintile)]
                        w = part.PWGTP.to_numpy(float)
                        rows.append({
                            "definition": definition_name, "population": population,
                            "year": year, "age_group": age_group, "quintile": quintile,
                            "occupations_with_positive_stock": int((w > 0).sum()),
                            "weighted_stock": float(w.sum()),
                            "respondent_equivalent": float(part.respondent_equivalent.sum()),
                            "occupation_stock_concentration_effective_count":
                                float(w.sum() ** 2 / np.square(w).sum()) if np.square(w).sum() > 0 else 0.0,
                        })
            base = block.loc[block.year.isin([2017, 2018, 2019, 2021])].groupby(
                ["family", "quintile"], observed=True).PWGTP.sum().unstack(fill_value=0.0)
            for family in sorted(definition.family.unique()):
                q1 = float(base.loc[family, 1]) if family in base.index and 1 in base.columns else 0.0
                q5 = float(base.loc[family, 5]) if family in base.index and 5 in base.columns else 0.0
                tails.append({
                    "definition": definition_name, "population": population,
                    "family": family, "preperiod_Q1_stock": q1,
                    "preperiod_Q5_stock": q5, "direct_Q1_Q5_family": q1 > 0 and q5 > 0,
                })
    return rows, tails


def findings_text(benchmarks: list[dict[str, Any]], panels: list[dict[str, Any]],
                  paired: list[dict[str, Any]]) -> str:
    b = pd.DataFrame(benchmarks)
    p = pd.DataFrame(panels)
    d = pd.DataFrame(paired)
    lines = [
        "# Gate 4 annual ACS findings", "",
        "Status: post-outcome exploratory. The v1.1 confirmatory CPS design is unchanged.", "",
        "## Public benchmark analogue", "",
        "Every row below is an independent public reconstruction, not an exact BCC replication, because BCC's complete occupation membership is unavailable.", "",
        "| definition | population | Q5-Q1 growth | ACS SDR 95% interval | unweighted analogue |",
        "|---|---|---:|---:|---:|",
    ]
    for row in b.itertuples(index=False):
        if row.population not in ("all_employed", "full_time_civilian_wage_salary"):
            continue
        lines.append(
            f"| `{row.definition}` | `{row.population}` | "
            f"{row.estimate_Q5_minus_Q1_growth_factor:.4f} | "
            f"[{row.ACS_SDR_ci_lower:.4f}, {row.ACS_SDR_ci_upper:.4f}] | "
            f"{row.unweighted_respondent_count_analogue:.4f} |")
    lines += ["", "BCC's published comparison targets are -0.022 for all employed and -0.019 for full-time civilian wage-and-salary workers. A gap here combines any sampling difference with the unavailable BCC occupation membership.", "",
              "## Young-relative annual extension", "",
              "| definition | population | calendar | pooled | family-year |",
              "|---|---|---|---:|---:|"]
    for definition in PANEL_DEFINITIONS:
        for population in PANEL_POPULATIONS:
            for calendar in ("full_2017_2019_2021_2023_2024",
                             "nonreuse_2017_2021_2023_2024"):
                cells = []
                for structure in STRUCTURES:
                    row = p.loc[p.definition.eq(definition) & p.population.eq(population) &
                                p.calendar_rule.eq(calendar) & p.structure.eq(structure)]
                    require(len(row) == 1, "findings panel row is not unique")
                    value = row.iloc[0]
                    cells.append(f"{value.coefficient:.4f} [{value.ACS_block_independent_SDR_ci_lower:.4f}, {value.ACS_block_independent_SDR_ci_upper:.4f}]")
                lines.append(f"| `{definition}` | `{population}` | `{calendar}` | " +
                             " | ".join(cells) + " |")
    lines += ["", "## Interpretation boundary", "",
              "The ACS intervals above measure person-sampling uncertainty under the stated year-block approximation. Occupation- and family-shock intervals are reported separately in the machine-readable tables. Larger respondent counts do not repair missing family-by-quintile comparisons, and neither interval identifies a causal AI effect.", "",
              f"There are {len(d)} paired pooled-minus-family-year rows. A paired interval containing zero is described only as failure to detect a difference, never as equivalence.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acs-dir", type=Path, required=True)
    parser.add_argument("--bridge", type=Path, required=True)
    parser.add_argument("--primary-membership", type=Path, required=True)
    parser.add_argument("--broader-membership", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output_dir.exists(), "refusing to overwrite ACS output directory")
    expected = {year: args.acs_dir / f"acs1_pums_{year}_csv_pus.zip" for year in YEARS}
    require(all(path.is_file() for path in expected.values()), "one or more annual ACS ZIPs are missing")
    definitions, definition_audit = load_memberships(
        args.primary_membership, args.broader_membership)
    broader_support = set(definitions["BCC_analogue_broader_equal"].occ_code)
    bridge = prepare_bridge(args.bridge, broader_support)
    all_cells: list[pd.DataFrame] = []
    manifests: list[dict[str, Any]] = []
    for year, path in expected.items():
        cells, manifest = aggregate_year(year, path, bridge, broader_support)
        all_cells.append(cells)
        manifests.append(manifest)
    cells = pd.concat(all_cells, ignore_index=True)
    require(set(cells.year.unique()) == set(YEARS), "annual cell calendar differs")
    benchmarks, benchmark_reps = benchmark_results(cells, definitions)
    benchmark_paired = benchmark_paired_results(benchmarks, benchmark_reps)
    panels, paired, panel_reps = panel_results(cells, definitions)
    support, tails = support_information(cells, definitions)

    args.output_dir.mkdir(parents=True)
    write_csv(args.output_dir / "ACS_BENCHMARK_RESULTS.csv", benchmarks)
    write_csv(args.output_dir / "ACS_BENCHMARK_PAIRED.csv", benchmark_paired)
    write_csv(args.output_dir / "ACS_PANEL_RESULTS.csv", panels)
    write_csv(args.output_dir / "ACS_PANEL_PAIRED.csv", paired)
    write_csv(args.output_dir / "ACS_SURVEY_REPLICATE_ESTIMATES.csv",
              benchmark_reps + panel_reps)
    write_csv(args.output_dir / "ACS_SUPPORT_INFORMATION.csv", support)
    write_csv(args.output_dir / "ACS_DIRECT_TAIL_SUPPORT.csv", tails)
    input_manifest = {
        "status": "PASS_PUBLIC_ACS_INPUT_READ",
        "years": list(YEARS), "omitted_year": 2020,
        "files": manifests, "definition_audit": definition_audit,
        "bridge": {"path": str(args.bridge.resolve()), "sha256": sha256_file(args.bridge)},
        "primary_membership": {"path": str(args.primary_membership.resolve()),
                               "sha256": sha256_file(args.primary_membership)},
        "broader_membership": {"path": str(args.broader_membership.resolve()),
                               "sha256": sha256_file(args.broader_membership)},
    }
    write_json(args.output_dir / "ACS_INPUT_MANIFEST.json", input_manifest)
    (args.output_dir / "FINDINGS.md").write_text(
        findings_text(benchmarks, panels, paired), encoding="utf-8")
    outputs = [
        "ACS_BENCHMARK_RESULTS.csv", "ACS_BENCHMARK_PAIRED.csv",
        "ACS_PANEL_RESULTS.csv", "ACS_PANEL_PAIRED.csv",
        "ACS_SURVEY_REPLICATE_ESTIMATES.csv", "ACS_SUPPORT_INFORMATION.csv",
        "ACS_DIRECT_TAIL_SUPPORT.csv", "ACS_INPUT_MANIFEST.json", "FINDINGS.md",
    ]
    receipt = {
        "status": "PASS_PUBLIC_ACS_EXTENSION",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(), "code_sha256": sha256_file(Path(__file__)),
        "spec_sha256": sha256_file(HERE / "ACS_EXTENSION_SPEC.md"),
        "years": list(YEARS), "model_years": list(MODEL_YEARS),
        "nonreuse_model_years": list(NONREUSE_MODEL_YEARS),
        "transition_year": 2022, "standard_2020_one_year_spliced": False,
        "replicate_count_per_year": REPLICATES, "SDR_factor": SDR_FACTOR,
        "cross_year_variance_assumption":
            "year-block independent approximation; exact cross-year address linkage unavailable",
        "benchmark_result_count": len(benchmarks), "panel_model_count": len(panels),
        "benchmark_paired_count": len(benchmark_paired),
        "paired_result_count": len(paired),
        "replicate_result_count": len(benchmark_reps) + len(panel_reps),
        "panel_replicate_estimator":
            "same_grouped_logit_score_signed_SDR_weights",
        "panel_replicate_fit_count": len(panel_reps),
        "panel_replicate_maximum_normalized_score": max(
            float(row["replicate_maximum_normalized_score"])
            for row in panel_reps),
        "panel_replicate_maximum_iterations": max(
            int(row["replicate_iterations"]) for row in panel_reps),
        "panel_replicates_with_negative_young_cells": sum(
            int(row["replicate_negative_young_cells"] > 0) for row in panel_reps),
        "panel_replicates_with_negative_older_cells": sum(
            int(row["replicate_negative_older_cells"] > 0) for row in panel_reps),
        "panel_replicates_with_nonpositive_total_cells": sum(
            int(row["replicate_nonpositive_total_cells"] > 0) for row in panel_reps),
        "panel_replicates_with_inactive_first_effects": sum(
            int(row["replicate_inactive_first_effects"] > 0) for row in panel_reps),
        "panel_replicates_with_inactive_second_effects": sum(
            int(row["replicate_inactive_second_effects"] > 0) for row in panel_reps),
        "output_hashes": {name: sha256_file(args.output_dir / name) for name in outputs},
    }
    receipt["receipt_id"] = "yax_acs_extension_v1_" + hashlib.sha256(
        stable_json(receipt).encode()).hexdigest()
    write_json(args.output_dir / "EXECUTION_RECEIPT.json", receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
