#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

BASE = Path("/Users/lilyluo/P1_Fixed_125USD_Pilot_Order_extracted/p1_fixed_pilot")
SRC = Path("/Users/lilyluo/research-portfolio-p1-advanced-readonly/p1")
OUT = BASE / "source_wave_gap_resolution_20260915"

PATHS = {
    "config": OUT / "config.json",
    "public_projection": BASE / "recovered99_other_wave_provenance_20260915/public_fund_series_metadata_projection.csv",
    "exposure_cells": SRC / "exposure/exposure_stock_wave_all.csv",
    "gate0_events": SRC / "exposure/exposure_universe_gate0_pass.csv",
    "parse_audit": SRC / "exposure/nport_pre_parse_audit.csv",
    "mapping_audit": SRC / "exposure/nport_crsp_security_crosswalk.csv",
    "event_master": SRC / "universe_v2/output/event_master_final_reconciled.csv",
    "historical_events": SRC / "events_merged.csv",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def classify(row: pd.Series) -> tuple[str, str]:
    if int(row.common_equity_candidates) == 0:
        return (
            "INTENTIONAL_NO_NPORT_COMMON_EQUITY_CANDIDATES_IN_STOCK_SCOPE",
            "Selected strict-PRE N-PORT metadata reports zero common-equity candidate positions; no stock cell is constructed.",
        )
    if int(row.mapping_rows) != int(row.common_equity_candidates):
        return (
            "UNKNOWN_MAPPING_AUDIT_ROW_COVERAGE_GAP",
            "Common-equity candidate count does not reconcile to mapping-audit rows for the wave.",
        )
    if int(row.unrecognized_mapping_status_rows) > 0:
        return (
            "UNKNOWN_UNRECOGNIZED_MAPPING_STATUS",
            "Mapping audit contains a status outside the pinned explicit status set.",
        )
    if int(row.unmatched_rows) + int(row.ambiguous_rows) > 0:
        return (
            "UNKNOWN_IDENTIFIER_LINK_GAP",
            "At least one N-PORT common-equity candidate lacks a unique date-valid CRSP U.S.-common-stock mapping.",
        )
    outside = int(row.non_common_rows) + int(row.non_us_rows) + int(row.non_us_non_crsp_rows)
    if outside == int(row.mapping_rows):
        return (
            "INTENTIONAL_CANDIDATES_OUTSIDE_CRSP_US_COMMON_STOCK_SCOPE",
            "Observed candidates are affirmatively classified as non-common or non-U.S. by the pinned mapping logic; no eligible U.S. common-stock cell is constructed.",
        )
    return ("UNKNOWN_MAPPING_STATE", "Candidate mapping rows do not resolve to an exhaustively recognized terminal state.")


def main() -> None:
    cfg = json.loads(PATHS["config"].read_text())
    public = pd.read_csv(PATHS["public_projection"], usecols=["wave_id", "effective_date"], dtype=str)
    cells = pd.read_csv(PATHS["exposure_cells"], usecols=["wave_id"], dtype=str)
    gaps = sorted(set(public.wave_id.dropna()) - set(cells.wave_id.dropna()))

    gate = pd.read_csv(
        PATHS["gate0_events"],
        usecols=["event_id", "wave_id", "effective_date", "adviser", "pre_series_id", "pre_series_name", "post_series_id", "post_series_name", "pre_report_date", "pre_accession", "gate0"],
        dtype=str,
    )
    gate = gate[gate.wave_id.isin(gaps)].copy()
    parse = pd.read_csv(
        PATHS["parse_audit"],
        usecols=["event_id", "wave_id", "pre_series_id", "pre_accession", "pre_report_date", "effective_date", "strictly_pre_pass", "series_id_pass", "positions", "common_equity_candidates", "source_url"],
        dtype=str,
    )
    parse = parse[parse.wave_id.isin(gaps)].copy()
    for c in ["positions", "common_equity_candidates"]:
        parse[c] = pd.to_numeric(parse[c], errors="raise").astype(int)

    mapping = pd.read_csv(
        PATHS["mapping_audit"],
        usecols=["event_id", "wave_id", "pre_series_id", "mapping_status", "mapping_method", "permno"],
        dtype=str,
    )
    mapping_gap = mapping[mapping.wave_id.isin(gaps)].copy()
    recognized_statuses = {"exact_matched", "unmatched", "ambiguous", "non_common_equity", "non_us", "non_us_non_crsp"}
    mapping_gap["recognized_mapping_status"] = mapping_gap.mapping_status.isin(recognized_statuses)
    status = (
        mapping_gap.groupby(["wave_id", "mapping_status"], dropna=False).size().unstack(fill_value=0)
        if len(mapping_gap) else pd.DataFrame()
    )
    for c in ["exact_matched", "unmatched", "ambiguous", "non_common_equity", "non_us", "non_us_non_crsp"]:
        if c not in status.columns:
            status[c] = 0

    wave = parse.groupby("wave_id", as_index=False).agg(
        effective_date=("effective_date", "first"),
        gate0_event_rows=("event_id", "nunique"),
        predecessor_series=("pre_series_id", "nunique"),
        strict_pre_positions=("positions", "sum"),
        common_equity_candidates=("common_equity_candidates", "sum"),
        strict_pre_all_events=("strictly_pre_pass", lambda s: bool((s == "True").all())),
        series_id_all_events=("series_id_pass", lambda s: bool((s == "True").all())),
        pre_accessions=("pre_accession", lambda s: ";".join(sorted(set(s.dropna())))),
        source_urls=("source_url", lambda s: ";".join(sorted(set(s.dropna())))),
    )
    for col, outcol in [
        ("exact_matched", "exact_matched_rows"), ("unmatched", "unmatched_rows"),
        ("ambiguous", "ambiguous_rows"), ("non_common_equity", "non_common_rows"),
        ("non_us", "non_us_rows"), ("non_us_non_crsp", "non_us_non_crsp_rows"),
    ]:
        wave[outcol] = wave.wave_id.map(status[col]).fillna(0).astype(int)
    wave["mapping_rows"] = wave.wave_id.map(mapping_gap.groupby("wave_id").size()).fillna(0).astype(int)
    wave["unrecognized_mapping_status_rows"] = wave.wave_id.map(
        mapping_gap.groupby("wave_id").recognized_mapping_status.apply(lambda s: int((~s).sum()))
    ).fillna(0).astype(int)
    labels = wave.apply(classify, axis=1)
    wave["gap_classification"] = [x[0] for x in labels]
    wave["classification_basis"] = [x[1] for x in labels]
    wave["missing_or_intentional"] = wave.gap_classification.map(lambda x: "MISSING_UNKNOWN" if x.startswith("UNKNOWN") else "INTENTIONAL_STOCK_SCOPE_ABSENCE")
    wave["final_sample_inference"] = "NOT_ASSESSED"
    wave = wave.sort_values("wave_id")
    wave.to_csv(OUT / "wave_gap_classification.csv", index=False)

    # W006 keeps predecessor series before the existing wave aggregation.
    w006 = mapping[(mapping.wave_id == "W006") & (mapping.mapping_status == "exact_matched")]
    w006_counts = w006.groupby(["event_id", "pre_series_id"], as_index=False).agg(
        exact_mapped_position_rows=("permno", "size"), distinct_permnos=("permno", "nunique")
    )
    w006_public = pd.read_csv(
        BASE / "recovered99_other_wave_provenance_20260915/public_fund_series_metadata_projection.csv",
        usecols=["wave_id", "effective_date", "adviser", "pre_series_id", "pre_series_name", "post_series_id", "post_series_name"], dtype=str,
    )
    w006_public = w006_public[w006_public.wave_id == "W006"]
    w006_out = w006_public.merge(w006_counts, on="pre_series_id", how="left", validate="one_to_one")
    w006_out["existing_wave_level_linkage_status"] = "DATE_BUCKET_LINKAGE_ONLY_NOT_SHARED_SPONSOR_OR_PACKAGE"
    w006_out["fund_level_attribution_feasibility"] = "FEASIBLE_FROM_PRE_AGGREGATION_EVENT_AND_SERIES_LINEAGE_REQUIRES_VERSIONED_REBUILD"
    w006_out.to_csv(OUT / "w006_fund_attribution_feasibility.csv", index=False)

    master = pd.read_csv(
        PATHS["event_master"],
        usecols=["pre_series_id", "pre_series_name", "post_series_id", "post_series_name", "n14_first_filed", "supporting_accessions", "proposed_close", "final_effective_date", "final_source_accession", "final_evidence", "verified_effective_date", "verified_date_source_accession", "verified_date_source_form"],
        dtype=str,
    )
    w032 = master[master.pre_series_id.isin(["S000008429", "S000008433"])].copy()
    w032["historical_proposed_effective_date"] = "2024-11-15"
    w032["historical_proposed_accession"] = "0001193125-24-203605"
    w032["date_conflict_status"] = "DATE_TYPE_VERSION_CONFLICT_PROPOSED_2024_11_15_VS_VERIFIED_COMPLETION_2024_12_09"
    w032["iw_status"] = "UNKNOWN_NO_AUTOMATIC_LEGAL_OR_OPERATION_BOUND_SELECTION"
    w032.to_csv(OUT / "w032_date_version_conflict.csv", index=False)

    summary = wave.groupby(["missing_or_intentional", "gap_classification"], as_index=False).agg(waves=("wave_id", "nunique"))
    summary.to_csv(OUT / "gap_classification_summary.csv", index=False)

    invariants = {
        "public_wave_count_47": int(public.wave_id.nunique()) == cfg["public_wave_universe_expected"],
        "exposure_wave_count_30": int(cells.wave_id.nunique()) == cfg["exposure_wave_universe_expected"],
        "gap_set_exactly_17": len(gaps) == cfg["gap_wave_count_expected"] and set(wave.wave_id) == set(gaps),
        "all_gap_gate0_rows_pass": bool((gate.gate0 == "PASS").all()),
        "all_gap_strict_pre": bool(wave.strict_pre_all_events.all()),
        "all_gap_series_id_match": bool(wave.series_id_all_events.all()),
        "no_exact_mapped_rows_in_gap_waves": int(wave.exact_matched_rows.sum()) == 0,
        "candidate_mapping_rows_reconcile": bool((wave.mapping_rows == wave.common_equity_candidates).all()),
        "mapping_statuses_exhaustive": int(wave.unrecognized_mapping_status_rows.sum()) == 0,
        "w006_two_distinct_predecessor_series": len(w006_out) == 2 and w006_out.adviser.nunique() == 2,
        "w032_two_series_preserved": len(w032) == 2,
        "no_final_sample_inference": bool((wave.final_sample_inference == "NOT_ASSESSED").all()),
    }
    if not all(invariants.values()):
        raise AssertionError(invariants)

    receipt = {
        "status": "SOURCE_WAVE_GAP_RESOLUTION_COMPLETE",
        "counts": {
            "public_waves": int(public.wave_id.nunique()),
            "exposure_waves": int(cells.wave_id.nunique()),
            "gap_waves": len(gaps),
            "intentional_stock_scope_absence_waves": int((wave.missing_or_intentional == "INTENTIONAL_STOCK_SCOPE_ABSENCE").sum()),
            "identifier_link_unknown_waves": int((wave.missing_or_intentional == "MISSING_UNKNOWN").sum()),
            "w006_predecessor_series": int(len(w006_out)),
            "w032_date_conflict_series": int(len(w032)),
        },
        "gap_waves": gaps,
        "invariants": invariants,
        "input_sha256": {str(p): sha256(p) for p in PATHS.values()},
        "output_sha256": {str(p): sha256(p) for p in [OUT / "wave_gap_classification.csv", OUT / "gap_classification_summary.csv", OUT / "w006_fund_attribution_feasibility.csv", OUT / "w032_date_version_conflict.csv"]},
        "limits": [
            "No outcome, forecast value, price, return, quote, or response was read.",
            "Intentional means absent under the pinned U.S.-common-stock construction, not absent from the fund or vendor universe.",
            "W006 candidate links remain date-bucket-only until a versioned fund-level rebuild is executed.",
            "W032 proposed and verified completion dates are preserved; this stage does not select I_w.",
        ],
        "requested_route": "Sol/medium",
        "backend_telemetry": "NOT_OBSERVED",
    }
    (OUT / "EXECUTION_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
