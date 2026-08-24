import pathlib
import sys

import pandas as pd

MAPPING = pathlib.Path(__file__).resolve().parents[1] / "mapping"
sys.path.insert(0, str(MAPPING))

from run_mapA_v2_validation import load_task_metadata, rank_band  # noqa: E402


def test_rank_band_is_deterministic_and_complete():
    first = rank_band({"B": 2.0, "A": 2.0, "C": 5.0}, 2)
    second = rank_band({"C": 5.0, "A": 2.0, "B": 2.0}, 2)
    assert first == second
    assert set(first) == {"A", "B", "C"}
    assert set(first.values()) <= {1, 2}


def test_task_metadata_uses_zero_mass_and_minus_one_score_for_missing(tmp_path):
    onet = pd.DataFrame({"task_id": ["T1", "T2"], "onet_soc": ["11-1011.00", "13-2011.00"]})
    wages = pd.DataFrame({
        "task_id": ["T1"],
        "vintage": [2021],
        "task_annual_wage_bill_allocation": [10.0],
        "allocation_usable": [True],
    })
    v1 = pd.DataFrame({"onet_task_id": ["T1"], "similarity": [0.5]})
    wage_path = tmp_path / "wages.csv"
    v1_path = tmp_path / "v1.csv"
    wages.to_csv(wage_path, index=False)
    v1.to_csv(v1_path, index=False)
    rows = load_task_metadata(onet, wage_path, v1_path)
    assert {row.onet_task_id for row in rows} == {"T1", "T2"}
    assert {row.major_soc_family for row in rows} == {"11", "13"}
