import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest


MODULE = Path(__file__).parents[1] / "code" / "contract_counterexamples.py"
SPEC = importlib.util.spec_from_file_location("counterexamples", MODULE)
counterexamples = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = counterexamples
SPEC.loader.exec_module(counterexamples)


def test_heterogeneous_baseline_amplitude_is_not_pure_timing():
    r = counterexamples.heterogeneous_baseline_amplitude_only()
    assert np.allclose(r.high_normalized, (0.8, 1.0))
    assert np.allclose(r.low_normalized, (0.4, 1.0))
    assert np.allclose(r.high_post_normalized, r.high_normalized)
    assert np.allclose(r.low_post_normalized, r.low_normalized)
    assert np.allclose(r.high_minus_low_did, (0.08, 0.0))
    assert np.allclose(r.group_specific_normalized_did, (0.0, 0.0))
    assert np.allclose(r.common_reference_shape_residual, (0.08, 0.0))
    assert r.pure_timing_classification.startswith("FAIL_PURE_TIMING")


def test_equal_wave_is_not_pooled_information_weighting():
    r = counterexamples.pooled_vs_equal_wave()
    assert r["pooled_information_weighted"] == 0.9
    assert r["equal_wave_target"] == 0.5


def test_reused_event_is_one_shock():
    r = counterexamples.reused_event_variance()
    assert r["correct_shared_event_variance_at_sigma2_1"] == 1.0
    assert r["incorrect_row_independent_variance_at_sigma2_1"] == 0.5


def test_estimated_reference_has_failure_state():
    assert counterexamples.reference_failure_state(0.05, 0.10) == "WEAK_OR_SIGN_UNCERTAIN_REFERENCE_BLOCK"
    assert counterexamples.reference_failure_state(0.50, 0.10) == "REFERENCE_REQUIRES_JOINT_UNCERTAINTY_PROPAGATION"
    v0 = counterexamples.normalized_ratio_variance(.40, 1.0, np.array([[.04, .0], [.0, .04]]))
    v1 = counterexamples.normalized_ratio_variance(.40, 1.0, np.array([[.04, .015], [.015, .04]]))
    assert v0 != v1
    with pytest.raises(ValueError, match="finite"):
        counterexamples.reference_failure_state(float("nan"), .1)
    with pytest.raises(ValueError, match="symmetric"):
        counterexamples.normalized_ratio_variance(.4, 1., np.array([[.04, .01], [.0, .04]]))
    with pytest.raises(ValueError, match="positive semidefinite"):
        counterexamples.normalized_ratio_variance(.4, 1., np.array([[.04, .10], [.10, .04]]))


def test_draft_cannot_self_approve_and_metadata_scope_never_opens_outcomes():
    draft = {"document_status": "PROPOSAL_NOT_PI_APPROVED", "pi_approval": {"primary_contract": True, "protected_extract": True}}
    assert counterexamples.contract_gate_status(draft, "metadata_extract") == "FAIL_DRAFT_CANNOT_SELF_APPROVE"
    approved_metadata = {"document_status": "PI_APPROVED", "pi_approval": {"primary_contract": True, "protected_extract": True}}
    assert counterexamples.contract_gate_status(approved_metadata, "metadata_extract") == "AUTHORITY_VERIFICATION_REQUIRED"
    assert counterexamples.contract_gate_status(approved_metadata, "outcome_access") == "FAIL_SEALED_OUTCOME_NOT_AUTHORIZED"


def test_actual_proposed_yaml_cannot_pass_pi_or_extract_gate():
    contract = Path(__file__).parents[1] / "estimation_contract.reconciled.PROPOSED.yaml"
    assert counterexamples.yaml_contract_gate_status(contract, "metadata_extract") == "FAIL_DRAFT_CANNOT_SELF_APPROVE"
