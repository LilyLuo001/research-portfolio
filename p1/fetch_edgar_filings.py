# -*- coding: utf-8 -*-
"""P1 — EDGAR filing-package harvester (L0, deterministic, no LLM).

Builds the /edgar_filings/ package that BOTH P1-T1-events and P1-T13-ant
extract from (manual §4 T1: "输入:文件目录 /edgar_filings/"; 修订4 T13:
"数据来源: 我提供的 EDGAR 文件包"). Until this has run, neither task's
L1 batch can be spec'd — this script is the unlock for all four post-gate
overnight batches (P1-T1-events A/B, P1-T13-ant A/B).

What it does (idempotent, resumable):
  1. EDGAR full-text search (efts.sec.gov) for conversion language in
     497 / 497K / N-14 / N-8A / N-1A filings, 2019-01-01 → today
     (T13 needs 2019-11+ for ANT listings; T1's anchor wave is 2021-06).
  2. Downloads each hit's primary document to p1/edgar_filings/
     <CIK>_<accession>.htm (skips files that already exist).
  3. Writes p1/edgar_filings/manifest.csv:
     cik,accession,form,filed,company,query_phrase,source_url
     — every downstream extraction row must carry one of these locators
     (meta-rule 1).

SEC fair-use compliance: declared User-Agent (set EDGAR_CONTACT in the
environment to your email — refuses to run without it), <= 8 req/s with a
0.15s sleep, retry with backoff on 429/503.

RUN ON THE BOX (this container's proxy blocks sec.gov):
    cd ~/portfolio && . .venv/bin/activate
    EDGAR_CONTACT=you@example.com python p1/fetch_edgar_filings.py --limit 50   # smoke
    EDGAR_CONTACT=you@example.com python p1/fetch_edgar_filings.py             # full

python 3.6 compatible (box venv). requests only.
"""
from __future__ import print_function
import argparse
import csv
import os
import re
import sys
import time

import requests

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(ROOT, "edgar_filings")
MANIFEST = os.path.join(OUT_DIR, "manifest.csv")
FTS_URL = "https://efts.sec.gov/LATEST/search-index?q={q}&forms={forms}&startdt={start}&enddt={end}&from={offset}"
DOC_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc_nodash}/{doc}"

# Conversion language, quoted phrases per EDGAR fts syntax. Two families:
# T1 (MF->ETF conversion) and T13 (semi-transparent / ANT structures).
QUERIES = [
    '"conversion of the fund into an exchange-traded fund"',
    '"convert the fund to an exchange-traded fund"',
    '"mutual fund to ETF conversion"',
    '"conversion of each fund into an ETF"',
    # K-4 (audit 2026-07-10): conversion family was too narrow — filings often
    # use reorganization/restructuring language. Union of both seats' K-4
    # expansions. Terms anchored to ETF context; bare "reorganization"/
    # "statutory trust" would match thousands of unrelated mergers and
    # DE-trust filings. The '"into an exchange-traded fund"' anchor subsumes
    # any phrase that contains it.
    '"into an exchange-traded fund"',
    '"reorganization of the fund into an exchange-traded fund"',
    '"reorganization" "into an ETF"',
    '"restructuring" "into an exchange-traded fund"',
    '"statutory trust" "into an exchange-traded fund"',
    '"fund conversion"',
    '"conversion to an exchange-traded fund"',
    '"reorganization of the target fund into"',
    '"converting the fund to an exchange-traded fund"',
    '"semi-transparent exchange-traded fund"',
    '"ActiveShares"',
    '"proxy portfolio" "exchange-traded fund"',
]
FORMS = "497,497K,N-14,N-8A,N-1A"
START, END = "2019-01-01", time.strftime("%Y-%m-%d")
SLEEP_S = 0.15
MAX_PAGES = 100         # raised from 20 (audit T-1/K-4: ActiveShares hit 228 > old 200
                        # cap; the broadened queries reach ~476 — 2026-07-10 re-run
                        # confirmed no truncation warnings at 1000)


def ua():
    contact = os.environ.get("EDGAR_CONTACT", "").strip()
    if not contact or "@" not in contact:
        sys.exit("EDGAR_CONTACT env var (your email) is required — SEC fair-use policy.")
    return {"User-Agent": "research-portfolio P1 event harvest {0}".format(contact)}


def get(url, headers, tries=4):
    for i in range(tries):
        r = requests.get(url, headers=headers, timeout=30)
        # efts.sec.gov intermittently 500s on paginated queries (same offset
        # succeeds on retry) — observed 2026-07-10 during the K-4 re-run
        if r.status_code in (429, 500, 502, 503):
            time.sleep(2.0 * (i + 1))
            continue
        r.raise_for_status()
        return r
    raise RuntimeError("gave up after {0} tries: {1}".format(tries, url))


def search(query, headers, offset=0):
    url = FTS_URL.format(q=requests.utils.quote(query), forms=FORMS,
                         start=START, end=END, offset=offset)
    return get(url, headers).json()


def hit_rows(js, query):
    for h in js.get("hits", {}).get("hits", []):
        src = h.get("_source", {})
        acc = src.get("adsh", "")
        ciks = src.get("ciks", [])
        cik = ciks[0].lstrip("0") if ciks else ""
        names = src.get("display_names", [])
        doc_id = h.get("_id", "")            # "<adsh>:<document name>"
        doc = doc_id.split(":", 1)[1] if ":" in doc_id else ""
        yield {
            "cik": cik, "accession": acc,
            "form": src.get("file_type") or src.get("root_forms", [""])[0] if src.get("root_forms") else src.get("file_type", ""),
            "filed": src.get("file_date", ""),
            "company": names[0] if names else "",
            "query_phrase": query,
            "doc": doc,
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="stop after N downloads (smoke run)")
    args = ap.parse_args()
    headers = ua()
    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)

    seen = {}
    rows = []
    for q in QUERIES:
        offset, total = 0, None
        while offset < MAX_PAGES * 10:
            js = search(q, headers, offset)
            time.sleep(SLEEP_S)
            if total is None:
                total = js.get("hits", {}).get("total", {}).get("value", 0)
                print("query {0!r}: {1} hits".format(q, total))
                if total > MAX_PAGES * 10:
                    print("  WARNING: {0} hits > page cap {1} — results TRUNCATED; "
                          "raise MAX_PAGES or narrow the query (audit 2026-07-10)"
                          .format(total, MAX_PAGES * 10))
            got = list(hit_rows(js, q))
            if not got:
                break
            for r in got:
                key = (r["cik"], r["accession"])
                if key not in seen and r["cik"] and r["accession"] and r["doc"]:
                    seen[key] = True
                    rows.append(r)
            offset += 10
            if offset >= total:
                break

    print("{0} unique filings across {1} queries".format(len(rows), len(QUERIES)))
    n_dl = 0
    with open(MANIFEST, "w") as f:
        w = csv.DictWriter(f, fieldnames=["cik", "accession", "form", "filed",
                                          "company", "query_phrase", "source_url"])
        w.writeheader()
        for r in rows:
            acc_nodash = r["accession"].replace("-", "")
            url = DOC_URL.format(cik=r["cik"], acc_nodash=acc_nodash, doc=r["doc"])
            dest = os.path.join(OUT_DIR, "{0}_{1}.htm".format(r["cik"], r["accession"]))
            r2 = dict((k, r[k]) for k in ("cik", "accession", "form", "filed",
                                          "company", "query_phrase"))
            r2["source_url"] = url
            w.writerow(r2)
            if os.path.exists(dest):
                continue
            if args.limit and n_dl >= args.limit:
                continue
            try:
                resp = get(url, headers)
                # write-then-rename: a crash mid-write must not leave a partial
                # file that the skip-if-exists resume would treat as complete
                with open(dest + ".part", "wb") as fh:
                    fh.write(resp.content)
                os.rename(dest + ".part", dest)
                n_dl += 1
                time.sleep(SLEEP_S)
            except Exception as e:                      # noqa: BLE001
                print("  DOWNLOAD-FAIL {0} {1}: {2}".format(r["cik"], r["accession"], e))
    print("downloaded {0} new files; manifest at {1}".format(n_dl, MANIFEST))
    # basic sanity asserts (rule: every step asserts)
    assert os.path.exists(MANIFEST)
    n_manifest = sum(1 for _ in open(MANIFEST)) - 1
    assert n_manifest == len(rows), "manifest rows != unique hits"
    print("OK: {0} manifest rows".format(n_manifest))


if __name__ == "__main__":
    main()
