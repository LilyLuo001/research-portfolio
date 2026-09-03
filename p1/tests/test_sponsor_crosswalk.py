"""The trust -> economic sponsor crosswalk, and the gate that keeps it honest.

Clustering on `events_merged.csv`'s `family` splits one asset manager into
several registrants and overstates the number of independent clusters — in the
exact dimension the headline inference rests on. Name matching GENERATES
CANDIDATES; it is not evidence, and it fails in both directions -- the same
manager under unrelated names, and unrelated managers under one series trust.

These tests pin both halves: the candidate generator behaves, and nothing reaches
a final mapping without a filing locator behind it.
"""
import csv
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "p1" / "t5_spec" / "sponsor_crosswalk.py"
sys.path.insert(0, str(SCRIPT.parent))

import sponsor_crosswalk as sc  # noqa: E402

PROPOSAL = ROOT / "p1" / "t5_spec" / "sponsor_crosswalk_PROPOSED.csv"
GATE = ROOT / "p1" / "t5_spec" / "SPONSOR-CROSSWALK-GATE.md"
EVENTS = ROOT / "p1" / "events_merged.csv"


def test_selftest_passes():
    r = subprocess.run([sys.executable, str(SCRIPT), "--selftest"],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr


# --------------------------------------------------------------------------- #
# what the names PROPOSE (candidates -- still gated on filing evidence)        #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("a,b", [
    ("JPMorgan Trust I", "JPMorgan Trust II"),           # trailing enumerator
    ("JPMorgan Trust I", "JPMorgan Trust IV"),
    ("Bridgeway Funds", "Bridgeway Funds, Inc."),        # punctuation + suffix
    ("NORTHERN LIGHTS FUND TRUST II",                    # case only
     "Northern Lights Fund Trust II"),
    ("The Hartford Mutual Funds, Inc.", "The Hartford Mutual Funds II, Inc."),
    ("Columbia Funds Series Trust I", "Columbia Funds Series Trust II"),
])
def test_same_manager_by_name_collides(a, b):
    assert sc.normalise_registrant(a) == sc.normalise_registrant(b)


def test_prefix_containment_keeps_a_family_together():
    """Exact-stem matching alone splits 'Morgan Stanley Pathway Funds' off from
    the other Morgan Stanley trusts — a false extra cluster."""
    rows = sc.propose(["Morgan Stanley", "Morgan Stanley ETF Trust",
                       "Morgan Stanley Institutional Fund Trust",
                       "Morgan Stanley Pathway Funds"])
    assert len({r["name_stem"] for r in rows}) == 1
    assert {r["status"] for r in rows} == {"CANDIDATE_GROUP_NEEDS_FILING_EVIDENCE"}


def test_a_short_stem_does_not_swallow_a_lookalike():
    """'ab' must not absorb 'abrdn': the prefix test is token-wise, not
    character-wise, or every stem sharing a few letters would merge."""
    ab = sc.normalise_registrant("AB Bond Fund, Inc.")
    abrdn = sc.normalise_registrant("abrdn Funds")
    assert not sc._is_token_prefix(ab, abrdn)
    rows = sc.propose(["AB Bond Fund, Inc.", "abrdn Funds"])
    assert len({r["name_stem"] for r in rows}) == 2


# --------------------------------------------------------------------------- #
# what the names DO NOT prove — and must not pretend to                        #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("a,b", [
    # the two cases the plan names, and the reason this gate exists at all
    ("DFA Investment Dimensions Group Inc.", "Dimensional Investment Group Inc."),
    ("Undiscovered Managers Funds", "JPMorgan Trust I"),
    ("Sanford C. Bernstein Fund, Inc.", "AB Bond Fund, Inc."),
])
def test_same_manager_with_no_shared_token_is_not_invented(a, b):
    """A string tool cannot find these. It must not claim to — and it must not
    quietly leave them as two independent clusters either, which is what the
    SINGLETON status and the owner gate are for."""
    assert sc.normalise_registrant(a) != sc.normalise_registrant(b)
    rows = {r["family"]: r["status"] for r in sc.propose([a, b])}
    assert all(s.startswith("SINGLETON") for s in rows.values())


def test_leading_token_near_misses_are_surfaced_not_merged():
    """Three Fidelity trusts share only their first word. Merging them silently
    would be a guess; hiding them would waste the cheapest review the owner
    can do."""
    fam = ["Fidelity Commonwealth Trust II", "Fidelity Salem Street Trust",
           "Fidelity Summer Street Trust"]
    rows = sc.propose(fam)
    assert len({r["name_stem"] for r in rows}) == 3          # not merged
    assert {r["status"] for r in rows} == {"SINGLETON_LEADING_TOKEN_CANDIDATE"}
    for r in rows:                                           # but named
        assert "fidelity" in r["basis"]


# --------------------------------------------------------------------------- #
# the gate                                                                     #
# --------------------------------------------------------------------------- #
def test_unsigned_crosswalk_refuses(tmp_path):
    with pytest.raises(sc.CrosswalkNotSigned) as e:
        sc.load_signed(tmp_path / "nope.csv")
    assert "PROPOSAL" in str(e.value) or "PROPOSED" in str(e.value)


FIELDS = ["family", "proposed_sponsor", "evidence_locator", "owner_signoff"]


def _write(path, rows):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})
    return path


def test_partially_filled_crosswalk_refuses(tmp_path):
    p = _write(tmp_path / "signed.csv", [
        {"family": "JPMorgan Trust I", "proposed_sponsor": "JPMorgan",
         "evidence_locator": "ADV 801-xxxxx", "owner_signoff": "QL 2026-08-28"},
        {"family": "JPMorgan Trust II"},
    ])
    with pytest.raises(sc.CrosswalkNotSigned) as e:
        sc.load_signed(p)
    assert "signoff" in str(e.value)


def test_a_row_with_no_filing_evidence_refuses(tmp_path):
    """Name evidence does not satisfy the evidence column. A candidate group with
    no filing behind it is still a guess -- and a shared series trust is a
    positive reason to expect the name to be WRONG."""
    p = _write(tmp_path / "signed.csv", [
        {"family": "JPMorgan Trust I", "proposed_sponsor": "JPMorgan",
         "evidence_locator": "", "owner_signoff": "QL 2026-08-28"},
    ])
    with pytest.raises(sc.CrosswalkNotSigned) as e:
        sc.load_signed(p)
    msg = str(e.value)
    assert "evidence locator" in msg and "Stem matching" in msg


def test_proposal_carries_an_evidence_column_for_every_row():
    with open(PROPOSAL, newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert rows and "evidence_locator" in rows[0]
    assert all(r["evidence_locator"] == "" for r in rows), (
        "the proposal must ship the evidence column EMPTY -- prefilling it from "
        "name matching is exactly the substitution the gate forbids")


def test_a_crosswalk_missing_registrants_refuses(tmp_path):
    """An omitted registrant does not error at estimation time — it silently
    becomes its own cluster."""
    p = tmp_path / "signed.csv"
    _write(p, [{"family": "JPMorgan Trust I", "proposed_sponsor": "JPMorgan",
                "evidence_locator": "ADV 801-xxxxx",
                "owner_signoff": "QL 2026-08-28"}])
    with pytest.raises(sc.CrosswalkNotSigned) as e:
        sc.load_signed(p)
    assert "absent from" in str(e.value)


def test_no_signed_crosswalk_is_committed_yet():
    """If this ever fails, the owner has signed one — good. Update the plan's
    NEED_HUMAN and delete this test in the same commit."""
    assert not sc.SIGNED.exists(), (
        "a signed crosswalk exists; §15.3.0's NEED_HUMAN should be closed and "
        "this guard removed in the same commit")


# --------------------------------------------------------------------------- #
# the committed artifacts reproduce                                            #
# --------------------------------------------------------------------------- #
def test_proposal_reproduces_from_committed_events():
    assert PROPOSAL.exists() and GATE.exists()
    with open(PROPOSAL, newline="") as fh:
        committed = list(csv.DictReader(fh))
    fresh = sc.propose(sc._read_families(EVENTS))
    assert [dict(r) for r in committed] == fresh, (
        "the committed proposal no longer reproduces from events_merged.csv — "
        "re-run `python p1/t5_spec/sponsor_crosswalk.py --propose`")


def test_every_registrant_appears_exactly_once():
    with open(PROPOSAL, newline="") as fh:
        rows = list(csv.DictReader(fh))
    fams = [r["family"] for r in rows]
    assert len(fams) == len(set(fams))
    assert set(fams) == set(sc._read_families(EVENTS))


def test_gate_names_the_two_cases_string_matching_cannot_find():
    text = GATE.read_text()
    assert "Undiscovered Managers Funds" in text
    assert "DFA Investment Dimensions Group Inc." in text
    assert "559/573" in text           # current reason the DFA pair is material


def test_gate_warns_about_shared_series_trusts_and_names_the_review_priorities():
    """Names fail in BOTH directions. A series trust hosts unrelated managers, so
    grouping by trust name is positively wrong there -- the economic sponsor is
    the sub-adviser of the converting series."""
    text = GATE.read_text()
    for trust in ("Advisors Series Trust", "The RBB Fund", "Two Roads Shared",
                  "Northern Lights"):
        assert trust in text, trust
    assert "sub-adviser" in text
    for name in ("Dimensional", "JPMorgan", "Fidelity"):
        assert name in text, name
    assert "not evidence" in text


def test_gate_maps_to_the_decision_maker_not_to_a_label():
    """Correcting an over-correction. The target is the entity that plausibly
    made the conversion decision and transmits the common organizational shock
    -- NOT the legal trust, and not automatically the sub-adviser either. A
    platform that converted several sub-advised series at once IS a shared
    shock, and splitting those by sub-adviser would overstate independence."""
    text = GATE.read_text()
    assert "generated the conversion decision" in text
    assert "not automatically the sub-adviser" in text.lower()
    assert "platform" in text


def test_ambiguous_is_a_permitted_answer_not_a_failure(tmp_path):
    """Forcing an unresolved registrant into a heuristic group produces an
    unknown that LOOKS settled -- a confident, wrong cluster count that nothing
    downstream can detect."""
    assert "AMBIGUOUS" in GATE.read_text()
    p = _write(tmp_path / "signed.csv", [
        {"family": f, "proposed_sponsor": ("AMBIGUOUS" if i == 0 else "X"),
         "evidence_locator": "checked ADV + SAI; adviser vs platform unresolved",
         "owner_signoff": "QL 2026-08-28"}
        for i, f in enumerate(sorted(set(sc._read_families())))
    ])
    mapping = sc.load_signed(p)                 # accepted, not refused
    amb = sc.ambiguous_families(p)
    assert len(amb) == 1 and mapping[amb[0]] == "AMBIGUOUS"


def test_ambiguous_alternatives_are_described_as_alternative_maps(tmp_path):
    """Not 'alternative treatments'. The treatment variable, sample and
    specification are identical across the two runs; only the partition defining
    the sponsor dimension differs. Calling them alternative treatments invites
    the reader to think two different estimands are being compared."""
    for text in (GATE.read_text(), sc.ambiguous_families.__doc__):
        assert "sponsor/clustering maps" in text or "sponsor map" in text, text[:80]
    doc = sc.ambiguous_families.__doc__
    assert "not alternative treatments" in doc
    assert "same sample" in GATE.read_text() or "same specification" in doc


def test_ambiguous_still_requires_evidence_of_what_was_checked(tmp_path):
    """'Ambiguous' is a conclusion, not a blank. It has to say what failed to
    resolve, or it is indistinguishable from an unreviewed row."""
    p = _write(tmp_path / "signed.csv", [
        {"family": "JPMorgan Trust I", "proposed_sponsor": "AMBIGUOUS",
         "evidence_locator": "", "owner_signoff": "QL 2026-08-28"},
    ])
    with pytest.raises(sc.CrosswalkNotSigned):
        sc.load_signed(p)
