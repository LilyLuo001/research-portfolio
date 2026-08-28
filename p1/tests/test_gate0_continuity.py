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


def _msf_actions(min_events=20):
    """Real corporate actions from landed CRSP msf: (prev_shrout, prev_cfacshr,
    shrout, cfacshr) at every permno-month where CFACSHR moves."""
    import pandas as pd
    df = pd.read_parquet(CRSP_MSF)
    cols = {c.lower(): c for c in df.columns}
    for need in ("permno", "date", "shrout", "cfacshr"):
        assert need in cols, (
            f"msf landed without {need.upper()} (got {sorted(df.columns)}). Add it "
            "to the msf pull in p1/wrds/tables.yaml — the direction of the share "
            "adjustment cannot be verified without BOTH raw shares and the factor.")
    d = df[[cols["permno"], cols["date"], cols["shrout"], cols["cfacshr"]]].copy()
    d.columns = ["permno", "date", "shrout", "cfacshr"]
    d = d.dropna().sort_values(["permno", "date"])
    d["prev_shrout"] = d.groupby("permno")["shrout"].shift()
    d["prev_cfacshr"] = d.groupby("permno")["cfacshr"].shift()
    ch = d[d["prev_cfacshr"].notna() & (d["cfacshr"] != d["prev_cfacshr"])
           & (d["shrout"] > 0) & (d["prev_shrout"] > 0)
           & (d["cfacshr"] > 0) & (d["prev_cfacshr"] > 0)].copy()
    if len(ch) < min_events:
        pytest.skip(
            f"BLOCKED: only {len(ch)} real CFACSHR changes in the landed msf; "
            f"need >= {min_events} for the median to mean anything. SHROUT also "
            "moves for issuance and buybacks, so a single event cannot decide "
            "the direction — a population can.")
    return ch


def test_direction_against_real_crsp_corporate_actions():
    """Validate the convention on REAL splits, using CRSP's own raw share counts.

    The earlier version of this test was circular. It took a real CFACSHR change,
    then MANUFACTURED the pre/post raw share counts as `raw_post = raw_pre/ratio`
    — i.e. it assumed shares move inversely to the factor, which is the same
    statement as "adjusted = raw x factor". Any convention would have passed a
    test whose raw side was derived from the convention under test.

    The non-circular version uses SHROUT, which CRSP reports independently of
    CFACSHR. In a true split with no issuance, raw shares outstanding mechanically
    change; the ADJUSTED series (raw x cfacshr under the frozen convention) must
    be continuous across the action, and the inverted convention must not be.

    SHROUT does move for real reasons (issuance, buybacks, repurchase programs) in
    the same month, so no single event is decisive. The test therefore compares
    the two conventions across the whole population of factor changes and requires
    the frozen one to win by an order of magnitude.
    """
    if not CRSP_MSF.exists():
        pytest.skip(
            "BLOCKED: needs landed CRSP msf with CFACSHR and SHROUT. Until this "
            "runs, the crsp_cfacshr direction is OWNER-ASSERTED, not verified. "
            "Pull it with the WRDS sprint (ops/briefs/P1-WRDS-SPRINT.md).")
    ch = _msf_actions()

    def rel_break(op):
        """Median |relative jump| in the adjusted share series across the action."""
        if op == "multiply":
            pre = ch["prev_shrout"] * ch["prev_cfacshr"]
            post = ch["shrout"] * ch["cfacshr"]
        else:
            pre = ch["prev_shrout"] / ch["prev_cfacshr"]
            post = ch["shrout"] / ch["cfacshr"]
        return float(((post - pre).abs() / pre).median())

    mult, div = rel_break("multiply"), rel_break("divide")
    raw = float(((ch["shrout"] - ch["prev_shrout"]).abs()
                 / ch["prev_shrout"]).median())

    assert mult < div, (
        f"CFACSHR direction is INVERTED. Across {len(ch)} real CRSP corporate "
        f"actions the median adjusted-share discontinuity is {mult:.4f} under "
        f"multiply (the frozen convention) but {div:.4f} under divide — the "
        "wrong one is smoother, which means the frozen one is wrong. Flip "
        "ADJUSTMENT_CONVENTIONS['crsp_cfacshr'] and re-run Gate 0 from scratch.")
    assert mult < 0.05, (
        f"multiply is the better of the two but still leaves a median "
        f"{mult:.4f} break across {len(ch)} actions. Adjusted shares should be "
        "nearly continuous; this says neither direction reconciles and the "
        "field or its units are not what the pull assumes.")
    assert raw > 5 * mult, (
        f"the RAW series barely moves across these 'corporate actions' (median "
        f"{raw:.4f} vs adjusted {mult:.4f}), so this sample cannot discriminate "
        "the direction — the events found are not real splits.")


def test_adjustment_cancels_a_real_action_on_a_real_holding():
    """End-to-end on one real event: a holder who did not trade reads as flat.

    Unlike the population test above this uses ONE action, but it takes both
    sides from CRSP: the position is scaled by CRSP's own observed SHROUT change,
    not by a ratio derived from the factor. A fund holding a constant FRACTION of
    a company across a split holds prev_shrout -> shrout in raw terms.
    """
    if not CRSP_MSF.exists():
        pytest.skip("BLOCKED: needs landed CRSP msf (see the sprint brief).")
    ch = _msf_actions()
    # the cleanest event: factor moved most, raw shares tracked it most exactly
    ch = ch.assign(implied=(ch["prev_cfacshr"] / ch["cfacshr"]),
                   actual=(ch["shrout"] / ch["prev_shrout"]))
    ch = ch[(ch["implied"] - 1).abs() > 0.10]          # a real split, not a stub
    if ch.empty:
        pytest.skip("BLOCKED: no factor change above 10% in the landed msf.")
    row = ch.reindex((ch["actual"] / ch["implied"] - 1).abs()
                     .sort_values().index).iloc[0]

    pre = cc.adjust_shares({"X": float(row["prev_shrout"])},
                           {"X": float(row["prev_cfacshr"])},
                           convention="crsp_cfacshr")
    post = cc.adjust_shares({"X": float(row["shrout"])},
                            {"X": float(row["cfacshr"])},
                            convention="crsp_cfacshr")
    r = cc.share_continuity(pre, post)
    assert r["share_turnover"] < 0.01, (
        f"permno {row['permno']} on {row['date']}: factor "
        f"{row['prev_cfacshr']} -> {row['cfacshr']}, raw shares "
        f"{row['prev_shrout']} -> {row['shrout']}; adjusted turnover "
        f"{r['share_turnover']:.4f} instead of ~0.")


# --------------------------------------------------------------------------- #
# v2.1d item 1 — join the factor on the HOLDINGS AS-OF DATE, not `filed`        #
# --------------------------------------------------------------------------- #
def test_factor_joins_on_the_asof_date_not_the_filing_date():
    """A split between repPdDate and the filing date is the failure mode.

    Holdings are as of 2023-03-31; the N-PORT is filed 2023-05-30; a 2:1 split
    happens in April. Joining on `filed` picks the post-split factor and so
    INTRODUCES the very discontinuity the adjustment exists to remove.
    """
    panel = {"AAA": {"2023-03-31": 2.0, "2023-04-28": 1.0, "2023-05-30": 1.0}}
    asof = cc.factors_asof(panel, ["AAA"], "2023-03-31", freq="daily")
    filed = cc.factors_asof(panel, ["AAA"], "2023-05-30", freq="daily")
    assert asof["AAA"] == 2.0 and filed["AAA"] == 1.0

    raw_pre, raw_post = {"AAA": 100.0}, {"AAA": 100.0}   # manager traded nothing
    right = cc.share_continuity(
        cc.adjust_shares(raw_pre, asof, convention="crsp_cfacshr"),
        cc.adjust_shares(raw_post, asof, convention="crsp_cfacshr"))
    wrong = cc.share_continuity(
        cc.adjust_shares(raw_pre, filed, convention="crsp_cfacshr"),
        cc.adjust_shares(raw_post, asof, convention="crsp_cfacshr"))
    assert right["share_turnover"] == 0.0
    assert wrong["share_turnover"] > 0.0, (
        "joining on the filing date must be detectably wrong; if this passes "
        "silently the join key does not matter and the test is vacuous")


def test_factor_join_never_looks_ahead_and_never_defaults():
    panel = {"AAA": {"2023-04-28": 1.0}}
    with pytest.raises(cc.FactorJoinError):                # only a LATER obs
        cc.factors_asof(panel, ["AAA"], "2023-03-31", freq="daily")
    with pytest.raises(cc.FactorJoinError):                # security absent
        cc.factors_asof(panel, ["ZZZ"], "2023-04-28", freq="daily")
    with pytest.raises(cc.FactorJoinError):                # stale by months
        cc.factors_asof(panel, ["AAA"], "2023-09-29", freq="daily")
    with pytest.raises(cc.FactorJoinError):                # unnamed frequency
        cc.factors_asof(panel, ["AAA"], "2023-04-28", freq="whatever")
    # a month-end on a weekend still joins to the last trading day
    got = cc.factors_asof({"AAA": {"2023-04-28": 1.0}}, ["AAA"],
                          "2023-04-30", freq="daily")
    assert got["AAA"] == 1.0


def test_monthly_factor_sufficiency_is_measured_not_assumed():
    """Whether MONTHLY cfacshr is precise enough is a question about the dates."""
    # non-month-end as-of dates: monthly has no observation for them at all
    r = cc.monthly_factor_sufficiency(["2023-03-31", "2023-04-14"])
    assert r["verdict"] == "insufficient" and "2023-04-14" in r["non_month_end"]

    # all month-ends but no daily panel -> UNKNOWN, never "sufficient"
    r = cc.monthly_factor_sufficiency(["2023-03-31", "2023-06-30"])
    assert r["verdict"] == "unknown" and "crsp.dsf" in r["why"]

    # month-ends with a daily panel that is flat inside the month -> sufficient
    daily = {"AAA": {"2023-03-15": 1.0, "2023-03-31": 1.0}}
    assert cc.monthly_factor_sufficiency(["2023-03-31"], daily)["verdict"] == \
        "sufficient"

    # a split INSIDE the month: the month-end value is not the as-of value
    daily = {"AAA": {"2023-03-15": 2.0, "2023-03-31": 1.0}}
    r = cc.monthly_factor_sufficiency(["2023-03-15"], daily)
    assert r["verdict"] == "insufficient" and r["intramonth_changes"]
