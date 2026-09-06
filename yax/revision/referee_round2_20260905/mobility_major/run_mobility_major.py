#!/usr/bin/env python3
"""Execute the RR1-M11 / RR2-M8 YAX mobility revision.

POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1.

Raw linked CPS records are read only on SCC.  Every written output is an
aggregate or a simulation draw and contains no respondent identifier.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import itertools
import json
import math
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd


HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
LABEL = "POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1"
MEASURES = (
    "aioe_admin_equal",
    "aioe_ability_direct",
    "aioe_oews2018_source_weighted",
    "dv_rating_alpha",
    "dv_rating_beta",
    "dv_rating_gamma",
)
AIOE = MEASURES[:3]
TASK = MEASURES[3:]
KEYS = (
    "age_group",
    "month",
    "origin_major",
    "destination_major",
    "origin_code",
    "destination_code",
)
PSEUDO_UNITS = 200_000
ALT_DRAWS = 999
ALT_SEED = 2026090512
BOOT_DRAWS = 399
BOOT_REMATCHES = 2
BOOT_PSEUDO_UNITS = 200_000
BOOT_SEED = 2026090511


def import_path(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


P3 = import_path(
    "yax_round2_mobility_phase3",
    ROOT / "yax/analysis/postoutcome_phase3_final/run_phase3.py",
)
CORE = P3.CORE
P25 = P3.P25


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def write_json(path: pathlib.Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_csv(path: pathlib.Path, rows: list[dict]) -> None:
    if not rows:
        raise RuntimeError("refusing to write empty CSV: {}".format(path))
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    values = np.asarray(values, float)
    weights = np.asarray(weights, float)
    keep = np.isfinite(values) & np.isfinite(weights) & (weights > 0)
    if not keep.any():
        raise RuntimeError("weighted mean has no positive finite observations")
    return float(np.average(values[keep], weights=weights[keep]))


def percentile_interval(values: np.ndarray) -> list[float]:
    return [float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))]


def normal_interval(center: float, standard_error: float) -> list[float]:
    return [center - 1.959963984540054 * standard_error,
            center + 1.959963984540054 * standard_error]


def build_switch_frame(args: argparse.Namespace):
    """Rebuild the Phase-3 six-way switch frame and retain cluster IDs."""
    reference, moments = P3.load_reference_components(args.characteristics)
    pairs, link = P25.PRIMARY.load_pairs(args.microdata, args.weight_patch)
    maps = P25.exposure_maps(args.lookup)
    employment = P25.preperiod_employment(args.microdata)
    major = P25.major_group_map(args.bridge, args.computerization)
    frame = P25.build_switch_universe(pairs, maps, employment, major)

    if not frame.index.is_unique:
        raise RuntimeError("switch frame index is not unique")
    cluster = pairs.loc[frame.index, ["CPSID", "CPSIDV", "month"]]
    if not np.array_equal(cluster.month.to_numpy(), frame.month.to_numpy()):
        raise RuntimeError("cluster identifiers did not align to switch rows")
    frame["household_cluster"] = cluster.CPSID.to_numpy()
    frame["respondent_cluster"] = cluster.CPSIDV.to_numpy()

    frame["opposite_direction_conflict"] = False
    sixway = frame.sixway_included.to_numpy(bool)
    signs = frame.loc[sixway, ["sign__{}".format(m) for m in MEASURES]].to_numpy(float)
    frame.loc[sixway, "opposite_direction_conflict"] = (
        (np.min(signs, axis=1) < 0) & (np.max(signs, axis=1) > 0)
    )
    components = CORE.component_maps(maps, moments)
    common = frame.loc[frame.sixway_included].copy()
    for measure in MEASURES:
        mapping = components["z__{}".format(measure)]
        common["d__z__{}".format(measure)] = (
            common.destination_code.map(mapping) - common.origin_code.map(mapping)
        )
    if common[["d__z__{}".format(m) for m in MEASURES]].isna().any().any():
        raise RuntimeError("six-way common switch has a missing standardized movement")
    if len(common) != 108_500:
        raise RuntimeError("six-way switch count changed: {}".format(len(common)))
    return reference, common, maps, link


def pair_conflict(frame: pd.DataFrame, left: str, right: str, mask: np.ndarray) -> dict:
    dl = frame["d__z__{}".format(left)].to_numpy(float)[mask]
    dr = frame["d__z__{}".format(right)].to_numpy(float)[mask]
    weights = frame.LNKFW1MWT.to_numpy(float)[mask]
    conflict = dl * dr < 0
    non_tie = (dl != 0) & (dr != 0)
    family_left = "AIOE" if left in AIOE else "task_share"
    family_right = "AIOE" if right in AIOE else "task_share"
    family_block = (
        "within_AIOE" if family_left == family_right == "AIOE"
        else "within_task_share" if family_left == family_right == "task_share"
        else "between_families"
    )
    return {
        "analysis_status": LABEL,
        "measure_1": left,
        "measure_2": right,
        "family_1": family_left,
        "family_2": family_right,
        "family_block": family_block,
        "switches": int(mask.sum()),
        "switch_weight": float(weights.sum()),
        "both_nonzero_weight_share": weighted_mean(non_tie.astype(float), weights),
        "conflict_share_all_switches": weighted_mean(conflict.astype(float), weights),
        "conflict_share_conditional_both_nonzero": weighted_mean(
            conflict[non_tie].astype(float), weights[non_tie]
        ),
    }


def family_balanced_rows(frame: pd.DataFrame, represented_mask: np.ndarray) -> tuple[list[dict], dict]:
    rows: list[dict] = []
    for support_name, mask in (
        ("sixway_all", np.ones(len(frame), dtype=bool)),
        ("hard_benchmark_represented", represented_mask),
    ):
        local: list[dict] = []
        for left, right in itertools.combinations(MEASURES, 2):
            row = pair_conflict(frame, left, right, mask)
            row["support"] = support_name
            local.append(row)
            rows.append(row)
        for block in ("within_AIOE", "within_task_share", "between_families"):
            selected = [row for row in local if row["family_block"] == block]
            rows.append({
                "analysis_status": LABEL,
                "support": support_name,
                "measure_1": "BLOCK_AVERAGE",
                "measure_2": block,
                "family_1": "",
                "family_2": "",
                "family_block": block,
                "switches": int(mask.sum()),
                "switch_weight": float(frame.loc[mask, "LNKFW1MWT"].sum()),
                "both_nonzero_weight_share": float(np.mean([
                    row["both_nonzero_weight_share"] for row in selected
                ])),
                "conflict_share_all_switches": float(np.mean([
                    row["conflict_share_all_switches"] for row in selected
                ])),
                "conflict_share_conditional_both_nonzero": float(np.mean([
                    row["conflict_share_conditional_both_nonzero"] for row in selected
                ])),
            })
        block_rows = rows[-3:]
        rows.append({
            "analysis_status": LABEL,
            "support": support_name,
            "measure_1": "FAMILY_BALANCED",
            "measure_2": "equal_one_third_block_weights",
            "family_1": "",
            "family_2": "",
            "family_block": "family_balanced_three_blocks",
            "switches": int(mask.sum()),
            "switch_weight": float(frame.loc[mask, "LNKFW1MWT"].sum()),
            "both_nonzero_weight_share": float(np.mean([
                row["both_nonzero_weight_share"] for row in block_rows
            ])),
            "conflict_share_all_switches": float(np.mean([
                row["conflict_share_all_switches"] for row in block_rows
            ])),
            "conflict_share_conditional_both_nonzero": float(np.mean([
                row["conflict_share_conditional_both_nonzero"] for row in block_rows
            ])),
        })
    definition = {
        "pair_count": 15,
        "within_AIOE_pairs": 3,
        "within_task_share_pairs": 3,
        "between_family_pairs": 9,
        "family_balanced_rule": (
            "arithmetic mean of the within-AIOE, within-task-share, and "
            "between-family block means; each conceptual block receives one third"
        ),
        "status": "descriptive normalization; no unique welfare scale asserted",
    }
    return rows, definition


def endpoint_identity(reference: pd.DataFrame, frame: pd.DataFrame) -> dict:
    raw_error = (
        reference.dv_rating_beta
        - (reference.dv_rating_alpha + reference.dv_rating_gamma) / 2
    ).to_numpy(float)
    da = frame["d__z__dv_rating_alpha"].to_numpy(float)
    db = frame["d__z__dv_rating_beta"].to_numpy(float)
    dg = frame["d__z__dv_rating_gamma"].to_numpy(float)
    endpoints_same_strict = ((da > 0) & (dg > 0)) | ((da < 0) & (dg < 0))
    violation = endpoints_same_strict & (np.sign(db) != np.sign(da))
    endpoint_conflict = da * dg < 0
    beta_conflict_alpha = da * db < 0
    beta_conflict_gamma = dg * db < 0
    impossible_new = (~endpoint_conflict) & (beta_conflict_alpha | beta_conflict_gamma)
    weights = frame.LNKFW1MWT.to_numpy(float)
    return {
        "analysis_status": LABEL,
        "identity": "beta = (alpha + broad) / 2 on raw task shares",
        "maximum_absolute_raw_occupation_identity_error": float(np.max(np.abs(raw_error))),
        "positive_standardization_preserves_movement_sign": True,
        "switches_with_same_strict_endpoint_sign": int(endpoints_same_strict.sum()),
        "same_endpoint_sign_weight_share": weighted_mean(endpoints_same_strict.astype(float), weights),
        "beta_sign_violations_when_endpoints_agree": int(violation.sum()),
        "beta_new_conflict_violations": int(impossible_new.sum()),
        "endpoint_alpha_broad_conflict_share": weighted_mean(endpoint_conflict.astype(float), weights),
        "interpretation": (
            "beta is redundant for zero-threshold directional-conflict detection "
            "when alpha and broad are both included; it can still affect separately "
            "standardized magnitude thresholds and movement-mass summaries"
        ),
    }


def cell_table(frame: pd.DataFrame, units: int) -> tuple[pd.DataFrame, dict, np.ndarray]:
    cells = (
        frame.groupby(list(KEYS), as_index=False)
        .agg(
            official_weight=("LNKFW1MWT", "sum"),
            realized_conflict=("opposite_direction_conflict", "first"),
            rows=("LNKFW1MWT", "size"),
        )
        .sort_values(list(KEYS), kind="mergesort")
        .reset_index(drop=True)
    )
    counts, expected = CORE.hamilton_counts(cells.official_weight.to_numpy(float), units)
    cells["pseudo_count"] = counts
    cells["represented"] = counts > 0
    cells["stratum_key"] = list(map(tuple, cells[list(KEYS[:4])].to_numpy()))
    cells["stratum_id"], levels = pd.factorize(cells.stratum_key, sort=True)
    represented_index = pd.MultiIndex.from_frame(cells.loc[cells.represented, list(KEYS)])
    frame_index = pd.MultiIndex.from_frame(frame[list(KEYS)])
    represented_mask = frame_index.isin(represented_index)
    if int(represented_mask.sum()) != int(cells.loc[cells.represented, "rows"].sum()):
        raise RuntimeError("represented support did not map back to switch records")
    detail = {
        "strata": int(len(levels)),
        "cells_total": int(len(cells)),
        "cells_represented": int(cells.represented.sum()),
        "max_joint_share_approximation_error": float(
            np.max(np.abs(counts / units - expected / units))
        ),
    }
    return cells, detail, represented_mask


def conflict_matrix(maps: dict, codes: list[str]) -> np.ndarray:
    exposure = np.column_stack([
        [maps[measure][code] for code in codes] for measure in MEASURES
    ])
    signs = np.sign(exposure[None, :, :] - exposure[:, None, :])
    return ((np.min(signs, axis=2) < 0) & (np.max(signs, axis=2) > 0))


def expand_pseudo(cells: pd.DataFrame, counts: np.ndarray, maps: dict) -> dict:
    represented = counts > 0
    local = cells.loc[represented].copy()
    local["pseudo_count_local"] = counts[represented]
    codes = sorted(set(local.origin_code) | set(local.destination_code))
    code_index = {code: index for index, code in enumerate(codes)}
    stratum_id, levels = pd.factorize(local.stratum_key, sort=True)
    local["local_stratum_id"] = stratum_id
    order = np.argsort(local.local_stratum_id.to_numpy(), kind="mergesort")
    local = local.iloc[order].reset_index(drop=True)
    origin = np.repeat(
        local.origin_code.map(code_index).to_numpy(int), local.pseudo_count_local
    )
    destination = np.repeat(
        local.destination_code.map(code_index).to_numpy(int), local.pseudo_count_local
    )
    groups = np.repeat(local.local_stratum_id.to_numpy(int), local.pseudo_count_local)
    if len(origin) != int(counts.sum()) or np.any(origin == destination):
        raise RuntimeError("invalid hard pseudo-population")
    return {
        "origin": origin,
        "destination": destination,
        "groups": groups,
        "conflict": conflict_matrix(maps, codes),
        "strata": int(len(levels)),
        "represented_cells": int(represented.sum()),
        "represented_cell_mask": represented,
    }


def fast_no_self_repair(
    origin: np.ndarray,
    destination: np.ndarray,
    groups: np.ndarray,
    rng: np.random.Generator,
    random_bad: bool,
    max_attempts: int = 20,
) -> tuple[np.ndarray, int, int]:
    """Phase-3 no-self repair, skipping strata with no initial self-match.

    With ``random_bad=False`` this has the same stochastic rule as the sealed
    implementation: the first bad position in a stratum is repaired with a
    uniformly selected feasible partner.  The speed-up is exact because the
    omitted strata used no random numbers and required no repair.  With
    ``random_bad=True``, the bad position is also selected uniformly.
    """
    origin = np.asarray(origin)
    destination = np.asarray(destination)
    groups = np.asarray(groups)
    boundaries = np.r_[0, 1 + np.flatnonzero(groups[1:] != groups[:-1]), len(groups)]
    for attempt in range(1, max_attempts + 1):
        keys = rng.random(len(destination))
        shuffled_order = np.lexsort((keys, groups))
        candidate = destination[shuffled_order].copy()
        if not np.array_equal(groups[shuffled_order], groups):
            raise RuntimeError("alternative repair crossed a stratum")
        repairs = 0
        failed = False
        bad_groups = np.unique(groups[origin == candidate])
        for group in bad_groups:
            start, stop = boundaries[int(group)], boundaries[int(group) + 1]
            local_origin = origin[start:stop]
            local_destination = candidate[start:stop]
            for _ in range(max(1, 4 * (stop - start))):
                bad = np.flatnonzero(local_origin == local_destination)
                if len(bad) == 0:
                    break
                i = int(bad[rng.integers(len(bad))]) if random_bad else int(bad[0])
                feasible = np.flatnonzero(
                    (np.arange(stop - start) != i)
                    & (local_destination != local_origin[i])
                    & (local_destination[i] != local_origin)
                )
                if len(feasible) == 0:
                    failed = True
                    break
                j = int(feasible[rng.integers(len(feasible))])
                local_destination[i], local_destination[j] = (
                    local_destination[j], local_destination[i]
                )
                repairs += 1
            if failed or np.any(local_origin == local_destination):
                failed = True
                break
            candidate[start:stop] = local_destination
        if not failed:
            if np.any(origin == candidate):
                raise RuntimeError("self transition survived alternative repair")
            return candidate, repairs, attempt
    raise RuntimeError("alternative no-self repair failed")


def alternative_random_bad_repair(
    origin: np.ndarray,
    destination: np.ndarray,
    groups: np.ndarray,
    rng: np.random.Generator,
    max_attempts: int = 20,
) -> tuple[np.ndarray, int, int]:
    return fast_no_self_repair(
        origin, destination, groups, rng, random_bad=True, max_attempts=max_attempts
    )


def sealed_first_bad_repair(
    origin: np.ndarray,
    destination: np.ndarray,
    groups: np.ndarray,
    rng: np.random.Generator,
    max_attempts: int = 20,
) -> tuple[np.ndarray, int, int]:
    return fast_no_self_repair(
        origin, destination, groups, rng, random_bad=False, max_attempts=max_attempts
    )


def validate_margins(origin: np.ndarray, before: np.ndarray, after: np.ndarray,
                     groups: np.ndarray) -> bool:
    if np.any(origin == after):
        return False
    for group in np.unique(groups):
        mask = groups == group
        if not np.array_equal(np.sort(before[mask]), np.sort(after[mask])):
            return False
    return True


def support_reconciliation(frame: pd.DataFrame, cells: pd.DataFrame, detail: dict,
                           represented_mask: np.ndarray, sealed: dict) -> dict:
    weights = frame.LNKFW1MWT.to_numpy(float)
    conflict = frame.opposite_direction_conflict.to_numpy(bool)
    s = float(weights[represented_mask].sum() / weights.sum())
    r_all = weighted_mean(conflict.astype(float), weights)
    r_rep = weighted_mean(conflict[represented_mask].astype(float), weights[represented_mask])
    omitted = ~represented_mask
    r_omit = weighted_mean(conflict[omitted].astype(float), weights[omitted])
    b_rep = float(sealed["hard_benchmark_mean"])
    if abs(s - float(sealed["represented_official_weight_share"])) > 1e-12:
        raise RuntimeError("reconstructed represented weight share differs from sealed receipt")
    if abs(r_all - float(sealed["realized_conflict_official_weight"])) > 1e-12:
        raise RuntimeError("all-support realized conflict differs from sealed receipt")
    conditional_gap = r_rep - b_rep
    benchmark_bounds = [s * b_rep, s * b_rep + (1 - s)]
    gap_bounds = [r_all - benchmark_bounds[1], r_all - benchmark_bounds[0]]
    return {
        "analysis_status": LABEL,
        "pseudo_units": PSEUDO_UNITS,
        **detail,
        "represented_official_weight_share": s,
        "omitted_official_weight_share": 1 - s,
        "all_support_realized_conflict": r_all,
        "represented_support_realized_conflict": r_rep,
        "omitted_support_realized_conflict_descriptive": r_omit,
        "represented_support_benchmark_mean": b_rep,
        "represented_support_conditional_gap": conditional_gap,
        "previous_misaligned_gap_all_realized_minus_represented_benchmark": r_all - b_rep,
        "all_support_benchmark_conflict_bounds": benchmark_bounds,
        "all_support_realized_minus_benchmark_bounds": gap_bounds,
        "bound_assumption": (
            "omitted-support benchmark conflict is unrestricted in [0,1]; "
            "observed all-support realized conflict is known"
        ),
        "gap_sign_identified_under_omitted_support_bounds": bool(
            gap_bounds[0] > 0 or gap_bounds[1] < 0
        ),
    }


def alternative_rule_sensitivity(cells: pd.DataFrame, maps: dict, sealed: dict):
    counts = cells.pseudo_count.to_numpy(int)
    pseudo = expand_pseudo(cells, counts, maps)
    rng = np.random.default_rng(ALT_SEED)
    draws = np.empty(ALT_DRAWS)
    repairs = np.empty(ALT_DRAWS, int)
    attempts = np.empty(ALT_DRAWS, int)
    margins_ok = True
    for draw in range(ALT_DRAWS):
        rematched, repair_count, attempt = alternative_random_bad_repair(
            pseudo["origin"], pseudo["destination"], pseudo["groups"], rng
        )
        draws[draw] = float(np.mean(pseudo["conflict"][pseudo["origin"], rematched]))
        repairs[draw] = repair_count
        attempts[draw] = attempt
        if draw < 5:
            margins_ok &= validate_margins(
                pseudo["origin"], pseudo["destination"], rematched, pseudo["groups"]
            )
    original_draws = np.asarray(sealed["benchmark_draws"], float)
    summary = {
        "analysis_status": LABEL,
        "same_pseudo_population": True,
        "pseudo_units": int(len(pseudo["origin"])),
        "draws_per_rule": ALT_DRAWS,
        "alternative_seed": ALT_SEED,
        "existing_rule": {
            "initial_distribution": "uniform random permutation of destination pseudo-units within each hard stratum",
            "repair_path": "scan first self-match, choose feasible swap partner uniformly, restart after impasse",
            "uniform_over_feasible_derangements": False,
            "reason": "feasible assignments have unequal numbers of initial permutations and repair paths leading to them",
            "mean": float(original_draws.mean()),
            "sd_across_rematches": float(original_draws.std(ddof=1)),
            "mc_se_of_mean": float(original_draws.std(ddof=1) / math.sqrt(len(original_draws))),
            "central_95_percent_rematch_interval": percentile_interval(original_draws),
        },
        "alternative_rule": {
            "initial_distribution": "uniform random permutation of destination pseudo-units within each hard stratum",
            "repair_path": "choose a self-match uniformly, choose a feasible swap partner uniformly, restart after impasse",
            "uniform_over_feasible_derangements": False,
            "mean": float(draws.mean()),
            "sd_across_rematches": float(draws.std(ddof=1)),
            "mc_se_of_mean": float(draws.std(ddof=1) / math.sqrt(len(draws))),
            "central_95_percent_rematch_interval": percentile_interval(draws),
            "maximum_repairs": int(repairs.max()),
            "maximum_attempts": int(attempts.max()),
        },
        "alternative_minus_existing_mean": float(draws.mean() - original_draws.mean()),
        "margins_and_no_self_verified_first_five_draws": bool(margins_ok),
        "interpretation": (
            "both are algorithm-defined benchmark distributions; agreement is a "
            "repair-rule sensitivity, not proof of a unique random-matching null"
        ),
    }
    rows = [
        {"draw": i + 1, "alternative_random_bad_conflict": float(value)}
        for i, value in enumerate(draws)
    ]
    return summary, rows


def prepare_bootstrap_arrays(frame: pd.DataFrame, cells: pd.DataFrame):
    key_index = pd.MultiIndex.from_frame(cells[list(KEYS)])
    index_lookup = {key: index for index, key in enumerate(key_index)}
    row_keys = list(map(tuple, frame[list(KEYS)].to_numpy()))
    cell_index = np.fromiter((index_lookup[key] for key in row_keys), int, len(row_keys))
    household = frame.household_cluster.to_numpy()
    missing_household = household == 0
    if missing_household.any():
        replacement = np.arange(missing_household.sum(), dtype=np.int64)
        floor = int(np.max(np.abs(household))) + 1
        household = household.copy()
        household[missing_household] = -(floor + replacement)
    household_index, levels = pd.factorize(household, sort=True)
    return cell_index, household_index.astype(int), int(len(levels)), int(missing_household.sum())


def cluster_bootstrap(frame: pd.DataFrame, cells: pd.DataFrame, maps: dict,
                      represented_mask: np.ndarray, sealed: dict):
    cell_index, cluster_index, cluster_count, missing_clusters = prepare_bootstrap_arrays(
        frame, cells
    )
    rng = np.random.default_rng(BOOT_SEED)
    row_weight = frame.LNKFW1MWT.to_numpy(float)
    conflict = frame.opposite_direction_conflict.to_numpy(bool)
    cell_conflict = cells.realized_conflict.to_numpy(bool)
    cell_count = len(cells)
    draws: list[dict] = []
    failed = 0
    for draw in range(BOOT_DRAWS):
        multiplier = rng.exponential(scale=1.0, size=cluster_count)
        bootstrap_row_weight = row_weight * multiplier[cluster_index]
        bootstrap_cell_weight = np.bincount(
            cell_index, weights=bootstrap_row_weight, minlength=cell_count
        )
        if bootstrap_cell_weight.sum() <= 0:
            raise RuntimeError("zero total bootstrap weight")
        counts, _ = CORE.hamilton_counts(bootstrap_cell_weight, BOOT_PSEUDO_UNITS)
        pseudo = expand_pseudo(cells, counts, maps)
        represented_cells = pseudo["represented_cell_mask"]
        represented_rows = represented_cells[cell_index]
        realized = weighted_mean(
            conflict[represented_rows].astype(float),
            bootstrap_row_weight[represented_rows],
        )
        rematch = np.empty(BOOT_REMATCHES)
        try:
            for j in range(BOOT_REMATCHES):
                destination, _, _ = sealed_first_bad_repair(
                    pseudo["origin"], pseudo["destination"], pseudo["groups"], rng
                )
                rematch[j] = float(np.mean(
                    pseudo["conflict"][pseudo["origin"], destination]
                ))
        except RuntimeError:
            failed += 1
            continue
        benchmark = float(rematch.mean())
        draws.append({
            "draw": draw + 1,
            "realized_conflict": realized,
            "benchmark_mean_rematches": benchmark,
            "realized_minus_benchmark": realized - benchmark,
            "within_rematch_variance": float(rematch.var(ddof=1)),
            "pseudo_represented_cells": int(represented_cells.sum()),
        })
    if len(draws) < int(0.95 * BOOT_DRAWS):
        raise RuntimeError("too many cluster bootstrap repair failures: {}".format(failed))
    realized_values = np.array([row["realized_conflict"] for row in draws])
    benchmark_values = np.array([row["benchmark_mean_rematches"] for row in draws])
    gap_values = np.array([row["realized_minus_benchmark"] for row in draws])
    within_variance = np.array([row["within_rematch_variance"] for row in draws])
    raw_gap_variance = float(gap_values.var(ddof=1))
    mean_mc_variance_of_mean = float(np.mean(within_variance) / BOOT_REMATCHES)
    adjusted_gap_se = math.sqrt(max(raw_gap_variance - mean_mc_variance_of_mean, 0.0))

    weights = frame.LNKFW1MWT.to_numpy(float)
    conflict_all = frame.opposite_direction_conflict.to_numpy(bool)
    point_realized = weighted_mean(
        conflict_all[represented_mask].astype(float), weights[represented_mask]
    )
    point_gap = point_realized - float(sealed["hard_benchmark_mean"])
    summary = {
        "analysis_status": LABEL,
        "sampling_model": (
            "mean-one exponential multiplier bootstrap at longitudinal household "
            "CPSID cluster; official LNKFW1MWT retained"
        ),
        "not_covered": (
            "not CPS replicate-weight/full complex-survey inference; exposure construction, "
            "crosswalk allocation, and latent occupation-code error are not resampled"
        ),
        "seed": BOOT_SEED,
        "requested_draws": BOOT_DRAWS,
        "successful_draws": len(draws),
        "failed_draws": failed,
        "household_clusters": cluster_count,
        "zero_CPSID_rows_treated_as_separate_clusters": missing_clusters,
        "rematches_per_bootstrap": BOOT_REMATCHES,
        "pseudo_units_per_bootstrap": BOOT_PSEUDO_UNITS,
        "realized_conflict": {
            "point_on_sealed_represented_support": point_realized,
            "cluster_bootstrap_se": float(realized_values.std(ddof=1)),
            "percentile_95_interval": percentile_interval(realized_values),
        },
        "benchmark": {
            "sealed_200k_999_draw_mean": float(sealed["hard_benchmark_mean"]),
            "sealed_sd_across_rematches": float(sealed["hard_benchmark_sd"]),
            "sealed_mc_se_of_mean": float(
                sealed["hard_benchmark_sd"] / math.sqrt(sealed["draws"])
            ),
            "bootstrap_plugin_mean": float(benchmark_values.mean()),
            "bootstrap_plugin_raw_sd": float(benchmark_values.std(ddof=1)),
        },
        "realized_minus_benchmark": {
            "point_on_sealed_represented_support": point_gap,
            "raw_cluster_bootstrap_plus_mc_se": float(gap_values.std(ddof=1)),
            "raw_percentile_95_interval": percentile_interval(gap_values),
            "mean_within_replicate_mc_variance_of_rematch_mean": mean_mc_variance_of_mean,
            "variance_subtracted_cluster_sampling_se": adjusted_gap_se,
            "normal_95_interval_using_variance_subtracted_se": normal_interval(
                point_gap, adjusted_gap_se
            ),
        },
        "separation_rule": (
            "sampling variance is raw variance of bootstrap replicate gap means minus "
            "average within-replicate rematch variance divided by the recorded number "
            "of rematches, truncated at zero"
        ),
        "bootstrap_pseudo_represented_cells": {
            "p10": float(np.quantile([
                row["pseudo_represented_cells"] for row in draws
            ], 0.10)),
            "median": float(np.median([
                row["pseudo_represented_cells"] for row in draws
            ])),
            "p90": float(np.quantile([
                row["pseudo_represented_cells"] for row in draws
            ], 0.90)),
        },
    }
    return summary, draws


def entry_evidence(args: argparse.Namespace) -> dict:
    results = pd.read_csv(args.phase2_flow_results)
    row = results.loc[
        results.margin.eq("entry_destination") & results.weighting.eq("official")
    ]
    if len(row) != 1:
        raise RuntimeError("expected one official entry-destination row")
    item = row.iloc[0]
    counts = pd.read_csv(args.phase2_flow_counts)
    count = counts.loc[
        counts.margin.eq("entry_destination") & counts.weighting.eq("official")
    ]
    if len(count) != 1:
        raise RuntimeError("expected one official entry count row")
    count = count.iloc[0]
    return {
        "analysis_status": LABEL,
        "record": "existing Phase-2 entry-destination evidence surfaced for RR1-M11",
        "source_result_sha256": sha256(args.phase2_flow_results),
        "source_count_sha256": sha256(args.phase2_flow_counts),
        "coefficient_log_points": float(item.coefficient_log_points),
        "exponential_percent": float(item.exponential_percent),
        "analytic_cluster_se": float(item.analytic_cluster_se),
        "wild_score_ci": [float(item.wild_score_ci_lower), float(item.wild_score_ci_upper)],
        "wild_score_p_value": float(item.wild_score_p_value),
        "entrants_raw": int(count.risk_or_entrant_raw),
        "entrants_official_weight": float(count.risk_or_entrant_weighted),
        "young_entrants_raw": int(count.young_events_raw),
        "post_entrants_raw": int(count.post_events_raw),
        "estimand": (
            "post change in young-versus-older allocation of observed entrants to beta "
            "Q5 rather than Q1 destination occupations, conditional on a linked "
            "nonemployed origin becoming employed"
        ),
        "not_an_estimand": "employment-finding probability or hiring hazard from a nonemployment risk set",
        "interpretation": (
            "point estimate is negative but imprecise; the interval includes zero and "
            "does not establish the presence or absence of an entry-allocation mechanism"
        ),
    }


def coding_instability_decision(frame: pd.DataFrame, phase1_receipt_path: pathlib.Path) -> dict:
    weights = frame.LNKFW1MWT.to_numpy(float)
    reversal = frame.immediate_reversal.to_numpy(bool)
    observable = frame.t2_observable.to_numpy(bool)
    phase1 = json.loads(phase1_receipt_path.read_text())
    earlier = phase1["flow_feasibility"]["switching"]
    return {
        "analysis_status": LABEL,
        "immediate_reversal_share_all_switches_official_weight": weighted_mean(
            reversal.astype(float), weights
        ),
        "immediate_reversal_share_conditional_t2_observable_raw": float(
            reversal.sum() / observable.sum()
        ),
        "immediate_reversal_share_conditional_t2_observable_official_weight": weighted_mean(
            reversal[observable].astype(float), weights[observable]
        ),
        "immediate_reversal_switches": int(reversal.sum()),
        "t2_observable_switches": int(observable.sum()),
        "earlier_phase1_universe": {
            "ages": "18-65",
            "exposure_support_restriction": "none; flow-feasibility universe",
            "observable_first_switches": int(earlier["three_month_first_switches_observable"]),
            "immediate_reversals": int(earlier["immediate_A_B_A_reversals"]),
            "raw_conditional_share": float(
                earlier["immediate_reversal_share_of_observable_first_switches"]
            ),
            "source_sha256": sha256(phase1_receipt_path),
        },
        "measured_occupation_coding_error_rate": None,
        "stock_misclassification_curve_adopted": False,
        "decision": "principled non-adoption",
        "reason": (
            "A-B-A sequences mix genuine temporary moves, within-job assignment changes, "
            "proxy reporting, and occupation coding/reporting error.  The switch sample "
            "does not reveal a latent true occupation or a five-category transition-error "
            "matrix for the stock panel.  Under unknown differential errors, Q5-Q1 "
            "misclassification can attenuate, amplify, or reassign the contrast.  Treating "
            "the reversal share as a symmetric error probability would manufacture a correction."
        ),
        "evidence_needed_for_adoption": (
            "validated repeated occupation codes or an external reinterview/audit sample "
            "estimating the latent-code misclassification matrix by occupation and period"
        ),
    }


def cell_summary_rows(cells: pd.DataFrame) -> list[dict]:
    rows = []
    for represented, group in cells.groupby("represented", sort=False):
        rows.append({
            "analysis_status": LABEL,
            "support": "represented" if represented else "omitted_by_Hamilton_rounding",
            "detailed_cells": int(len(group)),
            "source_switch_rows": int(group.rows.sum()),
            "official_weight": float(group.official_weight.sum()),
            "official_weighted_realized_conflict": weighted_mean(
                group.realized_conflict.to_numpy(float), group.official_weight.to_numpy(float)
            ),
            "pseudo_units": int(group.pseudo_count.sum()),
        })
    return rows


def run(args: argparse.Namespace) -> dict:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    reference, frame, maps, link = build_switch_frame(args)
    sealed_all = json.loads(args.phase3_hard_results.read_text())
    sealed = sealed_all["primary_hard_benchmark"]

    cells, detail, represented_mask = cell_table(frame, PSEUDO_UNITS)
    support = support_reconciliation(frame, cells, detail, represented_mask, sealed)
    pair_rows, family_definition = family_balanced_rows(frame, represented_mask)
    identity = endpoint_identity(reference, frame)
    alternative, alternative_draws = alternative_rule_sensitivity(cells, maps, sealed)
    bootstrap, bootstrap_draws = cluster_bootstrap(
        frame, cells, maps, represented_mask, sealed
    )
    entry = entry_evidence(args)
    coding = coding_instability_decision(frame, args.phase1_receipt)

    write_csv(args.output_dir / "FAMILY_BALANCED_PAIRWISE_DISAGREEMENT.csv", pair_rows)
    write_json(args.output_dir / "FAMILY_BALANCED_DEFINITION.json", family_definition)
    write_json(args.output_dir / "TASK_ENDPOINT_IDENTITY.json", identity)
    write_json(args.output_dir / "HARD_SUPPORT_RECONCILIATION.json", support)
    write_csv(args.output_dir / "HARD_SUPPORT_CELL_SUMMARY.csv", cell_summary_rows(cells))
    write_json(args.output_dir / "HOUSEHOLD_CLUSTER_BOOTSTRAP.json", bootstrap)
    write_csv(args.output_dir / "HOUSEHOLD_CLUSTER_BOOTSTRAP_DRAWS.csv", bootstrap_draws)
    write_json(args.output_dir / "REMATCH_RULE_SENSITIVITY.json", alternative)
    write_csv(args.output_dir / "REMATCH_RULE_DRAWS.csv", alternative_draws)
    write_json(args.output_dir / "ENTRY_DESTINATION_EVIDENCE.json", entry)
    write_json(args.output_dir / "CODING_INSTABILITY_DECISION.json", coding)

    inputs = {
        "microdata_private": sha256(args.microdata),
        "longitudinal_weight_patch_private": sha256(args.weight_patch),
        "exposure_lookup": sha256(args.lookup),
        "computerization": sha256(args.computerization),
        "occupation_bridge": sha256(args.bridge),
        "occupation_characteristics": sha256(args.characteristics),
        "sealed_phase3_hard_results": sha256(args.phase3_hard_results),
        "phase2_flow_results": sha256(args.phase2_flow_results),
        "phase2_flow_counts": sha256(args.phase2_flow_counts),
        "phase1_flow_feasibility_receipt": sha256(args.phase1_receipt),
        "analysis_spec": sha256(HERE / "ANALYSIS_SPEC_BEFORE_RESULTS.md"),
        "technical_correction": sha256(
            HERE / "TECHNICAL_CORRECTION_BEFORE_FINAL_RERUN.md"
        ),
    }
    output_paths = sorted(
        path for path in args.output_dir.iterdir()
        if path.is_file() and path.name != "EXECUTION_RECEIPT.json"
    )
    receipt = {
        "analysis_status": LABEL,
        "record": "YAX RR1-M11 / RR2-M8 major mobility revision",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head_at_execution": git_head(),
        "switches": len(frame),
        "official_switch_weight": float(frame.LNKFW1MWT.sum()),
        "linked_sample_audit": link,
        "private_identifiers_written": False,
        "input_hashes": inputs,
        "output_hashes": {path.name: sha256(path) for path in output_paths},
        "fixed_seeds": {
            "household_cluster_bootstrap": BOOT_SEED,
            "alternative_rematch_rule": ALT_SEED,
        },
    }
    write_json(args.output_dir / "EXECUTION_RECEIPT.json", receipt)
    print(json.dumps({
        "status": "PASS_MAJOR_MOBILITY_EXECUTION",
        "switches": len(frame),
        "represented_share": support["represented_official_weight_share"],
        "conditional_gap": support["represented_support_conditional_gap"],
        "bootstrap_draws": bootstrap["successful_draws"],
    }, indent=2))
    return receipt


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--microdata", type=pathlib.Path, required=True)
    value.add_argument("--weight-patch", type=pathlib.Path, required=True)
    value.add_argument("--output-dir", type=pathlib.Path, required=True)
    value.add_argument(
        "--lookup", type=pathlib.Path,
        default=ROOT / "yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv",
    )
    value.add_argument(
        "--computerization", type=pathlib.Path,
        default=ROOT / "yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv",
    )
    value.add_argument(
        "--bridge", type=pathlib.Path,
        default=ROOT / "yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv",
    )
    value.add_argument(
        "--characteristics", type=pathlib.Path,
        default=ROOT / "yax/measurement/test_a/TEST_A_OCCUPATION_CHARACTERISTICS.csv",
    )
    value.add_argument(
        "--phase3-hard-results", type=pathlib.Path,
        default=ROOT / "yax/analysis/postoutcome_phase3_final/YAX_PHASE3_HARD_BENCHMARK_RESULTS.json",
    )
    value.add_argument(
        "--phase2-flow-results", type=pathlib.Path,
        default=ROOT / "yax/analysis/postoutcome_phase2/YAX_PHASE2_PRIMARY_BETA_FLOW_RESULTS.csv",
    )
    value.add_argument(
        "--phase2-flow-counts", type=pathlib.Path,
        default=ROOT / "yax/analysis/postoutcome_phase2/YAX_PHASE2_FLOW_SAMPLE_COUNTS.csv",
    )
    value.add_argument(
        "--phase1-receipt", type=pathlib.Path,
        default=ROOT / "yax/analysis/postoutcome_scope_phase1/YAX_SCOPE_PHASE1_REPRODUCIBILITY_RECEIPT.json",
    )
    return value


if __name__ == "__main__":
    run(parser().parse_args())
