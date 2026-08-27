#!/usr/bin/env python3
"""Gate 0 — portfolio continuity across each MF→ETF conversion.

The paper's whole narrative is "the same portfolio in a different wrapper".
That is a falsifiable empirical claim about holdings, not an institutional fact
that can be assumed. Plan v2.0 filed it as robustness threat T3; v2.1 promotes it
to **Gate 0**, ahead of the kill test, because if continuity is weak the wrapper
interpretation is wrong — and that is a reason to rewrite the framing, not a
footnote to a headline regression.

Four measures per conversion wave, comparing the LAST pre-conversion N-PORT
against the FIRST post-conversion N-PORT of the surviving ETF:

    name_jaccard   |A ∩ B| / |A ∪ B| over the held security sets
    weight_overlap Σ_i min(w_i^pre, w_i^post)      — overlapping mass, in [0,1]
    weight_corr    corr(w^pre, w^post) on the union, missing filled with 0
    turnover       ½ Σ_i |w_i^post − w_i^pre|      — in [0,1]

`weight_overlap` is the headline: it is the share of the portfolio, by weight,
that survived the wrapper change. `name_jaccard` alone would call a fund
continuous when it kept every ticker but re-weighted the book entirely.

Thresholds are frozen BEFORE the distribution is seen (plan §9.0):
    ≥ 0.80  main sample
    0.60–0.80  "partially continuous" — reported separately, never pooled
    < 0.60  NOT a wrapper change — dropped from the main sample and named

Sensitivity at 0.70 / 0.80 / 0.90 is reported so the conclusion cannot rest on
one cut.

  python p1/gate0_continuity/compute_continuity.py --holdings <parquet>
  python p1/gate0_continuity/compute_continuity.py --selftest   # no data needed
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent / "continuity_by_wave.csv"
REPORT = pathlib.Path(__file__).resolve().parent / "GATE0-RESULT.md"

MAIN_FLOOR = 0.80
PARTIAL_FLOOR = 0.60
SENSITIVITY = (0.70, 0.80, 0.90)


def weights(holdings):
    """Security -> portfolio weight. `holdings` maps security id -> USD value."""
    total = sum(v for v in holdings.values() if v and v > 0)
    if total <= 0:
        return {}
    return {k: v / total for k, v in holdings.items() if v and v > 0}


def share_continuity(pre_sh: dict, post_sh: dict) -> dict:
    """Continuity in SHARES HELD, independent of price (v2.1, item 4).

    Value weights move when prices move. A fund that traded nothing across a
    quarter in which its largest position doubled will show a value-weight shift
    and look like it rebalanced. Share counts do not have that problem: they
    change only if the manager actually traded.

    So value-weight overlap answers "is the economic exposure the same?" while
    share overlap answers "did the manager trade?". Both are reported; a wave
    where share continuity is high but weight overlap is low is a PRICE move,
    not a portfolio change, and must not be classified as discontinuous.
    """
    names = set(pre_sh) | set(post_sh)
    if not names:
        return {"share_overlap": None, "share_turnover": None, "n_traded_out": None}
    kept = sum(min(pre_sh.get(k, 0.0), post_sh.get(k, 0.0)) for k in names)
    total_pre = sum(v for v in pre_sh.values() if v and v > 0)
    overlap = kept / total_pre if total_pre > 0 else None
    turn = (sum(abs(post_sh.get(k, 0.0) - pre_sh.get(k, 0.0)) for k in names)
            / (2 * total_pre)) if total_pre > 0 else None
    out = sum(1 for k in pre_sh if pre_sh.get(k, 0) > 0 and post_sh.get(k, 0) == 0)
    return {"share_overlap": overlap, "share_turnover": turn, "n_traded_out": out}


def continuity(pre: dict, post: dict, pre_shares=None, post_shares=None) -> dict:
    """Continuity measures for one wave. Pure function — unit-testable offline.

    `pre`/`post` are security -> USD value. `pre_shares`/`post_shares` are
    security -> share count; when supplied, the share-based measures are added
    so a price move is not mistaken for a rebalancing (item 4).
    """
    wp, wq = weights(pre), weights(post)
    if not wp or not wq:
        return {"name_jaccard": None, "weight_overlap": None,
                "weight_corr": None, "turnover": None,
                "n_pre": len(wp), "n_post": len(wq),
                "note": "empty portfolio on one side"}

    names_p, names_q = set(wp), set(wq)
    union = names_p | names_q
    jac = len(names_p & names_q) / len(union) if union else None
    overlap = sum(min(wp.get(k, 0.0), wq.get(k, 0.0)) for k in union)
    turn = 0.5 * sum(abs(wq.get(k, 0.0) - wp.get(k, 0.0)) for k in union)

    # Pearson correlation on the union, absent holdings treated as weight 0.
    xs = [wp.get(k, 0.0) for k in union]
    ys = [wq.get(k, 0.0) for k in union]
    n = len(union)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sxx = sum((a - mx) ** 2 for a in xs)
    syy = sum((b - my) ** 2 for b in ys)
    corr = sxy / ((sxx * syy) ** 0.5) if sxx > 0 and syy > 0 else None

    out = {"name_jaccard": jac, "weight_overlap": overlap,
           "weight_corr": corr, "turnover": turn,
           "n_pre": len(wp), "n_post": len(wq), "note": ""}
    if pre_shares is not None and post_shares is not None:
        out.update(share_continuity(pre_shares, post_shares))
        # A large weight move with almost no share move is a PRICE move.
        if (out.get("share_overlap") is not None and overlap is not None
                and out["share_overlap"] - overlap > 0.15):
            out["note"] = ("weight shift exceeds share shift — likely a PRICE "
                           "move, not rebalancing; classify on share_overlap")
    return out


def classify(overlap, turnover, floor=MAIN_FLOOR):
    """Frozen ex-ante rule. Returns one of main / partial / not_a_wrapper_change.

    **0.80 is an OPERATIONAL cutoff, not an economically natural discontinuity**
    (v2.1, item 4). Nothing changes about a conversion at 0.7999 that does not
    also hold at 0.8001. The bin exists so the sample rule is frozen before the
    distribution is seen; it is NOT a claim that continuity is bimodal.

    Therefore the deliverable is the CONTINUOUS distribution plus sensitivity at
    0.70/0.80/0.90 — and, where power allows, the headline coefficient as a
    smooth function of the continuity measure. `classify` is for sample
    bookkeeping, never for a "high vs low continuity" economic contrast.
    """
    if overlap is None:
        return "unknown"
    if overlap >= floor and (turnover is None or turnover <= 0.20):
        return "main"
    if overlap >= PARTIAL_FLOOR:
        return "partial"
    return "not_a_wrapper_change"


def cc_share_case():
    """One position doubles in price, zero trading. Weights move, shares do not."""
    pre_v  = {"AAA": 50.0, "BBB": 50.0}
    post_v = {"AAA": 100.0, "BBB": 50.0}          # AAA doubled in price
    pre_s  = {"AAA": 10.0, "BBB": 10.0}
    post_s = {"AAA": 10.0, "BBB": 10.0}           # nothing traded
    return continuity(pre_v, post_v, pre_s, post_s)


def _selftest() -> int:
    """Prove the measures behave before any real holdings exist."""
    ok = True

    def check(label, got, want, tol=1e-9):
        nonlocal ok
        good = got is None and want is None or (
            got is not None and want is not None and abs(got - want) < tol)
        print(f"  {'ok  ' if good else 'FAIL'} {label}: got {got}, want {want}")
        ok = ok and good

    # identical portfolios -> perfect continuity, zero turnover
    a = {"AAA": 50.0, "BBB": 50.0}
    r = continuity(a, dict(a))
    check("identical weight_overlap", r["weight_overlap"], 1.0)
    check("identical turnover", r["turnover"], 0.0)
    check("identical jaccard", r["name_jaccard"], 1.0)

    # disjoint portfolios -> nothing survives
    r = continuity({"AAA": 100.0}, {"ZZZ": 100.0})
    check("disjoint weight_overlap", r["weight_overlap"], 0.0)
    check("disjoint turnover", r["turnover"], 1.0)
    check("disjoint jaccard", r["name_jaccard"], 0.0)

    # same names, fully re-weighted -> jaccard says 1.0 but overlap catches it.
    # This is exactly why weight_overlap is the headline and jaccard is not.
    r = continuity({"AAA": 90.0, "BBB": 10.0}, {"AAA": 10.0, "BBB": 90.0})
    check("reweighted jaccard (misleading)", r["name_jaccard"], 1.0)
    check("reweighted weight_overlap", r["weight_overlap"], 0.2)
    check("reweighted turnover", r["turnover"], 0.8)

    # share-based measures: a pure PRICE move must not read as rebalancing
    r = cc_share_case()
    check("price-move share_overlap", r["share_overlap"], 1.0)
    check("price-move share_turnover", r["share_turnover"], 0.0)
    good = "PRICE" in (r.get("note") or "")
    print(f"  {'ok  ' if good else 'FAIL'} price-move flagged in note: {r.get('note')!r}")
    ok = ok and good

    # classification boundaries
    for overlap, turn, want in [(0.95, 0.05, "main"), (0.80, 0.20, "main"),
                                (0.79, 0.05, "partial"), (0.60, 0.10, "partial"),
                                (0.59, 0.10, "not_a_wrapper_change"),
                                (0.95, 0.50, "partial")]:
        got = classify(overlap, turn)
        good = got == want
        print(f"  {'ok  ' if good else 'FAIL'} classify({overlap},{turn}) = {got}")
        ok = ok and good

    print("\nSELFTEST", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--holdings", help="parquet with pre/post holdings per wave")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        sys.exit(_selftest())

    if not a.holdings:
        print("GATE 0 — BLOCKED, not run.\n")
        print("Needs the FIRST POST-conversion N-PORT of each surviving ETF.")
        print("The committed ConvExp pipeline only fetches PRE-conversion filings")
        print("(build_nport_convexp.py: `filed < eff_date`), so that side does not")
        print("exist in this repo yet and cannot be derived from what is here.\n")
        print("Unblocks with SEC egress, alongside the ConvExp rebuild:")
        print("  ops/briefs/P1-T2-CONVEXP-REBUILD.md\n")
        print("Run --selftest to verify the measures offline in the meantime.")
        sys.exit(2)

    sys.exit("NEED_HUMAN: --holdings ingestion is intentionally unimplemented "
             "until the post-conversion N-PORT schema is known. Writing a "
             "reader against a guessed schema is how you get a silent join bug "
             "(meta-rule 1). Implement it in the same lane that fetches them.")


if __name__ == "__main__":
    main()
