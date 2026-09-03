"""Enforcement tests for the frozen OCC2010/O*NET downstream standard."""

import importlib.util
import pathlib
import sys

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


bounds = _load("dose_bounds", "w2/crosswalk/dose_bounds.py")
audit = _load("audit_standard_freeze", "w2/crosswalk/audit_standard_freeze.py")


def _row(
    code,
    onet,
    weight,
    route_status,
    code_status,
    *,
    new="1000",
    pattern="11-1000",
    soc="11-1011",
    base=1.0,
):
    return {
        "cps_occ2010": code,
        "census_2018_occ": new,
        "base_route_weight": base,
        "soc_2018_pattern": pattern,
        "soc_2018": soc,
        "onet_soc2019": onet,
        "mapping_weight": weight,
        "route_status": route_status,
        "cps_code_status": code_status,
        "downstream_eligible": code_status == "resolved_employment_weighted",
    }


def test_only_whole_code_resolved_status_exposes_point_estimate():
    rows = [
        _row("0010", "11-1011.00", 0.6, "resolved_employment_weighted",
             "partial_unresolved"),
        _row("0010", "", 0.4, "unresolved_no_usable_onet",
             "partial_unresolved"),
    ]
    result = bounds.construct_cps_doses(
        rows, {"11-1011.00": bounds.DoseInterval.point(0.4)},
        expected_cps_codes={"0010", "7630"},
    )
    assert result["0010"].point_estimate is None
    assert result["0010"].dose_min is None
    assert result["0010"].downstream_eligible is False
    assert result["7630"].status == "absent_from_crosswalk"
    assert result["7630"].point_estimate is None


def test_equal_onet_children_produce_bounds_not_point():
    rows = [
        _row("0020", "11-1011.00", 0.5, "provisional_equal_within_soc",
             "provisional_equal_within_soc"),
        _row("0020", "11-1011.01", 0.5, "provisional_equal_within_soc",
             "provisional_equal_within_soc"),
    ]
    result = bounds.construct_cps_doses(rows, {
        "11-1011.00": bounds.DoseInterval.point(0.2),
        "11-1011.01": bounds.DoseInterval.point(0.8),
    })["0020"]
    assert result.diagnostic_center == pytest.approx(0.5)
    assert result.dose_min == pytest.approx(0.2)
    assert result.dose_max == pytest.approx(0.8)
    assert result.point_estimate is None
    assert result.downstream_eligible is False


def test_missing_oews_bounds_across_all_official_soc_children():
    rows = [
        _row("0030", "11-1011.00", 0.25,
             "provisional_equal_soc_missing_oews",
             "provisional_equal_within_soc", soc="11-1011"),
        _row("0030", "11-1021.00", 0.25,
             "provisional_equal_soc_missing_oews",
             "provisional_equal_within_soc", soc="11-1021"),
        _row("0030", "13-1011.00", 0.5, "resolved_employment_weighted",
             "provisional_equal_within_soc", new="2000", pattern="13-1011",
             soc="13-1011", base=0.5),
    ]
    result = bounds.construct_cps_doses(rows, {
        "11-1011.00": bounds.DoseInterval.point(0.0),
        "11-1021.00": bounds.DoseInterval.point(1.0),
        "13-1011.00": bounds.DoseInterval.point(0.4),
    })["0030"]
    assert result.diagnostic_center == pytest.approx(0.45)
    assert result.dose_min == pytest.approx(0.2)
    assert result.dose_max == pytest.approx(0.7)
    assert result.point_estimate is None


def test_legacy_equal_source_mix_is_a_diagnostic_center_only():
    rows = [
        {
            "onet_soc2019": "15-1252.00", "onet_soc2010": "15-1132.00",
            "task_id": "1", "legacy_task_time_share": 0.25,
            "legacy_source_weight": 0.5, "bounds_required": True,
        },
        {
            "onet_soc2019": "15-1252.00", "onet_soc2010": "15-1132.00",
            "task_id": "2", "legacy_task_time_share": 0.75,
            "legacy_source_weight": 0.5, "bounds_required": True,
        },
        {
            "onet_soc2019": "15-1252.00", "onet_soc2010": "15-1133.00",
            "task_id": "1", "legacy_task_time_share": 1.0,
            "legacy_source_weight": 0.5, "bounds_required": True,
        },
    ]
    intervals = bounds.legacy_profile_intervals(rows, {
        ("15-1132.00", "1"): 0.0,
        ("15-1132.00", "2"): 1.0,
        ("15-1133.00", "1"): 0.25,
    })
    interval = intervals["15-1252.00"]
    assert interval.center == pytest.approx(0.5)
    assert interval.minimum == pytest.approx(0.25)
    assert interval.maximum == pytest.approx(0.75)


def test_multiple_legacy_onet_children_are_bounded_as_one_soc_component():
    rows = [
        _row("0035", "15-1252.00", 0.5, "provisional_legacy_task_ratings",
             "provisional_equal_within_soc", pattern="15-1252", soc="15-1252"),
        _row("0035", "15-1252.01", 0.5, "provisional_legacy_task_ratings",
             "provisional_equal_within_soc", pattern="15-1252", soc="15-1252"),
    ]
    result = bounds.construct_cps_doses(rows, {
        "15-1252.00": bounds.DoseInterval(0.3, 0.1, 0.5),
        "15-1252.01": bounds.DoseInterval(0.7, 0.6, 0.8),
    })["0035"]
    assert result.diagnostic_center == pytest.approx(0.5)
    assert result.dose_min == pytest.approx(0.1)
    assert result.dose_max == pytest.approx(0.8)
    assert result.point_estimate is None


def test_resolved_code_rejects_bounded_onet_input():
    rows = [_row("0040", "11-1011.00", 1.0,
                 "resolved_employment_weighted", "resolved_employment_weighted")]
    with pytest.raises(ValueError, match="resolved CPS code"):
        bounds.construct_cps_doses(rows, {
            "11-1011.00": bounds.DoseInterval(0.5, 0.2, 0.8),
        })


def test_inconsistent_downstream_flag_fails_closed():
    row = _row("0050", "11-1011.00", 1.0,
               "provisional_legacy_task_ratings", "provisional_equal_within_soc")
    row["downstream_eligible"] = True
    with pytest.raises(ValueError, match="whole-code eligibility"):
        bounds.construct_cps_doses(
            [row], {"11-1011.00": bounds.DoseInterval.point(0.5)}
        )


def test_independent_audit_separates_mapped_from_fully_resolved():
    rows = [
        _row("0060", "11-1011.00", 0.75, "resolved_employment_weighted",
             "provisional_equal_within_soc"),
        _row("0060", "11-1011.01", 0.25, "provisional_equal_within_soc",
             "provisional_equal_within_soc"),
    ]
    metrics, errors = audit.audit_crosswalk(rows, {"0060": 9.0, "7630": 1.0})
    assert errors == []
    assert metrics["fully_resolved_component_mass_share"] == 0.675
    assert metrics["bounded_provisional_component_mass_share"] == 0.225
    assert metrics["mapped_component_mass_share"] == 0.9
    assert metrics["absent_component_mass_share"] == 0.1
    assert metrics["mapped_is_not_fully_resolved"] is True


def test_audit_rejects_point_flag_on_provisional_code():
    row = _row("0070", "11-1011.00", 1.0,
               "provisional_legacy_task_ratings", "provisional_equal_within_soc")
    row["downstream_eligible"] = True
    metrics, errors = audit.audit_crosswalk([row], {"0070": 1.0})
    assert metrics["eligibility_violations"] == 1
    assert "crosswalk violates fail-closed whole-code eligibility" in errors
