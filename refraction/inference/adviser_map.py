#!/usr/bin/env python3
"""REFR — map converting funds to ECONOMIC ADVISERS for clustering (Plan v2.4 §8.2).

Trust-level family strings are wrong for clustering in BOTH directions, which is why
the naive count of ~46 "families" cannot be used:

  OVERSTATES independence — one adviser operating several trusts. Fidelity Commonwealth
  Trust II / Fidelity Salem Street Trust / Fidelity Summer Street Trust are one economic
  sponsor, as are JPMorgan Trust I / II, and the Neuberger Berman trusts.

  UNDERSTATES independence — a multi-manager SERIES TRUST hosting unrelated advisers.
  Northern Lights Fund Trust, The RBB Fund, Trust for Professional Managers, Advisor
  Managed Portfolios and similar shells exist to rent registration infrastructure; the
  funds inside have their own independent advisers and are NOT one treatment cluster.

The second error is the dangerous one: it would pool unrelated sponsors into a single
cluster and shrink the standard errors that clustering exists to widen.

Series-trust membership cannot be resolved from the trust name — it needs the fund-level
adviser from the filing (N-CEN / prospectus). This module therefore emits a BOUNDED RANGE
plus an explicit to-resolve list, never a false point estimate.

  python refraction/inference/adviser_map.py
"""
import csv
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
EVENTS = ROOT / "p1" / "events_merged.csv"
MEMBERS = ROOT / "p1" / "t2_wrds" / "waves_members.csv"
OUT = pathlib.Path(__file__).resolve().parent / "adviser_map.csv"
WAVES_END = "2025-06-30"

# Same adviser, several trusts. Rule-based, and every rule is a name a human can check.
ADVISER_RULES = [
    (r"^Fidelity\b", "Fidelity"),
    (r"^JPMorgan Trust|^Undiscovered Managers", "JPMorgan"),   # UM is JPMorgan-advised
    (r"^Neuberger Berman", "Neuberger Berman"),
    (r"^DFA Investment Dimensions|^Dimensional Investment", "Dimensional"),
    (r"^BlackRock", "BlackRock"),
    (r"^Bridgeway", "Bridgeway"),
    (r"^AB (Bond|Cap) Fund", "AllianceBernstein"),
    (r"^BNY Mellon", "BNY Mellon"),
    (r"^Goldman Sachs", "Goldman Sachs"),
    (r"^Franklin|^Legg Mason", "Franklin/Legg Mason"),
    (r"^Morgan Stanley", "Morgan Stanley"),
    (r"^PIMCO", "PIMCO"),
    (r"^Matthews", "Matthews"),
    (r"^Mirae", "Mirae"),
    (r"^Metropolitan West", "Metropolitan West"),
    (r"^The Hartford", "Hartford"),
    (r"^The Lazard", "Lazard"),
    (r"^Leuthold", "Leuthold"),
    (r"^Touchstone", "Touchstone"),
    (r"^Guinness Atkinson", "Guinness Atkinson"),
    (r"^abrdn", "abrdn"),
    (r"^FundX", "FundX"),
]

# Multi-manager series trusts: the trust is NOT the adviser. Each fund inside needs its
# adviser read from the filing before it can be clustered.
SERIES_TRUSTS = [
    r"^Advisor Managed Portfolios", r"^FundVantage Trust",
    r"^Investment Managers Series Trust", r"^Manager Directed Portfolios",
    r"NORTHERN LIGHTS FUND TRUST", r"^Northern Lights Fund Trust",
    r"^The RBB Fund", r"^Trust for Advised Portfolios",
    r"^Trust for Professional Managers", r"^Two Roads Shared Trust",
    r"^The Advisors' Inner Circle Fund", r"^Forum Funds",
    r"^OTG Asset Management", r"^ETF Opportunities Trust",
]


def classify(family: str):
    """-> (adviser_or_None, is_series_trust)."""
    f = (family or "").strip()
    for pat in SERIES_TRUSTS:
        if re.search(pat, f, re.I):
            return None, True
    for pat, name in ADVISER_RULES:
        if re.search(pat, f, re.I):
            return name, False
    return f, False          # single-trust adviser: the trust name IS the sponsor


def build():
    fam = {}
    for e in csv.DictReader(open(EVENTS)):
        fam[e["fund_name"]] = (e.get("family") or "").strip()
    rows = []
    for m in csv.DictReader(open(MEMBERS)):
        if m["effective_date"] > WAVES_END:
            continue
        family = fam.get(m["fund_name"], "")
        adviser, series = classify(family)
        rows.append({"wave_id": m["wave_id"], "fund_name": m["fund_name"],
                     "family": family,
                     "adviser": adviser or "UNRESOLVED_SERIES_TRUST",
                     "needs_filing_lookup": "yes" if series or not family else "no"})
    return rows


def summarize(rows):
    resolved = {r["adviser"] for r in rows if r["needs_filing_lookup"] == "no"}
    unresolved = [r for r in rows if r["needs_filing_lookup"] == "yes"]
    trusts = {r["family"] for r in unresolved if r["family"]}
    return {
        "funds_in_frame": len(rows),
        "waves_in_frame": len({r["wave_id"] for r in rows}),
        "resolved_advisers": len(resolved),
        "funds_needing_filing_lookup": len(unresolved),
        "series_trusts_involved": len(trusts),
        # Lower: every series trust collapses to one adviser (understates independence).
        "adviser_count_lower_bound": len(resolved) + len(trusts),
        # Upper: every fund in a series trust has its own adviser (overstates).
        "adviser_count_upper_bound": len(resolved) + len(unresolved),
    }


def main():
    rows = build()
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["wave_id", "fund_name", "family", "adviser",
                                          "needs_filing_lookup"])
        w.writeheader()
        w.writerows(rows)
    s = summarize(rows)
    print("funds in frame: %(funds_in_frame)d across %(waves_in_frame)d waves" % s)
    print("advisers resolved from the trust name: %(resolved_advisers)d" % s)
    print("funds inside multi-manager SERIES TRUSTS needing a filing lookup: "
          "%(funds_needing_filing_lookup)d across %(series_trusts_involved)d trusts" % s)
    print("ECONOMIC ADVISER COUNT: between %(adviser_count_lower_bound)d and "
          "%(adviser_count_upper_bound)d — not a point estimate until the filing "
          "lookup is done" % s)
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
