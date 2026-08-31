#!/usr/bin/env python3
"""Estimate only the predeclared YAX Phase-2 beta flow margins.

POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd


LABEL = "POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1"
ROOT = pathlib.Path(__file__).resolve().parents[3]
PLAN_COMMIT = "aed4ba518800d10b74284a7f3312e90a15b7b0d3"
BOOTSTRAP_DRAWS = 999
SEEDS = {"employment_exit": 2026083101, "occupational_outflow": 2026083102,
         "persistent_outflow": 2026083103, "entry_destination": 2026083104}
ENGINE_PATH = ROOT / "dax/memo/power_calcs/young_relative_employment_power.py"
SPEC = importlib.util.spec_from_file_location("yax_phase2_engine", ENGINE_PATH)
ENGINE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ENGINE
SPEC.loader.exec_module(ENGINE)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def write_csv(path: pathlib.Path, rows: list[dict]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty output: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def authenticate(args: argparse.Namespace) -> dict:
    if subprocess.run(["git", "merge-base", "--is-ancestor", PLAN_COMMIT, "HEAD"],
                      cwd=ROOT).returncode:
        raise RuntimeError("committed Phase-2 plan is not an ancestor of execution HEAD")
    receipt = json.loads(args.weight_receipt.read_text())
    if receipt.get("status") != "PASS_DEFENSIBLE_CPSIDV_WITH_OFFICIAL_WEIGHT":
        raise RuntimeError("Phase-1.5 weight compatibility gate is not PASS")
    if receipt.get("AI_flow_coefficients_estimated") != []:
        raise RuntimeError("Phase-1.5 receipt does not preserve the pre-coefficient state")
    expected = receipt["input_hashes"]
    actual = {
        "wide_microdata_private": sha256(args.microdata),
        "weight_patch_private": sha256(args.weight_patch),
        "bridge": sha256(args.bridge),
        "preperiod_beta_membership": sha256(args.membership),
    }
    bad = {key: (actual[key], expected[key]) for key in actual if actual[key] != expected[key]}
    if bad:
        raise RuntimeError(f"authenticated Phase-2 input mismatch: {bad}")
    return {"weight_receipt": receipt, "actual_hashes": actual, "execution_head": git("rev-parse", "HEAD")}


def load_pairs(main_path: pathlib.Path, patch_path: pathlib.Path) -> tuple[pd.DataFrame, dict]:
    main_columns = [
        "YEAR", "MONTH", "SERIAL", "PERNUM", "CPSID", "CPSIDP", "CPSIDV",
        "MISH", "AGE", "EMPSTAT", "OCC", "OCC2010", "WTFINL", "ASECFLAG",
    ]
    patch_columns = [
        "YEAR", "MONTH", "SERIAL", "PERNUM", "CPSID", "CPSIDP", "CPSIDV",
        "MISH", "AGE", "LNKFW1MWT",
    ]
    mains = pd.read_csv(main_path, usecols=main_columns, chunksize=400_000)
    patches = pd.read_csv(patch_path, usecols=patch_columns, chunksize=400_000)
    pieces = []
    total = 0
    while True:
        try:
            main = next(mains)
        except StopIteration:
            main = None
        try:
            patch = next(patches)
        except StopIteration:
            patch = None
        if main is None or patch is None:
            if main is not None or patch is not None:
                raise RuntimeError("wide/patch row counts differ")
            break
        if len(main) != len(patch):
            raise RuntimeError("wide/patch chunks differ")
        total += len(main)
        for key in ["YEAR", "MONTH", "SERIAL", "PERNUM", "CPSID", "CPSIDP", "CPSIDV", "MISH", "AGE"]:
            if not main[key].fillna(-1).equals(patch[key].fillna(-1)):
                raise RuntimeError(f"weight patch differs on {key}")
        main["LNKFW1MWT"] = pd.to_numeric(patch.LNKFW1MWT, errors="raise")
        main = main.loc[
            main.ASECFLAG.ne(1)
            & pd.to_numeric(main.WTFINL, errors="coerce").gt(0)
            & pd.to_numeric(main.EMPSTAT, errors="coerce").between(10, 36)
        ].drop(columns="ASECFLAG")
        pieces.append(main)
    frame = pd.concat(pieces, ignore_index=True)
    del pieces
    integers = ["YEAR", "MONTH", "SERIAL", "PERNUM", "MISH", "AGE", "EMPSTAT", "OCC", "OCC2010"]
    for column in integers:
        frame[column] = pd.to_numeric(frame[column], errors="raise").astype("int64")
    for column in ["CPSID", "CPSIDP", "CPSIDV"]:
        frame[column] = pd.to_numeric(frame[column], errors="raise").astype("int64")
    for column in ["WTFINL", "LNKFW1MWT"]:
        frame[column] = pd.to_numeric(frame[column], errors="raise").astype("float64")
    frame["month_ord"] = frame.YEAR * 12 + frame.MONTH
    frame["month"] = frame.YEAR.astype(str) + "-" + frame.MONTH.astype(str).str.zfill(2)
    frame["age_group"] = np.where(frame.AGE.between(22, 25), "young_22_25", "older_26_65")
    frame["employed"] = frame.EMPSTAT.isin([10, 12])
    frame["nonemployed"] = frame.EMPSTAT.between(20, 36)

    observed = set(frame.month_ord.unique())
    origin = frame.loc[
        frame.AGE.between(22, 65) & frame.MISH.isin([1, 2, 3, 5, 6, 7])
    ].copy()
    origin["target_ord"] = origin.month_ord + 1
    origin = origin.loc[origin.target_ord.isin(observed) & origin.CPSIDV.ne(0)].copy()
    dest_columns = ["CPSIDV", "month_ord", "MISH", "YEAR", "EMPSTAT", "OCC", "OCC2010", "employed", "nonemployed"]
    destination = frame.loc[frame.CPSIDV.ne(0), dest_columns].copy()
    if destination.duplicated(["CPSIDV", "month_ord"]).any():
        raise RuntimeError("CPSIDV is duplicated within destination month")
    destination = destination.rename(columns={name: f"{name}_d" for name in dest_columns if name != "CPSIDV"})
    pairs = origin.merge(
        destination,
        left_on=["CPSIDV", "target_ord"], right_on=["CPSIDV", "month_ord_d"],
        how="inner", validate="many_to_one",
    )
    pairs = pairs.loc[pairs.MISH_d.eq(pairs.MISH + 1) & pairs.LNKFW1MWT.gt(0)].copy()
    if ((pairs.month.eq("2025-09")) & pairs.month_ord_d.eq(2025 * 12 + 11)).any():
        raise RuntimeError("false September-to-November 2025 link")

    # One fixed t+2 construction for the persistence sensitivity.
    third = frame.loc[frame.CPSIDV.ne(0), ["CPSIDV", "month_ord", "MISH", "EMPSTAT", "OCC2010"]].copy()
    third = third.rename(columns={"month_ord": "month_ord_t2", "MISH": "MISH_t2",
                                  "EMPSTAT": "EMPSTAT_t2", "OCC2010": "OCC2010_t2"})
    pairs["target_ord_t2"] = pairs.month_ord + 2
    pairs = pairs.merge(
        third, left_on=["CPSIDV", "target_ord_t2"], right_on=["CPSIDV", "month_ord_t2"],
        how="left", validate="many_to_one",
    )
    pairs["legitimate_t2"] = (
        pairs.month_ord_t2.eq(pairs.target_ord_t2)
        & pairs.MISH_t2.eq(pairs.MISH + 2)
        & pairs.MISH.isin([1, 2, 5, 6])
    )
    return pairs, {
        "wide_rows_read": total,
        "validated_adjacent_pairs": int(len(pairs)),
        "young_validated_pairs": int(pairs.age_group.eq("young_22_25").sum()),
        "pre_validated_pairs": int(pairs.month.le("2022-11").sum()),
        "post_validated_pairs": int(pairs.month.ge("2023-01").sum()),
        "long_gap_pairs": 0,
        "false_September_to_November_2025_links": 0,
    }


def input_maps(args: argparse.Namespace) -> tuple[pd.DataFrame, dict, dict]:
    bridge = pd.read_csv(args.bridge, dtype={"census_2010": str, "census_2018": str})
    bridge["census_2010"] = bridge.census_2010.str.zfill(4)
    bridge["census_2018"] = bridge.census_2018.str.zfill(4)
    membership = pd.read_csv(args.membership, dtype={"occ_code": str})
    membership["occ_code"] = membership.occ_code.str.zfill(4)
    qmap = membership.set_index("occ_code").preperiod_quintile.astype(int).to_dict()
    comp = pd.read_csv(args.computerization, dtype={"census2018": str})
    comp["census2018"] = comp.census2018.str.zfill(4)
    webb = pd.to_numeric(comp.set_index("census2018").webb_pct_software, errors="coerce").to_dict()
    support = sorted(code for code in qmap if np.isfinite(webb.get(code, np.nan)))
    if len(support) != 468:
        raise RuntimeError(f"primary beta/Webb support changed: {len(support)}")
    q5_hash = hashlib.sha256("\n".join(sorted(code for code in support if qmap[code] == 5)).encode()).hexdigest()
    if q5_hash != "82549d91f47b526448b7ae7c2b35feec056dc01981ab60a88dae501d731a9e4d":
        raise RuntimeError("historical beta Q5 membership changed")
    return bridge, {code: qmap[code] for code in support}, {code: float(webb[code]) for code in support}


def route_cells(base: pd.DataFrame, occ_col: str, year_col: str, bridge: pd.DataFrame,
                qmap: dict, webb: dict, value_columns: list[str]) -> pd.DataFrame:
    base = base.copy()
    base["source_occ"] = base[occ_col].astype(int).map(lambda value: f"{value:04d}")
    early = base.loc[base[year_col].le(2019)].merge(
        bridge[["census_2010", "census_2018", "bridge_weight"]],
        left_on="source_occ", right_on="census_2010", how="inner", validate="many_to_many",
    )
    early["occ_code"] = early.census_2018
    for column in value_columns:
        early[column] *= early.bridge_weight
    current = base.loc[base[year_col].ge(2020)].copy()
    current["occ_code"] = current.source_occ
    keep = ["occ_code", "month", "age_group", *value_columns]
    routed = pd.concat([early[keep], current[keep]], ignore_index=True)
    routed["quintile"] = routed.occ_code.map(qmap)
    routed["webb"] = routed.occ_code.map(webb)
    routed = routed.loc[routed.quintile.notna() & routed.webb.notna()].copy()
    routed["quintile"] = routed.quintile.astype(int)
    return routed.groupby(["occ_code", "month", "age_group", "quintile", "webb"], as_index=False)[value_columns].sum()


def build_cells(pairs: pd.DataFrame, bridge: pd.DataFrame, qmap: dict, webb: dict) -> tuple[dict, list[dict]]:
    weights = {"official": "LNKFW1MWT", "unweighted": None, "origin_WTFINL": "WTFINL"}
    results: dict[str, dict[str, pd.DataFrame]] = {}
    counts: list[dict] = []
    for weighting, column in weights.items():
        w = np.ones(len(pairs)) if column is None else pairs[column].to_numpy(float)
        work = pairs[["YEAR", "month", "age_group", "OCC", "OCC2010", "EMPSTAT",
                      "YEAR_d", "OCC_d", "OCC2010_d", "EMPSTAT_d", "employed",
                      "nonemployed", "employed_d", "nonemployed_d", "legitimate_t2",
                      "EMPSTAT_t2", "OCC2010_t2"]].copy()
        work["analysis_weight"] = w

        exit_risk = work.employed
        exit_event = exit_risk & work.nonemployed_d
        exit_base = work.loc[exit_risk & work.OCC.gt(0), ["YEAR", "month", "age_group", "OCC", "analysis_weight"]].copy()
        exit_base["risk"] = exit_base.analysis_weight
        exit_base["event"] = np.where(exit_event.loc[exit_base.index], exit_base.analysis_weight, 0.0)
        results.setdefault("employment_exit", {})[weighting] = route_cells(
            exit_base, "OCC", "YEAR", bridge, qmap, webb, ["risk", "event"]
        )

        switch_risk = (
            work.employed & work.employed_d & work.OCC2010.gt(0) & work.OCC2010_d.gt(0)
            & work.month.ne("2019-12")
        )
        switch_event = switch_risk & work.OCC2010.ne(work.OCC2010_d)
        switch_base = work.loc[switch_risk & work.OCC.gt(0), ["YEAR", "month", "age_group", "OCC", "analysis_weight"]].copy()
        switch_base["risk"] = switch_base.analysis_weight
        switch_base["event"] = np.where(switch_event.loc[switch_base.index], switch_base.analysis_weight, 0.0)
        results.setdefault("occupational_outflow", {})[weighting] = route_cells(
            switch_base, "OCC", "YEAR", bridge, qmap, webb, ["risk", "event"]
        )

        persistent_risk = (
            switch_risk & work.legitimate_t2 & work.EMPSTAT_t2.isin([10, 12]) & work.OCC2010_t2.gt(0)
        )
        persistent_event = (
            persistent_risk & work.OCC2010.ne(work.OCC2010_d) & work.OCC2010_d.eq(work.OCC2010_t2)
        )
        persistent_base = work.loc[persistent_risk & work.OCC.gt(0), ["YEAR", "month", "age_group", "OCC", "analysis_weight"]].copy()
        persistent_base["risk"] = persistent_base.analysis_weight
        persistent_base["event"] = np.where(persistent_event.loc[persistent_base.index], persistent_base.analysis_weight, 0.0)
        results.setdefault("persistent_outflow", {})[weighting] = route_cells(
            persistent_base, "OCC", "YEAR", bridge, qmap, webb, ["risk", "event"]
        )

        entry_event = work.nonemployed & work.employed_d & work.OCC_d.gt(0)
        entry_base = work.loc[entry_event, ["YEAR_d", "month", "age_group", "OCC_d", "analysis_weight"]].copy()
        entry_base["event"] = entry_base.analysis_weight
        results.setdefault("entry_destination", {})[weighting] = route_cells(
            entry_base, "OCC_d", "YEAR_d", bridge, qmap, webb, ["event"]
        )

        for margin, risk_mask, event_mask in (
            ("employment_exit", exit_risk, exit_event),
            ("occupational_outflow", switch_risk, switch_event),
            ("persistent_outflow", persistent_risk, persistent_event),
            ("entry_destination", entry_event, entry_event),
        ):
            counts.append({
                "analysis_status": LABEL, "weighting": weighting, "margin": margin,
                "risk_or_entrant_raw": int(risk_mask.sum()), "events_raw": int(event_mask.sum()),
                "risk_or_entrant_weighted": float(w[risk_mask].sum()),
                "events_weighted": float(w[event_mask].sum()),
                "young_events_raw": int((event_mask & work.age_group.eq("young_22_25")).sum()),
                "post_events_raw": int((event_mask & work.month.ge("2023-01")).sum()),
            })
    return results, counts


def _sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(values, -700, 700)))


def fit_offset(young: np.ndarray, total: np.ndarray, occ: np.ndarray, month: np.ndarray,
               regressors: np.ndarray, offset: np.ndarray, max_iterations: int = 5000):
    keep = total > 0
    y, n, o, t, x, off = young[keep], total[keep], occ[keep], month[keep], regressors[keep], offset[keep]
    used_occ = np.unique(o)
    remap = {old: new for new, old in enumerate(used_occ)}
    o = np.array([remap[value] for value in o], int)
    n_occ, n_month = len(used_occ), int(t.max()) + 1
    overall = np.clip(y.sum() / n.sum(), 1e-6, 1 - 1e-6)
    occ_effect = np.zeros(n_occ)
    month_effect = np.full(n_month, math.log(overall / (1 - overall)))
    beta = np.zeros(x.shape[1])
    converged = False
    for iteration in range(1, max_iterations + 1):
        largest = 0.0
        for _ in range(2):
            eta = off + occ_effect[o] + month_effect[t] + x @ beta
            p = np.clip(_sigmoid(eta), 1e-10, 1 - 1e-10)
            residual, weight = y - n * p, np.maximum(n * p * (1 - p), 1e-12)
            score = np.bincount(o, weights=residual, minlength=n_occ)
            info = np.bincount(o, weights=weight, minlength=n_occ)
            step = np.clip(np.divide(score, info, out=np.zeros_like(score), where=info > 0), -1, 1)
            occ_effect += step
            largest = max(largest, float(np.max(np.abs(step))))
            eta = off + occ_effect[o] + month_effect[t] + x @ beta
            p = np.clip(_sigmoid(eta), 1e-10, 1 - 1e-10)
            residual, weight = y - n * p, np.maximum(n * p * (1 - p), 1e-12)
            score = np.bincount(t, weights=residual, minlength=n_month)
            info = np.bincount(t, weights=weight, minlength=n_month)
            step = np.clip(np.divide(score, info, out=np.zeros_like(score), where=info > 0), -1, 1)
            month_effect += step
            largest = max(largest, float(np.max(np.abs(step))))
            anchor = month_effect[0]
            month_effect -= anchor
            occ_effect += anchor
        eta = off + occ_effect[o] + month_effect[t] + x @ beta
        p = np.clip(_sigmoid(eta), 1e-10, 1 - 1e-10)
        residual, weight = y - n * p, np.maximum(n * p * (1 - p), 1e-12)
        rx = ENGINE._weighted_absorb(x, weight, o, t, n_occ, n_month)
        information = rx.T @ (weight[:, None] * rx)
        score = rx.T @ residual
        step = np.clip(np.linalg.solve(information, score), -1, 1)
        beta += step
        largest = max(largest, float(np.max(np.abs(step))))
        if largest < 1e-8:
            converged = True
            break
    if not converged:
        raise RuntimeError("offset grouped-binomial fit did not converge")
    eta = off + occ_effect[o] + month_effect[t] + x @ beta
    p = np.clip(_sigmoid(eta), 1e-10, 1 - 1e-10)
    residual, weight = y - n * p, np.maximum(n * p * (1 - p), 1e-12)
    rx = ENGINE._weighted_absorb(x, weight, o, t, n_occ, n_month)
    information = rx.T @ (weight[:, None] * rx)
    bread = np.linalg.inv(information)
    scores = np.zeros((n_occ, x.shape[1]))
    np.add.at(scores, o, rx * residual[:, None])
    influence = scores @ bread.T * math.sqrt(n_occ / (n_occ - 1))
    variance = influence.T @ influence
    return beta, np.sqrt(np.maximum(np.diag(variance), 0)), influence, iteration, used_occ


def model_cells(cells: pd.DataFrame, margin: str, weighting: str, webb_reference: tuple[float, float]) -> dict:
    static = cells.loc[cells.month.ne("2022-12")].copy()
    months = sorted(static.month.unique())
    occupations = sorted(static.occ_code.unique())
    index = pd.MultiIndex.from_product([occupations, months, ["young_22_25", "older_26_65"]],
                                       names=["occ_code", "month", "age_group"])
    value_columns = ["event"] + (["risk"] if "risk" in static else [])
    panel = static.set_index(["occ_code", "month", "age_group"])[value_columns].reindex(index, fill_value=0.0)
    event_y = panel.xs("young_22_25", level="age_group").event.to_numpy().reshape(len(occupations), len(months))
    event_o = panel.xs("older_26_65", level="age_group").event.to_numpy().reshape(len(occupations), len(months))
    if "risk" in value_columns:
        risk_y = panel.xs("young_22_25", level="age_group").risk.to_numpy().reshape(len(occupations), len(months))
        risk_o = panel.xs("older_26_65", level="age_group").risk.to_numpy().reshape(len(occupations), len(months))
        offset = np.log(np.clip(risk_y, 1e-12, None) / np.clip(risk_o, 1e-12, None)).reshape(-1)
        valid_risk = (risk_y > 0) & (risk_o > 0)
    else:
        offset = np.zeros(len(occupations) * len(months))
        valid_risk = np.ones((len(occupations), len(months)), dtype=bool)
    total = (event_y + event_o).reshape(-1)
    total[~valid_risk.reshape(-1)] = 0
    q = static.drop_duplicates("occ_code").set_index("occ_code").quintile.reindex(occupations).to_numpy(int)
    webb = static.drop_duplicates("occ_code").set_index("occ_code").webb.reindex(occupations).to_numpy(float)
    mean, sd = webb_reference
    webb_z = (webb - mean) / sd
    post = np.array([month >= "2023-01" for month in months])
    columns = [((q[:, None] == value) & post[None, :]).reshape(-1).astype(float) for value in [2, 3, 4, 5]]
    columns.append((webb_z[:, None] * post[None, :]).reshape(-1))
    regressors = np.column_stack(columns)
    occ_index = np.repeat(np.arange(len(occupations)), len(months))
    month_index = np.tile(np.arange(len(months)), len(occupations))
    beta, se, influence, iterations, used_occ = fit_offset(
        event_y.reshape(-1), total, occ_index, month_index, regressors, offset
    )
    target = 3
    rng = np.random.default_rng(SEEDS[margin] + {"official": 0, "unweighted": 100, "origin_WTFINL": 200}[weighting])
    signs = rng.choice(np.array([-1.0, 1.0]), size=(BOOTSTRAP_DRAWS, len(influence)))
    shifts = signs @ influence[:, target]
    studentizer = se[target] if se[target] > 0 else float(np.std(shifts, ddof=1))
    critical = float(np.quantile(np.abs(shifts / studentizer), 0.95, method="higher"))
    pvalue = float((1 + np.sum(np.abs(shifts / studentizer) >= abs(beta[target] / studentizer))) / (BOOTSTRAP_DRAWS + 1))
    return {
        "analysis_status": LABEL, "margin": margin, "weighting": weighting,
        "target": "beta_Q5_vs_Q1_x_young_x_post", "coefficient_log_points": float(beta[target]),
        "exponential_percent": float(100 * (math.exp(beta[target]) - 1)),
        "analytic_cluster_se": float(se[target]),
        "wild_score_ci_lower": float(beta[target] - critical * se[target]),
        "wild_score_ci_upper": float(beta[target] + critical * se[target]),
        "wild_score_p_value": pvalue, "wild_score_critical": critical,
        "bootstrap_draws": BOOTSTRAP_DRAWS, "bootstrap_seed": int(SEEDS[margin] + {"official": 0, "unweighted": 100, "origin_WTFINL": 200}[weighting]),
        "converged": True, "iterations": int(iterations),
        "occupations_on_input": len(occupations), "event_contributing_occupations": len(used_occ),
        "months": len(months), "first_month": months[0], "last_month": months[-1],
        "december_2022_excluded": "2022-12" not in months,
        "december_2019_excluded": margin in {"occupational_outflow", "persistent_outflow"},
        "long_gap_links_used": False,
    }


def decide(primary: dict[str, dict]) -> tuple[str, str]:
    directions = {"employment_exit": 1, "occupational_outflow": 1, "entry_destination": -1}
    consistent, opposite = [], []
    for margin, direction in directions.items():
        row = primary[margin]
        excludes = row["wild_score_ci_lower"] > 0 or row["wild_score_ci_upper"] < 0
        if excludes and np.sign(row["coefficient_log_points"]) == direction:
            consistent.append(margin)
        elif excludes:
            opposite.append(margin)
    if opposite or len(consistent) >= 2:
        return "FLOW-M4", f"stock-consistent={consistent}; statistically opposite={opposite}"
    if consistent == ["entry_destination"]:
        return "FLOW-M1", "entry is the only stock-consistent distinguishable margin"
    if consistent == ["employment_exit"]:
        return "FLOW-M2", "employment exit is the only stock-consistent distinguishable margin"
    if consistent == ["occupational_outflow"]:
        return "FLOW-M3", "occupational outflow is the only stock-consistent distinguishable margin"
    return "FLOW-M5", "no primary target wild-score CI excludes zero"


def run(args: argparse.Namespace) -> dict:
    auth = authenticate(args)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    pairs, link = load_pairs(args.microdata, args.weight_patch)
    bridge, qmap, webb = input_maps(args)
    cells, counts = build_cells(pairs, bridge, qmap, webb)
    counts_path = args.output_dir / "YAX_PHASE2_FLOW_SAMPLE_COUNTS.csv"
    write_csv(counts_path, counts)

    exit_pre = cells["employment_exit"]["official"]
    pre = exit_pre.loc[exit_pre.month.le("2022-11")]
    weights = pre.groupby("occ_code").risk.sum()
    webb_values = np.array([webb[code] for code in weights.index], float)
    w = weights.to_numpy(float)
    webb_mean = float(np.average(webb_values, weights=w))
    webb_sd = float(np.sqrt(np.average((webb_values - webb_mean) ** 2, weights=w)))
    webb_reference = (webb_mean, webb_sd)

    rows = []
    for margin in ["employment_exit", "occupational_outflow", "persistent_outflow", "entry_destination"]:
        for weighting in ["official", "unweighted", "origin_WTFINL"]:
            rows.append(model_cells(cells[margin][weighting], margin, weighting, webb_reference))
    results_path = args.output_dir / "YAX_PHASE2_PRIMARY_BETA_FLOW_RESULTS.csv"
    write_csv(results_path, rows)
    primary = {row["margin"]: row for row in rows if row["weighting"] == "official"}
    classification, reason = decide(primary)

    decision_path = args.output_dir / "YAX_PHASE2_FLOW_MARGIN_DECISION.md"
    decision_path.write_text(
        f"""# YAX Phase 2 beta flow-margin decision

> **{LABEL}**

## Classification

**{classification}** — {reason}.

| margin | beta Q5/Q1 log coefficient | wild 95% CI | p-value |
|---|---:|---:|---:|
| employment exit | {primary['employment_exit']['coefficient_log_points']:.6f} | [{primary['employment_exit']['wild_score_ci_lower']:.6f}, {primary['employment_exit']['wild_score_ci_upper']:.6f}] | {primary['employment_exit']['wild_score_p_value']:.4f} |
| occupational outflow | {primary['occupational_outflow']['coefficient_log_points']:.6f} | [{primary['occupational_outflow']['wild_score_ci_lower']:.6f}, {primary['occupational_outflow']['wild_score_ci_upper']:.6f}] | {primary['occupational_outflow']['wild_score_p_value']:.4f} |
| entry destination | {primary['entry_destination']['coefficient_log_points']:.6f} | [{primary['entry_destination']['wild_score_ci_lower']:.6f}, {primary['entry_destination']['wild_score_ci_upper']:.6f}] | {primary['entry_destination']['wild_score_p_value']:.4f} |

The coefficients are linked-sample relative rate/allocation associations, not
shares of the employment-stock coefficient. The persistent-switch result is a
declared sensitivity and does not determine the margin gate.

Stage 2B is {'AUTHORIZED only for the plan-permitted distinguishable margin(s)' if classification != 'FLOW-M5' else 'STOPPED; no six-architecture treatment-effect grid may run'}.
Stage 2C remains independently authorized because it was committed before
these coefficients and switching-data quality is assessed separately.
""",
        encoding="utf-8",
    )

    figure_path = args.output_dir / "figure_phase2A_beta_flow_margins.png"
    try:
        import matplotlib.pyplot as plt
        fig_rows = [primary[name] for name in ["employment_exit", "occupational_outflow", "entry_destination"]]
        y = np.arange(3)
        estimates = np.array([row["coefficient_log_points"] for row in fig_rows])
        lower = np.array([row["wild_score_ci_lower"] for row in fig_rows])
        upper = np.array([row["wild_score_ci_upper"] for row in fig_rows])
        fig, ax = plt.subplots(figsize=(7.2, 3.7))
        ax.errorbar(estimates, y, xerr=np.vstack([estimates - lower, upper - estimates]), fmt="o", color="#1f4e79", capsize=4)
        ax.axvline(0, color="black", linewidth=0.8)
        ax.set_yticks(y, ["Employment exit", "Occupational outflow", "Entry destination"])
        ax.invert_yaxis()
        ax.set_xlabel("Beta Q5 vs Q1 young-relative post coefficient (log points)")
        ax.set_title("Phase 2A: primary beta flow margins")
        fig.tight_layout()
        fig.savefig(figure_path, dpi=180)
        plt.close(fig)
    except ModuleNotFoundError:
        figure_path = None

    receipt = {
        "record": "YAX Phase 2A primary beta flow execution receipt", "analysis_status": LABEL,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(), "plan_commit": PLAN_COMMIT,
        "execution_head": auth["execution_head"], "authenticated_inputs": auth["actual_hashes"],
        "execution_script_sha256": sha256(pathlib.Path(__file__)),
        "link_sample": link, "primary_weight": "origin LNKFW1MWT on successful CPSIDV adjacent links",
        "sensitivities": ["unweighted", "origin WTFINL (non-longitudinal)"],
        "webb_preperiod_mean": webb_mean, "webb_preperiod_sd": webb_sd,
        "beta_Q5_codes_sha256": "82549d91f47b526448b7ae7c2b35feec056dc01981ab60a88dae501d731a9e4d",
        "classification": classification, "classification_reason": reason,
        "stage2B_authorized": classification != "FLOW-M5",
        "stage2C_predeclared_independently": True,
        "new_outcome_regressions_executed": [
            f"{margin}__{weighting}__beta_RuleA_Webb"
            for margin in ["employment_exit", "occupational_outflow", "persistent_outflow", "entry_destination"]
            for weighting in ["official", "unweighted", "origin_WTFINL"]
        ],
        "excluded_analyses_executed": [], "long_gap_links_used": False,
        "figure_A_generated_in_execution_environment": figure_path is not None,
        "outputs": {path.name: sha256(path) for path in [counts_path, results_path, decision_path]
                    + ([] if figure_path is None else [figure_path])},
    }
    receipt_path = args.output_dir / "YAX_PHASE2_STAGE2A_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"classification": classification, "primary": primary}, indent=2))
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--microdata", required=True, type=pathlib.Path)
    parser.add_argument("--weight-patch", required=True, type=pathlib.Path)
    parser.add_argument("--weight-receipt", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent / "YAX_PHASE2_LONGITUDINAL_WEIGHT_RECEIPT.json")
    parser.add_argument("--bridge", type=pathlib.Path, default=ROOT / "yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv")
    parser.add_argument("--membership", type=pathlib.Path, default=ROOT / "yax/analysis/postoutcome_v41_quintile_weight/YAX_V41_QUINTILE_MEMBERSHIP.csv")
    parser.add_argument("--computerization", type=pathlib.Path, default=ROOT / "yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv")
    parser.add_argument("--output-dir", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent)
    args = parser.parse_args()
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
