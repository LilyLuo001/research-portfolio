#!/usr/bin/env python3
"""Deterministic, outcome-blind P1 population/support design build.

This script reads only named local metadata columns. It never reads raw EPS,
forecast, ownership/dose, liquidity, price, return, quote-body, or POST response
values. CSV headers are validated before pandas parses any body rows.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path("/Users/lilyluo/P1_Fixed_125USD_Pilot_Order_extracted/p1_fixed_pilot")
MD = ROOT / "missing_data_round_20260914"
GATE = ROOT / "gate1_20260915"
PLAN_DIR = ROOT / "pilot_research_plan_20260915"
OUT = ROOT / "pilot_design_build_20260915" / "design"
CONTRACT = Path(
    "/Users/lilyluo/research-portfolio-p1-feasibility-20260913/p1/"
    "feasibility_adjudication/20260913/reconciliation/"
    "estimation_contract.reconciled.PROPOSED.yaml"
)
BUILD_DATE = "2026-09-15"
CONTRACT_SHA256 = "00af7d39fd51e9c3c6a9051036f26a68b337f2132848368a729ff8a70d32663f"


INPUTS = {
    "accepted_contract": {
        "path": CONTRACT,
        "expected": CONTRACT_SHA256,
        "role": "accepted proposed estimation contract; preserved, not reopened",
        "usecols": [],
    },
    "research_plan": {
        "path": PLAN_DIR / "PILOT_RESEARCH_PLAN.md",
        "expected": "4d83c93dd68554786d2e22ef6f6bd5f2089f7e9f226096b4d1cd7a7f4d501ab4",
        "role": "P1 design instructions",
        "usecols": [],
    },
    "gap_matrix": {
        "path": PLAN_DIR / "DATA_GAP_MATRIX.md",
        "expected": "f14aa922b56a64bab556822d80f1d886a44290bdc0d45a1adc57374f5a43a9fe",
        "role": "outcome-blind data gap inventory",
        "usecols": [],
    },
    "v1_population": {
        "path": MD / "EARNINGS_METADATA_ELIGIBILITY.csv",
        "expected": "cc7a7f32913f5a0ef72eab30bb69ea714a2c2d882d20b248ebf39ed42b10cf5b",
        "role": "v1 2,592 tail population and 8 PRE/4 POST flag",
        "usecols": ["wave_id", "permno", "provisional_tier", "has_8pre_4post"],
    },
    "v2_population": {
        "path": MD / "supported_roster/ALL_CANDIDATE_EVENT_SUPPORT.csv",
        "expected": "31cdfdba68b2c65f6fa25153b8f06403839cf0de5edbc64f5042d8ac342c3cc6",
        "role": "separate v2 4,186 roster and 8 PRE/4 POST flag",
        "usecols": ["wave_id", "permno", "has_8pre_4post"],
    },
    "v2_tier_projection": {
        "path": MD / "PREANNOUNCEMENT_EXPOSURE_PROVISIONAL_TIERS.csv",
        "expected": "9f31091f3b7ea9ecbaba39c8c43b64e76713227e361552c9ca6bc52a895fa35e",
        "role": "tier labels only for v2 keys; no exposure/dose/liquidity columns",
        "usecols": ["wave_id", "permno", "provisional_tier"],
    },
    "analyst_candidate_screen": {
        "path": MD / "full_pool_analyst_coverage/candidate_analyst_coverage.csv",
        "expected": "856f3eb24343b29c6a4a32887b4df30e94774b41931fa4f4219bde5d5c257954",
        "role": "candidate-level all-12-events min-2 analyst metadata screen",
        "usecols": ["wave_id", "permno", "provisional_tier", "all_12_events_min2"],
    },
    "overlap_clean_pool": {
        "path": MD / "clean_acquisition/full_supported_pool_with_overlap_flag.csv",
        "expected": "be9b710a2a2ab3ccf1e84534d6fb96e1885c3522119116d2a29b61c0fa930ba4",
        "role": "v1 8/4 pool with proposed overlap-clean flag",
        "usecols": ["wave_id", "permno", "provisional_tier", "proposed_overlap_clean"],
    },
    "clean_analyst_intersection": {
        "path": MD / "analysis_ready_acquisition/full_support_overlap_analyst_intersection.csv",
        "expected": "60c8ef59a7dfce9ac9444d7f7f775f46806ae12309bd3868129595a0d43f472a",
        "role": "v1 8/4 pool with separate overlap, analyst, and intersection flags",
        "usecols": [
            "wave_id", "permno", "provisional_tier", "proposed_overlap_clean",
            "all_12_events_min2", "clean_and_analyst12",
        ],
    },
    "acquisition_union": {
        "path": MD / "analysis_ready_acquisition/PILOT_STOCKS_ACQUISITION_UNION_V2.csv",
        "expected": "55bdd43af41fc8421936d327395f6274400e7cc2ef34d0eaddef2112e9fc08d7",
        "role": "71-unit acquisition work roster, not final sample",
        "usecols": [
            "wave_id", "permno", "tier", "roster_source", "purpose",
            "final_analysis_eligibility",
        ],
    },
    "selected_clean_analyst_core": {
        "path": MD / "analysis_ready_acquisition/PILOT_STOCKS_CLEAN_ANALYST_MAX15.csv",
        "expected": "5935c912009f9430fde43a9f367ea08e9da988e522705cf996e615a5d36c6a99",
        "role": "15-unit capped clean+all12 acquisition core, keys and labels only",
        "usecols": ["wave_id", "permno", "tier", "roster_source", "purpose", "final_analysis_eligibility"],
    },
    "event_metadata": {
        "path": MD / "union_v2_earnings_inputs/selected_event_metadata.csv",
        "expected": "3d644fb4210accf8ac5fde5a4f8509bd6b31ea26f2caeffe36496cae0591f5c5",
        "role": "852 event associations; identity, dates, regime, tier, analyst eligibility only",
        "usecols": [
            "association_id", "wave_id", "permno", "tier", "sample_period",
            "announcement_date", "sue_analyst_min2_coverage",
        ],
    },
    "calendar_metadata": {
        "path": MD / "union_v2_event_calendar_actions/event_calendar_and_action_flags.csv",
        "expected": "e075616e43700f815abfc55745801364f235a4de09ad1c373997f9f0d4a6c8cd",
        "role": "calendar basis/status projection only; no factors/actions/returns",
        "usecols": [
            "association_id", "announcement_date", "announcement_date_is_observed_session",
            "calendar_basis",
        ],
    },
    "readiness_receipt": {
        "path": GATE / "readiness_receipt.json",
        "expected": "8fb35e11bb9fac3cd2ab6e47c525e18f543062b16dbb4bf6ffa566390fe97a91",
        "role": "provisional readiness controls; not Gate 1 PASS",
        "usecols": [],
    },
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_header(path: Path, usecols: list[str]) -> None:
    if not usecols:
        return
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        header = next(csv.reader(handle))
    missing = sorted(set(usecols) - set(header))
    if missing:
        raise RuntimeError(f"Missing required columns in {path}: {missing}")


def read_csv(key: str) -> pd.DataFrame:
    spec = INPUTS[key]
    validate_header(spec["path"], spec["usecols"])
    return pd.read_csv(spec["path"], usecols=spec["usecols"])


def write_csv(df: pd.DataFrame, name: str) -> None:
    df.to_csv(OUT / name, index=False, lineterminator="\n")


def bool_col(series: pd.Series, label: str) -> pd.Series:
    if series.dtype == bool:
        return series
    mapped = series.astype(str).str.strip().str.lower().map({"true": True, "false": False})
    if mapped.isna().any():
        raise RuntimeError(f"Non-boolean values in {label}")
    return mapped


def keyed_values(df: pd.DataFrame, value_col: str) -> dict[tuple[str, int], object]:
    """Return an exact stock-wave keyed mapping after rejecting duplicate keys."""
    if df.duplicated(["wave_id", "permno"]).any():
        raise RuntimeError(f"Duplicate stock-wave keys in projection for {value_col}")
    return {
        (str(row.wave_id), int(row.permno)): getattr(row, value_col)
        for row in df.itertuples(index=False)
    }


def component_summary(edges: pd.DataFrame, specification: str, interpretation: str) -> dict[str, object]:
    """Summarize event-node components; this is topology, never ESS or inference."""
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for row in edges.itertuples(index=False):
        union(row.source_node_id, row.target_node_id)
    event_nodes = sorted(n for n in parent if n.startswith("EVENT::"))
    counts: dict[str, int] = {}
    for node in event_nodes:
        root = find(node)
        counts[root] = counts.get(root, 0) + 1
    sizes = sorted(counts.values())
    return {
        "component_specification": specification,
        "event_association_denominator": len(event_nodes),
        "connected_components_among_events": len(sizes),
        "largest_component_event_associations": max(sizes) if sizes else 0,
        "median_component_event_associations": float(pd.Series(sizes).median()) if sizes else 0,
        "interpretation": interpretation,
    }


def stage_rows(
    df: pd.DataFrame,
    universe_df: pd.DataFrame,
    population_version: str,
    stage_id: str,
    stage_label: str,
    prior_stage_id: str,
    prior_df: pd.DataFrame | None,
    transition_basis: str,
) -> pd.DataFrame:
    levels = pd.MultiIndex.from_product(
        [sorted(universe_df["wave_id"].unique()), sorted(universe_df["tier"].unique())],
        names=["wave_id", "tier"],
    )
    now = df.groupby(["wave_id", "tier"]).size().reindex(levels, fill_value=0)
    if prior_df is None:
        prior = pd.Series(pd.NA, index=levels, dtype="Int64")
    else:
        prior = prior_df.groupby(["wave_id", "tier"]).size().reindex(levels, fill_value=0).astype("Int64")
    out = now.rename("stage_count").reset_index()
    out["population_version"] = population_version
    out["stage_id"] = stage_id
    out["stage_label"] = stage_label
    out["prior_stage_id"] = prior_stage_id
    out["prior_stage_count_same_wave_tier"] = prior.array
    out["retention_rate_same_wave_tier"] = [
        (n / p if pd.notna(p) and p > 0 else pd.NA)
        for n, p in zip(out["stage_count"], out["prior_stage_count_same_wave_tier"])
    ]
    out["stage_total_all_waves_tiers"] = int(len(df))
    out["transition_basis"] = transition_basis
    return out[
        ["population_version", "stage_id", "stage_label", "wave_id", "tier",
         "stage_count", "stage_total_all_waves_tiers", "prior_stage_id",
         "prior_stage_count_same_wave_tier", "retention_rate_same_wave_tier",
         "transition_basis"]
    ]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    manifest_rows = []
    for key, spec in INPUTS.items():
        actual = sha256(spec["path"])
        if actual != spec["expected"]:
            raise RuntimeError(f"Input hash mismatch for {key}: {actual} != {spec['expected']}")
        validate_header(spec["path"], spec["usecols"])
        manifest_rows.append({
            "input_id": key,
            "path": str(spec["path"]),
            "sha256": actual,
            "expected_sha256": spec["expected"],
            "hash_match": True,
            "bytes": spec["path"].stat().st_size,
            "role": spec["role"],
            "loaded_columns": ";".join(spec["usecols"]) if spec["usecols"] else "NONE_BODY_NOT_PARSED",
        })
    manifest = pd.DataFrame(manifest_rows).sort_values("input_id")
    write_csv(manifest, "source_manifest.csv")

    tiers_universe = read_csv("v2_tier_projection").rename(columns={"provisional_tier": "tier"})
    tiers_universe["tier"] = tiers_universe["tier"].str.upper()
    if len(tiers_universe) != 4191 or tiers_universe.duplicated(["wave_id", "permno"]).any():
        raise RuntimeError("Source tier universe count/key uniqueness control failed")
    source_tail = tiers_universe[tiers_universe["tier"].isin(["HIGH", "LOW"])].copy()
    if len(source_tail) != 2794:
        raise RuntimeError("Source H/L tail universe count control failed")

    v1 = read_csv("v1_population").rename(columns={"provisional_tier": "tier"})
    v1["tier"] = v1["tier"].str.upper()
    v1["has_8pre_4post"] = bool_col(v1["has_8pre_4post"], "v1 has_8pre_4post")
    if v1.duplicated(["wave_id", "permno"]).any() or len(v1) != 2592:
        raise RuntimeError("Unexpected v1 key duplication or count")
    source_tail_keys = set(keyed_values(source_tail, "tier"))
    v1_keys = set(keyed_values(v1, "tier"))
    if not v1_keys < source_tail_keys:
        raise RuntimeError("v1 represented snapshot is not a strict subset of the 2,794 H/L tail")
    v1_support = v1[v1["has_8pre_4post"]].copy()

    overlap = read_csv("overlap_clean_pool").rename(columns={"provisional_tier": "tier"})
    overlap["tier"] = overlap["tier"].str.upper()
    overlap["proposed_overlap_clean"] = bool_col(overlap["proposed_overlap_clean"], "overlap clean")
    overlap_clean = overlap[overlap["proposed_overlap_clean"]].copy()

    inter = read_csv("clean_analyst_intersection").rename(columns={"provisional_tier": "tier"})
    inter["tier"] = inter["tier"].str.upper()
    for col in ["proposed_overlap_clean", "all_12_events_min2", "clean_and_analyst12"]:
        inter[col] = bool_col(inter[col], col)
    all12_in_8_4 = inter[inter["all_12_events_min2"]].copy()
    clean_all12 = inter[inter["clean_and_analyst12"]].copy()

    coverage = read_csv("analyst_candidate_screen")
    coverage["all_12_events_min2"] = bool_col(coverage["all_12_events_min2"], "candidate all12")
    if len(coverage) != 2592 or int(coverage["all_12_events_min2"].sum()) != 895:
        raise RuntimeError("Candidate analyst coverage control failed")

    v1_support_keys = set(keyed_values(v1_support, "has_8pre_4post"))
    overlap_keys = set(keyed_values(overlap, "proposed_overlap_clean"))
    inter_keys = set(keyed_values(inter, "all_12_events_min2"))
    if not (v1_support_keys == overlap_keys == inter_keys):
        raise RuntimeError("v1 support, overlap, and intersection key sets differ")
    coverage_values = keyed_values(coverage, "all_12_events_min2")
    if set(coverage_values) != set(keyed_values(v1, "has_8pre_4post")):
        raise RuntimeError("Candidate analyst coverage keys do not exactly match v1 population")
    inter_values = keyed_values(inter, "all_12_events_min2")
    if any(bool(inter_values[key]) != bool(coverage_values[key]) for key in inter_keys):
        raise RuntimeError("Analyst flags in intersection differ from candidate screen")
    expected_intersection = inter["proposed_overlap_clean"] & inter["all_12_events_min2"]
    if not inter["clean_and_analyst12"].equals(expected_intersection):
        raise RuntimeError("clean_and_analyst12 is not the exact conjunction")

    v2 = read_csv("v2_population")
    v2["has_8pre_4post"] = bool_col(v2["has_8pre_4post"], "v2 has_8pre_4post")
    v2_keys_before_tier = set(zip(v2["wave_id"].astype(str), v2["permno"].astype(int)))
    universe_keys = set(keyed_values(tiers_universe, "tier"))
    if not v2_keys_before_tier < universe_keys:
        raise RuntimeError("v2 represented snapshot is not a strict subset of the 4,191 source universe")
    v2 = v2.merge(tiers_universe, on=["wave_id", "permno"], how="left", validate="one_to_one")
    if v2["tier"].isna().any() or len(v2) != 4186:
        raise RuntimeError("v2 tier projection did not map exactly")
    v2["tier"] = v2["tier"].str.upper()
    v2_support = v2[v2["has_8pre_4post"]].copy()

    acq = read_csv("acquisition_union")
    acq["tier"] = acq["tier"].str.upper()
    if len(acq) != 71 or acq.duplicated(["wave_id", "permno"]).any():
        raise RuntimeError("Acquisition roster control failed")
    if set(acq["final_analysis_eligibility"]) != {"NOT_CERTIFIED"}:
        raise RuntimeError("Acquisition roster unexpectedly claims certified eligibility")
    selected_core = read_csv("selected_clean_analyst_core")
    selected_core["tier"] = selected_core["tier"].str.upper()
    if selected_core.duplicated(["wave_id", "permno"]).any():
        raise RuntimeError("Selected clean analyst core has duplicate keys")

    controls = {
        "source_universe": 4191, "source_tail": 2794,
        "v1_snapshot_represented": 2592, "v1_representation_unknown_absent": 202,
        "v1_support": 2088, "overlap_clean": 508,
        "all12_in_8_4": 895, "clean_all12": 182, "selected_core": 15,
        "acquisition": 71, "v2_snapshot_represented": 4186,
        "v2_representation_unknown_absent": 5, "v2_support": 3246,
    }
    v1_absent_keys = source_tail_keys - v1_keys
    v2_absent_keys = universe_keys - v2_keys_before_tier
    observed = {
        "source_universe": len(tiers_universe), "source_tail": len(source_tail),
        "v1_snapshot_represented": len(v1),
        "v1_representation_unknown_absent": len(v1_absent_keys),
        "v1_support": len(v1_support), "overlap_clean": len(overlap_clean),
        "all12_in_8_4": len(all12_in_8_4), "clean_all12": len(clean_all12),
        "selected_core": len(selected_core), "acquisition": len(acq),
        "v2_snapshot_represented": len(v2),
        "v2_representation_unknown_absent": len(v2_absent_keys),
        "v2_support": len(v2_support),
    }
    if observed != controls:
        raise RuntimeError(f"Attrition controls failed: {observed}")

    attrition = pd.concat([
        stage_rows(tiers_universe, tiers_universe, "SOURCE_TIER_UNIVERSE_4191", "SRC_00", "source tier universe", "", None, "source universe; representation, not final population"),
        stage_rows(source_tail, source_tail, "SOURCE_HL_TAIL_2794", "SRC_10", "source high/low tail universe", "SRC_00", tiers_universe, "tier restriction only"),
        stage_rows(v1, source_tail, "V1_REPRESENTED_SNAPSHOT_2592", "V1_00", "represented in v1 eligibility snapshot", "SRC_10", source_tail, "representation step; 202 absent keys have unknown retrieval/coverage status"),
        stage_rows(v1_support, source_tail, "V1_REPRESENTED_SNAPSHOT_2592", "V1_10", "8 PRE/4 POST metadata support among represented keys", "V1_00", v1, "sequential attrition within represented snapshot"),
        stage_rows(overlap_clean, source_tail, "V1_REPRESENTED_SNAPSHOT_2592", "V1_20", "proposed overlap-clean within represented 8/4", "V1_10", v1_support, "sequential attrition; proposed rule"),
        stage_rows(all12_in_8_4, source_tail, "V1_REPRESENTED_SNAPSHOT_2592", "V1_21", "all 12 events min-2 analysts within represented 8/4", "V1_10", v1_support, "parallel screen from V1_10"),
        stage_rows(clean_all12, source_tail, "V1_REPRESENTED_SNAPSHOT_2592", "V1_30", "overlap-clean and all-12 min-2", "V1_20", overlap_clean, "intersection; proposed rule"),
        stage_rows(selected_core, v1, "ACQUISITION_WORK_ROSTER", "ACQ_10", "capped clean+all12 acquisition core", "V1_30", clean_all12, "selection cap, not population ceiling"),
        stage_rows(acq, v1, "ACQUISITION_WORK_ROSTER", "ACQ_20", "71-unit acquisition union", "", None, "union expansion; not an attrition step or final sample"),
        stage_rows(v2, tiers_universe, "V2_REPRESENTED_SNAPSHOT_4186", "V2_00", "represented in separate v2 snapshot", "SRC_00", tiers_universe, "representation step; 5 absent keys have unknown retrieval/coverage status"),
        stage_rows(v2_support, tiers_universe, "V2_REPRESENTED_SNAPSHOT_4186", "V2_10", "8 PRE/4 POST metadata support among represented keys", "V2_00", v2, "sequential attrition within V2 only"),
    ], ignore_index=True)
    attrition = attrition.sort_values(["population_version", "stage_id", "wave_id", "tier"])
    write_csv(attrition, "sequential_attrition_by_wave_tier.csv")

    summary = pd.DataFrame([
        {"population_version": "SOURCE_TIER_UNIVERSE_4191", "stage_id": "SRC_00", "count": 4191, "denominator": pd.NA, "rate": pd.NA, "interpretation": "source tier universe; not final population"},
        {"population_version": "SOURCE_HL_TAIL_2794", "stage_id": "SRC_10", "count": 2794, "denominator": 4191, "rate": 2794/4191, "interpretation": "high/low tail restriction"},
        {"population_version": "V1_REPRESENTED_SNAPSHOT_2592", "stage_id": "V1_00", "count": 2592, "denominator": 2794, "rate": 2592/2794, "interpretation": "represented v1 keys; 202 absent keys have unknown retrieval/coverage status"},
        {"population_version": "V1_REPRESENTED_SNAPSHOT_2592", "stage_id": "V1_10", "count": 2088, "denominator": 2592, "rate": 2088/2592, "interpretation": "v1 8 PRE/4 POST pool among represented keys"},
        {"population_version": "V1_REPRESENTED_SNAPSHOT_2592", "stage_id": "V1_20", "count": 508, "denominator": 2088, "rate": 508/2088, "interpretation": "proposed overlap-clean branch"},
        {"population_version": "V1_REPRESENTED_SNAPSHOT_2592", "stage_id": "V1_21", "count": 895, "denominator": 2088, "rate": 895/2088, "interpretation": "all-12 min-2 branch"},
        {"population_version": "V1_REPRESENTED_SNAPSHOT_2592", "stage_id": "V1_30", "count": 182, "denominator": 508, "rate": 182/508, "interpretation": "overlap-clean plus all-12 min-2 intersection"},
        {"population_version": "ACQUISITION_WORK_ROSTER", "stage_id": "ACQ_10", "count": 15, "denominator": 182, "rate": 15/182, "interpretation": "capped core; not full pool ceiling"},
        {"population_version": "ACQUISITION_WORK_ROSTER", "stage_id": "ACQ_20", "count": 71, "denominator": pd.NA, "rate": pd.NA, "interpretation": "expanded acquisition union; provisional, not final sample"},
        {"population_version": "V2_REPRESENTED_SNAPSHOT_4186", "stage_id": "V2_00", "count": 4186, "denominator": 4191, "rate": 4186/4191, "interpretation": "separate represented v2 keys; 5 absent keys have unknown retrieval/coverage status"},
        {"population_version": "V2_REPRESENTED_SNAPSHOT_4186", "stage_id": "V2_10", "count": 3246, "denominator": 4186, "rate": 3246/4186, "interpretation": "v2 8 PRE/4 POST pool among represented keys; not pooled with v1"},
    ])
    write_csv(summary, "attrition_summary.csv")

    gap_frames = []
    for snapshot, base, represented in [
        ("V1_REPRESENTED_SNAPSHOT_2592", source_tail, v1[["wave_id", "permno"]]),
        ("V2_REPRESENTED_SNAPSHOT_4186", tiers_universe, v2[["wave_id", "permno"]]),
    ]:
        gap = base.merge(
            represented.assign(snapshot_represented=True),
            on=["wave_id", "permno"], how="left", validate="one_to_one",
        )
        gap = gap[gap["snapshot_represented"].isna()]
        grouped = gap.groupby(["wave_id", "tier"], as_index=False).size().rename(columns={"size": "absent_key_count"})
        grouped["snapshot"] = snapshot
        grouped["status"] = "UNKNOWN_RETRIEVAL_OR_COVERAGE_REPRESENTATION"
        grouped["not_interpretable_as"] = "NO_EARNINGS_OR_INELIGIBLE_FINAL_POPULATION"
        gap_frames.append(grouped)
    representation_gaps = pd.concat(gap_frames, ignore_index=True).sort_values(["snapshot", "wave_id", "tier"])
    write_csv(representation_gaps, "snapshot_representation_gaps_by_wave_tier.csv")

    events = read_csv("event_metadata")
    events["tier"] = events["tier"].str.upper()
    events["sue_analyst_min2_coverage"] = bool_col(
        events["sue_analyst_min2_coverage"], "event analyst eligibility"
    )
    if len(events) != 852 or events["association_id"].duplicated().any():
        raise RuntimeError("Event metadata identity/count control failed")
    if int(events["sue_analyst_min2_coverage"].sum()) != 659:
        raise RuntimeError("Event analyst eligibility control failed")
    event_out = events[[
        "association_id", "wave_id", "permno", "tier", "sample_period",
        "announcement_date", "sue_analyst_min2_coverage",
    ]].rename(columns={"sue_analyst_min2_coverage": "analyst_min2_metadata_eligible"})
    event_out["eligibility_scope"] = "metadata_count_only_not_SUE_certification"
    event_out = event_out.sort_values(["wave_id", "tier", "sample_period", "permno", "announcement_date"])
    write_csv(event_out, "event_level_analyst_eligibility.csv")

    event_summary = (
        event_out.groupby(["wave_id", "tier", "sample_period"], as_index=False)
        .agg(
            association_denominator=("association_id", "size"),
            analyst_min2_eligible=("analyst_min2_metadata_eligible", "sum"),
            unique_stocks=("permno", "nunique"),
            unique_release_dates=("announcement_date", "nunique"),
        )
    )
    event_summary["analyst_min2_eligibility_rate"] = (
        event_summary["analyst_min2_eligible"] / event_summary["association_denominator"]
    )
    event_summary["status"] = "PROVISIONAL_METADATA_DIAGNOSTIC_NOT_FINAL_SAMPLE"
    write_csv(event_summary, "event_analyst_eligibility_by_wave_tier_regime.csv")

    calendar = read_csv("calendar_metadata")
    if len(calendar) != 852 or calendar["association_id"].duplicated().any():
        raise RuntimeError("Calendar metadata identity/count control failed")
    events = events.merge(
        calendar, on=["association_id", "announcement_date"], how="left", validate="one_to_one"
    )
    if events["calendar_basis"].isna().any():
        raise RuntimeError("Calendar metadata failed exact association join")
    release_dt = pd.to_datetime(events["announcement_date"], format="%Y-%m-%d", errors="raise")
    events["calendar_quarter"] = release_dt.dt.to_period("Q").astype(str).str.replace("Q", "Q", regex=False)

    acquired_keys = acq[["wave_id", "permno", "tier"]].drop_duplicates()
    matrix_parts = []
    common_matrix_parts = []
    excluded_quarter_rows = []
    for (wave, regime), group in events.groupby(["wave_id", "sample_period"]):
        cells = sorted(group["calendar_quarter"].unique())
        tier_cells = {
            tier: set(tier_group["calendar_quarter"].unique())
            for tier, tier_group in group.groupby("tier")
        }
        common_cells = sorted(tier_cells.get("HIGH", set()) & tier_cells.get("LOW", set()))
        for cell in sorted(set(cells) - set(common_cells)):
            observed_tiers = sorted(tier for tier, values in tier_cells.items() if cell in values)
            excluded_quarter_rows.append({
                "wave_id": wave,
                "sample_period": regime,
                "calendar_quarter": cell,
                "observed_tiers": ";".join(observed_tiers),
                "exclusion_reason": "NOT_OBSERVED_IN_BOTH_HIGH_AND_LOW",
                "contract_cell_set_status": "EXCLUDED_BEFORE_INDUSTRY_RESTRICTION",
            })
        stocks = acquired_keys[acquired_keys["wave_id"] == wave]
        counts = group.groupby(["permno", "calendar_quarter"]).size()
        for row in stocks.itertuples(index=False):
            for cell in cells:
                n = int(counts.get((row.permno, cell), 0))
                matrix_parts.append({
                    "wave_id": wave,
                    "tier": row.tier,
                    "sample_period": regime,
                    "permno": int(row.permno),
                    "calendar_quarter": cell,
                    "observed_event_count": n,
                    "stock_cell_observed": n > 0,
                    "support_interpretation": "necessary_literal_calendar_support_only",
                    "industry_control_status": "UNKNOWN_INDUSTRY_COLUMN_ABSENT",
                })
                if cell in common_cells:
                    common_matrix_parts.append({
                        "wave_id": wave,
                        "tier": row.tier,
                        "sample_period": regime,
                        "permno": int(row.permno),
                        "calendar_quarter": cell,
                        "observed_event_count": n,
                        "stock_cell_observed": n > 0,
                        "support_interpretation": "necessary_common_HL_calendar_support_only",
                        "industry_control_status": "UNKNOWN_INDUSTRY_COLUMN_ABSENT",
                    })
    all_quarter_matrix = pd.DataFrame(matrix_parts).sort_values(
        ["wave_id", "sample_period", "calendar_quarter", "tier", "permno"]
    )
    matrix = pd.DataFrame(common_matrix_parts).sort_values(
        ["wave_id", "sample_period", "calendar_quarter", "tier", "permno"]
    )
    excluded_quarters = pd.DataFrame(excluded_quarter_rows, columns=[
        "wave_id", "sample_period", "calendar_quarter", "observed_tiers",
        "exclusion_reason", "contract_cell_set_status",
    ]).sort_values(["wave_id", "sample_period", "calendar_quarter"])
    write_csv(all_quarter_matrix, "all_quarter_structural_calendar_support_matrix.csv")
    write_csv(matrix, "structural_calendar_support_matrix.csv")
    write_csv(excluded_quarters, "excluded_one_tier_quarters.csv")

    cal_summary = (
        matrix.groupby(["wave_id", "sample_period", "calendar_quarter", "tier"], as_index=False)
        .agg(
            stock_denominator=("permno", "nunique"),
            stocks_with_observation=("stock_cell_observed", "sum"),
            event_rows=("observed_event_count", "sum"),
        )
    )
    cal_summary["stocks_missing_observation"] = (
        cal_summary["stock_denominator"] - cal_summary["stocks_with_observation"]
    )
    cal_summary["all_positive_weight_stocks_observed_if_all_acquired_weighted"] = (
        cal_summary["stocks_missing_observation"] == 0
    )
    cal_summary["scope"] = "calendar-quarter necessary condition; industry dimension unavailable"
    write_csv(cal_summary, "structural_calendar_support_summary.csv")

    nodes = []
    edges = []
    for wave in sorted(events["wave_id"].unique()):
        nodes.append({"node_id": f"WAVE::{wave}", "node_type": "wave", "value": wave, "status": "OBSERVED"})
    for permno in sorted(events["permno"].unique()):
        nodes.append({"node_id": f"STOCK::{int(permno)}", "node_type": "stock", "value": str(int(permno)), "status": "OBSERVED"})
    for date in sorted(events["announcement_date"].unique()):
        nodes.append({"node_id": f"RELEASE_DATE::{date}", "node_type": "release_date", "value": date, "status": "OBSERVED_DATE_METADATA"})
    for quarter in sorted(events["calendar_quarter"].unique()):
        nodes.append({"node_id": f"CALQ::{quarter}", "node_type": "calendar_quarter", "value": quarter, "status": "DERIVED_FROM_RELEASE_DATE"})
    nodes.append({
        "node_id": "SPONSOR::UNKNOWN_NOT_OBSERVED", "node_type": "sponsor",
        "value": "UNKNOWN", "status": "NO_EDGES_CONSTRUCTED_DO_NOT_INFER_FROM_WAVE",
    })
    for row in events.sort_values("association_id").itertuples(index=False):
        event_node = f"EVENT::{row.association_id}"
        plus1_node = f"PLUS1D::{row.association_id}::UNKNOWN"
        nodes.append({"node_id": event_node, "node_type": "event_association", "value": row.association_id, "status": "OBSERVED_DATE_KEY_NOT_CERTIFIED_ECONOMIC_EVENT"})
        nodes.append({"node_id": plus1_node, "node_type": "plus1d_response_date", "value": "UNKNOWN", "status": "CALENDAR_APPROVAL_NOT_OBSERVED"})
        edges.extend([
            {"source_node_id": event_node, "target_node_id": f"WAVE::{row.wave_id}", "edge_type": "belongs_to_wave", "status": "OBSERVED", "component_use": "WAVE_PROXY_ONLY"},
            {"source_node_id": event_node, "target_node_id": f"STOCK::{int(row.permno)}", "edge_type": "belongs_to_stock", "status": "OBSERVED", "component_use": "BASE_PARTIAL"},
            {"source_node_id": event_node, "target_node_id": f"RELEASE_DATE::{row.announcement_date}", "edge_type": "shares_release_date", "status": "OBSERVED_DATE_METADATA", "component_use": "BASE_PARTIAL"},
            {"source_node_id": event_node, "target_node_id": f"CALQ::{row.calendar_quarter}", "edge_type": "release_calendar_quarter", "status": "DERIVED_FROM_RELEASE_DATE", "component_use": "RELATION_ONLY_EXCLUDED"},
            {"source_node_id": event_node, "target_node_id": plus1_node, "edge_type": "requires_plus1d_response_date", "status": "UNKNOWN_CALENDAR_APPROVAL_NOT_OBSERVED", "component_use": "UNKNOWN_EXCLUDED"},
        ])
    nodes_df = pd.DataFrame(nodes).drop_duplicates("node_id").sort_values(["node_type", "node_id"])
    edges_df = pd.DataFrame(edges).sort_values(["edge_type", "source_node_id", "target_node_id"])
    write_csv(nodes_df, "dependency_nodes.csv")
    write_csv(edges_df, "dependency_edges.csv")
    base_component_edges = edges_df[edges_df["component_use"] == "BASE_PARTIAL"]
    wave_proxy_edges = edges_df[edges_df["component_use"].isin(["BASE_PARTIAL", "WAVE_PROXY_ONLY"])]
    component_counts = pd.DataFrame([
        component_summary(
            base_component_edges,
            "EVENT_STOCK_PLUS_EVENT_RELEASE_DATE",
            "partial observed topology only; excludes wave, quarter, +1d, and sponsor; not ESS",
        ),
        component_summary(
            wave_proxy_edges,
            "EVENT_STOCK_PLUS_EVENT_RELEASE_DATE_PLUS_WAVE_PROXY",
            "wave-linked proxy topology only; sponsor remains unknown; not valid inference or ESS",
        ),
    ])
    write_csv(component_counts, "dependency_component_summary.csv")

    missing = pd.DataFrame([
        ["v1_snapshot_representation_status", "202_SOURCE_TAIL_KEYS_ABSENT", "population denominator and attrition interpretation", "resolve retrieval/coverage representation for exact absent keys", "UNKNOWN; do not label no earnings"],
        ["v2_snapshot_representation_status", "5_SOURCE_UNIVERSE_KEYS_ABSENT", "population denominator and attrition interpretation", "resolve retrieval/coverage representation for exact absent keys", "UNKNOWN; do not label no earnings"],
        ["sponsor_id", "UNKNOWN", "sponsor clustering/dependence and leave-one-out", "signed package/sponsor provenance", "NO; do not infer sponsor from wave"],
        ["industry_code_at_event", "ABSENT_FROM_ALLOWED_EVENT_PROJECTION", "industry-by-calendar-quarter-by-wave intercepts and SUE slopes", "approved historical industry classification", "NO"],
        ["calendar_approval_status", "NOT_OBSERVED", "+1d response-date graph and session-qualified endpoint dates", "PI-approved calendar/version and endpoint rule", "NO; existing CRSP calendar basis is not approval"],
        ["plus1d_response_date", "UNKNOWN", "+1d shared-date dependence", "derive only after calendar approval", "NO"],
        ["release_uncertainty_lower_upper", "UNKNOWN", "RTH-60 and short-horizon session classification", "approved release-time uncertainty interval", "NO"],
        ["certified_economic_event_id", "UNKNOWN_DATE_KEYS_ONLY", "event reuse and covariance grouping", "certified duplicate/revision resolution", "NO"],
        ["signed_sue", "NOT_COMPUTED", "numeric design rank, slope information and effects", "licensed, contract-compatible SUE build", "NO; symbolic/structural outputs only"],
        ["endpoint_common_mask", "NOT_ASSESSED", "six-horizon literal response support", "approved endpoint parser and common-mask metadata", "NO"],
        ["response_values", "INTENTIONALLY_NOT_READ", "effect estimation", "separate POST unseal authority", "NO; outside this build"],
    ], columns=["required_column_or_input", "current_status", "blocked_design_element", "minimal_action", "inference_policy"])
    write_csv(missing, "actionable_missing_columns.csv")

    counts_clean = clean_all12.groupby(["wave_id", "tier"]).size().to_dict()
    total_stock_cells = len(matrix)
    missing_stock_cells = int((~matrix["stock_cell_observed"]).sum())
    all_quarter_cells = len(all_quarter_matrix)
    all_quarter_missing = int((~all_quarter_matrix["stock_cell_observed"]).sum())
    excluded_quarter_count = len(excluded_quarters)
    report = f"""# P1 local outcome-blind design build

Build date: {BUILD_DATE}. This is a bounded P1 metadata diagnostic. It is not a new plan, Gate 1 PASS, approval of a final sample, an effect estimate, or an ESS calculation. The accepted proposed contract remains SHA256 `{CONTRACT_SHA256}`.

## Measured attrition

The source tier universe has 4,191 stock-wave keys: 1,396 high, 1,398 low, and 1,397 middle. The high/low tail therefore contains 2,794 keys. The v1 eligibility snapshot represents 2,592 of those tail keys; 202 are absent before the 8 PRE/4 POST screen. Their retrieval/coverage representation is `UNKNOWN` and their absence must not be labeled no earnings or final ineligibility. The absent v1 keys are W002 high 59/low 73, W016 high 24/low 29, and W025 high 6/low 11.

Among the 2,592 represented v1 keys, 2,088 have 8 PRE/4 POST metadata support. The proposed overlap-clean screen retains 508. The all-12-events/minimum-two-analyst screen retains 895 as a separate branch from the 2,088 pool. Their intersection retains 182: W002 high 10/low 165, W016 high 2/low 1, and W025 high 2/low 2. W013 and W021 retain zero. The capped clean+all12 acquisition core contains 15, which is a selection cap rather than the full-pool ceiling.

The 71-unit acquisition union is reported separately because it expands across roster sources and is not the next attrition stage. All 71 rows remain `NOT_CERTIFIED`. Its 852 event associations comprise 568 PRE and 284 POST rows; 659/852 pass the event-level minimum-two-analyst metadata count. That flag does not certify SUE compatibility.

A separate v2 snapshot represents 4,186 of the 4,191 source-universe keys. Five are absent: W016 low 3 and W025 high 1/middle 1. Their retrieval/coverage representation is also `UNKNOWN`. Among represented v2 keys, 3,246 have 8 PRE/4 POST support. No v1 overlap or analyst flag was applied to this version, and it was never pooled with the 2,592/2,088 snapshot.

## Structural calendar support

The contract cell set first intersects release calendar quarters observed in both high and low tiers within each wave and regime. That common-H/L expansion contains {total_stock_cells:,} acquired-stock by wave/regime/quarter cells, of which {missing_stock_cells:,} lack an observed event association. {excluded_quarter_count:,} one-tier-only wave/regime/quarter cells were excluded before any industry restriction and are reported separately. The broader all-quarter diagnostic contains {all_quarter_cells:,} cells with {all_quarter_missing:,} missing; it is not the contract cell set.

These are necessary calendar-support diagnostics only. The allowed event projection has no approved historical industry column, so the required industry-by-calendar-quarter-by-wave support and numeric rank remain unknown. No SUE or response values were read.

## Partial dependency graph

The graph contains 852 event-association nodes, 71 stock nodes, five wave nodes, and 417 observed release-date nodes. Its base partial components use only event-stock and event-release-date edges: {int(component_counts.iloc[0]['connected_components_among_events'])} event components, with {int(component_counts.iloc[0]['largest_component_event_associations'])} event associations in the largest. The separately labeled wave-edge proxy has a component count of {int(component_counts.iloc[1]['connected_components_among_events'])} and is not an inference rule. Calendar-quarter edges are relation-only and excluded from both algorithms. These topology counts are not ESS and do not validate an inference procedure.

The graph does not construct sponsor edges: sponsor identity is `UNKNOWN` and is not inferred from wave. The existing calendar metadata names a CRSP observed-session basis but does not record scientific approval, so all +1d response-date nodes remain explicitly `UNKNOWN`.

## Files

- `source_manifest.csv`: exact input hashes and allowed columns.
- `attrition_summary.csv` and `sequential_attrition_by_wave_tier.csv`: version-separated totals and per-wave/tier denominators.
- `snapshot_representation_gaps_by_wave_tier.csv`: exact counts absent before snapshot-specific support screens, labeled unknown.
- `event_level_analyst_eligibility.csv` and `event_analyst_eligibility_by_wave_tier_regime.csv`: 852-row metadata eligibility and grouped denominators.
- `structural_calendar_support_matrix.csv` and `structural_calendar_support_summary.csv`: common-H/L-quarter necessary support.
- `all_quarter_structural_calendar_support_matrix.csv` and `excluded_one_tier_quarters.csv`: broader diagnostic and quarters excluded from the contract cell set.
- `dependency_nodes.csv`, `dependency_edges.csv`, and `dependency_component_summary.csv`: partial observed graph and explicitly scoped topology counts.
- `actionable_missing_columns.csv`: exact missing inputs that block full design/rank construction.

## Scope controls

The build used explicit CSV `usecols` after header validation. It asserts v1 keys are a strict subset of the 2,794 source H/L tail, v2 keys are a strict subset of the 4,191 source universe, exact v1-support/overlap/intersection key equality, exact candidate analyst-flag alignment, the clean-plus-analyst conjunction, and uniqueness of the tier universe before joining. It did not read ownership/dose, liquidity, raw financial, EPS/forecast values, prices, returns, quote bodies, POST responses, or SUE. It made no SCC/network call, purchase, commit, or effect estimate. All snapshot labels remain provisional diagnostics.
"""
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")

    output_files = sorted(
        p for p in OUT.iterdir()
        if p.is_file() and p.name not in {"build_receipt.json", "build_design.py"}
    )
    receipt = {
        "status": "P1_LOCAL_OUTCOME_BLIND_DESIGN_BUILD_COMPLETE",
        "build_date": BUILD_DATE,
        "contract_sha256": CONTRACT_SHA256,
        "contract_preserved": True,
        "not_gate1_pass": True,
        "not_final_sample_approval": True,
        "not_effect_estimation": True,
        "not_ess": True,
        "input_hashes_verified": {row["input_id"]: row["sha256"] for row in manifest_rows},
        "counts": {
            **observed,
            "event_associations": len(events),
            "event_analyst_min2": int(events["sue_analyst_min2_coverage"].sum()),
            "pre_associations": int((events["sample_period"] == "PRE").sum()),
            "post_associations": int((events["sample_period"] == "POST").sum()),
            "unique_release_dates": int(events["announcement_date"].nunique()),
            "structural_stock_quarter_cells": total_stock_cells,
            "structural_stock_quarter_missing": missing_stock_cells,
            "all_quarter_diagnostic_cells": all_quarter_cells,
            "all_quarter_diagnostic_missing": all_quarter_missing,
            "excluded_one_tier_wave_regime_quarters": excluded_quarter_count,
        },
        "clean_all12_by_wave_tier": {
            f"{wave}_{tier}": int(counts_clean.get((wave, tier), 0))
            for wave in sorted(events["wave_id"].unique()) for tier in ["HIGH", "LOW"]
        },
        "calendar_support_scope": "NECESSARY_RELEASE_QUARTER_CONDITION_ONLY",
        "calendar_contract_cell_set": "QUARTERS_OBSERVED_IN_BOTH_HIGH_AND_LOW_WITHIN_WAVE_REGIME",
        "industry_controls": "UNKNOWN_COLUMN_ABSENT",
        "numeric_rank": "NOT_COMPUTED_REQUIRES_SIGNED_SUE_AND_INDUSTRY_CONTROLS",
        "sponsor_status": "UNKNOWN_NO_EDGES_INFERRED_FROM_WAVE",
        "plus1d_status": "UNKNOWN_CALENDAR_APPROVAL_NOT_OBSERVED",
        "dependency_components": component_counts.to_dict(orient="records"),
        "quarter_edges_component_use": "RELATION_ONLY_EXCLUDED",
        "source_key_assertions": {
            "v1_snapshot_keys_strict_subset_of_2794_source_tail": True,
            "v2_snapshot_keys_strict_subset_of_4191_source_universe": True,
            "v1_support_equals_overlap_equals_intersection_keys": True,
            "candidate_analyst_keys_equal_v1_keys": True,
            "candidate_analyst_flags_match_intersection": True,
            "clean_and_analyst12_is_exact_conjunction": True,
            "source_tier_universe_keys_unique_before_join": True,
        },
        "snapshot_representation_status": "UNKNOWN_RETRIEVAL_OR_COVERAGE_NOT_NO_EARNINGS",
        "raw_financial_liquidity_price_dose_return_quote_values_read": False,
        "post_response_values_read": False,
        "scc_or_network_access": False,
        "outputs_sha256": {p.name: sha256(p) for p in output_files},
    }
    (OUT / "build_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
