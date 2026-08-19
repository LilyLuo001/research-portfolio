import importlib.util
import pathlib

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "memo" / "power_calcs" / "audit_entrant_companion.py"
SPEC = importlib.util.spec_from_file_location("entrant_audit", PATH)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def _row(person, month, mish, empstat, occ=0, weight=1.0):
    return {
        "YEAR": 2022, "MONTH": month, "MISH": mish, "CPSIDP": person,
        "AGE": 23, "SEX": 1, "RACE": 100, "HISPAN": 0, "EDUC": 111,
        "EMPSTAT": empstat, "OCC2010": occ, "WTFINL": weight,
    }


def test_audit_separates_linked_entry_from_link_failure_and_survey_entry():
    frame = pd.DataFrame([
        _row(1, 1, 1, 20),
        _row(1, 2, 2, 10, 1010),       # valid linked labor-market entry
        _row(2, 2, 2, 10, 2020),       # expected prior record is missing
        _row(3, 1, 1, 10, 3030),
        _row(3, 2, 2, 10, 3030),       # continuously employed, not an entry
        _row(4, 2, 1, 10, 4040),       # survey entrant, not link-identifiable
    ])
    receipt, details = AUDIT.audit_frame(frame, minimum_pair_count=2)
    assert receipt["n_expected_prior_interviews"] == 3
    assert receipt["n_successfully_linked_prior_month"] == 2
    assert receipt["n_expected_prior_link_failures"] == 1
    assert receipt["n_linked_labor_market_entries"] == 1
    assert receipt["occupation_level_pi_go_estimable"] is False
    assert details["OCC2010"].tolist() == [1010]


def test_audit_never_claims_registered_companion_is_gate_ready():
    frame = pd.DataFrame([
        _row(1, 1, 1, 20),
        _row(1, 2, 2, 10, 1010),
    ])
    receipt, _ = AUDIT.audit_frame(frame, minimum_pair_count=2)
    assert receipt["status"] == "ENTRANT_COMPANION_DEMOTED_TO_EXPLORATORY"
    assert receipt["outcome_data_opened"] is False
