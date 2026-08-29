#!/usr/bin/env python3
"""Execute the frozen YAX v1.1 post-outcome employment-stock analysis.

The script implements the exact two-age conditional equivalent of the frozen
PPML and refuses to run unless the repository commit, private microdata hash,
pre-period-cell hash, and first-access receipt all authenticate.  Static models
drop the December-2022 transition month; event studies retain it.  October 2025
is absent by design.
"""
from __future__ import annotations

import argparse
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


FROZEN_COMMIT = "22fbf7924809b7a535e31ae0ab68f5b113ce8078"
FROZEN_TAG = "v1.1-design-freeze"
MICRODATA_SHA256 = "3fe42477e6f2ce401e85123f0e278e758595c1c4071a8743f243a92752db38c9"
PRE_CELLS_SHA256 = "4b8c8b96caeebc4121ad4914adbadf7ebfa98d677a80b32b78a9f905956ea800"
LOOKUP_SHA256 = "c6eb70623ea598bfc41f2352391add7a342a8809a4e57b02f2af0e75dd0223f8"
COMP_SHA256 = "352cb40834ec83225f747d316eb3e03fce1d1c5c65d80720c558177f85801fdd"
AI_MEASURES = (
    "aioe_admin_equal", "aioe_ability_direct", "aioe_oews2018_source_weighted",
    "dv_rating_alpha", "dv_rating_beta", "dv_rating_gamma",
)
COMP_MEASURES = (
    "webb_pct_software", "onet_computers_importance", "onet_computers_level",
    "rti_autor_dorn", "frey_osborne_probability",
)
EXPECTED_POST = [
    f"{year:04d}-{month:02d}"
    for year in range(2023, 2027)
    for month in range(1, 13)
    if (year, month) <= (2026, 7) and (year, month) != (2025, 10)
]
TRANSITION = "2022-12"
EVENT_REFERENCE = "2022-10"
BOOTSTRAP_DRAWS = 999
BOOTSTRAP_SEED = 20260829
PAIRED_SEED = 20260828


ROOT = pathlib.Path(__file__).resolve().parents[2]
ENGINE_PATH = ROOT / "dax/memo/power_calcs/young_relative_employment_power.py"
SPEC = importlib.util.spec_from_file_location("yax_frozen_engine", ENGINE_PATH)
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


def weighted_scale(values: np.ndarray, weights: np.ndarray) -> tuple[float, float]:
    mean = float(np.average(values, weights=weights))
    sd = float(np.sqrt(np.average(np.square(values - mean), weights=weights)))
    if not np.isfinite(sd) or sd <= 0:
        raise ValueError("weighted scale has zero variance")
    return mean, sd


def weighted_quintiles(values: np.ndarray, weights: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    cumulative = np.cumsum(weights[order])
    cuts = np.array([
        values[order[min(np.searchsorted(cumulative, share * cumulative[-1], side="left"),
                         len(values) - 1)]]
        for share in (0.2, 0.4, 0.6, 0.8)
    ])
    if np.any(cuts[:-1] >= cuts[1:]):
        raise ValueError("employment-weighted quintile cuts are not distinct")
    return np.searchsorted(cuts, values, side="left") + 1


def validate_inputs(args: argparse.Namespace) -> dict:
    if git("rev-parse", f"{FROZEN_TAG}^{{}}") != FROZEN_COMMIT:
        raise RuntimeError("frozen tag does not peel to the recorded commit")
    current = git("rev-parse", "HEAD")
    if not git("merge-base", "--is-ancestor", FROZEN_COMMIT, current) == "":
        pass
    hashes = {
        "microdata": sha256(args.microdata), "preperiod_cells": sha256(args.preperiod_cells),
        "lookup": sha256(args.lookup), "computerization": sha256(args.computerization),
        "rule_b": sha256(args.rule_b_values),
    }
    expected = {"microdata": MICRODATA_SHA256, "preperiod_cells": PRE_CELLS_SHA256,
                "lookup": LOOKUP_SHA256, "computerization": COMP_SHA256}
    bad = {key: (hashes[key], value) for key, value in expected.items()
           if hashes[key] != value}
    if bad:
        raise RuntimeError(f"authenticated input hash mismatch: {bad}")
    receipt = json.loads(args.first_access_receipt.read_text(encoding="utf-8"))
    if receipt.get("frozen_commit") != FROZEN_COMMIT or receipt.get("frozen_tag") != FROZEN_TAG:
        raise RuntimeError("first-access receipt does not authenticate the freeze")
    if receipt.get("microdata_sha256") != MICRODATA_SHA256:
        raise RuntimeError("first-access receipt does not authenticate microdata")
    if receipt.get("status") != "AUTHORIZED_FIRST_POST_FREEZE_OUTCOME_ACCESS":
        raise RuntimeError("first-access receipt lacks authorization status")
    return {"head": current, "hashes": hashes, "receipt": receipt}


def read_preperiod(path: pathlib.Path) -> tuple[pd.DataFrame, list[str], list[str]]:
    cells = pd.read_csv(path, dtype={"occ_code": str})
    cells = cells.loc[cells.lookup_role.eq("raw_occ_main_2020_plus")].copy()
    cells["occ_code"] = cells.occ_code.str.zfill(4)
    pivot = cells.pivot_table(index=["occ_code", "month"], columns="age_group",
                              values="employment_headcount", aggfunc="sum", fill_value=0.0)
    months = sorted(cells.month.unique())
    occupations = sorted(cells.occ_code.unique())
    index = pd.MultiIndex.from_product([occupations, months], names=["occ_code", "month"])
    pivot = pivot.reindex(index, fill_value=0.0)
    for age in ("young_22_25", "older_26_65"):
        if age not in pivot:
            pivot[age] = 0.0
    totals = pivot.groupby(level="occ_code")[["young_22_25", "older_26_65"]].sum()
    support = totals.index[(totals > 0).all(axis=1)].tolist()
    if len(support) != 490 or len(months) != 66 or months[-1] != "2022-11":
        raise RuntimeError("pre-period support does not match frozen 490 x 66 panel")
    return pivot.loc[(support, slice(None)), :], support, months


def read_post_cells(path: pathlib.Path, occupations: list[str]) -> tuple[pd.DataFrame, dict]:
    pieces = []
    counters = {"rows_read": 0, "rows_post": 0, "rows_employed_age_22_65": 0}
    usecols = ["YEAR", "MONTH", "AGE", "EMPSTAT", "OCC", "WTFINL"]
    for chunk in pd.read_csv(path, usecols=usecols, chunksize=500_000):
        counters["rows_read"] += len(chunk)
        month_code = chunk.YEAR.astype(int) * 100 + chunk.MONTH.astype(int)
        chunk = chunk.loc[month_code.ge(202212)].copy()
        counters["rows_post"] += len(chunk)
        age = pd.to_numeric(chunk.AGE, errors="coerce")
        emp = pd.to_numeric(chunk.EMPSTAT, errors="coerce").isin([10, 12])
        weight = pd.to_numeric(chunk.WTFINL, errors="coerce")
        keep = age.between(22, 65) & emp & np.isfinite(weight) & weight.gt(0)
        chunk = chunk.loc[keep].copy()
        counters["rows_employed_age_22_65"] += len(chunk)
        occ = pd.to_numeric(chunk.OCC, errors="coerce")
        chunk = chunk.loc[occ.notna() & occ.between(0, 9999) & occ.mod(1).eq(0)].copy()
        chunk["occ_code"] = occ.loc[chunk.index].astype(int).map(lambda x: f"{x:04d}")
        chunk = chunk.loc[chunk.occ_code.isin(occupations)]
        chunk["month"] = (chunk.YEAR.astype(int).astype(str) + "-"
                          + chunk.MONTH.astype(int).astype(str).str.zfill(2))
        chunk["age_group"] = np.where(chunk.AGE.between(22, 25),
                                      "young_22_25", "older_26_65")
        pieces.append(chunk.groupby(["occ_code", "month", "age_group"], as_index=False)
                      .WTFINL.sum().rename(columns={"WTFINL": "employment_headcount"}))
    grouped = pd.concat(pieces).groupby(["occ_code", "month", "age_group"], as_index=False)
    grouped = grouped.employment_headcount.sum()
    months = sorted(grouped.month.unique())
    expected = [TRANSITION, *EXPECTED_POST]
    if months != expected:
        raise RuntimeError(f"protected month coverage differs from freeze: {months}")
    index = pd.MultiIndex.from_product([occupations, expected], names=["occ_code", "month"])
    pivot = grouped.pivot_table(index=["occ_code", "month"], columns="age_group",
                                values="employment_headcount", aggfunc="sum", fill_value=0.0)
    pivot = pivot.reindex(index, fill_value=0.0)
    for age in ("young_22_25", "older_26_65"):
        if age not in pivot:
            pivot[age] = 0.0
    return pivot, {**counters, "months": months, "cell_rows": int(len(pivot) * 2)}


def exposure_maps(lookup_path: pathlib.Path, rule_b_path: pathlib.Path) -> dict:
    lookup = pd.read_csv(lookup_path, dtype={"occ_code": str})
    lookup = lookup.loc[lookup.lookup_role.eq("raw_occ_main_2020_plus")].copy()
    lookup["occ_code"] = lookup.occ_code.str.zfill(4)
    lookup = lookup.set_index("occ_code")
    rule_b = pd.read_csv(rule_b_path, dtype={"census2018": str})
    rule_b["census2018"] = rule_b.census2018.str.zfill(4)
    rule_b = rule_b.set_index("census2018")
    result = {}
    for measure in AI_MEASURES:
        if measure.startswith("dv_rating_"):
            mass = pd.to_numeric(lookup[f"{measure}_covered_route_mass"], errors="coerce")
            partial = pd.to_numeric(lookup[f"{measure}_partial_weighted_sum"], errors="coerce")
            strict = pd.to_numeric(lookup[measure], errors="coerce").where(np.isclose(mass, 1.0))
            b = pd.to_numeric(rule_b[f"{measure}_rule_b"], errors="coerce").reindex(lookup.index)
            c = (partial / mass).where(mass.ge(0.95))
            result[measure] = {"A": strict.to_dict(), "B": b.to_dict(), "C": c.to_dict()}
        else:
            value = pd.to_numeric(lookup[measure], errors="coerce")
            result[measure] = {"A": value.to_dict()}
    remote = pd.to_numeric(lookup.dingel_neiman_telework, errors="coerce")
    result["dingel_neiman_telework"] = {"A": remote.to_dict()}
    exact = pd.to_numeric(rule_b.aioe_exact_code_baseline, errors="coerce").reindex(lookup.index)
    result["aioe_exact_code_baseline"] = {"A": exact.to_dict()}
    return result


def comp_maps(path: pathlib.Path) -> tuple[dict, dict, dict]:
    frame = pd.read_csv(path, dtype={"census2018": str})
    frame["census2018"] = frame.census2018.str.zfill(4)
    names = frame.set_index("census2018").occupation.to_dict()
    groups = frame.set_index("census2018").soc_major_group.astype(str).to_dict()
    return ({measure: pd.to_numeric(frame.set_index("census2018")[measure],
                                    errors="coerce").to_dict()
             for measure in COMP_MEASURES}, names, groups)


def panel_arrays(panel: pd.DataFrame, occupations: list[str], months: list[str]):
    selected = panel.reindex(pd.MultiIndex.from_product(
        [occupations, months], names=["occ_code", "month"]), fill_value=0.0)
    young = selected.young_22_25.to_numpy().reshape(len(occupations), len(months))
    older = selected.older_26_65.to_numpy().reshape(len(occupations), len(months))
    return young, older


def fit_with_influence(young, older, regressors):
    n_occ, n_month = young.shape
    total = (young + older).reshape(-1)
    occ = np.repeat(np.arange(n_occ), n_month)
    month = np.tile(np.arange(n_month), n_occ)
    fit = ENGINE.fit_grouped_logit_fe(
        young.reshape(-1), total, occ, month, regressors, max_iterations=5000
    )
    if not fit.converged:
        raise RuntimeError("frozen conditional PPML did not converge")
    keep = total > 0
    y, n = young.reshape(-1)[keep], total[keep]
    o, t, x = occ[keep], month[keep], regressors[keep]
    probability = fit.fitted_probability[keep]
    residual = y - n * probability
    weight = np.maximum(n * probability * (1 - probability), 1e-12)
    rx = ENGINE._weighted_absorb(x, weight, o, t, n_occ, n_month)
    information = rx.T @ (weight[:, None] * rx)
    bread = np.linalg.inv(information)
    scores = np.zeros((n_occ, x.shape[1]))
    np.add.at(scores, o, rx * residual[:, None])
    influence = scores @ bread.T
    influence *= math.sqrt(n_occ / (n_occ - 1))
    return fit, influence


def bootstrap_summary(fit, influence, target, seed, store_draws=False):
    rng = np.random.default_rng(seed)
    signs = rng.choice(np.array([-1.0, 1.0]), size=(BOOTSTRAP_DRAWS, len(influence)))
    shifts = signs @ influence[:, target]
    estimate = float(fit.beta[target])
    analytic_se = float(fit.standard_error[target])
    bootstrap_se = float(np.std(shifts, ddof=1))
    studentizer = analytic_se if analytic_se > 0 else bootstrap_se
    critical = float(np.quantile(np.abs(shifts / studentizer), 0.95, method="higher"))
    pvalue = float((1 + np.sum(np.abs(shifts / studentizer)
                               >= abs(estimate / studentizer))) / (BOOTSTRAP_DRAWS + 1))
    result = {"coefficient": estimate, "analytic_cluster_se": analytic_se,
              "bootstrap_se": bootstrap_se, "bootstrap_p_value": pvalue,
              "ci_lower": estimate - critical * analytic_se,
              "ci_upper": estimate + critical * analytic_se,
              "bootstrap_critical": critical, "bootstrap_draws": BOOTSTRAP_DRAWS,
              "bootstrap_seed": seed, "converged": bool(fit.converged),
              "iterations": int(fit.iterations)}
    if store_draws:
        result["centered_bootstrap_draws"] = shifts.tolist()
    return result, shifts, signs


def prepare_model(panel, base_occupations, months, exposure, comp=None, remote=None,
                  scale="q5_q1", ai_reference=None):
    support = [code for code in base_occupations
               if np.isfinite(exposure.get(code, np.nan))
               and (comp is None or np.isfinite(comp.get(code, np.nan)))
               and (remote is None or np.isfinite(remote.get(code, np.nan)))]
    young, older = panel_arrays(panel, support, months)
    weights = (young + older).sum(axis=1)
    ai = np.array([exposure[code] for code in support], dtype=float)
    ai_mean, ai_sd = weighted_scale(ai, weights) if ai_reference is None else ai_reference
    ai_z = (ai - ai_mean) / ai_sd
    post = np.array([month >= "2023-01" for month in months])
    columns, labels = [], []
    target = 0
    if scale == "q5_q1":
        q = weighted_quintiles(ai, weights)
        for value in (2, 3, 4, 5):
            columns.append(((q[:, None] == value) & post[None, :]).reshape(-1).astype(float))
            labels.append(f"AI_Q{value}_x_post")
        target = 3
    elif scale == "per_sd":
        columns.append((ai_z[:, None] * post[None, :]).reshape(-1))
        labels.append("AI_z_x_post")
    else:
        raise ValueError(scale)
    if comp is not None:
        values = np.array([comp[code] for code in support], dtype=float)
        mean, sd = weighted_scale(values, weights)
        columns.append((((values - mean) / sd)[:, None] * post[None, :]).reshape(-1))
        labels.append("computerization_z_x_post")
    if remote is not None:
        values = np.array([remote[code] for code in support], dtype=float)
        mean, sd = weighted_scale(values, weights)
        columns.append((((values - mean) / sd)[:, None] * post[None, :]).reshape(-1))
        labels.append("remote_z_x_post")
    return {"occupations": support, "young": young, "older": older,
            "regressors": np.column_stack(columns), "labels": labels,
            "target": target, "weights": weights, "ai_z": ai_z}


def estimate_static(panel, base_occupations, months, exposure, comp=None, remote=None,
                    scale="q5_q1", seed=BOOTSTRAP_SEED, ai_reference=None):
    prepared = prepare_model(panel, base_occupations, months, exposure, comp, remote,
                             scale, ai_reference)
    fit, influence = fit_with_influence(prepared["young"], prepared["older"],
                                        prepared["regressors"])
    coefficients = {}
    for index, label in enumerate(prepared["labels"]):
        summary, _, _ = bootstrap_summary(fit, influence, index, seed + index)
        coefficients[label] = summary
    return {"scale": scale, "occupations": len(prepared["occupations"]),
            "months": len(months), "labels": prepared["labels"],
            "target_label": prepared["labels"][prepared["target"]],
            "coefficients": coefficients}, prepared, fit, influence


def paired_beta_alpha(panel, base_occupations, months, exposures, comp):
    common = [code for code in base_occupations
              if np.isfinite(exposures["dv_rating_beta"]["A"].get(code, np.nan))
              and np.isfinite(exposures["dv_rating_alpha"]["A"].get(code, np.nan))
              and np.isfinite(comp.get(code, np.nan))]
    fitted = {}
    for measure in ("dv_rating_beta", "dv_rating_alpha"):
        prepared = prepare_model(panel, common, months, exposures[measure]["A"], comp,
                                 scale="q5_q1")
        fit, influence = fit_with_influence(prepared["young"], prepared["older"],
                                            prepared["regressors"])
        fitted[measure] = (prepared, fit, influence)
    rng = np.random.default_rng(PAIRED_SEED)
    signs = rng.choice(np.array([-1.0, 1.0]), size=(BOOTSTRAP_DRAWS, len(common)))
    draws = {}
    estimates = {}
    for measure, (prepared, fit, influence) in fitted.items():
        target = prepared["target"]
        estimates[measure] = float(fit.beta[target])
        draws[measure] = estimates[measure] + signs @ influence[:, target]
    delta = estimates["dv_rating_beta"] - estimates["dv_rating_alpha"]
    centered = (draws["dv_rating_beta"] - draws["dv_rating_alpha"]) - delta
    se = float(np.std(centered, ddof=1))
    critical = float(np.quantile(np.abs(centered / se), 0.95, method="higher"))
    pvalue = float((1 + np.sum(np.abs(centered / se) >= abs(delta / se)))
                   / (BOOTSTRAP_DRAWS + 1))
    return {"pair": "dv_rating_beta-minus-dv_rating_alpha", "scale": "q5_q1",
            "support": "Rule A pairwise common support with Webb",
            "occupations": len(common), "beta_primary": estimates["dv_rating_beta"],
            "alpha_contrast": estimates["dv_rating_alpha"], "delta": delta,
            "paired_se_delta": se, "paired_ci_lower": delta - critical * se,
            "paired_ci_upper": delta + critical * se, "paired_p_value": pvalue,
            "paired_critical": critical, "common_bootstrap_draws": BOOTSTRAP_DRAWS,
            "seed": PAIRED_SEED, "paired_covariance": float(np.cov(
                draws["dv_rating_beta"], draws["dv_rating_alpha"], ddof=1)[0, 1]),
            "centered_delta_draws": centered.tolist(),
            "mde_delta_80_relative": 0.032722,
            "interpretation_rule": "CI includes zero => does not detect a difference; never equivalence"}


def estimate_event(panel, base_occupations, months, exposure, comp):
    support = [code for code in base_occupations
               if np.isfinite(exposure.get(code, np.nan)) and np.isfinite(comp.get(code, np.nan))]
    young, older = panel_arrays(panel, support, months)
    weights = (young + older).sum(axis=1)
    ai = np.array([exposure[c] for c in support], float)
    cv = np.array([comp[c] for c in support], float)
    am, astd = weighted_scale(ai, weights)
    cm, cstd = weighted_scale(cv, weights)
    ai, cv = (ai - am) / astd, (cv - cm) / cstd
    event_months = [month for month in months if month != EVENT_REFERENCE]
    columns = []
    for month in event_months:
        indicator = np.array([value == month for value in months])
        columns.append((ai[:, None] * indicator[None, :]).reshape(-1))
    for month in event_months:
        indicator = np.array([value == month for value in months])
        columns.append((cv[:, None] * indicator[None, :]).reshape(-1))
    fit, influence = fit_with_influence(young, older, np.column_stack(columns))
    rng = np.random.default_rng(BOOTSTRAP_SEED + 7000)
    signs = rng.choice(np.array([-1.0, 1.0]), size=(BOOTSTRAP_DRAWS, len(support)))
    shifts = signs @ influence[:, :len(event_months)]
    rows = []
    for index, month in enumerate(event_months):
        se = float(fit.standard_error[index])
        critical = float(np.quantile(np.abs(shifts[:, index] / se), 0.95, method="higher"))
        coefficient = float(fit.beta[index])
        rows.append({"event_month": month, "coefficient": coefficient,
                     "ci_lower": coefficient - critical * se,
                     "ci_upper": coefficient + critical * se,
                     "placebo_indicator": month < "2022-12"})
    rows.append({"event_month": EVENT_REFERENCE, "coefficient": 0.0,
                 "ci_lower": 0.0, "ci_upper": 0.0, "placebo_indicator": True,
                 "reference": True})
    return {"support": "beta Rule A with Webb", "scale": "per weighted SD",
            "reference_month": EVENT_REFERENCE, "occupations": len(support),
            "bootstrap_draws": BOOTSTRAP_DRAWS, "rows": sorted(rows, key=lambda x: x["event_month"])}


def estimate_placebo(panel, base_occupations, exposure, comp):
    months = [month for month in sorted(panel.index.get_level_values("month").unique())
              if "2017-01" <= month <= "2019-12"]
    support = [code for code in base_occupations
               if np.isfinite(exposure.get(code, np.nan)) and np.isfinite(comp.get(code, np.nan))]
    young, older = panel_arrays(panel, support, months)
    exists = (young.sum(axis=1) > 0) & (older.sum(axis=1) > 0)
    dropped_nonexistent_mle = [code for code, keep in zip(support, exists) if not keep]
    support = [code for code, keep in zip(support, exists) if keep]
    young, older = young[exists], older[exists]
    weights = (young + older).sum(axis=1)
    ai = np.array([exposure[c] for c in support], float)
    cv = np.array([comp[c] for c in support], float)
    ai = (ai - weighted_scale(ai, weights)[0]) / weighted_scale(ai, weights)[1]
    cv = (cv - weighted_scale(cv, weights)[0]) / weighted_scale(cv, weights)[1]
    post = np.array([month >= "2018-11" for month in months])
    x = np.column_stack([(ai[:, None] * post).reshape(-1),
                         (cv[:, None] * post).reshape(-1)])
    fit, influence = fit_with_influence(young, older, x)
    summary, _, _ = bootstrap_summary(fit, influence, 0, BOOTSTRAP_SEED + 8000)
    return {"window": [months[0], months[-1]], "placebo_post": "2018-11",
            "occupations": len(support), "ai": summary,
            "computerization_coefficient": float(fit.beta[1]),
            "dropped_for_nonexistent_fixed_effect_mle": dropped_nonexistent_mle,
            "existence_rule": "positive placebo-window employment stock in both age groups"}


def estimate_extension(panel, base_occupations, months, exposure, comp):
    support = [code for code in base_occupations
               if np.isfinite(exposure.get(code, np.nan)) and np.isfinite(comp.get(code, np.nan))]
    young, older = panel_arrays(panel, support, months)
    weights = (young + older).sum(axis=1)
    ai = np.array([exposure[c] for c in support], float)
    cv = np.array([comp[c] for c in support], float)
    ai = (ai - weighted_scale(ai, weights)[0]) / weighted_scale(ai, weights)[1]
    cv = (cv - weighted_scale(cv, weights)[0]) / weighted_scale(cv, weights)[1]
    early = np.array(["2023-01" <= month <= "2024-12" for month in months])
    extension = np.array([month >= "2025-01" for month in months])
    x = np.column_stack([(ai[:, None] * early).reshape(-1),
                         (ai[:, None] * extension).reshape(-1),
                         (cv[:, None] * early).reshape(-1),
                         (cv[:, None] * extension).reshape(-1)])
    fit, influence = fit_with_influence(young, older, x)
    rng = np.random.default_rng(BOOTSTRAP_SEED + 9000)
    signs = rng.choice(np.array([-1.0, 1.0]), size=(BOOTSTRAP_DRAWS, len(support)))
    centered = signs @ (influence[:, 1] - influence[:, 0])
    difference = float(fit.beta[1] - fit.beta[0])
    se = float(np.std(centered, ddof=1))
    pvalue = float((1 + np.sum(np.abs(centered / se) >= abs(difference / se)))
                   / (BOOTSTRAP_DRAWS + 1))
    return {"early_window": ["2023-01", "2024-12"],
            "extension_window": ["2025-01", "2026-07"],
            "ai_early": float(fit.beta[0]), "ai_extension": float(fit.beta[1]),
            "extension_minus_early": difference, "wald_bootstrap_p": pvalue,
            "occupations": len(support)}


def result_ledger(results, inputs):
    rows = []
    def add(table, spec, measure, outcome, support, item, extra=None):
        rows.append({"table_figure": table, "specification_id": spec,
                     "exposure_measure": measure, "outcome": outcome,
                     "sample_support": support, "coefficient": item.get("coefficient"),
                     "se": item.get("bootstrap_se", item.get("analytic_cluster_se")),
                     "ci_lower": item.get("ci_lower"), "ci_upper": item.get("ci_upper"),
                     "p_value": item.get("bootstrap_p_value"),
                     "bootstrap_draws": item.get("bootstrap_draws"),
                     "converged": item.get("converged"), "input_hashes": inputs,
                     "frozen_commit": FROZEN_COMMIT, **(extra or {})})
    for spec, model in results["headline"].items():
        add("Table 2", spec, spec.split("__")[0], "employment_stock",
            f"{model['occupations']} occupations", model["coefficients"][model["target_label"]])
    for spec, model in results["remote"].items():
        add("Table 6", spec, spec, "employment_stock",
            f"{model['occupations']} occupations", model["coefficients"][model["target_label"]])
    pair = results["paired_test_c"]
    rows.append({"table_figure": "Table 4", "specification_id": pair["pair"],
                 "exposure_measure": "beta-minus-alpha", "outcome": "employment_stock",
                 "sample_support": pair["support"], "coefficient": pair["delta"],
                 "se": pair["paired_se_delta"], "ci_lower": pair["paired_ci_lower"],
                 "ci_upper": pair["paired_ci_upper"], "p_value": pair["paired_p_value"],
                 "paired_delta": pair["delta"], "mde_comparison": 0.032722,
                 "bootstrap_draws": pair["common_bootstrap_draws"],
                 "input_hashes": inputs, "frozen_commit": FROZEN_COMMIT})
    return rows


def write_outputs(output_dir: pathlib.Path, results: dict, ledger: list[dict]):
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "FROZEN_RESULTS.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8")
    with (output_dir / "RESULT_LEDGER.jsonl").open("w", encoding="utf-8") as handle:
        for row in ledger:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    lines = ["# YAX v1.1 frozen confirmatory results", "",
             f"Generated {results['generated_at_utc']} from `{FROZEN_COMMIT}`.", "",
             "## Headline Q5-Q1 estimates", "",
             "| specification | coefficient | bootstrap 95% CI | p | occupations |",
             "|---|---:|---:|---:|---:|"]
    for spec, model in results["headline"].items():
        item = model["coefficients"][model["target_label"]]
        lines.append(f"| {spec} | {item['coefficient']:.4f} | "
                     f"[{item['ci_lower']:.4f}, {item['ci_upper']:.4f}] | "
                     f"{item['bootstrap_p_value']:.3f} | {model['occupations']} |")
    pair = results["paired_test_c"]
    lines += ["", "## Paired Test C", "",
              f"β − α = {pair['delta']:.4f}; paired 95% CI "
              f"[{pair['paired_ci_lower']:.4f}, {pair['paired_ci_upper']:.4f}]; "
              f"p = {pair['paired_p_value']:.3f}. The frozen paired MDE80 is 3.326%.",
              "", "Failure to detect a difference is not economic equivalence.", ""]
    (output_dir / "FROZEN_RESULTS.md").write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict:
    authenticated = validate_inputs(args)
    pre, occupations, pre_months = read_preperiod(args.preperiod_cells)
    post, post_receipt = read_post_cells(args.microdata, occupations)
    panel = pd.concat([pre, post]).sort_index()
    all_months = pre_months + [TRANSITION, *EXPECTED_POST]
    static_months = [month for month in all_months if month != TRANSITION]
    exposures = exposure_maps(args.lookup, args.rule_b_values)
    computers, names, major_groups = comp_maps(args.computerization)
    del names

    headline = {}
    for measure in ("dv_rating_beta", "dv_rating_alpha"):
        for rule in ("A", "B", "C"):
            for comp_measure in ("webb_pct_software", "onet_computers_importance"):
                key = f"{measure}__Rule{rule}__{comp_measure}__q5_q1"
                model, *_ = estimate_static(panel, occupations, static_months,
                                            exposures[measure][rule], computers[comp_measure])
                headline[key] = model

    alternatives = {}
    for measure in AI_MEASURES:
        model, *_ = estimate_static(panel, occupations, static_months,
                                    exposures[measure]["A"], computers["webb_pct_software"])
        alternatives[f"{measure}__RuleA__webb__q5_q1"] = model
    for comp_measure in COMP_MEASURES:
        model, *_ = estimate_static(panel, occupations, static_months,
                                    exposures["dv_rating_beta"]["A"], computers[comp_measure])
        alternatives[f"dv_rating_beta__RuleA__{comp_measure}__q5_q1"] = model

    remote = {}
    remote_map = exposures["dingel_neiman_telework"]["A"]
    for measure in ("dv_rating_beta", "dv_rating_alpha"):
        ai_only, *_ = estimate_static(panel, occupations, static_months,
                                      exposures[measure]["A"], scale="per_sd")
        joint, *_ = estimate_static(panel, occupations, static_months,
                                    exposures[measure]["A"], remote=remote_map, scale="per_sd")
        remote[f"{measure}__ai_only"] = ai_only
        remote[f"{measure}__ai_remote_joint"] = joint
    remote_only, *_ = estimate_static(panel, occupations, static_months,
                                      remote_map, scale="per_sd")
    remote["remote_only"] = remote_only

    # Frozen four-row mapping decomposition, one repaired-support scale.
    repaired = exposures["aioe_admin_equal"]["A"]
    exact = exposures["aioe_exact_code_baseline"]["A"]
    webb = computers["webb_pct_software"]
    expanded = [code for code in occupations
                if np.isfinite(repaired.get(code, np.nan)) and np.isfinite(webb.get(code, np.nan))]
    y_ref, o_ref = panel_arrays(panel, expanded, static_months)
    w_ref = (y_ref + o_ref).sum(axis=1)
    v_ref = np.array([repaired[code] for code in expanded], float)
    fixed_reference = weighted_scale(v_ref, w_ref)
    original = [code for code in expanded if np.isfinite(exact.get(code, np.nan))]
    no_group15 = [code for code in expanded if major_groups.get(code) != "15"]
    crosswalk_decomposition = {}
    for row_id, support, measure_map, label in (
        (1, original, exact, "original exposure, original support"),
        (2, original, repaired, "repaired exposure, original support"),
        (3, expanded, repaired, "repaired exposure, expanded support"),
        (4, no_group15, repaired, "repaired exposure, expanded support, group 15 excluded"),
    ):
        model, *_ = estimate_static(panel, support, static_months, measure_map, webb,
                                    scale="per_sd", ai_reference=fixed_reference,
                                    seed=BOOTSTRAP_SEED + 10000 + row_id)
        crosswalk_decomposition[str(row_id)] = {"label": label, **model}

    results = {
        "record_version": "yax-frozen-postoutcome-v11-first-run",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "frozen_commit": FROZEN_COMMIT, "frozen_tag": FROZEN_TAG,
        "implementation_commit": authenticated["head"],
        "first_authorized_post_outcome_access": True,
        "inputs": authenticated["hashes"], "post_cell_build": post_receipt,
        "design": {"unit": "occupation x age-group x month employment stock",
                   "young": "22-25", "comparison": "26-65",
                   "static_post": ["2023-01", "2026-07"],
                   "transition_excluded_static": TRANSITION,
                   "event_reference": EVENT_REFERENCE, "gap": "2025-10",
                   "estimator": "grouped-binomial conditional equivalent of frozen PPML",
                   "fixed_effects": ["occupation x age-group", "occupation x month",
                                     "age-group x month"],
                   "inference": "occupation-cluster Rademacher wild score bootstrap",
                   "bootstrap_draws": BOOTSTRAP_DRAWS},
        "headline": headline, "alternative_exposures_and_controls": alternatives,
        "paired_test_c": paired_beta_alpha(panel, occupations, static_months,
                                            exposures, computers["webb_pct_software"]),
        "remote": remote,
        "crosswalk_decomposition": crosswalk_decomposition,
        "event_study": estimate_event(panel, occupations, all_months,
                                      exposures["dv_rating_beta"]["A"],
                                      computers["webb_pct_software"]),
        "placebo_2017_2019": estimate_placebo(panel, occupations,
                                              exposures["dv_rating_beta"]["A"],
                                              computers["webb_pct_software"]),
        "post_2025_extension": estimate_extension(panel, occupations, static_months,
                                                   exposures["dv_rating_beta"]["A"],
                                                   computers["webb_pct_software"]),
        "interpretation_limit": (
            "Employment-stock movements combine entry, exit, and occupational switching; "
            "they are not individual employment-probability effects."
        ),
    }
    ledger = result_ledger(results, authenticated["hashes"])
    write_outputs(args.output_dir, results, ledger)
    return results


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--microdata", type=pathlib.Path, required=True)
    parser.add_argument("--preperiod-cells", type=pathlib.Path, required=True)
    parser.add_argument("--lookup", type=pathlib.Path, required=True)
    parser.add_argument("--computerization", type=pathlib.Path, required=True)
    parser.add_argument("--rule-b-values", type=pathlib.Path, required=True)
    parser.add_argument("--first-access-receipt", type=pathlib.Path, required=True)
    parser.add_argument("--output-dir", type=pathlib.Path, required=True)
    args = parser.parse_args(argv)
    result = run(args)
    print(json.dumps({"status": "PASS_FROZEN_ANALYSIS_COMPLETE",
                      "output": str(args.output_dir),
                      "headline_models": len(result["headline"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
