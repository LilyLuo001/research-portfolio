"""Gate 0 continuity measures — offline proof before any holdings exist.

The wrapper narrative ("same portfolio, different shell") is a falsifiable claim
about holdings. These measures decide it, so they are pinned here rather than
first exercised on the day the post-conversion N-PORT lands.
"""
import pathlib
import subprocess
import sys

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
