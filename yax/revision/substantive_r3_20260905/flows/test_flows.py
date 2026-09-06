#!/usr/bin/env python3
"""Small deterministic unit checks that do not read protected outcomes."""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import numpy as np
import pandas as pd


HERE = pathlib.Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("r3_flows", HERE / "run_flows_outcomes.py")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_bridge_lineage_and_conservation() -> None:
    bridge = pd.DataFrame({
        "census_2010": ["1000", "1000", "2000"],
        "census_2018": ["1100", "1200", "2100"],
        "bridge_weight": [0.25, 0.75, 1.0],
    })
    components = MODULE.lineage_components(bridge, ["1100", "1200", "2100", "3000"])
    assert components["1100"] == components["1200"]
    assert components["1100"] != components["2100"]
    base = pd.DataFrame({
        "YEAR": [2019, 2020], "month": ["2019-01", "2020-01"],
        "age_group": ["young_22_25", "older_26_65"], "OCC": [1000, 3000],
        "risk": [8.0, 4.0], "event": [2.0, 1.0],
    })
    qmap = {"1100": 1, "1200": 5, "2100": 2, "3000": 3}
    webb = {code: value for code, value in zip(qmap, [-1.0, 1.0, 0.0, 0.2], strict=True)}
    cells, audit = MODULE.route_cells(
        base, "OCC", "YEAR", bridge, qmap, webb, ["risk", "event"],
        {"horizon": "test", "role": "test"},
    )
    assert np.isclose(cells.risk.sum(), 12.0)
    assert np.isclose(cells.event.sum(), 3.0)
    assert max(abs(row["route_conservation_error"]) for row in audit) < 1e-12


def synthetic_frame() -> pd.DataFrame:
    rows = []
    # One adjacent pair and one annual pair for each synthetic person.
    for person, origin_mish in [(1, 1), (2, 2)]:
        for year, month, mish, age, status, occ in [
            (2023, 1, origin_mish, 25 + person, 10, 1100),
            (2023, 2, origin_mish + 1, 25 + person, 20, 0),
            (2024, 1, origin_mish + 4, 26 + person, 10, 1200),
        ]:
            rows.append({
                "YEAR": year, "MONTH": month, "month": f"{year}-{month:02d}",
                "month_ord": year * 12 + month, "SERIAL": person, "PERNUM": 1,
                "CPSID": 100 + person, "CPSIDP": 1000 + person, "CPSIDV": 2000 + person,
                "MISH": mish, "AGE": age, "EMPSTAT": status, "LABFORCE": 2 if status < 30 else 1,
                "OCC": occ, "OCC2010": occ, "WTFINL": 10.0, "CLASSWKR": 20,
                "UHRSWORKT": 40 if status < 20 else 999, "DURUNEMP": 2 if status == 20 else 999,
                "EARNWT": 0.0, "EARNWEEK": 9999.99, "LNKFW1MWT": 8.0,
                "LNKFW1YWT": 7.0, "age_group": "young_22_25" if age <= 25 else "older_26_65",
                "employed": status in [10, 12], "unemployed": 20 <= status <= 22,
                "nilf": 30 <= status <= 36, "nonemployed": 20 <= status <= 36,
            })
    return pd.DataFrame(rows)


def test_link_rules() -> None:
    frame = synthetic_frame()
    adjacent_pairs, adjacent, _ = MODULE.build_pairs(frame, "adjacent_month")
    annual_pairs, annual, _ = MODULE.build_pairs(frame, "twelve_month")
    assert len(adjacent) == 2
    assert (adjacent.MISH_d == adjacent.MISH + 1).all()
    assert len(annual) == 2
    assert (annual.MISH_d == annual.MISH + 4).all()
    assert not adjacent_pairs.analysis_link.isna().any()
    assert not annual_pairs.analysis_link.isna().any()


def test_weighted_absorption() -> None:
    values = np.array([1.0, 2.0, 3.0, 5.0])
    weights = np.ones(4)
    occ = np.array([0, 0, 1, 1])
    month = np.array([0, 1, 0, 1])
    residual = MODULE._weighted_absorb(values, weights, occ, month, 2, 2)
    assert np.allclose(np.bincount(occ, weights=residual, minlength=2), 0, atol=1e-10)
    assert np.allclose(np.bincount(month, weights=residual, minlength=2), 0, atol=1e-10)


def main() -> int:
    test_bridge_lineage_and_conservation()
    test_link_rules()
    test_weighted_absorption()
    print("3 flow unit tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

