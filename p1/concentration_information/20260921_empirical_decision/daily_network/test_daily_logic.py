#!/usr/bin/env python3
"""Outcome-free logical fixtures for the daily analysis."""
import numpy as np
import pandas as pd

from run_daily_network import compound, overlap_components, window_has_calendar_date


def main():
    assert abs(compound([0.10, -0.05]) - 0.045) < 1e-12
    assert np.isnan(compound([0.10, np.nan]))
    windows = {
        pd.Timestamp("2023-01-03"): (pd.Timestamp("2023-01-03"), pd.Timestamp("2023-01-04")),
        pd.Timestamp("2023-01-04"): (pd.Timestamp("2023-01-04"), pd.Timestamp("2023-01-05")),
        pd.Timestamp("2023-01-09"): (pd.Timestamp("2023-01-09"), pd.Timestamp("2023-01-10")),
    }
    blocks = overlap_components(windows)
    assert blocks[pd.Timestamp("2023-01-03")] == blocks[pd.Timestamp("2023-01-04")]
    assert blocks[pd.Timestamp("2023-01-09")] != blocks[pd.Timestamp("2023-01-03")]
    # A holiday/weekend release between two trading closes is detected.
    assert window_has_calendar_date(pd.Timestamp("2023-04-06"), pd.Timestamp("2023-04-10"), {pd.Timestamp("2023-04-07")}, left_open=True)
    assert not window_has_calendar_date(pd.Timestamp("2023-04-06"), pd.Timestamp("2023-04-10"), {pd.Timestamp("2023-04-06")}, left_open=True)
    print("daily logical fixtures: PASS")


if __name__ == "__main__":
    main()
