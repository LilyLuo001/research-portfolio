#!/usr/bin/env python3
# refraction/scan.py — REFR-R13a: monthly collision monitor (plan §11).
# Deterministic, NO LLM (manual §R13 指派: "不依赖 LLM 联网的脚本"): arXiv API +
# Semantic Scholar API over a fixed bilingual keyword list, last 31 days.
# SSRN has no stable public API — per spec this script only GENERATES manual
# search URLs for a human to click; it does not fabricate an SSRN interface.
# Architecture is E2-T11a's corrected one, ported as-is (manual §R13: "E2 T11
# 修正后架构原样搬用"); the keyword list and the hair trigger are refraction's.
#
# Outputs (under refraction/scans/):
#   hits_YYYYMMDD.csv    [标题, 作者, 日期, 摘要, 链接, 来源, 毛刺, ALERT阈值]
#   hits_YYYYMMDD.jsonl  same records, one JSON object per line (R13b input)
#   hairtrigger_YYYYMMDD.md   the 毛刺节, pre-built; empty file if no hits
#   ssrn_manual_YYYYMMDD.txt  SSRN search URLs for manual click-through
#   seen_ids.json        cross-run dedup registry (id -> first_seen date)
#
# Why the hair trigger is computed HERE and not left to the R13b triage model:
# manual §R13b mandates that Marta/Riva authors and replication-technique/switch
# titles are listed in the 毛刺节 "无论初判重叠度如何" and carry a 40% (not 60%)
# ALERT threshold. Author-name and title matching is purely mechanical, so it is
# machine-enforced rather than left to a cheap model's discipline — the house
# pattern for iron rules (cf. refraction/guards/prereg_guard.py). The triage
# model still judges OVERLAP; it may not re-decide 毛刺 membership.
#
# Exit code 0 always on clean run (0 new hits is a normal outcome); nonzero
# only on total source failure (both APIs unreachable) so cron surfaces it.
#
# Cron: wire into ops/box/cron_night.sh next to e2/scan.py; outputs are
# committed by the 21:00 evening digest tick. Box venv is Python 3.6 —
# keep this file 3.6-compatible (no f-strings, no dataclasses, stdlib only).

import argparse
import csv
import datetime
import io
import json
import os
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

# 月度碰撞监测 (manual §R13 title) — E2's T11 is biweekly at 21d; this is monthly.
WINDOW_DAYS = 31

# Fixed bilingual list — the six English strings are verbatim from manual §R13a
# (= plan §11 monitor keywords); the Chinese half satisfies its "中英双语".
KEYWORDS = [
    "ETF basket comovement announcement",
    "conversion comovement",
    "announcement day beta ETF",
    "ETF replication switch comovement",
    "creation basket transmission",
    "passive macro news cross-section",
    "ETF 篮子 共动 宏观公告",
    "基金转换 共动",
    "公告日 beta ETF",
    "复制方式转换 共动",
    "申购篮子 传导",
    "被动投资 宏观信息 横截面",
]

# manual §R13b: 毛刺节 membership. Marta–Riva is the nearest causal neighbour,
# so plan §11 gives it a 40% hair trigger against the 60% general ALERT line.
HAIR_AUTHORS = ["marta", "riva"]
HAIR_TITLE_RE = re.compile(r"replication\s+(technique|switch)", re.I)
ALERT_DEFAULT = 60
ALERT_HAIR = 40

# plan §11 monthly monitor watchlist — recorded on each hit for the triage step;
# does NOT by itself set the hair trigger (only §R13b's two rules do).
WATCH_AUTHORS = ["da", "shive", "greenwood", "marta", "riva", "brogaard",
                 "heath", "huang", "sammon", "ernst", "saglam", "tuzun",
                 "wermers"]

UA = "portfolio-refr-r13-scan/1.0 (research literature monitor)"
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


def _name_tokens(authors):
    """Every alphabetic name token, lowercased. Deliberately over-inclusive."""
    return [t for t in re.split(r"[^a-z\u4e00-\u9fff]+", (authors or "").lower()) if t]


def _surnames(authors):
    """Best-effort surnames. "Ada Marta; B. C. Riva" -> ["marta", "riva"];
    comma form "Marta, Ada" -> ["marta"]. Tolerant of empty/odd input.

    Used for the WATCHLIST, where precision matters (plan §11 tracks "Da",
    which is also a common given-name/particle token). The hair trigger does
    NOT use this — see classify_hit.
    """
    out = []
    for a in (authors or "").split(";"):
        a = a.strip().lower()
        if not a:
            continue
        # "Last, First" — the surname is what precedes the comma.
        head = a.split(",")[0] if "," in a else a
        parts = [p for p in re.split(r"[\s.]+", head) if p]
        if parts:
            out.append(parts[-1])
    return out


def classify_hit(hit):
    """Attach 毛刺 / ALERT-threshold / watchlist fields. Pure; no network.

    manual §R13b: author contains Marta or Riva, OR title contains
    'replication technique/switch' -> 毛刺节 regardless of overlap, ALERT 40%.
    """
    surnames = _surnames(hit.get("authors"))
    # The hair trigger scans EVERY name token, not just the parsed surname:
    # author strings arrive as "Ada Marta", "Marta, Ada" and "Marta A." from
    # different sources, and a missed Marta–Riva hit is the single failure this
    # trigger exists to prevent (plan §11). Over-inclusive by design; the cost
    # of a false 毛刺 entry is one extra line for the triage step to read.
    hit_authors = sorted(set(t for t in _name_tokens(hit.get("authors"))
                             if t in HAIR_AUTHORS))
    title_hit = bool(HAIR_TITLE_RE.search(hit.get("title") or ""))
    reasons = []
    if hit_authors:
        reasons.append("author:" + "+".join(hit_authors))
    if title_hit:
        reasons.append("title:replication-technique/switch")
    hit["hair_trigger"] = bool(reasons)
    hit["hair_reason"] = "; ".join(reasons)
    hit["alert_threshold_pct"] = ALERT_HAIR if reasons else ALERT_DEFAULT
    hit["watchlist"] = "; ".join(
        sorted(set(s for s in surnames if s in WATCH_AUTHORS)))
    return hit


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
        hits.append(classify_hit({
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
        }))
    return hits


def s2_search_bulk(cutoff):
    # One bulk call for ALL keywords (boolean OR) — the unauthenticated S2 pool
    # 429s hard under separate /paper/search calls (E2-T11 observed this live
    # 2026-07-09). Free key via env S2_API_KEY lifts the shared-pool limit.
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
        hits.append(classify_hit({
            "id": pid,
            "title": (p.get("title") or "").strip(),
            "authors": "; ".join((a.get("name") or "") for a in (p.get("authors") or [])),
            "date": pub.isoformat(),
            "abstract": re.sub(r"\s+", " ", p.get("abstract") or "").strip(),
            "url": p.get("url") or "",
            "source": "SemanticScholar",
            "keyword": "s2-bulk",
        }))
    return hits


def ssrn_manual_urls():
    # No stable public SSRN API (spec: do NOT fabricate one) — manual links only.
    return ["https://www.ssrn.com/index.cfm/en/search/?term=" + quote_plus(k)
            for k in KEYWORDS]


def dedup(batches, seen):
    """Collapse batches into ordered unique hits, skipping anything in `seen`.

    Keyed on the source id and on the normalized title, so the same paper
    arriving from arXiv and S2 lands once. Pure; no network.
    """
    collected = {}
    for h in batches:
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
    uniq = list({id(h): h for h in collected.values()}.values())
    return sorted(uniq, key=lambda h: (h["date"], h["title"]), reverse=True)


def render_hairtrigger(hits, stamp):
    """Pre-build the 毛刺节 that manual §R13b requires R13b to emit."""
    hair = [h for h in hits if h.get("hair_trigger")]
    lines = ["# 毛刺节 — REFR-R13 %s" % stamp, "",
             "manual §R13b: these entries are listed REGARDLESS of the triage "
             "model's overlap judgement, and carry ALERT threshold "
             "%d%% (not %d%%). The triage step judges overlap only; it may not "
             "re-decide membership of this section." % (ALERT_HAIR, ALERT_DEFAULT), ""]
    if not hair:
        lines.append("(empty this run — no Marta/Riva author hit, no "
                     "replication-technique/switch title hit)")
    for h in hair:
        lines += ["## %s" % h["title"],
                  "- 作者: %s" % (h["authors"] or "UNKNOWN"),
                  "- 日期: %s" % h["date"],
                  "- 全文链接: %s" % (h["url"] or "UNKNOWN"),
                  "- 来源: %s" % h["source"],
                  "- 毛刺理由: %s" % h["hair_reason"],
                  "- ALERT 阈值: %d%%" % h["alert_threshold_pct"], ""]
    if hair:
        lines += ["---", "",
                  "毛刺节非空 → manual §R13b requires the triage output to carry "
                  "a separate 「计划 §10/§1 边界表影响评估」 section."]
    return "\n".join(lines) + "\n"


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

    batches, errors, n_legs = [], [], len(KEYWORDS) + 1

    for kw in KEYWORDS:
        try:
            batches.extend(arxiv_search(kw, cutoff))
        except Exception as e:
            errors.append("arxiv %r: %s" % (kw, e))
        time.sleep(3)  # arXiv asks >=3s between calls
    try:
        batches.extend(s2_search_bulk(cutoff))
    except Exception as e:
        errors.append("s2-bulk: %s" % e)

    if len(errors) == n_legs:
        print("FATAL: every API call failed:\n  " + "\n  ".join(errors), file=sys.stderr)
        return 1

    hits = dedup(batches, seen)
    stamp = today.strftime("%Y%m%d")

    with io.open(str(OUTDIR / ("hits_%s.csv" % stamp)), "w",
                 encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["标题", "作者", "日期", "摘要", "链接", "来源",
                    "毛刺", "毛刺理由", "ALERT阈值", "监测名单"])
        for h in hits:
            w.writerow([h["title"], h["authors"], h["date"], h["abstract"],
                        h["url"], h["source"], "Y" if h["hair_trigger"] else "",
                        h["hair_reason"], h["alert_threshold_pct"], h["watchlist"]])

    with io.open(str(OUTDIR / ("hits_%s.jsonl" % stamp)), "w", encoding="utf-8") as f:
        for h in hits:
            f.write(json.dumps(h, ensure_ascii=False) + "\n")

    with io.open(str(OUTDIR / ("hairtrigger_%s.md" % stamp)), "w", encoding="utf-8") as f:
        f.write(render_hairtrigger(hits, stamp))

    with io.open(str(OUTDIR / ("ssrn_manual_%s.txt" % stamp)), "w", encoding="utf-8") as f:
        f.write("# SSRN has no stable public API — click these by hand "
                "(manual §R13a, E2 T11a item 2):\n")
        for u in ssrn_manual_urls():
            f.write(u + "\n")

    if not a.full:
        for h in hits:
            seen[h["dedup_key"]] = today.isoformat()
            seen[norm_key(h["title"])] = today.isoformat()
        SEEN_PATH.write_text(json.dumps(seen, indent=0, sort_keys=True))

    n_hair = sum(1 for h in hits if h["hair_trigger"])
    print("scan %s: %d new hit(s), %d 毛刺, window %s..%s, %d source error(s)%s"
          % (stamp, len(hits), n_hair, cutoff, today, len(errors),
             (" — " + "; ".join(errors)) if errors else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
