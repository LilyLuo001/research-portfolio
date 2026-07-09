#!/usr/bin/env bash
# inbox.sh — commands for the box's next 30-min cycle (see run_inbox.sh).
# inbox-version: 2026-07-09-b
#
# Previous cycle results (inbox_log.md @ 788e1f3): E2-T1-facts-B DONE via
# Gemini grounding (fence passed, ¥0); kimi 404'd because kimi-latest is not
# on this key — the /models list shows the K-series: kimi-k2.5/k2.6/k2.7-code.
# The E2 manual specs K2.6 -> pin it, clear the stale strikes, rerun live.

echo "== pin KIMI_MODEL=kimi-k2.6 (from /models discovery; manual specs K2.6) =="
if grep -q '^KIMI_MODEL=' ops/box/.env 2>/dev/null; then
  sed -i 's/^KIMI_MODEL=.*/KIMI_MODEL=kimi-k2.6/' ops/box/.env
else
  echo 'KIMI_MODEL=kimi-k2.6' >> ops/box/.env
fi
export KIMI_MODEL=kimi-k2.6
grep '^KIMI_MODEL=' ops/box/.env

echo "== clear stale strikes (both were infra-era, and T1-B is now DONE) =="
python ops/runner/runner.py --clear-fail E2-T6b-nav E2-T1-facts-B

echo "== live L1 pass on the pinned model =="
python ops/runner/l1_driver.py --live

echo "== capture DONE outputs so channel-A/B union review can happen off-box =="
git add -f ops/l1/out/E2-T1-facts-B.json ops/l1/out/DAX-W0.5-legwork.json 2>/dev/null || true

echo "== state after =="
cat ops/runner/state.json
