#!/usr/bin/env python3
"""Registrant/trust name -> economic sponsor, for the clustering dimension.

`events_merged.csv`'s `family` column is the SEC REGISTRANT (a trust or an
"Inc."), not the asset manager. Clustering on it directly splits one decision
maker into several and OVERSTATES the number of independent clusters — which
inflates precision in exactly the dimension the headline inference rests on
(plan §15.3, §15.3.0).

This script GENERATES CANDIDATES from committed data. It does not establish the
crosswalk, and it refuses to be used as if it had.

**Name matching is a candidate generator, not evidence** (owner, 2026-08-28).
Every final mapping must carry a filing/adviser locator — an ADV, a
prospectus/SAI adviser section, an N-CEN, a registrant series list — before
sign-off. Names fail in both directions:

  false negatives : "Undiscovered Managers Funds" is JPMorgan; "DFA Investment
               Dimensions Group Inc." and "Dimensional Investment Group Inc."
               are one Dimensional (93.6% of treated mass); the Sanford C.
               Bernstein funds sit under the same manager as the AB funds. None
               of these share a token. No string processing finds them, and
               filling them from model knowledge is the hallucination meta-rule 1
               forbids.

  false positives : a shared name is not a shared adviser. Shared SERIES TRUSTS
               host unrelated managers — Advisors Series Trust, The RBB Fund,
               Northern Lights, Two Roads Shared Trust, FundVantage,
               Professionally Managed Portfolios. There the registrant may be a
               shell, so the mapping can differ row by row inside one registrant.

WHAT THE TARGET ACTUALLY IS. Not the legal trust, and **not automatically the
sub-adviser label either**: the object is the economic entity that plausibly
GENERATED THE CONVERSION DECISION and would transmit a common organizational
shock. Sometimes that is the sub-adviser; sometimes it is the trust's own
adviser or a distribution platform that drove the conversion across several
sub-advised series. Reading either label off mechanically is the same error in a
different costume.

Where governance genuinely does not resolve, the answer is `AMBIGUOUS`, not a
forced group. An honest ambiguous row is a known unknown that downstream code
must handle; a forced one is an unknown that looks settled.

So the deliverable is a CANDIDATE list plus a gate. Every singleton is marked
"not proven independent" — the asymmetry matters, because an unreviewed singleton
reads as one more independent cluster when it may be the fourth trust of a
manager already in the sample.

`load_signed()` returns nothing until an owner-signed file exists in which every
row has a sponsor, an evidence locator and a signoff.

  python p1/t5_spec/sponsor_crosswalk.py --selftest
  python p1/t5_spec/sponsor_crosswalk.py --propose
"""
from __future__ import annotations

import argparse
import collections
import csv
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
EVENTS = ROOT / "p1" / "events_merged.csv"
HERE = pathlib.Path(__file__).resolve().parent
PROPOSAL = HERE / "sponsor_crosswalk_PROPOSED.csv"
SIGNED = HERE / "sponsor_crosswalk_SIGNED.csv"
GATE = HERE / "SPONSOR-CROSSWALK-GATE.md"

# Words that carry no information about WHO manages the fund. Stripping them is
# what makes "JPMorgan Trust I" and "JPMorgan Trust II" collide.
_VEHICLE = {
    "fund", "funds", "trust", "trusts", "portfolio", "portfolios", "series",
    "group", "inc", "incorporated", "llc", "lp", "co", "company", "the",
    "of", "for", "and", "mutual", "investment", "investments", "select",
    "institutional", "advised", "managed", "account", "accounts", "core",
    "equity", "income", "bond", "municipal", "strategy", "strategic",
    "alternative", "alternatives", "etf", "cap", "large", "small", "mid",
    "value", "growth", "index", "shares", "class", "dba",
}
# Trailing enumerators: JPMorgan Trust I / II / IV, Hartford Mutual Funds II.
_ORDINAL = re.compile(r"^(i{1,3}|iv|v|vi{1,3}|ix|x|\d+)$")
_PUNCT = re.compile(r"[^a-z0-9]+")


class CrosswalkNotSigned(RuntimeError):
    """Raised when estimation code tries to use an unsigned crosswalk."""


def normalise_registrant(name: str) -> str:
    """Registrant name -> comparison stem. Typography and vehicle words only.

    Deliberately conservative: it strips wrappers, it never MAPS one manager
    onto another. "dfa investment dimensions" and "dimensional investment"
    normalise to different stems, and that is the correct answer for a function
    whose only evidence is the string.
    """
    toks = [t for t in _PUNCT.sub(" ", (name or "").lower()).split() if t]
    keep = [t for t in toks if t not in _VEHICLE and not _ORDINAL.match(t)]
    # A name made entirely of vehicle words (e.g. "Managed Account Series") has
    # no stem; fall back to the full normalised string so it stays distinct
    # rather than colliding with every other such name.
    return " ".join(keep) if keep else " ".join(toks)


MIN_PREFIX_CHARS = 4     # do not let a two-letter stem swallow unrelated names


def _is_token_prefix(short: str, long: str) -> bool:
    """Is `short` a whole-token prefix of `long`? "morgan stanley" ⊂ "morgan
    stanley pathway", but "ab" is not a prefix of "abrdn" — token-wise, not
    character-wise, or every stem starting with the same letters would merge."""
    if short == long or len(short) < MIN_PREFIX_CHARS:
        return False
    a, b = short.split(), long.split()
    return len(a) < len(b) and b[:len(a)] == a


def _merge_groups(stems):
    """Union stems that are equal or token-prefix related. Union-find, so
    a ⊂ b ⊂ c lands in one group rather than two overlapping pairs."""
    parent = {s: s for s in stems}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a in stems:
        for b in stems:
            if _is_token_prefix(a, b):
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[rb] = ra          # the SHORTER stem is the root
    out = collections.defaultdict(list)
    for s in stems:
        out[find(s)].append(s)
    return out


def leading_token_candidates(stems):
    """Distinct stems sharing a first token — CANDIDATES, never auto-merged.

    "fidelity commonwealth" / "fidelity salem street" / "fidelity summer street"
    are almost certainly one Fidelity, but no string fact says so: three
    unrelated managers could each begin with the same word. Surfacing them for
    review is right; merging them silently is the same error as leaving
    Undiscovered Managers on its own, pointed the other way.
    """
    by_head = collections.defaultdict(set)
    for s in stems:
        if s:
            by_head[s.split()[0]].add(s)
    return {h: sorted(v) for h, v in sorted(by_head.items()) if len(v) > 1}


def propose(families) -> list[dict]:
    """Group registrants by normalised stem. Returns one row per registrant."""
    by_stem = collections.defaultdict(list)
    for f in sorted(set(families)):
        by_stem[normalise_registrant(f)].append(f)
    merged = _merge_groups(list(by_stem))
    cands = leading_token_candidates(list(by_stem))

    rows = []
    for root, stems in sorted(merged.items()):
        members = sorted(f for s in stems for f in by_stem[s])
        for f in members:
            others = [m for m in members if m != f]
            head = root.split()[0] if root else ""
            flagged = [s for s in cands.get(head, []) if s not in stems]
            if others:
                basis = "name_stem_shared_with: " + "; ".join(others)
                status = "CANDIDATE_GROUP_NEEDS_FILING_EVIDENCE"
            elif flagged:
                basis = ("no registrant shares this name stem, but these stems "
                         "share its leading token and MAY be the same manager: "
                         + "; ".join(flagged))
                status = "SINGLETON_LEADING_TOKEN_CANDIDATE"
            else:
                basis = "no other registrant shares this name stem"
                status = "SINGLETON_NOT_PROVEN_INDEPENDENT"
            rows.append({
                "family": f,
                "name_stem": root,
                "proposed_sponsor": "",        # owner fills: the economic manager
                "basis": basis,
                "status": status,
                # Owner fills: the FILING/ADVISER locator that establishes the
                # mapping — an ADV, a prospectus/SAI adviser section, an N-CEN,
                # a registrant's series list. Name evidence is a candidate
                # generator, NOT evidence (owner, 2026-08-28), so this column is
                # required on every row, including the ones the stem matcher
                # grouped: two trusts sharing a brand name can sit under
                # different advisers, and shared-series-trust structures
                # (Advisors Series Trust, The RBB Fund, Northern Lights, Two
                # Roads) host unrelated managers. On an AMBIGUOUS row this
                # column records what WAS checked and why it did not resolve.
                "evidence_locator": "",
                "owner_signoff": "",           # owner fills: initials + date
            })
    return rows


def _read_families(path=EVENTS) -> list[str]:
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows or "family" not in rows[0]:
        sys.exit(f"NEED_HUMAN: {path} has no `family` column "
                 f"(has {sorted(rows[0]) if rows else 'no rows'})")
    return [r["family"] for r in rows if r.get("family")]


def load_signed(path=SIGNED) -> dict:
    """family -> economic sponsor, from the OWNER-SIGNED file only.

    Refuses on: a missing file, any row without a sponsor, any row without a
    signoff, and any registrant in events_merged.csv that the file omits. Every
    one of those failures would otherwise show up as a plausible cluster count
    rather than as an error.
    """
    p = pathlib.Path(path)
    if not p.exists():
        raise CrosswalkNotSigned(
            f"{p} does not exist. The PROPOSAL ({PROPOSAL.name}) is NOT a "
            "substitute: it groups only what registrant names prove, and the two "
            "cases the plan names (Undiscovered Managers -> JPMorgan, DFA <-> "
            "Dimensional) share no tokens and cannot be found that way. Run "
            "--propose, have the owner complete and sign it, then re-run.")
    with open(p, newline="") as fh:
        rows = list(csv.DictReader(fh))
    bad = [r.get("family") for r in rows
           if not (r.get("proposed_sponsor") or "").strip()
           or not (r.get("owner_signoff") or "").strip()]
    if bad:
        raise CrosswalkNotSigned(
            f"{len(bad)} rows lack a sponsor or an owner signoff (first few: "
            f"{bad[:5]}). A partially signed crosswalk is not usable: the "
            "unsigned rows would each count as their own cluster.")
    # Name evidence is a candidate generator, not evidence (owner, 2026-08-28).
    # Every mapping needs a filing/adviser locator — including the ones the stem
    # matcher grouped, since a shared brand name does not establish a shared
    # adviser and a shared series trust positively implies unrelated ones.
    noev = [r.get("family") for r in rows
            if not (r.get("evidence_locator") or "").strip()]
    if noev:
        raise CrosswalkNotSigned(
            f"{len(noev)} rows carry no filing/adviser evidence locator (first "
            f"few: {noev[:5]}). Stem matching may PROPOSE a grouping; it cannot "
            "establish one. Cite an ADV, a prospectus/SAI adviser section, an "
            "N-CEN, or a registrant series list per row.")
    mapping = {r["family"]: r["proposed_sponsor"].strip() for r in rows}
    missing = sorted(set(_read_families()) - set(mapping))
    if missing:
        raise CrosswalkNotSigned(
            f"{len(missing)} registrants in events_merged.csv are absent from "
            f"the signed crosswalk (first few: {missing[:5]}). Each would "
            "silently become its own sponsor.")
    return mapping


AMBIGUOUS = "AMBIGUOUS"


def ambiguous_families(path=SIGNED) -> list[str]:
    """Registrants the owner marked `AMBIGUOUS` — governance did not resolve.

    A permitted answer, not a failure. Forcing an unresolved registrant into a
    heuristic group produces an unknown that LOOKS settled, which is worse than
    a known unknown: the cluster count comes out confident and wrong, in either
    direction.

    Estimation must handle these EXPLICITLY rather than letting them default.
    Both treatments are defensible and neither is free, so the plan requires
    both to be reported: (a) each ambiguous registrant as its own cluster —
    which over-counts independence if it in fact belongs to a sponsor already in
    the sample; (b) merged into its best-guess candidate group — which
    under-counts if it does not. If the headline conclusion moves between them,
    that is a finding about how much the crosswalk carries, and it is stated
    rather than resolved by picking the nicer one.
    """
    return [f for f, s in load_signed(path).items() if s.upper() == AMBIGUOUS]


def summarise(rows) -> dict:
    groups = collections.defaultdict(list)
    for r in rows:
        groups[r["name_stem"]].append(r["family"])
    multi = {k: v for k, v in groups.items() if len(v) > 1}
    singles = sorted(v[0] for v in groups.values() if len(v) == 1)
    cands = sorted(r["family"] for r in rows
                   if r["status"] == "SINGLETON_LEADING_TOKEN_CANDIDATE")
    return {
        "n_registrants": len(rows),
        "n_stems": len(groups),
        "n_merged_by_name": sum(len(v) for v in multi.values()),
        "groups_found": {k: sorted(v) for k, v in sorted(multi.items())},
        "singletons": singles,
        "leading_token_candidates": cands,
        "by_basis": {r["family"]: r["basis"] for r in rows
                     if r["status"] == "SINGLETON_LEADING_TOKEN_CANDIDATE"},
        "collapse": f"{len(rows)} registrants -> {len(groups)} name stems",
    }


def _write_gate(rows, s) -> None:
    lines = [
        "# OWNER GATE — trust → economic sponsor crosswalk",
        "",
        "**Blocks**: §15.3.1 headline inference and §15.3.0's dependence",
        "measurement. **Does NOT block** Gate 0, B1 or B2 — neither uses sponsor",
        "clustering.",
        "",
        "## Why this cannot be automated",
        "",
        "`family` in `events_merged.csv` is the SEC registrant, not the manager.",
        "Clustering on it splits one decision maker into several and overstates",
        "the number of independent clusters — precision inflated in exactly the",
        "dimension the headline result rests on.",
        "",
        "**Name matching generates candidates. It is not evidence** (owner,",
        "2026-08-28). It fails in both directions:",
        "",
        "*False negatives* — the same manager under unrelated names:",
        "",
        "* `Undiscovered Managers Funds` → JPMorgan — shares no token with",
        "  `JPMorgan Trust I/II/IV`.",
        "* `DFA Investment Dimensions Group Inc.` ↔ `Dimensional Investment",
        "  Group Inc.` — 'DFA' and 'Dimensional' share no token, and this pair",
        "  carries 93.6% of treated mass.",
        "",
        "*False positives* — a shared name that is not a shared adviser. Series",
        "trusts host UNRELATED managers: `Advisors Series Trust`, `The RBB",
        "Fund`, `Northern Lights Fund Trust II/IV`, `Two Roads Shared Trust`,",
        "`Trust for Advised Portfolios`, `Manager Directed Portfolios`,",
        "`Investment Managers Series Trust II`, `FundVantage Trust`,",
        "`Professionally Managed Portfolios`. For these the registrant may be a",
        "shell, so the mapping can differ row by row within one registrant and",
        "grouping by trust name would be wrong.",
        "",
        "## What you are mapping TO",
        "",
        "**The economic entity that plausibly generated the conversion decision**",
        "— the one that would transmit a common organizational shock. Not the",
        "legal trust. **And not automatically the sub-adviser label either.**",
        "",
        "Sometimes the decision sits with the sub-adviser. Sometimes it sits with",
        "the trust's own adviser, or with a distribution platform that converted",
        "several sub-advised series at once — in which case those series DO share",
        "a shock and splitting them by sub-adviser would overstate independence.",
        "Reading either label off mechanically is the same error in a different",
        "costume. The question is always: who decided, and whose shock is shared?",
        "",
        "### `AMBIGUOUS` is a permitted answer",
        "",
        "Where governance genuinely does not resolve, write `AMBIGUOUS` in",
        "`proposed_sponsor` and record in `evidence_locator` what you checked and",
        "why it did not settle. **Do not force the row into a heuristic group.**",
        "A forced row is an unknown that looks settled: the cluster count comes",
        "out confident and wrong, and nothing downstream can tell.",
        "",
        "`ambiguous_families()` returns these, and estimation must handle them",
        "explicitly — reporting the headline both with each ambiguous registrant",
        "as its own cluster and merged into its best-guess group. If the",
        "conclusion moves between the two, that is a finding about how much the",
        "crosswalk carries, and it gets stated rather than resolved by picking",
        "the nicer one.",
        "",
        "So every row needs a locator: an ADV, a prospectus/SAI adviser section,",
        "an N-CEN, or a registrant series list. Filling any of it from model",
        "knowledge is the hallucination meta-rule 1 forbids.",
        "",
        "**Review these four first** — they are where the cluster count actually",
        "moves: **Dimensional** (93.6% of treated mass), **JPMorgan**,",
        "**Fidelity**, and the shared-series-trust rows above.",
        "",
        f"## Candidate groupings from names — {s['collapse']}",
        "",
        f"{s['n_merged_by_name']} registrants fall into "
        f"{len(s['groups_found'])} multi-registrant candidate groups. **Each",
        "still needs filing evidence before sign-off** — `load_signed()` refuses",
        "a row with no `evidence_locator`, grouped or not:",
        "",
    ]
    for stem, members in s["groups_found"].items():
        lines.append(f"* **{stem}** — " + "; ".join(f"`{m}`" for m in members))
    if s["leading_token_candidates"]:
        lines += [
            "",
            f"## {len(s['leading_token_candidates'])} near-misses — same leading "
            "token, NOT merged",
            "",
            "These share a first word with another stem. They are very likely the",
            "same manager, but no string fact says so — three unrelated firms",
            "could each begin with the same word — so they are surfaced, not",
            "merged. **Review these first: they are the cheapest real reductions",
            "in the cluster count.**",
            "",
        ]
        for f in s["leading_token_candidates"]:
            lines.append(f"* `{f}` — {s['by_basis'][f]}")
    lines += [
        "",
        f"## The {len(s['singletons'])} singletons are NOT proven independent",
        "",
        "This is the asymmetry that matters. A group found by name is evidence;",
        "a singleton is only *absence* of name evidence. Left unreviewed, each",
        "one counts as another independent cluster — which is the error, not the",
        "safe default.",
        "",
    ]
    lines += [f"* `{f}`" for f in s["singletons"]]
    lines += [
        "",
        "## What to do",
        "",
        f"1. Open `{PROPOSAL.name}`.",
        "2. Fill `proposed_sponsor` for **every** row with the entity that",
        "   plausibly made the conversion decision — or `AMBIGUOUS` if the",
        "   governance does not resolve. For a shared series trust the answer",
        "   may be the sub-adviser, the trust's adviser, or a platform; decide",
        "   it, do not read a label.",
        "3. Fill `evidence_locator` on **every** row — including rows the stem",
        "   matcher grouped. A candidate group with no filing behind it is still",
        "   a guess.",
        "4. Initial + date each row in `owner_signoff`.",
        f"5. Save as `{SIGNED.name}`.",
        "",
        "`load_signed()` refuses a missing file, an unfilled sponsor, a missing",
        "evidence locator, an unsigned row, or any registrant it omits — so",
        "nothing can run on a partial answer.",
        "",
    ]
    GATE.write_text("\n".join(lines) + "\n")


def _selftest() -> int:
    ok = True

    def check(label, got, want):
        nonlocal ok
        good = got == want
        print(f"  {'ok  ' if good else 'FAIL'} {label}: got {got!r}, want {want!r}")
        ok = ok and good

    n = normalise_registrant
    check("enumerator stripped", n("JPMorgan Trust I"), n("JPMorgan Trust II"))
    check("suffix/punctuation stripped",
          n("Bridgeway Funds"), n("Bridgeway Funds, Inc."))
    check("case only", n("NORTHERN LIGHTS FUND TRUST II"),
          n("Northern Lights Fund Trust II"))
    check("hartford II", n("The Hartford Mutual Funds II, Inc."),
          n("The Hartford Mutual Funds, Inc."))

    # The two cases the whole gate exists for: string evidence CANNOT find them,
    # and the function must not pretend otherwise.
    check("DFA != Dimensional by name",
          n("DFA Investment Dimensions Group Inc.")
          == n("Dimensional Investment Group Inc."), False)
    check("Undiscovered Managers != JPMorgan by name",
          n("Undiscovered Managers Funds") == n("JPMorgan Trust I"), False)

    # An all-vehicle-word name keeps its full string rather than collapsing
    check("all-vehicle names stay distinct",
          n("Managed Account Series") == n("Series Portfolios Trust"), False)

    rows = propose(["JPMorgan Trust I", "JPMorgan Trust II", "VanEck Funds"])
    stat = {r["family"]: r["status"] for r in rows}
    check("grouped rows marked", stat["JPMorgan Trust I"],
          "CANDIDATE_GROUP_NEEDS_FILING_EVIDENCE")
    check("singleton flagged", stat["VanEck Funds"],
          "SINGLETON_NOT_PROVEN_INDEPENDENT")

    # prefix containment: "Morgan Stanley Pathway Funds" must not split off
    rows = propose(["Morgan Stanley", "Morgan Stanley ETF Trust",
                    "Morgan Stanley Pathway Funds"])
    check("prefix containment merges pathway",
          len({r["name_stem"] for r in rows}), 1)
    check("all three grouped", {r["status"] for r in rows},
          {"CANDIDATE_GROUP_NEEDS_FILING_EVIDENCE"})

    # leading-token near-miss: surfaced, never silently merged
    rows = propose(["Fidelity Salem Street Trust", "Fidelity Summer Street Trust"])
    check("fidelity stems stay distinct",
          len({r["name_stem"] for r in rows}), 2)
    check("fidelity flagged as candidates", {r["status"] for r in rows},
          {"SINGLETON_LEADING_TOKEN_CANDIDATE"})

    # a short stem must not swallow an unrelated name that merely starts alike
    check("ab does not absorb abrdn",
          _is_token_prefix(n("AB Bond Fund, Inc."), n("abrdn Funds")), False)

    try:
        load_signed(HERE / "does_not_exist.csv")
        print("  FAIL unsigned crosswalk did not refuse"); ok = False
    except CrosswalkNotSigned as e:
        print(f"  ok   unsigned crosswalk refuses: {str(e)[:48]}...")

    print("\nSELFTEST", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--propose", action="store_true",
                    help="write the proposal + owner gate from events_merged.csv")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        sys.exit(_selftest())
    if not a.propose:
        ap.print_help()
        sys.exit(2)

    rows = propose(_read_families())
    with open(PROPOSAL, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    s = summarise(rows)
    _write_gate(rows, s)
    print(f"wrote {PROPOSAL}  ({s['collapse']})")
    print(f"wrote {GATE}")
    print(f"\n{s['n_merged_by_name']} registrants fall into "
          f"{len(s['groups_found'])} CANDIDATE groups on name evidence — "
          "candidates, not conclusions.")
    print(f"{len(s['singletons'])} singletons remain — NOT proven independent, "
          "owner review required.")
    print("\nNEED_HUMAN: fill proposed_sponsor + evidence_locator + "
          f"owner_signoff on EVERY row and save as {SIGNED.name}. Name evidence "
          "does not satisfy evidence_locator; estimation refuses until then.")


if __name__ == "__main__":
    main()
