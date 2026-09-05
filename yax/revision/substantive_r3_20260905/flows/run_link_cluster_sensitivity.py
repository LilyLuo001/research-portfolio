#!/usr/bin/env python3
"""Compute aggregate person/household score-cluster flow sensitivities.

This is the narrow post-outcome amendment registered in
HOUSEHOLD_CLUSTER_AMENDMENT_BEFORE_RESULTS.md. Restricted identifiers are used
only in memory; every written artifact is aggregate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import subprocess
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from run_flows_outcomes import (
    BOOTSTRAP_DRAWS,
    BOOTSTRAP_SEED,
    LABEL,
    MDE_MULTIPLIER,
    _sigmoid,
    _weighted_absorb,
    analysis_period,
    build_flow_cells,
    build_pairs,
    design_from_cells,
    load_corrected_frame,
    load_maps,
    sha256,
    write_csv,
    write_json,
)


AMENDMENT_COMMIT = "0501a789196c9a91d69e6a4c24484180764567c8"
CORE_MARGINS = [
    "employment_exit",
    "unemployment_entry",
    "labor_force_exit",
    "occupational_outflow",
    "entry_destination",
]
HORIZONS = ["adjacent_month", "twelve_month"]


def git(*args: str) -> str:
    root = pathlib.Path(__file__).resolve().parents[4]
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def _fit_offset_with_internals(
    young: np.ndarray,
    total: np.ndarray,
    occ: np.ndarray,
    month: np.ndarray,
    regressors: np.ndarray,
    offset: np.ndarray,
    max_iterations: int = 5_000,
) -> dict:
    """Exact companion to ``fit_offset`` retaining score ingredients."""
    keep = total > 0
    input_indices = np.flatnonzero(keep)
    y = young[keep]
    n = total[keep]
    o0 = occ[keep]
    t = month[keep]
    x = regressors[keep]
    off = offset[keep]
    used_occ = np.unique(o0)
    remap = {old: new for new, old in enumerate(used_occ)}
    o = np.array([remap[value] for value in o0], dtype=int)
    n_occ = len(used_occ)
    n_month = int(t.max()) + 1
    occ_y = np.bincount(o, weights=y, minlength=n_occ)
    occ_n = np.bincount(o, weights=n, minlength=n_occ)
    share = np.clip((occ_y + 0.5) / (occ_n + 1.0), 1e-8, 1 - 1e-8)
    mean_offset = np.divide(
        np.bincount(o, weights=n * off, minlength=n_occ),
        occ_n,
        out=np.zeros(n_occ),
        where=occ_n > 0,
    )
    occ_effect = np.log(share / (1 - share)) - mean_offset
    month_effect = np.zeros(n_month)
    beta = np.zeros(x.shape[1])
    for iteration in range(1, max_iterations + 1):
        for _ in range(2):
            eta = off + occ_effect[o] + month_effect[t] + x @ beta
            p = np.clip(_sigmoid(eta), 1e-10, 1 - 1e-10)
            residual = y - n * p
            info_w = np.maximum(n * p * (1 - p), 1e-12)
            score = np.bincount(o, weights=residual, minlength=n_occ)
            info = np.bincount(o, weights=info_w, minlength=n_occ)
            occ_effect += np.clip(
                np.divide(score, info, out=np.zeros_like(score), where=info > 0),
                -1,
                1,
            )
            eta = off + occ_effect[o] + month_effect[t] + x @ beta
            p = np.clip(_sigmoid(eta), 1e-10, 1 - 1e-10)
            residual = y - n * p
            info_w = np.maximum(n * p * (1 - p), 1e-12)
            score = np.bincount(t, weights=residual, minlength=n_month)
            info = np.bincount(t, weights=info_w, minlength=n_month)
            month_effect += np.clip(
                np.divide(score, info, out=np.zeros_like(score), where=info > 0),
                -1,
                1,
            )
            anchor = month_effect[0]
            month_effect -= anchor
            occ_effect += anchor
        eta = off + occ_effect[o] + month_effect[t] + x @ beta
        p = np.clip(_sigmoid(eta), 1e-10, 1 - 1e-10)
        residual = y - n * p
        info_w = np.maximum(n * p * (1 - p), 1e-12)
        rx = _weighted_absorb(x, info_w, o, t, n_occ, n_month)
        information = rx.T @ (info_w[:, None] * rx)
        score = rx.T @ residual
        step = np.clip(np.linalg.solve(information, score), -1, 1)
        beta += step
        eta_check = off + occ_effect[o] + month_effect[t] + x @ beta
        p_check = np.clip(_sigmoid(eta_check), 1e-10, 1 - 1e-10)
        residual_check = y - n * p_check
        info_check = np.maximum(n * p_check * (1 - p_check), 1e-12)
        rx_check = _weighted_absorb(x, info_check, o, t, n_occ, n_month)
        scale = max(1.0, float(n.sum()))
        fe_score = max(
            float(np.max(np.abs(np.bincount(o, weights=residual_check, minlength=n_occ)))),
            float(np.max(np.abs(np.bincount(t, weights=residual_check, minlength=n_month)))),
        ) / scale
        beta_score = float(np.max(np.abs(rx_check.T @ residual_check))) / scale
        if np.max(np.abs(step)) < 1e-8 and max(fe_score, beta_score) < 1e-9:
            break
    else:
        raise RuntimeError("conditional event-allocation refit did not converge")

    eta = off + occ_effect[o] + month_effect[t] + x @ beta
    p = np.clip(_sigmoid(eta), 1e-10, 1 - 1e-10)
    residual = y - n * p
    info_w = np.maximum(n * p * (1 - p), 1e-12)
    rx = _weighted_absorb(x, info_w, o, t, n_occ, n_month)
    bread = np.linalg.inv(rx.T @ (info_w[:, None] * rx))
    raw_scores = np.zeros((n_occ, x.shape[1]))
    np.add.at(raw_scores, o, rx * residual[:, None])
    return {
        "beta": beta,
        "p": p,
        "rx": rx,
        "bread": bread,
        "raw_influence": raw_scores @ bread.T,
        "used_occ_indices": used_occ,
        "input_indices": input_indices,
        "iterations": iteration,
    }


def fit_flow_with_internals(cells: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    data = design_from_cells(cells)
    panel = data["panel"]
    n_occ = len(data["occupations"])
    n_month = len(data["months"])
    event_y = (
        panel.xs("young_22_25", level="age_group").event.to_numpy().reshape(n_occ, n_month)
    )
    event_o = (
        panel.xs("older_26_65", level="age_group").event.to_numpy().reshape(n_occ, n_month)
    )
    if "risk" in panel:
        risk_y = (
            panel.xs("young_22_25", level="age_group").risk.to_numpy().reshape(n_occ, n_month)
        )
        risk_o = (
            panel.xs("older_26_65", level="age_group").risk.to_numpy().reshape(n_occ, n_month)
        )
        valid = (risk_y > 0) & (risk_o > 0)
        offset = np.log(
            np.clip(risk_y, 1e-12, None) / np.clip(risk_o, 1e-12, None)
        ).reshape(-1)
    else:
        valid = np.ones_like(event_y, dtype=bool)
        offset = np.zeros(event_y.size)
    total = (event_y + event_o).reshape(-1)
    total[~valid.reshape(-1)] = 0
    fit = _fit_offset_with_internals(
        event_y.reshape(-1),
        total,
        data["occ_index"],
        data["month_index"],
        data["regressors"],
        offset,
    )
    grid = pd.DataFrame(
        {
            "occ_code": np.repeat(data["occupations"], n_month),
            "month": np.tile(data["months"], n_occ),
        }
    ).iloc[fit["input_indices"]].copy()
    grid["p_young_event"] = fit["p"]
    for column in range(fit["rx"].shape[1]):
        grid[f"rx_{column}"] = fit["rx"][:, column]
    return fit, grid


def _route_event_records(
    selected: pd.DataFrame,
    occ_col: str,
    year_col: str,
    weight_col: str,
    bridge: pd.DataFrame,
    qmap: dict[str, int],
    webb_z: dict[str, float],
) -> pd.DataFrame:
    columns = [
        year_col,
        "month",
        "age_group",
        occ_col,
        "CPSID",
        "CPSIDV",
        weight_col,
    ]
    work = selected[columns].copy()
    if work.CPSIDV.le(0).any() or work.CPSID.le(0).any():
        raise RuntimeError("modeled event has a nonpositive person or household link identifier")
    work["event_id"] = np.arange(len(work), dtype=np.int64)
    work["event_weight"] = work[weight_col].astype(float)
    work["source_occ"] = work[occ_col].astype(int).map(lambda value: f"{value:04d}")
    early_base = work.loc[work[year_col].le(2019)].copy()
    current = work.loc[work[year_col].ge(2020)].copy()
    early = early_base.merge(
        bridge[["census_2010", "census_2018", "bridge_weight"]],
        left_on="source_occ",
        right_on="census_2010",
        how="inner",
        validate="many_to_many",
    )
    early["event_weight"] *= early.bridge_weight
    early["occ_code"] = early.census_2018
    current["occ_code"] = current.source_occ
    keep = [
        "occ_code",
        "month",
        "age_group",
        "CPSID",
        "CPSIDV",
        "event_id",
        "event_weight",
    ]
    routed = pd.concat([early[keep], current[keep]], ignore_index=True)
    routed["quintile"] = routed.occ_code.map(qmap)
    routed["webb_z"] = routed.occ_code.map(webb_z)
    routed = routed.loc[routed.quintile.notna() & routed.webb_z.notna()].copy()
    routed["quintile"] = routed.quintile.astype(int)
    return routed


def event_records_for_model(
    linked: pd.DataFrame,
    horizon: str,
    margin: str,
    bridge: pd.DataFrame,
    qmap: dict[str, int],
    webb_z: dict[str, float],
) -> pd.DataFrame:
    weight = "LNKFW1MWT" if horizon == "adjacent_month" else "LNKFW1YWT"
    if margin == "entry_destination":
        selected = linked.loc[
            analysis_period(linked, horizon)
            & linked.nonemployed
            & linked.employed_d
            & linked.OCC_d.gt(0)
        ].copy()
        return _route_event_records(
            selected, "OCC_d", "YEAR_d", weight, bridge, qmap, webb_z
        )

    base = linked.loc[
        analysis_period(linked, horizon) & linked.OCC.gt(0) & linked.employed
    ].copy()
    taxonomy_ok = base.month.ne("2019-12") if horizon == "adjacent_month" else base.YEAR.ne(2019)
    masks = {
        "employment_exit": base.nonemployed_d,
        "unemployment_entry": base.unemployed_d,
        "labor_force_exit": base.nilf_d,
        "occupational_outflow": (
            base.employed_d
            & base.OCC2010.gt(0)
            & base.OCC2010_d.gt(0)
            & taxonomy_ok
            & base.OCC2010.ne(base.OCC2010_d)
        ),
    }
    selected = base.loc[masks[margin]].copy()
    return _route_event_records(selected, "OCC", "YEAR", weight, bridge, qmap, webb_z)


def cluster_summary(influence: pd.Series, clusters: pd.Series) -> dict:
    grouped = pd.DataFrame({"influence": influence, "cluster": clusters}).groupby(
        "cluster", sort=False
    ).influence.sum()
    count = int(len(grouped))
    factor = math.sqrt(count / (count - 1)) if count > 1 else 1.0
    se = float(np.sqrt(np.sum(np.square(grouped.to_numpy()))) * factor)
    return {
        "clusters": count,
        "se": se,
        "ci_lower": None,
        "ci_upper": None,
        "mde80": float(MDE_MULTIPLIER * se),
    }


def _hash_rows(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args: argparse.Namespace) -> dict:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    frame, reconstruction = load_corrected_frame(
        args.microdata, args.repair_microdata, args.weight_patch
    )
    bridge, qmap, webb_z, components, mapping = load_maps(args.membership, args.bridge)
    del components
    fixed = pd.read_csv(args.fixed_results)
    fixed = fixed.loc[
        fixed.weighting.eq("official")
        & fixed.horizon.isin(HORIZONS)
        & fixed.model_id.str.replace("__official", "", regex=False).str.split("__").str[-1].isin(CORE_MARGINS)
    ].copy()
    # The string expression above is deliberately backed by an exact ID set.
    expected_ids = {
        f"{horizon}__{margin}__official"
        for horizon in HORIZONS
        for margin in CORE_MARGINS
    }
    fixed = fixed.loc[fixed.model_id.isin(expected_ids)].copy()
    if set(fixed.model_id) != expected_ids or len(fixed) != 10:
        raise RuntimeError("fixed official core-flow result set is not exactly ten models")
    fixed_by_id = fixed.set_index("model_id")
    saved_influence = pd.read_csv(args.fixed_influence, dtype={"occ_code": str})
    saved_influence["occ_code"] = saved_influence.occ_code.str.zfill(4)

    rows: list[dict] = []
    conservation: list[dict] = []
    link_counts: dict[str, dict] = {}
    for horizon in HORIZONS:
        pairs, linked, repeat = build_pairs(frame, horizon)
        del pairs
        link_counts[horizon] = repeat
        cells, _, _ = build_flow_cells(linked, horizon, bridge, qmap, webb_z)
        for margin in CORE_MARGINS:
            model_id = f"{horizon}__{margin}__official"
            fit, grid = fit_flow_with_internals(cells[(margin, "official")])
            target = 3
            beta = float(fit["beta"][target])
            stored = fixed_by_id.loc[model_id]
            beta_error = beta - float(stored.coefficient)
            if abs(beta_error) > 1e-10:
                raise RuntimeError(f"{model_id}: refit coefficient mismatch {beta_error}")

            events = event_records_for_model(
                linked, horizon, margin, bridge, qmap, webb_z
            )
            routed_event_weight = float(events.event_weight.sum())
            scored = events.merge(
                grid,
                on=["occ_code", "month"],
                how="inner",
                validate="many_to_one",
            )
            rx_columns = [f"rx_{index}" for index in range(fit["rx"].shape[1])]
            young_sign = np.where(
                scored.age_group.eq("young_22_25"),
                1.0 - scored.p_young_event.to_numpy(),
                -scored.p_young_event.to_numpy(),
            )
            score = (
                scored[rx_columns].to_numpy()
                * (scored.event_weight.to_numpy() * young_sign)[:, None]
            )
            influence = score @ fit["bread"].T
            scored["target_influence"] = influence[:, target]

            used_indices = fit["used_occ_indices"]
            occupations = design_from_cells(cells[(margin, "official")])["occupations"]
            used_codes = [occupations[int(index)] for index in used_indices]
            reproduced = scored.groupby("occ_code").target_influence.sum().reindex(
                used_codes, fill_value=0.0
            ).to_numpy()
            raw_expected = fit["raw_influence"][:, target]
            raw_occ_error = float(np.max(np.abs(reproduced - raw_expected)))
            g_occ = len(used_codes)
            finite = math.sqrt(g_occ / (g_occ - 1)) if g_occ > 1 else 1.0
            saved = (
                saved_influence.loc[saved_influence.model_id.eq(model_id)]
                .set_index("occ_code")
                .target_influence.reindex(used_codes)
                .to_numpy()
            )
            saved_occ_error = float(np.max(np.abs(finite * raw_expected - saved)))
            if raw_occ_error > 1e-8 or saved_occ_error > 1e-8:
                raise RuntimeError(
                    f"{model_id}: event-score conservation failed "
                    f"({raw_occ_error}, {saved_occ_error})"
                )

            person = cluster_summary(scored.target_influence, scored.CPSIDV)
            household = cluster_summary(scored.target_influence, scored.CPSID)
            for result in [person, household]:
                result["ci_lower"] = float(beta - 1.959963984540054 * result["se"])
                result["ci_upper"] = float(beta + 1.959963984540054 * result["se"])
            person_counts = scored.groupby("CPSIDV").event_id.nunique()
            household_counts = scored.groupby("CPSID").event_id.nunique()
            modeled_event_weight = float(scored.event_weight.sum())
            cell_event_weight = float(
                cells[(margin, "official")]
                .loc[
                    cells[(margin, "official")][["occ_code", "month"]]
                    .apply(tuple, axis=1)
                    .isin(set(map(tuple, grid[["occ_code", "month"]].to_numpy())))
                ]
                .event.sum()
            )

            rows.append(
                {
                    "analysis_status": LABEL,
                    "model_id": model_id,
                    "coefficient": beta,
                    "coefficient_units": stored.coefficient_units,
                    "primary_occupation_cluster_se": float(stored.analytic_occupation_cluster_se),
                    "primary_wild_score_ci_lower": float(stored.wild_score_ci_lower),
                    "primary_wild_score_ci_upper": float(stored.wild_score_ci_upper),
                    "person_score_clusters": person["clusters"],
                    "persons_with_multiple_modeled_events": int((person_counts > 1).sum()),
                    "person_cluster_se": person["se"],
                    "person_normal_ci_lower": person["ci_lower"],
                    "person_normal_ci_upper": person["ci_upper"],
                    "person_normal_mde80": person["mde80"],
                    "household_score_clusters": household["clusters"],
                    "households_with_multiple_modeled_events": int((household_counts > 1).sum()),
                    "household_cluster_se": household["se"],
                    "household_normal_ci_lower": household["ci_lower"],
                    "household_normal_ci_upper": household["ci_upper"],
                    "household_normal_mde80": household["mde80"],
                    "household_to_occupation_se_ratio": float(
                        household["se"] / float(stored.analytic_occupation_cluster_se)
                    ),
                    "conditional_score_interpretation": (
                        "separate sampling-dependence sensitivity conditional on cell risk sets and event totals; "
                        "not CPS design-based and not combined with occupation-shock variance"
                    ),
                }
            )
            conservation.append(
                {
                    "analysis_status": LABEL,
                    "model_id": model_id,
                    "coefficient_reproduction_error": beta_error,
                    "routed_supported_event_weight": routed_event_weight,
                    "modeled_event_weight": modeled_event_weight,
                    "cell_modeled_event_weight": cell_event_weight,
                    "event_weight_conservation_error": modeled_event_weight - cell_event_weight,
                    "max_raw_occupation_influence_error": raw_occ_error,
                    "max_saved_occupation_influence_error": saved_occ_error,
                    "modeled_event_records": int(scored.event_id.nunique()),
                    "modeled_route_records": int(len(scored)),
                    "conditional_score_sum": float(scored.target_influence.sum()),
                }
            )
        del linked, cells

    result_path = args.output_dir / "PERSON_HOUSEHOLD_CLUSTER_SENSITIVITY.csv"
    conservation_path = args.output_dir / "EVENT_SCORE_CONSERVATION.csv"
    write_csv(result_path, rows)
    write_csv(conservation_path, conservation)
    receipt = {
        "record": "YAX R3 flow person/household conditional-score cluster sensitivity",
        "analysis_status": LABEL,
        "amendment_commit": AMENDMENT_COMMIT,
        "execution_head": git("rev-parse", "HEAD"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": {"horizons": HORIZONS, "margins": CORE_MARGINS, "models": len(rows)},
        "method": (
            "one-way origin-person and origin-household clustering of event-level conditional-score influence; "
            "normal intervals; cell risks and event totals conditioned upon"
        ),
        "not_full_CPS_design_inference": True,
        "not_combined_with_occupation_cluster_variance": True,
        "no_restricted_identifier_or_event_record_written": True,
        "fixed_point_results_sha256": sha256(args.fixed_results),
        "fixed_occupation_influence_sha256": sha256(args.fixed_influence),
        "amendment_sha256": sha256(args.amendment),
        "script_sha256": _hash_rows(pathlib.Path(__file__)),
        "restricted_input_hashes": {
            "base_wide": sha256(args.microdata),
            "march_repair": sha256(args.repair_microdata),
            "corrected_weight_patch": sha256(args.weight_patch),
        },
        "public_input_hashes": {
            "membership": sha256(args.membership),
            "bridge": sha256(args.bridge),
        },
        "corrected_reconstruction": reconstruction,
        "mapping": mapping,
        "link_repeat_and_aging": link_counts,
        "historical_occupation_draw_contract": {
            "draws": BOOTSTRAP_DRAWS,
            "seed": BOOTSTRAP_SEED,
            "note": "reported for lineage only; this analytic cluster sensitivity defines no paired draw comparison",
        },
        "output_hashes": {
            result_path.name: sha256(result_path),
            conservation_path.name: sha256(conservation_path),
        },
    }
    write_json(args.output_dir / "EXECUTION_RECEIPT.json", receipt)
    print(json.dumps({"models": len(rows), "status": "COMPLETE"}, indent=2))
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--microdata", required=True, type=pathlib.Path)
    parser.add_argument("--repair-microdata", required=True, type=pathlib.Path)
    parser.add_argument("--weight-patch", required=True, type=pathlib.Path)
    parser.add_argument("--membership", required=True, type=pathlib.Path)
    parser.add_argument("--bridge", required=True, type=pathlib.Path)
    parser.add_argument("--fixed-results", required=True, type=pathlib.Path)
    parser.add_argument("--fixed-influence", required=True, type=pathlib.Path)
    parser.add_argument(
        "--amendment",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parent / "HOUSEHOLD_CLUSTER_AMENDMENT_BEFORE_RESULTS.md",
    )
    parser.add_argument("--output-dir", required=True, type=pathlib.Path)
    args = parser.parse_args()
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
