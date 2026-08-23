"""Fail-closed contracts for the prospective O*NET-aligned v3 benchmark.

This module defines metadata checks only.  It does not construct benchmark
items, call a model, score an item, open Mapping A v2 labels, or touch DAX
outcomes.  Numerical sampling and scoring choices remain PI decisions.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping


EVALUABILITY = {
    "directly_executable_digital",
    "executable_with_provided_files_data",
    "executable_with_simulated_construct_valid_inputs",
    "requires_unavailable_proprietary_system",
    "requires_physical_world_action",
    "requires_interpersonal_interaction",
    "otherwise_non_evaluable",
}

EVALUABLE = {
    "directly_executable_digital",
    "executable_with_provided_files_data",
    "executable_with_simulated_construct_valid_inputs",
}

REQUIRED_DEFINITION_FIELDS = {
    "benchmark_item_id",
    "source_onet_task_id",
    "occupation_task_family",
    "required_inputs",
    "allowed_tools",
    "required_deliverable",
    "completion_criterion",
    "scoring_rubric",
    "failure_criterion",
    "review_requirements",
    "professional_context_assumptions",
    "evaluable_class",
    "definition_version",
}

RELEASE_DEFINITION_FIELDS = (
    REQUIRED_DEFINITION_FIELDS.difference({"source_onet_task_id"})
    | {"source_task_ref_hash"}
)

MODEL_RESULT_FIELDS = {
    "model_id",
    "model_output",
    "model_score",
    "model_success",
    "input_tokens",
    "output_tokens",
    "latency_ms",
    "realized_cost_usd",
}


class BenchmarkContractError(ValueError):
    """A proposed item or result violates the prospective v3 boundary."""


def _nonblank(record: Mapping[str, object], key: str) -> object:
    value = record.get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise BenchmarkContractError(f"blank required field {key}")
    return value


def definition_sha256(definition: Mapping[str, object]) -> str:
    """Hash a task definition without importing a model result."""

    import json

    forbidden = sorted(MODEL_RESULT_FIELDS.intersection(definition))
    if forbidden:
        raise BenchmarkContractError(
            f"task definition contains model-evaluation fields: {forbidden}"
        )
    encoded = json.dumps(definition, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate_task_definition(
    definition: Mapping[str, object], *, release_path: bool = False
) -> None:
    """Validate the task-definition side of the benchmark freeze.

    The O*NET identifier is required in the private definition and forbidden in
    a public/release-path representation.  Release artifacts should carry only
    a salted or keyed reference produced outside this repository.
    """

    required = RELEASE_DEFINITION_FIELDS if release_path else REQUIRED_DEFINITION_FIELDS
    missing = sorted(required.difference(definition))
    if missing:
        raise BenchmarkContractError(f"missing definition fields: {missing}")
    for key in required:
        _nonblank(definition, key)
    if release_path and "source_onet_task_id" in definition:
        raise BenchmarkContractError("private O*NET task identifier on release path")
    forbidden = sorted(MODEL_RESULT_FIELDS.intersection(definition))
    if forbidden:
        raise BenchmarkContractError(
            f"task definition contains model-evaluation fields: {forbidden}"
        )
    evaluability = str(definition["evaluable_class"])
    if evaluability not in EVALUABILITY:
        raise BenchmarkContractError(f"unknown evaluability class {evaluability!r}")
    rubric = definition["scoring_rubric"]
    if not isinstance(rubric, (list, tuple)) or not rubric:
        raise BenchmarkContractError("scoring_rubric must be a nonempty list")
    for list_key in ("required_inputs", "allowed_tools", "review_requirements"):
        if not isinstance(definition[list_key], (list, tuple)):
            raise BenchmarkContractError(f"{list_key} must be a list")


def validate_model_result(
    result: Mapping[str, object], *, frozen_definition_sha256: str, evaluable_class: str
) -> None:
    """Require a frozen definition and prevent zero-filling non-evaluable items."""

    observed_hash = str(_nonblank(result, "definition_sha256"))
    if observed_hash != frozen_definition_sha256:
        raise BenchmarkContractError("model result does not match frozen definition")
    if evaluable_class not in EVALUABILITY:
        raise BenchmarkContractError(f"unknown evaluability class {evaluable_class!r}")
    status = str(_nonblank(result, "evaluation_status"))
    if evaluable_class not in EVALUABLE:
        if status != "not_evaluable":
            raise BenchmarkContractError("non-evaluable task must stay not_evaluable")
        if result.get("model_score") is not None or result.get("model_success") is not None:
            raise BenchmarkContractError("non-evaluable task cannot be zero-scored or imputed")
        return
    if status not in {"captured", "capture_failed"}:
        raise BenchmarkContractError("evaluable task requires captured/capture_failed status")
    if status == "capture_failed":
        if result.get("model_score") is not None or result.get("model_success") is not None:
            raise BenchmarkContractError("failed capture cannot be score-filled")
        return
    if not isinstance(result.get("model_success"), bool):
        raise BenchmarkContractError("captured result requires boolean model_success")
    try:
        score = float(result["model_score"])
    except (KeyError, TypeError, ValueError) as error:
        raise BenchmarkContractError("captured result requires numeric model_score") from error
    if not math.isfinite(score) or not 0 <= score <= 1:
        raise BenchmarkContractError("model_score must lie in [0, 1]")


def non_evaluable_mass_bounds(
    *, identified_crossing_mass: float, non_evaluable_mass: float
) -> dict[str, float | None | str]:
    """Return sharp ignorance bounds; never invent a center for missing mass."""

    values = (identified_crossing_mass, non_evaluable_mass)
    if any(not math.isfinite(float(value)) or value < 0 for value in values):
        raise BenchmarkContractError("mass inputs must be finite and nonnegative")
    lower = float(identified_crossing_mass)
    upper = lower + float(non_evaluable_mass)
    if upper > 1 + 1e-12:
        raise BenchmarkContractError("crossing plus non-evaluable mass cannot exceed one")
    return {
        "lower": lower,
        "center": None,
        "upper": min(1.0, upper),
        "center_status": "UNIDENTIFIED_REQUIRES_SEPARATE_SIGNED_MODEL",
    }
