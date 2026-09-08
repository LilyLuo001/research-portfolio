#!/usr/bin/env python3
"""Build Gate 1 comparison/interference and consolidated gap audits.

The script consumes evidence tables. It does not estimate outcome regressions.
In particular, it leaves dose-information statistics blank unless a complete
grade-A assignment vector is present for an event.
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import Counter, defaultdict
from pathlib import Path


COMPARISON_FIELDS = [
    "evidence_key",
    "event_id",
    "event_group_id",
    "index_family",
    "event_type",
    "assignment_grade",
    "assignment_vector_complete",
    "assignment_rows",
    "grade_a_rows",
    "grade_b_rows",
    "grade_c_rows",
    "grade_u_rows",
    "signed_dose_rows",
    "absolute_dose_min_pct",
    "absolute_dose_max_pct",
    "residualization_spec",
    "dose_information_n",
    "treatment_object",
    "counterfactual_comparison",
    "assignment_unit",
    "inference_unit",
    "mechanical_weight_confound",
    "common_news_exposure_confound",
    "signal_precision_confound",
    "anticipation_status",
    "interference_status",
    "spillover_status",
    "comparison_credibility",
    "matrix_rank_status",
    "leave_largest_episode_status",
    "leave_dominant_issuer_status",
    "leave_technology_status",
    "leave_sep2024_transition_status",
    "evidence_grade",
    "status",
    "limitations",
    "notes",
]

GAP_FIELDS = [
    "evidence_key",
    "gap_id",
    "stage",
    "scope",
    "required_input",
    "observed_state",
    "why_decision_relevant",
    "minimum_resolution",
    "status",
    "blocks_gate1_assignment",
    "blocks_future_measurement",
    "source_locator",
    "next_action",
    "notes",
]

PILOT_NOTES = {
    "SS_TECH_2024Q1_REGULAR": {
        "comparison": "Within-family nonbinding and other-sector checks are candidates, but repeated mega-cap issuers, different sector exposures, and a single calendar intervention prevent automatic causal comparability.",
        "anticipation": "Rule was scheduled; exact pro-forma publication time and trader information set require event-specific verification.",
    },
    "SS_TECH_2024Q2_REGULAR": {
        "comparison": "Within-family nonbinding and other-sector checks are candidates, but repeated mega-cap issuers, different sector exposures, and a single calendar intervention prevent automatic causal comparability.",
        "anticipation": "Rule was scheduled; exact pro-forma publication time and trader information set require event-specific verification.",
    },
    "SS_ALL_2024Q3_RULE_TRANSITION": {
        "comparison": "The methodology change is one common policy intervention across affected Select Sector indexes; sectors or constituents are not independent experiments.",
        "anticipation": "Consultation, result announcement, and pro-forma visibility precede implementation; all must be represented as separate information stages.",
    },
    "NDX_2023_07_SPECIAL": {
        "comparison": "Nasdaq-100 is a separate institutional cross-check, not a clean control for Select Sector events because composition, rule, payoff, and exposure differ.",
        "anticipation": "The official schedule separates reference, pro-forma, and effective dates; the pro-forma contents remain a distinct input requirement.",
    },
}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "complete"}


def as_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def strongest_grade(grades: list[str]) -> str:
    order = {"A": 4, "B": 3, "C": 2, "U": 1}
    valid = [grade for grade in grades if grade in order]
    return max(valid, key=order.get) if valid else "U"


def dose_information_n(values: list[float]) -> float | None:
    denominator = sum(value * value for value in values)
    if denominator <= 0:
        return None
    shares = [(value * value) / denominator for value in values]
    concentration = sum(share * share for share in shares)
    return (1 / concentration) if concentration > 0 else None


def build_comparison_rows(
    events: list[dict[str, str]], doses: list[dict[str, str]]
) -> list[dict[str, object]]:
    by_event: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in doses:
        by_event[row.get("event_id", "")].append(row)

    output: list[dict[str, object]] = []
    for event in events:
        event_id = event.get("event_id", "")
        event_doses = by_event.get(event_id, [])
        grades = [(row.get("evidence_grade") or "U").strip() for row in event_doses]
        grade_counts = Counter(grades)
        complete = bool(event_doses) and all(
            as_bool(row.get("vector_complete", "")) and row.get("evidence_grade") == "A"
            for row in event_doses
        )
        signed_values = [
            value
            for value in (
                as_float(row.get("rebalance_change_weight_pct", "")) for row in event_doses
            )
            if value is not None
        ]
        information_n = dose_information_n(signed_values) if complete else None
        pilot = PILOT_NOTES.get(event_id, {})
        assignment_grade = strongest_grade(grades or [event.get("evidence_grade", "U")])

        if complete and signed_values:
            status = "ELIGIBLE_EXACT_DOSE_SUPPORT_AUDIT"
            matrix_status = "NOT_ESTIMATED_GATE1_DESIGN_MATRIX_REQUIRED"
        elif assignment_grade == "B":
            status = "EVENT_DOCUMENTED_DOSE_INCOMPLETE"
            matrix_status = "BLOCKED_INCOMPLETE_ASSIGNMENT_VECTOR"
        elif assignment_grade == "C":
            status = "SCREENING_PROXY_ONLY"
            matrix_status = "BLOCKED_PROXY_NOT_ASSIGNMENT"
        else:
            status = "ASSIGNMENT_UNKNOWN"
            matrix_status = "BLOCKED_ASSIGNMENT_UNKNOWN"

        abs_values = [abs(value) for value in signed_values]
        limitations = (
            "No residualized support, rank, collinearity, dominance, or leave-one-out statistic is reported "
            "without a complete grade-A signed vector and a frozen future design matrix."
        )
        output.append(
            {
                "evidence_key": f"DESIGN:{event_id}",
                "event_id": event_id,
                "event_group_id": event.get("event_group_id", ""),
                "index_family": event.get("index_family", ""),
                "event_type": event.get("event_type", ""),
                "assignment_grade": assignment_grade,
                "assignment_vector_complete": "yes" if complete else "no",
                "assignment_rows": len(event_doses),
                "grade_a_rows": grade_counts["A"],
                "grade_b_rows": grade_counts["B"],
                "grade_c_rows": grade_counts["C"],
                "grade_u_rows": grade_counts["U"],
                "signed_dose_rows": len(signed_values),
                "absolute_dose_min_pct": f"{min(abs_values):.8g}" if abs_values else "",
                "absolute_dose_max_pct": f"{max(abs_values):.8g}" if abs_values else "",
                "residualization_spec": "none; future design matrix not frozen" if not complete else "raw signed dose only; residualization pending frozen design matrix",
                "dose_information_n": f"{information_n:.8g}" if information_n else "",
                "treatment_object": "rule-assigned index-weight change or event-level intervention; not ETF holdings",
                "counterfactual_comparison": pilot.get("comparison", "Not established by Gate 1 evidence."),
                "assignment_unit": "basket assignment within intervention group",
                "inference_unit": "intervention group and common-news meeting; repeated securities are dependent",
                "mechanical_weight_confound": "OPEN: arithmetic basket reweighting is the first adversary and must be replayed on identical price paths.",
                "common_news_exposure_confound": "OPEN: same signal stock does not equalize residual-basket macro loadings.",
                "signal_precision_confound": "OPEN: forecast gains can reflect heterogeneous direct response, noise, or quote timing rather than transmission.",
                "anticipation_status": pilot.get("anticipation", "Unknown dates/times remain unknown."),
                "interference_status": "OPEN: shared issuers, shared dates, and overlapping baskets preclude independent-row interpretation.",
                "spillover_status": "OPEN: controls sharing stocks or trading flows may themselves be affected.",
                "comparison_credibility": pilot.get("comparison", "Not established by Gate 1 evidence."),
                "matrix_rank_status": matrix_status,
                "leave_largest_episode_status": "NOT_COMPUTED_INCOMPLETE_EXACT_SUPPORT",
                "leave_dominant_issuer_status": "NOT_COMPUTED_INCOMPLETE_EXACT_SUPPORT",
                "leave_technology_status": "NOT_COMPUTED_INCOMPLETE_EXACT_SUPPORT",
                "leave_sep2024_transition_status": "NOT_COMPUTED_INCOMPLETE_EXACT_SUPPORT",
                "evidence_grade": assignment_grade,
                "status": status,
                "limitations": limitations,
                "notes": "Grade describes assignment observability, not exogeneity, causal validity, or statistical power.",
            }
        )
    return output


def build_gap_rows(
    events: list[dict[str, str]],
    doses: list[dict[str, str]],
    local_catalog: list[dict[str, str]],
    stage_a_gaps: list[dict[str, str]],
) -> list[dict[str, object]]:
    doses_by_event: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in doses:
        doses_by_event[row.get("event_id", "")].append(row)

    def exact(event_id: str) -> bool:
        rows = doses_by_event.get(event_id, [])
        return bool(rows) and all(
            row.get("evidence_grade") == "A" and as_bool(row.get("vector_complete", ""))
            for row in rows
        )

    select_sector_pilots = [
        "SS_TECH_2024Q1_REGULAR",
        "SS_TECH_2024Q2_REGULAR",
        "SS_ALL_2024Q3_RULE_TRANSITION",
    ]
    select_exact = all(exact(event_id) for event_id in select_sector_pilots)
    ndx_exact = exact("NDX_2023_07_SPECIAL")
    has_membership = any(
        "membership" in (row.get("logical_dataset", "").lower())
        and row.get("status", "").upper().startswith(("VERIFIED", "AVAILABLE", "AUDITED"))
        for row in local_catalog
    )

    gaps: list[dict[str, object]] = [
        {
            "evidence_key": "GAP:EXACT_SELECT_SECTOR_ASSIGNMENTS",
            "gap_id": "EXACT_SELECT_SECTOR_ASSIGNMENTS",
            "stage": "B-C",
            "scope": "2018-2025 Select Sector interventions, beginning with 2024 pilots",
            "required_input": "Official historical pro-forma/assignment files or complete contemporaneous float-adjusted inputs sufficient to replay and reconcile each applicable rule.",
            "observed_state": "All three pilot vectors are grade A and complete." if select_exact else "Public records document rules/events or selected rounded weights, but complete reconciled pilot assignment vectors are not established.",
            "why_decision_relevant": "Exact signed doses, cap distortions, binding status, and support diagnostics require complete assignments on a common valuation date.",
            "minimum_resolution": "Recover and reconcile the March, June, and September 2024 provider assignment/pro-forma files, then demonstrate one repeatable path for earlier quarters.",
            "status": "RESOLVED" if select_exact else "OPEN_BLOCKING_GATE1_ASSIGNMENT",
            "blocks_gate1_assignment": "yes" if not select_exact else "no",
            "blocks_future_measurement": "yes" if not select_exact else "no",
            "source_locator": "assignment_doses_and_evidence.csv; rebalance_event_ledger.csv",
            "next_action": "Request/export the precise historical constituent assignment package from an authorized index-data source; do not substitute ETF holdings.",
            "notes": "A transport-specific 403 for an official PDF is not this gap; the missing object is the complete historical assignment vector/input package.",
        },
        {
            "evidence_key": "GAP:EXACT_NDX_202307_ASSIGNMENT",
            "gap_id": "EXACT_NDX_202307_ASSIGNMENT",
            "stage": "B-C",
            "scope": "Nasdaq-100 July 2023 special rebalance",
            "required_input": "Historical July 14, 2023 pro-forma/index-share file or complete verified reference inputs and rule replay.",
            "observed_state": "Complete grade-A assignment recovered." if ndx_exact else "Official notice verifies the schedule and qualitative redistribution; complete historical pro-forma contents are not established.",
            "why_decision_relevant": "The episode is one cross-check, and its exact dose cannot be inferred from the schedule notice alone.",
            "minimum_resolution": "Recover the official historical pro-forma/index-share file and reconcile effective weights at the correct reference state.",
            "status": "RESOLVED" if ndx_exact else "OPEN_BLOCKING_EXACT_NDX_DOSE",
            "blocks_gate1_assignment": "no",
            "blocks_future_measurement": "yes" if not ndx_exact else "no",
            "source_locator": "assignment_doses_and_evidence.csv; rebalance_event_ledger.csv",
            "next_action": "Use an authorized Nasdaq index-data history or contemporaneously archived official pro-forma, preserving publication timestamp.",
            "notes": "This single episode would remain one intervention even if every constituent weight were recovered.",
        },
        {
            "evidence_key": "GAP:POINT_IN_TIME_INDEX_MEMBERSHIP",
            "gap_id": "POINT_IN_TIME_INDEX_MEMBERSHIP",
            "stage": "A-C",
            "scope": "Select Sector and Nasdaq-100 constituent universes",
            "required_input": "Point-in-time constituent membership, issuer mapping, share-class treatment, and effective-date lineage.",
            "observed_state": "Verified membership table located." if has_membership else "No verified archive object has yet been established as exact point-in-time index constituent membership.",
            "why_decision_relevant": "Fund holdings, industry codes, and index returns do not define the provider's historical assignment universe.",
            "minimum_resolution": "Identify an authoritative constituent-history source and validate effective dates and issuer aggregation.",
            "status": "RESOLVED" if has_membership else "OPEN_BLOCKING_RECONSTRUCTION",
            "blocks_gate1_assignment": "yes" if not has_membership else "no",
            "blocks_future_measurement": "yes" if not has_membership else "no",
            "source_locator": "local_data_catalog.csv",
            "next_action": "Audit licensed/public index constituent history; retain ETF holdings only as validation or screening evidence.",
            "notes": "Suggestive filenames are not membership evidence.",
        },
        {
            "evidence_key": "GAP:INTRADAY_OUTCOME_MEASUREMENT",
            "gap_id": "INTRADAY_OUTCOME_MEASUREMENT",
            "stage": "Q2-Q3",
            "scope": "Later stock-ETF-futures measurement pilot",
            "required_input": "Timestamped modern stock/ETF quotes and trades, and futures data only if the scientific claim retains futures, with clock/source metadata.",
            "observed_state": "The documented archive offers daily MIDAS summaries, not modern event-time quote/trade paths; modern TAQ entitlement was not established.",
            "why_decision_relevant": "Daily data cannot validate intraday speed, quote disagreement, cross-market clocks, or event-level measurement variance/MDE.",
            "minimum_resolution": "Acquire a bounded pilot package for frozen securities, events, sessions, identifiers, quote/trade fields, timestamps, conditions, and corporate-action handling.",
            "status": "OPEN_NOT_A_GATE1_EVENT_COUNT_FAILURE",
            "blocks_gate1_assignment": "no",
            "blocks_future_measurement": "yes",
            "source_locator": "local_data_catalog.csv; WRDS manual sections 26A and 40, subject to executed audit",
            "next_action": "Only after assignment support clears, specify and source the smallest measurement-development sample; do not create pseudo-ticks from daily prices.",
            "notes": "A stock-ETF-only pilot can narrow the claim and avoid CME, but cannot answer a futures-inclusive question.",
        },
        {
            "evidence_key": "GAP:CAUSAL_COMPARISON_SUPPORT",
            "gap_id": "CAUSAL_COMPARISON_SUPPORT",
            "stage": "D-E",
            "scope": "Preferred future intervention design",
            "required_input": "A frozen treatment/exposure matrix and credible counterfactual that addresses arithmetic weights, exposure differences, anticipation, shared issuers, and spillovers.",
            "observed_state": "Event existence and common-news overlap alone do not establish a valid comparison or exclusion restriction.",
            "why_decision_relevant": "A same-stock or cross-index comparison can retain heterogeneous target loadings and shared treatment; a numerical rule is not random assignment.",
            "minimum_resolution": "After exact vectors are recovered, pre-specify one estimand, replay the mechanical benchmark, test matrix support, and state the strongest falsification.",
            "status": "OPEN_DESIGN_GAP",
            "blocks_gate1_assignment": "no",
            "blocks_future_measurement": "yes",
            "source_locator": "comparison_and_interference_audit.csv; assignment_and_fomc_support.csv",
            "next_action": "Do not select a comparison using outcome returns; first audit support after event, regime, issuer, technology, and September-2024 exclusions.",
            "notes": "This gap may remain even if exact assignments are purchased or recovered.",
        },
    ]

    for source in stage_a_gaps:
        gap_id = source.get("gap_id", "UNNAMED_STAGE_A_GAP")
        gaps.append(
            {
                "evidence_key": source.get("evidence_key") or f"GAP:STAGE_A:{gap_id}",
                "gap_id": f"STAGE_A_{gap_id}",
                "stage": "A",
                "scope": source.get("scope", source.get("affected_dataset_or_funds", "")),
                "required_input": source.get("required_input", ""),
                "observed_state": source.get("notes", "See Stage A audit."),
                "why_decision_relevant": source.get("why_needed", ""),
                "minimum_resolution": source.get("next_action", ""),
                "status": source.get("status", "OPEN"),
                "blocks_gate1_assignment": "review_stage_a_gap",
                "blocks_future_measurement": "review_stage_a_gap",
                "source_locator": source.get("source_locator", "remaining_input_gaps_stage_a.csv"),
                "next_action": source.get("next_action", ""),
                "notes": "Imported from the executed Stage A archive audit; blocking role requires design-level adjudication.",
            }
        )

    # Keep only events argument in the function contract so future extensions can
    # adjudicate sample-wide gaps without changing the interface.
    _ = events
    return gaps


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    events = read_csv(root / "rebalance_event_ledger.csv")
    doses = read_csv(root / "assignment_doses_and_evidence.csv")
    local_catalog = read_csv(root / "local_data_catalog.csv")
    stage_a_gaps = read_csv(root / "remaining_input_gaps_stage_a.csv")
    if not events:
        raise SystemExit("rebalance_event_ledger.csv is missing or empty")
    if not doses:
        raise SystemExit("assignment_doses_and_evidence.csv is missing or empty")
    write_csv(
        root / "comparison_and_interference_audit.csv",
        COMPARISON_FIELDS,
        build_comparison_rows(events, doses),
    )
    write_csv(
        root / "remaining_input_gaps.csv",
        GAP_FIELDS,
        build_gap_rows(events, doses, local_catalog, stage_a_gaps),
    )
    print(f"wrote comparison and gap audits under {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
