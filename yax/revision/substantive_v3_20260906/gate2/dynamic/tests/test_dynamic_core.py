from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest
from scipy import sparse


HERE = Path(__file__).resolve().parent
CORE_PATH = HERE.parent / "run_dynamic_core.py"
PARENT_PATH = HERE.parent / "run_dynamic_reconciliation.py"
PARENT_SPEC_PATH = HERE.parent / "DYNAMIC_RECONCILIATION_SPEC.json"
CORE_SPEC_PATH = HERE.parent / "DYNAMIC_CORE_SPEC.json"
ROOT = HERE.parents[2]


def load_module(name: str, path: Path):
    loader = importlib.util.spec_from_file_location(name, path)
    assert loader and loader.loader
    module = importlib.util.module_from_spec(loader)
    sys.modules[name] = module
    loader.loader.exec_module(module)
    return module


CORE = load_module("test_gate2_dynamic_core", CORE_PATH)
DYNAMIC = load_module("test_gate2_dynamic_parent_for_core", PARENT_PATH)
VALIDATOR = load_module(
    "test_gate2_dynamic_core_validator",
    HERE.parent / "validate_authoritative_dynamic_core.py",
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_paths() -> tuple[Path, Path]:
    run = ROOT / "runs/gate1_numerical_a1_pass_7482383"
    return run / "numerical/MODEL_AUDIT.json", run / "DEPENDENCY_RELEASE.json"


def test_dynamic_core_spec_binds_the_executing_code_and_scientific_scope():
    spec = load_json(CORE_SPEC_PATH)
    CORE.validate_spec(spec, CORE_PATH)
    assert spec["requirements"]["Y05"] == "AUTHORITATIVE_RUN_REQUIRED"
    assert spec["requirements"]["Y08"].startswith("OUT_OF_SCOPE")

    changed = copy.deepcopy(spec)
    changed["functionals"]["transition_month"] = "2023-01"
    with pytest.raises(CORE.DynamicCoreError, match="spec ID differs"):
        CORE.validate_spec(changed, CORE_PATH)


def fake_fit_from_audit(model: dict, seed: int) -> SimpleNamespace:
    original = []
    for label, value in model["solver_comparison"]["trust_path_target_vector"].items():
        if label.startswith("original_treatment::"):
            _, index, coefficient_label = label.split("::", 2)
            original.append((int(index), coefficient_label, float(value)))
    original.sort()
    labels = [row[1] for row in original]
    treatment = np.asarray([row[2] for row in original])
    rng = np.random.default_rng(seed)
    influence = rng.normal(scale=1e-4, size=(468, len(labels)))
    covariance = (468 / 467) * influence.T @ influence
    return SimpleNamespace(
        model_id=model["model_id"], labels=labels, treatment=treatment,
        influence=influence, covariance=covariance,
    )


def test_actual_a1_release_authorizes_all_four_dynamic_core_models():
    audit_path, release_path = audit_paths()
    audit = load_json(audit_path)
    release = load_json(release_path)
    CORE.check_core_release(audit, release)

    changed = copy.deepcopy(release)
    changed["target_dependencies"]["downstream_requirement_releases"]["Y03"][
        "release_status"
    ] = "BLOCKED"
    with pytest.raises(CORE.DynamicCoreError, match="Y03 numerical prerequisites"):
        CORE.check_core_release(audit, changed)


def test_reconciliation_reproduces_frozen_trust_path_point_values():
    audit_path, _ = audit_paths()
    models = {row["model_id"]: row for row in load_json(audit_path)["models"]}
    fits = {
        model_id: fake_fit_from_audit(models[model_id], 100 + index)
        for index, model_id in enumerate(CORE.CORE_MODELS)
    }
    parent_spec = load_json(PARENT_SPEC_PATH)
    estimates, covariance, objects = CORE.build_reconciliation(
        fits, parent_spec, DYNAMIC
    )
    indexed = estimates.set_index("target")
    assert len(estimates) == 18
    assert len(covariance) == 18 ** 2
    assert indexed.loc["unconditioned::S", "estimate"] == pytest.approx(
        -0.132109450792428, abs=1e-13
    )
    assert indexed.loc["unconditioned::P", "estimate"] == pytest.approx(
        -0.1198887653315, abs=1e-9
    )
    assert indexed.loc["unconditioned::D", "estimate"] == pytest.approx(
        -0.1313721669, abs=1e-9
    )
    assert indexed.loc["family_month::P", "estimate"] == pytest.approx(
        -0.2074336938061, abs=1e-12
    )
    assert indexed.loc[
        "conditioning_family_month_minus_unconditioned::D", "estimate"
    ] == pytest.approx(0.1096828494796, abs=1e-12)
    assert objects["unconditioned::P_minus_D"].estimate == pytest.approx(
        0.0114834016, abs=1e-9
    )


def test_rank_wald_common_draw_inference_matches_direct_linear_algebra():
    beta = np.array([0.2, -0.1, 0.05])
    influence = np.array([
        [0.10, 0.01, -0.02],
        [-0.03, 0.08, 0.01],
        [0.02, -0.04, 0.07],
        [-0.04, -0.03, -0.01],
    ])
    covariance = influence.T @ influence
    restrictions = np.array([[1.0, -1.0, 0.0], [0.0, 1.0, -1.0]])
    xi = np.array([
        [1.0, 1.0, -1.0, -1.0],
        [1.0, -1.0, 1.0, -1.0],
        [-1.0, 1.0, 1.0, -1.0],
    ])
    parent = load_json(PARENT_SPEC_PATH)
    result = CORE.rank_wald_with_inference(
        DYNAMIC, beta, covariance, influence, restrictions, xi, parent
    )
    target = restrictions @ beta
    restricted_covariance = restrictions @ covariance @ restrictions.T
    expected = float(target @ np.linalg.solve(restricted_covariance, target))
    assert result["wald_statistic"] == pytest.approx(expected)
    assert result["degrees_of_freedom"] == 2
    assert 0 < result["p_value_multiplier"] <= 1


def test_nesting_audit_uses_the_predeclared_exact_post_column_sum():
    frame = __import__("pandas").DataFrame({
        "occ_code": ["11", "11", "22", "22"],
        "month": ["2023-01", "2023-04", "2023-01", "2023-04"],
    })
    active = np.ones(4, dtype=bool)
    nuisance = sparse.csr_matrix(np.ones((4, 1)))
    dynamic_x = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 0.0], [0.0, 1.0]])
    static_x = dynamic_x.sum(axis=1, keepdims=True)
    static_design = SimpleNamespace(
        nuisance=nuisance,
        full=sparse.hstack([nuisance, sparse.csr_matrix(static_x)], format="csr"),
        nuisance_column_labels=["constant"],
    )
    dynamic_design = SimpleNamespace(
        nuisance=nuisance.copy(),
        full=sparse.hstack([nuisance, sparse.csr_matrix(dynamic_x)], format="csr"),
        nuisance_column_labels=["constant"],
    )
    static_fit = SimpleNamespace(
        active=active, labels=["Q5_x_post"], design=static_design,
        bundle=SimpleNamespace(frame=frame, regressors=static_x),
    )
    dynamic_fit = SimpleNamespace(
        active=active, labels=["Q5_x_2023Q1", "Q5_x_2023Q2"],
        design=dynamic_design,
        bundle=SimpleNamespace(frame=frame, regressors=dynamic_x),
    )
    result = CORE.nesting_mapping_audit(static_fit, dynamic_fit)
    assert result["status"] == "PASS_EXACT_PREDECLARED_SPARSE_DESIGN_NESTING"
    assert result["maximum_absolute_residual"] == 0
    assert result["treatment_mapping_nonzeros"] == 2

    changed = copy.deepcopy(static_fit)
    changed.bundle = SimpleNamespace(frame=frame, regressors=static_x.copy())
    changed.bundle.regressors[0, 0] = 0.0
    with pytest.raises(CORE.DynamicCoreError, match="nesting failed"):
        CORE.nesting_mapping_audit(changed, dynamic_fit)


def test_original_coordinate_probability_reconstruction_is_stable():
    full = sparse.csr_matrix(np.array([
        [1.0, 0.0], [1.0, 1.0], [1.0, -1.0],
    ]))
    fit = SimpleNamespace(
        model_id="tiny", theta=np.array([-1000.0, 3.0]),
        treatment=np.array([3.0]),
        design=SimpleNamespace(nuisance=sparse.csr_matrix(np.ones((3, 1))), full=full),
    )
    eta = np.asarray(full @ np.array([-1000.0, 3.0])).reshape(-1)
    probability = np.exp(eta) / (1.0 + np.exp(eta))
    fit.probability = probability
    beta, maximum = CORE.original_full_beta(fit)
    assert np.array_equal(beta, np.array([-1000.0, 3.0]))
    assert maximum == 0.0


def test_authoritative_dynamic_core_result_recomputes_from_public_objects(tmp_path: Path):
    run_dir = ROOT / "runs/gate2_dynamic_core_authoritative_20260908"
    support_dir = ROOT / "runs/gate2_support_inference_authoritative_20260908"
    report = tmp_path / "validation.json"
    assert VALIDATOR.main([
        "--run-dir", str(run_dir),
        "--support-run-dir", str(support_dir),
        "--core-spec", str(CORE_SPEC_PATH),
        "--parent-spec", str(PARENT_SPEC_PATH),
        "--common-multipliers", str(support_dir / "COMMON_MULTIPLIERS.npz"),
        "--report", str(report),
    ]) == 0
    result = load_json(report)
    assert result["status"] == "PASS_INDEPENDENT_DYNAMIC_CORE_RECOMPUTATION"
    assert result["result"]["result_id"] == (
        "yaxresult_v1_b039944581f0da60fb7e8368bff687858b740a7e638c190a8c934369fc10defe"
    )
    assert max(result["maximum_absolute_recomputation_differences"].values()) < 2e-12
