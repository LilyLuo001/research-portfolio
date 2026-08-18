"""REFR-R1b transform + assertions, on synthetic rows.

Per the iron rules these assert about the machinery — standardization, the
scheduled-window policy, the acceptance assertions — never about the world. No
USMPD file is touched or imagined: the parse stage is deliberately unimplemented.
"""
import math
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from refraction.pipeline import surprises as sp  # noqa: E402

CONFIG = yaml.safe_load(
    (Path(__file__).resolve().parents[1] / "frozen_config.yaml").read_text())


def row(type_="FOMC", date="2022-06-15", time=None, s_raw=1.0, scheduled=True,
        source="USMPD"):
    if time is None:
        time = CONFIG["panel"]["release_times_ET"][type_]
    return {"type": type_, "date_ET": date, "time_ET": time, "S_raw": s_raw,
            "S_std": None, "source": source, "is_scheduled": scheduled}


def cal(type_="FOMC", date="2022-06-15"):
    return {"type": type_, "date_ET": date,
            "time_ET": CONFIG["panel"]["release_times_ET"][type_],
            "is_scheduled": True, "source": "federalreserve.gov"}


# --------------------------------------------------------------------------- #
# the stage that must NOT be guessed                                           #
# --------------------------------------------------------------------------- #

def test_parse_stage_refuses_rather_than_inventing_a_schema():
    with pytest.raises(sp.NeedInfo) as e:
        sp.parse_usmpd("anything.csv")
    msg = str(e.value)
    assert msg.startswith("NEED_INFO")
    assert "column list" in msg and "unscheduled" in msg


def test_an_unknown_standardization_policy_is_refused_not_defaulted():
    cfg = {**CONFIG, "surprise": {**CONFIG["surprise"], "standardize": "zscore_full"}}
    with pytest.raises(sp.NeedInfo):
        sp.standardize([row()], cfg)


# --------------------------------------------------------------------------- #
# standardization                                                              #
# --------------------------------------------------------------------------- #

def test_s_std_is_s_raw_over_the_in_sample_std_per_type():
    rows = [row(s_raw=1.0, date="2022-01-26"), row(s_raw=3.0, date="2022-03-16")]
    out, diag = sp.standardize(rows, CONFIG)
    sd = diag["sd_by_type"]["FOMC"]
    assert sd == pytest.approx(math.sqrt(2.0))          # sample std of {1,3}
    assert [r["S_std"] for r in out] == pytest.approx([1 / sd, 3 / sd])


def test_each_type_is_standardized_on_its_own_scale():
    rows = [row(s_raw=1.0, date="2022-01-26"), row(s_raw=3.0, date="2022-03-16"),
            row("CPI", "2022-02-10", s_raw=10.0), row("CPI", "2022-03-10", s_raw=30.0)]
    out, diag = sp.standardize(rows, CONFIG)
    assert diag["sd_by_type"]["CPI"] == pytest.approx(10 * math.sqrt(2.0))
    fomc = [r["S_std"] for r in out if r["type"] == "FOMC"]
    cpi = [r["S_std"] for r in out if r["type"] == "CPI"]
    assert fomc == pytest.approx(cpi)                   # same shape, different units


@pytest.mark.parametrize("missing", [None, "", float("nan")])
def test_a_release_with_no_consensus_gets_null_not_zero(missing):
    """A CPI row without consensus has no surprise. Writing 0.0 would assert
    'the release matched expectations' — a fabricated fact, not a default."""
    rows = [row("CPI", "2022-02-10", s_raw=1.0), row("CPI", "2022-03-10", s_raw=3.0),
            row("CPI", "2022-04-12", s_raw=missing)]
    out, diag = sp.standardize(rows, CONFIG)
    assert out[-1]["S_std"] is None
    assert diag["null_S_std_by_type"]["CPI"] == 1


def test_a_single_observation_yields_null_not_a_divide_by_zero():
    out, _ = sp.standardize([row()], CONFIG)
    assert out[0]["S_std"] is None


def test_a_constant_series_yields_null_not_infinity():
    rows = [row(s_raw=2.0, date="2022-01-26"), row(s_raw=2.0, date="2022-03-16")]
    out, _ = sp.standardize(rows, CONFIG)
    assert all(r["S_std"] is None for r in out)


# --------------------------------------------------------------------------- #
# scheduled-window policy                                                      #
# --------------------------------------------------------------------------- #

def test_unscheduled_meetings_are_excluded_per_config_and_counted():
    rows = [row(), row(date="2022-03-16", scheduled=False)]
    kept, dropped = sp.apply_scheduled_policy(rows, CONFIG)
    assert CONFIG["surprise"]["exclude_unscheduled"] is True
    assert len(kept) == 1 and len(dropped) == 1


def test_the_policy_is_read_from_config_never_decided_here():
    cfg = {**CONFIG, "surprise": {**CONFIG["surprise"], "exclude_unscheduled": False}}
    kept, dropped = sp.apply_scheduled_policy(
        [row(), row(date="2022-03-16", scheduled=False)], cfg)
    assert len(kept) == 2 and dropped == []


# --------------------------------------------------------------------------- #
# acceptance assertions                                                        #
# --------------------------------------------------------------------------- #

def test_clean_series_passes_every_assertion():
    rows, rep, _ = sp.build([row(), row(date="2022-03-16", s_raw=2.0)],
                            [cal(), cal(date="2022-03-16")], CONFIG)
    assert rep["overall_pass"] and rep["reconciliation_pass"]


def test_duplicate_type_date_is_caught():
    rep = sp.a1_no_duplicate_keys([row(), row()])
    assert not rep["pass"] and rep["offending"] == [["FOMC", "2022-06-15"]]


def test_a_year_silently_lost_in_parsing_is_caught_against_the_calendar():
    """The assertion that exists because a parse can lose a year without erroring."""
    rows = [row(date="2022-06-15")]
    calendar = [cal(date="2022-06-15"), cal(date="2023-06-14")]
    rep = sp.a2_reconciles_with_calendar(rows, calendar)
    assert not rep["pass"]
    assert rep["offending"][0] == {"type": "FOMC", "year": "2023",
                                   "surprises": 0, "calendar": 1}


@pytest.mark.parametrize("bad", [float("inf"), float("nan"), -float("inf")])
def test_non_finite_s_std_fails_while_null_stays_legal(bad):
    rep = sp.a3_s_std_finite_or_null([{**row(), "S_std": bad},
                                      {**row(date="2022-03-16"), "S_std": None}])
    assert not rep["pass"] and rep["n_null"] == 1


def test_a_timezone_slip_in_release_times_is_caught():
    """FOMC at 13:00 instead of 14:00 would misalign every announcement window
    downstream, and nothing else in the chain would notice."""
    rep = sp.a4_release_times_match_config([row(time="13:00")], CONFIG)
    assert not rep["pass"]
    assert rep["offending"][0]["expected"] == CONFIG["panel"]["release_times_ET"]["FOMC"]


def test_rows_outside_the_registered_window_are_caught():
    rep = sp.a5_within_registered_sample_window(
        [row(date="2016-12-14"), row(date="2027-01-27")], CONFIG)
    assert not rep["pass"] and len(rep["offending"]) == 2


def test_reconciliation_failure_does_not_by_itself_void_the_build():
    """A2 compares against R1a's calendar, which may legitimately not exist yet;
    it is reported separately from the hard asserts rather than blocking them."""
    rows, rep, _ = sp.build([row()], [], CONFIG)
    assert rep["overall_pass"] is True
    assert rep["reconciliation_pass"] is False
    assert "A2_calendar_reconciliation" not in sp.HARD


def test_build_reports_what_it_dropped():
    _, _, diag = sp.build([row(), row(date="2022-03-16", scheduled=False)],
                          [cal()], CONFIG)
    assert diag["dropped_unscheduled"] == 1


def test_contract_columns_match_the_frozen_contract():
    contract = yaml.safe_load(
        (Path(__file__).resolve().parents[2] / "ops" / "contracts" /
         "surprises.yaml").read_text())
    assert set(sp.SURPRISE_COLUMNS) == set(contract["columns"])
    cal_contract = yaml.safe_load(
        (Path(__file__).resolve().parents[2] / "ops" / "contracts" /
         "macro_calendar.yaml").read_text())
    assert set(sp.CALENDAR_COLUMNS) == set(cal_contract["columns"])
