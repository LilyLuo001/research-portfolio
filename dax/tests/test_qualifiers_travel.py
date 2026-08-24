"""Numbers that are diagnostics-only must not appear without their qualifier.

Two results in this repository are recomputable, exact, and NOT evidence:

  * the S1 construct-validity pilot -- 13 PASS of 120 -- whose own receipt
    records `formal_s1_gate_result: UNRESOLVED` and an audit limit of
    PRELIMINARY_SINGLE_CODEX_NOT_INDEPENDENT_DOMAIN_EXPERT_VALIDATION. It ran
    with one annotator where its protocol requires independent domain
    reviewers, so it did not meet its own qualification standard.
  * the Mapping A v2 labels, which are single-annotator.

Both are usable as diagnostics and neither can carry a claim. The standing
rule is that the qualifier travels wherever the number is cited -- and until
now that rule lived only in prose, which is to say it lived in whoever
remembered it. A quoted headline is exactly the thing that gets lifted into a
slide, an abstract, or a reviewer reply without the sentence that qualified it
three paragraphs up.

This makes the rule a property CI checks. It is deliberately per-file and
coarse: a file that cites one of these numbers must somewhere say what is
wrong with it. That is weaker than checking proximity, and it is the version
that will not produce false alarms people learn to silence.
"""
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Distinctive renderings of each headline. Bare "120" or "13" would match
# arithmetic everywhere, so every pattern here is specific enough that its
# presence really is a citation of the result.
S1_CITATIONS = (
    "13 PASS", "13 of 120", "PASS of 120",
    "0.10757575", "0.80454545", "0.08787878",
)
# The v2 side gets NO citation scan, and that is a deliberate limit rather
# than an omission. Its headline diagnostics are bare decimals -- direct_rate
# 0.0, direct_or_family_rate 0.4 -- which no pattern can match without firing
# on arithmetic across the whole repository. A first attempt keyed on the
# receipt FILENAME, which flagged three files that merely referenced the path
# and cited no result: precisely the false alarm this check must not produce.
# What is guarded instead is the source: the v2 receipts must keep the status
# fields that say what they are, so the qualifier cannot be dropped upstream
# of any citation. See test_the_v2_receipts_keep_their_qualifying_status.

# Any one of these is enough. They are the words the receipts and decisions
# actually use, so a file that discusses the limitation in its own terms
# passes without having to quote a magic string.
S1_QUALIFIERS = (
    "UNRESOLVED", "unresolved",
    "SINGLE_CODEX", "single-annotator", "single annotator",
    "UNSIGNED", "unsigned",
    "diagnostic", "PRELIMINARY", "preliminary",
    "non-evaluable", "NON_EVALUABLE",
)

# The receipts and the code that writes them ARE the source of the numbers and
# carry the qualifier in their own fields; the tests below are this file's
# subject matter. Excluding them keeps the check on prose and release paths,
# which is where an unqualified number does damage.
EXCLUDED_NAMES = {
    "s1_construct_validity_result_receipt_20260823.json",
    "s1_construct_validity_execution_receipt_20260823.json",
    "s1_construct_validity_spec_20260823.json",
    "s1_draw_receipt_20260823.json",
    "run_s1_construct_validity.py",
    "mapA_v2_recall_audit.py",
    "mapA_v2_recall_audit_receipt.json",
    "test_qualifiers_travel.py",
    "test_s1_construct_validity.py",
    "test_red_team.py",
}


def _candidate_files():
    for path in sorted(ROOT.rglob("*")):
        if path.suffix not in {".md", ".py"}:
            continue
        if "__pycache__" in path.parts or path.name in EXCLUDED_NAMES:
            continue
        yield path


def _cites(text, patterns):
    return [p for p in patterns if p in text]


def _qualified(text, qualifiers):
    return any(q in text for q in qualifiers)


def test_every_citation_carries_its_qualifier(
        kind="S1", citations=S1_CITATIONS, qualifiers=S1_QUALIFIERS):
    offenders = []
    for path in _candidate_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        hits = _cites(text, citations)
        if hits and not _qualified(text, qualifiers):
            offenders.append(f"{path.relative_to(ROOT.parent)} cites {hits}")
    assert not offenders, (
        f"{kind} results are diagnostics only and their qualifier must travel "
        f"with them. These files cite the numbers without saying what is "
        f"wrong with them:\n  " + "\n  ".join(offenders))


def test_the_check_would_actually_catch_an_unqualified_citation(tmp_path):
    """A guard that cannot fail is a guard nobody should trust."""
    assert _cites("the pilot returned 13 PASS", S1_CITATIONS) == ["13 PASS"]
    assert _qualified("the pilot returned 13 PASS", S1_QUALIFIERS) is False
    assert _qualified("13 PASS, but the gate is UNRESOLVED", S1_QUALIFIERS) is True


def test_the_s1_receipt_still_says_the_gate_is_unresolved():
    """If S1 is ever resolved this test fails, which is the prompt to retire
    the qualifier deliberately rather than let it quietly stop being true."""
    import json
    receipt = json.loads(
        (ROOT / "mapping" / "s1_construct_validity_result_receipt_20260823.json")
        .read_text(encoding="utf-8"))
    assert receipt["formal_s1_gate_result"] == "UNRESOLVED"
    assert "NOT_INDEPENDENT_DOMAIN_EXPERT" in receipt["audit_limit"]


def test_the_v2_receipts_keep_their_qualifying_status():
    """The v2 labels are single-annotator, and the receipts must keep saying so.

    This guards the source rather than the citations. If these status fields
    are ever relaxed, every downstream use of the v2 diagnostics silently
    becomes a use of something that looks validated -- and unlike S1 there is
    no distinctive number to catch it further downstream.
    """
    import json
    diagnostic = json.loads(
        (ROOT / "mapping" / "mapA_v2_codex_diagnostic_result_receipt_20260821.json")
        .read_text(encoding="utf-8"))
    assert diagnostic["annotator"].startswith("single_")
    assert diagnostic["independent_multi_vendor_validation"] is False
    assert diagnostic["scope"] == "development_calibration_only"
    assert "NOT_FORMAL_VALIDATION" in diagnostic["status"]

    recall = json.loads(
        (ROOT / "mapping" / "mapA_v2_recall_audit_receipt.json")
        .read_text(encoding="utf-8"))
    # Labels are absent, so recall is not a number anyone may quote.
    assert recall["labels_present"] is False
    assert recall["recall_at_40"] == "NOT_EVALUABLE"
