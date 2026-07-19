#!/usr/bin/env python3
"""Full per-filing audit export of the adjudicated T1 channel.

One row per (filing × event), plus one row per no_event / NEED_HUMAN filing, so
all 1418 harvested filings are represented and manually verifiable. Emits:
  p1/t1_full_audit.csv   — flat, sortable, every field + provenance
  p1/t1_full_audit.json  — same rows, plus a summary block

study_status tells you exactly why each row is / isn't in events_merged.csv:
  in_events_merged      — event with a resolved effective_date (feeds the study)
  held_needs_fulltext   — event, but no effective_date resolved yet
  excluded_spotcheck:*  — owner Gate-1 correction (not_event / recheck / defer)
  no_event:<reason>     — deepseek/qwen/owner ruled not a MF->ETF conversion
"""
import csv
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
P1 = HERE.parent
FINAL = P1 / "t1_events_final.json"
META = HERE / "id_meta.json"
RECOV = HERE / "recovered_dates.json"
OUT_CSV = P1 / "t1_full_audit.csv"
OUT_JSON = P1 / "t1_full_audit.json"

COLS = ["source_accession", "company", "form", "filed", "verdict", "reason",
        "study_status", "fund_name", "family", "mutual_fund_ticker", "etf_ticker",
        "announce_date", "effective_date", "effective_date_source", "asset_class",
        "AUM_at_conversion_USD", "confidence", "evidence", "adjudication_source",
        "spotcheck_disposition", "source_url"]
ISO = __import__("re").compile(r"^\d{4}-\d{2}-\d{2}$")


def main():
    final = json.loads(FINAL.read_text())
    meta = json.loads(META.read_text())
    overlay = json.loads(RECOV.read_text()).get("recovered", {}) if RECOV.exists() else {}

    rows = []
    for fid, v in final.items():
        if fid == "_meta":
            continue
        m = meta.get(fid, {})
        base = {"source_accession": fid, "company": m.get("company", ""),
                "form": m.get("form", ""), "filed": m.get("filed", ""),
                "source_url": m.get("url", ""),
                "adjudication_source": (v.get("_adjudication") or {}).get("source", "deepseek-v2A")}
        if v.get("NEED_HUMAN"):
            rows.append({**{c: "" for c in COLS}, **base, "verdict": "NEED_HUMAN",
                         "study_status": "NEED_HUMAN", "evidence": json.dumps(v.get("quotes", ""))[:300]})
            continue
        if v.get("no_event"):
            fsc = v.get("_spotcheck") or {}
            status = f"no_event:{v.get('reason','')}"
            if fsc.get("disposition"):
                status = f"{fsc['disposition']}(was no_event:{v.get('reason','')})"
            rows.append({**{c: "" for c in COLS}, **base, "verdict": "no_event",
                         "reason": v.get("reason", ""), "study_status": status,
                         "spotcheck_disposition": fsc.get("disposition", ""),
                         "evidence": str(v.get("evidence", ""))[:300]})
            continue
        for e in (v["events"] if "events" in v else [v]):
            eff = str(e.get("effective_date", "NA"))
            eff_src = "extraction"
            if not ISO.match(eff) and fid in overlay and ISO.match(str(overlay[fid].get("effective_date", ""))):
                eff, eff_src = overlay[fid]["effective_date"], "full-text-recovery"
            sc = e.get("_spotcheck") or {}
            if sc.get("disposition") in ("not_event", "recheck", "defer"):
                status = f"excluded_spotcheck:{sc['disposition']}"
            elif ISO.match(eff):
                status = "in_events_merged"
            else:
                status = "held_needs_fulltext"
            rows.append({**base, "verdict": "event", "reason": "",
                         "study_status": status,
                         "fund_name": str(e.get("fund_name", "")),
                         "family": str(e.get("family", "")),
                         "mutual_fund_ticker": str(e.get("mutual_fund_ticker", "")),
                         "etf_ticker": str(e.get("etf_ticker", "")),
                         "announce_date": str(e.get("announce_date", "")),
                         "effective_date": eff, "effective_date_source": eff_src,
                         "asset_class": str(e.get("asset_class", "")),
                         "AUM_at_conversion_USD": str(e.get("AUM_at_conversion_USD", "")),
                         "confidence": str(e.get("confidence", "")),
                         "evidence": str(e.get("evidence", ""))[:300],
                         "spotcheck_disposition": sc.get("disposition", "")})

    rows.sort(key=lambda r: (r["verdict"] != "event", r.get("study_status", ""),
                             r.get("effective_date", ""), r["source_accession"]))
    with OUT_CSV.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLS})

    import collections
    summ = collections.Counter(r["verdict"] for r in rows)
    stat = collections.Counter(r["study_status"] for r in rows)
    OUT_JSON.write_text(json.dumps(
        {"_meta": {"total_rows": len(rows), "distinct_filings": len({r["source_accession"] for r in rows}),
                   "by_verdict": dict(summ), "by_study_status": dict(stat),
                   "note": "one row per filing×event (+ one per no_event/NEED_HUMAN filing); "
                           "events_merged.csv = the in_events_merged rows collapsed to unique conversions"}},
        indent=1))
    # append the full rows to the json under 'rows'
    doc = json.loads(OUT_JSON.read_text())
    doc["rows"] = rows
    OUT_JSON.write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    print(f"wrote {OUT_CSV.name} & {OUT_JSON.name}: {len(rows)} rows over "
          f"{len({r['source_accession'] for r in rows})} filings")
    print("  by_verdict:", dict(summ))
    print("  by_study_status:", dict(stat))


if __name__ == "__main__":
    main()
