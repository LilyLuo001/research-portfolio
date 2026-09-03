import importlib.util
import json
import pathlib

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "capability_panel" / "availability.py"
SPEC = importlib.util.spec_from_file_location("w4_availability", PATH)
assert SPEC and SPEC.loader
AVAIL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AVAIL)
REGISTRY_PATH = ROOT / "capability_panel" / "vintage_registry.json"


def test_registry_preserves_exclusion_standins_and_alias_blocks():
    registry = AVAIL.load_registry(REGISTRY_PATH)
    by_source = {}
    for row in registry["models"]:
        by_source.setdefault(row["source_model_id"], []).append(row)
    assert by_source["gpt-4.5-preview"][0]["status"] == "excluded_binding"
    assert by_source["gpt-4.5-preview"][0]["measurement_model_id"] is None
    assert by_source["gpt-4-0314"][0]["measurement_route"] == "approved_open_weight_standin"
    assert by_source["o1-preview"][0]["measurement_route"] == "approved_open_weight_standin"
    assert by_source["gpt-5.6-sol"][0]["status"] == "blocked_missing_approved_snapshot_rule"


def test_missing_key_is_unprobed_not_guessed_available():
    registry = AVAIL.load_registry(REGISTRY_PATH)
    receipt = AVAIL.audit_registry(registry, None)
    assert receipt["account_probe_performed"] is False
    assert receipt["probed_at_utc"] is None
    direct = [row for row in receipt["matrix"] if row["measurement_route"] == "direct"]
    assert direct
    assert {row["availability_status"] for row in direct} == {"unprobed_missing_key"}


def test_account_list_is_filtered_to_targets_and_records_shutdown_date():
    registry = AVAIL.load_registry(REGISTRY_PATH)
    account = [
        {"id": "gpt-4o-2024-05-13", "shutdown_date": "2026-10-23"},
        {"id": "unrelated-private-model", "shutdown_date": None},
    ]
    receipt = AVAIL.audit_registry(registry, account, probed_at_utc="2026-08-19T00:00:00Z")
    target = next(row for row in receipt["matrix"] if row["source_model_id"] == "gpt-4o-2024-05-13")
    assert target["availability_status"] == "account_available"
    assert target["shutdown_date"] == "2026-10-23"
    assert "unrelated-private-model" not in str(receipt)


def test_private_env_requires_owner_only_permissions(tmp_path):
    path = tmp_path / ".env"
    path.write_text("OPENAI_" + "API_KEY=test-placeholder\n", encoding="utf-8")
    path.chmod(0o644)
    with pytest.raises(AVAIL.AvailabilityError, match="0600"):
        AVAIL.private_env_value(path, "OPENAI_API_KEY")
    path.chmod(0o600)
    assert AVAIL.private_env_value(path, "OPENAI_API_KEY") == "test-placeholder"


def test_cli_refuses_to_write_an_unprobed_receipt_without_a_key(tmp_path, capsys, monkeypatch):
    """A missing key must fail closed, not silently produce a non-result.

    The committed receipt in dax/data_raw/ is a no-key run: every field a
    reader skims is present, account_probe_performed is false, and the old CLI
    exited 0. That is how a non-result gets mistaken for a result. The CLI now
    refuses and leaves any existing receipt untouched.
    """

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    out = tmp_path / "receipt.json"
    code = AVAIL.main([
        "--registry", str(REGISTRY_PATH), "--output", str(out),
    ])
    assert code == 2
    assert not out.exists(), "a refused probe must not write a receipt"
    assert "NEED_HUMAN" in capsys.readouterr().err


def test_cli_names_the_failed_precondition(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    missing = tmp_path / "absent" / ".env"
    assert AVAIL.main([
        "--registry", str(REGISTRY_PATH), "--env-file", str(missing),
        "--output", str(tmp_path / "r.json"),
    ]) == 2
    assert "does not exist" in capsys.readouterr().err

    loose = tmp_path / "loose.env"
    loose.write_text("OPENAI_API_KEY=sk-test\n", encoding="utf-8")
    loose.chmod(0o644)
    assert AVAIL.main([
        "--registry", str(REGISTRY_PATH), "--env-file", str(loose),
        "--output", str(tmp_path / "r.json"),
    ]) == 2
    assert "chmod 600" in capsys.readouterr().err

    wrong_var = tmp_path / "other.env"
    wrong_var.write_text("DEEPSEEK_API_KEY=x\n", encoding="utf-8")
    wrong_var.chmod(0o600)
    assert AVAIL.main([
        "--registry", str(REGISTRY_PATH), "--env-file", str(wrong_var),
        "--output", str(tmp_path / "r.json"),
    ]) == 2
    assert "no OPENAI_API_KEY assignment" in capsys.readouterr().err


def test_an_unprobed_receipt_still_requires_an_explicit_opt_in(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    out = tmp_path / "receipt.json"
    assert AVAIL.main([
        "--registry", str(REGISTRY_PATH), "--output", str(out), "--allow-unprobed",
    ]) == 0
    receipt = json.loads(out.read_text())
    assert receipt["account_probe_performed"] is False
    assert receipt["probed_at_utc"] is None
