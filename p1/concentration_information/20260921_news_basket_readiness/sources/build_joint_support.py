#!/usr/bin/env python3
"""Build value-blind news--ETF--actual-basket readiness counts from retained metadata.

This program intentionally reads only the named small receipts/manifests.  It neither
opens SCC nor decodes DBN/Parquet inputs, so its output is a reproducible accounting
of retained evidence, not a claim of live quote or holding availability.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "20260921_news_basket_readiness"
INPUTS = {
    "event_clock": ROOT / "20260920_phase3/event_clock/CLOCK_SUMMARY.json",
    "quote_inventory": ROOT / "20260920/execution/quote_inventory/inventory_summary.json",
    "quote_scc_inventory": ROOT / "20260920/execution/quote_inventory/scc_inventory_summary.json",
    "manifest_overlap": ROOT / "20260920/execution/roster/safe_manifest_overlap_summary.json",
    "holdings_inventory": ROOT / "20260920/execution/network/NETWORK_SUPPORT.json",
    "qqq_source_manifest": ROOT / "20260920_phase3/p2_rebalance/SOURCE_MANIFEST.json",
    "old_intraday_manifest": ROOT / "20260921_empirical_decision/intraday/SCC_DBN_SOURCE_MANIFEST.csv",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str) -> dict:
    return json.loads(INPUTS[name].read_text())


def main() -> None:
    clock = load("event_clock")
    quote = load("quote_inventory")
    overlap = load("manifest_overlap")
    holdings = load("holdings_inventory")
    qqq = load("qqq_source_manifest")
    nport = [s for s in qqq["sources"] if "Form N-PORT" in s["title"]]
    comparators = {x["comparator"]: x for x in overlap["comparators"]}
    old_dbn_rows = len(INPUTS["old_intraday_manifest"].read_text().splitlines()) - 1

    result = {
        "purpose": "retained-metadata readiness accounting; no values, bodies, or SCC query",
        "inputs_sha256": {key: digest(path) for key, path in INPUTS.items()},
        "stages": [
            {
                "stage": "candidate_news_records",
                "count": clock["events"],
                "denominator": "retained candidate release groups",
                "status": "RECORD_COVERAGE_ONLY",
            },
            {
                "stage": "first_public_clock_certified",
                "count": clock["scientifically_freezable_events"],
                "denominator": clock["events"],
                "status": "ZERO_CERTIFIED_NOT_DATA_ABSENCE",
                "reason": clock["reason_no_event_is_frozen"],
            },
            {
                "stage": "conditional_clock_technical_anchors",
                "count": clock["conditional_technical_anchor_events"],
                "denominator": clock["events"],
                "status": "NOT_SCIENTIFICALLY_ELIGIBLE",
            },
            {
                "stage": "actual_fund_holdings_files",
                "count": len(nport),
                "denominator": "retained public QQQ Form N-PORT snapshots",
                "status": "RECORD_FILE_COVERAGE_ONLY",
                "reason": "quarter-end reports, not availability-matched event baskets",
            },
            {
                "stage": "candidate_events_with_availability_matched_actual_basket",
                "count": None,
                "denominator": clock["events"],
                "status": "UNKNOWN_NO_AUTHORIZED_JOIN",
            },
            {
                "stage": "historical_identity_and_manifest_coverage_spy",
                "count": comparators["SPY"]["release_groups_with_manifest_symbol_match"],
                "denominator": comparators["SPY"]["release_groups_with_historical_identity"],
                "status": "MANIFEST_INTERVAL_COVERAGE_NOT_VALID_QUOTES",
            },
            {
                "stage": "historical_identity_and_manifest_coverage_qqq",
                "count": comparators["QQQ"]["release_groups_with_manifest_symbol_match"],
                "denominator": comparators["QQQ"]["release_groups_with_historical_identity"],
                "status": "ZERO_OLD_MANIFEST_MATCH_NOT_DATA_ABSENCE",
            },
            {
                "stage": "candidate_news_etf_actual_basket_valid_quote_joint_support",
                "count": None,
                "denominator": clock["events"],
                "status": "UNKNOWN_NO_AUTHORIZED_CUSTODIAN_VALIDITY_PROCESS",
            },
        ],
        "retained_source_metadata": {
            "quote_manifest_rows": quote["download_receipt"]["manifest_rows"],
            "quote_catalog_datasets": quote["catalog"]["datasets"],
            "old_intraday_manifest_rows": old_dbn_rows,
            "archived_holdings_files": holdings["holdings_files"],
            "archived_holdings_header_files": holdings["historical_header_files"],
            "archived_holdings_status": holdings["status"],
            "nport_record_count_each": "NOT_INDEPENDENTLY_RECOUNTED: historical narrative figure, excluded from this recomputed accounting",
        },
    }
    (OUT / "sources").mkdir(parents=True, exist_ok=True)
    (OUT / "sources" / "STAGED_COUNTS.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
