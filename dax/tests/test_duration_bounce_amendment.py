import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_bounce_supersedes_wait_but_does_not_claim_contact():
    text = (ROOT / "memo" / "PI_AMENDMENT_GDPVAL_OUTREACH_BOUNCE_2026-08-21.md").read_text()
    assert "AUTHOR_OUTREACH_BOUNCED" in text
    assert "no author contact was established" in text
    assert "14-calendar-day waiting rule" in text
    assert "real qualified human annotators" in text


def test_pilot_is_frozen_but_has_no_responses_or_spend():
    sample = json.loads((ROOT / "capability_panel" / "gdpval_duration_pilot_sampling_receipt_20260821.json").read_text())
    budget = json.loads((ROOT / "capability_panel" / "gdpval_duration_pilot_budget_preflight_20260821.json").read_text())
    assert sample["pilot_tasks"] == 40
    assert sample["production_reserve_tasks"] == 180
    assert sample["human_responses_collected"] == 0
    assert sample["task_ids_committed"] is False
    assert budget["status"] == "NEED_PI_BUDGET_AUTHORIZATION"
    assert budget["available_verified_qualified_humans"] == 0
    assert budget["realized_spend_usd"] == 0
