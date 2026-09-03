"""Regression tests for component-level OCC2010 crosswalk coverage."""

import importlib.util
import pathlib


MODULE = (pathlib.Path(__file__).resolve().parents[1]
          / "w2" / "crosswalk" / "build_occ2010_crosswalk.py")
SPEC = importlib.util.spec_from_file_location("build_occ2010_crosswalk", MODULE)
assert SPEC and SPEC.loader
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


def test_unusable_soc_child_does_not_delete_usable_component():
    rows = builder.compose_rows(
        routes={"4020": [("4020", "35-2010", 1.0)]},
        onet_by_soc={"35-2011": ["35-2011.00"]},
        oews_employment={"35-2011": 80.0, "35-2019": 20.0},
        all_onet_by_soc={
            "35-2011": ["35-2011.00"],
            "35-2019": ["35-2019.00"],
        },
    )
    assert sum(float(row["mapping_weight"]) for row in rows) == 1.0
    resolved = [row for row in rows if row["route_status"] == "resolved_employment_weighted"]
    missing = [row for row in rows if row["route_status"] == "unresolved_no_usable_onet"]
    assert len(resolved) == len(missing) == 1
    assert resolved[0]["mapping_weight"] == 0.8
    assert missing[0]["mapping_weight"] == 0.2
    assert all(row["cps_code_status"] == "partial_unresolved" for row in rows)
    assert all(row["downstream_eligible"] is False for row in rows)


def test_missing_oews_uses_bounded_equal_soc_components():
    rows = builder.compose_rows(
        routes={"2540": [("2545", "25-9040", 1.0)]},
        onet_by_soc={"25-9044": ["25-9044.00"]},
        oews_employment={"25-9044": 100.0},
        all_onet_by_soc={
            "25-9042": ["25-9042.00"],
            "25-9044": ["25-9044.00"],
        },
    )
    assert len(rows) == 2
    assert [row["mapping_weight"] for row in rows] == [0.5, 0.5]
    assert {row["route_status"] for row in rows} == {
        "unresolved_no_usable_onet", "provisional_equal_soc_missing_oews"
    }
    assert sum(float(row["mapping_weight"]) for row in rows) == 1.0


def test_equal_onet_children_are_provisional_and_bounded():
    rows = builder.compose_rows(
        routes={"3255": [("3255", "29-1141", 1.0)]},
        onet_by_soc={"29-1141": ["29-1141.00", "29-1141.01"]},
        oews_employment={},
        all_onet_by_soc={"29-1141": ["29-1141.00", "29-1141.01"]},
    )
    assert [row["mapping_weight"] for row in rows] == [0.5, 0.5]
    assert all(row["route_status"] == "provisional_equal_within_soc" for row in rows)
    assert all(row["cps_code_status"] == "provisional_equal_within_soc" for row in rows)


def test_legacy_task_rating_bridge_is_always_provisional():
    rows = builder.compose_rows(
        routes={"1020": [("1021", "15-1252", 1.0)]},
        onet_by_soc={"15-1252": ["15-1252.00"]},
        oews_employment={},
        all_onet_by_soc={"15-1252": ["15-1252.00"]},
        legacy_onet_codes={"15-1252.00"},
    )
    assert len(rows) == 1
    assert rows[0]["route_status"] == "provisional_legacy_task_ratings"
    assert "onet25_legacy_bridge" in rows[0]["allocation_method"]


def test_component_coverage_counts_resolved_and_provisional_only():
    rows = [
        {"cps_occ2010": "1", "route_status": "resolved_employment_weighted",
         "mapping_weight": 0.6},
        {"cps_occ2010": "1", "route_status": "provisional_equal_within_soc",
         "mapping_weight": 0.3},
        {"cps_occ2010": "1", "route_status": "unresolved_no_usable_onet",
         "mapping_weight": 0.1},
    ]
    shares = builder.component_weight_mass_shares(rows, {"1": 10.0, "2": 10.0})
    assert shares == {
        "resolved": 0.3,
        "provisional_equal_within_soc": 0.15,
        "unresolved_no_usable_onet": 0.05,
        "absent_from_crosswalk": 0.5,
    }
