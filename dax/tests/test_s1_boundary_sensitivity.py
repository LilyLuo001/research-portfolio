"""The S1 headline's sensitivity to two choices nobody has signed.

The reason this exists: S1 is single-annotator, and the instinct is to fix
that first. These tests pin why the annotator count is not the binding
uncertainty -- the evaluable boundary moves the identified share by more than
two careful annotators plausibly would, and it moves it definitionally rather
than by any judgment about a task.
"""
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "s1_boundary_sensitivity", ROOT / "mapping" / "s1_boundary_sensitivity.py")
S = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(S)


def test_the_strict_boundary_identifies_nothing():
    """S1 found zero directly-executable-digital tasks. Not few -- zero.

    Under the narrowest defensible reading of the project's own taxonomy the
    identified mass is exactly 0, the multiplier collapses to kappa, and the
    index would carry no information from data at all.
    """
    rec = S.build()
    assert rec["boundaries"]["strict"]["identified_mass_share_B"] == 0.0
    assert rec["directly_executable_digital_mass"] == 0.0
    for kappa, value in rec["boundaries"]["strict"]["kappa_multiplier"].items():
        assert value == pytest.approx(float(kappa)), (
            "at B=0 the multiplier must equal kappa exactly: the result would "
            "be the assumption alone")


def test_the_boundary_moves_the_identified_share_more_than_the_weighting_does():
    """The ranking that decides which uncertainty to spend money on first."""
    rec = S.build()
    assert rec["identified_share_spread"] > rec["headline_spread_across_weightings"]
    # 0.2572 against 0.0617 -- four times as much.
    assert rec["identified_share_spread"] > 4 * rec["headline_spread_across_weightings"]


def test_each_boundary_is_nested_in_the_next():
    """Non-nested boundaries would not be a sensitivity, just three numbers."""
    rec = S.build()
    order = ["strict", "medium", "broad"]
    seen = []
    for key in order:
        classes = rec["boundaries"][key]["classes_counted_evaluable"]
        assert set(seen) <= set(classes), f"{key} does not contain its predecessor"
        seen = classes
    values = [rec["boundaries"][k]["identified_mass_share_B"] for k in order]
    assert values == sorted(values)


def test_the_multiplier_matches_the_missing_mass_formula():
    assert S.kappa_multiplier(0.25, 0.0) == pytest.approx(0.25)
    assert S.kappa_multiplier(0.25, 1.0) == pytest.approx(1.0)
    assert S.kappa_multiplier(0.25, 0.5) == pytest.approx(0.625)


def test_a_changed_taxonomy_stops_rather_than_silently_dropping_a_class():
    """Meta-rule 4. A boundary that quietly skips a missing class would report
    a smaller identified share and look like a finding."""
    result = S.load_result()
    del result["task_mass_weighted_evaluable_class_shares_within_pilot"][
        "executable_with_supplied_files_data"]
    with pytest.raises(S.SensitivityError):
        S.build(result=result)


def test_the_record_carries_the_s1_qualifier():
    """The guard requires it; so does honesty about a single-annotator input."""
    rec = S.build()
    assert "single-annotator" in rec["s1_qualifier"]
    assert "UNRESOLVED" in rec["s1_qualifier"]
    assert "does not substitute" in rec["what_this_is"]


def test_it_does_not_claim_to_be_a_second_annotation():
    rec = S.build()
    assert "not a second annotation" in rec["what_this_is"]


# --- MM-5: the rule must be IN the pre-registered memo, not beside it -------

MEMO = ROOT / "memo" / "design_memo_v1.md"


def memo_text():
    """Whitespace-normalised, because the memo hard-wraps and a sentence
    asserted here may be split across lines at any time."""
    return " ".join(MEMO.read_text(encoding="utf-8").split())


def test_the_missing_mass_rule_is_in_the_preregistered_memo():
    """MM-5. A rule in a decision packet is not a pre-registered rule.

    Before this amendment design_memo_v1.md contained no partial-identification
    treatment at all, while the rule governing most of the task mass lived only
    in the v3 packet. Choosing it after the tag would be a post-hoc
    identification choice over most of the mass.
    """
    memo = memo_text()
    assert "missing-mass rule" in memo
    assert "PI-DECISION 7a" in memo
    assert "kappa" in memo or "κ" in memo


def test_the_memo_forbids_the_upper_bound_as_a_regressor():
    """The specific hazard, stated in the specification rather than a memo."""
    memo = memo_text()
    assert "must not be used as a level or as a regressor" in memo
    assert "decreasing" in memo


def test_the_memo_freezes_the_kappa_grid_and_refuses_a_headline_kappa():
    memo = memo_text()
    assert "{0, 0.25, 0.50, 0.75, 1}" in memo
    assert "No single" in memo and "headline" in memo
    assert "reported per occupation" in memo


def test_the_memo_records_the_evaluable_boundary_as_medium_with_sensitivities():
    """MM-6. Both alternatives must survive as prespecified sensitivities, or
    the choice becomes a selection rather than a decision."""
    memo = memo_text()
    assert "excluded from the identified set" in memo
    assert "prespecified sensitivities" in memo


def test_pi_decision_7a_stays_outside_the_one_to_seventeen_counter():
    """Deliberate, and worth pinning so nobody 'fixes' it into an 18th.

    validate_w1_readiness requires the memo to carry PI decisions 1..17 exactly
    once each, and PI_DECISIONS_OPEN.md to hold exactly one response row for
    each. An 18th decision would fail both. 7a is an amendment in the same
    class as D1, D3 and D4, which are also outside that sequence.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "validate_w1_readiness", ROOT / "memo" / "validate_w1_readiness.py")
    v = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v)
    memo = MEMO.read_text(encoding="utf-8")
    assert v.DECISION_RE.findall(memo) == [str(i) for i in range(1, 18)]
    assert not v.audit()["structural_errors"]
