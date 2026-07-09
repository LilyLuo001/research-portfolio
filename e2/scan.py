#!/usr/bin/env python3
# e2/scan.py — E2-T11a: biweekly literature squat-scan (kill criterion #3).
# Deterministic, NO LLM (v1.1 manual §T11 corrected assignment): arXiv API +
# Semantic Scholar API over a fixed bilingual keyword list, last 21 days.
# SSRN has no stable public API — per spec this script only GENERATES manual
# search URLs for a human to click; it does not fabricate an SSRN interface.
#
# Outputs (under e2/scans/):
#   hits_YYYYMMDD.csv    [标题, 作者, 日期, 摘要, 链接, 来源]  — new hits only
#   hits_YYYYMMDD.jsonl  same records, one JSON object per line (triage input)
#   ssrn_manual_YYYYMMDD.txt   SSRN search URLs for manual click-through
#   seen_ids.json        cross-run dedup registry (id -> first_seen date)
#
# Exit code 0 always on clean run (0 new hits is a normal outcome); nonzero
# only on total source failure (both APIs unreachable) so cron surfaces it.
#
# Cron: wired into ops/box/cron_night.sh (02:00, after the L1 driver); outputs
# are committed by the 21:00 evening digest tick. Box venv is Python 3.6 —
# keep this file 3.6-compatible (no dataclasses, no fromisoformat, stdlib only).

import argparse
import csv
import datetime
import io
import json
import re
import sys
import time
import xml.etree.ElementTree as ET

try:
    from urllib.request import urlopen, Request
    from urllib.parse import quote_plus, urlencode
    from urllib.error import HTTPError, URLError
except ImportError:  # pragma: no cover
    raise SystemExit("python3 required")

from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTDIR = HERE / "scans"
SEEN_PATH = OUTDIR / "seen_ids.json"

WINDOW_DAYS = 21

# Fixed bilingual list — verbatim from manual v1.1 §T11 / Prompt T11a.
KEYWORDS = [
    "RWA looping",
    "tokenized collateral rehypothecation",
    "embedded leverage DeFi",
    "tokenized treasury lending",
    "NAV oracle liquidation",
    "RWA 循环",
    "代币化资产 抵押 杠杆",
]

UA = "portfolio-e2-t11-scan/1.0 (research literature monitor)"
ATOM = "{http://www.w3.org/2005/Atom}"


def http_get(url, tries=4, base_sleep=5, headers=None):
    last = None
    for i in range(tries):
        try:
            h = {"User-Agent": UA}
            h.update(headers or {})
            req = Request(url, headers=h)
            with urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except HTTPError as e:
            last = e
            if e.code == 429:  # unauthenticated S2 pool is tight; back off hard
                time.sleep(base_sleep * (2 ** i) * 3)
                continue
            if 500 <= e.code < 600:
                time.sleep(base_sleep * (2 ** i))
                continue
            raise
        except URLError as e:
            last = e
            time.sleep(base_sleep * (2 ** i))
    raise last


def norm_key(title):
    return re.sub(r"[^a-z0-9一-鿿]+", "", (title or "").lower())


def parse_date(s):
    if not s:
        return None
    try:
        return datetime.datetime.strptime(s[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def arxiv_search(keyword, cutoff):
    q = urlencode({
        "search_query": 'all:"%s"' % keyword,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": "50",
    })
    body = http_get("https://export.arxiv.org/api/query?" + q)
    hits = []
    for entry in ET.fromstring(body).findall(ATOM + "entry"):
        pub = parse_date((entry.findtext(ATOM + "published") or ""))
        if pub is None or pub < cutoff:
            continue
        link = (entry.findtext(ATOM + "id") or "").strip()
        hits.append({
            "id": "arxiv:" + link.rsplit("/", 1)[-1],
            "title": re.sub(r"\s+", " ", entry.findtext(ATOM + "title") or "").strip(),
            "authors": "; ".join(
                (a.findtext(ATOM + "name") or "").strip()
                for a in entry.findall(ATOM + "author")),
            "date": pub.isoformat(),
            "abstract": re.sub(r"\s+", " ", entry.findtext(ATOM + "summary") or "").strip(),
            "url": link,
            "source": "arXiv",
            "keyword": keyword,
        })
    return hits


def s2_search_bulk(cutoff):
    # One bulk call for ALL keywords (boolean OR) — the unauthenticated S2
    # pool 429s hard under 7 separate /paper/search calls (observed live
    # 2026-07-09). Free key via env S2_API_KEY lifts the shared-pool limit.
    import os
    q = urlencode({
        "query": " | ".join('"%s"' % k for k in KEYWORDS),
        "fields": "title,authors,abstract,url,publicationDate,externalIds",
        # server-side prefilter; local date check below remains authoritative
        "publicationDateOrYear": cutoff.isoformat() + ":",
    })
    key = os.getenv("S2_API_KEY")
    body = http_get(
        "https://api.semanticscholar.org/graph/v1/paper/search/bulk?" + q,
        base_sleep=20, headers={"x-api-key": key} if key else None)
    hits = []
    for p in (json.loads(body).get("data") or []):
        pub = parse_date(p.get("publicationDate"))
        if pub is None or pub < cutoff:
            continue
        ext = p.get("externalIds") or {}
        pid = ("doi:" + ext["DOI"]) if ext.get("DOI") else \
              ("arxiv:" + ext["ArXiv"]) if ext.get("ArXiv") else \
              ("s2:" + (p.get("paperId") or ""))
        hits.append({
            "id": pid,
            "title": (p.get("title") or "").strip(),
            "authors": "; ".join((a.get("name") or "") for a in (p.get("authors") or [])),
            "date": pub.isoformat(),
            "abstract": re.sub(r"\s+", " ", p.get("abstract") or "").strip(),
            "url": p.get("url") or "",
            "source": "SemanticScholar",
            "keyword": "s2-bulk",
        })
    return hits


def ssrn_manual_urls():
    # No stable public SSRN API (spec: do NOT fabricate one) — manual links only.
    return ["https://www.ssrn.com/index.cfm/en/search/?term=" + quote_plus(k)
            for k in KEYWORDS]


def load_seen():
    if SEEN_PATH.exists():
        return json.loads(SEEN_PATH.read_text())
    return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true",
                    help="ignore seen_ids.json — report every in-window hit")
    a = ap.parse_args()

    today = datetime.datetime.utcnow().date()
    cutoff = today - datetime.timedelta(days=WINDOW_DAYS)
    OUTDIR.mkdir(exist_ok=True)
    seen = {} if a.full else load_seen()

    collected, errors, n_legs = {}, [], len(KEYWORDS) + 1

    def take(batch):
        for h in batch:
            key = h["id"] if not h["id"].startswith("s2:") else norm_key(h["title"])
            tkey = norm_key(h["title"])
            if key in collected or tkey in collected:
                prev = collected.get(key) or collected.get(tkey)
                if h["keyword"] not in prev["keyword"]:
                    prev["keyword"] += ", " + h["keyword"]
                continue
            if key in seen or tkey in seen:
                continue
            h["dedup_key"] = key
            collected[key] = h
            collected.setdefault(tkey, h)

    for kw in KEYWORDS:
        try:
            take(arxiv_search(kw, cutoff))
        except Exception as e:
            errors.append("arxiv %r: %s" % (kw, e))
        time.sleep(3)  # arXiv asks >=3s between calls
    try:
        take(s2_search_bulk(cutoff))
    except Exception as e:
        errors.append("s2-bulk: %s" % e)

    if len(errors) == n_legs:
        print("FATAL: every API call failed:\n  " + "\n  ".join(errors), file=sys.stderr)
        return 1

    hits = sorted({id(h): h for h in collected.values()}.values(),
                  key=lambda h: (h["date"], h["title"]), reverse=True)
    stamp = today.strftime("%Y%m%d")

    with io.open(str(OUTDIR / ("hits_%s.csv" % stamp)), "w",
                 encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["标题", "作者", "日期", "摘要", "链接", "来源"])
        for h in hits:
            w.writerow([h["title"], h["authors"], h["date"],
                        h["abstract"], h["url"], h["source"]])

    with io.open(str(OUTDIR / ("hits_%s.jsonl" % stamp)), "w", encoding="utf-8") as f:
        for h in hits:
            f.write(json.dumps(h, ensure_ascii=False) + "\n")

    with io.open(str(OUTDIR / ("ssrn_manual_%s.txt" % stamp)), "w", encoding="utf-8") as f:
        f.write("# SSRN has no stable public API — click these by hand "
                "(spec T11a item 2):\n")
        for u in ssrn_manual_urls():
            f.write(u + "\n")

    if not a.full:
        for h in hits:
            seen[h["dedup_key"]] = today.isoformat()
            seen[norm_key(h["title"])] = today.isoformat()
        SEEN_PATH.write_text(json.dumps(seen, indent=0, sort_keys=True))

    print("scan %s: %d new hit(s), window %s..%s, %d source error(s)%s"
          % (stamp, len(hits), cutoff, today, len(errors),
             (" — " + "; ".join(errors)) if errors else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
