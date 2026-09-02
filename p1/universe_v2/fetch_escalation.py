"""Fetch the remaining SEC filing chain for pairs the 497 channel could not settle.

The 497 sweep only reads the *predecessor's* supplements. That misses the most
reliable statement of a completed conversion, which the *successor* makes in its
own prospectus and shareholder reports:

    "The Fund is the successor to the Cannabis Growth Fund following the
     reorganization of the Predecessor Fund, which occurred on July 9, 2021"

That sentence appears in the financial-highlights note of the successor's annual
prospectus (485BPOS), in its N-CSR/N-CSRS shareholder reports, and in 497
supplements filed off that prospectus. Forms are fetched in descending order of
observed density so the cheap sources are exhausted before the 497K bulk.

Both CIKs are swept because a conversion moves a fund between trusts and either
side may be the one that describes it.

Fetched in two stages by document size, not by expected yield. A 485BPOS annual
prospectus runs 8-13 MB, so sweeping the whole chain at once costs ~20 GB and
several hours; the supplements that carry the same sentence run a few hundred KB.
Stage "small" is therefore exhausted first and stage "large" is only asked for
what is still unresolved after parsing it.
"""
import ssl
import sys
import time
import urllib.request

import certifi
import pandas as pd

from paths import CACHE as HERE  # data lives outside the repo; see paths.py
CACHE = HERE / "escalation"
SUP497 = HERE / "sup497"
UA = "Qingyan Luo luoqingyan166@gmail.com"
CTX = ssl.create_default_context(cafile=certifi.where())
WINDOW_DAYS = 540

STAGES = {
    # 497 first: smallest documents and the highest observed density of completion
    # sentences. N-14/A last -- it is an amended proxy, so it is prospective and
    # rarely states a close, but the audit asks for the channel to be swept.
    "small": ["497", "497K", "N-14/A"],
    "large": ["485BPOS", "N-CSR", "N-CSRS", "485APOS", "24F-2NT"],
}


def targets(stage):
    FORMS = STAGES[stage]
    ev = pd.read_csv(HERE / "events_master_v2_stage3.csv")
    ev = ev[ev.final_tier == "unresolved"]
    sub = pd.read_parquet(HERE / "submissions_flat.parquet")
    sub["filed"] = pd.to_datetime(sub.filed, errors="coerce")
    sub = sub[sub.form.isin(FORMS)]
    order = {f: i for i, f in enumerate(FORMS)}

    out = {}
    for r in ev.itertuples(index=False):
        lo = pd.to_datetime(r.n14_first_filed)
        if pd.isna(lo):
            continue
        hi = pd.to_datetime(r.n14_last_filed) + pd.Timedelta(days=WINDOW_DAYS)
        for cik in {r.pre_cik, r.post_cik}:
            if pd.isna(cik):
                continue
            g = sub[(sub.cik == int(cik)) & (sub.filed >= lo) & (sub.filed <= hi)]
            for x in g.itertuples(index=False):
                out[x.acc] = (order[x.form], x.cik, x.doc)
    return sorted(out.items(), key=lambda kv: (kv[1][0], kv[0]))


def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else "small"
    CACHE.mkdir(exist_ok=True)
    want = targets(stage)
    print(f"stage={stage} documents to retrieve: {len(want):,d}", flush=True)
    ok = skip = fail = 0
    for i, (acc, (_, cik, doc)) in enumerate(want, 1):
        dest = CACHE / f"{acc}.html"
        # the predecessor-497 sweep already pulled part of this set
        if (SUP497 / f"{acc}.html").exists() or (dest.exists() and dest.stat().st_size):
            skip += 1
            continue
        url = (f"https://www.sec.gov/Archives/edgar/data/{cik}/"
               f"{acc.replace('-', '')}/{doc}")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60, context=CTX) as resp:
                dest.write_bytes(resp.read())
            ok += 1
        except Exception as e:
            dest.with_suffix(".err").write_text(f"{type(e).__name__}: {e}")
            fail += 1
        time.sleep(0.34)
        if i % 200 == 0:
            print(f"  {i}/{len(want)} ok={ok} cached={skip} fail={fail}", flush=True)
    print(f"done. fetched={ok} cached={skip} failed={fail}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
