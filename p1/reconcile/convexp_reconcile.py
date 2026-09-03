#!/usr/bin/env python3
"""p1/reconcile — free-path ConvExp vs CRSP ConvExp, side by side.

Why this is worth writing before the data exists
------------------------------------------------
We will shortly have TWO independent constructions of the same quantity:

  free   ConvExp = Σ_f (N-PORT shares held) / (SEC XBRL shares outstanding)
  CRSP   ConvExp = Σ_f (crsp holdings shares) / (CRSP shares outstanding)

Different holdings source, different denominator source, different identifier
system. Where they agree, both are corroborated by something stronger than an
internal consistency check. Where they disagree, the disagreement localises the
error — and the free path's own audit says its coverage story is "a strong
expectation, not yet a proof" (p1/output/convexp_coverage_audit/).

That makes this the cheapest validation in the project, and it costs nothing to
have ready before the WRDS window opens.

What it will NOT do
-------------------
It does not average, blend, or pick a winner. Two constructions that disagree
are a finding to report, not a number to reconcile away. The output is a
comparison table plus an explicit verdict, and a systematic divergence (a level
shift, or a tilt with market cap) is flagged as such rather than summarised as a
correlation.

  python p1/reconcile/convexp_reconcile.py                  # uses the default paths
  python p1/reconcile/convexp_reconcile.py --crsp <parquet> # once T2-wrds lands
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
FREE = ROOT / "p1" / "conv_exposure_free.parquet"
CRSP = ROOT / "p1" / "conv_exposure.parquet"
CROSSWALK = ROOT / "p1" / "t2_free" / "conv_exposure_free_crosswalk.csv"
STOCKNAMES = ROOT / "p1" / "wrds" / "raw" / "stock_names__stocknames.parquet"
OUTDIR = ROOT / "p1" / "reconcile"

# Treated-set thresholds the project already reasons in (coverage audit, T2a floor).
THRESHOLDS = (0.0025, 0.005, 0.01)
# A cell-level relative gap above this is "materially different", not rounding.
MATERIAL_REL_GAP = 0.10
# One-sidedness is judged by an exact sign test, not a fixed share band: with a
# handful of cells "higher in 2 of 3" is nothing, while with 5,000 cells a 55/45
# split is a real construction difference. Flag only when symmetry is genuinely
# implausible.
SIGN_TEST_ALPHA = 0.01


def sign_test_p(n_higher: int, n_total: int) -> float:
    """Exact two-sided binomial p-value against 50/50. No scipy dependency."""
    from math import comb
    if n_total == 0:
        return 1.0
    k, n = min(n_higher, n_total - n_higher), n_total
    tail = sum(comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def load_crosswalk(path: pathlib.Path = CROSSWALK) -> dict[str, str]:
    """cusip -> permno, from the free path's own crosswalk (permno may be blank)."""
    out: dict[str, str] = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            if r.get("permno"):
                out[r["cusip"].strip().upper()] = r["permno"].strip()
    return out


def permno_from_stocknames(cusips: set[str], path: pathlib.Path = STOCKNAMES,
                           resolver=None) -> dict[str, str]:
    """cusip -> permno from a landed CRSP stocknames pull.

    CRSP's cusip fields are historically 8-char; N-PORT carries 9. Match on the
    first 8 — that is the documented relationship, not a heuristic. Any CUSIP
    mapping to more than one permno is DROPPED rather than arbitrated: an
    ambiguous identifier match is exactly the kind of silent error this whole
    exercise exists to catch.
    """
    import pandas as pd
    if not path.exists():
        return {}
    df = pd.read_parquet(path)
    if resolver is None:
        sys.path.insert(0, str(ROOT / "p1" / "wrds"))
        from schema import Resolver
        resolver = Resolver()
    cols = resolver.spec["pulls"]["stock_names"]["columns"]
    pcol, ccol = cols["security_id"]["resolved"], cols["cusip"]["resolved"]
    if not pcol or not ccol:
        raise SystemExit("NEED_HUMAN: stock_names columns unresolved — run "
                         "`python p1/wrds/pull.py resolve` first.")
    df = df[[pcol, ccol]].dropna()
    df["_c8"] = df[ccol].astype(str).str.upper().str[:8]
    want8 = {c[:8] for c in cusips}
    df = df[df["_c8"].isin(want8)]
    grouped = df.groupby("_c8")[pcol].nunique()
    ambiguous = set(grouped[grouped > 1].index)
    if ambiguous:
        print(f"  {len(ambiguous)} CUSIP(s) map to multiple permnos — dropped, not "
              f"arbitrated (see reconcile_ambiguous_cusips.csv)")
        (OUTDIR / "reconcile_ambiguous_cusips.csv").write_text(
            "cusip8\n" + "\n".join(sorted(ambiguous)) + "\n")
    df = df[~df["_c8"].isin(ambiguous)]
    return {c: str(p) for c, p in zip(df["_c8"], df[pcol])}


def reconcile(free_df, crsp_df, cusip_to_permno: dict[str, str]) -> dict:
    """Join the two constructions on (permno, wave_id) and characterise the gap."""
    import numpy as np
    import pandas as pd

    f = free_df.copy()
    f["_c8"] = f["cusip"].astype(str).str.upper().str[:8]
    f["permno"] = f["_c8"].map(lambda c: cusip_to_permno.get(c))
    mapped = f[f["permno"].notna()].copy()
    mapped["permno"] = mapped["permno"].astype(str)

    c = crsp_df.copy()
    c["permno"] = c["permno"].astype(str)

    j = mapped.merge(c[["permno", "wave_id", "conv_exp"]],
                     on=["permno", "wave_id"], how="outer",
                     suffixes=("_free", "_crsp"), indicator=True)

    both = j[j["_merge"] == "both"].copy()
    both["abs_gap"] = (both["conv_exp_free"] - both["conv_exp_crsp"]).abs()
    denom = both[["conv_exp_free", "conv_exp_crsp"]].max(axis=1).replace(0, np.nan)
    both["rel_gap"] = both["abs_gap"] / denom

    rep: dict = {
        "cells": {
            "free_total": int(len(f)),
            "free_mapped_to_permno": int(len(mapped)),
            "free_unmapped": int(len(f) - len(mapped)),
            "crsp_total": int(len(c)),
            "matched_both": int(len(both)),
            "free_only": int((j["_merge"] == "left_only").sum()),
            "crsp_only": int((j["_merge"] == "right_only").sum()),
        },
        "agreement": {},
        "treated_sets": {},
        "systematic": {},
    }

    if len(both):
        rep["agreement"] = {
            "median_rel_gap": float(both["rel_gap"].median(skipna=True)),
            "p90_rel_gap": float(both["rel_gap"].quantile(0.90)),
            "share_within_1pct": float((both["rel_gap"] <= 0.01).mean()),
            "share_material_gap": float((both["rel_gap"] > MATERIAL_REL_GAP).mean()),
            # correlation is undefined for a single cell; report null, not NaN
            "correlation": (float(both["conv_exp_free"].corr(both["conv_exp_crsp"]))
                            if len(both) > 1 else None),
        }
        # A level shift or a size tilt is a BUG SIGNATURE, not noise. Report the
        # signed mean gap and its relationship to exposure size separately from
        # the symmetric dispersion measures above.
        signed = both["conv_exp_free"] - both["conv_exp_crsp"]
        nonzero = signed[signed != 0]
        n_higher, n_tied = int((signed > 0).sum()), int((signed == 0).sum())
        p = sign_test_p(int((nonzero > 0).sum()), int(len(nonzero)))
        rep["systematic"] = {
            "signed_mean_gap": float(signed.mean()),
            "signed_median_gap": float(signed.median()),
            "free_higher_share": float(n_higher / len(both)),
            "n_tied": n_tied,
            "sign_test_p": p,
            "one_sided": bool(p < SIGN_TEST_ALPHA),
            "note": ("exact two-sided sign test on the non-tied cells. Significant = a "
                     "one-sided construction difference that must be explained before "
                     "either series is used; not significant = symmetric noise, or too "
                     "few cells to tell."),
        }
        for t in THRESHOLDS:
            fs = set(both.loc[both["conv_exp_free"] >= t, "permno"])
            cs = set(both.loc[both["conv_exp_crsp"] >= t, "permno"])
            rep["treated_sets"][f"ge_{t}"] = {
                "free": len(fs), "crsp": len(cs),
                "intersection": len(fs & cs),
                "jaccard": (len(fs & cs) / len(fs | cs)) if (fs | cs) else None,
            }
    return rep


def verdict(rep: dict) -> list[str]:
    """State what the numbers mean, including when they mean 'do not proceed'."""
    a, s = rep.get("agreement"), rep.get("systematic")
    if not a:
        return ["NO OVERLAP — nothing to compare. Either the CRSP pull has not "
                "landed or the identifier mapping failed; check the crosswalk."]
    out = []
    if a["share_within_1pct"] >= 0.90:
        out.append("AGREE: >=90% of shared cells match within 1%. Two independent "
                   "constructions corroborate each other; the free path is validated "
                   "on the overlap.")
    elif a["share_material_gap"] >= 0.25:
        out.append(f"DISAGREE: {a['share_material_gap']:.0%} of shared cells differ by "
                   f"more than {MATERIAL_REL_GAP:.0%}. Do NOT average them. Localise "
                   "the cause (holdings source, denominator date, share-class "
                   "aggregation) before either series is used.")
    else:
        out.append("PARTIAL: agreement is neither clean nor broken — inspect the "
                   "tail before relying on either series.")
    if s and s.get("one_sided"):
        out.append(f"ONE-SIDED: the free path is higher in "
                   f"{s['free_higher_share']:.0%} of cells (sign test p="
                   f"{s['sign_test_p']:.2g}). That is a construction difference, not "
                   "noise — most likely a denominator-date or share-class convention "
                   "mismatch. Explain it before proceeding.")
    for t in THRESHOLDS:
        k = rep["treated_sets"].get(f"ge_{t}")
        if k and k["jaccard"] is not None and k["jaccard"] < 0.8:
            out.append(f"TREATED SET MOVES at ConvExp>={t}: Jaccard {k['jaccard']:.2f} "
                       f"(free {k['free']} vs CRSP {k['crsp']}). The sample the paper "
                       "keys on is construction-dependent — this belongs in the paper, "
                       "not in a footnote.")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--free", type=pathlib.Path, default=FREE)
    ap.add_argument("--crsp", type=pathlib.Path, default=CRSP)
    ap.add_argument("--out", type=pathlib.Path, default=OUTDIR / "convexp_reconcile.json")
    a = ap.parse_args()

    import pandas as pd
    if not a.crsp.exists():
        sys.exit(f"WAITING: {a.crsp.relative_to(ROOT)} does not exist yet — this "
                 "harness runs once P1-T2-wrds lands. Nothing to do (not an error).")
    free_df, crsp_df = pd.read_parquet(a.free), pd.read_parquet(a.crsp)

    m = load_crosswalk()
    m8 = {k[:8]: v for k, v in m.items()}
    m8.update(permno_from_stocknames(set(free_df["cusip"].astype(str)), resolver=None))
    print(f"identifier map: {len(m8)} cusip8 -> permno")

    rep = reconcile(free_df, crsp_df, m8)
    rep["verdict"] = verdict(rep)
    a.out.write_text(json.dumps(rep, indent=2) + "\n")

    sys.path.insert(0, str(ROOT / "ops" / "runner"))
    from lineage import write_lineage
    write_lineage(a.out, [a.free, a.crsp, CROSSWALK])

    print(json.dumps(rep["cells"], indent=2))
    for line in rep["verdict"]:
        print(f"\n  {line}")


if __name__ == "__main__":
    main()
