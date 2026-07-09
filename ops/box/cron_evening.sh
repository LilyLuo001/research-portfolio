#!/usr/bin/env bash
# cron_evening.sh — 21:00: evening digest, then push briefs/digest/state and
# the L1 debug surface to main. Shares the portfolio-wide lock.
cd "$(dirname "$0")/../.." || exit 1
exec 9>ops/box/.cron.lock
flock -n 9 || exit 0

.venv/bin/python ops/runner/runner.py --digest
git add ops/briefs ops/digest ops/runner/state.json ops/decisions.md ops/l1/out
git commit -q -m "box: nightly digest $(date +%F)" || exit 0
git push -q origin HEAD:main \
  || { git pull --rebase -q origin main && git push -q origin HEAD:main; }
