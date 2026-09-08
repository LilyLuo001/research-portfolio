#!/usr/bin/env python3
"""Create a deterministic, non-regression summary of Gate 1 audit tables."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def counts(rows: list[dict[str, str]], field: str) -> dict[str, int]:
    return dict(sorted(Counter((row.get(field) or "<blank>") for row in rows).items()))


def yes(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def build_summary(root: Path) -> dict[str, object]:
    catalog = read_rows(root / "local_data_catalog.csv")
    funds = read_rows(root / "fund_identifier_and_coverage_audit.csv")
    rules = read_rows(root / "source_and_rule_registry.csv")
    events = read_rows(root / "rebalance_event_ledger.csv")
    doses = read_rows(root / "assignment_doses_and_evidence.csv")
    fomc = read_rows(root / "fomc_calendar.csv")
    support = read_rows(root / "assignment_and_fomc_support.csv")
    comparisons = read_rows(root / "comparison_and_interference_audit.csv")
    gaps = read_rows(root / "remaining_input_gaps.csv")

    real_meeting_ids = {
        row.get("meeting_id", "")
        for row in support
        if row.get("meeting_id", "") not in {"", "UNRESOLVED", "NA"}
    }
    real_event_ids = {row.get("event_id", "") for row in events if row.get("event_id", "")}
    real_event_groups = {
        row.get("event_group_id", "") for row in events if row.get("event_group_id", "")
    }

    unique_band_pairs: dict[str, set[tuple[str, str]]] = {
        "20": set(),
        "40": set(),
        "60": set(),
    }
    for row in support:
        group = row.get("event_group_id", "") or row.get("event_id", "")
        meeting = row.get("meeting_id", "")
        if not group or not meeting or meeting in {"UNRESOLVED", "NA"}:
            continue
        for band in ("20", "40", "60"):
            if yes(row.get(f"within_{band}td", "")):
                unique_band_pairs[band].add((group, meeting))

    return {
        "summary_type": "assignment_and_support_audit_only",
        "headline_outcome_regressions_run": False,
        "local": {
            "catalog_rows": len(catalog),
            "catalog_status_counts": counts(catalog, "status"),
            "fund_period_rows": len(funds),
            "unique_fund_tickers": sorted(
                {row.get("fund_ticker", "") for row in funds if row.get("fund_ticker", "")}
            ),
            "fund_status_counts": counts(funds, "status"),
        },
        "institutional": {
            "rule_source_rows": len(rules),
            "rule_evidence_grade_counts": counts(rules, "evidence_grade"),
            "event_rows": len(events),
            "unique_event_ids": len(real_event_ids),
            "unique_event_groups": len(real_event_groups),
            "event_binding_status_counts": counts(events, "binding_status"),
            "event_evidence_grade_counts": counts(events, "evidence_grade"),
        },
        "assignment": {
            "dose_rows": len(doses),
            "dose_grade_counts": counts(doses, "evidence_grade"),
            "dose_status_counts": counts(doses, "dose_status"),
            "complete_grade_a_events": sorted(
                {
                    row.get("event_id", "")
                    for row in doses
                    if row.get("evidence_grade") == "A" and yes(row.get("vector_complete", ""))
                }
            ),
        },
        "common_news": {
            "fomc_calendar_rows": len(fomc),
            "eligible_calendar_meeting_ids": len(
                {
                    row.get("meeting_id", "")
                    for row in fomc
                    if yes(row.get("eligible_common_news", ""))
                    and row.get("calendar_scope", "").lower() == "primary_2018_2025"
                }
            ),
            "fomc_meeting_status_counts": counts(fomc, "meeting_status"),
            "support_rows": len(support),
            "distinct_support_meeting_ids": len(real_meeting_ids),
            "unique_event_group_meeting_pairs_by_band": {
                band: len(pairs) for band, pairs in unique_band_pairs.items()
            },
        },
        "design": {
            "comparison_rows": len(comparisons),
            "comparison_status_counts": counts(comparisons, "status"),
            "matrix_rank_status_counts": counts(comparisons, "matrix_rank_status"),
        },
        "gaps": {
            "rows": len(gaps),
            "status_counts": counts(gaps, "status"),
            "gate1_assignment_blockers": [
                row.get("gap_id", "")
                for row in gaps
                if yes(row.get("blocks_gate1_assignment", ""))
            ],
            "future_measurement_blockers": [
                row.get("gap_id", "")
                for row in gaps
                if yes(row.get("blocks_future_measurement", ""))
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output or root / "logs" / "gate1_summary.json"
    summary = build_summary(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
