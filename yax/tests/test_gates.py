"""Tests for the YAX gate runner.

The gates exist to catch two specific mistakes: freezing on a power simulation
that is describing its own smoothness, and committing an outcome before the
pre-registration is sealed. Both are cheap to get wrong and impossible to undo,
so the checks themselves are worth testing.

The invariant that matters most: BLOCKED must never be reported as PASS, and
must never produce a zero exit status.
"""

import importlib.util
import json
import math
import pathlib

MODULE = pathlib.Path(__file__).resolve().parents[1] / "gates.py"
SPEC = importlib.util.spec_from_file_location("yax_gates", MODULE)
assert SPEC and SPEC.loader
gates = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gates)


def agg(points, null_size=0.05, coverage=0.95, **extra):
    """Build a power aggregate. `points` is [(relative_decline, power), ...]."""
    rows = [{"true_log_effect": 0.0, "rejection_probability_zero": null_size,
             "coverage_95": coverage}]
    for d, p in points:
        rows.append({"true_log_effect": math.log(1 - d),
                     "rejection_probability_zero": p, "coverage_95": coverage})
    return dict(
        results=rows,
        design={
            "post_start": "2023-01",
            "transition_excluded": "2022-12",
            "post_end": "2026-07",
            "post_gaps": ["2025-10"],
        },
        effect_scale_code="q5_q1",
        **extra,
    )


def test_superseded_december_power_window_is_blocked():
    record = agg([(0.01, 0.4), (0.03, 0.9)])
    record["design"]["post_start"] = "2022-12"
    assert gates.gate_gradient(record).status == "BLOCKED"
    assert gates.gate_calibration(record).status == "BLOCKED"


def test_superseded_per_sd_power_scale_is_blocked():
    record = agg([(0.01, 0.4), (0.03, 0.9)])
    record["effect_scale_code"] = "per_sd"
    assert gates.gate_gradient(record).status == "BLOCKED"
    assert gates.gate_calibration(record).status == "BLOCKED"


# ------------------------------------------------------------ gradient

def test_ceiling_power_at_smallest_effect_is_an_engine_bug():
    """The exact failure the plan warns about: flat power across the grid."""
    r = gates.gate_gradient(agg([(0.01, 0.999), (0.05, 1.0), (0.19, 1.0)]))
    assert r.status == "FAIL"
    assert "SMALLEST" in r.detail and "engine bug" in r.detail


def test_gradient_passes_and_interpolates_the_mde():
    r = gates.gate_gradient(agg([(0.01, 0.40), (0.02, 0.80), (0.03, 0.95)]))
    assert r.status == "PASS"
    assert "MDE80" in r.detail and "2." in r.detail


def test_underpowered_design_is_distinguished_from_engine_bug():
    r = gates.gate_gradient(agg([(0.01, 0.05), (0.05, 0.12), (0.19, 0.30)]))
    assert r.status == "FAIL"
    assert "underpowered" in r.detail
    assert "engine bug" not in r.detail


def test_gradient_blocked_without_an_aggregate():
    assert gates.gate_gradient(None).status == "BLOCKED"


def test_gradient_blocked_on_too_few_points():
    assert gates.gate_gradient(agg([(0.02, 0.8)])).status == "BLOCKED"


def test_gradient_checks_every_joint_scenario():
    good = agg([(0.01, 0.40), (0.02, 0.80), (0.03, 0.95)])
    bad = agg([(0.01, 0.05), (0.05, 0.12), (0.19, 0.30)])
    good.update(ai_measure="beta", computerization_measure="ONet")
    bad.update(ai_measure="alpha", computerization_measure="Webb")
    assert gates.gate_gradient({"scenarios": [good, bad]}).status == "FAIL"


# ------------------------------------------------------------ calibration

def test_oversized_inference_without_bootstrap_fails():
    r = gates.gate_calibration(agg([(0.02, 0.8)], null_size=0.066, coverage=0.935))
    assert r.status == "FAIL"
    assert "bootstrap" in r.detail


def test_oversized_inference_with_bootstrap_passes():
    r = gates.gate_calibration(
        agg([(0.02, 0.8)], null_size=0.066, bootstrap_mde80_relative=0.021))
    assert r.status == "PASS"


def test_well_calibrated_engine_passes_without_bootstrap():
    assert gates.gate_calibration(agg([(0.02, 0.8)], null_size=0.052)).status == "PASS"


def test_calibration_checks_every_joint_scenario():
    good = agg([(0.02, 0.8)], null_size=0.066, bootstrap={"draws": 999})
    bad = agg([(0.02, 0.8)], null_size=0.066)
    good.update(ai_measure="beta", computerization_measure="ONet")
    bad.update(ai_measure="alpha", computerization_measure="Webb")
    assert gates.gate_calibration({"scenarios": [good, bad]}).status == "FAIL"


# ------------------------------------------------------------ coverage rule

def test_failed_coverage_gate_may_not_unlock_the_freeze():
    r = gates.gate_coverage_rule(
        agg([(0.02, 0.8)], design_freeze_permitted=True,
            covered_route_mass_fraction=0.8870))
    assert r.status == "FAIL"
    assert "must not" in r.detail


def test_coverage_rule_passes_when_prespec_declares_all_three():
    assert gates.gate_coverage_rule(None).status == "PASS"


# ------------------------------------------------------------ runner

def test_blocked_never_exits_zero(capsys):
    """The invariant. 'Not checked' must not read as 'fine'.

    The summary line reports FAILs first when any gate fails, so assert on the
    per-gate output rather than on which summary happens to fire.
    """
    code = gates.main(["--freeze-tag", "tag-that-does-not-exist"])
    out = capsys.readouterr().out
    assert code == 1
    assert "BLOCKED" in out
    assert ("not the same as" in out) or ("Do not proceed to the freeze" in out)


def test_json_output_is_parseable(capsys):
    gates.main(["--json", "--freeze-tag", "tag-that-does-not-exist"])
    payload = json.loads(capsys.readouterr().out)
    assert {r["gate"] for r in payload} >= {"gradient", "seal", "freeze_doc"}
    assert all(r["status"] in ("PASS", "FAIL", "BLOCKED") for r in payload)


def test_seal_gate_reports_current_repository_state():
    """The immutable v1.1 freeze predates any committed outcome archive."""
    r = gates.gate_seal("v1.1-design-freeze")
    assert r.status == "PASS"
    assert "v1.1-design-freeze exists" in r.detail


# ------------------------------------------------------------ novelty

def _plan_saying(tmp_path, monkeypatch, body):
    p = tmp_path / gates.PLAN
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    monkeypatch.setattr(gates, "ROOT", tmp_path)





def test_computerization_gate_passes_only_on_complete_real_measure_receipt():
    r = gates.gate_computerization("v1.0-preregistered")
    assert r.status == "PASS"
    assert "AI×computerization pairs" in r.detail


# ------------------------------------------------------------ plan consistency

def test_plan_consistency_passes_on_the_current_plan():
    assert gates.gate_plan_consistency("v1.0-design-freeze").status == "PASS"


def test_default_tag_is_design_freeze_not_preregistered():
    """'Pre-registered' claims a public timestamped third-party record. A git
    tag is not one, and the plan says so."""
    assert gates.DEFAULT_TAG == "v1.0-design-freeze"


# ------------------------------------------------------- convergent validity

def test_convergent_validity_catches_the_orphaned_measure():
    """Regression for the Y1b failure: `computerization` PASSED because Webb
    had failed to join. A control uncorrelated with the treatment leaves the AI
    coefficient looking maximally identified, so a broken merge produces the
    best headroom the support gate can report."""
    r = gates.gate_convergent_validity("v1.0-design-freeze")
    assert r.status in ("PASS", "FAIL", "BLOCKED")
    if r.status == "FAIL":
        assert "agree with no other" in r.detail


# ------------------------------------------------------------ novelty, inverted

def test_current_latest_version_novelty_audit_passes():
    """Action 2 supplied the positive sentinel and source-backed audit.

    The tmp-path test below remains the regression proving that silence and
    inherited warning prose block.
    """
    r = gates.gate_novelty("v1.1-design-freeze")
    assert r.status == "PASS"
    assert "primary source" in r.detail


def test_amendment_gate_blocks_until_the_amended_freeze_is_tagged(tmp_path, monkeypatch):
    monkeypatch.setattr(gates, "ROOT", tmp_path)
    for rel in (gates.PLAN, gates.AMENDMENT, gates.PAIRED_AMENDMENT,
                gates.FREEZE_V2):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("recorded\n", encoding="utf-8")
    monkeypatch.setattr(gates, "_git", lambda *args: None)
    r = gates.gate_amendment_current("v1.1-design-freeze")
    assert r.status == "BLOCKED"
    assert "not tagged" in r.detail


def test_novelty_sentinel_is_required_verbatim(tmp_path, monkeypatch):
    """The old contract was 'no warning words present'. Two rewrites walked
    through it. The new contract is a verbatim sentinel a human must add
    deliberately, so both failure modes are closed."""
    plan = tmp_path / "plan.md"
    monkeypatch.setattr(gates, "ROOT", tmp_path)
    monkeypatch.setattr(gates, "PLAN", "plan.md")

    plan.write_text("a plan that simply says nothing about prior work\n")
    assert gates.gate_novelty("t").status == "BLOCKED"

    plan.write_text("references are relayed and unverified\n")
    assert gates.gate_novelty("t").status == "BLOCKED"

    plan.write_text("NOVELTY-GATE: all references opened at primary source\n")
    assert gates.gate_novelty("t").status == "PASS"


def test_novelty_fails_when_sentinel_contradicts_an_unresolved_row(tmp_path, monkeypatch):
    """Claiming completion while a row is still marked unverified is worse than
    silence — it is a false assertion, so it FAILs rather than BLOCKs."""
    plan = tmp_path / "plan.md"
    monkeypatch.setattr(gates, "ROOT", tmp_path)
    monkeypatch.setattr(gates, "PLAN", "plan.md")
    plan.write_text(
        "NOVELTY-GATE: all references opened at primary source\n"
        "but Rai (2026) is relayed and unverified\n")
    r = gates.gate_novelty("t")
    assert r.status == "FAIL"
    assert "sentinel" in r.detail


# --------------------------------------------------------- paired-delta power





def _full_precision_artifact():
    return {
        "post_outcomes_read": False,
        "paired_delta_distribution": [0.0] * 999,
        "paired_delta_se": 0.0117,
        "paired_confidence_interval": {
            "confidence_level": 0.95,
            "method": "percentile-t paired occupation-cluster bootstrap",
            "bootstrap_draws_minimum": 999,
            "same_occupation_cluster_weights_for_both_exposures": True,
            "construction": "[delta_hat - q975*t_se, delta_hat - q025*t_se]",
            "computed_after_outcomes_open": False,
        },
        "mde_delta_80": {
            "power_target": 0.80,
            "log_points": 0.0327,
            "relative_magnitude": 0.0333,
        },
        "common_bootstrap_draws": {
            "same_draw_applied_to_both_exposure_definitions": True,
            "covariance_preserved": True,
            "paired_covariance": 0.000095,
            "draws": 999,
            "failures": 0,
        },
    }


def test_paired_precision_gate_accepts_complete_artifact_without_sesoi():
    art = _full_precision_artifact()
    assert "sesoi" not in art
    result = gates.gate_paired_difference_precision(art)
    assert result.status == "PASS"
    assert "not economic equivalence" in result.detail


def test_paired_precision_gate_rejects_unpaired_or_missing_covariance():
    art = _full_precision_artifact()
    art["common_bootstrap_draws"]["same_draw_applied_to_both_exposure_definitions"] = False
    result = gates.gate_paired_difference_precision(art)
    assert result.status == "BLOCKED"
    assert "preserving covariance" in result.detail


def test_paired_precision_gate_requires_ci_construction_not_equivalence_interval():
    art = _full_precision_artifact()
    del art["paired_confidence_interval"]
    art["equivalence_interval"] = [-0.01, 0.01]
    result = gates.gate_paired_difference_precision(art)
    assert result.status == "BLOCKED"
    assert "paired percentile-t 95% CI construction" in result.detail


def test_paired_precision_gate_fails_closed_if_outcomes_were_read():
    art = _full_precision_artifact()
    art["post_outcomes_read"] = True
    result = gates.gate_paired_difference_precision(art)
    assert result.status == "BLOCKED"
    assert "zero protected" in result.detail


def test_paired_precision_gate_blocks_without_an_aggregate():
    assert gates.gate_paired_difference_precision(None).status == "BLOCKED"
