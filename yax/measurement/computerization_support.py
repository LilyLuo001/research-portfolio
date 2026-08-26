#!/usr/bin/env python3
"""Is AI exposure separable from computer-based work, cross-sectionally?

The advisor's question: is the AI-exposure gradient partly a computerization
gradient? AIOE is built by mapping AI capability benchmarks onto O*NET
ABILITIES -- comprehension, deductive reasoning, information ordering -- which
are the same items that load on routine-cognitive and computerization measures.
The measure was not constructed to separate the two.

Whether a horse-race regression can separate them is not a modelling question,
it is a question about the joint distribution: **is there employment in
occupations that are AI-exposed but NOT computer-desk work?** If that cell is
empty, adding a computerization control produces collinear noise, not
identification, and the honest thing is to say so rather than report an
uninformative coefficient.

This script measures that cell before the design freeze, so the answer is known
in advance rather than discovered in a referee report.

**Dingel-Neiman teleworkability is a PROXY here, not the construct.**
Teleworkable is close to "can be done at a computer away from the workplace".
It is not routine-task intensity and it is not Frey-Osborne computerisability.
It is what is available in-repo today. Webb (2020), Frey-Osborne (2017) and a
constructed RTI are the real measures and this check must be re-run against
them -- see yax/briefs/Y1b_computerization.md. Read this as a lower bound on
how bad the collinearity is, not as the final word.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ai_vs_telework_overlap import (  # noqa: E402
    ELOUNDOU_MEASURES, load_aioe, load_dingel_neiman, load_eloundou)
from audit_common_support import (  # noqa: E402
    load_employment_titled, wquantile, wcorr, kish_n)

# The cell that identifies an AI effect net of computerization: high exposure,
# no computer-desk character. Cut the exposure at its employment-weighted 75th
# percentile; "low computer" is teleworkable == 0, which is the only defensible
# cut given 62.7% of SOC codes sit at exactly zero (see AUDIT_RESULTS item 7).
EXPOSURE_QUANTILE = 0.75
CLEAN_CELL_FLOOR = 0.05   # below this share of employment, the horse race is dead


def analyse(series, dn, emp, title, name, top_k=12):
    ks = [k for k in series if k in dn and k in emp]
    if len(ks) < 20:
        return {"status": "insufficient", "n": len(ks)}
    w = [emp[k] for k in ks]
    tot = sum(w)
    cut = wquantile([series[k] for k in ks], w, EXPOSURE_QUANTILE)

    hi = [k for k in ks if series[k] > cut]
    clean = [k for k in hi if dn[k] == 0.0]        # AI-exposed, not desk work
    confounded = [k for k in hi if dn[k] > 0.0]
    e_hi = sum(emp[k] for k in hi)
    e_clean = sum(emp[k] for k in clean)

    def named(codes):
        return [{"soc": k, "occupation": title.get(k, k), "employment": emp[k],
                 "exposure": series[k], "teleworkable_share": dn[k]}
                for k in sorted(codes, key=lambda k: -emp[k])[:top_k]]

    r = wcorr([series[k] for k in ks], [dn[k] for k in ks], w)
    clean_share = e_clean / tot if tot else None
    return {
        "n_occupations": len(ks),
        "employment": tot,
        "correlation_with_computer_proxy": r,
        "r2": (r ** 2) if r is not None else None,
        "exposure_cut": cut,
        "exposure_cut_rule": f"employment-weighted p{int(EXPOSURE_QUANTILE*100)}",
        "high_exposure": {"n": len(hi), "employment": e_hi,
                          "employment_share": e_hi / tot if tot else None},
        "clean_cell_high_ai_low_computer": {
            "n": len(clean), "employment": e_clean,
            "employment_share_of_all": clean_share,
            "employment_share_of_high_exposure": (e_clean / e_hi) if e_hi else None,
            "kish_effective_n": kish_n([emp[k] for k in clean]) if clean else None,
            "largest": named(clean),
        },
        "confounded_cell_high_ai_high_computer": {
            "n": len(confounded),
            "employment": e_hi - e_clean,
            "largest": named(confounded),
        },
        "verdict": (
            "SEPARABLE" if clean_share and clean_share >= CLEAN_CELL_FLOOR
            else "NOT SEPARABLE"),
        "verdict_note": (
            f"the clean cell holds {clean_share:.2%} of employment against a "
            f"{CLEAN_CELL_FLOOR:.0%} floor. Below the floor, a regression "
            f"entering AI exposure and a computerization measure together is "
            f"not identified off meaningful variation, and reporting its "
            f"coefficients as a decomposition would overstate what the data "
            f"supports." if clean_share is not None else ""),
    }


def build(dn_path, el_path, aioe_path, oews_path):
    dn, _ = load_dingel_neiman(dn_path)
    el = load_eloundou(el_path)
    emp, title = load_employment_titled(oews_path)
    measures = {"AIOE_Felten": load_aioe(aioe_path)}
    for m in ELOUNDOU_MEASURES:
        measures[f"Eloundou_{m}"] = {k: d[m] for k, d in el.items() if m in d}

    return {
        "record_version": "yax-computerization-support-v1",
        "question": ("Is there employment in occupations that are AI-exposed "
                     "but not computer-desk work? That cell is what a horse "
                     "race between AI exposure and computerization is "
                     "identified from."),
        "proxy_warning": (
            "Dingel-Neiman teleworkability stands in for computer-based work. "
            "It is NOT routine-task intensity and NOT Frey-Osborne "
            "computerisability. Re-run against Webb (2020), Frey-Osborne and a "
            "constructed RTI before the design freeze."),
        "inputs": {"dingel_neiman": str(dn_path), "eloundou": str(el_path),
                   "aioe_felten": str(aioe_path), "employment": str(oews_path)},
        "clean_cell_floor": CLEAN_CELL_FLOOR,
        "measures": {n: analyse(s, dn, emp, title, n) for n, s in measures.items()},
    }


def main(argv=None):
    here = pathlib.Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dingel-neiman", type=pathlib.Path, default=here / "dingel_neiman_occ.csv")
    ap.add_argument("--eloundou", type=pathlib.Path, default=here / "eloundou_occ.csv")
    ap.add_argument("--aioe", type=pathlib.Path, default=here / "AIOE_DataAppendix.xlsx")
    ap.add_argument("--oews", type=pathlib.Path,
                    default=pathlib.Path("dax/data_built/oews_wages.parquet"))
    ap.add_argument("--output", type=pathlib.Path,
                    default=here / "computerization_support_receipt.json")
    args = ap.parse_args(argv)

    for p in (args.dingel_neiman, args.eloundou, args.aioe, args.oews):
        if not p.is_file():
            print(f"NEED_HUMAN: missing input {p}", file=sys.stderr)
            return 2

    rec = build(args.dingel_neiman, args.eloundou, args.aioe, args.oews)
    args.output.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}\n")

    hdr = f"{'measure':<30} {'r':>7} {'R2':>7} {'clean cell emp':>15} {'verdict':>15}"
    print(hdr); print("-" * len(hdr))
    for n, m in rec["measures"].items():
        if m.get("status") == "insufficient":
            continue
        c = m["clean_cell_high_ai_low_computer"]
        print(f"{n:<30} {m['correlation_with_computer_proxy']:>7.4f} {m['r2']:>7.4f} "
              f"{c['employment_share_of_all']:>14.2%} {m['verdict']:>15}")
    print("\nClean cell = exposure above its employment-weighted p75 AND zero "
          "teleworkable detail codes.\nProxy only — see the module docstring.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
