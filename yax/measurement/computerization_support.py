#!/usr/bin/env python3
"""Is AI exposure separable from computer-based work, cross-sectionally?

The advisor's question: is the AI-exposure gradient partly a computerization
gradient? AIOE is built by mapping AI capability benchmarks onto O*NET
ABILITIES -- comprehension, deductive reasoning, information ordering -- which
are the same items that load on routine-cognitive and computerization measures.
The measure was not constructed to separate the two.

Whether a horse race can separate them is a question about the joint
distribution. **The right statistic is the partial variance of AI exposure
after projecting out computerization** -- 1 - R^2 -- because a continuous
conditional model is identified off all of that residual variation.

A discretized "clean cell" (high AI, low computerization) is NOT the right
statistic and an earlier version of this script led with it. Cutting a
continuous regressor into a 2x2 discards most of the identifying variation and
understates what the model can do: Eloundou beta's clean cell holds 3.22% of
employment while 57.9% of its variance is orthogonal to the computer proxy.
Those describe different things and only the second bears on identification.
The cell share is retained below as a descriptive aid and as the source of the
named divergence occupations, which are genuinely useful for presentation.
See CORRECTION_2026-08-26_separability_verdict.md.

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
import math
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
# SE inflation from adding a collinear regressor is sqrt(VIF) = sqrt(1/(1-R^2)).
# Judge identification against the magnitude the literature contests, not
# against an abstract threshold.
UNCONDITIONAL_MDE_LOG = 0.035   # measured, 999 reps, 490 clusters, 66 months
NULL_SIZE_CORRECTION = 1.0742   # engine rejects at 6.8068% against nominal 5%
CONTESTED_MAGNITUDE = 0.19      # the effect size the literature disputes


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
    R2 = (r ** 2) if r is not None else None
    vif = (1.0 / (1.0 - R2)) if R2 is not None and R2 < 1 else None
    infl = math.sqrt(vif) if vif else None
    cond_mde = (1 - math.exp(-UNCONDITIONAL_MDE_LOG * infl * NULL_SIZE_CORRECTION)
                if infl else None)
    return {
        "n_occupations": len(ks),
        "employment": tot,
        "correlation_with_computer_proxy": r,
        "r2": R2,
        "identification": {
            "partial_variance_of_ai": (1 - R2) if R2 is not None else None,
            "vif": vif,
            "se_inflation": infl,
            "conditional_mde80_estimate": cond_mde,
            "contested_magnitude": CONTESTED_MAGNITUDE,
            "headroom": (CONTESTED_MAGNITUDE / cond_mde) if cond_mde else None,
            "note": ("This is the statistic that bears on whether a joint "
                     "AI-plus-computerization model is identified. The "
                     "conditional MDE is the measured unconditional MDE "
                     "inflated by sqrt(VIF) and the null-size correction; it is "
                     "an ESTIMATE and must be replaced by a simulation on the "
                     "observed joint distribution before the freeze."),
        },
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
        "verdict_note": (
            f"{(1-R2):.1%} of this measure's employment-weighted variance is "
            f"orthogonal to the computer proxy; adding the control inflates the "
            f"standard error by {infl:.2f}x, putting the conditional MDE near "
            f"{cond_mde:.2%} against a contested magnitude of "
            f"{CONTESTED_MAGNITUDE:.0%} -- headroom of "
            f"{CONTESTED_MAGNITUDE/cond_mde:.1f}x. The discretized clean cell "
            f"({clean_share:.2%} of employment) is a descriptive aid, not the "
            f"identification statistic."
            if (R2 is not None and cond_mde) else ""),
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
        "unconditional_mde80_log": UNCONDITIONAL_MDE_LOG,
        "contested_magnitude": CONTESTED_MAGNITUDE,
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

    hdr = (f"{'measure':<30} {'R2':>7} {'partial var':>12} {'VIF':>6} "
           f"{'SE infl':>8} {'cond MDE':>9} {'headroom':>9} {'cell':>7}")
    print(hdr); print("-" * len(hdr))
    for n, m in rec["measures"].items():
        if m.get("status") == "insufficient":
            continue
        i = m["identification"]
        c = m["clean_cell_high_ai_low_computer"]
        print(f"{n:<30} {m['r2']:>7.4f} {i['partial_variance_of_ai']:>11.1%} "
              f"{i['vif']:>6.2f} {i['se_inflation']:>7.2f}x "
              f"{i['conditional_mde80_estimate']:>8.2%} {i['headroom']:>8.1f}x "
              f"{c['employment_share_of_all']:>6.2%}")
    print("\nPartial variance is the identification statistic. The clean cell is "
          "descriptive.\nConditional MDE is an ESTIMATE pending a joint-distribution "
          "simulation.\nComputer proxy = teleworkability — see the module docstring.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
