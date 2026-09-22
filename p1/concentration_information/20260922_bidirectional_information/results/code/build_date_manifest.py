#!/usr/bin/env python3
"""Create the predeclared 2023 NYSE date and chronological split manifest."""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

OLD_PILOT_DATES = {"2023-01-31", "2023-02-03", "2023-08-04"}

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(); args.out.parent.mkdir(parents=True, exist_ok=True)
    # NYSE's published 2023 full-day closures (early closes remain sessions).
    holidays = pd.to_datetime(["2023-01-02", "2023-01-16", "2023-02-20", "2023-04-07",
                               "2023-05-29", "2023-06-19", "2023-07-04", "2023-09-04",
                               "2023-11-23", "2023-12-25"])
    sessions = pd.bdate_range("2023-01-01", "2023-12-31").difference(holidays)
    selected: list[pd.Timestamp] = []
    for month in pd.period_range("2023-01", "2023-12", freq="M"):
        month_sessions = sessions[(sessions.month == month.month)]
        for ordinal in (5, 15):
            candidate = month_sessions[ordinal - 1]
            # This loop is intentionally only calendar/previous-sample driven.
            while str(candidate.date()) in OLD_PILOT_DATES or candidate in selected:
                candidate = month_sessions[month_sessions.get_loc(candidate) + 1]
            selected.append(candidate)
    frame = pd.DataFrame({"date": [str(x.date()) for x in selected],
                          "nyse_session_ordinal": [5, 15] * 12,
                          "window_et": "10:00:00-10:30:00",
                          "grid_shifts_ms": "0;500"})
    frame["split"] = ["train"] * 12 + ["valid"] * 4 + ["test"] * 8
    assert len(frame) == 24 and frame.date.nunique() == 24
    assert not set(frame.date) & OLD_PILOT_DATES
    frame.to_csv(args.out, index=False)

if __name__ == "__main__":
    main()
