#!/usr/bin/env bash
# cron_night.sh — 02:00 nightly: run every READY L1 batch (sentinel-fenced,
# budget-capped). Shares the portfolio-wide lock — if a long inbox run is
# still holding it, tonight's tick skips rather than double-dispatching
# (the driver re-runs anything without output tomorrow).
cd "$(dirname "$0")/../.." || exit 1
exec 9>ops/box/.cron.lock
flock -n 9 || exit 0

set -a; . ops/box/.env 2>/dev/null; set +a
.venv/bin/python ops/runner/l1_driver.py --live
