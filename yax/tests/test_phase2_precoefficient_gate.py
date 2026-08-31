import hashlib
import importlib.util
import json
import pathlib
import sys

import numpy as np
import pandas as pd


ROOT = pathlib.Path(__file__).resolve().parents[2]
PHASE = ROOT / "yax/analysis/postoutcome_phase2"


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def test_minimal_ipums_patch_is_completed_and_sanitized():
    request = json.loads((PHASE / "YAX_PHASE2_LNKFW1MWT_EXTRACT_REQUEST.json").read_text())
    spec = json.loads((PHASE / "YAX_PHASE2_LNKFW1MWT_EXTRACT_SPEC.json").read_text())
    assert request["extract_status"] == "completed"
    assert request["extract_number"] == 10
    assert request["errors"] == {}
    assert request["spec_sha256"] == sha256(PHASE / "YAX_PHASE2_LNKFW1MWT_EXTRACT_SPEC.json")
    assert len(spec["samples"]) == 114
    assert "cps2025_10s" not in spec["samples"]
    assert "LNKFW1MWT" in spec["variables"]
    serialized = json.dumps(request).lower()
    assert "api_key" not in serialized
    assert "59cba" not in serialized


def test_weight_compatibility_gate_passes_before_flow_outcomes():
    receipt = json.loads((PHASE / "YAX_PHASE2_LONGITUDINAL_WEIGHT_RECEIPT.json").read_text())
    assert receipt["status"] == "PASS_DEFENSIBLE_CPSIDV_WITH_OFFICIAL_WEIGHT"
    assert receipt["extract"]["merge"]["merge_success_rate"] == 1.0
    assert receipt["extract"]["merge"]["duplicate_basic_merge_keys"] == 0
    assert all(receipt["compatibility_conditions"].values())
    assert receipt["overall"]["positive_weight_rate_among_CPSIDP_matches"] == 1.0
    assert receipt["overall"]["weighted_CPSIDV_retention_rate"] > 0.98
    assert receipt["overall"]["false_September_to_November_2025_links"] == 0
    assert receipt["flow_outcome_variables_read"] == []
    assert receipt["AI_flow_coefficients_estimated"] == []
    for name, expected in receipt["outputs"].items():
        assert sha256(PHASE / name) == expected


def test_link_audit_reports_age_period_and_exposure_selection():
    frame = pd.read_csv(PHASE / "YAX_PHASE2_LINK_SAMPLE_AUDIT.csv")
    assert {"overall", "age_group", "period", "origin_beta_quintile"}.issubset(
        set(frame.dimension)
    )
    overall = frame.loc[frame.dimension.eq("overall")].iloc[0]
    assert int(overall.eligible_origins) == 4_500_962
    assert int(overall.CPSIDP_matched) == 4_124_467
    assert int(overall.CPSIDV_matched) == 4_085_493
    q = frame.loc[frame.dimension.eq("origin_beta_quintile")]
    assert set(q.level) == {"Q1", "Q2", "Q3", "Q4", "Q5"}
    assert q.weighted_CPSIDV_retention_rate.min() > 0.98


def test_plan_freezes_gated_estimands_and_exclusions():
    plan = (PHASE / "YAX_PHASE2_FLOW_ANALYSIS_PLAN.md").read_text()
    for required in (
        "FLOW-M1", "FLOW-M2", "FLOW-M3", "FLOW-M4", "FLOW-M5",
        "LNKFW1MWT", "December 2019→January 2020", "999 Rademacher",
        "Entry destination", "realized-transition diagnostic",
        "No propensity weight", "No V5 manuscript",
    ):
        assert required in plan
    assert "MISH 4→5 eight-month returns are excluded" in plan
    assert "September→November 2025 is not" in plan
    assert "At the time this plan is committed" in plan


def test_offset_flow_engine_converges_on_synthetic_panel():
    path = PHASE / "run_phase2_primary_beta_flows.py"
    spec = importlib.util.spec_from_file_location("phase2_primary_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    n_occ, n_month = 15, 10
    occ = np.repeat(np.arange(n_occ), n_month)
    month = np.tile(np.arange(n_month), n_occ)
    post = month >= 5
    q = np.repeat((np.arange(n_occ) % 5) + 1, n_month)
    webb = np.repeat(np.linspace(-1, 1, n_occ), n_month)
    x = np.column_stack([((q == value) & post).astype(float) for value in (2, 3, 4, 5)]
                        + [(webb * post).astype(float)])
    offset = np.repeat(np.linspace(-0.25, 0.25, n_occ), n_month)
    eta = offset + np.repeat(np.linspace(-0.3, 0.3, n_occ), n_month) + 0.2 * post + x @ np.array([0.03, -0.02, 0.04, 0.08, -0.01])
    total = np.full(n_occ * n_month, 400.0)
    young = np.round(total / (1 + np.exp(-eta)))
    beta, se, influence, iterations, used = module.fit_offset(
        young, total, occ, month, x, offset
    )
    assert beta.shape == (5,)
    assert np.all(np.isfinite(beta)) and np.all(np.isfinite(se))
    assert influence.shape == (n_occ, 5)
    assert iterations < 5000
    assert len(used) == n_occ
