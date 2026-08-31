import importlib.util
import pathlib
import sys

import numpy as np
import pandas as pd


ROOT = pathlib.Path(__file__).resolve().parents[2]
PHASE25 = ROOT / "yax/analysis/postoutcome_phase25_gate3"


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
    assert result["mean_absolute_im_rt_change"] == 0.5


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
