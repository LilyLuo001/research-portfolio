#!/usr/bin/env bash
# inbox.sh — commands for the box's next 30-min cycle (see run_inbox.sh).
# inbox-version: 2026-07-10-i
#
# Payload i — K-4 remediation on box recovery (audit L2-AUDIT-2026-07-10):
# the hand-run manifest was 95% T13-family (9 conversion hits) and the
# ActiveShares query overran the old page cap, so ALL FOUR extraction specs
# are parked. This payload: (1) re-runs the patched harvester (reorganization
# phrase family, MAX_PAGES 60, T-1 truncation warnings, atomic writes) —
# idempotent, only new filings download; (2) regenerates the four specs with
# --force (K-4 guard refuses P1-T1 if conversion coverage is still thin);
# (3) commits manifest + specs. Runs only when the box lane is back.

echo "== host identity =="
echo "$(hostname) : $(pwd) : $(git rev-parse --short HEAD)"

echo "== harvester re-run (expanded phrases; idempotent) =="
.venv/bin/python p1/fetch_edgar_filings.py 2>&1 | tail -15
echo "-- truncation warnings, if any:"
grep -c "TRUNCATED" p1/edgar_filings/harvest.log 2>/dev/null || echo "0 (or no log)"

echo "== per-query hit counts (K-4 review surface) =="
.venv/bin/python - << 'PYEOF'
import csv, collections
c = collections.Counter(r["query_phrase"] for r in csv.DictReader(open("p1/edgar_filings/manifest.csv")))
for q, n in c.most_common():
    print("%5d  %s" % (n, q))
PYEOF

echo "== regenerate extraction specs (K-4 guard active) =="
.venv/bin/python p1/make_extraction_specs.py --force

echo "== dry-run: what tonight would dispatch =="
.venv/bin/python ops/runner/l1_driver.py 2>&1 | tail -12

echo "== commit =="
git add p1/edgar_filings/manifest.csv ops/l1/P1-T1-events.yaml ops/l1/P1-T1-events-B.yaml \
        ops/l1/P1-T13-ant.yaml ops/l1/P1-T13-ant-B.yaml 2>/dev/null || true
git commit -q -m "box: K-4 remediation — expanded harvest + regenerated extraction specs (payload i)" \
  || echo "nothing new to commit"

echo "== state =="
cat ops/runner/state.json
