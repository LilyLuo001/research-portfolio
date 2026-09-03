#!/usr/bin/env python3
"""Gate0: does every timing-eligible conversion have observable holdings on both
sides of its effective date?

Exposure^pre is a predetermined dose, so the design needs a portfolio snapshot
taken strictly before the fund converted and a first snapshot of the successor
after it. This file decides, per event, whether those two observations exist. It
decides nothing else: no exposure is computed here, and a pass means only that
the raw material is present.

Two things make that decision non-trivial, and both are handled explicitly.

Report date, not filing date. An N-PORT filed two weeks after the conversion can
report holdings as of a date two months before it, and an N-PORT filed before the
conversion is always as-of an earlier date still. Selecting on filing date would
therefore both admit post-conversion filings as "pre" and miss genuine pre-period
holdings. PRE/POST is decided on <repPdDate>, the date the holdings are stated as
of, which is read out of the filing itself.

Series identity, not fund name. A trust files one N-PORT per series and a fund
name matches several of them loosely, so the universe's series ids are used to
enumerate filings directly and the id inside each filing is checked against the
one asked for. A mismatch fails the event rather than being scored and accepted.

PRE is read on the predecessor series and POST on the successor, because the
predecessor stops filing at conversion and the successor is the entity holding
the portfolio afterwards. Where a fund converted in place the two ids coincide
and the same logic applies unchanged.
"""
import logging
import pathlib
import re
import sys
import xml.etree.ElementTree as ET
from datetime import timedelta

import pandas as pd

from sec_http import CACHE, http_get

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = ROOT / "p1" / "t2_free"
UNIVERSE = (pathlib.Path.home() / "p1_data_cache" / "universe_v2"
            / "event_master_final_reconciled.csv")
WAVES = pathlib.Path.home() / "p1_data_cache" / "universe_v2" / "wave_membership_v2.csv"

EVENT_OUT = HERE / "nport_gate0_event_level.csv"
FAIL_OUT = HERE / "nport_gate0_failure_list.csv"
SUMMARY_OUT = HERE / "nport_gate0_summary.csv"

# Filings whose *filing* date falls this far either side of the event are opened
# to read their report date. N-PORT is quarterly and filed within 60 days, so a
# window this wide holds several observations on each side; it is a fetch budget,
# not a selection rule, and it widens automatically when a boundary is missing.
WINDOW = timedelta(days=550)

for d in (CACHE / "series", CACHE / "nport"):
    d.mkdir(parents=True, exist_ok=True)

log = logging.getLogger("gate0")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout),
              logging.FileHandler(HERE / "nport_gate0.log", mode="w")])


def _lname(tag):
    return tag.split("}", 1)[1] if "}" in tag else tag


ACC_RE = re.compile(r"<accession-n\w*>([\d-]+)</accession-n\w*>")
ENTRY_RE = re.compile(r"<entry>(.*?)</entry>", re.S)


def series_filings(series_id):
    """Every NPORT-P (and /A) filed for exactly this series, oldest first.

    Enumerating by series id rather than by registrant is what makes the match
    exact: EDGAR resolves the id itself, so a multi-series trust never offers a
    sibling series as a candidate.
    """
    url = ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
           f"&CIK={series_id}&type=NPORT-P&dateb=&owner=include&count=200"
           "&output=atom")
    txt = http_get(url, CACHE / "series" / f"{series_id}_nportp.atom")
    if not txt:
        return []
    out = []
    for body in ENTRY_RE.findall(txt):
        acc = ACC_RE.search(body)
        fdt = re.search(r"<filing-date>([\d-]+)</filing-date>", body)
        typ = re.search(r"<filing-type>([^<]+)</filing-type>", body)
        href = re.search(r"<filing-href>([^<]+)</filing-href>", body)
        if not (acc and fdt and href):
            continue
        cik = re.search(r"/data/(\d+)/", href.group(1))
        out.append({"accession": acc.group(1), "filed": fdt.group(1),
                    "form": (typ.group(1) if typ else "NPORT-P"),
                    "cik": int(cik.group(1)) if cik else None})
    out.sort(key=lambda r: (r["filed"], r["accession"]))
    return out


def read_nport(f):
    """Report date, series identity and holdings counts for one filing."""
    if f.get("_parsed"):
        return f["_parsed"]
    nodash = f["accession"].replace("-", "")
    url = (f"https://www.sec.gov/Archives/edgar/data/{f['cik']}/{nodash}"
           "/primary_doc.xml")
    txt = http_get(url, CACHE / "nport" / f"{f['cik']}_{nodash}.xml",
                   is_json=False)
    if not txt:
        f["_parsed"] = None
        return None
    try:
        root = ET.fromstring(txt)
    except ET.ParseError as e:
        log.warning("XML parse error %s in %s", e, f["accession"])
        f["_parsed"] = None
        return None
    gen = {}
    for el in root.iter():
        if _lname(el.tag) == "genInfo":
            gen = {_lname(c.tag): (c.text or "").strip() for c in el}
            break
    secs = [e for e in root.iter() if _lname(e.tag) == "invstOrSec"]
    n_eq = 0
    for s in secs:
        v = {}
        for c in s.iter():
            n = _lname(c.tag)
            if n in ("units", "assetCat", "balance") and n not in v:
                v[n] = (c.text or "").strip()
        cat = v.get("assetCat", "")
        try:
            bal = float(v.get("balance") or 0)
        except ValueError:
            bal = 0.0
        if v.get("units") == "NS" and (not cat or cat == "EC") and bal > 0:
            n_eq += 1
    p = {"accession": f["accession"], "filed": f["filed"], "form": f["form"],
         "cik": f["cik"], "report_date": gen.get("repPdDate", ""),
         "period_end": gen.get("repPdEnd", ""),
         "series_id": gen.get("seriesId", ""),
         "series_name": gen.get("seriesName", ""),
         "is_final": gen.get("isFinalFiling", ""),
         "n_holdings": len(secs), "n_equity_share_holdings": n_eq}
    f["_parsed"] = p
    return p


def observations(series_id, eff, side, cache):
    """Parsed filings for a series near `eff`, widening until `side` is covered.

    `side` is 'pre' or 'post'. The window is a budget on how many filings to
    open, so it is widened rather than accepted whenever the boundary the caller
    needs has not been seen; only a genuinely sparse filing history returns
    without one.
    """
    fils = cache.setdefault(series_id, series_filings(series_id))
    if not fils:
        return [], []
    span = WINDOW
    for _ in range(3):
        lo, hi = (eff - span).strftime("%Y-%m-%d"), (eff + span).strftime("%Y-%m-%d")
        sel = [f for f in fils if lo <= f["filed"] <= hi]
        parsed = [p for p in (read_nport(f) for f in sel) if p and p["report_date"]]
        rd = [p for p in parsed if pd.Timestamp(p["report_date"]) < eff] \
            if side == "pre" else \
            [p for p in parsed if pd.Timestamp(p["report_date"]) > eff]
        if rd:
            return parsed, rd
        # nothing on the needed side inside the window: either widen, or stop
        # because the series simply has no filing out there to find
        edge = (min(f["filed"] for f in fils) if side == "pre"
                else max(f["filed"] for f in fils))
        if (side == "pre" and edge >= lo) or (side == "post" and edge <= hi):
            return parsed, []
        span *= 2
    return parsed, []


def pick(cands, side):
    """Latest strictly-pre, or earliest strictly-post, on report date.

    Amendments restate a date rather than add one, so among filings sharing a
    report date the last filed wins.
    """
    if not cands:
        return None
    by_date = {}
    for c in cands:
        k = c["report_date"]
        if k not in by_date or c["filed"] >= by_date[k]["filed"]:
            by_date[k] = c
    key = max if side == "pre" else min
    return by_date[key(by_date)]


def main():
    ev = pd.read_csv(UNIVERSE)
    elig = ev[ev.timing_eligible_primary].copy()
    log.info("timing-eligible events: %d", len(elig))

    wm = pd.read_csv(WAVES)[["pre_series_id", "wave_id", "wave_date"]]
    elig = elig.merge(wm, on="pre_series_id", how="left")
    assert elig.wave_id.notna().all(), "eligible event missing a wave"

    cache, rows = {}, []
    for i, r in enumerate(elig.itertuples(index=False), 1):
        eff = pd.Timestamp(r.verified_effective_date)
        pre_sid, post_sid = r.pre_series_id, r.post_series_id
        fails = []

        pre_all, pre_c = observations(pre_sid, eff, "pre", cache)
        pre = pick(pre_c, "pre")
        if not pre_all:
            fails.append("no_nport_filings_for_predecessor_series")
        elif pre is None:
            fails.append("no_nport_report_date_strictly_before_event")
        elif pre["n_holdings"] == 0:
            fails.append("pre_nport_holdings_empty")

        if not isinstance(post_sid, str) or not post_sid.startswith("S"):
            post_all, post_c, post = [], [], None
            fails.append("no_successor_series_id")
        else:
            post_all, post_c = observations(post_sid, eff, "post", cache)
            post = pick(post_c, "post")
            if not post_all:
                fails.append("no_nport_filings_for_successor_series")
            elif post is None:
                fails.append("no_nport_report_date_strictly_after_event")
            elif post["n_holdings"] == 0:
                fails.append("post_nport_holdings_empty")

        # the id inside the filing must be the id we asked EDGAR for
        amb = []
        if pre and pre["series_id"] and pre["series_id"] != pre_sid:
            amb.append(f"pre:{pre['series_id']}!={pre_sid}")
        if post and post["series_id"] and post["series_id"] != post_sid:
            amb.append(f"post:{post['series_id']}!={post_sid}")
        if amb:
            fails.append("series_id_mismatch(" + ";".join(amb) + ")")

        # a report dated exactly on the effective day is neither side
        onday = [p["report_date"] for p in (pre_all + post_all)
                 if p["report_date"] == eff.strftime("%Y-%m-%d")]

        rows.append({
            "event_id": r.event_id,
            "wave_id": r.wave_id,
            "effective_date": eff.strftime("%Y-%m-%d"),
            "adviser": getattr(r, "adviser", "") if pd.notna(getattr(r, "adviser", None)) else "",
            "pre_series_id": pre_sid,
            "pre_series_name": r.pre_series_name,
            "pre_cik": r.pre_cik,
            "post_series_id": post_sid,
            "post_series_name": r.post_series_name,
            "post_cik": r.post_cik,
            "pre_report_date": pre["report_date"] if pre else "",
            "pre_accession": pre["accession"] if pre else "",
            "pre_form": pre["form"] if pre else "",
            "pre_filing_date": pre["filed"] if pre else "",
            "pre_nport_series_id": pre["series_id"] if pre else "",
            "pre_holdings_count": pre["n_holdings"] if pre else 0,
            "pre_equity_share_holdings": pre["n_equity_share_holdings"] if pre else 0,
            "post_report_date": post["report_date"] if post else "",
            "post_accession": post["accession"] if post else "",
            "post_form": post["form"] if post else "",
            "post_filing_date": post["filed"] if post else "",
            "post_nport_series_id": post["series_id"] if post else "",
            "post_holdings_count": post["n_holdings"] if post else 0,
            "post_equity_share_holdings": post["n_equity_share_holdings"] if post else 0,
            "days_pre_report_to_event": ((eff - pd.Timestamp(pre["report_date"])).days
                                         if pre else ""),
            "days_event_to_post_report": ((pd.Timestamp(post["report_date"]) - eff).days
                                          if post else ""),
            "n_pre_candidates": len(pre_c),
            "n_post_candidates": len(post_c),
            "report_date_on_effective_day": ";".join(sorted(set(onday))),
            "gate0": "FAIL" if fails else "PASS",
            "failure_reason": "; ".join(fails),
        })
        log.info("[%3d/%d] %s %s %s pre=%s post=%s", i, len(elig), r.event_id,
                 eff.date(), rows[-1]["gate0"],
                 rows[-1]["pre_report_date"] or "-",
                 rows[-1]["post_report_date"] or "-")

    g = pd.DataFrame(rows)
    g.to_csv(EVENT_OUT, index=False)
    fl = g[g.gate0 == "FAIL"]
    fl.to_csv(FAIL_OUT, index=False)

    # ------------------------------------------------------------------ report
    n = len(g)
    p = int((g.gate0 == "PASS").sum())
    print("\n" + "=" * 76 + "\nGATE0  (strictly-pre and first-eligible-post N-PORT, "
          "on report date)\n" + "=" * 76)
    print(f"  {n:>5d}   timing-eligible events tested")
    print(f"  {p:>5d}   PASS with valid PRE + POST ({p / n:.0%})")
    print(f"  {n - p:>5d}   FAIL")

    def cnt(sub):
        return int(g.failure_reason.str.contains(sub, regex=False).sum())

    print(f"\n  {cnt('predecessor_series') + cnt('strictly_before'):>5d}   missing PRE")
    print(f"  {cnt('successor_series') + cnt('strictly_after') + cnt('no_successor_series_id'):>5d}"
          f"   missing POST")
    print(f"  {cnt('series_id_mismatch'):>5d}   series-id ambiguity")
    print(f"  {cnt('holdings_empty'):>5d}   malformed / empty holdings")
    onday = int((g.report_date_on_effective_day != "").sum())
    print(f"  {onday:>5d}   events with an N-PORT dated exactly on the effective day"
          f" (counted as neither side)")

    ok = g[g.gate0 == "PASS"]
    if len(ok):
        a = ok.days_pre_report_to_event.astype(int)
        b = ok.days_event_to_post_report.astype(int)
        print(f"\n  PRE report -> event, days:  median {int(a.median())}  "
              f"min {int(a.min())}  max {int(a.max())}")
        print(f"  event -> POST report, days: median {int(b.median())}  "
              f"min {int(b.min())}  max {int(b.max())}")
        print(f"  PRE holdings:  median {int(ok.pre_holdings_count.median())}  "
              f"min {int(ok.pre_holdings_count.min())}  "
              f"max {int(ok.pre_holdings_count.max())}")

    print("\n" + "=" * 76 + "\nCOVERAGE BY ADVISER\n" + "=" * 76)
    ca = (g.assign(pass_=(g.gate0 == "PASS").astype(int))
          .groupby(g.adviser.replace("", "(unmapped)"))
          .agg(events=("gate0", "size"), passed=("pass_", "sum"))
          .sort_values("events", ascending=False))
    for k, r in ca.iterrows():
        print(f"  {int(r.passed):>3d}/{int(r.events):<3d}  {str(k)[:56]}")

    print("\n" + "=" * 76 + "\nCOVERAGE BY WAVE\n" + "=" * 76)
    cw = (g.assign(pass_=(g.gate0 == "PASS").astype(int))
          .groupby(["wave_id", "effective_date"])
          .agg(events=("gate0", "size"), passed=("pass_", "sum"))
          .reset_index().sort_values("effective_date"))
    for r in cw.itertuples(index=False):
        mark = "ok  " if r.passed == r.events else "PART" if r.passed else "NONE"
        print(f"  {mark}  {r.wave_id}  {r.effective_date}  {r.passed}/{r.events}")

    print("\n" + "=" * 76 + "\nFAILURES (each listed)\n" + "=" * 76)
    if fl.empty:
        print("  none")
    for r in fl.itertuples(index=False):
        print(f"  {r.event_id}  {r.effective_date}  {str(r.pre_series_name)[:44]:<44}"
              f"  {r.failure_reason}")

    summary = pd.DataFrame(
        [{"metric": "timing_eligible_events", "value": n},
         {"metric": "gate0_pass", "value": p},
         {"metric": "gate0_pass_share", "value": round(p / n, 4)},
         {"metric": "gate0_fail", "value": n - p},
         {"metric": "missing_pre", "value": cnt("predecessor_series") + cnt("strictly_before")},
         {"metric": "missing_post",
          "value": cnt("successor_series") + cnt("strictly_after") + cnt("no_successor_series_id")},
         {"metric": "series_id_ambiguity", "value": cnt("series_id_mismatch")},
         {"metric": "empty_or_malformed_holdings", "value": cnt("holdings_empty")},
         {"metric": "nport_dated_on_effective_day", "value": onday}]
        + [{"metric": f"adviser::{k}", "value": f"{int(r.passed)}/{int(r.events)}"}
           for k, r in ca.iterrows()]
        + [{"metric": f"wave::{r.wave_id}@{r.effective_date}",
            "value": f"{r.passed}/{r.events}"} for r in cw.itertuples(index=False)])
    summary.to_csv(SUMMARY_OUT, index=False)

    print(f"\n  written: {EVENT_OUT.name}, {FAIL_OUT.name}, {SUMMARY_OUT.name}")
    print("\n  Gate0 is a data-availability gate only. No exposure is built here.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
