"""Strict schema and cost-accounting tests for the private W4 panel."""

import copy
import importlib.util
import pathlib

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "capability_panel" / "contract.py"
SPEC = importlib.util.spec_from_file_location("w4_contract", PATH)
assert SPEC and SPEC.loader
CONTRACT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTRACT)

HASH = "a" * 64
COMMIT = "b" * 40


def row(**updates):
    pi, lower, upper = CONTRACT.wilson_95(1, 2)
    value = {
        "task_id": "task-001",
        "event_id": "GPT4O_LAUNCH",
        "event_date": "2024-05-13",
        "model_requested": "gpt-4o-2024-05-13",
        "model_returned": "gpt-4o-2024-05-13",
        "model_vintage_date": "2024-05-13",
        "measurement_route": "direct",
        "source_model_id": "gpt-4o-2024-05-13",
        "approved_rule_id": "W05-DIRECT-DATED-SNAPSHOT",
        "perturbation_id": "baseline",
        "repetition_id": 1,
        "seed_requested": 7,
        "seed_applied": True,
        "correctness_measure": "grader-v1",
        "success": True,
        "pi_variant": "average_case",
        "pi_successes": 1,
        "pi_trials": 2,
        "pi": pi,
        "pi_ci_lower": lower,
        "pi_ci_upper": upper,
        "pi_uncertainty_method": "wilson_95",
        "task_duration_source": "gdpval-private@revision:duration_minutes",
        "task_duration_value": 15.0,
        "task_duration_unit": "minute",
        "task_duration_status": "verified",
        "input_tokens": 100,
        "cached_input_tokens": 20,
        "output_tokens": 50,
        "reasoning_tokens": 10,
        "latency_ms": 123.4,
        "price_lineage_version": "w2-prices-v1",
        "price_lineage_sha256": HASH,
        "input_usd_per_1m": 2.5,
        "cached_input_usd_per_1m": 1.25,
        "output_usd_per_1m": 10.0,
        "realized_api_cost_usd": (80 * 2.5 + 20 * 1.25 + 50 * 10.0) / 1_000_000,
        "realized_cost_method": "metered_usage_x_frozen_price",
        "failure_status": "none",
        "failure_code": "none",
        "model_availability": "account_available",
        "availability_probe_method": "models_list_metadata",
        "availability_probed_at_utc": "2026-08-19T00:00:00Z",
        "prompt_ciphertext_sha256": HASH,
        "response_ciphertext_sha256": HASH,
        "mapping_commit": COMMIT,
        "mapping_receipt_sha256": HASH,
        "harness_version": "1.0.0",
        "harness_commit": COMMIT,
    }
    value.update(updates)
    return value


def test_valid_row_and_reasoning_tokens_are_not_double_billed():
    value = row()
    CONTRACT.validate_row(value)
    assert value["realized_api_cost_usd"] == pytest.approx(
        CONTRACT.metered_cost_usd(
            input_tokens=100,
            cached_input_tokens=20,
            output_tokens=50,
            reasoning_tokens=10,
            input_usd_per_1m=2.5,
            cached_input_usd_per_1m=1.25,
            output_usd_per_1m=10.0,
        )
    )


def test_reasoning_tokens_cannot_exceed_billed_output_tokens():
    with pytest.raises(CONTRACT.ContractError, match="reasoning_tokens"):
        CONTRACT.validate_row(row(reasoning_tokens=51))


def test_gpt45_is_bindingly_excluded_even_if_a_response_exists():
    with pytest.raises(CONTRACT.ContractError, match="bindingly excluded"):
        CONTRACT.validate_row(row(
            model_requested="gpt-4.5-preview",
            model_returned="gpt-4.5-preview",
            source_model_id="gpt-4.5-preview",
        ))


def test_current_alias_requires_a_separate_approved_alias_rule():
    with pytest.raises(CONTRACT.ContractError, match="undated direct alias"):
        CONTRACT.validate_row(row(
            model_requested="gpt-5.6-sol",
            model_returned="gpt-5.6-sol",
            source_model_id="gpt-5.6-sol",
        ))


def test_average_and_perturbation_robust_variants_cannot_be_collapsed():
    with pytest.raises(CONTRACT.ContractError, match="baseline"):
        CONTRACT.validate_row(row(perturbation_id="paraphrase"))
    robust = row(
        perturbation_id="paraphrase",
        pi_variant="perturbation_robust",
    )
    CONTRACT.validate_row(robust)


def test_missing_duration_must_be_null_and_blocks_the_row():
    blocked = row(
        model_returned=None,
        task_duration_source="",
        task_duration_value=None,
        task_duration_unit=None,
        task_duration_status="blocked_missing",
        success=False,
        failure_status="blocked",
        failure_code="blocked_missing_task_duration",
        model_availability="unprobed_missing_key",
        availability_probe_method="none",
        availability_probed_at_utc=None,
        response_ciphertext_sha256=None,
        pi_successes=0,
        pi_trials=0,
        pi=None,
        pi_ci_lower=None,
        pi_ci_upper=None,
        pi_uncertainty_method="not_estimable",
        **CONTRACT.blocked_row_cost_fields(),
    )
    CONTRACT.validate_row(blocked)
    damaged = copy.deepcopy(blocked)
    damaged["task_duration_value"] = 30
    damaged["task_duration_unit"] = "minute"
    with pytest.raises(CONTRACT.ContractError, match="never imputed"):
        CONTRACT.validate_row(damaged)

    damaged = copy.deepcopy(blocked)
    damaged["model_returned"] = "gpt-4o-2024-05-13"
    with pytest.raises(CONTRACT.ContractError, match="explicitly null"):
        CONTRACT.validate_row(damaged)

    damaged = copy.deepcopy(blocked)
    del damaged["model_returned"]
    with pytest.raises(CONTRACT.ContractError, match="explicitly null"):
        CONTRACT.validate_row(damaged)


def test_plaintext_private_fields_are_rejected():
    with pytest.raises(CONTRACT.ContractError, match="plaintext/private"):
        CONTRACT.validate_row(row(prompt="secret task text"))


def test_unapproved_current_alias_is_an_explicit_blocked_row():
    blocked = row(
        event_id="GPT56_FAMILY_LAUNCH",
        event_date="2026-07-09",
        model_requested=None,
        model_returned=None,
        model_vintage_date="2026-07-09",
        measurement_route="blocked_alias",
        source_model_id="gpt-5.6-sol",
        approved_rule_id=None,
        success=False,
        pi_successes=0,
        pi_trials=0,
        pi=None,
        pi_ci_lower=None,
        pi_ci_upper=None,
        pi_uncertainty_method="not_estimable",
        failure_status="blocked",
        failure_code="blocked_missing_approved_snapshot_rule",
        model_availability="blocked_missing_approved_snapshot_rule",
        availability_probe_method="none",
        availability_probed_at_utc=None,
        response_ciphertext_sha256=None,
        **CONTRACT.blocked_row_cost_fields(),
    )
    CONTRACT.validate_row(blocked)


def test_cost_must_reconcile_exactly_to_frozen_prices_and_usage():
    with pytest.raises(CONTRACT.ContractError, match="does not reconcile"):
        CONTRACT.validate_row(row(realized_api_cost_usd=1.0))
