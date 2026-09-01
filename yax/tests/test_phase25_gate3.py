import hashlib
import importlib.util
import json
import pathlib
import sys

import numpy as np
import pandas as pd


ROOT = pathlib.Path(__file__).resolve().parents[2]
PHASE25 = ROOT / "yax/analysis/postoutcome_phase25_gate3"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_module():
    path = PHASE25 / "run_phase25_reallocation_validity.py"
    spec = importlib.util.spec_from_file_location("phase25_reallocation_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_pair_specific_support_uses_only_the_named_pair():
    module = load_module()
    frame = pd.DataFrame({"LNKFW1MWT": [1.0, 2.0, 3.0, 4.0]})
    for measure in module.MEASURES:
        frame[f"available__{measure}"] = True
        frame[f"sign__{measure}"] = 1.0
    # Row 1 lacks an irrelevant third architecture and must remain in the
    # first named pair's support. Row 2 lacks one member of that named pair.
    frame.loc[1, "available__dv_rating_gamma"] = False
    frame.loc[2, "available__aioe_admin_equal"] = False
    frame["sixway_included"] = frame[
        [f"available__{measure}" for measure in module.MEASURES]
    ].all(axis=1)

    support, _ = module.pair_rows(frame)
    row = next(
        item for item in support
        if item["measure_1"] == "aioe_admin_equal"
        and item["measure_2"] == "aioe_ability_direct"
    )
    assert row["pair_support_raw"] == 3
    assert row["pair_support_weight"] == 7.0
    assert row["sixway_support_raw"] == 2


def test_self_match_repair_is_reproducible_and_removes_all_false_switches():
    module = load_module()
    origin = np.array(["a", "a", "b", "b", "c", "c"])
    destination = origin.copy()
    first, first_repairs = module.repair_self_matches(
        origin, destination, np.random.default_rng(17)
    )
    second, second_repairs = module.repair_self_matches(
        origin, destination, np.random.default_rng(17)
    )
    assert np.array_equal(first, second)
    assert first_repairs == second_repairs
    assert not np.any(origin == first)


def test_weighted_marginal_benchmark_is_seed_reproducible(monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "BENCHMARK_DRAWS", 19)
    monkeypatch.setattr(module, "BENCHMARK_PSEUDO_UNITS", 600)
    frame = pd.DataFrame({
        "origin_code": ["a", "b", "c"],
        "destination_code": ["b", "c", "a"],
        "LNKFW1MWT": [1.0, 1.0, 1.0],
        "opposite_direction_conflict": [True, False, True],
    })
    maps = {}
    for index, measure in enumerate(module.MEASURES):
        if index % 2:
            maps[measure] = {"a": 0.0, "b": 2.0, "c": 1.0}
        else:
            maps[measure] = {"a": 0.0, "b": 1.0, "c": 2.0}

    first = module.benchmark_one(frame, maps, "primary")
    second = module.benchmark_one(frame, maps, "primary")
    assert first["benchmark_draws"] == second["benchmark_draws"]
    assert first["false_self_switches_after_repair"] == 0
    assert first["draws"] == 19


def test_phase2_commit_reconciliation_names_result_and_seal_commits():
    text = (PHASE25 / "YAX_PHASE25_PHASE2_COMMIT_RECONCILIATION.md").read_text()
    assert "8ebef7c4f443b5f9300ccfa7d1761f822215d790" in text
    assert "9772a494afc2c1af5630979631c4b67640f4ff3f" in text
    assert "true final Phase-2 commit" in text


def test_onet_task_matching_distinguishes_revision_and_renumbering():
    path = PHASE25 / "run_onet_dynamic_task_feasibility.py"
    spec = importlib.util.spec_from_file_location("phase25_onet_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    class ArchiveNames:
        @staticmethod
        def namelist():
            return ["db/Task Statements.txt", "db/Green Task Statements.txt"]

    assert module.find_member(ArchiveNames(), "Task Statements.txt") == "db/Task Statements.txt"
    left_tasks = pd.DataFrame({
        "occ": ["11-0000.00", "11-0000.00"],
        "task_id": ["1", "2"],
        "task_text": ["Do reports.", "Meet clients."],
        "task_type": ["Core", "Core"],
    })
    right_tasks = pd.DataFrame({
        "occ": ["11-0000.00", "11-0000.00"],
        "task_id": ["1", "3"],
        "task_text": ["Prepare reports.", "Meet clients."],
        "task_type": ["Core", "Core"],
    })
    left_ratings = pd.DataFrame({
        "occ": ["11-0000.00"], "task_id": ["1"], "scale_id": ["IM"],
        "data_value": [3.0],
    })
    right_ratings = pd.DataFrame({
        "occ": ["11-0000.00"], "task_id": ["1"], "scale_id": ["IM"],
        "data_value": [3.5],
    })
    result = module.transition_metrics(
        left_tasks, right_tasks, left_ratings, right_ratings,
        "x", "y", "2020-01", "2021-01",
    )
    assert result["task_id_wording_revisions"] == 1
    assert result["apparent_task_id_renumbering_same_occ_text"] == 1
    assert result["task_additions"] == result["task_deletions"] == 1
    assert result["mean_absolute_importance_change"] == 0.5
    assert result["comparable_importance_ratings"] == 1
    assert result["comparable_relevance_ratings"] == 0


def test_factor_family_balancing_assigns_equal_total_family_weight():
    path = PHASE25 / "run_shared_component_feasibility.py"
    spec = importlib.util.spec_from_file_location("phase25_factor_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    frame = pd.DataFrame({
        "a1": [0.0, 1.0, 2.0, 4.0], "a2": [0.0, 1.0, 2.0, 4.0],
        "a3": [0.0, 1.0, 2.0, 4.0], "e1": [4.0, 2.0, 1.0, 0.0],
    })
    weights = np.array([1.0, 2.0, 3.0, 4.0])
    aioe, eloundou, shared = module.family_balanced_shared(
        frame, weights, ["a1", "a2", "a3"], ["e1"]
    )
    expected = module.weighted_standardize((aioe + eloundou) / 2, weights)
    assert np.allclose(shared, expected)
    assert np.isclose(np.average(shared, weights=weights), 0.0)
    assert np.isclose(np.average(shared ** 2, weights=weights), 1.0)


def test_phase25_aggregate_outputs_preserve_support_and_benchmark_rules():
    support = pd.read_csv(PHASE25 / "YAX_PHASE25_PAIR_SPECIFIC_SUPPORT.csv")
    agreement = pd.read_csv(PHASE25 / "YAX_PHASE25_PAIR_SPECIFIC_AGREEMENT.csv")
    receipt = json.loads((PHASE25 / "YAX_PHASE25_REALLOCATION_EXECUTION_RECEIPT.json").read_text())
    benchmark = json.loads((PHASE25 / "YAX_PHASE25_REALIZED_VS_MATCHED_BENCHMARK.json").read_text())
    assert len(support) == len(agreement) == 15
    assert receipt["switches"] == 186_370
    assert receipt["sixway_switches"] == 108_500
    assert support.pair_support_raw.ge(support.sixway_support_raw).all()
    assert benchmark["primary"]["draws"] == 999
    assert benchmark["primary"]["seed"] == 2026090101
    assert benchmark["primary"]["false_self_switches_after_repair"] == 0
    assert benchmark["persistence_sensitivity"]["false_self_switches_after_repair"] == 0
    assert benchmark["primary"]["classification"] == "BENCH-B1"


def test_onet_outputs_are_archive_only_and_hash_sealed():
    receipt = json.loads((PHASE25 / "YAX_ONET_DYNAMIC_TASK_EXECUTION_RECEIPT.json").read_text())
    assert receipt["archives"] == 37
    assert receipt["archive_versions"][0] == "22.0"
    assert receipt["archive_versions"][-1] == "31.0"
    assert receipt["labor_outcome_files_read"] == []
    assert receipt["labor_outcome_regressions"] == []
    for name, expected in receipt["outputs"].items():
        assert sha256(PHASE25 / name) == expected
    coverage = pd.read_csv(PHASE25 / "YAX_ONET_TASK_VINTAGE_COVERAGE.csv")
    current = coverage.loc[coverage.last_archive_release.astype(str).eq("31.0")]
    assert len(current) == 923
    assert int(current.has_multiple_pre_and_post_2022.sum()) == 267


def test_factor_outputs_balance_families_and_use_no_labor_outcomes():
    receipt = json.loads((PHASE25 / "YAX_SHARED_COMPONENT_EXECUTION_RECEIPT.json").read_text())
    assert receipt["weighting_rule"].endswith("each family gets total weight 1/2")
    assert receipt["labor_outcomes_read"] == []
    assert receipt["labor_outcome_regressions"] == []
    assert receipt["occupations"] == 463
    for name, expected in receipt["outputs"].items():
        assert sha256(PHASE25 / name) == expected
    stability = pd.read_csv(PHASE25 / "YAX_EXPOSURE_FACTOR_STABILITY.csv")
    lomo = stability.loc[stability.diagnostic.eq("leave_one_measure_out")]
    assert len(lomo) == 6
    assert lomo.correlation_with_full_family_balanced_component.min() > 0.98
    leave_family = stability.loc[stability.diagnostic.eq("leave_one_family_out_limitation")]
    assert not leave_family.identifies_cross_family_shared_dimension.any()


def test_gate3_selects_exactly_one_path_and_prohibits_new_outcome_models():
    memo = (PHASE25 / "YAX_GATE3_DECISION_MEMO.md").read_text()
    paths = ["PATH-G3-A", "PATH-G3-B", "PATH-G3-C", "PATH-G3-D"]
    assert sum(path in memo for path in paths) == 1
    assert "PATH-G3-B" in memo
    assert "No new labor-outcome regressions were executed." in memo
