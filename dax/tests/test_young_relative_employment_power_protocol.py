import json
import math
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
PROTOCOL = (
    ROOT
    / "memo"
    / "power_calcs"
    / "young_relative_employment_power_protocol_v1.json"
)
DESIGN = ROOT / "paper" / "DESIGN_FREEZE_CANDIDATE_v1.md"


def test_protocol_is_fail_closed_and_uses_only_pre_outcomes():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["status"] == "BLOCKED_PENDING_C1"
    assert protocol["post_outcomes_permitted"] is False
    assert protocol["wide_extract"]["pre_outcome_last_month"] == "2022-11"
    assert protocol["wide_extract"]["structural_validation_status"] == "PASS"
    assert protocol["wide_extract"]["outcomes_inspected_during_validation"] is False
    assert protocol["wide_extract"]["row_count"] == 9262480
    assert protocol["timing"]["post_first_month"] == "2022-12"
    assert protocol["wide_extract"]["missing_months"] == ["2025-10"]
    assert protocol["wide_extract"]["usable_basic_month_count"] == 109
    assert protocol["wide_extract"]["usable_preperiod_month_count"] == 66
    assert protocol["wide_extract"]["structural_asec_gaps"] == [
        "2017-03", "2018-03", "2019-03", "2020-03", "2021-03",
    ]
    assert protocol["wide_extract"]["corrective_spec_status"] == (
        "PREPARED_NOT_SUBMITTED"
    )
    assert protocol["recode_contract"]["status"] == "PASS_METADATA_ONLY"
    assert protocol["recode_contract"]["microdata_read"] is False


def test_external_declines_are_mapped_to_log_contrasts():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    for benchmark in protocol["benchmarks"]:
        expected = math.log(1.0 - benchmark["relative_decline"])
        assert benchmark["log_contrast"] == round(expected, 9)
    primary = [
        row
        for row in protocol["benchmarks"]
        if row["role"] == "primary_authenticated_2026_08_12_current_page"
    ]
    assert len(primary) == 1 and primary[0]["relative_decline"] == 0.19


def test_power_and_continuation_rules_are_numerical():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    simulation = protocol["simulation"]
    continuation = protocol["continuation"]
    assert simulation["minimum_repetitions"] >= 999
    assert simulation["target_power"] == 0.8
    assert continuation["detect_primary_benchmark_power_min"] == 0.8
    assert continuation["exclude_primary_benchmark_under_null_probability_min"] == 0.8
    assert continuation["extension_difference_log_points_min"] > 0
    assert continuation["crosswalk_magnitude_change_fraction"] > 0


def test_design_does_not_claim_same_estimand_or_preregistration():
    text = DESIGN.read_text(encoding="utf-8")
    assert "does **not** confirm or reject the ADP coefficient" in text
    assert "as the same estimand" in text
    assert "must be called a **design freeze**, not a prospective preregistration" in text
    assert "individual employment probability conditional on current occupation" in text


def test_current_benchmark_has_primary_locator_and_dallas_is_validation_only():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    locator = protocol["external_benchmark_locator"]
    assert locator["revision_date"] == "2026-08-12"
    assert "digitaleconomy.stanford.edu" in locator["url"]
    dallas = protocol["dallas_pipeline_check"]
    assert dallas["role"] == "pipeline_validation_not_primary_estimand"
    assert dallas["young_ages"] == [20, 24]
    assert dallas["prime_ages"] == [25, 55]
    assert dallas["moving_average_months"] == 12
    assert dallas["published_endpoints"] == {
        "2022-11": 16.36441,
        "2025-09": 15.53797,
    }
