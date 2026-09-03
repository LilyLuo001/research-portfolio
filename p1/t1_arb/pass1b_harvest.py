# -*- coding: utf-8 -*-
"""BOX-ONLY. Pass 1b — subsequent-filing harvest for still-undated conversions.

For every held-back conversion that Pass 1 could NOT date (no recovered_dates
entry), find the registrant's SUBSEQUENT EDGAR filings that typically carry the
completed conversion date — 485BPOS post-effective amendments, 497/497K
stickers, N-CEN annual reports, N-8F (deregistration of the old fund at close),
24F-2NT — via the free submissions API (data.sec.gov, no LLM), and download
their primary documents to p1/edgar_filings_1b/.

Writes p1/t1_arb/pass1b_candidates.json:
  {rep_accession: {"fund","family","announce","pending_flag",
                   "cands":[{cik,accession,form,filed,url,path}]}}
keyed by the conversion's representative accession (== the id used by
build_daterecover_spec / recovered_dates overlay), so the extraction merge maps
recovered dates straight back onto the conversion.

Usage (on box, venv active, EDGAR_CONTACT set):
    python p1/t1_arb/pass1b_harvest.py --size       # count candidates, no download
    python p1/t1_arb/pass1b_harvest.py              # download primary docs
"""
from __future__ import print_function
import argparse
import json
import os
import re
import sys
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HELD = os.path.join(ROOT, "p1", "t1_arb", "held_back.json")
RECOVERED = os.path.join(ROOT, "p1", "t1_arb", "recovered_dates.json")
OUT_DIR = os.path.join(ROOT, "p1", "edgar_filings_1b")
CAND = os.path.join(ROOT, "p1", "t1_arb", "pass1b_candidates.json")

SUB_URL = "https://data.sec.gov/submissions/CIK{cik:0>10}.json"
DOC_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc_nodash}/{doc}"
# forms that carry a COMPLETED / effective conversion date (not the pre-close proxy).
# N-8F = deregistration of the merged-away fund (filed AT close, small, decisive);
# 485BPOS/497 carry "the Fund is the successor to X" retrospective language;
# N-CEN lists reorganizations. 497K (summary sticker) / N-1A (registration) dropped:
# high-volume, low-signal, rarely state the specific closing day.
TARGET_FORMS = {"485BPOS", "485APOS", "497", "N-CEN", "N-8F", "24F-2NT", "N-14/A"}
MAX_CAND = 6           # cap candidate docs per conversion (nearest-after-announce first)
SLEEP_S = 0.15
TODAY = time.strftime("%Y-%m-%d")


def ua():
    contact = os.environ.get("EDGAR_CONTACT", "").strip()
    if not contact or "@" not in contact:
        sys.exit("EDGAR_CONTACT env var (your email) is required — SEC fair-use policy.")
    return {"User-Agent": "research-portfolio P1 pass1b harvest {0}".format(contact)}


def get(url, headers, tries=4):
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, headers=headers, timeout=30)
        except requests.exceptions.RequestException as e:
            last = e
            time.sleep(1.5 * (i + 1))
            continue
        if r.status_code in (429, 500, 502, 503):
            time.sleep(1.5 * (i + 1))
            continue
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r
    raise RuntimeError("gave up: {0} (last: {1})".format(url, last))


def undated_conversions():
    held = json.load(open(HELD))["held"]
    rec = set(json.load(open(RECOVERED)).get("recovered", {}))
    out = []
    for h in held:
        accs = [a["id"] for a in h["accessions"]]
        if any(a in rec for a in accs):
            continue                      # already dated by Pass 1
        ciks = []
        for a in h["accessions"]:
            m = re.search(r"/data/(\d+)/", a.get("url", ""))
            if m and m.group(1) not in ciks:
                ciks.append(m.group(1))
        out.append({
            "rep": h["accessions"][0]["id"],
            "fund": h["fund_name"], "family": h["family"],
            "announce": h.get("announce_date") or "0000-00-00",
            "ciks": ciks,
            "held_accs": set(accs),
        })
    return out


def submissions(cik, headers):
    r = get(SUB_URL.format(cik=cik), headers)
    if r is None:
        return []
    js = r.json()
    rec = js.get("filings", {}).get("recent", {})
    keys = ("accessionNumber", "filingDate", "form", "primaryDocument")
    cols = [rec.get(k, []) for k in keys]
    return list(zip(*cols)) if all(cols) else []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", action="store_true", help="count candidates, no downloads")
    args = ap.parse_args()
    headers = ua()
    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)

    convs = undated_conversions()
    print("undated conversions: {0}".format(len(convs)))
    result, n_dl, n_pending, sub_cache = {}, 0, 0, {}
    for c in convs:
        announce = c["announce"]
        # future-pending heuristic: announced but no completion possible yet
        cands = []
        for cik in c["ciks"]:
            if cik not in sub_cache:
                sub_cache[cik] = submissions(cik, headers)
                time.sleep(SLEEP_S)
            for acc, filed, form, doc in sub_cache[cik]:
                if form not in TARGET_FORMS:
                    continue
                if filed <= announce:            # must be AFTER the conversion was announced
                    continue
                if acc in c["held_accs"]:
                    continue                     # already in our package
                cands.append({"cik": cik, "accession": acc, "form": form,
                              "filed": filed, "doc": doc})
        # nearest-after-announce first, cap
        cands.sort(key=lambda x: x["filed"])
        cands = cands[:MAX_CAND]
        pending = len(cands) == 0
        if pending:
            n_pending += 1
        for cd in cands:
            acc_nodash = cd["accession"].replace("-", "")
            cd["url"] = DOC_URL.format(cik=cd["cik"], acc_nodash=acc_nodash, doc=cd["doc"])
            cd["path"] = os.path.join(OUT_DIR, "{0}_{1}.htm".format(cd["cik"], cd["accession"]))
            if not args.size and not os.path.exists(cd["path"]):
                resp = get(cd["url"], headers)
                if resp is not None:
                    with open(cd["path"] + ".part", "wb") as fh:
                        fh.write(resp.content)
                    os.rename(cd["path"] + ".part", cd["path"])
                    n_dl += 1
                    time.sleep(SLEEP_S)
        result[c["rep"]] = {"fund": c["fund"], "family": c["family"],
                            "announce": announce, "pending_flag": pending,
                            "cands": cands}
    total_cands = sum(len(v["cands"]) for v in result.values())
    if not args.size:
        json.dump({"_meta": {"undated": len(convs), "total_candidates": total_cands,
                             "downloaded": n_dl, "no_subsequent_filing": n_pending,
                             "built": TODAY}, "conversions": result},
                  open(CAND, "w"), indent=1)
    print("candidate subsequent filings: {0} across {1} conversions | "
          "{2} conversions have NO subsequent target filing (likely future-pending)"
          .format(total_cands, len(convs), n_pending))
    if not args.size:
        print("downloaded {0} new docs -> {1}".format(n_dl, OUT_DIR))
        print("wrote {0}".format(CAND))


if __name__ == "__main__":
    main()
