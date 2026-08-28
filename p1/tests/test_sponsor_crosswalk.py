"""The trust -> economic sponsor crosswalk, and the gate that keeps it honest.

Clustering on `events_merged.csv`'s `family` splits one asset manager into
several registrants and overstates the number of independent clusters — in the
exact dimension the headline inference rests on. Name matching recovers part of
that; the rest is external knowledge and must come from the owner with a locator.

These tests pin both halves: the string evidence behaves, and the parts that are
NOT string evidence are refused rather than guessed.
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
# what the names DO prove                                                      #
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
    assert {r["status"] for r in rows} == {"proposed_group"}


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


def test_partially_filled_crosswalk_refuses(tmp_path):
    p = tmp_path / "signed.csv"
    with open(p, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["family", "proposed_sponsor",
                                           "owner_signoff"])
        w.writeheader()
        w.writerow({"family": "JPMorgan Trust I", "proposed_sponsor": "JPMorgan",
                    "owner_signoff": "QL 2026-08-28"})
        w.writerow({"family": "JPMorgan Trust II", "proposed_sponsor": "",
                    "owner_signoff": ""})
    with pytest.raises(sc.CrosswalkNotSigned) as e:
        sc.load_signed(p)
    assert "signoff" in str(e.value)


def test_a_crosswalk_missing_registrants_refuses(tmp_path):
    """An omitted registrant does not error at estimation time — it silently
    becomes its own cluster."""
    p = tmp_path / "signed.csv"
    with open(p, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["family", "proposed_sponsor",
                                           "owner_signoff"])
        w.writeheader()
        w.writerow({"family": "JPMorgan Trust I", "proposed_sponsor": "JPMorgan",
                    "owner_signoff": "QL 2026-08-28"})
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
    assert "93.6%" in text            # why the DFA pair is the expensive one
