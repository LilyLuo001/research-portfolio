"""Pin the inversion and the repair."""

import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "bound_repair", ROOT / "memo" / "nonevaluable_bound_repair.py")
assert SPEC and SPEC.loader
R = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(R)

SHARES = [0.05, 0.15, 0.30, 0.50, 0.80]


def test_v3_upper_bound_inverts_the_ordering():
    """5% evaluable must not outrank 80% evaluable — but under the rule it does."""
    low_evaluable = R.level_bounds(0.05, 0.40)[1]
    high_evaluable = R.level_bounds(0.80, 0.40)[1]
    assert low_evaluable > high_evaluable
    assert R.upper_bound_inverts(SHARES, 0.40)


def test_lower_bound_does_not_invert():
    """Only the upper rule is broken; B*E is increasing in B, as it should be."""
    assert R.level_bounds(0.05, 0.40)[0] < R.level_bounds(0.80, 0.40)[0]


def test_dose_multiplier_never_inverts_on_the_unit_interval():
    for kappa in (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0):
        assert R.multiplier_preserves_order(SHARES, kappa), kappa


def test_kappa_endpoints_have_their_intended_meaning():
    # kappa = 0 : digitally identified — multiplier is the evaluable share
    assert R.dose_multiplier(0.3, 0.0) == 0.3
    # kappa = 1 : all mass crosses at the digital rate — uniform multiplier
    assert all(R.dose_multiplier(b, 1.0) == 1.0 for b in SHARES)
