"""Regression tests for the common-support audit's statistics.

These pin the arithmetic, not the substantive results. The audit's job is to
report measurement properties honestly, so the things worth guarding are the
places where a plausible-looking number would be wrong: weighted correlation
under unequal weights, Spearman under ties, the Kish effective n, and -- the
one that actually bit -- the refusal to emit quartiles that do not exist.
"""

import importlib.util
import math
import pathlib

MODULE = (pathlib.Path(__file__).resolve().parents[1]
          / "w2" / "exposure_gate" / "audit_common_support.py")
SPEC = importlib.util.spec_from_file_location("audit_common_support", MODULE)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def test_wcorr_matches_unweighted_pearson_when_weights_are_equal():
    x = [1.0, 2.0, 3.0, 4.0, 7.0]
    y = [2.0, 1.0, 4.0, 3.0, 9.0]
    assert math.isclose(audit.wcorr(x, y), audit.wcorr(x, y, [3.0] * 5), rel_tol=1e-12)


def test_wcorr_weights_actually_bind():
    """One heavily weighted point should move the correlation, not be ignored."""
    x = [0.0, 1.0, 2.0, 3.0]
    y = [0.0, 1.0, 2.0, -9.0]
    assert audit.wcorr(x, y) > audit.wcorr(x, y, [1.0, 1.0, 1.0, 50.0])


def test_wcorr_returns_none_when_a_margin_is_constant():
    assert audit.wcorr([1.0, 1.0, 1.0, 1.0], [1.0, 2.0, 3.0, 4.0]) is None


def test_ranks_average_ties():
    assert audit.ranks([10.0, 20.0, 20.0, 40.0]) == [1.0, 2.5, 2.5, 4.0]


def test_spearman_is_one_under_a_monotone_nonlinear_transform():
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    y = [math.exp(v) for v in x]
    assert math.isclose(audit.wspearman(x, y), 1.0, rel_tol=1e-12)
    assert audit.wcorr(x, y) < 0.95  # Pearson is not, which is why item 1 has both


def test_kish_effective_n():
    assert math.isclose(audit.kish_n([1.0] * 10), 10.0, rel_tol=1e-12)
    # one dominant weight collapses the effective sample toward one
    assert audit.kish_n([1.0, 1.0, 1.0, 1000.0]) < 1.02


def test_wols_recovers_a_known_line():
    x = [0.0, 1.0, 2.0, 3.0]
    y = [2.0 + 3.0 * v for v in x]
    a, b, res = audit.wols(y, x, [1.0, 5.0, 2.0, 7.0])
    assert math.isclose(a, 2.0, abs_tol=1e-9)
    assert math.isclose(b, 3.0, abs_tol=1e-9)
    assert max(abs(r) for r in res) < 1e-9


def test_residual_structure_returns_none_without_regressor_variation():
    keys = [f"11-{i:04d}" for i in range(60)]
    flat = {k: 0.0 for k in keys}
    assert audit.residual_structure(flat, {k: float(i) for i, k in enumerate(keys)},
                                    {k: 1.0 for k in keys}, {}, keys) is None


def test_residual_structure_flags_concentration():
    """A single outlier must dominate the reported residual variance."""
    keys = [f"11-{i:04d}" for i in range(60)]
    dn = {k: (i % 2) * 1.0 for i, k in enumerate(keys)}
    series = {k: dn[k] * 0.3 for k in keys}   # perfectly on the line...
    emp = {k: 100.0 for k in keys}
    title = {k: k for k in keys}
    odd = keys[7]
    series[odd] = 50.0                        # ...except for one occupation
    out = audit.residual_structure(dn, series, emp, title, keys)
    conc = out["concentration_of_weighted_residual_variance"]
    assert conc["occupations_to_reach_half"] == 1
    assert conc["effective_number_of_occupations"] < 1.1
    assert out["largest_contributors_to_residual_variance"][0]["soc"] == odd


def test_item7_refuses_degenerate_quartiles():
    """The real Dingel-Neiman positive subsample piles up at 1.0. When the
    quartile cuts are not distinct the audit must say so, not emit a table
    with one populated cell."""
    keys = [f"43-{i:04d}" for i in range(40)]
    dn = {k: 1.0 for k in keys}
    dn[keys[0]] = 0.5
    series = {k: 0.2 for k in keys}
    emp = {k: 1000.0 for k in keys}
    out = audit.positive_telework_contrast(dn, series, emp, {k: k for k in keys}, keys)
    assert out["quartiles_degenerate"] is True
    assert out["quartiles"] is None
    assert out["fully_vs_partially"]["partially_teleworkable_0_lt_share_lt_1"]["n_occupations"] == 1
    assert out["distribution_among_positive"]["n_at_exactly_1.0"] == 39


def test_item7_uses_quartiles_when_they_exist():
    keys = [f"43-{i:04d}" for i in range(40)]
    dn = {k: (i + 1) / 40.0 for i, k in enumerate(keys)}
    series = {k: dn[k] * 0.5 for k in keys}
    emp = {k: 1000.0 for k in keys}
    out = audit.positive_telework_contrast(dn, series, emp, {k: k for k in keys}, keys)
    assert out["quartiles_degenerate"] is False
    assert set(out["quartiles"]) == {"Q1", "Q2", "Q3", "Q4"}


def test_item2_is_reported_as_blocked_not_silently_skipped():
    """Item 2 needs bls.gov, which this environment cannot reach. A future
    reader must find an explicit BLOCKED status rather than an absence."""
    src = MODULE.read_text(encoding="utf-8")
    assert '"item2_blocked"' in src
    assert '"status": "BLOCKED"' in src
