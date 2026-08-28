import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from refraction.pipeline import assert_panel as ap  # noqa: E402


def _run(panel, betas, weights, basket, convexp, calendar, wave_effective, config, **kw):
    """Dev-mode runner: these fixtures exercise one assert at a time and do not
    supply the A11/A14 inputs, so they run strict=False. Strict mode — what
    production uses — is covered by the tests at the bottom of this file."""
    kw.setdefault("strict", False)
    return ap.run_all(panel, betas, weights, basket, convexp, calendar,
                      wave_effective, config, **kw)


def _full_inputs(panel, betas):
    """The two inputs strict mode requires."""
    return {"expected_pairs": panel[["permno", "announcement_id"]].drop_duplicates(),
            "upstream_for_a14": {"betas": (betas, ["permno", "wave"], ["beta_i"])}}


def test_clean_world_passes(panel, betas, weights, basket, convexp, calendar,
                            wave_effective, config):
    rep = _run(panel, betas, weights, basket, convexp, calendar, wave_effective, config)
    failing = [k for k in ap.HARD if not rep[k]["pass"]]
    assert rep["overall_pass"], f"failing asserts: {failing}: " + str(
        {k: rep[k]["detail"] for k in failing})


def test_a1_catches_duplicate_key(panel, betas, weights, basket, convexp, calendar,
                                  wave_effective, config):
    dup = pd.concat([panel, panel.iloc[[0]]], ignore_index=True)
    rep = _run(dup, betas, weights, basket, convexp, calendar, wave_effective, config)
    assert not rep["A1"]["pass"] and not rep["overall_pass"]


def test_a3_catches_broken_return_identity(panel, betas, weights, basket, convexp,
                                           calendar, wave_effective, config):
    bad = panel.copy()
    bad.loc[3, "r_total"] += 0.5
    rep = _run(bad, betas, weights, basket, convexp, calendar, wave_effective, config)
    assert not rep["A3"]["pass"]


def test_a4_catches_lookahead(panel, betas, weights, basket, convexp, calendar,
                              wave_effective, config):
    bad = betas.copy()
    bad.loc[0, "max_est_date"] = "2023-03-22"  # post-effective announcement leaked in
    rep = _run(panel, bad, weights, basket, convexp, calendar, wave_effective, config)
    assert not rep["A4"]["pass"] and not rep["overall_pass"]


def test_a6_catches_hardcoded_w_shrink(tmp_path, panel, betas, weights, basket,
                                       convexp, calendar, wave_effective, config):
    (tmp_path / "sneaky.py").write_text("w_shrink = 0.4  # magic number\n")
    rep = _run(panel, betas, weights, basket, convexp, calendar, wave_effective,
               config, src_dir=tmp_path)
    assert not rep["A6"]["pass"]


def test_a7_catches_lever_identity_break(panel, betas, weights, basket, convexp,
                                         calendar, wave_effective, config):
    bad = panel.copy()
    bad.loc[5, "L_tilt"] += 0.2
    rep = _run(bad, betas, weights, basket, convexp, calendar, wave_effective, config)
    assert not rep["A7"]["pass"]


def test_a8_catches_weight_sum(panel, betas, weights, basket, convexp, calendar,
                               wave_effective, config):
    bad = weights.copy()
    bad.loc[0, "weight"] = 0.10
    rep = _run(panel, betas, bad, basket, convexp, calendar, wave_effective, config)
    assert not rep["A8"]["pass"]


def test_a9_catches_broken_loo(panel, betas, weights, basket, convexp, calendar,
                               wave_effective, config):
    bad = betas.copy()
    bad.loc[bad["permno"] == 1001, "beta_b_loo"] += 0.05
    rep = _run(panel, bad, weights, basket, convexp, calendar, wave_effective, config)
    assert not rep["A9"]["pass"]


def test_a10_catches_convexp_drift(panel, betas, weights, basket, convexp, calendar,
                                   wave_effective, config):
    bad = panel.copy()
    bad.loc[bad["permno"] == 1001, "ConvExp"] = 0.03  # differs from frozen file
    rep = _run(bad, betas, weights, basket, convexp, calendar, wave_effective, config)
    assert not rep["A10"]["pass"]


def test_a11_catches_silent_drop(panel, betas, weights, basket, convexp, calendar,
                                 wave_effective, config):
    expected = panel[["permno", "announcement_id"]].drop_duplicates()
    dropped = panel.iloc[1:]
    rep = _run(dropped, betas, weights, basket, convexp, calendar, wave_effective,
               config, expected_pairs=expected)
    assert not rep["A11"]["pass"]


def test_a12_catches_wrong_release_time(panel, betas, weights, basket, convexp,
                                        calendar, wave_effective, config):
    bad = panel.copy()
    bad.loc[bad["type"] == "FOMC", "time_ET"] = "08:30"
    rep = _run(bad, betas, weights, basket, convexp, calendar, wave_effective, config)
    assert not rep["A12"]["pass"]


def test_a14_traceback_detects_mutation(panel, betas, weights, basket, convexp,
                                        calendar, wave_effective, config):
    upstream = {"betas": (betas, ["permno", "wave"], ["beta_i"])}
    ok = _run(panel, betas, weights, basket, convexp, calendar, wave_effective,
              config, upstream_for_a14=upstream)
    assert ok["A14"]["pass"]
    bad = panel.copy()
    bad["beta_i"] = bad["beta_i"] + 0.01  # panel drifted from upstream
    rep = _run(bad, betas, weights, basket, convexp, calendar, wave_effective,
               config, upstream_for_a14=upstream)
    assert not rep["A14"]["pass"]


# ---------------------------------------------------------------------------
# strict mode (default): A11 and A14 are hard asserts, so they must FAIL when
# their inputs are absent rather than passing vacuously. Before this was
# enforced, expected_pairs defaulted to the panel itself and A14 returned pass
# on no upstream frames, while main() supplied neither — so a CLI manifest could
# report both as passing when neither had run.
# ---------------------------------------------------------------------------

def test_strict_is_the_default(panel, betas, weights, basket, convexp, calendar,
                               wave_effective, config):
    rep = ap.run_all(panel, betas, weights, basket, convexp, calendar,
                     wave_effective, config)
    assert not rep["A11"]["pass"] and "NOT EXECUTED" in rep["A11"]["detail"]
    assert not rep["A14"]["pass"] and "NOT EXECUTED" in rep["A14"]["detail"]
    assert not rep["overall_pass"], "a battery that did not run must not certify"


def test_strict_passes_when_both_inputs_are_supplied(panel, betas, weights, basket,
                                                     convexp, calendar,
                                                     wave_effective, config):
    rep = ap.run_all(panel, betas, weights, basket, convexp, calendar,
                     wave_effective, config, **_full_inputs(panel, betas))
    failing = [k for k in ap.HARD if not rep[k]["pass"]]
    assert rep["overall_pass"], f"failing: {failing}: " + str(
        {k: rep[k]["detail"] for k in failing})


def test_strict_still_catches_a_silent_drop(panel, betas, weights, basket, convexp,
                                            calendar, wave_effective, config):
    """The check A11 exists for, exercised through the strict path."""
    full = _full_inputs(panel, betas)
    rep = ap.run_all(panel.iloc[1:], betas, weights, basket, convexp, calendar,
                     wave_effective, config, **full)
    assert not rep["A11"]["pass"] and not rep["overall_pass"]


def test_strict_a11_alone_is_not_enough(panel, betas, weights, basket, convexp,
                                        calendar, wave_effective, config):
    """Supplying one input must not excuse the other."""
    rep = ap.run_all(panel, betas, weights, basket, convexp, calendar,
                     wave_effective, config,
                     expected_pairs=panel[["permno", "announcement_id"]].drop_duplicates())
    assert rep["A11"]["pass"]
    assert not rep["A14"]["pass"] and not rep["overall_pass"]


def test_nonstrict_still_allows_the_dev_path(panel, betas, weights, basket, convexp,
                                             calendar, wave_effective, config):
    rep = ap.run_all(panel, betas, weights, basket, convexp, calendar,
                     wave_effective, config, strict=False)
    assert rep["overall_pass"]
    assert "strict=False" in rep["A14"]["detail"]
