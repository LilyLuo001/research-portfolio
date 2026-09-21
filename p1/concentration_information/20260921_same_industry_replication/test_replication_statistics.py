#!/usr/bin/env python3
"""Synthetic, outcome-free tests for the frozen replication estimand."""
from pathlib import Path
import tempfile

import numpy as np
import pandas as pd

from replication_statistics import H1_X_MEAN, H1_X_SD, add_frozen_terms, design_diagnostics, fit_primary, support_gate, verify_opening_gate


def fixture(blocks=8):
    rows = []
    for b in range(blocks):
        for e in range(2):
            event = f"B{b}E{e}"
            issuer = f"I{b % 3}"
            for i in range(12):
                same = i % 2
                x = -1.5 + 3 * i / 11 + .03 * e
                size = 8 + .2 * ((i * 3 + b) % 7)
                liq = 5 + .1 * ((i * 5 + b) % 11)
                y = .4 * x + .7 * same + 1.1 * x * same + .05 * size - .02 * liq + .01 * b
                rows.append({"outcome": y, "event_id": event, "block_id": f"B{b}", "issuer_id": issuer,
                             "receiver_id": f"R{i}", "pair_strength": np.exp(H1_X_MEAN + H1_X_SD * x),
                             "same_sic2": same, "log_size": size, "log_liquidity": liq})
    return pd.DataFrame(rows)


def main():
    f = fixture()
    terms = add_frozen_terms(f)
    assert np.max(np.abs(terms.x_std - np.tile(np.linspace(-1.5, 1.5, 12), 16).reshape(16, 12).ravel() - np.repeat(np.tile([0, .03], 8), 12))) < 1e-10
    d = design_diagnostics(f.drop(columns="outcome"))
    ok, reasons = support_gate(d, calendar_reuse_count=0, minimum_controls=2)
    assert ok, reasons
    dup = pd.concat([f, f.iloc[[0]]], ignore_index=True)
    no, reasons = support_gate(design_diagnostics(dup), 0, 2)
    assert not no and "duplicate_event_receiver_design_keys" in reasons
    no, reasons = support_gate(design_diagnostics(fixture(7)), 0, 2)
    assert not no and "fewer_than_8_disjoint_calendar_blocks" in reasons
    no, reasons = support_gate(design_diagnostics(f.iloc[:0]), 0, 0)
    assert not no and "main_design_not_full_rank" in reasons and "receiver_event_with_fewer_than_2_controls" in reasons
    ans = fit_primary(f)
    assert abs(ans["coefficients"]["x_std"] - .4) < 1e-9
    assert abs(ans["same_industry_slope"] - 1.5) < 1e-9
    assert abs(ans["same_minus_other_slope"] - 1.1) < 1e-9
    with tempfile.TemporaryDirectory() as td:
        try:
            verify_opening_gate(Path(td), [])
            raise AssertionError("missing gate did not block response opening")
        except PermissionError:
            pass
    print("replication synthetic estimand and opening-gate fixtures: PASS")


if __name__ == "__main__":
    main()
