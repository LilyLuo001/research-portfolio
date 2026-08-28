import importlib
import pathlib
import urllib.error

import pytest


pytest.importorskip("cryptography")
from cryptography.fernet import Fernet

HARNESS = importlib.import_module("dax.capability_panel.harness")


def test_encrypted_store_never_writes_plaintext(tmp_path):
    store = HARNESS.EncryptedStore((tmp_path / "private").resolve(), Fernet.generate_key())
    digest = store.put_json("item-1", {"prompt": "TOP SECRET TASK"})
    files = list((tmp_path / "private").glob("*.fernet"))
    assert len(files) == 1
    assert b"TOP SECRET TASK" not in files[0].read_bytes()
    assert len(digest) == 64
    assert store.get_json("item-1")["prompt"] == "TOP SECRET TASK"


def test_budget_reservation_is_idempotent_and_fail_closed(tmp_path):
    ledger = HARNESS.BudgetLedger(tmp_path / "private" / "budget.sqlite", 1.0)
    assert ledger.reserve("a", 0.6) is True
    assert ledger.reserve("a", 0.6) is False
    with pytest.raises(HARNESS.BudgetExceeded):
        ledger.reserve("b", 0.5)
    ledger.settle("a", 0.4)
    assert ledger.reserve("b", 0.5) is True
    with pytest.raises(HARNESS.BudgetExceeded):
        ledger.settle("b", 0.7)


def test_checkpoint_resume_skips_completed_item(tmp_path):
    path = tmp_path / "checkpoint.jsonl"
    first = HARNESS.Checkpoint(path)
    first.append({"item_id": "x", "terminal": True, "status": "captured"})
    second = HARNESS.Checkpoint(path)
    assert "x" in second.completed
    with pytest.raises(HARNESS.HarnessError, match="private fields"):
        second.append({"item_id": "y", "prompt": "leak"})


def test_execute_is_resumable_metered_and_sanitized(tmp_path):
    key = Fernet.generate_key()
    prompts = HARNESS.EncryptedStore((tmp_path / "prompts").resolve(), key)
    responses = HARNESS.EncryptedStore((tmp_path / "responses").resolve(), key)
    item = {
        "item_id": "item-1",
        "plan_status": "eligible",
        "measurement_model_id": "gpt-4o-2024-05-13",
        "endpoint_kind": "chat_completions",
        "supports_seed": True,
        "deterministic_seed": 123,
    }
    prompts.put_json("item-1", {"prompt": "private prompt"})
    ledger = HARNESS.BudgetLedger(tmp_path / "ledger" / "budget.sqlite", 1.0)
    checkpoint = HARNESS.Checkpoint(tmp_path / "checkpoint" / "rows.jsonl")
    limiter = HARNESS.RateLimiter(1e9, sleeper=lambda _: None)
    calls = []

    def transport(endpoint, body):
        calls.append((endpoint, body))
        return {
            "model": "gpt-4o-2024-05-13",
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "prompt_tokens_details": {"cached_tokens": 20},
                "completion_tokens_details": {"reasoning_tokens": 10},
            },
            "choices": [{"message": {"content": "private response"}}],
        }

    prices = {
        "input_usd_per_1m": 2.5,
        "cached_input_usd_per_1m": 1.25,
        "output_usd_per_1m": 10.0,
    }
    result = HARNESS.execute_item(
        item,
        prompt_store=prompts,
        response_store=responses,
        transport=transport,
        score=lambda _: True,
        prices=prices,
        ledger=ledger,
        checkpoint=checkpoint,
        limiter=limiter,
        max_output_tokens=100,
        sleeper=lambda _: None,
    )
    assert result["status"] == "captured"
    assert result["failure_status"] == "none"
    assert result["model_returned"] == "gpt-4o-2024-05-13"
    assert result["reasoning_tokens"] == 10
    assert result["realized_api_cost_usd"] == pytest.approx(
        (80 * 2.5 + 20 * 1.25 + 50 * 10) / 1_000_000
    )
    assert calls[0][1]["seed"] == 123
    assert "private response" not in (tmp_path / "checkpoint" / "rows.jsonl").read_text()
    assert HARNESS.execute_item(
        item,
        prompt_store=prompts,
        response_store=responses,
        transport=transport,
        score=lambda _: True,
        prices=prices,
        ledger=ledger,
        checkpoint=checkpoint,
        limiter=limiter,
        max_output_tokens=100,
    ) is None
    assert len(calls) == 1


def test_o1_request_uses_supported_output_parameter_without_temperature():
    body = HARNESS.request_body(
        {
            "measurement_model_id": "o1-2024-12-17",
            "endpoint_kind": "chat_completions",
            "supports_seed": False,
            "supports_temperature": False,
            "max_output_parameter": "max_completion_tokens",
        },
        "private prompt",
        max_output_tokens=17,
    )
    assert body["max_completion_tokens"] == 17
    assert "max_tokens" not in body
    assert "temperature" not in body


def test_blocked_item_has_explicit_null_returned_model_and_pi(tmp_path):
    key = Fernet.generate_key()
    record = HARNESS.execute_item(
        {
            "item_id": "blocked-item",
            "plan_status": "blocked",
            "blockers": ["blocked_missing_task_duration"],
            "task_id": "task-1",
            "mapping_commit": "b" * 40,
        },
        prompt_store=HARNESS.EncryptedStore((tmp_path / "prompts").resolve(), key),
        response_store=HARNESS.EncryptedStore((tmp_path / "responses").resolve(), key),
        transport=lambda *_: pytest.fail("blocked item must not call provider"),
        score=lambda _: True,
        prices={"input_usd_per_1m": 1.0, "cached_input_usd_per_1m": 0.0, "output_usd_per_1m": 1.0},
        ledger=HARNESS.BudgetLedger(tmp_path / "ledger" / "budget.sqlite", 1.0),
        checkpoint=HARNESS.Checkpoint(tmp_path / "checkpoint" / "rows.jsonl"),
        limiter=HARNESS.RateLimiter(1e9, sleeper=lambda _: None),
        max_output_tokens=10,
    )
    assert record["failure_status"] == "blocked"
    assert record["model_returned"] is None
    assert record["pi"] is None
    assert record["pi_ci_lower"] is None
    assert record["pi_ci_upper"] is None
    assert record["pi_uncertainty_method"] == "not_estimable"
    assert record["mapping_commit"] == "b" * 40


def test_missing_usage_is_failed_and_retains_full_reservation(tmp_path):
    key = Fernet.generate_key()
    prompts = HARNESS.EncryptedStore((tmp_path / "prompts").resolve(), key)
    prompts.put_json("missing-usage", {"prompt": "private"})
    ledger = HARNESS.BudgetLedger(tmp_path / "ledger" / "budget.sqlite", 1.0)
    record = HARNESS.execute_item(
        {
            "item_id": "missing-usage",
            "plan_status": "eligible",
            "measurement_model_id": "gpt-4o-2024-05-13",
            "endpoint_kind": "chat_completions",
            "supports_seed": False,
            "task_id": "task-1",
            "mapping_commit": "b" * 40,
        },
        prompt_store=prompts,
        response_store=HARNESS.EncryptedStore((tmp_path / "responses").resolve(), key),
        transport=lambda *_: {"model": "gpt-4o-2024-05-13", "choices": []},
        score=lambda _: True,
        prices={"input_usd_per_1m": 1.0, "cached_input_usd_per_1m": 0.0, "output_usd_per_1m": 1.0},
        ledger=ledger,
        checkpoint=HARNESS.Checkpoint(tmp_path / "checkpoint" / "rows.jsonl"),
        limiter=HARNESS.RateLimiter(1e9, sleeper=lambda _: None),
        max_output_tokens=10,
        max_retries=0,
    )
    assert record["failure_status"] == "measurement_failed"
    assert record["usage_status"] == "not_estimable_reservation_retained"
    assert record["model_returned"] is None and record["pi"] is None
    assert len(record["response_ciphertext_sha256"]) == 64
    assert ledger.summary()["reserved_or_retained_usd"] > 0


def test_existing_ledger_state_prevents_paid_replay_after_checkpoint_gap(tmp_path):
    key = Fernet.generate_key()
    prompts = HARNESS.EncryptedStore((tmp_path / "prompts").resolve(), key)
    prompts.put_json("ambiguous-item", {"prompt": "private"})
    ledger = HARNESS.BudgetLedger(tmp_path / "ledger" / "budget.sqlite", 1.0)
    assert ledger.reserve("ambiguous-item", 0.25)
    calls = []
    record = HARNESS.execute_item(
        {
            "item_id": "ambiguous-item",
            "plan_status": "eligible",
            "measurement_model_id": "gpt-4o-2024-05-13",
            "endpoint_kind": "chat_completions",
            "supports_seed": False,
            "mapping_commit": "b" * 40,
        },
        prompt_store=prompts,
        response_store=HARNESS.EncryptedStore((tmp_path / "responses").resolve(), key),
        transport=lambda *args: calls.append(args),
        score=lambda _: True,
        prices={"input_usd_per_1m": 1.0, "cached_input_usd_per_1m": 0.0, "output_usd_per_1m": 1.0},
        ledger=ledger,
        checkpoint=HARNESS.Checkpoint(tmp_path / "checkpoint" / "rows.jsonl"),
        limiter=HARNESS.RateLimiter(1e9, sleeper=lambda _: None),
        max_output_tokens=10,
        max_retries=0,
    )
    assert calls == []
    assert record["failure_code"] == "ledger_state_prevents_replay"
    assert record["ledger_status"] == "reserved"
    assert record["retained_unknown_cost_usd"] == pytest.approx(0.25)
    assert record["model_returned"] is None and record["pi"] is None
    assert ledger.summary()["reserved_or_retained_usd"] == pytest.approx(0.25)


def test_grader_failure_preserves_metered_usage_cost_and_lineage(tmp_path):
    key = Fernet.generate_key()
    prompts = HARNESS.EncryptedStore((tmp_path / "prompts").resolve(), key)
    prompts.put_json("grader-failure", {"prompt": "private"})
    record = HARNESS.execute_item(
        {
            "item_id": "grader-failure",
            "plan_status": "eligible",
            "measurement_model_id": "gpt-4o-2024-05-13",
            "endpoint_kind": "chat_completions",
            "supports_seed": False,
            "task_id": "task-1",
            "event_id": "GPT4O_LAUNCH",
            "mapping_commit": "b" * 40,
            "mapping_receipt_sha256": "a" * 64,
        },
        prompt_store=prompts,
        response_store=HARNESS.EncryptedStore((tmp_path / "responses").resolve(), key),
        transport=lambda *_: {
            "model": "gpt-4o-2024-05-13",
            "usage": {"prompt_tokens": 3, "completion_tokens": 2},
        },
        score=lambda _: (_ for _ in ()).throw(RuntimeError("private grader detail")),
        prices={"input_usd_per_1m": 2.0, "cached_input_usd_per_1m": 0.0, "output_usd_per_1m": 4.0},
        ledger=HARNESS.BudgetLedger(tmp_path / "ledger" / "budget.sqlite", 1.0),
        checkpoint=HARNESS.Checkpoint(tmp_path / "checkpoint" / "rows.jsonl"),
        limiter=HARNESS.RateLimiter(1e9, sleeper=lambda _: None),
        max_output_tokens=10,
        max_retries=0,
    )
    assert record["failure_status"] == "measurement_failed"
    assert record["model_returned"] is None and record["pi"] is None
    assert record["input_tokens"] == 3 and record["output_tokens"] == 2
    assert record["realized_api_cost_usd"] == pytest.approx(14 / 1_000_000)
    assert record["event_id"] == "GPT4O_LAUNCH"
    assert record["mapping_receipt_sha256"] == "a" * 64


def test_retry_keeps_a_conservative_unknown_cost_reservation(tmp_path):
    key = Fernet.generate_key()
    prompts = HARNESS.EncryptedStore((tmp_path / "prompts").resolve(), key)
    responses = HARNESS.EncryptedStore((tmp_path / "responses").resolve(), key)
    item = {
        "item_id": "retry-item",
        "plan_status": "eligible",
        "measurement_model_id": "gpt-4o-2024-05-13",
        "endpoint_kind": "chat_completions",
        "supports_seed": False,
        "deterministic_seed": 1,
    }
    prompts.put_json("retry-item", {"prompt": "private"})
    ledger = HARNESS.BudgetLedger(tmp_path / "ledger" / "budget.sqlite", 1.0)
    checkpoint = HARNESS.Checkpoint(tmp_path / "checkpoint" / "rows.jsonl")
    attempts = iter(("fail", "pass"))

    def transport(_endpoint, _body):
        if next(attempts) == "fail":
            raise urllib.error.URLError("transient")
        return {"usage": {"prompt_tokens": 1, "completion_tokens": 1}}

    result = HARNESS.execute_item(
        item,
        prompt_store=prompts,
        response_store=responses,
        transport=transport,
        score=lambda _: True,
        prices={
            "input_usd_per_1m": 1.0,
            "cached_input_usd_per_1m": 0.0,
            "output_usd_per_1m": 1.0,
        },
        ledger=ledger,
        checkpoint=checkpoint,
        limiter=HARNESS.RateLimiter(1e9, sleeper=lambda _: None),
        max_output_tokens=10,
        max_retries=1,
        sleeper=lambda _: None,
    )
    assert result["retained_unknown_cost_usd"] > 0
    assert ledger.summary()["reserved_or_retained_usd"] > 0
