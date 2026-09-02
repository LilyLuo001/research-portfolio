"""Escalate the still-open pairs one at a time, newest evidence first, stopping early.

A blind sweep of the filing chain is the wrong shape for this problem. Sixteen
open pairs sit inside trusts like Goldman Sachs and BlackRock that file hundreds
of supplements a year, so the sweep costs ~2,650 documents -- 165 per pair -- and
most of them are prospectuses for unrelated series. Worse, the documents are not
uniformly sized: a "497" is sometimes a two-page supplement and sometimes a 12 MB
restated prospectus, so throughput is bandwidth-bound and unpredictable.

So this fetches per event instead, in ascending distance from the date the
conversion is expected to have closed, and stops that event as soon as an
attributable completion statement is found. The window is not truncated -- every
document in it remains reachable -- but the ones most likely to answer the
question are read first. That is the opposite of a document cap: a cap discards
the tail of the window, this reorders it.

The expected close is bracketed by the predecessor's last N-CEN period and its
registrant's next annual filing, which is the only thing known before reading.
"""
import ssl
import sys
import time
import urllib.request

import certifi
import pandas as pd

import parse_escalation as PE
from build_completion_evidence import names_match

from paths import CACHE as HERE  # data lives outside the repo; see paths.py
CACHE = HERE / "escalation"
SUP497 = HERE / "sup497"
UA = "Qingyan Luo luoqingyan166@gmail.com"
CTX = ssl.create_default_context(cafile=certifi.where())
WINDOW_DAYS = 540
FORMS = ["497", "497K", "N-14/A", "485BPOS", "N-CSR", "N-CSRS"]
# a single event is allowed this many documents before it is given up on, purely
# to stop one pathological trust from consuming the whole run
MAX_PER_EVENT = 120


def fetch(acc, cik, doc):
    for d in (CACHE, SUP497):
        p = d / f"{acc}.html"
        if p.exists() and p.stat().st_size:
            return p
    dest = CACHE / f"{acc}.html"
    url = (f"https://www.sec.gov/Archives/edgar/data/{cik}/"
           f"{acc.replace('-', '')}/{doc}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=90, context=CTX) as resp:
            dest.write_bytes(resp.read())
    except Exception as e:
        dest.with_suffix(".err").write_text(f"{type(e).__name__}: {e}")
        return None
    time.sleep(0.34)
    return dest


def statements(path):
    """Completion sentences in one document, as (date, pattern, context)."""
    try:
        t = PE.text_of(path)
    except Exception:
        return []
    out = []
    for pat, nm in PE.ALL_PATS:
        for m in pat.finditer(t):
            ctx = t[max(0, m.start() - 250):m.end() + 450]
            if PE.NEG.search(ctx):
                continue
            d = pd.to_datetime(m.group(1), errors="coerce")
            if pd.notna(d):
                out.append((d, nm, ctx))
            break
    return out


def main():
    ev = pd.read_csv(HERE / "events_master_v2_stage3.csv")
    open_ = ev[(ev.final_tier == "unresolved")
               | (ev.final_tier.str.startswith(("A_", "B_"), na=False)
                  & ev.final_year.isna())]
    print(f"pairs still open (unresolved or year-ambiguous): {len(open_)}", flush=True)

    sub = pd.read_parquet(HERE / "submissions_flat.parquet")
    sub["filed"] = pd.to_datetime(sub.filed, errors="coerce")
    sub = sub[sub.form.isin(FORMS)].drop_duplicates("acc")

    found, rows = 0, []
    for n, r in enumerate(open_.itertuples(index=False), 1):
        lo = pd.to_datetime(r.n14_first_filed)
        hi = pd.to_datetime(r.n14_last_filed) + pd.Timedelta(days=WINDOW_DAYS)
        # best guess at when it closed, used only to order the reading
        guess = pd.to_datetime(r.cease_window_hi) if pd.notna(r.cease_window_hi) \
            else pd.to_datetime(r.n14_last_filed) + pd.Timedelta(days=90)
        ciks = {int(c) for c in (r.pre_cik, r.post_cik) if pd.notna(c)}
        g = sub[sub.cik.isin(ciks) & (sub.filed >= lo) & (sub.filed <= hi)].copy()
        g["d"] = (g.filed - guess).abs()
        g = g.sort_values("d").head(MAX_PER_EVENT)

        hit = None
        for k, x in enumerate(g.itertuples(index=False), 1):
            p = fetch(x.acc, x.cik, x.doc)
            if p is None:
                continue
            for d, nm, ctx in statements(p):
                if not (lo <= d <= hi):
                    continue
                if not names_match(ctx, r.pre_series_name, r.post_series_name):
                    continue
                hit = {"pre_series_id": r.pre_series_id, "acc": x.acc,
                       "form": x.form, "close_date": d, "pattern": nm,
                       "context": ctx[:400], "docs_read": k}
                break
            if hit:
                break
        if hit:
            found += 1
            rows.append(hit)
            print(f"  [{n}/{len(open_)}] {r.pre_series_name[:44]:<44} "
                  f"-> {hit['close_date']:%Y-%m-%d} after {hit['docs_read']} docs",
                  flush=True)
        else:
            print(f"  [{n}/{len(open_)}] {r.pre_series_name[:44]:<44} "
                  f"-> nothing in {len(g)} docs", flush=True)

    d = pd.DataFrame(rows)
    d.to_csv(HERE / "escalation_resolved.csv", index=False)
    print(f"\nresolved by escalation: {found}/{len(open_)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
