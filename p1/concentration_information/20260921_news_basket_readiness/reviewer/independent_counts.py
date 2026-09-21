#!/usr/bin/env python3
"""Independent, value-blind census of the explicitly permitted local metadata.

This deliberately does not import the source engineer's accounting program.  It
opens only the named local clock evidence, public source manifest, and archived
safe aggregate overlap summary.  The latter is a propagated aggregate check,
not an independent census of the unavailable old manifest rows.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
ROOT = STAGE.parent

CLOCK = ROOT / "20260920_phase3/event_clock/CLOCK_EVIDENCE.csv"
QQQ_MANIFEST = ROOT / "20260920_phase3/p2_rebalance/SOURCE_MANIFEST.json"
OVERLAP = ROOT / "20260920/execution/roster/safe_manifest_overlap_summary.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    with CLOCK.open(newline="", encoding="utf-8") as handle:
        clock_rows = list(csv.DictReader(handle))
    qqq = json.loads(QQQ_MANIFEST.read_text(encoding="utf-8"))
    overlap = json.loads(OVERLAP.read_text(encoding="utf-8"))

    event_ids = [row["event_id"] for row in clock_rows]
    issuer_counts = Counter(row["issuer"] for row in clock_rows)
    date_counts = Counter(row["event_date"] for row in clock_rows)
    comparators = {row["comparator"]: row for row in overlap["comparators"]}
    result = {
        "scope": "permitted local metadata only; no financial, quote, return, or response values",
        "inputs_sha256": {
            "clock_evidence": sha256(CLOCK),
            "qqq_source_manifest": sha256(QQQ_MANIFEST),
            "safe_manifest_overlap_summary": sha256(OVERLAP),
        },
        "independent_row_census": {
            "old_clock_inventory_rows": len(clock_rows),
            "unique_old_clock_event_ids": len(set(event_ids)),
            "scientifically_frozen_rows": sum(
                row["pilot_status"] not in {
                    "NOT_ELIGIBLE_EARLIEST_TIME_UNPROVEN",
                    "NOT_ELIGIBLE_CLOCK_UNKNOWN",
                    "TECHNICAL_ANCHOR_ONLY_NOT_SCIENTIFICALLY_FREEZABLE",
                }
                for row in clock_rows
            ),
            "conditional_technical_anchor_rows": sum(
                row["pilot_status"] == "TECHNICAL_ANCHOR_ONLY_NOT_SCIENTIFICALLY_FREEZABLE"
                for row in clock_rows
            ),
            "qqq_form_nport_source_files": sum(
                "Form N-PORT" in source.get("title", "") for source in qqq["sources"]
            ),
            "old_inventory_unique_issuers": len(issuer_counts),
            "old_inventory_events_per_issuer_min": min(issuer_counts.values()),
            "old_inventory_events_per_issuer_max": max(issuer_counts.values()),
            "old_inventory_unique_event_dates": len(date_counts),
            "old_inventory_shared_date_blocks": sum(count > 1 for count in date_counts.values()),
            "old_inventory_events_on_shared_dates": sum(count for count in date_counts.values() if count > 1),
            "old_inventory_max_events_on_one_date": max(date_counts.values()),
        },
        "propagated_aggregate_reaccounting_not_row_census": {
            "SPY": {
                "old_groups_with_historical_identity": comparators["SPY"]["release_groups_with_historical_identity"],
                "old_groups_with_manifest_symbol_match": comparators["SPY"]["release_groups_with_manifest_symbol_match"],
            },
            "QQQ": {
                "old_groups_with_historical_identity": comparators["QQQ"]["release_groups_with_historical_identity"],
                "old_groups_with_manifest_symbol_match": comparators["QQQ"]["release_groups_with_manifest_symbol_match"],
            },
        },
        "interpretation": {
            "old_32_denominator": "retained inventory, not a newly approved research population",
            "old_manifest_matches": "request/name support only, not valid quote support",
            "availability_matched_actual_baskets": "UNKNOWN",
            "valid_news_etf_actual_basket_joint_quotes": "UNKNOWN",
            "cross_etf_event_reuse": "UNKNOWN; the permitted clock inventory has no new-design ETF join",
            "issuer_and_date_counts": "inventory dependence diagnostics only, not inference clusters or effective sample size",
        },
    }
    expected = result["independent_row_census"]
    assert expected == {
        "old_clock_inventory_rows": 32,
        "unique_old_clock_event_ids": 32,
        "scientifically_frozen_rows": 0,
        "conditional_technical_anchor_rows": 2,
        "qqq_form_nport_source_files": 2,
        "old_inventory_unique_issuers": 8,
        "old_inventory_events_per_issuer_min": 4,
        "old_inventory_events_per_issuer_max": 4,
        "old_inventory_unique_event_dates": 25,
        "old_inventory_shared_date_blocks": 6,
        "old_inventory_events_on_shared_dates": 13,
        "old_inventory_max_events_on_one_date": 3,
    }
    out = HERE / "INDEPENDENT_COUNTS.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
