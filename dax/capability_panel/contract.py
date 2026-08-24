"""Strict private-row contract and hard token-cost accounting for DAX W4."""

from __future__ import annotations

import datetime as dt
import hashlib
import math
import re
from collections.abc import Mapping


SHA256 = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
DATED_MODEL = re.compile(r"(?:-\d{4}-\d{2}-\d{2}|-\d{4}|-\d{3,4})$")
PI_VARIANTS = {"average_case", "perturbation_robust"}
ROUTES = {"direct", "approved_open_weight_standin", "blocked_alias"}
FAILURE_STATUSES = {"none", "measurement_failed", "blocked"}
AVAILABILITY = {
    "account_available",
    "account_unavailable",
    "unprobed_missing_key",
    "excluded_binding",
    "blocked_missing_approved_snapshot_rule",
    "standin_provider_unconfigured",
}
FORBIDDEN_KEYS = {
    "task_text",
    "prompt",
    "raw_prompt",
    "response",
    "raw_response",
    "outcome_text",
    "grader_rationale",
}


class ContractError(ValueError):
    """A row cannot enter the W4 private capability/cost panel."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _text(row: Mapping[str, object], key: str) -> str:
    value = str(row.get(key, "")).strip()
    if not value:
        raise ContractError(f"blank required field {key}")
    return value


def _number(row: Mapping[str, object], key: str, *, minimum: float = 0.0) -> float:
    try:
        value = float(row[key])
    except (KeyError, TypeError, ValueError) as error:
        raise ContractError(f"invalid numeric field {key}") from error
    if not math.isfinite(value) or value < minimum:
        raise ContractError(f"{key} must be finite and >= {minimum}")
    return value


def _integer(row: Mapping[str, object], key: str, *, minimum: int = 0) -> int:
    value = _number(row, key, minimum=minimum)
    if not value.is_integer():
        raise ContractError(f"{key} must be an integer")
    return int(value)


def _hash(row: Mapping[str, object], key: str, *, nullable: bool = False) -> str | None:
    raw = row.get(key)
    if nullable and raw in (None, ""):
        return None
    value = _text(row, key)
    if not SHA256.fullmatch(value):
        raise ContractError(f"{key} must be a lowercase SHA-256")
    return value


def _iso_date(row: Mapping[str, object], key: str) -> str:
    value = _text(row, key)
    try:
        dt.date.fromisoformat(value)
    except ValueError as error:
        raise ContractError(f"{key} must be an ISO-8601 date") from error
    return value


def _iso_timestamp(row: Mapping[str, object], key: str, *, nullable: bool = False) -> str | None:
    raw = row.get(key)
    if nullable and raw in (None, ""):
        return None
    value = _text(row, key)
    try:
        dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ContractError(f"{key} must be an ISO-8601 timestamp") from error
    return value


def metered_cost_usd(
    *,
    input_tokens: int,
    cached_input_tokens: int,
    output_tokens: int,
    reasoning_tokens: int,
    input_usd_per_1m: float,
    cached_input_usd_per_1m: float,
    output_usd_per_1m: float,
) -> float:
    """Cost one completed call without double-counting reasoning tokens.

    OpenAI Responses usage includes reasoning tokens inside output_tokens.
    Cached input is a subset of input_tokens, so ordinary input is the
    non-cached remainder.
    """

    counts = (input_tokens, cached_input_tokens, output_tokens, reasoning_tokens)
    if any(not isinstance(value, int) or value < 0 for value in counts):
        raise ContractError("token counts must be nonnegative integers")
    if cached_input_tokens > input_tokens:
        raise ContractError("cached_input_tokens cannot exceed input_tokens")
    if reasoning_tokens > output_tokens:
        raise ContractError("reasoning_tokens cannot exceed output_tokens")
    rates = (input_usd_per_1m, cached_input_usd_per_1m, output_usd_per_1m)
    if any(not math.isfinite(float(value)) or float(value) < 0 for value in rates):
        raise ContractError("price rates must be finite and nonnegative")
    ordinary = input_tokens - cached_input_tokens
    return (
        ordinary * input_usd_per_1m
        + cached_input_tokens * cached_input_usd_per_1m
        + output_tokens * output_usd_per_1m
    ) / 1_000_000.0


def wilson_95(successes: int, trials: int) -> tuple[float, float, float]:
    if not isinstance(successes, int) or not isinstance(trials, int):
        raise ContractError("successes and trials must be integers")
    if trials < 1 or successes < 0 or successes > trials:
        raise ContractError("require 0 <= successes <= trials and trials >= 1")
    z = 1.959963984540054
    p = successes / trials
    denominator = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / denominator
    half = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denominator
    return p, max(0.0, center - half), min(1.0, center + half)


def validate_row(row: Mapping[str, object], *, tolerance: float = 1e-12) -> None:
    forbidden = sorted(key for key in row if str(key).lower() in FORBIDDEN_KEYS)
    if forbidden:
        raise ContractError(f"plaintext/private fields forbidden in panel row: {forbidden}")

    failure = _text(row, "failure_status")
    if failure not in FAILURE_STATUSES:
        raise ContractError(f"unsupported failure_status {failure!r}")
    _text(row, "failure_code")
    if failure != "none" and row.get("success"):
        raise ContractError("failed or blocked rows cannot be successful")

    _text(row, "task_id")
    _text(row, "event_id")
    _iso_date(row, "event_date")
    requested_raw = row.get("model_requested")
    requested = "" if requested_raw is None else str(requested_raw).strip()
    returned_raw = row.get("model_returned")
    returned = "" if returned_raw is None else str(returned_raw).strip()
    route = _text(row, "measurement_route")
    if route not in ROUTES:
        raise ContractError(f"unsupported measurement_route {route!r}")
    source_model = _text(row, "source_model_id")
    rule_raw = row.get("approved_rule_id")
    rule = "" if rule_raw is None else str(rule_raw).strip()
    if source_model == "gpt-4.5-preview" or requested == "gpt-4.5-preview":
        raise ContractError("gpt-4.5-preview is bindingly excluded")
    if route == "blocked_alias":
        if failure != "blocked":
            raise ContractError("blocked alias requires failure_status blocked")
        if requested_raw is not None or rule_raw is not None:
            raise ContractError("blocked alias cannot claim a requested model or approved rule")
    elif not requested or not rule:
        raise ContractError("measurement route requires model_requested and approved_rule_id")
    elif route == "direct":
        if requested != source_model:
            raise ContractError("direct measurement cannot substitute another model")
        if not DATED_MODEL.search(requested) and "ALIAS" not in rule:
            raise ContractError("undated direct alias requires an approved alias rule")
    elif requested == source_model:
        raise ContractError("stand-in route must name a distinct measurement model")
    if failure == "none" and not returned:
        raise ContractError("provider-returned model identifier is required")
    if failure != "none" and ("model_returned" not in row or returned_raw is not None):
        raise ContractError("failed/blocked model_returned must be explicitly null")

    _iso_date(row, "model_vintage_date")
    perturbation = _text(row, "perturbation_id")
    _integer(row, "repetition_id", minimum=1)
    seed_requested = row.get("seed_requested")
    if seed_requested is not None and not isinstance(seed_requested, int):
        raise ContractError("seed_requested must be an integer or null")
    if not isinstance(row.get("seed_applied"), bool):
        raise ContractError("seed_applied must be boolean")
    if row.get("seed_applied") and seed_requested is None:
        raise ContractError("seed_applied requires seed_requested")
    _text(row, "correctness_measure")
    if not isinstance(row.get("success"), bool):
        raise ContractError("success must be boolean")

    variant = _text(row, "pi_variant")
    if variant not in PI_VARIANTS:
        raise ContractError(f"unsupported pi_variant {variant!r}")
    if variant == "average_case" and perturbation != "baseline":
        raise ContractError("average_case rows must use the baseline perturbation")
    if variant == "perturbation_robust" and perturbation == "baseline":
        raise ContractError("perturbation_robust rows must identify a perturbation")
    successes = _integer(row, "pi_successes")
    trials = _integer(row, "pi_trials")
    if failure == "none":
        if trials < 1:
            raise ContractError("captured pi_trials must be positive")
        expected_pi, _, _ = wilson_95(successes, trials)
        pi = _number(row, "pi")
        lower = _number(row, "pi_ci_lower")
        upper = _number(row, "pi_ci_upper")
        if not (0 <= lower <= pi <= upper <= 1):
            raise ContractError("pi interval must satisfy 0 <= lower <= pi <= upper <= 1")
        if not math.isclose(pi, expected_pi, abs_tol=tolerance):
            raise ContractError("pi must equal pi_successes / pi_trials")
        if _text(row, "pi_uncertainty_method") != "wilson_95":
            raise ContractError("captured rows require wilson_95 uncertainty")
    else:
        if successes != 0 or trials != 0:
            raise ContractError("failed/blocked pi counts must be zero, never guess-filled")
        if any(row.get(key) is not None for key in ("pi", "pi_ci_lower", "pi_ci_upper")):
            raise ContractError("failed/blocked pi and uncertainty must remain null")
        if _text(row, "pi_uncertainty_method") != "not_estimable":
            raise ContractError("failed/blocked rows require not_estimable uncertainty")

    duration_status = _text(row, "task_duration_status")
    duration_value = row.get("task_duration_value")
    duration_unit = row.get("task_duration_unit")
    duration_source = str(row.get("task_duration_source", "")).strip()
    if duration_status == "verified":
        _number(row, "task_duration_value", minimum=1e-15)
        if duration_unit not in {"second", "minute", "hour"}:
            raise ContractError("verified duration requires second, minute, or hour")
        if not duration_source:
            raise ContractError("verified duration requires an authorized source")
    elif duration_status in ("blocked_missing", "deferred_scoring"):
        # deferred_scoring is the capture/scoring split (amendment section 3):
        # duration is absent for the same reason and under the same no-inference
        # rule, but the row was MEASURED, so it may carry pi. blocked_missing
        # keeps its original meaning untouched -- see the coupling at the
        # failure_status check below.
        if duration_value is not None or duration_unit is not None:
            raise ContractError("missing duration must remain null, never imputed")
        if duration_source:
            raise ContractError("missing duration cannot claim a source")
    else:
        raise ContractError(f"unsupported task_duration_status {duration_status!r}")

    input_tokens = _integer(row, "input_tokens")
    cached_tokens = _integer(row, "cached_input_tokens")
    output_tokens = _integer(row, "output_tokens")
    reasoning_tokens = _integer(row, "reasoning_tokens")
    _number(row, "latency_ms")
    _text(row, "price_lineage_version")
    _hash(row, "price_lineage_sha256")
    input_rate = _number(row, "input_usd_per_1m")
    cache_rate = _number(row, "cached_input_usd_per_1m")
    output_rate = _number(row, "output_usd_per_1m")
    expected_cost = metered_cost_usd(
        input_tokens=input_tokens,
        cached_input_tokens=cached_tokens,
        output_tokens=output_tokens,
        reasoning_tokens=reasoning_tokens,
        input_usd_per_1m=input_rate,
        cached_input_usd_per_1m=cache_rate,
        output_usd_per_1m=output_rate,
    )
    realized = _number(row, "realized_api_cost_usd")
    if not math.isclose(realized, expected_cost, abs_tol=tolerance):
        raise ContractError("realized_api_cost_usd does not reconcile to usage and prices")
    if _text(row, "realized_cost_method") != "metered_usage_x_frozen_price":
        raise ContractError("unsupported realized_cost_method")

    if duration_status == "blocked_missing" and failure != "blocked":
        raise ContractError("missing duration must block the row")

    availability = _text(row, "model_availability")
    if availability not in AVAILABILITY:
        raise ContractError(f"unsupported model_availability {availability!r}")
    method = _text(row, "availability_probe_method")
    _iso_timestamp(row, "availability_probed_at_utc", nullable=True)
    if availability == "account_available" and method == "none":
        raise ContractError("account availability requires a probe")
    if availability != "account_available" and failure == "none":
        raise ContractError("an unavailable/unprobed model cannot produce an eligible row")
    if route == "blocked_alias" and availability != "blocked_missing_approved_snapshot_rule":
        raise ContractError("blocked alias requires blocked_missing_approved_snapshot_rule availability")

    _hash(row, "prompt_ciphertext_sha256")
    _hash(row, "response_ciphertext_sha256", nullable=True)
    mapping_commit = _text(row, "mapping_commit")
    harness_commit = _text(row, "harness_commit")
    if not GIT_SHA.fullmatch(mapping_commit) or not GIT_SHA.fullmatch(harness_commit):
        raise ContractError("mapping_commit and harness_commit must be exact 40-char SHAs")
    _hash(row, "mapping_receipt_sha256")
    _text(row, "harness_version")


def blocked_row_cost_fields() -> dict[str, object]:
    """Canonical zero-usage fields for a row blocked before a provider call."""

    return {
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "output_tokens": 0,
        "reasoning_tokens": 0,
        "latency_ms": 0.0,
        "input_usd_per_1m": 0.0,
        "cached_input_usd_per_1m": 0.0,
        "output_usd_per_1m": 0.0,
        "realized_api_cost_usd": 0.0,
        "realized_cost_method": "metered_usage_x_frozen_price",
    }


SCOREABLE_DURATION_STATUS = "verified"


class ScoringGuardError(ContractError):
    """A row without verified task duration reached an economic scoring path."""


def assert_scoreable(row: Mapping[str, object]) -> None:
    """Refuse any row whose task duration is not verified.

    Every consumer that derives an economic quantity from a W4 row must call
    this before reading `pi`: the design memo section 2 crossing rule
    `A_tom = 1[c/pi_eff + f*(1-pi_eff)/pi_eff < w]`, the wage comparison `w`,
    the DAX index, and W5.

    Today this guarantee is structural rather than behavioural. A row missing
    duration carries `failure_status = "blocked"` and therefore null `pi`
    (see `validate_row`), so it cannot reach a crossing computation because it
    carries nothing to compute with. If the capture/scoring split of
    `dax/memo/AMENDMENT_DRAFT_w4_capture_scoring_split.md` is signed, that stops
    being true: capture-only rows will carry a real measured `pi` while their
    duration is still unknown, and only this guard stands between them and the
    index.

    The guard admits `verified` alone. It is therefore already correct under
    both worlds -- the current two-valued enum and the proposed
    `deferred_scoring` third value -- and needs no change if the amendment is
    signed. If the amendment is rejected it remains a correct statement of the
    invariant that `validate_row` enforces structurally.
    """

    status = str(row.get("task_duration_status", "")).strip()
    if status != SCOREABLE_DURATION_STATUS:
        raise ScoringGuardError(
            "task duration is not verified; this row may be captured but never "
            f"scored (task_duration_status={status or 'missing'!r})"
        )


def scoreable_pi(row: Mapping[str, object]) -> float:
    """Return `pi` for scoring, refusing rows whose duration is unverified.

    Scoring consumers should read `pi` through this accessor rather than
    indexing the row, so that the guard cannot be forgotten at the call site.
    """

    assert_scoreable(row)
    pi = row.get("pi")
    if not isinstance(pi, (int, float)) or isinstance(pi, bool):
        raise ScoringGuardError("a scoreable row must carry a numeric pi")
    if not 0.0 <= float(pi) <= 1.0:
        raise ScoringGuardError("pi outside [0, 1]")
    return float(pi)
