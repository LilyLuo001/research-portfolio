from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("yax_flow_selection_test_runner",
                                              HERE / "run_flow_selection.py")
RUN = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUN
SPEC.loader.exec_module(RUN)


def test_period_contract_and_annual_duration() -> None:
    months = pd.Series(["2021-11", "2021-12", "2022-12", "2023-01"])
    assert RUN.period_label(months, "twelve_month").tolist() == [
        "pre", "straddling_or_transition", "straddling_or_transition", "post"]
    assert RUN.exposure_duration("2021-12") == 0
    assert RUN.exposure_duration("2022-01") == 1 / 12
    assert RUN.exposure_duration("2022-12") == 1
    assert RUN.exposure_duration("2023-01") == 1


def test_route_origin_records_preserves_fractional_current_support() -> None:
    records = pd.DataFrame({
        "employed": [True, True], "OCC": [100, 300], "YEAR": [2019, 2023],
        "WTFINL": [10.0, 20.0], "month": ["2019-01", "2023-01"],
    })
    bridge = pd.DataFrame({
        "census_2010": ["0100", "0100"], "census_2018": ["0200", "0300"],
        "bridge_weight": [0.25, 0.75],
    })
    qmap = {"0200": 1, "0300": 5}
    webb = {"0200": -1.0, "0300": 1.0}
    result = RUN.route_origin_records(records, bridge, qmap, webb)
    assert len(result) == 3
    assert np.isclose(result.origin_weight.sum(), 30.0)
    assert np.isclose(result.loc[result.YEAR.eq(2019), "route_fraction"].sum(), 1.0)


def synthetic_entry_pairs() -> pd.DataFrame:
    return pd.DataFrame({
        "analysis_link": [True, True, True, True],
        "nonemployed": [True, True, True, True],
        "nonemployed_d": [True, False, False, False],
        "employed_d": [False, True, True, True],
        "OCC_d": [0, 100, 999, 0], "YEAR_d": [2023, 2019, 2023, 2023],
        "LNKFW1MWT": [2.0, 3.0, 4.0, 1.0],
        "LNKFW1YWT": [2.0, 3.0, 4.0, 1.0],
        "month": ["2023-01"] * 4, "age_group": ["young_22_25"] * 4,
    })


def test_entry_destinations_share_one_denominator_and_reconcile() -> None:
    bridge = pd.DataFrame({
        "census_2010": ["0100", "0100"], "census_2018": ["0200", "0300"],
        "bridge_weight": [0.25, 0.75],
    })
    rows, checks, allocation = RUN.entry_rows(
        synthetic_entry_pairs(), "adjacent_month", bridge, {"0200": 1, "0300": 5})
    assert len(checks) == 1
    assert abs(checks[0]["identity_error"]) <= 1e-12
    assert np.isclose(checks[0]["all_destination_probability_sum"], 1)
    assert {row["destination_category"] for row in rows} == {
        "remaining_nonemployed", "destination_Q1", "destination_Q5",
        "employed_valid_occupation_outside_support",
        "employed_missing_or_invalid_destination_occupation",
    }
    assert np.isclose(sum(row["conditional_allocation_share"] for row in allocation), 1)


def bound_frame() -> pd.DataFrame:
    rows = []
    index = 0
    for period in ("pre", "post"):
        for age in ("young_22_25", "older_26_65"):
            for q in (1, 5):
                for linked, event in ((True, True), (False, False)):
                    rows.append({
                        "period": period, "age_group": age, "quintile": q,
                        "origin_weight": 1.0, "analysis_link": linked,
                        "nonemployed_d": event, "unemployed_d": event,
                        "nilf_d": False, "employed_d": not event,
                        "OCC2010": 100 + q, "OCC2010_d": 100 + q,
                        "month": "2023-01" if period == "post" else "2021-01",
                        "YEAR": 2023 if period == "post" else 2021,
                        "route_fraction": 1.0, "source_record_id": index,
                    })
                    index += 1
    return pd.DataFrame(rows)


def test_missing_outcome_bounds_are_unclipped_and_jointly_ordered() -> None:
    groups, contrasts = RUN.missing_outcome_bounds(bound_frame(), "adjacent_month")
    assert len(groups) == 24
    active = [row for row in groups if row["margin"] in
              {"employment_exit", "unemployment_entry"}]
    inactive = [row for row in groups if row["margin"] == "labor_force_exit"]
    assert all(np.isclose(row["probability_lower"], .5) for row in active)
    assert all(np.isclose(row["probability_lower"], 0) for row in inactive)
    assert all(row["probability_lower"] <= row["probability_upper"] for row in groups)
    assert all(row["linear_probability_contrast_lower"] <=
               row["linear_probability_contrast_upper"] for row in contrasts)
    assert all(row["Lee_trimming_used"] is False and
               row["probabilities_clipped"] is False for row in contrasts)


def test_joint_bounds_keep_bridge_descendants_on_one_missing_outcome() -> None:
    data = bound_frame()
    q1 = (data.period.eq("post") & data.age_group.eq("young_22_25") &
          data.quintile.eq(1) & ~data.analysis_link)
    q5 = (data.period.eq("post") & data.age_group.eq("young_22_25") &
          data.quintile.eq(5) & ~data.analysis_link)
    shared_id = int(data.loc[q1, "source_record_id"].iloc[0])
    data.loc[q5, "source_record_id"] = shared_id
    _, contrasts = RUN.missing_outcome_bounds(data, "adjacent_month")
    row = next(item for item in contrasts if item["margin"] == "employment_exit")
    assert row["missing_source_record_count"] == 7
    assert np.isclose(row["linear_probability_contrast_lower"], -1.5)
    assert np.isclose(row["linear_probability_contrast_upper"], 1.5)
    assert "common outcome per source record" in row["joint_feasibility_scope"]


def test_observable_poststratification_preserves_complete_balanced_cells() -> None:
    data = bound_frame()
    data["LNKFW1MWT"] = np.where(data.analysis_link, 1.0, 0.0)
    data["LNKFW1YWT"] = data.LNKFW1MWT
    data["AGE"] = np.where(data.age_group.eq("young_22_25"), 23, 40)
    data["MISH"] = 1
    data["education_group"] = "non_BA"
    data["full_time_35plus"] = True
    data["YEAR"] = np.where(data.period.eq("pre"), 2021, 2023)
    rates, contrasts = RUN.poststratified_rows(data, "adjacent_month")
    assert len(rates) == 24
    assert len(contrasts) == 9
    for row in rates:
        assert row["unsupported_eligible_share"] == 0
        assert row["poststrat_factor_min"] == row["poststrat_factor_max"] == 2
        assert np.isclose(row["origin_WTFINL_complete_case_probability"],
                          row["observable_poststratified_probability"])


def test_intensity_design_reduces_to_binary_legacy_design() -> None:
    rows = []
    for occ, q, webb in (("0100", 1, -1.0), ("0200", 5, 1.0)):
        for month in ("2022-11", "2023-01"):
            for age in ("young_22_25", "older_26_65"):
                rows.append({"occ_code": occ, "month": month, "age_group": age,
                             "quintile": q, "webb_z": webb, "risk": 10.0, "event": 2.0})
    cells = pd.DataFrame(rows)
    legacy = RUN.LEGACY.design_from_cells(cells)
    current = RUN.design_with_intensity(cells, {"2022-11": 0.0, "2023-01": 1.0})
    assert np.array_equal(legacy["regressors"], current["regressors"])


def test_spec_fixes_required_scope_and_does_not_overclaim() -> None:
    text = " ".join((HERE / "FLOW_SELECTION_SPEC.md").read_text().split())
    for marker in ("eligible-but-not-retained", "conditional missing-at-random",
                       "positive or negative infinity", "remaining nonemployed",
                       "outside retained exposure support", "employer hiring rate",
                   "fraction of the twelve destination months", "EARNWEEK2"):
        assert marker in text
    assert "Lee trimming" in text
    assert "causal AI" in text
