"""Scope the open pricing conflict to the scenarios it can actually reach.

The point of this preflight is a spending decision, so both directions of
error matter. Reporting the $97.28 preservation run as exposed would hold it
behind a defect that cannot touch it, and the five snapshots it preserves are
gone on 2026-10-23. Reporting the $1,922.63 full plan as clean would authorize
a figure built on a rate nobody can reconcile to a source.
"""
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "price_conflict_preflight", ROOT / "capability_panel" / "price_conflict_preflight.py")
P = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(P)


def test_the_preservation_run_is_not_exposed():
    """The five 2026-10-23 snapshots are gpt-4 and o1 vintages, not gpt-5.x."""
    rec = P.build()
    block = rec["scenarios"]["gdpval_220_baseline_only"]
    assert block["conflict_affects_this_figure"] is False
    assert block["exposed_model_ids"] == []
    assert block["usd"] == 97.28


def test_the_full_plan_is_exposed():
    """It reaches gpt-5.4 and gpt-5.5, which are exactly the conflicted families."""
    rec = P.build()
    block = rec["scenarios"]["full_plan_for_contrast"]
    assert block["conflict_affects_this_figure"] is True
    assert "gpt-5.4-2026-03-05" in block["exposed_model_ids"]
    assert "gpt-5.5-2026-04-23" in block["exposed_model_ids"]


def test_exposure_matches_on_family_prefix_not_substring():
    """A substring match would sweep in unrelated ids and inflate exposure."""
    out = P.exposure(["gpt-5.4-2026-03-05", "gpt-4o-2024-05-13",
                      "o1-2024-12-17", "gpt-5.1-2025-11-13"])
    assert out["exposed"] == ["gpt-5.4-2026-03-05"]
    assert "gpt-5.1-2025-11-13" in out["unexposed"]


def test_it_never_claims_to_resolve_the_conflict():
    assert P.build()["resolves_the_conflict"] is False


def test_a_resolved_conflict_stops_reporting_exposure():
    """A permanent false alarm is one people learn to click through."""
    note = P.FEASIBILITY.read_text(encoding="utf-8")
    resolved = note.replace("Open at signature time: **CONFLICT-B**",
                            "Resolved 2026-09-01: **CONFLICT-B**")
    assert P.conflict_is_open(resolved) is False
    assert P.conflict_is_open(note) is True


def test_a_removed_conflict_stops_rather_than_guesses(tmp_path, monkeypatch):
    """Meta-rule 4. If the note no longer names it, its scope is unknown."""
    p = tmp_path / "note.md"
    p.write_text("no pricing defects recorded here")
    monkeypatch.setattr(P, "FEASIBILITY", p)
    with pytest.raises(P.PreflightError):
        P.build()


def test_scenario_mode_exits_by_exposure(tmp_path):
    out = ["--output", str(tmp_path / "r.json")]
    assert P.main(out + ["--scenario", "gdpval_220_baseline_only"]) == 0
    assert P.main(out + ["--scenario", "full_plan_for_contrast"]) == 1
    assert P.main(out + ["--scenario", "no_such_scenario"]) == 2
