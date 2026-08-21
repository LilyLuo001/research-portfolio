"""Fail-closed validation for frozen GDPval human-duration metadata.

Duration is an input to the adoption-cost inequality, not something the W4
model runner may infer.  This validator accepts task-specific observed timings
or a completed multi-annotator protocol.  It rejects constants, occupation
averages, and LLM-only guesses.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence


PROTOCOL_VERSION = "DAX-TD-v1"
ALLOWED_SOURCE_TYPES = {"observed_task_timing", "expert_annotation"}
MIN_ANNOTATORS = 3
MIN_OBSERVED_COMPLETIONS = 3
MIN_ADJACENT_BIN_AGREEMENT = 0.80


class DurationGateError(ValueError):
    pass


def validate_duration_rows(
    rows: Iterable[dict[str, object]],
    *,
    expected_task_ids: Sequence[str],
) -> dict[str, object]:
    expected = set(expected_task_ids)
    if len(expected) != len(expected_task_ids) or not expected:
        raise DurationGateError("expected task IDs must be unique and non-empty")

    records = list(rows)
    by_id: dict[str, dict[str, object]] = {}
    errors: list[str] = []
    for record in records:
        task_id = str(record.get("gdpval_task_id", "")).strip()
        if not task_id:
            errors.append("row with blank gdpval_task_id")
            continue
        if task_id in by_id:
            errors.append(f"duplicate task row: {task_id}")
            continue
        by_id[task_id] = record

    missing = sorted(expected - set(by_id))
    extra = sorted(set(by_id) - expected)
    if missing:
        errors.append(f"missing task rows: {missing}")
    if extra:
        errors.append(f"unexpected task rows: {extra}")

    for task_id in sorted(expected & set(by_id)):
        record = by_id[task_id]
        try:
            lower = float(record["duration_lower_minutes"])
            median = float(record["duration_median_minutes"])
            upper = float(record["duration_upper_minutes"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"{task_id}: invalid duration bounds")
            continue
        if not (0 < lower <= median <= upper):
            errors.append(f"{task_id}: require 0 < lower <= median <= upper")

        source_type = str(record.get("source_type", ""))
        if source_type not in ALLOWED_SOURCE_TYPES:
            errors.append(f"{task_id}: prohibited or unknown source_type {source_type!r}")
        if str(record.get("protocol_version", "")) != PROTOCOL_VERSION:
            errors.append(f"{task_id}: protocol version mismatch")
        if str(record.get("adjudication_status", "")).upper() != "PASS":
            errors.append(f"{task_id}: adjudication is not PASS")
        if not str(record.get("source_locator", "")).strip():
            errors.append(f"{task_id}: missing source locator")

        if source_type == "expert_annotation":
            try:
                n_annotators = int(record.get("n_independent_annotators", 0))
                agreement = float(record.get("adjacent_bin_agreement", 0))
            except (TypeError, ValueError):
                n_annotators, agreement = 0, 0
            if n_annotators < MIN_ANNOTATORS:
                errors.append(f"{task_id}: fewer than {MIN_ANNOTATORS} annotators")
            if agreement < MIN_ADJACENT_BIN_AGREEMENT:
                errors.append(
                    f"{task_id}: adjacent-bin agreement below "
                    f"{MIN_ADJACENT_BIN_AGREEMENT:.2f}"
                )
        elif source_type == "observed_task_timing":
            try:
                n_observed = int(record.get("n_observed_completions", 0))
            except (TypeError, ValueError):
                n_observed = 0
            if n_observed < MIN_OBSERVED_COMPLETIONS:
                errors.append(
                    f"{task_id}: fewer than {MIN_OBSERVED_COMPLETIONS} observed completions"
                )

    return {
        "status": "PASS" if not errors else "BLOCKED",
        "expected_tasks": len(expected),
        "received_tasks": len(by_id),
        "errors": errors,
        "protocol_version": PROTOCOL_VERSION,
    }


def assert_duration_gate(
    rows: Iterable[dict[str, object]],
    *,
    expected_task_ids: Sequence[str],
) -> dict[str, object]:
    report = validate_duration_rows(rows, expected_task_ids=expected_task_ids)
    if report["status"] != "PASS":
        raise DurationGateError("duration gate blocked: " + "; ".join(report["errors"]))
    return report
