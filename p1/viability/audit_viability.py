#!/usr/bin/env python3
"""Reproduce the P1 ex-ante viability audit without loading outcome data.

The script reads only the frozen event, Gate0, holdings-mapping, and exposure
artifacts.  It must not read an earnings or CAR file.  All MDEs are stated in
units of the residual CAR standard deviation because an untreated/pre-period
outcome panel has not yet been built.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm, t


ROOT = Path(__file__).resolve().parents[2]
P1 = ROOT / "p1"
OUT = P1 / "viability"
SEED = 20260903
N_REPS = 20
THRESHOLDS = [0.0, 0.001, 0.0025, 0.005, 0.01]
HORIZONS = ["5m", "15m", "30m", "60m", "close", "+1d"]
DIM_NAME = "Dimensional Fund Advisors LP"

INPUTS = {
    "master": P1 / "universe_v2/output/event_master_final_reconciled.csv",
    "waves": P1 / "universe_v2/output/wave_membership_v2.csv",
    "nonexact": P1 / "universe_v2/output/excluded_82_source_date_audit.csv",
    "gate0": P1 / "t2_free/nport_gate0_event_level.csv",
    "gate_pass": P1 / "exposure/exposure_universe_gate0_pass.csv",
    "all": P1 / "exposure/exposure_stock_wave_all.csv",
    "dimensional_only": P1 / "exposure/exposure_stock_wave_dimensional_only.csv",
    "exclude_dimensional": P1 / "exposure/exposure_stock_wave_ex_dimensional.csv",
    "crosswalk": P1 / "exposure/nport_crsp_security_crosswalk.csv",
    "coverage": P1 / "exposure/nport_pre_post_coverage_by_wave.csv",
}

# Variance shares for a unit-variance, treatment-free SUE-to-CAR slope error.
# The primary model allows dependence at every level required by the frozen
# design.  The cluster-heavy and iid-only rows are sensitivity bounds.
VARIANCE_MODELS = {
    "clustered_base_primary": (0.30, 0.25, 0.20, 0.25),
    "cluster_heavy_sensitivity": (0.40, 0.30, 0.20, 0.10),
    "iid_only_optimistic_bound": (0.00, 0.00, 0.00, 1.00),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load() -> dict[str, pd.DataFrame]:
    return {name: pd.read_csv(path) for name, path in INPUTS.items()}


def clean_cells(frame: pd.DataFrame) -> pd.DataFrame:
    d = frame.loc[frame["primary_ready"].eq(True) & frame["exposure_ownership"].gt(0)].copy()
    d["permno"] = d["permno"].astype(str)
    d["x"] = d["exposure_ownership"] / 0.005
    d["sponsor"] = d["advisers"].fillna("UNKNOWN_ADVISER_PROXY").str.strip()
    return d[["permno", "wave_id", "sponsor", "x", "exposure_ownership"]]


def kish(values: pd.Series) -> float:
    a = values.astype(float).to_numpy()
    return float(a.sum() ** 2 / np.square(a).sum()) if np.square(a).sum() else math.nan


def design_stats(cells: pd.DataFrame, variance_model: str = "clustered_base_primary") -> dict[str, float]:
    """Analytic variance of an equal-wave-weighted continuous-dose estimator.

    x is ExposureOwnership / 0.5%, so beta is the standardized CAR effect for
    a one-SD SUE at 0.5% ownership.  The calculation uses no outcome values.
    """
    if cells.empty:
        return {k: math.nan for k in ["se", "mde80", "mde90", "df", "wave_info_ess", "sponsor_info_ess", "stock_info_ess", "kish_cell_ess"]}
    d = cells.copy()
    n_waves = d["wave_id"].nunique()
    d["n_in_wave"] = d.groupby("wave_id")["permno"].transform("size")
    d["weight"] = 1.0 / (n_waves * d["n_in_wave"])
    d["wx"] = d["weight"] * d["x"]
    d["info"] = d["weight"] * np.square(d["x"])
    denominator = float(d["info"].sum())
    vw, vs, vi, ve = VARIANCE_MODELS[variance_model]
    wave_term = float(np.square(d.groupby("wave_id")["wx"].sum()).sum())
    sp = d[["sponsor", "wx", "info"]].copy()
    sp["sponsor_group"] = sp["sponsor"]
    sp["sponsor"] = sp["sponsor"].str.split(";")
    sp["n_parts"] = sp["sponsor"].str.len()
    sp = sp.explode("sponsor")
    sp["sponsor"] = sp["sponsor"].str.strip()
    sp["wx_share"] = sp["wx"] / sp["n_parts"]
    sp["info_share"] = sp["info"] / sp["n_parts"]
    sponsor_term = float(np.square(sp.groupby("sponsor")["wx_share"].sum()).sum())
    stock_term = float(np.square(d.groupby("permno")["wx"].sum()).sum())
    idio_term = float(np.square(d["wx"]).sum())
    variance = (vw * wave_term + vs * sponsor_term + vi * stock_term + ve * idio_term) / denominator**2
    se = math.sqrt(variance)
    n_sponsors = sp["sponsor"].nunique()
    df = min(n_waves - 1, n_sponsors - 1)
    wave_info = d.groupby("wave_id")["info"].sum()
    sponsor_info = sp.groupby("sponsor")["info_share"].sum()
    stock_info = d.groupby("permno")["info"].sum()
    result = {
        "se": se,
        "df": float(df),
        "wave_info_ess": kish(wave_info),
        "sponsor_info_ess": kish(sponsor_info),
        "stock_info_ess": kish(stock_info),
        "kish_cell_ess": kish(d["weight"]),
        "n_sponsors": float(n_sponsors),
    }
    if df < 2:
        result["mde80"] = math.nan
        result["mde90"] = math.nan
    else:
        critical = float(t.ppf(0.975, df))
        result["mde80"] = (critical + float(norm.ppf(0.80))) * se
        result["mde90"] = (critical + float(norm.ppf(0.90))) * se
    return result


def build_wave_audit(d: dict[str, pd.DataFrame]) -> pd.DataFrame:
    gate = d["gate_pass"].copy()
    gate["adviser"] = gate["adviser"].fillna("").str.strip()
    base = gate.groupby("wave_id").agg(
        effective_date=("effective_date", "first"),
        gate0_pass_events=("event_id", "nunique"),
        sponsors=("adviser", lambda x: ";".join(sorted(set(x)))),
        sponsor_count=("adviser", "nunique"),
        dimensional_wave=("adviser", lambda x: bool(x.eq(DIM_NAME).any())),
        predecessor_holdings=("pre_holdings_count", "sum"),
        predecessor_equity_share_holdings=("pre_equity_share_holdings", "sum"),
    ).reset_index()

    xw = d["crosswalk"].copy()
    xw["position_value_usd"] = pd.to_numeric(xw["position_value_usd"], errors="coerce").fillna(0)
    xw["candidate_value"] = xw["position_value_usd"].where(xw["is_common_equity_candidate"].eq(True), 0)
    xw["matched_value"] = xw["position_value_usd"].where(xw["mapping_status"].eq("exact_matched"), 0)
    xm = xw.groupby("wave_id").agg(
        common_equity_candidates=("is_common_equity_candidate", "sum"),
        exact_matched_positions=("mapping_status", lambda x: int(x.eq("exact_matched").sum())),
        candidate_value_usd=("candidate_value", "sum"),
        matched_value_usd=("matched_value", "sum"),
        mapping_statuses=("mapping_status", lambda x: ";".join(sorted(set(x.dropna().astype(str))))),
    ).reset_index()
    base = base.merge(xm, on="wave_id", how="left")

    all_cells = clean_cells(d["all"])
    wm = all_cells.groupby("wave_id").agg(
        primary_ready_cells=("permno", "size"),
        unique_positive_stocks=("permno", "nunique"),
        max_exposure_ownership=("exposure_ownership", "max"),
    ).reset_index()
    base = base.merge(wm, on="wave_id", how="left")
    for col in ["common_equity_candidates", "exact_matched_positions", "candidate_value_usd", "matched_value_usd", "primary_ready_cells", "unique_positive_stocks", "max_exposure_ownership"]:
        base[col] = base[col].fillna(0)
    base["candidate_value_match_rate"] = np.where(base["candidate_value_usd"] > 0, base["matched_value_usd"] / base["candidate_value_usd"], np.nan)

    def classify(row: pd.Series) -> tuple[str, bool, str]:
        if row["primary_ready_cells"] > 0:
            if row["candidate_value_match_rate"] >= 0.95:
                return "fully ownership-ready", False, "positive primary-ready cells and >=95% candidate-value mapping"
            return "partially mapped", True, "positive primary-ready cells but <95% candidate-value mapping"
        if row["wave_id"] == "W047":
            return "missing CRSP denominator", True, "three tiny 2026 common-stock positions; mirror lacks 2026 CRSP denominator coverage"
        if row["common_equity_candidates"] == 0:
            return "non-common-equity only", False, "no N-PORT position classified as candidate U.S. common equity"
        return "security-mapping failure", False, "candidate positions are foreign/ADR, pooled-fund/cash, or otherwise ineligible for exact U.S.-common mapping"

    cl = base.apply(classify, axis=1, result_type="expand")
    cl.columns = ["coverage_class", "technically_recoverable", "coverage_reason"]
    base = pd.concat([base, cl], axis=1)
    base["recovery_value"] = np.where(base["wave_id"].eq("W047"), "negligible_for_frozen_0.5pct_gate", np.where(base["coverage_class"].eq("partially mapped"), "incremental_cells_only_wave_already_ready", "none_under_frozen_us_common_equity_design"))
    return base.sort_values("wave_id")


def effective_sample_audit(d: dict[str, pd.DataFrame], waves: pd.DataFrame) -> pd.DataFrame:
    gate = d["gate_pass"].copy()
    gate["adviser"] = gate["adviser"].fillna("").str.strip()
    rows: list[dict[str, object]] = []

    def add(section: str, sample: str, metric: str, value: object, unit: str, note: str = "") -> None:
        rows.append({"section": section, "sample": sample, "metric": metric, "value": value, "unit": unit, "note": note})

    add("raw_counts", "all", "raw_earnings_event_observations", "NOT_YET_OBSERVABLE", "rows", "No earnings/CAR panel was loaded or built for this audit")
    add("raw_counts", "all", "gate0_pass_conversion_events", gate["event_id"].nunique(), "events")
    add("raw_counts", "all", "gate0_pass_waves", gate["wave_id"].nunique(), "waves")
    add("raw_counts", "all", "ownership_ready_waves", int(waves["primary_ready_cells"].gt(0).sum()), "waves")
    add("raw_counts", "all", "gate0_adviser_proxies", gate["adviser"].nunique(), "sponsors", "Unsigned adviser proxies, not PI-signed economic sponsor groups")
    add("raw_counts", "exclude_dimensional", "gate0_non_dimensional_adviser_proxies", gate.loc[~gate["adviser"].eq(DIM_NAME), "adviser"].nunique(), "sponsors")
    for sample, key in [("all", "all"), ("dimensional_only", "dimensional_only"), ("exclude_dimensional", "exclude_dimensional")]:
        cells = clean_cells(d[key])
        stats = design_stats(cells)
        add("treatment_cells", sample, "positive_stock_wave_cells", len(cells), "stock-wave cells")
        add("treatment_cells", sample, "unique_positive_stocks", cells["permno"].nunique(), "stocks")
        add("treatment_cells", sample, "positive_waves", cells["wave_id"].nunique(), "waves")
        individual_sponsors = {part.strip() for group in cells["sponsor"].unique() for part in group.split(";")}
        add("treatment_cells", sample, "contributing_adviser_proxies", len(individual_sponsors), "sponsors")
        for threshold in THRESHOLDS[1:]:
            tag = str(threshold * 100).rstrip("0").rstrip(".").replace(".", "p")
            above = cells.loc[cells["exposure_ownership"].ge(threshold)]
            add("thresholds", sample, f"unique_stocks_ge_{tag}pct", above["permno"].nunique(), "stocks")
            add("thresholds", sample, f"stock_wave_cells_ge_{tag}pct", len(above), "stock-wave cells")
        add("effective_n", sample, "kish_equal_wave_cell_ess", round(stats["kish_cell_ess"], 6), "effective stock-wave cells", "Kish ESS of weights 1/(W*n_w)")
        add("effective_n", sample, "wave_information_ess", round(stats["wave_info_ess"], 6), "effective waves", "Kish ESS of each wave's weighted x^2 contribution; x=Exposure/0.5%")
        add("effective_n", sample, "sponsor_information_ess", round(stats["sponsor_info_ess"], 6), "effective sponsors", "Kish ESS of each adviser proxy's weighted x^2 contribution")
        add("effective_n", sample, "stock_information_ess", round(stats["stock_info_ess"], 6), "effective stocks", "Kish ESS of each stock's weighted x^2 contribution")

    evdist = gate.groupby("wave_id")["event_id"].nunique()
    for n, count in evdist.value_counts().sort_index().items():
        add("distribution", "all", f"waves_with_{n}_events", int(count), "waves")
    stockdist = waves.loc[waves["primary_ready_cells"].gt(0), "unique_positive_stocks"]
    for stat, value in [("min", stockdist.min()), ("p25", stockdist.quantile(.25)), ("median", stockdist.median()), ("p75", stockdist.quantile(.75)), ("max", stockdist.max()), ("mean", stockdist.mean())]:
        add("distribution", "all", f"positive_stocks_per_ready_wave_{stat}", round(float(value), 3), "stocks per wave")
    return pd.DataFrame(rows)


def current_mde(d: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for sample, key in [("all", "all"), ("dimensional_only", "dimensional_only"), ("exclude_dimensional", "exclude_dimensional")]:
        cells = clean_cells(d[key])
        for model in VARIANCE_MODELS:
            s = design_stats(cells, model)
            for horizon in HORIZONS:
                rows.append({
                    "sample": sample,
                    "horizon": horizon,
                    "variance_model": model,
                    "waves": cells["wave_id"].nunique(),
                    "adviser_proxy_clusters": int(s["n_sponsors"]),
                    "unique_stocks": cells["permno"].nunique(),
                    "positive_stock_wave_cells": len(cells),
                    "cluster_df": s["df"],
                    "mde80_residual_car_sd_at_0p5pct": s["mde80"],
                    "mde90_residual_car_sd_at_0p5pct": s["mde90"],
                    "absolute_mde_bps": "NOT_ESTIMABLE_PRE_OUTCOME_PANEL",
                    "variance_source": "ex-ante unit-variance random-slope decomposition; no treatment or outcome estimate",
                    "variance_shares_wave_sponsor_stock_idio": "/".join(f"{x:.2f}" for x in VARIANCE_MODELS[model]),
                    "economic_benchmark": "0.5 residual-CAR SD at one-SD SUE and 0.5% ownership",
                    "passes_0p5sd_80": bool(pd.notna(s["mde80"]) and s["mde80"] <= .5),
                    "passes_0p5sd_90": bool(pd.notna(s["mde90"]) and s["mde90"] <= .5),
                    "note": "All horizons share standardized MDE until untreated/pre-period horizon-specific CAR variance is built" if sample != "dimensional_only" else "Not estimable: only one adviser proxy cluster across two waves",
                })
    return pd.DataFrame(rows)


def clone_wave(source: pd.DataFrame, wave_id: str, sponsor_new: bool, stock_new_prob: float, rng: np.random.Generator, serial: int) -> pd.DataFrame:
    if source.empty:
        return source.copy()
    out = source.copy()
    old_ids = out["permno"].unique()
    mapping = {}
    for j, old in enumerate(old_ids):
        # A finite synthetic pool forces overlap across added waves instead of
        # letting the number of listed stocks grow without bound.
        mapping[old] = f"NEW_POOL_{int(rng.integers(0, 4000))}" if rng.random() < stock_new_prob else old
    out["permno"] = out["permno"].map(mapping)
    out["wave_id"] = wave_id
    if sponsor_new:
        out["sponsor"] = f"NEW_NONDIM_SPONSOR_{serial}"
    return out


def expansion_scenarios(d: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    gate = d["gate_pass"].copy()
    event_counts = gate.groupby("wave_id")["event_id"].nunique().to_dict()
    all_base = clean_cells(d["all"])
    ex_base = clean_cells(d["exclude_dimensional"])
    dim_waves = set(gate.loc[gate["adviser"].fillna("").str.strip().eq(DIM_NAME), "wave_id"])
    wave_ids = sorted(event_counts)
    all_templates = {w: all_base.loc[all_base["wave_id"].eq(w)].copy() for w in wave_ids}
    ex_templates = {w: ex_base.loc[ex_base["wave_id"].eq(w)].copy() for w in wave_ids}
    ex_info = {}
    for w, frame in ex_templates.items():
        ex_info[w] = float(np.square(frame["x"]).mean()) if len(frame) else 0.0
    ranked_ex = [w for w, _ in sorted(ex_info.items(), key=lambda kv: kv[1], reverse=True) if len(ex_templates[w])]
    targeted_pool = ranked_ex[: max(6, math.ceil(len(ranked_ex) / 4))]
    strategies = {
        "conservative": {"pool": wave_ids, "new_sponsor": .05, "new_stock": .10, "force_ex": False},
        "proportional_current_composition": {"pool": wave_ids, "new_sponsor": .25, "new_stock": .30, "force_ex": False},
        "non_dimensional_targeted": {"pool": targeted_pool, "new_sponsor": .75, "new_stock": .50, "force_ex": True},
    }
    required_targets = [74, 80, 90, 100, 110, 120, 130, 140, 150]
    records = []
    pass_rate = 71 / 74

    for strategy, cfg in strategies.items():
        # The required grid stops at 150.  The targeted arm is extended only
        # to locate the power rescue point and show whether it is feasible
        # inside the currently known 247-member structural universe.
        targets = required_targets if strategy != "non_dimensional_targeted" else required_targets + [175, 200, 250, 300, 350, 400, 450, 500, 600, 700, 800, 900, 1000, 1100, 1300, 1500, 1750, 2000]
        for target in targets:
            rep_rows = []
            reps = 1 if target == 74 else (10 if target > 1500 else N_REPS)
            for rep in range(reps):
                extra_exact = target - 74
                extra_pass = 0 if extra_exact == 0 else int(rng.binomial(extra_exact, pass_rate))
                remaining = extra_pass
                new_specs = []
                serial = 0
                while remaining > 0:
                    size = min(int(rng.choice(list(event_counts.values()))), remaining)
                    candidates = [w for w in cfg["pool"] if event_counts[w] == size]
                    if not candidates:
                        distance = min(abs(event_counts[w] - size) for w in cfg["pool"])
                        candidates = [w for w in cfg["pool"] if abs(event_counts[w] - size) == distance]
                    source_wave = str(rng.choice(candidates))
                    serial += 1
                    new_specs.append((source_wave, size, serial))
                    remaining -= size

                all_parts = [all_base]
                ex_parts = [ex_base]
                added_nondim_waves = 0
                for source_wave, size, serial in new_specs:
                    new_wave = f"SIM_{strategy}_{target}_{rep}_{serial}"
                    is_dim = source_wave in dim_waves and not cfg["force_ex"]
                    sponsor_new = bool(rng.random() < cfg["new_sponsor"])
                    if cfg["force_ex"]:
                        source_all = ex_templates[source_wave]
                        source_ex = ex_templates[source_wave]
                        is_dim = False
                    else:
                        source_all = all_templates[source_wave]
                        source_ex = ex_templates[source_wave]
                    a = clone_wave(source_all, new_wave, sponsor_new and not is_dim, cfg["new_stock"], rng, serial + rep * 1000)
                    e = clone_wave(source_ex, new_wave, sponsor_new, cfg["new_stock"], rng, serial + rep * 1000 + 500000)
                    all_parts.append(a)
                    ex_parts.append(e)
                    if not is_dim:
                        added_nondim_waves += 1

                all_sim = pd.concat(all_parts, ignore_index=True)
                ex_sim = pd.concat(ex_parts, ignore_index=True)
                all_stats = design_stats(all_sim)
                ex_stats = design_stats(ex_sim)
                ex_hi = ex_sim.loc[ex_sim["exposure_ownership"].ge(.005), "permno"].nunique()
                rep_rows.append({
                    "gate0_usable_events_assumed": 71 + extra_pass,
                    "total_waves": 47 + len(new_specs),
                    "ownership_ready_waves": all_sim["wave_id"].nunique(),
                    "non_dimensional_waves": 45 + added_nondim_waves,
                    "all_positive_stocks": all_sim["permno"].nunique(),
                    "exclude_dimensional_positive_stocks": ex_sim["permno"].nunique(),
                    "exclude_dimensional_stocks_ge_0p5pct": ex_hi,
                    "all_mde80_sd": all_stats["mde80"],
                    "all_mde90_sd": all_stats["mde90"],
                    "exclude_dimensional_mde80_sd": ex_stats["mde80"],
                    "exclude_dimensional_mde90_sd": ex_stats["mde90"],
                    "added_non_dimensional_waves": added_nondim_waves,
                })
            med = pd.DataFrame(rep_rows).median(numeric_only=True)
            q10 = pd.DataFrame(rep_rows).quantile(.10, numeric_only=True)
            q90 = pd.DataFrame(rep_rows).quantile(.90, numeric_only=True)
            row = {"expansion_strategy": strategy, "total_exact_date_events": target, "simulation_repetitions": reps}
            row.update({k: float(v) for k, v in med.items()})
            row["exclude_dimensional_mde80_sd_p10"] = float(q10["exclude_dimensional_mde80_sd"])
            row["exclude_dimensional_mde80_sd_p90"] = float(q90["exclude_dimensional_mde80_sd"])
            row["frozen_k2_33_stock_gate"] = "PASS" if med["exclude_dimensional_stocks_ge_0p5pct"] >= 33 else "FAIL"
            row["meaningful_0p5sd_power80_gate"] = "PASS" if med["exclude_dimensional_mde80_sd"] <= .5 else "FAIL"
            row["meaningful_0p5sd_power90_gate"] = "PASS" if med["exclude_dimensional_mde90_sd"] <= .5 else "FAIL"
            records.append(row)
    return pd.DataFrame(records)


def rescue_targets(scenarios: pd.DataFrame) -> pd.DataFrame:
    rows = []
    rules = [
        ("frozen_K2", "frozen_k2_33_stock_gate", "PASS"),
        ("80pct_power_for_0p5sd", "meaningful_0p5sd_power80_gate", "PASS"),
        ("90pct_power_for_0p5sd", "meaningful_0p5sd_power90_gate", "PASS"),
    ]
    for strategy in scenarios["expansion_strategy"].unique():
        s = scenarios.loc[scenarios["expansion_strategy"].eq(strategy)].sort_values("total_exact_date_events")
        for target_name, col, pass_value in rules:
            hit = s.loc[s[col].eq(pass_value)]
            if hit.empty:
                ceiling = int(s["total_exact_date_events"].max())
                ceiling_row = s.iloc[-1]
                rows.append({
                    "target": target_name,
                    "expansion_strategy": strategy,
                    "minimum_total_exact_date_events": f">{ceiling}",
                    "additional_exact_date_events_from_74": f">{ceiling - 74}",
                    "additional_gate0_usable_events_from_71": f">{int(round(ceiling_row['gate0_usable_events_assumed'] - 71))}",
                    "additional_independent_non_dimensional_waves": f">{int(round(ceiling_row['added_non_dimensional_waves']))}",
                    "status": "NOT_REACHED_AT_GRID_CEILING_LOWER_BOUND_REPORTED",
                })
            else:
                r = hit.iloc[0]
                rows.append({
                    "target": target_name,
                    "expansion_strategy": strategy,
                    "minimum_total_exact_date_events": int(r["total_exact_date_events"]),
                    "additional_exact_date_events_from_74": int(r["total_exact_date_events"] - 74),
                    "additional_gate0_usable_events_from_71": int(round(r["gate0_usable_events_assumed"] - 71)),
                    "additional_independent_non_dimensional_waves": int(round(r["added_non_dimensional_waves"])),
                    "status": "REACHED_IN_SIMULATED_GRID",
                })
    return pd.DataFrame(rows)


def rank_nonexact(d: dict[str, pd.DataFrame]) -> pd.DataFrame:
    x = d["nonexact"].copy()
    exact_dates = set(pd.to_datetime(d["waves"]["wave_date"], errors="coerce").dt.strftime("%Y-%m-%d"))
    text = (x["pre_series_name"].fillna("") + " " + x["post_series_name"].fillna("")).str.lower()
    equity_signal = text.str.contains(r"equity|stock|growth|value|small.?cap|mid.?cap|large.?cap|dividend|technology|opportunit", regex=True)
    foreign_signal = text.str.contains(r"international|global|emerging|china|world|developing|asia|europe", regex=True)
    fixed_income_signal = text.str.contains(r"bond|mortgage|credit|treasury|municipal|high yield|fixed income|duration", regex=True)
    us_equity = equity_signal & ~foreign_signal & ~fixed_income_signal
    broad_us = text.str.contains(r"u\.s\.|us |core|total|broad|large.?cap|small.?cap|mid.?cap", regex=True) & us_equity
    non_dim = ~x["adviser"].fillna("").str.contains("Dimensional", case=False)
    precision_points = x["final_precision"].map({"proposed_exact_day_only": 4, "month_only": 3, "bounded_window": 2, "year_only": 1}).fillna(0)
    proposed = pd.to_datetime(x["final_proposed_day"], errors="coerce")
    new_wave = ~proposed.dt.strftime("%Y-%m-%d").isin(exact_dates)
    lo = pd.to_datetime(x["cease_window_lo"], errors="coerce")
    hi = pd.to_datetime(x["cease_window_hi"], errors="coerce")
    width = (hi - lo).dt.days
    bracket_points = np.select([width.le(90), width.le(180), width.notna()], [2, 1, 0], default=0)
    accessions = pd.to_numeric(x.get("n_accessions", pd.Series(0, index=x.index)), errors="coerce").fillna(0).clip(upper=2)
    sec_signal = x["final_source_accession"].notna() | x["proposed_effective_date_source"].notna() | x["completion_evidence"].notna()
    score = (3 * non_dim.astype(int) + 3 * us_equity.astype(int) + broad_us.astype(int) + 2 * new_wave.astype(int) + precision_points + bracket_points + accessions + 2 * sec_signal.astype(int) - 2 * foreign_signal.astype(int) - 3 * fixed_income_signal.astype(int))
    x["priority_score"] = score.astype(int)
    x["non_dimensional_sponsor"] = non_dim
    x["new_wave_if_proposed_day_verified"] = np.where(proposed.notna(), new_wave, "UNKNOWN_UNTIL_DATE_RECOVERED")
    x["broad_us_equity_name_signal"] = broad_us
    x["likely_crsp_mappable_name_signal"] = us_equity
    x["foreign_or_fixed_income_name_signal"] = foreign_signal | fixed_income_signal
    x["date_bracket_days"] = width
    x["predecessor_aum_status"] = "NOT_AVAILABLE_IN_FROZEN_EVENT_MASTER"
    x["sec_evidence_signal"] = sec_signal
    x["recommended_first_action"] = np.select(
        [x["final_precision"].eq("proposed_exact_day_only"), x["final_precision"].eq("bounded_window"), x["final_precision"].eq("month_only")],
        ["verify proposed day in completion 497/N-14", "search completion filing within existing bracket", "search month-local 497/N-14 and adviser archive"],
        default="recover a narrower period before manual day search",
    )
    keep = [
        "event_id", "pre_series_id", "pre_series_name", "pre_tickers", "post_series_id", "post_series_name", "adviser",
        "final_precision", "final_effective_date", "final_proposed_day", "cease_window_lo", "cease_window_hi", "date_bracket_days",
        "priority_score", "non_dimensional_sponsor", "new_wave_if_proposed_day_verified", "broad_us_equity_name_signal",
        "likely_crsp_mappable_name_signal", "foreign_or_fixed_income_name_signal", "predecessor_aum_status", "sec_evidence_signal", "recommended_first_action",
    ]
    return x[keep].sort_values(["priority_score", "event_id"], ascending=[False, True]).reset_index(drop=True).assign(priority_rank=lambda z: np.arange(1, len(z) + 1))[["priority_rank"] + keep]


def main() -> None:
    d = load()
    wave_audit = build_wave_audit(d)
    ess = effective_sample_audit(d, wave_audit)
    mde = current_mde(d)
    scenarios = expansion_scenarios(d)
    rescue = rescue_targets(scenarios)
    priority = rank_nonexact(d)
    outputs = {
        "p1_effective_sample_size_audit.csv": ess,
        "p1_wave_coverage_audit.csv": wave_audit,
        "p1_mde_current_design.csv": mde,
        "p1_power_expansion_scenarios.csv": scenarios,
        "p1_rescue_target.csv": rescue,
        "p1_nonexact_82_priority.csv": priority,
    }
    for name, frame in outputs.items():
        frame.to_csv(OUT / name, index=False)
    manifest = {
        "generated_by": str(Path(__file__).relative_to(ROOT)),
        "seed": SEED,
        "simulation_repetitions": N_REPS,
        "outcome_files_read": [],
        "input_sha256": {str(path.relative_to(ROOT)): sha256(path) for path in INPUTS.values()},
        "output_rows": {name: len(frame) for name, frame in outputs.items()},
    }
    (OUT / "audit_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
