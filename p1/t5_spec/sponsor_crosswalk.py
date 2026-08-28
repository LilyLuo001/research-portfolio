#!/usr/bin/env python3
"""Registrant/trust name -> economic sponsor, for the clustering dimension.

`events_merged.csv`'s `family` column is the SEC REGISTRANT (a trust or an
"Inc."), not the asset manager. Clustering on it directly splits one decision
maker into several and OVERSTATES the number of independent clusters — which
inflates precision in exactly the dimension the headline inference rests on
(plan §15.3, §15.3.0).

This script does the part that is derivable from committed data, and REFUSES to
do the part that is not.

  Derivable  : two registrants whose names normalise to the same stem are the
               same sponsor ("JPMorgan Trust I" / "JPMorgan Trust II"; "Bridgeway
               Funds" / "Bridgeway Funds, Inc."; the case-only duplicate
               "NORTHERN LIGHTS FUND TRUST II"). This is string evidence, and
               the evidence is printed next to every grouping.

  NOT derivable: that "Undiscovered Managers Funds" is JPMorgan, or that "DFA
               Investment Dimensions Group Inc." and "Dimensional Investment
               Group Inc." are one Dimensional, or that the Sanford C. Bernstein
               funds sit under the same manager as the AB funds. Those share no
               tokens. No amount of string processing finds them, and asserting
               them from model knowledge is exactly the hallucination meta-rule 1
               forbids.

So the deliverable is a PROPOSAL plus a gate. The proposal groups what names
prove and lists every remaining singleton as **not proven independent** — the
asymmetry matters, because an unreviewed singleton is the failure mode: it reads
as "one more independent cluster" when it may be the fourth trust of a manager
already in the sample.

`load_signed()` refuses to return anything until an owner-signed file exists,
so no estimation can quietly run on the proposal.

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
                status = "proposed_group"
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
    mapping = {r["family"]: r["proposed_sponsor"].strip() for r in rows}
    missing = sorted(set(_read_families()) - set(mapping))
    if missing:
        raise CrosswalkNotSigned(
            f"{len(missing)} registrants in events_merged.csv are absent from "
            f"the signed crosswalk (first few: {missing[:5]}). Each would "
            "silently become its own sponsor.")
    return mapping


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
        "Name matching finds some of it. It cannot find the rest, and the plan",
        "names two cases that prove it:",
        "",
        "* `Undiscovered Managers Funds` → JPMorgan — shares no token with",
        "  `JPMorgan Trust I/II/IV`.",
        "* `DFA Investment Dimensions Group Inc.` ↔ `Dimensional Investment",
        "  Group Inc.` — 'DFA' and 'Dimensional' share no token, and this pair",
        "  carries 93.6% of treated mass.",
        "",
        "Filling those from model knowledge is the hallucination meta-rule 1",
        "forbids. They need a locator (an ADV, a prospectus, an SEC filing).",
        "",
        f"## What the names DO prove — {s['collapse']}",
        "",
        f"{s['n_merged_by_name']} registrants fall into "
        f"{len(s['groups_found'])} multi-registrant groups on name evidence:",
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
        "2. Fill `proposed_sponsor` for **every** row with the economic asset",
        "   manager, and record the locator you used.",
        "3. Initial + date each row in `owner_signoff`.",
        f"4. Save as `{SIGNED.name}`.",
        "",
        "`load_signed()` refuses a missing file, an unfilled sponsor, an unsigned",
        "row, or any registrant it omits — so nothing can run on a partial answer.",
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
    check("grouped rows marked", stat["JPMorgan Trust I"], "proposed_group")
    check("singleton flagged", stat["VanEck Funds"],
          "SINGLETON_NOT_PROVEN_INDEPENDENT")

    # prefix containment: "Morgan Stanley Pathway Funds" must not split off
    rows = propose(["Morgan Stanley", "Morgan Stanley ETF Trust",
                    "Morgan Stanley Pathway Funds"])
    check("prefix containment merges pathway",
          len({r["name_stem"] for r in rows}), 1)
    check("all three grouped",
          {r["status"] for r in rows}, {"proposed_group"})

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
    print(f"\n{s['n_merged_by_name']} registrants merged into "
          f"{len(s['groups_found'])} groups on name evidence.")
    print(f"{len(s['singletons'])} singletons remain — NOT proven independent, "
          "owner review required.")
    print("\nNEED_HUMAN: fill proposed_sponsor + owner_signoff and save as "
          f"{SIGNED.name}. Estimation refuses until then.")


if __name__ == "__main__":
    main()
