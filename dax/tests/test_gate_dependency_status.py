"""The derived Gate-1 dependency view must not overstate progress.

The 2026-08-20 person-level power receipt names two blockers; the 2026-08-24
freeze satisfied one of them. This module exists to make sure the derivation
says exactly that and never more -- the failure mode worth guarding is a
status record that reports a gate as closer than it is, because that is the
one a seat would act on.
"""
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "gate_dependency_status", ROOT / "memo" / "power_calcs" / "gate_dependency_status.py")
G = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(G)

FROZEN = json.loads((ROOT / "memo" / "power_calcs" / "power_standard.json").read_text())


def test_the_live_standard_resolves_the_benchmark_dependency():
    assert G.benchmark_is_resolved(FROZEN)["satisfied"] is True


def test_an_unfrozen_standard_resolves_nothing():
    """The exact state the receipts were written in."""
    s = json.loads(json.dumps(FROZEN))
    s["status"] = "PLACEHOLDER_REQUIRES_REAL_CPS"
    assert G.benchmark_is_resolved(s)["satisfied"] is False


def test_frozen_is_not_enough_without_a_verified_locator():
    """A standard frozen against an unverified benchmark is what D3 forbids.

    Freezing and verifying are independent, and neither implies the other. If
    this ever passed, the programme could freeze a bar derived from a number
    nobody could trace to a source -- the exact failure meta-rule 1 exists for.
    """
    s = json.loads(json.dumps(FROZEN))
    s["benchmark"]["locator_status"] = "UNRESOLVED"
    assert G.benchmark_is_resolved(s)["satisfied"] is False


def test_frozen_and_verified_still_needs_both_ceilings():
    s = json.loads(json.dumps(FROZEN))
    s["standard"]["hours_mde_ceiling"] = None
    assert G.benchmark_is_resolved(s)["satisfied"] is False


def test_the_dose_dependency_is_never_inferred():
    """Only the receipt's own flag may satisfy it -- never a bare panel name."""
    assert G.dose_panel_present({"w5_dose_panel_name": "w5_dose_panel.parquet"})["satisfied"] is False
    assert G.dose_panel_present({"w5_dose_panel_present": True})["satisfied"] is True


def test_the_dose_dependency_is_still_pending_in_this_repo():
    rec = G.build()
    assert G.DOSE_DEPENDENCY in rec["dependencies_still_pending"]
    assert G.BENCHMARK_DEPENDENCY not in rec["dependencies_still_pending"]


def test_the_record_claims_no_gate_advanced():
    """The whole hazard of a 'progress' artifact is that it implies progress."""
    rec = G.build()
    assert rec["gates_advanced"] == []
    assert "still fail" in rec["gate_1_effect"]


def test_a_reworded_dependency_stops_rather_than_guesses(monkeypatch, tmp_path):
    """Meta-rule 4: don't know -> stop.

    The mapping from receipt text to dependency is literal. If the receipt is
    reworded, resolving it by resemblance would be a guess about which blocker
    was satisfied -- so the script must refuse instead.
    """
    receipt = json.loads(G.PERSON_POWER.read_text())
    receipt["pending_dependencies"] = ["some reworded benchmark thing",
                                       G.DOSE_DEPENDENCY]
    p = tmp_path / "person.json"
    p.write_text(json.dumps(receipt))
    monkeypatch.setattr(G, "PERSON_POWER", p)
    with pytest.raises(G.StatusError) as e:
        G.build()
    assert "re-checked by hand" in str(e.value)


def test_check_mode_exits_nonzero_while_anything_is_pending(tmp_path):
    assert G.main(["--output", str(tmp_path / "s.json"), "--check"]) == 1
    assert G.main(["--output", str(tmp_path / "s2.json")]) == 0


def test_the_w1_validator_still_reports_both_gates_blocked():
    """The load-bearing assertion: this work must not have moved Gate 1.

    If deriving a status record ever changes what the readiness validator says,
    something has leaked from bookkeeping into the gate itself.
    """
    spec = importlib.util.spec_from_file_location(
        "validate_w1_readiness", ROOT / "memo" / "validate_w1_readiness.py")
    v = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v)
    blockers = v.audit()["blockers"]
    assert any("identification gate" in b for b in blockers)
    assert any("person-level empirical power gate" in b for b in blockers)
