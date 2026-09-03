import csv
import importlib.util
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "memo" / "validate_event_registry.py"
SPEC = importlib.util.spec_from_file_location("validate_event_registry", MODULE_PATH)
assert SPEC and SPEC.loader
REGISTRY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REGISTRY)

AUDITED_PASS = {
    "GPT4_TURBO_PREVIEW": "https://openai.com/index/new-models-and-developer-products-announced-at-devday/",
    "O1_PREVIEW_LAUNCH": "https://openai.com/index/learning-to-reason-with-llms/",
    "GPT45_PREVIEW_LAUNCH": "https://openai.com/index/introducing-gpt-4-5/",
    "O3_PRICE_CUT": "https://community.openai.com/t/o3-is-80-cheaper-and-introducing-o3-pro/1284925",
    "GPT54_MINI_NANO_LAUNCH": "https://openai.com/index/introducing-gpt-5-4-mini-and-nano/",
    "GPT55_LAUNCH": "https://openai.com/index/introducing-gpt-5-5/",
    "GPT56_FAMILY_LAUNCH": "https://openai.com/index/gpt-5-6/",
    "GPT56_PRICE_CUT": "https://openai.com/index/gpt-5-6/",
}
AUDITED_PENDING = {"GPT56_FAST_LONG_CONTEXT"}


def _rows_by_id():
    rows, errors = REGISTRY.validate()
    assert not errors
    return {row["event_id"]: row for row in rows}


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
    rows = _rows_by_id()
    excluded = {
        event_id
        for event_id, row in rows.items()
        if row["analysis_status"] == "excluded_binding"
    }
    assert "GPT45_PREVIEW_LAUNCH" in excluded
    assert rows["GPT45_PREVIEW_LAUNCH"]["price_status"] == "n_a"


def test_w2_verified_price_status_is_backed_by_panel():
    rows, errors = REGISTRY.validate()
    assert not errors
    priced = [row for row in rows if row["price_status"] != "n_a"]
    assert priced
    assert all(row["price_status"] == "verified_w2" for row in priced)


def test_dated_event_evidence_audit_is_pinned():
    rows = _rows_by_id()
    assert {
        event_id
        for event_id, row in rows.items()
        if row["verification_status"] == "pending_second_date_locator"
    } == AUDITED_PENDING
    for event_id, second_locator in AUDITED_PASS.items():
        assert rows[event_id]["verification_status"] == "verified"
        assert rows[event_id]["source_2"] == second_locator


def test_gpt55_api_date_conflict_is_preserved():
    row = _rows_by_id()["GPT55_LAUNCH"]
    assert row["api_effective_date"] == "2026-04-24"
    assert row["date_conflict"] == "2026-04-23"
    assert "2026-04-23" in row["model_ids"]


def test_future_rows_are_not_promoted_to_retained_events():
    rows = _rows_by_id()
    future = {
        "O3_PRICE_CUT",
        "GPT56_FAMILY_LAUNCH",
        "GPT56_PRICE_CUT",
        "GPT56_FAST_LONG_CONTEXT",
    }
    assert all(rows[event_id]["analysis_status"] == "candidate" for event_id in future)
    assert rows["GPT56_FAST_LONG_CONTEXT"]["verification_status"] == "pending_second_date_locator"


def test_unqualified_and_binding_rows_stay_out_of_w5_fill():
    shell = ROOT / "memo" / "event_table_shell_v1.csv"
    with shell.open(newline="", encoding="utf-8") as handle:
        rows = {row["event_id"]: row for row in csv.DictReader(handle)}
    assert rows["GPT56_FAST_LONG_CONTEXT"]["w5_fill_status"] == "BLOCKED_SOURCE_THEN_W5_FILL"
    assert rows["GPT45_PREVIEW_LAUNCH"]["w5_fill_status"] == "NOT_APPLICABLE"
