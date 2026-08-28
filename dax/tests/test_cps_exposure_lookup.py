"""Tests for the CPS occupation-vintage exposure lookup."""

import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest


MODULE = (
    Path(__file__).resolve().parents[2]
    / "yax/measurement/build_cps_exposure_lookup.py"
)
SPEC = importlib.util.spec_from_file_location("build_cps_exposure_lookup", MODULE)
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


def exposure(values):
    assert len(values) == len(GATE.VARIANTS)
    return {
        variant: value for variant, value in zip(GATE.VARIANTS, values)
    }


def test_route_weights_are_used_without_renormalization():
    rows = {
        "1001": exposure((1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 0.0)),
        "1002": exposure((3.0, 6.0, 9.0, 8.0, 10.0, 12.0, 1.0)),
    }
    result = GATE.aggregate_routes(
        "0100",
        [("1001", "11-1111", 0.25), ("1002", "11-1112", 0.75)],
        rows,
        "test",
    )
    assert result["aioe_admin_equal"] == pytest.approx(2.5)
    assert result["aioe_ability_direct"] == pytest.approx(5.0)
    assert result["aioe_oews2018_source_weighted"] == pytest.approx(7.5)
    assert result["aioe_admin_equal_covered_route_mass"] == pytest.approx(1.0)


def test_missing_child_fails_closed_and_keeps_partial_sum_visible():
    rows = {"1001": exposure((2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 1.0))}
    result = GATE.aggregate_routes(
        "0100",
        [("1001", "11-1111", 0.25), ("1002", "11-1112", 0.75)],
        rows,
        "test",
    )
    assert pd.isna(result["aioe_admin_equal"])
    assert result["aioe_admin_equal_covered_route_mass"] == pytest.approx(0.25)
    assert result["aioe_admin_equal_partial_weighted_sum"] == pytest.approx(0.5)


def test_target_soc_partial_coverage_propagates_through_census_bridge():
    row = exposure((1.0, 2.0, 3.0, None, 5.0, 6.0, 0.5))
    row["dv_rating_alpha_target_soc_covered_weight"] = 0.8
    row["dv_rating_alpha_target_soc_partial_weighted_sum"] = 0.4
    result = GATE.aggregate_routes(
        "0100", [("1001", "11-1111", 1.0)], {"1001": row}, "test"
    )
    assert pd.isna(result["dv_rating_alpha"])
    assert result["dv_rating_alpha_covered_route_mass"] == pytest.approx(0.8)
    assert result["dv_rating_alpha_partial_weighted_sum"] == pytest.approx(0.4)


def test_variants_are_never_collapsed_into_one_measure():
    result = GATE.aggregate_routes(
        "0100",
        [("1001", "11-1111", 1.0)],
        {"1001": exposure((1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 0.5))},
        "test",
    )
    assert [result[name] for name in GATE.VARIANTS] == [
        1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 0.5
    ]


def test_ambiguity_is_explicit():
    assert GATE.ambiguity_status([1.0]) == "one_to_one"
    assert GATE.ambiguity_status([0.95, 0.05]) == "one_to_many_dominant_route"
    assert GATE.ambiguity_status([0.6, 0.4]) == "one_to_many_diffuse"


def test_output_design_keeps_direct_and_harmonized_roles_separate(monkeypatch):
    variants = pd.DataFrame(
        {
            "census_2018": ["1001"],
            "aioe_admin_equal": [1.0],
            "aioe_ability_direct": [2.0],
            "aioe_oews2018_source_weighted": [3.0],
            "dv_rating_alpha": [4.0],
            "dv_rating_beta": [5.0],
            "dv_rating_gamma": [6.0],
            "dingel_neiman_telework": [0.5],
        }
    )
    monkeypatch.setattr(GATE, "read_total_conversion_rates", lambda _: {})
    monkeypatch.setattr(
        GATE,
        "read_census_crosswalk",
        lambda _: ({"0100": ("1001", "11-1111")}, {"1001": "11-1111"}),
    )
    monkeypatch.setattr(GATE, "read_ipums_occ2010_crosswalk", lambda _: {})
    bridge, lookup = GATE.build_tables(
        variants, Path("rates"), Path("census"), Path("ipums")
    )
    roles = set(lookup.lookup_role)
    assert roles == {
        "raw_occ_main_2017_2019",
        "raw_occ_main_2020_plus",
        "occ2010_sensitivity_all_years",
    }
    direct = lookup.loc[lookup.lookup_role.eq("raw_occ_main_2020_plus")].iloc[0]
    assert direct.occ_code == "1001"
    assert direct.aioe_ability_direct == 2.0
    assert direct.dv_rating_beta == 5.0
    assert direct.dingel_neiman_telework == 0.5
    assert bridge.bridge_weight.sum() == pytest.approx(1.0)


def test_committed_bridge_weights_sum_to_one():
    path = MODULE.with_name("CENSUS_OCC2010_TO_2018_BRIDGE.csv")
    if not path.exists():
        pytest.skip("generated bridge not present")
    bridge = pd.read_csv(path, dtype={"census_2010": str, "census_2018": str})
    totals = bridge.groupby("census_2010").bridge_weight.sum()
    assert (totals - 1.0).abs().max() < 1e-9
    assert bridge.loc[bridge.n_routes.gt(1), "ambiguity_status"].str.startswith(
        "one_to_many"
    ).all()


def test_committed_lookup_is_exhaustive_and_fail_closed():
    path = MODULE.with_name("CPS_OCCUPATION_EXPOSURE_LOOKUP.csv")
    if not path.exists():
        pytest.skip("generated lookup not present")
    lookup = pd.read_csv(path, dtype={"occ_code": str})
    assert not lookup.duplicated(["lookup_role", "occ_code"]).any()
    direct = lookup.loc[lookup.lookup_role.eq("raw_occ_main_2020_plus")]
    assert direct.ambiguity_status.eq("direct_observed_code").all()
    for variant in GATE.VARIANTS:
        mass = lookup[f"{variant}_covered_route_mass"]
        assert mass.between(0, 1).all()
        incomplete = mass.lt(1 - 1e-9)
        assert lookup.loc[incomplete, variant].isna().all()
    # The variants remain genuinely distinct columns, not aliases.
    complete = direct[list(GATE.VARIANTS)].dropna()
    assert not complete[GATE.VARIANTS[0]].equals(complete[GATE.VARIANTS[1]])


def test_committed_receipt_exposes_machine_gate_contract():
    path = MODULE.with_name("CPS_OCCUPATION_EXPOSURE_LOOKUP_RECEIPT.json")
    if not path.exists():
        pytest.skip("generated receipt not present")
    receipt = json.loads(path.read_text())
    assert receipt["status"] == "PASS"
    assert receipt["gate"] == "vintage_aware_cps_occupation_exposure_lookup"
    assert receipt["outcome_fields_read"] is False
