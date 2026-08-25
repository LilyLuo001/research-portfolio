#!/usr/bin/env python3
"""Common-support and robustness audit of the AI-vs-telework separability gate.

`ai_vs_telework_overlap.py` reported employment-weighted correlations between
four AI-exposure measures and Dingel-Neiman teleworkability. It established
that the correlations differ across measures. It established nothing about
whether the residual variation those correlations leave behind is *usable* --
whether it is spread across ordinary occupations or concentrated in a handful
of peculiar ones, whether it survives dropping a single occupational family,
and whether the measures were even compared on the same set of occupations.

This script answers those questions and only those questions. It reports
measurement properties. It makes no employment claim, no identification claim,
and no novelty claim, and it does not select a measure -- see AUDIT_SPEC.md
"Decision rule, fixed now".

Items implemented (AUDIT_SPEC.md numbering):

  1  weighted and unweighted Pearson AND Spearman
  2  alternative OEWS weight years -- BLOCKED, see item2_blocked below
  3  SOC crosswalk coverage, many-to-one collapsing, unmatched employment
  4  correlations within 2-digit major groups, with Kish effective n and
     within-group residual variance
  5  leave-one-major-group-out
  6  residualised distributions, residual-variance concentration, and the
     named occupations supplying the residual variation
  7  quartile contrast among occupations with positive teleworkability

  plus  SOC-vintage sensitivity: every measure re-run on the identical
        common sample, because the headline gate did not do this.

Items 8-10 (CPS power, Webb/Frey-Osborne, novelty verification) are out of
scope here and remain open in AUDIT_SPEC.md.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
from collections import defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ai_vs_telework_overlap import (  # noqa: E402
    ELOUNDOU_MEASURES, soc6, load_dingel_neiman, load_eloundou, load_aioe,
)

MIN_GROUP_N = 8   # 2-digit groups smaller than this are reported, not correlated


# ---------------------------------------------------------------- statistics

def _wsum(w):
    return sum(w)


def wmean(x, w):
    sw = _wsum(w)
    return sum(wi * xi for wi, xi in zip(w, x)) / sw if sw > 0 else None


def wcorr(x, y, w=None):
    """Weighted Pearson. None when either margin has no weighted variance."""
    if len(x) < 3:
        return None
    w = [1.0] * len(x) if w is None else w
    sw = _wsum(w)
    if sw <= 0:
        return None
    mx, my = wmean(x, w), wmean(y, w)
    sxx = sum(wi * (xi - mx) ** 2 for wi, xi in zip(w, x))
    syy = sum(wi * (yi - my) ** 2 for wi, yi in zip(w, y))
    sxy = sum(wi * (xi - mx) * (yi - my) for wi, xi, yi in zip(w, x, y))
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def ranks(vals):
    """Average ranks, ties shared."""
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    out = [0.0] * len(vals)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            out[order[k]] = avg
        i = j + 1
    return out


def wspearman(x, y, w=None):
    """Spearman as weighted Pearson on UNWEIGHTED average ranks.

    Weighted ranks have no single accepted definition; ranking without weights
    and then weighting the correlation keeps the rank transform unambiguous.
    The receipt records this choice so the number is not read as something it
    is not.
    """
    return wcorr(ranks(x), ranks(y), w)


def kish_n(w):
    """Effective sample size under unequal weights: (sum w)^2 / sum w^2."""
    s1 = sum(w)
    s2 = sum(wi * wi for wi in w)
    return (s1 * s1 / s2) if s2 > 0 else None


def wols(y, x, w):
    """Weighted OLS of y on x with intercept. Returns (a, b, residuals)."""
    mx, my = wmean(x, w), wmean(y, w)
    sxx = sum(wi * (xi - mx) ** 2 for wi, xi in zip(w, x))
    if sxx <= 0:
        return None, None, None
    sxy = sum(wi * (xi - mx) * (yi - my) for wi, xi, yi in zip(w, x, y))
    b = sxy / sxx
    a = my - b * mx
    return a, b, [yi - a - b * xi for xi, yi in zip(x, y)]


def describe(vals, w=None):
    if not vals:
        return None
    s = sorted(vals)
    n = len(s)
    q = lambda p: s[min(int(p * (n - 1) + 0.5), n - 1)]  # noqa: E731
    m = wmean(vals, w) if w else sum(vals) / n
    if w:
        sd = math.sqrt(sum(wi * (v - m) ** 2 for wi, v in zip(w, vals)) / sum(w))
    else:
        sd = math.sqrt(sum((v - m) ** 2 for v in vals) / n)
    return {"n": n, "mean": m, "sd": sd, "min": s[0], "p10": q(0.10),
            "p25": q(0.25), "median": q(0.50), "p75": q(0.75), "p90": q(0.90),
            "max": s[-1]}


def wquantile(vals, w, p):
    order = sorted(zip(vals, w))
    tot = sum(w)
    run = 0.0
    for v, wi in order:
        run += wi
        if run >= tot * p:
            return v
    return order[-1][0] if order else None


# ---------------------------------------------------------------- data load

def load_employment_titled(path):
    import pandas as pd
    df = pd.read_parquet(path)
    df = df[df["tot_emp"].notna()].copy()
    df["occ_code"] = df["occ_code"].astype(str).map(soc6)
    emp = dict(zip(df["occ_code"], df["tot_emp"].astype(float)))
    title = dict(zip(df["occ_code"], df["occ_title"].astype(str)))
    return emp, title


def source_titles(dn_path, el_path, aioe_path):
    """Occupation names as each SOURCE spells them, for codes OEWS lacks."""
    import csv
    out = {}
    with open(aioe_path, "rb"):
        pass
    import openpyxl
    ws = openpyxl.load_workbook(aioe_path, read_only=True)["Appendix A"]
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i and row[0] is not None:
            out.setdefault(soc6(row[0]), str(row[1]))
    for path, code_col, title_col in ((dn_path, "onetsoccode", "title"),
                                      (el_path, "O*NET-SOC Code", "Title")):
        with open(path, newline="", encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                out.setdefault(soc6(row[code_col]), str(row[title_col]))
    return out


def detail_code_counts(dn_path, el_path):
    """How many O*NET-SOC detail codes collapse into each 6-digit SOC, and how
    much the collapsed values disagree within a SOC."""
    import csv
    counts = {"dingel_neiman": defaultdict(list), "eloundou_alpha": defaultdict(list)}
    with open(dn_path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            v = (row.get("teleworkable") or "").strip()
            if v != "":
                counts["dingel_neiman"][soc6(row["onetsoccode"])].append(float(v))
    with open(el_path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            v = (row.get("dv_rating_alpha") or "").strip()
            if v != "":
                counts["eloundou_alpha"][soc6(row["O*NET-SOC Code"])].append(float(v))
    out = {}
    for name, d in counts.items():
        hist = defaultdict(int)
        disagree = 0
        spreads = []
        for k, vs in d.items():
            hist[len(vs)] += 1
            if len(vs) > 1:
                sp = max(vs) - min(vs)
                spreads.append(sp)
                if sp > 0:
                    disagree += 1
        out[name] = {
            "six_digit_socs": len(d),
            "detail_rows": sum(len(v) for v in d.values()),
            "detail_codes_per_soc": {str(k): v for k, v in sorted(hist.items())},
            "socs_with_multiple_detail_codes": sum(1 for v in d.values() if len(v) > 1),
            "socs_where_detail_codes_disagree": disagree,
            "within_soc_spread_when_multiple": describe(spreads) if spreads else None,
            "aggregation_rule": "unweighted mean across the SOC's detail codes",
            "note": ("O*NET publishes no employment counts below the 6-digit "
                     "SOC, so the collapse cannot be employment-weighted. Where "
                     "detail codes disagree, the collapsed value is a within-SOC "
                     "average and its dispersion is measurement the audit cannot "
                     "recover."),
        }
    return out


# ---------------------------------------------------------------- the audit

def measure_table(dn, series, emp, keys):
    """Item 1 on one sample: Pearson and Spearman, weighted and unweighted."""
    keys = [k for k in keys if k in series and k in dn]
    if len(keys) < 3:
        return None
    x = [series[k] for k in keys]
    y = [dn[k] for k in keys]
    wk = [k for k in keys if k in emp]
    xw = [series[k] for k in wk]
    yw = [dn[k] for k in wk]
    w = [emp[k] for k in wk]
    r_w = wcorr(xw, yw, w)
    return {
        "n_occupations": len(keys),
        "n_with_employment": len(wk),
        "employment_covered": sum(w),
        "kish_effective_n": kish_n(w),
        "pearson_unweighted": wcorr(x, y),
        "pearson_employment_weighted": r_w,
        "spearman_unweighted": wspearman(x, y),
        "spearman_employment_weighted": wspearman(xw, yw, w),
        "r2_employment_weighted": (r_w ** 2) if r_w is not None else None,
        "vif_if_both_entered": (1.0 / (1.0 - r_w ** 2)) if r_w is not None and abs(r_w) < 1 else None,
    }


def within_group(dn, series, emp, title, keys):
    """Item 4 + the user's effective-sample-size and within-group-variance ask."""
    groups = defaultdict(list)
    for k in keys:
        if k in series and k in dn and k in emp:
            groups[k[:2]].append(k)
    out = {}
    for g, ks in sorted(groups.items()):
        x = [series[k] for k in ks]
        y = [dn[k] for k in ks]
        w = [emp[k] for k in ks]
        anchor = max(ks, key=lambda k: emp[k])
        rec = {
            "n_occupations": len(ks),
            "employment": sum(w),
            "kish_effective_n": kish_n(w),
            "largest_occupation": title.get(anchor, anchor),
            "correlated": len(ks) >= MIN_GROUP_N,
        }
        tw_distinct = len({round(v, 6) for v in y})
        rec["distinct_telework_values_in_group"] = tw_distinct
        rec["telework_constant_within_group"] = tw_distinct == 1
        if tw_distinct == 1:
            rec["not_correlated_reason"] = (
                "every occupation in this group has the same teleworkable "
                "share, so there is no within-group variation to correlate "
                "against")
            rec["correlated"] = False
        elif len(ks) < MIN_GROUP_N:
            rec["not_correlated_reason"] = (
                f"fewer than {MIN_GROUP_N} matched occupations")
        if rec["correlated"]:
            r = wcorr(x, y, w)
            rec["pearson_employment_weighted"] = r
            rec["spearman_employment_weighted"] = wspearman(x, y, w)
            rec["r2_employment_weighted"] = (r ** 2) if r is not None else None
            _, _, res = wols(x, y, w)
            tot_var = sum(wi * (xi - wmean(x, w)) ** 2 for wi, xi in zip(w, x)) / sum(w)
            rec["measure_variance_within_group"] = tot_var
            if res is not None:
                rec["residual_variance_within_group"] = (
                    sum(wi * ri ** 2 for wi, ri in zip(w, res)) / sum(w))
        out[g] = rec
    return out


def leave_one_out(dn, series, emp, keys):
    """Item 5."""
    ks = [k for k in keys if k in series and k in dn and k in emp]
    base = wcorr([series[k] for k in ks], [dn[k] for k in ks], [emp[k] for k in ks])
    base_r2 = base ** 2 if base is not None else None
    out = {"full_sample_r2": base_r2, "dropped": {}}
    groups = sorted({k[:2] for k in ks})
    for g in groups:
        sub = [k for k in ks if k[:2] != g]
        r = wcorr([series[k] for k in sub], [dn[k] for k in sub], [emp[k] for k in sub])
        r2 = r ** 2 if r is not None else None
        out["dropped"][g] = {
            "r2_employment_weighted": r2,
            "delta_vs_full": (r2 - base_r2) if (r2 is not None and base_r2 is not None) else None,
            "n_dropped": len(ks) - len(sub),
        }
    deltas = {g: v["delta_vs_full"] for g, v in out["dropped"].items()
              if v["delta_vs_full"] is not None}
    if deltas:
        worst = max(deltas, key=lambda g: abs(deltas[g]))
        out["most_influential_major_group"] = worst
        out["largest_absolute_r2_shift"] = abs(deltas[worst])
    return out


def residual_structure(dn, series, emp, title, keys, top_k=25):
    """Item 6. The decisive one: WHERE does the residual variation live?"""
    ks = [k for k in keys if k in series and k in dn and k in emp]
    if len(ks) < 10:
        return None
    x = [dn[k] for k in ks]          # regressor: teleworkability
    y = [series[k] for k in ks]      # regressand: AI exposure
    w = [emp[k] for k in ks]
    a, b, res = wols(y, x, w)
    if res is None:
        return None
    sw = sum(w)
    contrib = [(wi * ri * ri) for wi, ri in zip(w, res)]
    tot = sum(contrib)
    idx = sorted(range(len(ks)), key=lambda i: -contrib[i])
    shares = [contrib[i] / tot for i in idx] if tot > 0 else []
    cum = []
    run = 0.0
    for s in shares:
        run += s
        cum.append(run)
    hhi = sum(s * s for s in shares)

    def named(order, key):
        return [{"soc": ks[i], "occupation": title.get(ks[i], ks[i]),
                 "teleworkable_share": dn[ks[i]], "measure": series[ks[i]],
                 "residual": res[i], "employment": emp[ks[i]],
                 "share_of_weighted_residual_variance": (contrib[i] / tot) if tot > 0 else None}
                for i in order[:key]]

    by_resid = sorted(range(len(ks)), key=lambda i: -res[i])
    return {
        "regression": {"form": "measure = a + b * teleworkable_share + e, "
                               "weighted by OEWS 2021 employment",
                       "intercept": a, "slope": b},
        "residual_distribution_unweighted": describe(res),
        "residual_distribution_employment_weighted_moments": {
            "mean": wmean(res, w),
            "sd": math.sqrt(sum(wi * ri ** 2 for wi, ri in zip(w, res)) / sw),
        },
        "concentration_of_weighted_residual_variance": {
            "top_10_occupations_share": cum[9] if len(cum) > 9 else None,
            "top_25_occupations_share": cum[24] if len(cum) > 24 else None,
            "top_50_occupations_share": cum[49] if len(cum) > 49 else None,
            "occupations_to_reach_half": next((i + 1 for i, c in enumerate(cum) if c >= 0.5), None),
            "herfindahl": hhi,
            "effective_number_of_occupations": (1.0 / hhi) if hhi > 0 else None,
            "n_occupations": len(ks),
            "how_to_read": ("each occupation's weighted squared residual as a "
                            "share of the total. A small effective number means "
                            "the variation left after removing teleworkability "
                            "sits in few occupations."),
        },
        "largest_positive_residuals": named(by_resid, top_k),
        "largest_negative_residuals": named(by_resid[::-1], top_k),
        "largest_contributors_to_residual_variance": named(idx, top_k),
    }


def positive_telework_contrast(dn, series, emp, title, keys):
    """Item 7. 62.7% of SOC codes sit at exactly zero teleworkability, so the
    full-sample split is >0 vs =0. AUDIT_SPEC.md asked for quartiles among the
    positive occupations instead.

    Those quartiles do not exist. The collapsed teleworkable share is a mean of
    binary detail-code flags, and almost every occupation with any teleworkable
    detail code has ALL of them teleworkable, so the positive subsample piles up
    at exactly 1.0. This function measures that pile-up, refuses to emit
    quartiles when they are degenerate, and reports the contrast that the data
    actually supports: fully teleworkable versus partially teleworkable.
    """
    ks = [k for k in keys if k in series and k in dn and k in emp and dn[k] > 0]
    if len(ks) < 20:
        return {"status": "insufficient", "n": len(ks)}
    x = [dn[k] for k in ks]
    y = [series[k] for k in ks]
    w = [emp[k] for k in ks]
    tot_emp = sum(w)

    at_one_n = sum(1 for v in x if v >= 1.0)
    at_one_emp = sum(wi for wi, v in zip(w, x) if v >= 1.0)
    distinct = len({round(v, 6) for v in x})
    cuts = [wquantile(x, w, p) for p in (0.25, 0.50, 0.75)]
    degenerate = len({round(c, 6) for c in cuts if c is not None}) < 3

    out = {
        "n_occupations_positive_telework": len(ks),
        "employment": tot_emp,
        "kish_effective_n": kish_n(w),
        "distribution_among_positive": {
            "distinct_values": distinct,
            "n_at_exactly_1.0": at_one_n,
            "share_of_occupations_at_1.0": at_one_n / len(ks),
            "employment_share_at_1.0": at_one_emp / tot_emp if tot_emp else None,
            "describe": describe(x, w),
        },
        "quartile_cuts_attempted": cuts,
        "quartiles_degenerate": degenerate,
    }
    if degenerate:
        out["quartiles"] = None
        out["why_no_quartiles"] = (
            "The employment-weighted 25th, 50th and 75th percentiles of the "
            "teleworkable share among positive occupations are not distinct, "
            "because the collapsed share is an average of binary detail-code "
            "flags and most occupations have every detail code teleworkable. "
            "Emitting quartiles here would be a table of one populated cell. "
            "The fully-versus-partially contrast below is what the data "
            "supports.")
        cells = {"fully_teleworkable_share_eq_1": [k for k in ks if dn[k] >= 1.0],
                 "partially_teleworkable_0_lt_share_lt_1": [k for k in ks if dn[k] < 1.0]}
        out["fully_vs_partially"] = {
            name: {
                "n_occupations": len(cks),
                "employment": sum(emp[k] for k in cks),
                "employment_share_of_positive_telework": (
                    sum(emp[k] for k in cks) / tot_emp if tot_emp else None),
                "mean_measure_employment_weighted": (
                    wmean([series[k] for k in cks], [emp[k] for k in cks]) if cks else None),
                "mean_measure_unweighted": (
                    sum(series[k] for k in cks) / len(cks) if cks else None),
                "largest_occupations": [
                    {"soc": k, "occupation": title.get(k, k), "employment": emp[k],
                     "measure": series[k]}
                    for k in sorted(cks, key=lambda k: -emp[k])[:5]],
            } for name, cks in cells.items()}
    else:
        buckets = defaultdict(lambda: {"n": 0, "emp": 0.0, "vals": [], "wts": []})
        for k in ks:
            q = 1 + sum(1 for c in cuts if dn[k] > c)
            bk = buckets[f"Q{q}"]
            bk["n"] += 1
            bk["emp"] += emp[k]
            bk["vals"].append(series[k])
            bk["wts"].append(emp[k])
        out["quartiles"] = {
            q: {"n_occupations": bk["n"], "employment": bk["emp"],
                "employment_share_of_positive_telework": bk["emp"] / tot_emp,
                "mean_measure_employment_weighted": wmean(bk["vals"], bk["wts"]),
                "mean_measure_unweighted": sum(bk["vals"]) / len(bk["vals"])}
            for q, bk in sorted(buckets.items())}

    r = wcorr(y, x, w)
    out.update({
        "pearson_employment_weighted_within_positive": r,
        "spearman_employment_weighted_within_positive": wspearman(y, x, w),
        "r2_employment_weighted_within_positive": (r ** 2) if r is not None else None,
        "caveat_on_within_positive_correlation": (
            "computed against a regressor that is almost binary within this "
            "subsample; it is not a high-versus-low gradient in teleworkability."),
    })
    return out


def coverage(dn, el, aioe, emp, title, stitle):
    """Item 3 + the SOC-vintage question the headline gate never asked."""
    sets = {"AIOE_Felten": set(aioe), "Eloundou": set(el),
            "DingelNeiman": set(dn), "OEWS_2021": set(emp)}
    tot_emp = sum(emp.values())

    def unmatched(codes, n=15):
        miss = sorted(set(emp) - codes, key=lambda k: -emp[k])
        return {
            "oews_codes_absent_from_source": len(miss),
            "employment_share_absent": sum(emp[k] for k in miss) / tot_emp,
            "largest_absent_by_employment": [
                {"soc": k, "occupation": title.get(k, k), "employment": emp[k],
                 "employment_share": emp[k] / tot_emp} for k in miss[:n]],
        }

    def orphans(codes, n=10):
        orp = sorted(codes - set(emp))
        return {"source_codes_absent_from_oews_2021": len(orp),
                "examples": [{"soc": k, "occupation": stitle.get(k, k)} for k in orp[:n]]}

    common = sets["AIOE_Felten"] & sets["Eloundou"] & sets["DingelNeiman"] & sets["OEWS_2021"]

    # Where the coverage loss lands. An economy-wide 19.65% is one number; the
    # per-group table is what tells you whether it falls on occupations the
    # study is about.
    by_group = {}
    for g in sorted({k[:2] for k in emp}):
        ks = [k for k in emp if k[:2] == g]
        matched = [k for k in ks if k in dn]
        te = sum(emp[k] for k in ks)
        me = sum(emp[k] for k in matched)
        anchor = max(ks, key=lambda k: emp[k])
        by_group[g] = {
            "oews_2021_occupations": len(ks),
            "matched_into_the_gate": len(matched),
            "oews_2021_employment": te,
            "matched_employment": me,
            "employment_share_lost": (1.0 - me / te) if te else None,
            "largest_occupation_in_group": title.get(anchor, anchor),
        }
    return {
        "codes_per_source": {k: len(v) for k, v in sets.items()},
        "pairwise_intersections": {
            f"{a}&{b}": len(sets[a] & sets[b])
            for a, b in (("AIOE_Felten", "DingelNeiman"),
                         ("Eloundou", "DingelNeiman"),
                         ("AIOE_Felten", "Eloundou"),
                         ("AIOE_Felten", "OEWS_2021"),
                         ("Eloundou", "OEWS_2021"),
                         ("DingelNeiman", "OEWS_2021"))},
        "common_sample_all_four": {
            "n": len(common),
            "employment": sum(emp[k] for k in common if k in emp),
            "employment_share_of_oews_2021": sum(emp[k] for k in common if k in emp) / tot_emp,
        },
        "employment_loss_by_major_group": by_group,
        "unmatched_against_oews_2021": {k: unmatched(v) for k, v in sets.items() if k != "OEWS_2021"},
        "source_codes_not_in_oews_2021": {k: orphans(v) for k, v in sets.items() if k != "OEWS_2021"},
        "identical_code_sets": {
            "AIOE_equals_DingelNeiman_code_set": set(aioe) == set(dn),
            "consequence": (
                "AIOE and Dingel-Neiman are published on exactly the same list "
                "of 6-digit SOC codes, and every measure in the gate is merged "
                "against Dingel-Neiman. The employment loss below therefore "
                "binds on ALL measures equally, so it does not distort the "
                "cross-measure comparison -- which is why the common-sample "
                "re-run barely moves. What it does damage is external validity: "
                "the named occupations below are outside the gate entirely."),
        },
        "soc_vintage_reading": (
            "AIOE and Dingel-Neiman are published on the SOC 2010 taxonomy; "
            "Eloundou is published on O*NET-SOC 2019 (SOC 2018), which is also "
            "the OEWS 2021 taxonomy. The unmatched counts and employment shares "
            "above are the direct evidence: read them, do not take this sentence "
            "on faith. A consequence is that the headline gate did not compare "
            "the measures on the same occupations -- hence the common-sample "
            "re-run reported under 'soc_vintage_sensitivity'."),
        "repair_status": (
            "BLOCKED in this environment: mapping SOC 2010 to SOC 2018 requires "
            "the official BLS/Census crosswalk, and bls.gov and census.gov are "
            "unreachable from this session (proxy CONNECT returns 403). The "
            "audit therefore reports the loss rather than repairing it."),
    }


def build(dn_path, el_path, aioe_path, oews_path):
    dn, _dn_n = load_dingel_neiman(dn_path)
    el = load_eloundou(el_path)
    aioe = load_aioe(aioe_path)
    emp, title = load_employment_titled(oews_path)
    stitle = source_titles(dn_path, el_path, aioe_path)
    for k, v in stitle.items():
        title.setdefault(k, v)

    measures = {"AIOE_Felten": dict(aioe)}
    for m in ELOUNDOU_MEASURES:
        measures[f"Eloundou_{m}"] = {k: d[m] for k, d in el.items() if m in d}

    cov = coverage(dn, el, aioe, emp, title, stitle)
    common = (set(aioe) & set(el) & set(dn) & set(emp))

    per_measure = {}
    for name, series in measures.items():
        own_keys = sorted(set(series) & set(dn))
        per_measure[name] = {
            "item1_correlations_own_sample": measure_table(dn, series, emp, own_keys),
            "item4_within_major_group": within_group(dn, series, emp, title, own_keys),
            "item5_leave_one_major_group_out": leave_one_out(dn, series, emp, own_keys),
            "item6_residual_structure": residual_structure(dn, series, emp, title, own_keys),
            "item7_positive_telework_quartiles": positive_telework_contrast(
                dn, series, emp, title, own_keys),
        }

    vintage = {}
    for name, series in measures.items():
        own = per_measure[name]["item1_correlations_own_sample"]
        com = measure_table(dn, series, emp, sorted(common))
        vintage[name] = {
            "own_sample": {k: own[k] for k in
                           ("n_with_employment", "employment_covered",
                            "pearson_employment_weighted", "r2_employment_weighted")} if own else None,
            "common_sample": {k: com[k] for k in
                              ("n_with_employment", "employment_covered",
                               "pearson_employment_weighted", "r2_employment_weighted")} if com else None,
            "r2_shift_common_minus_own": (
                com["r2_employment_weighted"] - own["r2_employment_weighted"]
                if com and own and com["r2_employment_weighted"] is not None
                and own["r2_employment_weighted"] is not None else None),
        }

    return {
        "record_version": "dax-exposure-common-support-audit-v1",
        "scope": ("Measurement properties of the separability gate only. No "
                  "employment claim, no identification claim, no novelty claim, "
                  "and no measure selection."),
        "inputs": {"dingel_neiman": str(dn_path), "eloundou": str(el_path),
                   "aioe_felten": str(aioe_path), "employment_weights": str(oews_path)},
        "item2_blocked": {
            "status": "BLOCKED",
            "item": "alternative OEWS employment-weight years",
            "reason": ("OEWS files for other years are not in the repo and "
                       "bls.gov is unreachable from this session: the agent "
                       "proxy returns `CONNECT tunnel failed, response 403` for "
                       "both www.bls.gov and download.bls.gov. Only OEWS 2021 "
                       "is available locally, so the weight-year sensitivity "
                       "check cannot be run here and remains open."),
            "what_would_settle_it": ("re-run this script with --oews pointing at "
                                     "a pre-pandemic year (e.g. 2019) and a "
                                     "recent year, and compare the R2 column."),
        },
        "item3_crosswalk_coverage": cov,
        "item3_detail_code_collapsing": detail_code_counts(dn_path, el_path),
        "soc_vintage_sensitivity": {
            "common_sample_definition": ("6-digit SOC codes present in AIOE, "
                                         "Eloundou, Dingel-Neiman and OEWS 2021 "
                                         "simultaneously"),
            "common_sample_n": len(common),
            "by_measure": vintage,
            "how_to_read": ("if a measure's R2 moves materially between its own "
                            "sample and the common sample, the headline gate's "
                            "cross-measure comparison was partly a difference in "
                            "which occupations each measure covers."),
        },
        "spearman_definition": ("weighted Pearson on unweighted average ranks; "
                               "weighted ranks have no single accepted definition"),
        "by_measure": per_measure,
    }


# ---------------------------------------------------------------- reporting

def _f(v, spec="8.4f"):
    return "n/a" if v is None else format(v, spec)


def write_markdown(rec, path):
    L = []
    A = L.append
    A("# Common-support and robustness audit — results\n")
    A("Measurement properties only. No employment claim, no identification")
    A("claim, no novelty claim, and no measure is selected here.\n")
    A(f"Generated by `dax/w2/exposure_gate/audit_common_support.py`. "
      f"Machine-readable receipt: `audit_common_support_receipt.json`. "
      f"Figures in `figures/`.\n")
    A("## What the tables show\n")
    A("Descriptive statements about the measures only. Nothing here is a claim")
    A("about employment, about identification, or about novelty, and no")
    A("measure is selected.\n")
    for name in ("Eloundou_dv_rating_alpha", "AIOE_Felten"):
        m = rec["by_measure"].get(name)
        if not m:
            continue
        t = m["item1_correlations_own_sample"]
        r6 = m["item6_residual_structure"]
        l5 = m["item5_leave_one_major_group_out"]
        c = r6["concentration_of_weighted_residual_variance"]
        top = r6["largest_contributors_to_residual_variance"][0]
        g = l5.get("most_influential_major_group")
        A(f"- **{name}.** Employment-weighted R² against teleworkability is "
          f"{t['r2_employment_weighted']:.4f} across {t['n_with_employment']} "
          f"occupations, whose Kish effective n is {t['kish_effective_n']:.0f}. "
          f"The variation left after removing teleworkability is concentrated: "
          f"{c['occupations_to_reach_half']} occupations carry half of it and "
          f"the effective number of contributing occupations is "
          f"{c['effective_number_of_occupations']:.0f}. The single largest "
          f"contributor is {top['occupation']} at "
          f"{top['share_of_weighted_residual_variance']:.1%}. Dropping 2-digit "
          f"group {g} moves the R² from {l5['full_sample_r2']:.4f} to "
          f"{l5['dropped'][g]['r2_employment_weighted']:.4f}.")
    bg = rec["item3_crosswalk_coverage"]["employment_loss_by_major_group"]
    worst = max(bg, key=lambda g: bg[g]["employment_share_lost"] or 0)
    cs = rec["item3_crosswalk_coverage"]["common_sample_all_four"]
    A(f"- **Coverage.** The gate runs on {cs['n']} occupations carrying "
      f"{cs['employment_share_of_oews_2021']:.1%} of OEWS 2021 employment. The "
      f"missing fifth is not spread evenly: 2-digit group {worst} "
      f"({bg[worst]['largest_occupation_in_group']}) matches "
      f"{bg[worst]['matched_into_the_gate']} of its "
      f"{bg[worst]['oews_2021_occupations']} OEWS occupations and loses "
      f"{bg[worst]['employment_share_lost']:.1%} of its employment, because "
      f"AIOE and Dingel–Neiman are published on SOC 2010 codes that OEWS 2021 "
      f"has since split or renumbered.")
    A("")
    A("Three requested checks could not be run here and are marked as such")
    A("below rather than approximated: alternative OEWS weight years (item 2),")
    A("the SOC 2010-to-2018 crosswalk repair (item 3), and Webb and")
    A("Frey–Osborne (item 9). All three need network access this session does")
    A("not have.\n")

    A("## Item 1 — Pearson and Spearman, weighted and unweighted (own sample)\n")
    A("| measure | n | Kish n_eff | Pearson (unw) | Pearson (emp) | Spearman (unw) | Spearman (emp) | R² (emp) | VIF |")
    A("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for name, m in rec["by_measure"].items():
        t = m["item1_correlations_own_sample"]
        if not t:
            continue
        A(f"| {name} | {t['n_with_employment']} | {_f(t['kish_effective_n'],'.1f')} | "
          f"{_f(t['pearson_unweighted'],'.4f')} | {_f(t['pearson_employment_weighted'],'.4f')} | "
          f"{_f(t['spearman_unweighted'],'.4f')} | {_f(t['spearman_employment_weighted'],'.4f')} | "
          f"{_f(t['r2_employment_weighted'],'.4f')} | {_f(t['vif_if_both_entered'],'.2f')} |")
    A("")
    A("Kish effective n is `(Σw)²/Σw²`: the number of equally weighted")
    A("occupations that would carry the same information as the employment-")
    A("weighted sample. It is far below the occupation count, which is what")
    A("employment weighting does.\n")

    A("## Item 2 — alternative employment-weight years\n")
    b = rec["item2_blocked"]
    A(f"**{b['status']}.** {b['reason']}\n")

    A("## Item 3 — crosswalk coverage and SOC vintage\n")
    cov = rec["item3_crosswalk_coverage"]
    A("| source | 6-digit codes | OEWS-2021 codes it lacks | employment share lost | its codes OEWS lacks |")
    A("|---|---:|---:|---:|---:|")
    for src, n in cov["codes_per_source"].items():
        if src == "OEWS_2021":
            A(f"| {src} | {n} | — | — | — |")
            continue
        u = cov["unmatched_against_oews_2021"][src]
        o = cov["source_codes_not_in_oews_2021"][src]
        A(f"| {src} | {n} | {u['oews_codes_absent_from_source']} | "
          f"{u['employment_share_absent']:.2%} | {o['source_codes_absent_from_oews_2021']} |")
    c = cov["common_sample_all_four"]
    A("")
    A(f"Common sample across all four sources: **{c['n']} occupations**, "
      f"{c['employment_share_of_oews_2021']:.2%} of OEWS 2021 employment.\n")
    A(cov["soc_vintage_reading"] + "\n")
    A(cov["identical_code_sets"]["consequence"] + "\n")
    A(f"*Repair status:* {cov['repair_status']}\n")
    A("### Largest OEWS-2021 occupations unmatched by an exact-code merge\n")
    A("These occupations are **not absent from AIOE or Dingel–Neiman**. Both")
    A("sources cover them under their SOC 2010 codes; SOC 2018 renumbered")
    A("major group 15 almost entirely, so an exact-code merge onto the OEWS")
    A("2021 taxonomy fails to find them. Software Developers, for instance, is")
    A("15-1132 and 15-1133 in AIOE and 15-1252 in OEWS 2021. What the table")
    A("measures is the cost of merging without a crosswalk, not a gap in the")
    A("measures.\n")
    A("| SOC | occupation | employment | share |")
    A("|---|---|---:|---:|")
    for r in cov["unmatched_against_oews_2021"]["AIOE_Felten"]["largest_absent_by_employment"]:
        A(f"| {r['soc']} | {r['occupation']} | {r['employment']:,.0f} | {r['employment_share']:.2%} |")
    A("")
    A("### Where the coverage loss lands, by 2-digit major group\n")
    A("The economy-wide figure is one number; this is whether it falls on the")
    A("occupations an AI-exposure study is about. Ten worst groups.\n")
    A("| group | largest occupation in group | OEWS occs | matched | OEWS employment | employment lost |")
    A("|---|---|---:|---:|---:|---:|")
    bg = cov["employment_loss_by_major_group"]
    for g in sorted(bg, key=lambda g: -(bg[g]["employment_share_lost"] or 0))[:10]:
        v = bg[g]
        A(f"| {g} | {v['largest_occupation_in_group']} | {v['oews_2021_occupations']} | "
          f"{v['matched_into_the_gate']} | {v['oews_2021_employment']:,.0f} | "
          f"{_f(v['employment_share_lost'],'.1%')} |")
    A("")
    A("### Many-to-one collapsing of O*NET-SOC detail codes\n")
    A("| source | 6-digit SOCs | detail rows | SOCs with >1 detail code | of those, detail codes disagree | median within-SOC spread |")
    A("|---|---:|---:|---:|---:|---:|")
    for src, d in rec["item3_detail_code_collapsing"].items():
        sp = d["within_soc_spread_when_multiple"]
        A(f"| {src} | {d['six_digit_socs']} | {d['detail_rows']} | "
          f"{d['socs_with_multiple_detail_codes']} | {d['socs_where_detail_codes_disagree']} | "
          f"{_f(sp['median'],'.4f') if sp else 'n/a'} |")
    A("")

    A("## SOC-vintage sensitivity — every measure on the identical sample\n")
    A("| measure | own n | own R² | common n | common R² | shift |")
    A("|---|---:|---:|---:|---:|---:|")
    for name, v in rec["soc_vintage_sensitivity"]["by_measure"].items():
        o, cm = v["own_sample"], v["common_sample"]
        A(f"| {name} | {o['n_with_employment'] if o else 'n/a'} | "
          f"{_f(o['r2_employment_weighted'],'.4f') if o else 'n/a'} | "
          f"{cm['n_with_employment'] if cm else 'n/a'} | "
          f"{_f(cm['r2_employment_weighted'],'.4f') if cm else 'n/a'} | "
          f"{_f(v['r2_shift_common_minus_own'],'+.4f')} |")
    A("")
    A(rec["soc_vintage_sensitivity"]["how_to_read"] + "\n")

    A("## Item 4 — within 2-digit major groups\n")
    A(f"Groups with fewer than {MIN_GROUP_N} matched occupations, or with no "
      f"within-group variation in teleworkability, are reported here but not "
      f"correlated.\n")
    first = next(iter(rec["by_measure"].values()))["item4_within_major_group"]
    flat = {g: v for g, v in first.items() if v.get("telework_constant_within_group")}
    if flat:
        A("**Groups where teleworkability is constant across every occupation "
          "in the group** — there is no within-group contrast to identify "
          "anything from, whatever the pooled correlation says:\n")
        A("| group | largest occupation in group | n | employment | teleworkable share |")
        A("|---|---|---:|---:|---:|")
        for g, v in sorted(flat.items()):
            A(f"| {g} | {v['largest_occupation']} | {v['n_occupations']} | "
              f"{v['employment']:,.0f} | constant |")
        A("")
    for name in rec["by_measure"]:
        wg = rec["by_measure"][name]["item4_within_major_group"]
        corr_groups = {g: v for g, v in wg.items() if v.get("correlated")}
        if not corr_groups:
            continue
        A(f"### {name}\n")
        A("| group | largest occupation in group | n | Kish n_eff | Pearson (emp) | R² | measure var | residual var |")
        A("|---|---|---:|---:|---:|---:|---:|---:|")
        for g, v in corr_groups.items():
            A(f"| {g} | {v['largest_occupation']} | {v['n_occupations']} | "
              f"{_f(v['kish_effective_n'],'.1f')} | {_f(v.get('pearson_employment_weighted'),'.4f')} | "
              f"{_f(v.get('r2_employment_weighted'),'.4f')} | "
              f"{_f(v.get('measure_variance_within_group'),'.5f')} | "
              f"{_f(v.get('residual_variance_within_group'),'.5f')} |")
        A("")

    A("## Item 5 — leave one major group out\n")
    A("| measure | full-sample R² | most influential group | largest abs ΔR² | R² without that group |")
    A("|---|---:|---|---:|---:|")
    for name, m in rec["by_measure"].items():
        l = m["item5_leave_one_major_group_out"]
        g = l.get("most_influential_major_group")
        without = l["dropped"][g]["r2_employment_weighted"] if g else None
        A(f"| {name} | {_f(l['full_sample_r2'],'.4f')} | {g or 'n/a'} | "
          f"{_f(l.get('largest_absolute_r2_shift'),'.4f')} | {_f(without,'.4f')} |")
    A("")

    A("## Item 6 — where the residual variation lives\n")
    A("| measure | slope on telework | resid sd (emp) | top-10 share | top-25 share | occs to reach half | effective # occs |")
    A("|---|---:|---:|---:|---:|---:|---:|")
    for name, m in rec["by_measure"].items():
        r = m["item6_residual_structure"]
        if not r:
            continue
        c = r["concentration_of_weighted_residual_variance"]
        A(f"| {name} | {_f(r['regression']['slope'],'.4f')} | "
          f"{_f(r['residual_distribution_employment_weighted_moments']['sd'],'.4f')} | "
          f"{_f(c['top_10_occupations_share'],'.2%')} | {_f(c['top_25_occupations_share'],'.2%')} | "
          f"{c['occupations_to_reach_half']} | {_f(c['effective_number_of_occupations'],'.1f')} |")
    A("")
    for name, m in rec["by_measure"].items():
        r = m["item6_residual_structure"]
        if not r:
            continue
        A(f"### {name} — 25 occupations contributing most residual variation\n")
        A("| SOC | occupation | telework share | measure | residual | employment | share of resid. var |")
        A("|---|---|---:|---:|---:|---:|---:|")
        for e in r["largest_contributors_to_residual_variance"]:
            A(f"| {e['soc']} | {e['occupation']} | {e['teleworkable_share']:.3f} | "
              f"{e['measure']:.3f} | {e['residual']:+.3f} | {e['employment']:,.0f} | "
              f"{e['share_of_weighted_residual_variance']:.2%} |")
        A("")
        A(f"#### {name} — 25 largest positive residuals (more AI-exposed than telework predicts)\n")
        A("| SOC | occupation | telework share | measure | residual | employment |")
        A("|---|---|---:|---:|---:|---:|")
        for e in r["largest_positive_residuals"]:
            A(f"| {e['soc']} | {e['occupation']} | {e['teleworkable_share']:.3f} | "
              f"{e['measure']:.3f} | {e['residual']:+.3f} | {e['employment']:,.0f} |")
        A("")
        A(f"#### {name} — 25 largest negative residuals (less AI-exposed than telework predicts)\n")
        A("| SOC | occupation | telework share | measure | residual | employment |")
        A("|---|---|---:|---:|---:|---:|")
        for e in r["largest_negative_residuals"]:
            A(f"| {e['soc']} | {e['occupation']} | {e['teleworkable_share']:.3f} | "
              f"{e['measure']:.3f} | {e['residual']:+.3f} | {e['employment']:,.0f} |")
        A("")

    A("## Item 7 — contrast among occupations with positive teleworkability\n")
    any_deg = False
    for name, m in rec["by_measure"].items():
        p7 = m["item7_positive_telework_quartiles"]
        if p7.get("quartiles_degenerate"):
            any_deg = True
            d = p7["distribution_among_positive"]
            A(f"The requested quartiles do not exist. Among the "
              f"{p7['n_occupations_positive_telework']} occupations with any "
              f"teleworkable detail code, the collapsed share takes only "
              f"{d['distinct_values']} distinct values and "
              f"{d['n_at_exactly_1.0']} of them "
              f"({d['share_of_occupations_at_1.0']:.1%} of occupations, "
              f"{d['employment_share_at_1.0']:.1%} of their employment) sit at "
              f"exactly 1.0. " + p7["why_no_quartiles"] + "\n")
            break
    if any_deg:
        A("| measure | fully teleworkable: n | emp share | mean measure | partially: n | emp share | mean measure | Pearson (emp) |")
        A("|---|---:|---:|---:|---:|---:|---:|---:|")
        for name, m in rec["by_measure"].items():
            p7 = m["item7_positive_telework_quartiles"]
            fv = p7.get("fully_vs_partially")
            if not fv:
                continue
            f_, pa = fv["fully_teleworkable_share_eq_1"], fv["partially_teleworkable_0_lt_share_lt_1"]
            A(f"| {name} | {f_['n_occupations']} | {_f(f_['employment_share_of_positive_telework'],'.1%')} | "
              f"{_f(f_['mean_measure_employment_weighted'],'.4f')} | {pa['n_occupations']} | "
              f"{_f(pa['employment_share_of_positive_telework'],'.1%')} | "
              f"{_f(pa['mean_measure_employment_weighted'],'.4f')} | "
              f"{_f(p7['pearson_employment_weighted_within_positive'],'.4f')} |")
        A("")
        A("The within-positive Pearson column is computed against a regressor")
        A("that is almost binary inside this subsample. It is not a")
        A("high-versus-low gradient in teleworkability and should not be read")
        A("as one.\n")
    else:
        A("| measure | n | Kish n_eff | Q1 mean | Q2 mean | Q3 mean | Q4 mean | Pearson (emp) | R² |")
        A("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
        for name, m in rec["by_measure"].items():
            p7 = m["item7_positive_telework_quartiles"]
            if p7.get("status") == "insufficient" or not p7.get("quartiles"):
                continue
            q = p7["quartiles"]
            g = lambda k: _f(q[k]["mean_measure_employment_weighted"], ".4f") if k in q else "n/a"  # noqa: E731
            A(f"| {name} | {p7['n_occupations_positive_telework']} | "
              f"{_f(p7['kish_effective_n'],'.1f')} | {g('Q1')} | {g('Q2')} | {g('Q3')} | {g('Q4')} | "
              f"{_f(p7['pearson_employment_weighted_within_positive'],'.4f')} | "
              f"{_f(p7['r2_employment_weighted_within_positive'],'.4f')} |")
        A("")

    A("## Items 8–10\n")
    A("Out of scope for this script and still open in `AUDIT_SPEC.md`: CPS")
    A("power on the real cluster structure (8), Webb (2020) and Frey–Osborne")
    A("(2017) (9, not obtained — both would need network access this session")
    A("does not have), and novelty verification (10).\n")

    pathlib.Path(path).write_text("\n".join(L) + "\n", encoding="utf-8")


def write_figures(rec, dn, measures, emp, outdir):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover - environment dependent
        return {"status": "skipped", "reason": f"matplotlib unavailable: {exc}"}
    outdir = pathlib.Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    written = []

    focus = ["AIOE_Felten", "Eloundou_dv_rating_alpha"]

    # 1. scatter, point area proportional to employment
    fig, axes = plt.subplots(1, len(focus), figsize=(11, 4.6))
    for ax, name in zip(axes, focus):
        s = measures[name]
        ks = [k for k in s if k in dn and k in emp]
        ax.scatter([dn[k] for k in ks], [s[k] for k in ks],
                   s=[max(emp[k] / 6000.0, 1.5) for k in ks], alpha=0.35,
                   edgecolors="none")
        ax.set_xlabel("Dingel–Neiman teleworkable share")
        ax.set_ylabel(name)
        ax.set_title(f"{name}\npoint area ∝ OEWS 2021 employment", fontsize=9)
    fig.tight_layout()
    p = outdir / "fig1_scatter_measure_vs_telework.png"
    fig.savefig(p, dpi=140); plt.close(fig); written.append(str(p))

    # 2. concentration curve of weighted residual variance.
    # Computed over every occupation, not interpolated between the summary
    # percentiles -- a Lorenz curve drawn through four points would invent its
    # own shape.
    fig, ax = plt.subplots(figsize=(6, 4.6))
    for name in focus:
        s = measures[name]
        ks = [k for k in s if k in dn and k in emp]
        x = [dn[k] for k in ks]
        y = [s[k] for k in ks]
        w = [emp[k] for k in ks]
        _a, _b, res = wols(y, x, w)
        if res is None:
            continue
        contrib = sorted((wi * ri * ri for wi, ri in zip(w, res)), reverse=True)
        tot = sum(contrib)
        if tot <= 0:
            continue
        cum, run = [], 0.0
        for c in contrib:
            run += c / tot
            cum.append(run)
        ax.plot([(i + 1) / len(cum) for i in range(len(cum))], cum, label=name)
    ax.plot([0, 1], [0, 1], "k--", lw=0.8, label="perfectly even")
    ax.set_xlabel("share of occupations (ranked by contribution)")
    ax.set_ylabel("cumulative share of weighted residual variance")
    ax.set_title("Concentration of the variation left after removing telework", fontsize=9)
    ax.legend(fontsize=7)
    fig.tight_layout()
    p = outdir / "fig2_residual_variance_concentration.png"
    fig.savefig(p, dpi=140); plt.close(fig); written.append(str(p))

    # 3. within-major-group R2. Only groups where BOTH measures were actually
    # correlated: a zero-height bar for a group that was never computed reads
    # as "R2 = 0", which is a different statement.
    fig, ax = plt.subplots(figsize=(9, 4.8))
    per = {name: rec["by_measure"][name]["item4_within_major_group"] for name in focus}
    all_groups = sorted({g for wg in per.values() for g in wg})
    groups = [g for g in all_groups
              if all(per[n].get(g, {}).get("correlated")
                     and per[n][g].get("r2_employment_weighted") is not None
                     for n in focus)]
    omitted = [g for g in all_groups if g not in groups]
    width = 0.4
    for i, name in enumerate(focus):
        vals = [per[name][g]["r2_employment_weighted"] for g in groups]
        ax.bar([j + i * width for j in range(len(groups))], vals, width, label=name)
    ax.set_xticks([j + width / 2 for j in range(len(groups))])
    ax.set_xticklabels(groups, rotation=0, fontsize=7)
    ax.set_xlabel("SOC 2-digit major group"
                  + (f"   (omitted, fewer than {MIN_GROUP_N} matched occupations "
                     f"or no weighted variance: {', '.join(omitted)})" if omitted else ""),
                  fontsize=8)
    ax.set_ylabel("employment-weighted R² vs telework")
    ax.set_title("Within-group overlap (pooled R² can be entirely between-group)", fontsize=9)
    ax.legend(fontsize=7)
    fig.tight_layout()
    p = outdir / "fig3_within_major_group_r2.png"
    fig.savefig(p, dpi=140); plt.close(fig); written.append(str(p))

    # 4. own-sample vs common-sample R2
    fig, ax = plt.subplots(figsize=(9, 4.6))
    names = list(rec["soc_vintage_sensitivity"]["by_measure"])
    own = [(rec["soc_vintage_sensitivity"]["by_measure"][n]["own_sample"] or {}).get("r2_employment_weighted") or 0.0
           for n in names]
    com = [(rec["soc_vintage_sensitivity"]["by_measure"][n]["common_sample"] or {}).get("r2_employment_weighted") or 0.0
           for n in names]
    xs = range(len(names))
    ax.bar([x - 0.2 for x in xs], own, 0.4, label="own sample")
    ax.bar([x + 0.2 for x in xs], com, 0.4, label="common sample (all four sources)")
    ax.set_xticks(list(xs))
    ax.set_xticklabels([n.replace("Eloundou_", "El_") for n in names], rotation=30,
                       ha="right", fontsize=7)
    ax.set_ylabel("employment-weighted R² vs telework")
    ax.set_title("SOC-vintage sensitivity: same statistic, same occupations", fontsize=9)
    ax.legend(fontsize=7)
    fig.tight_layout()
    p = outdir / "fig4_soc_vintage_sensitivity.png"
    fig.savefig(p, dpi=140); plt.close(fig); written.append(str(p))

    return {"status": "written", "figures": written}


def main(argv=None):
    here = pathlib.Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dingel-neiman", type=pathlib.Path, default=here / "dingel_neiman_occ.csv")
    ap.add_argument("--eloundou", type=pathlib.Path, default=here / "eloundou_occ.csv")
    ap.add_argument("--aioe", type=pathlib.Path, default=here / "AIOE_DataAppendix.xlsx")
    ap.add_argument("--oews", type=pathlib.Path,
                    default=pathlib.Path("dax/data_built/oews_wages.parquet"))
    ap.add_argument("--output", type=pathlib.Path,
                    default=here / "audit_common_support_receipt.json")
    ap.add_argument("--markdown", type=pathlib.Path, default=here / "AUDIT_RESULTS.md")
    ap.add_argument("--figures", type=pathlib.Path, default=here / "figures")
    args = ap.parse_args(argv)

    for p in (args.dingel_neiman, args.eloundou, args.aioe, args.oews):
        if not p.is_file():
            print(f"NEED_HUMAN: missing input {p}", file=sys.stderr)
            return 2

    rec = build(args.dingel_neiman, args.eloundou, args.aioe, args.oews)

    dn, _ = load_dingel_neiman(args.dingel_neiman)
    el = load_eloundou(args.eloundou)
    measures = {"AIOE_Felten": load_aioe(args.aioe)}
    for m in ELOUNDOU_MEASURES:
        measures[f"Eloundou_{m}"] = {k: d[m] for k, d in el.items() if m in d}
    emp, _t = load_employment_titled(args.oews)
    rec["figures"] = write_figures(rec, dn, measures, emp, args.figures)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    write_markdown(rec, args.markdown)

    print(f"wrote {args.output}")
    print(f"wrote {args.markdown}")
    print(f"figures: {rec['figures'].get('status')}")
    print()
    hdr = (f"{'measure':<30} {'n':>4} {'r(emp)':>8} {'rho(emp)':>9} {'R2':>7} "
           f"{'ownR2->commonR2':>17} {'effOccs':>8}")
    print(hdr); print("-" * len(hdr))
    for name, m in rec["by_measure"].items():
        t = m["item1_correlations_own_sample"]
        v = rec["soc_vintage_sensitivity"]["by_measure"][name]
        r6 = m["item6_residual_structure"]
        eff = (r6["concentration_of_weighted_residual_variance"]["effective_number_of_occupations"]
               if r6 else None)
        o = (v["own_sample"] or {}).get("r2_employment_weighted")
        c = (v["common_sample"] or {}).get("r2_employment_weighted")
        print(f"{name:<30} {t['n_with_employment']:>4} "
              f"{_f(t['pearson_employment_weighted'],'8.4f')} "
              f"{_f(t['spearman_employment_weighted'],'9.4f')} "
              f"{_f(t['r2_employment_weighted'],'7.4f')} "
              f"{_f(o,'7.4f')}->{_f(c,'7.4f')} "
              f"{_f(eff,'8.1f')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
