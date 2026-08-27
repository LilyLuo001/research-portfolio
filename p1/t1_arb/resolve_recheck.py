#!/usr/bin/env python3
"""Verify the recheck adjudications, then emit the overlay assemble.py consumes.

`recheck_resolution.json` records one verdict per gated fund group, each citing a
verbatim quote from a named accession. This script is the guard on that file:

  **every quote must be found, character for character, in that accession's
  committed excerpt — or nothing is emitted at all.**

That is the whole point. A verdict is only as good as the evidence behind it, and
a quote nobody re-checks is indistinguishable from a quote from memory
(CLAUDE.md meta-rule 1). Here the check is mechanical and runs in CI.

It also refuses on coverage gaps in either direction: a gated fund group with no
resolution, or a resolution naming a fund group that is not in the pool.

  python p1/t1_arb/resolve_recheck.py            # verify + write the overlay
  python p1/t1_arb/resolve_recheck.py --check    # verify only, exit non-zero on failure
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
import unicodedata

HERE = pathlib.Path(__file__).resolve().parent
P1 = HERE.parent
ROOT = P1.parent
RESOLUTION = HERE / "recheck_resolution.json"
OVERLAY = HERE / "recheck_overlay.json"

sys.path.insert(0, str(HERE))

VERDICTS = ("event", "not_event", "unresolved")


def normalise(s: str) -> str:
    """Fold the differences that are typography, not substance.

    The excerpts carry curly quotes, non-breaking spaces and soft hyphens from
    the original HTML. A quote that differs only in those is the same quote; a
    quote that differs in a WORD is not, and must still fail.
    """
    s = unicodedata.normalize("NFKC", s)
    for a, b in [("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'),
                 ("–", "-"), ("—", "-"), (" ", " "), ("­", "")]:
        s = s.replace(a, b)
    return " ".join(s.split())


def load_pool() -> dict[tuple[str, str], list[dict]]:
    """The gated records, keyed by (fund_name, family) — same key the file uses."""
    from recheck_dossier import load_gated
    pool: dict[tuple[str, str], list[dict]] = collections.OrderedDict()
    for r in load_gated():
        pool.setdefault((r["fund_name"], r["family"]), []).append(r)
    return pool


def verify() -> tuple[list[dict], list[str]]:
    from recheck_dossier import excerpt_index

    spec = json.loads(RESOLUTION.read_text())
    resolutions = spec["resolutions"]
    pool = load_pool()
    idx = excerpt_index()
    errors: list[str] = []

    seen: set[tuple[str, str]] = set()
    for r in resolutions:
        key = (r["fund_name"], r["family"])
        seen.add(key)
        if key not in pool:
            errors.append(f"resolution names a fund group not in the gated pool: {key}")
            continue
        if r["verdict"] not in VERDICTS:
            errors.append(f"{key}: unknown verdict {r['verdict']!r}")
            continue

        if r["verdict"] == "unresolved":
            if r.get("quote"):
                errors.append(f"{key}: unresolved rows must not carry a quote")
            if not r.get("reason"):
                errors.append(f"{key}: unresolved rows must state a reason")
            continue

        quote, acc = r.get("quote"), r.get("accession")
        if not quote or not acc:
            errors.append(f"{key}: verdict {r['verdict']} needs both a quote and an accession")
            continue
        text = idx.get(acc)
        if text is None:
            errors.append(f"{key}: no committed excerpt for accession {acc}")
            continue
        if normalise(quote) not in normalise(text):
            errors.append(
                f"{key}: QUOTE NOT FOUND in {acc}. This is the failure mode the whole "
                f"file exists to prevent — a verdict resting on text that is not there.\n"
                f"      quote: {quote[:160]!r}")

    for key in pool:
        if key not in seen:
            errors.append(f"gated fund group has no resolution: {key}")

    return resolutions, errors


def build_overlay(resolutions: list[dict]) -> dict:
    """Per (fund_name, family): the verdict assemble.py should apply.

    `event` releases the record from the gate; `not_event` and `unresolved` keep
    it out — but for DIFFERENT reasons, and the overlay preserves the difference
    so a later reader can tell a rejection from an open question.
    """
    pool = load_pool()
    entries = {}
    for r in resolutions:
        key = f"{r['fund_name']}||{r['family']}"
        recs = pool.get((r["fund_name"], r["family"]), [])
        entries[key] = {
            "fund_name": r["fund_name"],
            "family": r["family"],
            "verdict": r["verdict"],
            "standard": r.get("standard"),
            "accession": r.get("accession"),
            "quote": r.get("quote"),
            "reason": r.get("reason"),
            "note": r.get("note"),
            "n_gated_records": len(recs),
            "gate_reasons": sorted({x["gate_reason"] for x in recs}),
            "effective_dates": sorted({x["effective_date"] for x in recs}),
        }
    counts = collections.Counter(e["verdict"] for e in entries.values())
    rec_counts = collections.Counter()
    for e in entries.values():
        rec_counts[e["verdict"]] += e["n_gated_records"]
    return {
        "_meta": {
            "purpose": "Owner-gate recheck pool, adjudicated. Consumed by assemble.py.",
            "produced_by": "p1/t1_arb/resolve_recheck.py",
            "every_quote_verified_against": "p1/t1_channelA_wip/handoff/cb_*.txt",
            "fund_groups": dict(counts),
            "gated_records": dict(rec_counts),
        },
        "entries": entries,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify only, write nothing")
    a = ap.parse_args()

    resolutions, errors = verify()
    if errors:
        print(f"REFUSING — {len(errors)} problem(s) with recheck_resolution.json:\n")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)

    overlay = build_overlay(resolutions)
    m = overlay["_meta"]
    print(f"all {len(resolutions)} resolutions verified against the committed excerpts.")
    print(f"  fund groups   : {m['fund_groups']}")
    print(f"  gated records : {m['gated_records']}")
    if a.check:
        return
    OVERLAY.write_text(json.dumps(overlay, indent=2, ensure_ascii=False) + "\n")
    print(f"\nwrote {OVERLAY.relative_to(ROOT)}")
    print("next: python p1/t1_arb/assemble.py")


if __name__ == "__main__":
    main()
