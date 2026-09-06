import importlib.util
import json
import pathlib
import sys

import numpy as np
import pandas as pd


ROOT = pathlib.Path(__file__).resolve().parents[2]
PHASE3 = ROOT / "yax/analysis/postoutcome_phase3_final"
CORE_PATH = PHASE3 / "phase3_core.py"
SPEC = importlib.util.spec_from_file_location("yax_phase3_core_test", CORE_PATH)
CORE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CORE
SPEC.loader.exec_module(CORE)


def toy_exposures():
    values = np.array([0.0, 1.0, 3.0, 6.0])
    frame = pd.DataFrame({
        measure: values * (index + 1) + index
        for index, measure in enumerate(CORE.MEASURES)
    })
    return frame, np.array([1.0, 2.0, 3.0, 4.0])


def test_protected_tags_are_annotated_objects_with_unchanged_peeled_commits():
    receipt = json.loads((PHASE3 / "YAX_PHASE3_PROTECTED_REF_RECEIPT.json").read_text())
    assert receipt["integrity_gate"] == "PASS"
    assert receipt["actual_ref_movement"] is False
    assert receipt["protected_tags"]["v1.1-design-freeze"]["object_type"] == "tag"
    assert receipt["protected_tags"]["v1.1-design-freeze"]["peeled_commit"] == (
        "22fbf7924809b7a535e31ae0ab68f5b113ce8078"
    )
    assert receipt["protected_tags"]["v1.1-confirmatory-results"]["peeled_commit"] == (
        "b16109482c3bf5ca176f6f08976e120b04769945"
    )


def test_family_centroid_component_is_exact_and_mechanically_oriented():
    frame, weights = toy_exposures()
    moments = CORE.fit_component_moments(frame, weights)
    result = CORE.component_arrays(frame, moments)
    z = np.column_stack([
        (frame[measure] - moments.mean[measure]) / moments.sd[measure]
        for measure in CORE.MEASURES
    ])
    expected_a = z[:, :3].mean(axis=1)
    expected_e = z[:, 3:].mean(axis=1)
    assert np.allclose(result.A, expected_a)
    assert np.allclose(result.E, expected_e)
    assert np.allclose(result.F, (expected_a + expected_e) / 2)
    assert np.allclose(result.G, (expected_a - expected_e) / 2)
    for index, measure in enumerate(CORE.MEASURES):
        assert np.allclose(result[f"R__{measure}"], z[:, index] - result.F)


def test_component_maps_apply_reference_moments_without_restandardizing_target():
    frame, weights = toy_exposures()
    moments = CORE.fit_component_moments(frame, weights)
    maps = {
        measure: {f"{index:04d}": value for index, value in enumerate(frame[measure])}
        for measure in CORE.MEASURES
    }
    mapped = CORE.component_maps(maps, moments)
    direct = CORE.component_arrays(frame, moments)
    assert np.allclose([mapped["F"][f"{i:04d}"] for i in range(4)], direct.F)
    assert np.allclose([mapped["G"][f"{i:04d}"] for i in range(4)], direct.G)


def test_weighted_bins_keep_ties_and_use_frozen_cut_values():
    values = np.array([0.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
    weights = np.ones(len(values))
    bins, cuts = CORE.tie_preserving_weighted_bins(values, weights)
    assert bins[0] == bins[1]
    assert len(np.unique(cuts)) == 4
    assert bins.min() == 1 and bins.max() == 5
    reapplied = np.searchsorted(cuts, values, side="left") + 1
    assert np.array_equal(bins, reapplied)


def test_hard_rematch_preserves_each_stratum_margin_and_removes_self_pairs():
    origin = np.array([0, 0, 1, 1, 2, 2, 3, 3])
    destination = np.array([1, 1, 0, 0, 3, 3, 2, 2])
    groups = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    rematched, _, _ = CORE.repair_self_matches_within_groups(
        origin, destination, groups, np.random.default_rng(2026090301)
    )
    assert not np.any(origin == rematched)
    for group in np.unique(groups):
        mask = groups == group
        assert sorted(destination[mask].tolist()) == sorted(rematched[mask].tolist())


def test_hamilton_counts_are_exact_and_deterministic():
    first, expected = CORE.hamilton_counts(np.array([1.0, 2.0, 3.0]), 101)
    second, _ = CORE.hamilton_counts(np.array([1.0, 2.0, 3.0]), 101)
    assert first.sum() == 101
    assert np.array_equal(first, second)
    assert np.max(np.abs(first - expected)) < 1


def test_frozen_decision_thresholds_cover_all_paths_without_search():
    assert CORE.classify_hard_benchmark(0.05, 0.53, 0.49) == "HB-A"
    assert CORE.classify_hard_benchmark(0.02, 0.53, 0.52) == "HB-B"
    assert CORE.classify_hard_benchmark(0.005, 0.53, 0.52) == "HB-C"
    assert CORE.classify_reallocation_component(0.16, 1.30, 0.11) == "SC-R1"
    assert CORE.classify_reallocation_component(0.08, 1.15, 0.02) == "SC-R2"
    assert CORE.classify_reallocation_component(0.01, 1.05, -0.01) == "SC-R3"
    assert CORE.classify_shared_stock(-0.10, -0.01) == "SC-A"
    assert CORE.classify_shared_stock(-0.05, -0.01) == "SC-B"
    assert CORE.classify_shared_stock(0.01, 0.05) == "SC-C"
    assert CORE.select_phase3_path("HB-A", "SC-R1", "SC-A") == "PATH-P3-A"
    assert CORE.select_phase3_path("HB-B", "SC-R2", "SC-B") == "PATH-P3-B"
    assert CORE.select_phase3_path("HB-C", "SC-R1", "SC-A") == "PATH-P3-C"


def test_joint_upper_bounds_use_common_draw_matrix_and_do_not_pool_parameters():
    estimates = np.array([-0.2, -0.1])
    ses = np.array([0.05, 0.04])
    shifts = np.array([
        [-0.02, -0.01], [0.01, 0.02], [-0.01, 0.01], [0.02, -0.02],
    ])
    result = CORE.simultaneous_one_sided_upper_bounds(estimates, ses, shifts, 0.75)
    assert result["upper_bounds"].shape == (2,)
    assert len(result["marginal_one_sided_p"]) == 2
    assert result["intersection_union_p"] == max(result["marginal_one_sided_p"])
    assert result["all_upper_bounds_negative"]


def test_plan_authorizes_exactly_one_new_stock_model_and_no_rescue_search():
    plan = (PHASE3 / "YAX_PHASE3_EXECUTION_PLAN.md").read_text()
    assert "The only new labor-outcome model is the single shared-family-component" in plan
    assert "No continuous-F, G, residual, alternative-cut, alternative-support" in plan
    assert "PATH-P3-A" in plan and "PATH-P3-B" in plan and "PATH-P3-C" in plan
    definition = (PHASE3 / "YAX_PHASE3_SHARED_COMPONENT_DEFINITION.md").read_text()
    assert "true, latent causal, or uniquely correct AI exposure" in definition


def test_runner_uses_bracket_access_for_the_sample_column_after_documented_fix():
    source = (PHASE3 / "run_phase3.py").read_text()
    assert 'f_rows["sample"].eq("primary")' in source
    assert 'f_rows["sample"].eq("persistent")' in source
    assert 'result["sample"].eq("primary")' in source
    assert ".sample.eq" not in source
    ledger = (PHASE3 / "YAX_PHASE3_IMPLEMENTATION_FIXES.md").read_text()
    assert "Pandas `sample` attribute collision" in ledger
    assert "No specification, estimand, support rule, seed, draw count" in ledger


def test_sealed_phase3_classifications_and_single_stock_model_are_exact():
    receipt = json.loads((PHASE3 / "YAX_PHASE3_EXECUTION_RECEIPT.json").read_text())
    assert receipt["result_classifications"] == {
        "hard_benchmark": "HB-C",
        "phase3_path": "PATH-P3-C",
        "reallocation_component": "SC-R1",
        "shared_stock": "SC-A",
    }
    assert receipt["new_labor_outcome_model_count"] == 1
    assert receipt["new_labor_outcome_models"] == [
        "shared_F_Q2_Q5_with_Q1_omitted_and_Webb"
    ]
    assert receipt["pre_result_commit"] == (
        "2683af26768c343af6060988689728d88878d568"
    )


def test_hard_benchmark_hbc_is_not_overruled_by_descriptive_tail_area():
    result = json.loads((PHASE3 / "YAX_PHASE3_HARD_BENCHMARK_RESULTS.json").read_text())
    primary = result["primary_hard_benchmark"]
    persistent = result["persistent_hard_benchmark"]
    assert primary["classification"] == "HB-C"
    assert persistent["classification"] == "HB-C"
    assert primary["draws"] == persistent["draws"] == 999
    assert primary["realized_minus_hard_mean"] < 0.01
    assert persistent["realized_minus_hard_mean"] < 0.01
    assert primary["false_self_switches_after_repair"] == 0
    assert persistent["false_self_switches_after_repair"] == 0
    decision = (PHASE3 / "YAX_PHASE3_HARD_BENCHMARK_DECISION.md").read_text()
    assert "neither a conventional sampling p-value nor causal evidence" in decision


def test_shared_component_results_pass_declared_gates_without_extra_model():
    reallocation = json.loads(
        (PHASE3 / "YAX_PHASE3_REALLOCATION_COMPONENT_RESULTS.json").read_text()
    )
    stock = json.loads((PHASE3 / "YAX_PHASE3_SHARED_STOCK_RESULT.json").read_text())
    assert reallocation["classification"] == "SC-R1"
    assert reallocation["primary_lowest_minus_highest_F_bin_conflict"] > 0.75
    assert reallocation["persistent_lowest_minus_highest_F_bin_conflict"] > 0.75
    assert stock["classification"] == "SC-A"
    assert stock["coefficient_log_points"] < 0
    assert stock["wild_score_ci_upper"] < 0
    assert stock["occupations"] == 444
    assert stock["wild_score_draws"] == 999


def test_joint_all_six_negative_statement_is_explicitly_not_supported():
    joint = json.loads((PHASE3 / "YAX_PHASE3_JOINT_SIGN_INFERENCE.json").read_text())
    rows = pd.read_csv(PHASE3 / "YAX_PHASE3_JOINT_SIGN_INFERENCE.csv")
    assert joint["common_cluster_multipliers"] is True
    assert joint["common_parameter_assumption"] is False
    assert joint["all_simultaneous_upper_bounds_negative"] is False
    assert joint["joint_all_negative_statement_supported"] is False
    assert rows["upper_bound_below_zero"].sum() == 5


def test_execution_artifact_hashes_match_scc_receipt():
    import hashlib

    receipt = json.loads((PHASE3 / "YAX_PHASE3_EXECUTION_RECEIPT.json").read_text())
    for name, expected in receipt["artifact_hashes"].items():
        actual = hashlib.sha256((PHASE3 / name).read_bytes()).hexdigest()
        assert actual == expected, name


def test_v5_obeys_path_p3c_and_labels_phase3_as_exploratory():
    manuscript = (ROOT / "yax/manuscript/v5/YAX_MANUSCRIPT_v5_CLEAN.md").read_text()
    appendix = (ROOT / "yax/manuscript/v5/YAX_V5_SUPPLEMENTARY_APPENDIX.md").read_text()
    for text in [manuscript, appendix]:
        assert "POST-OUTCOME EXPLORATORY" in text
        assert "No Phase 4" in text
    assert "Robustness does not transfer automatically across economic statements" in manuscript
    assert "does not claim that actual occupational pairing is meaningfully unusually conflict-heavy" in manuscript
    assert "joint all-six-negative statement is not supported" in appendix
    forbidden = [
        "workers are causally fleeing AI",
        "AI causes workers to move toward",
        "the shared component is true AI exposure",
        "all six architectures estimate the same causal parameter",
    ]
    for phrase in forbidden:
        assert phrase not in manuscript


def test_headless_renderer_is_fixed_and_gate_eligible_figures_exist():
    renderer = (PHASE3 / "render_phase3_figures.py").read_text()
    assert 'matplotlib.use("Agg", force=True)' in renderer
    assert (PHASE3 / "YAX_PHASE3_REALLOCATION_COMPONENT_FIGURE.png").stat().st_size > 10000
    assert (PHASE3 / "YAX_PHASE3_SHARED_STOCK_FIGURE.png").stat().st_size > 10000
    assert not (PHASE3 / "YAX_PHASE3_HARD_BENCHMARK_FIGURE.png").exists()
