#!/usr/bin/env python3
"""Measure the (sponsor, stock) dependence structure on the FINAL regression sample.

Plan §15.3.0 used to justify a sponsor-only resampling scheme with "only 20 of
389 treated stocks appear under more than one sponsor, so 94.9% of the relevant
dependence is covered". That argument is deleted, for two reasons that have
nothing to do with any result:

  * the numerator counted TREATED stocks only, while the stacked design's rows
    are overwhelmingly CONTROLS, and controls are reused across waves heavily
    (measured: 1,541 of 2,241 stocks appear in more than one wave, one of them
    23 times). The cross-sponsor repetition therefore lives mostly in the part
    that 20/389 never counted;
  * the denominator was the treated-stock count rather than the estimation
    sample, so the percentage answered a question nobody asks of a standard
    error.

So this script measures it instead of asserting it. It runs on the table the
estimator actually consumes — treated and control rows together — and writes
`dependence_profile.json`. Until that file exists, no coverage percentage may
appear in the paper (meta-rule 1: a number with no locator is a hallucination,
however reasonable it sounds).

Column names are NOT sniffed. The caller names them, because a wrong guess here
produces a plausible number rather than an error.

  python p1/t5_spec/measure_dependence.py --selftest
  python p1/t5_spec/measure_dependence.py --sample <parquet> \
      --stock-col permno --sponsor-col sponsor --wave-col wave_id \
      --treated-col treated
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

OUT = pathlib.Path(__file__).resolve().parent / "dependence_profile.json"


def _share(num, den):
    return (num / den) if den else None


def _profile_side(rows):
    """One side (all / treated / control) of the dependence profile."""
    by_stock = collections.defaultdict(set)
    rows_by_stock = collections.Counter()
    waves_by_stock = collections.defaultdict(set)
    for r in rows:
        by_stock[r["stock"]].add(r["sponsor"])
        waves_by_stock[r["stock"]].add(r["wave"])
        rows_by_stock[r["stock"]] += 1
    n_rows = sum(rows_by_stock.values())
    multi = {s for s, sp in by_stock.items() if len(sp) > 1}
    multi_rows = sum(rows_by_stock[s] for s in multi)
    per_stock = collections.Counter(len(sp) for sp in by_stock.values())
    wave_hist = collections.Counter(len(w) for w in waves_by_stock.values())
    return {
        "n_rows": n_rows,
        "n_stocks": len(by_stock),
        "n_sponsors": len({r["sponsor"] for r in rows}),
        "n_waves": len({r["wave"] for r in rows}),
        # THE number that may be quoted. Not a stock count: a ROW share, because
        # the standard error is a statement about the rows in the regression.
        "cross_sponsor_stocks": len(multi),
        "cross_sponsor_stock_share": _share(len(multi), len(by_stock)),
        "cross_sponsor_row_share": _share(multi_rows, n_rows),
        "max_sponsors_per_stock": max((len(sp) for sp in by_stock.values()),
                                      default=0),
        "sponsors_per_stock_hist": {str(k): v for k, v in sorted(per_stock.items())},
        "waves_per_stock_hist": {str(k): v for k, v in sorted(wave_hist.items())},
    }


def dependence_profile(rows) -> dict:
    """Cross-sponsor stock reuse on the estimation sample.

    `rows` are dicts with keys stock / sponsor / wave / treated. Pure, so the
    whole thing is testable without a landed sample.

    Reported three ways — all rows, treated rows, control rows — because the
    treated-only figure is precisely the one that misled the earlier draft. A
    sponsor-only resampling scheme leaves the cross-sponsor share UNCOVERED, so
    `cross_sponsor_row_share` on the ALL side is the honest size of what a
    one-way sponsor bootstrap would be assuming away.
    """
    rows = list(rows)
    treated = [r for r in rows if r.get("treated")]
    control = [r for r in rows if not r.get("treated")]
    prof = {
        "all": _profile_side(rows),
        "treated": _profile_side(treated),
        "control": _profile_side(control),
    }
    prof["verdict"] = (
        "sponsor-only resampling leaves "
        f"{prof['all']['cross_sponsor_row_share']:.1%} of estimation rows' "
        "cross-sponsor stock dependence uncovered"
        if prof["all"]["cross_sponsor_row_share"] is not None else
        "empty sample")
    # A one-way sponsor bootstrap is defensible only if stocks nest in sponsors.
    prof["stocks_nest_in_sponsors"] = prof["all"]["cross_sponsor_stocks"] == 0
    return prof


def _selftest() -> int:
    ok = True

    def check(label, got, want):
        nonlocal ok
        good = got == want
        print(f"  {'ok  ' if good else 'FAIL'} {label}: got {got!r}, want {want!r}")
        ok = ok and good

    # Nested: every stock sits under exactly one sponsor -> one-way is enough.
    nested = [{"stock": "A", "sponsor": "S1", "wave": "W1", "treated": True},
              {"stock": "B", "sponsor": "S2", "wave": "W2", "treated": True}]
    p = dependence_profile(nested)
    check("nested -> nests", p["stocks_nest_in_sponsors"], True)
    check("nested -> zero uncovered rows", p["all"]["cross_sponsor_row_share"], 0.0)

    # The case the deleted 94.9% claim got wrong: treated side looks clean, the
    # CONTROL side carries the cross-sponsor reuse. A treated-only figure would
    # report 0% uncovered while half the estimation rows are in fact uncovered.
    mixed = [
        {"stock": "A", "sponsor": "S1", "wave": "W1", "treated": True},
        {"stock": "B", "sponsor": "S2", "wave": "W2", "treated": True},
        {"stock": "C", "sponsor": "S1", "wave": "W1", "treated": False},
        {"stock": "C", "sponsor": "S2", "wave": "W2", "treated": False},
    ]
    p = dependence_profile(mixed)
    check("treated side looks clean", p["treated"]["cross_sponsor_row_share"], 0.0)
    check("control side is not", p["control"]["cross_sponsor_row_share"], 1.0)
    check("all rows uncovered share", p["all"]["cross_sponsor_row_share"], 0.5)
    check("does not nest", p["stocks_nest_in_sponsors"], False)
    check("max sponsors per stock", p["all"]["max_sponsors_per_stock"], 2)

    check("empty sample is not a 0%",
          dependence_profile([])["all"]["cross_sponsor_row_share"], None)

    print("\nSELFTEST", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", help="parquet/csv of the FINAL regression sample")
    ap.add_argument("--stock-col")
    ap.add_argument("--sponsor-col")
    ap.add_argument("--wave-col")
    ap.add_argument("--treated-col")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        sys.exit(_selftest())
    if not a.sample:
        print("BLOCKED — not run.\n")
        print("Needs the FINAL regression sample (treated AND control rows), which")
        print("does not exist until §15.3.1's estimation table is built. Measuring")
        print("cross-sponsor reuse on the treated set alone is the error this")
        print("script replaces (plan §15.3.0).\n")
        print("Also blocked on the trust -> economic-sponsor crosswalk: clustering")
        print("on the raw `family` field splits one JPMorgan into three and would")
        print("UNDERSTATE cross-sponsor reuse.\n")
        print("Run --selftest to verify the measure offline meanwhile.")
        sys.exit(2)

    missing = [n for n in ("stock_col", "sponsor_col", "wave_col", "treated_col")
               if not getattr(a, n)]
    if missing:
        sys.exit("NEED_HUMAN: name every column explicitly (missing "
                 f"{missing}). Sniffing them would turn a wrong guess into a "
                 "plausible number instead of an error (meta-rule 1).")

    import pandas as pd
    path = pathlib.Path(a.sample)
    df = (pd.read_parquet(path) if path.suffix == ".parquet"
          else pd.read_csv(path))
    for col in (a.stock_col, a.sponsor_col, a.wave_col, a.treated_col):
        if col not in df.columns:
            sys.exit(f"NEED_HUMAN: column {col!r} is not in {path.name} "
                     f"(has {sorted(df.columns)})")
    rows = [{"stock": r[a.stock_col], "sponsor": r[a.sponsor_col],
             "wave": r[a.wave_col], "treated": bool(r[a.treated_col])}
            for _, r in df.iterrows()]
    prof = dependence_profile(rows)
    prof["source"] = {"path": str(path), "stock_col": a.stock_col,
                      "sponsor_col": a.sponsor_col, "wave_col": a.wave_col,
                      "treated_col": a.treated_col, "n_input_rows": int(len(df))}
    OUT.write_text(json.dumps(prof, indent=2, sort_keys=True) + "\n")
    print(json.dumps(prof, indent=2, sort_keys=True))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
