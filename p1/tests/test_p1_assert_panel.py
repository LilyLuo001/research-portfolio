"""p1/pipeline/assert_panel.py — each assertion must FAIL on the thing it names.

An assertion that has never been seen to fail is not a guard, it is decoration.
Every check below gets a panel built to violate it, and a clean panel to prove it
does not cry wolf. The panel itself does not exist yet — that is exactly why
these are written now.
"""
import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]

pytest.importorskip("pandas")
import pandas as pd  # noqa: E402

# Loaded by explicit path under a unique module name. refraction/pipeline/ has a
# file of the same basename, and a bare `import assert_panel` off sys.path would
# make which one you get depend on collection order.
_spec = importlib.util.spec_from_file_location(
    "p1_assert_panel", ROOT / "p1" / "pipeline" / "assert_panel.py")
ap = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ap)

EFF = "2021-06-11"          # the DFA anchor wave


def clean_panel():
    """Two stocks in one wave, four quarters, treatment flagged correctly."""
    rows = []
    for permno in (10001, 10002):
        for q in (20211, 20212, 20213, 20214):
            rows.append({
                "permno": permno, "yyyyq": q, "wave_id": "W002",
                "effective_date": EFF, "conv_exp": 0.006,
                # 2021Q2 ends 06-30, after the 06-11 conversion -> post
                "treated_post": int(ap.quarter_end(q) > pd.Timestamp(EFF)),
                "russell_change": 0,
            })
    return pd.DataFrame(rows)


def frozen_convexp():
    return pd.DataFrame([{"permno": 10001, "wave_id": "W002", "conv_exp": 0.006},
                         {"permno": 10002, "wave_id": "W002", "conv_exp": 0.006}])


def waves():
    return pd.DataFrame([{"wave_id": "W002", "effective_date": EFF, "is_anchor": 1}])


def _check(rep, name):
    return next(c for c in rep["checks"] if c["assert"] == name)


# --------------------------------------------------------------------------- #
def test_clean_panel_passes_everything():
    rep = ap.run_all(clean_panel(), frozen_convexp(), waves())
    assert rep["overall_pass"], [c for c in rep["checks"] if not c["passed"]]


def test_quarter_end_is_right():
    assert ap.quarter_end(20212) == pd.Timestamp("2021-06-30")
    assert ap.quarter_end(20214) == pd.Timestamp("2021-12-31")
    assert ap.quarter_end(20261) == pd.Timestamp("2026-03-31")
    with pytest.raises(ValueError):
        ap.quarter_end(20215)


# --------------------------------------------------------------------------- #
def test_a1_catches_duplicate_keys():
    p = pd.concat([clean_panel(), clean_panel().head(1)])
    assert not _check(ap.run_all(p), "A1_primary_key")["passed"]


def test_a2_catches_premature_post_the_signature_lookahead_bug():
    """A quarter ending BEFORE the conversion marked post — the bug that would
    contaminate every downstream coefficient while looking fine in a plot."""
    p = clean_panel()
    p.loc[p["yyyyq"] == 20211, "treated_post"] = 1     # Q1 ends 03-31 < 06-11
    c = _check(ap.run_all(p), "A2_no_lookahead")
    assert not c["passed"]
    assert c["n_premature_post"] == 2


def test_a2_fails_closed_when_the_columns_are_absent():
    """Missing the means to check must never read as 'passed'."""
    p = clean_panel().drop(columns=["treated_post"])
    assert not _check(ap.run_all(p), "A2_no_lookahead")["passed"]


def test_a3_catches_treatment_that_moves_over_quarters():
    p = clean_panel()
    p.loc[(p["permno"] == 10001) & (p["yyyyq"] == 20214), "conv_exp"] = 0.009
    c = _check(ap.run_all(p), "A3_treatment_constant")
    assert not c["passed"] and c["n_varying"] == 1


def test_a4_catches_a_panel_that_recomputed_treatment():
    p = clean_panel()
    p["conv_exp"] = 0.0075                      # differs from the frozen 0.006
    c = _check(ap.run_all(p, frozen_convexp()), "A4_treatment_frozen")
    assert not c["passed"] and c["n_drifted"] == 2


def test_a5_catches_an_invented_wave():
    p = clean_panel()
    p.loc[0, "wave_id"] = "W999"
    assert not _check(ap.run_all(p, frozen_convexp(), waves()), "A5_waves_exist")["passed"]


def test_a6_catches_an_already_treated_stock_used_for_a_later_wave():
    """Stock 10001 is treated in 2021-06; attributing its later quarters to a
    2023 wave makes it a contaminated control."""
    later = clean_panel().head(2).copy()
    later["wave_id"] = "W019"
    later["effective_date"] = "2023-03-10"
    later["yyyyq"] = [20231, 20232]
    later["treated_post"] = [0, 1]
    p = pd.concat([clean_panel(), later], ignore_index=True)
    c = _check(ap.run_all(p), "A6_clean_controls")
    assert not c["passed"] and c["n_contaminated"] == 2


def test_a7_catches_a_stock_that_never_reaches_the_panel():
    cx = pd.concat([frozen_convexp(),
                    pd.DataFrame([{"permno": 10003, "wave_id": "W002",
                                   "conv_exp": 0.007}])])
    c = _check(ap.run_all(clean_panel(), cx), "A7_no_silent_drops")
    assert not c["passed"] and c["n_missing"] == 1


def test_a8_reads_ranges_from_the_contract_not_from_hardcoded_numbers():
    p = clean_panel()
    p.loc[0, "conv_exp"] = -0.5           # contract says min 0
    p.loc[1, "russell_change"] = 7        # contract says max 1
    c = _check(ap.run_all(p), "A8_declared_ranges")
    assert not c["passed"]
    assert any("conv_exp" in v for v in c["violations"])
    assert any("russell_change" in v for v in c["violations"])


def test_a8_catches_nulls_in_a_required_column():
    p = clean_panel()
    p.loc[0, "permno"] = None
    assert not _check(ap.run_all(p), "A8_declared_ranges")["passed"]


def test_a9_profiles_missingness_without_failing_the_run():
    p = clean_panel()
    p["some_future_spine_var"] = None
    rep = ap.run_all(p)
    c = _check(rep, "A9_missingness")
    assert c["passed"] and c["severity"] == ap.REPORT
    assert c["profile"]["some_future_spine_var"] == 1.0
    assert rep["overall_pass"], "a REPORT-level note must not gate the panel"


# --------------------------------------------------------------------------- #
def test_optional_inputs_downgrade_to_report_rather_than_false_pass():
    """Without the frozen files, the checks that need them must say so — and
    must not silently count as hard passes."""
    rep = ap.run_all(clean_panel())
    for name in ("A4_treatment_frozen", "A5_waves_exist", "A7_no_silent_drops"):
        assert _check(rep, name)["severity"] == ap.REPORT


def test_contract_and_guard_agree_on_the_primary_key():
    """If the contract's key changes, this guard must change with it."""
    import yaml
    spec = yaml.safe_load((ROOT / "ops" / "contracts" / "outcomes_panel.yaml").read_text())
    assert spec["primary_key"] == ["permno", "yyyyq"]
