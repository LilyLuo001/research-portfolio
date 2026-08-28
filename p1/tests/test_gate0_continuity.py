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
def test_synthetic_split_cancels_under_the_frozen_convention():
    """Mechanism check ONLY.

    This CANNOT validate the direction: if the code multiplied where it should
    divide, a synthetic test whose factors were written to match would still
    pass. Direction is validated against a real split below.
    Under crsp_cfacshr (adjusted = raw * cfacshr) a 2:1 split HALVES the factor.
    """
    raw_pre, raw_post = {"AAA": 100.0}, {"AAA": 200.0}
    assert cc.share_continuity(raw_pre, raw_post)["share_turnover"] == 0.5
    adj = cc.share_continuity(
        cc.adjust_shares(raw_pre, {"AAA": 1.0}, convention="crsp_cfacshr"),
        cc.adjust_shares(raw_post, {"AAA": 0.5}, convention="crsp_cfacshr"))
    assert adj["share_turnover"] == 0.0
    assert adj["share_overlap"] == 1.0


def test_convention_must_be_named_and_is_frozen():
    """No default: the direction is the whole risk (v2.1c, item 1)."""
    with pytest.raises(TypeError):
        cc.adjust_shares({"A": 1.0}, {"A": 1.0})          # positional / missing kw
    with pytest.raises(cc.UnadjustedShares) as e:
        cc.adjust_shares({"A": 1.0}, {"A": 1.0}, convention="cfacshr-style")
    assert "unknown adjustment convention" in str(e.value)
    assert cc.ADJUSTMENT_CONVENTIONS["crsp_cfacshr"] == "multiply", (
        "Frozen: CRSP adjusted shares = raw * CFACSHR (owner-supplied "
        "2026-08-27). Flipping this silently inverts every split.")


def test_missing_adjustment_factor_refuses_rather_than_defaulting_to_one():
    """Defaulting to 1.0 would silently assume 'no corporate action'."""
    with pytest.raises(cc.UnadjustedShares) as e:
        cc.adjust_shares({"AAA": 1.0, "ZZZ": 1.0}, {"AAA": 1.0},
                         convention="crsp_cfacshr")
    assert "ZZZ" in str(e.value)


def test_non_positive_factor_refuses():
    for bad in (0.0, -1.0, None):
        with pytest.raises(cc.UnadjustedShares):
            cc.adjust_shares({"AAA": 1.0}, {"AAA": bad}, convention="crsp_cfacshr")


# --------------------------------------------------------------------------- #
# INTEGRATION — the only test that can catch an inverted convention            #
# --------------------------------------------------------------------------- #
CRSP_MSF = ROOT / "p1" / "wrds" / "raw" / "msf__msf.parquet"


def test_direction_against_a_real_crsp_split():
    """Validate the convention on a REAL historical split, not a synthetic one.

    Method, using only the landed data (no assumed split ratios):
      1. find permno-months where CFACSHR changes -> candidate corporate actions
      2. take the largest such change (a clean split dominates)
      3. hold shares constant across it and adjust both sides
      4. under the CORRECT direction the adjusted counts are equal; under the
         inverted one they differ by the square of the factor ratio

    Step 4 is what a synthetic test cannot do: here the factor values come from
    CRSP, so only one direction reconciles.
    """
    if not CRSP_MSF.exists():
        pytest.skip(
            "BLOCKED: needs landed CRSP msf with CFACSHR. Until this runs, the "
            "crsp_cfacshr direction is OWNER-ASSERTED, not verified. Pull it "
            "with the WRDS sprint (ops/briefs/P1-WRDS-SPRINT.md) and re-run.")
    import pandas as pd
    df = pd.read_parquet(CRSP_MSF)
    col = next((c for c in df.columns if c.lower() == "cfacshr"), None)
    assert col, (
        f"msf landed without CFACSHR (got {sorted(df.columns)}). Add it to the "
        "msf pull in p1/wrds/tables.yaml — Gate 0 cannot adjust shares without it.")

    d = df.sort_values(["permno", "date"])
    d["prev"] = d.groupby("permno")[col].shift()
    ch = d[(d["prev"].notna()) & (d[col] != d["prev"])].copy()
    assert len(ch), "no CFACSHR changes found — cannot validate the direction"
    ch["ratio"] = ch[col] / ch["prev"]
    row = ch.reindex(ch["ratio"].sub(1).abs().sort_values(ascending=False).index).iloc[0]

    # A holder who did not trade: raw shares scale by 1/ratio across the action.
    raw_pre, raw_post = 100.0, 100.0 / float(row["ratio"])
    adj_pre = cc.adjust_shares({"X": raw_pre}, {"X": float(row["prev"])},
                               convention="crsp_cfacshr")["X"]
    adj_post = cc.adjust_shares({"X": raw_post}, {"X": float(row[col])},
                                convention="crsp_cfacshr")["X"]
    assert adj_pre == pytest.approx(adj_post, rel=1e-9), (
        f"CFACSHR direction is INVERTED. permno {row['permno']} on {row['date']}: "
        f"factor {row['prev']} -> {row[col]} (ratio {row['ratio']:.4f}); "
        f"adjusted {adj_pre:.4f} vs {adj_post:.4f}. Flip "
        "ADJUSTMENT_CONVENTIONS['crsp_cfacshr'] and re-run Gate 0 from scratch.")
