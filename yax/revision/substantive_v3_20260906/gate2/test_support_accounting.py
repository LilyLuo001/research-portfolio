"""Pre-result regression tests for Gate 2 support and stock accounting."""
from __future__ import annotations

import copy
import importlib.util
import itertools
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
SPEC = importlib.util.spec_from_file_location(
    "run_support_accounting", HERE / "run_support_accounting.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


FAMILIES = [
    "11", "13", "15", "17", "19", "21", "23", "25", "27", "29", "31",
    "33", "35", "37", "39", "41", "43", "45", "47", "49", "51", "53",
]
MONTHS = ["2022-10", "2022-11", "2022-12", "2023-01", "2023-02"]


def fixture() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    assignments: list[tuple[str, str, int]] = []
    code = 1
    for family, quintiles in {
        "11": [1, 2], "13": [2, 3], "15": [3, 4], "17": [4, 5], "19": [1, 5],
    }.items():
        for quintile in quintiles:
            assignments.append((f"{code:04d}", family, quintile))
            code += 1
    for index, family in enumerate(FAMILIES[5:]):
        assignments.append((f"{code:04d}", family, index % 5 + 1))
        code += 1
    cell_rows = []
    member_rows = []
    for occ_index, (occ, family, quintile) in enumerate(assignments, start=1):
        webb = (occ_index - 10) / 10
        pre_weight = 0.0
        for month_index, month in enumerate(MONTHS):
            young = float(10 + occ_index + month_index)
            older = float(30 + 2 * occ_index + month_index)
            if month <= "2022-11":
                pre_weight += young + older
            cell_rows.append({
                "occ_code": occ,
                "month": month,
                "family": family,
                "young": young,
                "older": older,
                "beta_quintile": quintile,
                "webb_z": webb,
            })
        member_rows.append({
            "occupation_code": occ,
            "occupation_name": f"Occupation {occ}",
            "preperiod_weight": pre_weight,
            "rule_A_beta": quintile / 6 + occ_index / 10000,
            "beta_quintile": quintile,
            "webb_z": webb,
        })
    spec = {
        "support": {
            "expected_soc2_families": FAMILIES,
            "quintiles": [1, 2, 3, 4, 5],
            "expected_occupation_count": len(assignments),
        },
        "calendar": {
            "observed_window": ["2022-10", "2023-02"],
            "missing_months": [],
            "preperiod": ["2017-01", "2022-11"],
            "postperiod": ["2023-01", "2026-07"],
            "transition_month": "2022-12",
            "observed_month_count": len(MONTHS),
            "expected_period_month_counts": {"pre": 2, "post": 2},
        },
        "accounting": {
            "temporal_weights": "equal_observed_month",
            "closure_absolute_tolerance": 1e-12,
        },
    }
    return pd.DataFrame(cell_rows), pd.DataFrame(member_rows), spec


def validated_fixture() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    cells, membership, spec = fixture()
    return (*MODULE.validate_inputs(cells, membership, spec), spec)


def test_support_matrix_is_complete_connected_and_names_direct_tails():
    cells, membership, spec = validated_fixture()
    result = MODULE.build_support(cells, membership, spec)
    assert len(result["matrix"]) == 22 * 5
    assert result["graph"]["connected"] is True
    assert result["graph"]["incidence_rank"] == 4
    assert result["graph"]["graph_incidence_full_rank"] is True
    assert result["graph"]["direct_q1_q5_families"] == ["19"]
    assert set(result["direct"]["beta_quintile"]) == {1, 5}
    assert result["direct"]["occupation_name"].str.startswith("Occupation").all()
    assert result["edges"]["low_named_occupations"].str.len().gt(0).all()
    assert result["edges"]["high_named_occupations"].str.len().gt(0).all()
    assert np.isclose(result["matrix"]["national_preperiod_stock_share"].sum(), 1.0)
    supported = result["matrix"].loc[result["matrix"]["cell_has_support"]]
    family_sums = supported.groupby("family")["within_family_preperiod_stock_share"].sum()
    assert np.allclose(family_sums, 1.0)


def test_log_stock_identity_and_family_level_decomposition_close_exactly():
    cells, _, spec = validated_fixture()
    accounting = MODULE.build_accounting(cells, spec)
    assert accounting["tail"]["status"] == "PASS_EXACT_TAIL_LOG_STOCK_IDENTITY"
    assert abs(accounting["tail"]["closure_residual"]) <= 1e-12
    composition = MODULE.build_family_composition(accounting["work"], spec)
    assert composition["summary"]["status"] == (
        "PASS_Q1_Q5_FAMILY_COMPOSITION_DECOMPOSITIONS"
    )
    for row in composition["summary"]["quintiles"].values():
        assert abs(row["closure_residual"]) <= 1e-12
        assert np.isclose(
            row["national_level_ratio_change"],
            row["within_family_ratio_change_component"]
            + row["older_family_weight_change_component"],
        )
    for row in composition["log_shapley"]["quintiles"].values():
        assert abs(row["closure_residual"]) <= 1e-12
    assert np.isclose(
        composition["log_shapley"]["q5_minus_q1"]["log_ratio_change_q5_minus_q1"],
        accounting["tail"]["D_relative"],
    )


def test_positive_young_stock_with_zero_older_is_retained_as_boundary_mass():
    cells, _, spec = validated_fixture()
    mask = (
        cells["family"].eq("19")
        & cells["beta_quintile"].eq(5)
        & cells["month"].isin(["2023-01", "2023-02"])
    )
    cells.loc[mask, "older"] = 0.0
    accounting = MODULE.build_accounting(cells, spec)
    composition = MODULE.build_family_composition(accounting["work"], spec)
    audit_rows = pd.DataFrame(composition["zero_audit"]["rows"])
    target = audit_rows.loc[
        audit_rows["family"].eq("19")
        & audit_rows["beta_quintile"].eq(5)
        & audit_rows["period"].eq("post")
    ]
    assert target["classification"].eq("UNDEFINED_YOUNG_ONLY").all()
    q5 = composition["summary"]["quintiles"]["Q5"]
    assert q5["boundary_mass_post"] > 0
    assert abs(q5["closure_residual"]) <= 1e-12
    family_row = composition["rows"].loc[
        composition["rows"]["family"].eq("19")
        & composition["rows"]["beta_quintile"].eq(5)
    ].iloc[0]
    assert np.isnan(family_row["young_older_ratio_post"])
    log_q5 = composition["log_shapley"]["quintiles"]["Q5"]
    assert log_q5["boundary_mass_component"] != 0
    hybrids = log_q5["hybrid_log_values"]
    assert set(hybrids) == {
        "".join(map(str, bits)) for bits in itertools.product((0, 1), repeat=3)
    }
    assert all(math.isfinite(value) for value in hybrids.values())
    factors = ("composition", "within", "boundary")
    independent = {factor: 0.0 for factor in factors}
    for ordering in itertools.permutations(range(3)):
        state = [0, 0, 0]
        previous = hybrids["000"]
        for index in ordering:
            state[index] = 1
            current = hybrids["".join(map(str, state))]
            independent[factors[index]] += (current - previous) / 6.0
            previous = current
    assert np.isclose(independent["within"], log_q5["within_family_ratio_component"])
    assert np.isclose(independent["composition"], log_q5["older_family_weight_component"])
    assert np.isclose(independent["boundary"], log_q5["boundary_mass_component"])
    assert np.isclose(sum(independent.values()), hybrids["111"] - hybrids["000"])
    assert np.isclose(
        composition["log_shapley"]["q5_minus_q1"]["log_ratio_change_q5_minus_q1"],
        accounting["tail"]["D_relative"],
    )


def test_quintile_assignment_mismatch_fails_closed():
    cells, membership, spec = fixture()
    membership.loc[0, "beta_quintile"] = 5
    with pytest.raises(MODULE.Gate2Error, match="quintiles differ"):
        MODULE.validate_inputs(cells, membership, spec)


def test_wrong_missing_month_fails_closed():
    cells, membership, spec = fixture()
    mask = cells["occ_code"].eq(cells["occ_code"].iloc[0]) & cells["month"].eq("2023-02")
    cells.loc[mask, "month"] = "2023-03"
    with pytest.raises(MODULE.Gate2Error, match="exact signed calendar"):
        MODULE.validate_inputs(cells, membership, spec)


def test_authenticated_metadata_rejects_duplicate_model_ids():
    spec = {
        "authenticated_inputs": {
            "cells_receipt": {
                "expected_schema_version": "cells-v1",
                "expected_status": "PASS_CELLS",
            },
            "model_audit": {
                "expected_schema_version": "audit-v1",
                "expected_status": "PASS_AUDIT",
                "required_model_certification_status": "PASS_MODEL",
            },
        },
        "numerical_comparison": {"certified_models": ["pooled"]},
    }
    cells_receipt = {"schema_version": "cells-v1", "status": "PASS_CELLS"}
    model = {"model_id": "pooled", "a1_certification": {"status": "PASS_MODEL"}}
    audit = {
        "schema_version": "audit-v1",
        "status": "PASS_AUDIT",
        "models": [model, model],
    }
    with pytest.raises(MODULE.Gate2Error, match="duplicate model IDs"):
        MODULE.validate_authenticated_metadata(cells_receipt, audit, spec)


def test_preperiod_stock_mismatch_fails_at_gate1_tolerance():
    cells, membership, spec = validated_fixture()
    membership = membership.copy()
    membership.loc[0, "preperiod_weight"] += 1e-5
    with pytest.raises(MODULE.Gate2Error, match="preperiod stocks"):
        MODULE.build_support(cells, membership, spec)


def test_spec_identifier_changes_with_temporal_weighting():
    cells, membership, spec = fixture()
    full = {
        "schema_version": MODULE.SPEC_SCHEMA,
        "spec_id": "placeholder",
        "status": "test",
        "canonical_spec": {},
        "authenticated_inputs": {},
        "calendar": spec["calendar"],
        "support": spec["support"],
        "accounting": spec["accounting"],
        "numerical_comparison": {},
        "execution": {},
        "outputs": {},
    }
    first = MODULE.compute_spec_id(full)
    changed = copy.deepcopy(full)
    changed["accounting"]["temporal_weights"] = "stock_weighted_month"
    assert MODULE.compute_spec_id(changed) != first


def test_result_identifier_binds_spec_logical_key_and_artifact():
    first = MODULE.compute_result_id("spec-a", "SUPPORT_MATRIX.csv", "a" * 64)
    assert first != MODULE.compute_result_id("spec-b", "SUPPORT_MATRIX.csv", "a" * 64)
    assert first != MODULE.compute_result_id("spec-a", "SUPPORT_GRAPH.json", "a" * 64)
    assert first != MODULE.compute_result_id("spec-a", "SUPPORT_MATRIX.csv", "b" * 64)


def test_frozen_membership_repairs_historical_direct_tail_support():
    membership = pd.read_csv(
        REPO
        / "yax/revision/substantive_r3_20260905/rebuilt_baseline/results"
        / "REBUILT_TREATMENT_MEMBERSHIP.csv",
        dtype={"occupation_code": str},
    )
    family_map = pd.read_csv(
        REPO / "yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv",
        dtype={"census2018": str, "soc_major_group": str},
    )[["census2018", "soc_major_group"]]
    joined = membership.merge(
        family_map,
        left_on="occupation_code",
        right_on="census2018",
        how="left",
        validate="one_to_one",
    )
    assert joined["soc_major_group"].notna().all()
    direct_families = sorted(
        family
        for family, part in joined.groupby("soc_major_group")
        if {1, 5}.issubset(set(part["beta_quintile"]))
    )
    direct = joined.loc[
        joined["soc_major_group"].isin(direct_families)
        & joined["beta_quintile"].isin([1, 5])
    ]
    assert direct_families == ["27", "29", "31", "41"]
    assert len(direct) == 29
    assert int(joined.loc[joined["occupation_code"].eq("3620"), "beta_quintile"].iloc[0]) == 2
