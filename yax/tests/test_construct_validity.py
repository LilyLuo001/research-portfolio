import csv
import importlib.util
import math
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "measurement" / "construct_validity.py"
SPEC = importlib.util.spec_from_file_location("construct_validity", PATH)
C = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = C
SPEC.loader.exec_module(C)


def test_pairwise_correlation_reports_its_own_n():
    rows = [
        {"a": "1", "b": "2"},
        {"a": "2", "b": "4"},
        {"a": "3", "b": ""},
    ]
    result = C.correlation(rows, "a", "b")
    assert result["n"] == 2
    assert math.isclose(result["correlation"], 1.0)


def test_rank_is_deterministic_at_ties():
    rows = [
        {"cps_occ2010": "2", "occupation": "B", "m": "1"},
        {"cps_occ2010": "1", "occupation": "A", "m": "1"},
        {"cps_occ2010": "3", "occupation": "C", "m": "2"},
    ]
    result = C.rank(rows, "m", k=2)
    assert [row["cps_occ2010"] for row in result["lowest"]] == ["0001", "0002"]
    assert result["highest"][0]["cps_occ2010"] == "0003"
