#!/usr/bin/env python3
"""Execute the corrected-calendar R3 CPS flow and worker-outcome package.

Only aggregate outputs are written. Restricted person and household
identifiers remain in memory and outside git.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import pathlib
import subprocess
from datetime import datetime, timezone

import numpy as np
import pandas as pd


LABEL = "POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1"
PRESPEC_COMMIT = "96801eebad9015e03aae22a599fdf66750b0b0e9"
MARCH_MONTHS = {f"{year}-03" for year in range(2017, 2022)}
BOOTSTRAP_DRAWS = 9_999
BOOTSTRAP_SEED = 2026090524
MDE_MULTIPLIER = 2.8015852181129683
ROOT = pathlib.Path(__file__).resolve().parents[4]


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: pathlib.Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: pathlib.Path, rows: list[dict]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty CSV: {path}")
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def month_string(year: pd.Series, month: pd.Series) -> pd.Series:
    return year.astype(int).astype(str) + "-" + month.astype(int).astype(str).str.zfill(2)


MICRODATA_COLUMNS = [
    "YEAR", "MONTH", "SERIAL", "PERNUM", "CPSID", "CPSIDP", "CPSIDV",
    "MISH", "AGE", "EMPSTAT", "LABFORCE", "OCC", "OCC2010", "WTFINL",
    "ASECFLAG", "CLASSWKR", "UHRSWORKT", "DURUNEMP", "EARNWT", "EARNWEEK",
]
PATCH_COLUMNS = [
    "YEAR", "MONTH", "SERIAL", "PERNUM", "CPSID", "CPSIDP", "CPSIDV",
    "MISH", "AGE", "LNKFW1MWT", "LNKFW1YWT",
]


def _read_microdata(path: pathlib.Path, source: str) -> tuple[pd.DataFrame, dict]:
    pieces: list[pd.DataFrame] = []
    counters = {
        "source": source, "raw_rows": 0, "superseded_march_rows": 0,
        "superseded_march_positive_weight_rows": 0, "retained_analysis_scope_rows": 0,
    }
    for chunk in pd.read_csv(path, usecols=MICRODATA_COLUMNS, chunksize=400_000):
        counters["raw_rows"] += len(chunk)
        month = month_string(chunk.YEAR, chunk.MONTH)
        if source == "base_wide":
            superseded = month.isin(MARCH_MONTHS)
            counters["superseded_march_rows"] += int(superseded.sum())
            counters["superseded_march_positive_weight_rows"] += int(
                (superseded & pd.to_numeric(chunk.WTFINL, errors="coerce").gt(0)).sum()
            )
            chunk = chunk.loc[~superseded].copy()
            month = month.loc[~superseded]
        else:
            if not set(month.unique()).issubset(MARCH_MONTHS):
                raise RuntimeError("March repair contains a non-repair month")
        keep = (
            chunk.ASECFLAG.ne(1)
            & pd.to_numeric(chunk.WTFINL, errors="coerce").gt(0)
            & pd.to_numeric(chunk.AGE, errors="coerce").between(21, 66)
            & pd.to_numeric(chunk.EMPSTAT, errors="coerce").between(10, 36)
        )
        selected = chunk.loc[keep].copy()
        counters["retained_analysis_scope_rows"] += len(selected)
        pieces.append(selected)
    frame = pd.concat(pieces, ignore_index=True)
    return frame, counters


def load_corrected_frame(
    base_path: pathlib.Path, repair_path: pathlib.Path, patch_path: pathlib.Path,
) -> tuple[pd.DataFrame, dict]:
    base, base_counts = _read_microdata(base_path, "base_wide")
    repair, repair_counts = _read_microdata(repair_path, "march_basic_repair")
    corrected = pd.concat([base, repair], ignore_index=True)
    del base, repair
    corrected["month"] = month_string(corrected.YEAR, corrected.MONTH)
    if set(corrected.loc[corrected.month.isin(MARCH_MONTHS), "month"].unique()) != MARCH_MONTHS:
        raise RuntimeError("corrected frame does not contain all five March Basic months")
    key = ["YEAR", "MONTH", "SERIAL", "PERNUM"]
    if corrected.duplicated(key).any():
        raise RuntimeError("corrected microdata merge key is not unique")

    patch_pieces: list[pd.DataFrame] = []
    patch_rows = 0
    for chunk in pd.read_csv(patch_path, usecols=PATCH_COLUMNS, chunksize=500_000):
        patch_rows += len(chunk)
        keep = pd.to_numeric(chunk.AGE, errors="coerce").between(21, 66)
        patch_pieces.append(chunk.loc[keep].copy())
    patch = pd.concat(patch_pieces, ignore_index=True)
    del patch_pieces
    if patch.duplicated(key).any():
        raise RuntimeError("corrected weight-patch merge key is not unique")
    rename = {
        name: f"patch_{name}" for name in
        ["CPSID", "CPSIDP", "CPSIDV", "MISH", "AGE"]
    }
    patch = patch.rename(columns=rename)
    merged = corrected.merge(patch, on=key, how="left", validate="one_to_one", indicator=True)
    unmatched = int(merged._merge.ne("both").sum())
    if unmatched:
        raise RuntimeError(f"corrected microdata has {unmatched} rows absent from the weight patch")
    for name in ["CPSID", "CPSIDP", "CPSIDV", "MISH", "AGE"]:
        left = pd.to_numeric(merged[name], errors="coerce").fillna(-1).astype("int64")
        right = pd.to_numeric(merged[f"patch_{name}"], errors="coerce").fillna(-1).astype("int64")
        if not left.equals(right):
            raise RuntimeError(f"weight patch identifier mismatch: {name}")
    merged = merged.drop(columns=["_merge", *rename.values()])
    integer_columns = [
        "YEAR", "MONTH", "SERIAL", "PERNUM", "CPSID", "CPSIDP", "CPSIDV",
        "MISH", "AGE", "EMPSTAT", "LABFORCE", "OCC", "OCC2010", "CLASSWKR",
        "UHRSWORKT", "DURUNEMP",
    ]
    for column in integer_columns:
        merged[column] = pd.to_numeric(merged[column], errors="raise").astype("int64")
    for column in ["WTFINL", "EARNWT", "EARNWEEK", "LNKFW1MWT", "LNKFW1YWT"]:
        merged[column] = pd.to_numeric(merged[column], errors="coerce").fillna(0).astype("float64")
    merged["month_ord"] = merged.YEAR * 12 + merged.MONTH
    merged["age_group"] = np.where(merged.AGE.between(22, 25), "young_22_25", "older_26_65")
    merged["employed"] = merged.EMPSTAT.isin([10, 12])
    merged["unemployed"] = merged.EMPSTAT.between(20, 22)
    merged["nilf"] = merged.EMPSTAT.between(30, 36)
    merged["nonemployed"] = merged.unemployed | merged.nilf

    march = merged.loc[merged.month.isin(MARCH_MONTHS)]
    if not set(march.month.unique()) == MARCH_MONTHS:
        raise RuntimeError("March replacement disappeared after patch merge")
    receipt = {
        "base": base_counts,
        "repair": repair_counts,
        "corrected_analysis_scope_rows": int(len(merged)),
        "weight_patch_raw_rows": int(patch_rows),
        "weight_patch_analysis_scope_rows": int(len(patch)),
        "merge_key": key,
        "merge_unmatched": unmatched,
        "march_rows_after_replacement": int(len(march)),
        "march_positive_LNKFW1MWT_rows": int(march.LNKFW1MWT.gt(0).sum()),
        "march_positive_LNKFW1YWT_rows": int(march.LNKFW1YWT.gt(0).sum()),
        "duplicate_corrected_keys": 0,
    }
    return merged, receipt


def load_maps(membership_path: pathlib.Path, bridge_path: pathlib.Path) -> tuple[pd.DataFrame, dict, dict, dict, dict]:
    membership = pd.read_csv(membership_path, dtype={"occupation_code": str})
    membership["occupation_code"] = membership.occupation_code.str.zfill(4)
    required = {"occupation_code", "beta_quintile", "webb_z"}
    if not required.issubset(membership.columns):
        raise RuntimeError(f"rebuilt membership lacks {sorted(required - set(membership.columns))}")
    if membership.occupation_code.duplicated().any():
        raise RuntimeError("rebuilt membership occupation codes are duplicated")
    qmap = membership.set_index("occupation_code").beta_quintile.astype(int).to_dict()
    webb_z = pd.to_numeric(membership.set_index("occupation_code").webb_z, errors="coerce").to_dict()
    support = sorted(code for code in qmap if np.isfinite(webb_z.get(code, np.nan)))
    if len(support) != 468:
        raise RuntimeError(f"rebuilt beta/Webb support is not 468 occupations: {len(support)}")
    bridge = pd.read_csv(bridge_path, dtype={"census_2010": str, "census_2018": str})
    bridge["census_2010"] = bridge.census_2010.str.zfill(4)
    bridge["census_2018"] = bridge.census_2018.str.zfill(4)
    bridge["bridge_weight"] = pd.to_numeric(bridge.bridge_weight, errors="raise")
    sums = bridge.groupby("census_2010").bridge_weight.sum()
    if not np.allclose(sums.to_numpy(), 1.0, atol=1e-10, rtol=0):
        raise RuntimeError("bridge route probabilities do not sum to one")
    components = lineage_components(bridge, support)
    return bridge, qmap, {code: float(webb_z[code]) for code in support}, components, {
        "support_occupations": len(support),
        "support_sha256": hashlib.sha256("\n".join(support).encode()).hexdigest(),
        "q5_sha256": hashlib.sha256("\n".join(code for code in support if qmap[code] == 5).encode()).hexdigest(),
        "bridge_source_codes": int(len(sums)),
        "bridge_max_route_sum_error": float(np.max(np.abs(sums.to_numpy() - 1))),
        "lineage_components": len(set(components.values())),
    }


def lineage_components(bridge: pd.DataFrame, support: list[str]) -> dict[str, int]:
    parent = {code: code for code in support}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    for _, group in bridge.loc[bridge.census_2018.isin(parent)].groupby("census_2010"):
        targets = sorted(set(group.census_2018))
        for other in targets[1:]:
            union(targets[0], other)
    roots = sorted({find(code) for code in support})
    root_index = {root: index for index, root in enumerate(roots)}
    return {code: root_index[find(code)] for code in support}


def build_pairs(frame: pd.DataFrame, horizon: str) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    if horizon == "adjacent_month":
        gap, allowed, mish_shift, weight = 1, {1, 2, 3, 5, 6, 7}, 1, "LNKFW1MWT"
    elif horizon == "twelve_month":
        gap, allowed, mish_shift, weight = 12, {1, 2, 3, 4}, 4, "LNKFW1YWT"
    else:
        raise ValueError(horizon)
    observed = set(frame.month_ord.unique())
    origin = frame.loc[
        frame.AGE.between(22, 65) & frame.MISH.isin(allowed) & frame.CPSIDV.ne(0)
    ].copy()
    origin["target_ord"] = origin.month_ord + gap
    origin = origin.loc[origin.target_ord.isin(observed)].copy()
    destination_columns = [
        "CPSIDV", "month_ord", "MISH", "AGE", "YEAR", "EMPSTAT", "LABFORCE",
        "OCC", "OCC2010", "UHRSWORKT", "DURUNEMP", "employed", "unemployed",
        "nilf", "nonemployed",
    ]
    destination = frame.loc[frame.CPSIDV.ne(0), destination_columns].copy()
    if destination.duplicated(["CPSIDV", "month_ord"]).any():
        raise RuntimeError("CPSIDV is duplicated within a corrected Basic Monthly sample")
    destination = destination.rename(
        columns={name: f"{name}_d" for name in destination_columns if name != "CPSIDV"}
    )
    pairs = origin.merge(
        destination, left_on=["CPSIDV", "target_ord"],
        right_on=["CPSIDV", "month_ord_d"], how="left", validate="many_to_one", indicator=True,
    )
    pairs["matched_identifier"] = pairs._merge.eq("both")
    pairs["validated_rotation"] = pairs.matched_identifier & pairs.MISH_d.eq(pairs.MISH + mish_shift)
    pairs["positive_official_weight"] = pairs[weight].gt(0)
    pairs["analysis_link"] = pairs.validated_rotation & pairs.positive_official_weight
    if horizon == "adjacent_month" and (
        pairs.matched_identifier & pairs.month.eq("2025-09") & pairs.month_ord_d.eq(2025 * 12 + 11)
    ).any():
        raise RuntimeError("nonadjacent September-to-November 2025 link was formed")
    linked = pairs.loc[pairs.analysis_link].copy()
    linked["endpoint_age_crosses_26"] = linked.AGE.le(25) & linked.AGE_d.ge(26)
    linked["same_harmonized_occupation"] = (
        linked.employed & linked.employed_d & linked.OCC2010.gt(0) & linked.OCC2010_d.gt(0)
        & linked.OCC2010.eq(linked.OCC2010_d)
    )
    repeat = {
        "validated_positive_weight_links": int(len(linked)),
        "unique_CPSIDV": int(linked.CPSIDV.nunique()),
        "CPSIDV_with_multiple_links": int((linked.groupby("CPSIDV").size() > 1).sum()),
        "maximum_links_per_CPSIDV": int(linked.groupby("CPSIDV").size().max()) if len(linked) else 0,
        "unique_CPSID_households": int(linked.CPSID.nunique()),
        "CPSID_households_with_multiple_links": int((linked.groupby("CPSID").size() > 1).sum()),
        "age_26_crossings": int(linked.endpoint_age_crosses_26.sum()),
        "age_26_crossing_rate": float(linked.endpoint_age_crosses_26.mean()) if len(linked) else None,
    }
    return pairs.drop(columns="_merge"), linked, repeat


def link_audit_rows(pairs: pd.DataFrame, horizon: str, weight: str) -> list[dict]:
    rows: list[dict] = []

    def add(dimension: str, level: str, mask: pd.Series) -> None:
        selected = pairs.loc[mask]
        validated = selected.validated_rotation
        positive = validated & selected.positive_official_weight
        rows.append({
            "analysis_status": LABEL, "horizon": horizon, "official_weight": weight,
            "dimension": dimension, "level": level, "eligible_origins": int(len(selected)),
            "validated_CPSIDV_rotation_links": int(validated.sum()),
            "validated_link_rate": float(validated.mean()) if len(selected) else None,
            "positive_official_weight_links": int(positive.sum()),
            "positive_weight_rate_among_validated": (
                float(selected.loc[validated, "positive_official_weight"].mean()) if validated.any() else None
            ),
            "eligible_origin_WTFINL": float(selected.WTFINL.sum()),
            "retained_origin_WTFINL": float(selected.loc[positive, "WTFINL"].sum()),
        })

    all_rows = pd.Series(True, index=pairs.index)
    add("overall", "all eligible nonzero-CPSIDV origins with observed endpoint month", all_rows)
    add("age", "young 22-25 at origin", pairs.AGE.between(22, 25))
    add("age", "older 26-65 at origin", pairs.AGE.between(26, 65))
    if horizon == "adjacent_month":
        periods = {
            "pre through 2022-11": pairs.month.le("2022-11"),
            "transition 2022-12": pairs.month.eq("2022-12"),
            "post from 2023-01": pairs.month.ge("2023-01"),
        }
    else:
        periods = {
            "non-straddling pre through 2021-11": pairs.month.le("2021-11"),
            "excluded straddling/transition 2021-12 through 2022-12": pairs.month.between("2021-12", "2022-12"),
            "post from 2023-01": pairs.month.ge("2023-01"),
        }
    for level, mask in periods.items():
        add("period", level, mask)
    add("origin_state", "employed", pairs.employed)
    add("origin_state", "unemployed", pairs.unemployed)
    add("origin_state", "not in labor force", pairs.nilf)
    for mish in sorted(pairs.MISH.unique()):
        shift = 1 if horizon == "adjacent_month" else 4
        add("MISH_transition", f"{mish}->{mish + shift}", pairs.MISH.eq(mish))
    return rows


def route_cells(
    base: pd.DataFrame, occ_col: str, year_col: str, bridge: pd.DataFrame,
    qmap: dict[str, int], webb_z: dict[str, float], value_columns: list[str],
    audit_prefix: dict,
) -> tuple[pd.DataFrame, list[dict]]:
    work = base[[year_col, "month", "age_group", occ_col, *value_columns]].copy()
    work["source_occ"] = work[occ_col].astype(int).map(lambda value: f"{value:04d}")
    early_base = work.loc[work[year_col].le(2019)].copy()
    current = work.loc[work[year_col].ge(2020)].copy()
    bridge_codes = set(bridge.census_2010)
    early_mapped = early_base.loc[early_base.source_occ.isin(bridge_codes)].copy()
    early = early_mapped.merge(
        bridge[["census_2010", "census_2018", "bridge_weight"]],
        left_on="source_occ", right_on="census_2010", how="inner", validate="many_to_many",
    )
    early["occ_code"] = early.census_2018
    for column in value_columns:
        early[column] = early[column] * early.bridge_weight
    current["occ_code"] = current.source_occ
    keep = ["occ_code", "month", "age_group", *value_columns]
    routed_all = pd.concat([early[keep], current[keep]], ignore_index=True)
    routed_all["quintile"] = routed_all.occ_code.map(qmap)
    routed_all["webb_z"] = routed_all.occ_code.map(webb_z)
    supported = routed_all.loc[routed_all.quintile.notna() & routed_all.webb_z.notna()].copy()
    supported["quintile"] = supported.quintile.astype(int)
    cells = supported.groupby(
        ["occ_code", "month", "age_group", "quintile", "webb_z"], as_index=False
    )[value_columns].sum()
    audit: list[dict] = []
    for column in value_columns:
        routeable_input = float(early_mapped[column].sum() + current[column].sum())
        routed = float(routed_all[column].sum())
        on_support = float(supported[column].sum())
        error = routed - routeable_input
        absolute_scale = float(early_mapped[column].abs().sum() + current[column].abs().sum())
        tolerance = max(1e-7, absolute_scale * 1e-10)
        if abs(error) > tolerance:
            raise RuntimeError(f"route conservation failed for {audit_prefix} {column}: {error}")
        audit.append({
            "analysis_status": LABEL, **audit_prefix, "quantity": column,
            "input_total": float(work[column].sum()),
            "routeable_input_total": routeable_input, "routed_pre_support_total": routed,
            "route_conservation_error": error, "supported_total": on_support,
            "absolute_routeable_input_total": absolute_scale,
            "support_retention_rate": on_support / routed if routed else None,
            "unmapped_pre2020_source_rows": int(len(early_base) - len(early_mapped)),
        })
    return cells, audit


def quintile_attrition_rows(
    pairs: pd.DataFrame, horizon: str, bridge: pd.DataFrame,
    qmap: dict[str, int], webb_z: dict[str, float],
) -> tuple[list[dict], list[dict]]:
    """Route employed origins for an exposure-specific attrition diagnostic only."""
    base = pairs.loc[pairs.employed & pairs.OCC.gt(0)].copy()
    base["eligible_raw_fraction"] = 1.0
    base["validated_raw_fraction"] = base.validated_rotation.astype(float)
    base["positive_weight_raw_fraction"] = (
        base.validated_rotation & base.positive_official_weight
    ).astype(float)
    base["eligible_WTFINL"] = base.WTFINL
    base["retained_WTFINL"] = np.where(
        base.validated_rotation & base.positive_official_weight, base.WTFINL, 0.0
    )
    value_columns = [
        "eligible_raw_fraction", "validated_raw_fraction", "positive_weight_raw_fraction",
        "eligible_WTFINL", "retained_WTFINL",
    ]
    routed, audit = route_cells(
        base, "OCC", "YEAR", bridge, qmap, webb_z, value_columns,
        {"horizon": horizon, "role": "employed_origin_attrition"},
    )
    rows = []
    for quintile in range(1, 6):
        selected = routed.loc[routed.quintile.eq(quintile)]
        eligible = float(selected.eligible_raw_fraction.sum())
        validated = float(selected.validated_raw_fraction.sum())
        positive = float(selected.positive_weight_raw_fraction.sum())
        eligible_w = float(selected.eligible_WTFINL.sum())
        retained_w = float(selected.retained_WTFINL.sum())
        rows.append({
            "analysis_status": LABEL, "horizon": horizon,
            "dimension": "origin_rebuilt_beta_quintile_route_expanded", "level": f"Q{quintile}",
            "eligible_origins_fractional": eligible,
            "validated_CPSIDV_rotation_links_fractional": validated,
            "validated_link_rate": validated / eligible if eligible else None,
            "positive_official_weight_links_fractional": positive,
            "positive_weight_rate_among_validated": positive / validated if validated else None,
            "eligible_origin_WTFINL": eligible_w, "retained_origin_WTFINL": retained_w,
        })
    return rows, audit


def transition_diagnostic_rows(linked: pd.DataFrame, horizon: str) -> list[dict]:
    rows = []

    def add(period: str, age: str, mask: pd.Series) -> None:
        selected = linked.loc[mask]
        both = selected.employed & selected.employed_d & selected.OCC2010.gt(0) & selected.OCC2010_d.gt(0)
        if horizon == "adjacent_month":
            taxonomy_ok = selected.month.ne("2019-12")
            weight = selected.LNKFW1MWT
        else:
            taxonomy_ok = selected.YEAR.ne(2019)
            weight = selected.LNKFW1YWT
        valid = both & taxonomy_ok
        switch = valid & selected.OCC2010.ne(selected.OCC2010_d)
        rows.append({
            "analysis_status": LABEL, "horizon": horizon, "period": period, "age_group": age,
            "positive_weight_links": int(len(selected)),
            "employed_both_endpoints_valid_OCC2010": int(both.sum()),
            "taxonomy_boundary_excluded": int((both & ~taxonomy_ok).sum()),
            "switch_risk_after_taxonomy_exclusion": int(valid.sum()),
            "endpoint_OCC2010_changes": int(switch.sum()),
            "raw_endpoint_switch_rate": float(switch.sum() / valid.sum()) if valid.any() else None,
            "official_weighted_endpoint_switch_rate": (
                float(weight.loc[switch].sum() / weight.loc[valid].sum()) if valid.any() else None
            ),
            "age_changes_between_endpoints": int(selected.AGE_d.ne(selected.AGE).sum()),
            "age_26_crossings": int((selected.AGE.le(25) & selected.AGE_d.ge(26)).sum()),
        })

    for period, pmask in [("pre", linked.month.lt("2023-01")), ("post", linked.month.ge("2023-01"))]:
        add(period, "young_22_25", pmask & linked.AGE.between(22, 25))
        add(period, "older_26_65", pmask & linked.AGE.between(26, 65))
    return rows


def analysis_period(pairs: pd.DataFrame, horizon: str) -> pd.Series:
    if horizon == "adjacent_month":
        return ~pairs.month.eq("2022-12")
    return pairs.month.le("2021-11") | pairs.month.ge("2023-01")


MARGINS = ["employment_exit", "unemployment_entry", "labor_force_exit", "occupational_outflow"]
WEIGHTINGS = {"official": None, "unweighted": None, "origin_WTFINL": "WTFINL"}


def build_flow_cells(
    linked: pd.DataFrame, horizon: str, bridge: pd.DataFrame,
    qmap: dict[str, int], webb_z: dict[str, float],
) -> tuple[dict, list[dict], list[dict]]:
    link_weight = "LNKFW1MWT" if horizon == "adjacent_month" else "LNKFW1YWT"
    base = linked.loc[analysis_period(linked, horizon) & linked.OCC.gt(0)].copy()
    base["w__official"] = base[link_weight]
    base["w__unweighted"] = 1.0
    base["w__origin_WTFINL"] = base.WTFINL
    outflow_taxonomy_ok = base.month.ne("2019-12") if horizon == "adjacent_month" else base.YEAR.ne(2019)
    exit_risk = base.employed
    events = {
        "employment_exit": exit_risk & base.nonemployed_d,
        "unemployment_entry": exit_risk & base.unemployed_d,
        "labor_force_exit": exit_risk & base.nilf_d,
        "occupational_outflow": (
            exit_risk & base.employed_d & base.OCC2010.gt(0) & base.OCC2010_d.gt(0)
            & outflow_taxonomy_ok & base.OCC2010.ne(base.OCC2010_d)
        ),
    }
    risks = {
        "employment_exit": exit_risk,
        "unemployment_entry": exit_risk,
        "labor_force_exit": exit_risk,
        "occupational_outflow": (
            exit_risk & base.employed_d & base.OCC2010.gt(0) & base.OCC2010_d.gt(0)
            & outflow_taxonomy_ok
        ),
    }
    value_columns: list[str] = []
    count_rows: list[dict] = []
    for weighting in WEIGHTINGS:
        w = base[f"w__{weighting}"]
        for margin in MARGINS:
            risk_col = f"{weighting}__{margin}__risk"
            event_col = f"{weighting}__{margin}__event"
            base[risk_col] = np.where(risks[margin], w, 0.0)
            base[event_col] = np.where(events[margin], w, 0.0)
            value_columns.extend([risk_col, event_col])
            count_rows.append({
                "analysis_status": LABEL, "horizon": horizon, "weighting": weighting,
                "margin": margin, "risk_raw_records": int(risks[margin].sum()),
                "event_raw_records": int(events[margin].sum()),
                "risk_weight": float(base[risk_col].sum()),
                "event_weight": float(base[event_col].sum()),
                "young_event_raw_records": int((events[margin] & base.AGE.between(22, 25)).sum()),
                "post_event_raw_records": int((events[margin] & base.month.ge("2023-01")).sum()),
            })
    routed, route_audit = route_cells(
        base, "OCC", "YEAR", bridge, qmap, webb_z, value_columns,
        {"horizon": horizon, "role": "employed_origin"},
    )
    cells: dict[tuple[str, str], pd.DataFrame] = {}
    for weighting in WEIGHTINGS:
        for margin in MARGINS:
            selected = routed[["occ_code", "month", "age_group", "quintile", "webb_z",
                               f"{weighting}__{margin}__risk", f"{weighting}__{margin}__event"]].copy()
            selected = selected.rename(columns={
                f"{weighting}__{margin}__risk": "risk",
                f"{weighting}__{margin}__event": "event",
            })
            cells[(margin, weighting)] = selected

    # Entry is a destination-allocation quantity conditional on observed N->E.
    entries = linked.loc[
        analysis_period(linked, horizon) & linked.nonemployed & linked.employed_d & linked.OCC_d.gt(0)
    ].copy()
    entries["w__official"] = entries[link_weight]
    entries["w__unweighted"] = 1.0
    entries["w__origin_WTFINL"] = entries.WTFINL
    entry_values = []
    for weighting in WEIGHTINGS:
        name = f"{weighting}__entry_destination__event"
        entries[name] = entries[f"w__{weighting}"]
        entry_values.append(name)
        count_rows.append({
            "analysis_status": LABEL, "horizon": horizon, "weighting": weighting,
            "margin": "entry_destination", "risk_raw_records": int(len(entries)),
            "event_raw_records": int(len(entries)),
            "risk_weight": float(entries[name].sum()), "event_weight": float(entries[name].sum()),
            "young_event_raw_records": int(entries.AGE.between(22, 25).sum()),
            "post_event_raw_records": int(entries.month.ge("2023-01").sum()),
        })
    routed_entry, entry_audit = route_cells(
        entries, "OCC_d", "YEAR_d", bridge, qmap, webb_z, entry_values,
        {"horizon": horizon, "role": "entry_destination"},
    )
    route_audit.extend(entry_audit)
    for weighting in WEIGHTINGS:
        selected = routed_entry[["occ_code", "month", "age_group", "quintile", "webb_z",
                                 f"{weighting}__entry_destination__event"]].copy()
        cells[("entry_destination", weighting)] = selected.rename(
            columns={f"{weighting}__entry_destination__event": "event"}
        )
    return cells, count_rows, route_audit


def build_hours_cells(
    linked: pd.DataFrame, bridge: pd.DataFrame, qmap: dict[str, int], webb_z: dict[str, float],
) -> tuple[dict, list[dict], list[dict], list[dict]]:
    valid = (
        analysis_period(linked, "adjacent_month") & linked.employed & linked.employed_d
        & linked.OCC.gt(0) & linked.UHRSWORKT.between(1, 99) & linked.UHRSWORKT_d.between(1, 99)
    )
    base = linked.loc[valid].copy()
    base["hours_change"] = base.UHRSWORKT_d - base.UHRSWORKT
    count_rows, value_columns = [], []
    for weighting, source in [("official", "LNKFW1MWT"), ("unweighted", None), ("origin_WTFINL", "WTFINL")]:
        w = np.ones(len(base)) if source is None else base[source].to_numpy(float)
        risk = f"{weighting}__hours_change__risk"
        total = f"{weighting}__hours_change__total"
        base[risk] = w
        base[total] = w * base.hours_change
        value_columns.extend([risk, total])
        count_rows.append({
            "analysis_status": LABEL, "horizon": "adjacent_month", "weighting": weighting,
            "margin": "usual_hours_change_continuing_workers",
            "risk_raw_records": int(len(base)), "event_raw_records": int(len(base)),
            "risk_weight": float(np.sum(w)), "event_weight": float(np.sum(w * base.hours_change)),
            "young_event_raw_records": int(base.AGE.between(22, 25).sum()),
            "post_event_raw_records": int(base.month.ge("2023-01").sum()),
        })
    routed, audit = route_cells(
        base, "OCC", "YEAR", bridge, qmap, webb_z, value_columns,
        {"horizon": "adjacent_month", "role": "continuing_worker_hours"},
    )
    cells = {}
    for weighting in WEIGHTINGS:
        columns = ["occ_code", "month", "age_group", "quintile", "webb_z",
                   f"{weighting}__hours_change__risk", f"{weighting}__hours_change__total"]
        cells[weighting] = routed[columns].rename(columns={
            f"{weighting}__hours_change__risk": "risk",
            f"{weighting}__hours_change__total": "total",
        })
    desc = []
    for period, mask in [("pre", base.month.le("2022-11")), ("post", base.month.ge("2023-01"))]:
        for age, age_mask in [("young_22_25", base.AGE.between(22, 25)), ("older_26_65", base.AGE.between(26, 65))]:
            selected = base.loc[mask & age_mask]
            if len(selected):
                desc.append({
                    "analysis_status": LABEL, "outcome": "usual_hours_change_continuing_workers",
                    "period": period, "age_group": age, "raw_records": int(len(selected)),
                    "official_weighted_mean_change_hours": float(np.average(selected.hours_change, weights=selected.LNKFW1MWT)),
                })
    return cells, count_rows, audit, desc


def build_earnings_cells(
    frame: pd.DataFrame, bridge: pd.DataFrame, qmap: dict[str, int], webb_z: dict[str, float],
) -> tuple[pd.DataFrame, list[dict], list[dict]]:
    valid = (
        frame.AGE.between(22, 65) & frame.employed & frame.OCC.gt(0)
        & frame.MISH.isin([4, 8]) & frame.EARNWT.gt(0)
        & frame.EARNWEEK.gt(0) & frame.EARNWEEK.lt(9999.99)
        & frame.month.ne("2022-12")
    )
    base = frame.loc[valid].copy()
    base["earnings__risk"] = base.EARNWT
    base["earnings__event"] = base.EARNWT * base.EARNWEEK
    cells, audit = route_cells(
        base, "OCC", "YEAR", bridge, qmap, webb_z,
        ["earnings__risk", "earnings__event"],
        {"horizon": "cross_sectional_month", "role": "ORG_weekly_earnings"},
    )
    cells = cells.rename(columns={"earnings__risk": "risk", "earnings__event": "event"})
    counts = [{
        "analysis_status": LABEL, "horizon": "cross_sectional_month", "weighting": "EARNWT",
        "margin": "weekly_earnings_conditional_workers", "risk_raw_records": int(len(base)),
        "event_raw_records": int(len(base)), "risk_weight": float(base.EARNWT.sum()),
        "event_weight": float((base.EARNWT * base.EARNWEEK).sum()),
        "young_event_raw_records": int(base.AGE.between(22, 25).sum()),
        "post_event_raw_records": int(base.month.ge("2023-01").sum()),
    }]
    return cells, counts, audit


def _sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(values, -700, 700)))


def _weighted_absorb(
    values: np.ndarray, weights: np.ndarray, occ: np.ndarray, month: np.ndarray,
    n_occ: int, n_month: int, tolerance: float = 1e-11, max_iterations: int = 20_000,
) -> np.ndarray:
    result = np.asarray(values, dtype=float).copy()
    was_vector = result.ndim == 1
    if was_vector:
        result = result[:, None]
    for _ in range(max_iterations):
        old = result.copy()
        occ_denom = np.bincount(occ, weights=weights, minlength=n_occ)
        for column in range(result.shape[1]):
            numerator = np.bincount(occ, weights=weights * result[:, column], minlength=n_occ)
            mean = np.divide(numerator, occ_denom, out=np.zeros_like(numerator), where=occ_denom > 0)
            result[:, column] -= mean[occ]
        month_denom = np.bincount(month, weights=weights, minlength=n_month)
        for column in range(result.shape[1]):
            numerator = np.bincount(month, weights=weights * result[:, column], minlength=n_month)
            mean = np.divide(numerator, month_denom, out=np.zeros_like(numerator), where=month_denom > 0)
            result[:, column] -= mean[month]
        if np.max(np.abs(result - old)) < tolerance:
            return result[:, 0] if was_vector else result
    raise RuntimeError("weighted two-way absorption did not converge")


def fit_offset(
    young: np.ndarray, total: np.ndarray, occ: np.ndarray, month: np.ndarray,
    regressors: np.ndarray, offset: np.ndarray, max_iterations: int = 5_000,
) -> dict:
    keep = total > 0
    y, n, o0, t, x, off = young[keep], total[keep], occ[keep], month[keep], regressors[keep], offset[keep]
    used_occ = np.unique(o0)
    remap = {old: new for new, old in enumerate(used_occ)}
    o = np.array([remap[value] for value in o0], int)
    n_occ, n_month = len(used_occ), int(t.max()) + 1
    occ_y = np.bincount(o, weights=y, minlength=n_occ)
    occ_n = np.bincount(o, weights=n, minlength=n_occ)
    share = np.clip((occ_y + 0.5) / (occ_n + 1.0), 1e-8, 1 - 1e-8)
    mean_offset = np.divide(
        np.bincount(o, weights=n * off, minlength=n_occ), occ_n,
        out=np.zeros(n_occ), where=occ_n > 0,
    )
    occ_effect = np.log(share / (1 - share)) - mean_offset
    month_effect = np.zeros(n_month)
    beta = np.zeros(x.shape[1])
    for iteration in range(1, max_iterations + 1):
        for _ in range(2):
            eta = off + occ_effect[o] + month_effect[t] + x @ beta
            p = np.clip(_sigmoid(eta), 1e-10, 1 - 1e-10)
            residual, info_w = y - n * p, np.maximum(n * p * (1 - p), 1e-12)
            score = np.bincount(o, weights=residual, minlength=n_occ)
            info = np.bincount(o, weights=info_w, minlength=n_occ)
            occ_effect += np.clip(np.divide(score, info, out=np.zeros_like(score), where=info > 0), -1, 1)
            eta = off + occ_effect[o] + month_effect[t] + x @ beta
            p = np.clip(_sigmoid(eta), 1e-10, 1 - 1e-10)
            residual, info_w = y - n * p, np.maximum(n * p * (1 - p), 1e-12)
            score = np.bincount(t, weights=residual, minlength=n_month)
            info = np.bincount(t, weights=info_w, minlength=n_month)
            month_effect += np.clip(np.divide(score, info, out=np.zeros_like(score), where=info > 0), -1, 1)
            anchor = month_effect[0]
            month_effect -= anchor
            occ_effect += anchor
        eta = off + occ_effect[o] + month_effect[t] + x @ beta
        p = np.clip(_sigmoid(eta), 1e-10, 1 - 1e-10)
        residual, info_w = y - n * p, np.maximum(n * p * (1 - p), 1e-12)
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
        raise RuntimeError("grouped conditional-Poisson representation did not converge")
    eta = off + occ_effect[o] + month_effect[t] + x @ beta
    p = np.clip(_sigmoid(eta), 1e-10, 1 - 1e-10)
    residual, info_w = y - n * p, np.maximum(n * p * (1 - p), 1e-12)
    rx = _weighted_absorb(x, info_w, o, t, n_occ, n_month)
    bread = np.linalg.inv(rx.T @ (info_w[:, None] * rx))
    raw_scores = np.zeros((n_occ, x.shape[1]))
    np.add.at(raw_scores, o, rx * residual[:, None])
    raw_influence = raw_scores @ bread.T
    return {
        "beta": beta, "raw_influence": raw_influence, "used_occ_indices": used_occ,
        "iterations": iteration, "fitted_cells": int(keep.sum()),
    }


def design_from_cells(cells: pd.DataFrame) -> dict:
    months = sorted(cells.month.unique())
    occupations = sorted(cells.occ_code.unique())
    ages = ["young_22_25", "older_26_65"]
    index = pd.MultiIndex.from_product([occupations, months, ages], names=["occ_code", "month", "age_group"])
    value_columns = [name for name in ["risk", "event", "total"] if name in cells]
    panel = cells.groupby(["occ_code", "month", "age_group"], as_index=True)[value_columns].sum().reindex(index, fill_value=0.0)
    q = cells.drop_duplicates("occ_code").set_index("occ_code").quintile.reindex(occupations).to_numpy(int)
    webb = cells.drop_duplicates("occ_code").set_index("occ_code").webb_z.reindex(occupations).to_numpy(float)
    post = np.array([month >= "2023-01" for month in months])
    columns = [
        ((q[:, None] == value) & post[None, :]).reshape(-1).astype(float)
        for value in [2, 3, 4, 5]
    ]
    columns.append((webb[:, None] * post[None, :]).reshape(-1))
    regressors = np.column_stack(columns)
    return {
        "months": months, "occupations": occupations, "panel": panel,
        "regressors": regressors,
        "occ_index": np.repeat(np.arange(len(occupations)), len(months)),
        "month_index": np.tile(np.arange(len(months)), len(occupations)),
    }


def _wild_summary(
    beta: float, raw_influence: np.ndarray, used_codes: list[str], canonical_codes: list[str],
    signs: np.ndarray,
) -> tuple[dict, list[dict]]:
    g = len(used_codes)
    factor = math.sqrt(g / (g - 1)) if g > 1 else 1.0
    influence = raw_influence * factor
    se = float(np.sqrt(np.sum(influence**2)))
    canonical_index = {code: i for i, code in enumerate(canonical_codes)}
    shifts = signs[:, [canonical_index[code] for code in used_codes]] @ influence
    studentizer = se if se > 0 else float(np.std(shifts, ddof=1))
    critical = float(np.quantile(np.abs(shifts / studentizer), 0.95, method="higher"))
    pvalue = float((1 + np.sum(np.abs(shifts / studentizer) >= abs(beta / studentizer))) / (len(shifts) + 1))
    rows = [
        {"occ_code": code, "target_influence": float(value)}
        for code, value in zip(used_codes, influence, strict=True)
    ]
    return {
        "analytic_occupation_cluster_se": se,
        "wild_score_ci_lower": float(beta - critical * se),
        "wild_score_ci_upper": float(beta + critical * se),
        "wild_score_p_value": pvalue, "wild_score_critical": critical,
        "normal_theory_MDE80": float(MDE_MULTIPLIER * se),
    }, rows


def _lineage_summary(
    beta: float, raw_influence: np.ndarray, used_codes: list[str], components: dict[str, int],
    component_signs: np.ndarray,
) -> dict:
    component_ids = sorted({components[code] for code in used_codes})
    remap = {value: index for index, value in enumerate(component_ids)}
    aggregate = np.zeros(len(component_ids))
    for code, value in zip(used_codes, raw_influence, strict=True):
        aggregate[remap[components[code]]] += value
    g = len(aggregate)
    aggregate *= math.sqrt(g / (g - 1)) if g > 1 else 1.0
    se = float(np.sqrt(np.sum(aggregate**2)))
    shifts = component_signs[:, component_ids] @ aggregate
    studentizer = se if se > 0 else float(np.std(shifts, ddof=1))
    critical = float(np.quantile(np.abs(shifts / studentizer), 0.95, method="higher"))
    pvalue = float((1 + np.sum(np.abs(shifts / studentizer) >= abs(beta / studentizer))) / (len(shifts) + 1))
    return {
        "lineage_component_clusters": g,
        "lineage_component_cluster_se": se,
        "lineage_wild_ci_lower": float(beta - critical * se),
        "lineage_wild_ci_upper": float(beta + critical * se),
        "lineage_wild_p_value": pvalue,
    }


def fit_rate_model(
    cells: pd.DataFrame, model_id: str, horizon: str, weighting: str,
    canonical_codes: list[str], signs: np.ndarray, components: dict[str, int],
    component_signs: np.ndarray,
) -> tuple[dict, list[dict]]:
    data = design_from_cells(cells)
    panel = data["panel"]
    n_occ, n_month = len(data["occupations"]), len(data["months"])
    event_y = panel.xs("young_22_25", level="age_group").event.to_numpy().reshape(n_occ, n_month)
    event_o = panel.xs("older_26_65", level="age_group").event.to_numpy().reshape(n_occ, n_month)
    if "risk" in panel:
        risk_y = panel.xs("young_22_25", level="age_group").risk.to_numpy().reshape(n_occ, n_month)
        risk_o = panel.xs("older_26_65", level="age_group").risk.to_numpy().reshape(n_occ, n_month)
        valid = (risk_y > 0) & (risk_o > 0)
        offset = np.log(np.clip(risk_y, 1e-12, None) / np.clip(risk_o, 1e-12, None)).reshape(-1)
    else:
        valid = np.ones_like(event_y, dtype=bool)
        offset = np.zeros(event_y.size)
    total = (event_y + event_o).reshape(-1)
    total[~valid.reshape(-1)] = 0
    fit = fit_offset(
        event_y.reshape(-1), total, data["occ_index"], data["month_index"],
        data["regressors"], offset,
    )
    target = 3
    beta = float(fit["beta"][target])
    used_codes = [data["occupations"][int(index)] for index in fit["used_occ_indices"]]
    primary, influence_rows = _wild_summary(
        beta, fit["raw_influence"][:, target], used_codes, canonical_codes, signs,
    )
    lineage = _lineage_summary(
        beta, fit["raw_influence"][:, target], used_codes, components, component_signs,
    )
    row = {
        "analysis_status": LABEL, "model_id": model_id, "horizon": horizon,
        "weighting": weighting, "estimand": "beta_Q5_vs_Q1_x_young_x_post",
        "coefficient": beta, "coefficient_units": "log relative rate/allocation ratio",
        "relative_percent": float(100 * (math.exp(beta) - 1)), **primary, **lineage,
        "bootstrap_draws": BOOTSTRAP_DRAWS, "bootstrap_seed": BOOTSTRAP_SEED,
        "occupations_on_input": len(data["occupations"]),
        "event_contributing_occupations": len(used_codes),
        "fitted_occupation_months": fit["fitted_cells"], "iterations": fit["iterations"],
        "months": len(data["months"]), "first_month": data["months"][0],
        "last_month": data["months"][-1], "december_2022_excluded": "2022-12" not in data["months"],
        "annual_straddling_origins_excluded": horizon == "twelve_month",
    }
    for item in influence_rows:
        item.update({"analysis_status": LABEL, "model_id": model_id})
    return row, influence_rows


def fit_hours_change_model(
    cells: pd.DataFrame, model_id: str, weighting: str, canonical_codes: list[str],
    signs: np.ndarray, components: dict[str, int], component_signs: np.ndarray,
) -> tuple[dict, list[dict]]:
    data = design_from_cells(cells)
    panel = data["panel"]
    n_occ, n_month = len(data["occupations"]), len(data["months"])
    risk_y = panel.xs("young_22_25", level="age_group").risk.to_numpy().reshape(n_occ, n_month)
    risk_o = panel.xs("older_26_65", level="age_group").risk.to_numpy().reshape(n_occ, n_month)
    total_y = panel.xs("young_22_25", level="age_group").total.to_numpy().reshape(n_occ, n_month)
    total_o = panel.xs("older_26_65", level="age_group").total.to_numpy().reshape(n_occ, n_month)
    valid = (risk_y > 0) & (risk_o > 0)
    y = np.divide(total_y, risk_y, out=np.zeros_like(total_y), where=risk_y > 0) - np.divide(
        total_o, risk_o, out=np.zeros_like(total_o), where=risk_o > 0
    )
    harmonic = np.divide(risk_y * risk_o, risk_y + risk_o, out=np.zeros_like(risk_y), where=(risk_y + risk_o) > 0)
    keep = valid.reshape(-1)
    yv = y.reshape(-1)[keep]
    w = harmonic.reshape(-1)[keep]
    o0 = data["occ_index"][keep]
    t = data["month_index"][keep]
    x = data["regressors"][keep]
    used_occ = np.unique(o0)
    remap = {old: new for new, old in enumerate(used_occ)}
    o = np.array([remap[value] for value in o0], int)
    ry = _weighted_absorb(yv, w, o, t, len(used_occ), n_month)
    rx = _weighted_absorb(x, w, o, t, len(used_occ), n_month)
    information = rx.T @ (w[:, None] * rx)
    beta_vector = np.linalg.solve(information, rx.T @ (w * ry))
    residual = ry - rx @ beta_vector
    bread = np.linalg.inv(information)
    raw_scores = np.zeros((len(used_occ), x.shape[1]))
    np.add.at(raw_scores, o, rx * (w * residual)[:, None])
    raw_influence = raw_scores @ bread.T
    target = 3
    beta = float(beta_vector[target])
    used_codes = [data["occupations"][int(index)] for index in used_occ]
    primary, influence_rows = _wild_summary(
        beta, raw_influence[:, target], used_codes, canonical_codes, signs,
    )
    lineage = _lineage_summary(
        beta, raw_influence[:, target], used_codes, components, component_signs,
    )
    row = {
        "analysis_status": LABEL, "model_id": model_id, "horizon": "adjacent_month",
        "weighting": weighting, "estimand": "beta_Q5_vs_Q1_x_young_x_post",
        "coefficient": beta, "coefficient_units": "hours per week, young-minus-older change contrast",
        "relative_percent": None, **primary, **lineage,
        "bootstrap_draws": BOOTSTRAP_DRAWS, "bootstrap_seed": BOOTSTRAP_SEED,
        "occupations_on_input": len(data["occupations"]),
        "event_contributing_occupations": len(used_codes),
        "fitted_occupation_months": int(keep.sum()), "iterations": 1,
        "months": len(data["months"]), "first_month": data["months"][0],
        "last_month": data["months"][-1], "december_2022_excluded": True,
        "annual_straddling_origins_excluded": False,
    }
    for item in influence_rows:
        item.update({"analysis_status": LABEL, "model_id": model_id})
    return row, influence_rows


def descriptive_rate_rows(cells: pd.DataFrame, horizon: str, margin: str) -> list[dict]:
    rows: list[dict] = []
    for period, period_mask in [("pre", cells.month.lt("2023-01")), ("post", cells.month.ge("2023-01"))]:
        for age in ["young_22_25", "older_26_65"]:
            for quintile in [1, 5]:
                selected = cells.loc[period_mask & cells.age_group.eq(age) & cells.quintile.eq(quintile)]
                event = float(selected.event.sum())
                if "risk" in selected:
                    risk = float(selected.risk.sum())
                    value = event / risk if risk else None
                    unit = "event per at-risk origin"
                else:
                    denominator = float(cells.loc[period_mask & cells.age_group.eq(age), "event"].sum())
                    risk = denominator
                    value = event / denominator if denominator else None
                    unit = "share of supported observed entry destinations"
                rows.append({
                    "analysis_status": LABEL, "horizon": horizon, "margin": margin,
                    "period": period, "age_group": age, "quintile": quintile,
                    "event_weight": event, "denominator_weight": risk,
                    "descriptive_rate_or_share": value, "unit": unit,
                })
    return rows


def duration_descriptives(linked: pd.DataFrame, horizon: str) -> list[dict]:
    weight = "LNKFW1MWT" if horizon == "adjacent_month" else "LNKFW1YWT"
    sample = linked.loc[
        analysis_period(linked, horizon) & linked.employed & linked.unemployed_d
        & linked.DURUNEMP_d.between(0, 998)
    ].copy()
    rows = []
    for period, pmask in [("pre", sample.month.lt("2023-01")), ("post", sample.month.ge("2023-01"))]:
        for age, amask in [("young_22_25", sample.AGE.between(22, 25)), ("older_26_65", sample.AGE.between(26, 65))]:
            selected = sample.loc[pmask & amask]
            if selected.empty:
                continue
            rows.append({
                "analysis_status": LABEL, "horizon": horizon, "period": period,
                "age_group": age, "raw_employed_to_unemployed_events": int(len(selected)),
                "weighted_mean_destination_duration_weeks": float(np.average(selected.DURUNEMP_d, weights=selected[weight])),
                "median_destination_duration_weeks": float(selected.DURUNEMP_d.median()),
                "interpretation": "selected descriptive duration among observed E-to-U endpoint events; not an at-risk exposure effect",
            })
    return rows


def stock_flow_bridge_rows() -> list[dict]:
    return [
        {
            "quantity": "YAX employment stock", "population": "monthly CPS ages 22-25 versus 26-65",
            "denominator": "survey-weighted employment stock", "observed_changes": "net entry, exit, switching, aging, population/composition",
            "match_to_flow_package": "not an accounting identity; repeated cross-sections and linked samples differ",
        },
        {
            "quantity": "adjacent CPS employment exit", "population": "positive-LNKFW1MWT validated employed origins",
            "denominator": "linked employed origins", "observed_changes": "employment to unemployment or NILF at t+1",
            "match_to_flow_package": "valid origin-exposure rate; misses job-to-job employer changes",
        },
        {
            "quantity": "adjacent CPS entry destination", "population": "validated N-to-E links only",
            "denominator": "observed supported entries by age-month", "observed_changes": "allocation across destination occupations",
            "match_to_flow_package": "not an employment-finding probability or employer hire rate",
        },
        {
            "quantity": "annual CPS endpoint", "population": "positive-LNKFW1YWT validated origin-endpoint links",
            "denominator": "linked origins or observed N-to-E endpoints", "observed_changes": "status/code difference at t+12",
            "match_to_flow_package": "misses intervening spells and jobs; young origins age during horizon",
        },
        {
            "quantity": "BCC payroll hiring", "population": "full-time positive-earnings worker-firm matches in balanced ADP firms",
            "denominator": "prior worker stock under BCC definition", "observed_changes": "new employer matches over prior year",
            "match_to_flow_package": "CPS has no employer identifier; no numerical calibration is identified",
        },
    ]


def run(args: argparse.Namespace) -> dict:
    if subprocess.run(["git", "merge-base", "--is-ancestor", PRESPEC_COMMIT, "HEAD"], cwd=ROOT).returncode:
        raise RuntimeError("flow pre-results specification commit is not an ancestor of execution HEAD")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    input_hashes = {
        "base_wide": sha256(args.microdata), "march_repair": sha256(args.repair_microdata),
        "corrected_weight_patch": sha256(args.weight_patch), "membership": sha256(args.membership),
        "bridge": sha256(args.bridge), "analysis_spec": sha256(args.analysis_spec),
    }
    frame, reconstruction = load_corrected_frame(args.microdata, args.repair_microdata, args.weight_patch)
    bridge, qmap, webb_z, components, map_receipt = load_maps(args.membership, args.bridge)
    canonical_codes = sorted(qmap)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    signs = rng.choice(np.array([-1.0, 1.0]), size=(BOOTSTRAP_DRAWS, len(canonical_codes)))
    component_count = len(set(components.values()))
    component_signs = rng.choice(np.array([-1.0, 1.0]), size=(BOOTSTRAP_DRAWS, component_count))

    link_rows, repeat_receipt, linked_by_horizon = [], {}, {}
    transition_rows: list[dict] = []
    all_cells: dict[tuple[str, str, str], pd.DataFrame] = {}
    count_rows, route_rows, duration_rows = [], [], []
    for horizon in ["adjacent_month", "twelve_month"]:
        pairs, linked, repeats = build_pairs(frame, horizon)
        linked_by_horizon[horizon] = linked
        weight = "LNKFW1MWT" if horizon == "adjacent_month" else "LNKFW1YWT"
        link_rows.extend(link_audit_rows(pairs, horizon, weight))
        quintile_rows, attrition_routes = quintile_attrition_rows(
            pairs, horizon, bridge, qmap, webb_z
        )
        link_rows.extend(quintile_rows)
        route_rows.extend(attrition_routes)
        repeat_receipt[horizon] = repeats
        transition_rows.extend(transition_diagnostic_rows(linked, horizon))
        cells, counts, routes = build_flow_cells(linked, horizon, bridge, qmap, webb_z)
        for (margin, weighting), value in cells.items():
            all_cells[(horizon, margin, weighting)] = value
        count_rows.extend(counts)
        route_rows.extend(routes)
        duration_rows.extend(duration_descriptives(linked, horizon))
        del pairs

    hours_cells, hours_counts, hours_routes, hours_desc = build_hours_cells(
        linked_by_horizon["adjacent_month"], bridge, qmap, webb_z
    )
    count_rows.extend(hours_counts)
    route_rows.extend(hours_routes)
    earnings_cells, earnings_counts, earnings_routes = build_earnings_cells(frame, bridge, qmap, webb_z)
    count_rows.extend(earnings_counts)
    route_rows.extend(earnings_routes)

    results, influences, failures, descriptive = [], [], [], []
    for horizon in ["adjacent_month", "twelve_month"]:
        for margin in [*MARGINS, "entry_destination"]:
            for weighting in WEIGHTINGS:
                model_id = f"{horizon}__{margin}__{weighting}"
                print(f"FITTING {model_id}", flush=True)
                try:
                    row, influence = fit_rate_model(
                        all_cells[(horizon, margin, weighting)], model_id, horizon, weighting,
                        canonical_codes, signs, components, component_signs,
                    )
                    results.append(row)
                    influences.extend(influence)
                    print(f"DONE {model_id} beta={row['coefficient']:.8f}", flush=True)
                except Exception as error:  # keep a declared failure rather than substitute a model
                    failures.append({"model_id": model_id, "error_type": type(error).__name__, "error": str(error)})
                    print(f"FAILED {model_id}: {error}", flush=True)
            descriptive.extend(descriptive_rate_rows(
                all_cells[(horizon, margin, "official")], horizon, margin
            ))

    for weighting, cells in hours_cells.items():
        model_id = f"adjacent_month__usual_hours_change_continuing_workers__{weighting}"
        print(f"FITTING {model_id}", flush=True)
        try:
            row, influence = fit_hours_change_model(
                cells, model_id, weighting, canonical_codes, signs, components, component_signs,
            )
            results.append(row)
            influences.extend(influence)
            print(f"DONE {model_id} beta={row['coefficient']:.8f}", flush=True)
        except Exception as error:
            failures.append({"model_id": model_id, "error_type": type(error).__name__, "error": str(error)})
            print(f"FAILED {model_id}: {error}", flush=True)

    earnings_model_id = "cross_sectional_month__weekly_earnings_conditional_workers__EARNWT"
    print(f"FITTING {earnings_model_id}", flush=True)
    try:
        row, influence = fit_rate_model(
            earnings_cells, earnings_model_id, "cross_sectional_month", "EARNWT",
            canonical_codes, signs, components, component_signs,
        )
        results.append(row)
        influences.extend(influence)
        print(f"DONE {earnings_model_id} beta={row['coefficient']:.8f}", flush=True)
    except Exception as error:
        failures.append({"model_id": earnings_model_id, "error_type": type(error).__name__, "error": str(error)})
        print(f"FAILED {earnings_model_id}: {error}", flush=True)

    # One declared near-age changed-population sensitivity for adjacent employment exit.
    near = linked_by_horizon["adjacent_month"].loc[
        linked_by_horizon["adjacent_month"].AGE.between(22, 30)
    ].copy()
    near["age_group"] = np.where(near.AGE.between(22, 25), "young_22_25", "older_26_65")
    near_cells, near_counts, near_routes = build_flow_cells(near, "adjacent_month", bridge, qmap, webb_z)
    count_rows.extend([
        {**row, "margin": "employment_exit_near_age_26_30"}
        for row in near_counts if row["margin"] == "employment_exit" and row["weighting"] == "official"
    ])
    route_rows.extend([{**row, "role": f"near_age_{row['role']}"} for row in near_routes])
    near_id = "adjacent_month__employment_exit__official__older_26_30"
    try:
        row, influence = fit_rate_model(
            near_cells[("employment_exit", "official")], near_id, "adjacent_month", "official",
            canonical_codes, signs, components, component_signs,
        )
        row["comparison_age_group"] = "26-30 (changed population sensitivity)"
        results.append(row)
        influences.extend(influence)
    except Exception as error:
        failures.append({"model_id": near_id, "error_type": type(error).__name__, "error": str(error)})

    output_files = {
        "LINK_ATTRITION_AUDIT.csv": link_rows,
        "FLOW_RISK_EVENT_COUNTS.csv": count_rows,
        "ROUTE_AND_SUPPORT_AUDIT.csv": route_rows,
        "FLOW_AND_WORKER_OUTCOME_RESULTS.csv": results,
        "FLOW_DESCRIPTIVE_RATES.csv": descriptive,
        "HOURS_CHANGE_DESCRIPTIVES.csv": hours_desc,
        "UNEMPLOYMENT_DURATION_DESCRIPTIVES.csv": duration_rows,
        "LINK_TRANSITION_DIAGNOSTICS.csv": transition_rows,
        "TARGET_OCCUPATION_INFLUENCE.csv": influences,
        "STOCK_FLOW_BCC_COMPARABILITY.csv": stock_flow_bridge_rows(),
    }
    for filename, rows in output_files.items():
        write_csv(args.output_dir / filename, rows)
    write_json(args.output_dir / "MODEL_FAILURES.json", failures)
    feasibility = args.output_dir / "OUTCOME_FEASIBILITY_AND_LIMITS.md"
    feasibility.write_text(
        f"""# R3 flow and outcome feasibility

> **{LABEL}**

The package uses official adjacent-month and adjacent-year IPUMS link weights
on stricter validated `CPSIDV` links. Adjacent and annual estimates describe
positive-weight linked populations, not the full monthly CPS population. The
annual endpoint is not a sum of monthly transitions and can miss intervening
jobs and spells. Ages are fixed at origin; annual young origins may be age 26
at the endpoint.

Employment exit is split into unemployment entry and labor-force exit from an
employed origin. This is the only occupation-exposure LFP margin executed:
nonemployed respondents are not assigned a fabricated current occupation.
Unemployment duration is reported descriptively only among selected observed
E-to-U endpoints and is not treated as an at-risk effect.

Usual-hours change is estimated only among workers employed with valid hours
at both adjacent interviews. Weekly earnings use the official `EARNWT` in a
cross-sectional outgoing-rotation sample. No linked annual earnings model is
reported because the available documentation gives separate link and earnings
weights but no validated combined longitudinal-earnings weight.

Occupation-cluster and route-lineage-component intervals describe declared
economic-shock dependence sensitivities. Neither is full CPS complex-survey
inference. Repeated households/persons are disclosed in the receipt. These
variances are not mechanically added to separate household-resampling results.

The CPS has no employer identifier. Entry destination conditions on becoming
employed and occupational outflow need not be an employer change. Therefore
BCC's new-employer-match hiring margin and the CPS stock coefficient cannot be
calibrated from these outputs without additional assumptions; BCC-04 remains
not identified.

Model failures recorded: **{len(failures)}**. They are retained in
`MODEL_FAILURES.json`; no alternative model was selected in response.
""",
        encoding="utf-8",
    )

    outputs = [args.output_dir / filename for filename in output_files]
    outputs.extend([args.output_dir / "MODEL_FAILURES.json", feasibility])
    receipt = {
        "record": "YAX R3 corrected CPS flows and worker outcomes",
        "analysis_status": LABEL, "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "prespec_commit": PRESPEC_COMMIT, "execution_head": git("rev-parse", "HEAD"),
        "input_hashes": input_hashes, "execution_script_sha256": sha256(pathlib.Path(__file__)),
        "corrected_reconstruction": reconstruction, "mapping": map_receipt,
        "link_repeat_and_aging": repeat_receipt,
        "official_weights": {"adjacent_month": "origin LNKFW1MWT", "twelve_month": "origin LNKFW1YWT", "weekly_earnings": "EARNWT"},
        "draw_contract": {
            "draws": BOOTSTRAP_DRAWS, "seed": BOOTSTRAP_SEED,
            "canonical_occupation_order_sha256": hashlib.sha256("\n".join(canonical_codes).encode()).hexdigest(),
            "common_occupation_signs_sha256": hashlib.sha256(signs.tobytes()).hexdigest(),
            "common_lineage_signs_sha256": hashlib.sha256(component_signs.tobytes()).hexdigest(),
        },
        "models_completed": len(results), "models_failed": len(failures),
        "no_person_or_household_identifiers_written": True,
        "stock_flow_calibration_identified": False,
        "output_hashes": {path.name: sha256(path) for path in outputs},
    }
    write_json(args.output_dir / "EXECUTION_RECEIPT.json", receipt)
    print(json.dumps({"models_completed": len(results), "models_failed": len(failures)}, indent=2))
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--microdata", required=True, type=pathlib.Path)
    parser.add_argument("--repair-microdata", required=True, type=pathlib.Path)
    parser.add_argument("--weight-patch", required=True, type=pathlib.Path)
    parser.add_argument("--membership", required=True, type=pathlib.Path)
    parser.add_argument("--bridge", required=True, type=pathlib.Path)
    parser.add_argument("--analysis-spec", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent / "ANALYSIS_SPEC_BEFORE_RESULTS.md")
    parser.add_argument("--output-dir", required=True, type=pathlib.Path)
    args = parser.parse_args()
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
