#!/usr/bin/env python3
"""Execute the frozen final YAX Phase 3 program.

POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1.

The program runs one hard descriptive reallocation benchmark, one descriptive
shared/architecture-specific switch decomposition, exactly one new shared-F
employment-stock model, and supporting joint sign inference for the six
already reported literal-common-support specifications.
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
ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))
import phase3_core as CORE  # noqa: E402


LABEL = CORE.LABEL
MEASURES = CORE.MEASURES
PARENT = "3feda26c698b19823d3370eecb3abf2a57ad9cfd"
HARD_SEEDS = {"primary": 2026090301, "persistent": 2026090302}
STOCK_SEED = 2026090303
JOINT_SEED = 2026090304
DRAWS = 999
PSEUDO_UNITS = 200_000


def import_path(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


P25 = import_path(
    "yax_phase3_phase25",
    ROOT / "yax/analysis/postoutcome_phase25_gate3/run_phase25_reallocation_validity.py",
)
V4 = import_path(
    "yax_phase3_v4",
    ROOT / "yax/analysis/postoutcome_v4_supplementary/run_v4_alignment.py",
)
FROZEN = V4.FROZEN


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def support_hash(codes: list[str]) -> str:
    return hashlib.sha256("".join(f"{code}\n" for code in sorted(codes)).encode()).hexdigest()


def write_json(path: pathlib.Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: pathlib.Path, rows: list[dict]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty CSV: {path}")
    fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def authenticate(args: argparse.Namespace) -> dict:
    head = git("rev-parse", "HEAD")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", args.pre_result_commit, head],
        cwd=ROOT,
        check=False,
    ).returncode:
        raise RuntimeError("recorded pre-result commit is not an ancestor of execution HEAD")
    if head != args.pre_result_commit:
        changed = set(git("diff", "--name-only", f"{args.pre_result_commit}..{head}").splitlines())
        allowed = {
            "yax/analysis/postoutcome_phase3_final/run_phase3.py",
            "yax/analysis/postoutcome_phase3_final/YAX_PHASE3_IMPLEMENTATION_FIXES.md",
            "yax/tests/test_phase3_final.py",
        }
        if not changed or not changed.issubset(allowed):
            raise RuntimeError(f"post-plan execution changes exceed the documented bug fix: {changed}")
    protected = {
        "v1.1-design-freeze": git("rev-parse", "v1.1-design-freeze^{}"),
        "v1.1-confirmatory-results": git("rev-parse", "v1.1-confirmatory-results^{}"),
    }
    expected = {
        "v1.1-design-freeze": "22fbf7924809b7a535e31ae0ab68f5b113ce8078",
        "v1.1-confirmatory-results": "b16109482c3bf5ca176f6f08976e120b04769945",
    }
    if protected != expected:
        raise RuntimeError(f"protected peeled commit moved: {protected}")
    inputs = {
        "microdata": sha256(args.microdata),
        "weight_patch": sha256(args.weight_patch),
        "preperiod_cells": sha256(args.preperiod_cells),
        "lookup": sha256(args.lookup),
        "computerization": sha256(args.computerization),
        "bridge": sha256(args.bridge),
        "rule_b": sha256(args.rule_b_values),
        "first_access_receipt": sha256(args.first_access_receipt),
        "characteristics": sha256(args.characteristics),
        "sealed_table5b_results": sha256(args.table5b_results),
        "sealed_phase25_benchmark": sha256(args.phase25_benchmark),
    }
    expected_inputs = {
        "microdata": FROZEN.MICRODATA_SHA256,
        "weight_patch": "841e13798c34f74a8cd8e0ac1d913742aad5f24fce2c6876793ecf1dd8bd55a8",
        "preperiod_cells": FROZEN.PRE_CELLS_SHA256,
        "lookup": FROZEN.LOOKUP_SHA256,
        "computerization": FROZEN.COMP_SHA256,
        "bridge": FROZEN.BRIDGE_SHA256,
        "rule_b": "8092f0eef57aaf4271a7dc563a4820e2f9a6d13519bcac9372837bc7a2c991e6",
        "characteristics": "88311c3bc26f00fde4aa792888491ae4a1e340c601d1c62147d52727afbf207c",
        "sealed_table5b_results": "6b51a2a5c0a5f30ea73b1889828b89df460ffc740d069a567c129f6d135e9ca1",
        "sealed_phase25_benchmark": "6efb546839545b7d0216a909bebd6d5744d603712f96804173198056fc4a119f",
    }
    bad = {
        key: (inputs[key], expected_hash)
        for key, expected_hash in expected_inputs.items()
        if inputs[key] != expected_hash
    }
    if bad:
        raise RuntimeError(f"Phase 3 input hash mismatch: {bad}")
    return {"head": head, "protected": protected, "input_hashes": inputs}


def load_reference_components(path: pathlib.Path) -> tuple[pd.DataFrame, CORE.ComponentMoments]:
    raw = pd.read_csv(path, dtype={"census2018": str})
    required = ["census2018", "occupation", "preperiod_employment_weight", *MEASURES]
    frame = raw.dropna(subset=required).copy()
    frame["census2018"] = frame.census2018.str.zfill(4)
    weights = frame.preperiod_employment_weight.to_numpy(float)
    if len(frame) != 463 or np.any(~np.isfinite(weights)) or np.any(weights <= 0):
        raise RuntimeError("frozen six-measure component reference support changed")
    moments = CORE.fit_component_moments(frame, weights)
    components = CORE.component_arrays(frame, moments)
    for column in components:
        frame[column] = components[column].to_numpy(float)
    return frame, moments


def component_stability(frame: pd.DataFrame) -> list[dict]:
    weights = frame.preperiod_employment_weight.to_numpy(float)
    rows = []
    for measure in MEASURES:
        rows.append({
            "analysis_status": LABEL,
            "diagnostic": "correlation_with_shared_F",
            "omitted": "",
            "item": measure,
            "value": CORE.weighted_corr(frame[f"z__{measure}"], frame.F, weights),
            "occupations": len(frame),
            "note": "fixed six-measure z moments; no outcome used",
        })
    rows.extend([
        {
            "analysis_status": LABEL,
            "diagnostic": "family_correlation",
            "omitted": "",
            "item": "AIOE centroid vs Eloundou centroid",
            "value": CORE.weighted_corr(frame.A, frame.E, weights),
            "occupations": len(frame),
            "note": "equal total family weight",
        },
        {
            "analysis_status": LABEL,
            "diagnostic": "F_G_correlation",
            "omitted": "",
            "item": "F vs G",
            "value": CORE.weighted_corr(frame.F, frame.G, weights),
            "occupations": len(frame),
            "note": "descriptive weighted correlation",
        },
    ])
    for omitted in MEASURES:
        aioe = [name for name in CORE.AIOE if name != omitted]
        eloundou = [name for name in CORE.ELOUNDOU if name != omitted]
        a = frame[[f"z__{name}" for name in aioe]].mean(axis=1)
        e = frame[[f"z__{name}" for name in eloundou]].mean(axis=1)
        candidate = (a + e) / 2
        rows.append({
            "analysis_status": LABEL,
            "diagnostic": "leave_one_measure_out",
            "omitted": omitted,
            "item": "correlation with full F",
            "value": CORE.weighted_corr(candidate, frame.F, weights),
            "occupations": len(frame),
            "note": "both families retained at equal total weight",
        })
    return rows


def build_switch_frame(args: argparse.Namespace, moments: CORE.ComponentMoments):
    pairs, link = P25.PRIMARY.load_pairs(args.microdata, args.weight_patch)
    maps = P25.exposure_maps(args.lookup)
    employment = P25.preperiod_employment(args.microdata)
    major = P25.major_group_map(args.bridge, args.computerization)
    frame = P25.build_switch_universe(pairs, maps, employment, major)
    signs = frame[[f"sign__{measure}" for measure in MEASURES]].to_numpy(float)
    frame["opposite_direction_conflict"] = (
        frame.sixway_included & (np.nanmin(signs, axis=1) < 0) & (np.nanmax(signs, axis=1) > 0)
    )
    component = CORE.component_maps(maps, moments)
    hard_common = frame.loc[frame.sixway_included].copy()
    finite = pd.Series(True, index=hard_common.index)
    for endpoint in ("origin_code", "destination_code"):
        finite &= hard_common[endpoint].isin(component["F"])
    retained_weight = float(
        hard_common.loc[finite, "LNKFW1MWT"].sum() / hard_common.LNKFW1MWT.sum()
    )
    common = hard_common.loc[finite].copy()
    for name, mapping in component.items():
        common[f"d__{name}"] = common.destination_code.map(mapping) - common.origin_code.map(mapping)
    dz = common[[f"d__z__{measure}" for measure in MEASURES]].to_numpy(float)
    dr = common[[f"d__R__{measure}" for measure in MEASURES]].to_numpy(float)
    common["component_conflict"] = (np.min(dz, axis=1) < 0) & (np.max(dz, axis=1) > 0)
    common["component_unanimous"] = np.all(dz > 0, axis=1) | np.all(dz < 0, axis=1)
    if not np.array_equal(
        common.component_conflict.to_numpy(), common.opposite_direction_conflict.to_numpy()
    ):
        raise RuntimeError("positive z transformations changed frozen directional conflict")
    common["abs_dF"] = np.abs(common.d__F)
    common["abs_dG"] = np.abs(common.d__G)
    common["H"] = np.sqrt(np.mean(np.square(dr), axis=1))
    bins, cuts = CORE.tie_preserving_weighted_bins(
        common.abs_dF.to_numpy(float), common.LNKFW1MWT.to_numpy(float)
    )
    common["F_distance_bin"] = bins
    return hard_common, common, maps, link, retained_weight, cuts


def make_hard_pseudopop(frame: pd.DataFrame, maps: dict, units: int) -> dict:
    strata = ["age_group", "month", "origin_major", "destination_major"]
    cells = (
        frame.groupby([*strata, "origin_code", "destination_code"], as_index=False)
        .LNKFW1MWT.sum()
        .sort_values([*strata, "origin_code", "destination_code"], kind="mergesort")
        .reset_index(drop=True)
    )
    counts, expected = CORE.hamilton_counts(cells.LNKFW1MWT.to_numpy(float), units)
    represented = counts > 0
    represented_weight = float(cells.loc[represented, "LNKFW1MWT"].sum() / cells.LNKFW1MWT.sum())
    cells = cells.loc[represented].copy()
    cells["pseudo_count"] = counts[represented]
    cells["stratum_key"] = list(map(tuple, cells[strata].to_numpy()))
    stratum_codes, stratum_levels = pd.factorize(cells.stratum_key, sort=True)
    cells["stratum_id"] = stratum_codes
    all_codes = sorted(set(cells.origin_code) | set(cells.destination_code))
    code_index = {code: index for index, code in enumerate(all_codes)}
    order = np.argsort(cells.stratum_id.to_numpy(), kind="mergesort")
    cells = cells.iloc[order].reset_index(drop=True)
    origin = np.repeat(cells.origin_code.map(code_index).to_numpy(int), cells.pseudo_count)
    destination = np.repeat(cells.destination_code.map(code_index).to_numpy(int), cells.pseudo_count)
    groups = np.repeat(cells.stratum_id.to_numpy(int), cells.pseudo_count)
    if len(origin) != units or np.any(origin == destination):
        raise RuntimeError("hard pseudo-population does not reproduce non-self switches")
    exposure = np.column_stack([
        [maps[measure][code] for code in all_codes] for measure in MEASURES
    ])
    sign = np.sign(exposure[None, :, :] - exposure[:, None, :])
    conflict = (np.min(sign, axis=2) < 0) & (np.max(sign, axis=2) > 0)
    return {
        "origin": origin,
        "destination": destination,
        "groups": groups,
        "conflict": conflict,
        "represented_weight_share": represented_weight,
        "strata": len(stratum_levels),
        "detailed_joint_cells": len(cells),
        "max_joint_share_approximation_error": float(
            np.max(np.abs(counts / units - expected / units))
        ),
        "pseudo_realized_conflict": float(np.mean(conflict[origin, destination])),
    }


def hard_benchmark_one(frame: pd.DataFrame, maps: dict, sample: str) -> dict:
    pseudo = make_hard_pseudopop(frame, maps, PSEUDO_UNITS)
    rng = np.random.default_rng(HARD_SEEDS[sample])
    draws = np.empty(DRAWS)
    repair_counts = np.empty(DRAWS, dtype=int)
    attempts = np.empty(DRAWS, dtype=int)
    for draw in range(DRAWS):
        rematched, repairs, attempt = CORE.repair_self_matches_within_groups(
            pseudo["origin"], pseudo["destination"], pseudo["groups"], rng
        )
        draws[draw] = np.mean(pseudo["conflict"][pseudo["origin"], rematched])
        repair_counts[draw] = repairs
        attempts[draw] = attempt
    realized = float(np.average(frame.opposite_direction_conflict, weights=frame.LNKFW1MWT))
    mean = float(draws.mean())
    p975 = float(np.quantile(draws, 0.975))
    gap = realized - mean
    classification = CORE.classify_hard_benchmark(
        gap, realized, p975, pseudo["represented_weight_share"]
    )
    return {
        "analysis_status": LABEL,
        "sample": sample,
        "seed": HARD_SEEDS[sample],
        "draws": DRAWS,
        "pseudo_units": PSEUDO_UNITS,
        "stratum": "age_group x calendar month x origin broad family x destination broad family",
        "realized_conflict_official_weight": realized,
        "realized_conflict_pseudo_approximation": pseudo["pseudo_realized_conflict"],
        "hard_benchmark_mean": mean,
        "hard_benchmark_sd": float(draws.std(ddof=1)),
        "hard_benchmark_p025": float(np.quantile(draws, 0.025)),
        "hard_benchmark_p975": p975,
        "realized_minus_hard_mean": gap,
        "empirical_upper_tail_probability": float(
            (1 + np.sum(draws >= realized)) / (DRAWS + 1)
        ),
        "classification": classification,
        "represented_official_weight_share": pseudo["represented_weight_share"],
        "strata": pseudo["strata"],
        "detailed_joint_cells": pseudo["detailed_joint_cells"],
        "max_joint_share_approximation_error": pseudo["max_joint_share_approximation_error"],
        "maximum_self_match_repairs": int(repair_counts.max()),
        "maximum_repair_attempts": int(attempts.max()),
        "false_self_switches_after_repair": 0,
        "benchmark_draws": draws.tolist(),
    }


def summarize_switch_components(
    frame: pd.DataFrame, cuts: np.ndarray
) -> tuple[list[dict], dict]:
    rows: list[dict] = []

    def add_group(sample: str, group: str, value: str, selected: pd.DataFrame) -> None:
        if selected.empty:
            return
        w = selected.LNKFW1MWT.to_numpy(float)
        rows.append({
            "analysis_status": LABEL,
            "section": group,
            "sample": sample,
            "pair": "all_six",
            "bin_or_group": value,
            "switches_raw": len(selected),
            "weight_sum": float(w.sum()),
            "conflict_rate": CORE.weighted_mean(selected.component_conflict, w),
            "mean_abs_dF": CORE.weighted_mean(selected.abs_dF, w),
            "median_abs_dF": CORE.weighted_median(selected.abs_dF, w),
            "mean_abs_dG": CORE.weighted_mean(selected.abs_dG, w),
            "median_abs_dG": CORE.weighted_median(selected.abs_dG, w),
            "mean_H": CORE.weighted_mean(selected.H, w),
            "median_H": CORE.weighted_median(selected.H, w),
            "share_abs_dG_gt_abs_dF": CORE.weighted_mean(selected.abs_dG.gt(selected.abs_dF), w),
            "share_H_gt_abs_dF": CORE.weighted_mean(selected.H.gt(selected.abs_dF), w),
            "pair_residual_median": "",
        })

    samples = {"primary": frame, "persistent": frame.loc[frame.persistent].copy()}
    for sample, selected in samples.items():
        if sample == "persistent":
            selected["F_distance_bin"] = np.searchsorted(
                cuts, selected.abs_dF.to_numpy(float), side="left"
            ) + 1
        for bin_number in range(1, 6):
            add_group(sample, "F_distance_bin", str(bin_number), selected.loc[selected.F_distance_bin.eq(bin_number)])
        add_group(sample, "direction_group", "conflict", selected.loc[selected.component_conflict])
        add_group(sample, "direction_group", "unanimous", selected.loc[selected.component_unanimous])

    for left, right in itertools.combinations(MEASURES, 2):
        sign_left = np.sign(frame[f"d__z__{left}"])
        sign_right = np.sign(frame[f"d__z__{right}"])
        comparable = sign_left.ne(0) & sign_right.ne(0)
        pair_conflict = sign_left.mul(sign_right).lt(0)
        pair_h = np.abs(frame[f"d__R__{left}"] - frame[f"d__R__{right}"]) / 2
        for bin_number in range(1, 6):
            mask = comparable & frame.F_distance_bin.eq(bin_number)
            selected = frame.loc[mask]
            w = selected.LNKFW1MWT.to_numpy(float)
            rows.append({
                "analysis_status": LABEL,
                "section": "pair_by_F_distance_bin",
                "sample": "primary",
                "pair": f"{left}__{right}",
                "bin_or_group": str(bin_number),
                "switches_raw": len(selected),
                "weight_sum": float(w.sum()),
                "conflict_rate": CORE.weighted_mean(pair_conflict.loc[mask], w),
                "mean_abs_dF": CORE.weighted_mean(selected.abs_dF, w),
                "median_abs_dF": CORE.weighted_median(selected.abs_dF, w),
                "mean_abs_dG": CORE.weighted_mean(selected.abs_dG, w),
                "median_abs_dG": CORE.weighted_median(selected.abs_dG, w),
                "mean_H": CORE.weighted_mean(selected.H, w),
                "median_H": CORE.weighted_median(selected.H, w),
                "share_abs_dG_gt_abs_dF": CORE.weighted_mean(selected.abs_dG.gt(selected.abs_dF), w),
                "share_H_gt_abs_dF": CORE.weighted_mean(selected.H.gt(selected.abs_dF), w),
                "pair_residual_median": CORE.weighted_median(pair_h.loc[mask], w),
            })

    result = pd.DataFrame(rows)
    f_rows = result.loc[
        result.section.eq("F_distance_bin") & result.pair.eq("all_six")
    ]
    primary = f_rows.loc[f_rows["sample"].eq("primary")].set_index("bin_or_group")
    persistent = f_rows.loc[f_rows["sample"].eq("persistent")].set_index("bin_or_group")
    direction = result.loc[
        result.section.eq("direction_group") & result.sample.eq("primary")
    ].set_index("bin_or_group")
    low_high = float(primary.loc["1", "conflict_rate"] - primary.loc["5", "conflict_rate"])
    persistent_low_high = float(
        persistent.loc["1", "conflict_rate"] - persistent.loc["5", "conflict_rate"]
    )
    h_ratio = float(direction.loc["conflict", "median_H"] / direction.loc["unanimous", "median_H"])
    summary = {
        "analysis_status": LABEL,
        "weighted_abs_dF_cuts": cuts.tolist(),
        "primary_lowest_minus_highest_F_bin_conflict": low_high,
        "persistent_lowest_minus_highest_F_bin_conflict": persistent_low_high,
        "conflict_to_unanimous_median_H_ratio": h_ratio,
        "classification": CORE.classify_reallocation_component(low_high, h_ratio, persistent_low_high),
    }
    return rows, summary


def stock_and_joint(
    args: argparse.Namespace,
    reference: pd.DataFrame,
) -> tuple[dict, list[dict], dict, list[dict], list[dict], list[dict]]:
    data = V4.load_inputs(args)
    webb = data["computers"]["webb_pct_software"]
    base = sorted(data["occupations"])
    supports = {
        measure: V4.finite_support(base, data["exposures"][measure]["A"], webb)
        for measure in MEASURES
    }
    common = sorted(set.intersection(*(set(value) for value in supports.values())))
    if len(common) != 444 or support_hash(common) != "1e184b27678b7978d4b15e618db5b44f44b5e9ec1b50b69b53093ec62e0ce462":
        raise RuntimeError("literal six-architecture stock support changed")
    f_map = dict(zip(reference.census2018, reference.F))
    if any(code not in f_map or not np.isfinite(f_map[code]) for code in common):
        raise RuntimeError("shared F is not finite on the frozen 444-occupation support")

    prepared_f = FROZEN.prepare_model(
        data["panel"], common, data["static_months"], f_map, webb, scale="q5_q1"
    )
    if prepared_f["occupations"] != common:
        raise RuntimeError("shared-F stock estimator changed literal common support")
    fit_f, influence_f = FROZEN.fit_with_influence(
        prepared_f["young"], prepared_f["older"], prepared_f["regressors"]
    )
    f_summary, _, _ = FROZEN.bootstrap_summary(
        fit_f, influence_f, prepared_f["target"], STOCK_SEED
    )
    f_values = np.array([f_map[code] for code in common], float)
    f_quintiles = FROZEN.weighted_quintiles(f_values, prepared_f["weights"])
    f_q1 = {code for code, q in zip(common, f_quintiles) if q == 1}
    f_q5 = {code for code, q in zip(common, f_quintiles) if q == 5}
    overlap_rows = []
    membership_rows = []
    for code, q, value in zip(common, f_quintiles, f_values):
        membership_rows.append({
            "analysis_status": LABEL,
            "occupation_code": code,
            "occupation_name": data["names"].get(code, code),
            "shared_F": value,
            "shared_F_quintile": int(q),
            "is_q1": bool(q == 1),
            "is_q5": bool(q == 5),
        })
    for measure in MEASURES:
        values = np.array([data["exposures"][measure]["A"][code] for code in common], float)
        q = FROZEN.weighted_quintiles(values, prepared_f["weights"])
        q1 = {code for code, value in zip(common, q) if value == 1}
        q5 = {code for code, value in zip(common, q) if value == 5}
        overlap_rows.append({
            "analysis_status": LABEL,
            "measure": measure,
            "F_Q1_count": len(f_q1),
            "measure_Q1_count": len(q1),
            "Q1_jaccard": len(f_q1 & q1) / len(f_q1 | q1),
            "F_Q5_count": len(f_q5),
            "measure_Q5_count": len(q5),
            "Q5_jaccard": len(f_q5 & q5) / len(f_q5 | q5),
        })
    base_weight = V4.occupation_weights(data["panel"], base, data["static_months"]).sum()
    common_weight = prepared_f["weights"].sum()
    stock_result = {
        "analysis_status": LABEL,
        "record": "exactly one authorized new Phase 3 employment-stock model",
        "treatment": "shared family component F employment-weighted quintiles; Q1 omitted; Q2-Q5 separate",
        "comparison_technology": "Webb software exposure standardized on the same support",
        "coefficient_log_points": f_summary["coefficient"],
        "analytic_occupation_cluster_se": f_summary["analytic_cluster_se"],
        "wild_score_p_value": f_summary["bootstrap_p_value"],
        "wild_score_ci_lower": f_summary["ci_lower"],
        "wild_score_ci_upper": f_summary["ci_upper"],
        "wild_score_draws": DRAWS,
        "wild_score_seed": STOCK_SEED,
        "transformed_percent": 100 * math.expm1(f_summary["coefficient"]),
        "occupations": len(common),
        "support_hash_sha256": support_hash(common),
        "employment_support_share": float(common_weight / base_weight),
        "q1_occupation_count": len(f_q1),
        "q5_occupation_count": len(f_q5),
        "q1_hash_sha256": support_hash(sorted(f_q1)),
        "q5_hash_sha256": support_hash(sorted(f_q5)),
        "quintile_weighting": "young-plus-older stocks over 108 static estimation months; December 2022 excluded",
        "classification": CORE.classify_shared_stock(f_summary["coefficient"], f_summary["ci_upper"]),
    }

    sealed = pd.read_csv(args.table5b_results).set_index("measure")
    estimates, ses, influence_columns, joint_rows = [], [], [], []
    for measure in MEASURES:
        prepared = FROZEN.prepare_model(
            data["panel"], common, data["static_months"],
            data["exposures"][measure]["A"], webb, scale="q5_q1"
        )
        fit, influence = FROZEN.fit_with_influence(
            prepared["young"], prepared["older"], prepared["regressors"]
        )
        target = prepared["target"]
        estimate = float(fit.beta[target])
        expected = float(sealed.loc[measure, "coefficient_log_points"])
        if not np.isclose(estimate, expected, atol=1e-10, rtol=0):
            raise RuntimeError(f"joint-inference point estimate changed for {measure}: {estimate} != {expected}")
        estimates.append(estimate)
        ses.append(float(fit.standard_error[target]))
        influence_columns.append(influence[:, target])
    influence_matrix = np.column_stack(influence_columns)
    rng = np.random.default_rng(JOINT_SEED)
    multipliers = rng.choice(np.array([-1.0, 1.0]), size=(DRAWS, len(common)))
    shifts = multipliers @ influence_matrix
    inference = CORE.simultaneous_one_sided_upper_bounds(
        np.array(estimates), np.array(ses), shifts
    )
    covariance = np.cov(shifts, rowvar=False, ddof=1)
    for index, measure in enumerate(MEASURES):
        joint_rows.append({
            "analysis_status": LABEL,
            "measure": measure,
            "coefficient_log_points": estimates[index],
            "analytic_occupation_cluster_se": ses[index],
            "simultaneous_one_sided_upper_95": float(inference["upper_bounds"][index]),
            "marginal_one_sided_tail_area": float(inference["marginal_one_sided_p"][index]),
            "upper_bound_below_zero": bool(inference["upper_bounds"][index] < 0),
        })
    covariance_rows = []
    for i, left in enumerate(MEASURES):
        for j, right in enumerate(MEASURES):
            covariance_rows.append({
                "analysis_status": LABEL,
                "measure_1": left,
                "measure_2": right,
                "centered_shift_covariance": float(covariance[i, j]),
            })
    joint_result = {
        "analysis_status": LABEL,
        "record": "joint sign inference for six frozen literal-common-support parameters",
        "joint_null": "at least one architecture-specific coefficient is nonnegative",
        "joint_alternative": "all six architecture-specific coefficients are negative",
        "common_support_occupations": len(common),
        "common_support_hash_sha256": support_hash(common),
        "draws": DRAWS,
        "seed": JOINT_SEED,
        "common_cluster_multipliers": True,
        "simultaneous_one_sided_critical": inference["critical"],
        "intersection_union_p": inference["intersection_union_p"],
        "all_simultaneous_upper_bounds_negative": inference["all_upper_bounds_negative"],
        "joint_all_negative_statement_supported": inference["all_upper_bounds_negative"],
        "point_estimates_verified_against_sealed_table5b": True,
        "point_estimate_tolerance": 1e-10,
        "common_parameter_assumption": False,
    }
    return stock_result, membership_rows, joint_result, joint_rows, covariance_rows, overlap_rows


def run(args: argparse.Namespace) -> dict:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    auth = authenticate(args)
    reference, moments = load_reference_components(args.characteristics)
    definition_path = args.output_dir / "YAX_PHASE3_SHARED_COMPONENT_VALUES.csv"
    reference[[
        "census2018", "occupation", "preperiod_employment_weight", *MEASURES,
        *[f"z__{measure}" for measure in MEASURES], "A", "E", "F", "G",
        *[f"R__{measure}" for measure in MEASURES],
    ]].to_csv(definition_path, index=False)
    stability_path = args.output_dir / "YAX_PHASE3_SHARED_COMPONENT_STABILITY.csv"
    write_csv(stability_path, component_stability(reference))

    hard_switches, switches, maps, link, component_retention, cuts = build_switch_frame(args, moments)
    primary_hard = hard_benchmark_one(hard_switches, maps, "primary")
    persistent_hard = hard_benchmark_one(
        hard_switches.loc[hard_switches.persistent].copy(), maps, "persistent"
    )
    old_benchmark = json.loads(args.phase25_benchmark.read_text())
    hard_result = {
        "analysis_status": LABEL,
        "record": "YAX Phase 3 hard reallocation benchmark",
        "current_marginal_benchmark": {
            "realized_conflict": old_benchmark["primary"]["realized_conflict_official_weight"],
            "benchmark_mean": old_benchmark["primary"]["benchmark_mean"],
            "realized_minus_benchmark_mean": old_benchmark["primary"]["realized_minus_benchmark_mean"],
        },
        "primary_hard_benchmark": primary_hard,
        "persistent_hard_benchmark": persistent_hard,
        "fallback_used": False,
        "tail_area_interpretation": "descriptive constrained-rematching reference; not a conventional sampling p-value or causal test",
    }
    hard_path = args.output_dir / "YAX_PHASE3_HARD_BENCHMARK_RESULTS.json"
    write_json(hard_path, hard_result)

    component_rows, component_summary = summarize_switch_components(switches, cuts)
    component_summary.update({
        "switches": len(switches),
        "official_weight_retained_from_sixway_support": component_retention,
        "persistence_switches": int(switches.persistent.sum()),
    })
    realloc_csv = args.output_dir / "YAX_PHASE3_REALLOCATION_COMPONENT_RESULTS.csv"
    realloc_json = args.output_dir / "YAX_PHASE3_REALLOCATION_COMPONENT_RESULTS.json"
    write_csv(realloc_csv, component_rows)
    write_json(realloc_json, component_summary)

    stock, membership, joint, joint_rows, covariance_rows, overlap = stock_and_joint(args, reference)
    stock_path = args.output_dir / "YAX_PHASE3_SHARED_STOCK_RESULT.json"
    stock_membership_path = args.output_dir / "YAX_PHASE3_SHARED_STOCK_MEMBERSHIP.csv"
    overlap_path = args.output_dir / "YAX_PHASE3_SHARED_STOCK_OVERLAP.csv"
    write_json(stock_path, stock)
    write_csv(stock_membership_path, membership)
    write_csv(overlap_path, overlap)
    joint_path = args.output_dir / "YAX_PHASE3_JOINT_SIGN_INFERENCE.json"
    joint_csv = args.output_dir / "YAX_PHASE3_JOINT_SIGN_INFERENCE.csv"
    covariance_path = args.output_dir / "YAX_PHASE3_JOINT_SIGN_COVARIANCE.csv"
    write_json(joint_path, joint)
    write_csv(joint_csv, joint_rows)
    write_csv(covariance_path, covariance_rows)

    result_classes = {
        "hard_benchmark": primary_hard["classification"],
        "reallocation_component": component_summary["classification"],
        "shared_stock": stock["classification"],
    }
    result_classes["phase3_path"] = CORE.select_phase3_path(
        result_classes["hard_benchmark"],
        result_classes["reallocation_component"],
        result_classes["shared_stock"],
    )
    outputs = [
        definition_path, stability_path, hard_path, realloc_csv, realloc_json,
        stock_path, stock_membership_path, overlap_path, joint_path, joint_csv,
        covariance_path,
    ]
    execution = {
        "record": "YAX Phase 3 execution receipt before manuscript assembly",
        "analysis_status": LABEL,
        "generated_at_utc": now(),
        "pre_result_commit": args.pre_result_commit,
        "execution_head": auth["head"],
        "protected_peeled_commits": auth["protected"],
        "input_hashes": auth["input_hashes"],
        "seeds": {"hard_primary": HARD_SEEDS["primary"], "hard_persistent": HARD_SEEDS["persistent"], "stock": STOCK_SEED, "joint": JOINT_SEED},
        "hard_benchmark_draws": DRAWS,
        "hard_benchmark_pseudo_units": PSEUDO_UNITS,
        "stock_wild_score_draws": DRAWS,
        "joint_multiplier_draws": DRAWS,
        "new_labor_outcome_models": ["shared_F_Q2_Q5_with_Q1_omitted_and_Webb"],
        "new_labor_outcome_model_count": 1,
        "joint_inference_reconstructs_existing_six_point_estimates": True,
        "result_classifications": result_classes,
        "link_sample": link,
        "artifact_hashes": {path.name: sha256(path) for path in outputs},
    }
    receipt_path = args.output_dir / "YAX_PHASE3_EXECUTION_RECEIPT.json"
    write_json(receipt_path, execution)
    print(json.dumps({
        "classifications": result_classes,
        "hard_gap": primary_hard["realized_minus_hard_mean"],
        "component_low_high": component_summary["primary_lowest_minus_highest_F_bin_conflict"],
        "shared_stock_coefficient": stock["coefficient_log_points"],
        "joint_all_negative": joint["joint_all_negative_statement_supported"],
    }, indent=2))
    return execution


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--pre-result-commit", required=True)
    value.add_argument("--microdata", type=pathlib.Path, required=True)
    value.add_argument("--weight-patch", type=pathlib.Path, required=True)
    value.add_argument("--preperiod-cells", type=pathlib.Path, required=True)
    value.add_argument("--lookup", type=pathlib.Path, default=ROOT / "yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv")
    value.add_argument("--computerization", type=pathlib.Path, default=ROOT / "yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv")
    value.add_argument("--bridge", type=pathlib.Path, default=ROOT / "yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv")
    value.add_argument("--rule-b-values", type=pathlib.Path, default=ROOT / "yax/measurement/RULE_B_VALUES_CENSUS2018.csv")
    value.add_argument("--first-access-receipt", type=pathlib.Path, default=ROOT / "yax/analysis/FIRST_OUTCOME_ACCESS_RECEIPT.json")
    value.add_argument("--characteristics", type=pathlib.Path, default=ROOT / "yax/measurement/test_a/TEST_A_OCCUPATION_CHARACTERISTICS.csv")
    value.add_argument("--table5b-results", type=pathlib.Path, default=ROOT / "yax/analysis/postoutcome_v4_supplementary/TABLE5B_COMMON_SUPPORT_RESULTS.csv")
    value.add_argument("--phase25-benchmark", type=pathlib.Path, default=ROOT / "yax/analysis/postoutcome_phase25_gate3/YAX_PHASE25_REALIZED_VS_MATCHED_BENCHMARK.json")
    value.add_argument("--output-dir", type=pathlib.Path, default=HERE)
    return value


def main() -> int:
    run(parser().parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
