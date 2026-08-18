"""Contract tests for the private DAX W5 real dose-panel build."""

import copy
import importlib.util
import pathlib

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "w5" / "build_dose_panel.py"
SPEC = importlib.util.spec_from_file_location("w5_dose_panel", PATH)
assert SPEC and SPEC.loader
PANEL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PANEL)

HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64
HASH_D = "d" * 64
HASH_E = "e" * 64


def event(**updates):
    row = {
        "event_id": "MODEL_RELEASE_1",
        "event_date": "2025-01-15",
        "event_date_status": "written_dated_verified",
        "event_inclusion_status": "retained",
        "event_multiplier_lower": 0.5,
        "event_multiplier_center": 0.75,
        "event_multiplier_upper": 1.0,
        "event_evidence_version": "events-v1",
        "event_evidence_sha256": HASH_A,
        "event_evidence_row_count": 7,
        "price_evidence_status": "verified",
        "price_input_version": "prices-v1",
        "price_input_sha256": HASH_B,
        "price_input_row_count": 11,
        "exclusion_reason": "",
    }
    row.update(updates)
    return row


def component(**updates):
    row = {
        "cps_occ2010": "0010",
        "component_id": "route-1",
        "crosswalk_status": "resolved_employment_weighted",
        "route_status": "resolved_employment_weighted",
        "component_weight": 1.0,
        "component_dose_lower": 0.4,
        "component_dose_center": 0.4,
        "component_dose_upper": 0.4,
        "mapping_input_version": "mapping-v1",
        "mapping_input_sha256": HASH_C,
        "mapping_input_row_count": 100,
        "dose_input_version": "dose-v1",
        "dose_input_sha256": HASH_D,
        "dose_input_row_count": 200,
        "exclusion_reason": "",
    }
    row.update(updates)
    return row


def build(events=None, components=None):
    return PANEL.build_panel(
        events if events is not None else [event()],
        components if components is not None else [component()],
        panel_version="w5-gate1-v1",
        build_code_version="git-test",
        build_code_sha256=HASH_E,
    )


def test_resolved_whole_code_may_be_point_valued_and_lineage_is_complete():
    rows, exclusions = build()
    assert exclusions == []
    assert len(rows) == 1
    row = rows[0]
    assert row["dose_lower"] == pytest.approx(0.2)
    assert row["dose_center"] == pytest.approx(0.3)
    assert row["dose_upper"] == pytest.approx(0.4)
    assert row["occupation_total_center"] == pytest.approx(0.3)
    assert row["panel_row_id"] == PANEL.stable_row_id(
        "w5-gate1-v1", "MODEL_RELEASE_1", "0010", "route-1"
    )
    for field in (
        "event_evidence_sha256", "price_input_sha256",
        "mapping_input_sha256", "dose_input_sha256", "build_code_sha256",
    ):
        assert len(row[field]) == 64


def test_price_evidence_cannot_substitute_for_failed_event_date_gate():
    excluded = event(
        event_date_status="pending_second_date_locator",
        event_inclusion_status="candidate",
        price_evidence_status="verified",
        exclusion_reason="written dated release locator not frozen",
    )
    rows, exclusions = build(events=[excluded])
    assert rows == []
    assert exclusions == [{
        "entity_type": "event",
        "entity_id": "MODEL_RELEASE_1",
        "status": "candidate",
        "reason": "written dated release locator not frozen",
        "event_date_status": "pending_second_date_locator",
        "price_evidence_status": "verified",
    }]


def test_unresolved_crosswalk_is_excluded_without_zero_fill_or_status_upgrade():
    unresolved = component(
        crosswalk_status="partial_unresolved",
        route_status="unresolved_no_usable_onet",
        exclusion_reason="official route contains unresolved mass",
    )
    rows, exclusions = build(components=[unresolved])
    assert rows == []
    assert exclusions[0]["status"] == "partial_unresolved"
    assert exclusions[0]["reason"] == "official route contains unresolved mass"


def test_provisional_component_requires_nondegenerate_bounds():
    provisional = component(
        crosswalk_status="provisional_equal_within_soc",
        route_status="provisional_equal_within_soc",
    )
    with pytest.raises(PANEL.PanelContractError, match="requires bounds"):
        build(components=[provisional])


def test_frozen_19_22pp_provisional_mass_is_bounded_and_reconciles():
    rows = [
        {
            "occupation_mass": 0.8078,
            "crosswalk_status": "resolved_employment_weighted",
        },
        {
            "occupation_mass": 0.1922,
            "crosswalk_status": "provisional_equal_within_soc",
            "dose_lower": 0.1,
            "dose_center": 0.4,
            "dose_upper": 0.8,
        },
    ]
    receipt = PANEL.audit_crosswalk_mass(
        rows, expected_provisional_share=0.1922, tolerance=1e-12
    )
    assert receipt == pytest.approx({
        "resolved_mass_share": 0.8078,
        "provisional_mass_share": 0.1922,
        "unresolved_mass_share": 0.0,
    })


def test_component_weights_and_reported_totals_reconcile():
    components = [
        component(component_id="a", component_weight=0.25),
        component(component_id="b", component_weight=0.75),
    ]
    rows, _ = build(components=components)
    assert len(rows) == 2
    assert {row["occupation_total_center"] for row in rows} == pytest.approx({0.3})
    damaged = copy.deepcopy(rows)
    damaged[0]["occupation_total_center"] += 0.01
    with pytest.raises(PANEL.PanelContractError, match="inconsistent occupation totals"):
        PANEL.validate_panel(damaged)


def test_component_weights_must_sum_to_one():
    with pytest.raises(PANEL.PanelContractError, match="sum to"):
        build(components=[component(component_weight=0.99)])


@pytest.mark.parametrize("column", [
    "employment_rate", "weekly_hours", "log_wage", "real_post_event_outcome"
])
def test_no_outcome_columns_can_enter_any_construction_input(column):
    tainted = component()
    tainted[column] = 1.0
    with pytest.raises(PANEL.PanelContractError, match="outcome-like columns"):
        build(components=[tainted])


def test_lineage_hashes_and_row_counts_are_enforced():
    bad_hash = component(mapping_input_sha256="not-a-hash")
    with pytest.raises(PANEL.PanelContractError, match="lowercase SHA-256"):
        build(components=[bad_hash])
    bad_count = event(event_evidence_row_count=0)
    with pytest.raises(PANEL.PanelContractError, match="positive integer"):
        build(events=[bad_count])
