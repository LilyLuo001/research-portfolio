#!/usr/bin/env bash
# inbox.sh — commands for the box's next 30-min cycle (see run_inbox.sh).
# inbox-version: 2026-07-09-e
#
# Acting on the 10:55 cycle + content review of the DONE outputs:
# (1) module diagnostics — payload d found no python3 module; find out why.
# (2) COMPLETE P1-T0-crash-B — content reviewed: only hit is the Saglam-Tuzun
#     FEDS Note itself (LOW overlap, market-quality not earnings-info);
#     keyword sweep is a clean UNKNOWN with documented search paths; fence
#     3/3. Verdict: NO collision, the P1 information-side window is open.
# (3) QUARANTINE DAX-W0.5-legwork.json — produced by legacy moonshot-v1-32k
#     and slipped past its (too-famous) fence: fabricated retrieval date
#     2024-02-26, OpenAI models as "open-weight stand-ins", invented
#     gdpval.mit.edu URL. Deleted; re-runs on k2.6 via split.
# (4) Clear parked strikes (infra-era artifacts + the stall failures now
#     being retried), then live pass with the new `split: true` per-item mode.

echo "== python module diagnostics (payload d found none) =="
source /etc/profile.d/modules.sh 2>/dev/null || true
if type module >/dev/null 2>&1; then
  echo "MODULEPATH=$MODULEPATH"
  module -t avail 2>&1 | grep -i python | head -20
else
  echo "no module command in this shell"
fi
ls -d /share/pkg* 2>/dev/null | head -5

echo "== complete P1-T0-crash-B (reviewed — see payload header) =="
python ops/runner/runner.py --complete P1-T0-crash-B

echo "== quarantine weak-model DAX output =="
git rm -q --cached ops/l1/out/DAX-W0.5-legwork.json 2>/dev/null || true
rm -f ops/l1/out/DAX-W0.5-legwork.json

echo "== clear parked strikes (infra artifacts + stall failures now split-retried) =="
python ops/runner/runner.py --clear-fail E2-T1-facts E2-T9b-scenarios

echo "== live pass: split per-item retries on kimi-k2.6 =="
python ops/runner/l1_driver.py --live

echo "== capture outputs (incl. per-item partials for provenance) =="
git add -f ops/l1/out/*.json 2>/dev/null || true
cat ops/l1/out/_last_night.json 2>/dev/null
