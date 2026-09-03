#!/usr/bin/env python3
"""How separable is AI exposure from remote-work feasibility?

The gate. Emanuel, Harrington & Pallais (NY Fed, 2026) attribute 64% of the
rise in young college-graduate unemployment to remote work rather than AI, and
Brynjolfsson, Chandar & Chen control for interest-rate exposure but not for
telework. If AI exposure and telework feasibility are measuring nearly the same
occupations, then the young-worker AI literature has an unaddressed confound
and the two channels may not be separately identified in occupation-level data.

That is an empirical question about the joint distribution and it decides which
paper gets written:

  * separable  -> the decomposition is estimable; report both channels
  * inseparable -> the finding is that occupation-level data cannot attribute
                   the young-worker decline between AI and remote work, which
                   bounds what the existing literature can claim

Correlation alone does not settle it. What matters for identification is
whether enough EMPLOYMENT sits off the diagonal -- occupations that are
AI-exposed but not teleworkable, and vice versa. A high correlation with a
thick off-diagonal is workable; a moderate correlation concentrated in a few
tiny occupations is not.

Sources, all public and downloaded rather than recalled:
  Dingel & Neiman (2020) teleworkable, O*NET-SOC, binary
    github.com/jdingel/DingelNeiman-workathome
  Eloundou, Manning, Mishkin & Rock (2023) GPT exposure, O*NET-SOC
    github.com/openai/GPTs-are-GPTs -- alpha=E1, beta=E1+0.5*E2, gamma=E1+E2,
    separately as GPT-4 ratings (dv_) and human annotator ratings (human_)
  Felten, Raj & Seamans (2021) AIOE, 6-digit SOC
    github.com/AIOE-Data/AIOE
  OEWS 2021 employment, for weights -- already built in this repo
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
from collections import defaultdict

# Eloundou's three cumulative definitions. beta is the paper's headline.
ELOUNDOU_MEASURES = ["dv_rating_alpha", "dv_rating_beta", "dv_rating_gamma",
                     "human_rating_alpha", "human_rating_beta", "human_rating_gamma"]


def soc6(code):
    """O*NET-SOC 11-1011.00 -> SOC 11-1011. Already-6-digit codes pass through."""
    return str(code).strip()[:7]


def _corr(pairs, weights=None):
    """Pearson correlation, optionally weighted. Returns None if degenerate."""
    if len(pairs) < 3:
        return None
    w = weights if weights is not None else [1.0] * len(pairs)
    sw = sum(w)
    if sw <= 0:
        return None
    mx = sum(wi * x for wi, (x, _) in zip(w, pairs)) / sw
    my = sum(wi * y for wi, (_, y) in zip(w, pairs)) / sw
    sxx = sum(wi * (x - mx) ** 2 for wi, (x, _) in zip(w, pairs))
    syy = sum(wi * (y - my) ** 2 for wi, (_, y) in zip(w, pairs))
    sxy = sum(wi * (x - mx) * (y - my) for wi, (x, y) in zip(w, pairs))
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def load_dingel_neiman(path):
    """Collapse the binary O*NET-SOC flag to a 6-digit SOC share.

    Averaging the binary flag across an occupation's detail codes yields the
    fraction of its detailed occupations that are teleworkable, which is a
    better-behaved regressor than the binary and is what the SOC-level merge
    requires anyway.
    """
    import csv
    acc = defaultdict(list)
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            v = (row.get("teleworkable") or "").strip()
            if v == "":
                continue
            acc[soc6(row["onetsoccode"])].append(float(v))
    return {k: sum(v) / len(v) for k, v in acc.items()}, {k: len(v) for k, v in acc.items()}


def load_eloundou(path):
    import csv
    acc = defaultdict(lambda: defaultdict(list))
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            k = soc6(row["O*NET-SOC Code"])
            for m in ELOUNDOU_MEASURES:
                v = (row.get(m) or "").strip()
                if v != "":
                    acc[k][m].append(float(v))
    return {k: {m: sum(vs) / len(vs) for m, vs in d.items()} for k, d in acc.items()}


def load_aioe(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb["Appendix A"]
    out = {}
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0 or row[0] is None:
            continue
        out[soc6(row[0])] = float(row[2])
    return out


def load_employment(path):
    import pandas as pd
    df = pd.read_parquet(path)
    df = df[df["tot_emp"].notna()]
    return dict(zip(df["occ_code"].astype(str).map(soc6), df["tot_emp"].astype(float)))


def build(dn_path, el_path, aioe_path, oews_path, quantile_cut=0.5):
    dn, dn_n = load_dingel_neiman(dn_path)
    el = load_eloundou(el_path)
    aioe = load_aioe(aioe_path)
    emp = load_employment(oews_path)

    measures = {"AIOE_Felten": {k: v for k, v in aioe.items()}}
    for m in ELOUNDOU_MEASURES:
        measures[f"Eloundou_{m}"] = {k: d[m] for k, d in el.items() if m in d}

    results = {}
    for name, series in measures.items():
        keys = sorted(set(series) & set(dn))
        pairs = [(series[k], dn[k]) for k in keys]
        wkeys = [k for k in keys if k in emp]
        wpairs = [(series[k], dn[k]) for k in wkeys]
        w = [emp[k] for k in wkeys]

        # Off-diagonal mass. Each measure is split at its own employment-
        # weighted median so cells are comparable across measures on different
        # scales -- but note what that means for telework: 62.7% of SOC codes
        # have a teleworkable share of exactly zero, so its weighted median IS
        # zero and the "high" cell is really "any teleworkable detail code at
        # all". That is a defensible cut, but it is not a median split and the
        # receipt says so rather than implying a symmetric comparison.
        # The correlation and R2 do not depend on any cut and are the
        # statistics to lead with.
        def wmedian(vals, wts):
            order = sorted(zip(vals, wts))
            tot = sum(wts)
            run = 0.0
            for v, ww in order:
                run += ww
                if run >= tot / 2:
                    return v
            return order[-1][0] if order else None

        ai_vals = [series[k] for k in wkeys]
        dn_vals = [dn[k] for k in wkeys]
        ai_cut = wmedian(ai_vals, w)
        dn_cut = wmedian(dn_vals, w)

        cells = defaultdict(lambda: {"n": 0, "emp": 0.0})
        for k, ww in zip(wkeys, w):
            hi_ai = series[k] > ai_cut
            hi_dn = dn[k] > dn_cut
            cell = f"{'highAI' if hi_ai else 'lowAI'}_{'highRemote' if hi_dn else 'lowRemote'}"
            cells[cell]["n"] += 1
            cells[cell]["emp"] += ww
        total_emp = sum(w)
        for c in cells:
            cells[c]["emp_share"] = cells[c]["emp"] / total_emp if total_emp else None

        off = sum(cells[c]["emp"] for c in
                  ("highAI_lowRemote", "lowAI_highRemote") if c in cells)

        r_unw = _corr(pairs)
        r_w = _corr(wpairs, w)
        results[name] = {
            "occupations_matched": len(keys),
            "occupations_with_employment": len(wkeys),
            "employment_covered": total_emp,
            "corr_unweighted": r_unw,
            "corr_employment_weighted": r_w,
            "r2_employment_weighted": (r_w ** 2) if r_w is not None else None,
            "cut_points": {
                "ai_cut": ai_cut, "remote_cut": dn_cut,
                "cut_rule": "employment-weighted median of each measure",
                "caveat": (
                    "the telework cut is degenerate: its weighted median is "
                    "zero because most employment is in occupations with no "
                    "teleworkable detail code, so 'highRemote' means "
                    "share > 0, not above-median. Read corr/R2, not the cells, "
                    "as the headline."),
            },
            "cells": {c: dict(v) for c, v in sorted(cells.items())},
            "off_diagonal_employment_share": (off / total_emp) if total_emp else None,
        }

    def _describe(vals):
        vals = sorted(vals)
        if not vals:
            return None
        q = lambda p: vals[min(int(p * (len(vals) - 1) + 0.5), len(vals) - 1)]
        n = len(vals)
        mean = sum(vals) / n
        sd = (sum((v - mean) ** 2 for v in vals) / n) ** 0.5
        return {"n": n, "zeros": sum(1 for v in vals if v == 0),
                "zero_share": sum(1 for v in vals if v == 0) / n,
                "min": vals[0], "p25": q(0.25), "median": q(0.50),
                "p75": q(0.75), "max": vals[-1], "sd": sd}

    distributions = {"teleworkable_share": _describe(list(dn.values()))}
    for name, series in measures.items():
        distributions[name] = _describe(list(series.values()))

    return {
        "record_version": "dax-ai-telework-overlap-v1",
        "distributions": distributions,
        "question": (
            "Are AI exposure and remote-work feasibility separately identified "
            "in occupation-level data?"),
        "why_it_matters": (
            "Emanuel, Harrington & Pallais attribute 64% of the rise in young "
            "college-graduate unemployment to remote work. Brynjolfsson, "
            "Chandar & Chen control for interest-rate exposure but not "
            "telework. If the two measures overlap heavily, the attribution in "
            "that literature is not identified from occupation-level data."),
        "how_to_read": (
            "corr_employment_weighted says how alike the measures are. "
            "off_diagonal_employment_share says how much employment sits in "
            "occupations where they DISAGREE -- that is the variation any "
            "decomposition is identified from. A high correlation with a thick "
            "off-diagonal is workable; a moderate correlation whose divergent "
            "cells hold little employment is not."),
        "inputs": {
            "dingel_neiman": str(dn_path), "eloundou": str(el_path),
            "aioe_felten": str(aioe_path), "employment_weights": str(oews_path),
        },
        "note_on_dingel_neiman": (
            "teleworkable is published as a binary at O*NET-SOC detail level; "
            "collapsed here to the share of an occupation's detail codes that "
            "are teleworkable, which is what the 6-digit SOC merge requires."),
        "measures": results,
    }


def main(argv=None):
    here = pathlib.Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dingel-neiman", type=pathlib.Path, required=True)
    ap.add_argument("--eloundou", type=pathlib.Path, required=True)
    ap.add_argument("--aioe", type=pathlib.Path, required=True)
    ap.add_argument("--oews", type=pathlib.Path,
                    default=pathlib.Path("dax/data_built/oews_wages.parquet"))
    ap.add_argument("--output", type=pathlib.Path,
                    default=here / "ai_telework_overlap_receipt.json")
    args = ap.parse_args(argv)

    for p in (args.dingel_neiman, args.eloundou, args.aioe, args.oews):
        if not p.is_file():
            print(f"NEED_HUMAN: missing input {p}", file=sys.stderr)
            return 2

    rec = build(args.dingel_neiman, args.eloundou, args.aioe, args.oews)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")

    print(f"wrote {args.output}\n")
    hdr = f"{'measure':<28} {'n':>5} {'r(unw)':>8} {'r(emp)':>8} {'R2':>7} {'off-diag emp':>13}"
    print(hdr); print("-" * len(hdr))
    for name, r in rec["measures"].items():
        ru = r["corr_unweighted"]; rw = r["corr_employment_weighted"]
        r2 = r["r2_employment_weighted"]; od = r["off_diagonal_employment_share"]
        print(f"{name:<28} {r['occupations_with_employment']:>5} "
              f"{ru if ru is None else f'{ru:8.4f}'} "
              f"{rw if rw is None else f'{rw:8.4f}'} "
              f"{r2 if r2 is None else f'{r2:7.4f}'} "
              f"{od if od is None else f'{od:12.1%}'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
