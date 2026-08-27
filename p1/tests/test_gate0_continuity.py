"""Gate 0 continuity measures — offline proof before any holdings exist.

The wrapper narrative ("same portfolio, different shell") is a falsifiable claim
about holdings. These measures decide it, so they are pinned here rather than
first exercised on the day the post-conversion N-PORT lands.
"""
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "p1" / "gate0_continuity" / "compute_continuity.py"
sys.path.insert(0, str(SCRIPT.parent))

import compute_continuity as cc  # noqa: E402


def test_selftest_passes():
    r = subprocess.run([sys.executable, str(SCRIPT), "--selftest"],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr


def test_name_overlap_alone_would_miss_a_full_reweighting():
    """Why weight_overlap is the headline and jaccard is not.

    A fund that keeps every ticker but inverts the weights is NOT the same
    portfolio in a different wrapper. Jaccard says 1.0; the headline measure
    must catch it.
    """
    r = cc.continuity({"AAA": 90.0, "BBB": 10.0}, {"AAA": 10.0, "BBB": 90.0})
    assert r["name_jaccard"] == 1.0
    assert abs(r["weight_overlap"] - 0.2) < 1e-9
    assert cc.classify(r["weight_overlap"], r["turnover"]) == "not_a_wrapper_change"


def test_thresholds_are_the_ex_ante_ones():
    """Frozen before the distribution is seen (plan 9.0). Changing these after
    looking at real data is specification search."""
    assert cc.MAIN_FLOOR == 0.80
    assert cc.PARTIAL_FLOOR == 0.60
    assert cc.SENSITIVITY == (0.70, 0.80, 0.90)


def test_high_turnover_demotes_even_with_high_overlap():
    assert cc.classify(0.95, 0.50) == "partial"


def test_blocked_path_exits_two_and_says_why():
    r = subprocess.run([sys.executable, str(SCRIPT)],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 2
    assert "BLOCKED" in r.stdout and "POST-conversion" in r.stdout


# --------------------------------------------------------------------------- #
# v2.1b — corporate-action adjustment (item 3)                                 #
# --------------------------------------------------------------------------- #
def test_unadjusted_split_reads_as_turnover_and_adjustment_fixes_it():
    """A 2:1 split with zero trading must not look like the manager bought."""
    raw_pre, raw_post = {"AAA": 100.0}, {"AAA": 200.0}
    assert cc.share_continuity(raw_pre, raw_post)["share_turnover"] == 0.5
    adj = cc.share_continuity(cc.adjust_shares(raw_pre, {"AAA": 1.0}),
                              cc.adjust_shares(raw_post, {"AAA": 2.0}))
    assert adj["share_turnover"] == 0.0
    assert adj["share_overlap"] == 1.0


def test_missing_adjustment_factor_refuses_rather_than_defaulting_to_one():
    """Defaulting to 1.0 would silently assume 'no corporate action'."""
    with pytest.raises(cc.UnadjustedShares) as e:
        cc.adjust_shares({"AAA": 1.0, "ZZZ": 1.0}, {"AAA": 1.0})
    assert "ZZZ" in str(e.value)


def test_non_positive_factor_refuses():
    for bad in (0.0, -1.0, None):
        with pytest.raises(cc.UnadjustedShares):
            cc.adjust_shares({"AAA": 1.0}, {"AAA": bad})
