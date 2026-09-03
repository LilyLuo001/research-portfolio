#!/usr/bin/env python3
# refraction/scan.py — REFR-R13a: monthly literature collision monitor for the
# refraction chapter ("One Shock, Many Prices").
#
# Architecture is E2-T11's corrected one, carried over verbatim per manual
# §R13 ("E2 T11 修正后架构原样搬用"): deterministic, NO LLM in the path —
# arXiv API + Semantic Scholar API over a fixed bilingual keyword list, plus
# GENERATED SSRN search URLs for a human to click (SSRN has no stable public
# API; the spec forbids inventing one). The LLM appears only downstream, in
# REFR-R13-triage, and only to judge overlap — never to discover papers.
#
# What this script adds over e2/scan.py, per manual §R13b:
#   * the 毛刺节 (hair-trigger) section — any hit whose authors include Marta
#     or Riva, or whose title contains "replication technique"/"switch", is
#     listed separately WITH its full-text link no matter what its provisional
#     overlap looks like, and carries ALERT threshold 0.40 instead of 0.60.
#     The flag is computed HERE so a triage model cannot lose it.
#
# Outputs (under refraction/scans/):
#   hits_YYYYMMDD.csv          [标题, 作者, 日期, 摘要, 链接, 来源, 毛刺, ALERT阈值, 关键词]
#   hits_YYYYMMDD.jsonl        same records as JSON objects — R13b triage input
#   burr_YYYYMMDD.md           毛刺节: hair-trigger hits + reasons + links (always written)
#   ssrn_manual_YYYYMMDD.txt   SSRN search URLs for manual click-through
#   seen_ids.json              cross-run dedup registry (id -> first_seen date)
#
# Exit code 0 on a clean run (0 new hits is a normal outcome); 1 only if EVERY
# source leg failed, so cron surfaces a dead monitor instead of a silent green.
#
# Cron: R13 is resident from R0 onward. The box wiring (one line in
# ops/box/cron_night.sh) is a seat-D edit — see refraction/scans/manifest.md
# §handoff; this seat owns refraction/ only.
#
# Box venv is Python 3.6 — keep this file 3.6-compatible (no f-strings, no
# dataclasses, stdlib only), same constraint as e2/scan.py.

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
from pathlib import Path

try:
    from urllib.request import urlopen, Request
    from urllib.parse import quote_plus, urlencode
    from urllib.error import HTTPError, URLError
except ImportError:  # pragma: no cover
    raise SystemExit("python3 required")

HERE = Path(__file__).resolve().parent
OUTDIR = HERE / "scans"
SEEN_NAME = "seen_ids.json"

# Monthly cadence (manual §R13 "月度碰撞监测") with a 5-day overlap so a run
# that slips by a few days cannot open a hole in coverage.
WINDOW_DAYS = 35

# Keyword list — the six English phrases are VERBATIM from manual §R13a. The
# manual asks for 中英双语; the Chinese lines are this seat's translations of
# those same six phrases (translation, not a sourced fact — no bibliographic
# content is derived from them).
KEYWORDS_EN = [
    "ETF basket comovement announcement",
    "conversion comovement",
    "announcement day beta ETF",
    "ETF replication switch comovement",
    "creation basket transmission",
    "passive macro news cross-section",
]
KEYWORDS_ZH = [
    "ETF 篮子 共动 公告",
    "基金转换 共动",
    "公告日 beta ETF",
    "ETF 复制方式 切换 共动",
    "申购篮子 传导",
    "被动投资 宏观新闻 截面",
]
KEYWORDS = KEYWORDS_EN + KEYWORDS_ZH

# 毛刺 (hair-trigger) rules — manual §R13b, verbatim intent:
#   "命中作者含 Marta 或 Riva, 或标题含 replication technique/switch 的条目,
#    无论初判重叠度如何一律单列'毛刺节'并给全文链接 —— 该来源的 ALERT 阈值
#    为 40% 而非 60%."
# Author matching is token-exact (not substring) so "Rivas"/"Martarelli" do
# not masquerade as the target authors. Title matching is deliberately broad:
# a bare "switch" over-flags, and over-flagging costs a human 30 seconds while
# under-flagging costs the chapter its priority claim.
BURR_AUTHOR_TOKENS = ["marta", "riva"]
BURR_TITLE_PATTERNS = ["replication technique", "switch", "复制方式", "切换"]
ALERT_BURR = 0.40
ALERT_DEFAULT = 0.60

UA = "portfolio-refr-r13-scan/1.0 (research literature monitor)"
ATOM = "{http://www.w3.org/2005/Atom}"


def http_get(url, tries=4, base_sleep=5, headers=None):
    """GET with backoff. Patched out wholesale in tests — no network in pytest."""
    last = None
    for i in range(tries):
        try:
            h = {"User-Agent": UA}
            h.update(headers or {})
            req = Request(url, headers=h)
            r = urlopen(req, timeout=60)
            try:
                return r.read().decode("utf-8", "replace")
            finally:
                r.close()
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


def _author_tokens(authors):
    return set(t for t in re.split(r"[^A-Za-z一-鿿]+", (authors or "").lower()) if t)


def burr_reasons(hit):
    """Return the list of §R13b hair-trigger reasons this hit fires (may be empty)."""
    reasons = []
    toks = _author_tokens(hit.get("authors"))
    for name in BURR_AUTHOR_TOKENS:
        if name in toks:
            reasons.append("author:" + name)
    title = (hit.get("title") or "").lower()
    for pat in BURR_TITLE_PATTERNS:
        if pat in title:
            reasons.append("title:" + pat)
    return reasons


def classify(hit):
    """Attach burr flag + ALERT threshold. Runs on every hit, before triage."""
    reasons = burr_reasons(hit)
    hit["burr"] = bool(reasons)
    hit["burr_reason"] = "; ".join(reasons)
    hit["alert_threshold"] = ALERT_BURR if reasons else ALERT_DEFAULT
    return hit


def parse_arxiv_atom(body, cutoff, keyword):
    hits = []
    for entry in ET.fromstring(body).findall(ATOM + "entry"):
        pub = parse_date((entry.findtext(ATOM + "published") or ""))
        if pub is None or pub < cutoff:
            continue
        link = (entry.findtext(ATOM + "id") or "").strip()
        hits.append(classify({
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


def arxiv_search(keyword, cutoff):
    q = urlencode({
        "search_query": 'all:"%s"' % keyword,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": "50",
    })
    return parse_arxiv_atom(
        http_get("https://export.arxiv.org/api/query?" + q), cutoff, keyword)


def parse_s2(body, cutoff):
    hits = []
    for p in (json.loads(body).get("data") or []):
        pub = parse_date(p.get("publicationDate"))
        if pub is None or pub < cutoff:
            continue
        ext = p.get("externalIds") or {}
        if ext.get("DOI"):
            pid = "doi:" + ext["DOI"]
        elif ext.get("ArXiv"):
            pid = "arxiv:" + ext["ArXiv"]
        else:
            pid = "s2:" + (p.get("paperId") or "")
        hits.append(classify({
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


def s2_search_bulk(cutoff):
    # One bulk call for ALL keywords (boolean OR): the unauthenticated S2 pool
    # 429s hard under one /paper/search call per keyword (observed live on
    # E2-T11, 2026-07-09). A free key in S2_API_KEY lifts the shared-pool cap.
    q = urlencode({
        "query": " | ".join('"%s"' % k for k in KEYWORDS),
        "fields": "title,authors,abstract,url,publicationDate,externalIds",
        # server-side prefilter; the local date check above stays authoritative
        "publicationDateOrYear": cutoff.isoformat() + ":",
    })
    key = os.getenv("S2_API_KEY")
    body = http_get(
        "https://api.semanticscholar.org/graph/v1/paper/search/bulk?" + q,
        base_sleep=20, headers={"x-api-key": key} if key else None)
    return parse_s2(body, cutoff)


def ssrn_manual_urls():
    # No stable public SSRN API (spec: do NOT fabricate one) — manual links only.
    # The Marta–Riva working paper lives on SSRN, so this leg is the one that
    # actually covers the priority risk; it is a human click-through by design.
    return ["https://www.ssrn.com/index.cfm/en/search/?term=" + quote_plus(k)
            for k in KEYWORDS]


def load_seen(outdir):
    p = Path(outdir) / SEEN_NAME
    if p.exists():
        return json.loads(p.read_text())
    return {}


def collect(legs, seen):
    """Merge source legs, dedup within-run and against `seen`. Order preserved."""
    collected, index = [], {}

    def keys_of(h):
        k = h["id"] if not h["id"].startswith("s2:") else norm_key(h["title"])
        return k, norm_key(h["title"])

    for batch in legs:
        for h in batch:
            k, tkey = keys_of(h)
            prev = index.get(k) or index.get(tkey)
            if prev is not None:
                if h["keyword"] not in prev["keyword"]:
                    prev["keyword"] += ", " + h["keyword"]
                continue
            if k in seen or tkey in seen:
                continue
            h["dedup_key"] = k
            collected.append(h)
            index[k] = h
            index[tkey] = h
    return collected


def write_outputs(outdir, hits, stamp, cutoff, today, errors):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    with io.open(str(outdir / ("hits_%s.csv" % stamp)), "w",
                 encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["标题", "作者", "日期", "摘要", "链接", "来源",
                    "毛刺", "ALERT阈值", "关键词"])
        for h in hits:
            w.writerow([h["title"], h["authors"], h["date"], h["abstract"],
                        h["url"], h["source"], "Y" if h["burr"] else "",
                        h["alert_threshold"], h["keyword"]])

    with io.open(str(outdir / ("hits_%s.jsonl" % stamp)), "w", encoding="utf-8") as f:
        for h in hits:
            f.write(json.dumps(h, ensure_ascii=False, sort_keys=True) + "\n")

    burrs = [h for h in hits if h["burr"]]
    with io.open(str(outdir / ("burr_%s.md" % stamp)), "w", encoding="utf-8") as f:
        f.write("# 毛刺节 %s (manual §R13b; ALERT 阈值 %.2f, 其余 %.2f)\n\n"
                % (stamp, ALERT_BURR, ALERT_DEFAULT))
        f.write("窗口 %s..%s;本轮新命中 %d 条,其中毛刺 %d 条。\n\n"
                % (cutoff.isoformat(), today.isoformat(), len(hits), len(burrs)))
        if not burrs:
            f.write("本轮无毛刺命中(Marta/Riva 作者、replication technique/switch 标题)。\n")
        for h in burrs:
            f.write("## %s\n\n- 作者: %s\n- 日期: %s\n- 来源: %s (关键词: %s)\n"
                    "- 触发: %s\n- 全文链接: %s\n\n"
                    % (h["title"], h["authors"], h["date"], h["source"],
                       h["keyword"], h["burr_reason"], h["url"]))
        if errors:
            f.write("\n> 源错误 %d: %s\n" % (len(errors), "; ".join(errors)))

    with io.open(str(outdir / ("ssrn_manual_%s.txt" % stamp)), "w", encoding="utf-8") as f:
        f.write("# SSRN has no stable public API — click these by hand "
                "(manual §R13a; Marta–Riva SSRN 4079302 lives here):\n")
        for u in ssrn_manual_urls():
            f.write(u + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description="REFR-R13a collision scan")
    ap.add_argument("--full", action="store_true",
                    help="ignore seen_ids.json — report every in-window hit")
    ap.add_argument("--window-days", type=int, default=WINDOW_DAYS,
                    help="lookback window in days (default %d)" % WINDOW_DAYS)
    ap.add_argument("--out-dir", default=str(OUTDIR))
    a = ap.parse_args(argv)

    today = datetime.datetime.utcnow().date()
    cutoff = today - datetime.timedelta(days=a.window_days)
    outdir = Path(a.out_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    seen = {} if a.full else load_seen(outdir)

    legs, errors, n_legs = [], [], len(KEYWORDS) + 1
    for kw in KEYWORDS:
        try:
            legs.append(arxiv_search(kw, cutoff))
        except Exception as e:
            errors.append("arxiv %r: %s" % (kw, e))
        time.sleep(3)  # arXiv asks for >=3s between calls
    try:
        legs.append(s2_search_bulk(cutoff))
    except Exception as e:
        errors.append("s2-bulk: %s" % e)

    if len(errors) == n_legs:
        sys.stderr.write("FATAL: every API call failed:\n  "
                         + "\n  ".join(errors) + "\n")
        return 1

    hits = collect(legs, seen)
    hits.sort(key=lambda h: (h["date"], h["title"]), reverse=True)
    stamp = today.strftime("%Y%m%d")
    write_outputs(outdir, hits, stamp, cutoff, today, errors)

    if not a.full:
        for h in hits:
            seen[h["dedup_key"]] = today.isoformat()
            seen[norm_key(h["title"])] = today.isoformat()
        (outdir / SEEN_NAME).write_text(json.dumps(seen, indent=0, sort_keys=True))

    n_burr = sum(1 for h in hits if h["burr"])
    print("scan %s: %d new hit(s), %d 毛刺, window %s..%s, %d source error(s)%s"
          % (stamp, len(hits), n_burr, cutoff, today, len(errors),
             (" — " + "; ".join(errors)) if errors else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
