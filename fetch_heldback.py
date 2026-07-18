"""Targeted fetch of ONLY the held-back filings needed by build_daterecover_spec.py.
Saves each to p1/edgar_filings/{cik}_{acc}.htm (the path the build script reads),
cik resolved from manifest.csv, url taken from held_back.json. SEC-polite: descriptive
UA + rate limit. Idempotent: skips files already present."""
import csv, io, json, os, pathlib, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[0]
PKG = ROOT / "p1" / "edgar_filings"
MANIFEST = PKG / "manifest.csv"
HELD = ROOT / "p1" / "t1_arb" / "held_back.json"
UA = "BU research qluo@bu.edu"

cik_of = {}
with open(MANIFEST) as f:
    for r in csv.DictReader(f):
        cik_of[r["accession"]] = r["cik"]

held = json.loads(HELD.read_text())["held"]
targets = []  # (acc, cik, url, dest)
seen = set()
no_cik = []
for h in held:
    for a in h["accessions"]:
        acc = a["id"]
        if acc in seen:
            continue
        seen.add(acc)
        cik = cik_of.get(acc)
        if not cik:
            no_cik.append(acc)
            continue
        dest = PKG / f"{cik}_{acc}.htm"
        targets.append((acc, cik, a["url"], dest))

print(f"held={len(held)} distinct_accessions={len(seen)} "
      f"with_cik={len(targets)} no_cik_in_manifest={len(no_cik)}")

dl = skip = fail = 0
failures = []
for acc, cik, url, dest in targets:
    if dest.exists() and dest.stat().st_size > 0:
        skip += 1
        continue
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=45) as r:
            data = r.read()
        if not data:
            raise ValueError("empty body")
        dest.write_bytes(data)
        dl += 1
        time.sleep(0.15)  # ~7 req/s, under SEC's 10/s guidance
    except Exception as e:
        fail += 1
        failures.append((acc, url, f"{type(e).__name__}: {e}"))

print(f"downloaded={dl} already_present={skip} failed={fail}")
if no_cik:
    print("NO_CIK (not in manifest, cannot place):", no_cik[:20], "..." if len(no_cik) > 20 else "")
if failures:
    print("FAILURES:")
    for acc, url, err in failures[:20]:
        print(f"  {acc}  {err}  {url}")
