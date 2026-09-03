"""Refetch each relevant registrant's filing history into one flat table.

Everything downstream that needs to ask "what did this trust file, and when"
reads this table: the corpus sweep for completion statements, the per-event
escalation, and the date-recovery search. It is the index, not the documents.

EDGAR paginates a long filer's history -- the submissions JSON carries the most
recent block inline and older blocks as sibling files -- so both are followed.
A fund trust that has filed for thirty years will otherwise silently return only
its last thousand filings, which for these registrants is about four years and
would quietly truncate every search window before 2022.

The CIK set is closed: it is the predecessor and successor registrants of the
event register plus every N-14 filer, which is exactly the set of parties that
can make a statement about one of these transactions.
"""
import json
import sys

import pandas as pd

import fetchlib
from paths import CACHE, SUBMISSIONS

BASE = "https://data.sec.gov/submissions"
KEEP = ["form", "filingDate", "accessionNumber", "primaryDocument", "reportDate"]


def ciks():
    out = set()
    ev = CACHE / "events_master_v2_stage3.csv"
    if ev.exists():
        e = pd.read_csv(ev)
        for c in ("pre_cik", "post_cik"):
            out |= {int(x) for x in e[c].dropna()}
    led = CACHE / "classification_ledger.csv"
    if led.exists():
        d = pd.read_csv(led)
        for c in ("tgt_cik", "acq_cik"):
            if c in d:
                out |= {int(x) for x in pd.to_numeric(d[c], errors="coerce").dropna()}
    return sorted(out)


def blocks(cik):
    """The inline recent block plus every paginated older block, as dicts."""
    p = fetchlib.get(f"{BASE}/CIK{cik:010d}.json",
                     SUBMISSIONS / f"CIK{cik:010d}.json",
                     kind="edgar_submissions")
    if not p:
        return []
    try:
        j = json.load(open(p))
    except Exception:
        return []
    out = [j.get("filings", {}).get("recent", {})]
    for extra in j.get("filings", {}).get("files", []):
        name = extra.get("name")
        if not name:
            continue
        q = fetchlib.get(f"{BASE}/{name}", SUBMISSIONS / name,
                         kind="edgar_submissions_page")
        if q:
            try:
                out.append(json.load(open(q)))
            except Exception:
                pass
    return out


def main():
    cs = ciks()
    print(f"registrants to index: {len(cs)}", flush=True)
    rows = []
    for n, cik in enumerate(cs, 1):
        for b in blocks(cik):
            if not b.get("accessionNumber"):
                continue
            df = pd.DataFrame({k: b.get(k, []) for k in KEEP})
            df["cik"] = cik
            rows.append(df)
        if n % 25 == 0:
            print(f"  {n}/{len(cs)}  rows so far {sum(len(r) for r in rows):,d}",
                  flush=True)

    sub = pd.concat(rows, ignore_index=True).rename(columns={
        "filingDate": "filed", "accessionNumber": "acc",
        "primaryDocument": "doc", "reportDate": "report_date"})
    sub = sub.dropna(subset=["acc"]).drop_duplicates(["cik", "acc"])
    out = CACHE / "submissions_flat.parquet"
    sub.to_parquet(out, index=False)
    fetchlib.record(out, kind="derived", parser="fetch_submissions.py",
                    extra={"lineage": "raw/submissions/*.json", "registrants": len(cs)})

    print(f"\nregistrants : {sub.cik.nunique():,d}")
    print(f"filings     : {len(sub):,d}")
    print(f"date range  : {sub.filed.min()} .. {sub.filed.max()}")
    print("\ntop forms:")
    print(sub.form.value_counts().head(12).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
