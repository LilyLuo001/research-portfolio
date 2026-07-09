#!/usr/bin/env bash
# cron_halfhour.sh — the box's 30-min tick: pull main, apply L3 decisions
# (which also fires the inbox hook), reap stale leases.
#
# ALL portfolio cron jobs share ONE non-blocking lock (ops/box/.cron.lock):
# if any portfolio job is still running, this tick exits instead of racing it.
# Duplicate/overlapping cron entries were the root cause of the 2026-07-09
# merge wedge (two processes committing and pushing simultaneously).
cd "$(dirname "$0")/../.." || exit 1
exec 9>ops/box/.cron.lock
flock -n 9 || exit 0

git pull --ff-only -q origin main
.venv/bin/python ops/runner/runner.py --apply-decisions
.venv/bin/python ops/runner/runner.py --reap
