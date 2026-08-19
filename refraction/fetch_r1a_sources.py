#!/usr/bin/env python3
"""REFR-R1a — fetch the first-hand sources and emit the registry mechanically.

R1a is blocked because no lane in this portfolio can currently reach
frbsf.org / federalreserve.gov / bls.gov. It is NOT blocked on judgement: the
task is to fetch official pages, record what they say with a locator, and hand
R1b the file's real column names. All of that is mechanical. This script does it,
and runs anywhere with outbound HTTPS — the box, a laptop, a WRDS Cloud node.

What it produces
----------------
  cache/<sha>.<ext>            immutable raw download, keyed by URL digest
  r1a_registry.csv             one row per fetched artifact:
                               [fact, conclusion, source_url, retrieved_at,
                                http_status, sha256, bytes, confidence, unknown]
  r1a_file_heads.md            for every tabular download: the exact column list
                               and first 20 rows — items 2 and 3 of
                               refraction/R1b_input_requirements.md, produced from
                               the file instead of pasted by hand
  r1a_discovered_links.csv     candidate data-file links found on each seed page

What it deliberately does NOT do
--------------------------------
* It does not decide which column is the registered FOMC surprise (requirements
  item 4). That needs the official definition read and quoted, which is a
  verification judgement, not a download.
* It does not hardcode deep file URLs from anyone's memory. It fetches SEED pages
  and DISCOVERS links on them. A seed that is wrong surfaces as a 404 row in the
  registry — evidence, not a silent failure.
* It never writes a fact it did not receive. A failed fetch produces an UNKNOWN
  row carrying the URL tried and the error, per iron rule 2.

Run:  python refraction/fetch_r1a_sources.py
      python refraction/fetch_r1a_sources.py --only usmpd
"""
import argparse
import csv
import hashlib
import io
import json
import pathlib
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

HERE = pathlib.Path(__file__).resolve().parent
CACHE = HERE / "cache" / "r1a"
REGISTRY = HERE / "r1a_registry.csv"
HEADS = HERE / "r1a_file_heads.md"
LINKS = HERE / "r1a_discovered_links.csv"

UA = "portfolio-refr-r1a/1.0 (academic research; contact via repo owner)"
HEAD_ROWS = 20

# Seed pages only — landing pages, never deep file paths. Each is a CANDIDATE:
# the run records the status it actually got, so a stale or wrong seed shows up
# as a 404 row rather than as a confident claim. Correct them here after the
# first run; that is the one-place edit.
SEEDS = {
    "usmpd": ["https://www.frbsf.org/research-and-insights/data-and-indicators/"
              "us-monetary-policy-event-study-database/"],
    "fomc_calendar": ["https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"],
    "cpi_schedule": ["https://www.bls.gov/schedule/news_release/cpi.htm"],
    "employment_schedule": ["https://www.bls.gov/schedule/news_release/empsit.htm"],
}
DATA_LINK = re.compile(r'href=["\']([^"\']+\.(?:xlsx|xls|csv|zip|dta|pdf))["\']', re.I)
ANY_LINK = re.compile(r'href=["\']([^"\']+)["\']', re.I)


def now():
    return datetime.now(timezone.utc).isoformat()


def fetch(url, timeout=60):
    """Return (status, body_bytes, error). Never raises — a failure is a datum."""
    try:
        req = Request(url, headers={"User-Agent": UA})
        with urlopen(req, timeout=timeout) as r:
            return getattr(r, "status", 200), r.read(), ""
    except HTTPError as e:
        return e.code, b"", f"HTTPError {e.code}"
    except URLError as e:
        return 0, b"", f"URLError {e.reason}"
    except Exception as e:  # noqa: BLE001 — a sweep must not die on one URL
        return 0, b"", f"{type(e).__name__}: {e}"


def cache_path(url, body):
    ext = pathlib.Path(url.split("?")[0]).suffix.lower() or ".html"
    return CACHE / (hashlib.sha256(url.encode()).hexdigest()[:16] + ext)


def registry_row(kind, url, status, body, error):
    ok = status == 200 and body
    return {
        "kind": kind,
        "fact": f"{kind} source page" if ok else f"{kind} source UNREACHABLE",
        "conclusion": "fetched" if ok else "UNKNOWN",
        "source_url": url,
        "retrieved_at": now(),
        "http_status": status,
        "sha256": hashlib.sha256(body).hexdigest() if body else "",
        "bytes": len(body),
        # 'high' only means the bytes came from that URL on that date — never that
        # their CONTENT has been verified. Reading them is R1a's next step.
        "confidence": "high" if ok else "UNKNOWN",
        "unknown": "" if ok else (error or f"status {status}"),
    }


def discover_links(base_url, body):
    html = body.decode("utf-8", "replace")
    data = [urljoin(base_url, m) for m in DATA_LINK.findall(html)]
    if data:
        return sorted(set(data))
    # No obvious data file: record every link so a human can see what was there,
    # rather than reporting "no data file exists".
    return sorted({urljoin(base_url, m) for m in ANY_LINK.findall(html)})[:200]


def tabular_head(path, n=HEAD_ROWS):
    """Column list + first n rows of a CSV-ish download. Returns None if not CSV."""
    if path.suffix.lower() not in (".csv", ".txt", ".tsv"):
        return None
    text = path.read_bytes().decode("utf-8", "replace")
    sample = text[:64000]
    delim = "\t" if sample.count("\t") > sample.count(",") else ","
    rows = list(csv.reader(io.StringIO(sample), delimiter=delim))
    if not rows:
        return None
    return {"columns": rows[0], "rows": rows[1:n + 1], "delimiter": delim}


def write_outputs(rows, links, heads):
    fields = ["kind", "fact", "conclusion", "source_url", "retrieved_at",
              "http_status", "sha256", "bytes", "confidence", "unknown"]
    with REGISTRY.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    with LINKS.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["kind", "seed_url", "discovered_url"])
        w.writeheader()
        w.writerows(links)

    L = ["# R1a file heads — produced from the files, not pasted from memory", "",
         f"generated: {now()}", "",
         "Answers items 2 and 3 of `refraction/R1b_input_requirements.md`. Item 4",
         "(which column is the registered FOMC surprise, with its official",
         "definition quoted) is deliberately NOT answered here: that is a",
         "verification judgement, not a download.", ""]
    if not heads:
        L += ["**No tabular file was retrieved.** Either the seed pages exposed no",
              "CSV/TSV link, or every fetch failed — see `r1a_registry.csv`, whose",
              "UNKNOWN rows carry the URL tried and the error."]
    for h in heads:
        L += [f"## {h['kind']} — `{h['url']}`", "",
              f"- sha256: `{h['sha256']}`  ·  bytes: {h['bytes']}  ·  "
              f"delimiter: `{h['delimiter']}`",
              f"- columns ({len(h['columns'])}): `{'`, `'.join(h['columns'])}`", "",
              "```", h["delimiter"].join(h["columns"])]
        L += [h["delimiter"].join(r) for r in h["rows"]]
        L += ["```", ""]
    HEADS.write_text("\n".join(L) + "\n")


def run(kinds=None, fetcher=fetch):
    CACHE.mkdir(parents=True, exist_ok=True)
    rows, links, heads = [], [], []
    for kind, urls in SEEDS.items():
        if kinds and kind not in kinds:
            continue
        for url in urls:
            status, body, err = fetcher(url)
            rows.append(registry_row(kind, url, status, body, err))
            if not body:
                continue
            p = cache_path(url, body)
            p.write_bytes(body)
            for found in discover_links(url, body):
                links.append({"kind": kind, "seed_url": url, "discovered_url": found})
                if not found.lower().split("?")[0].endswith((".csv", ".tsv", ".txt")):
                    continue
                s2, b2, e2 = fetcher(found)
                rows.append(registry_row(f"{kind}:data", found, s2, b2, e2))
                if not b2:
                    continue
                p2 = cache_path(found, b2)
                p2.write_bytes(b2)
                head = tabular_head(p2)
                if head:
                    heads.append({"kind": kind, "url": found,
                                  "sha256": hashlib.sha256(b2).hexdigest(),
                                  "bytes": len(b2), **head})
    return rows, links, heads


def main(argv=None):
    ap = argparse.ArgumentParser(description="REFR-R1a first-hand source fetch")
    ap.add_argument("--only", action="append", default=[], choices=sorted(SEEDS),
                    help="restrict to these seed kinds (repeatable)")
    a = ap.parse_args(argv)
    rows, links, heads = run(a.only or None)
    write_outputs(rows, links, heads)
    ok = sum(1 for r in rows if r["conclusion"] == "fetched")
    unknown = [r for r in rows if r["conclusion"] == "UNKNOWN"]
    print(f"R1a fetch: {ok} artifact(s) retrieved, {len(unknown)} UNKNOWN, "
          f"{len(heads)} tabular head(s) extracted -> {REGISTRY.name}, {HEADS.name}")
    for r in unknown:
        print(f"  UNKNOWN {r['kind']}: {r['source_url']} ({r['unknown']})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
