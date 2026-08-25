"""Offline tests for P1-B1: the sample-scenario table and the asset_class merge.

No network, no WRDS. The merge tests use a temporary copy of events_merged.csv so
the real file is never touched.
"""
import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
RECON = ROOT / "p1" / "t1_reconcile"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"p1_{name}", RECON / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


scen = _load("sample_scenarios")
appl = _load("apply_asset_class")


# ---------------------------------------------------------------- scenarios

def test_T01_scenario_table_regenerates():
    ev, mm, ce, cls = scen.load()
    pure, touch = scen.wave_sets(cls)
    tab = scen.scenarios(ce, pure, touch)
    assert len(tab) == 12, "2 dose tiers x 6 scenarios"
    assert set(tab.columns) >= {"dose_tier", "scenario", "stocks", "waves", "powered"}


def test_T02_committed_csv_matches_a_fresh_run():
    """The committed table must not drift from what the code produces."""
    ev, mm, ce, cls = scen.load()
    pure, touch = scen.wave_sets(cls)
    fresh = scen.scenarios(ce, pure, touch)
    have = pd.read_csv(RECON / "sample_scenarios.csv")
    pd.testing.assert_frame_equal(
        fresh.reset_index(drop=True), have.reset_index(drop=True), check_dtype=False)


def test_T03_excluding_dfa_is_a_large_drop():
    """Pins the finding: W002 dominates treated mass at the 0.5% line."""
    ev, mm, ce, cls = scen.load()
    pure, touch = scen.wave_sets(cls)
    t = scen.scenarios(ce, pure, touch)
    t = t[t.dose_tier == ">=0.5%"].set_index("scenario")["stocks"]
    assert t["ALL (as built)"] > 300
    assert t["excl DFA (W002)"] < 60
    assert t["excl DFA (W002)"] / t["ALL (as built)"] < 0.15


def test_T04_cuts_compound_monotonically():
    ev, mm, ce, cls = scen.load()
    pure, touch = scen.wave_sets(cls)
    t = scen.scenarios(ce, pure, touch)
    for tier in t.dose_tier.unique():
        s = t[t.dose_tier == tier].set_index("scenario")["stocks"]
        assert s["excl DFA + Option A"] <= s["excl DFA (W002)"]
        assert s["excl DFA + A-strict"] <= s["excl DFA + Option A"]
        assert s["A-strict — drop any intl-touching wave"] <= s["Option A — drop pure-intl waves"]


def test_T05_classification_backlog_has_no_treated_mass():
    """The negative result that makes the DFA finding robust to the backlog."""
    ev, mm, ce, cls = scen.load()
    gap = scen.classification_gap(ev, mm, ce)
    assert gap["unclassified_events"] > 0, "if this hits 0 the backlog is done"
    assert all(v == 0 for v in gap["treated_cells_at_stake"].values())


def test_T06_pure_intl_is_a_subset_of_touching_intl():
    ev, mm, ce, cls = scen.load()
    pure, touch = scen.wave_sets(cls)
    assert pure <= touch


# ------------------------------------------------------------- apply merge

def _events_fixture(tmp_path, monkeypatch):
    df = pd.DataFrame({
        "fund_name": ["Alpha Fund", "Beta Fund", "Gamma Fund"],
        "effective_date": ["2023-01-02", "2023-01-02", "2024-05-06"],
        "source_accession": ["0001-23-1", "0001-23-1", "0002-24-9"],
        "asset_class": [None, "fixed_income", None],
        "other_col": ["keep", "keep", "keep"],
    })
    p = tmp_path / "events_merged.csv"
    df.to_csv(p, index=False)
    monkeypatch.setattr(appl, "EVENTS", p)
    return p


def _filled(tmp_path, rows):
    p = tmp_path / "filled.csv"
    pd.DataFrame(rows).to_csv(p, index=False)
    return p


def test_T07_fills_only_blank_rows(tmp_path, monkeypatch):
    ev = _events_fixture(tmp_path, monkeypatch)
    f = _filled(tmp_path, [{"fund_name": "Alpha Fund", "effective_date": "2023-01-02",
                            "source_accession": "0001-23-1",
                            "asset_class_FILL": "equity_US",
                            "evidence_quote_FILL": "invests primarily in US equity securities"}])
    assert appl.apply(f) == 0
    out = pd.read_csv(ev)
    assert out.loc[0, "asset_class"] == "equity_US"
    assert out.loc[1, "asset_class"] == "fixed_income"   # untouched
    assert pd.isna(out.loc[2, "asset_class"])            # still blank, legal
    assert list(out.other_col) == ["keep"] * 3


def test_T08_refuses_to_overwrite_an_existing_class(tmp_path, monkeypatch, capsys):
    _events_fixture(tmp_path, monkeypatch)
    f = _filled(tmp_path, [{"fund_name": "Beta Fund", "effective_date": "2023-01-02",
                            "source_accession": "0001-23-1",
                            "asset_class_FILL": "equity_US",
                            "evidence_quote_FILL": "q"}])
    assert appl.apply(f) == 1
    assert "refusing to overwrite" in capsys.readouterr().err


def test_T09_refuses_a_class_with_no_evidence(tmp_path, monkeypatch, capsys):
    """A class without a locator-backed quote is a guess — meta-rule 1."""
    _events_fixture(tmp_path, monkeypatch)
    f = _filled(tmp_path, [{"fund_name": "Alpha Fund", "effective_date": "2023-01-02",
                            "source_accession": "0001-23-1",
                            "asset_class_FILL": "equity_US",
                            "evidence_quote_FILL": ""}])
    assert appl.apply(f) == 1
    assert "no evidence quote" in capsys.readouterr().err


def test_T10_refuses_an_invalid_class(tmp_path, monkeypatch, capsys):
    _events_fixture(tmp_path, monkeypatch)
    f = _filled(tmp_path, [{"fund_name": "Alpha Fund", "effective_date": "2023-01-02",
                            "source_accession": "0001-23-1",
                            "asset_class_FILL": "equities",   # not a frozen value
                            "evidence_quote_FILL": "q"}])
    assert appl.apply(f) == 1
    assert "is not one of" in capsys.readouterr().err


def test_T11_blank_fills_are_skipped_not_errors(tmp_path, monkeypatch):
    ev = _events_fixture(tmp_path, monkeypatch)
    f = _filled(tmp_path, [{"fund_name": "Alpha Fund", "effective_date": "2023-01-02",
                            "source_accession": "0001-23-1",
                            "asset_class_FILL": "", "evidence_quote_FILL": ""}])
    assert appl.apply(f) == 0
    assert pd.isna(pd.read_csv(ev).loc[0, "asset_class"])


def test_T12_unknown_row_is_refused(tmp_path, monkeypatch, capsys):
    _events_fixture(tmp_path, monkeypatch)
    f = _filled(tmp_path, [{"fund_name": "Ghost Fund", "effective_date": "2099-01-01",
                            "source_accession": "9999-99-9",
                            "asset_class_FILL": "equity_US",
                            "evidence_quote_FILL": "q"}])
    assert appl.apply(f) == 1
    assert "no matching row" in capsys.readouterr().err


def test_T13_dry_run_does_not_write(tmp_path, monkeypatch):
    ev = _events_fixture(tmp_path, monkeypatch)
    before = ev.read_text()
    f = _filled(tmp_path, [{"fund_name": "Alpha Fund", "effective_date": "2023-01-02",
                            "source_accession": "0001-23-1",
                            "asset_class_FILL": "equity_US",
                            "evidence_quote_FILL": "q"}])
    assert appl.apply(f, dry_run=True) == 0
    assert ev.read_text() == before


def test_T14_todo_file_carries_a_locator_for_every_row():
    todo = pd.read_csv(RECON / "asset_class_TODO.csv")
    assert len(todo) > 0
    assert todo.source_url.notna().all(), "every row needs a locator (meta-rule 1)"
    assert todo.asset_class_FILL.isna().all(), "TODO must ship unfilled"
