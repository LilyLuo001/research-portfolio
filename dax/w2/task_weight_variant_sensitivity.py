#!/usr/bin/env python3
"""Does the choice of task-weight definition change occupation-level answers?

W2-D4 froze two variants alongside the primary weight, before anyone looked,
for exactly one reason: if a headline moves materially across them, the
aggregation function is doing work the data cannot support, and that is a
finding to report rather than a number to choose from.

This measures the movement. It runs on the built weights alone and needs no
wage bill, no mapping and no index, so it can answer the question long before
any of those exist -- which is the point, because the answer changes whether
the weight is a footnote or a threat.

W2-D2's note that "the choice probably does not matter much" rests on a
reported correlation of 0.999 between importance-weighted and unweighted
occupation means, recorded there as *reported, not verified*, because the
source was unreachable. This turns that citation into a measurement on the
actual O*NET release the project uses. If it holds, the weight defect in
W2-D3 -- ordinal FT bands treated as cardinal -- is bounded in consequence and
can be reported as such. If it does not hold, that defect is load-bearing and
the paper has to say so.

Three definitions, all normalised within occupation:
  task_weight_share       importance x frequency-band-weighted mean  (primary)
  importance_only_share   IM / sum(IM)                              (field standard)
  equal_weight_share      1 / n_tasks
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

VARIANTS = ("task_weight_share", "importance_only_share", "equal_weight_share")


def pairwise(frame, a, b):
    """Agreement between two weight definitions, within occupation.

    Rank correlation answers "would this reorder an occupation's tasks"; the
    share gap answers "by how much would any one task's mass change". A
    definition can preserve order perfectly and still move mass a long way,
    so neither number alone settles it.
    """
    import pandas as pd  # noqa: F401

    # equal_weight_share is constant within every occupation by construction,
    # so it has no within-occupation ranking and a rank correlation against it
    # is undefined for EVERY occupation -- not for a few odd ones. Discovered
    # in test: without this the equal-weight pairs would have reported an
    # empty correlation block with no stated reason, and a reader would have
    # taken the silence for missing data rather than for a structural fact.
    # Mass reallocated stays meaningful there and is the metric to read.
    constant = [name for name in (a, b)
                if frame.groupby("onet_soc")[name].nunique().max() == 1]

    per_occ = []
    for occ, g in frame.groupby("onet_soc"):
        if len(g) < 2:
            # A single-task occupation has share 1.0 under every definition
            # and a rank correlation that is undefined, not perfect. Counting
            # it as agreement would inflate every headline here.
            continue
        # Ties give zero variance and a NaN correlation. That is a handled
        # case here, not a numerical accident, so numpy's divide warning is
        # suppressed for this call only rather than repo-wide.
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            rho = g[a].rank().corr(g[b].rank(), method="pearson")  # Spearman
        per_occ.append({
            "onet_soc": occ,
            "n_tasks": int(len(g)),
            "rank_corr": float(rho) if rho == rho else None,
            "max_abs_share_gap": float((g[a] - g[b]).abs().max()),
            "total_abs_share_gap": float((g[a] - g[b]).abs().sum()),
        })

    usable = [r for r in per_occ if r["rank_corr"] is not None]
    rhos = sorted(r["rank_corr"] for r in usable)
    gaps = sorted(r["max_abs_share_gap"] for r in per_occ)

    def q(values, p):
        if not values:
            return None
        i = min(int(p * (len(values) - 1) + 0.5), len(values) - 1)
        return values[i]

    return {
        "pair": [a, b],
        "occupations_compared": len(per_occ),
        "occupations_with_defined_rank_corr": len(usable),
        "rank_corr": {"min": rhos[0] if rhos else None,
                      "p05": q(rhos, 0.05), "median": q(rhos, 0.50),
                      "mean": (sum(rhos) / len(rhos)) if rhos else None},
        "rank_corr_undefined_reason": (
            f"{constant} is constant within occupation, so there is no "
            f"within-occupation ranking to correlate. Read "
            f"mass_reallocated_fraction instead." if constant else None),
        "max_abs_share_gap": {"median": q(gaps, 0.50), "p95": q(gaps, 0.95),
                              "max": gaps[-1] if gaps else None},
        # Half the summed absolute gap is total variation distance between the
        # two share distributions: the fraction of an occupation's mass that
        # would have to move to turn one weighting into the other.
        "mass_reallocated_fraction": {
            "median": (q(sorted(r["total_abs_share_gap"] / 2 for r in per_occ), 0.50)),
            "p95": (q(sorted(r["total_abs_share_gap"] / 2 for r in per_occ), 0.95)),
            "max": (q(sorted(r["total_abs_share_gap"] / 2 for r in per_occ), 1.0)),
        },
        "per_occupation": per_occ,
    }


def _distribution(pair):
    """How the disagreement is spread, not just where its middle sits.

    A median alone understates this badly: the median rank correlation is
    respectable while a large minority of occupations reorder heavily, and it
    is the minority that decides whether a headline is stable.
    """
    rhos = sorted(r["rank_corr"] for r in pair["per_occupation"]
                  if r["rank_corr"] is not None)
    mass = sorted(r["total_abs_share_gap"] / 2 for r in pair["per_occupation"])
    if not rhos:
        return {"rank_corr_available": False}
    return {
        "pair": pair["pair"],
        "occupations": len(rhos),
        "share_of_occupations_with_rank_corr_below": {
            str(t): sum(1 for r in rhos if r < t) / len(rhos)
            for t in (0.99, 0.95, 0.90, 0.80, 0.70, 0.50)},
        "share_of_occupations_with_mass_moved_above": {
            str(t): sum(1 for m in mass if m > t) / len(mass)
            for t in (0.05, 0.10, 0.15)},
    }


def build(frame):
    import pandas as pd  # noqa: F401

    missing = [c for c in VARIANTS if c not in frame.columns]
    if missing:
        raise SystemExit(
            f"NEED_HUMAN: weights file is missing {missing}. W2-D4 requires "
            f"all three definitions to be built together; comparing a subset "
            f"would report agreement that was never measured.")

    pairs = [pairwise(frame, VARIANTS[0], VARIANTS[1]),
             pairwise(frame, VARIANTS[0], VARIANTS[2]),
             pairwise(frame, VARIANTS[1], VARIANTS[2])]

    return {
        "record_version": "dax-w2-task-weight-variant-sensitivity-v1",
        "decision": "dax/memo/W2_DECISION_task_weight_2026-08-24.md [W2-D4]",
        "what_this_answers": (
            "whether the aggregation function is doing work the data cannot "
            "support. Frozen before inspection, so this is a report and not a "
            "selection: no variant may be adopted because it looks better."),
        "n_rows": int(len(frame)),
        "n_occupations": int(frame["onet_soc"].nunique()),
        "pairs": [{k: v for k, v in p.items() if k != "per_occupation"}
                  for p in pairs],
        "per_occupation": {"/".join(p["pair"]): p["per_occupation"] for p in pairs},
        "reported_literature_claim": {
            "claim": "importance-weighted and unweighted occupation means "
                     "correlate at 0.999",
            "status_in_W2_D2": "reported, not verified -- source unreachable",
            "still_unverified": True,
            "not_comparable_to_the_numbers_here": (
                "That claim is a BETWEEN-occupation correlation of "
                "occupation-level aggregate scores. Everything measured here "
                "is WITHIN-occupation agreement between task shares. A high "
                "correlation of occupation aggregates is fully compatible "
                "with substantial within-occupation reordering, because "
                "aggregating averages the reordering away. An earlier version "
                "of this record placed the two side by side, which invited "
                "reading one as a test of the other. Reproducing the claim "
                "needs a task-level score to aggregate, which requires "
                "crossing data that does not exist yet."),
        },
        "within_occupation_disagreement": _distribution(pairs[0]),
        "how_to_read_this": (
            "High rank correlation with small reallocated mass means the "
            "W2-D3 defect (ordinal FT bands treated as cardinal) is bounded in "
            "consequence and can be reported as a limitation. Low correlation "
            "or large reallocation means that defect is load-bearing, the "
            "headline must be reported across all three definitions, and the "
            "fix path in W2-D3 becomes required work rather than a note."),
        "not_a_selection_rule": (
            "This never picks a weight. The primary is fixed by W2-D1 and "
            "changing it would break the reconciliation with Mapping A's "
            "coverage and the DWA bound."),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--weights", type=pathlib.Path,
                    default=pathlib.Path("dax/data_built/onet_task_weights.parquet"))
    ap.add_argument("--output", type=pathlib.Path,
                    default=pathlib.Path(
                        "dax/data_built/onet_task_weight_variant_sensitivity.json"))
    args = ap.parse_args(argv)

    try:
        import pandas as pd
    except ImportError:
        print("pandas is required", file=sys.stderr)
        return 2
    if not args.weights.is_file():
        print(f"NEED_HUMAN: {args.weights} not found. Run "
              f"dax/w2/build_onet_task_weights.py first.", file=sys.stderr)
        return 2

    rec = build(pd.read_parquet(args.weights))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")

    print(f"wrote {args.output}")
    print(f"{rec['n_rows']} tasks across {rec['n_occupations']} occupations\n")
    for p in rec["pairs"]:
        print(f"{p['pair'][0]} vs {p['pair'][1]}")
        if p["rank_corr"]["median"] is None:
            print(f"  rank corr   undefined -- {p['rank_corr_undefined_reason']}")
        else:
            print(f"  rank corr   median {p['rank_corr']['median']:.4f}   "
                  f"p05 {p['rank_corr']['p05']:.4f}   min {p['rank_corr']['min']:.4f}")
        print(f"  mass moved  median {p['mass_reallocated_fraction']['median']:.4f}  "
              f"p95 {p['mass_reallocated_fraction']['p95']:.4f}  "
              f"max {p['mass_reallocated_fraction']['max']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
