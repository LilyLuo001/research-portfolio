#!/usr/bin/env python3
"""P1-T1-arb assembly: adjudicated channel -> events_merged.csv.

Deterministic, rerunnable. The channel-level dual-source adjudication is already
done upstream (deepseek v2-A primary + targeted qwen tiebreaker + owner gate;
see ../t1_arb_evaluation.md); its product is ../t1_events_final.json (1418
filings, verdict-adjudicated, per-record _adjudication provenance). This script
performs the remaining step: collapse the EVENT filings (many filings describe
one conversion: N-14 + amendments + 497) into one row per unique conversion,
consolidating fields across filings, and split into:
  - events_merged.csv : conversions with a resolvable fund_name AND effective_date
                        (the contract requires both non-null; effective_date is
                        the study key). One row per (fund_name, effective_date).
  - held_back (report): conversions with no stated effective_date in the excerpt
                        windows -> needs_fulltext (fetch the full filing later),
                        never dropped silently.

Rules (frozen; POLICY.md §T1):
  announce_date  = earliest ISO across the group's filings (first disclosure)
  effective_date = the ISO closing date from the LATEST-FILED filing that states
                   one (amendments move closing dates; newest is authoritative).
                   Conflicts (>1 distinct ISO) are recorded in the report.
  identity fields (family, tickers, asset_class, AUM) = first non-NA, longest
  confidence     = best available (H>M>L)
  representative source_accession/url = the filing that supplied effective_date
                   (best locator for the study key); all accessions listed in report.
Grouping key = normalized fund_name (case/punct/stopword-stripped). Limitation:
name variants across filings may under-merge (double-count) and generic names
may over-merge; the report lists every group's members for audit.
"""
import csv
import json
import pathlib
import re
import collections

HERE = pathlib.Path(__file__).resolve().parent
P1 = HERE.parent
FINAL = P1 / "t1_events_final.json"
META = HERE / "id_meta.json"
OUT_CSV = P1 / "events_merged.csv"
REPORT = HERE / "arb_report.md"

COLS = ["fund_name", "family", "mutual_fund_ticker", "etf_ticker", "announce_date",
        "effective_date", "asset_class", "AUM_at_conversion_USD",
        "source_accession", "source_url", "confidence",
        "effective_date_approx", "date_precision"]
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STOP = re.compile(r"\b(the|fund|funds|portfolio|trust|inc|lp|llc|ltd|co|series|"
                  r"class|shares?|etf|of|company|incorporated)\b", re.I)
CONF_RANK = {"H": 3, "M": 2, "L": 1, "NA": 0, None: 0}
PREC_RANK = {"month": 3, "quarter": 2, "pending": 1, "NA": 0, "": 0, None: 0}


def norm(name):
    n = re.sub(r"[^a-z0-9 ]", " ", str(name).lower())
    n = STOP.sub(" ", n)
    return re.sub(r"\s+", " ", n).strip()


def fam2(family):
    """First two significant family words — disambiguates same-named funds across
    families (e.g. Sanford Bernstein 'Emerging Markets Portfolio' vs Mirae
    'Emerging Markets Fund') without splitting one conversion's own filings."""
    return " ".join(norm(family).split()[:2])


def isod(x):
    return bool(ISO.match(str(x)))


def pick_longest_nonNA(vals):
    cand = [v for v in vals if str(v) not in ("NA", "", "None", "nan")]
    return max(cand, key=lambda s: len(str(s))) if cand else "NA"


def load_events():
    final = json.loads(FINAL.read_text())
    meta = json.loads(META.read_text())
    # optional overlay: {source_accession: {"effective_date": "YYYY-MM-DD", ...}}
    # produced by the full-text date-recovery pass (merge_daterecover.py). Absent = no-op.
    overlay_p = HERE / "recovered_dates.json"
    overlay = json.loads(overlay_p.read_text()).get("recovered", {}) if overlay_p.exists() else {}
    # approximate-timing overlay (Pass 1b): {source_accession: {"effective_date_approx":
    # "YYYY-Qn"|"YYYY-MM", "date_precision": "quarter"|"month"|"pending", ...}}.
    # NEVER promotes effective_date (kept strict for verbatim ISO days); annotates held rows.
    approx_p = HERE / "approx_dates.json"
    approx = json.loads(approx_p.read_text()).get("approx", {}) if approx_p.exists() else {}
    rows = []
    for fid, v in final.items():
        if fid == "_meta" or v.get("no_event") or v.get("NEED_HUMAN"):
            continue
        evs = v["events"] if "events" in v else [v]
        for e in evs:
            sc = e.get("_spotcheck")
            if sc and sc.get("disposition") in ("not_event", "recheck", "defer"):
                continue                     # owner-gate correction: excluded from the clean set
            m = meta.get(fid, {})
            eff = str(e.get("effective_date", "NA"))
            if not ISO.match(eff) and fid in overlay and ISO.match(str(overlay[fid].get("effective_date", ""))):
                eff = overlay[fid]["effective_date"]        # promoted from full-text recovery
            ap = approx.get(fid, {})
            rows.append({
                "fund_name": str(e.get("fund_name", "NA")),
                "family": str(e.get("family", "NA")),
                "mutual_fund_ticker": str(e.get("mutual_fund_ticker", "NA")),
                "etf_ticker": str(e.get("etf_ticker", "NA")),
                "announce_date": str(e.get("announce_date", "NA")),
                "effective_date": eff,
                "asset_class": str(e.get("asset_class", "NA")),
                "AUM_at_conversion_USD": str(e.get("AUM_at_conversion_USD", "NA")),
                "source_accession": fid,
                "source_url": m.get("url") or "NA",
                "confidence": str(e.get("confidence", "NA")),
                "effective_date_approx": str(ap.get("effective_date_approx", "NA")),
                "date_precision": str(ap.get("date_precision", "NA")),
                "_filed": m.get("filed") or "0000-00-00",
            })
    return rows


def consolidate(group):
    """One event row from all filings of one conversion."""
    by_filed = sorted(group, key=lambda r: r["_filed"])
    best_prec = max(group, key=lambda r: PREC_RANK.get(r.get("date_precision"), 0))
    iso_eff = [(r["_filed"], r["effective_date"], r) for r in group if isod(r["effective_date"])]
    iso_ann = sorted(r["announce_date"] for r in group if isod(r["announce_date"]))
    eff_conflict = sorted({e for _, e, _ in iso_eff})
    if iso_eff:
        # latest-filed filing that states a closing date is authoritative
        _, eff, rep = max(iso_eff, key=lambda t: (t[0], t[1]))
    else:
        eff, rep = "NA", by_filed[-1]
    row = {
        "fund_name": pick_longest_nonNA([r["fund_name"] for r in group]),
        "family": pick_longest_nonNA([r["family"] for r in group]),
        "mutual_fund_ticker": pick_longest_nonNA([r["mutual_fund_ticker"] for r in group]),
        "etf_ticker": pick_longest_nonNA([r["etf_ticker"] for r in group]),
        "announce_date": iso_ann[0] if iso_ann else "NA",
        "effective_date": eff,
        "asset_class": pick_longest_nonNA([r["asset_class"] for r in group]),
        "AUM_at_conversion_USD": pick_longest_nonNA([r["AUM_at_conversion_USD"] for r in group]),
        "source_accession": rep["source_accession"],
        "source_url": rep["source_url"],
        "confidence": max((r["confidence"] for r in group), key=lambda c: CONF_RANK.get(c, 0)),
        "effective_date_approx": best_prec.get("effective_date_approx", "NA") if isod(eff) is False else "NA",
        "date_precision": best_prec.get("date_precision", "NA") if isod(eff) is False else "NA",
    }
    return row, {"n_filings": len(group), "accessions": [r["source_accession"] for r in group],
                 "eff_conflict": eff_conflict if len(eff_conflict) > 1 else None}


def main():
    rows = load_events()
    groups = collections.defaultdict(list)
    for r in rows:
        fn = r["fund_name"]
        key = (norm(fn), fam2(r["family"])) if fn not in ("NA", "", "None") else ("__NA__", r["source_accession"])
        groups[key].append(r)

    merged, held, audit = [], [], []
    for key, g in groups.items():
        row, info = consolidate(g)
        info["key"] = key
        info["fund_name"] = row["fund_name"]
        audit.append(info)
        if row["fund_name"] in ("NA", "", "None") or not isod(row["effective_date"]):
            held.append((row, info))
        else:
            merged.append((row, info))

    # second pass — collapse cross-trust splits: the target trust and the acquiring
    # ETF trust each file for one conversion, so fam2 splits them, but they resolve
    # to the SAME (fund_name, effective_date). Merge those (that pair IS the
    # contract PK). Genuinely distinct same-name funds differ in effective_date.
    by_pk = collections.OrderedDict()
    for row, info in merged:
        pk = (row["fund_name"], row["effective_date"])
        if pk in by_pk:
            prow, pinfo = by_pk[pk]
            for c in COLS:
                if str(prow[c]) in ("NA", "", "None") and str(row[c]) not in ("NA", "", "None"):
                    prow[c] = row[c]
            prow["announce_date"] = min(d for d in (prow["announce_date"], row["announce_date"])
                                        if isod(d)) if (isod(prow["announce_date"]) or isod(row["announce_date"])) else prow["announce_date"]
            prow["confidence"] = max(prow["confidence"], row["confidence"], key=lambda c: CONF_RANK.get(c, 0))
            pinfo["accessions"] += info["accessions"]
            pinfo["n_filings"] += info["n_filings"]
        else:
            by_pk[pk] = (row, info)
    merged = list(by_pk.values())

    # a conversion whose date was found on one trust's filings may leave the other
    # trust's filings dateless -> a held row duplicating a merged one. Drop those.
    merged_names = {r["fund_name"] for r, _ in merged}
    held = [(r, i) for r, i in held if r["fund_name"] not in merged_names]

    # primary-key collision guard: (fund_name, effective_date) must be unique
    seen = collections.Counter((r["fund_name"], r["effective_date"]) for r, _ in merged)
    pk_dups = [k for k, n in seen.items() if n > 1]

    OUT_CSV.parent.mkdir(exist_ok=True)
    with OUT_CSV.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        for r, _ in sorted(merged, key=lambda t: (t[0]["effective_date"], t[0]["fund_name"])):
            w.writerow(r)

    _write_report(rows, groups, merged, held, audit, pk_dups)
    print(f"events_merged.csv: {len(merged)} conversions | held_back {len(held)} | "
          f"from {len(rows)} event-filings / {len(groups)} groups | pk_dups {len(pk_dups)}")


def _write_report(rows, groups, merged, held, audit, pk_dups):
    conflicts = [a for a in audit if a.get("eff_conflict")]
    L = ["# P1-T1-arb — assembly report\n",
         f"Source: `../t1_events_final.json` (adjudicated channel). Assembly by "
         f"`assemble.py`.\n",
         "## Counts",
         f"- event-filings (filing × fund): **{len(rows)}**",
         f"- unique conversion groups: **{len(groups)}**",
         f"- → `events_merged.csv` (fund_name + effective_date resolved): **{len(merged)}**",
         f"- → held back (needs_fulltext, no stated effective_date or fund_name): **{len(held)}**",
         f"- effective_date conflicts across a group's filings (resolved to latest-filed): **{len(conflicts)}**",
         f"- primary-key (fund_name, effective_date) collisions: **{len(pk_dups)}**\n",
         "## Adjudication provenance",
         "Channel-level event/no_event calls were adjudicated upstream: deepseek "
         "v2-A primary, qwen targeted tiebreaker on 140 contested items, owner gate "
         "on the residual 11. 21 verdicts corrected (see ../t1_arb_evaluation.md, "
         "../t1_arb_resolution.json). This step only consolidates filings into "
         "conversions; it makes no new event/no_event judgments.\n",
         "## effective_date conflicts (latest-filed filing wins; all candidates listed)"]
    for a in conflicts:
        L.append(f"- **{a['fund_name']}** — candidates {a['eff_conflict']} across "
                 f"{a['n_filings']} filings ({', '.join(a['accessions'])})")
    L.append("\n## Held back — needs_fulltext (owner spotcheck / full-filing fetch)")
    L.append("Conversions confirmed as events but with no closing date in the excerpt "
             "windows (typical of N-14s saying 'as soon as practicable'); the date "
             "lands in a later 497 or completed-conversion filing outside our windows.\n")
    n_approx = sum(1 for r, _ in held if str(r.get("date_precision", "NA")) not in ("NA", "", "None"))
    L.append(f"Of these, **{n_approx}** now carry an approximate timing "
             f"(`effective_date_approx` + `date_precision`) recovered by Pass 1b; "
             f"`effective_date` stays NA (reserved for verbatim ISO days).\n")
    for row, info in sorted(held, key=lambda t: t[0]["fund_name"]):
        fn = row["fund_name"] if row["fund_name"] not in ("NA", "") else "(fund_name NA)"
        ap = str(row.get("effective_date_approx", "NA"))
        prec = str(row.get("date_precision", "NA"))
        tag = f" — approx {ap} ({prec})" if prec not in ("NA", "", "None") else ""
        L.append(f"- {fn} — announce {row['announce_date']}{tag} — "
                 f"{info['n_filings']} filing(s): {', '.join(info['accessions'])}")
    if pk_dups:
        L.append("\n## PRIMARY-KEY COLLISIONS (need disambiguation)")
        for k in pk_dups:
            L.append(f"- {k}")
    REPORT.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
