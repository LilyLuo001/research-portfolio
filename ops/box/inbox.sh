#!/usr/bin/env bash
# inbox.sh — commands for the box's next 30-min cycle (see run_inbox.sh).
# Runs once per version, from the repo root, with ops/box/.env loaded and the
# venv python first on PATH. Output lands in ops/box/inbox_log.md on main.
# inbox-version: 2026-07-09-a

echo "== where am I =="
git log --oneline -2
python --version

echo "== which kimi model ids can this key use =="
python ops/runner/models.py --list kimi

echo "== clear stale strikes (billing-era + contested-sentinel voids) =="
python ops/runner/runner.py --clear-fail E2-T1-facts-B E2-T6b-nav

echo "== live L1 pass (gemini is free + fence-fixed; kimi will ERROR until KIMI_MODEL is pinned — no strikes) =="
python ops/runner/l1_driver.py --live
