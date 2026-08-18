"""Pin the §3.2 window rule and the D1 finding as tests, not as an argument.

The point of these is that a future change to the rule, the registry, or the
power simulation cannot quietly restore agreement. If any of these fail, the
memo and the code have diverged again and someone must look.
"""

import csv
import pathlib
import sys

MEMO = pathlib.Path(__file__).resolve().parents[1] / "memo"
sys.path.insert(0, str(MEMO))

from validate_window_survival import (  # noqa: E402
    MIN_EVENTS, clean_window, month_index, scenarios, survival,
)


def test_reproduces_the_memos_own_worked_example():
    """§3.2: April and December origins eight months apart.

    "The origins are eight month indices apart, so August is the tied midpoint
    and is excluded; April keeps May--July and December keeps September--
    November on their adjacent sides."

    If this fails, the implementation is not the memo's rule and every other
    number here is meaningless.
    """
    april, december = 0, 8
    _, april_post = clean_window(april, None, december)
    december_pre, _ = clean_window(december, april, None)
    assert april_post == 3, "April should keep exactly May, June, July"
    assert december_pre == 3, "December should keep exactly Sep, Oct, Nov"


def test_equidistant_month_is_excluded_from_both_sides():
    focal, following = 0, 8
    _, post = clean_window(focal, None, following)
    pre, _ = clean_window(following, focal, None)
    # month +4 from April is month -4 from December: claimed by neither.
    assert post + pre == 6, "the tied midpoint must not be double-counted"


def test_same_calendar_month_rows_compound_to_one_origin():
    windows = survival(["2026-03-05", "2026-03-17"])
    assert len(windows) == 1, "§3.2 compounds same-month rows into one origin"


def _registry_rows():
    path = MEMO / "event_registry_v1.csv"
    return list(csv.DictReader(path.open(encoding="utf-8")))


def test_D1_current_eligible_set_cannot_be_estimated():
    """The finding itself: 4 eligible rows -> 2 estimable, below the gate."""
    dates = scenarios(_registry_rows())[
        "A: only rows currently `eligible` (what the power sim assumed)"]
    estimable = [w for w in survival(dates) if w.estimable]
    assert len(dates) == 4, "registry no longer has exactly 4 eligible rows"
    assert len(estimable) == 2, (
        "the §3.2 window rule should leave exactly 2 estimable events; "
        "if this changed, the rule or the registry moved and the power "
        "simulation's event set must be re-derived"
    )
    assert len(estimable) < MIN_EVENTS, "power engine hard-fails below 3 events"


def test_completing_the_registry_makes_identification_worse():
    """Non-monotonicity — the planning consequence, pinned."""
    sets = scenarios(_registry_rows())
    counts = {
        name[0]: len([w for w in survival(dates) if w.estimable])
        for name, dates in sets.items()
    }
    assert counts["C"] <= counts["A"], (
        "resolving candidate events should not increase estimable events "
        "under a midpoint-contamination rule; if it now does, §3.2 changed"
    )
    assert counts["C"] < MIN_EVENTS


def test_gpt41_and_gpt5_are_the_events_that_drop():
    """Names the mechanism so the fix can be targeted, not guessed at."""
    windows = {w.label: w for w in survival(
        scenarios(_registry_rows())[
            "A: only rows currently `eligible` (what the power sim assumed)"])}
    assert not windows["2025-04"].estimable, "GPT-4.1 loses its post window"
    assert not windows["2025-08"].estimable, "GPT-5 loses its pre window"
    assert windows["2023-03"].estimable and windows["2024-05"].estimable


def test_power_simulation_still_disagrees_with_the_rule():
    """The sim gives every event a full window; §3.2 does not. Pinned until fixed."""
    source = (MEMO / "power_calcs" / "simulate_power.py").read_text(encoding="utf-8")
    assert "range(-6, 7)" in source, (
        "simulate_power.py no longer hard-codes a full [-6,+6] window — if the "
        "clean-window rule was implemented, delete this test and re-derive the "
        "power result, which currently assumes 4 events where §3.2 allows 2"
    )
