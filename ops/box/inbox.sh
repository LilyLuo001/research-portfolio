#!/usr/bin/env bash
# inbox.sh — commands for the box's next 30-min cycle (see run_inbox.sh).
# inbox-version: 2026-07-10-h
#
# Payload h — turn the harvested EDGAR package into tonight's four extraction
# batches. The harvest is done (423 filings; manifest committed in 547c577);
# p1/make_extraction_specs.py (merged alongside this payload) reads the
# box-local .htm files and writes ops/l1/{P1-T1-events,P1-T1-events-B,
# P1-T13-ant,P1-T13-ant-B}.yaml — channel A deepseek, channel B gemini_free
# (kimi stays benched; deepseek/google keeps cross-vendor A/B; extraction
# reads embedded excerpts so neither channel needs web_search).
# All idempotent: the generator skips existing specs without --force.

echo "== host identity (duplicate-checkout watch: the 02:03 run saw a venv-less host) =="
echo "$(hostname) : $(pwd) : $(git rev-parse --short HEAD)"

echo "== harvest completeness =="
n_htm=$(ls p1/edgar_filings/*.htm 2>/dev/null | wc -l)
n_man=$(($(wc -l < p1/edgar_filings/manifest.csv) - 1))
echo "local filings: $n_htm / manifest rows: $n_man"
if [ "$n_htm" -lt $((n_man / 2)) ]; then
  echo "over half the filings missing locally — re-running the harvester (resumable) first"
  .venv/bin/python p1/fetch_edgar_filings.py 2>&1 | tail -3
fi

echo "== generate extraction specs =="
.venv/bin/python p1/make_extraction_specs.py

echo "== validate specs parse + what tonight's driver would run (dry-run) =="
.venv/bin/python -c "
import yaml, glob
for p in sorted(glob.glob('ops/l1/P1-T1*.yaml') + glob.glob('ops/l1/P1-T13*.yaml')):
    s = yaml.safe_load(open(p))
    print(p, '->', s['worker'], len(s['items']), 'items,', len(s.get('sentinels', [])), 'sentinels')
"
.venv/bin/python ops/runner/l1_driver.py 2>&1 | tail -10

echo "== commit the generated specs so every seat sees tonight's plan =="
git add ops/l1/P1-T1-events.yaml ops/l1/P1-T1-events-B.yaml \
        ops/l1/P1-T13-ant.yaml ops/l1/P1-T13-ant-B.yaml 2>/dev/null || true
git commit -q -m "box: extraction specs generated from the EDGAR package (payload h)" \
  || echo "nothing new to commit"

echo "== state =="
cat ops/runner/state.json
