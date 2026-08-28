#!/usr/bin/env python3
"""Outcome-blind paired precision for YAX Test C.

The only comparison executed here is the comparison explicitly frozen in
DESIGN_FREEZE_v1: Eloundou GPT-4 beta (primary) versus GPT-4 alpha (the named
pre-specified contrast). Both models use the same occupations, synthetic
outcomes and Rademacher/donor draws. No protected post-period outcome is read.

The script deliberately does not invent a numerical SESOI. It will calculate
the paired Delta distribution and difference-detection precision when the
literature benchmark is unresolved, but it leaves equivalence power null and
the gate blocked. A numerical benchmark may be supplied only if its receipt
establishes the same age band, stock outcome, Q5-Q1 contrast, pooled older
comparison, estimand and functional scale.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import pathlib
import sys

import numpy as np
import pandas as pd


ROOT = pathlib.Path(__file__).resolve().parents[2]
ENGINE_PATH = ROOT / "dax" / "memo" / "power_calcs" / "young_relative_employment_power.py"
SPEC = importlib.util.spec_from_file_location("young_relative_employment_power", ENGINE_PATH)
ENGINE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ENGINE
SPEC.loader.exec_module(ENGINE)

LOOKUP_ROLE = "raw_occ_main_2020_plus"
PRE_END = "2022-11"
POST_START = "2023-01"
POST_END = "2026-07"
POST_GAPS = {"2025-10"}
PRIMARY = "dv_rating_beta"
CONTRAST = "dv_rating_alpha"
PRIMARY_COMPUTERIZATION = "webb_pct_software"
DEFAULT_BETA_C = math.log(0.95)


def sha256(path):
    digest = hashlib.sha256()
    with pathlib.Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def post_months():
    result = []
    for year in range(int(POST_START[:4]), int(POST_END[:4]) + 1):
        for month in range(1, 13):
            value = "%04d-%02d" % (year, month)
            if POST_START <= value <= POST_END and value not in POST_GAPS:
                result.append(value)
    return result


def read_lookup(path, measures):
    result = {}
    with pathlib.Path(path).open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if row["lookup_role"] != LOOKUP_ROLE:
                continue
            if not all(row.get(measure) not in (None, "") for measure in measures):
                continue
            result[row["occ_code"].zfill(4)] = {
                measure: float(row[measure]) for measure in measures
            }
    return result


def read_computerization(path, measure):
    result = {}
    with pathlib.Path(path).open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if row.get(measure) not in (None, ""):
                result[row["census2018"].zfill(4)] = float(row[measure])
    return result


def validate_receipts(cells, cells_receipt, lookup, lookup_receipt,
                      computerization, computerization_receipt):
    cell_record = json.loads(pathlib.Path(cells_receipt).read_text(encoding="utf-8"))
    if cell_record.get("post_outcomes_read") is not False:
        raise ValueError("cells receipt does not preserve the outcome seal")
    if (cell_record.get("source_seal", {}).get("audited_split_status")
            != "PASS_OUTCOME_BLIND_PREPERIOD_SPLIT"):
        raise ValueError("cells receipt lacks the audited pre-period split")
    if cell_record.get("cells_sha256") != sha256(cells):
        raise ValueError("cells hash does not match receipt")
    if cell_record.get("lookup_sha256") != sha256(lookup):
        raise ValueError("cells receipt does not authenticate this exposure lookup")

    lookup_record = json.loads(pathlib.Path(lookup_receipt).read_text(encoding="utf-8"))
    outputs = lookup_record.get("outputs", {})
    expected_lookup = next((value.get("sha256") for key, value in outputs.items()
                            if key.endswith("CPS_OCCUPATION_EXPOSURE_LOOKUP.csv")), None)
    if lookup_record.get("status") != "PASS" or expected_lookup != sha256(lookup):
        raise ValueError("exposure lookup receipt is not PASS for this file")

    comp_record = json.loads(
        pathlib.Path(computerization_receipt).read_text(encoding="utf-8")
    )
    expected_comp = comp_record.get("census2018_output", {}).get("sha256")
    if comp_record.get("status") != "PASS" or expected_comp != sha256(computerization):
        raise ValueError("computerization receipt is not PASS for this file")
    return cell_record, lookup_record, comp_record


def weighted_quintiles(values, weights):
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    if (len(values) == 0 or np.any(weights <= 0)
            or np.any(~np.isfinite(values + weights))):
        raise ValueError("invalid weighted quintile inputs")
    order = np.argsort(values, kind="mergesort")
    sorted_values, sorted_weights = values[order], weights[order]
    cumulative = np.cumsum(sorted_weights)
    total = float(cumulative[-1])
    if total <= 0:
        raise ValueError("nonpositive employment weight")
    cuts = np.asarray([
        sorted_values[min(np.searchsorted(cumulative, share * total, side="left"),
                          len(values) - 1)]
        for share in (0.2, 0.4, 0.6, 0.8)
    ])
    if np.any(cuts[:-1] >= cuts[1:]):
        raise ValueError("employment-weighted exposure quintile cuts are not distinct")
    # This is the frozen CPS-builder rule: equal scores remain in the same bin.
    return np.searchsorted(cuts, values, side="left") + 1


def design(quintile, comp_z, post):
    columns = [
        ((quintile[:, None] == value) & post[None, :]).reshape(-1).astype(float)
        for value in (2, 3, 4, 5)
    ]
    columns.append((comp_z[:, None] * post[None, :]).reshape(-1))
    return np.column_stack(columns)


def prepare(cells_path, lookup_path, computerization_path):
    cells = pd.read_csv(cells_path)
    required = {"month", "lookup_role", "occ_code", "age_group", "employment_headcount"}
    missing = required - set(cells.columns)
    if missing:
        raise ValueError("cells missing %s" % sorted(missing))
    if str(cells["month"].max()) > PRE_END:
        raise ValueError("protected post-period outcome detected")
    cells = cells.loc[cells["lookup_role"] == LOOKUP_ROLE].copy()
    cells["occ_code"] = cells["occ_code"].astype(str).str.zfill(4)
    pivot = cells.pivot_table(
        index=["occ_code", "month"], columns="age_group",
        values="employment_headcount", aggfunc="sum", fill_value=0.0,
    )
    months = sorted(cells["month"].astype(str).unique())
    occupations = sorted(cells["occ_code"].unique())
    index = pd.MultiIndex.from_product([occupations, months], names=["occ_code", "month"])
    pivot = pivot.reindex(index, fill_value=0.0)
    for age in ("young_22_25", "older_26_65"):
        if age not in pivot:
            pivot[age] = 0.0
    totals = pivot.groupby(level="occ_code")[["young_22_25", "older_26_65"]].sum()
    balanced = totals.index[(totals > 0).all(axis=1)].astype(str).tolist()
    if len(balanced) != 490:
        raise ValueError("expected 490 balanced clusters, got %d" % len(balanced))
    lookup = read_lookup(lookup_path, (PRIMARY, CONTRAST))
    comp = read_computerization(computerization_path, PRIMARY_COMPUTERIZATION)
    support = [code for code in balanced if code in lookup and code in comp]
    if len(support) < 30:
        raise ValueError("fewer than 30 common-support occupations")
    selected = pivot.loc[(support, slice(None)), :]
    young = selected["young_22_25"].to_numpy().reshape(len(support), len(months))
    older = selected["older_26_65"].to_numpy().reshape(len(support), len(months))
    weights = (young + older).sum(axis=1)
    comp_values = np.asarray([comp[code] for code in support], dtype=float)
    comp_mean = float(np.sum(weights * comp_values) / np.sum(weights))
    comp_sd = float(np.sqrt(np.sum(weights * np.square(comp_values - comp_mean)) / np.sum(weights)))
    if comp_sd <= 0:
        raise ValueError("computerization has zero variance")
    quintiles = {}
    for measure in (PRIMARY, CONTRAST):
        values = np.asarray([lookup[code][measure] for code in support], dtype=float)
        quintiles[measure] = weighted_quintiles(values, weights)
        if set(quintiles[measure]) != {1, 2, 3, 4, 5}:
            raise ValueError("all five quintiles must survive for %s" % measure)
    return {
        "occupations": support,
        "months": months,
        "young": young,
        "older": older,
        "weights": weights,
        "comp_z": (comp_values - comp_mean) / comp_sd,
        "quintiles": quintiles,
        "comp_scale": {"mean": comp_mean, "sd": comp_sd},
        "balanced_clusters": len(balanced),
    }


def fit_preperiod(prepared):
    young = prepared["young"]
    total = young + prepared["older"]
    n_occ, n_pre = young.shape
    fit = ENGINE.fit_grouped_logit_fe(
        young.reshape(-1), total.reshape(-1),
        np.repeat(np.arange(n_occ), n_pre), np.tile(np.arange(n_pre), n_occ),
        np.empty((n_occ * n_pre, 0)),
    )
    if not fit.converged:
        raise RuntimeError("pre-period FE fit did not converge")
    return {
        "total": total,
        "fitted": (fit.fitted_probability * total.reshape(-1)).reshape(n_occ, n_pre),
        "residual": fit.residual.reshape(n_occ, n_pre),
    }


def simulate_pairs(prepared, prefit, repetitions, seed, beta_c):
    rng = np.random.default_rng(seed)
    n_occ, n_pre = prefit["total"].shape
    target_months = prepared["months"] + post_months()
    n_month = len(target_months)
    post = np.asarray([month >= POST_START for month in target_months], dtype=bool)
    regressors = {
        measure: design(prepared["quintiles"][measure], prepared["comp_z"], post)
        for measure in (PRIMARY, CONTRAST)
    }
    occupation = np.repeat(np.arange(n_occ), n_month)
    month = np.tile(np.arange(n_month), n_occ)
    estimates = {PRIMARY: [], CONTRAST: []}
    deltas = []
    failures = 0
    attempts = 0
    while len(deltas) < repetitions and attempts < repetitions * 3:
        attempts += 1
        offset = int(rng.integers(0, n_pre))
        donors = (np.arange(n_month) + offset) % n_pre
        total = prefit["total"][:, donors]
        signs = rng.choice(np.asarray([-1.0, 1.0]), size=n_occ)
        young_null = prefit["fitted"][:, donors] + signs[:, None] * prefit["residual"][:, donors]
        probability = np.divide(young_null, total, out=np.full_like(young_null, 0.5), where=total > 0)
        probability = np.clip(probability, 1e-9, 1 - 1e-9)
        shift = beta_c * prepared["comp_z"][:, None] * post[None, :]
        simulated = total * ENGINE._sigmoid(np.log(probability / (1 - probability)) + shift)
        pair = {}
        valid = True
        for measure in (PRIMARY, CONTRAST):
            fit = ENGINE.fit_grouped_logit_fe(
                simulated.reshape(-1), total.reshape(-1), occupation, month,
                regressors[measure],
            )
            if not fit.converged or not np.isfinite(fit.beta[3]):
                valid = False
                break
            pair[measure] = float(fit.beta[3])
        if not valid:
            failures += 1
            continue
        estimates[PRIMARY].append(pair[PRIMARY])
        estimates[CONTRAST].append(pair[CONTRAST])
        deltas.append(pair[PRIMARY] - pair[CONTRAST])
    if len(deltas) < repetitions:
        raise RuntimeError("only %d successful paired draws" % len(deltas))
    return {
        "beta_primary": np.asarray(estimates[PRIMARY]),
        "beta_contrast": np.asarray(estimates[CONTRAST]),
        "delta": np.asarray(deltas),
        "failures": failures,
        "attempts": attempts,
        "target_months": target_months,
    }


def quantile_higher(values, probability):
    try:
        return float(np.quantile(values, probability, method="higher"))
    except TypeError:  # NumPy < 1.22 on SCC
        return float(np.quantile(values, probability, interpolation="higher"))


def difference_mde80(delta, critical):
    centered = delta - float(np.mean(delta))
    low, high = 0.0, max(0.01, 4 * float(np.std(centered, ddof=1)))
    while float(np.mean(np.abs(centered + high) > critical)) < 0.80:
        high *= 2
    for _ in range(80):
        mid = (low + high) / 2
        if float(np.mean(np.abs(centered + mid) > critical)) >= 0.80:
            high = mid
        else:
            low = mid
    return high


def equivalence_power(delta, critical, margin):
    centered = delta - float(np.mean(delta))
    return float(np.mean(
        (centered - critical > -margin) & (centered + critical < margin)
    ))


def run(args):
    validate_receipts(
        args.cells, args.cells_receipt, args.lookup, args.lookup_receipt,
        args.computerization, args.computerization_receipt,
    )
    prepared = prepare(args.cells, args.lookup, args.computerization)
    draws = simulate_pairs(prepared, fit_preperiod(prepared), args.repetitions,
                           args.seed, args.beta_c)
    delta = draws["delta"]
    delta_centered = delta - float(np.mean(delta))
    critical = quantile_higher(np.abs(delta_centered), 0.95)
    mde = difference_mde80(delta, critical)

    benchmark = args.benchmark
    benchmark_status = "FINAL_COMMON_SCALE" if benchmark is not None else "BLOCKED_NO_COMMON_SCALE_BENCHMARK"
    primary_margin = None if benchmark is None else 0.25 * abs(benchmark)
    grid = []
    for fraction in (0.125, 0.25, 0.50):
        margin = None if benchmark is None else fraction * abs(benchmark)
        grid.append({
            "benchmark_fraction": fraction,
            "margin_log_points": margin,
            "equivalence_power_at_delta_zero": (
                None if margin is None else equivalence_power(delta, critical, margin)
            ),
            "diagnostic_only": fraction != 0.25,
        })
    return {
        "record_version": "yax-paired-equivalence-power-v1",
        "status": "BLOCKED_BENCHMARK" if benchmark is None else "PASS_SIMULATION_COMPLETE",
        "post_outcomes_read": False,
        "synthetic_post_constructed_only_from_preperiod_donors": True,
        "comparison_scope": {
            "status": "EXPLICITLY_FROZEN_PAIR_ONLY",
            "primary": PRIMARY,
            "contrast": CONTRAST,
            "delta_definition": "Q5minusQ1_beta_primary - Q5minusQ1_beta_contrast",
            "note": "v5 does not enumerate any additional direct pairs; none are invented here"
        },
        "design": {
            "age_groups": ["young_22_25", "older_26_65"],
            "outcome": "occupation-age-group-month employment stock",
            "post_start": POST_START,
            "transition_excluded": "2022-12",
            "post_end": POST_END,
            "computerization_control": PRIMARY_COMPUTERIZATION,
            "beta_c": args.beta_c,
            "q5_q1_definition": "employment-weighted quintiles on pairwise common occupation support; Q5 coefficient relative to Q1 with Q2-Q4 separately absorbed"
        },
        "inputs": {
            "cells": {"path": str(args.cells), "sha256": sha256(args.cells)},
            "cells_receipt": {"path": str(args.cells_receipt), "sha256": sha256(args.cells_receipt)},
            "lookup": {"path": str(args.lookup), "sha256": sha256(args.lookup)},
            "lookup_receipt": {"path": str(args.lookup_receipt), "sha256": sha256(args.lookup_receipt)},
            "computerization": {"path": str(args.computerization), "sha256": sha256(args.computerization)},
            "computerization_receipt": {"path": str(args.computerization_receipt), "sha256": sha256(args.computerization_receipt)}
        },
        "occupation_clusters": len(prepared["occupations"]),
        "balanced_clusters_before_overlap": prepared["balanced_clusters"],
        "preperiod_months": len(prepared["months"]),
        "synthetic_post_months": len(post_months()),
        "seed": args.seed,
        "paired_draws": args.repetitions,
        "paired_failures": draws["failures"],
        "paired_attempts": draws["attempts"],
        "paired_delta_distribution": [float(value) for value in delta],
        "paired_delta_se": float(np.std(delta, ddof=1)),
        "paired_covariance_beta_primary_beta_contrast": float(np.cov(
            draws["beta_primary"], draws["beta_contrast"], ddof=1
        )[0, 1]),
        "paired_delta_mean_null": float(np.mean(delta)),
        "paired_95_critical_halfwidth_log_points": critical,
        "benchmark": {
            "status": benchmark_status,
            "value_log_points": benchmark,
            "required_match_dimensions": [
                "age 22-25", "employment stock", "Q5-Q1", "young relative to pooled age 26-65",
                "occupation-age-month estimand", "log/PPML functional scale"
            ],
            "rejected_shortcuts": {
                "BCC_19_percent": "top-two versus bottom-three descriptive kept-pace shortfall",
                "BCC_minus_0_179": "Q5-Q1 long difference for age 22-25 only; no pooled 26-65 relative estimand"
            }
        },
        "primary_equivalence_interval": (
            None if primary_margin is None else [-primary_margin, primary_margin]
        ),
        "equivalence_power_at_delta_zero_primary_sesoi": (
            None if primary_margin is None else equivalence_power(delta, critical, primary_margin)
        ),
        "benchmark_margin_grid": grid,
        "mde_delta_80_log_points": mde,
        "mde_delta_80_relative_magnitude": math.exp(mde) - 1,
        "interpretation": (
            "Paired precision is measured, but equivalence feasibility is not identified until "
            "a benchmark on the signed-off common estimand is supplied. The SESOI is not widened."
        )
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells", type=pathlib.Path, required=True)
    parser.add_argument("--cells-receipt", type=pathlib.Path, required=True)
    parser.add_argument("--lookup", type=pathlib.Path, required=True)
    parser.add_argument("--lookup-receipt", type=pathlib.Path, required=True)
    parser.add_argument("--computerization", type=pathlib.Path, required=True)
    parser.add_argument("--computerization-receipt", type=pathlib.Path, required=True)
    parser.add_argument("--benchmark", type=float)
    parser.add_argument("--beta-c", type=float, default=DEFAULT_BETA_C)
    parser.add_argument("--repetitions", type=int, default=999)
    parser.add_argument("--seed", type=int, default=20260828)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args(argv)
    if args.repetitions < 999:
        raise SystemExit("NEED_HUMAN: final artifact requires at least 999 paired draws")
    result = run(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "paired_delta_se": result["paired_delta_se"],
        "mde_delta_80_log_points": result["mde_delta_80_log_points"],
        "equivalence_power": result["equivalence_power_at_delta_zero_primary_sesoi"]
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
