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


def test_fresh_red_team_blockers_are_machine_enforced():
    blockers = READINESS.audit()["blockers"]
    assert "power benchmark is not frozen from a verified dated locator" in blockers
    assert "entrant companion is demoted to exploratory" in blockers
    assert "real-dose residualized identification gate has not run" in blockers
    assert "person-level empirical power receipt is missing" in blockers


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


def test_benchmark_is_stated_as_employment_not_payroll():
    """M2: 0.13 is a relative EMPLOYMENT decline; payroll is the data source.

    The execution plan calls it "the 13% payroll estimate", and the memo
    inherited that phrasing. A frozen constant built on the wrong quantity is
    unrecoverable, so the distinction is pinned here.
    """
    memo = (ROOT / "memo" / "design_memo_v1.md").read_text(encoding="utf-8")
    assert "relative decline in EMPLOYMENT" in memo
    assert "docs/DAX_ERE_Proposal_v3.md:12" in memo, "the claim needs its locator"
    assert "Canaries in the Coal Mine" in memo, "the citation must be in the memo"


def test_freeze_refuses_while_the_benchmark_version_is_unresolved():
    """M2b: 0.13 / 0.16 / 0.19 across versions of the same paper.

    A larger figure loosens the pass bar, so choosing one after seeing that the
    margin is tight would be specification search. The freezer must refuse
    rather than rely on anyone remembering.
    """
    import json

    standard = json.loads(
        (ROOT / "memo" / "power_calcs" / "power_standard.json").read_text())
    benchmark = standard["benchmark"]

    source = (ROOT / "memo" / "power_calcs" / "freeze_power_standard.py").read_text()
    assert 'benchmark.get("version_status") == "RESOLVED"' in source, \
        "the freezer must gate on the version being resolved"
    assert 'benchmark.get("locator_status") == "VERIFIED"' in source, \
        "a resolved label cannot substitute for a verified dated locator"

    if benchmark["locator_status"] != "VERIFIED":
        assert benchmark["relative_decline"] is None, \
            "an unsourced value must not remain executable in the standard"

    if benchmark["version_status"] == "RESOLVED":
        # A resolved version must say who chose it and what it supersedes, and
        # must not silently claim a locator it does not have.
        assert benchmark.get("version_decided_by"), \
            "a resolved version must record who decided it"
        assert benchmark.get("locator_status") in {"VERIFIED", "PENDING_EXCERPT"}, \
            "locator_status must be explicit, not absent"
        if benchmark["locator_status"] == "PENDING_EXCERPT":
            assert benchmark.get("locator_caveat"), \
                "an unsourced PI-directed figure must carry its caveat in the file"
