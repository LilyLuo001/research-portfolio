#!/usr/bin/env python3
"""Deterministic checks for the proposed P1 reconciliation contract.

These fixtures use no P1 earnings, quote, treatment-response, or licensed raw
data. They are algebraic counterexamples: passing them does not establish
identification, data eligibility, inference validity, or empirical power.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class HeterogeneousBaselineResult:
    high_pre: tuple[float, float]
    high_post: tuple[float, float]
    low_pre: tuple[float, float]
    low_post: tuple[float, float]
    high_normalized: tuple[float, float]
    low_normalized: tuple[float, float]
    high_post_normalized: tuple[float, float]
    low_post_normalized: tuple[float, float]
    high_minus_low_did: tuple[float, float]
    group_specific_normalized_did: tuple[float, float]
    common_reference_shape_residual: tuple[float, float]
    pure_timing_classification: str


def heterogeneous_baseline_amplitude_only() -> HeterogeneousBaselineResult:
    """Show why a common fixed shape can falsely label amplitude as timing."""
    high_pre = np.array([0.80, 1.00])
    high_post = np.array([0.96, 1.20])
    low_pre = np.array([0.40, 1.00])
    low_post = np.array([0.48, 1.20])
    did = (high_post - high_pre) - (low_post - low_pre)
    high_norm = high_pre / high_pre[-1]
    low_norm = low_pre / low_pre[-1]
    high_post_norm = high_post / high_post[-1]
    low_post_norm = low_post / low_post[-1]
    kappa = (high_post_norm - high_norm) - (low_post_norm - low_norm)
    # A common-reference contrast q = beta - f*beta_T cannot repair distinct
    # baseline shapes when beta_T is zero: it returns the early DID unchanged.
    common_reference_q = did - high_norm * did[-1]
    return HeterogeneousBaselineResult(
        tuple(high_pre), tuple(high_post), tuple(low_pre), tuple(low_post),
        tuple(high_norm), tuple(low_norm), tuple(high_post_norm), tuple(low_post_norm),
        tuple(did), tuple(kappa), tuple(common_reference_q),
        "FAIL_PURE_TIMING: both groups retain their own normalized shape; a positive early DID is amplitude-composition, not timing."
    )


def pooled_vs_equal_wave() -> dict[str, float]:
    """Two waves: pooled residual-dose OLS is 0.9 while equal-wave target is .5."""
    x1, x2 = np.array([-1.0, 1.0]), np.array([-3.0, 3.0])
    b1, b2 = 0.0, 1.0
    y1, y2 = b1 * x1, b2 * x2
    pooled = float((x1 @ y1 + x2 @ y2) / (x1 @ x1 + x2 @ x2))
    equal_wave = (b1 + b2) / 2
    return {"pooled_information_weighted": pooled, "equal_wave_target": equal_wave,
            "wave1_information": float(x1 @ x1), "wave2_information": float(x2 @ x2)}


def reused_event_variance() -> dict[str, float]:
    """Duplicating a single economic event cannot halve its shock variance."""
    influence = np.array([0.5, 0.5])
    correct_shared_shock_variance = float(influence.sum() ** 2)
    incorrect_independent_row_variance = float(influence @ influence)
    return {"correct_shared_event_variance_at_sigma2_1": correct_shared_shock_variance,
            "incorrect_row_independent_variance_at_sigma2_1": incorrect_independent_row_variance}


def reference_failure_state(reference_terminal: float, reference_terminal_se: float, z_cutoff: float = 1.96) -> str:
    """A weak/sign-uncertain estimated reference cannot be a fixed normalizer."""
    if not all(np.isfinite(x) for x in (reference_terminal, reference_terminal_se, z_cutoff)):
        raise ValueError("reference inputs must be finite")
    if reference_terminal_se <= 0 or z_cutoff <= 0:
        raise ValueError("reference_terminal_se and z_cutoff must be positive")
    if abs(reference_terminal) <= z_cutoff * reference_terminal_se:
        return "WEAK_OR_SIGN_UNCERTAIN_REFERENCE_BLOCK"
    return "REFERENCE_REQUIRES_JOINT_UNCERTAINTY_PROPAGATION"


def normalized_ratio_variance(numerator: float, terminal: float, covariance: np.ndarray) -> float:
    """Finite two-parameter delta-method fixture, not a production inference engine."""
    covariance = np.asarray(covariance, dtype=float)
    if covariance.shape != (2, 2):
        raise ValueError("covariance must be 2x2")
    if not np.all(np.isfinite(covariance)) or not np.isfinite(numerator) or not np.isfinite(terminal):
        raise ValueError("numerator, terminal, and covariance must be finite")
    if terminal == 0:
        raise ValueError("terminal reference cannot be zero")
    if not np.allclose(covariance, covariance.T, rtol=0.0, atol=1e-12):
        raise ValueError("covariance must be symmetric")
    if np.linalg.eigvalsh(covariance).min() < -1e-12:
        raise ValueError("covariance must be positive semidefinite")
    gradient = np.array([1.0 / terminal, -numerator / terminal**2])
    return float(gradient @ covariance @ gradient)


def contract_gate_status(contract: dict[str, Any], purpose: str) -> str:
    """A non-authorizing scope lint: all actual access checks remain external."""
    if contract.get("document_status") != "PI_APPROVED":
        return "FAIL_DRAFT_CANNOT_SELF_APPROVE"
    approvals = contract.get("pi_approval", {})
    if purpose == "metadata_extract":
        if approvals.get("primary_contract") is True and approvals.get("protected_extract") is True:
            # A document and two booleans are never the owner record, signed
            # hash, or authorized protected view. Those are external checks.
            return "AUTHORITY_VERIFICATION_REQUIRED"
        return "FAIL_MISSING_SCOPE_APPROVAL"
    if purpose == "outcome_access":
        return "FAIL_SEALED_OUTCOME_NOT_AUTHORIZED"
    raise ValueError("unknown gate purpose")


def yaml_contract_gate_status(contract_path: Path, purpose: str) -> str:
    """Evaluate the actual proposed YAML, rather than a hand-built fixture."""
    import yaml

    parsed = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("contract YAML must parse to a mapping")
    return contract_gate_status(parsed, purpose)


def results() -> dict[str, Any]:
    hetero = heterogeneous_baseline_amplitude_only()
    return {
        "heterogeneous_baseline_amplitude_only": asdict(hetero),
        "pooled_vs_equal_wave": pooled_vs_equal_wave(),
        "reused_event_variance": reused_event_variance(),
        "reference_failure_weak": reference_failure_state(0.05, 0.10),
        "reference_failure_precise": reference_failure_state(0.50, 0.10),
        "reference_variance_covariance_zero": normalized_ratio_variance(.40, 1.0, np.array([[.04, .0], [.0, .04]])),
        "reference_variance_covariance_positive": normalized_ratio_variance(.40, 1.0, np.array([[.04, .015], [.015, .04]])),
        "draft_gate_pending": contract_gate_status({"document_status": "PROPOSAL_NOT_PI_APPROVED", "pi_approval": {}}, "metadata_extract"),
        "draft_gate_outcome_denied": contract_gate_status({"document_status": "PI_APPROVED", "pi_approval": {"primary_contract": True, "protected_extract": True}}, "outcome_access"),
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
