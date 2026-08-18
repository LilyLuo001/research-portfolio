"""Execute the memo's own §3.2 clean-window rule against its own event registry.

WHY THIS EXISTS
---------------
The W1 memo specifies a stacking protocol in §3.2 and, separately, a power
simulation. Both were written carefully. Neither was ever run against the
other, and they do not agree: the power engine gives every event a full
[-6,+6] window (`simulate_power.py`, `for event_time in range(-6, 7)`), while
§3.2 truncates windows at the midpoint between adjacent eligible events and
drops any event left with fewer than three clean months per side.

Applied to the four currently-eligible registry rows, §3.2 leaves **two**
estimable events. The power engine refuses to run below three
("approved minimum estimability requires at least three events"). So the
pre-registered protocol, executed as written on its own registry, cannot
produce a runnable primary analysis.

The rule is non-monotone in evidence quality, which is the part that matters
for planning: completing the registry makes identification *worse*, because
more eligible events means more adjacency and shorter clean windows. At 14
eligible events only one survives. W2 price work therefore cannot be
sequenced ahead of a decision on §3.2 without risking wasted effort.

This module is deliberately a *validator*, not a fix. Widening the window,
relaxing the 3+3 requirement, permitting overlapping stacks, or pre-registering
a fixed event subset are all [PI-DECISION] choices. An agent must not pick one,
least of all after seeing which choice passes.

    python dax/memo/validate_window_survival.py          # report
    python dax/memo/validate_window_survival.py --strict # exit 1 if infeasible
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import pathlib
import sys

REGISTRY = pathlib.Path(__file__).with_name("event_registry_v1.csv")

HALF_WIDTH = 6      # §3.2: "start with event time [-6,+6]"
MIN_PRE = 3         # §3.2: "at least three uncontaminated pre months"
MIN_POST = 3        # §3.2: "...and three uncontaminated post months"
MIN_EVENTS = 3      # Decision 13(c), enforced as a hard gate by simulate_power


@dataclasses.dataclass(frozen=True)
class EventWindow:
    month_index: int
    pre_months: int
    post_months: int

    @property
    def label(self) -> str:
        year, month = divmod(self.month_index, 12)
        return f"{year}-{month + 1:02d}"

    @property
    def estimable(self) -> bool:
        return self.pre_months >= MIN_PRE and self.post_months >= MIN_POST


def month_index(iso_date: str) -> int:
    year, month, _ = (int(part) for part in iso_date.split("-"))
    return year * 12 + (month - 1)


def clean_window(focal: int, previous: int | None, following: int | None,
                 half_width: int = HALF_WIDTH) -> tuple[int, int]:
    """§3.2 verbatim, as a pair of counts.

    "retain a month on the pre side only when its integer month distance to the
    focal event is strictly smaller than its distance to the previous eligible
    event, and retain a month on the post side only when its distance to the
    focal event is strictly smaller than its distance to the next eligible
    event. A calendar month exactly equidistant between two events is excluded
    from both windows."
    """
    pre = sum(1 for k in range(1, half_width + 1)
              if previous is None or k < abs((focal - k) - previous))
    post = sum(1 for k in range(1, half_width + 1)
               if following is None or k < abs(following - (focal + k)))
    return pre, post


def survival(dates: list[str], half_width: int = HALF_WIDTH) -> list[EventWindow]:
    """Compound same-calendar-month rows into one origin, then window each."""
    origins = sorted({month_index(d) for d in dates})
    windows: list[EventWindow] = []
    for position, focal in enumerate(origins):
        previous = origins[position - 1] if position else None
        following = origins[position + 1] if position + 1 < len(origins) else None
        pre, post = clean_window(focal, previous, following, half_width)
        windows.append(EventWindow(focal, pre, post))
    return windows


def scenarios(rows: list[dict[str, str]]) -> dict[str, list[str]]:
    """Three readings of "which events are eligible", worst case last."""
    live = [r for r in rows if r["analysis_status"] != "excluded_binding"]
    return {
        "A: only rows currently `eligible` (what the power sim assumed)":
            [r["api_effective_date"] for r in rows if r["analysis_status"] == "eligible"],
        "B: every date-`verified` row becomes eligible":
            [r["api_effective_date"] for r in live if r["verification_status"] == "verified"],
        "C: every non-excluded row becomes eligible (registry completed)":
            [r["api_effective_date"] for r in live],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 when the eligible scenario cannot be estimated")
    parser.add_argument("--half-width", type=int, default=HALF_WIDTH)
    args = parser.parse_args()

    rows = list(csv.DictReader(REGISTRY.open(encoding="utf-8")))
    counts: dict[str, int] = {}

    for name, dates in scenarios(rows).items():
        windows = survival(dates, args.half_width)
        estimable = [w for w in windows if w.estimable]
        counts[name[0]] = len(estimable)
        print(f"\n{name}")
        print(f"  {len(windows)} monthly origins -> {len(estimable)} estimable "
              f"(Decision 13c / power engine require >= {MIN_EVENTS})")
        for window in windows:
            verdict = "OK" if window.estimable else "DROP"
            print(f"    {window.label}  pre={window.pre_months} "
                  f"post={window.post_months}  {verdict}")

    print("\n" + "=" * 66)
    print(f"estimable events: A={counts['A']}  B={counts['B']}  C={counts['C']}")
    if counts["B"] < counts["A"] or counts["C"] < counts["A"]:
        print("NON-MONOTONE: completing the registry REDUCES estimable events.")
        print("Sequencing consequence: resolve §3.2 before, or alongside, W2.")
    if counts["A"] < MIN_EVENTS:
        print(f"INFEASIBLE AS WRITTEN: scenario A yields {counts['A']} < {MIN_EVENTS}.")
        print("This is a [PI-DECISION]; no agent may widen the window to clear it.")
        if args.strict:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
