import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PHASE = ROOT / "yax/analysis/postoutcome_scope_phase1"
LABEL = "POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_phase1_has_only_declared_age_regression():
    receipt = json.loads((PHASE / "YAX_SCOPE_PHASE1_REPRODUCIBILITY_RECEIPT.json").read_text())
    assert receipt["new_outcome_regressions_executed"] == [
        "one pre-declared grouped-multinomial conditional-PPML flexible age-profile model"
    ]
    assert receipt["flow_treatment_effect_regressions_executed"] == []
    assert receipt["prohibited_analyses_executed"] == []


def test_phase1_age_bins_and_status_are_exact():
    with (PHASE / "YAX_AGE_PROFILE_RESULTS.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    assert [row["Age group"] for row in rows] == [
        "18-21", "22-25", "26-30", "31-40", "41-50", "51-65"
    ]
    assert all(row["analysis_status"] == LABEL for row in rows)
    assert rows[-1]["coefficient"] == "0.0"
    assert rows[-1]["reference group"] == "normalized reference"


def test_phase1_protected_hashes_remain_exact():
    expected = {
        ROOT / "yax/analysis/outcomes/frozen_v11_corrected_run/FROZEN_RESULTS.json":
            "4f7df33a530e499c5562dead9464b2a19b87a3e3c6454d52944bc5e00879a831",
        ROOT / "yax/analysis/outcomes/frozen_v11_corrected_run/RESULT_LEDGER.jsonl":
            "e900adb75510729be635eb7aea381bfe6e523b376b6f2723350cf47bdf09266b",
        ROOT / "yax/manuscript/v4_1/YAX_MANUSCRIPT_v4_1_CLEAN.md":
            "1591a4a545095d3d7b0c65062849fb1101a49bd803e6e0e3e732e84c715e700c",
    }
    assert {path: digest(path) for path in expected} == expected


def test_phase1_flow_is_feasibility_only_and_decision_is_bounded():
    flow = json.loads((PHASE / "CPS_LONGITUDINAL_FEASIBILITY_RECEIPT.json").read_text())
    assert flow["flow_treatment_effect_regressions_executed"] == []
    memo = (PHASE / "YAX_SCOPE_PHASE1_DECISION_MEMO.md").read_text()
    assert "**AGE-A with a precision caveat; FLOW-B (strong, adjacent-month only); PATH 1.**" in memo
    assert "**No CPS flow treatment-effect regressions were executed in Phase 1.**" in memo
    assert "**The immutable v1.1 confirmatory results and V4.1 manuscript baseline were not altered.**" in memo

