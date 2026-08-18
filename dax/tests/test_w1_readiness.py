import importlib.util
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "memo" / "validate_w1_readiness.py"
SPEC = importlib.util.spec_from_file_location("validate_w1_readiness", MODULE_PATH)
assert SPEC and SPEC.loader
READINESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(READINESS)


def test_w1_draft_is_structurally_coherent():
    report = READINESS.audit()
    assert report["structural_errors"] == []


def test_w1_draft_remains_fail_closed_after_pi_defaults_are_approved():
    report = READINESS.audit()
    assert report["blockers"]
    assert report["open_decisions"] == []
    assert report["pending_event_locators"]
    # Assert the property, not a count: the draft must stay fail-closed while
    # any evidence item is open. Pinning an exact number made this test fail
    # every time the checklist legitimately grew, which is noise, not signal.
    assert report["unchecked_items"] > 0


def test_red_team_item_is_unchecked_after_the_d1_design_change():
    """The 2026-08-06 CONDITIONAL_GO reviewed the superseded discrete design.

    A verdict on a design that no longer exists must never count as evidence
    for the one that replaced it.
    """
    checklist = (ROOT / "memo" / "PI_DECISIONS_OPEN.md").read_text(encoding="utf-8")
    line = next(l for l in checklist.splitlines() if "cross-vendor red-team" in l)
    assert line.strip().startswith("- [ ]"), \
        "the red-team evidence item must be unchecked until this draft is reviewed"


def test_memo_records_that_the_prior_review_does_not_transfer():
    memo = (ROOT / "memo" / "design_memo_v1.md").read_text(encoding="utf-8")
    assert "does **not** transfer" in memo


def test_pdf_matches_the_memo():
    """The rendered PDF must be built from the current memo, not a past one.

    PR #35 merged a PDF one revision behind its source; the PI would have
    reviewed the superseded draft. This is the guard against a repeat.
    """
    import hashlib

    memo = ROOT / "memo" / "design_memo_v1.md"
    stamp = ROOT / "memo" / "design_memo_v1.pdf.source.sha256"
    assert stamp.is_file(), "render_design_memo.py must emit a source stamp"
    recorded = stamp.read_text(encoding="utf-8").split()[0]
    actual = hashlib.sha256(memo.read_bytes()).hexdigest()
    assert recorded == actual, (
        "design_memo_v1.pdf is stale — it was rendered from a different revision "
        "of design_memo_v1.md. Re-run dax/memo/render_design_memo.py before "
        "asking the PI to review the PDF."
    )
