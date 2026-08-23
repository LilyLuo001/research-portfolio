"""The scoring guard: a row may be captured without duration, never scored.

These tests pin the invariant that `validate_row` currently enforces
structurally, and that `assert_scoreable` must enforce behaviourally if the
capture/scoring split in
`dax/memo/AMENDMENT_DRAFT_w4_capture_scoring_split.md` is signed.

They are correct under both worlds, so they do not presuppose the amendment.
"""

import importlib.util
import pathlib

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "capability_panel" / "contract.py"
SPEC = importlib.util.spec_from_file_location("w4_contract_guard", PATH)
assert SPEC and SPEC.loader
CONTRACT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTRACT)


# Every duration status that must never reach a scoring path. "deferred_scoring"
# is not yet in the frozen enum at
# ops/contracts/dax_w4_capability_cost_panel.yaml; it is listed here so the
# guard is already correct on the day that value is admitted.
UNSCOREABLE = ["blocked_missing", "deferred_scoring", "", "VERIFIED", "verified_later"]


def test_verified_duration_is_scoreable():
    CONTRACT.assert_scoreable({"task_duration_status": "verified", "pi": 0.5})


@pytest.mark.parametrize("status", UNSCOREABLE)
def test_unverified_duration_is_refused(status):
    with pytest.raises(CONTRACT.ScoringGuardError):
        CONTRACT.assert_scoreable({"task_duration_status": status, "pi": 0.5})


def test_whitespace_is_normalised_exactly_as_the_validator_does():
    """The guard and `validate_row` must agree about the same row.

    `_text` strips before comparing, so a padded status is `verified` to the
    validator. A guard that refused it would disagree with the contract about
    whether the row is scoreable, which is a worse failure than accepting the
    padding.
    """

    CONTRACT.assert_scoreable({"task_duration_status": " verified ", "pi": 0.5})


def test_missing_duration_key_is_refused():
    with pytest.raises(CONTRACT.ScoringGuardError):
        CONTRACT.assert_scoreable({"pi": 0.5})


def test_guard_is_not_fooled_by_a_populated_duration_value():
    """A value without `verified` status must not buy its way past the guard.

    This is the shape a constant-fill or inferred duration would take, which
    meta-rule 1 and the plan.py blocking rule both prohibit.
    """

    with pytest.raises(CONTRACT.ScoringGuardError):
        CONTRACT.assert_scoreable({
            "task_duration_status": "deferred_scoring",
            "task_duration_value": 15.0,
            "task_duration_unit": "minute",
            "pi": 0.5,
        })


def test_scoreable_pi_returns_pi_only_for_verified_rows():
    assert CONTRACT.scoreable_pi({"task_duration_status": "verified", "pi": 0.5}) == 0.5
    with pytest.raises(CONTRACT.ScoringGuardError):
        CONTRACT.scoreable_pi({"task_duration_status": "blocked_missing", "pi": 0.5})


@pytest.mark.parametrize("pi", [None, "0.5", True, -0.1, 1.1])
def test_scoreable_pi_rejects_a_non_numeric_or_out_of_range_pi(pi):
    with pytest.raises(CONTRACT.ScoringGuardError):
        CONTRACT.scoreable_pi({"task_duration_status": "verified", "pi": pi})


def test_current_structural_invariant_still_holds():
    """Until the amendment is signed, `blocked_missing` also forces null pi.

    This is the guarantee the amendment would trade away. If this test starts
    failing, the contract was relaxed and `assert_scoreable` is the only thing
    left standing between a capture-only row and the DAX index.
    """

    source = (PATH).read_text(encoding="utf-8")
    assert 'if duration_status == "blocked_missing" and failure != "blocked":' in source
    assert '"missing duration must block the row"' in source


def test_an_unguarded_consumer_is_the_residual_gap():
    """Documents what these tests cannot enforce.

    A scoring consumer that reads `row["pi"]` directly bypasses the guard
    entirely. No unit test can prevent code that does not exist yet from
    forgetting to call a function. Closing this needs a CI check once the first
    crossing consumer lands -- the same enforcement-where-the-violation-happens
    pattern already used for the outcomes seal and the NDA grep.
    """

    capture_only = {"task_duration_status": "deferred_scoring", "pi": 0.5}
    assert capture_only["pi"] == 0.5           # an unguarded consumer sees this
    with pytest.raises(CONTRACT.ScoringGuardError):
        CONTRACT.scoreable_pi(capture_only)    # the guarded path does not
