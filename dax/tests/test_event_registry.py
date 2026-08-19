import importlib.util
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "memo" / "validate_event_registry.py"
SPEC = importlib.util.spec_from_file_location("validate_event_registry", MODULE_PATH)
assert SPEC and SPEC.loader
REGISTRY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REGISTRY)


def test_registry_passes_fail_closed_checks():
    rows, errors = REGISTRY.validate()
    assert not errors
    assert rows


def test_only_verified_events_can_be_eligible():
    rows, _ = REGISTRY.validate()
    assert all(
        row["verification_status"] == "verified"
        for row in rows
        if row["analysis_status"] == "eligible"
    )


def test_binding_exclusion_is_preserved():
    rows, _ = REGISTRY.validate()
    excluded = {row["event_id"] for row in rows if row["analysis_status"] == "excluded_binding"}
    assert "GPT45_PREVIEW_LAUNCH" in excluded


def test_w2_verified_price_status_is_backed_by_panel():
    rows, errors = REGISTRY.validate()
    assert not errors
    priced = [row for row in rows if row["price_status"] != "n_a"]
    assert priced
    assert all(row["price_status"] == "verified_w2" for row in priced)
