#!/usr/bin/env bash
# inbox.sh — commands for the box's next 30-min cycle (see run_inbox.sh).
# inbox-version: 2026-07-09-c
#
# (1) CRON DEDUPE: the box has TWO cron sets — an old hand-installed one and
# the bootstrap-managed block — racing each other every tick (root cause of
# the merge wedge and the phantom double-strike). Strip every portfolio line,
# then reinstall the single managed block, which now delegates to
# ops/box/cron_*.sh scripts sharing one non-blocking flock.
# (2) Payload b's steps (it never got to run): pin KIMI_MODEL=kimi-k2.6,
# clear stale strikes, live rerun, capture DONE outputs. All idempotent.

echo "== crontab BEFORE =="
crontab -l

echo "== strip all portfolio cron lines (both duplicate sets) =="
crontab -l 2>/dev/null | grep -v portfolio | crontab -

echo "== reinstall the single managed block (new flock'd cron_*.sh) =="
INSTALL_CRON=1 bash ops/box/bootstrap.sh 2>&1 | tail -8

echo "== crontab AFTER =="
crontab -l

echo "== pin KIMI_MODEL=kimi-k2.6 (from /models discovery; manual specs K2.6) =="
if grep -q '^KIMI_MODEL=' ops/box/.env 2>/dev/null; then
  sed -i 's/^KIMI_MODEL=.*/KIMI_MODEL=kimi-k2.6/' ops/box/.env
else
  echo 'KIMI_MODEL=kimi-k2.6' >> ops/box/.env
fi
export KIMI_MODEL=kimi-k2.6
grep '^KIMI_MODEL=' ops/box/.env

echo "== clear stale strikes =="
python ops/runner/runner.py --clear-fail E2-T6b-nav E2-T1-facts-B

echo "== live L1 pass on the pinned model =="
python ops/runner/l1_driver.py --live

echo "== capture DONE outputs for off-box review =="
git add -f ops/l1/out/E2-T1-facts-B.json ops/l1/out/DAX-W0.5-legwork.json 2>/dev/null || true

echo "== state after =="
cat ops/runner/state.json
