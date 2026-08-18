"""p1/design/russell_fallback_check.py — counts must be reproducible and honest.

The script answers a design question from committed data: does the plan's
§133(iii) Russell fallback (2022-2025 non-June waves) have a sample? Its numbers
feed a T5 spec decision, so they need to be checked rather than eyeballed once.
"""
import datetime as dt
import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "russell_fallback_check", ROOT / "p1" / "design" / "russell_fallback_check.py")
rf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rf)


@pytest.fixture(scope="module")
def report():
    return rf.analyse()


def test_waves_partition_cleanly_by_june(report):
    """June and non-June must account for every usable wave, with no overlap."""
    waves = [w for w in rf.load_waves()
             if dt.date.fromisoformat(w["effective_date"]) <= dt.date.today()]
    june = [w for w in waves if w["in_june"]]
    non = [w for w in waves if not w["in_june"]]
    assert len(june) + len(non) == len(waves) == report["all_waves"]["n_waves"]
    assert all(w["month"] == 6 for w in june)


def test_future_dated_waves_are_excluded_from_every_count(report):
    """Three waves are effective after today; counting them would inflate the
    fallback with samples that do not exist yet."""
    all_waves = rf.load_waves()
    usable = report["all_waves"]["n_waves"]
    assert usable < len(all_waves), "future-dated waves must be dropped"
    for w in all_waves:
        if dt.date.fromisoformat(w["effective_date"]) > dt.date.today():
            assert w["year"] >= 2026


def test_fallback_window_is_exactly_the_plan_text(report):
    """§133(iii) says 2022-2025, non-June — not 2021, not June, not 2026."""
    fb = report["fallback_133iii"]
    assert fb["years"] == sorted(fb["years"])
    assert min(fb["years"]) >= 2022 and max(fb["years"]) <= 2025


def test_extended_window_is_a_superset_and_is_reported_separately(report):
    """The 2026 waves are a real power gain, but must not be silently folded
    into a number the plan defines as ending in 2025."""
    fb, ext = report["fallback_133iii"], report["fallback_extended"]
    assert ext["n_waves"] >= fb["n_waves"]
    assert ext["n_funds"] >= fb["n_funds"]


def test_anchor_is_unique_and_is_the_dfa_date(report):
    assert report["anchor"]["n_waves"] == 1
    june = report["june_wave_detail"]
    assert any(w["effective_date"] == rf.ANCHOR for w in june)


def test_june_waves_are_not_only_the_anchor(report):
    """The amendment names 2021-06 alone; the data says the reconstitution window
    catches more waves than that, which is the finding worth surfacing."""
    assert report["june_waves"]["n_waves"] > 1


def test_verdict_states_availability_and_the_stock_level_caveat(report):
    v = " ".join(rf.verdict(report))
    assert ("FALLBACK AVAILABLE" in v) or ("FALLBACK EMPTY" in v)
    # funds bound the design from above; treated stocks are the real constraint
    assert "treated STOCKS" in v


def test_fund_counts_never_exceed_the_event_file():
    import csv
    with open(ROOT / "p1" / "events_merged.csv", newline="") as f:
        n_events = len(list(csv.DictReader(f)))
    assert rf.analyse()["all_waves"]["n_funds"] <= n_events
