#!/usr/bin/env python3
"""Is the Russell fallback design actually available? Answered from our own data.

The problem (plan §6, threat T3): the DFA anchor wave is effective
2021-06-11, two weeks before the June 2021 Russell annual reconstitution, which
mechanically moves volume, spreads and index-fund holdings on exactly the
small/value names DFA is heavy in — i.e. directly on top of our outcome
variables. §修订3 makes handling it a MANDATORY T5 sub-spec.

The research plan (docs/基金转换实验_博士研究计划.md §133) gives three responses.
Two of them need CRSP/Russell membership data we do not have. The third does not:

  (iii) 用 2022–2025 的非 6 月波次做纯复制 —— 如果效应只在 2021-06 出现而后续
        波次全无, 结论降级, 写进出口矩阵

That is a fallback whose *availability* is computable today from
p1/events_merged.csv alone. Whether it has any funds in it is a design fact that
should be established BEFORE the design commits to it — discovering afterwards
that the fallback sample is empty would be discovering it at the referee's desk.

This script only counts what exists. It makes no claim about effects.

  python p1/design/russell_fallback_check.py [--write]
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
EVENTS = ROOT / "p1" / "events_merged.csv"
MEMBERS = ROOT / "p1" / "t2_wrds" / "waves_members.csv"
OUT = ROOT / "p1" / "design" / "russell_fallback.json"

ANCHOR = "2021-06-11"
# Russell's annual reconstitution happens in late June. A wave effective in June
# of any year sits inside that window; those are the ones the confound touches.
RECONSTITUTION_MONTH = 6


def load_waves() -> list[dict]:
    with open(MEMBERS, newline="") as f:
        members = list(csv.DictReader(f))
    by_wave: dict[str, list[dict]] = collections.defaultdict(list)
    for m in members:
        by_wave[m["wave_id"]].append(m)
    out = []
    for wid, ms in by_wave.items():
        d = dt.date.fromisoformat(ms[0]["effective_date"])
        out.append({"wave_id": wid, "effective_date": d.isoformat(), "year": d.year,
                    "month": d.month, "n_funds": len(ms),
                    "is_anchor": ms[0]["effective_date"] == ANCHOR,
                    "in_june": d.month == RECONSTITUTION_MONTH,
                    "families": sorted({m.get("family", "") for m in ms if m.get("family")}),
                    "funds": [m["fund_name"] for m in ms]})
    return sorted(out, key=lambda w: w["effective_date"])


def analyse() -> dict:
    waves = load_waves()
    today = dt.date.today()
    usable = [w for w in waves if dt.date.fromisoformat(w["effective_date"]) <= today]

    anchor = [w for w in usable if w["is_anchor"]]
    june = [w for w in usable if w["in_june"]]
    # the §133(iii) fallback, verbatim: 2022-2025, not June
    fb = [w for w in usable if 2022 <= w["year"] <= 2025 and not w["in_june"]]
    # the same idea without the plan's end-year cutoff, since we now have 2026 data
    fb_ext = [w for w in usable if w["year"] >= 2022 and not w["in_june"]]

    def summarise(ws, label):
        return {"label": label, "n_waves": len(ws),
                "n_funds": sum(w["n_funds"] for w in ws),
                "years": sorted({w["year"] for w in ws}),
                "n_families": len({f for w in ws for f in w["families"]}),
                "largest_wave": max((w["n_funds"] for w in ws), default=0)}

    return {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(),
        "question": ("Does the plan's §133(iii) Russell fallback — replicate on "
                     "2022-2025 non-June waves — have a sample to run on?"),
        "source": "p1/t2_wrds/waves_members.csv (derived from events_merged.csv)",
        "caveat": ("Counts CONVERSION EVENTS, not treated stocks. How many stocks "
                   "each wave treats depends on ConvExp, which for the anchor is "
                   "known (361 stocks >=0.5%) and for later waves is thin in the "
                   "free-path build. Fund counts bound the design from above."),
        "all_waves": summarise(usable, "all effective waves to date"),
        "anchor": summarise(anchor, "DFA anchor 2021-06-11"),
        "june_waves": summarise(june, "June waves (Russell reconstitution window)"),
        "fallback_133iii": summarise(fb, "2022-2025, non-June (plan §133 iii)"),
        "fallback_extended": summarise(fb_ext, "2022+, non-June (incl. 2026)"),
        "june_wave_detail": [{k: w[k] for k in
                              ("wave_id", "effective_date", "n_funds", "families")}
                             for w in june],
    }


def verdict(r: dict) -> list[str]:
    fb, anc, ext = r["fallback_133iii"], r["anchor"], r["fallback_extended"]
    out = []
    if fb["n_waves"] == 0:
        out.append("FALLBACK EMPTY — §133(iii) cannot be run as written. The Russell "
                   "confound would have to be handled entirely by the control and "
                   "drop-sample specs, both of which need Russell membership data.")
    else:
        out.append(f"FALLBACK AVAILABLE — {fb['n_waves']} waves / {fb['n_funds']} funds "
                   f"across {fb['years'][0]}-{fb['years'][-1]}, {fb['n_families']} "
                   "families. §133(iii) is runnable as written.")
    out.append(f"For scale: the anchor is {anc['n_funds']} funds in 1 wave, and the "
               f"anchor alone carries 361 stocks at ConvExp>=0.5% (coverage audit). "
               f"The fallback's {fb['n_funds']} funds are spread over "
               f"{fb['n_waves']} waves, so per-wave treated counts will be far "
               "thinner — the binding constraint is treated STOCKS, not funds, and "
               "that cannot be settled until ConvExp is rebuilt on CRSP.")
    if ext["n_waves"] > fb["n_waves"]:
        out.append(f"The plan's 2025 cutoff now costs {ext['n_waves'] - fb['n_waves']} "
                   f"waves / {ext['n_funds'] - fb['n_funds']} funds that have since "
                   "become available. Extending to 2026 is a free power gain and "
                   "should be a spec decision, not an oversight.")
    if r["june_waves"]["n_waves"] > 1:
        out.append(f"{r['june_waves']['n_waves']} waves fall in June across all years, "
                   "not just the anchor — the reconstitution control must be applied "
                   "to all of them, not only 2021-06.")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    r = analyse()
    r["verdict"] = verdict(r)
    for k in ("all_waves", "anchor", "june_waves", "fallback_133iii", "fallback_extended"):
        s = r[k]
        print(f"  {s['label']:45s} {s['n_waves']:3d} waves  {s['n_funds']:4d} funds")
    for line in r["verdict"]:
        print(f"\n  {line}")
    if a.write:
        OUT.write_text(json.dumps(r, indent=2) + "\n")
        import sys
        sys.path.insert(0, str(ROOT / "ops" / "runner"))
        from lineage import write_lineage
        write_lineage(OUT, [MEMBERS, EVENTS])
        print(f"\nwrote {OUT.relative_to(ROOT)} + lineage")


if __name__ == "__main__":
    main()
