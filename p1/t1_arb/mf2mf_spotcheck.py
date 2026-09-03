#!/usr/bin/env python3
"""BOX-ONLY. Build a confirmatory spot-check spec: 10 random filings from the
UNCHECKED MF_TO_MF pool (reason==MF_TO_MF and not already re-read by Pass 3),
full-text, under the frozen v2 STEP rules. Seeded for reproducibility.
"""
import csv, html, io, json, random, re, importlib.util, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
final = json.loads((ROOT / "p1" / "t1_events_final.json").read_text())
cik = {r["accession"]: r["cik"]
       for r in csv.DictReader(open(ROOT / "p1" / "edgar_filings" / "manifest.csv"))}
PKG = ROOT / "p1" / "edgar_filings"

pool = []
for acc, v in final.items():
    if acc == "_meta" or not isinstance(v, dict) or not v.get("no_event"):
        continue
    if v.get("reason") != "MF_TO_MF":
        continue
    if (v.get("_adjudication") or {}).get("source") == "recat-fulltext":
        continue
    if acc not in cik or not (PKG / "{0}_{1}.htm".format(cik[acc], acc)).exists():
        continue
    pool.append(acc)
print("unchecked MF_TO_MF with raw file:", len(pool))
random.seed(20260719)
sample = sorted(random.sample(pool, 10))

spec = importlib.util.spec_from_file_location("brs", str(ROOT / "p1" / "t1_arb" / "build_recat_spec.py"))
brs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(brs)
TAG = re.compile(r"<[^>]+>")

lines = ["# P1-T1-mf2mf-spot — confirmatory spot-check, 10 unchecked MF_TO_MF filings",
         "worker: deepseek", "web_search: false", "max_items_per_call: 4",
         "est_cost: 0.05", "items:"]
for acc in sample:
    c = cik[acc]
    raw = io.open(PKG / "{0}_{1}.htm".format(c, acc), "r", encoding="utf-8", errors="ignore").read()
    txt = re.sub(r"\s+", " ", html.unescape(TAG.sub(" ", raw))).strip()[:brs.BODY_CAP]
    lines.append('  - id: "{0}"'.format(acc))
    lines.append('    _cik: "{0}"'.format(c))
    lines.append("    prompt: |")
    for ln in (brs.RULES + "\n完整正文:\n" + txt).splitlines():
        lines.append("      " + ln)
lines.append(brs.SENTINELS)
(ROOT / "ops" / "l1" / "P1-T1-mf2mf-spot.yaml").write_text("\n".join(lines) + "\n")
print("sample:", sample)
print("wrote ops/l1/P1-T1-mf2mf-spot.yaml with 10 items")
