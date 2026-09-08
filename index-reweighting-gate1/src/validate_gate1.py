#!/usr/bin/env python3
"""Validate the structural, semantic, provenance, and privacy Gate 1 contract.

The validator checks internal consistency and public-output hygiene. It cannot
establish that an institutional claim is true or provide a legal license opinion;
those require inspection of the cited primary source and applicable agreements.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any


SECRET_PATTERNS = (
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"https://[^/@\s:]+:[^/@\s]+@"),
)
RAW_SUFFIXES = {
    ".arrow",
    ".db",
    ".dta",
    ".duckdb",
    ".feather",
    ".parquet",
    ".pq",
    ".rdata",
    ".rds",
    ".sas7bdat",
    ".sqlite",
    ".sqlite3",
    ".xls",
    ".xlsx",
    ".xpt",
}
PRIVATE_NAME_PATTERNS = (
    re.compile(r"(^|_)private\.csv$", re.IGNORECASE),
    re.compile(r"stage_a_private_evidence\.json$", re.IGNORECASE),
)
RUNTIME_PATH_PATTERNS = (
    re.compile("/" + r"Users/[^/\s]+/"),
    re.compile("/" + r"home/[^/\s]+/"),
    re.compile("/" + r"projectnb/[^\s'\"`]+"),
    re.compile(r"\buid=\d+"),
    re.compile(r"\bgid=\d+"),
)
PROHIBITED_PUBLIC_JSON_KEYS = {
    "archive",
    "baseline_manifest",
    "candidate_identifiers",
    "done_file",
    "done_payload",
    "holdings_batches",
    "hostname",
    "left",
    "left_sha256",
    "output_dir",
    "overlap_comparisons",
    "part_files",
    "pid",
    "platform",
    "post_snapshot_path",
    "python_executable",
    "query_file",
    "right",
    "right_sha256",
    "target_metadata_rows",
    "target_metadata_key_fingerprint",
    "target_keyword_manifest_hits",
    "target_keyword_near_taq_hits",
}

TABLE_PREFIXES = {
    "local_data_catalog.csv": ("LOCAL:",),
    "fund_identifier_and_coverage_audit.csv": ("FUND:",),
    "source_and_rule_registry.csv": ("RULE:", "SOURCE:"),
    "rebalance_event_ledger.csv": ("EVENT:",),
    "assignment_doses_and_evidence.csv": ("DOSE:",),
    "fomc_calendar.csv": ("FOMC:",),
    "assignment_and_fomc_support.csv": ("SUPPORT:",),
    "comparison_and_interference_audit.csv": ("DESIGN:",),
    "remaining_input_gaps.csv": ("GAP:", "GAPA:"),
    "remaining_input_gaps_stage_a.csv": ("GAPA:",),
}
ALLOWED_GRADES = {"A", "B", "C", "U"}
ALLOWED_BINDING = {
    "confirmed_binding",
    "confirmed_nonbinding",
    "confirmed_other_intervention",
    "outside_applicable_regime",
    "uncertain",
}
ROLE_BY_BINDING = {
    "confirmed_binding": "CONFIRMED_BINDING_EVENT_SUPPORT",
    "confirmed_nonbinding": "CONFIRMED_NONBINDING_EVENT_CONTEXT",
    "confirmed_other_intervention": "OTHER_CONFIRMED_INTERVENTION_CONTEXT",
    "outside_applicable_regime": "OUTSIDE_REGIME_CONTEXT",
    "uncertain": "BINDING_UNCERTAIN_SCREENING_CONTEXT",
}
ANCHOR_FIELDS = (
    "input_reference_date",
    "earliest_public_announcement_date",
    "pro_forma_available_date",
    "implementation_close_date",
    "effective_open_date",
    "secondary_adjustment_date",
    "next_intervention_date",
)
ANTICIPATION_FIELDS = (
    "meeting_in_anticipation_interval",
    "band_20_overlaps_anticipation",
    "band_40_overlaps_anticipation",
    "band_60_overlaps_anticipation",
)
NEXT_INTERVENTION_FIELDS = (
    "meeting_on_or_after_next_intervention",
    "band_20_overlaps_next_intervention",
    "band_40_overlaps_next_intervention",
    "band_60_overlaps_next_intervention",
)
UNRESOLVED_SUPPORT_BLANK_FIELDS = (
    "fomc_evidence_key",
    "fomc_calendar_scope",
    "common_news_group_id",
    "statement_date",
    "temporal_relation",
    "trading_day_distance_signed",
    "calendar_day_distance_signed",
    "nearest_pre",
    "nearest_post",
    "same_day",
    "within_20td",
    "within_40td",
    "within_60td",
    "pre_count_20td",
    "post_count_20td",
    "total_count_20td",
    "pre_count_40td",
    "post_count_40td",
    "total_count_40td",
    "pre_count_60td",
    "post_count_60td",
    "total_count_60td",
    "has_sep",
    "has_press_conference",
    "communication_package",
)


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def split_keys(value: str) -> list[str]:
    return [item.strip() for item in value.split("|") if item.strip()]


def is_true(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def strongest_grade(values: list[str], fallback: str = "U") -> str:
    order = {"A": 4, "B": 3, "C": 2, "U": 1}
    valid = [value for value in values if value in order]
    return max(valid, key=order.get) if valid else fallback


def walk_json_keys(value: Any, path: str = "root") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in PROHIBITED_PUBLIC_JSON_KEYS:
                errors.append(f"prohibited public Stage A JSON key: {path}.{key}")
            errors.extend(walk_json_keys(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(walk_json_keys(child, f"{path}[{index}]"))
    return errors


def load_summary_builder(root: Path):
    module_path = root / "src" / "summarize_gate1.py"
    spec = importlib.util.spec_from_file_location("gate1_summary_validator", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load summary builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_summary


def load_fomc_builder(root: Path):
    module_path = root / "src" / "build_fomc_calendar.py"
    spec = importlib.util.spec_from_file_location("gate1_fomc_validator", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load FOMC builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_package(root: Path, contract_path: Path) -> list[str]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    tables: dict[str, list[dict[str, str]]] = {}

    for directory in contract["required_directories"]:
        if not (root / directory).is_dir():
            errors.append(f"missing required directory: {directory}")

    for document in contract["required_documents"]:
        path = root / document
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            errors.append(f"missing or empty required document: {document}")

    all_csv_contracts = {
        **contract["required_files"],
        **contract.get("required_auxiliary_files", {}),
    }
    for filename, required_columns in all_csv_contracts.items():
        path = root / filename
        if not path.is_file():
            errors.append(f"missing required table: {filename}")
            continue
        raw = path.read_bytes()
        if b"\r" in raw:
            errors.append(f"{filename}: CSV must use LF line endings")
        fields, rows = read_rows(path)
        tables[filename] = rows
        if not fields or fields[0] != "evidence_key":
            errors.append(f"{filename}: evidence_key must be first column")
        missing_columns = [column for column in required_columns if column not in fields]
        if missing_columns:
            errors.append(f"{filename}: missing columns {missing_columns}")
        if not rows:
            errors.append(f"{filename}: contains no audit rows")
            continue

        prefixes = TABLE_PREFIXES.get(filename)
        local_keys: set[str] = set()
        for number, row in enumerate(rows, start=2):
            key = (row.get("evidence_key") or "").strip()
            if not key:
                errors.append(f"{filename}:{number}: blank evidence_key")
            elif key in local_keys:
                errors.append(f"{filename}:{number}: duplicate evidence_key {key}")
            else:
                local_keys.add(key)
            if prefixes and key and not key.startswith(prefixes):
                errors.append(f"{filename}:{number}: invalid evidence_key prefix {key}")
            if "status" in fields and not (row.get("status") or "").strip():
                errors.append(f"{filename}:{number}: blank status")
            for url_field in ("source_url", "statement_url", "event_source_url", "trading_calendar_source_url"):
                if url_field in fields:
                    url = (row.get(url_field) or "").strip()
                    if url and not url.startswith(("https://", "http://")):
                        errors.append(f"{filename}:{number}: malformed {url_field} {url!r}")

    for json_name in contract.get("required_json_documents", []):
        path = root / json_name
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"missing or invalid required JSON: {json_name}: {exc}")

    rules = tables.get("source_and_rule_registry.csv", [])
    events = tables.get("rebalance_event_ledger.csv", [])
    doses = tables.get("assignment_doses_and_evidence.csv", [])
    fomc = tables.get("fomc_calendar.csv", [])
    support = tables.get("assignment_and_fomc_support.csv", [])
    comparisons = tables.get("comparison_and_interference_audit.csv", [])
    stage_a_gaps = tables.get("remaining_input_gaps_stage_a.csv", [])
    stage_e_sources = tables.get("logs/stage_e_sources.csv", [])

    rule_by_key = {row.get("evidence_key", ""): row for row in rules}
    registry_source_pairs = {
        (row.get("source_id", ""), row.get("source_url", "")) for row in rules
    }
    registry_source_ids = {source_id for source_id, _ in registry_source_pairs}
    for row in rules:
        key = row.get("evidence_key", "")
        if row.get("grade_dimension") != "rule/source completeness; never assignment observability":
            errors.append(f"{key}: invalid rule grade_dimension")
        if row.get("rule_source_grade") not in {"A", "B", "U"}:
            errors.append(f"{key}: invalid rule_source_grade")

    event_by_id: dict[str, dict[str, str]] = {}
    for row in events:
        event_id = row.get("event_id", "")
        if not event_id:
            errors.append("event ledger: blank event_id")
            continue
        if event_id in event_by_id:
            errors.append(f"event ledger: duplicate event_id {event_id}")
        event_by_id[event_id] = row
        binding = row.get("binding_status", "")
        if binding not in ALLOWED_BINDING:
            errors.append(f"{event_id}: invalid binding_status {binding!r}")
        if row.get("classification_evidence_grade") not in {"A", "B", "U"}:
            errors.append(f"{event_id}: invalid classification_evidence_grade")
        if row.get("assignment_evidence_grade") not in ALLOWED_GRADES:
            errors.append(f"{event_id}: invalid assignment_evidence_grade")
        if row.get("grade_dimension") != "classification evidence and assignment observability are separate":
            errors.append(f"{event_id}: invalid event grade_dimension")
        if binding == "confirmed_nonbinding" and (
            row.get("classification_evidence_grade") != "B"
            or row.get("assignment_evidence_grade") != "U"
        ):
            errors.append(f"{event_id}: nonbinding event must be classification B / assignment U")
        if binding == "outside_applicable_regime" and (
            row.get("classification_evidence_grade") != "U"
            or row.get("assignment_evidence_grade") != "U"
        ):
            errors.append(f"{event_id}: outside-regime event must use U/U grades")
        rule_keys = split_keys(row.get("rule_evidence_keys", ""))
        if not rule_keys:
            errors.append(f"{event_id}: blank rule_evidence_keys")
        missing = [key for key in rule_keys if key not in rule_by_key]
        if missing:
            errors.append(f"{event_id}: unresolved rule_evidence_keys {missing}")
        elif not any(
            rule_by_key[key].get("regime_id") == row.get("regime_id")
            for key in rule_keys
        ):
            errors.append(f"{event_id}: no referenced rule matches event regime")
        if registry_source_pairs and (
            row.get("source_id", ""), row.get("source_url", "")
        ) not in registry_source_pairs:
            errors.append(f"{event_id}: event source pair not registered")

    for row in events:
        event_id = row.get("event_id", "")
        for linked in split_keys(row.get("interference_event_ids", "")):
            if linked not in event_by_id:
                errors.append(f"{event_id}: unresolved interference event {linked}")

    doses_by_event: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in doses:
        event_id = row.get("event_id", "")
        grade = row.get("evidence_grade", "")
        if grade not in contract["allowed_assignment_grades"]:
            errors.append(f"{row.get('evidence_key')}: invalid evidence_grade {grade!r}")
        if row.get("grade_dimension") and row.get("grade_dimension") != "assignment evidence":
            errors.append(f"{row.get('evidence_key')}: invalid dose grade_dimension")
        if event_id not in event_by_id:
            errors.append(f"dose row: unresolved event_id {event_id}")
            continue
        doses_by_event[event_id].append(row)
        if row.get("grade_dimension") != "assignment evidence":
            errors.append(f"{row.get('evidence_key')}: invalid dose grade_dimension")
        if grade != event_by_id[event_id].get("assignment_evidence_grade"):
            errors.append(f"{row.get('evidence_key')}: dose/event assignment grade mismatch")
        if event_by_id[event_id].get("binding_status") not in {
            "confirmed_binding",
            "confirmed_other_intervention",
        }:
            errors.append(f"{row.get('evidence_key')}: dose attached to non-treatment context")
        pair = (row.get("source_id", ""), row.get("source_url", ""))
        if registry_source_pairs and pair not in registry_source_pairs:
            errors.append(f"{row.get('evidence_key')}: dose source pair not registered")
        for field in (
            "uncapped_source_id",
            "assignment_source_id",
            "etf_holdings_source_id",
            "creation_basket_source_id",
        ):
            source_id = row.get(field, "")
            if source_id and source_id not in registry_source_ids:
                errors.append(f"{row.get('evidence_key')}: unresolved {field} {source_id}")
        if (grade == "A" or is_true(row.get("vector_complete", ""))) and (
            grade != "A" or not is_true(row.get("vector_complete", ""))
        ):
            errors.append(f"{row.get('evidence_key')}: grade A and vector_complete must coincide")

    for event_id, rows in doses_by_event.items():
        if any(is_true(row.get("vector_complete", "")) for row in rows):
            if not all(
                row.get("evidence_grade") == "A"
                and is_true(row.get("vector_complete", ""))
                and row.get("rebalance_change_weight_pct", "").strip()
                for row in rows
            ):
                errors.append(f"{event_id}: complete vector is not wholly grade A with signed doses")

    comparison_by_event: dict[str, dict[str, str]] = {}
    for row in comparisons:
        event_id = row.get("event_id", "")
        if event_id not in event_by_id:
            errors.append(f"comparison row: unresolved event_id {event_id}")
            continue
        if event_id in comparison_by_event:
            errors.append(f"comparison audit: duplicate event_id {event_id}")
        comparison_by_event[event_id] = row
        event_doses = doses_by_event.get(event_id, [])
        counts = Counter(item.get("evidence_grade", "U") for item in event_doses)
        expected_grade = strongest_grade(
            [item.get("evidence_grade", "U") for item in event_doses],
            event_by_id[event_id].get("assignment_evidence_grade", "U"),
        )
        expected_complete = bool(event_doses) and all(
            item.get("evidence_grade") == "A"
            and is_true(item.get("vector_complete", ""))
            for item in event_doses
        )
        expected_signed = sum(
            bool(item.get("rebalance_change_weight_pct", "").strip())
            for item in event_doses
        )
        expected_values = {
            "assignment_rows": len(event_doses),
            "grade_a_rows": counts["A"],
            "grade_b_rows": counts["B"],
            "grade_c_rows": counts["C"],
            "grade_u_rows": counts["U"],
            "signed_dose_rows": expected_signed,
        }
        if row.get("assignment_grade") != expected_grade:
            errors.append(f"{event_id}: comparison assignment grade mismatch")
        if is_true(row.get("assignment_vector_complete", "")) != expected_complete:
            errors.append(f"{event_id}: comparison vector-complete mismatch")
        for field, expected in expected_values.items():
            if row.get(field, "") != str(expected):
                errors.append(f"{event_id}: comparison {field} mismatch")
        if not expected_complete and row.get("dose_information_n", "").strip():
            errors.append(f"{event_id}: dose_information_n requires complete grade-A vector")
    if events and set(comparison_by_event) != set(event_by_id):
        errors.append("comparison audit must contain exactly one row for every event")

    stage_e_pairs = {
        (row.get("source_id", ""), row.get("source_url", ""))
        for row in stage_e_sources
    }
    fomc_by_key = {row.get("evidence_key", ""): row for row in fomc}
    eligible_fomc_keys = {
        row.get("evidence_key", "")
        for row in fomc
        if is_true(row.get("eligible_common_news", ""))
    }
    fomc_ids: set[str] = set()
    for row in fomc:
        meeting_id = row.get("meeting_id", "")
        if not meeting_id or meeting_id in fomc_ids:
            errors.append(f"FOMC calendar: blank/duplicate meeting_id {meeting_id!r}")
        fomc_ids.add(meeting_id)
        if stage_e_pairs and (row.get("source_id", ""), row.get("source_url", "")) not in stage_e_pairs:
            errors.append(f"{meeting_id}: FOMC source pair not in Stage E registry")

    expected_support_keys: dict[tuple[str, str], set[str]] = {}
    try:
        fomc_builder = load_fomc_builder(root)
        eligible_rows = [
            row
            for row in fomc
            if row.get("evidence_key", "") in eligible_fomc_keys
            and row.get("statement_date", "")
        ]
        calendar_dates = [date.fromisoformat(row["statement_date"]) for row in eligible_rows]
        anchor_dates: list[date] = []
        for event in events:
            for anchor in ANCHOR_FIELDS:
                parsed, error = fomc_builder._parse_date(event.get(anchor, ""))
                if parsed is not None and error is None:
                    anchor_dates.append(parsed)
        if calendar_dates and anchor_dates:
            sessions = fomc_builder.trading_sessions(
                min(calendar_dates + anchor_dates) - timedelta(days=400),
                max(calendar_dates + anchor_dates) + timedelta(days=400),
            )
            for event in events:
                event_id = event.get("event_id", "")
                for anchor in ANCHOR_FIELDS:
                    anchor_day, anchor_error = fomc_builder._parse_date(
                        event.get(anchor, "")
                    )
                    if anchor_day is None or anchor_error is not None:
                        continue
                    distances = [
                        (
                            row,
                            date.fromisoformat(row["statement_date"]),
                            fomc_builder.signed_trading_day_distance(
                                anchor_day,
                                date.fromisoformat(row["statement_date"]),
                                sessions,
                            ),
                        )
                        for row in eligible_rows
                    ]
                    pre = [item for item in distances if item[1] < anchor_day]
                    post = [item for item in distances if item[1] > anchor_day]
                    nearest_pre = (
                        min(pre, key=lambda item: (abs(item[2]), -item[1].toordinal()))[
                            0
                        ]["evidence_key"]
                        if pre
                        else ""
                    )
                    nearest_post = (
                        min(post, key=lambda item: (abs(item[2]), item[1]))[0][
                            "evidence_key"
                        ]
                        if post
                        else ""
                    )
                    expected_support_keys[(event_id, anchor)] = {
                        item[0]["evidence_key"]
                        for item in distances
                        if abs(item[2]) <= 60
                        or item[0]["evidence_key"] in {nearest_pre, nearest_post}
                        or item[1] == anchor_day
                    }
    except Exception as exc:
        errors.append(f"could not reconstruct expected FOMC support sets: {exc}")

    support_groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in support:
        event_id = row.get("event_id", "")
        event = event_by_id.get(event_id)
        if event is None:
            errors.append(f"support row: unresolved event_id {event_id}")
            continue
        anchor = row.get("anchor", "")
        support_groups[(event_id, anchor)].append(row)
        if anchor not in ANCHOR_FIELDS:
            errors.append(f"{row.get('evidence_key')}: invalid support anchor {anchor!r}")
        elif row.get("anchor_date", "") != event.get(anchor, ""):
            errors.append(f"{row.get('evidence_key')}: anchor_date does not match event anchor")
        copied_fields = {
            "event_evidence_key": "evidence_key",
            "event_binding_status": "binding_status",
            "event_status": "status",
            "event_classification_evidence_grade": "classification_evidence_grade",
            "event_assignment_evidence_grade": "assignment_evidence_grade",
            "event_assignment_observability": "assignment_observability",
            "event_rule_evidence_keys": "rule_evidence_keys",
            "event_interference_event_ids": "interference_event_ids",
            "event_group_id": "event_group_id",
            "common_rebalance_group_id": "event_group_id",
            "comparison_id": "comparison_id",
            "event_source_id": "source_id",
            "event_source_url": "source_url",
        }
        for support_field, event_field in copied_fields.items():
            if row.get(support_field, "") != event.get(event_field, ""):
                errors.append(f"{row.get('evidence_key')}: copied {support_field} mismatch")
        if row.get("basket_assignment_id") != event_id:
            errors.append(f"{row.get('evidence_key')}: basket_assignment_id mismatch")
        expected_role = ROLE_BY_BINDING.get(event.get("binding_status", ""))
        if row.get("support_role") != expected_role:
            errors.append(f"{row.get('evidence_key')}: support_role mismatch")
        if stage_e_pairs and (
            row.get("trading_calendar_source_id", ""),
            row.get("trading_calendar_source_url", ""),
        ) not in stage_e_pairs:
            errors.append(f"{row.get('evidence_key')}: trading-calendar source not registered")

        if row.get("meeting_id") == "UNRESOLVED":
            if row.get("status") != "UNRESOLVED_ANCHOR" or row.get("anchor_date"):
                errors.append(f"{row.get('evidence_key')}: malformed unresolved anchor row")
            if any(row.get(field, "").strip() for field in UNRESOLVED_SUPPORT_BLANK_FIELDS):
                errors.append(f"{row.get('evidence_key')}: unresolved row has computed FOMC fields")
            if (row.get("source_id"), row.get("source_url")) != (
                event.get("source_id"),
                event.get("source_url"),
            ):
                errors.append(f"{row.get('evidence_key')}: unresolved row must retain event source")
        else:
            fomc_row = fomc_by_key.get(row.get("fomc_evidence_key", ""))
            if fomc_row is None:
                errors.append(f"{row.get('evidence_key')}: unresolved FOMC evidence key")
            else:
                expected_fomc = {
                    "meeting_id": "meeting_id",
                    "statement_date": "statement_date",
                    "fomc_calendar_scope": "calendar_scope",
                    "has_sep": "has_sep",
                    "has_press_conference": "has_press_conference",
                    "communication_package": "communication_package",
                    "source_id": "source_id",
                    "source_url": "source_url",
                }
                for support_field, fomc_field in expected_fomc.items():
                    if row.get(support_field, "") != fomc_row.get(fomc_field, ""):
                        errors.append(f"{row.get('evidence_key')}: FOMC {support_field} mismatch")
                if not is_true(fomc_row.get("eligible_common_news", "")):
                    errors.append(f"{row.get('evidence_key')}: support references ineligible FOMC row")
        if row.get("anticipation_window_status") != "VALID_DOCUMENTED_STAGE_DATES" and any(
            row.get(field, "").strip() for field in ANTICIPATION_FIELDS
        ):
            errors.append(f"{row.get('evidence_key')}: unknown anticipation fields must be blank")
        if row.get("next_intervention_status") != "VALID_FUTURE_DATE" and any(
            row.get(field, "").strip() for field in NEXT_INTERVENTION_FIELDS
        ):
            errors.append(f"{row.get('evidence_key')}: unknown next-intervention fields must be blank")

    if support and events:
        for event_id, event in event_by_id.items():
            for anchor in ANCHOR_FIELDS:
                rows = support_groups.get((event_id, anchor), [])
                if not rows:
                    errors.append(f"{event_id}: missing support anchor group {anchor}")
                    continue
                unresolved = [row for row in rows if row.get("meeting_id") == "UNRESOLVED"]
                if event.get(anchor, "").strip():
                    if unresolved:
                        errors.append(f"{event_id}:{anchor}: dated anchor has unresolved support row")
                    observed_fomc_keys = [
                        row.get("fomc_evidence_key", "")
                        for row in rows
                        if row.get("meeting_id") != "UNRESOLVED"
                    ]
                    expected_keys = expected_support_keys.get((event_id, anchor))
                    if expected_keys is None:
                        errors.append(
                            f"{event_id}:{anchor}: expected support set was not reconstructed"
                        )
                    elif (
                        len(observed_fomc_keys) != len(expected_keys)
                        or len(set(observed_fomc_keys)) != len(observed_fomc_keys)
                        or set(observed_fomc_keys) != expected_keys
                    ):
                        errors.append(
                            f"{event_id}:{anchor}: support FOMC set must equal "
                            "the eligible ±60-session/nearest support set exactly once"
                        )
                elif len(rows) != 1 or len(unresolved) != 1:
                    errors.append(f"{event_id}:{anchor}: blank anchor must have one unresolved row")

    for row in tables.get("remaining_input_gaps.csv", []):
        for field in ("blocks_gate1_assignment", "blocks_future_measurement"):
            if row.get(field) not in {"yes", "no"}:
                errors.append(f"{row.get('evidence_key')}: {field} must be yes or no")
        if row.get("evidence_key", "").startswith("GAPA:") and row.get(
            "source_locator", ""
        ) != f"SCC_PRIVATE_LINEAGE:{row.get('evidence_key')}":
            errors.append(
                f"{row.get('evidence_key')}: integrated Stage A gap locator not redacted"
            )

    for row in stage_a_gaps:
        if row.get("source_locator", "") != f"SCC_PRIVATE_LINEAGE:{row.get('evidence_key')}":
            errors.append(f"{row.get('evidence_key')}: public Stage A gap locator not redacted")

    catalog = tables.get("local_data_catalog.csv", [])
    for row in catalog:
        if not row.get("source_locator", "").startswith("SCC_PRIVATE_LINEAGE:"):
            errors.append(f"{row.get('evidence_key')}: public catalog locator not redacted")
        if row.get("schema_hash") != "WITHHELD_LICENSED_SCHEMA_FINGERPRINT":
            errors.append(f"{row.get('evidence_key')}: public schema fingerprint not redacted")
    for row in tables.get("fund_identifier_and_coverage_audit.csv", []):
        for field in ("crsp_fundno", "crsp_portno", "security_permno", "fund_cusip8", "fund_ncusip"):
            if row.get(field) != "WITHHELD_LICENSED_IDENTIFIER":
                errors.append(f"{row.get('evidence_key')}: public {field} not redacted")
        if not row.get("source_locator", "").startswith("SCC_PRIVATE_LINEAGE:"):
            errors.append(f"{row.get('evidence_key')}: public fund locator not redacted")

    stage_a_path = root / "logs" / "stage_a_evidence.json"
    if stage_a_path.is_file():
        stage_a = json.loads(stage_a_path.read_text(encoding="utf-8"))
        errors.extend(walk_json_keys(stage_a))
        if stage_a.get("run", {}).get("output_profile") != "PUBLIC_AGGREGATE_REDACTED":
            errors.append("Stage A evidence JSON: wrong public output profile")
        if stage_a.get("method_notes", {}).get("raw_rows_exported") is not False:
            errors.append("Stage A evidence JSON: raw_rows_exported must be false")
        if "read-only" not in stage_a.get("run", {}).get("archive_write_policy", ""):
            errors.append("Stage A evidence JSON: archive policy must be read-only")

    summary_path = root / "logs" / "gate1_summary.json"
    if summary_path.is_file() and (root / "src" / "summarize_gate1.py").is_file():
        recorded = json.loads(summary_path.read_text(encoding="utf-8"))
        try:
            rebuilt = load_summary_builder(root)(root)
            if recorded != rebuilt:
                errors.append("logs/gate1_summary.json is stale relative to source tables")
        except Exception as exc:  # validation must fail closed with a useful message
            errors.append(f"could not recompute Gate 1 summary: {exc}")

    decision_path = root / "FINAL_DECISION.md"
    if decision_path.is_file():
        decision = decision_path.read_text(encoding="utf-8")
        selected = [
            recommendation
            for recommendation in contract["allowed_recommendations"]
            if recommendation in decision
        ]
        if len(selected) != 1:
            errors.append(
                "FINAL_DECISION.md must contain exactly one permitted recommendation; "
                f"found {len(selected)}"
            )

    for path in root.rglob("*"):
        if path.is_dir():
            if path.name == "private_lineage":
                errors.append(f"private lineage directory present: {path.relative_to(root)}")
            continue
        if ".git" in path.parts:
            continue
        relative = path.relative_to(root)
        if path.suffix.lower() in RAW_SUFFIXES:
            errors.append(f"raw/private data artifact present: {relative}")
        if any(pattern.search(path.name) for pattern in PRIVATE_NAME_PATTERNS):
            errors.append(f"private lineage artifact present: {relative}")
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                errors.append(f"possible credential material in {relative}")
            if pattern.search(str(relative)):
                errors.append(f"possible credential material in filename {relative}")
        path_scan_content = content
        if relative.as_posix() == "docs/OPUS_5_HIGH_REVIEW_PACKAGE.md":
            path_scan_content = content.split(
                "## Appendix A — Upstream research-agent prompt (verbatim)", 1
            )[0]
        for pattern in RUNTIME_PATH_PATTERNS:
            if pattern.search(path_scan_content):
                errors.append(f"possible account/runtime path in {relative}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--contract", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    contract = args.contract or root / "config" / "output_contract.json"
    errors = validate_package(root, contract)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"PASS: Gate 1 package contract validated at {root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
