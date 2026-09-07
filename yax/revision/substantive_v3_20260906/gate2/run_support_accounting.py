#!/usr/bin/env python3
"""Build the V3 Gate 2 support matrix and exact stock accounting package.

This module consumes only the authenticated Gate 1 occupation-month aggregate,
its receipt, the frozen canonical membership, and the retained numerical audit.
It does not read row-level CPS microdata and does not estimate sampling
uncertainty.  The support and accounting outputs precede heterogeneous or
causal interpretation.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Iterable

import numpy as np
import pandas as pd


SPEC_SCHEMA = "yax-gate2-support-accounting-spec-v1"
SPEC_PREFIX = "yaxgate2sa_v1_"
RECEIPT_SCHEMA = "yax-gate2-support-accounting-receipt-v1"
REQUIRED_CELL_COLUMNS = (
    "occ_code", "month", "family", "young", "older", "beta_quintile", "webb_z",
)
REQUIRED_MEMBERSHIP_COLUMNS = (
    "occupation_code", "occupation_name", "preperiod_weight", "rule_A_beta",
    "beta_quintile", "webb_z",
)
OUTPUT_FILES = (
    "SUPPORT_MATRIX.csv",
    "FAMILY_SUPPORT_SUMMARY.csv",
    "SUPPORT_EDGES.csv",
    "DIRECT_TAIL_MEMBERSHIP.csv",
    "SUPPORT_GRAPH.json",
    "MONTHLY_QUINTILE_STOCKS.csv",
    "PERIOD_STOCKS.csv",
    "TAIL_LOG_STOCK_ACCOUNTING.json",
    "FAMILY_COMPOSITION_DECOMPOSITION.csv",
    "FAMILY_COMPOSITION_SUMMARY.json",
    "ZERO_DENOMINATOR_AUDIT.json",
    "LOG_SHAPLEY_DECOMPOSITION.json",
)


class Gate2Error(ValueError):
    """Raised when a frozen input or accounting invariant fails."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise Gate2Error(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as stream:
            value = json.load(
                stream,
                object_pairs_hook=_unique_pairs,
                parse_constant=lambda token: (_ for _ in ()).throw(
                    Gate2Error(f"non-finite JSON constant: {token}")
                ),
            )
    except json.JSONDecodeError as exc:
        raise Gate2Error(f"invalid JSON in {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise Gate2Error(f"{path.name} must contain a JSON object")
    return value


def compute_spec_id(spec: dict[str, Any]) -> str:
    payload = dict(spec)
    payload.pop("spec_id", None)
    return SPEC_PREFIX + hashlib.sha256(canonical_bytes(payload)).hexdigest()


def validate_spec(spec: dict[str, Any], code_path: Path) -> None:
    required = {
        "schema_version", "spec_id", "status", "canonical_spec",
        "authenticated_inputs", "calendar", "support", "accounting",
        "numerical_comparison", "execution", "outputs",
    }
    if set(spec) != required:
        raise Gate2Error(
            "Gate 2 spec keys differ: "
            f"missing={sorted(required - set(spec))}, extra={sorted(set(spec) - required)}"
        )
    if spec["schema_version"] != SPEC_SCHEMA:
        raise Gate2Error("Gate 2 spec schema differs")
    if spec["spec_id"] != compute_spec_id(spec):
        raise Gate2Error("Gate 2 spec_id mismatch")
    if spec["execution"]["code_sha256"] != sha256_file(code_path):
        raise Gate2Error("Gate 2 runner byte hash differs from the signed spec")
    families = spec["support"]["expected_soc2_families"]
    if len(families) != 22 or len(set(families)) != 22:
        raise Gate2Error("support spec must declare 22 unique SOC2 families")
    if spec["support"]["quintiles"] != [1, 2, 3, 4, 5]:
        raise Gate2Error("support spec must declare quintiles 1 through 5")
    if spec["calendar"]["preperiod"] != ["2017-01", "2022-11"]:
        raise Gate2Error("preperiod differs from the canonical construction window")
    if spec["calendar"]["transition_month"] != "2022-12":
        raise Gate2Error("transition month must remain explicit")
    if spec["accounting"]["temporal_weights"] != "equal_observed_month":
        raise Gate2Error("unsupported temporal weighting rule")


def _read_csv(path: Path, string_columns: Iterable[str]) -> pd.DataFrame:
    return pd.read_csv(path, dtype={column: "string" for column in string_columns})


def _normalize_code(series: pd.Series, width: int) -> pd.Series:
    if series.isna().any():
        raise Gate2Error("occupation/family code contains missing values")
    result = series.astype(str).str.strip().str.replace(r"\.0$", "", regex=True).str.zfill(width)
    if not result.str.fullmatch(r"\d+", na=False).all():
        raise Gate2Error("occupation/family code is not numeric")
    return result


def validate_inputs(
    cells: pd.DataFrame,
    membership: pd.DataFrame,
    spec: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    missing_cells = sorted(set(REQUIRED_CELL_COLUMNS) - set(cells.columns))
    missing_membership = sorted(set(REQUIRED_MEMBERSHIP_COLUMNS) - set(membership.columns))
    if missing_cells or missing_membership:
        raise Gate2Error(
            f"input columns missing: cells={missing_cells}, membership={missing_membership}"
        )
    cells = cells[list(REQUIRED_CELL_COLUMNS)].copy()
    membership = membership[list(REQUIRED_MEMBERSHIP_COLUMNS)].copy()
    cells["occ_code"] = _normalize_code(cells["occ_code"], 4)
    cells["family"] = _normalize_code(cells["family"], 2)
    membership["occupation_code"] = _normalize_code(membership["occupation_code"], 4)
    for column in ("young", "older", "webb_z"):
        cells[column] = pd.to_numeric(cells[column], errors="raise")
    for column in ("preperiod_weight", "rule_A_beta", "webb_z"):
        membership[column] = pd.to_numeric(membership[column], errors="raise")
    cells["beta_quintile"] = pd.to_numeric(cells["beta_quintile"], errors="raise").astype(int)
    membership["beta_quintile"] = pd.to_numeric(
        membership["beta_quintile"], errors="raise"
    ).astype(int)
    if not np.isfinite(cells[["young", "older", "webb_z"]].to_numpy()).all():
        raise Gate2Error("cell input contains non-finite numeric values")
    if not np.isfinite(
        membership[["preperiod_weight", "rule_A_beta", "webb_z"]].to_numpy()
    ).all():
        raise Gate2Error("membership input contains non-finite numeric values")
    if (cells[["young", "older"]] < 0).any().any():
        raise Gate2Error("employment stocks must be nonnegative")
    if cells[["occ_code", "month"]].duplicated().any():
        raise Gate2Error("occupation-month cells are duplicated")
    if membership["occupation_code"].duplicated().any():
        raise Gate2Error("membership contains duplicate occupation codes")
    if not cells["month"].astype(str).str.fullmatch(r"\d{4}-\d{2}").all():
        raise Gate2Error("month must use YYYY-MM")
    expected_occ = int(spec["support"]["expected_occupation_count"])
    if cells["occ_code"].nunique() != expected_occ or len(membership) != expected_occ:
        raise Gate2Error("occupation count differs from the canonical 468-occupation support")
    month_counts = cells.groupby("occ_code", observed=True)["month"].nunique()
    if month_counts.nunique() != 1 or int(month_counts.iloc[0]) != int(
        spec["calendar"]["observed_month_count"]
    ):
        raise Gate2Error("occupation-month grid is not balanced on 114 observed months")
    if len(cells) != expected_occ * int(spec["calendar"]["observed_month_count"]):
        raise Gate2Error("occupation-month row count differs")
    fixed = cells.groupby("occ_code", observed=True).agg(
        family=("family", "first"),
        family_n=("family", "nunique"),
        beta_quintile=("beta_quintile", "first"),
        quintile_n=("beta_quintile", "nunique"),
        webb_z=("webb_z", "first"),
        webb_n=("webb_z", "nunique"),
    ).reset_index()
    if (fixed[["family_n", "quintile_n", "webb_n"]] != 1).any().any():
        raise Gate2Error("occupation assignment varies over calendar months")
    merged = fixed.merge(
        membership,
        left_on="occ_code",
        right_on="occupation_code",
        how="outer",
        validate="one_to_one",
        indicator=True,
        suffixes=("_cell", "_membership"),
    )
    if not merged["_merge"].eq("both").all():
        raise Gate2Error("cell and canonical membership occupation sets differ")
    family_map = cells[["occ_code", "family"]].drop_duplicates()
    # The membership file does not repeat family; the frozen cell assignment is authoritative.
    if not merged["beta_quintile_cell"].eq(merged["beta_quintile_membership"]).all():
        raise Gate2Error("cell quintiles differ from canonical membership")
    if not np.allclose(
        merged["webb_z_cell"], merged["webb_z_membership"], rtol=1e-12, atol=1e-12
    ):
        raise Gate2Error("cell Webb normalization differs from canonical membership")
    expected_families = set(spec["support"]["expected_soc2_families"])
    if set(family_map["family"]) != expected_families:
        raise Gate2Error("observed SOC2 family set differs from the signed 22-family set")
    return cells, membership.merge(family_map, left_on="occupation_code", right_on="occ_code", validate="one_to_one")


def assign_period(month: str, spec: dict[str, Any]) -> str:
    pre_start, pre_end = spec["calendar"]["preperiod"]
    post_start, post_end = spec["calendar"]["postperiod"]
    if pre_start <= month <= pre_end:
        return "pre"
    if post_start <= month <= post_end:
        return "post"
    if month == spec["calendar"]["transition_month"]:
        return "transition_excluded"
    raise Gate2Error(f"month outside signed calendar: {month}")


def build_support(
    cells: pd.DataFrame,
    membership: pd.DataFrame,
    spec: dict[str, Any],
) -> dict[str, Any]:
    cells = cells.copy()
    cells["period"] = [assign_period(str(value), spec) for value in cells["month"]]
    pre = cells.loc[cells["period"].eq("pre")].copy()
    pre["stock"] = pre["young"] + pre["older"]
    occ_stock = pre.groupby("occ_code", observed=True)["stock"].sum().rename("preperiod_stock")
    occ = membership.merge(occ_stock, left_on="occupation_code", right_index=True, validate="one_to_one")
    total_stock = float(occ["preperiod_stock"].sum())
    if not total_stock > 0:
        raise Gate2Error("preperiod stock is not positive")
    if not np.allclose(
        occ["preperiod_stock"], occ["preperiod_weight"], rtol=1e-10, atol=1e-5
    ):
        raise Gate2Error("cell preperiod stocks do not reproduce frozen construction weights")
    families = spec["support"]["expected_soc2_families"]
    quintiles = spec["support"]["quintiles"]
    grid = pd.MultiIndex.from_product([families, quintiles], names=["family", "beta_quintile"])
    grouped = occ.groupby(["family", "beta_quintile"], observed=True).agg(
        occupation_count=("occupation_code", "nunique"),
        preperiod_stock=("preperiod_stock", "sum"),
        exposure_min=("rule_A_beta", "min"),
        exposure_max=("rule_A_beta", "max"),
    ).reindex(grid)
    grouped["occupation_count"] = grouped["occupation_count"].fillna(0).astype(int)
    grouped["preperiod_stock"] = grouped["preperiod_stock"].fillna(0.0)
    grouped["national_preperiod_stock_share"] = grouped["preperiod_stock"] / total_stock
    family_stock = grouped.groupby(level="family")["preperiod_stock"].transform("sum")
    quintile_stock = grouped.groupby(level="beta_quintile")["preperiod_stock"].transform("sum")
    grouped["within_family_preperiod_stock_share"] = np.divide(
        grouped["preperiod_stock"], family_stock,
        out=np.zeros(len(grouped), dtype=float), where=family_stock.to_numpy() > 0,
    )
    grouped["within_quintile_preperiod_stock_share"] = np.divide(
        grouped["preperiod_stock"], quintile_stock,
        out=np.zeros(len(grouped), dtype=float), where=quintile_stock.to_numpy() > 0,
    )
    grouped["cell_has_support"] = grouped["occupation_count"].gt(0)
    matrix = grouped.reset_index()
    summary_rows: list[dict[str, Any]] = []
    edge_rows: list[dict[str, Any]] = []
    for family in families:
        part = matrix.loc[matrix["family"].eq(family)].copy()
        present = part.loc[part["cell_has_support"], "beta_quintile"].astype(int).tolist()
        family_occ = occ.loc[occ["family"].eq(family)]
        summary_rows.append({
            "family": family,
            "occupation_count": int(len(family_occ)),
            "preperiod_stock": float(family_occ["preperiod_stock"].sum()),
            "national_preperiod_stock_share": float(family_occ["preperiod_stock"].sum() / total_stock),
            "quintiles_present": "|".join(map(str, present)),
            "quintile_count": len(present),
            "q1_occupation_count": int((family_occ["beta_quintile"] == 1).sum()),
            "q5_occupation_count": int((family_occ["beta_quintile"] == 5).sum()),
            "direct_q1_q5_support": bool(1 in present and 5 in present),
            "exposure_min": float(family_occ["rule_A_beta"].min()),
            "exposure_max": float(family_occ["rule_A_beta"].max()),
        })
        for left_index, left in enumerate(present):
            for right in present[left_index + 1:]:
                left_row = part.loc[part["beta_quintile"].eq(left)].iloc[0]
                right_row = part.loc[part["beta_quintile"].eq(right)].iloc[0]
                left_names = occ.loc[
                    occ["family"].eq(family) & occ["beta_quintile"].eq(left),
                    "occupation_name",
                ].sort_values(kind="mergesort")
                right_names = occ.loc[
                    occ["family"].eq(family) & occ["beta_quintile"].eq(right),
                    "occupation_name",
                ].sort_values(kind="mergesort")
                edge_rows.append({
                    "family": family,
                    "quintile_low": left,
                    "quintile_high": right,
                    "quintile_distance": right - left,
                    "low_occupation_count": int(left_row["occupation_count"]),
                    "high_occupation_count": int(right_row["occupation_count"]),
                    "low_preperiod_stock": float(left_row["preperiod_stock"]),
                    "high_preperiod_stock": float(right_row["preperiod_stock"]),
                    "low_named_occupations": "; ".join(left_names.astype(str)),
                    "high_named_occupations": "; ".join(right_names.astype(str)),
                    "direct_tail_edge": bool(left == 1 and right == 5),
                })
    family_summary = pd.DataFrame(summary_rows)
    edges = pd.DataFrame(edge_rows)
    direct_families = family_summary.loc[
        family_summary["direct_q1_q5_support"], "family"
    ].tolist()
    direct = occ.loc[
        occ["family"].isin(direct_families) & occ["beta_quintile"].isin([1, 5]),
        ["family", "beta_quintile", "occupation_code", "occupation_name", "rule_A_beta", "preperiod_stock"],
    ].copy()
    direct["within_family_tail_preperiod_stock_share"] = direct.groupby(
        ["family", "beta_quintile"], observed=True
    )["preperiod_stock"].transform(lambda values: values / values.sum())
    direct = direct.sort_values(
        ["family", "beta_quintile", "preperiod_stock", "occupation_code"],
        ascending=[True, True, False, True], kind="mergesort",
    )
    adjacency: dict[int, set[int]] = {q: set() for q in quintiles}
    for row in edge_rows:
        adjacency[int(row["quintile_low"])].add(int(row["quintile_high"]))
        adjacency[int(row["quintile_high"])].add(int(row["quintile_low"]))
    reached = {quintiles[0]}
    frontier = [quintiles[0]]
    while frontier:
        node = frontier.pop()
        for neighbor in adjacency[node] - reached:
            reached.add(neighbor)
            frontier.append(neighbor)
    represented_edges = sorted(
        {
            (int(row["quintile_low"]), int(row["quintile_high"]))
            for row in edge_rows
        }
    )
    incidence = np.zeros((len(quintiles), len(represented_edges)), dtype=float)
    for column, (left, right) in enumerate(represented_edges):
        incidence[quintiles.index(left), column] = -1.0
        incidence[quintiles.index(right), column] = 1.0
    incidence_rank = int(np.linalg.matrix_rank(incidence))
    graph = {
        "status": "PASS_CONNECTED_QUINTILE_SUPPORT_GRAPH" if reached == set(quintiles) else "BLOCKED_DISCONNECTED_QUINTILE_SUPPORT_GRAPH",
        "nodes": quintiles,
        "reached_from_q1": sorted(reached),
        "connected": reached == set(quintiles),
        "represented_edges": [f"Q{left}-Q{right}" for left, right in represented_edges],
        "represented_edge_count": len(represented_edges),
        "incidence_rank": incidence_rank,
        "full_contrast_rank": incidence_rank == len(quintiles) - 1,
        "direct_q1_q5_families": direct_families,
        "direct_q1_q5_family_count": len(direct_families),
        "edge_family_counts": {
            f"Q{left}-Q{right}": int(
                ((edges["quintile_low"] == left) & (edges["quintile_high"] == right)).sum()
            )
            for left in quintiles for right in quintiles if left < right
        },
        "interpretation": "Connectivity identifies a common-profile comparison only under the imposed common coefficient restrictions; it is not a family-average of directly observed Q5-Q1 contrasts.",
    }
    if not graph["connected"] or not graph["full_contrast_rank"]:
        raise Gate2Error("national quintile support graph is disconnected")
    return {
        "matrix": matrix,
        "family_summary": family_summary,
        "edges": edges,
        "direct": direct,
        "graph": graph,
    }


def build_accounting(cells: pd.DataFrame, spec: dict[str, Any]) -> dict[str, Any]:
    work = cells.copy()
    work["period"] = [assign_period(str(value), spec) for value in work["month"]]
    work = work.loc[work["period"].isin(["pre", "post"])].copy()
    monthly = work.groupby(["month", "period", "beta_quintile"], observed=True)[
        ["young", "older"]
    ].sum().reset_index()
    month_counts = monthly.groupby("period", observed=True)["month"].nunique().to_dict()
    expected_counts = spec["calendar"]["expected_period_month_counts"]
    if month_counts != expected_counts:
        raise Gate2Error(f"period month counts differ: {month_counts} != {expected_counts}")
    period_wide = monthly.groupby(["period", "beta_quintile"], observed=True)[
        ["young", "older"]
    ].mean().reset_index()
    period_rows = period_wide.melt(
        id_vars=["period", "beta_quintile"], value_vars=["young", "older"],
        var_name="age_group", value_name="equal_month_average_stock",
    )
    period_rows["observed_month_count"] = period_rows["period"].map(month_counts)
    period_rows["normalized_month_weight"] = period_rows["observed_month_count"].map(
        lambda count: 1.0 / float(count)
    )
    lookup = {
        (row.period, int(row.beta_quintile), row.age_group): float(row.equal_month_average_stock)
        for row in period_rows.itertuples(index=False)
    }
    values: dict[str, float] = {}
    for age in ("young", "older"):
        for quintile in (1, 5):
            for period in ("pre", "post"):
                value = lookup[(period, quintile, age)]
                if not value > 0:
                    raise Gate2Error(f"tail period stock is not positive: {age}, Q{quintile}, {period}")
                values[f"N_{age}_q{quintile}_{period}"] = value
    d_young = math.log(values["N_young_q5_post"] / values["N_young_q5_pre"]) - math.log(
        values["N_young_q1_post"] / values["N_young_q1_pre"]
    )
    d_older = math.log(values["N_older_q5_post"] / values["N_older_q5_pre"]) - math.log(
        values["N_older_q1_post"] / values["N_older_q1_pre"]
    )
    d_relative = d_young - d_older
    ratio_identity = math.log(
        (values["N_young_q5_post"] / values["N_older_q5_post"])
        / (values["N_young_q5_pre"] / values["N_older_q5_pre"])
    ) - math.log(
        (values["N_young_q1_post"] / values["N_older_q1_post"])
        / (values["N_young_q1_pre"] / values["N_older_q1_pre"])
    )
    closure = d_relative - ratio_identity
    tolerance = float(spec["accounting"]["closure_absolute_tolerance"])
    if abs(closure) > tolerance:
        raise Gate2Error("tail log-stock identity does not close")
    return {
        "monthly": monthly.sort_values(["month", "beta_quintile"], kind="mergesort"),
        "period": period_rows.sort_values(["beta_quintile", "age_group", "period"], kind="mergesort"),
        "tail": {
            "status": "PASS_EXACT_TAIL_LOG_STOCK_IDENTITY",
            "temporal_weighting": "equal observed calendar-month averages within period",
            "stocks": values,
            "D_young": d_young,
            "D_older": d_older,
            "D_relative": d_relative,
            "ratio_identity_value": ratio_identity,
            "closure_residual": closure,
            "closure_absolute_tolerance": tolerance,
            "interpretation": "This exact aggregate identity is not automatically the grouped-binomial regression coefficient.",
        },
        "work": work,
    }


def _log_shapley(
    share_pre: np.ndarray,
    share_post: np.ndarray,
    ratio_pre: np.ndarray,
    ratio_post: np.ndarray,
    boundary_pre: float,
    boundary_post: float,
) -> dict[str, Any]:
    states = {
        "composition": (share_pre, share_post),
        "within": (ratio_pre, ratio_post),
        "boundary": (boundary_pre, boundary_post),
    }

    def value(state: dict[str, int]) -> float:
        share = states["composition"][state["composition"]]
        ratio = states["within"][state["within"]]
        boundary = float(states["boundary"][state["boundary"]])
        level = float(np.dot(share, ratio) + boundary)
        if not level > 0 or not math.isfinite(level):
            raise Gate2Error("log Shapley hybrid evaluation is not strictly positive")
        return math.log(level)

    factors = ("composition", "within", "boundary")
    contributions = {factor: 0.0 for factor in factors}
    hybrid_values: dict[str, float] = {}
    for bits in itertools.product((0, 1), repeat=3):
        state = dict(zip(factors, bits))
        hybrid_values["".join(map(str, bits))] = value(state)
    for ordering in itertools.permutations(factors):
        state = {factor: 0 for factor in factors}
        previous = value(state)
        for factor in ordering:
            state[factor] = 1
            current = value(state)
            contributions[factor] += (current - previous) / 6.0
            previous = current
    total = hybrid_values["111"] - hybrid_values["000"]
    closure = total - sum(contributions.values())
    return {
        "status": "PASS_EXACT_THREE_FACTOR_LOG_SHAPLEY",
        "log_ratio_change": total,
        "within_family_ratio_component": contributions["within"],
        "older_family_weight_component": contributions["composition"],
        "boundary_mass_component": contributions["boundary"],
        "closure_residual": closure,
        "hybrid_log_values": hybrid_values,
    }


def build_family_composition(work: pd.DataFrame, spec: dict[str, Any]) -> dict[str, Any]:
    tolerance = float(spec["accounting"]["closure_absolute_tolerance"])
    family_month = work.groupby(
        ["month", "period", "beta_quintile", "family"], observed=True
    )[["young", "older"]].sum().reset_index()
    aggregate = family_month.groupby(
        ["period", "beta_quintile", "family"], observed=True
    )[["young", "older"]].mean().reset_index()
    rows: list[dict[str, Any]] = []
    summaries: dict[str, Any] = {}
    log_summaries: dict[str, Any] = {}
    zero_audit_rows: list[dict[str, Any]] = []
    families = spec["support"]["expected_soc2_families"]
    for quintile in (1, 5):
        part = aggregate.loc[aggregate["beta_quintile"].eq(quintile)].copy()
        pivot_y = part.pivot(index="family", columns="period", values="young").reindex(families).fillna(0.0)
        pivot_o = part.pivot(index="family", columns="period", values="older").reindex(families).fillna(0.0)
        for period in ("pre", "post"):
            if period not in pivot_y:
                pivot_y[period] = 0.0
            if period not in pivot_o:
                pivot_o[period] = 0.0
        supported = set(
            work.loc[work["beta_quintile"].eq(quintile), "family"].drop_duplicates()
        )
        classifications: dict[tuple[str, str], str] = {}
        for family in families:
            for period in ("pre", "post"):
                young = float(pivot_y.loc[family, period])
                older = float(pivot_o.loc[family, period])
                if family not in supported:
                    label = "STRUCTURAL_ABSENCE"
                elif older > 0:
                    label = "VALID_POSITIVE"
                elif young > 0:
                    label = "UNDEFINED_YOUNG_ONLY"
                else:
                    label = "UNDEFINED_ZERO_ZERO"
                classifications[(family, period)] = label
                zero_audit_rows.append({
                    "beta_quintile": quintile,
                    "family": family,
                    "period": period,
                    "fixed_support_present": family in supported,
                    "young_stock": young,
                    "older_stock": older,
                    "classification": label,
                })
        total_y = pivot_y[["pre", "post"]].sum(axis=0)
        total_o = pivot_o[["pre", "post"]].sum(axis=0)
        if (total_o <= 0).any():
            raise Gate2Error(f"Q{quintile} national older denominator is not positive")
        common = (pivot_o["pre"] > 0) & (pivot_o["post"] > 0)
        ratio = pivot_y.loc[common, ["pre", "post"]] / pivot_o.loc[common, ["pre", "post"]]
        share = pivot_o.loc[common, ["pre", "post"]] / total_o
        boundary = {
            period: float(pivot_y.loc[~common, period].sum() / total_o[period])
            for period in ("pre", "post")
        }
        within = ((share["pre"] + share["post"]) / 2.0) * (ratio["post"] - ratio["pre"])
        composition = ((ratio["pre"] + ratio["post"]) / 2.0) * (share["post"] - share["pre"])
        boundary_change = boundary["post"] - boundary["pre"]
        delta = float(total_y["post"] / total_o["post"] - total_y["pre"] / total_o["pre"])
        within_total = float(within.sum())
        composition_total = float(composition.sum())
        closure = delta - within_total - composition_total - boundary_change
        if abs(closure) > tolerance:
            raise Gate2Error(f"Q{quintile} symmetric family decomposition does not close")
        for family in families:
            in_common = bool(common.loc[family])
            rows.append({
                "beta_quintile": quintile,
                "family": family,
                "young_pre": float(pivot_y.loc[family, "pre"]),
                "young_post": float(pivot_y.loc[family, "post"]),
                "older_pre": float(pivot_o.loc[family, "pre"]),
                "older_post": float(pivot_o.loc[family, "post"]),
                "classification_pre": classifications[(family, "pre")],
                "classification_post": classifications[(family, "post")],
                "common_positive_denominator_set": in_common,
                "older_share_pre": float(pivot_o.loc[family, "pre"] / total_o["pre"]),
                "older_share_post": float(pivot_o.loc[family, "post"] / total_o["post"]),
                "young_older_ratio_pre": float(ratio.loc[family, "pre"]) if in_common else np.nan,
                "young_older_ratio_post": float(ratio.loc[family, "post"]) if in_common else np.nan,
                "within_family_ratio_change_contribution_level_units": float(within.loc[family]) if in_common else 0.0,
                "older_family_weight_change_contribution_level_units": float(composition.loc[family]) if in_common else 0.0,
            })
        summaries[f"Q{quintile}"] = {
            "status": "PASS_EXACT_SYMMETRIC_LEVEL_RATIO_DECOMPOSITION",
            "fixed_support_family_count": len(supported),
            "common_positive_denominator_family_count": int(common.sum()),
            "national_ratio_pre": float(total_y["pre"] / total_o["pre"]),
            "national_ratio_post": float(total_y["post"] / total_o["post"]),
            "national_level_ratio_change": delta,
            "within_family_ratio_change_component": within_total,
            "older_family_weight_change_component": composition_total,
            "boundary_mass_pre": boundary["pre"],
            "boundary_mass_post": boundary["post"],
            "boundary_mass_change_component": boundary_change,
            "closure_residual": closure,
            "closure_absolute_tolerance": tolerance,
            "units": "level change in the national young/older stock ratio; not log points and not a causal share",
        }
        log_result = _log_shapley(
            share["pre"].to_numpy(), share["post"].to_numpy(),
            ratio["pre"].to_numpy(), ratio["post"].to_numpy(),
            boundary["pre"], boundary["post"],
        )
        if abs(log_result["closure_residual"]) > tolerance:
            raise Gate2Error(f"Q{quintile} log Shapley decomposition does not close")
        log_summaries[f"Q{quintile}"] = log_result
    q1 = summaries["Q1"]
    q5 = summaries["Q5"]
    log_q1 = log_summaries["Q1"]
    log_q5 = log_summaries["Q5"]
    level_difference = {
        "national_level_ratio_change_q5_minus_q1": q5["national_level_ratio_change"] - q1["national_level_ratio_change"],
        "within_family_ratio_component_q5_minus_q1": q5["within_family_ratio_change_component"] - q1["within_family_ratio_change_component"],
        "older_family_weight_component_q5_minus_q1": q5["older_family_weight_change_component"] - q1["older_family_weight_change_component"],
        "boundary_mass_component_q5_minus_q1": q5["boundary_mass_change_component"] - q1["boundary_mass_change_component"],
    }
    level_difference["closure_residual"] = (
        level_difference["national_level_ratio_change_q5_minus_q1"]
        - level_difference["within_family_ratio_component_q5_minus_q1"]
        - level_difference["older_family_weight_component_q5_minus_q1"]
        - level_difference["boundary_mass_component_q5_minus_q1"]
    )
    log_difference = {
        "log_ratio_change_q5_minus_q1": log_q5["log_ratio_change"] - log_q1["log_ratio_change"],
        "within_family_ratio_component_q5_minus_q1": log_q5["within_family_ratio_component"] - log_q1["within_family_ratio_component"],
        "older_family_weight_component_q5_minus_q1": log_q5["older_family_weight_component"] - log_q1["older_family_weight_component"],
        "boundary_mass_component_q5_minus_q1": log_q5["boundary_mass_component"] - log_q1["boundary_mass_component"],
    }
    log_difference["closure_residual"] = (
        log_difference["log_ratio_change_q5_minus_q1"]
        - log_difference["within_family_ratio_component_q5_minus_q1"]
        - log_difference["older_family_weight_component_q5_minus_q1"]
        - log_difference["boundary_mass_component_q5_minus_q1"]
    )
    if abs(level_difference["closure_residual"]) > tolerance or abs(log_difference["closure_residual"]) > tolerance:
        raise Gate2Error("Q5-minus-Q1 family decomposition does not close")
    return {
        "rows": pd.DataFrame(rows).sort_values(["beta_quintile", "family"], kind="mergesort"),
        "zero_audit": {
            "status": "PASS_ZERO_DENOMINATORS_CLASSIFIED_WITHOUT_IMPUTATION",
            "classification_counts": {
                key: int(value) for key, value in
                pd.DataFrame(zero_audit_rows)["classification"].value_counts().sort_index().items()
            },
            "rows": zero_audit_rows,
        },
        "log_shapley": {
            "status": "PASS_Q1_Q5_EXACT_LOG_SHAPLEY_DECOMPOSITIONS",
            "quintiles": log_summaries,
            "q5_minus_q1": log_difference,
            "units": "log change in the young-to-older stock ratio; exact descriptive decomposition",
        },
        "summary": {
            "status": "PASS_Q1_Q5_FAMILY_COMPOSITION_DECOMPOSITIONS",
            "formula": "delta R_q = sum_g mean(s_gq) delta R_gq + sum_g mean(R_gq) delta s_gq",
            "zero_denominator_policy": "All family-quintile-period cells are classified. Common-positive families enter the ratio terms; all remaining young stock is retained as boundary mass. No undefined ratio is assigned zero and no stock is dropped.",
            "quintiles": summaries,
            "q5_minus_q1": level_difference,
        },
    }


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> Path:
    spec = load_json(args.spec)
    validate_spec(spec, Path(__file__).resolve())
    expected = spec["authenticated_inputs"]
    input_paths = {
        "cells": args.cells,
        "cells_receipt": args.cells_receipt,
        "canonical_spec": args.canonical_spec,
        "membership": args.membership,
        "model_audit": args.model_audit,
    }
    for key, path in input_paths.items():
        actual = sha256_file(path)
        if actual != expected[key]["sha256"]:
            raise Gate2Error(f"{key} SHA-256 differs: {actual}")
    canonical = load_json(args.canonical_spec)
    if canonical.get("spec_id") != spec["canonical_spec"]["spec_id"]:
        raise Gate2Error("canonical specification identifier differs")
    cells_receipt = load_json(args.cells_receipt)
    receipt_hash = cells_receipt.get("cells_sha256")
    if receipt_hash is None:
        receipt_hash = cells_receipt.get("output_hashes", {}).get("aggregate_cells.csv")
    if receipt_hash is None:
        receipt_hash = cells_receipt.get("aggregate_artifact", {}).get("sha256")
    if receipt_hash != expected["cells"]["sha256"]:
        raise Gate2Error("cell receipt does not authenticate aggregate_cells.csv")
    model_audit = load_json(args.model_audit)
    if model_audit.get("cells_sha256") != expected["cells"]["sha256"]:
        raise Gate2Error("numerical audit is not bound to the same cell artifact")
    cells = _read_csv(args.cells, ["occ_code", "month", "family"])
    membership = _read_csv(args.membership, ["occupation_code"])
    cells, membership = validate_inputs(cells, membership, spec)
    support = build_support(cells, membership, spec)
    accounting = build_accounting(cells, spec)
    composition = build_family_composition(accounting["work"], spec)
    certified = {
        row["model_id"]: float(row["focal_target_estimate"])
        for row in model_audit.get("models", [])
        if row.get("a1_certification", {}).get("status") == "PASS_A1_NUMERICAL_CERTIFICATE"
    }
    for model_id in ("pooled", "family_month"):
        if model_id not in certified:
            raise Gate2Error(f"required certified model absent: {model_id}")
    accounting["tail"]["certified_grouped_binomial_targets"] = {
        "pooled": certified["pooled"],
        "family_month": certified["family_month"],
    }
    accounting["tail"]["accounting_minus_grouped_binomial"] = {
        "pooled": accounting["tail"]["D_relative"] - certified["pooled"],
        "family_month": accounting["tail"]["D_relative"] - certified["family_month"],
    }
    output_parent = args.output_parent.resolve()
    output_parent.mkdir(parents=True, exist_ok=True)
    final = output_parent / args.run_id
    if final.exists():
        raise Gate2Error(f"refusing to overwrite existing run: {final.name}")
    staging = Path(tempfile.mkdtemp(prefix=f".{args.run_id}-", dir=output_parent))
    try:
        support["matrix"].to_csv(staging / "SUPPORT_MATRIX.csv", index=False)
        support["family_summary"].to_csv(staging / "FAMILY_SUPPORT_SUMMARY.csv", index=False)
        support["edges"].to_csv(staging / "SUPPORT_EDGES.csv", index=False)
        support["direct"].to_csv(staging / "DIRECT_TAIL_MEMBERSHIP.csv", index=False)
        _write_json(staging / "SUPPORT_GRAPH.json", support["graph"])
        accounting["monthly"].to_csv(staging / "MONTHLY_QUINTILE_STOCKS.csv", index=False)
        accounting["period"].to_csv(staging / "PERIOD_STOCKS.csv", index=False)
        _write_json(staging / "TAIL_LOG_STOCK_ACCOUNTING.json", accounting["tail"])
        composition["rows"].to_csv(staging / "FAMILY_COMPOSITION_DECOMPOSITION.csv", index=False)
        _write_json(staging / "FAMILY_COMPOSITION_SUMMARY.json", composition["summary"])
        _write_json(staging / "ZERO_DENOMINATOR_AUDIT.json", composition["zero_audit"])
        _write_json(staging / "LOG_SHAPLEY_DECOMPOSITION.json", composition["log_shapley"])
        output_hashes = {name: sha256_file(staging / name) for name in OUTPUT_FILES}
        receipt = {
            "schema_version": RECEIPT_SCHEMA,
            "status": "PASS_GATE2_SUPPORT_AND_ACCOUNTING",
            "run_id": args.run_id,
            "spec_id": spec["spec_id"],
            "spec_sha256": sha256_file(args.spec),
            "code_sha256": sha256_file(Path(__file__).resolve()),
            "authenticated_inputs": {
                key: {"sha256": sha256_file(path)} for key, path in input_paths.items()
            },
            "protected_row_level_microdata_opened": False,
            "authenticated_aggregate_cells_opened": True,
            "occupation_count": int(cells["occ_code"].nunique()),
            "observed_month_count": int(cells["month"].nunique()),
            "support_matrix_rows": int(len(support["matrix"])),
            "direct_tail_family_count": int(support["graph"]["direct_q1_q5_family_count"]),
            "support_graph_connected": bool(support["graph"]["connected"]),
            "tail_log_identity_status": accounting["tail"]["status"],
            "family_composition_status": composition["summary"]["status"],
            "inference_executed": False,
            "output_hashes": output_hashes,
        }
        _write_json(staging / "EXECUTION_RECEIPT.json", receipt)
        os.replace(staging, final)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return final


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--spec", required=True, type=Path)
    result.add_argument("--canonical-spec", required=True, type=Path)
    result.add_argument("--cells", required=True, type=Path)
    result.add_argument("--cells-receipt", required=True, type=Path)
    result.add_argument("--membership", required=True, type=Path)
    result.add_argument("--model-audit", required=True, type=Path)
    result.add_argument("--output-parent", required=True, type=Path)
    result.add_argument("--run-id", required=True)
    return result


def main() -> int:
    try:
        final = run(parser().parse_args())
    except (Gate2Error, OSError, ValueError, KeyError) as exc:
        print(f"GATE 2 BLOCKED: {exc}")
        return 2
    print(json.dumps({"status": "PASS", "output": str(final)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
