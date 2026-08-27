import importlib.util
import csv
import math
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "measurement" / "computerization_support.py"
SPEC = importlib.util.spec_from_file_location("computerization_support", PATH)
C = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = C
SPEC.loader.exec_module(C)


def test_projection_reports_partial_variance_vif_and_residuals():
    fit = C.weighted_projection([1, 2, 4], [1, 2, 3], [1, 2, 1])
    assert 0 < fit["partial_variance_of_ai"] < 1
    assert math.isclose(fit["vif"], 1 / fit["partial_variance_of_ai"])
    assert math.isclose(fit["se_inflation"], math.sqrt(fit["vif"]))
    assert len(fit["residual"]) == 3


def test_named_support_and_major_group_shares_are_complete():
    ai = {"0010": 1.0, "0020": 2.0, "0030": 4.0}
    comp = {
        "0010": {"score": 1.0, "occupation": "A", "soc_major_group": "11"},
        "0020": {"score": 2.0, "occupation": "B", "soc_major_group": "11"},
        "0030": {"score": 3.0, "occupation": "C", "soc_major_group": "13"},
    }
    result = C.analyse_pair("ai", "score", ai, comp,
                            {"0010": 1, "0020": 2, "0030": 1}, 4)
    shares = result["residual_variation_by_soc_major_group"]
    assert math.isclose(sum(row["residual_variance_share"] for row in shares), 1)
    named = result["named_divergence_occupations"]
    assert named["largest_residual_variance_contributors"][0]["occupation"] in {"A", "B", "C"}
    assert result["common_support_employment_share"] == 1


def test_preperiod_mass_rejects_post_rows_before_weighting(tmp_path):
    path = tmp_path / "cells.csv"
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["cps_occ", "month", "weight_sum", "employment_rate"])
        writer.writerow(["0010", "2022-11-01", "10", "0.2"])
        writer.writerow(["0010", "2022-12-01", "999", "0.9"])
    mass, months, excluded = C.preperiod_mass(path)
    assert mass == {"0010": 10}
    assert months == ["2022-11-01"]
    assert excluded == ["2022-12-01"]
