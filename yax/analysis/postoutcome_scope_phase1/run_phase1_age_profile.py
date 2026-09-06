#!/usr/bin/env python3
"""Run the single pre-declared YAX Phase-1 flexible age-profile model.

POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1.

This script implements one grouped multinomial conditional-PPML model. It does
not estimate CPS transition outcomes or modify confirmatory artifacts.
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
from scipy import optimize, sparse
from scipy.sparse import linalg as splinalg
from scipy.special import logsumexp


LABEL = "POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1"
AGE_GROUPS = ("18-21", "22-25", "26-30", "31-40", "41-50", "51-65")
REFERENCE = "51-65"
NONREFERENCE = AGE_GROUPS[:-1]
BOOTSTRAP_DRAWS = 999
BOOTSTRAP_SEED = 20260901
PRIMARY_SUPPORT_HASH = "11ec58ab1004cd83d62c57785f6c0dd3ee5a8abf08b7f71a3b664e91ded8333b"
ROOT = pathlib.Path(__file__).resolve().parents[3]
FROZEN_PATH = ROOT / "yax/analysis/run_frozen_v11.py"
SPEC = importlib.util.spec_from_file_location("yax_phase1_frozen", FROZEN_PATH)
FROZEN = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = FROZEN
SPEC.loader.exec_module(FROZEN)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def support_hash(codes: list[str]) -> str:
    return hashlib.sha256("".join(f"{code}\n" for code in sorted(codes)).encode()).hexdigest()


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def age_group(age: pd.Series) -> pd.Categorical:
    return pd.cut(
        age,
        bins=[17, 21, 25, 30, 40, 50, 65],
        labels=AGE_GROUPS,
        include_lowest=True,
        right=True,
    )


def read_age_cells(
    microdata: pathlib.Path,
    bridge_path: pathlib.Path,
    support: list[str],
    expected_months: list[str],
) -> tuple[pd.DataFrame, dict]:
    """Build occupation x month x six-age-bin employment stocks."""
    bridge = pd.read_csv(
        bridge_path,
        dtype={"census_2010": str, "census_2018": str},
    )
    bridge["census_2010"] = bridge.census_2010.str.zfill(4)
    bridge["census_2018"] = bridge.census_2018.str.zfill(4)
    bridge["bridge_weight"] = pd.to_numeric(bridge.bridge_weight, errors="raise")
    gaps = {f"{year}-03" for year in range(2017, 2022)}
    pieces: list[pd.DataFrame] = []
    counters = {
        "rows_read": 0,
        "rows_employed_age_18_65": 0,
        "probabilistically_expanded_rows": 0,
    }
    for chunk in pd.read_csv(
        microdata,
        usecols=["YEAR", "MONTH", "AGE", "EMPSTAT", "OCC", "WTFINL"],
        chunksize=500_000,
    ):
        counters["rows_read"] += len(chunk)
        chunk["month"] = (
            chunk.YEAR.astype(int).astype(str)
            + "-"
            + chunk.MONTH.astype(int).astype(str).str.zfill(2)
        )
        chunk = chunk.loc[~chunk.month.isin(gaps)].copy()
        age = pd.to_numeric(chunk.AGE, errors="coerce")
        weight = pd.to_numeric(chunk.WTFINL, errors="coerce")
        keep = (
            age.between(18, 65)
            & pd.to_numeric(chunk.EMPSTAT, errors="coerce").isin([10, 12])
            & np.isfinite(weight)
            & weight.gt(0)
        )
        chunk = chunk.loc[keep].copy()
        counters["rows_employed_age_18_65"] += len(chunk)
        occ = pd.to_numeric(chunk.OCC, errors="coerce")
        chunk = chunk.loc[occ.notna() & occ.between(0, 9999) & occ.mod(1).eq(0)].copy()
        chunk["source_occ"] = occ.loc[chunk.index].astype(int).map(lambda value: f"{value:04d}")
        chunk["age_group"] = age_group(pd.to_numeric(chunk.AGE, errors="coerce"))

        early = chunk.loc[chunk.YEAR.le(2019)].merge(
            bridge,
            left_on="source_occ",
            right_on="census_2010",
            how="inner",
            validate="many_to_many",
        )
        early["occ_code"] = early.census_2018
        early["cell_weight"] = early.WTFINL * early.bridge_weight
        counters["probabilistically_expanded_rows"] += len(early)

        current = chunk.loc[chunk.YEAR.ge(2020)].copy()
        current["occ_code"] = current.source_occ
        current["cell_weight"] = current.WTFINL
        routed = pd.concat(
            [
                early[["occ_code", "month", "age_group", "cell_weight"]],
                current[["occ_code", "month", "age_group", "cell_weight"]],
            ],
            ignore_index=True,
        )
        routed = routed.loc[routed.occ_code.isin(support)]
        pieces.append(
            routed.groupby(
                ["occ_code", "month", "age_group"], observed=True, as_index=False
            ).cell_weight.sum()
        )

    grouped = pd.concat(pieces, ignore_index=True).groupby(
        ["occ_code", "month", "age_group"], observed=True, as_index=False
    ).cell_weight.sum()
    observed_months = sorted(grouped.month.unique())
    if observed_months != expected_months:
        raise RuntimeError(
            f"age-cell month support differs from frozen panel: {observed_months}"
        )
    index = pd.MultiIndex.from_product(
        [support, expected_months, AGE_GROUPS],
        names=["occ_code", "month", "age_group"],
    )
    cells = grouped.set_index(["occ_code", "month", "age_group"])
    cells = cells.reindex(index, fill_value=0.0).rename(
        columns={"cell_weight": "employment_stock"}
    )
    if cells.employment_stock.lt(0).any() or not np.isfinite(cells.employment_stock).all():
        raise RuntimeError("invalid employment stock")
    counters.update(
        {
            "occupations": len(support),
            "months": len(expected_months),
            "age_groups": len(AGE_GROUPS),
            "cell_rows": len(cells),
        }
    )
    return cells, counters


def build_design(
    cells: pd.DataFrame,
    support: list[str],
    months: list[str],
    quintiles: np.ndarray,
    webb_z: np.ndarray,
) -> tuple[np.ndarray, list[sparse.csr_matrix], list[dict]]:
    """Build category-specific sparse designs, pruning separated occ-age FEs."""
    y = (
        cells.employment_stock.unstack("age_group")
        .reindex(
            pd.MultiIndex.from_product([support, months], names=["occ_code", "month"]),
            fill_value=0.0,
        )[list(AGE_GROUPS)]
        .to_numpy(dtype=float)
    )
    n_occ, n_month = len(support), len(months)
    j = n_occ * n_month
    occ_index = np.repeat(np.arange(n_occ), n_month)
    month_index = np.tile(np.arange(n_month), n_occ)
    post = np.array([month >= "2023-01" for month in months], dtype=float)
    q_slopes = np.column_stack(
        [
            ((quintiles[:, None] == q) * post[None, :]).reshape(-1)
            for q in (2, 3, 4, 5)
        ]
    )
    webb_slope = (webb_z[:, None] * post[None, :]).reshape(-1, 1)
    slopes = np.column_stack([q_slopes, webb_slope])

    designs: list[sparse.csr_matrix] = []
    metadata: list[dict] = []
    totals_by_occ_age = y.reshape(n_occ, n_month, len(AGE_GROUPS)).sum(axis=1)
    for g_index, group in enumerate(NONREFERENCE):
        available_occ = totals_by_occ_age[:, g_index] > 0
        active_occ = np.flatnonzero(available_occ)
        occ_position = np.full(n_occ, -1, dtype=int)
        occ_position[active_occ] = np.arange(len(active_occ))
        active_row = available_occ[occ_index]
        rows = np.flatnonzero(active_row)
        cols_occ = occ_position[occ_index[rows]]
        occ_block = sparse.coo_matrix(
            (np.ones(len(rows)), (rows, cols_occ)),
            shape=(j, len(active_occ)),
        ).tocsr()
        if n_month > 1:
            month_rows = np.flatnonzero(active_row & (month_index > 0))
            month_block = sparse.coo_matrix(
                (
                    np.ones(len(month_rows)),
                    (month_rows, month_index[month_rows] - 1),
                ),
                shape=(j, n_month - 1),
            ).tocsr()
        else:
            month_block = sparse.csr_matrix((j, 0))
        slope_block = sparse.csr_matrix(slopes * active_row[:, None])
        design = sparse.hstack([occ_block, month_block, slope_block], format="csr")
        designs.append(design)
        metadata.append(
            {
                "age_group": group,
                "active_occupation_count": int(len(active_occ)),
                "separated_zero_stock_occupations": [
                    support[i] for i in np.flatnonzero(~available_occ)
                ],
                "nuisance_columns": int(len(active_occ) + n_month - 1),
                "slope_columns": ["Q2_x_post", "Q3_x_post", "Q4_x_post", "Q5_x_post", "Webb_z_x_post"],
                "slope_start": int(len(active_occ) + n_month - 1),
                "columns": int(design.shape[1]),
                "available_row_mask": active_row,
            }
        )
    return y, designs, metadata


def fit_multinomial(
    y: np.ndarray,
    designs: list[sparse.csr_matrix],
    metadata: list[dict],
    n_occ: int,
    maxiter: int = 10000,
) -> dict:
    """Fit joint multinomial QMLE and return clustered slope influence."""
    n = y.sum(axis=1)
    if np.any(n < 0) or not np.any(n > 0):
        raise RuntimeError("occupation-month totals are invalid")
    sizes = [x.shape[1] for x in designs]
    offsets = np.cumsum([0, *sizes])
    scale = float(n.sum())

    def unpack(parameters: np.ndarray) -> list[np.ndarray]:
        return [parameters[offsets[k] : offsets[k + 1]] for k in range(len(designs))]

    def objective(parameters: np.ndarray) -> tuple[float, np.ndarray]:
        blocks = unpack(parameters)
        eta = np.zeros((len(n), len(AGE_GROUPS)), dtype=float)
        for k, (x, b, meta) in enumerate(zip(designs, blocks, metadata)):
            eta[:, k] = x @ b
            eta[~meta["available_row_mask"], k] = -np.inf
        logden = logsumexp(eta, axis=1)
        loglike = np.sum(y[:, :-1] * np.where(np.isfinite(eta[:, :-1]), eta[:, :-1], 0.0))
        loglike -= np.dot(n, logden)
        probability = np.exp(eta - logden[:, None])
        residual = n[:, None] * probability[:, :-1] - y[:, :-1]
        gradient = np.concatenate(
            [np.asarray(x.T @ residual[:, k]).reshape(-1) for k, x in enumerate(designs)]
        )
        return -float(loglike) / scale, gradient / scale

    start = np.zeros(sum(sizes), dtype=float)
    result = optimize.minimize(
        objective,
        start,
        method="L-BFGS-B",
        jac=True,
        options={"maxiter": maxiter, "ftol": 1e-15, "gtol": 1e-9, "maxls": 50},
    )
    if not result.success:
        raise RuntimeError(
            "multinomial optimization failed: "
            f"{result.message}; iterations={result.nit}; objective={result.fun:.12g}; "
            f"max_scaled_gradient={np.max(np.abs(result.jac)):.12g}"
        )
    blocks = unpack(result.x)
    eta = np.zeros((len(n), len(AGE_GROUPS)), dtype=float)
    for k, (x, b, meta) in enumerate(zip(designs, blocks, metadata)):
        eta[:, k] = x @ b
        eta[~meta["available_row_mask"], k] = -np.inf
    logden = logsumexp(eta, axis=1)
    probability = np.exp(eta - logden[:, None])
    if not np.isfinite(probability).all() or np.max(np.abs(probability.sum(axis=1) - 1)) > 1e-10:
        raise RuntimeError("invalid fitted multinomial probabilities")

    # Expected information in category-major parameter ordering.
    h_blocks: list[list[sparse.csr_matrix]] = []
    for g, xg in enumerate(designs):
        row = []
        for h, xh in enumerate(designs):
            weight = n * probability[:, g] * ((1.0 if g == h else 0.0) - probability[:, h])
            row.append((xg.T @ xh.multiply(weight[:, None])).tocsr())
        h_blocks.append(row)
    information = sparse.bmat(h_blocks, format="csc")

    slope_indices: list[int] = []
    target_indices: list[int] = []
    for k, meta in enumerate(metadata):
        begin = int(offsets[k] + meta["slope_start"])
        slope_indices.extend(range(begin, begin + 5))
        target_indices.append(begin + 3)
    nuisance_indices = np.setdiff1d(np.arange(information.shape[0]), slope_indices)
    h_nn = information[nuisance_indices, :][:, nuisance_indices].tocsc()
    h_nb = information[nuisance_indices, :][:, slope_indices].toarray()
    h_bb = information[slope_indices, :][:, slope_indices].toarray()
    factor = splinalg.splu(h_nn)
    nuisance_projection = factor.solve(h_nb)
    schur = h_bb - h_nb.T @ nuisance_projection
    bread = np.linalg.inv(schur)

    # Occupation-cluster scores, then nuisance-profiled slope scores.
    occ_index = np.repeat(np.arange(n_occ), len(n) // n_occ)
    group_matrix = sparse.coo_matrix(
        (np.ones(len(n)), (occ_index, np.arange(len(n)))),
        shape=(n_occ, len(n)),
    ).tocsr()
    score_parts = []
    for g, xg in enumerate(designs):
        residual = y[:, g] - n * probability[:, g]
        score_parts.append((group_matrix @ xg.multiply(residual[:, None])).toarray())
    scores = np.concatenate(score_parts, axis=1)
    score_n = scores[:, nuisance_indices]
    score_b = scores[:, slope_indices]
    efficient_score = score_b - score_n @ nuisance_projection
    influence_all = efficient_score @ bread.T
    influence_all *= math.sqrt(n_occ / (n_occ - 1))
    covariance = influence_all.T @ influence_all
    analytic_se_all = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    target_positions = [slope_indices.index(index) for index in target_indices]
    beta = result.x[target_indices]
    influence = influence_all[:, target_positions]
    analytic_se = analytic_se_all[target_positions]
    max_scaled_gradient = float(np.max(np.abs(result.jac)))
    max_scaled_slope_gradient = float(np.max(np.abs(result.jac[slope_indices])))
    max_scaled_target_gradient = float(np.max(np.abs(result.jac[target_indices])))
    return {
        "beta": beta,
        "analytic_se": analytic_se,
        "influence": influence,
        "converged": bool(result.success),
        "iterations": int(result.nit),
        "objective": float(result.fun),
        "max_scaled_gradient": max_scaled_gradient,
        "max_scaled_slope_gradient": max_scaled_slope_gradient,
        "max_scaled_target_gradient": max_scaled_target_gradient,
        "probability_min": float(probability.min()),
        "probability_max": float(probability.max()),
        "information_condition_number_slopes": float(np.linalg.cond(schur)),
        "zero_total_occupation_month_cells": int(np.sum(n == 0)),
    }


def inference_rows(fit: dict) -> tuple[list[dict], dict]:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    signs = rng.choice(np.array([-1.0, 1.0]), size=(BOOTSTRAP_DRAWS, fit["influence"].shape[0]))
    shifts = signs @ fit["influence"]
    rows = []
    for index, group in enumerate(NONREFERENCE):
        coefficient = float(fit["beta"][index])
        se = float(fit["analytic_se"][index])
        t_draw = np.abs(shifts[:, index] / se)
        critical = float(np.quantile(t_draw, 0.95, method="higher"))
        pvalue = float(
            (1 + np.sum(t_draw >= abs(coefficient / se))) / (BOOTSTRAP_DRAWS + 1)
        )
        rows.append(
            {
                "analysis_status": LABEL,
                "Age group": group,
                "coefficient": coefficient,
                "SE": se,
                "CI low": coefficient - critical * se,
                "CI high": coefficient + critical * se,
                "p": pvalue,
                "relative %": 100 * (math.exp(coefficient) - 1),
                "reference group": REFERENCE,
            }
        )
    rows.append(
        {
            "analysis_status": LABEL,
            "Age group": REFERENCE,
            "coefficient": 0.0,
            "SE": "",
            "CI low": "",
            "CI high": "",
            "p": "",
            "relative %": 0.0,
            "reference group": "normalized reference",
        }
    )
    return rows, {
        "draws": BOOTSTRAP_DRAWS,
        "seed": BOOTSTRAP_SEED,
        "common_cluster_multipliers": True,
        "centered_target_draws_sha256": hashlib.sha256(shifts.tobytes()).hexdigest(),
    }


def write_figure(rows: list[dict], confirmatory: dict, path: pathlib.Path) -> None:
    estimated = rows[:-1]
    labels = [row["Age group"] for row in estimated]
    values = np.array([row["coefficient"] for row in estimated], dtype=float)
    low = np.array([row["CI low"] for row in estimated], dtype=float)
    high = np.array([row["CI high"] for row in estimated], dtype=float)
    positions = np.arange(len(labels))
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ModuleNotFoundError:
        # SCC's lean analysis environment has gnuplot but not matplotlib.
        data_path = path.with_suffix(".plot.tsv")
        script_path = path.with_suffix(".plot.gnuplot")
        data_path.write_text(
            "\n".join(
                f"{index}\t{value:.12g}\t{lo:.12g}\t{hi:.12g}\t{label}"
                for index, (value, lo, hi, label) in enumerate(zip(values, low, high, labels))
            )
            + "\n",
            encoding="utf-8",
        )
        safe_output = str(path).replace("'", "''")
        safe_data = str(data_path).replace("'", "''")
        script_path.write_text(
            "\n".join(
                [
                    "set terminal pngcairo size 1892,1188 enhanced font 'Arial,18'",
                    f"set output '{safe_output}'",
                    "set title 'Age profile of the beta Q5-versus-Q1 post-2022 employment-stock gradient'",
                    "set xlabel 'Age group (reference: 51-65)'",
                    "set ylabel 'Log-point coefficient'",
                    "set grid ytics lc rgb '#dddddd'",
                    "set xzeroaxis lc rgb '#555555' lw 1",
                    "set xrange [-0.5:4.5]",
                    "set xtics ('18-21' 0, '22-25' 1, '26-30' 2, '31-40' 3, '41-50' 4)",
                    "set key outside bottom center horizontal",
                    "set label 1 'POST-OUTCOME EXPLORATORY - NOT PART OF CONFIRMATORY YAX v1.1' at graph 0.01,0.02 front font ',10' textcolor rgb '#666666'",
                    f"confirm={float(confirmatory['coefficient']):.12g}",
                    f"plot '{safe_data}' using 1:2:3:4 with yerrorbars pt 7 ps 1.2 lw 2 lc rgb '#1f4e79' title 'Exploratory age-specific Q5-Q1 post gradient', \\",
                    "     '+' using (1):(confirm) with points pt 13 ps 1.5 lc rgb '#b34700' title 'Confirmatory pooled-older benchmark - different comparison group'",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        subprocess.run(["gnuplot", str(script_path)], check=True)
        data_path.unlink()
        script_path.unlink()
        return

    fig, ax = plt.subplots(figsize=(8.6, 5.4), constrained_layout=True)
    ax.axhline(0, color="#555555", linewidth=1)
    ax.errorbar(
        positions,
        values,
        yerr=np.vstack([values - low, high - values]),
        fmt="o",
        color="#1f4e79",
        ecolor="#1f4e79",
        capsize=4,
        linewidth=1.5,
        label="Exploratory age-specific Q5–Q1 post gradient",
    )
    ax.scatter(
        [1],
        [confirmatory["coefficient"]],
        marker="D",
        color="#b34700",
        zorder=4,
        label="Confirmatory pooled-older benchmark — different comparison group",
    )
    ax.set_xticks(positions, labels)
    ax.set_xlabel("Age group (reference: 51–65)")
    ax.set_ylabel("Log-point coefficient")
    ax.set_title("Age profile of the beta Q5-versus-Q1 post-2022 employment-stock gradient")
    ax.legend(frameon=False, fontsize=8, loc="best")
    ax.text(
        0.01,
        0.01,
        LABEL,
        transform=ax.transAxes,
        fontsize=7,
        color="#666666",
        va="bottom",
    )
    fig.savefig(path, dpi=220)
    plt.close(fig)


def run(args: argparse.Namespace) -> dict:
    authenticated = FROZEN.validate_inputs(args)
    frozen_pre, frozen_support, pre_months = FROZEN.read_preperiod(args.preperiod_cells)
    exposures = FROZEN.exposure_maps(args.lookup, args.rule_b_values)
    computers, _, _ = FROZEN.comp_maps(args.computerization)
    beta = exposures["dv_rating_beta"]["A"]
    webb = computers["webb_pct_software"]
    support = [
        code
        for code in frozen_support
        if np.isfinite(beta.get(code, np.nan)) and np.isfinite(webb.get(code, np.nan))
    ]
    if len(support) != 468 or support_hash(support) != PRIMARY_SUPPORT_HASH:
        raise RuntimeError("primary 468-occupation support mismatch")
    all_months = [*pre_months, FROZEN.TRANSITION, *FROZEN.EXPECTED_POST]
    static_months = [month for month in all_months if month != FROZEN.TRANSITION]
    cells, build_receipt = read_age_cells(args.microdata, args.bridge, support, all_months)
    static_cells = cells.loc[(support, static_months, AGE_GROUPS), :]

    # The treatment classification is fixed from ages 22-65 pre-period stocks.
    pre_weights = frozen_pre.loc[(support, pre_months), ["young_22_25", "older_26_65"]]
    pre_weights = pre_weights.groupby(level="occ_code").sum().sum(axis=1).reindex(support).to_numpy()
    beta_values = np.array([beta[code] for code in support], dtype=float)
    quintiles = FROZEN.weighted_quintiles(beta_values, pre_weights)

    # Preserve the historical Webb scaling: all static months, ages 22-65.
    wide = static_cells.employment_stock.unstack("age_group")
    full_weights = wide[["22-25", "26-30", "31-40", "41-50", "51-65"]].sum(axis=1)
    full_weights = full_weights.groupby(level="occ_code").sum().reindex(support).to_numpy()
    webb_values = np.array([webb[code] for code in support], dtype=float)
    webb_mean, webb_sd = FROZEN.weighted_scale(webb_values, full_weights)
    webb_z = (webb_values - webb_mean) / webb_sd

    # Historical Q5 membership comparison.
    historical_q = FROZEN.weighted_quintiles(beta_values, full_weights)
    q5_pre = {code for code, q in zip(support, quintiles) if q == 5}
    q5_historical = {code for code, q in zip(support, historical_q) if q == 5}

    y, designs, metadata = build_design(
        static_cells, support, static_months, quintiles, webb_z
    )
    fit = fit_multinomial(y, designs, metadata, len(support))
    rows, bootstrap = inference_rows(fit)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result_csv = args.output_dir / "YAX_AGE_PROFILE_RESULTS.csv"
    with result_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    frozen_results = json.loads(
        (ROOT / "yax/analysis/outcomes/frozen_v11_corrected_run/FROZEN_RESULTS.json").read_text()
    )
    primary_key = "dv_rating_beta__RuleA__webb_pct_software__q5_q1"
    confirmatory = frozen_results["headline"][primary_key]["coefficients"]["AI_Q5_x_post"]
    figure_path = args.output_dir / "figure_age_experience_profile.png"
    write_figure(rows, confirmatory, figure_path)

    receipt = {
        "record": "YAX Phase 1 age-profile implementation receipt",
        "analysis_status": LABEL,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "preanalysis_plan_commit": args.plan_commit,
        "execution_head": git_head(),
        "new_outcome_regressions_executed": [
            "one pre-declared grouped-multinomial conditional-PPML flexible age-profile model"
        ],
        "design": {
            "age_groups": list(AGE_GROUPS),
            "reference": REFERENCE,
            "sample": [static_months[0], static_months[-1]],
            "static_months": len(static_months),
            "transition_excluded": FROZEN.TRANSITION,
            "post_start": "2023-01",
            "occupation_support": len(support),
            "support_sha256": support_hash(support),
            "exposure": "dv_rating_beta Rule A strict",
            "control": "webb_pct_software",
            "quintile_weight_window": [pre_months[0], pre_months[-1]],
            "quintile_weight_population": "ages 22-65",
            "webb_weight_window": "108 static months, ages 22-65, historical primary scaling",
            "estimator": "joint grouped-multinomial conditional equivalent of saturated PPML",
            "fixed_effects": ["occupation x age bin", "occupation x month", "age bin x month"],
            "inference": "occupation-cluster analytic CRSE and 999-draw one-step Rademacher wild score",
        },
        "q5_membership_identical_to_historical": q5_pre == q5_historical,
        "q5_jaccard": len(q5_pre & q5_historical) / len(q5_pre | q5_historical),
        "age_cell_build": build_receipt,
        "separation_handling": [
            {key: value for key, value in item.items() if key != "available_row_mask"}
            for item in metadata
        ],
        "optimizer": {key: fit[key] for key in (
            "converged", "iterations", "objective", "max_scaled_gradient",
            "max_scaled_slope_gradient", "max_scaled_target_gradient",
            "probability_min", "probability_max", "information_condition_number_slopes",
            "zero_total_occupation_month_cells"
        )},
        "bootstrap": bootstrap,
        "input_hashes": authenticated["hashes"],
        "output_hashes": {
            result_csv.name: sha256(result_csv),
            figure_path.name: sha256(figure_path),
        },
        "confirmatory_benchmark": {
            "comparison": "22-25 versus pooled 26-65; different estimand",
            "coefficient": confirmatory["coefficient"],
        },
        "protected_confirmatory_artifacts_modified": False,
    }
    receipt_path = args.output_dir / "YAX_AGE_PROFILE_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, default=lambda value: value.tolist()) + "\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--microdata", required=True, type=pathlib.Path)
    parser.add_argument("--preperiod-cells", required=True, type=pathlib.Path)
    parser.add_argument("--plan-commit", required=True)
    parser.add_argument("--lookup", type=pathlib.Path, default=ROOT / "yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv")
    parser.add_argument("--computerization", type=pathlib.Path, default=ROOT / "yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv")
    parser.add_argument("--rule-b-values", type=pathlib.Path, default=ROOT / "yax/measurement/RULE_B_VALUES_CENSUS2018.csv")
    parser.add_argument("--bridge", type=pathlib.Path, default=ROOT / "yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv")
    parser.add_argument("--first-access-receipt", type=pathlib.Path, default=ROOT / "yax/analysis/FIRST_OUTCOME_ACCESS_RECEIPT.json")
    parser.add_argument("--output-dir", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent)
    args = parser.parse_args()
    receipt = run(args)
    print(json.dumps({"status": "PASS_PHASE1_AGE_PROFILE", "receipt": receipt["output_hashes"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
