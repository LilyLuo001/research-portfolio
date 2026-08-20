import importlib.util
import pathlib

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "w5" / "sanitize_identification_receipt.py"
SPEC = importlib.util.spec_from_file_location("w5_receipt", PATH)
assert SPEC and SPEC.loader
RECEIPT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RECEIPT)


def gate(**updates):
    value = {
        "status": "PASS_DYNAMIC_IDENTIFICATION",
        "n_occupations": 100,
        "n_months": 12,
        "n_panel_rows": 1200,
        "weighted_residual_dose_variance": 0.01,
        "effective_rank": 3,
        "leading_singular_share": 0.8,
        "minimum_rank": 2,
        "maximum_leading_share": 0.95,
        "rank_tolerance": 1e-6,
        "dynamic_claim_allowed": True,
        "degenerate_reporting_rule": "frozen rule",
        "outcome_data_opened": False,
        "singular_values": [3.0, 2.0, 1.0],
        "input_name": "private-panel.csv",
        "input_sha256": "f" * 64,
    }
    value.update(updates)
    return value


def kwargs():
    return {
        "input_commits": {
            "seat_c": "a" * 40,
            "price_redteam": "b" * 40,
            "integration": "c" * 40,
            "event_evidence": "d" * 40,
        },
        "output_commit": "e" * 40,
        "panel_version": "w5-v1",
        "component_row_count": 500,
        "event_occupation_cell_count": 400,
        "retained_event_count": 4,
        "occupation_count": 100,
        "exclusion_counts": {"event_date_gate": 2, "unresolved_crosswalk": 5},
        "reconciliation_passed": True,
    }


def test_receipt_omits_private_paths_hashes_vectors_and_labels():
    result = RECEIPT.sanitize(gate(), **kwargs())
    encoded = repr(result)
    for forbidden in (
        "private-panel.csv", "input_sha256", "singular_values", "f" * 64
    ):
        assert forbidden not in encoded
    assert result["identification_gate"]["effective_rank"] == 3
    assert result["privacy"]["outcomes_opened"] is False


def test_receipt_rejects_opened_outcomes_or_weakened_gate():
    with pytest.raises(ValueError, match="sealed outcomes"):
        RECEIPT.sanitize(gate(outcome_data_opened=True), **kwargs())
    with pytest.raises(ValueError, match="minimum rank 2"):
        RECEIPT.sanitize(gate(minimum_rank=1), **kwargs())
    with pytest.raises(ValueError, match="leading-share 0.95"):
        RECEIPT.sanitize(gate(maximum_leading_share=0.951), **kwargs())


def test_receipt_requires_all_exact_dependency_commits_and_reconciliation():
    bad = kwargs()
    bad["input_commits"] = {"seat_c": "a" * 40}
    with pytest.raises(ValueError, match="input commits must be exactly"):
        RECEIPT.sanitize(gate(), **bad)
    bad = kwargs()
    bad["reconciliation_passed"] = False
    with pytest.raises(ValueError, match="unreconciled"):
        RECEIPT.sanitize(gate(), **bad)
