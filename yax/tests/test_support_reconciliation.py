import importlib.util
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "measurement" / "reconcile_computerization_support.py"
SPEC = importlib.util.spec_from_file_location("reconcile_computerization_support", PATH)
R = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = R
SPEC.loader.exec_module(R)


def test_metric_contract_contains_identification_and_coverage():
    assert "partial_variance_of_ai" in R.METRICS
    assert "vif" in R.METRICS
    assert "effective_number_identifying_ai" in R.METRICS
    assert "common_support_employment_share" in R.METRICS
