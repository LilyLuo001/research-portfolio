"""Validate the authoritative aggregate-only Gate 2 support/accounting run."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs" / "gate2_support_accounting_authoritative_20260907"
SPEC = ROOT / "gate2" / "SUPPORT_ACCOUNTING_SPEC.json"
CODE = ROOT / "gate2" / "run_support_accounting.py"
EXPECTED_RECEIPT_SHA256 = (
    "5c39aaedfe33182a578a21c63047bef6c548be53c31b4ca682ca2246d165e9e1"
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def result_id(spec_id: str, logical_key: str, artifact_sha256: str) -> str:
    payload = {
        "artifact_sha256": artifact_sha256,
        "logical_key": logical_key,
        "spec_id": spec_id,
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return "yaxresult_v1_" + hashlib.sha256(encoded).hexdigest()


def test_gate2_receipt_byte_binds_all_results_and_signed_code():
    receipt_path = RUN / "EXECUTION_RECEIPT.json"
    receipt = load(receipt_path)
    assert digest(receipt_path) == EXPECTED_RECEIPT_SHA256
    assert receipt["status"] == "PASS_GATE2_SUPPORT_AND_ACCOUNTING"
    assert receipt["schema_version"] == "yax-gate2-support-accounting-receipt-v1"
    assert receipt["spec_sha256"] == digest(SPEC)
    assert receipt["code_sha256"] == digest(CODE)
    assert receipt["protected_row_level_microdata_opened"] is False
    assert receipt["authenticated_aggregate_cells_opened"] is True
    assert len(receipt["output_hashes"]) == 12
    assert set(receipt["output_hashes"]) == set(receipt["result_ids"])
    for name, expected in receipt["output_hashes"].items():
        assert digest(RUN / name) == expected
        assert receipt["result_ids"][name] == result_id(
            receipt["spec_id"], name, expected
        )


def test_support_matrix_topology_and_direct_tail_membership():
    matrix = pd.read_csv(RUN / "SUPPORT_MATRIX.csv", dtype={"family": str})
    direct = pd.read_csv(
        RUN / "DIRECT_TAIL_MEMBERSHIP.csv",
        dtype={"family": str, "occupation_code": str},
    )
    graph = load(RUN / "SUPPORT_GRAPH.json")
    assert len(matrix) == 110
    assert matrix["family"].nunique() == 22
    assert set(matrix["beta_quintile"]) == {1, 2, 3, 4, 5}
    assert np.isclose(matrix["national_preperiod_stock_share"].sum(), 1.0)
    supported = matrix.loc[matrix["cell_has_support"]]
    assert np.allclose(
        supported.groupby("family")["within_family_preperiod_stock_share"].sum(),
        1.0,
    )
    assert graph["status"] == "PASS_CONNECTED_QUINTILE_SUPPORT_TOPOLOGY"
    assert graph["connected"] is True
    assert graph["incidence_rank"] == 4
    assert graph["graph_incidence_full_rank"] is True
    assert graph["represented_edge_count"] == 10
    assert set(graph["direct_q1_q5_families"]) == {"27", "29", "31", "41"}
    assert len(direct) == 29
    assert set(direct["family"]) == {"27", "29", "31", "41"}
    assert set(direct["beta_quintile"]) == {1, 5}
    assert "within_family_tail_preperiod_stock_share" not in direct.columns
    assert np.allclose(
        direct.groupby(["family", "beta_quintile"])[
            "within_family_quintile_preperiod_stock_share"
        ].sum(),
        1.0,
    )
    assert np.allclose(
        direct.groupby("family")[
            "within_direct_family_tails_preperiod_stock_share"
        ].sum(),
        1.0,
    )


def test_tail_stock_identity_and_regression_comparisons_recompute():
    tail = load(RUN / "TAIL_LOG_STOCK_ACCOUNTING.json")
    stocks = tail["stocks"]
    young = math.log(stocks["N_young_q5_post"] / stocks["N_young_q5_pre"]) - math.log(
        stocks["N_young_q1_post"] / stocks["N_young_q1_pre"]
    )
    older = math.log(stocks["N_older_q5_post"] / stocks["N_older_q5_pre"]) - math.log(
        stocks["N_older_q1_post"] / stocks["N_older_q1_pre"]
    )
    relative = young - older
    assert np.isclose(young, tail["D_young"], atol=1e-14, rtol=0)
    assert np.isclose(older, tail["D_older"], atol=1e-14, rtol=0)
    assert np.isclose(relative, tail["D_relative"], atol=1e-14, rtol=0)
    assert abs(tail["closure_residual"]) <= tail["closure_absolute_tolerance"]
    for model, target in tail["certified_grouped_binomial_targets"].items():
        assert np.isclose(
            tail["accounting_minus_grouped_binomial"][model],
            relative - target,
            atol=1e-14,
            rtol=0,
        )


def test_level_log_and_zero_denominator_accounting_close():
    level = load(RUN / "FAMILY_COMPOSITION_SUMMARY.json")
    log = load(RUN / "LOG_SHAPLEY_DECOMPOSITION.json")
    zero = load(RUN / "ZERO_DENOMINATOR_AUDIT.json")
    tail = load(RUN / "TAIL_LOG_STOCK_ACCOUNTING.json")
    for row in level["quintiles"].values():
        total = (
            row["within_family_ratio_change_component"]
            + row["older_family_weight_change_component"]
            + row["boundary_mass_change_component"]
        )
        assert np.isclose(row["national_level_ratio_change"], total, atol=1e-14, rtol=0)
        assert abs(row["closure_residual"]) <= row["closure_absolute_tolerance"]
    level_difference = level["q5_minus_q1"]
    assert np.isclose(
        level_difference["national_level_ratio_change_q5_minus_q1"],
        level_difference["within_family_ratio_component_q5_minus_q1"]
        + level_difference["older_family_weight_component_q5_minus_q1"]
        + level_difference["boundary_mass_component_q5_minus_q1"],
        atol=1e-14,
        rtol=0,
    )
    for row in log["quintiles"].values():
        total = (
            row["within_family_ratio_component"]
            + row["older_family_weight_component"]
            + row["boundary_mass_component"]
        )
        assert np.isclose(row["log_ratio_change"], total, atol=1e-14, rtol=0)
        assert np.isclose(
            row["log_ratio_change"],
            row["hybrid_log_values"]["111"] - row["hybrid_log_values"]["000"],
            atol=1e-14,
            rtol=0,
        )
        assert len(row["hybrid_log_values"]) == 8
    log_difference = log["q5_minus_q1"]
    assert np.isclose(
        log_difference["log_ratio_change_q5_minus_q1"],
        log_difference["within_family_ratio_component_q5_minus_q1"]
        + log_difference["older_family_weight_component_q5_minus_q1"]
        + log_difference["boundary_mass_component_q5_minus_q1"],
        atol=1e-14,
        rtol=0,
    )
    assert np.isclose(
        log_difference["log_ratio_change_q5_minus_q1"],
        tail["D_relative"],
        atol=1e-14,
        rtol=0,
    )
    assert zero["classification_counts"] == {
        "STRUCTURAL_ABSENCE": 36,
        "VALID_POSITIVE": 52,
    }
    assert sum(zero["classification_counts"].values()) == 88


def test_public_package_contains_no_private_paths_or_occupation_month_cells():
    forbidden = (
        "/projectnb/",
        "/Users/",
        "scc1.bu.edu",
        "IPUMS API",
        "BEA API key",
        "ghp_",
        "github_pat_",
    )
    for path in RUN.iterdir():
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            assert not any(token in text for token in forbidden), path.name
    for path in RUN.glob("*.csv"):
        columns = set(pd.read_csv(path, nrows=0).columns)
        assert not ({"occ_code", "month"} <= columns), path.name
        assert not ({"occupation_code", "month"} <= columns), path.name
