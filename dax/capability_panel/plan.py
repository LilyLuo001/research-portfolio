"""Task-ID-only W4 plan construction with W3, duration, and availability gates."""

from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import re
from collections.abc import Iterable, Mapping


GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
PERTURBATIONS = ("baseline", "paraphrase", "reformat", "distractor")
FORBIDDEN_OUTPUT_KEYS = {
    "task_text", "prompt", "raw_prompt", "response", "raw_response",
    "rationale", "grader_rationale", "outcome",
}


class PlanError(ValueError):
    pass


def _sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_task_ids(mapping_csv: pathlib.Path) -> list[str]:
    """Read IDs only. GDPval/O*NET text never enters the returned object."""

    with mapping_csv.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or ())
        if "gdpval_task_id" not in fields:
            raise PlanError("W3 mapping lacks gdpval_task_id")
        forbidden = fields.intersection(FORBIDDEN_OUTPUT_KEYS)
        if forbidden:
            raise PlanError(f"W3 task-ID input contains forbidden private columns: {sorted(forbidden)}")
        task_ids = {
            str(row.get("gdpval_task_id", "")).strip()
            for row in reader
            if str(row.get("gdpval_task_id", "")).strip()
        }
    if not task_ids:
        raise PlanError("W3 mapping contains no eligible GDPval task IDs")
    return sorted(task_ids)


def validate_w3_receipt(
    receipt: Mapping[str, object],
    *,
    expected_commit: str,
    mapping_path: pathlib.Path | None = None,
) -> None:
    if not GIT_SHA.fullmatch(expected_commit):
        raise PlanError("expected W3 commit must be an exact 40-character SHA")
    if receipt.get("mapping_commit") != expected_commit:
        raise PlanError("W3 receipt commit does not match the fetched exact commit")
    if receipt.get("license_guard_status") != "PASS_TASK_IDS_ONLY":
        raise PlanError("W3 license guard is not PASS_TASK_IDS_ONLY")
    if receipt.get("adjudication_status") != "PASS":
        raise PlanError("W3 adjudication receipt is not PASS")
    digest = str(receipt.get("mapping_sha256", ""))
    if not SHA256.fullmatch(digest):
        raise PlanError("W3 receipt lacks a valid mapping SHA-256")
    count = receipt.get("mapping_row_count")
    if not isinstance(count, int) or count < 1:
        raise PlanError("W3 receipt lacks a positive mapping row count")
    if mapping_path and _sha256_file(mapping_path) != digest:
        raise PlanError("W3 mapping bytes do not match its receipt")


def duration_coverage_from_receipt(receipt: Mapping[str, object]) -> dict[str, object]:
    total = receipt.get("n_unique_task_ids")
    if not isinstance(total, int) or total < 0:
        raise PlanError("duration source receipt lacks n_unique_task_ids")
    fields = receipt.get("task_completion_duration_fields")
    if not isinstance(fields, list):
        raise PlanError("duration source receipt has malformed duration fields")
    status = str(receipt.get("task_completion_duration_status", ""))
    covered = total if fields and status == "VERIFIED" else 0
    return {
        "source_status": status,
        "task_ids": total,
        "covered_task_ids": covered,
        "missing_task_ids": total - covered,
        "coverage_rate": 0.0 if total == 0 else covered / total,
        "duration_fields": list(fields),
        "blocking_rule": "missing duration blocks the row; no inference or constant fill",
    }


def stable_item_id(parts: Iterable[object]) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_run_plan(
    task_ids: Iterable[str],
    registry: Mapping[str, object],
    availability_receipt: Mapping[str, object],
    *,
    repetitions: int,
    mapping_commit: str,
    mapping_receipt_sha256: str,
    duration_by_task: Mapping[str, Mapping[str, object]] | None = None,
) -> list[dict[str, object]]:
    if not isinstance(repetitions, int) or repetitions < 1:
        raise PlanError("repetitions must be a positive signed integer")
    if not GIT_SHA.fullmatch(mapping_commit):
        raise PlanError("mapping_commit must be an exact 40-character SHA")
    if not SHA256.fullmatch(mapping_receipt_sha256):
        raise PlanError("mapping_receipt_sha256 must be a lowercase SHA-256")
    tasks = sorted({str(task).strip() for task in task_ids if str(task).strip()})
    if not tasks:
        raise PlanError("run plan requires at least one task ID")
    availability = {
        (str(row["event_id"]), str(row["source_model_id"])): row
        for row in availability_receipt.get("matrix", [])  # type: ignore[union-attr]
    }
    plan: list[dict[str, object]] = []
    for model in registry.get("models", []):  # type: ignore[union-attr]
        event_id = str(model["event_id"])
        source_model = str(model["source_model_id"])
        matrix = availability.get((event_id, source_model))
        if matrix is None:
            raise PlanError(f"availability receipt missing {(event_id, source_model)}")
        if model["status"] == "excluded_binding":
            continue
        for task_id in tasks:
            duration = None if duration_by_task is None else duration_by_task.get(task_id)
            duration_verified = bool(duration and duration.get("status") == "verified")
            for perturbation in PERTURBATIONS:
                variant = "average_case" if perturbation == "baseline" else "perturbation_robust"
                for repetition in range(1, repetitions + 1):
                    availability_status = str(matrix["availability_status"])
                    blockers: list[str] = []
                    if availability_status != "account_available" and model["provider"] == "openai":
                        blockers.append(availability_status)
                    if model["provider"] != "openai" and model["status"] != "account_available":
                        blockers.append(str(model["status"]))
                    # Duration no longer blocks CAPTURE (amendment section 3).
                    # It blocks scoring, which assert_scoreable enforces.
                    scoring_blockers: list[str] = []
                    if not duration_verified:
                        scoring_blockers.append("deferred_missing_task_duration")
                    item = {
                        "item_id": stable_item_id((
                            mapping_commit, event_id, source_model, task_id,
                            perturbation, repetition,
                        )),
                        "task_id": task_id,
                        "event_id": event_id,
                        "event_date": model["event_date"],
                        "source_model_id": source_model,
                        "measurement_model_id": model.get("measurement_model_id"),
                        "measurement_route": model["measurement_route"],
                        "provider": model["provider"],
                        "endpoint_kind": model.get("endpoint_kind"),
                        "supports_seed": bool(model.get("supports_seed")),
                        "supports_temperature": bool(model.get("supports_temperature", True)),
                        "max_output_parameter": model.get("max_output_parameter", "max_tokens"),
                        "approved_rule_id": model.get("approved_rule_id"),
                        "perturbation_id": perturbation,
                        "pi_variant": variant,
                        "repetition_id": repetition,
                        "deterministic_seed": int(stable_item_id((task_id, source_model, perturbation, repetition))[:8], 16),
                        "mapping_commit": mapping_commit,
                        "mapping_receipt_sha256": mapping_receipt_sha256,
                        "task_duration_status": "verified" if duration_verified else "deferred_scoring",
                        "scoring_status": "scoreable" if duration_verified else "deferred_missing_task_duration",
                        "scoring_blockers": scoring_blockers,
                        "task_duration_value": duration.get("value") if duration_verified else None,
                        "task_duration_unit": duration.get("unit") if duration_verified else None,
                        "task_duration_source": duration.get("source", "") if duration_verified else "",
                        "plan_status": "eligible" if not blockers else "blocked",
                        "blockers": sorted(set(blockers)),
                    }
                    if FORBIDDEN_OUTPUT_KEYS.intersection(item):
                        raise PlanError("private text leaked into the run plan")
                    plan.append(item)
    return plan


def sanitized_plan_receipt(plan: Iterable[Mapping[str, object]]) -> dict[str, object]:
    rows = list(plan)
    states: dict[str, int] = {}
    blocker_counts: dict[str, int] = {}
    tasks = set()
    models = set()
    for row in rows:
        states[str(row["plan_status"])] = states.get(str(row["plan_status"]), 0) + 1
        tasks.add(str(row["task_id"]))
        models.add((str(row["event_id"]), str(row["source_model_id"])))
        for blocker in row.get("blockers", []):  # type: ignore[union-attr]
            blocker_counts[str(blocker)] = blocker_counts.get(str(blocker), 0) + 1
    return {
        "receipt_version": "dax-w4-run-plan-v1",
        "run_plan_rows": len(rows),
        "unique_task_ids": len(tasks),
        "event_model_rows": len(models),
        "status_counts": states,
        "blocker_counts": blocker_counts,
        "contains_task_text": False,
        "contains_prompt_text": False,
        "contains_outcomes": False,
    }


def write_jsonl_private(path: pathlib.Path, rows: Iterable[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            if FORBIDDEN_OUTPUT_KEYS.intersection(str(key).lower() for key in row):
                raise PlanError("private text fields are forbidden in the task-ID run plan")
            handle.write(json.dumps(dict(row), sort_keys=True, separators=(",", ":")) + "\n")
    path.chmod(0o600)
